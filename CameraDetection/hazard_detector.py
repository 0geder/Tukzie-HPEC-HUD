#!/usr/bin/env python3
"""
SW-7 hazard/obstacle detector for the Pi 5 (front) and Pi 4 (rear) cameras.

Runs under ethics approval EBE/03305/2026 (approved with conditions,
23 Sep 2026 - 22 Sep 2027, EBE Faculty Research Ethics Committee). The
conditions attached to that approval are enforced directly in this file,
not left as a report-only statement:

  - Camera data is processed for object detection and distance-alert
    research only (see HAZARD_CLASSES below - restricted to the category
    list proposed in the ethics application, nothing broader).
  - Raw camera frames are never written to disk: capture_array() output
    exists only in memory and is replaced by the next frame. With the
    optional --preview on, the latest annotated frame is also held in
    memory (as one JPEG) until the next replaces it. Only the fields
    listed in ALERT_LOG_FIELDS are ever persisted.
  - No facial recognition, no number-plate recognition, no per-instance
    identification of any person or vehicle is performed anywhere in this
    file - COCO class labels only ("person", "car", etc.), never who or
    which one.
  - Inference is entirely local to this Pi. No frame or result is sent
    to any external or cloud service. When the optional --preview is
    enabled, annotated frames are served over plain HTTP: to this Pi
    only by default, or, with --preview-host 0.0.0.0, to devices on the
    same local network. They are never stored.
  - The system has no actuator output of any kind: it prints/logs only.
    It must not, and does not, control steering, braking, acceleration,
    or any other vehicle function.

Scope, stated honestly beyond the ethics conditions: this runs a
pretrained, COCO-trained SSD-MobileNet-v1 object detector (quantized
TFLite, no NPU required) on live camera frames, and reports which of a
small set of road-relevant classes are present, with a *rough* distance
estimate from a known-object-width heuristic. It does NOT do lane-level
blind-spot geometry and does NOT constitute an autonomous-driving
perception stack - it is a hazard-presence-and-rough-range indicator,
sized to what a Pi 4 with no hardware accelerator can actually sustain in
real time. The distance alerts are class-level (see
ALERT_PERSISTENCE_FRAMES); the approaching alerts below are per track.

Distance estimate uses the pinhole-camera relationship:
    distance_m = (real_object_width_m * focal_length_px) / bbox_width_px
This is an estimate, not a measurement: it assumes the object is roughly
front-on to the camera and uses one average real-world width per class
(a car is not always 1.8m wide from every angle). The raw metre value is
used only internally to select a distance BAND (see DISTANCE_BANDS) -
the ethics application specifies logging an "approximate distance band",
not a precise continuous figure, so the raw estimate itself is never
persisted.

Detections for the camera and ToF fusion (GET /detections, served with
--preview on the same port as /alerts): the latest frame's detections of
the HAZARD_CLASSES above CONFIDENCE_THRESHOLD, each with its class,
confidence, normalised bounding box, bearing (from the box centre and the
horizontal field of view, --hfov-deg) and the raw distance estimate, plus
the frame's monotonic timestamp and the frame rate. No image data. The
telemetry bridge on the same Pi reads it (sensor_fusion.py); the raw
estimate is served, never written to disk by this script.

Approaching objects and time to contact (TTC). The same code runs on the
Pi 5 at the front (about 19 fps) and the Pi 4 at the rear (about 14.7
fps); --side front|rear (or "side" in detector_options.json, default
front) names which, and is echoed in /alerts and /detections.
  - Tracking: a small IoU tracker (ApproachMonitor) gives each detection
    of a HAZARD_CLASSES class a track_id that persists across frames and
    survives up to TRACK_MAX_MISSED (2) missed frames. The id is a counter
    from 1 at start-up; it links boxes of one object over a second or so
    and identifies nobody (no face, plate or appearance is used, only box
    overlap), so the "no per-instance identification" condition holds.
  - TTC from scale expansion (Lee's tau): over the last TTC_WINDOW_S
    (0.6 s) of the track, a Theil-Sen fit of 1/box_width against the
    frames' sensor timestamps gives TTC = w / (dw/dt). Valid only with at
    least TTC_MIN_FRAMES frames over TTC_MIN_SPAN_S, consistent growth
    (TTC_MIN_CONSISTENCY of pairwise slopes), at least TTC_MIN_REL_GROWTH
    growth, no box clipped by the left or right image edge, and (when not
    clipped top or bottom) the height giving a TTC within a factor 2. It
    needs no focal length, so it is independent of the uncalibrated
    --focal-length-px. closing_mps, the slope of the pinhole distance
    estimate, is NOT: it scales with --focal-length-px and the class
    width, and is reported for evaluation only.
  - Approaching alert: TTC under TTC_WARNING_S (4 s) is "warning", under
    TTC_IMMEDIATE_S (2 s) "immediate", taken after 3 consecutive frames,
    held until TTC rises above 1.25 times the threshold (or is invalid)
    for 5 frames. The class-level distance alerts are unchanged; in
    /alerts an approaching track raises the band of its class's entry when
    more urgent, and an approaching track with no distance alert (a fast
    car beyond 15 m, say) gets its own entry.
  - Ego motion: with the trike moving forward, stationary objects ahead
    (parked cars, a person standing) grow in the front camera and are
    reported as approaching. That is intended: it is a forward collision
    warning, the TTC being to contact at the current closing speed. At
    the rear, the same motion makes stationary objects shrink, so only
    objects closing faster than the trike moves (an overtaking or
    tailgating car) are reported.

Schema (additive; earlier fields unchanged). Every entry of GET /alerts
"active" and of GET /detections "detections" gains:
    "side": "front" | "rear",
    "track_id": int (null only on an /alerts entry whose track was never
                     seen, which the code does not produce),
    "approaching": bool (the hysteresis state above),
    "ttc_s": float or null (this frame's TTC, null when not valid),
    "closing_mps": float or null (positive = nearer; uncalibrated).
Both responses also carry a top-level "side". An /alerts entry with
"approaching": true has distance_band raised to the approaching band
when that is more urgent.

Alert log. Approaching alerts go to the same JSONL log (--log-path) with
the five fields above plus "approaching": true, "track_id", "ttc_s"
(0.1 s, null on clear) and "side" (APPROACH_LOG_FIELDS); distance-alert
lines are unchanged. These four extra fields and the approaching alert
itself are a change to the logged fields and the alert method, which the
ethics conditions (README) ask to be reviewed before field use.

Experimental pothole path, off by default (pothole_detector.py, --potholes on|off or
"potholes" in detector_options.json): the run-2 YOLO11n pothole model runs
in a separate low-priority process on the road band of the latest frame
(42 to 68 % of the height, three tiles, as it was trained), at 0.25 Hz by default,
without the main loop ever waiting for it. Its results are published as
new keys only: "road_hazards" and "road_hazards_meta" in GET /detections
and "road_hazards" in GET /alerts, each marked "experimental": true; the
existing "detections" and "active" lists never contain a pothole, so the
fusion, the bridge and the dashboard are unaffected. A pothole alert needs
potholes in 2 of the last 3 runs and is logged with the same five fields
(class "pothole", distance band null). The band is passed to the worker
in memory over a pipe and never written to disk.

--test-image PATH replaces the camera with one saved picture, repeated at
about 15 fps, for checking the whole pipeline (including the endpoints)
without the camera; it can run as a second instance on another
--preview-port while the service holds the camera.
"""
import argparse
import json
import os
import time
import numpy as np

# COCO class widths, metres - rough, front-on average estimates, not
# per-instance measurements. Classes outside this map are still detected
# and reported, just without a distance estimate.
KNOWN_WIDTHS_M = {
    # Person: 0.60 m (26 Oct 2026, the student's choice). The fit on the front camera (BenchTest/logs/focal_cal.csv,
    # standing person at 2.2 and 3.2 m) gave 0.80 m for one person and stance; 0.5 m read 38 % short. With 0.60 a
    # person in that stance reads about 25 % short; slimmer people and poses read closer to true.
    "person": 0.60,
    "bicycle": 0.6,
    "car": 1.8,
    "motorcycle": 0.8,
    "bus": 2.5,
    "truck": 2.5,
    "dog": 0.3,
}

