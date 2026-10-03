# SW-7: Embedded HPEC Telemetry Unit and Dashboard Integration for the TUKZIE Rev 0

Final-year project (UCT EEE4022S, 2026) by Samson Okuthe (OKTSAM001), supervised by A/Prof. Simon Winberg with co-supervisor Sampath Jayalath. Official title since 2 Oct 2026: "Development of an Embedded HPEC Telemetry Unit and Dashboard Integration for the TUKZIE Rev 0 Platform".

An ESP32-S3 telemetry unit (Makerfabs board with an A7670X LTE Cat 1 modem, firmware v0.7.0) samples two MPU6050 IMUs at 200 Hz, computes calibrated, fused ride-quality features, reads the JBD BMS over BLE and GNSS through the modem, logs to internal flash and publishes JSON over MQTT on LTE. Once a second it also prints a DASH line on USB to a Raspberry Pi 4, which runs a camera hazard detector and a telemetry bridge that adds three time-of-flight sensors. The driver display is the vehicle's existing PySide6 dashboard on the Raspberry Pi 5 (Pirate5), extended with our camera page, live-data provider (live-only mode), ride-quality card and Pi 4 finder. The original brief named a windshield HUD; on 1 to 2 Oct 2026 it was replaced by dashboard integration, agreed with the supervisor and recorded by the course coordinator (PROJECT_LOG.md, D26).

The repository name (Tukzie-HPEC-HUD) predates the title change and is kept so that existing links keep working.

## Architecture

```
                         sync-pulse wire (GPIO edges for time alignment)
          +------------------------------------------------------+
          |                                                      v
  ESP32-S3 telemetry unit            USB serial        Raspberry Pi 4 (front enclosure)
  (TelemetryUnit/, v0.7.0)  -------- DASH line, 1 Hz -->  telemetry bridge  HTTP :8081 /telemetry
   2x MPU6050 @ 200 Hz                                     + 3x VL53L0X ToF (I2C)
   JBD BMS over BLE                                       camera hazard detector HTTP :8080
   GNSS via A7670X                                          /stream (MJPEG), /alerts (JSON)
   LittleFS log                                           UDP beacon every 2 s, port 50808
          |                                                      |
          | LTE, MQTT                                            | wired 10.20.0.1 <-> 10.20.0.2,
          v                                                      | beacon, mDNS or last good host
        cloud broker                                             v
                                               Raspberry Pi 5 (Pirate5): vehicle PySide6 dashboard
                                               + camera page, live-data provider (live-only),
                                                 ride-quality card, Pi 4 resolver
```

A single-Pi-5 setup (bridge and detector on the Pi 5) is being considered; the resolver already tries localhost first.

### Where each part lives

| Part | Folder and main files | Tests | Deploy |
|---|---|---|---|
| Telemetry unit firmware | `TelemetryUnit/src/main.cpp`, `platformio.ini` | `BenchTest/v050_bench_test.py`, `v060_bench_test.py`, `log_dump.py`, `signal_loss_test.py`, `gnss_capture.py`, `bms_probe.py` | `pio run -t upload` (below) |
| Telemetry bridge (Pi 4) | `CameraDetection/telemetry_bridge.py`, `tof_reader.py` | `CameraDetection/tests/test_telemetry_bridge.py` | `CameraDetection/deploy/telemetry-bridge.service`, `INSTALL.md` |
| Camera hazard detector (Pi 4) | `CameraDetection/hazard_detector.py`, `detect.tflite`, `labelmap.txt`; YOLO trials in `yolo_bench.py`, `ncnn_bench.py`, `training/` | `BenchTest/TEST_PROCEDURES.md` C1 to C8 | `CameraDetection/deploy/hazard-detector.service`, `INSTALL.md` |
| Sync logger (Pi 4) | `CameraDetection/sync_logger.py` | TEST_PROCEDURES C6 | copied by hand |
| Dashboard add-ons (Pi 5) | `DashboardIntegration/front_camera_page.py`, `live_data_provider.py`, `ride_quality_card.py`, `sw7_endpoints.py`, `sw7_live_only.py` | `DashboardIntegration/tests/` | `DashboardIntegration/deploy/deploy_dashboard.sh`, `start_sw7_dashboard.sh`, `setup_sw7_link.sh` |
| Link contract | `DashboardIntegration/TELEMETRY_LINK.md` | | |
| Pre-test check | `BenchTest/sw7_check.py` | `BenchTest/tests/test_sw7_check.py` | |
| Bench tools | `BenchTest/sw7_console.html`, `live_telemetry.html`, `VirtualTukzie/dashboard.html` | | local HTTP server |
| Camera casing | `CameraMount/casing/` (STL) | | 3D print |

