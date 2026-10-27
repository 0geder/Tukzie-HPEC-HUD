# SW-7: Embedded Telemetry with Road-Surface Characterisation and Camera-Based Hazard Detection for the TUKZIE Electric Trike

Final-year project (UCT EEE4022S, 2026) by Samson Okuthe (OKTSAM001), supervised by A/Prof. Simon Winberg with co-supervisor Sampath Jayalath. Official title since 26 Oct 2026 (PROJECT_LOG.md, D43); from 2 Oct to 26 Oct it was "Development of an Embedded HPEC Telemetry Unit and Dashboard Integration for the TUKZIE Rev 0 Platform".

The system measures ride quality with two 200 Hz IMU nodes, logs the battery (BMS over BLE), GNSS and LTE telemetry from a Makerfabs ESP32-S3 unit, runs camera hazard detection on two Raspberry Pis, and shows it all on the vehicle's existing PySide6 dashboard on the Pi 5. The original brief named a windshield HUD; on 1 to 2 Oct 2026 it was replaced by dashboard integration, agreed with the supervisor and recorded by the course coordinator (D26).

The repository name (Tukzie-HPEC-HUD) predates the title change and is kept so that existing links keep working.

## Start here

New to this repository? These are the places to look, in order.

1. Read the report: `Report/EEE4022S 2026 FINAL REPORT OKTSAM001 OKUTHE S - WINBERG.pdf`. It explains what was built, how it was tested and what the results mean.
2. Watch the system working: https://tuksense.site (the 27 October road test and the build journey).
3. Check the status table below to see what works and what is still open.
4. Look up any number in the report in `DATA_INDEX.md`, which points to the file it came from.

### What each folder holds

| Folder | What is in it |
|---|---|
| `Report/` | The final report (PDF and LaTeX source), its figures and appendices |
| `TelemetryUnit/` | Firmware for the three ESP32-S3 boards (telemetry unit, front and rear IMU nodes) |
| `CameraDetection/` | Camera hazard detector, time-of-flight sensors and the telemetry bridge on the Raspberry Pis |
| `DashboardIntegration/` | Add-ons to the trike's existing dashboard: live data, camera page, phone GPS, voice commands |
| `Server/` | The small database that stores telemetry sent over LTE |
| `BenchTest/` | Test procedures, the pre-test check, the road recorder, all test logs and the analysis code |
| `BenchTest/logs/` | Raw data from every test, including both road sessions (19 and 27 Oct) |
| `CAD/`, `CameraMount/` | 3D-printed enclosures, pods and mounts (models and STL files) |
| `VirtualTukzie/` | A browser view of a 3D scan of the trike with live IMU readings from a connected board |
| `Planning/` | The lab notebook, test checklists and review notes |
| `Research/` | The literature search database and its scripts |
| `References/` | Papers, datasheets, course documents and hardware manuals used in the report |
| `Presentation/` | Slide deck, poster, talking points and media |
| `Photos/` | Photographs of the bench, the vehicle and reference parts |
| `Vehicle Documentation/` | The trike's user manual |
| `GA Tracking Form/` | The signed graduate attribute tracking form |
| `tools/` | Small helper scripts (data index, report comparison, dashboard time-lapse) |

### If you want to...

- understand a result: find it in the report, then follow `DATA_INDEX.md` to the data and `BenchTest/analysis/` to the code that produced it;
- see what happened on a given day: search `Planning/lab-notebook.md` for the date;
- know why something was decided: see the decisions (D1 to D43) in `PROJECT_LOG.md`;
- flash a board or run the system: follow "How to build, deploy and run" below;
- continue the project: start with Chapter 8 of the report (recommendations and future work) and the status table below.

## Architecture (as driven on 27 Oct 2026)

