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

Not lane-level blind-spot geometry, not an autonomous-driving perception
stack (the object tracking below is a short-lived box-overlap tracker for
the approaching warning, nothing more). Chosen deliberately to match what
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

From the repository root on the development machine, copy the
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

With `--preview` the same server also answers `GET /alerts` with the
currently active alerts as JSON (the same five fields as the log, plus
frame rate and sensor-to-result latency), for the dashboard's Front camera
page (`../DashboardIntegration/`). Every 5 s the console prints a
`[timing]` line with p50, p95 and max per stage; `--timing-log file.csv`
keeps per-frame timings, `--threads` sets inference threads (default 4),
`--tuning ov5647_noir.json` loads the tuning for a camera with no infrared
filter, and `--verbose` prints every detection.

To start it at boot and restart it on failure, see `deploy/INSTALL.md`.

## Approaching objects (time to contact)

Warns of something closing fast, such as a car coming up from behind or
an object ahead, from either camera. The same detector runs on the Pi 5
(front, about 19 fps) and the Pi 4 (rear, about 14.7 fps); `--side
front|rear`, or `{"side": "rear"}` in `detector_options.json` (default
front), says which, and is echoed in `/alerts` and `/detections`.

- Tracking: each detection gets a `track_id` from a box-overlap (IoU)
  tracker that survives up to 2 missed frames. Ids count up from 1 at
  start-up and identify no person or vehicle.
- Time to contact from box growth (Lee's tau): TTC = w / (dw/dt), from a
  robust line fit of 1/width against the frames' sensor timestamps over
  the last 0.6 s. Valid only with at least 5 frames over 0.25 s,
  consistent growth, at least 5 % growth, no box cut by the left or right
  image edge, and the height agreeing within a factor 2 when not cut at
  the top or bottom. It needs no focal length. `closing_mps`, the slope
  of the pinhole distance estimate, does, and is uncalibrated like the
  distance.
- Alert: TTC under 4 s is `warning`, under 2 s `immediate`, after 3
  frames; it holds until the TTC is above 5 s (2.5 s for immediate) or
  invalid for 5 frames. The distance alerts are unchanged; an approaching
  track raises its class's band when more urgent, and one with no
  distance alert (a car beyond 15 m) gets its own `/alerts` entry.
  Earliest alert after an object first appears: its 8th frame at 19 fps
  (0.37 s) or 7th at 14.7 fps (0.41 s), plus the pipeline latency.
- Ego motion: with the trike moving forward, still objects ahead grow in
  the front camera and are reported as approaching. That is intended (a
  forward collision warning); at the rear only objects closing faster
  than the trike are reported.
- Constants (thresholds, window, hysteresis) are at the top of the
  "Approaching objects" section of `hazard_detector.py`, each commented.

Schema, additive (existing fields unchanged). Each `/alerts` `active`
entry and each `/detections` `detections` entry gains:

```
"side": "front" | "rear",
"track_id": 3,
"approaching": true,         # alert state, with the hysteresis above
"ttc_s": 2.41,               # this frame's TTC, null when not valid
"closing_mps": 4.8           # positive = nearer; uncalibrated, null with too few frames
```

and both responses gain a top-level `"side"`. The telemetry bridge's fused
hazards (`sensor_fusion.py` rule 6) gain `ttc_s`, `closing_mps`,
`approaching`, `side` and `ttc_source` (`"tof"`, `"camera"` or null): the
ToF closing rate (robust fit over 0.3 s, nulls and out-of-range readings
left out) is used inside ToF range when camera and ToF agree on bearing,
the camera's TTC beyond it. The bridge takes `--side front|rear`; without
it the side the detector reports is used.

Logging: approaching alerts are logged to the same alert log with the five
fields plus `"approaching": true`, `track_id`, `ttc_s` (0.1 s) and `side`;
distance-alert lines are unchanged. This, and the new alert itself, is a
change to the logged fields and the alert method, so it needs the ethics
review described above before field use.

Status (15 Oct 2026): tested offline only (`tests/test_approach.py`, 40
tests, synthetic box sequences and ToF histories; the existing tests
still pass). Added cost on the laptop with six objects in view: median
0.28 ms, p95 0.46 ms a frame. Not yet run on either Pi, nor against real
approaches; the accuracy test is BenchTest C11.

## Experimental pothole path (off by default)

`pothole_detector.py` runs the run-2 YOLO11n pothole model (NCNN, 320 input, folder
`yolo11n_sa_band_tiles_320_ncnn_model` next to the detector, ncnn installed in the venv) on the
road band it was trained on, 42 to 68 % of the frame height cut into three tiles, in a separate
low-priority process. Turn it on with `--potholes on` or `{"potholes": true}` in
`detector_options.json`. Results appear only under new keys, `road_hazards` and
`road_hazards_meta` in `/detections` and `road_hazards` in `/alerts`, each marked
`"experimental": true`; a pothole alert needs potholes in 2 of the last 3 runs (confidence 0.5 or
more) and is logged with the same five fields (class `pothole`, band null).

It is off because it does not fit next to the main detector on the Pi 4: only at 0.25 runs per
second (its default rate) did the main detector stay within 10 % (13.9 against 14.6 fps); at 1 Hz
it fell to 12 fps. Measurements and limits: `../Planning/pothole-integration-prompt.md` and
BenchTest C10. `--test-image PATH` replaces the camera with a saved picture for checks without
driving. Adding a model and an alert class is a change the ethics conditions above ask to be
reviewed before field use.

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
