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

An object must be detected continuously for `ALERT_PERSISTENCE_FRAMES`
(default 3) consecutive frames within a reportable distance band before
it is logged as an alert, rather than every single-frame flicker. Only
five fields are ever written to the alert log (`alerts.jsonl` by
default): object class, distance band (`immediate`/`warning`/
`monitoring`), detection confidence, timestamp, and alert status
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

From the scratchpad (or wherever this was prepared on the development
machine): `python pi_deploy_hazard_detector.py` copies `hazard_detector.py`,
`detect.tflite`, and `labelmap.txt` to `/home/ogeder/hazard_detector/` on
the Pi and checks whether `tflite_runtime`, `picamera2`, and `PIL` are
already installed there.

Run on the Pi: `python3 hazard_detector.py` (add `--duration 30` to run
for a fixed window instead of until Ctrl+C).

## Status

Not yet run against the real camera - the ethics-conditioned category
restriction, distance banding, persistence debounce, and structured
alert logger described above are all implemented and syntax-checked,
but have not yet been exercised against live frames on the Pi. Model
file verified as a genuine, complete TFLite archive (not a corrupted or
truncated download). Needs, in order: (1) a real run to confirm frame
rate is usable and the alert log fills in as expected, (2) focal-length
calibration, (3) a decision on whether "hazard" for this project means
road-surface defects specifically or general object presence - raised
with the supervisor separately, not yet answered.
