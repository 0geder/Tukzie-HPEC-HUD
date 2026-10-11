# Pothole detection in the camera detector (11 Oct 2026)

## What

Add road-surface hazard detection (potholes) to `CameraDetection/hazard_detector.py` on the Pi 4, next to the
existing SSD-MobileNet detector for people, vehicles and animals, without slowing that detector down.

- Model: run 2 (YOLO11n, one class, fine-tuned on Stellenbosch road-band tiles), exported to NCNN.
- Input: the same road band and tiling the model was trained on. Each camera frame is cropped to 42 to 68 % of its
  height and cut into three overlapping tiles, each 1280/3680 = 34.8 % of the frame width, at the left, centre and
  right (cell 2g of the training notebook). On the 640 x 480 camera stream that is rows 201 to 326 and three tiles
  223 x 125 pixels starting at x = 0, 208 and 417.
- Rate: a separate, low-priority worker process (nice 19, its own ncnn threads), fed with the band of the latest
  frame whenever it is idle, capped at a set rate (planned 2 to 5 Hz; see Results for what fitted). The main detector never waits for it. A separate process rather than a
  thread, so the pothole inference cannot hold Python's interpreter lock while the main loop needs it.
- Output, backward compatible: new keys only. `GET /detections` gains `road_hazards` (list) and `road_hazards_meta`;
  `GET /alerts` gains `road_hazards` (active pothole alerts). The existing `detections` and `active` lists are
  unchanged, so `sensor_fusion.py` (reads `detections`, `bands`, `frame_t_mono`, `t_mono`), the telemetry bridge and
  the dashboard camera page (reads `active`, `fps`, `latency_ms`) keep working and never see a pothole. A pothole
  has no distance estimate (there is no known real width), so its `band` and `est_distance_m` are null; it carries a
  bearing, a normalised box, the tile, the confidence, the model name and `experimental: true`.
