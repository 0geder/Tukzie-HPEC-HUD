# SW-7 project log

SW-7 is a UCT EEE4022S 2026 final-year project by Samson Okuthe (OKTSAM001), supervised by A/Prof. Simon Winberg with co-supervisor Sampath Jayalath. It is an embedded HPEC telemetry unit and a windshield HUD for the TUKZIE Rev 0, a 72 V electric cargo trike. The telemetry unit is an ESP32-S3 (Makerfabs board with an A7670X LTE Cat 1 modem). It runs FreeRTOS and samples two MPU6050 IMUs at 200 Hz. From those it computes calibrated, speed-normalised ride features and fuses them. It also reads the JBD BMS over BLE and GNSS through the modem, publishes JSON over MQTT on LTE, and logs locally to internal flash (LittleFS). A Raspberry Pi 4 runs a forward camera with a pretrained object detector, a live view and an alerts endpoint for the inherited vac-work dashboard. The HUD is on hold pending the supervisor meeting. This file records everything technical done and every decision made. The `progress-scribe` agent (.claude/agents/progress-scribe.md) keeps it current.

Last updated: 2026-09-28, evening (initial build from the repo, report, GA form and session transcript; covers commits 3dd8ab9 to 72ba826; later on 28 Sept: firmware v0.5.0 committed as dfc6542, and the fusion and calibration figures in the report, deck and poster corrected from the bench log).

Conventions: dates are 2026. "Transcript" means the Claude Code session transcript. A fact marked "per the student, not in the repo" was stated by the student in the session but has no file in this repo behind it. "Unverified" means claimed but not measured or not found.

---

## 1. Where we are

The bench phase is complete. All ESP32 subsystems run together on the target board. Dual-IMU acquisition at 200 Hz is calibrated and fused live, with a 150 s session recorded. The MQTT publish over LTE was acknowledged once against a public broker, and local flash logging mounts and writes. The Pi 4 camera detector ran live for the first time on 28 Sept at about 7 fps. It now has a live view, an /alerts endpoint, latency instrumentation, a systemd unit and a Front camera page for the dashboard, though only the person class is confirmed. Nothing has been tested on the moving vehicle yet. The report has a full Methodology but Results, Discussion and Conclusions are placeholders. The main body is about 62 pages against a 50-page limit. Firmware v0.5.0 is being written today and is not yet flashed.

Deadlines: report pre-submission opens 6 Oct; final report due 27 Oct 23:59; presentations 16 to 17 Nov; Open Day 18 Nov.

### Status board

#### Done (with evidence)

ESP32-S3 telemetry unit
- Modem bring-up over UART (AT, CPIN, CSQ, CREG): commit 309fdeb; Methodology.
- Dual-IMU FreeRTOS acquisition at 200 Hz, GNSS parsing, BMS BLE, sync pulse, ride features with sine self-test: 7d989cb; Methodology.
- Per-sensor magnitude calibration stored in NVS (factors 0.9773 and 0.9901 on first calibration): 5e3e6d9; Methodology.
- Speed-normalised roughness index: d6f73bb; Methodology (Speed-normalised roughness index).
- MQTT over the A7670X (AT+CMQTT): 59fdd82. Acknowledged publish to test.mosquitto.org (+CMQTTPUB: 0,0): Methodology (End-to-end validation).
- Local logging to LittleFS: 20d2fa6. Mount verified live after the flash fix: 6d3a080.
- Boot loop fixed (flash_size 16MB, DIO): 6d3a080; Methodology.
- Dual-IMU fusion with 5/5 boot self-tests passing: 8fb96f3, verified live 6d3a080; BenchTest/logs/2026-09-25_bench_fusion_shake.log.
- 150 s bench session recorded (149 fused windows, printed as 222 lines because both sensor tasks print each result; skew under 1 ms, no dropped samples): 46377a3; log above; Methodology.

Raspberry Pi 4 camera
- Pi 4 provisioned (OS Trixie, USB drive, hotspot networking, OV5647 identified): Methodology (Pi camera provisioning).
- Camera to IMU time alignment within about 1 s (lens-cover test): Methodology (time sync).
- Detector MVP: 9d84608. Categories restricted, three distance bands, five logged fields: 0383316.
- First live runs, label offset and B,G,R fixes, hysteresis: 4a62173; CameraDetection/README.md Status; Methodology (Status at time of writing).
- Non-blocking live view, per-stage latency output, 4 inference threads: 4e3da88.
- --tuning option for a no-IR-filter camera: 5206a95.
- GET /alerts endpoint: 57dd18e.
- systemd unit and install notes: 7b0601f (CameraDetection/deploy/).
- 15-paper camera/ML reading library: 54a8baf (Report/references_pdf/camera_ml).

Dashboard integration
- Front camera page (PySide6/QtNetwork) tested offscreen on the laptop: 7b0601f; DashboardIntegration/README.md.

Bench tools
- Live bench classifier and Gaussian-splat walkthrough: 5e3e6d9.
- Browser live-telemetry dashboard (Web Serial) with log replay: 6e871a1, 46377a3.
- Automated research pipeline with gap ledger: e9c5203, c0442ec, 6154050.

Mechanical
- Three-part camera casing designed by the student and 3D printed; second casing for a second camera: STLs in CameraMount/casing (18d7e24); Methodology. Student's own statement in transcript, 24 and 25 Sept.

Report, GA form, presentation
- GA tracking form submitted and signed by the supervisor as satisfactory ("DP satisfied"): GA Tracking Form/OKTSAM001 GA Tracking Form - Signed.pdf (18d7e24). Supervisor's email in transcript, 24 Sept evening.
- Report Methodology documents fusion, logging, flash fix, bench session and camera live run: f2838d1, 46377a3, 4f2aff7, 4a62173.
- Deck (12 slides) and A1 poster in the UCT poster-template style: c5f5b55 (Presentation/).

#### In progress
- Firmware v0.5.0 (committed dfc6542 on 28 Sept, compiles; not yet flashed or tested). Adds serial commands !status, !log off, !log on, !mqtt and !recal. MQTT result codes are checked per A76XX manual v1.09 section 18.2 (+CMQTTCONNECT, +CMQTTPUB), and reconnects use backoff (first retry 30 s after a failure, then doubling). Not yet flashed or tested.
- Supervisor meeting preparation: HUD on hold, replacement RQ2, and the other items under "Waiting on someone".

