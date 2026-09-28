# Camera hazard/obstacle detection (Pi 4)

## Ethics status

Runs under ethics approval **EBE/03305/2026** (approved with conditions,
23 Sep 2026 - 22 Sep 2027, EBE Faculty Research Ethics Committee). The
approval's conditions are enforced in code, not just documented:
category list restricted to what the application proposed, raw frames never written
to disk, only class/distance-band/confidence/timestamp/alert-status ever
logged, no facial or number-plate recognition, no actuator output. See
the module docstring in `hazard_detector.py` for the full list and where
each condition is enforced. Any change to camera location, field of
view, retention, model, or alert method requires a further ethics review
before it is made, not just a code change.

## What this actually is

A pretrained, COCO-trained SSD-MobileNet-v1 object detector (quantized
TFLite, `detect.tflite` + `labelmap.txt`, no custom training), run on
live frames from the Pi 4's camera via `hazard_detector.py`. It reports
which road-relevant COCO classes are visible - restricted to the
categories proposed in the ethics application (person, bicycle, car,
motorcycle, bus, truck, dog), each with a rough distance estimate from a
known-object-width heuristic. Earlier versions also reported traffic
light/stop sign/fire hydrant; those are not in the application's
category list and have been removed.

An object class must be detected within any reportable distance band
for `ALERT_PERSISTENCE_FRAMES` (default 3) consecutive frames before it
is logged as an alert, rather than every single-frame flicker. Once
active, it is re-logged if it holds a nearer band for the same 3 frames,
and it clears only after `CLEAR_AFTER_MISSED_FRAMES` (default 5)
consecutive frames without it, so detections hovering near the
confidence threshold do not toggle the alert on and off. Only five
fields are ever written to the alert log (`alerts.jsonl` by default):
object class, distance band (`immediate`/`warning`/`monitoring`),
detection confidence, timestamp (with UTC offset), and alert status
(`active`/`cleared`). No frame, bounding box, or raw continuous distance
value is ever persisted.

## What this is not

Not lane-level blind-spot geometry, not multi-frame object tracking, not
an autonomous-driving perception stack. Chosen deliberately to match what
a Raspberry Pi 4 with no hardware ML accelerator can actually sustain in
real time - a hazard-presence-and-rough-range indicator, not a precision
ranging or decision-making system.

## Distance estimate: read this before trusting a number

Distance uses `distance_m = (real_object_width_m * focal_length_px) / bbox_width_px`.
Two things this depends on that are **not yet done**:

1. **`--focal-length-px` is currently an uncalibrated placeholder** (600px
   default). Calibrate it properly with one object of known width at a
   known distance before trusting any reported number: `focal_length_px =
   (bbox_width_px * distance_m) / real_object_width_m`.
2. Each class uses one fixed average real-world width (e.g. 1.8m for a
   car). A car is not 1.8m wide from every angle - this is an
   order-of-magnitude estimate, not a measurement.

## Deploying

From the `Tukzie-HPEC-HUD` folder on the development machine, copy the
three files to the Pi (the Pi is `pi4-camera`; use its IP, from
`hostname -I` on the Pi, where `.local` names do not resolve):

```
ssh -i ~/.ssh/pi4_camera_key ogeder@<pi-ip> "mkdir -p ~/hazard_detector"
scp -i ~/.ssh/pi4_camera_key CameraDetection/hazard_detector.py CameraDetection/detect.tflite CameraDetection/labelmap.txt ogeder@<pi-ip>:~/hazard_detector/
```

On the Pi, once. Pi OS Trixie runs Python 3.13, for which `tflite-runtime`
has no wheels, so the LiteRT package (`ai-edge-litert`, its successor)
is used, in a venv that can still see the system `picamera2`:

```
cd ~/hazard_detector
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install ai-edge-litert
```

Run (in each new terminal, `source venv/bin/activate` first):

```
python3 hazard_detector.py --duration 60              # fixed run
python3 hazard_detector.py --preview                  # live view at http://localhost:8080 on the Pi
python3 hazard_detector.py --preview --preview-host 0.0.0.0   # live view from another device: http://<pi-ip>:8080
```

The live view draws the model's detections (class, confidence,
estimated distance, band) on the camera image. It is served over plain,
unauthenticated HTTP and never saved. With `--preview-host 0.0.0.0`
anyone on the same network can open it, so use that only on a private
network such as a phone hotspot.

## Status

First run against the live camera on the bench on 28 September 2026
(Raspberry Pi 4, OV5647 at 640x480, LiteRT): about 7 frames per second
(430 frames and 419 frames in two 60 s runs).

- The first run exposed two input faults, both fixed: the label file's
  leading `???` placeholder shifted every class name by one (a person in
  view was never reported), and Picamera2's `RGB888` buffers are stored
  B, G, R (Picamera2 manual, Image Formats) while the model expects
  R, G, B. After both fixes a person in view was detected with
  confidence 0.50 to 0.73. The two fixes went in together, so their
  individual effects were not separated.
- The same run showed an alert clearing on one missed frame (16
  activations in 47 s for one person standing in view). Clear-side
  hysteresis and escalation debounce were added afterwards and tested
  offline against a replayed detection sequence, not yet on the Pi.
- Only `person` has been confirmed on live frames. The other six classes
  are untested.
- Outstanding, in order: focal-length calibration (the console now
  prints `bbox_width_px` per detection for this; 600 px is a placeholder,
  and about 643 px would be expected from the Camera Module v1 lens
  spec), an outdoor and on-vehicle test, and a decision on whether
  "hazard" means road-surface defects or general object presence.
