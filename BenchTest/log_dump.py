"""Save the telemetry unit's stored log (LittleFS /telemetry.log) to the laptop.

Sends !log dump and keeps the "LOG|index|length|record" lines whose length
matches (other tasks keep printing while it runs, and their output can land
inside a record). Repeats the dump, up to MAX_PASSES times, until every
index from 0 to the firmware's line count has arrived intact. Then checks
each record as JSON (records written before v0.6.3 contain "nan", which
JSON does not allow; these are counted and also saved with nan replaced by
null for analysis) and summarises the contents. With --clear, the log is
deleted on the board once the copy is complete. Does not reset the board.

Usage: python log_dump.py [COM10] [output.jsonl] [--clear]
Writes output.jsonl (records exactly as stored) and output.clean.jsonl.
"""
import json
import re
import sys
import time

import serial

args = [a for a in sys.argv[1:] if not a.startswith("--")]
PORT = args[0] if args else "COM10"
OUT = args[1] if len(args) > 1 else "logs/telemetry_dump.jsonl"
CLEAR = "--clear" in sys.argv
MAX_PASSES = 4

ser = serial.Serial()
ser.port, ser.baudrate, ser.timeout = PORT, 115200, 0.2
ser.dtr, ser.rts = False, False
ser.open()
time.sleep(1)

got = {}          # index -> record
total = None      # (lines, bytes) from the firmware's end marker
for p in range(1, MAX_PASSES + 1):
    ser.reset_input_buffer()
    ser.write(b"!log dump\r\n")
    t0, buf, end, before = time.monotonic(), b"", None, len(got)
    while time.monotonic() - t0 < 600 and end is None:
        buf += ser.read(65536)
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            text = raw.decode("utf-8", "replace").rstrip("\r")
            m = re.match(r"LOG\|(\d+)\|(\d+)\|(.*)$", text)
            if m:
                if len(m.group(3).encode("utf-8")) == int(m.group(2)):
                    got.setdefault(int(m.group(1)), m.group(3))
                continue
            m = re.search(r"\[LOGDUMP\] end (\d+) lines (\d+) bytes", text)
            if m:
                end = (int(m.group(1)), int(m.group(2)))
            elif "[LOGDUMP] no log file" in text:
                end = (0, 0)
    total = end
    missing = [] if total is None else [i for i in range(total[0]) if i not in got]
    print("pass %d: %.0f s, %d new records, %d of %s intact, %d missing"
          % (p, time.monotonic() - t0, len(got) - before, len(got),
             total[0] if total else "?", len(missing)))
    if total is not None and not missing:
        break

complete = total is not None and all(i in got for i in range(total[0]))
records = [got[i] for i in sorted(got)]
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    for r in records:
        f.write(r + "\n")

nan_lines, bad, parsed = 0, [], []
clean_out = OUT.replace(".jsonl", ".clean.jsonl")
with open(clean_out, "w", encoding="utf-8", newline="\n") as f:
    for i, r in enumerate(records):
        c = re.sub(r":-?(nan|inf)\b", ":null", r)
        if c != r:
            nan_lines += 1
        try:
            parsed.append(json.loads(c))
            f.write(c + "\n")
        except ValueError:
            bad.append(i)

print("complete copy: %s (%d records) -> %s" % ("YES" if complete else "NO", len(records), OUT))
print("records containing nan (not valid JSON as stored): %d; still invalid after nan -> null: %d"
      % (nan_lines, len(bad)))
for i in bad[:3]:
    print("   ", records[i][:200])
layouts = {}
for d in parsed:
    k = ",".join(sorted(d))
    layouts[k] = layouts.get(k, 0) + 1
print("record layouts (count, top-level fields):")
for k, n in sorted(layouts.items(), key=lambda x: -x[1]):
    print("   %5d  %s" % (n, k))
print("records with a GNSS fix: %d; with a valid BMS reading: %d; about %.1f h of records at 10 s each"
      % (sum(1 for d in parsed if (d.get("gnss") or {}).get("valid")),
         sum(1 for d in parsed if (d.get("bms") or {}).get("checksum_ok")),
         len(records) * 10 / 3600))

if CLEAR:
    if complete:
        ser.write(b"!log clear\r\n")
        time.sleep(1.5)
        out = ser.read(8192).decode("utf-8", "replace")
        print("clear:", "done" if "deleted" in out else "no confirmation seen")
    else:
        print("not clearing: the copy is incomplete")
ser.close()
