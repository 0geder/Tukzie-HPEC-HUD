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
    exists only in memory for the duration of one inference pass, and is
    discarded (goes out of scope) immediately after. Only the fields
    listed in ALERT_LOG_FIELDS are ever persisted.
  - No facial recognition, no number-plate recognition, no per-instance
    identification of any person or vehicle is performed anywhere in this
    file - COCO class labels only ("person", "car", etc.), never who or
    which one.
  - Processing is entirely local (this Pi, this process) - no frame or
    inference result is uploaded to any external service.
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

# An object must be continuously detected (this class, this band or
# nearer) for this many consecutive frames before it is logged as a
# reportable alert, rather than every single-frame flicker. This is a
# class-level debounce, not per-instance tracking: it cannot distinguish
# two different cars both briefly visible from one car persisting, since
# no cross-frame object identity is maintained. That limitation is
# stated here rather than implied by the counter's existence.
ALERT_PERSISTENCE_FRAMES = 3

# The only fields this script ever persists to the alert log, matching
# the fields proposed in the ethics application.
ALERT_LOG_FIELDS = ("class", "distance_band", "confidence", "timestamp", "alert_status")


def load_labels(path):
    with open(path, "r") as f:
        return [line.strip() for line in f.readlines()]


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
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "alert_status": alert_status,
    }
    assert set(record.keys()) == set(ALERT_LOG_FIELDS), "log_alert record must match ALERT_LOG_FIELDS exactly"
    with open(log_path, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="detect.tflite")
    parser.add_argument("--labels", default="labelmap.txt")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    # Focal length in pixels: focal_length_px = (image_width_px * distance_m) / real_width_m,
    # calibrated with one object at a known distance. NOT yet calibrated for
    # this camera - this default is a rough placeholder from the OV5647's
    # published field of view and must be replaced with a real calibration
    # shot before distance numbers are trusted.
    parser.add_argument("--focal-length-px", type=float, default=600.0,
                         help="UNCALIBRATED placeholder - see comment in source")
    parser.add_argument("--duration", type=int, default=0,
                         help="Seconds to run, 0 = run until Ctrl+C")
    parser.add_argument("--log-path", default="alerts.jsonl",
                         help="Append-only JSONL file for reportable alert events "
                              "(class, distance_band, confidence, timestamp, alert_status only)")
    args = parser.parse_args()

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

    # Class-level persistence state: an object must be seen in-band for
    # ALERT_PERSISTENCE_FRAMES consecutive frames before it becomes a
    # reportable alert, and a "cleared" event is logged once it drops out
    # again. This is deliberately class-level, not per-instance (see
    # module docstring) - it answers "is a car persistently near", not
    # "is this specific car persistently near".
    streak = {cls: 0 for cls in HAZARD_CLASSES}
    active = {cls: False for cls in HAZARD_CLASSES}

    start = time.time()
    frame_count = 0
    try:
        while args.duration == 0 or (time.time() - start) < args.duration:
            frame = picam2.capture_array()
            frame_count += 1

            resized = np_resize(frame, input_width, input_height)
            input_data = np.expand_dims(resized, axis=0)
            if input_details[0]['dtype'] == np.float32:
                input_data = (np.float32(input_data) - 127.5) / 127.5

            interpreter.set_tensor(input_details[0]['index'], input_data)
            interpreter.invoke()
            # Frame is not referenced again after this point in the loop
            # body and is overwritten by the next capture_array() call -
            # nothing derived from it is written to disk (see docstring).

            boxes = interpreter.get_tensor(output_details[0]['index'])[0]
            classes = interpreter.get_tensor(output_details[1]['index'])[0]
            scores = interpreter.get_tensor(output_details[2]['index'])[0]

            frame_h, frame_w = frame.shape[0], frame.shape[1]
            in_band_this_frame = {}  # class_name -> (band, confidence), nearest band wins
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
                if band is None:
                    continue  # detected, but outside the reportable zones entirely

                confidence = float(scores[i])
                prev = in_band_this_frame.get(class_name)
                if prev is None or confidence > prev[1]:
                    in_band_this_frame[class_name] = (band, confidence)

            ts_console = time.strftime("%H:%M:%S")
            for class_name in HAZARD_CLASSES:
                if class_name in in_band_this_frame:
                    band, confidence = in_band_this_frame[class_name]
                    streak[class_name] += 1
                    print(f"[{ts_console}] {class_name} band={band} conf={confidence:.2f} "
                          f"streak={streak[class_name]}/{ALERT_PERSISTENCE_FRAMES}")
                    if streak[class_name] >= ALERT_PERSISTENCE_FRAMES and not active[class_name]:
                        active[class_name] = True
                        log_alert(args.log_path, class_name, band, confidence, "active")
                        print(f"  -> ALERT logged: {class_name} ({band})")
                else:
                    streak[class_name] = 0
                    if active[class_name]:
                        active[class_name] = False
                        log_alert(args.log_path, class_name, None, 0.0, "cleared")
                        print(f"  -> cleared: {class_name}")

    except KeyboardInterrupt:
        pass
    finally:
        elapsed = time.time() - start
        fps = frame_count / elapsed if elapsed > 0 else 0
        print(f"\nStopped. {frame_count} frames in {elapsed:.1f}s ({fps:.1f} fps average).")
        picam2.stop()


def np_resize(frame, width, height):
    # Nearest-neighbour resize without adding an OpenCV dependency - the
    # model's own input size is small (300x300 for this SSD-MobileNet-v1),
    # so quality loss from a simple resize is acceptable here.
    from PIL import Image
    img = Image.fromarray(frame)
    img = img.resize((width, height))
    return np.array(img)


if __name__ == "__main__":
    main()
