"""Time-of-flight sensor against a tape (test C7, register C5): one sensor, one taped distance per run.

Hold a flat, matt board (a box face) square to the sensor at a taped distance from the sensor's front face, then run
  python BenchTest/tof_tape.py --side rear --sensor ahead --tape 0.5
It samples the bridge's /telemetry for 20 s, ignores readings older than 500 ms, and records the median, spread and
error against the tape. Each run is appended to BenchTest/logs/tof_tape.csv. Distances: 0.3, 0.5, 0.75, 1.0 m.
Pass (R8): within about 5 % of the tape below 1 m; the largest distance within 5 % becomes max_range_m.
Front sensors are on the Pi 5 (:8082), rear on the Pi 4 (:8081).
"""
import argparse, csv, json, os, statistics, time, urllib.request

HOSTS = {"front": "http://Pirate5.local:8082/telemetry", "rear": "http://pi4-camera.local:8081/telemetry"}

ap = argparse.ArgumentParser()
ap.add_argument("--side", choices=list(HOSTS), required=True)
ap.add_argument("--sensor", choices=["left", "ahead", "right"], required=True)
ap.add_argument("--tape", type=float, required=True, help="tape distance, sensor face to the board, m")
ap.add_argument("--seconds", type=float, default=20.0)
ap.add_argument("--url", help="override the bridge URL (for example http://192.168.137.85:8081/telemetry)")
a = ap.parse_args()
url = a.url or HOSTS[a.side]

vals, polls, t_end = [], 0, time.time() + a.seconds
while time.time() < t_end:
    polls += 1
    try:
        with urllib.request.urlopen(url, timeout=1) as r:
            tof = json.loads(r.read()).get("tof") or {}
        v = tof.get(a.sensor + "_mm")
        if v is not None and (tof.get("age_ms") or 0) <= 500:
            vals.append(float(v))
    except Exception:
        pass
    time.sleep(0.1)

if len(vals) < 10:
    raise SystemExit(f"only {len(vals)} readings from {a.side} {a.sensor} in {polls} polls: sensor not answering?")
med = statistics.median(vals) / 1000.0
err = med - a.tape
row = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "side": a.side, "sensor": a.sensor, "tape_m": a.tape,
       "n": len(vals), "polls": polls, "median_m": round(med, 4), "spread_m": round(statistics.pstdev(vals) / 1000.0, 4),
       "min_m": round(min(vals) / 1000.0, 4), "max_m": round(max(vals) / 1000.0, 4),
       "error_m": round(err, 4), "error_pct": round(100.0 * err / a.tape, 1)}
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "tof_tape.csv")
new = not os.path.exists(out)
with open(out, "a", newline="") as fh:
    wr = csv.DictWriter(fh, fieldnames=list(row))
    if new:
        wr.writeheader()
    wr.writerow(row)
ok = "PASS" if abs(row["error_pct"]) <= 5.0 else "outside 5 %"
print(f"{a.side} {a.sensor} at {a.tape} m: median {med:.3f} m (spread {row['spread_m']} m, n={len(vals)}), "
      f"error {err * 100:+.1f} cm ({row['error_pct']:+.1f} %) {ok}")
