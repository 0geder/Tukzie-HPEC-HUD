# Changelog

Every change to this repository, however small, with the reason for it.

How to read this file:
- Sections are dated, newest first. Each date opens with a one-line summary of the day.
- Under each date, each commit has its own heading: short hash and subject, newest first.
- Each bullet is one change: the file (and, where useful, the function or report section), what changed, and why.
- The reason comes from the commit message, code comments, the report text or PROJECT_LOG.md (decisions D1 to D32, findings F1 to F19). Where none of these records a reason, the bullet says "reason not recorded".
- Uncommitted work in the working tree sits under "Unreleased" at the top.

New entries are appended by the progress-scribe agent (.claude/agents/progress-scribe.md).

---

## Unreleased

- `Poster Templates/` (untracked): four reference files, "2. Scientific Poster Design _Cornell U.pdf", "SAUPEC Poster 2017v3 A4.pdf", "Spanish Workshop Poster_v5.pdf" and "Spanish Workshop Poster_v5.pptx". Why: reason not recorded. D25 says the A1 poster was built in the UCT poster-template style, which these may relate to.

---


## 2026-09-30

GNSS confirmed outdoors; three firmware faults found and fixed; signal-loss recovery tested; test procedures written.

### (this commit) Stand-in ToF running on the Pi

- Pi: Blinka and the VL53L0X driver installed in the detector's venv; `tof_probe.py` and `tof_reader.py` deployed. Micromouse sensor board wired through its J2 header. Probe: VL53L0X. Reader: three sensors at about 31 readings/s each. Why: stand-in for the VL53L5CX (not yet arrived).
- `BenchTest/logs/2026-10-01_tof_three_sensors.csv`; TEST_PROCEDURES C7; Methodology ToF stand-in result; Appendix C row. Why: record the first run.

### (80b3c77) Firmware v0.6.1 to v0.6.3: log read-back, JSON NaN fix

- `HUDTelemetryUnit/src/main.cpp` v0.6.1 to v0.6.3: `!log dump` (records as LOG|index|length|record, paced 4 ms per record) and `!log clear`. Why: the stored log had never been read back, and it was at 2.2 MB of the 3 MB cap, where it would be deleted.
- v0.6.3: nan and inf in the telemetry JSON written as null. Why: the read-back found 5,545 of 6,020 records invalid as JSON (position fields before a fix); the same text went to MQTT.
- `BenchTest/log_dump.py`: multi-pass dump with index and length checks. Why: a single pass lost records to other tasks' output on the same serial link. `BenchTest/logs/2026-10-01_telemetry_log_dump*.jsonl`: the recovered log (also holds the only complete BMS readings so far, 14 records from 30 Sep).
- `Report/Methodology.tex`: read-back result replaces "not yet done"; BMS checksum confirmed from the log. TEST_PROCEDURES T10 and T7; Appendix C row.

### (55dee14) Firmware v0.5.4 and v0.6.0: BMS checksum, buffered log, signal quality, Hall counter

- `HUDTelemetryUnit/src/main.cpp` v0.5.4: BMS checksum now sums status, length and data, not the register byte; rejected frames printed raw. Why: on the vehicle the only three frames received were all rejected; the query frame's own checksum shows the rule.
- v0.6.0: log lines buffered in RAM and written in one append about once a minute (and before `!recal`); `!log flush`; flush timing in `!status`. Why: each flash write pauses the IMU tasks (33 to 40 ms every 10 s in v0.5.0); now about once a minute.
- v0.6.0: `AT+CSQ` every publish cycle, in `!status` and the JSON (`cell.csq`). Why: map coverage on the road test and explain failed publishes.
- v0.6.0: Hall pulse counter (PCNT, both edges, 12.5 us filter, read every second), in `!status` and the JSON (`hall.eps`, `hall.rpm`, null until the pole-pair count is set). Bench loopback on the sync pin until the optocoupler tap is wired. Why: motor speed for RQ4 and powertrain monitoring.
- `BenchTest/v060_bench_test.py`, `BenchTest/bms_probe.py`: new tests. `TEST_PROCEDURES.md` T9 and T7 result. `Report/Methodology.tex`: BMS checksum fault, Motor speed tap section, buffered-log result, I2C voltage, ToF stand-in. Appendix C row.

### (b1b3c56) Camera latency measured, ToF probe, optocoupler identified

- Pi: current `hazard_detector.py` deployed (the Pi had an older copy without `--threads` and `--timing-log`; the old copy kept as `hazard_detector_old.py`). Why: needed for C4.
- `BenchTest/logs/2026-09-30_c4_latency/`: three one-minute latency runs. `Report/Methodology.tex`: results and Table tab:camera-latency replace the "not yet measured" sentence; `TEST_PROCEDURES.md` C4; Appendix C row. Why: the brief asks for edge latency.
- `CameraDetection/tof_reader.py`: reads one or three VL53L0X micro-sensors, waking them one at a time through XSHUT to give each its own address. Why: the micromouse schematic identifies the stand-in part as VL53L0X; untested until the Pi's I2C is on.
- `CameraDetection/tof_probe.py`: identifies the stand-in ToF chip from its model-ID register. Why: the micromouse sensors are unmarked, and each chip needs a different driver.
- `Planning/camera-tof-next-prompt.md`: the plan for this piece of work. `Planning/mounting-and-enclosures.md` added earlier.
- `PROJECT_LOG.md`: optocoupler identified from photos as a bestep PC817 module. Why: closes the part-number question in D31.

### (a03861a) Pi sync-edge logger, I2C voltage check

