"""Benchmark a YOLO11 NCNN model on the Raspberry Pi 4 camera without PyTorch,
timed the same way as hazard_detector.py and yolo_bench.py, so the numbers
compare directly with SSD-MobileNet (19.5 fps, median 102 ms, 30 Sep 2026).

Runs the exported NCNN model with the ncnn Python package only; preprocessing
(letterbox), box decoding and non-maximum suppression are done here in numpy.
For segmentation models the masks are also built (coefficients times prototypes,
sigmoid, crop to the box, threshold) and turned into polygons when OpenCV is
available, since that is the extra work a polygon display needs.

Per frame: queue (sensor readout to the frame reaching this script, from the
frame's SensorTimestamp on the monotonic clock), pre, inference, post, and the
total from sensor readout to result. Frames exist only in memory and are never
written to disk; only timings and detection counts are kept.

Usage (on the Pi, detector stopped, camera free):
  python ncnn_bench.py --model yolo11n_320_ncnn_model --imgsz 320 --duration 60 \
      --tuning ov5647_noir.json --saturation 1.8 --out results/ncnn_yolo11n_320.csv
"""
import argparse
import csv
import os
import statistics
import time

import numpy as np
import ncnn
from picamera2 import Picamera2

try:
    import cv2
except ImportError:  # polygons are skipped without OpenCV; masks are still built
    cv2 = None


def pct(vals, p):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(p * len(vals)))]


def cpu_temp_c():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read()) / 1000
    except OSError:
        return float("nan")


def letterbox(rgb, size):
    """Resize keeping the aspect ratio and pad to size x size with grey 114, as Ultralytics does."""
    h, w = rgb.shape[:2]
    r = min(size / h, size / w)
    nh, nw = int(round(h * r)), int(round(w * r))
    if cv2 is not None:
        small = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
    else:  # nearest-neighbour fallback
        ys = (np.arange(nh) / r).astype(int).clip(0, h - 1)
        xs = (np.arange(nw) / r).astype(int).clip(0, w - 1)
        small = rgb[ys][:, xs]
    out = np.full((size, size, 3), 114, np.uint8)
    top, left = (size - nh) // 2, (size - nw) // 2
    out[top:top + nh, left:left + nw] = small
    return out, r, left, top


