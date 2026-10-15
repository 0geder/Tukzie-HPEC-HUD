"""Camera and ToF fusion for SW-7 (Raspberry Pi 4).

Combines the camera hazard detector (hazard_detector.py, GET /detections:
class, confidence, bounding box, bearing and a rough pinhole distance
estimate per object) with the three VL53L0X time-of-flight sensors read by
telemetry_bridge.py (left, ahead, right; one distance each, about a 25
degree cone, reliable to about 1.2 m). The camera says what and in which
direction; the ToF says how far, accurately, but only close by and only in
three fixed directions. Fusion keeps the camera's class and the ToF's
distance where both see the same object.

Rules (geometry in fusion_config.json, all bearings in degrees from the
camera's optical axis, negative = left):

1. Bearing. Each camera detection's bearing is recomputed from its box
   centre with the configured horizontal field of view (pinhole model, as
   in hazard_detector.bearing_deg), so the field of view is calibrated in
   one place.
2. Association. A detection is matched to a ToF sensor when
   - its bearing lies within the sensor's cone, |bearing - sensor bearing|
     <= half_angle + gate,
   - the ToF sample nearest in time to the camera frame is within
     max_dt_ms (200 ms) of it,
   - and that sample is valid (not null) and within the sensor's
     max_range_m.
   If several sensors qualify, the closest ToF reading wins. Each sensor
   is given to at most one detection: candidate pairs are taken in order
   of ToF distance, then of agreement between the camera estimate and the
   ToF reading, so of two objects in one cone the one whose camera
   estimate is nearer the ToF reading gets it.
3. Output per hazard: class, source ("fused", "camera" or "tof"),
   bearing_deg, distance_m (the ToF reading when fused or ToF-only, the
   camera estimate otherwise), band (recomputed from distance_m with the
   detector's band thresholds), confidence (camera; null for ToF-only),
   camera_distance_m and tof_distance_m (both kept for evaluation), sensor
   and tof_dt_ms.
4. ToF-only obstacle ("obstacle", source "tof"): a sensor not given to any
   detection whose last debounce_readings (3) samples are all valid and
   within range, like the detector's three-frame onset. Its bearing is the
   sensor's centre bearing and its distance the latest sample.
5. Camera data older than camera_stale_ms (1 s) is ignored, so with the
   detector stopped only ToF-only obstacles are reported.
6. Approaching (time to contact). For each ToF sensor, a Theil-Sen line
   fit of range against time over the last TOF_TTC_WINDOW_S (0.3 s) of
   valid, in-range samples (null and out-of-range readings left out; at
   least TOF_TTC_MIN_SAMPLES over TOF_TTC_MIN_SPAN_S) gives the closing
   speed; when the range falls consistently (TOF_TTC_MIN_CONSISTENCY of
   the pairwise slopes) at TOF_MIN_CLOSING_MPS or more, TTC = range now /
   closing speed. Every hazard gains:
     "ttc_s": float or null, "closing_mps": float or null (positive =
     nearer), "approaching": bool, "ttc_source": "tof" | "camera" | null,
     "side": "front" | "rear" | null.
   A fused hazard (camera and ToF agree on bearing, so the object is
   inside the ToF's range) takes the ToF's rate when it has one
   ("ttc_source": "tof"), else the camera's; a camera-only hazard (beyond
   ToF range) takes the detector's ttc_s, closing_mps and approaching
   (TTC from box growth, with the detector's hysteresis; closing_mps
   uncalibrated); a ToF-only obstacle takes its sensor's. A ToF-timed
   hazard is approaching when its TTC is under TTC_WARNING_S (4 s), with
   no further hysteresis than the 0.3 s fit. "side" is the bridge's
   --side, else the side the detector reports in /detections. The band is
   still from the distance alone. With the trike moving forward,
   stationary objects ahead also close and are reported as approaching
   (a forward collision warning, intended).

Limitations, stated rather than hidden: a ToF sensor reports the nearest
surface in its cone, which need not be the object the camera saw at that
bearing (no plausibility check against the uncalibrated camera estimate is
made); association is per frame (the detector's track_id is not used
to match); with the default geometry
the side cones (-47.5 to -22.5 and 22.5 to 47.5 degrees) overlap the
camera's 53.5 degree view only at its edges, so most side objects can only
be ToF-only.

Pure functions plus FusionRunner, the thread the telemetry bridge runs. No
images are handled; the fusion log holds numbers only.
"""
import bisect
import copy
import json
import math
import os
import threading
import time
import urllib.request

