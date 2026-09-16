# Camera hazard/obstacle detection (Pi 4)

## What this actually is

A pretrained, COCO-trained SSD-MobileNet-v1 object detector (quantized
TFLite, `detect.tflite` + `labelmap.txt`, no custom training), run on
live frames from the Pi 4's camera via `hazard_detector.py`. It reports
which road-relevant COCO classes (person, bicycle, car, motorcycle, bus,
truck, dog, traffic light, stop sign, fire hydrant) are visible, each
with a rough distance estimate from a known-object-width heuristic.

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

Not yet run against the real camera - written and prepared while the Pi
was unreachable (not powered on / not on the network at the time). Model
file verified as a genuine, complete TFLite archive (not a corrupted or
truncated download). Needs, in order: (1) a real run to confirm frame
rate is usable, (2) focal-length calibration, (3) a decision on whether
"hazard" for this project means road-surface defects specifically or
general object presence - raised with the supervisor separately, not yet
answered.
