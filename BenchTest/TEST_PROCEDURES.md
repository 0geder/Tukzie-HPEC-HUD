# SW-7 test procedures

How each test in the project is run, what counts as a pass, and where the
result and the evidence are. Every test here can be repeated from the files
in this repo. Results go in the report (Chapter 3 now, Results chapter
later), and raw evidence is indexed in Report Appendix C.

Board: Makerfabs ESP32-S3 A7670X on COM10 (native USB). Only one program
can hold COM10 at a time: close the bench console and any PlatformIO
monitor before running a script.

## Telemetry unit (ESP32)

### T1. Recorded bench session: acquisition and dual-IMU fusion
- Purpose: show 200 Hz acquisition with no drops, and dual-IMU fusion, over a full session from power-up.
- Setup: board on the bench, both IMUs connected, still, then disturbed by hand.
- Method: `BenchTest/capture_log.ps1` records every serial line with its time since reset; `BenchTest/analyse_log.py <log>` summarises it.
- Pass: both IMUs 195 Hz or more, zero dropped samples, every fused window from both sensors, all boot self-tests PASS.
- Result (25 Sep 2026): 200.0 to 200.5 Hz, 0 dropped, 149 of 149 fused windows from both IMUs, skew under 1 ms, 5 of 5 fusion self-tests passed.
- Evidence: `BenchTest/logs/2026-09-25_bench_fusion_shake.log`.

### T2. Firmware v0.5.0 bench test: commands, flash-write stall, MQTT reconnect
- Purpose: check the serial commands, test whether flash logging causes the periodic acquisition gaps, and check MQTT reconnection.
- Setup: board still on the bench, LTE antenna connected.
- Method: `python BenchTest/v050_bench_test.py COM10 <log>`: resets the board, sends `!help` and `!status`, runs 120 s with logging on, sends `!log off` and runs 120 s, then `!log on`, `!mqtt`, `!status`.
- Pass: commands answer; with logging off, no inter-sample gap over 10 ms; MQTT reconnects after `!mqtt`.
- Result (29 Sep 2026): logging on, 33 to 40 ms gaps every 10 s on both IMUs; logging off, worst gap 5.9 ms; no dropped samples; 47 publishes, 0 failed; reconnect in 0.4 s.
- Evidence: `BenchTest/logs/2026-09-29_v050_bench_test.log`.

### T3. GNSS outdoor fix and field-layout check
- Purpose: confirm the modem's +CGNSSINFO field order with a real fix, and measure position accuracy.
- Setup: board outdoors with a clear sky view (rooftop), patch antenna flat with its ceramic face up, board still. Reference position from a phone (Google Maps, long-press the blue dot).
- Method: `python BenchTest/gnss_capture.py COM10 <minutes> <log> raw <ref_lat> <ref_lon>`: turns on the firmware's `!gnssraw` printing, records every raw reply and parsed fix, and measures each fix against the reference. (Mode `query` sends its own AT+CGNSSINFO and is only for older firmware: it competes with the firmware's polling and garbles replies.)
- Pass: a 3D fix (mode 3); parsed position within 10 m of the phone; no damaged reply accepted as a fix.
- Result (29 Sep 2026, first capture, firmware v0.5.0): 3D fix after 51 s; 15 to 16 GPS, 9 BeiDou and 2 to 3 Galileo satellites; HDOP 0.86 to 0.96. The raw reply has 17 fields with latitude and longitude in decimal degrees; the old parser read satellite counts as the position. Well-formed replies were 2.4 and 5.5 m from the phone's position (-33.9800701, 18.4654199). Replies garbled by the competing query were identified and are now rejected by firmware v0.5.1.
- Result (30 Sep 2026, firmware v0.5.2, raw mode): 3D fix after 105 s from a cold start, 23 to 25 satellites, HDOP about 0.9 to 1.5. Over 104 fixes, median 2.7 m from the phone's position, 95% within 11.0 m, maximum 12.3 m. 18 replies had an 18-field layout (empty course, one extra trailing value) that v0.5.2 wrongly rejected; v0.5.3 accepts it.
- Also found: the modem power-key pulse at boot switched an already-running modem off after a reflash (a v0.5.1 capture got no replies at all); fixed in v0.5.2, which pulses only if the modem does not answer AT.
- Still open: speed units (the fix was stationary, 0.000; the manual says knots). Check against a phone's speed on the road test.
- Evidence: `BenchTest/logs/2026-09-29_gnss_rooftop.log` (v0.5.0, query mode), `BenchTest/logs/2026-09-29_gnss_rooftop_v051.log` (v0.5.1, modem switched off, no replies), `BenchTest/logs/2026-09-30_gnss_rooftop_v052.log` (v0.5.2, raw mode).