# Restricted to the category list proposed in the ethics application
# (the approval's condition is "only approved object categories"):
# motor vehicles, motorcycles, bicycles, pedestrians, animals, road
# obstacles. Earlier versions of this script also reported "traffic
# light", "stop sign", "fire hydrant" - none of those are in the approved
# list (they are infrastructure, not the approved object categories), so
# they have been removed rather than left in on the assumption they'd be
# covered by "road obstacles". If traffic-infrastructure detection is
# wanted later, that is a new category requiring its own ethics review
# under the change-control condition, not an assumption made in code.
HAZARD_CLASSES = set(KNOWN_WIDTHS_M.keys())

CONFIDENCE_THRESHOLD = 0.5

# Distance bands, metres - matches the zones proposed in the ethics
# application (immediate / warning / monitoring). The application specifies
# logging a band, not a precise distance, so this is the coarsest
# representation that still supports a useful alert.
DISTANCE_BANDS = [
    (3.0, "immediate"),
    (8.0, "warning"),
    (15.0, "monitoring"),
]

# An object class must be detected within any reportable band for this
# many consecutive frames before it is logged as a reportable alert,
# rather than every single-frame flicker. This is a
# class-level debounce, not per-instance tracking: it cannot distinguish
# two different cars both briefly visible from one car persisting, since
# the distance alert does not use the object tracks (only the approaching
# alert does; the distance alert was deliberately left as it was). That limitation is
# stated here rather than implied by the counter's existence.
ALERT_PERSISTENCE_FRAMES = 3

# Once active, an alert only clears after the class has been missing for
# this many consecutive frames (about 0.7 s at the measured 7 fps). With
# a single-frame clear, detections hovering near the confidence threshold
# made one person standing still produce 16 separate alerts in 47 s.
CLEAR_AFTER_MISSED_FRAMES = 5

# Nearer bands rank lower. Used to pick the nearest detection of a class
# in a frame, and to re-log an active alert when the object gets nearer.
BAND_RANK = {"immediate": 0, "warning": 1, "monitoring": 2}

# The only fields this script ever persists to the alert log, matching
# the fields proposed in the ethics application.
ALERT_LOG_FIELDS = ("class", "distance_band", "confidence", "timestamp", "alert_status")

# Horizontal field of view of the OV5647 (Camera Module v1) lens, degrees:
# 53.50 +/- 0.13 in the Raspberry Pi camera hardware documentation, for the
# full sensor width. The 640x480 mode is binned from close to the full
# width, so the same figure is used. To be checked against the ToF
# bearing calibration (TEST_PROCEDURES.md C9).
DEFAULT_HFOV_DEG = 53.5


def bearing_deg(x_centre_norm, hfov_deg=DEFAULT_HFOV_DEG):
    """Horizontal bearing of an image point, degrees, 0 = optical axis,
    negative = left, positive = right. Pinhole model: the image half-width
    corresponds to tan(hfov / 2), so the bearing is not linear in x.
    x_centre_norm is 0 at the left edge of the frame and 1 at the right."""
    import math
    half = math.tan(math.radians(hfov_deg) / 2.0)
    return math.degrees(math.atan((2.0 * x_centre_norm - 1.0) * half))


def detection_record(class_name, confidence, box_norm, frame_w, focal_length_px, hfov_deg):
    """One entry of GET /detections. box_norm is the model's (ymin, xmin,
    ymax, xmax) in 0..1; the record uses (x0, y0, x1, y1), clipped to 0..1."""
    ymin, xmin, ymax, xmax = (min(1.0, max(0.0, float(v))) for v in box_norm)
    distance_m = estimate_distance_m(class_name, (xmax - xmin) * frame_w, focal_length_px)
    return {
        "class": class_name,
        "confidence": round(float(confidence), 3),
        "bbox": [round(xmin, 4), round(ymin, 4), round(xmax, 4), round(ymax, 4)],
        "bearing_deg": round(bearing_deg((xmin + xmax) / 2.0, hfov_deg), 2),
        "est_distance_m": None if distance_m is None else round(distance_m, 3),
        "band": distance_band(distance_m),
    }


def load_labels(path):
    with open(path, "r") as f:
        labels = [line.strip() for line in f.readlines()]
    # The COCO labelmap starts with a "???" placeholder, but the model's
    # class ids start at 0 = person. Without dropping it every detection
    # is named after the class one below it (a person is lost as "???").
    if labels and labels[0] == "???":
        labels = labels[1:]
    return labels


def estimate_distance_m(class_name, bbox_width_px, focal_length_px):
    real_width = KNOWN_WIDTHS_M.get(class_name)
    if real_width is None or bbox_width_px <= 0:
        return None
    return (real_width * focal_length_px) / bbox_width_px


def distance_band(distance_m):
    """Map a raw metre estimate to the coarse band the ethics approval
    permits logging. Returns None if the object is farther than the
    widest defined band (not a reportable event) or if no distance
    estimate was available at all."""
    if distance_m is None:
        return None
    for limit_m, band in DISTANCE_BANDS:
        if distance_m <= limit_m:
            return band
    return None