#### Waiting on someone
- Supervisor (A/Prof. Winberg):
  - Parking the HUD and what replaces RQ2.
  - Serving live imagery over the network (--preview-host 0.0.0.0).
  - Any model change (EfficientDet-Lite, YOLOv8n), training or image collection.
  - What counts as a hazard (road-surface defects or general objects).
  - What the optocouplers are for.
  - Source: Planning/camera-integration-prompt.md, "Needs the supervisor".
- Yusuf Vawda (Controls Lab): vehicle access for the field test. Scheduling emails are in the transcript (1 and 8 Sept). No test date is recorded.
- Dashboard team (vac work): review of the four wiring edits for the Front camera page (DashboardIntegration/README.md).
- Sharaav (SW-6): open UART details (CSV field order and precision, update rate, line termination, invalid-line behaviour). Source: Planning/sharaav-interface-definition.md.
- Suppliers: VL53L5CX (sourced, not received per report and deck) and SEN55 (ordered locally, not received per report).
- Repo access for Winberg: per the student, 2026-09-28, not in the repo. Details not recorded.

#### To do
ESP32
- Flash and test v0.5.0.
- Confirm the flash-write stall with `!log off`.
- Recalibrate both IMUs while stationary (`!recal`).
- Confirm that MQTT retries after a failed initial connect.
- Read back and check the LittleFS log. Replay unsent lines on reconnect (not built).
- Get an outdoor GNSS fix and confirm the speed units (knots or km/h).
- Battery test: BLE reliability over a sustained session and a discharge curve (Results 4.4 placeholder).

Camera
- Colour check (reddish view, possible NoIR module).
- Focal-length calibration (600 px placeholder, about 643 px expected).
- Detection tests of the other six classes at measured distances.
- Latency target and measurement.
- Install and verify the systemd unit on the Pi.
- Test the Front camera page on the Pi 5 against the live detector.
- Outdoor and on-vehicle test.

Sensors
- Integrate the VL53L5CX and SEN55 on arrival (bench validation plan in Methodology).

Field
- Full-system test on the vehicle with the TUKZIE team.

Report
- Cut the main body from about 62 to 50 pages.
- Fill Results, Discussion and Conclusions from field data.
- Fix the stale sentences in section 7 of this log.
- Rebuild the PDF.

Presentation
- Update slide 10 (says the detector has not run live) and slide 12 (says "Build and evaluate the HUD").
- Replace the slide 12 placeholder with field results.

Repo
- Update README.md: it still says the camera is untested live and the HUD is "not built yet".

---

## 2. Decisions register

Status values: agreed (the student decided, or the supervisor confirmed), pending supervisor, reversed, superseded.