### T4. IMU calibration
- Purpose: scale each IMU's acceleration magnitude to 9.80665 m/s2 at rest.
- Method: automatic at the first boot with no stored calibration (board must be still for about 1 s). To redo it: `!recal` in the bench console, then keep the board completely still while it restarts. Then `!status` for the stored factors and the ride-vibration card or `[RIDE]` lines for the rest reading.
- Pass: rest reading 9.80 to 9.82 m/s2 on both IMUs.
- Result: bare development board 18 Sep (factors 0.9773, 0.9901, then 9.80 to 9.81); target board first boot 18 Sep (9.4387 and 9.5725 measured, factors 1.0390 and 1.0245); the rest readings later drifted to 9.93 and 10.10, most likely because of orientation. To be redone after mounting on the vehicle, in the final orientation.

### T5. MQTT end-to-end publish
- Purpose: prove the cellular path from the board to a broker.
- Method: broker set to test.mosquitto.org in main.cpp; watch for `[MQTT] Connected.` and publish results. `!status` shows counts.
- Pass: connection and acknowledged publishes.
- Result: first acknowledged publish (+CMQTTPUB: 0,0) on the target board; T2 then gave 47 of 47.

### T6. Signal-loss recovery
- Method: `python BenchTest/signal_loss_test.py COM10 60 <log>` sends `AT+CFUN=4` (radio off), waits 60 s, sends `AT+CFUN=1`, and records until the firmware reconnects. By hand: the same two commands in the bench console.
- Pass: the firmware reports the loss, retries with increasing delay, and reconnects by itself within a few retry intervals of the radio coming back.
- Result (30 Sep 2026): loss detected 0.8 s (modem report) or 20.7 s (three failed publishes) after the radio went off; retries at 30 and 60 s; reconnect 36 s after the radio returned in v0.5.0, about 5 s in v0.5.3, which reconnects as soon as the modem reports the data connection back. No failed publishes afterwards.
- Evidence: `BenchTest/logs/2026-09-30_signal_loss_test.log` (v0.5.0), `BenchTest/logs/2026-09-30_signal_loss_test_v053.log` (v0.5.3).

