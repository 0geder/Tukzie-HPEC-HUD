#!/usr/bin/env python3
"""Camera-to-IMU time alignment (R6): an LED on the node's sync line, seen by the camera, against the Pi's sync edges.

The ESP32 drives a 500 ms pulse on its sync pin, wired to the Pi's GPIO17 (sync_logger.py / sw7-*-sync services log
every edge with the kernel's monotonic timestamp). An LED with a series resistor on the same pin, placed in the
camera's view, makes the pulse visible. This script captures frames with Picamera2 and their SensorTimestamp (the same
monotonic clock), finds the LED's pixels by their variance, labels each frame on or off, and pairs every rising edge
in the sync CSV with the first frame in which the LED is lit.

For one edge, the delay d = t_frame - t_edge lies between the true offset and the offset plus one frame period, so
over many edges at random phase: offset >= min(d) - (read-out skew) and offset <= min(d); the spread of d is about one
frame period if the clocks agree. The result is the bound [min(d) - T, min(d)] with T the frame period, and the median.

Stop the detector first (it holds the camera): sudo systemctl stop pi5-hazard-detector (Pi 5) or hazard-detector (Pi 4).
Run:  python3 led_offset.py --sync /path/to/sync_edges.csv --seconds 60 --fps 50 --out led_offset_<date>.json
(the sync service's live CSV can be passed; only edges inside the capture window are used).
"""
import argparse, csv, json, statistics, time

import numpy as np


def capture(seconds, fps, size=(640, 480)):
    from picamera2 import Picamera2
    cam = Picamera2()
    cfg = cam.create_video_configuration(main={"size": size, "format": "YUV420"},
                                         controls={"FrameDurationLimits": (int(1e6 / fps), int(1e6 / fps)),
                                                   "AeEnable": False, "ExposureTime": 2000, "AnalogueGain": 2.0})
    cam.configure(cfg)
    cam.start()
    frames, ts = [], []
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        req = cam.capture_request()
        y = req.make_array("main")[: size[1], : size[0]]          # luma plane
        frames.append(y[::4, ::4].astype(np.float32))              # 160 x 120 is enough to find the LED
        ts.append(req.get_metadata()["SensorTimestamp"])
        req.release()
    cam.stop()
    return np.stack(frames), np.array(ts, dtype=np.int64)


def led_state(frames):
    var = frames.var(axis=0)
    thr = np.percentile(var, 99.9)
    roi = var >= thr                                               # the few pixels that blink
    level = frames[:, roi].mean(axis=1)
    lo, hi = np.percentile(level, 10), np.percentile(level, 90)
    return level > (lo + hi) / 2, float(hi - lo), int(roi.sum())


def rising_edges(path, t0, t1):
    out = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r.get("edge") == "rise":
                t = int(r["t_mono_ns"])
                if t0 <= t <= t1:
                    out.append(t)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sync", required=True)
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--fps", type=float, default=50)
    ap.add_argument("--out", default="led_offset.json")
    a = ap.parse_args()
    frames, ts = capture(a.seconds, a.fps)
    on, contrast, npx = led_state(frames)
    period = float(np.median(np.diff(ts))) / 1e6
    edges = rising_edges(a.sync, int(ts[0]), int(ts[-1] - 2e9))
    delays = []
    for e in edges:
        k = int(np.searchsorted(ts, e))
        while k < len(ts) and not on[k]:
            k += 1
        if k < len(ts) and (ts[k] - e) / 1e6 < 300:
            delays.append((ts[k] - e) / 1e6)
    res = {"frames": int(len(ts)), "frame_period_ms": round(period, 3), "led_pixels": npx, "led_contrast": round(contrast, 1),
           "edges_used": len(delays)}
    if delays:
        res.update({"delay_ms_min": round(min(delays), 3), "delay_ms_median": round(statistics.median(delays), 3),
                    "delay_ms_max": round(max(delays), 3),
                    "offset_bound_ms": [round(min(delays) - period, 3), round(min(delays), 3)],
                    "spread_ms": round(max(delays) - min(delays), 3)})
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