| # | Date | Decision | Why | Who | Status |
|---|---|---|---|---|---|
| D1 | 2026-08-27 | ESP32-S3 on the Makerfabs board with built-in A7670X LTE Cat 1 modem as the telemetry unit | One board gives MCU, LTE and GNSS; modem on GPIO47/48 | Student | Agreed (309fdeb) |
| D2 | 2026-09-16 | Two MPU6050s on separate I2C buses (GPIO8/9 and GPIO17/18), each at 200 Hz via vTaskDelayUntil on core 1, highest priority | 200 Hz is above twice the 80 Hz ISO 2631-1 band; deterministic timing; separate buses avoid address clash | Student | Agreed (7d989cb; Methodology) |
| D3 | 2026-09-16 | Keep MQTT inside the modem task, not a separate task | Modem UART has no locking; concurrent AT commands would corrupt both streams | Student with Claude | Agreed (59fdd82) |
| D4 | 2026-09-16 | Broker left as placeholder, never the vac-work team's broker; later test.mosquitto.org for path validation only | Vac-work documentation says its credentials must not be shared with an LLM | Student with Claude | Agreed (59fdd82; Methodology) |
| D5 | 2026-09-16 | Pretrained COCO SSD-MobileNet-v1 (8-bit TFLite), no training | Fits a Pi 4 with no accelerator in real time; no data collection needed | Student with Claude | Agreed (9d84608) |
| D6 | 2026-09-04 (constraint), recorded in report | Camera on a Raspberry Pi 4, not the Pi 5 | The Pi 5 runs the inherited vac-work dashboard, and only one storage card was available; Pi 4 boots from its own USB drive | Student | Agreed (transcript 4 Sept; Methodology) |
| D7 | 2026-09-19 | Per-sensor scalar magnitude calibration stored in NVS, sanity range 0.5 to 2.0 | Two MPU6050s disagreed by about 5 to 8 percent at rest; features use magnitude only | Student with Claude | Agreed (5e3e6d9) |
| D8 | 2026-09-19 | Camera mount: friction-fit OpenSCAD bracket designed, then not used | No verified hole drawing for the camera board. Superseded by the student's own casing (D19) | Claude, then student | Superseded (bracket shown as "unprinted" in 4f2aff7) |
| D9 | 2026-09-19 | Speed-normalise the roughness index (mean square over GNSS speed, NaN below 1.0 or with no fix) | Raw RMS conflates road roughness with speed (Li et al. 2018) | Student with Claude | Agreed (d6f73bb) |
| D10 | 2026-09-19 | Research pipeline on OpenAlex, arXiv and Crossref with a falsifiable gap ledger; no Google Scholar scraping; every DOI re-resolved | Defensible gap claims; no bad citations | Student with Claude | Agreed (e9c5203) |
| D11 | 2026-09-19 | Narrow gap claims G1 (dual spatially separated IMUs, ride-quality framing, three-wheeler class) and G3 (not experimentally characterised); G2 stands; add G4 (HUD application and integration only) | Prior work (Electronics 2026 motorcycle unit) defeats the broad claims | Student with Claude | Agreed (c0442ec, fb894ff) |
| D12 | 2026-09-19 | ML excluded from version one; detector kept as prepared future work | The ethics application at the time said no ML in version one | Student with Claude | Reversed on 2026-09-23 by D16 (000783c) |
| D13 | 2026-09-19 | HUD: direct view as primary mode, combiner as secondary shade/dusk mode, to raise with supervisor | A sunlight-readable combiner needs 50,000 to 100,000 nit sources; MCU panels reach about 1,000 | Claude analysis | Pending supervisor, now overtaken by D26 (fb894ff) |
| D14 | 2026-09-21 | Local logging to internal flash (LittleFS), not microSD | The microSD chip select reaches GPIO10 only through R23, marked NC (not fitted) | Student with Claude | Agreed (20d2fa6) |
| D15 | 2026-09-21 | SW-6/SW-7 link: UART 115200 8N1 on GPIO43/44, CSV, speed (km/h) and battery percent from SW-6; SW-6 keeps its own IMU | Direct source for HUD speed and SoC | Student and Sharaav | Preliminary; details open (9af9724). A possible change is logged in fad31ab |
| D16 | 2026-09-23 | Run the detector as ML under the revised ethics application. Categories: person, bicycle, car, motorcycle, bus, truck, dog. No frames saved, five logged fields, no face or plate recognition | Revised application approved with conditions ("the ethics just came in and we are supposed to do ML") | Student; ethics committee | Agreed (0383316; transcript 23 Sept) |
| D17 | 2026-09-22 | VL53L5CX 8x8 multi-zone ToF chosen over the single-point VL53L1X | Left, centre and right discrimination from one sensor (63 degree field, 8x8 zones) | Student | Agreed (transcript 22 Sept; Methodology) |
| D18 | Not recorded | SEN55 environmental sensor (SEN55-SDN-T) ordered from a local supplier | Environmental data on the same timeline as ride data | Student | Agreed (Methodology; Introduction scope) |
| D19 | 2026-09-24, 25 | Camera casing designed by the student, 3D printed in three parts (bottom shell, top cover, 30 degree corner mount); a second printed casing houses a second camera | Student's own design; credited as individual work | Student | Agreed (CameraMount/casing; transcript 24 and 25 Sept) |
| D20 | 2026-09-24 | The report must not mention the ethics application, approval or protocol number; describe what was done and measured | Student's instruction | Student | Agreed (transcript 24 Sept; CLAUDE.md) |
| D21 | By 2026-09-24 | No em dashes and no unnecessary bold in chat, emails, report and GA form | Student's writing rule | Student | Agreed (transcript 24 Sept; CLAUDE.md; memory) |
| D22 | Set before 2026-09-28 | No Co-Authored-By trailer in commits; ask before pushing | Student's rule. Ten earlier commits (5e3e6d9 to 20d2fa6, 19 to 21 Sept) carry the trailer; noted, no action | Student | Agreed (CLAUDE.md; memory) |
| D23 | 2026-09-25 | Fix the boot loop with board_upload.flash_size 16MB and board_build.flash_mode dio, matching default_16MB.csv; PSRAM type left at default | The ROM reports DIO; an 8 MB flash-size setting with a 16 MB partition table boot-looped | Student with Claude | Agreed (6d3a080). First noted in 7d989cb, 16 Sept |
| D24 | 2026-09-25 | Fuse the two IMUs by equal-weight mean, with a disagreement figure, a 50 percent overlap rule and a 3 s single-sensor fallback; crest factor and crossings stay per sensor | Same part, same configuration and same calibration, so equal noise; inverse-variance weighting then reduces to the mean | Student with Claude | Agreed (8fb96f3; Methodology) |
| D25 | 2026-09-25 | Deck limited to 12 slides; deck and A1 poster built in the UCT poster-template style | Course limit ("the max number of slides is 12") | Student | Agreed (transcript 25 Sept; c5f5b55) |
| D26 | 2026-09-28 | HUD put on hold; the existing dashboard plus the camera is used instead | Student's view: the dashboard already carries what the HUD would show, two displays distract, and a move towards autonomy makes the camera more relevant | Student | Pending supervisor (transcript 23 and 28 Sept). Title and RQs unchanged until the supervisor agrees |
| D27 | 2026-09-28 | Picamera2 RGB888 is B,G,R, so convert to R,G,B; drop the labelmap "???" offset | Faults found on the first live run; checked against the model file, TF example and Picamera2 manual | Student with Claude | Agreed (4a62173) |
| D28 | 2026-09-28 | Alert hysteresis: 3-frame onset, re-log on a nearer band held 3 frames, clear after 5 missed frames | 16 activations in 47 s for one person when clearing on one missed frame | Student with Claude | Agreed; tested offline only (4a62173) |
| D29 | 2026-09-28 | Use LiteRT (ai-edge-litert), not tflite-runtime | No tflite-runtime wheels for Python 3.13 on Pi OS Trixie | Claude | Agreed (4a62173) |
| D30 | 2026-09-28 | Front camera page uses QtNetwork MJPEG, not QtWebEngine; kept outside the dashboard repo for the team to review | The WebEngine view has crashed on the Pi 5 (dashboard README); do not change another team's code | Student with Claude | Agreed (7b0601f) |
| D31 | 2026-09-28 | Optocouplers received; purpose to be confirmed with the supervisor | The vac-work DAQ plan puts a 12 V divider/opto on the Vehicle State 1 to 3 inputs (Tukzie-Vac-Work-2026/DAQ_G474RE_Nodes/Embedded_System_Pin_Planning_rev3.md lines 214 to 216) | Student | Pending supervisor (transcript 28 Sept). Part number not recorded; PC817 and a Netram module appear in 1 Sept planning |
| D32 | 2026-09-28 | Firmware v0.5.0: serial test commands, MQTT result-code checking, reconnect with backoff | The bench log shows "Initial connect failed, will not retry automatically"; stall test and recalibration need runtime switches | Student with Claude | In progress, not flashed |

---

## 3. Timeline

Grouped by week (weeks start on Monday). Commit hashes are in brackets. Events without a hash come from the transcript.

### Week of 3 Aug
- 08-03: Initial commit (3dd8ab9).
- 08-06 to 08-07: first literature papers added; Introduction started (4aff494, 0aa219a).
- 08-09: more papers (b1b466e).

### Week of 10 Aug
- 08-12, 08-15: further papers and research (9f6ff14, e07e7e0).

### Week of 24 Aug
- 08-27: ESP32-S3 A7670X firmware baseline. PlatformIO on COM10, modem UART on GPIO47/48, AT checks, heartbeat, pass-through; build and upload verified (309fdeb).
- 08-31: vac-work audit and development plan; BMS over BLE identified as a low-risk data source (transcript).

### Week of 31 Aug
- 09-01: component shopping list, including optocouplers for 12 V lines. IMUs ordered. Email to Yusuf about vehicle access (transcript).
- 09-04: constraint recorded that the Pi 5 holds the dashboard and the only storage card (transcript).

