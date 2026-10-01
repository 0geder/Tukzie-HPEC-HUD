"""Benchmark a YOLO model on the Raspberry Pi 4 camera, measured the same way
as hazard_detector.py, so the numbers compare directly with SSD-MobileNet
(19.5 fps, median 102 ms sensor to result, 30 Sep 2026).

Per frame it records: queue (sensor readout to the frame reaching this
script, from the frame's SensorTimestamp on the monotonic clock), and the
model's own preprocess, inference and postprocess times. For segmentation
models the total also includes turning each mask into a polygon, since
that is what drawing a polygon needs. Total = sensor readout to result.

Frames exist only in memory and are never written to disk; only timings
and detection counts are kept.

Usage (on the Pi, detector stopped, camera free):
  python yolo_bench.py --model yolo11n_ncnn_model --imgsz 320 --duration 60 \
      --tuning ov5647_noir.json --saturation 1.8 --out bench_yolo11n_320.csv
"""
import argparse
import csv
import statistics
import time

from picamera2 import Picamera2
from ultralytics import YOLO


def pct(vals, p):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(p * len(vals)))]


def cpu_temp_c():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read()) / 1000
    except OSError:
        return float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="NCNN model folder or .pt/.tflite file")
    ap.add_argument("--imgsz", type=int, default=320)
    ap.add_argument("--duration", type=float, default=60)
    ap.add_argument("--warmup", type=int, default=10, help="frames ignored at the start")
    ap.add_argument("--conf", type=float, default=0.5, help="same threshold as the detector")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--tuning", default=None)
    ap.add_argument("--saturation", type=float, default=None)
    ap.add_argument("--out", default=None, help="per-frame timings CSV")
    args = ap.parse_args()

    model = YOLO(args.model, task=None)
    seg = model.task == "segment"

    if args.tuning:
        picam2 = Picamera2(tuning=Picamera2.load_tuning_file(args.tuning))
    else:
        picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(
        main={"size": (args.width, args.height), "format": "RGB888"}))
    picam2.start()
    if args.saturation is not None:
        picam2.set_controls({"Saturation": args.saturation})

    print(f"Model {args.model} ({model.task}), imgsz {args.imgsz}, conf {args.conf}, {args.duration:.0f} s")
    rows, n = [], 0
    start = time.monotonic()
    try:
        while time.monotonic() - start < args.duration:
            request = picam2.capture_request()
            try:
                frame = request.make_array("main")   # stored B, G, R: what Ultralytics expects
                sensor_ns = request.get_metadata().get("SensorTimestamp")
            finally:
                request.release()
            t_got = time.monotonic_ns()
            r = model.predict(frame, imgsz=args.imgsz, conf=args.conf, verbose=False)[0]
            polys = 0
            if seg and r.masks is not None:
                polys = len(r.masks.xy)               # mask outlines as polygons, in frame pixels
            t_done = time.monotonic_ns()
            n += 1
            if n <= args.warmup or sensor_ns is None:
                continue
            rows.append({
                "queue_ms": (t_got - sensor_ns) / 1e6,
                "pre_ms": r.speed["preprocess"],
                "inf_ms": r.speed["inference"],
                "post_ms": r.speed["postprocess"],
                "total_ms": (t_done - sensor_ns) / 1e6,
                "detections": len(r.boxes),
                "polygons": polys,
                "t_s": (t_done / 1e9) - start,
            })
    finally:
        picam2.stop()

    elapsed = rows[-1]["t_s"] - rows[0]["t_s"] if len(rows) > 1 else float("nan")
    fps = (len(rows) - 1) / elapsed if len(rows) > 1 else float("nan")
    print(f"frames timed: {len(rows)} (after {args.warmup} warm-up), {fps:.1f} fps, CPU {cpu_temp_c():.1f} C")
    for k in ("queue_ms", "pre_ms", "inf_ms", "post_ms", "total_ms"):
        v = [row[k] for row in rows]
        print(f"  {k[:-3]:6s} p50 {statistics.median(v):7.1f}  p95 {pct(v, 0.95):7.1f}  max {max(v):7.1f} ms")
    print(f"  detections per frame: mean {statistics.mean(r['detections'] for r in rows):.2f}")
    if args.out:
        with open(args.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print("per-frame timings:", args.out)


if __name__ == "__main__":
    main()
