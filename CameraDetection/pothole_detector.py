"""
Experimental pothole path for hazard_detector.py (SW-7, Pi 4).

Runs the run-2 YOLO11n pothole model (NCNN export, one class, trained on
road-band tiles of the Stellenbosch dataset, see
training/runs/run2_sa_band_tiles_640/README.md) on the same road band and
tiling it was trained on:

  - each frame is cropped to 42 to 68 % of its height (BAND),
  - the band is cut into three overlapping tiles, each 1280/3680 of the
    frame width (TILE_FRAC), at the left edge, the centre and the right
    edge, exactly as cell 2g of the training notebook did on 3680 x 2760
    frames. Both cameras are 4:3, so the fractions carry over.

Each tile is letterboxed to the model's square input (grey 114 padding, as
Ultralytics does), the raw output (4 box values + 1 score per anchor) is
decoded, boxes are mapped back to full-frame pixels and merged across the
overlapping tiles with non-maximum suppression.

The inference runs in a separate, low-priority process (PotholeWorker), so
it never blocks the main detector loop and cannot hold the main process's
interpreter lock. It still competes for the Pi 4's cache and memory
bandwidth: three 320-pixel tiles take about 0.55 to 0.75 s on one core next
to the main detector, and only 0.25 runs per second kept the main detector
within 10 % of its speed (measured 11 Oct 2026), so the path is off by default. Only the band of the latest frame is passed to it, in
memory over a pipe; nothing is written to disk.

Honest confidence (see RunDebouncer): a threshold of 0.5, and an alert only
when potholes were found in at least 2 of the last 3 runs. Every pothole
record and alert carries "experimental": true. The model's 0.714 mAP@50 is
a validation-split, per-tile figure on another camera; it has not been
validated on this vehicle.

No distance estimate is made for a pothole (there is no known real width),
so its band and est_distance_m are None. The bearing uses the same pinhole
model as hazard_detector.bearing_deg.
"""
import math
import os
import time

import numpy as np

BAND = (0.42, 0.68)          # fraction of the frame height, cell 2g
TILE_FRAC = 1280.0 / 3680.0  # tile width as a fraction of the frame width, cell 2g
N_TILES = 3
CONF_THRESHOLD = 0.5         # conservative: the main detector's threshold, not YOLO's 0.25 default
NMS_IOU = 0.5
DEBOUNCE_K, DEBOUNCE_N = 2, 3  # alert when seen in 2 of the last 3 runs
CLEAR_AFTER_EMPTY_RUNS = 3
MAX_RATE_HZ = 0.25  # see POTHOLES_DEFAULT in hazard_detector.py for the measurements
MODEL_NAME = "yolo11n_sa_band_tiles (run 2)"


def band_rows(frame_h, band=BAND):
    """First and one-past-last row of the road band, as int() in cell 2g."""
    return int(band[0] * frame_h), int(band[1] * frame_h)


