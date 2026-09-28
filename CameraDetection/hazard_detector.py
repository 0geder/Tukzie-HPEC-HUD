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

Time-to-collision (TTC = distance / closing_speed) is only computed if a
vehicle speed is supplied externally (e.g. from the ESP32's GNSS speed
field) - that field's units are not yet confirmed (see Methodology.tex,
GNSS section), so TTC output is clearly marked provisional whenever shown.
"""
import argparse
import json
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
    devices on the same local network (still never saved or uploaded)."""

    def __init__(self, port, host="127.0.0.1"):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        self._lock = threading.Condition()
        self._jpeg = None
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
                elif self.path == "/stream":
                    self.send_response(200)
                    self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                    self.end_headers()
                    try:
                        while True:
                            with server._lock:
                                server._lock.wait(timeout=2)
                                jpeg = server._jpeg
                            if jpeg is None:
                                continue
                            self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                            self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode())
                            self.wfile.write(jpeg + b"\r\n")
                    except OSError:
                        pass  # viewer closed the page or the connection dropped
                else:
                    self.send_error(404)

        self._httpd = ThreadingHTTPServer((host, port), Handler)
        self._httpd.daemon_threads = True
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()

    def publish(self, rgb_frame, detections, fps):
        import io
        from PIL import Image, ImageDraw
        img = Image.fromarray(rgb_frame)
        draw = ImageDraw.Draw(img)
        for d in detections:
            colour = BAND_COLOURS.get(d["band"], (150, 150, 150))
            draw.rectangle(d["box"], outline=colour, width=3)
            dist = f"{d['distance_m']:.1f}m" if d["distance_m"] is not None else "?"
            label = f"{d['class']} {d['confidence']:.2f} {dist} {d['band'] or 'out of range'}"
            x, y = d["box"][0], max(0, d["box"][1] - 14)
            draw.rectangle((x, y, x + 7 * len(label), y + 14), fill=colour)
            draw.text((x + 2, y + 1), label, fill=(0, 0, 0))
        draw.text((6, 6), f"{fps:.1f} fps", fill=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        with self._lock:
            self._jpeg = buf.getvalue()
            self._lock.notify_all()

    def close(self):
        self._httpd.shutdown()
        self._httpd.server_close()


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

    from picamera2 import Picamera2

    labels = load_labels(args.labels)
    interpreter = Interpreter(model_path=args.model)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    input_height = input_details[0]['shape'][1]
    input_width = input_details[0]['shape'][2]

    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(
        main={"size": (args.width, args.height), "format": "RGB888"}))
    picam2.start()

    print(f"Model loaded: {args.model} (input {input_width}x{input_height})")
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

    preview = None
    start = time.monotonic()
    frame_count = 0
    try:
        if args.preview:
            preview = PreviewServer(args.preview_port, args.preview_host)
            if args.preview_host == "127.0.0.1":
                print(f"Live view: open http://localhost:{args.preview_port} in this Pi's browser")
            else:
                print(f"Live view: open http://<this Pi's IP>:{args.preview_port} from a device on the same network "
                      f"(hostname -I shows the IP)")
        start = time.monotonic()
        while args.duration == 0 or (time.monotonic() - start) < args.duration:
            frame = picam2.capture_array()
            frame_count += 1

            # Picamera2's "RGB888" is stored B, G, R; the model expects R, G, B.
            rgb = np.ascontiguousarray(frame[..., ::-1])
            resized = np_resize(rgb, input_width, input_height)
            input_data = np.expand_dims(resized, axis=0)
            if input_details[0]['dtype'] == np.float32:
                input_data = (np.float32(input_data) - 127.5) / 127.5

            interpreter.set_tensor(input_details[0]['index'], input_data)
            interpreter.invoke()
            # The frame (and rgb, if the preview is on) is replaced by the next
            # capture_array() call. Nothing derived from it is written to disk
            # (see docstring).

            boxes = interpreter.get_tensor(output_details[0]['index'])[0]
            classes = interpreter.get_tensor(output_details[1]['index'])[0]
            scores = interpreter.get_tensor(output_details[2]['index'])[0]

            frame_h, frame_w = frame.shape[0], frame.shape[1]
            in_band_this_frame = {}  # class_name -> (band, confidence, bbox_px); nearest band wins, then confidence
            drawn = []  # detections for the live view only, never logged
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

            if preview is not None:
                elapsed_now = time.monotonic() - start
                preview.publish(rgb, drawn, frame_count / elapsed_now if elapsed_now > 0 else 0.0)

            ts_console = time.strftime("%H:%M:%S")
            for class_name in HAZARD_CLASSES:
                if class_name in in_band_this_frame:
                    band, confidence, bbox_px = in_band_this_frame[class_name]
                    streak[class_name] += 1
                    missed[class_name] = 0
                    print(f"[{ts_console}] {class_name} band={band} conf={confidence:.2f} "
                          f"bbox_width_px={bbox_px:.0f} streak={streak[class_name]}/{ALERT_PERSISTENCE_FRAMES}")
                    current = active_band[class_name]
                    if current is None and streak[class_name] >= ALERT_PERSISTENCE_FRAMES:
                        active_band[class_name] = band
                        log_alert(args.log_path, class_name, band, confidence, "active")
                        print(f"  -> ALERT logged: {class_name} ({band})")
                    elif current is not None and BAND_RANK[band] < BAND_RANK[current]:
                        # Nearer than the logged band: re-log once it has held for
                        # the same debounce as an onset, so one noisy frame can't escalate.
                        nearer[class_name] += 1
                        if nearer[class_name] >= ALERT_PERSISTENCE_FRAMES:
                            nearer[class_name] = 0
                            active_band[class_name] = band
                            log_alert(args.log_path, class_name, band, confidence, "active")
                            print(f"  -> ALERT escalated: {class_name} ({current} -> {band})")
                    else:
                        nearer[class_name] = 0
                else:
                    streak[class_name] = 0
                    nearer[class_name] = 0
                    if active_band[class_name] is not None:
                        missed[class_name] += 1
                        if missed[class_name] >= CLEAR_AFTER_MISSED_FRAMES:
                            active_band[class_name] = None
                            missed[class_name] = 0
                            log_alert(args.log_path, class_name, None, 0.0, "cleared")
                            print(f"  -> cleared: {class_name}")

    except KeyboardInterrupt:
        pass
    finally:
        elapsed = time.monotonic() - start
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"\nStopped. {frame_count} frames in {elapsed:.1f}s ({fps:.1f} fps average).")
        picam2.stop()
        if preview is not None:
            preview.close()


def np_resize(frame, width, height):
    # Stretch the whole frame to the model's input size (300x300 for this
    # SSD-MobileNet-v1) with Pillow's default bicubic resize, so box
    # coordinates map straight back onto the full frame. Avoids adding an
    # OpenCV dependency.
    from PIL import Image
    img = Image.fromarray(frame)
    img = img.resize((width, height))
    return np.array(img)


if __name__ == "__main__":
    main()