- `CameraDetection/sync_logger.py`: new Pi-side logger for the ESP32 sync pulse, using gpiod kernel edge timestamps on the monotonic clock (the camera's clock), with a gpiozero fallback and an interval summary. Why: the earlier logger was not in the repo, and the road test needs it.
- `BenchTest/logs/2026-09-30_sync_edges_run*.csv`: first logged sync runs on the Pi (run 1 noisy for 16 s, run 2 clean, 500.06 ms median). Why: evidence for C6.
- `BenchTest/TEST_PROCEDURES.md`: C6 wiring, logger command and pass criteria; new T8 for the I2C line voltage (about 3.3 V on the bench). Why: record how the link is tested and the voltage result.

### (9e4387d) GNSS parser, modem power-up, fast reconnect, test procedures

- `HUDTelemetryUnit/src/main.cpp` v0.5.1: GNSS parser rewritten for the real reply (17 fields, decimal degrees), locating the hemisphere letter and reading fields relative to it; satellites, course, HDOP, date and time added to the fix. Why: the old 9-field mapping, fitted to an empty no-fix reply, read satellite counts as the position (first fix reported at 0.25, 0.10).
- v0.5.1: strict shape checks and a 100 m/s jump check before a reply is accepted as a fix; `!gnssraw` prints the raw reply on every poll. Why: replies garbled by a competing query were otherwise accepted; the raw printing avoids that competition in future tests.
- v0.5.2: the modem power key is pulsed at boot only if the modem does not answer AT. Why: the key toggles the modem, so the unconditional pulse switched a running modem off after a reflash (a whole capture got no replies).
- v0.5.3: the 18-field reply (empty course, one trailing value) is accepted. Why: 18 valid replies were rejected in the v0.5.2 capture.
- v0.5.3: reconnect a few seconds after the modem reports the data connection back (+CGEV ... PDN ACT), with the backoff reset. Why: in v0.5.0 the reconnect waited 36 s for its backoff although the network was back in 2.4 s; now about 5 s.
- `BenchTest/gnss_capture.py`, `BenchTest/signal_loss_test.py`: new test scripts. Why: repeatable GNSS and signal-loss tests.
- `BenchTest/capture_log.ps1`, `BenchTest/analyse_log.py`, `CameraDetection/tests/`, `DashboardIntegration/tests/`: test scripts moved from the scratch folder into the repo. Why: the student asked for the testing to be recorded; every test in TEST_PROCEDURES.md can now be rerun.
- `BenchTest/TEST_PROCEDURES.md`: method, pass criteria, results and evidence for every test. Why: same.
- `Report/Methodology.tex`: new subsection on the outdoor fix and confirmed field layout, the power-key fault, and the signal-loss results; two remaining hard-coded section numbers turned into \ref. Why: record the results; keep references correct.
- `Report/appendixc.tex`: three evidence rows. Why: keep the evidence index complete.

## 2026-09-29

Report captures all implemented work, marked tested or untested; length pass deferred. Firmware v0.5.0 flashed and bench-tested; flash-write stall confirmed.

### (this commit) Note dashboard design references

- `PROJECT_LOG.md`, 4.3 Dashboard integration: two design references the student shared (a Medium article on the evolution of car dashboards and a Figma community autonomous-vehicle dashboard). Why: the student asked for them to be noted, for the dashboard direction replacing the HUD.

### (this commit) Report clean-up pass

- `Report/Methodology.tex`: drafting notes removed or rewritten ("Chapter 2/Chapter 3 as appropriate", "before the report claims which physical pack", "the student observed", "for the report"). Why: they read as carelessness to an examiner (Planning/report-review.md).
- `Report/Methodology.tex`: the credentials remark keeps the fact that the vac-work broker credentials were not copied and drops the reason. Why: out of register for a report.
- `Report/Methodology.tex`: repository log path in running text replaced by a reference to Appendix C. Why: paths belong in the evidence index.
- `Report/Methodology.tex`: five wrong cross-references fixed (Fig 3.1 section number, serial bridge, sync-pin clause, baselining, camera mount); labels added for the AT-command section, the Pi verification subsection and Literature 2.4. Why: they pointed at sections that did not contain what the text claimed.
- All chapter files: chapter labels added and every hard-coded "Chapter~N" turned into a \ref; Introduction's "Chapter 5 (Results)" and Methodology's "Chapter 4" methodology reference corrected. Why: Results is Chapter 4, and \ref keeps numbers right if chapters move.
- `Report/appendixc.tex`: figure reference corrected (the recorded-session figure is in Chapter 3). Why: it said Appendix B.
- `Report/Methodology.tex`, calibration: figures corrected from the 18 Sept session record; the stored factors are shown to imply 10.03 and 9.90 m/s2 at calibration, the target-board first-boot measurements (9.44, 9.57) added, orientation dependence named as the likely cause and the recalibration consequence drawn. Why: the old text's factors could not produce the stated convergence (review finding, confirmed by arithmetic).
- `Report/Methodology.tex`, fusion: the target-board calibration boot is described as recorded. Why: it was in the session record.
- Abstract, deck slide 7, poster, talking points: "5 to 8%" changed to about 8%. Why: the readings were 5.7% high and 2.6% low, about 8% apart.
- `Report/Introduction.tex`: "augmented-reality interface" changed to "head-up driver interface"; IMU rate stated as 200 Hz above the 160 Hz minimum; "MQTT/HTTP over 4G/LTE-M" changed to MQTT over 4G LTE Cat-1. Why: internal contradictions with the rest of the report and the hardware.
- `Report/Project Report Template.tex`: one department name on the cover; HPEC defined in the Terms of Reference; word count 19,687. Why: consistency.
- `Report/Recommendations.tex`: "dissertation" changed to "project". Why: this is a project report.
- `Report/appendixa.tex`: GA appendix rewritten as one paragraph per GA (GA1, 4, 5, 6, 8, 9) with section references, consistent with the student's entries on the signed GA form and the supervisor's comments. Why: the old table was too thin to show how each GA was met.

### (this commit) Firmware v0.5.0 bench test and flash-stall confirmation

- `BenchTest/v050_bench_test.py`: new scripted bench test (reset, commands, 120 s logging on, 120 s off, reconnect). Why: to test v0.5.0 and settle the flash-stall question with a controlled comparison. It closes and reopens the port after the reset because the ESP32-S3's native USB disappears while it reboots (the first attempt failed on this).
- `BenchTest/logs/2026-09-29_v050_bench_test.log`: the recorded session. Why: evidence for the report.
- `Report/Methodology.tex`, local logging: the stall is now confirmed by the logging off/on comparison, with the measured figures. Why: replaces 'strongly suggested, not proven'.
- `Report/Methodology.tex`, v0.5.0 subsection: now records the bench test results and what was not exercised. Why: v0.5.0 is on the board.
- `Report/appendixc.tex`: evidence index row for the new log. Why: keep the evidence appendix complete.
- `PROJECT_LOG.md`: timeline entry. Why: record of the session.

### (this commit) Report: capture the camera, console and firmware v0.5.0 work

- `Report/Methodology.tex`, hazard detection: new parts on alert hysteresis, the live view and latency measurement, the alerts feed with the dashboard page and start-up service, and the colour cast. Why: the student asked to capture everything now and cut later; each part states whether it was tested offline, offscreen or not yet.
- `Report/Methodology.tex`, live telemetry dashboard: paragraph on the combined bench console. Why: same.
- `Report/Methodology.tex`, new subsection on firmware v0.5.0 result-code checking, reconnection and serial test commands. Why: records the latent OK-means-success fault found in the manual and the fixes; states that v0.5.0 is not yet on the board.
- `Report/Project Report Template.tex`: word count updated from 17,931 to 19,370. Why: the new text was added.
- `PROJECT_LOG.md`: timeline entry and F21 updated. `Planning/brief-compliance.md` format rows marked met (previous commit).
- Memory: report policy recorded as capture first, cut later.

## 2026-09-28

Summary: the camera detector ran live for the first time and gained a live view, latency timing, an /alerts endpoint, a boot service and a dashboard page; firmware v0.5.0 was committed; the project log, CLAUDE.md and the progress-scribe agent were added; bench figures in the report and deck were corrected.

### b57f742 Add PROJECT_LOG.md; correct fusion and calibration figures from the bench log

- `PROJECT_LOG.md`: new file with status board, 32 decisions, timeline from 3 Aug, per-subsystem technical breakdown, findings, report sync table and tooling. Why: the student's record of everything done and decided (CLAUDE.md), built from the repo, report, GA form and session transcript.
- `Report/Methodology.tex`, Dual-IMU fusion and recorded session: fused window count changed from 222 to 149, with a note that the log holds 222 fused lines for 149 windows. Why: each window's result is printed once by each sensor task, checked against BenchTest/logs/2026-09-25_bench_fusion_shake.log.
- `Report/Methodology.tex`, recorded session: still-period maximum changed from 0.058 to 0.067 m/s2, and the still period defined as the first 70 s. Why: 0.058 came from the first 48 s only.
- `Report/Methodology.tex`, recorded session: largest peak-to-peak changed from 76.8 to 77.6 m/s2 ("largest peak-to-peak amplitude in any window"). Why: checked against the bench log; 76.8 was the peak-to-peak of the peak-std window only (PROJECT_LOG 4.4).
- `Report/Methodology.tex`, Dual-IMU fusion: resting magnitudes changed from 10.07/9.97 to 9.93/10.10 m/s2 with the stored factors 1.0390 and 1.0245, and the 0.9773/0.9901 factors attributed to the bare dev board. Why: 10.07/9.97 came from a capture not in the repo (F5).
- `Report/Methodology.tex`, Dual-IMU fusion: disagreement range changed from "0.06 to 0.87" to "0.00 to 1.68", and the text now points to the recorded session figure. Why: checked against the bench log (commit message).
- `Report/Methodology.tex`, time synchronisation: the sync task is now described as toggling every 500 ms (1 s period, two edges per second) instead of "once per second (2 s period)". Why: the code toggles every 500 ms (F16).
- `Report/Methodology.tex`, ride characterisation: "Since the physical IMUs are not yet connected" changed to "Before the physical IMUs were connected". Why: the IMUs are now connected (F13).
- `Report/OKTSAM001 SW7 Report Draft.pdf`: rebuilt. Why: to carry the corrections above.
- `Presentation/source/build_deck.js` and `Presentation/SW7_Talking_Points.md`: windows fused changed from 222/222 to 149/149, resting readings from 1.6 and 2.7 to 1.3 and 2.9 percent above gravity, and the calibration note now says the stored calibration was not the one first measured. Why: to match the bench log (commit message).
- `Presentation/source/build_deck.js` and talking points, camera slide: "implemented, not yet run on live data" replaced with "now run on live bench footage at about 7 frames a second and detects a person reliably; other object types and distance calibration still to be tested". Why: the detector ran live on 28 Sept (4a62173).
- `Presentation/source/build_poster.js`: windows fused changed from 222/222 to 149/149. Why: to match the bench log.
- `Presentation/SW7_Final_Presentation.pptx`, `Presentation/SW7_Poster_A1.pptx`: rebuilt. Why: to carry the corrections above.

### dfc6542 ESP32 firmware v0.5.0: MQTT result codes and reconnect, serial commands

- `HUDTelemetryUnit/src/main.cpp`: firmware version set to v0.5.0 (a FIRMWARE_VERSION define). Why: marks this set of changes (D32).
- `HUDTelemetryUnit/src/main.cpp`, MQTT: AT+CMQTTSTART, CONNECT and PUB now wait for their +CMQTTxxx result line and error code instead of treating the first OK as success. Why: the A76XX manual v1.09 section 18.2 returns OK for both success and failure.
- `HUDTelemetryUnit/src/main.cpp`, MQTT: reconnect with backoff (30 s, doubling to 5 min) after a failed connect, three failed publishes in a row, or a +CMQTTCONNLOST / +CMQTTNONET URC, with DISC, REL, STOP teardown first. Why: the bench log shows "Initial connect failed, will not retry automatically" (F8, D32); the manual requires the teardown order.
- `HUDTelemetryUnit/src/main.cpp`, USB console: lines starting with "!" are now local commands (!status, !log off, !log on, !mqtt, !recal); everything else still passes through to the modem. Why: the flash-write stall test (F6) and IMU recalibration (F5) need runtime switches (D32).
- `HUDTelemetryUnit/src/main.cpp`, !recal: erases the stored IMU calibration and restarts so the board recalibrates. Why: resting magnitudes drifted to 1.3 and 2.9 percent above g (F5).
- Status: compiles for esp32-s3-devkitc-1; not flashed or tested on the board (commit message).

### 72ba826 Add progress-scribe agent, CLAUDE.md project rules and the project-log prompt

- `.claude/agents/progress-scribe.md`: new agent that updates PROJECT_LOG.md and the report's affected sentences after each piece of work. Why: to keep the project record and report current with what was measured (agent description).
- `CLAUDE.md`: new project rules: run progress-scribe after each piece of work, no Co-Authored-By line, no em dashes or unnecessary bold, the report never mentions the ethics application or approval, verify every claim, the student runs Pi and ESP32 commands. Why: the student's rules (D20, D21, D22).
- `Planning/progress-log-prompt.md`: new prompt used to build the project log. Why: reason not recorded beyond the subject line.

### ccbcd2a Camera README: document /alerts, timing output, tuning option and the boot service

- `CameraDetection/README.md`: documents GET /alerts, the [timing] console line (p50, p95, max per stage), --timing-log, --threads (default 4), --tuning ov5647_noir.json, --verbose, and points to deploy/INSTALL.md for starting at boot. Why: to document the options added in 4e3da88, 5206a95, 57dd18e and 7b0601f (subject line).

### 7b0601f Front camera page for the dashboard, and a systemd service for the detector

- `DashboardIntegration/front_camera_page.py`: new FrontCameraPage for the vac-work PySide6 dashboard: QtNetwork MJPEG reader showing only the newest frame, /alerts polling, dashboard status colours, reconnect every 3 s, alerts_changed signal. Why: QtNetwork rather than QtWebEngine because the WebEngine view has crashed on the Pi 5 (D30).
- `DashboardIntegration/README.md`: wiring notes (four edits) for the dashboard team. Why: the page is kept outside the dashboard repo so another team's code is not changed (D30).
- Testing: offscreen with PySide6 6.11.2 inside a copy of the dashboard app package (commit message). Not tested on the Pi 5.
- `CameraDetection/deploy/hazard-detector.service`: new systemd unit that starts the detector with --preview at boot and restarts on failure. Why: reason not recorded beyond the subject line; PROJECT_LOG 4.2 lists it as the boot service.
- `CameraDetection/deploy/INSTALL.md`: install notes for the unit. Why: reason not recorded beyond the subject line.

### 57dd18e Hazard detector: GET /alerts JSON (active alerts, same five fields, plus fps and latency) for the dashboard

- `CameraDetection/hazard_detector.py`, preview server: new GET /alerts route returning JSON {active, fps, latency_ms}, with no-cache and CORS headers. Why: for the dashboard's Front camera page (subject line).
- `CameraDetection/hazard_detector.py`, `set_alerts()`: publishes only the same five fields as the alert log, sorted nearest band first. Why: "same five fields as the alert log, nothing else about the scene" (docstring).
- `CameraDetection/hazard_detector.py`, main loop: keeps an active_record per class, set on each logged "active" alert and removed when the alert clears. Why: to know which alerts are active for /alerts (code comment).

### 0e5656b Add camera integration prompt: colour check, detection coverage, latency target, calibration, service, dashboard

- `Planning/camera-integration-prompt.md`: new prompt for the next camera phase, listing what was verified on 28 Sept and the open work (colour check, detection coverage, latency target, focal-length calibration, service, dashboard) and the items that need the supervisor. Why: to hand the next phase to a new session (file header: "Paste everything below the line into a new session").

### 5206a95 Hazard detector: --tuning option for a camera with no IR filter (ov5647_noir.json)

- `CameraDetection/hazard_detector.py`: new --tuning option that loads a Picamera2 tuning file and prints which one is in use; default is the standard tuning. Why: the live view looks reddish, possibly a camera module with no IR-cut filter (F14; help text).

### 4e3da88 Hazard detector: non-blocking live view, per-stage latency measurement, 4 inference threads

- `CameraDetection/hazard_detector.py`, live view: drawing and JPEG encoding moved into its own thread, which skips stale frames. Why: it ran inside the detection loop, so detection waited on it.
- `CameraDetection/hazard_detector.py`, stream: small socket buffer. Why: a slow link then drops frames instead of lagging.
- `CameraDetection/hazard_detector.py`, timing: sensor-to-result latency from each frame's SensorTimestamp, printed every 5 s as p50/p95/max per stage. Why: SensorTimestamp is ns since boot on the same clock as time.monotonic_ns, so it gives true sensor-to-result latency.
- `CameraDetection/hazard_detector.py`: new --timing-log option for a per-frame CSV. Why: reason not recorded beyond the commit message.
- `CameraDetection/hazard_detector.py`: per-frame detection lines moved behind --verbose. Why: reason not recorded.
- `CameraDetection/hazard_detector.py`: resize switched to bilinear. Why: reason not recorded.
- `CameraDetection/hazard_detector.py`: new --threads option for inference, default 4. Why: reason not recorded.

### 54a8baf Add verified camera/ML reading library: 15 papers, beginner reading guide and BibTeX

- `Report/references_pdf/camera_ml/`: 15 papers added (COCO, SSD, MobileNets v1 and v2, quantisation, YOLO and a YOLO review, EfficientDet, Cityscapes, RDD2022, traffic cones, monocular distance, CMVision, transferable features, an edge benchmark). Why: a verified reading library for the camera and ML work (subject line); reason for each paper not recorded.
- `Report/references_pdf/camera_ml/README.md`: beginner reading guide. Why: reason not recorded beyond the subject line.
- `Report/references_pdf/camera_ml/refs_camera_ml.bib`: BibTeX for the 15 papers. Why: reason not recorded beyond the subject line.

### 4a62173 Hazard detector: first live run fixes, live view, alert hysteresis

- `CameraDetection/hazard_detector.py`: labelmap's leading "???" entry no longer shifts class names. Why: the first live run showed every class name shifted by one, so a person was never reported (F11, D27).
- `CameraDetection/hazard_detector.py`: Picamera2 RGB888 frames converted from B,G,R to R,G,B before inference. Why: Picamera2 RGB888 buffers are B,G,R while the model expects R,G,B (F11, D27; Picamera2 manual p. 21).
- `CameraDetection/hazard_detector.py`: tries ai-edge-litert (LiteRT) first. Why: tflite-runtime has no Python 3.13 wheels (D29).
- `CameraDetection/hazard_detector.py`: optional --preview live view (MJPEG over HTTP, never saved), local by default, --preview-host 0.0.0.0 for other devices on the same network. Why: reason not recorded beyond the commit message. Network exposure is pending the supervisor (PROJECT_LOG status board).
- `CameraDetection/hazard_detector.py`, alerts: clear only after 5 missed frames (CLEAR_AFTER_MISSED_FRAMES = 5), re-log when the object holds a nearer band for 3 frames, nearest band wins within a frame. Why: 16 activations in 47 s for one standing person when clearing on one missed frame (F12, D28). Tested offline only.
- `CameraDetection/hazard_detector.py`: prints bbox_width_px, and the focal-length formula comment is fixed. Why: for focal-length calibration (commit message).
- `CameraDetection/hazard_detector.py`: SIGTERM stops cleanly, the run clock is monotonic, and timestamps carry a UTC offset. Why: reason not recorded.
- `CameraDetection/README.md`: status updated with the live-run results. Why: the detector had now run live.
- `Report/Methodology.tex`, Pi camera provisioning: the real-time role is now described as "the later real-time detection role" rather than one "not required". Why: the detector now runs live.
- `Report/Methodology.tex`, hazard detection: "implemented but deliberately not executed against live camera data" replaced by "first processed live camera frames, on the bench on 28 September 2026". Why: the live run happened.
- `Report/Methodology.tex`, hazard detection: alert rule now states three consecutive frames to raise, re-log on a nearer band held three frames, clear after five absent frames. Why: matches the new hysteresis (D28).
- `Report/Methodology.tex`, status at time of writing: adds the live-run results (Pi 4, 640x480, LiteRT, about 7 fps over two 60 s runs of 430 and 419 frames) and the two input faults found. Why: the live run happened.
- `Report/Project Report Template.tex`, abstract: detector now "implemented and run on live bench footage at about 7 frames per second". Why: the live run happened.
- `Report/References.tex`: new \bibitem picamera2manual, with a comment recording the manual page checked. Why: cited for the B,G,R buffer order.
- `Report/OKTSAM001 SW7 Report Draft.pdf`: rebuilt. Why: to carry the report changes.

---

## 2026-09-25

Summary: dual-IMU fusion was added and verified live after the boot loop was fixed; all project files were brought into the repo; a Web Serial dashboard and a recorded 150 s bench session went into the report; figures moved to an appendix; the deck and poster were built.

### c5f5b55 Add final presentation deck, A1 poster and talking points

- `Presentation/SW7_Final_Presentation.pptx`: final presentation deck, 16:9. The commit message says 15 slides; the file and talking points have 12. Why: 12 is the course limit (D25, F17).
- `Presentation/SW7_Poster_A1.pptx`: A1 poster in the UCT poster-template style. Why: reason not recorded beyond the subject line (D25 names the style).
- `Presentation/SW7_Talking_Points.md`: speaker notes exported from the deck. Why: reason not recorded beyond the commit message.
- `Presentation/source/build_deck.js`, `build_poster.js`, `render.ps1`: generators (pptxgenjs) and render script. Why: so the deck and poster are rebuilt from source (commit message).
- `Presentation/source/assets/`: bench_labelled.png, casing_labelled.png, uct_banner.jpg, uct_logo.png, vibration_chart.png. Why: images used by the deck and poster; reason not recorded.
- Slide 12 is a placeholder for field-test results. Why: the field test has not happened (commit message).

### 4f2aff7 Report: move four supporting figures (nameplate, board pinout, live dashboard screenshot, unprinted OpenSCAD bracket) to a Supporting Figures appendix

- `Report/Introduction.tex`: vehicle nameplate figure removed from the chapter; the reference now points to Appendix B. Why: reason not recorded beyond the subject line; the main body was over the page limit (F15).
- `Report/Methodology.tex`: Makerfabs pinout, live dashboard screenshot and unprinted OpenSCAD bracket figures removed from the chapter; references now point to Appendix B. Why: reason not recorded beyond the subject line; see F15.
- `Report/appendixb.tex`: chapter renamed from "Addenda" to "Supporting Figures" (label app:figures) and now holds the four figures. Why: to receive the moved figures.
- `Report/Project Report Template.tex`: \include{appendixb} added. Why: the appendix was not previously included.
- `Report/OKTSAM001 SW7 Report Draft.pdf`: rebuilt.

### 46377a3 Record a 150 s bench session from power-up; add live dashboard and recorded-session figures, boot self-test excerpt, and the flash-write timing and GNSS poll findings to the report; add log replay to the dashboard

- `BenchTest/logs/2026-09-25_bench_fusion_shake.log`: new 150 s session from power-up, still then disturbed by hand; the header notes the planned 50 to 70 s cues were not heard. Why: a recorded session to evidence the fusion results (subject line).
- `BenchTest/live_telemetry.html`: new replay() that feeds a recorded log through the same parser using the recorded times. Why: "so a saved session can be viewed exactly as it looked live" (code comment).
- `BenchTest/live_telemetry.html`: chart time labels show absolute seconds in replay and use 10 s steps for windows of 60 s or less. Why: to label a replayed session; reason not otherwise recorded.
- `BenchTest/live_telemetry.html`: link status text changed from "connected"/"not connected" to "linked"/"no link". Why: reason not recorded.
- `Report/Methodology.tex`, GNSS: new paragraph explaining that the modem start-up takes about 27 s, polls then time out indoors, and the statistics count only answered polls, so zero polls does not mean polling stopped. Why: finding from the recorded session (F7, F9).
- `Report/Methodology.tex`: new subsection "Live telemetry dashboard and a recorded bench session" with the dashboard figure, the recorded-session figure and the boot self-test excerpt (both self-tests PASS, stored scales 1.0390 and 1.0245). Why: to report the session (subject line).
- `Report/Methodology.tex`, recorded session: results stated as 222 fused windows, still median 0.041 and max 0.058 m/s2, peak 9.35 m/s2, peak-to-peak 76.8 m/s2, 200.0 to 200.5 Hz, no drops. Why: from the log. Several of these figures were later corrected in b57f742.
- `Report/Methodology.tex`, local logging: used space grew from 12 KB to 56 KB across later boots. Why: evidence that records are being written.
- `Report/Methodology.tex`, local logging: new paragraph on the flash-write stall: max inter-sample interval 25 to 30 ms in one window in six on both IMUs, from about 30 s after boot, every 12 s, coinciding with flash writes; no samples lost. Why: found in the recorded session (F6, F7). Cause suggested, not proven.
- `Report/figures/live_dashboard.png`, `Report/figures/recorded_session.png`: new figures. Why: for the new subsection.
- `Report/OKTSAM001 SW7 Report Draft.pdf`: rebuilt.

### 6e871a1 Add browser live-telemetry dashboard (Web Serial): fused and per-IMU features, acquisition health, GNSS/BMS status, rolling charts, raw log

- `BenchTest/live_telemetry.html`: new Chromium Web Serial page showing fused and per-IMU features, sample rate and drops, GNSS/BMS status, free memory, self-test results, rolling plots of vibration and disagreement, and a raw log. Why: to view the telemetry as it is produced, with no installation (report, Live telemetry dashboard subsection).

### f2838d1 Report: document dual-IMU fusion with live results, local flash logging, and the flash-config boot-loop fix

- `Report/Methodology.tex`, flash and PSRAM: new paragraph on the boot loop with the 16 MB partition table and 8 MB flash size, fixed by 16 MB and DIO; LittleFS mounted for the first time; PSRAM type left at default. Why: documents the fix in 6d3a080 (D23, F4).
- `Report/Methodology.tex`: new subsection "Dual-IMU fusion": equal-weight mean, per-sensor crest factor and crossings, disagreement figure, 50 percent overlap rule, 3 s fallback, five self-tests passed, skew below 1 ms. Why: documents 8fb96f3 (D24).
- `Report/Methodology.tex`, Dual-IMU fusion: resting magnitudes of 10.07 and 9.97 m/s2 reported as drift since calibration, with recalibration planned before field testing. Why: found in a live capture. Later replaced in b57f742 because that capture is not in the repo (F5).
- `Report/Methodology.tex`: new subsection "Local logging to internal flash": LittleFS instead of microSD, JSON line every 10 s regardless of MQTT, 3 MB cap, no rotation or replay yet. Why: the microSD chip select reaches GPIO10 only through R23, marked not populated (D14).
- `Report/OKTSAM001 SW7 Report Draft.pdf`: rebuilt.

### 6d3a080 Fix boot loop on the Makerfabs board: set 16MB flash size and DIO mode to match the 16MB partition table; LittleFS now mounts and dual-IMU fusion verified live

- `HUDTelemetryUnit/platformio.ini`: board_upload.flash_size = 16MB and board_build.flash_mode = dio re-enabled. Why: back on the Makerfabs board, the 16 MB partition table boot-looped (RTC_SW_SYS_RST) with the devkit default of 8 MB; the ROM banner reports DIO (D23, F4).
- `HUDTelemetryUnit/platformio.ini`: board_build.arduino.memory_type left commented out. Why: it is the setting implicated in the earlier boot loop, and the firmware does not use PSRAM (code comment).
- Result: LittleFS mounts and dual-IMU fusion verified live (subject line).

### 18d7e24 Bring all project files into the repo: report source and figures, camera casing STLs, bench and vehicle photos, walkaround video, project brief, ethics application, GA forms, course and hardware references

- `.gitignore`: ignores Report/Signature.png, LaTeX build files in Report/ (aux, log, toc, lof, lot, out) and __pycache__/. Why: keeps the signature image out of the public repo (as in 9c7fd27) and build output out of version control; reason for the build-file entries not recorded.
- `CameraMount/casing/`: RPi_cam_case_bottom.stl, RPi_cam_case_top.stl, RPi_cam_30_deg_corner_mount.stl. Why: the student's own three-part camera casing (D19).
- `GA Tracking Form/OKTSAM001 GA Tracking Form - Signed.pdf` and `OKTSAM001 GA Tracking Form.pdf`: signed and unsigned GA forms. Why: record of the submitted form, signed by the supervisor as satisfactory (PROJECT_LOG status board).
- `GA Tracking Form/templates/`: blank GA form templates, including a copy of "GA Tracking Form incl GA5.pdf". Why: reason not recorded.
- `HUDTelemetryUnit/include/README`, `lib/README`, `test/README`: PlatformIO placeholder READMEs. Why: reason not recorded.
- `Photos/Bench/`, `Photos/Vehicle/`: bench setup and vehicle photos. Why: reason not recorded beyond the subject line; some are used as report figures.
- `Planning/EEE4022S 2026 Topics Winberg_Taken By Samson.pdf`: project brief. Why: reason not recorded beyond the subject line.
- `Planning/Ethical Application.pdf`: ethics application. Why: reason not recorded beyond the subject line.
- `References/Course/`: two EEE4022S lectures and GRT5 Experiment Refinement and Results. Why: reason not recorded beyond the subject line.
- `References/Hardware/`: Raspberry Pi 4 pinout PDF and the ESP32-S3 A7670X board image. Why: reason not recorded beyond the subject line.
- `Report/*.tex`: report source (Introduction, Literature, Methodology, Results, Discussion, Conclusions, Recommendations, References, appendices A and B, main template). Why: to version the report source in the repo (subject line).
- `Report/OKTSAM001 Literature Review Draft 1.pdf`, `Report/OKTSAM001 SW7 Report Draft.pdf`: literature review draft and current report build. Why: reason not recorded beyond the subject line.
- `Report/figures/`: bench_setup.jpg, camera_casing_setup.jpg, camera_mount_render.png, makerfabs_a7670x_pinout.jpg, vehicle_nameplate.jpg; plus Report/model.png and Report/uctLogo.png. Why: figures used by the report.
- `Report/references_pdf/`: five cited sources (SegmentMeIfYouCan, HazardNet, Grounding DINO, SIMCom A76XX AT manual v1.09, a YOLOv8n roadside paper). Why: reason not recorded beyond the subject line.
- `VirtualTukzie/TukzieVideo.mp4`: vehicle walkaround video. Why: reason not recorded beyond the subject line.

### 8fb96f3 Add dual-IMU fusion: overlap-checked mean of both sensors' ride features with a disagreement figure, single-sensor fallback, boot self-test, and fused block in the telemetry JSON

- `HUDTelemetryUnit/src/main.cpp`, `fuseRideFeatures()`: equal-weight mean of RMS, std, peak-to-peak, jerk and speed index; crest factor and crossings stay per sensor. Why: same part, same configuration and same calibration, so equal noise, and inverse-variance weighting reduces to the mean; ratios and counts do not combine by averaging (D24; code comment).
- `HUDTelemetryUnit/src/main.cpp`: disagreement figure |std1 - std2| / mean with a floor (RIDE_FUSION_STD_FLOOR 0.05 m/s2). Why: the sensors sit at different points on the vehicle, so the difference is reported rather than hidden; the floor avoids dividing by near-zero std at rest.
- `HUDTelemetryUnit/src/main.cpp`: a pair is fused only if the windows ended within 0.5 s (RIDE_FUSION_MAX_SKEW_US). Why: the two ride tasks fill windows independently; this guarantees at least 50 percent overlap.
- `HUDTelemetryUnit/src/main.cpp`: falls back to the remaining sensor after 3 s (RIDE_FUSION_STALE_US) and records it in `sources`. Why: rather than silently averaging in stale data (report, Dual-IMU fusion).
- `HUDTelemetryUnit/src/main.cpp`: boot self-test of the fusion on synthetic windows (mean, disagreement, speed index needs both, misaligned pair rejected, stale fallback). Why: to check the fusion logic before trusting it (code comment).
- `HUDTelemetryUnit/src/main.cpp`: rideMux lock around latestRideFeatures1/2 and latestFusedRide, with field-by-field copies. Why: the ride tasks and modem task access these from different contexts, and copies of a volatile struct could be torn mid-update (code comment).
- `HUDTelemetryUnit/src/main.cpp`, telemetry JSON: new "fused" block (src, rms, std, p2p, jerk, dis). Why: to publish and log the fused estimate (subject line).

---

## 2026-09-24

Summary: the hazard detector was brought in line with the ethics conditions, and the GA tracking form was rewritten, corrected, signed and resized over several passes.

### 57a6b03 GA8: add component selection, ordering, bench testing, camera casing, literature work; enlarge GA8 box

- `GA Tracking Form/GA Tracking Form.tex`, GA8: adds that the student selected and ordered components, bench-tested each one, designed and 3D printed the camera casing, and found and read the literature; "and acting on his guidance" added; the ToF example now mentions the trike's narrow front; the sentence about withholding the camera detector until approval was removed. Why: reason not recorded beyond the subject line.
- `GA Tracking Form/GA Tracking Form.tex`: GA8 box enlarged by 30 bp and the GA9 block moved down to match. Why: to fit the longer GA8 text (subject line).

### 1af82b8 GA9: name the specific research-gap claims narrowed and the camera claim that held

- `GA Tracking Form/GA Tracking Form.tex`, GA9: names the 2026 motorcycle telemetry system that narrowed claim one, the reframing of claim two (uplink reliability taken from specifications rather than measured), and the camera claim that survived a targeted search; other wording tightened. Why: reason not recorded beyond the subject line; the claims are G1, G3 and G2 in Research/gap_ledger.json (D11).

### 9c7fd27 Add student signature to the GA tracking form; keep the signature image out of the repo

- `GA Tracking Form/GA Tracking Form.tex`: signature image placed on the form. Why: the form needs the student's signature (subject line).
- `.gitignore`: ignores GA Tracking Form/Signature.png. Why: "Personal signature image: keep out of the public repo" (.gitignore comment).

### fad31ab Correct unsupported claims: GA4 DOI count, GA8 brief claim, GA9 framing; attribute detector categories and log fields to the ethics application, not the approval; log possible change to SW-6 link

- `GA Tracking Form/GA Tracking Form.tex`, GA4: "independently verified 120" changed to "confirmed the DOI of 114 of them against the published title". Why: the earlier count was unsupported (subject line).
- `GA Tracking Form/GA Tracking Form.tex`, GA8: "The brief asked for driver hazard awareness without prescribing a sensor" changed to "When a nearby-object alert for the driver became a requirement". Why: the brief claim was unsupported (subject line).
- `GA Tracking Form/GA Tracking Form.tex`, GA9: "checked the modem's behaviour against" the manual instead of "taught myself the command interface ... rather than relying on forum examples". Why: correct the framing (subject line).
- `CameraDetection/hazard_detector.py`: comments now attribute the category list, distance bands and log fields to the ethics application, noting the approval's condition is "only approved object categories". Why: those details come from the application, not the approval (subject line).
- `CameraDetection/README.md`: same attribution change ("proposed in the ethics application"). Why: as above.
- `Planning/sharaav-interface-definition.md`: update noting Sharaav may no longer need the SW-6 link, since speed and battery data may come from the vac-work dashboard; not yet confirmed. Why: to log a possible change to D15 (subject line).

### 509f218 GA form: replace GA9 ethics sentence with manual-vs-hardware learning, fit GA6 to its box, fix GA4 tilde rendering

- `GA Tracking Form/GA Tracking Form.tex`, GA9: the ethics sentence (with the protocol number) replaced by learning the modem from its 652-page AT manual and treating the manual as a hypothesis to test against the hardware (16 documented GNSS fields vs 9 returned, speed in knots). Why: reason not recorded beyond the subject line; D20 later records that the report must not mention the ethics approval.
- `GA Tracking Form/GA Tracking Form.tex`, GA6: text shortened. Why: to fit its box (subject line).
- `GA Tracking Form/GA Tracking Form.tex`, GA4: "~7\%" changed to "about 7\%". Why: the tilde was rendering wrongly (subject line).

### 5ae6025 Strengthen GA8 response with a concrete independent design decision tied to the brief

- `GA Tracking Form/GA Tracking Form.tex`, GA8: adds independent decisions and specific questions for the supervisor, the choice of an 8x8-zone ToF sensor over a single-point one for left, centre and right discrimination (D17), and withholding the detector until ethics approval; the next-stage sentence shortened. Why: to strengthen GA8 with a concrete independent decision (subject line). The "brief" claim was later corrected in fad31ab.

### 0383316 Enforce ethics approval EBE/03305/2026 conditions in the hazard detector, update GA tracking form

- `CameraDetection/hazard_detector.py`, HAZARD_CLASSES: traffic light, stop sign and fire hydrant removed, leaving person, bicycle, car, motorcycle, bus, truck, dog. Why: those are infrastructure, not in the approved category list; adding them would need its own ethics review (code comment; D16).
- `CameraDetection/hazard_detector.py`: new DISTANCE_BANDS (immediate up to 3 m, warning up to 8 m, monitoring up to 15 m); only the band is logged, not a continuous distance. Why: the application specifies logging an approximate distance band (code comment).
- `CameraDetection/hazard_detector.py`: class-level alert persistence (ALERT_PERSISTENCE_FRAMES = 3). Why: to log reportable alerts rather than every single-frame flicker; the comment states it cannot tell two objects apart.
- `CameraDetection/hazard_detector.py`, `log_alert()`: logs only class, distance_band, confidence, timestamp, alert_status; raw frames never written. Why: matches the data-recording condition (D16).
- `CameraDetection/README.md`: updated to match. Why: as above.
- `GA Tracking Form/GA Tracking Form.tex`: top block filled in (student name, student number, supervisor, dates). Why: reason not recorded beyond the commit message.
- `GA Tracking Form/GA Tracking Form.tex`: all six Student Response entries rewritten in first person with explicit next-stage plans. Why: reason not recorded beyond the commit message.
- `GA Tracking Form/GA Tracking Form.tex`, GA6: adds the fix of an Introduction/Methodology inconsistency about the camera detector. Why: reason not recorded.
- `GA Tracking Form/GA Tracking Form.tex`, GA9: updated to say the detector was withheld until a revised application was approved with conditions. Why: to reflect the ethics approval status (commit message). Replaced in 509f218.

---

## 2026-09-21

Summary: the preliminary SW-6/SW-7 UART agreement was written down and local telemetry logging to internal flash was added.

### 20d2fa6 Add local telemetry logging to internal flash (LittleFS)

- `HUDTelemetryUnit/platformio.ini`: board_build.partitions = default_16MB.csv and board_build.filesystem = littlefs. Why: a real bundled partition table giving about 3.375 MB of LittleFS next to a 6.25 MB app partition (commit message).
- `HUDTelemetryUnit/src/main.cpp`: every telemetry sample appended to /telemetry.log regardless of MQTT connection state. Why: the brief requires telemetry to be logged locally and transmitted, and gap claim G3 (store and forward) had no implementation behind it.
- Storage choice: internal flash rather than the microSD slot. Why: the card's CS line reaches GPIO10 only through R23, marked NC, so there may be no electrical path (D14; platformio.ini comment).
- `HUDTelemetryUnit/src/main.cpp`: log capped and truncated by size; no tracking of published lines yet. Why: scope stated in code; replay on reconnect is the next step, not yet built.
- Status: compiles (1,021,249 of 6,553,600 bytes app flash); not flashed at the time (commit message).

### 9af9724 Record preliminary SW-6/SW-7 UART interface agreement

- `Planning/sharaav-interface-definition.md`: new record of the agreement with Sharaav: 115200 8N1 on GPIO43/44, CSV, speed (km/h) and battery percent from SW-6 to SW-7, SW-6 keeps its own IMU; open items for Wednesday listed. Why: the VIT plan's D5 joint session should have produced this and no record exists, so it is captured as it happens (D15).

---

## 2026-09-20

Summary: GA1 and GA9 updated with the week's evidence.

### bf3d20a Update GA1/GA9 with speed-normalisation, gap-narrowing and ethics evidence

- `GA Tracking Form/GA Tracking Form.tex`, GA1: adds the speed-normalisation catch as a first-principles example and drops the mission sentence. Why: a literature-driven finding corrected before any field data existed (commit message).
- `GA Tracking Form/GA Tracking Form.tex`, GA9: the "persisted through infrastructure failures" line replaced with the research pipeline narrowing two gap claims and the ML ethics audit. Why: stronger, more recent examples of self-correction; the ethics point maps onto the outcome's wording (commit message).

---

## 2026-09-19

Summary: IMU calibration, bench tools and a camera mount were added; the research pipeline was built and used to narrow gap claims; the roughness metric was speed-normalised; the ML ethics position and HUD prior-art claim were recorded.

### fb894ff Record HUD prior-art finding as gap claim G4

- `Research/gap_ledger.json`: new claim G4: no HUD driven by on-board telemetry for any three-wheeled auto-rickshaw-class vehicle, scoped to application and integration only. Why: a targeted prior-art search found only head-down clusters and phone or GPS-fed maker HUDs; HUD optics are long established, so novelty there would not survive scrutiny (D11).
- Recorded in the commit message: a sunlight-readable combiner HUD needs a 50,000 to 100,000 nit source, while MCU-drivable panels reach about 1,000, so direct view should be primary and the combiner secondary, to raise with the supervisor (D13).

### 000783c State the ML ethics position explicitly; exclude ML from version one

- `Planning/ml-ethics-position.md`: new note: ML excluded from version one, detector kept as prepared future work and not run on live data, and the boundary stated so "detection" and "classification" in ride characterisation are not read as ML. Why: the ethics application at the time said no ML in version one, and the Methodology described the detector without that constraint (D12, later reversed by D16).
- Audit recorded in the note: exactly one ML component in the repo (detect.tflite and its script). Why: to establish the ML exposure.

### d6f73bb Speed-normalise the ride roughness metric

- `HUDTelemetryUnit/src/main.cpp`, ride features: new mean-square-over-speed index, with the speed used recorded alongside. Why: raw RMS conflates road roughness with speed because the road-to-acceleration transfer function is speed dependent (D9; Shock and Vibration 2018).
- `HUDTelemetryUnit/src/main.cpp`: index is NaN ("norm=n/a") with no GNSS fix or below 1.0 speed units. Why: dividing by near-zero speed gives a meaningless large number.
- `HUDTelemetryUnit/src/main.cpp`: code note that GNSS speed units (knots or km/h) are unconfirmed. Why: the index is valid for relative comparison only until confirmed.

### 6154050 Add dual-IMU and field-test-methodology searches (RQ6, RQ7)

- `Research/research_pipeline.py`: new search questions RQ6 (dual-IMU sensing) and RQ7 (field-test protocol and calibration). Why: after G1 narrowed onto dual IMUs, that was the least-searched part of the scope; the field test needs reference methodology.
- `Research/research.db`, `Research/sw7_autoreferences.bib`, `Research/digests/digest-2026-09-19.md`, `Research/gap_ledger.json`: updated with 241 new sources (733 total, 309 in BibTeX). Why: output of the new searches.
- Finding recorded: the Shock and Vibration 2018 paper normalises by speed. Why: led directly to d6f73bb.

### c0442ec Review all flagged gap evidence; narrow claims G1 and G3

- `Research/gap_ledger.json`, G1: narrowed to spatially separated dual IMUs, ride-quality framing and the three-wheeler class. Why: an Electronics 2026 open-architecture motorcycle telemetry unit defeats the broad claim (D11).
- `Research/gap_ledger.json`, G3: narrowed from "does not address" to "does not experimentally characterise" uplink reliability. Why: prior work logs locally with a cellular uplink but takes 4G reliability from specifications.
- `Research/gap_ledger.json`, G2: stands. Why: nothing found combines camera hazard awareness with vehicle-dynamics telemetry on this class.
- `Research/gap_ledger.json`: original claim wording kept next to the narrowed text; all 11 flagged items reviewed (3 challenge, 8 neutral). Why: so the narrowing is auditable.
- `Research/apply_review.py`: new script that applies the review to the ledger. Why: reason not recorded beyond the commit message.

### e9c5203 Add automated research pipeline with falsifiable gap ledger

- `Research/research_pipeline.py`: queries OpenAlex, arXiv and Crossref, stores records with provenance in SQLite, deduplicates, emits a dated digest and BibTeX; no Google Scholar. Why: Scholar has no public API, is CAPTCHA-blocked and forbids scraping, so the pipeline would fail silently later (D10).
- `Research/gap_ledger.json`: gap claims stored as falsifiable propositions with an evidence ledger, and each run surfaces items likely to challenge them. Why: a gap that survived attempts to disprove it is defensible.
- `Research/research_pipeline.py`: every DOI re-resolved against Crossref; failures marked UNVERIFIED. Why: 2 of 40 failed on the first run, the kind of error that would reach the report as a bad citation.
- Relevance scoring is a labelled keyword heuristic. Why: it orders a reading queue and does not judge relevance.
- `Research/README.md`, `Research/research.db`, `Research/digests/digest-2026-09-19.md`, `Research/sw7_autoreferences.bib`: pipeline docs and first-run output.

### 5e3e6d9 Add per-sensor IMU calibration, bench-test tooling, and camera mount design

- `HUDTelemetryUnit/src/main.cpp`, `loadOrCalibrateMagScale()`: per-sensor magnitude factor from 200 stationary samples, stored in NVS, rejected outside 0.5 to 2.0, skipped if the sensor is not ready. Why: two nominally identical MPU6050s disagreed by about 7 percent at rest (D7, F3); features use magnitude only, so a scalar is the right scope.
- `HUDTelemetryUnit/src/main.cpp`, RideCharacterizationTask: magnitude multiplied by mag_scale before feature computation. Why: applies the calibration.
- `HUDTelemetryUnit/src/main.cpp`: MQTT broker changed from a placeholder to test.mosquitto.org. Why: a public no-auth broker to prove the AT+CMQTT sequence and cellular path end to end, not for real telemetry (code comment; D4).
- `HUDTelemetryUnit/platformio.ini`: flash_size, flash_mode and memory_type overrides commented out. Why: testing moved to a bare ESP32-S3 dev board whose flash wiring was unverified, and the wrong memory_type had caused a boot loop (code comment).
- `HUDTelemetryUnit/platformio.ini`: comment explaining the ARDUINO_USB_MODE and ARDUINO_USB_CDC_ON_BOOT flags per board (off for the bare board, on for the Makerfabs board). Why: the flags were restored for the Makerfabs board and the reason cost real debugging time (commit message).
- `BenchTest/live_classifier.py`: live bench classifier on the [RIDE] feature stream. Why: bench tooling (commit message).
- `VirtualTukzie/dashboard.html`, `README.md`, `assets/`: browser walkthrough of the vehicle's Gaussian splat with live Web Serial telemetry and placeable markers. Why: bench tooling (commit message).
- `.gitignore`: ignores VirtualTukzie/splat/*.ply. Why: the 113 MB splat exceeds GitHub's 100 MB limit.
- `CameraMount/camera_mount.scad`, `.stl`, renders, `README.md`: parametric friction-fit camera mount. Why: no verified drawing of the camera board's mounting holes could be found (D8). Later superseded by the student's own casing (D19).
- `Planning/virtual-tukzie-digital-twin.md`, `Planning/automated-research-pipeline.md`: planning docs for the walkthrough and the research pipeline. Why: reason not recorded beyond the commit message.
- `GA Tracking Form/GA Tracking Form.tex`, GA4: adds the IMU calibration investigation and drops the inherited-codebase audit sentence. Why: this round of evidence (commit message).
- `GA Tracking Form/GA Tracking Form.tex`, GA5: adds OpenSCAD and the check of an export metric against a reference cube. Why: this round of evidence (commit message).
- Note: this commit carries a Co-Authored-By trailer, against D22 (F18). No action.

---

## 2026-09-16

Summary: the firmware was synced to the full dual-IMU architecture and gained MQTT; the repo was reorganised; the camera detector MVP, gap papers, a new README and GA updates were added.

### 008e524 Update GA1/GA4/GA9 with today's research-gap and self-test evidence

- `GA Tracking Form/GA Tracking Form.tex`, GA1: adds the competitive-landscape and literature audit and the evidenced research gap; wording tightened. Why: today's research-gap evidence (subject line).
- `GA Tracking Form/GA Tracking Form.tex`, GA4: the acquisition-instrumentation sentence replaced by the sine-wave self-test as a controlled experiment. Why: today's self-test evidence (subject line).
- `GA Tracking Form/GA Tracking Form.tex`, GA9: the "read an inherited codebase" sentence replaced by narrowing a novelty claim once prior art was found. Why: today's research-gap evidence (subject line).

### 59fdd82 Add MQTT-over-cellular telemetry publishing

- `HUDTelemetryUnit/src/main.cpp`: publishes ride, BMS and GNSS state as JSON over MQTT with AT+CMQTT, inside the modem task. Why: the modem UART has no locking, so a second task issuing AT commands would corrupt both streams (D3).
- `HUDTelemetryUnit/src/main.cpp`: broker and credentials left as placeholders. Why: the vac-work team's documentation says its credentials must not be shared with an LLM (D4).
- Verified: connect fails cleanly against the placeholder host, no crash or hang (commit message).

### 224e139 Rewrite README with a clear project description and repo guide

- `README.md`: rewritten with project description, subsystem list, repo layout table, hardware list, build commands, status and course context. Why: reason not recorded beyond the subject line.

### 8c25f21 Add reference papers for component-selection and hazard-detection gaps

- `References/Papers/Component Selection Justification/`: five papers (MEMS IMU vibration reliability, ultra-low-cost IMU navigation, ESP32 edge object detection, LoRaWAN in rural Mozambique, LoRaWAN vs NB-IoT). Why: to justify component and market choices (IMU vibration, edge MCU, cellular vs LPWAN).
- `References/Papers/Camera and Object Detection/`: four papers (near-field low-speed perception, two time-to-collision papers, MonoPIC). Why: hazard detection for low-speed vehicles on constrained hardware.
- `References/Papers/Urban Electric Cargo Trike/`: autonomous cycle-rickshaw path planning paper. Why: three-wheeled vehicle hazard context.
- Recorded as empty gaps: no academic comparison of low-cost camera sensors, and no camera hazard detection for cargo trikes or auto-rickshaws. Why: left empty rather than filled with a weak citation (commit message).

### 9d84608 Add camera hazard-detection MVP for the Pi 4

- `CameraDetection/hazard_detector.py`: pretrained COCO SSD-MobileNet-v1 on live frames, reporting road-relevant classes (person, bicycle, car, motorcycle, bus, truck, dog, plus traffic light, stop sign, fire hydrant) with a known-width distance estimate. Why: fits a Pi 4 with no accelerator in real time, with no training (D5).
- `CameraDetection/detect.tflite`, `labelmap.txt`: model and labels. Why: pretrained model, no training required.
- `CameraDetection/README.md`: notes that the focal length is an uncalibrated placeholder and gives the calibration procedure. Why: not yet run on the real camera (Pi unreachable).

### e0a2b11 Reorganize repo into a clear top-level structure

- Paper folders renamed: MoPapers to HPEC and Embedded Computing, "Some more" to General Automotive Sensors, "Comm Syst n Auto Comm" to Automotive Communication Systems, "hpec Telemetry Unit" to HPEC Telemetry Unit, and all moved under References/Papers/. Why: unclear names (commit message).
- Loose top-level PDFs moved into matching folders, with "(root-copy)" added on name collisions; two unsorted papers to Misc (unsorted). Why: consolidate without overwriting any copy.
- `Report/`, `Vehicle Documentation/`: Lit Review Draft 1, Project Report Template and User Manual moved here. Why: group remaining top-level files.
- Added: `GA Tracking Form/GA Tracking Form.tex` and prism-uploads, `Planning/SW7-VIT-001 Rev E` test plan (docx and pdf), the SEN5x datasheet, and 11 papers under Camera and Object Detection. Why: reason not recorded; the commit message describes a pure reorganisation.

### 7d989cb Sync ESP32-S3 firmware with current development state

- `HUDTelemetryUnit/src/main.cpp`: heartbeat stub replaced by v0.4.0: dual-IMU FreeRTOS acquisition at 200 Hz on separate I2C buses (GPIO8/9, GPIO17/18). Why: 200 Hz is above twice the 80 Hz ISO 2631-1 band; separate buses avoid an address clash (D2).
- `HUDTelemetryUnit/src/main.cpp`: GNSS parsing over the A7670X. Why: reason not recorded in the commit; the response had 9 fields, not 13 (F2).
- `HUDTelemetryUnit/src/main.cpp`: hardened JBD BMS BLE interface. Why: reason not recorded in the commit; PROJECT_LOG 4.1 notes a service UUID fix and a reconnect defect.
- `HUDTelemetryUnit/src/main.cpp`: ESP32 to Pi GPIO sync pulse on GPIO15. Why: to relate the two boards' clocks (report, time synchronisation).
- `HUDTelemetryUnit/src/main.cpp`: ride-characterisation task (RMS, std, peak-to-peak, crest factor, jerk, threshold crossings) with a sine-wave self-test. Why: validates the arithmetic independently of sensor hardware (report).
- `HUDTelemetryUnit/platformio.ini`: flash_size 16MB, flash_mode dio, memory_type dio_qspi. Why: the physical module is N16R8; qio_opi boot-looped because the ROM reports DIO; dio_opi fixed the loop but found no PSRAM, as N16R8 uses quad PSRAM (code comment; F1).
- `HUDTelemetryUnit/platformio.ini`: lib_deps added (Adafruit MPU6050, Unified Sensor, BusIO). Why: needed by the IMU code.
- PSRAM still undetected under dio_opi and dio_qspi. Why: left as documented open work rather than guessed at further (commit message).

---

## 2026-08-27

Summary: first firmware for the ESP32-S3 and A7670X modem, plus more papers and the user manual.

### 309fdeb feat: integrate ESP32-S3 A7670X telemetry firmware

- `HUDTelemetryUnit/platformio.ini`: PlatformIO env for esp32-s3-devkitc-1, upload and monitor on COM10 at 115200, ARDUINO_USB_MODE and ARDUINO_USB_CDC_ON_BOOT set. Why: one board gives MCU, LTE and GNSS (D1); flags route Serial to native USB (explained later in 5e3e6d9).
- `HUDTelemetryUnit/src/main.cpp`: v0.2.0: modem UART on GPIO47/48, three-second USB serial wait, version banner, AT / AT+CPIN? / AT+CSQ / AT+CREG? checks with two-second windows, non-blocking heartbeat, PC-to-modem pass-through. Why: modem bring-up (D1); detailed reasons not recorded.
- `.gitignore`, `HUDTelemetryUnit/.gitignore`: ignore worktree copies. Why: "Temporary PlatformIO/Git worktree copies" (.gitignore comment).
- Papers added under HMI, Comm Syst n Auto Comm and Some more; `Lit Review Draft 1.pdf` and `User Manual.pdf` added. Why: "preserve project research and supporting documentation" (commit message).
- `Papers/MoPapers.zip` removed (the unzipped folder stays). Why: reason not recorded.

---

## 2026-08-15

Summary: a large batch of papers added.

### e07e7e0 chore: some more research to add some more papers

- `Papers/MoPapers/`: 22 papers (HPEC, embedded computing, in-vehicle networking, automotive communication, HUD visual cognition). Why: reason not recorded.
- `Papers/MoPapers.zip`: zip of the same papers. Why: reason not recorded.
- `Project Report Template.pdf`: updated. Why: reason not recorded.

---

## 2026-08-12

Summary: three ride-roughness papers added.

### 9f6ff14 chore: gone thru some extra papers

- `Papers/IMU-based ride smoothness and road roughness/`: three papers. Why: reason not recorded.

---

## 2026-08-09

Summary: cargo trike and telemetry papers added and the template updated.

### b1b466e feat: added some more papers

- `Papers/Urban Electric Cargo Trike/`: six papers on cargo tricycle economics and use. Why: reason not recorded.
- `Papers/hpec Telemetry Unit/`: three papers, plus the telemetry preprint moved in from "Vehicle telemetry, IoV and edge monitoring". Why: reason not recorded.
- `Project Report Template.pdf`: updated. Why: reason not recorded.

---

## 2026-08-07

Summary: windshield HUD papers added and the report template started.

### 0aa219a feat: adding some more papers and working on the intro

- `Papers/Windshield HUD/`: eight HUD papers (some duplicates of 4aff494 files). Why: reason not recorded.
- `Project Report Template.pdf`: added. Why: "working on the intro" (subject line).

---

## 2026-08-06

Summary: first literature papers added.

### 4aff494 feat: added some papers to the repo

- `Papers/`: 12 papers on windshield HUDs, IMU road roughness, rough-road detection on microcontrollers, vehicle telemetry and a patent. Why: reason not recorded.

---

## 2026-08-03

Summary: repository created.

### 3dd8ab9 Initial commit

- `.gitignore`: standard C/C++ template. Why: reason not recorded.
- `README.md`: title and one-line description (telemetry and windshield HUD for the TUKZIE Rev 0, UCT EEE4022S 2026). Why: reason not recorded.