def log_alert(log_path, class_name, band, confidence, alert_status):
    """Append exactly one JSON line containing only the fields the
    ethics application specifies (ALERT_LOG_FIELDS) - never a frame, never a
    bounding box, never a raw continuous distance."""
    record = {
        "class": class_name,
        "distance_band": band,
        "confidence": round(float(confidence), 2),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "alert_status": alert_status,
    }
    if set(record.keys()) != set(ALERT_LOG_FIELDS):
        raise RuntimeError("log_alert record must match ALERT_LOG_FIELDS exactly")
    with open(log_path, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


# Approaching objects: tracking and time to contact ---------------------------
#
# Tracker. Every detection of a HAZARD_CLASSES class above the confidence
# threshold is matched to a track by box overlap (IoU), greedily, highest
# overlap first, within a class group (car, truck and bus form one group,
# because the COCO model often swaps them on the same vehicle). A track
# survives TRACK_MAX_MISSED frames without a match. The track id is a
# counter that starts at 1 when the detector starts: it links boxes of
# the same object across frames, it does not say who or which vehicle.

# Minimum box overlap (intersection over union) for a detection to
# continue a track. At 15 to 19 fps an object at 2 s time to contact
# grows about 3 % a frame, so consecutive boxes overlap far more than this.
TRACK_IOU_MIN = 0.3

# Frames a track may go unmatched before it is dropped (the brief asks
# for 1 to 2 missed frames to be tolerated).
TRACK_MAX_MISSED = 2

# Classes that may continue each other's tracks.
TRACK_CLASS_GROUP = {"car": "vehicle", "truck": "vehicle", "bus": "vehicle"}

# Time to contact from scale expansion (Lee's tau): for a box of width w
# on an object closing at constant speed, 1/w is proportional to the
# distance, so it falls linearly in time and reaches 0 at contact. A
# robust straight-line fit (Theil-Sen, the median of all pairwise slopes)
# of 1/w against the frames' sensor timestamps over the last
# TTC_WINDOW_S seconds gives TTC = -(1/w)(now) / slope. No focal length
# is needed, so this does not depend on the uncalibrated --focal-length-px.

# Sliding window of samples used for the fit, seconds (the brief allows
# 0.4 to 0.8 s): about 11 frames on the Pi 5, 9 on the Pi 4.
TTC_WINDOW_S = 0.6

# Fewest samples, and shortest time span between first and last, for a
# fit to count. 5 frames is about 0.3 s on the Pi 4 at 14.7 fps.
TTC_MIN_FRAMES = 5
TTC_MIN_SPAN_S = 0.25

# The fitted width must grow by at least this fraction across the window.
# Constant-size objects with box jitter fail this; over 0.6 s it is the
# growth of an object at about 12 s time to contact.
TTC_MIN_REL_GROWTH = 0.05

# Share of the pairwise slopes that must agree (width growing). About 0.5
# for pure jitter, near 1 for a steady approach. A Kendall-type check.
TTC_MIN_CONSISTENCY = 0.75

# A box edge within this fraction of the image edge counts as clipped:
# its width (left or right edge) or height (top or bottom edge) is then
# not the object's, so the width fit is rejected (left or right) or the
# height check is skipped (top or bottom).
TTC_EDGE_MARGIN = 0.01

# Height check: when the box is not clipped at the top or bottom, the
# time to contact from the height must have the same sign and lie within
# this factor of the width's, else the estimate is rejected (an object
# turning changes its width without approaching).
TTC_HEIGHT_RATIO_MAX = 2.0

# Approaching alert thresholds, seconds of time to contact.
TTC_WARNING_S = 4.0
TTC_IMMEDIATE_S = 2.0

# Hysteresis: once a band is held it is kept until the time to contact
# rises above the threshold times this factor (5.0 s and 2.5 s).
TTC_RELEASE_FACTOR = 1.25

# Fields of an approaching-alert line in the alert log: the five above
# plus these four. See the ethics note in the module docstring.
APPROACH_LOG_FIELDS = ALERT_LOG_FIELDS + ("approaching", "track_id", "ttc_s", "side")

SIDES = ("front", "rear")


def theil_sen(ts, ys):
    """Robust line fit y = a + b t: b is the median of all pairwise slopes,
    a the median of y - b t. Returns (a, b, share of the non-zero pairwise
    slopes that are negative), or None with fewer than two distinct times.
    Zero slopes (a repeated reading) are left out of the share."""
    slopes = []
    n = len(ts)
    for i in range(n):
        ti, yi = ts[i], ys[i]
        for j in range(i + 1, n):
            dt = ts[j] - ti
            if dt > 1e-6:
                slopes.append((ys[j] - yi) / dt)
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


def box_iou(a, b):
    """Intersection over union of two (x0, y0, x1, y1) boxes."""
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _ttc_from_sizes(ts, sizes):
    """(ttc_s, share of pairwise slopes agreeing, relative growth) from a
    size sequence, or None when the fit is impossible."""
    inv = [1.0 / s for s in sizes]
    fit = theil_sen(ts, inv)
    if fit is None:
        return None
    a, b, neg = fit
    u_first = a + b * ts[0]
    u_last = a + b * ts[-1]
    if b >= 0 or u_last <= 0:
        return None, neg, 0.0
    return -u_last / b, neg, u_first / u_last - 1.0


def scale_ttc(samples):
    """Time to contact of one track from scale expansion.

    samples: [(t_s, (x0, y0, x1, y1)), ...] oldest first, boxes normalised
    to 0..1, t on the sensor clock. Returns (ttc_s or None, reason): reason
    is "ok", "few_frames", "clipped", "not_growing", "inconsistent",
    "slow" or "height_disagrees"."""
    if len(samples) < TTC_MIN_FRAMES or samples[-1][0] - samples[0][0] < TTC_MIN_SPAN_S:
        return None, "few_frames"
    lo, hi = TTC_EDGE_MARGIN, 1.0 - TTC_EDGE_MARGIN
    if any(b[0] <= lo or b[2] >= hi for _, b in samples):
        return None, "clipped"
    ts = [t for t, _ in samples]
    widths = [max(1e-4, b[2] - b[0]) for _, b in samples]
    res = _ttc_from_sizes(ts, widths)
    if res is None or res[0] is None:
        return None, "not_growing"
    ttc, agree, growth = res
    if agree < TTC_MIN_CONSISTENCY:
        return None, "inconsistent"
    if growth < TTC_MIN_REL_GROWTH:
        return None, "slow"
    if not any(b[1] <= lo or b[3] >= hi for _, b in samples):
        hres = _ttc_from_sizes(ts, [max(1e-4, b[3] - b[1]) for _, b in samples])
        if hres is None or hres[0] is None or not (
                1.0 / TTC_HEIGHT_RATIO_MAX <= hres[0] / ttc <= TTC_HEIGHT_RATIO_MAX):
            return None, "height_disagrees"
    return ttc, "ok"


def closing_speed_mps(samples, class_name, focal_length_px, frame_w):
    """Closing speed, m/s (positive = getting nearer, negative = moving
    away), from the slope of the pinhole distance estimate over the window.
    Scales with --focal-length-px and the class's assumed width, so it is
    as uncalibrated as est_distance_m. None with too few samples, a
    clipped box or a class without a known width."""
    real_w = KNOWN_WIDTHS_M.get(class_name)
    if real_w is None or len(samples) < TTC_MIN_FRAMES or samples[-1][0] - samples[0][0] < TTC_MIN_SPAN_S:
        return None
    lo, hi = TTC_EDGE_MARGIN, 1.0 - TTC_EDGE_MARGIN
    if any(b[0] <= lo or b[2] >= hi for _, b in samples):
        return None
    k = real_w * focal_length_px / frame_w
    fit = theil_sen([t for t, _ in samples], [k / max(1e-4, b[2] - b[0]) for _, b in samples])
    return None if fit is None else -fit[1]


class ApproachState:
    """Onset, escalation, hysteresis and clear for one track's approaching
    alert, with the same discipline as the distance alerts: a band is
    taken after ALERT_PERSISTENCE_FRAMES consecutive frames below its
    threshold, raised to immediate after as many frames below 2 s, lowered
    or cleared only after CLEAR_AFTER_MISSED_FRAMES frames above the
    release threshold (or with no valid time to contact)."""

    def __init__(self):
        self.band = None      # None, "warning" or "immediate"
        self.onset = 0
        self.up = 0
        self.down = 0
        self.off = 0

    def _raw(self, ttc):
        if ttc is None:
            return None
        warn = TTC_WARNING_S * (TTC_RELEASE_FACTOR if self.band else 1.0)
        imm = TTC_IMMEDIATE_S * (TTC_RELEASE_FACTOR if self.band == "immediate" else 1.0)
        if ttc < imm:
            return "immediate"
        if ttc < warn:
            return "warning"
        return None

    def update(self, ttc):
        """Feed one frame's time to contact (None if not valid or the track
        was not seen). Returns "active", "escalated", "lowered", "cleared"
        or None."""
        raw = self._raw(ttc)
        if self.band is None:
            if raw is None:
                self.onset = 0
                return None
            self.onset += 1
            if self.onset >= ALERT_PERSISTENCE_FRAMES:
                self.band, self.onset, self.up, self.down, self.off = raw, 0, 0, 0, 0
                return "active"
            return None
        if raw is None:
            self.up = self.down = 0
            self.off += 1
            if self.off >= CLEAR_AFTER_MISSED_FRAMES:
                self.band, self.off = None, 0
                return "cleared"
            return None
        self.off = 0
        if raw == self.band:
            self.up = self.down = 0
        elif BAND_RANK[raw] < BAND_RANK[self.band]:
            self.down = 0
            self.up += 1
            if self.up >= ALERT_PERSISTENCE_FRAMES:
                self.band, self.up = raw, 0
                return "escalated"
        else:
            self.up = 0
            self.down += 1
            if self.down >= CLEAR_AFTER_MISSED_FRAMES:
                self.band, self.down = raw, 0
                return "lowered"
        return None


class Track:
    __slots__ = ("id", "cls", "box", "confidence", "missed", "samples", "ttc_s", "ttc_reason",
                 "closing_mps", "approach")

    def __init__(self, tid, cls, box, confidence):
        from collections import deque
        self.id = tid
        self.cls = cls
        self.box = box
        self.confidence = confidence
        self.missed = 0
        self.samples = deque()
        self.ttc_s = None
        self.ttc_reason = "few_frames"
        self.closing_mps = None
        self.approach = ApproachState()

    @property
    def approaching(self):
        return self.approach.band is not None


class ApproachMonitor:
    """IoU tracker plus per-track time to contact and approaching state.
    update() is called once per frame with that frame's detections."""

    def __init__(self, focal_length_px=600.0, frame_w=640):
        self.focal_length_px = focal_length_px
        self.frame_w = frame_w
        self.tracks = []
        self.next_id = 1

    def update(self, dets, t):
        """dets: [(class_name, confidence, (x0, y0, x1, y1) normalised)].
        t: the frame's sensor time, seconds. Returns (tracks, events):
        tracks[i] is the Track of dets[i]; events is a list of (status,
        Track) with status from ApproachState.update, including "cleared"
        for an approaching track that is dropped."""
        boxes = [tuple(min(1.0, max(0.0, float(v))) for v in d[2]) for d in dets]
        pairs = []
        for di, (cls, _, _) in enumerate(dets):
            g = TRACK_CLASS_GROUP.get(cls, cls)
            for ti, tr in enumerate(self.tracks):
                if TRACK_CLASS_GROUP.get(tr.cls, tr.cls) != g:
                    continue
                o = box_iou(boxes[di], tr.box)
                if o >= TRACK_IOU_MIN:
                    pairs.append((o, di, ti))
        pairs.sort(key=lambda p: -p[0])
        det_track = [None] * len(dets)
        used = set()
        for o, di, ti in pairs:
            if det_track[di] is not None or ti in used:
                continue
            det_track[di] = self.tracks[ti]
            used.add(ti)
        for di, (cls, conf, _) in enumerate(dets):
            tr = det_track[di]
            if tr is None:
                tr = Track(self.next_id, cls, boxes[di], conf)
                self.next_id += 1
                self.tracks.append(tr)
                det_track[di] = tr
            tr.cls, tr.box, tr.confidence, tr.missed = cls, boxes[di], float(conf), 0
            tr.samples.append((t, boxes[di]))
        matched = {id(tr) for tr in det_track}
        events, alive = [], []
        for tr in self.tracks:
            while tr.samples and tr.samples[0][0] < t - TTC_WINDOW_S - 1e-9:
                tr.samples.popleft()
            if id(tr) in matched:
                s = list(tr.samples)
                tr.ttc_s, tr.ttc_reason = scale_ttc(s)
                tr.closing_mps = closing_speed_mps(s, tr.cls, self.focal_length_px, self.frame_w)
            else:
                tr.missed += 1
                tr.ttc_s, tr.ttc_reason = None, "not_seen"
            ev = tr.approach.update(tr.ttc_s)
            if tr.missed > TRACK_MAX_MISSED:
                if tr.approaching or ev == "cleared":
                    tr.approach.band = None
                    events.append(("cleared", tr))
                continue
            if ev:
                events.append((ev, tr))
            alive.append(tr)
        self.tracks = alive
        return det_track, events

    def approaching_tracks(self):
        return [tr for tr in self.tracks if tr.approaching]


def track_fields(track, side):
    """The fields each /alerts and /detections entry gains."""
    if track is None:
        return {"side": side, "track_id": None, "approaching": False, "ttc_s": None, "closing_mps": None}
    return {
        "side": side,
        "track_id": track.id,
        "approaching": track.approaching,
        "ttc_s": None if track.ttc_s is None else round(track.ttc_s, 2),
        "closing_mps": None if track.closing_mps is None else round(track.closing_mps, 2),
    }


def log_approach(log_path, class_name, band, confidence, alert_status, track_id, ttc_s, side):
    """One approaching-alert line: the five ALERT_LOG_FIELDS plus
    "approaching": true, the track id, the time to contact (0.1 s, null on
    clear) and the side. Never a frame, a box or a distance."""
    record = {
        "class": class_name,
        "distance_band": band,
        "confidence": round(float(confidence), 2),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "alert_status": alert_status,
        "approaching": True,
        "track_id": int(track_id),
        "ttc_s": None if ttc_s is None else round(float(ttc_s), 1),
        "side": side,
    }
    if set(record.keys()) != set(APPROACH_LOG_FIELDS):
        raise RuntimeError("log_approach record must match APPROACH_LOG_FIELDS exactly")
    with open(log_path, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def alerts_list(active_record, class_track, class_fields, monitor, approach_record, side):
    """GET /alerts "active": the class-level distance alerts, each with the
    fields of the track that last held it, its band raised to the track's
    approaching band when that is more urgent; then one entry per
    approaching track not already listed. Most urgent first."""
    live = {tr.id: tr for tr in monitor.tracks}
    out, listed = [], set()
    for cls, rec in active_record.items():
        tr = live.get(class_track.get(cls))
        fields = track_fields(tr, side) if tr is not None else class_fields.get(cls, track_fields(None, side))
        e = dict(rec, **fields)
        if tr is not None and tr.approaching and (
                e["distance_band"] is None or BAND_RANK[tr.approach.band] < BAND_RANK[e["distance_band"]]):
            e["distance_band"] = tr.approach.band
        listed.add(fields["track_id"])
        out.append(e)
    for tr in monitor.approaching_tracks():
        if tr.id in listed:
            continue
        rec = approach_record.get(tr.id) or {"class": tr.cls, "confidence": round(tr.confidence, 2),
                                             "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                                             "alert_status": "active"}
        e = {k: rec[k] for k in ALERT_LOG_FIELDS if k in rec}
        e["distance_band"] = tr.approach.band
        e.update(track_fields(tr, side))
        out.append(e)
    out.sort(key=lambda r: (BAND_RANK.get(r["distance_band"], 9),
                            r["ttc_s"] if r.get("ttc_s") is not None else 1e9))
    return out


def side_setting(cli_value, options_path):
    """"front" or "rear": --side, else "side" in detector_options.json,
    else "front"."""
    raw = cli_value
    if raw is None:
        try:
            with open(options_path) as f:
                raw = json.load(f).get("side")
        except (OSError, ValueError):
            raw = None
    raw = (raw or "front").strip().lower()
    if raw not in SIDES:
        raise ValueError("side must be front or rear, not %r" % raw)
    return raw


PREVIEW_PAGE = b"""<!doctype html><html><head><title>SW-7 detector preview</title>
<style>body{margin:0;background:#111;color:#ddd;font-family:sans-serif;text-align:center}
img{max-width:100%;height:auto;margin-top:8px}</style></head>
<body><div>SW-7 hazard detector: live view, boxes drawn on what the model detects</div>
<img src="/stream"></body></html>"""

BAND_COLOURS = {"immediate": (230, 60, 50), "warning": (240, 170, 30), "monitoring": (60, 190, 90)}


class PreviewServer:
    """Live view of the camera with the model's detections drawn on it, for
    bench checks. Frames stay in memory as the latest JPEG only and are
    never written to disk. Bound to localhost by default, so only a browser
    on this Pi can open it; --preview-host 0.0.0.0 also serves it to
    devices on the same local network (still never saved or uploaded).

    Drawing and JPEG encoding run in their own thread. The detector only
    hands over its latest frame and returns immediately; if the encoder is
    still busy, older frames are skipped, so the live view can fall behind
    without ever slowing detection down."""

    def __init__(self, port, host="127.0.0.1", colour_fix=None):
        import threading
        self._colour_fix = colour_fix   # applied to the live view only, in this encoder thread
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        self._lock = threading.Condition()
        self._jpeg = None
        self._pending = None          # latest (rgb, detections, stats) not yet encoded
        self._pending_cv = threading.Condition()
        self._running = True
        self._alerts_json = b'{"active": [], "fps": 0, "latency_ms": null}'
        self._detections = None   # latest GET /detections content (dict), None before the first frame
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if self.path == "/":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(PREVIEW_PAGE)
                elif self.path == "/alerts":
                    with server._lock:
                        body = server._alerts_json
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif self.path.split("?", 1)[0] == "/detections":
                    with server._lock:
                        d = server._detections
                    if d is None:
                        d = {"detections": [], "frame_t_mono": None, "fps": 0.0}
                    d = dict(d, t_mono=round(time.monotonic(), 4))
                    body = json.dumps(d).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif self.path == "/stream":
                    import socket
                    # Keep the kernel from queueing several frames ahead of the
                    # viewer: a small send buffer means a slow link drops frames
                    # instead of showing ever-older ones.
                    try:
                        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                        self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 64 * 1024)
                    except OSError:
                        pass
                    self.send_response(200)
                    self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    last = None
                    try:
                        while server._running:
                            with server._lock:
                                if server._jpeg is last:
                                    server._lock.wait(timeout=2)
                                jpeg = server._jpeg
                            if jpeg is None or jpeg is last:
                                continue
                            last = jpeg
                            self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n"
                                             + f"Content-Length: {len(jpeg)}\r\n\r\n".encode()
                                             + jpeg + b"\r\n")
                    except OSError:
                        pass  # viewer closed the page or the connection dropped
                else:
                    self.send_error(404)

        self._httpd = ThreadingHTTPServer((host, port), Handler)
        self._httpd.daemon_threads = True
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()
        self._encoder = threading.Thread(target=self._encode_loop, daemon=True)
        self._encoder.start()

    def publish(self, rgb_frame, detections, stats):
        """Hand over the latest frame. Never blocks on encoding."""
        with self._pending_cv:
            self._pending = (rgb_frame, detections, stats)
            self._pending_cv.notify()

    def _encode_loop(self):
        import io
        from PIL import Image, ImageDraw
        while self._running:
            with self._pending_cv:
                while self._pending is None and self._running:
                    self._pending_cv.wait(timeout=1)
                item, self._pending = self._pending, None
            if item is None:
                continue
            rgb_frame, detections, stats = item
            if self._colour_fix is not None:
                rgb_frame = self._colour_fix(rgb_frame)
            img = Image.fromarray(rgb_frame)
            draw = ImageDraw.Draw(img)
            for d in detections:
                colour = d.get("colour") or BAND_COLOURS.get(d["band"], (150, 150, 150))
                draw.rectangle(d["box"], outline=colour, width=3)
                dist = f"{d['distance_m']:.1f}m" if d["distance_m"] is not None else "?"
                label = d.get("label") or f"{d['class']} {d['confidence']:.2f} {dist} {d['band'] or 'out of range'}"
                x, y = d["box"][0], max(0, d["box"][1] - 14)
                draw.rectangle((x, y, x + 7 * len(label), y + 14), fill=colour)
                draw.text((x + 2, y + 1), label, fill=(0, 0, 0))
            draw.rectangle((0, 0, 330, 18), fill=(0, 0, 0))
            draw.text((6, 4), stats, fill=(255, 255, 255))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=60)
            with self._lock:
                self._jpeg = buf.getvalue()
                self._lock.notify_all()

    def set_alerts(self, active, fps, latency_ms, road_hazards=None, side=None):
        """Publish the currently active alerts for GET /alerts. The five
        fields of the alert log plus the track fields (side, track_id,
        approaching, ttc_s, closing_mps; see the module docstring). With the
        pothole path on, "road_hazards" lists the active experimental
        pothole alerts (a new key, so readers of "active" are unaffected).
        side, when given, is also echoed at the top level."""
        d = {
            "active": active,
            "fps": round(fps, 1),
            "latency_ms": None if latency_ms is None else round(latency_ms),
        }
        if side is not None:
            d["side"] = side
        if road_hazards is not None:
            d["road_hazards"] = road_hazards
        body = json.dumps(d).encode()
        with self._lock:
            self._alerts_json = body

    def set_detections(self, detections, frame_t_mono, fps, hfov_deg=DEFAULT_HFOV_DEG,
                       road_hazards=None, road_hazards_meta=None, side=None):
        """Publish the latest frame's detections for GET /detections (see
        detection_record). frame_t_mono is the frame's time on this Pi's
        monotonic clock, seconds; the response also carries t_mono, the
        time it was served, so a reader on another clock can work out the
        frame's age."""
        d = {
            "detections": list(detections),
            "frame_t_mono": None if frame_t_mono is None else round(frame_t_mono, 4),
            "fps": round(fps, 1),
            "hfov_deg": hfov_deg,
            "bands": [[limit, band] for limit, band in DISTANCE_BANDS],
            "confidence_threshold": CONFIDENCE_THRESHOLD,
        }
        if side is not None:
            d["side"] = side
        if road_hazards_meta is not None:   # new keys only; "detections" never holds a pothole
            d["road_hazards"] = list(road_hazards or [])
            d["road_hazards_meta"] = road_hazards_meta
        with self._lock:
            self._detections = d

    def close(self):
        self._running = False
        with self._pending_cv:
            self._pending_cv.notify_all()
        self._httpd.shutdown()
        self._httpd.server_close()