def nms(boxes, scores, iou=0.7):
    """Greedy non-maximum suppression; boxes as x1, y1, x2, y2."""
    order = scores.argsort()[::-1]
    keep = []
    area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    while order.size:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0])
        yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
        xx2 = np.minimum(boxes[i, 2], boxes[order[1:], 2])
        yy2 = np.minimum(boxes[i, 3], boxes[order[1:], 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        order = order[1:][inter / (area[i] + area[order[1:]] - inter + 1e-9) < iou]
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="NCNN model folder (model.ncnn.param and .bin)")
    ap.add_argument("--imgsz", type=int, default=320)
    ap.add_argument("--duration", type=float, default=60)
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--conf", type=float, default=0.5, help="same threshold as the detector")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--tuning", default=None)
    ap.add_argument("--saturation", type=float, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    net = ncnn.Net()
    net.opt.num_threads = args.threads
    net.opt.use_vulkan_compute = False
    net.load_param(os.path.join(args.model, "model.ncnn.param"))
    net.load_model(os.path.join(args.model, "model.ncnn.bin"))
    seg = "out1" in open(os.path.join(args.model, "model.ncnn.param")).read()

    picam2 = Picamera2(tuning=Picamera2.load_tuning_file(args.tuning)) if args.tuning else Picamera2()
    picam2.configure(picam2.create_preview_configuration(
        main={"size": (args.width, args.height), "format": "RGB888"}))
    picam2.start()
    if args.saturation is not None:
        picam2.set_controls({"Saturation": args.saturation})

    print(f"Model {args.model} ({'segment' if seg else 'detect'}), imgsz {args.imgsz}, "
          f"{args.threads} threads, conf {args.conf}, polygons {'yes' if seg and cv2 else 'no'}, {args.duration:.0f} s")
    rows, n = [], 0
    start = time.monotonic()
    try:
        while time.monotonic() - start < args.duration:
            request = picam2.capture_request()
            try:
                frame = request.make_array("main")          # stored B, G, R
                sensor_ns = request.get_metadata().get("SensorTimestamp")
            finally:
                request.release()
            t_got = time.monotonic_ns()

            rgb = np.ascontiguousarray(frame[..., ::-1])
            img, r, left, top = letterbox(rgb, args.imgsz)
            blob = np.ascontiguousarray(img.transpose(2, 0, 1), dtype=np.float32) / 255.0
            t_pre = time.monotonic_ns()

            ex = net.create_extractor()
            ex.input("in0", ncnn.Mat(blob))
            _, out0 = ex.extract("out0")
            pred = np.array(out0)                          # (4 + classes [+ 32], N)
            proto = None
            if seg:
                _, out1 = ex.extract("out1")
                proto = np.array(out1)                     # (32, imgsz/4, imgsz/4)
            t_inf = time.monotonic_ns()

            nc = pred.shape[0] - 4 - (32 if seg else 0)
            scores_all = pred[4:4 + nc]
            cls = scores_all.argmax(0)
            score = scores_all[cls, np.arange(pred.shape[1])]
            m = score > args.conf
            dets, polys = 0, 0
            if m.any():
                cx, cy, w, h = pred[0, m], pred[1, m], pred[2, m], pred[3, m]
                boxes = np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 1)
                keep = []
                for c in np.unique(cls[m]):                # per-class NMS
                    idx = np.where(cls[m] == c)[0]
                    keep += list(idx[nms(boxes[idx], score[m][idx])])
                dets = len(keep)
                if seg and keep:
                    coef = pred[4 + nc:, m][:, keep]       # (32, k)
                    ph, pw = proto.shape[1:]
                    masks = 1 / (1 + np.exp(-(coef.T @ proto.reshape(32, -1)))).reshape(-1, ph, pw)
                    s = ph / args.imgsz
                    for j, k in enumerate(keep):
                        x1, y1, x2, y2 = (boxes[k] * s).astype(int).clip(0, ph)
                        mk = np.zeros((ph, pw), np.uint8)
                        mk[y1:y2, x1:x2] = masks[j, y1:y2, x1:x2] > 0.5
                        if cv2 is not None:
                            cs, _ = cv2.findContours(mk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            polys += len(cs)
            t_post = time.monotonic_ns()

            n += 1
            if n <= args.warmup or sensor_ns is None:
                continue
            rows.append({"queue_ms": (t_got - sensor_ns) / 1e6, "pre_ms": (t_pre - t_got) / 1e6,
                         "inf_ms": (t_inf - t_pre) / 1e6, "post_ms": (t_post - t_inf) / 1e6,
                         "total_ms": (t_post - sensor_ns) / 1e6, "detections": dets, "polygons": polys,
                         "t_s": t_post / 1e9 - start})
    finally:
        picam2.stop()

    fps = (len(rows) - 1) / (rows[-1]["t_s"] - rows[0]["t_s"]) if len(rows) > 1 else float("nan")
    print(f"frames timed: {len(rows)} (after {args.warmup} warm-up), {fps:.1f} fps, CPU {cpu_temp_c():.1f} C")
    for k in ("queue_ms", "pre_ms", "inf_ms", "post_ms", "total_ms"):
        v = [row[k] for row in rows]
        print(f"  {k[:-3]:6s} p50 {statistics.median(v):7.1f}  p95 {pct(v, 0.95):7.1f}  max {max(v):7.1f} ms")
    print(f"  detections per frame: mean {statistics.mean(r['detections'] for r in rows):.2f}"
          + (f", polygons per frame: mean {statistics.mean(r['polygons'] for r in rows):.2f}" if seg else ""))
    if args.out:
        with open(args.out, "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wr.writeheader()
            wr.writerows(rows)


if __name__ == "__main__":
    main()