# Same as hazard_detector.DISTANCE_BANDS (a test checks they agree). The
# detector also sends its own in GET /detections, which then take priority.
DEFAULT_BANDS = [(3.0, "immediate"), (8.0, "warning"), (15.0, "monitoring")]

TOF_NAMES = ("left", "ahead", "right")

# ToF closing rate (rule 6). Window of samples fitted, seconds: about 9
# samples at 30 Hz, 6 at the bridge's 20 Hz read rate.
TOF_TTC_WINDOW_S = 0.3
# Fewest valid samples, and shortest span between first and last, for a fit.
TOF_TTC_MIN_SAMPLES = 5
TOF_TTC_MIN_SPAN_S = 0.15
# Slower than this is not counted as closing: the VL53L0X reading varies
# by about a centimetre on a still target, which over 0.3 s is a few
# centimetres per second of apparent speed.
TOF_MIN_CLOSING_MPS = 0.1
# Share of the non-zero pairwise slopes that must show a falling range.
TOF_TTC_MIN_CONSISTENCY = 0.75
# Same thresholds as hazard_detector.TTC_WARNING_S and TTC_IMMEDIATE_S (a
# test checks): a ToF-timed hazard is "approaching" below the warning one.
TTC_WARNING_S = 4.0
TTC_IMMEDIATE_S = 2.0

DEFAULT_CONFIG = {
    "camera_hfov_deg": 53.5,
    "camera_mirror": False,
    "gate_deg": 5.0,
    "max_dt_ms": 200,
    "camera_stale_ms": 1000,
    "debounce_readings": 3,
    "sensors": {
        "left": {"bearing_deg": -35.0, "half_angle_deg": 12.5, "max_range_m": 1.2},
        "ahead": {"bearing_deg": 0.0, "half_angle_deg": 12.5, "max_range_m": 1.2},
        "right": {"bearing_deg": 35.0, "half_angle_deg": 12.5, "max_range_m": 1.2},
    },
    "calibrated": False,
}


def load_config(path=None):
    """DEFAULT_CONFIG with the values in the JSON file at path laid over it
    (per sensor, per key). Missing file or None: the defaults."""
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            user = json.load(f)
        for k, v in user.items():
            if k == "sensors" and isinstance(v, dict):
                for name, s in v.items():
                    cfg["sensors"].setdefault(name, {}).update(s)
            elif not k.startswith("_"):
                cfg[k] = v
    return cfg


def bearing_from_x(x_centre_norm, hfov_deg, mirror=False):
    """Bearing in degrees of an image column (0 = left edge, 1 = right
    edge), pinhole model; matches hazard_detector.bearing_deg."""
    if mirror:
        x_centre_norm = 1.0 - x_centre_norm
    half = math.tan(math.radians(hfov_deg) / 2.0)
    return math.degrees(math.atan((2.0 * x_centre_norm - 1.0) * half))


def detection_bearing(det, cfg):
    """The detection's bearing with the configured field of view; the
    detector's own bearing_deg if it has no box."""
    bbox = det.get("bbox")
    if bbox and len(bbox) == 4:
        return bearing_from_x((bbox[0] + bbox[2]) / 2.0, cfg["camera_hfov_deg"], cfg.get("camera_mirror", False))
    return det.get("bearing_deg")


def band_for(distance_m, bands=None):
    """Distance band as in hazard_detector.distance_band: the first band
    whose limit is at or above the distance, None beyond the last or with
    no distance."""
    if distance_m is None:
        return None
    for limit_m, band in (bands or DEFAULT_BANDS):
        if distance_m <= limit_m:
            return band
    return None


def in_cone(bearing, sensor_cfg, gate_deg):
    if bearing is None:
        return False
    return abs(bearing - sensor_cfg["bearing_deg"]) <= sensor_cfg["half_angle_deg"] + gate_deg