class LatencyStats:
    """Per-frame stage timings, summarised every few seconds.

    Sensor-to-result latency uses the frame's SensorTimestamp, which the
    Picamera2 manual defines as nanoseconds since boot at the moment the
    first pixel is read out of the sensor, on the same clock as
    time.monotonic_ns(). It therefore covers readout, ISP, queueing,
    preprocessing, inference and alert logic, but not the exposure itself."""

    FIELDS = ("frame", "sensor_ns", "queue_ms", "pre_ms", "infer_ms", "post_ms", "total_ms")

    def __init__(self, csv_path=None, every_s=5.0):
        self.rows = []
        self.every_s = every_s
        self.last_print = time.monotonic()
        self.frames_since = 0
        self.csv = None
        if csv_path:
            self.csv = open(csv_path, "w", buffering=1)
            self.csv.write(",".join(self.FIELDS) + "\n")

    def add(self, row):
        self.rows.append(row)
        self.frames_since += 1
        if self.csv:
            self.csv.write(",".join(f"{row[k]:.2f}" if isinstance(row[k], float) else str(row[k])
                                    for k in self.FIELDS) + "\n")

    @staticmethod
    def _pct(vals, q):
        v = sorted(vals)
        return v[min(len(v) - 1, int(round(q * (len(v) - 1))))]

    def maybe_print(self):
        now = time.monotonic()
        if now - self.last_print < self.every_s or not self.rows:
            return None
        fps = self.frames_since / (now - self.last_print)
        parts = [f"{fps:.1f} fps"]
        for k in ("queue_ms", "pre_ms", "infer_ms", "post_ms", "total_ms"):
            vals = [r[k] for r in self.rows]
            parts.append(f"{k[:-3]} p50={self._pct(vals, 0.5):.0f} p95={self._pct(vals, 0.95):.0f} "
                         f"max={max(vals):.0f}")
        line = "[timing] " + " | ".join(parts) + " (ms)"
        print(line)
        self.rows = []
        self.frames_since = 0
        self.last_print = now
        return line

    def close(self):
        if self.csv:
            self.csv.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="detect.tflite")
    parser.add_argument("--labels", default="labelmap.txt")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    # Focal length in pixels: focal_length_px = (bbox_width_px * distance_m) / real_width_m,
    # calibrated with one object at a known distance (the console prints
    # bbox_width_px for each detection). NOT yet calibrated for this camera.
    # This default is a rough placeholder; from the Camera Module v1 lens
    # spec (3.60 mm, 1.4 um pixels, 640x480 binned from near full field)
    # about 643 px would be expected, but a real calibration shot must
    # replace it before distance numbers are trusted. Valid at 640 px width only.
    parser.add_argument("--focal-length-px", type=float, default=600.0,
                         help="UNCALIBRATED placeholder - see comment in source")
    parser.add_argument("--hfov-deg", type=float, default=DEFAULT_HFOV_DEG,
                        help="Horizontal field of view, degrees, for the bearing in GET /detections "
                             "(default %(default)s, OV5647 Camera Module v1 lens)")
    parser.add_argument("--duration", type=int, default=0,
                         help="Seconds to run, 0 = run until Ctrl+C")
    parser.add_argument("--log-path", default="alerts.jsonl",
                         help="Append-only JSONL file for reportable alert events "
                              "(class, distance_band, confidence, timestamp, alert_status only)")
    parser.add_argument("--preview", action="store_true",
                         help="Serve a live view with detections drawn on it over HTTP "
                              "(never saved; see --preview-host for who can open it)")
    parser.add_argument("--preview-port", type=int, default=8080)
    parser.add_argument("--preview-host", default="127.0.0.1",
                         help="127.0.0.1 = this Pi only; 0.0.0.0 = also other devices on the local network")
    parser.add_argument("--tuning", default=None,
                         help="Camera tuning file, e.g. ov5647_noir.json for a module with no "
                              "infrared filter (pink or red cast). Default: the standard tuning")
    parser.add_argument("--saturation", type=float, default=None,
                        help="Colour saturation (libcamera control, 1.0 = normal). The module "
                             "has no infrared filter, so colours come out washed out even with "
                             "the NoIR tuning; about 1.5 to 2.0 restores some of it")
    parser.add_argument("--dark-neutral", default=None, metavar="LO,HI",
                        help="Live view only: remove the colour cast from dark pixels (black looks purple without an "
                             "infrared filter): fully neutral when every channel is at LO or below, unchanged "
                             "when any channel reaches HI, e.g. 50,110. Default: detector_options.json if present, else off")
    parser.add_argument("--threads", type=int, default=4,
                         help="CPU threads for inference (the Pi 4 has 4 cores)")
    parser.add_argument("--verbose", action="store_true",
                         help="Print every per-frame detection (slower terminals can lag); "
                              "otherwise only alerts and a timing summary every 5 s are printed")
    parser.add_argument("--timing-log", default=None,
                         help="Optional CSV of per-frame stage timings (no image data), for latency analysis")
    parser.add_argument("--potholes", choices=("on", "off"), default=None,
                        help="Experimental pothole path (pothole_detector.py). Default: \"potholes\" in "
                             "detector_options.json if present, else %s" % ("on" if POTHOLES_DEFAULT else "off"))
    parser.add_argument("--pothole-model", default=None,
                        help="NCNN model folder (default: options file \"pothole_model\", else "
                             + DEFAULT_POTHOLE_MODEL + " next to this script)")
    parser.add_argument("--pothole-threads", type=int, default=None,
                        help="ncnn threads in the pothole worker (default 1; it runs at nice 19 on its own core)")
    parser.add_argument("--pothole-rate", type=float, default=None,
                        help="Maximum pothole runs per second (default 0.25, the rate that kept the main detector within 10 %%)")
    parser.add_argument("--pothole-band", default=None, metavar="TOP,BOTTOM",
                        help="Road band as fractions of the frame height (default 0.42,0.68, as trained)")
    parser.add_argument("--pothole-conf", type=float, default=None,
                        help="Pothole confidence threshold (default 0.5)")
    parser.add_argument("--side", choices=SIDES, default=None,
                        help="Where this camera looks, echoed in /alerts and /detections: front (Pi 5) or "
                             "rear (Pi 4). Default: \"side\" in detector_options.json if present, else front")
    parser.add_argument("--test-image", default=None,
                        help="Use this saved picture instead of the camera (repeated at about 15 fps), "
                             "to test the pipeline without the camera")
    args = parser.parse_args()

    # ai_edge_litert is the successor to tflite_runtime and the only one
    # of the two with wheels for the Python 3.13 on current Pi OS.
    try:
        from ai_edge_litert.interpreter import Interpreter
    except ImportError:
        try:
            from tflite_runtime.interpreter import Interpreter
        except ImportError:
            from tensorflow.lite.python.interpreter import Interpreter

    here = os.path.dirname(os.path.abspath(__file__))
    options_path = os.path.join(here, "detector_options.json")
    # Start the pothole worker before the camera, so the new process starts clean.
    pothole_cfg = pothole_settings(args, options_path, here)
    pothole = None
    infer_threads = args.threads
    if pothole_cfg["enabled"]:
        # Optional ("pothole_reserve_core": true): pin the worker to the last core
        # and the main detector to the others. Tried on the Pi 4 on 11 Oct 2026 and
        # worse (10.9 fps against 12 fps sharing all four cores at 1 Hz): the cost
        # is shared cache and memory bandwidth, not CPU time, so it is off by default.
        ncpu = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else 1
        reserve = pothole_cfg["reserve_core"] and ncpu >= 2
        try:
            import pothole_detector as pd
            pothole = pd.PotholeWorker(pothole_cfg["model"], threads=pothole_cfg["threads"],
                                       max_rate_hz=pothole_cfg["rate"], band=pothole_cfg["band"],
                                       conf=pothole_cfg["conf"],
                                       cpus={max(os.sched_getaffinity(0))} if reserve else None)
            pothole_debounce = pd.RunDebouncer()
            if reserve:
                main_cpus = set(sorted(os.sched_getaffinity(0))[:-1])
                os.sched_setaffinity(0, main_cpus)   # threads started from here on inherit it
                infer_threads = min(args.threads, len(main_cpus))
            print(f"Pothole path (EXPERIMENTAL): {pothole_cfg['model']} at {pothole.imgsz} px, band "
                  f"{pothole_cfg['band'][0]:.2f}-{pothole_cfg['band'][1]:.2f} of the height, 3 tiles, "
                  f"conf {pothole_cfg['conf']}, alert after {pd.DEBOUNCE_K} of {pd.DEBOUNCE_N} runs, "
                  f"up to {pothole_cfg['rate']:g} Hz, {pothole_cfg['threads']} thread(s) at nice 19"
                  + (f", own core; main detector on {infer_threads} cores" if reserve else ""))
        except Exception as e:   # never let the experimental path stop the main detector
            if pothole is not None:
                pothole.close()
            pothole = None
            infer_threads = args.threads
            print(f"Pothole path disabled: {e!r}")
    else:
        print("Pothole path: off")

    if args.test_image:
        Picamera2 = still_image_camera(args.test_image, args.width, args.height)
    else:
        from picamera2 import Picamera2

    labels = load_labels(args.labels)
    interpreter = Interpreter(model_path=args.model, num_threads=infer_threads)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    input_height = input_details[0]['shape'][1]
    input_width = input_details[0]['shape'][2]

    if args.tuning and not args.test_image:
        picam2 = Picamera2(tuning=Picamera2.load_tuning_file(args.tuning))
        print(f"Camera tuning: {args.tuning}")
    else:
        picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(
        main={"size": (args.width, args.height), "format": "RGB888"}))
    picam2.start()
    if args.saturation is not None and not args.test_image:
        picam2.set_controls({"Saturation": args.saturation})
        print(f"Camera saturation: {args.saturation}")

    dn = dark_neutral_setting(args.dark_neutral, options_path)
    neutralise = DarkNeutraliser(*dn) if dn else None
    if neutralise:
        print(f"Dark neutralise (live view only, detector input unchanged): neutral with all channels "
              f"at {dn[0]} or below, unchanged from {dn[1]}")
    print(f"Model loaded: {args.model} (input {input_width}x{input_height}, {infer_threads} inference threads)")
    print(f"WARNING: focal_length_px={args.focal_length_px} is UNCALIBRATED - "
          f"distance estimates are order-of-magnitude only until calibrated.")
    print("Watching for:", ", ".join(sorted(HAZARD_CLASSES)))
    side = side_setting(args.side, options_path)
    print(f"Alert log (class/band/confidence/timestamp/status only; approaching alerts add "
          f"track_id/ttc_s/side): {args.log_path}")
    print(f"Side: {side}. Approaching alert: time to contact under {TTC_WARNING_S:g} s (warning), "
          f"{TTC_IMMEDIATE_S:g} s (immediate), from box growth over {TTC_WINDOW_S:g} s")

    # Stop cleanly under systemd (SIGTERM) the same way as Ctrl+C, so the
    # camera and preview are released in the finally block.
    import signal

    def _on_sigterm(signum, frame_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, _on_sigterm)

    # Class-level persistence state: an object must be seen in-band for
    # ALERT_PERSISTENCE_FRAMES consecutive frames before it becomes a
    # reportable alert, and a "cleared" event is logged once it drops out
    # again. This is deliberately class-level, not per-instance (see
    # module docstring) - it answers "is a car persistently near", not
    # "is this specific car persistently near".
    streak = {cls: 0 for cls in HAZARD_CLASSES}
    missed = {cls: 0 for cls in HAZARD_CLASSES}
    nearer = {cls: 0 for cls in HAZARD_CLASSES}  # consecutive frames nearer than the active band
    active_band = {cls: None for cls in HAZARD_CLASSES}  # None = no active alert
    active_record = {}  # class -> the last "active" record logged, for GET /alerts
    pothole_records = []    # latest pothole run's detections, for GET /detections road_hazards
    pothole_alert = None    # active experimental pothole alert, for GET /alerts road_hazards
    pothole_last = {"frame_t_mono": None, "infer_ms": None}
    # Per-object tracks and time to contact (see "Approaching objects" above).
    monitor = ApproachMonitor(args.focal_length_px, args.width)
    class_track = {}       # class -> id of the track that last held its distance alert
    class_fields = {}      # class -> that track's fields, kept while the track is gone
    approach_record = {}   # track id -> the approaching record last logged, for GET /alerts

    preview = None
    timing = LatencyStats(args.timing_log)
    last_timing = ""
    start = time.monotonic()
    frame_count = 0
    try:
        if args.preview:
            preview = PreviewServer(args.preview_port, args.preview_host, colour_fix=neutralise)
            if args.preview_host == "127.0.0.1":
                print(f"Live view: open http://localhost:{args.preview_port} in this Pi's browser")
            else:
                print(f"Live view: open http://<this Pi's IP>:{args.preview_port} from a device on the same network "
                      f"(hostname -I shows the IP)")
        start = time.monotonic()
        while args.duration == 0 or (time.monotonic() - start) < args.duration:
            request = picam2.capture_request()
            try:
                frame = request.make_array("main")
                sensor_ns = request.get_metadata().get("SensorTimestamp")
            finally:
                request.release()
            t_got = time.monotonic_ns()
            frame_count += 1

            # Picamera2's "RGB888" is stored B, G, R; the model expects R, G, B.
            rgb = np.ascontiguousarray(frame[..., ::-1])
            resized = np_resize(rgb, input_width, input_height)
            input_data = np.expand_dims(resized, axis=0)
            if input_details[0]['dtype'] == np.float32:
                input_data = (np.float32(input_data) - 127.5) / 127.5
            t_pre = time.monotonic_ns()

            interpreter.set_tensor(input_details[0]['index'], input_data)
            interpreter.invoke()
            t_inf = time.monotonic_ns()
            # The frame (and rgb, if the preview is on) is replaced by the next
            # capture_array() call. Nothing derived from it is written to disk
            # (see docstring).

            boxes = interpreter.get_tensor(output_details[0]['index'])[0]
            classes = interpreter.get_tensor(output_details[1]['index'])[0]
            scores = interpreter.get_tensor(output_details[2]['index'])[0]

            frame_h, frame_w = frame.shape[0], frame.shape[1]
            frame_t = (sensor_ns if sensor_ns else t_got) / 1e9
            in_band_this_frame = {}  # class_name -> (band, confidence, bbox_px, track); nearest band wins, then confidence
            drawn = []  # detections for the live view only, never logged
            frame_dets = []  # for GET /detections only (served, never logged)
            kept = []   # (index, class_name) of the hazard-class detections above the threshold
            for i in range(len(scores)):
                if scores[i] < CONFIDENCE_THRESHOLD:
                    continue
                class_id = int(classes[i])
                if class_id >= len(labels):
                    continue
                class_name = labels[class_id]
                if class_name in HAZARD_CLASSES:
                    kept.append((i, class_name))
            t_trk = time.perf_counter()
            det_tracks, approach_events = monitor.update(
                [(c, float(scores[i]), (boxes[i][1], boxes[i][0], boxes[i][3], boxes[i][2])) for i, c in kept],
                frame_t)
            track_ms = (time.perf_counter() - t_trk) * 1000.0
            for (i, class_name), track in zip(kept, det_tracks):
                ymin, xmin, ymax, xmax = boxes[i]
                bbox_width_px = (xmax - xmin) * frame_w
                distance_m = estimate_distance_m(class_name, bbox_width_px, args.focal_length_px)
                band = distance_band(distance_m)
                if preview is not None:
                    frame_dets.append(dict(detection_record(class_name, scores[i], boxes[i], frame_w,
                                                            args.focal_length_px, args.hfov_deg),
                                           **track_fields(track, side)))
                    item = {
                        "box": (int(xmin * frame_w), int(ymin * frame_h), int(xmax * frame_w), int(ymax * frame_h)),
                        "class": class_name, "confidence": float(scores[i]),
                        "distance_m": distance_m, "band": band,
                    }
                    if track.approaching:
                        item["band"] = track.approach.band
                        item["label"] = (f"#{track.id} {class_name} APPROACHING TTC {track.ttc_s:.1f}s"
                                         if track.ttc_s is not None else f"#{track.id} {class_name} APPROACHING")
                    drawn.append(item)
                if band is None:
                    continue  # detected, but outside the reportable zones entirely

                confidence = float(scores[i])
                prev = in_band_this_frame.get(class_name)
                if (prev is None or BAND_RANK[band] < BAND_RANK[prev[0]]
                        or (band == prev[0] and confidence > prev[1])):
                    in_band_this_frame[class_name] = (band, confidence, bbox_width_px, track)

            ts_console = time.strftime("%H:%M:%S")
            for class_name in HAZARD_CLASSES:
                if class_name in in_band_this_frame:
                    band, confidence, bbox_px, track = in_band_this_frame[class_name]
                    class_track[class_name] = track.id
                    class_fields[class_name] = track_fields(track, side)
                    streak[class_name] += 1
                    missed[class_name] = 0
                    if args.verbose:
                        print(f"[{ts_console}] {class_name} band={band} conf={confidence:.2f} "
                              f"bbox_width_px={bbox_px:.0f} streak={streak[class_name]}/{ALERT_PERSISTENCE_FRAMES}")
                    current = active_band[class_name]
                    if current is None and streak[class_name] >= ALERT_PERSISTENCE_FRAMES:
                        active_band[class_name] = band
                        active_record[class_name] = log_alert(args.log_path, class_name, band, confidence, "active")
                        print(f"[{ts_console}] ALERT {class_name} ({band}) conf={confidence:.2f} "
                              f"bbox_width_px={bbox_px:.0f}")
                    elif current is not None and BAND_RANK[band] < BAND_RANK[current]:
                        # Nearer than the logged band: re-log once it has held for
                        # the same debounce as an onset, so one noisy frame can't escalate.
                        nearer[class_name] += 1
                        if nearer[class_name] >= ALERT_PERSISTENCE_FRAMES:
                            nearer[class_name] = 0
                            active_band[class_name] = band
                            active_record[class_name] = log_alert(args.log_path, class_name, band, confidence, "active")
                            print(f"[{ts_console}] ALERT escalated: {class_name} ({current} -> {band})")
                    else:
                        nearer[class_name] = 0
                else:
                    streak[class_name] = 0
                    nearer[class_name] = 0
                    if active_band[class_name] is not None:
                        missed[class_name] += 1
                        if missed[class_name] >= CLEAR_AFTER_MISSED_FRAMES:
                            active_band[class_name] = None
                            active_record.pop(class_name, None)
                            class_track.pop(class_name, None)
                            class_fields.pop(class_name, None)
                            missed[class_name] = 0
                            log_alert(args.log_path, class_name, None, 0.0, "cleared")
                            print(f"[{ts_console}] cleared: {class_name}")

            for status, tr in approach_events:
                if status == "cleared":
                    approach_record.pop(tr.id, None)
                    log_approach(args.log_path, tr.cls, None, 0.0, "cleared", tr.id, None, side)
                    print(f"[{ts_console}] cleared: approaching {tr.cls} #{tr.id}")
                else:   # "active", "escalated" or "lowered": log the new band
                    approach_record[tr.id] = log_approach(args.log_path, tr.cls, tr.approach.band, tr.confidence,
                                                          "active", tr.id, tr.ttc_s, side)
                    ttc_txt = "?" if tr.ttc_s is None else f"{tr.ttc_s:.1f}"
                    print(f"[{ts_console}] ALERT approaching {tr.cls} #{tr.id} ({tr.approach.band}, {status}) "
                          f"TTC {ttc_txt} s, {side}")
            if args.verbose:
                for tr in monitor.tracks:
                    if tr.ttc_s is not None:
                        print(f"[{ts_console}] track #{tr.id} {tr.cls} ttc={tr.ttc_s:.2f}s "
                              f"closing={tr.closing_mps} m/s (uncalibrated) track_ms={track_ms:.2f}")

            if pothole is not None:
                # Never waits: collect a finished run if there is one, then hand
                # over this frame's band if the worker is idle and due.
                res = pothole.poll()
                if res is not None:
                    pothole_records = [pd.pothole_record(det, frame_w, frame_h, args.hfov_deg)
                                       for det in res["dets"]]
                    pothole_last = {"frame_t_mono": round(res["frame_t"], 4), "infer_ms": round(res["infer_ms"], 1)}
                    top = max(pothole_records, key=lambda r: r["confidence"], default=None)
                    change = pothole_debounce.update(top is not None)
                    if args.verbose and top is not None:
                        print(f"[{ts_console}] pothole x{len(pothole_records)} best={top['confidence']:.2f} "
                              f"({res['infer_ms']:.0f} ms)")
                    if change == "active":
                        rec = log_alert(args.log_path, "pothole", None, top["confidence"], "active")
                        pothole_alert = dict(rec, bearing_deg=top["bearing_deg"], model=top["model"],
                                             experimental=True)
                        print(f"[{ts_console}] ALERT pothole (EXPERIMENTAL) conf={top['confidence']:.2f} "
                              f"bearing={top['bearing_deg']:.1f} deg")
                    elif change == "cleared":
                        pothole_alert = None
                        log_alert(args.log_path, "pothole", None, 0.0, "cleared")
                        print(f"[{ts_console}] cleared: pothole (experimental)")
                    elif pothole_alert is not None and top is not None:
                        pothole_alert = dict(pothole_alert, bearing_deg=top["bearing_deg"])
                pothole.maybe_submit(rgb, (sensor_ns if sensor_ns else t_got) / 1e9)
                if preview is not None:
                    for r in pothole_records:
                        x0, y0, x1, y1 = r["bbox"]
                        drawn.append({"box": (int(x0 * frame_w), int(y0 * frame_h), int(x1 * frame_w),
                                              int(y1 * frame_h)),
                                      "class": "pothole", "confidence": r["confidence"], "distance_m": None,
                                      "band": None, "colour": (200, 80, 230),
                                      "label": f"pothole? {r['confidence']:.2f} (experimental)"})

            t_post = time.monotonic_ns()
            timing.add({
                "frame": frame_count,
                "sensor_ns": sensor_ns if sensor_ns is not None else -1,
                "queue_ms": (t_got - sensor_ns) / 1e6 if sensor_ns else 0.0,
                "pre_ms": (t_pre - t_got) / 1e6,
                "infer_ms": (t_inf - t_pre) / 1e6,
                "post_ms": (t_post - t_inf) / 1e6,
                "total_ms": (t_post - sensor_ns) / 1e6 if sensor_ns else (t_post - t_got) / 1e6,
            })
            line = timing.maybe_print()
            if line:
                last_timing = line
            if preview is not None:
                elapsed_now = time.monotonic() - start
                fps_now = frame_count / elapsed_now if elapsed_now > 0 else 0.0
                total_ms = (t_post - sensor_ns) / 1e6 if sensor_ns else 0.0
                preview.publish(rgb, drawn, f"{fps_now:.1f} fps  sensor-to-result {total_ms:.0f} ms")
                # Pothole keys are only passed when the path is on, so the
                # output (and any stand-in preview object) is unchanged when off.
                alert_extra, det_extra = {}, {}
                if pothole is not None:
                    alert_extra = {"road_hazards": [pothole_alert] if pothole_alert else []}
                    det_extra = {"road_hazards": pothole_records, "road_hazards_meta": {
                        "experimental": True, "model": pd.MODEL_NAME, "imgsz": pothole.imgsz,
                        "band": list(pothole_cfg["band"]), "tiles": 3,
                        "confidence_threshold": pothole_cfg["conf"],
                        "debounce": f"{pd.DEBOUNCE_K} of {pd.DEBOUNCE_N} runs",
                        "rate_hz": round(pothole.rate_hz(), 2), "runs": pothole.runs, **pothole_last}}
                # Positional, so stand-in preview objects that pass *args through keep working.
                preview.set_alerts(alerts_list(active_record, class_track, class_fields, monitor,
                                               approach_record, side),
                                   fps_now, total_ms if sensor_ns else None,
                                   alert_extra.get("road_hazards"), side)
                preview.set_detections(frame_dets, frame_t, fps_now, args.hfov_deg,
                                       det_extra.get("road_hazards"), det_extra.get("road_hazards_meta"), side)

    except KeyboardInterrupt:
        pass
    finally:
        elapsed = time.monotonic() - start
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"\nStopped. {frame_count} frames in {elapsed:.1f}s ({fps:.1f} fps average).")
        timing.close()
        picam2.stop()
        if preview is not None:
            preview.close()
        if pothole is not None:
            print(f"Pothole runs: {pothole.runs} ({pothole.rate_hz():.1f} Hz over the last 10 s)")
            pothole.close()


