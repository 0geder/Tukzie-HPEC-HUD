# Camera integration prompt (SW-7, next phase)

Historical: written before the HUD was replaced by dashboard integration on 2 Oct 2026.

Written 2026-09-28. Paste everything below the line into a new session, or
say "act on the camera integration prompt".

---

You are continuing the camera work on SW-7 (UCT EEE4022S 2026, Samson
Okuthe, supervisor A/Prof. Simon Winberg): a Raspberry Pi 4 camera
(`pi4-camera`, OV5647, Pi OS Trixie, Python 3.13) running
`CameraDetection/hazard_detector.py`, a pretrained COCO SSD-MobileNet-v1
(8-bit, LiteRT via `ai-edge-litert` in `~/hazard_detector/venv`) that
reports person, bicycle, car, motorcycle, bus, truck and dog in three
distance bands. The repo is `Tukzie-HPEC-HUD`. The Pi is reached from the
laptop with `ssh -i ~/.ssh/pi4_camera_key ogeder@<pi-ip>` (on the phone
hotspot it was 10.84.114.244; `hostname -I` on the Pi confirms it).
Commands the student runs are given as copy-paste blocks, laptop and Pi
clearly separated, and also kept current on the Camera Test Runbook page
(https://claude.ai/artifact/3dF7PdCeyP6256ChTkPrJU), whose Send box stores
Pi output you can read back with ArtifactData (collection `outputs`).

Already verified on 28 September 2026 (do not redo, build on it):
- First live runs: about 7 fps at 640x480. Label-offset and B,G,R colour
  order fixes are confirmed against the model file, the TensorFlow example
  source and the Picamera2 manual (p. 21: RGB888 is ordered [B, G, R]).
- Only "person" is confirmed on live frames (confidence 0.50 to 0.73).
- Alert hysteresis (clear after 5 missed frames, 3-frame onset and
  escalation debounce) is tested offline only.
- The live view (`--preview`, `--preview-host 0.0.0.0`) runs in its own
  thread; `[timing]` lines give p50/p95/max per stage using the frame's
  SensorTimestamp (ns since boot, same clock as time.monotonic_ns);
  `--timing-log` writes a per-frame CSV; `--threads` (default 4);
  `--tuning` loads a camera tuning file.
- Focal length is an uncalibrated 600 px placeholder (about 643 px is
  expected from the Camera Module v1 lens spec).

Rules:
- Nothing may be wrong. Check every claim against a primary source or a
  measurement, say when something is unverified, and never invent results,
  numbers, papers or URLs. Report failures and odd results as found.
- Writing: no em dashes, no unnecessary bold, in chat, code comments,
  README, runbook and report.
- In the report, describe what was done and measured; do not mention the
  ethics application or its approval.
- Frames are never written to disk by the detector. Colour-check stills
  are taken separately with rpicam-still, only of an object or colour card
  with no people in view, and deleted after checking.
- Commit locally with no Co-Authored-By line. Ask before pushing.
- Items that need the supervisor first are listed at the end: prepare
  them, do not implement them.

Work through these phases in order. For each, state the acceptance check,
run or hand over the test, and record the result.

## A. Colour check (the live view looks reddish)
1. Channel order: hold a strongly blue object in view in the live view.
   Blue shown as blue means the order is right; blue shown as orange or
   red means it is swapped.
2. Our code or the camera: compare the live view with the Pi's own
   preview (`rpicam-hello -t 0` on the Pi's monitor, detector stopped).
   If both are reddish, the cause is the camera or its tuning, not the
   detector.
3. Infrared: a pink or red cast on skin, plants and white paper in
   daylight is typical of a module with no infrared-cut filter (NoIR).
   Try `rpicam-hello -t 0 --tuning-file /usr/share/libcamera/ipa/rpi/vc4/ov5647_noir.json`.
   If that looks right, run the detector with `--tuning ov5647_noir.json`
   and record it as the camera's configuration. Confirm the file name
   exists with `ls /usr/share/libcamera/ipa/rpi/vc4/`.
4. White balance: a sheet of white paper should look neutral grey or
   white. Note indoor versus outdoor light.
5. Re-measure person confidence before and after, same position and
   light, so the effect of colour on detection is quantified, not assumed.

## B. Detection coverage, including bicycles
1. Protocol with a tape measure: for each class available (person and
   bicycle first, then car, motorcycle and others in the parking lot),
   record detected yes/no, confidence and `bbox_width_px` (`--verbose`)
   at 2, 4, 6, 8, 10 and 15 m, facing the camera and side-on.
2. Bicycle distance: KNOWN_WIDTHS_M uses 0.6 m, a front-on width. Side-on
   a bicycle is about 1.7 m long, so its distance would read about a third
   of the true value. Measure it, then decide with the student between an
   aspect-ratio-aware width or reporting the limitation.
3. Record the farthest reliable detection per class and the false
   positives seen (class, confidence, what was actually there).
4. Result goes in the report as a table: class, orientation, distance,
   detected, confidence.

## C. Latency against a stated target
1. From the `[timing]` lines and CSVs: preview off versus on, threads 1, 2
   and 4. Report p50, p95 and max for each stage and sensor-to-result.
2. Propose a target from first principles and the brief (real-time edge
   processing, no blocking): for example at 20 km/h the trike covers
   5.6 m/s, so state the metres travelled per 100 ms and include the
   debounce delay (N frames at the measured fps) in alert latency.
3. If the target is missed, try in this order and re-measure each:
   debounce 2 instead of 3 frames, camera frame rate and resolution,
   cheaper resize, and only then a different model (supervisor item).

## D. Focal-length calibration
Person or bicycle at a measured distance, read `bbox_width_px`, compute
focal_length_px = bbox_width_px x distance_m / real_width_m, repeat at
three distances, use the mean, then check the bands against the tape
measure. Replace the 600 px default only after this.

## E. Always-on service
A systemd unit on the Pi 4 that starts the detector with the live view at
boot and restarts on failure, running as `ogeder` from the venv (SIGTERM
already stops it cleanly). Keep per-frame prints off so journald holds
only alerts and timing. Give the unit file in the repo and the install
commands. Work out a stable address for the dashboard: mDNS
(`pi4-camera.local`) on the vehicle network, since the hotspot hands out
changing addresses.

## F. Dashboard integration (Pi 5, PySide6, inherited vac-work code)
The dashboard is in
`../Tukzie-Vac-Work-2026/Dashboard Team/Dashboard+ASIS` and already embeds
web content through QtWebEngineView. Add a Camera page that shows
`http://<pi4>:8080/stream`, and a small JSON endpoint on the detector
(for example `/alerts`, current active alerts only, the same five fields)
so the dashboard can show alerts without parsing video. Do not modify the
dashboard's existing pages or its Pi 5 install; add the page in a way the
dashboard team can review. Test the endpoint offline first.

## G. Records
Update the camera README, the runbook page and Methodology with each
measured result as it lands, rebuild the report PDF (Tectonic) and check
for undefined references, commit locally.

## Needs the supervisor before implementation
- Parking the HUD in favour of the dashboard and camera, and what replaces
  RQ2.
- Serving live imagery over the network (`--preview-host 0.0.0.0`).
- Any model change (EfficientDet-Lite, YOLOv8n) and any training or image
  collection.
- What counts as a hazard: road-surface defects or general objects.
- The optocouplers: part number and which vehicle signals they isolate.