def band_tiles(frame_w, frame_h, band=BAND, tile_frac=TILE_FRAC, n=N_TILES):
    """Tile rectangles (x0, y0, x1, y1) in full-frame pixels: n tiles of
    width round(tile_frac * frame_w) spread from the left edge to the right
    edge (left, centre, right for n = 3), all spanning the band rows."""
    y0, y1 = band_rows(frame_h, band)
    tw = min(frame_w, int(round(tile_frac * frame_w)))
    if n == 1:
        xs = [(frame_w - tw) // 2]
    else:  # n = 3 gives [0, (W - TW) // 2, W - TW], cell 2g's xs
        xs = [k * (frame_w - tw) // (n - 1) for k in range(n)]
    return [(x, y0, x + tw, y1) for x in xs]


def letterbox_params(w, h, size):
    """Scale and padding Ultralytics uses to fit w x h into size x size."""
    r = min(size / h, size / w)
    nw, nh = int(round(w * r)), int(round(h * r))
    left, top = (size - nw) // 2, (size - nh) // 2
    return r, nw, nh, left, top


def letterbox(rgb, size):
    """rgb (h, w, 3) uint8 -> (size, size, 3) uint8, r, left, top."""
    from PIL import Image
    h, w = rgb.shape[:2]
    r, nw, nh, left, top = letterbox_params(w, h, size)
    small = np.asarray(Image.fromarray(rgb).resize((nw, nh), Image.BILINEAR))
    out = np.full((size, size, 3), 114, np.uint8)
    out[top:top + nh, left:left + nw] = small
    return out, r, left, top


def nms(boxes, scores, iou=NMS_IOU):
    """Greedy non-maximum suppression; boxes (k, 4) as x1, y1, x2, y2.
    Returns the kept indices, highest score first."""
    boxes = np.asarray(boxes, dtype=np.float64).reshape(-1, 4)
    scores = np.asarray(scores, dtype=np.float64).reshape(-1)
    order = scores.argsort()[::-1]
    keep = []
    area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    while order.size:
        i = order[0]
        keep.append(int(i))
        rest = order[1:]
        xx1 = np.maximum(boxes[i, 0], boxes[rest, 0])
        yy1 = np.maximum(boxes[i, 1], boxes[rest, 1])
        xx2 = np.minimum(boxes[i, 2], boxes[rest, 2])
        yy2 = np.minimum(boxes[i, 3], boxes[rest, 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        order = rest[inter / (area[i] + area[rest] - inter + 1e-9) < iou]
    return keep


def decode_tile(pred, tile, r, left, top, conf=CONF_THRESHOLD):
    """Raw YOLO output for one tile -> boxes in full-frame pixels.

    pred: (4 + classes, anchors) as the NCNN export gives it: cx, cy, w, h
    in letterboxed-input pixels, then per-class scores (already sigmoid).
    tile: (x0, y0, x1, y1) of the tile in the frame. r, left, top: the
    letterbox scale and padding. Returns (boxes (k, 4) x1 y1 x2 y2 clipped
    to the tile, scores (k,))."""
    pred = np.asarray(pred, dtype=np.float32)
    score = pred[4:].max(0) if pred.shape[0] > 5 else pred[4]
    m = score > conf
    if not m.any():
        return np.zeros((0, 4)), np.zeros((0,))
    cx, cy, w, h = pred[0, m], pred[1, m], pred[2, m], pred[3, m]
    tx0, ty0, tx1, ty1 = tile
    x1 = (cx - w / 2 - left) / r + tx0
    y1 = (cy - h / 2 - top) / r + ty0
    x2 = (cx + w / 2 - left) / r + tx0
    y2 = (cy + h / 2 - top) / r + ty0
    boxes = np.stack([np.clip(x1, tx0, tx1), np.clip(y1, ty0, ty1),
                      np.clip(x2, tx0, tx1), np.clip(y2, ty0, ty1)], 1)
    ok = (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
    return boxes[ok], score[m][ok]


def merge_tiles(per_tile, iou=NMS_IOU):
    """per_tile: list of (boxes, scores) per tile, full-frame pixels. A
    pothole in the overlap of two tiles is found twice; NMS across all
    tiles keeps one. Returns a list of (x1, y1, x2, y2, score, tile_index)."""
    rows = [(b, s, k) for k, (bs, ss) in enumerate(per_tile) for b, s in zip(bs, ss)]
    if not rows:
        return []
    keep = nms([r[0] for r in rows], [r[1] for r in rows], iou)
    return [(*map(float, rows[i][0]), float(rows[i][1]), rows[i][2]) for i in keep]


def bearing_deg(x_centre_norm, hfov_deg):
    half = math.tan(math.radians(hfov_deg) / 2.0)
    return math.degrees(math.atan((2.0 * x_centre_norm - 1.0) * half))


def pothole_record(det, frame_w, frame_h, hfov_deg, model_name=MODEL_NAME):
    """One entry of road_hazards in GET /detections. Same keys as a
    detection_record (class, confidence, bbox, bearing_deg, est_distance_m,
    band) plus tile, model and experimental."""
    x1, y1, x2, y2, score, tile = det
    bx = [min(1.0, max(0.0, v)) for v in (x1 / frame_w, y1 / frame_h, x2 / frame_w, y2 / frame_h)]
    return {
        "class": "pothole",
        "confidence": round(score, 3),
        "bbox": [round(v, 4) for v in bx],
        "bearing_deg": round(bearing_deg((bx[0] + bx[2]) / 2.0, hfov_deg), 2),
        "est_distance_m": None,
        "band": None,
        "tile": ["left", "centre", "right"][tile] if tile < 3 else tile,
        "model": model_name,
        "experimental": True,
    }


class RunDebouncer:
    """Run-level debounce for the pothole alert: active once potholes were
    found in at least k of the last n runs; cleared after clear_after runs
    in a row without one. Class-level, like the main detector's debounce:
    it says "potholes keep being seen", not "this pothole"."""

    def __init__(self, k=DEBOUNCE_K, n=DEBOUNCE_N, clear_after=CLEAR_AFTER_EMPTY_RUNS):
        if not 1 <= k <= n:
            raise ValueError("need 1 <= k <= n")
        self.k, self.n, self.clear_after = k, n, clear_after
        self.history = []
        self.empty_streak = 0
        self.active = False

    def update(self, seen):
        """Feed one run's result. Returns "active" on onset, "cleared" on
        clear, else None."""
        self.history = (self.history + [bool(seen)])[-self.n:]
        self.empty_streak = 0 if seen else self.empty_streak + 1
        if not self.active and sum(self.history) >= self.k:
            self.active = True
            return "active"
        if self.active and self.empty_streak >= self.clear_after:
            self.active = False
            self.history = []
            return "cleared"
        return None


def read_imgsz(model_dir, default=320):
    """Input size from the export's metadata.yaml (imgsz: [n, n]), without a yaml dependency."""
    try:
        lines = open(os.path.join(model_dir, "metadata.yaml")).read().splitlines()
    except OSError:
        return default
    for i, line in enumerate(lines):
        if line.startswith("imgsz:"):
            rest = line.split(":", 1)[1].strip()
            if rest:
                return int(rest.strip("[]").split(",")[0])
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("-"):
                return int(lines[i + 1].strip().lstrip("-").strip())
    return default


class PotholeModel:
    """The NCNN model plus tiling, decode and merge. Used in-process by the
    tests and the worker process."""

    def __init__(self, model_dir, threads=1, imgsz=None):
        import ncnn
        self.ncnn = ncnn
        self.imgsz = imgsz or read_imgsz(model_dir)
        self.net = ncnn.Net()
        self.net.opt.num_threads = threads
        self.net.opt.use_vulkan_compute = False
        self.net.load_param(os.path.join(model_dir, "model.ncnn.param"))
        self.net.load_model(os.path.join(model_dir, "model.ncnn.bin"))

    def infer(self, rgb_tile):
        img, r, left, top = letterbox(rgb_tile, self.imgsz)
        blob = np.ascontiguousarray(img.transpose(2, 0, 1), dtype=np.float32) / 255.0
        ex = self.net.create_extractor()
        ex.input("in0", self.ncnn.Mat(blob))
        _, out0 = ex.extract("out0")
        return np.array(out0), r, left, top

    def detect_band(self, band_rgb, frame_w, frame_h, band=BAND, conf=CONF_THRESHOLD):
        """band_rgb: the frame's band rows only (y0:y1, all columns).
        Returns merged detections in full-frame pixels."""
        tiles = band_tiles(frame_w, frame_h, band)
        y0 = tiles[0][1]
        per_tile = []
        for t in tiles:
            crop = np.ascontiguousarray(band_rgb[:, t[0]:t[2]])
            pred, r, left, top = self.infer(crop)
            per_tile.append(decode_tile(pred, (t[0], y0, t[2], t[3]), r, left, top, conf))
        return merge_tiles(per_tile)

    def detect_frame(self, rgb, band=BAND, conf=CONF_THRESHOLD):
        h, w = rgb.shape[:2]
        y0, y1 = band_rows(h, band)
        return self.detect_band(rgb[y0:y1], w, h, band, conf)


def _worker_main(conn, model_dir, threads, imgsz, nice, cpus=None):
    try:
        os.nice(nice)
    except (AttributeError, OSError):
        pass
    if cpus:
        try:
            os.sched_setaffinity(0, cpus)   # Linux only; this process and the threads it starts
        except (AttributeError, OSError):
            pass
    try:
        model = PotholeModel(model_dir, threads, imgsz)
        conn.send({"ready": True, "imgsz": model.imgsz})
    except Exception as e:  # report and stop; the detector carries on without potholes
        conn.send({"ready": False, "error": repr(e)})
        return
    while True:
        try:
            msg = conn.recv()
        except (EOFError, OSError):
            return
        if msg is None:
            return
        meta, data = msg
        band_rgb = np.frombuffer(data, np.uint8).reshape(meta["shape"])
        t0 = time.monotonic()
        dets = model.detect_band(band_rgb, meta["frame_w"], meta["frame_h"], meta["band"], meta["conf"])
        conn.send({"dets": dets, "infer_ms": (time.monotonic() - t0) * 1000.0,
                   "frame_t": meta["frame_t"], "seq": meta["seq"]})


class PotholeWorker:
    """Runs PotholeModel in a separate process at low priority. The main
    loop calls poll() and maybe_submit() once per frame; neither waits for
    inference. A new band is only sent when the worker is idle and at
    least 1 / max_rate_hz has passed since the last one."""

    def __init__(self, model_dir, threads=1, imgsz=None, nice=19, max_rate_hz=MAX_RATE_HZ,
                 band=BAND, conf=CONF_THRESHOLD, ready_timeout_s=60.0, cpus=None):
        import multiprocessing as mp
        ctx = mp.get_context("spawn")   # clean child: no copy of the camera or HTTP threads
        self.conn, child = ctx.Pipe()
        self.proc = ctx.Process(target=_worker_main, args=(child, model_dir, threads, imgsz, nice, cpus),
                                daemon=True, name="pothole-worker")
        self.proc.start()
        child.close()
        if not self.conn.poll(ready_timeout_s):
            self.close()
            raise RuntimeError("pothole worker did not start")
        hello = self.conn.recv()
        if not hello.get("ready"):
            self.close()
            raise RuntimeError("pothole model failed to load: %s" % hello.get("error"))
        self.imgsz = hello["imgsz"]
        self.band, self.conf = band, conf
        self.min_period = 1.0 / max_rate_hz if max_rate_hz > 0 else 0.0
        self.busy = False
        self.last_submit = 0.0
        self.seq = 0
        self.runs = 0
        self.run_times = []  # monotonic time of each finished run, for the rate

    def maybe_submit(self, rgb, frame_t):
        now = time.monotonic()
        if self.busy or now - self.last_submit < self.min_period:
            return False
        h, w = rgb.shape[:2]
        y0, y1 = band_rows(h, self.band)
        band = np.ascontiguousarray(rgb[y0:y1])
        self.seq += 1
        self.conn.send(({"shape": band.shape, "frame_w": w, "frame_h": h, "band": self.band,
                         "conf": self.conf, "frame_t": frame_t, "seq": self.seq}, band.tobytes()))
        self.busy = True
        self.last_submit = now
        return True

    def poll(self):
        """The latest finished run's result dict, or None."""
        if not self.busy or not self.conn.poll():
            return None
        try:
            res = self.conn.recv()
        except (EOFError, OSError):
            return None
        self.busy = False
        self.runs += 1
        now = time.monotonic()
        self.run_times = [t for t in self.run_times if now - t < 10.0] + [now]
        return res

    def rate_hz(self):
        t = self.run_times
        return (len(t) - 1) / (t[-1] - t[0]) if len(t) > 1 and t[-1] > t[0] else 0.0

    def close(self):
        try:
            self.conn.send(None)
        except (OSError, ValueError):
            pass
        self.proc.join(timeout=2)
        if self.proc.is_alive():
            self.proc.terminate()
