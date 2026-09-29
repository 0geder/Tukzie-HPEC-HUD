"""Signal-loss recovery test for the telemetry unit's MQTT link (T6).

Switches the modem's radio off with AT+CFUN=4 (through the firmware's AT
pass-through), keeps it off for OFF_S seconds, switches it back on with
AT+CFUN=1, and records how the firmware notices the loss, backs off and
reconnects. Does not reset the board.

Usage: python signal_loss_test.py [COM10] [off_seconds] [output.log]
"""
import re
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM10"
OFF_S = float(sys.argv[2]) if len(sys.argv) > 2 else 60
OUT = sys.argv[3] if len(sys.argv) > 3 else "logs/signal_loss_test.log"
MAX_AFTER_S = 420   # give up waiting for a reconnect this long after radio on

ser = serial.Serial()
ser.port, ser.baudrate, ser.timeout = PORT, 115200, 0.2
ser.dtr, ser.rts = False, False
ser.open()
t0 = time.monotonic()
lines, buf, marks = [], b"", {}


def now():
    return time.monotonic() - t0


def pump(seconds, stop=None):
    global buf
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        buf += ser.read(4096)
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            text = raw.decode("utf-8", "replace").rstrip("\r")
            lines.append((now(), text))
            if stop and stop(text):
                return True
    return False


def send(cmd):
    marks.setdefault(cmd, now())
    lines.append((now(), "> " + cmd))
    ser.write((cmd + "\r\n").encode())


send("!status"); pump(5)
send("AT+CFUN=4"); pump(OFF_S)
send("AT+CFUN=1")
radio_on = now()
# wait for the firmware to reconnect after the radio returns, then two more publish cycles
reconnected = pump(MAX_AFTER_S, stop=lambda t: "[MQTT] Connected." in t and now() > radio_on)
if reconnected:
    pump(25)
send("!status"); pump(4)
ser.close()

with open(OUT, "w", encoding="utf-8") as f:
    f.write("# Signal-loss recovery test (T6), BenchTest/signal_loss_test.py on %s.\n" % PORT)
    f.write("# Radio off with AT+CFUN=4 for %.0f s, then AT+CFUN=1; board not reset.\n" % OFF_S)
    for t, text in lines:
        f.write("[%7.2fs] %s\n" % (t, text))

off_t = marks["AT+CFUN=4"]
print("radio off at %.1f s, on at %.1f s | log %s" % (off_t, radio_on, OUT))
for t, text in lines:
    if re.search(r"\[MQTT\]|CMQTT|\[CMD\] mqtt|\+CFUN|^> AT", text):
        print("  %7.1fs %s" % (t, text[:150]))
conn = [t for t, x in lines if "[MQTT] Connected." in x and t > radio_on]
lost = [t for t, x in lines if re.search(r"treating the session as lost|Connection lost", x) and t > off_t]
print("loss detected %s | reconnected %s"
      % ("%.1f s after radio off" % (lost[0] - off_t) if lost else "no",
         "%.1f s after radio on" % (conn[0] - radio_on) if conn else "no (within %d s)" % MAX_AFTER_S))