```
 Front IMU node (ESP32-S3, MPU6050, 200 Hz) --USB--> Raspberry Pi 5 (front camera unit and dashboard)
                                                     front camera hazard detector, recorder,
 Phone GNSS (Share GPS, NMEA over hotspot) --------> phone GPS bridge (speed source), PySide6
                                                     dashboard with SW-7 add-ons (live-only)
                                                           ^
                                                           | Ethernet, chrony time sync
                                                           v
 Rear IMU node (bare ESP32-S3, MPU6050, 200 Hz) --USB--> Raspberry Pi 4 (rear camera unit)
                                                     raw_capture.py :8083, rear camera hazard
 Makerfabs telemetry unit (ESP32-S3, v0.7.9) --UART--> detector :8080, telemetry bridge :8081,
   JBD BMS over BLE, GNSS and LTE (A7670X)           three VL53L0X ToF sensors
          |
          | LTE, MQTT (broker.hivemq.com) --> Pi 5 ingest
```

Changes since the bench design: the two IMUs are no longer fused on one board; each has its own node, compared rather than fused (from v0.7.6). The rear IMU moved to a bare ESP32-S3 board on 26 Oct after the Makerfabs board's IMU stopped answering; the Makerfabs board keeps BMS, GNSS, LTE and the DASH line, now on a wired UART to the Pi 4 (since 21 Oct). Vehicle speed comes from the phone's GNSS; the Makerfabs receiver updated only about every 25 s on the road.

### Where each part lives

| Part | Folder and main files | Deploy |
|---|---|---|
| Firmware (all three ESP32-S3 boards) | `TelemetryUnit/src/main.cpp`, `platformio.ini` (envs `esp32-s3-devkitc-1`, `front_node`, `rear_imu_node`) | `pio run -e ENV -t upload` |
| Telemetry bridge, ToF (Pi 4) | `CameraDetection/telemetry_bridge.py`, `tof_reader.py`, `sensor_fusion.py` | `CameraDetection/deploy/`, `INSTALL.md` |
| Camera hazard detector (both Pis) | `CameraDetection/hazard_detector.py`, `detect.tflite`, `labelmap.txt` | `CameraDetection/deploy/` |
| Raw IMU capture, recorder | `BenchTest/raw_capture.py`, `road_logger.py`, `CameraDetection/sync_logger.py` | rear capture from crontab on the Pi 4 |
| Dashboard add-ons (Pi 5) | `DashboardIntegration/` (camera page, live-data provider, ride card, phone GPS, voice, endpoints) | `DashboardIntegration/deploy/deploy_dashboard.sh` |
| Link contract | `DashboardIntegration/TELEMETRY_LINK.md` | |
| Pre-test check | `BenchTest/sw7_check.py` | |
| Analysis | `BenchTest/analysis/`, `BenchTest/collect_session.sh` | laptop |
| Camera casing | `CameraMount/casing/` (STL) | 3D print |

## Analysis tools

- `BenchTest/collect_session.sh YYYY-MM-DD`: copies one day's recordings from both Pis into `BenchTest/logs/run2_road_YYYY-MM-DD` (files chosen by modification time).
- `python -m BenchTest.analysis.run --session <folder> --out <folder>/analysis`: segments passes, computes a_w, VDV, sigma and the speed-normalised index, repeatability, spectra and powertrain lines.
- `BenchTest/analysis/auto_markers.py`: derives pass, coast and still markers from the phone GNSS speed and the BMS current (vehicle GNSS speed as fallback), so no typed markers are needed.
- `BenchTest/analysis/position_icc.py`: position-aligned ICC; places each IMU sample by the phone fix and uses 8 m ground cells crossed by every pass.

## How to build, deploy and run

Firmware (laptop): Makerfabs unit on COM10 (env `esp32-s3-devkitc-1`, 115200 baud), front node on COM11 (`front_node`), rear IMU node on COM15 (`rear_imu_node`); the two IMU nodes run at 921600 baud.
```
cd TelemetryUnit
pio run -e rear_imu_node -t upload
pio device monitor -e rear_imu_node   # !status, !recal; Makerfabs unit also !dash, !log dump, !mqtt on|off
```

Pi 4: install the detector and bridge services as in `CameraDetection/deploy/INSTALL.md`, then `sudo systemctl enable --now hazard-detector telemetry-bridge` and `curl -s http://localhost:8081/telemetry`. The rear capture (`raw_capture.py` on :8083) starts at boot from crontab.

Wired link (once on each Pi): `sudo bash setup_sw7_link.sh pi4` or `pi5`. Chrony on the Pi 4 follows the Pi 5 and steps on any offset over 1 s.

