"""Bench test for firmware v0.5.0 on the telemetry unit (COM10).

Resets the board, records the boot, checks the new serial commands, then
runs the flash-write stall test (logging on for 120 s, then off for 120 s)
and an MQTT reconnect request. Every line is saved with its time since the
reset, in the same format as the other bench logs, and a summary is printed.

Usage: python v050_bench_test.py [COM10] [output.log]
Keep the board still and close any other serial monitor while it runs.
"""
import re
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM10"
OUT = sys.argv[2] if len(sys.argv) > 2 else "logs/v050_bench_test.log"

ser = serial.Serial()
ser.port, ser.baudrate, ser.timeout = PORT, 115200, 0.2
ser.dtr, ser.rts = False, False
ser.open()

t0 = time.monotonic()
lines = []        # (t, text)
marks = []        # (t, label) for phase boundaries
buf = b""


def now():
    return time.monotonic() - t0


def pump(seconds, stop_on=None):
    """Read lines for up to `seconds`; stop early if a line matches stop_on."""
    global buf
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        buf += ser.read(4096)
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            text = raw.decode("utf-8", "replace").rstrip("\r")
            lines.append((now(), text))
            if stop_on and re.search(stop_on, text):
                return True
    return False


def send(cmd):
    marks.append((now(), cmd))
    lines.append((now(), "> " + cmd))
    ser.write((cmd + "\r\n").encode())
    ser.flush()


# Reset into the application (RTS drives EN on the USB serial/JTAG bridge).
# The ESP32-S3's native USB port disappears while the chip resets, so the
# handle is closed and the port reopened as soon as Windows shows it again;
# the firmware waits up to 3 s for a serial connection before printing.
ser.rts = True
time.sleep(0.2)
ser.rts = False
t0 = time.monotonic()
try:
    ser.close()
except Exception:
    pass
time.sleep(0.3)
for _ in range(100):
    try:
        ser.open()
        break
    except serial.SerialException:
        time.sleep(0.1)
else:
    sys.exit("port %s did not come back after reset" % PORT)

booted = pump(90, stop_on=r"Entering pass-through")
pump(3)
send("!help"); pump(2)
send("!status"); pump(3)

marks.append((now(), "PHASE logging on"))
pump(120)
send("!log off"); pump(1)
marks.append((now(), "PHASE logging off"))
pump(120)
send("!log on"); pump(1)
send("!status"); pump(3)
send("!mqtt")
pump(75)
send("!status"); pump(3)
ser.close()

with open(OUT, "w", encoding="utf-8") as f:
    f.write("# Firmware v0.5.0 bench test, run by BenchTest/v050_bench_test.py on %s.\n" % PORT)
    f.write("# Board still on the bench. Phases: boot, commands, 120 s logging on, 120 s logging off (!log off), !mqtt reconnect.\n")
    for t, text in lines:
        f.write("[%7.2fs] %s\n" % (t, text))

# ---- summary ----
def phase_of(t):
    label = "boot"
    for mt, m in marks:
        if mt <= t and m.startswith("PHASE"):
            label = m[6:]
        elif mt <= t and m == "!log on":
            label = "after"
    return label

gaps = {}
for t, text in lines:
    m = re.match(r"IMU(\d): \d+ samples \(([\d.]+) Hz\)\s+dt_us\[min=\d+ avg=\d+ max=(\d+)\]\s+dropped=(\d+)", text)
    if m:
        gaps.setdefault(phase_of(t), []).append((t, int(m.group(1)), float(m.group(2)), int(m.group(3)), int(m.group(4))))

print("booted to pass-through:", booted, "| lines:", len(lines), "| log:", OUT)
for text in [x for _, x in lines if re.search(r"Firmware v|\[CAL\]|Overall:|LittleFS mounted", x)]:
    print("  ", text.strip())
for ph in ("logging on", "logging off"):
    g = gaps.get(ph, [])
    if not g:
        print(ph, ": no IMU stats lines"); continue
    worst = max(x[3] for x in g) / 1000
    big = [(round(x[0]), "IMU%d" % x[1], x[3] / 1000) for x in g if x[3] > 10000]
    print("%-12s windows=%d  worst max gap=%.1f ms  windows over 10 ms=%d  rates %.1f-%.1f Hz  dropped=%d"
          % (ph, len(g), worst, len(big), min(x[2] for x in g), max(x[2] for x in g), sum(x[4] for x in g)))
    if big:
        print("   gaps over 10 ms at (s, sensor, ms):", big[:12])
print("command and MQTT lines:")
for t, text in lines:
    if re.search(r"^> |\[CMD\]|\[MQTT\]|CMQTT", text):
        print("  %7.2fs %s" % (t, text[:140]))