### Where to find records

| Record | Location |
|---|---|
| Test procedures and results | `BenchTest/TEST_PROCEDURES.md`, raw logs in `BenchTest/logs/` |
| Decisions, status and history | `PROJECT_LOG.md` (decisions D1 onwards), `CHANGELOG.md` (every change and why) |
| Report source and PDF | `Report/` (`Project Report Template.tex` and its PDF) |
| Evidence for the report | `Report/evidence/` (indexed in Appendix C) |
| Presentation, poster, talking points, Q&A | `Presentation/` (built from `Presentation/source/`) |
| Planning and brief compliance | `Planning/` (`brief-compliance.md`) |
| Literature and datasheets | `References/`, `Research/` (pipeline and gap ledger) |

## Other folders

| Folder | Contents |
|---|---|
| `GA Tracking Form/` | Graduate attributes tracking form (submitted) |
| `Photos/` | Bench and vehicle photos |
| `Vehicle Documentation/` | Manufacturer documentation for the trike |
| `.claude/` | Project agents (progress-scribe) |

## How to build, deploy and run

Firmware (laptop, board on COM10):
```
cd TelemetryUnit
pio run              # build
pio run -t upload    # flash
pio device monitor   # serial at 115200; !status, !dash on|off, !log dump, !recal
```

Pi 4 detector and bridge: copy the files and install the two services as in `CameraDetection/deploy/INSTALL.md`, then on the Pi 4:
```
sudo systemctl enable --now hazard-detector telemetry-bridge
curl -s http://localhost:8081/telemetry
```

Wired link (once on each Pi): `sudo bash setup_sw7_link.sh pi4` or `pi5`.

Pi 5 dashboard (laptop, Git Bash, from the repo root; never touches the team's `~/Dashboard`):
```
bash DashboardIntegration/deploy/deploy_dashboard.sh [--pi5 HOST]
```

Before every test session (laptop or Pi 5):
```
python BenchTest/sw7_check.py
```

Tests (laptop):
```
python -m pytest -q CameraDetection/tests/test_telemetry_bridge.py BenchTest/tests/test_sw7_check.py
python DashboardIntegration/tests/test_live_data_provider.py
```

Report: build with Tectonic as described in PROJECT_LOG.md section 7.

## Status (3 Oct 2026)

| Item | State | Date |
|---|---|---|
| Dual IMU 200 Hz, calibration, fusion | Tested on the bench (149/149 windows, 0 drops) | 25 Sep |
| MQTT over LTE, reconnect, signal-loss recovery | Tested on the bench | 29 to 30 Sep |
| GNSS fix (median 2.7 m from phone) | Tested outdoors (rooftop) | 30 Sep |
| LittleFS log, buffered writes, read-back | Tested on the bench | 1 Oct |
| BMS over BLE | Checksum fix confirmed from 14 logged records; sustained test outstanding | 30 Sep |
| Firmware v0.7.0 DASH line | Tested on the bench (40/40 lines) | 2 Oct |
| Telemetry bridge on the Pi 4, as a service | Tested live with the ESP32 and ToF | 2 Oct |
| Camera detector (19.5 fps, 102 ms median) and colour fix | Tested on the bench | 30 Sep, 1 Oct |
| Distance calibration, other object classes | Not yet tested | |
| Dashboard camera page | Tested on a laptop against the live detector | 1 Oct |
| Live-data provider, ride card, live-only mode, resolver | Tested offscreen on a laptop with a fake bridge | 3 Oct |
| Integrated dashboard copy on the Pi 5 | Running, native map, no crash; live data on the Pi 5 not yet recorded | 2 Oct |
| Beacon, wired link, pre-test check | Written and unit-tested; on-Pi results not yet recorded in TEST_PROCEDURES | 3 Oct |
| On-vehicle and road test | Not yet done | |

## Key documents

- `PROJECT_LOG.md`: status board, decisions, timeline.
- `DashboardIntegration/README.md` and `TELEMETRY_LINK.md`: dashboard add-ons and the link contract.
- `CameraDetection/README.md`: detector, ethics conditions, deployment.
- `BenchTest/TEST_PROCEDURES.md`: every test and its result.
- `Planning/brief-compliance.md`: brief items against current status.
