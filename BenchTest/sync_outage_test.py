"""Store-and-forward outage test for firmware v0.7.4 (T15).

Lets records flow for LEAD_S seconds, switches the modem's radio off with
AT+CFUN=4 (through the firmware's AT pass-through) for OFF_MIN minutes,
switches it on with AT+CFUN=1, and polls !sync every 5 s until the backlog is
zero (or MAX_DRAIN_S passes). Records every serial line with its time, and
prints the !sync figures before, during and after, the reconnect time and the
drain time (radio on to backlog 0, and reconnect to backlog 0). Does not reset
the board. The database side is checked separately with Server/sync_report.py.

Instead of AT+CFUN=4, the outage can be made by unplugging the LTE antenna:
run with off_minutes 0 and --manual, unplug when told, press Enter to plug back.

Usage: python sync_outage_test.py [COM10] [off_minutes] [output.log] [--manual]
"""
import re
import sys
import time

import serial

args = [a for a in sys.argv[1:] if not a.startswith("--")]
PORT = args[0] if args else "COM10"
OFF_MIN = float(args[1]) if len(args) > 1 else 10
OUT = args[2] if len(args) > 2 else "logs/sync_outage_test.log"
MANUAL = "--manual" in sys.argv
LEAD_S = 60          # records flowing normally before the outage
MAX_DRAIN_S = 900    # give up waiting for backlog 0 this long after radio on

ser = serial.Serial()
ser.port, ser.baudrate, ser.timeout = PORT, 115200, 0.2
ser.dtr, ser.rts = False, False
ser.open()
t0 = time.monotonic()
lines, buf, marks, syncs = [], b"", {}, []
SYNC_RE = re.compile(r"\[SYNC\] boot=(\d+).*?next_seq=(\d+).*?acked=(\d+).*?backlog=(\d+).*?replayed=(\d+)"
                     r".*?lost=(\d+).*?mqtt=(\w+)")


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
            m = SYNC_RE.search(text)
            if m:
                syncs.append((now(), dict(zip(("boot", "next_seq", "acked", "backlog", "replayed", "lost"),
                                              map(int, m.groups()[:6])), mqtt=m.group(7))))
            if stop and stop(text):
                return True
    return False


def send(cmd):
    marks.setdefault(cmd, now())
    lines.append((now(), "> " + cmd))
    ser.write((cmd + "\r\n").encode())


def sync_now():
    n = len(syncs)
    send("!sync")
    pump(3, stop=lambda t: len(syncs) > n)
    return syncs[-1][1] if len(syncs) > n else None


before = sync_now()
pump(LEAD_S)
start = sync_now()
if MANUAL:
    input("Unplug the LTE antenna now, wait, then press Enter when it is plugged back in... ")
    marks["off"] = now()
else:
    send("AT+CFUN=4")
    end = time.monotonic() + OFF_MIN * 60
    while time.monotonic() < end:
        pump(min(60, end - time.monotonic()))
        sync_now()
    send("AT+CFUN=1")
radio_on = now()
during = syncs[-1][1] if syncs else None
drained_at = None
while now() - radio_on < MAX_DRAIN_S:
    pump(5)
    s = sync_now()
    if s and s["mqtt"] == "up" and s["backlog"] == 0 and now() - radio_on > 10:
        drained_at = now()
        break
pump(25)          # two more live records after the drain
after = sync_now()
ser.close()

conn = [t for t, x in lines if "[MQTT] Connected." in x and t > radio_on]
with open(OUT, "w", encoding="utf-8") as f:
    f.write("# Store-and-forward outage test (T15), BenchTest/sync_outage_test.py on %s.\n" % PORT)
    f.write("# %s; board not reset.\n" % ("antenna unplugged by hand" if MANUAL else
                                         "radio off with AT+CFUN=4 for %.1f min, then AT+CFUN=1" % OFF_MIN))
    for t, text in lines:
        f.write("[%8.2fs] %s\n" % (t, text))

print("log", OUT)
for label, s in (("before", before), ("outage start", start), ("end of outage", during), ("after", after)):
    print("  %-14s %s" % (label, s))
print("radio on at %.1f s; reconnected %s; backlog 0 %s" % (
    radio_on,
    "%.1f s after radio on" % (conn[0] - radio_on) if conn else "not seen",
    ("%.1f s after radio on (%.1f s after reconnect)" % (drained_at - radio_on, drained_at - conn[0])
     if conn else "%.1f s after radio on" % (drained_at - radio_on)) if drained_at else
    "NOT reached within %d s" % MAX_DRAIN_S))
if before and after:
    print("records made during the test: %d; replayed this boot: %d; lost counter change: %d" % (
        after["next_seq"] - before["next_seq"], after["replayed"], after["lost"] - before["lost"]))
print("Now run Server/sync_report.py on the database for this time window (see T15).")
