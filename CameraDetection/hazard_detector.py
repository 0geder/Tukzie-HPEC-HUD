#!/usr/bin/env python3
"""
SW-7 hazard/obstacle detector for the Pi 4 camera.

Scope, stated honestly: this runs a pretrained, COCO-trained SSD-MobileNet-v1
object detector (quantized TFLite, no NPU required) on live camera frames,
and reports which of a small set of road-relevant classes are present, with
a *rough* distance estimate from a known-object-width heuristic. It does
NOT do lane-level blind-spot geometry, does NOT track objects across frames,
and does NOT constitute an autonomous-driving perception stack - it is a
hazard-presence-and-rough-range indicator, sized to what a Pi 4 with no
hardware accelerator can actually sustain in real time.

Distance estimate uses the pinhole-camera relationship:
    distance_m = (real_object_width_m * focal_length_px) / bbox_width_px
This is an estimate, not a measurement: it assumes the object is roughly
front-on to the camera and uses one average real-world width per class
(a car is not always 1.8m wide from every angle). Treat the reported
distance as "same order of magnitude", not precise ranging.

Time-to-collision (TTC = distance / closing_speed) is only computed if a
vehicle speed is supplied externally (e.g. from the ESP32's GNSS speed
field) - that field's units are not yet confirmed (see Methodology.tex,
GNSS section), so TTC output is clearly marked provisional whenever shown.
"""
import argparse
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

# Road-relevant subset of COCO's 90 classes - everything else detected is
# ignored for hazard reporting (COCO also includes e.g. "toothbrush",
# "kite", which are not road hazards).
HAZARD_CLASSES = set(KNOWN_WIDTHS_M.keys()) | {"traffic light", "stop sign", "fire hydrant"}

CONFIDENCE_THRESHOLD = 0.5


def load_labels(path):
    with open(path, "r") as f:
        return [line.strip() for line in f.readlines()]


def estimate_distance_m(class_name, bbox_width_px, focal_length_px):
    real_width = KNOWN_WIDTHS_M.get(class_name)
    if real_width is None or bbox_width_px <= 0:
        return None
    return (real_width * focal_length_px) / bbox_width_px


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

            boxes = interpreter.get_tensor(output_details[0]['index'])[0]
            classes = interpreter.get_tensor(output_details[1]['index'])[0]
            scores = interpreter.get_tensor(output_details[2]['index'])[0]

            frame_h, frame_w = frame.shape[0], frame.shape[1]
            detections_this_frame = []
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

                detections_this_frame.append({
                    "class": class_name,
                    "confidence": float(scores[i]),
                    "bbox_norm": [float(xmin), float(ymin), float(xmax), float(ymax)],
                    "distance_m_estimate": distance_m,
                })

            if detections_this_frame:
                ts = time.strftime("%H:%M:%S")
                for d in detections_this_frame:
                    dist_str = f"~{d['distance_m_estimate']:.1f}m" if d['distance_m_estimate'] else "distance n/a"
                    print(f"[{ts}] {d['class']} (conf={d['confidence']:.2f}) {dist_str}")

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