### Week of 7 Sep
- 09-06 to 09-08: camera hazard idea explored; lab scheduling with Yusuf (transcript).

### Week of 14 Sep
- 09-16:
  - Firmware synced to the full dual-IMU FreeRTOS architecture: GNSS, BMS BLE, sync pulse, ride features with self-test, 16MB/DIO flash overrides; PSRAM undetected (7d989cb).
  - Repo reorganised (e0a2b11).
  - Camera detector MVP (9d84608).
  - Gap papers (8c25f21).
  - README (224e139).
  - MQTT over cellular (59fdd82).
  - GA1/GA4/GA9 update (008e524).
- 09-17: autonomy and camera literature requested (transcript).

### Week of 14 Sep, continued (19 to 20 Sep)
- 09-19:
  - Per-sensor IMU calibration, bench tooling, OpenSCAD mount (5e3e6d9).
  - Research pipeline (e9c5203).
  - Gap review narrowing G1 and G3 (c0442ec).
  - RQ6/RQ7 searches (6154050).
  - Speed normalisation (d6f73bb).
  - ML excluded from version one (000783c).
  - HUD prior-art gap G4 (fb894ff).
- 09-20: GA1/GA9 update (bf3d20a).

### Week of 21 Sep
- 09-21: SW-6/SW-7 UART agreement recorded (9af9724); LittleFS local logging added, compiled but not flashed (20d2fa6).
- 09-22: VL53L5CX chosen over VL53L1X (transcript).
- 09-23:
  - Revised ethics application approved with conditions; ML now in scope (transcript).
  - Student questions HUD feasibility given the existing dashboard (transcript).
- 09-24:
  - Detector restricted to the approved categories and five log fields; GA form rewritten (0383316).
  - GA edits (5ae6025, 509f218, fad31ab, 9c7fd27, 1af82b8, 57a6b03).
  - Student asks that the report never mention the ethics approval (transcript).
  - Supervisor signs the GA form as satisfactory (transcript, evening of 24 Sept).
- 09-25:
  - Dual-IMU fusion (8fb96f3).
  - All project files brought into the repo, including the signed GA form and casing STLs (18d7e24).
  - Boot loop fixed; LittleFS mounts; fusion verified live (6d3a080).
  - Report: fusion, logging, flash fix (f2838d1).
  - Web Serial dashboard (6e871a1).
  - 150 s bench session recorded and added to the report (46377a3).
  - Figures moved to an appendix (4f2aff7).
  - Deck, poster and talking points; deck cut to 12 slides (c5f5b55).
  - Student confirms the casing is their own design and the second casing is for a second camera (transcript).