- Honest confidence: threshold 0.5 (the main detector's), and an alert only after a pothole is seen in at least 2 of
  the last 3 pothole runs; it clears after 3 runs in a row without one. Alerts are labelled experimental in the
  payload. Pothole alerts go into the same alert log with the same five approved fields (class `pothole`, band null).
- Switch: `--potholes on|off` on the command line, else `"potholes": true|false` in `detector_options.json` on the Pi
  (no service file edit needed), else the built-in default. Default on only if the speed budget below holds.
- Still-image test mode: `--test-image PATH` feeds a saved picture instead of the camera at about 15 fps, so the
  whole path (worker, debounce, endpoints) can be checked with a pothole photo while the vehicle cannot be driven.
  It can run as a second instance on another port while the service keeps the camera.

## Why

- The COCO classes contain no road-surface hazards, and the report already describes two training runs and a first
  NCNN timing on the Pi; the step left was running the model in the detector.
- Run 1 scored 0.000 mAP@50 on South African images, so only run 2, trained on the SA road band, is a candidate.
  Running it on anything other than the band and tiling it was trained on would change the object scale it learned.

## Speed budget

Today (service, 11 Oct 2026, from the `[timing]` lines): 14.6 fps, sensor-to-result median about 120 ms (p95 about
148 ms), inference about 52 ms. Keep fps and latency for people and vehicles within about 10 % of that with the
pothole path on. Choose the 320 or 640 export by speed measured on the Pi with the main detector running.

## Limits stated up front

- Resolution gap: in training a tile was 1280 x 718 source pixels; on the 640 x 480 stream a tile is 223 x 125, so the
  model sees an upscaled, softer image. The pothole occupies the same fraction of the tile, so the object scale at the
  model input matches, but fine texture does not.
- Camera geometry: the band was chosen from where potholes sit in the Stellenbosch vehicle's frames. On this vehicle
  the camera height, pitch and lens differ, so the band may need moving (`--pothole-band`), checked on the road.
- The 0.714 mAP@50 is on the validation tiles (optimistic). The held-out test score is still to be produced
  (`CameraDetection/training/score_heldout.py`, run in Colab).
- Ethics: the README states that a model or alert-method change needs further ethics review. Potholes fall under
  "road obstacles" in the approved category list and no person or vehicle is identified, but adding a model is a
  change the student should confirm with the supervisor before field use.

## Results (11 Oct 2026)

Files: `CameraDetection/pothole_detector.py` (new), `CameraDetection/hazard_detector.py` (pothole path, settings,
`--test-image`), `CameraDetection/tests/test_pothole.py` and `tests/data/pothole_slievebane_road.jpg` (CC BY-SA 2.0,
`tests/data/ATTRIBUTION.txt`), `CameraDetection/training/score_heldout.py`, README notes, BenchTest C10.

Tested:
- Laptop: 22 of 22 pothole tests pass (tiling matches cell 2g on 3680 x 2760 frames, decode round trip, merging
  across tiles, NMS, 2-of-3 debounce, settings; the model test needs the ncnn package). The existing detector,
  endpoint and fusion tests still pass; with the path off the endpoints are byte-for-byte the old shape.
- Model choice on the Pi 4, three tiles on the fixed picture next to the running detector: 320 at 2 threads
  0.54 s, at 4 threads 1.7 s; 640 at 2 threads 2.2 s, and 640 missed the pothole that 320 found. 320 was chosen.
- Speed on the Pi 4, service running, about 60 s of `[timing]` lines each:

| Setting | fps | total p50 (ms) | total p95 (ms) | pothole rate (Hz) |
|---|---|---|---|---|
| Path off (before, and after) | 14.6 | 121 | 148 | none |
| 2 threads, up to 4 Hz | 11.7 | 137 | 167 | not recorded |
| 1 thread, up to 2 Hz | 11.2 | 146 | 175 | 1.3 |
| 1 thread, up to 1 Hz | 12.0 | 138 | 172 | 0.95 |
| 1 thread on its own core, detector on 3 | 10.9 | 147 | 174 | 1.4 |
| 1 thread, 0.5 Hz | 13.3 | 129 | 166 | 0.49 |
| 1 thread, 0.25 Hz | 13.9 | 125 | 157 | 0.25 |

  The cost is in the main model's inference (52 ms rising to 65 to 72 ms), not in its own loop: the worker
  competes for the Pi 4's shared cache and memory bandwidth, so pinning it to its own core made things worse.
  Only 0.25 Hz stays within 10 %, which is too slow to warn a moving vehicle (2 of 3 runs is 4 to 8 s), so the
  2 to 5 Hz target does not fit next to the main detector. The path is therefore off by default
  (`POTHOLES_DEFAULT = False`, 0.25 Hz and one thread when switched on) and the service runs without it.
- Pothole check on the Pi 4 (second instance, `--test-image`, port 8090, the service kept the camera): pothole at
  confidence 0.63, box (0.379, 0.522, 0.480, 0.550), bearing -4.1 degrees, centre tile, in `road_hazards` with
  `experimental: true`; an alert after 2 runs in `/alerts` `road_hazards`, logged with the five approved fields.
  The same picture gave the same box on the laptop. On the same still, the SSD reported a car at 0.50 about 46 m
  away, which is not in the picture: a false positive of the main model, noted, not changed here.
- Deployed: `hazard_detector.py`, `pothole_detector.py`, both run-2 NCNN folders and the test picture in
  `~/hazard_detector`; ncnn 1.0.20260526 installed into the venv from the local wheel in `~/yolo_bench/wheels`
  (`--no-deps`). Backups `hazard_detector.py.bak-1011` and `detector_options.json.bak-1011`. Service active,
  path off, 14.6 fps, 121 ms; `/detections` and `/alerts` unchanged; telemetry bridge active.

Not tested:
- Any road, and this vehicle's camera: the band position, the upscaled tiles and the confidence on real frames.
  The model's photos-from-standing-height test found only small potholes in the band; large near potholes below
  the band are outside what it looks at by design.
- The held-out score: the test tiles are not on the laptop. `CameraDetection/training/score_heldout.py` scores
  `best.pt` on the test split in Colab (steps in the script) and refuses the validation split.
- The dashboard does not show `road_hazards` yet (left alone on purpose; `active` is unchanged).

Options to make it fit, not done: a faster pothole model (smaller input on a crop of only the tiles that matter,
or int8 NCNN), running it only when the vehicle moves, or the Pi 5 or an accelerator for the camera.
Before field use: confirm with the supervisor that the added model and alert class fit the ethics approval
("road obstacles"), as the README's change-control note asks.