def valid_in_range(mm, sensor_cfg):
    return mm is not None and 0 < mm <= sensor_cfg["max_range_m"] * 1000.0


def nearest_sample(history, t):
    """The (t_mono, values) entry of history (sorted by time) nearest to t,
    or None if history is empty."""
    if not history:
        return None
    times = [h[0] for h in history]
    i = bisect.bisect_left(times, t)
    best = None
    for j in (i - 1, i):
        if 0 <= j < len(history):
            if best is None or abs(history[j][0] - t) < abs(best[0] - t):
                best = history[j]
    return best


def theil_sen(ts, ys):
    """Robust line fit y = a + b t (same as hazard_detector.theil_sen; kept
    here so the bridge does not import the detector and numpy). Returns
    (a, b, share of the non-zero pairwise slopes that are negative), or
    None with fewer than two distinct times."""
    slopes = []
    n = len(ts)
    for i in range(n):
        for j in range(i + 1, n):
            dt = ts[j] - ts[i]
            if dt > 1e-6:
                slopes.append((ys[j] - ys[i]) / dt)
    if not slopes:
        return None
    slopes.sort()
    m = len(slopes)
    b = slopes[m // 2] if m % 2 else 0.5 * (slopes[m // 2 - 1] + slopes[m // 2])
    rs = sorted(y - b * t for t, y in zip(ts, ys))
    k = len(rs)
    a = rs[k // 2] if k % 2 else 0.5 * (rs[k // 2 - 1] + rs[k // 2])
    nonzero = sum(1 for s in slopes if s != 0)
    neg = sum(1 for s in slopes if s < 0) / nonzero if nonzero else 0.0
    return a, b, neg


def tof_closing(history, name, sensor_cfg):
    """Closing speed and time to contact of one ToF sensor (rule 6).
    Returns (closing_mps or None, ttc_s or None): closing_mps is positive
    when the range is falling, None with too few valid samples in the
    window; ttc_s is set only when the range is falling consistently and
    faster than TOF_MIN_CLOSING_MPS."""
    if not history:
        return None, None
    t_end = history[-1][0]
    pts = [(t, vals.get(name) / 1000.0) for t, vals in history
           if t >= t_end - TOF_TTC_WINDOW_S - 1e-9 and valid_in_range(vals.get(name), sensor_cfg)]
    if len(pts) < TOF_TTC_MIN_SAMPLES or pts[-1][0] - pts[0][0] < TOF_TTC_MIN_SPAN_S:
        return None, None
    ts = [p[0] for p in pts]
    fit = theil_sen(ts, [p[1] for p in pts])
    if fit is None:
        return None, None
    a, b, falling = fit
    closing = -b
    r_now = a + b * ts[-1]
    ttc = None
    if closing >= TOF_MIN_CLOSING_MPS and falling >= TOF_TTC_MIN_CONSISTENCY and r_now > 0:
        ttc = r_now / closing
    return closing, ttc


def tof_debounced(history, name, sensor_cfg, n):
    """True when the last n samples of sensor name are all valid and in range."""
    if n <= 0 or len(history) < n:
        return False
    return all(valid_in_range(vals.get(name), sensor_cfg) for _, vals in history[-n:])


def associate(detections, frame_t, history, cfg):
    """Match detections to ToF sensors (rule 2 of the module docstring).
    detections must already carry "_bearing". Returns {detection index:
    (sensor name, tof mm, dt_ms)}."""
    if frame_t is None or not detections:
        return {}
    sample = nearest_sample(history, frame_t)
    if sample is None:
        return {}
    dt_ms = (sample[0] - frame_t) * 1000.0
    if abs(dt_ms) > cfg["max_dt_ms"]:
        return {}
    vals = sample[1]
    pairs = []
    for i, det in enumerate(detections):
        for name, s in cfg["sensors"].items():
            mm = vals.get(name)
            if not in_cone(det["_bearing"], s, cfg["gate_deg"]) or not valid_in_range(mm, s):
                continue
            cam = det.get("est_distance_m")
            agree = abs(cam - mm / 1000.0) if cam is not None else float("inf")
            pairs.append((mm, agree, i, name))
    pairs.sort(key=lambda p: (p[0], p[1], p[2]))
    used_det, used_sensor, out = set(), set(), {}
    for mm, _, i, name in pairs:
        if i in used_det or name in used_sensor:
            continue
        used_det.add(i)
        used_sensor.add(name)
        out[i] = (name, mm, dt_ms)
    return out


def _r(x, nd):
    return None if x is None else round(x, nd)


def _tof_timing(rate):
    """ttc_s, closing_mps, approaching and ttc_source from a ToF rate."""
    closing, ttc = rate
    if closing is None:
        return {"ttc_s": None, "closing_mps": None, "approaching": False, "ttc_source": None}
    return {"ttc_s": _r(ttc, 2), "closing_mps": _r(closing, 2),
            "approaching": ttc is not None and ttc < TTC_WARNING_S, "ttc_source": "tof"}


def _camera_timing(d):
    """The detector's own ttc_s, closing_mps and approaching (with its
    hysteresis), or nulls from a detector without them."""
    ttc, closing = d.get("ttc_s"), d.get("closing_mps")
    src = "camera" if (ttc is not None or closing is not None or d.get("approaching")) else None
    return {"ttc_s": ttc, "closing_mps": closing, "approaching": bool(d.get("approaching", False)),
            "ttc_source": src}


def fuse(detections, frame_t, history, cfg, bands=None, now=None, side=None):
    """Fused hazard list from one set of camera detections (frame time
    frame_t on the local monotonic clock, or None) and the ToF history
    [(t_mono, {"left": mm or None, ...}), ...] sorted by time. Sorted
    nearest first. side ("front", "rear" or None) is copied to every
    hazard; a camera hazard without it takes the detection's own side."""
    now = time.monotonic() if now is None else now
    if frame_t is None or (now - frame_t) * 1000.0 > cfg["camera_stale_ms"]:
        detections = []
    dets = []
    for d in detections or []:
        d = dict(d)
        d["_bearing"] = detection_bearing(d, cfg)
        dets.append(d)
    matches = associate(dets, frame_t, history, cfg)
    rates = {name: tof_closing(history, name, s) for name, s in cfg["sensors"].items()}
    hazards = []
    for i, d in enumerate(dets):
        cam = d.get("est_distance_m")
        m = matches.get(i)
        tof_m = m[1] / 1000.0 if m else None
        dist = tof_m if m else cam
        # Inside the ToF's range (matched) its closing rate is preferred;
        # with too few ToF samples for a rate, or beyond it, the camera's.
        timing = _tof_timing(rates[m[0]]) if m else None
        if timing is None or timing["ttc_source"] is None:
            timing = _camera_timing(d)
        hazards.append({
            "class": d.get("class"),
            "source": "fused" if m else "camera",
            "sensor": m[0] if m else None,
            "bearing_deg": _r(d["_bearing"], 1),
            "distance_m": _r(dist, 3),
            "band": band_for(dist, bands),
            "confidence": _r(d.get("confidence"), 3),
            "camera_distance_m": _r(cam, 3),
            "tof_distance_m": _r(tof_m, 3),
            "tof_dt_ms": _r(m[2], 0) if m else None,
            "side": side or d.get("side"),
            **timing,
        })
    used = {m[0] for m in matches.values()}
    n = int(cfg.get("debounce_readings", 3))
    latest = history[-1] if history else None
    for name, s in cfg["sensors"].items():
        if name in used or latest is None or not tof_debounced(history, name, s, n):
            continue
        tof_m = latest[1][name] / 1000.0
        hazards.append({
            "class": "obstacle",
            "source": "tof",
            "sensor": name,
            "bearing_deg": _r(float(s["bearing_deg"]), 1),
            "distance_m": _r(tof_m, 3),
            "band": band_for(tof_m, bands),
            "confidence": None,
            "camera_distance_m": None,
            "tof_distance_m": _r(tof_m, 3),
            "tof_dt_ms": None,
            "side": side,
            **_tof_timing(rates[name]),
        })
    hazards.sort(key=lambda h: (h["distance_m"] is None, h["distance_m"] or 0.0))
    return hazards


def fetch_detections(url, timeout=0.5):
    """GET /detections. Returns (response dict, frame time on the local
    monotonic clock or None). The frame's age is taken from the detector's
    own clock (t_mono - frame_t_mono), so the two processes need not share
    a clock; the error is the HTTP round trip, a few ms on localhost."""
    with urllib.request.urlopen(url, timeout=timeout) as r:
        d = json.loads(r.read())
    recv = time.monotonic()
    frame_t = None
    if d.get("frame_t_mono") is not None and d.get("t_mono") is not None:
        frame_t = recv - max(0.0, float(d["t_mono"]) - float(d["frame_t_mono"]))
    return d, frame_t


class FusionRunner(threading.Thread):
    """Polls the detector's /detections at 5 Hz, fuses with the ToF history
    and publishes the block for /telemetry and /hazards.

    mode "on": always fuses (ToF-only when the detector is absent).
    mode "auto": idle until the detector first answers, polling every 2 s;
    from then on as "on". Until then publish() is never called, so the
    /telemetry JSON is unchanged on a Pi without the detector."""

    def __init__(self, stop, tof_history_fn, publish_fn, url="http://127.0.0.1:8080/detections",
                 config_path=None, log_path=None, mode="auto", period_s=0.2, side=None):
        super().__init__(daemon=True)
        self.stop = stop
        self.tof_history_fn = tof_history_fn
        self.publish_fn = publish_fn
        self.url = url
        self.config_path = config_path
        self.config_name = os.path.basename(config_path) if config_path else None
        self.cfg = load_config(config_path)
        self.log_path = os.path.expanduser(log_path) if log_path else None
        self.mode = mode
        self.period_s = period_s
        # "front" or "rear" from the bridge's --side; None: the side the
        # detector reports in /detections (the last one seen), else null.
        self.side = side
        self.detector_side = None
        self.active = mode == "on"
        self.updates = 0
        self.camera_errors = 0
        self.last_error = None
        self._log = None

    def step(self, now=None):
        """One poll and fusion. Returns the published block, or None while
        idle in auto mode."""
        try:
            resp, frame_t = fetch_detections(self.url)
            self.active = True
        except Exception as e:   # detector stopped, starting, or no --preview
            self.camera_errors += 1
            self.last_error = "%s: %s" % (type(e).__name__, e)
            resp, frame_t = None, None
            if not self.active:
                return None
        now = time.monotonic() if now is None else now
        history = self.tof_history_fn()
        bands = None
        if resp and resp.get("bands"):
            bands = [(float(l), b) for l, b in resp["bands"]]
        if resp and resp.get("side"):
            self.detector_side = resp["side"]
        hazards = fuse(resp.get("detections", []) if resp else [], frame_t, history, self.cfg, bands, now,
                       side=self.side or self.detector_side)
        camera_age_ms = None if frame_t is None else int(round((now - frame_t) * 1000))
        block = {
            "hazards": hazards,
            "t_mono": now,
            "camera_fps": resp.get("fps") if resp else None,
            "camera_age_ms": camera_age_ms,
            "config": self.config_name,
        }
        self.updates += 1
        self.publish_fn(block)
        self._write_log(block, history)
        return block

    def _write_log(self, block, history):
        if not self.log_path:
            return
        latest = history[-1][1] if history else {}
        wall = time.time()
        rec = {
            "t": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(wall)) + ".%03d" % int((wall % 1) * 1000),
            "t_mono": round(block["t_mono"], 3),
            "camera_fps": block["camera_fps"],
            "camera_age_ms": block["camera_age_ms"],
            "tof_mm": {n: latest.get(n) for n in TOF_NAMES},
            "hazards": block["hazards"],
        }
        try:
            if self._log is None:
                self._log = open(self.log_path, "a", buffering=1, encoding="utf-8")
            self._log.write(json.dumps(rec) + "\n")
        except OSError as e:
            self.last_error = "fusion log: %s" % e

    def run(self):
        try:
            while not self.stop.is_set():
                t0 = time.monotonic()
                self.step()
                wait = self.period_s if self.active else 2.0
                self.stop.wait(max(0.0, wait - (time.monotonic() - t0)))
        finally:
            if self._log is not None:
                self._log.close()
