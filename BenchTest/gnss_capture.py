"""Capture GNSS output from the telemetry unit outdoors.

Two modes:
  raw   (default, firmware v0.5.1+): sends "!gnssraw" once, so the firmware
        prints the modem's raw +CGNSSINFO reply on every one of its own
        polls. No extra AT commands are sent, so nothing competes with the
        firmware for the modem's replies.
  query (older firmware): sends AT+CGNSSINFO every 15 s through the AT
        pass-through. This competes with the firmware's own polling and can
        garble replies (seen on 29 Sep 2026), so use it only if needed.

If a reference position is given (for example from a phone), every parsed
fix is compared with it. Saves every line with a time stamp.

Usage: python gnss_capture.py [COM10] [minutes] [output.log] [raw|query] [ref_lat ref_lon]
"""
import math
import re
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM10"
MINUTES = float(sys.argv[2]) if len(sys.argv) > 2 else 5
OUT = sys.argv[3] if len(sys.argv) > 3 else "logs/gnss_capture.log"
MODE = sys.argv[4] if len(sys.argv) > 4 else "raw"
REF = (float(sys.argv[5]), float(sys.argv[6])) if len(sys.argv) > 6 else None

ser = serial.Serial()
ser.port, ser.baudrate, ser.timeout = PORT, 115200, 0.2
ser.dtr, ser.rts = False, False
ser.open()

t0 = time.monotonic()
lines, buf = [], b""
end = t0 + MINUTES * 60
next_query = t0 + 3
raw_on = False
first_fix = None


def now():
    return time.monotonic() - t0


while time.monotonic() < end:
    if MODE == "query" and time.monotonic() >= next_query:
        ser.write(b"AT+CGNSSINFO\r\n")
        lines.append((now(), "> AT+CGNSSINFO"))
        next_query = time.monotonic() + 15
    if MODE == "raw" and not raw_on and (now() > 3):
        ser.write(b"!gnssraw\r\n")
        lines.append((now(), "> !gnssraw"))
        raw_on = True
    buf += ser.read(4096)
    while b"\n" in buf:
        raw, buf = buf.split(b"\n", 1)
        text = raw.decode("utf-8", "replace").rstrip("\r")
        lines.append((now(), text))
        if "raw GNSS replies off" in text and MODE == "raw":
            ser.write(b"!gnssraw\r\n")   # it was already on; turn it back on
            lines.append((now(), "> !gnssraw"))
        if first_fix is None and re.search(r"\[GNSS\] fix mode=", text):
            first_fix = now()
            print("FIRST FIX at %.0f s: %s" % (first_fix, text), flush=True)
if MODE == "raw":
    ser.write(b"!gnssraw\r\n")   # leave raw printing off afterwards
ser.close()

with open(OUT, "w", encoding="utf-8") as f:
    f.write("# GNSS capture, BenchTest/gnss_capture.py on %s, %.0f min, mode %s.\n" % (PORT, MINUTES, MODE))
    f.write("# Reference position: %s.\n" % ("%.7f, %.7f (phone)" % REF if REF else "none"))
    for t, text in lines:
        f.write("[%7.2fs] %s\n" % (t, text))

fixes = []
for t, text in lines:
    m = re.search(r"\[GNSS\] fix mode=(\d+) lat=([-\d.]+) lon=([-\d.]+) alt=([-\d.]+)m speed=([-\d.]+) sats=(\d+) hdop=([-\d.na]+)", text)
    if m:
        fixes.append((t, float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5)), int(m.group(6)), m.group(7)))
ignored = [x for x in lines if re.search(r"\[GNSS\] (damaged|implausible|coordinates out|fix reply without)", x[1])]
nofix = [x for x in lines if "[GNSS] no fix" in x[1]]
rawl = [x for x in lines if "[GNSS] raw" in x[1] or "+CGNSSINFO:" in x[1]]
print("lines %d | raw replies %d | fixes %d | no-fix %d | ignored as damaged or implausible %d | log %s"
      % (len(lines), len(rawl), len(fixes), len(nofix), len(ignored), OUT))
if first_fix is not None:
    print("first fix after %.0f s of capture" % first_fix)
if fixes:
    sats = [x[5] for x in fixes]
    print("satellites %d to %d | altitude %.1f to %.1f m | speed field %.3f to %.3f"
          % (min(sats), max(sats), min(x[3] for x in fixes), max(x[3] for x in fixes),
             min(x[4] for x in fixes), max(x[4] for x in fixes)))
    if REF:
        d = sorted(math.hypot((x[1] - REF[0]) * 111320, (x[2] - REF[1]) * 111320 * math.cos(math.radians(REF[0]))) for x in fixes)
        print("distance to reference: median %.1f m, 95th percentile %.1f m, max %.1f m (n=%d)"
              % (d[len(d) // 2], d[min(len(d) - 1, int(0.95 * len(d)))], d[-1], len(d)))
for t, text in rawl[-2:]:
    print("  %7.1fs %s" % (t, text.strip()[:170]))
for t, text in ignored[-3:]:
    print("  %7.1fs %s" % (t, text.strip()[:170]))