### T8. I2C line voltage
- Method: board powered, multimeter on 20 V DC, black probe on GND, red probe on the IMU's SDA and then SCL pins with the bus idle.
- Pass: about 3.3 V (pull-ups to 3.3 V, safe for the ESP32 inputs; 5 V would mean the module's pull-ups go to 5 V).
- Result (30 Sep 2026, bench): about 3.3 V. To repeat on the vehicle wiring after mounting.

### T9. Firmware v0.6.0: buffered logging, signal quality, Hall counter
- Method: `python BenchTest/v060_bench_test.py COM10 <log> 330`: resets the board, `!status`, 330 s with logging on, `!status`. Board still. Hall counter in bench loopback on the sync pin (HALL_INPUT_PIN = SYNC_PULSE_PIN).
- Pass: gaps over 10 ms only at a log flush (about once a minute); no dropped samples; Hall count between the two `!status` = 2.00 edges/s; a CSQ value shown.
- Result (1 Oct 2026): 5 flushes (71 to 202 ms each); 10 windows with a gap over 10 ms (37 to 40 ms, both IMUs at each flush), all within 3.5 s after a flush; worst gap otherwise 5.9 ms; 200.0 to 200.5 Hz, 0 dropped; Hall 666 edges in 333.3 s = 2.00 edges/s; CSQ 24 to 26 (about -65 dBm). Log file 2.18 MB of the 3 MB cap.
- Evidence: `BenchTest/logs/2026-10-01_v060_bench_test.log`.

### T10. Stored log read-back
- Method: `python BenchTest/log_dump.py COM10 <out.jsonl> [--clear]`: sends `!log dump` (records printed as LOG|index|length|record, paced), keeps intact records, repeats up to four passes until every index is present, checks JSON, saves the records as stored and a .clean.jsonl with nan replaced by null; `--clear` then sends `!log clear`.
- Pass: every index up to the firmware's line count received intact; every record parses.
- Result (1 Oct 2026, v0.6.3): 6,020 records (2.2 MB, about 16.7 h) complete after four passes (the one index missing was a record written during the dump). 5,545 contained nan and were not valid JSON as stored (fixed in v0.6.3); all parse after nan -> null. 14 records with a valid BMS reading (74.78 V, 0.00 A, 60%) from the 30 Sep v0.5.4 session. Log cleared afterwards.
- Evidence: `BenchTest/logs/2026-10-01_telemetry_log_dump.jsonl`, `.clean.jsonl`.

### T7. BMS link on the vehicle (planned)
- Method: on the vehicle with the pack on, watch `[BMS] scan saw:` lines for the configured address; if absent, record the addresses seen.
- Result so far (30 Sep 2026): pack seen as DB24SA01L24S150ABU at the configured address, weak signal (-93 dBm at the laptop, -88 dBm on a phone). One connection, three frames, all rejected: checksum formula wrong (included the register byte). Fixed in v0.5.4, which also prints rejected frames raw. Confirmed by the stored log (T10): 14 records with a valid reading, 74.78 V, 0.00 A, 60%, later in the same session; still to compare with the phone app. Next: place the board within about 1 m of the pack's Bluetooth module; compare with the phone app.
- Evidence: `BenchTest/logs/2026-09-30_bms_vehicle_v054*.log`, `BenchTest/bms_probe.py` (laptop, read-only).
- Pass: connection and checksum-valid frames; pack voltage matches a meter reading.

## Camera and detector (Raspberry Pi 4)

Commands for the Pi are on the Camera Test Runbook page; the steps below
say what each test is for and what counts as a pass.

### C1. Live detection
- Method: `python3 hazard_detector.py --duration 60 --log-path alerts.jsonl` (optionally `--preview --preview-host 0.0.0.0` and view `http://<pi-ip>:8080`).
- Pass: runs for the full minute; a person in view is logged as "person"; frame rate at least 5 fps.
- Result (28 Sep 2026): run 1, 7.2 fps, person logged as "motorcycle" (label-offset fault); run 2 after the label and colour fixes, 7.0 fps, person at confidence 0.50 to 0.73; 16 alert activations in 47 s, which led to the clear-side hysteresis.
- Evidence: `Report/evidence/2026-09-28_camera_run1_label_bug.txt`, `..._run2_after_fixes.txt`.

### C2. Detector logic, offline
- Method: `python CameraDetection/tests/test_alert_logic.py`, `test_alerts_endpoint.py`, `test_latency_and_preview.py`. They run the unchanged detector loop with a fake camera and model (`CameraDetection/tests/fakes`).
- Pass: single missed frames do not clear an alert; a single near frame does not escalate it; a sustained approach does; the alert clears when the object leaves; `/alerts` empties after clearing; handing a frame to the preview does not block; timings are recorded.
- Result (28 to 30 Sep 2026): all pass.

### C3. Colour check
- Method: runbook step 5 with the colour cards in `Colour Cards/` (blue, red, green, grey, plus plain white paper), held together about 1 m from the camera.
- Pass: blue shows blue; grey and white look neutral. If both the live view and the Pi's own preview are reddish, try the `ov5647_noir.json` tuning.
- Result (1 Oct 2026): `rpicam-still` with the standard tuning: white wall strongly pink; with `ov5647_noir.json`: neutral. Detector frames (standard tuning) also pink, so the module has no IR-cut filter (student confirms the camera is the cause). With `--tuning ov5647_noir.json` alone: neutral but washed out, blue card RGB 120/124/125. With `--saturation 1.8` added: blue card 1/83/218, red box 213/7/56, white wall 202/217/214. Detector now started with both (service file updated). Each card held up in turn, mean RGB in the detector's frames: blue 1/86/216, red 222/8/77, green 6/124/103, grey 124/129/138, white 186/199/197. All four held together in one frame (card2_all4.jpg): blue 1/94/207, red 243/19/44, grey 187/189/176, green 77/145/89, all distinct. Pass: colours clearly identified; grey and white slightly cool (red about 12 to 14 low), acceptable. Recheck outdoors in daylight.
- Evidence: `Report/evidence/c3/` (default.jpg, noir.jpg, detector_view.jpg, detector_view_noir.jpg, card_blue.jpg, card_blue_sat18.jpg, card2_blue.jpg, card2_green.jpg, card2_grey.jpg, card2_white.jpg).

### C4. Latency
- Method: runbook step 7, three one-minute runs (no preview, with preview, one thread), keeping the `[timing]` lines and CSVs.
- Pass: to be set from the measurements and the speed argument in the report.
- Result (30 Sep 2026, current detector deployed to the Pi first; bench, no objects): 4 threads 19.5 fps, total median 102 ms, p95 120 ms, max 136 ms (queue 52, pre 12, inference 36, alert logic 0.1); with the live-view server (no viewer) 17.3 fps, 105 / 127 ms; 1 thread 7.0 fps, 186 / 207 ms (inference 126 ms). 65.7 C, no throttling. The earlier 7 fps live runs match the 1-thread figure.
- Evidence: `BenchTest/logs/2026-09-30_c4_latency/` (per-frame CSVs and console output).

### C5. Distance calibration and object coverage (planned)
- Method: runbook steps 4 and 6 with a tape measure (2, 4, 6, 8 m; facing and side-on; person and bicycle first).
- Pass: bands match the tape-measured distance after focal-length calibration.

### C6. Camera to IMU time alignment
- Method: sync pulse from the ESP32 (GPIO15, toggling every 500 ms) to the Pi (GPIO17), with a lens-cover test for the camera clock offset. Quick wiring check on the Pi: `time gpiomon -c gpiochip0 -n 20 17 > /dev/null`, expecting about 10 s.
- Wiring: ESP32 J5 pin 5 (GPIO15) to Pi physical pin 11 (GPIO17), plus a ground wire (Pi pin 9 to ESP32 GND). Both are 3.3 V logic, so they connect directly.
- Logger: `python3 CameraDetection/sync_logger.py --duration 60 --out sync_edges.csv` records every edge with the Pi's monotonic clock (kernel timestamps through gpiod) and prints the interval summary. Run it alongside the camera or detector so both use the same clock.
- Pass: about 2 edges per second; median interval 500 ms; no intervals outside 500 +/- 20 ms. Zero edges means the wire or ground is loose (seen once on the bench).
- Result: offset bounded under about 1 s (see Methodology, time synchronisation). Logger checked offline against a fake GPIO (30 Sep 2026); not yet run on the Pi. Wire check (30 Sep 2026): 20 edges in 9.95 s, one edge every 500 ms as expected. Logger on the Pi (30 Sep 2026, gpiod v2 kernel timestamps, 60 s each): run 1, 159 edges with 50 intervals out of range, all between 5 and 21 s into the run (bursts of extra edges down to 0.03 ms apart, consistent with a disturbed contact), clean for the last 39 s; run 2, 121 edges, median 500.06 ms, range 499.72 to 500.41 ms, 0 out of range. Evidence: `BenchTest/logs/2026-09-30_sync_edges_run1_noisy.csv`, `..._run2.csv`.

### C7. Stand-in ToF (micromouse sensor board, three VL53L0X)
- Wiring: sensor board J2 pin 3 (3V3) to Pi pin 1, J2 GND (pin 23) to Pi pin 6, J2 31 (SDA) to Pi 3, J2 32 (SCL) to Pi 5, XSHUT1/2/3 (J2 21/9/7) to Pi 15/16/18 (GPIO22/23/24). VDD (LED supply) not connected. Continuity-check each pin first. Pi I2C on (`sudo raspi-config nonint do_i2c 0`).
- Method: `venv/bin/python tof_probe.py`, then `venv/bin/python tof_reader.py --duration 15 --csv tof.csv`. Then a hand at about 15 cm in front of each sensor in turn to confirm which is left, ahead and right, and a tape measure at 0.2, 0.5, 1.0 and 1.5 m.
- Pass: chip identified; three sensors answer; readings change with the hand on the matching sensor; within about 5% of the tape below 1 m.
- Result (1 Oct 2026): chip VL53L0X; all three addressed and read at about 31 readings/s each; centre 267 to 300 mm, right 24 to 38 mm (something close in front of it), left 8190 every reading (no target in range, sensor answering). Cover test (1 Oct 2026, board untouched, each sensor covered by a fingertip in turn): left 27 to 46 mm, then centre 40 to 43 mm, then right 20 to 24 mm, in the order covered, so the labels match the physical sensors; afterwards about 690, 330 and 595 mm to the room. Tape check not yet done.
- Evidence: `BenchTest/logs/2026-10-01_tof_three_sensors.csv`, `..._tof_hand_test.csv`, `..._tof_cover_test.csv`.

## Bench tools

### B1. Bench console replay
- Method: inject a recorded log into `BenchTest/sw7_console.html` as `window.REPLAY_LINES` and screenshot it with headless Edge (the replay figure in Appendix C).
- Pass: every card and chart matches the log.

### B2. Dashboard camera page, offscreen
- Method: `DashboardIntegration/tests/test_front_camera_page.py` (setup in its header).
- Pass: newest frame chosen from a chunked stream; alerts listed and cleared; responsive and "Camera offline, retrying" against an unreachable address.
- Result (28 Sep 2026): passes. Not yet tested on the Pi 5.
- Live (1 Oct 2026, `DashboardIntegration/tests/test_front_camera_page_live.py` on the laptop, detector on the Pi 4 with `--preview --preview-host 0.0.0.0`, 50 s): page Live 0.6 s after start; 638 frames decoded in 45 s (14.2 per second, detector 14.8 fps); longest gap 0.22 s; frame rate and latency shown (14.7 fps, 76 to 87 ms); 'Camera offline, retrying' within a second of the detector stopping. No alerts (nobody in view), so the alert list against live detections is still to check. Note: start the detector in the foreground of the SSH session; started with nohup from SSH it did not serve.
- Evidence: `Report/evidence/2026-10-01_dashboard_page_live.png`.
