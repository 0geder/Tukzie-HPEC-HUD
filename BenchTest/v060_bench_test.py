"""Bench test for firmware v0.6.0 on the telemetry unit (COM10).

Checks the three v0.6.0 changes in one run with the board still on the
bench and logging on throughout:
  1. buffered flash logging: acquisition gaps over 10 ms now occur only at
     a log flush (about once a minute), not every 10 s;
  2. signal strength (AT+CSQ) shown in !status;
  3. Hall pulse counter in bench loopback on the sync pin: total edges
     between two !status readings must match 2 edges per second.

Usage: python v060_bench_test.py [COM10] [output.log] [seconds]
Close any other serial monitor first.
"""
import re
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM10"
OUT = sys.argv[2] if len(sys.argv) > 2 else "logs/v060_bench_test.log"
RUN_S = float(sys.argv[3]) if len(sys.argv) > 3 else 330

ser = serial.Serial()
ser.port, ser.baudrate, ser.timeout = PORT, 115200, 0.2
ser.dtr, ser.rts = False, False
ser.open()
t0 = time.monotonic()
lines, buf = [], b""


def now():
    return time.monotonic() - t0


def pump(seconds, stop_on=None):
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
    lines.append((now(), "> " + cmd))
    ser.write((cmd + "\r\n").encode())
    ser.flush()


# Reset into the application; the native USB port re-enumerates.
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

pump(90, stop_on=r"Entering pass-through")
pump(3)
send("!status"); pump(3)
pump(RUN_S)
send("!status"); pump(3)
ser.close()

with open(OUT, "w", encoding="utf-8") as f:
    f.write("# Firmware v0.6.0 bench test, BenchTest/v060_bench_test.py on %s.\n" % PORT)
    f.write("# Board still on the bench, logging on throughout, %.0f s run. Hall counter in loopback on the sync pin.\n" % RUN_S)
    for t, text in lines:
        f.write("[%7.2fs] %s\n" % (t, text))

# ---- summary ----
fw = [x for _, x in lines if "firmware v" in x.lower()]
print("firmware:", fw[-1] if fw else "?")
flushes = [(t, float(m.group(1))) for t, x in lines
           for m in [re.search(r"\[LOG\] flushed \d+ lines, \d+ bytes in ([\d.]+) ms", x)] if m]
print("flushes: %d, durations %s ms" % (len(flushes), [d for _, d in flushes]))

wins = []
for t, x in lines:
    m = re.match(r"IMU(\d): \d+ samples \(([\d.]+) Hz\)\s+dt_us\[min=\d+ avg=\d+ max=(\d+)\]\s+dropped=(\d+)", x)
    if m:
        wins.append((t, int(m.group(1)), float(m.group(2)), int(m.group(3)) / 1000, int(m.group(4))))
if wins:
    big = [w for w in wins if w[3] > 10]
    near = [w for w in big if any(0 <= w[0] - ft <= 3.5 for ft, _ in flushes)]
    print("IMU stats windows: %d, rates %.1f to %.1f Hz, dropped %d" %
          (len(wins), min(w[2] for w in wins), max(w[2] for w in wins), sum(w[4] for w in wins)))
    print("windows with a gap over 10 ms: %d, of which within 3.5 s after a flush: %d" % (len(big), len(near)))
    print("   (s, imu, ms):", [(round(w[0]), w[1], w[3]) for w in big][:20])
    quiet = [w[3] for w in wins if w not in big]
    if quiet:
        print("worst gap in the other windows: %.1f ms" % max(quiet))

st = [(t, x) for t, x in lines if "[CMD] hall:" in x]
if len(st) >= 2:
    e = [(t, int(re.search(r"hall: (\d+) edges", x).group(1))) for t, x in st]
    (ta, ea), (tb, eb) = e[0], e[-1]
    print("hall: %d edges in %.1f s between the two !status = %.2f edges/s (expect 2.00)" %
          (eb - ea, tb - ta, (eb - ea) / (tb - ta)))
for t, x in lines:
    if "[CMD] signal:" in x or "[CMD] log buffer:" in x or "[CMD] local log:" in x or "[HALL]" in x:
        print("  %6.1fs %s" % (t, x))
