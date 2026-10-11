#!/usr/bin/env python3
"""
SW-7 hazard/obstacle detector for the Pi 4 camera.

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
blind-spot geometry, does NOT track individual objects across frames
(the persistence check below is class-level, not per-instance), and does
NOT constitute an autonomous-driving perception stack - it is a
hazard-presence-and-rough-range indicator, sized to what a Pi 4 with no
hardware accelerator can actually sustain in real time.

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

Time-to-collision (TTC = distance / closing_speed) is only computed if a
vehicle speed is supplied externally (e.g. from the ESP32's GNSS speed
field) - that field's units are not yet confirmed (see Methodology.tex,
GNSS section), so TTC output is clearly marked provisional whenever shown.

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
    "person": 0.5,
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
# no cross-frame object identity is maintained. That limitation is
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

    def set_alerts(self, active, fps, latency_ms, road_hazards=None):
        """Publish the currently active alerts for GET /alerts. Same five
        fields as the alert log, nothing else about the scene. With the
        pothole path on, "road_hazards" lists the active experimental
        pothole alerts (a new key, so readers of "active" are unaffected)."""
        d = {
            "active": active,
            "fps": round(fps, 1),
            "latency_ms": None if latency_ms is None else round(latency_ms),
        }
        if road_hazards is not None:
            d["road_hazards"] = road_hazards
        body = json.dumps(d).encode()
        with self._lock:
            self._alerts_json = body

    def set_detections(self, detections, frame_t_mono, fps, hfov_deg=DEFAULT_HFOV_DEG,
                       road_hazards=None, road_hazards_meta=None):
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
    print(f"Alert log (class/band/confidence/timestamp/status only): {args.log_path}")

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
            in_band_this_frame = {}  # class_name -> (band, confidence, bbox_px); nearest band wins, then confidence
            drawn = []  # detections for the live view only, never logged
            frame_dets = []  # for GET /detections only (served, never logged)
            for i in range(len(scores)):
                if scores[i] < CONFIDENCE_THRESHOLD:
                    continue
                class_id = int(classes[i])
                if class_id >= len(labels):
                    continue
                class_name = labels[class_id]
                if class_name not in HAZARD_CLASSES:
                    continue

                ymin, xmin, ymax, xmax = boxes[i]
                bbox_width_px = (xmax - xmin) * frame_w
                distance_m = estimate_distance_m(class_name, bbox_width_px, args.focal_length_px)
                band = distance_band(distance_m)
                if preview is not None:
                    frame_dets.append(detection_record(class_name, scores[i], boxes[i], frame_w,
                                                       args.focal_length_px, args.hfov_deg))
                    drawn.append({
                        "box": (int(xmin * frame_w), int(ymin * frame_h), int(xmax * frame_w), int(ymax * frame_h)),
                        "class": class_name, "confidence": float(scores[i]),
                        "distance_m": distance_m, "band": band,
                    })
                if band is None:
                    continue  # detected, but outside the reportable zones entirely

                confidence = float(scores[i])
                prev = in_band_this_frame.get(class_name)
                if (prev is None or BAND_RANK[band] < BAND_RANK[prev[0]]
                        or (band == prev[0] and confidence > prev[1])):
                    in_band_this_frame[class_name] = (band, confidence, bbox_width_px)

            ts_console = time.strftime("%H:%M:%S")
            for class_name in HAZARD_CLASSES:
                if class_name in in_band_this_frame:
                    band, confidence, bbox_px = in_band_this_frame[class_name]
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
                            missed[class_name] = 0
                            log_alert(args.log_path, class_name, None, 0.0, "cleared")
                            print(f"[{ts_console}] cleared: {class_name}")

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
                preview.set_alerts(sorted(active_record.values(),
                                          key=lambda r: BAND_RANK.get(r["distance_band"], 9)),
                                   fps_now, total_ms if sensor_ns else None, **alert_extra)
                frame_t = (sensor_ns if sensor_ns else t_got) / 1e9
                preview.set_detections(frame_dets, frame_t, fps_now, args.hfov_deg, **det_extra)

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