Pi 5 dashboard (laptop, Git Bash, from the repo root; never touches the team's `~/Dashboard`): `bash DashboardIntegration/deploy/deploy_dashboard.sh [--pi5 HOST]`. Take screenshots before and after every deploy.

Before every session: `python BenchTest/sw7_check.py` (must print READY). After it: `bash BenchTest/collect_session.sh YYYY-MM-DD`, then the analysis above.

Tests (laptop): `python -m pytest -q CameraDetection/tests/test_telemetry_bridge.py BenchTest/tests/test_sw7_check.py` and `python DashboardIntegration/tests/test_live_data_provider.py`.

Report: `cd Report` then `latexmk -xelatex "Samson Okuthe - EEE4022S Final Report (2026).tex"`; `python wordcount.py` gives the body word count.

## Status (27 Oct 2026)

Two road sessions: 19 Oct (first on-vehicle run, IMU data over USB) and 27 Oct (laps in a car park at 10, 15 and 20 km/h, driver Yusuf Vadwa). Statuses follow Table 5.3 of the report (R1 to R13).

| Requirement | Status | Evidence |
|---|---|---|
| R1 IMU at 200 Hz | Met on the bench; on the vehicle met at the front | 27 Oct: front 0 gaps, rear 0.08 % lost in transport |
| R2 Calibration (about 9.81 m/s2) | Met at each calibration; not met on the vehicle | 27 Oct at rest: rear 9.845, front 9.941 |
| R3 Self-test and fusion | Met for the fused design (to v0.7.6) | nodes now compared, not fused |
| R4 GNSS | Partly met | bench median 2.7 m; on the vehicle 8 to 25 m from the phone, updating every 25 s |
| R5 BMS over BLE | Partly met | 27 Oct peak 82.9 A, 74.0 to 71.2 V; no meter check |
| R6 Sync pulse | Partly met | 500.06 ms median interval; camera-to-IMU offset not measured |
| R7 Camera detection | Partly met | road: rear 12.1 fps, median 103 ms; front 23.3 fps, median 68 ms; onset not timed at the screen |
| R8 ToF distance | Partly met | ahead 1.06 m at about 1.0 m; no flat-target series |
| R9 LTE and store-and-forward | Met on the bench; partly met on the vehicle | 153 records over LTE (116 replayed), median 0.44 s (n=9), link lost from 11:51 |
| R10 Link to the Pi | Met on the bench and on the vehicle | wired UART 4,196 of 4,201 records (99.9 %) |
| R11 Dashboard alerts | Partly met | clearing seen only offline |
| R12 Glance time | Not tested | no participants; alert banner below ISO 15008 legibility |
| R13 Fit without modification | Partly met | mounted 19 Oct, removal not timed |

Road results, 27 Oct:
- Smooth loop at 10 km/h, CV of a_w across 5 passes: 5.0 % rear, 5.3 % front. The rough loop reads about twice the smooth loop's a_w.
- Position-aligned ICC on the smooth loop: 0.16 (rear), against a criterion of 0.75: not met.
- Powertrain lines carry 1 to 3 % of the road vibration energy.

Not delivered: the air-quality sensor (damaged), the optical HUD (replaced by dashboard integration by agreement), validated ToF and camera fusion, the time-to-contact test, and the glance study.

## Key documents

- Final report: `Report/EEE4022S 2026 FINAL REPORT OKTSAM001 OKUTHE S - WINBERG.pdf` (source `Samson Okuthe - EEE4022S Final Report (2026).tex`).
- `Planning/lab-notebook.md`: every lab and road action, with what the student did.
- `PROJECT_LOG.md`: status board, decisions (D1 to D43), timeline; `CHANGELOG.md`: every change and why.
- `DATA_INDEX.md`: every data file, where the report cites it, and its checksum.
- `BenchTest/TEST_PROCEDURES.md`: test procedures and results; raw logs in `BenchTest/logs/`.
- `DashboardIntegration/README.md`, `CameraDetection/README.md`: dashboard add-ons, detector and ethics conditions.
- `Presentation/`: deck, poster, talking points and Q&A.
- Videos of the system on the road and of its development: https://tuksense.site (site source in a separate repo, 0geder/tuksense)