### Week of 28 Sep
- 09-28:
  - First live detector runs: 430 frames in 60 s (7.2 fps), then 419 frames in 60 s. Label offset and B,G,R fixes; person confidence 0.50 to 0.73; 16 activations in 47 s led to hysteresis; live view (4a62173).
  - 15-paper camera/ML library (54a8baf).
  - Non-blocking preview, latency timing, 4 threads (4e3da88).
  - --tuning (5206a95).
  - Camera integration prompt (0e5656b).
  - /alerts (57dd18e).
  - Front camera page and systemd unit (7b0601f).
  - README (ccbcd2a).
  - progress-scribe agent, CLAUDE.md and log prompt (72ba826).
  - Optocouplers received; HUD put on hold pending the supervisor (transcript).
  - Firmware v0.5.0: MQTT result codes and reconnect, serial commands; compiles, not yet flashed (dfc6542).
  - This log created, and figures corrected from the bench log: 149 fused windows, 0.067 still max, 9.93/10.10 resting, 1 s sync period (b57f742).
  - Bench console combining ESP32, camera, alerts, ToF and SEN55 panels (97481b0).
  - Report put into the handout format: Times New Roman 11 pt, single spacing (Intro Lecture p. 11, Lecture 2 p. 7). Content pages fell from 62 to 46 (limit 50). Body word count 17,931 added under the declaration (Lecture 2 p. 10), against 10,000 to 15,000 in GA6.
  - 29 Sept: per the student, capture all work in the report now and cut for length later. Methodology gained: alert hysteresis (tested offline), live view and latency measurement (tested offline), alerts feed, dashboard camera page and start-up service (page tested offscreen; service not installed), colour-cast investigation (tests not yet run), the combined bench console, and firmware v0.5.0 result-code checking, reconnection and serial commands (compiles, not flashed). Report now 49 content pages and 19,370 prose words.
  - 29 Sept: firmware v0.5.0 flashed to the target board and bench-tested with BenchTest/v050_bench_test.py (log BenchTest/logs/2026-09-29_v050_bench_test.log). Flash-write stall confirmed: 33 to 40 ms gaps on both IMUs every 10 s with logging on, worst 5.9 ms with !log off, no drops, MQTT publishing throughout. Commands work; MQTT 47 publishes, 0 failed; !mqtt reconnect in 0.4 s. GNSS polls no longer time out (indoors, no fix). Not yet exercised: retry after a failed first connect, real signal loss, !recal.
  - 29 Sept, clean-up pass (Planning/cleanup-pass-prompt.md): drafting notes removed; wrong cross-references fixed and every hard-coded chapter number turned into a \ref; calibration figures corrected from the 18 Sept session record (bare board raw 10.35 to 10.39 and 9.55 to 9.56, stored factors 0.9773 and 0.9901 implying 10.03 and 9.90 at calibration, target board first boot 9.4387 and 9.5725 giving 1.0390 and 1.0245; orientation dependence named as the likely cause, not confirmed); the '5 to 8%' figure corrected to about 8% in report, deck and poster; LTE Cat-1, one sampling figure, one department name, HPEC defined; GA appendix rewritten per GA, consistent with the signed GA form. 49 content pages, 19,687 words.
  - Vehicle state, per the student: the trike is on the ground in the lab and can be raised or lowered on request (the test plan's "permanently raised" is out of date). Sensors to be mounted on the trike on Wednesday 30 Sept; first road test requested from Yusuf for Friday 2 Oct (email drafted, not yet confirmed).
  - Appendix C, Test Evidence, and Report/evidence/ with a capture guide. CHANGELOG.md (every change and why) and Planning/brief-compliance.md (requirements matrix, about 40 percent complete) added.

---

## 4. Technical breakdown

### 4.1 ESP32-S3 telemetry unit (HUDTelemetryUnit/)

What it does:
- Board: Makerfabs ESP32-S3 (WROOM-1-N16R8) with an A7670X modem.
- PlatformIO environment esp32-s3-devkitc-1, Arduino framework, upload and monitor on COM10 at 115200. ARDUINO_USB_MODE=1 and ARDUINO_USB_CDC_ON_BOOT=1 route Serial to native USB on the Makerfabs board (5e3e6d9).
- Partitions default_16MB.csv, LittleFS, flash_size 16MB, flash_mode dio (platformio.ini).
- Libraries: Adafruit MPU6050, Unified Sensor, BusIO.

FreeRTOS tasks (committed v0.4.0, main.cpp):

| Task | Core | Priority | Role |
|---|---|---|---|
| Imu1Task, Imu2Task | 1 | 3 | 200 Hz sampling (5 ms vTaskDelayUntil), microsecond timestamps, bounded queues, drops counted |
| StatsTask | 1 | 2 | Rate and drop statistics every 2 s |
| SyncTask | 1 | 2 | Sync pulse on GPIO15 |
| RideChar1Task, RideChar2Task | 1 | 1 | 1 s windows, features and fusion |
| ModemTask | 0 | 1 | GNSS polling, MQTT, local log |
| BmsTask | 0 | 1 | JBD BMS over BLE |

Dual IMU acquisition
- IMU1 on GPIO8/9 and IMU2 on GPIO17/18, address 0x68 each.
- Settings: plus or minus 8 g, plus or minus 500 deg/s, 260 Hz DLPF.
- Queues of 100 samples per IMU.
- Measured 200.0 to 200.5 Hz with no drops (bench log, Methodology).

Calibration
- 200 stationary samples; factor = g / mean magnitude, stored in NVS, rejected outside 0.5 to 2.0.
- First calibration: 0.9773 and 0.9901, giving 9.80 to 9.81 m/s2 afterwards (Methodology).
- The bench log of 25 Sept loads stored scales of 1.0390 and 1.0245. The first calibration (0.9773, 0.9901) was done on the bare development board; the target board has its own NVS and would have calibrated itself at its first boot with the IMUs connected. That boot was not logged. Methodology now says this.

Ride features
- Per 1 s window: RMS, std, peak-to-peak, crest factor, mean absolute jerk, threshold crossings (mean + 2 sigma), and the speed-normalised index (mean square / GNSS speed, NaN below 1.0 or with no fix).
- Sine self-test within 5 percent.

Fusion
- Equal-weight mean of RMS, std, peak-to-peak, jerk and speed index. Crest factor and crossings stay per sensor.
- Disagreement figure = |std1 - std2| / mean, floored at 0.05 m/s2.
- A pair is fused only if the windows ended within 0.5 s of each other. Fallback to the remaining sensor after 3 s.
- Boot self-test has 5 checks: mean, disagreement, speed index needs both, misaligned pair rejected, stale-sensor fallback.

BMS over BLE
- JBD/Jiabaida protocol, basic-info query register 0x03, service UUID 0xff00 fix, reconnect defect addressed.
- Connection is intermittent and not yet complete (Methodology).
- The bench log shows scans but no pack connected.

GNSS
- AT+CGNSSINFO through the modem, polled about every 3 s, with about a 3 s timeout.
- The response had 9 fields, not the 13 expected; manual v1.09 lists 16.
- Speed units (knots per manual) not confirmed.
- No fix yet: the bench log reads "GNSS: 0 polls, 0 with a fix" (indoor).

LTE and MQTT
- AT+CMQTT, topic sw7/telemetry, publish every 10 s.
- LTE registration observed but intermittent indoors (+CGEV: NW PDN DEACT seen).
- One acknowledged publish to test.mosquitto.org.
- In the 25 Sept log, CMQTTSTART failed and the firmware printed "Initial connect failed, will not retry automatically this run".

Local logging
- /telemetry.log on LittleFS, 3,538,944 bytes total. A JSON line every 10 s (in practice every 12 s, see findings), regardless of MQTT state.
- Truncated beyond 3 MB. No rotation and no replay of unsent lines.
- Used space grew from 12 KB to 56 KB across boots (Methodology). Read-back not done.

Sync pulse
- GPIO15 toggled every 500 ms by SyncTask (vTaskDelayUntil 500 ms, main.cpp line 833), logged on the Pi on GPIO17.
- Edges measured 500.1 to 500.3 ms apart on the Pi.
- Camera to IMU alignment within about 1 s (lens-cover test).

SW-6 link: agreed in outline (D15), not implemented in the committed firmware (unverified; not seen in the v0.4.0 task list).

Current state: v0.4.0 verified on the bench. v0.5.0 committed (dfc6542) and compiles, not yet flashed (D32).

Known limitations:
- PSRAM is not detected (unused).
- Flash-write stalls (F6).
- No MQTT retry in v0.4.0.
- IMU calibration drift (F5).
- Nothing has run on the vehicle.

### 4.2 Raspberry Pi 4 camera (CameraDetection/)

Provisioning
- Pi 4 hostname pi4-camera, Pi OS Trixie, Python 3.13, booting from its own USB drive.
- Reached over the phone hotspot (2.4 GHz); the university network did not work.
- Camera is an OV5647 (Camera Module v1). The detector runs at 640x480.

Hazard detector
- hazard_detector.py runs COCO SSD-MobileNet-v1, 8-bit (detect.tflite, labelmap.txt), on LiteRT (ai-edge-litert) in ~/hazard_detector/venv with system site packages for Picamera2.
- Classes: person, bicycle, car, motorcycle, bus, truck, dog.
- Distance = real width x focal length / bbox width, with one fixed width per class (car 1.8 m, bicycle 0.6 m front-on). Focal length is an uncalibrated 600 px placeholder (about 643 px expected).
- Bands: immediate, warning, monitoring.
- Hysteresis per D28.
- Only five fields are logged to alerts.jsonl: class, distance_band, confidence, timestamp with UTC offset, alert_status. Frames are never written to disk.
- SIGTERM stops it cleanly.

Live view and endpoints
- --preview serves MJPEG at :8080 (/stream) from its own thread, dropping stale frames. It is local by default; --preview-host 0.0.0.0 exposes it to the network (plain, unauthenticated HTTP).
- GET /alerts returns the active alerts (the five fields) plus fps and latency_ms.

Latency measurement
- Uses each frame's SensorTimestamp (ns since boot, same clock as time.monotonic_ns).
- A [timing] line every 5 s gives p50, p95 and max per stage and sensor to result.
- --timing-log writes a per-frame CSV. --threads defaults to 4. --verbose prints each detection and bbox_width_px.
- No latency figures are recorded in the repo yet. The 182 ms in the DashboardIntegration README is an example JSON value, not a measurement.

Service
- CameraDetection/deploy/hazard-detector.service with INSTALL.md: starts with --preview on 8080 at boot and restarts on failure; logs via journalctl -u hazard-detector.
- Installation on the Pi is not recorded (unverified).

Measured (CameraDetection/README.md Status; Methodology):

| Run | Result |
|---|---|
| Run 1 | 430 frames in 60 s (7.2 fps computed; README says about 7 fps) |
| Run 2 | 419 frames in 60 s |
| Person after fixes | Confidence 0.50 to 0.73 |
| Before hysteresis | 16 activations in 47 s for one standing person |

Known limitations:
- Only person is confirmed.
- Focal length is uncalibrated.
- The fixed-width heuristic reads a side-on bicycle at about a third of its true distance (estimate, camera-integration-prompt.md).
- The live view looks reddish (possible NoIR module, not checked).
- Not tested outdoors or on the vehicle.
- The label and colour fixes went in together, so their individual effects were not separated.

### 4.3 Dashboard integration (DashboardIntegration/)

Design references noted by the student (29 Sept 2026), for the dashboard direction that is replacing the HUD (pending the supervisor). Not yet reviewed in detail:
- A. S. Suryavanshi, "Driving into the Future: The Evolution of Car Dashboards", Medium: https://medium.com/@aushijsingh.suryavanshi/driving-into-the-future-the-evolution-of-car-dashboards-c9a9c7f22f3c. A blog post, not peer reviewed, so useful as background but not as a citation for a claim in the report.
- "Smart Autonomous Vehicle Dashboard: Real-Time Interactive System", Figma Community file: https://www.figma.com/community/file/1582306361195081977/smart-autonomous-vehicle-dashboard-real-time-interactive-system. A design example for laying out camera, hazard and vehicle-state information on one screen.

What it does:
- front_camera_page.py is a FrontCameraPage for the vac-work PySide6 dashboard on the Pi 5 (Tukzie-Vac-Work-2026/Dashboard Team/Dashboard+ASIS).
- A QtNetwork MJPEG reader decodes only the newest frame and streams only while the page is visible.
- It polls /alerts and shows them in the dashboard's colours (red immediate, amber warning, green monitoring). It also shows fps and latency.
- It reconnects every 3 s and emits alerts_changed(list).
- The address comes from TUKZIE_CAMERA_URL (default http://pi4-camera.local:8080).
- Four wiring edits for the dashboard team are documented in the README.

Tested: offscreen on the laptop with PySide6 6.11.2 inside a copy of the dashboard app package. Covered frame parsing, uneven 1777-byte chunks, alert list and clear, offline "retrying" within 7 s, and the icon at 96 px.

Not tested: on the Pi 5, against the live detector, or with the four edits applied.

### 4.4 Bench tools (BenchTest/, VirtualTukzie/, Research/)

- BenchTest/live_telemetry.html: Chromium Web Serial dashboard. Shows fused and per-IMU features, sample rate and drops, GNSS/BMS status, free memory, self-test results, and rolling plots of vibration and disagreement. It can replay a saved log (6e871a1, 46377a3).
- BenchTest/sw7_console.html: the combined bench console (97481b0). One local page in Edge or Chrome with the ESP32 telemetry over Web Serial (cards for ride vibration, IMU acquisition, BMS, GNSS, MQTT, logging and system), the Pi camera live view and /alerts, buttons for the v0.5.0 serial commands (with an in-page confirm for !recal), a filtered log, a timestamped session-log download, and replay of recorded logs. ToF and SEN55 panels parse proposed `[TOF] mm=...` and `[ENV] ...` lines, ready for when those sensors are wired. Checked by replaying the 25 Sept log. It only reads data, so it does not change the firmware or the fusion; while connected it holds the COM port, so close it before flashing or using another serial monitor.
- BenchTest/live_classifier.py: live bench classifier on the [RIDE] feature stream (5e3e6d9).
- BenchTest/logs/2026-09-25_bench_fusion_shake.log: the 150 s session from power-up. It was still from 0 to about 75 s and disturbed by hand from about 75 to 128 s; the planned 50 to 70 s cues were not heard, and the log header says so. Results:
  - 149 fused windows (222 printed lines), all from both sensors, skew under 1 ms.
  - Still (first 70 s): median 0.041 m/s2, max 0.067 m/s2. The earlier 0.058 came from the first 48 s only.
  - Disturbed: peak std 9.35 m/s2 (that window's peak-to-peak 76.8); largest peak-to-peak in any window 77.6 m/s2.
  - Both IMUs at 200.0 to 200.5 Hz with no drops.
  - Resting magnitudes in this log (median, first 75 s): IMU1 9.93, IMU2 10.10 m/s2 (1.3 and 2.9 percent above g) with stored factors 1.0390 and 1.0245. The 10.07 and 9.97 previously in the report came from an earlier live capture that is not in the repo, so they were replaced.
  - Disagreement 0.00 to 1.68 over the session (the 0.06 to 0.87 earlier in the report came from a live capture not in the repo).
- Gaussian-splat walkthrough with live telemetry (5e3e6d9). The 113 MB splat is gitignored.
- Research/: pipeline, SQLite database, gap ledger, digests, BibTeX. 733 sources, 309 in BibTeX after RQ6/RQ7 (6154050).

### 4.5 Mechanical (CameraMount/)

- Casing designed by the student: RPi_cam_case_bottom.stl, RPi_cam_case_top.stl, RPi_cam_30_deg_corner_mount.stl. Per Methodology the bottom is 29.2 x 28.2 x 7.6 mm, the cover 4.8 mm and the mount 32.3 mm.
- Printed; a second casing holds a second camera. Not yet fixed to the vehicle.
- The OpenSCAD friction-fit bracket (camera_mount.scad/.stl) was not printed or used (D8).

### 4.6 Sensors on order or received

- VL53L5CX (Pololu carrier): 8x8 zones, 63 degrees, up to 4 m. Sourced, not received (report, deck slide 10). The five-step bench validation plan is in Methodology. Caroleo 2026 characterisation cited.
- SEN55-SDN-T: PM, VOC, NOx, RH and T over I2C. Ordered locally, not received or integrated (Methodology).
- Optocouplers: received 2026-09-28 (per the student in the transcript). The part number is not recorded yet. Their original purpose, from the session transcript in early September, was to isolate a tap on the motor's Hall-effect sensor (5 or 12 V) from the ESP32 GPIO, so the telemetry unit can measure motor speed without a direct electrical connection to the drivetrain. The vac-work DAQ plan uses the same approach (12 V divider/opto) for its vehicle-state inputs. Confirm the part number and the signal before wiring (D31).

### 4.7 Report, GA form and presentation

Report (Report/, main file Project Report Template.tex)
- Chapters: Introduction, Literature Review, Methodology, Results (placeholders), Discussion and Conclusions (one paragraph each), Recommendations, Appendix A (GA, AI use, repo) and Appendix B (supporting figures).
- Current PDF, Report/OKTSAM001 SW7 Report Draft.pdf, built 28 Sept: 85 pages. Front matter p1 to 10, main body p11 to 72 (about 62 pages against a 50-page limit), bibliography p73 to 80 (70 entries), appendices p81 to 85.
- The note "Draft abstract, to be revised once field results are available." is present and must stay.
- No ethics mentions and no em dashes in Report/*.tex (checked 28 Sept).

GA form
- Submitted and signed by the supervisor as satisfactory ("DP satisfied"; signed PDF committed in 18d7e24).
- GA4 states 733 candidate sources with 114 confirmed DOIs.
- GA6 text is now stale: it says the detector was withheld (see F13).

Presentation (Presentation/)
- SW7_Final_Presentation.pptx: 12 slides, 16:9. SW7_Poster_A1.pptx: 1 page. Built with pptxgenjs from Presentation/source (build_deck.js, build_poster.js). Talking points are in SW7_Talking_Points.md.
- Slide 10 says the detector is "Implemented, not yet run on live data" (out of date).
- Slide 12 lists "Build and evaluate the HUD" (out of date if D26 is agreed).

---

## 5. Findings and open issues

| # | Date | Finding | Status |
|---|---|---|---|
| F1 | 09-16 | qio_opi flash setting boot-looped; the ROM banner reports DIO; PSRAM undetected under dio_opi and dio_qspi | Flash resolved (F4); PSRAM open, not needed |
| F2 | 09-16 | GNSS response had 9 fields, not the 13 expected (manual v1.09 lists 16) | Parser corrected; units unconfirmed |
| F3 | 09-19 | Two MPU6050s disagreed by about 5 to 8 percent at rest (10.35 to 10.39 vs 9.55 to 9.60 m/s2) | Fixed by calibration (D7) |
| F4 | 09-25 | 16 MB partition table with 8 MB flash size boot-looped | Fixed (D23, 6d3a080) |
| F5 | 09-25 | Resting magnitudes 9.93 and 10.10 m/s2 (1.3 and 2.9 percent above g) with the target board's stored factors 1.0390 and 1.0245 | Open: recalibrate while stationary (v0.5.0 !recal) |
| F6 | 09-25 | Max inter-sample interval 25 to 30 ms (5 ms nominal) in 1 of every 6 two-second windows, on both IMUs together. Starts about 30 s after boot, recurs every 12 s, coincides with flash writes; no samples lost | Suspected cause, unconfirmed: test with !log off. Remedies: buffer writes, or put acquisition code in IRAM |
| F7 | 09-25 | Logging step runs every 12 s, not 10 s, because each GNSS poll waits about 3 s to time out | Open |
| F8 | 09-25 | MQTT initial connect failed (CMQTTSTART) with no automatic retry | Fix written in v0.5.0, untested |
| F9 | 09-25 | No GNSS fix indoors (0 polls with a fix in the bench log) | Open: outdoor test |
| F10 | Methodology | LTE registration intermittent indoors (PDN deactivated before an MQTT connect) | Open: vehicle test |
| F11 | 09-28 | Labelmap "???" shifted every class by one; Picamera2 RGB888 is B,G,R | Fixed (4a62173) |
| F12 | 09-28 | Alert toggled on single missed frames: 16 activations in 47 s | Fixed with hysteresis; tested offline only |
| F13 | 09-28 | Stale text elsewhere. README.md says the detector is untested live and the HUD not built. GA form GA6 says the detector was withheld. Deck slide 10 says not run live. Report Methodology line 275 says "the physical IMUs are not yet connected" | Open (README and deck to fix; the GA form is signed, leave as is) |
| F14 | 09-28 | Live view looks reddish; possibly a camera with no IR-cut filter | Open (colour check, --tuning ov5647_noir.json) |
| F15 | 09-28 | Report main body about 62 pages against a 50-page limit | Open |
| F16 | 09-28 | Report says the sync task "toggles a GPIO output once per second (2 s period, edges 500 ms apart)". The code toggles every 500 ms (1 s period); edges 500 ms apart matches the code | Fixed 28 Sept: Methodology now says every 500 ms, a 1 s period, two edges per second |
| F17 | Record | Commit c5f5b55 message says the deck has 15 slides; the file and talking points have 12 | Noted; file wins |
| F18 | Record | Ten commits (5e3e6d9 to 20d2fa6) carry a Co-Authored-By trailer, against D22 | Noted, no action |
| F19 | Record | CameraDetection/README.md still has an "Ethics status" section with the protocol number | Allowed in the README; must not reach the report |
| F20 | 09-28 | Report was 12 pt with 1.5 spacing; the handouts require Times New Roman 11 pt, single spacing, at most 50 content pages | Fixed: now 46 content pages |
| F21 | 09-28 | Body prose is about 17,931 words (19,370 on 29 Sept after capturing the new work) (Methodology 12,656) against 10,000 to 15,000 in GA6, and Results, Discussion and Conclusions are still mostly placeholders | Open: cut Methodology by roughly 5,000 words while writing the results chapters |
| F22 | 09-28 | Lecture 2 slide 7 lists an ethics approval letter for the report appendix, which conflicts with the student's rule of no ethics mention in the report (D20) | Open: ask the supervisor |

---

## 6. Report sync table

Checked against the evidence on 2026-09-28.

| Report section | What it says now | Matches latest evidence? |
|---|---|---|
| Title, abstract (Project Report Template.tex) | Telemetry unit and windshield HUD; 200 Hz dual IMU; camera about 7 fps, distance uncalibrated; 5 to 8 percent gap calibrated; working MQTT path; draft-abstract note | Yes for measured facts. HUD in title kept until the supervisor agrees (D26) |
| 1 Introduction (objectives, RQ table, scope) | Four RQs; RQ1 bench-verified, RQ2 (HUD) outstanding, RQ3 bench-verified with LittleFS read-back outstanding, RQ4 self-test only; scope includes SEN55, camera, 8x8 ToF, HUD, LTE | Yes, but the HUD scope and RQ2 depend on D26 (pending) |
| 2 Literature Review | Review only; VL53L5CX chosen (2.8) | Yes |
| 3 Methodology, flash and PSRAM | Boot loop, DIO diagnosis, later fixed with 16 MB + DIO, 3.5 MB LittleFS mounted | Yes |
| 3 Methodology, ride characterisation (line 275) | "Since the physical IMUs are not yet connected" | No, stale (F13) |
| 3 Methodology, calibration and fusion | Factors 0.9773/0.9901 (bare board) and 1.0390/1.0245 (target board); fusion rules; 5/5 self-tests; skew under 1 ms; 9.93/10.10 resting; 149 windows | Yes (corrected 28 Sept) |
| 3 Methodology, time sync | "every 500 ms (a 1 s period, so two edges per second)" | Yes (F16 fixed 28 Sept) |
| 3 Methodology, BMS | Intermittent connection | Yes (no newer test) |
| 3 Methodology, environmental (SEN55) | Ordered locally, not received | Yes |
| 3 Methodology, Pi camera and hazard detection | Pi 4 not Pi 5 and why; OV5647; casing credited to the project with a second casing; live run 430/419 frames, fixes, 0.50 to 0.73, 16 in 47 s, hysteresis; only person confirmed | Yes. Missing: live view, /alerts, latency instrumentation, service, dashboard page |
| 3 Methodology, ToF | VL53L5CX sourced, not received | Yes (receipt unknown) |
| 3 Methodology, MQTT and local logging | Placeholder fail, test.mosquitto.org publish, intermittent LTE; LittleFS details; flash stall 25 to 30 ms every 12 s, cause suggested not proven | Yes. v0.5.0 retry and !log off test not yet included (not tested) |
| 4 Results | One-line placeholders per subsystem, including 4.7 HUD | Placeholders; to fill after the field test |
| 5 Discussion, 6 Conclusions | One paragraph each on what they will cover | Placeholders |
| 7 Recommendations | Generic road-obstacle detection future work (YOLOv8-n and others, not adopted) | Yes |
| Appendix A, B | GA mapping, repo URL, AI use; four supporting figures | Yes |
| Page budget | Main body about 62 pages | Over the 50-page limit (F15) |

---

## 7. Tooling

### Build the report (Tectonic)
Tectonic is not on PATH. It has been run from the scratchpad; its cache is at C:\Users\0geda\AppData\Local\TectonicProject. The recipe:
1. Make an empty build folder (for example in the scratchpad).
2. Copy Report/*.tex, Report/*.png, Report/figures/ and Report/evidence/ into it.
3. In the build folder, copy "Project Report Template.tex" to SW7_Report.tex.
4. Run `tectonic --outdir <dir> SW7_Report.tex`.
5. Check the output for undefined references and errors.
6. Copy SW7_Report.pdf to "Report/OKTSAM001 SW7 Report Draft.pdf".

The template header mentions pdflatex; Tectonic (XeTeX) is what produced the current PDF (xdvipdfmx producer). Under XeTeX the preamble loads the real Times New Roman through fontspec; under pdfLaTeX it falls back to newtx, a Times clone. Word count: run the prose counter over Chapters 1 to 7 (tables, figures, captions and code excluded) and update the line under the declaration.

### Flash the ESP32
From HUDTelemetryUnit/:
```
pio run              # build
pio run -t upload    # flash (COM10)
pio device monitor   # serial at 115200
```
The Makerfabs board needs ARDUINO_USB_MODE=1 and ARDUINO_USB_CDC_ON_BOOT=1 (already in platformio.ini). With v0.5.0 flashed, type !status, !log off, !log on, !mqtt or !recal in the monitor (untested).

### Reach the Pi 4
The student runs Pi commands. Laptop PowerShell, from the repo root:
```
ssh -i ~/.ssh/pi4_camera_key ogeder@<pi-ip>
scp -i ~/.ssh/pi4_camera_key CameraDetection/hazard_detector.py ogeder@<pi-ip>:~/hazard_detector/
```
Get <pi-ip> from `hostname -I` on the Pi. .local names did not resolve on the phone hotspot; pi4-camera.local should work on a normal network. The Camera Test Runbook artifact page holds the current copy-paste blocks.

### Run the detector (Pi)
```
cd ~/hazard_detector && source venv/bin/activate
python3 hazard_detector.py --duration 60
python3 hazard_detector.py --preview                         # http://localhost:8080
python3 hazard_detector.py --preview --preview-host 0.0.0.0  # http://<pi-ip>:8080 and /alerts
```
Options: --verbose, --timing-log file.csv, --threads N, --tuning ov5647_noir.json, --focal-length-px N.

Service (after CameraDetection/deploy/INSTALL.md):
```
sudo systemctl enable --now hazard-detector
journalctl -u hazard-detector -f
sudo systemctl stop hazard-detector
```
Stop the service before running the detector or rpicam-hello by hand.

### Where logs live
- ESP32 bench captures: BenchTest/logs/ (currently 2026-09-25_bench_fusion_shake.log).
- On the ESP32: /telemetry.log in LittleFS (read-back not yet built).
- Detector alerts: alerts.jsonl in the working directory on the Pi. Timing CSV wherever --timing-log points. Service output in journald.
- Research pipeline: Research/research.db, Research/digests/, Research/gap_ledger.json.
- Camera/ML papers: Report/references_pdf/camera_ml (15 PDFs, README, refs_camera_ml.bib).
