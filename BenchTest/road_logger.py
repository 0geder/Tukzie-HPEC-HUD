"""Road-test recorder (16 Oct 2026): runs on the laptop, which travels on the trike and hosts the hotspot.

Polls, twice a second, both Pis' JSON endpoints and writes every reply, with the laptop's wall clock, to one JSONL
file per session:
  rear  = Pi 4 bridge  http://<pi4>:8081/telemetry  (ESP32 record: ride features, IMU rates, GNSS, BMS, modem;
          rear ToF; rear fusion)
  front = Pi 5 bridge  http://<pi5>:8082/telemetry  (front ToF and fusion)
  front_alerts / rear_alerts = http://<pi>:8080/alerts (detector alerts with side, track_id, ttc_s)
Markers: type a run id and press Enter (for example "S3 run2 start 20kmh"); each line is written as a marker
record, so every run can be cut out of the file afterwards. Type "q" and Enter to stop.

Usage: python BenchTest/road_logger.py [--pi4 192.168.137.220] [--pi5 192.168.137.128] [--out BenchTest/logs]
Nothing is sent anywhere; the file stays on the laptop.
"""
import argparse
import json
import os
import sys
import threading
import time
import urllib.request

ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
ap.add_argument("--pi4", default="192.168.137.220")
ap.add_argument("--pi5", default="192.168.137.128")
ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"))
ap.add_argument("--period", type=float, default=0.5)
a = ap.parse_args()

SOURCES = {
    "rear": f"http://{a.pi4}:8081/telemetry",
    "front": f"http://{a.pi5}:8082/telemetry",
    "rear_alerts": f"http://{a.pi4}:8080/alerts",
    "front_alerts": f"http://{a.pi5}:8080/alerts",
}
os.makedirs(a.out, exist_ok=True)
path = os.path.join(a.out, time.strftime("%Y-%m-%d_%H%M%S_roadtest.jsonl"))
f = open(path, "a", encoding="utf-8")
lock = threading.Lock()
stop = threading.Event()
counts = {k: [0, 0] for k in SOURCES}           # ok, failed


def write(rec):
    with lock:
        f.write(json.dumps(rec, separators=(",", ":")) + "\n")
        f.flush()


def poll(name, url):
    """One thread per source, so a Pi that is down does not slow the others."""
    while not stop.is_set():
        t0 = time.time()
        rec = {"t": round(t0, 3), "src": name}
        try:
            with urllib.request.urlopen(url, timeout=1.0) as r:
                rec["data"] = json.loads(r.read())
            counts[name][0] += 1
        except Exception as e:                    # unreachable, timeout, bad JSON: recorded, never fatal
            rec["error"] = type(e).__name__
            counts[name][1] += 1
        write(rec)
        stop.wait(max(0.0, a.period - (time.time() - t0)))


def status():
    while not stop.wait(10):
        print("  [%s] " % time.strftime("%H:%M:%S") +
              "  ".join(f"{k} {ok}/{ok + bad}" for k, (ok, bad) in counts.items()), flush=True)


write({"t": round(time.time(), 3), "src": "marker", "text": "session start", "sources": SOURCES})
for _name, _url in SOURCES.items():
    threading.Thread(target=poll, args=(_name, _url), daemon=True).start()
threading.Thread(target=status, daemon=True).start()
print(f"Recording to {path}\nType a marker and press Enter (e.g. 'S3 run2 start 20kmh'); 'q' to stop.", flush=True)
try:
    for line in sys.stdin:
        line = line.strip()
        if line.lower() in ("q", "quit", "exit"):
            break
        if line:
            write({"t": round(time.time(), 3), "src": "marker", "text": line})
            print(f"  marker at {time.strftime('%H:%M:%S')}: {line}", flush=True)
except KeyboardInterrupt:
    pass
stop.set()
time.sleep(0.3)
write({"t": round(time.time(), 3), "src": "marker", "text": "session end"})
f.close()
print("Saved", path)
