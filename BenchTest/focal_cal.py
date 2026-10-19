"""Camera focal-length calibration (test C5): record the detector's box width for an object at a measured distance.

Stand (or place) one object of known width straight in front of the camera at a taped distance, then run
  python BenchTest/focal_cal.py --dist 2.0 --width 0.42
It samples the detector's /detections for a few seconds, takes the median box width of the chosen class, and
works out the focal length in pixels:  f = distance x box_width_px / real_width.  Each run is appended to
BenchTest/logs/focal_cal.csv; run it at 3 to 5 distances and the summary line gives the mean and spread.
The detector's current setting is --focal-length-px 600 (uncalibrated).
"""
import argparse, csv, json, os, statistics, time, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--pi", default="192.168.137.128", help="Pi running the detector (front Pi 5 by default)")
ap.add_argument("--dist", type=float, required=True, help="tape distance, camera lens to the object's front, m")
ap.add_argument("--width", type=float, required=True, help="object's real width across the camera, m")
ap.add_argument("--cls", default="person")
ap.add_argument("--seconds", type=float, default=4.0)
ap.add_argument("--frame-w", type=int, default=640)
a = ap.parse_args()

widths, ests, t_end = [], [], time.time() + a.seconds
while time.time() < t_end:
    try:
        with urllib.request.urlopen(f"http://{a.pi}:8080/detections", timeout=1) as r:
            d = json.loads(r.read())
        dets = [x for x in d.get("detections", []) if x["class"] == a.cls]
        if dets:
            x = max(dets, key=lambda q: q["bbox"][2] - q["bbox"][0])      # the biggest, i.e. nearest, one
            x0, _, x1, _ = x["bbox"]
            if x0 > 0.01 and x1 < 0.99:                                     # box not cut by the image edge
                widths.append((x1 - x0) * a.frame_w)
                ests.append(x.get("est_distance_m"))
    except Exception:
        pass
    time.sleep(0.1)

if len(widths) < 5:
    raise SystemExit(f"only {len(widths)} usable detections of '{a.cls}' (not seen, or touching the image edge)")
w = statistics.median(widths)
f = a.dist * w / a.width
row = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "pi": a.pi, "class": a.cls, "dist_m": a.dist, "width_m": a.width,
       "samples": len(widths), "box_px_median": round(w, 1), "box_px_spread": round(statistics.pstdev(widths), 1),
       "focal_px": round(f, 1), "est_dist_at_600": round(statistics.median([e for e in ests if e]), 2)}
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "focal_cal.csv")
new = not os.path.exists(out)
with open(out, "a", newline="") as fh:
    wr = csv.DictWriter(fh, fieldnames=list(row))
    if new:
        wr.writeheader()
    wr.writerow(row)
print(f"{a.dist} m: box {w:.0f} px (spread {row['box_px_spread']}), focal {f:.0f} px; "
      f"the detector (600 px) said {row['est_dist_at_600']} m")
fs = [float(r["focal_px"]) for r in csv.DictReader(open(out)) if r["pi"] == a.pi]
if len(fs) > 1:
    print(f"all runs on {a.pi}: focal {statistics.mean(fs):.0f} px mean, {statistics.pstdev(fs):.0f} px spread, n={len(fs)}")