class DarkNeutraliser:
    """Removes the colour cast from dark pixels, so black looks black.

    The camera module has no infrared-cut filter, and many black fabrics and
    plastics reflect infrared, which the red and blue pixels pick up: black
    comes out purple, more so with the saturation boost. In HSV terms each
    pixel's saturation is scaled by a weight set by its brightness V (its
    brightest channel): 0 at or below `lo` (grey), rising linearly to 1 at
    `hi` (unchanged). V, not luma, decides, because a strong blue or red has a
    low luma but one bright channel and must keep its colour; a near-black
    pixel is dark in every channel. Pixels with V at or above `hi` are copied
    unchanged, so bright colours are bit-exact. Pillow only (C code, no OpenCV):
    a pure numpy version took 171 ms a frame on the Pi 4."""

    def __init__(self, lo=50, hi=110):
        if not 0 <= lo < hi <= 255:
            raise ValueError("need 0 <= lo < hi <= 255")
        self.lo, self.hi = lo, hi
        self.weight_lut = [max(0, min(255, (v - lo) * 255 // (hi - lo))) for v in range(256)]
        self.mask_lut = [255 if v < hi else 0 for v in range(256)]

    def __call__(self, rgb):
        from PIL import Image, ImageChops
        img = Image.fromarray(rgb)
        h, s, v = img.convert("HSV").split()
        s = ImageChops.multiply(s, v.point(self.weight_lut))
        fixed = Image.merge("HSV", (h, s, v)).convert("RGB")
        return np.asarray(Image.composite(fixed, img, v.point(self.mask_lut)))


def dark_neutral_setting(cli_value, options_path):
    """(lo, hi) from --dark-neutral "LO,HI", else from detector_options.json next to this
    script ({"dark_neutral": [50, 110]}), else None (off). The file lets the setting be
    changed on the Pi without editing the system service."""
    raw = cli_value
    if raw is None:
        try:
            with open(options_path) as f:
                raw = json.load(f).get("dark_neutral")
        except (OSError, ValueError):
            raw = None
    if raw in (None, "", "off", False):
        return None
    lo, hi = (int(v) for v in (raw.split(",") if isinstance(raw, str) else raw))
    return lo, hi


# Experimental pothole path: off by default. Measured on the Pi 4 with the
# service running (11 Oct 2026, Planning/pothole-integration-prompt.md): the
# main detector stays within 10 % of its 14.6 fps / 121 ms only with the pothole
# model at 0.25 Hz (13.9 fps, 125 ms median, 157 ms p95); at 0.5 Hz the p95
# latency rose 12 %, and at 1 Hz or more fps fell 18 to 25 %. 0.25 Hz is too slow
# to warn a moving vehicle, so the 2 to 5 Hz the path was meant to run at does
# not fit on the Pi 4 next to the main detector. Turn it on with --potholes on
# or {"potholes": true} in detector_options.json.
POTHOLES_DEFAULT = False
POTHOLE_RATE_DEFAULT_HZ = 0.25
DEFAULT_POTHOLE_MODEL = "yolo11n_sa_band_tiles_320_ncnn_model"


def pothole_settings(args, options_path, here):
    """Pothole path settings: command line first, then detector_options.json
    ("potholes", "pothole_model", "pothole_threads", "pothole_rate",
    "pothole_band", "pothole_conf"), then the defaults."""
    try:
        with open(options_path) as f:
            opts = json.load(f)
    except (OSError, ValueError):
        opts = {}

    def pick(cli, key, default):
        return cli if cli is not None else opts.get(key, default)

    enabled = args.potholes == "on" if args.potholes is not None else bool(opts.get("potholes", POTHOLES_DEFAULT))
    model = pick(args.pothole_model, "pothole_model", None)
    if model is None:
        model = os.path.join(here, DEFAULT_POTHOLE_MODEL)
        if not os.path.isdir(model):   # development checkout: the training run's export
            model = os.path.join(here, "training", "runs", "run2_sa_band_tiles_640", DEFAULT_POTHOLE_MODEL)
    elif not os.path.isabs(model):
        model = os.path.join(here, model)
    band = pick(args.pothole_band, "pothole_band", (0.42, 0.68))
    band = tuple(float(v) for v in (band.split(",") if isinstance(band, str) else band))
    if len(band) != 2 or not 0.0 <= band[0] < band[1] <= 1.0:
        raise ValueError("pothole band must be TOP,BOTTOM with 0 <= TOP < BOTTOM <= 1")
    return {"enabled": enabled, "model": model, "band": band,
            "threads": int(pick(args.pothole_threads, "pothole_threads", 1)),
            "reserve_core": bool(opts.get("pothole_reserve_core", False)),
            "rate": float(pick(args.pothole_rate, "pothole_rate", POTHOLE_RATE_DEFAULT_HZ)),
            "conf": float(pick(args.pothole_conf, "pothole_conf", 0.5))}


def still_image_camera(path, width, height):
    """A stand-in for Picamera2 that returns one saved picture, resized to
    width x height, at about 15 fps, stored B, G, R like Picamera2's
    "RGB888". For pipeline tests without the camera; the picture is only
    read, never written."""
    from PIL import Image
    rgb = np.asarray(Image.open(path).convert("RGB").resize((width, height), Image.BILINEAR))
    bgr = np.ascontiguousarray(rgb[..., ::-1])

    class _Request:
        def __init__(self):
            self.ts = time.monotonic_ns()

        def make_array(self, name):
            return bgr.copy()

        def get_metadata(self):
            return {"SensorTimestamp": self.ts}

        def release(self):
            pass

    class StillCamera:
        def __init__(self, *a, **k):
            self.next_t = time.monotonic()

        def create_preview_configuration(self, main):
            return main

        def configure(self, c):
            pass

        def start(self):
            print(f"Test image instead of the camera: {path}")

        def stop(self):
            pass

        def set_controls(self, c):
            pass

        def capture_request(self):
            self.next_t += 1 / 15.0
            delay = self.next_t - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            else:
                self.next_t = time.monotonic()
            return _Request()

    return StillCamera


def np_resize(frame, width, height):
    # Stretch the whole frame to the model's input size (300x300 for this
    # SSD-MobileNet-v1), so box coordinates map straight back onto the full
    # frame. Bilinear rather than Pillow's bicubic default: cheaper, and the
    # usual choice for this model's preprocessing. Avoids an OpenCV dependency.
    from PIL import Image
    img = Image.fromarray(frame)
    img = img.resize((width, height), Image.BILINEAR)
    return np.array(img)


if __name__ == "__main__":
    main()
