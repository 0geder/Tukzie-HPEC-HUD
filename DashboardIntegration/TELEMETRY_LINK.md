# Telemetry link to the dashboard (contract)

How telemetry from the ESP32 telemetry unit and the ToF sensors reaches the vehicle's dashboard on the Raspberry Pi 5. Written 2 Oct 2026, before the three parts were built, so that they fit together.

```
ESP32 (USB serial) --> Pi 4 telemetry bridge (HTTP :8081) --> Pi 5 dashboard live-data provider
                       Pi 4 camera detector (HTTP :8080) ----> Pi 5 dashboard camera page (existing)
```

Why this path: the ESP32 and the Pi 4 share the front enclosure (camera ribbon and sync wire), so one short USB cable links them and powers the ESP32. The dashboard then needs a single network link, to the Pi 4, for all on-vehicle data. The driver's display does not depend on cellular coverage or a cloud broker. MQTT over LTE continues unchanged for the cloud.

## 1. ESP32 to Pi 4: one line per second on USB serial

The firmware prints, once a second, one line that starts with `DASH ` followed by a single-line JSON object and `\n`. Other serial output continues as before; the bridge ignores every line that does not start with `DASH `.

Fields (any value that is unknown or NaN is `null`, never `nan`):

| Key | Type | Meaning |
|---|---|---|
| `seq` | int | increments by 1 per line, from boot |
| `up_ms` | int | milliseconds since boot (esp_timer) |
| `fw` | string | firmware version, e.g. `"0.7.0"` |
| `soc` | number or null | BMS state of charge, % |
| `v` | number or null | BMS pack voltage, V |
| `i` | number or null | BMS pack current, A (sign as reported by the JBD BMS; not yet confirmed which sign is discharge) |
| `bms_age_s` | number or null | seconds since the last valid BMS frame |
| `fix` | bool | GNSS has a valid fix |
| `lat`, `lon` | number or null | decimal degrees |
| `spd_raw` | number or null | GNSS speed field as reported (manual says knots; not confirmed) |
| `crs` | number or null | GNSS course over ground, degrees clockwise from true north (firmware 0.7.1+; null without a fix or when the receiver gives none) |
| `alt` | number or null | GNSS altitude, m (firmware 0.7.1+; null without a fix) |
| `vib` | number or null | fused vibration level: standard deviation of acceleration magnitude, m/s2, last 1 s window |
| `vib_dis` | number or null | IMU disagreement figure, last fused window |
| `imu_hz` | [number, number] | sample rate of IMU1, IMU2 |
| `drops` | [int, int] | dropped samples since boot, IMU1, IMU2 |
| `rpm` | number or null | motor speed from the Hall counter (null until pole pairs are set) |
| `csq` | int or null | modem signal quality 0 to 31 |
| `mqtt` | bool | MQTT session up |
| `cell_lat`, `cell_lon` | number or null | mobile-network position estimate (modem AT+CLBS), decimal degrees; firmware 0.7.3+; only while `fix` is false, null once the estimate is over 5 min old. Never copied into `lat`/`lon` |
| `cell_acc_m` | number or null | the modem's accuracy for that estimate, m (about 550 indoors, 10 Oct 2026) |
| `cell_age_s` | number or null | seconds since that estimate |
| `agps` | bool | assisted GNSS data loaded (AT+CAGPS succeeded), firmware 0.7.3+ |
| `node` | string | `"rear"` or `"front"`, firmware 0.7.5+ |
| `rdfail` | [int, int] | IMU I2C reads that failed (not acknowledged, or short) since boot, IMU1, IMU2; firmware 0.7.5+ |
| `stuck` | [int, int] | good IMU reads with all six values equal to the previous good read (registers not updating) since boot; firmware 0.7.5+ |
| `rawdrop` | [int, int] | samples never sent on the raw stream (queue full, or no port took the line) since boot; firmware 0.7.5+ |

The four 0.7.5 fields are appended at the end; every older field is unchanged. The front IMU node (build env `front_node`, section 6) sends a shorter DASH line: `seq`, `up_ms`, `fw`, `vib`, `imu_hz`, `drops`, `node`, `rdfail`, `stuck`, `rawdrop`, with one element in each array.

The line must be built without heap-heavy String concatenation in a timing-critical task and must never block the IMU tasks (core 1). Maximum length 576 bytes (400 until firmware 0.7.3, 480 until 0.7.5; the bridge accepts up to 4096).

Since firmware 0.7.5 the same link also carries the raw IMU stream: RAW, RAWH and RAWS lines, about 15 kB/s on the rear unit (`TelemetryUnit/RAW_STREAM.md`). They never start with `DASH `, so a reader that only wants DASH is unaffected; the bridge saves them (section 6).

On the dashboard, `cell_*` becomes `VehicleState.sw7_cell_position = (lat, lon, accuracy m)`, drawn on the map as a dot in a translucent accuracy circle labelled "Approximate position", the way a phone shows a network position indoors. It does not set `latitude`/`longitude`, `signal_validity["gps"]`, heading or navigation progress.

## 2. Pi 4 bridge: HTTP on port 8081

`CameraDetection/telemetry_bridge.py` reads the ESP32's USB serial port (`/dev/ttyACM0` by default, configurable), keeps the latest `DASH` record, reads the three ToF sensors itself (same wiring and code as `tof_reader.py`), and serves:

`GET /telemetry` returns `application/json`:

```json
{
  "esp32": { ...latest DASH object..., "age_ms": 420 },     // null if no line received yet
  "tof":   { "left_mm": 812, "ahead_mm": 1490, "right_mm": null, "age_ms": 35 },  // null if sensors absent; 8190 or out of range -> null
  "bridge": { "version": "1.0", "serial_port": "/dev/ttyACM0", "lines": 1234, "bad_lines": 2,
              "replay": false, "replay_file": null,
              "raw": { "capture": true, "dir": "/home/ogeder/rawlog", "file": "rear_raw_2026-10-22_141500.txt",
                       "lines": 5210, "bad_crc": 0, "raw": 5100, "rawh": 10, "raws": 100,
                       "bytes_written": 1860000, "not_written": 0, "write_errors": 0, "files": 1,
                       "paused": null } }
}
```

`lines` and `bad_lines` count DASH lines only, as before. `bridge.raw` (added 22 Oct 2026, additive) counts the raw-stream lines (section 6): `lines` every line with a RAW, RAWH or RAWS type word, `bad_crc` the subset that failed its CRC, `raw`/`rawh`/`raws` the good ones by type, `bytes_written`, `not_written` (lines lost while capture was paused), `write_errors`, `files` opened since start and `paused` (the reason, or null). `capture` is false with `--no-raw-capture` (counting continues; `dir` and `file` are then null). The plain-text status page at `GET /` has the same numbers on its `raw:` line.

`replay` is true while the bridge replays DASH lines from a file (`--replay FILE`, for bench tests) instead of reading the serial port; `replay_file` is then that file's name, otherwise null. Replay lines also carry an `fw` ending in `-replay` (for example `"0.7.1-replay"`). The dashboard treats either sign as replayed data: the live-data provider sets `data_source` to `sw7_replay`, and the map and the ride card show an amber REPLAY badge, so replayed positions are never taken for real ones.

`age_ms` is the time since that part was last updated, so the dashboard can mark stale data. The bridge must keep serving when the ESP32 is unplugged or the ToF sensors are absent (those parts become null).

## 3. Pi 5 dashboard: live-data provider

`DashboardIntegration/live_data_provider.py` polls `http://<pi4>:8081/telemetry` twice a second (address from the environment variable `TUKZIE_TELEMETRY_URL` if set, otherwise found by the resolver in section 4.3) with Qt networking only, maps fields onto the dashboard's `VehicleState` and passes them to `VehicleStateManager.ingest_live_state()`. Mapping:

| Bridge field | Dashboard field | Note |
|---|---|---|
| `esp32.soc` | `soc_pct` | |
| `esp32.v * esp32.i / 1000` | `signed_battery_power_kw` | sign convention to be checked on the vehicle |
| `esp32.lat`, `esp32.lon` | `latitude`, `longitude` | only when `fix` is true |
| `esp32.fix` | GPS entry of `signal_validity` | |
| `esp32.crs` | `heading`, heading entry of `signal_validity` | only when `fix` is true; otherwise None (not 0, which would mean north). The map turns heading-up from it |
| `esp32.alt` | `altitude_m` | only when `fix` is true; otherwise None (Navigation shows "ALTITUDE N/A") |
| `bridge.replay`, or `esp32.fw` ending in `-replay` | `data_source` = `sw7_replay` (otherwise `sw7_telemetry`) | REPLAY badge on the map and the ride card; Diagnostics shows the source |
| `esp32.spd_raw` | `speed_kmh` | NOT mapped until the units are confirmed; shown on the ride card only |
| `esp32.rpm` | (ride card) | |
| `tof.ahead_mm / 1000` | `front_obstacle_distance_m` | ahead sensor only (decided 2 Oct: side readings must not raise a front-obstacle warning) |
| `esp32.vib`, `vib_dis`, `imu_hz`, `drops`, `csq`, `mqtt` | ride-quality card (new) | the dashboard has no fields for these |

Parts of the dashboard state with no source here (throttle, brake, tyres, doors, motor temperature) are left to the existing behaviour; gear, indicators, headlights and parking brake come from the keyboard and controller. When the bridge cannot be reached, or `esp32.age_ms` exceeds 3000, the provider stops sending, so the dashboard's own stale-data fallback takes over. If the BMS has never reported, `soc_pct` is None (shown as `--%`), not the dashboard's default of 82 %.

Live-only mode (added 3 Oct 2026). With `TUKZIE_LIVE_ONLY=1` (set by `deploy/start_sw7_dashboard.sh`) the dashboard never shows simulated values: the simulation does not run, and until live data arrives, or within 2.5 s of it stopping, the dashboard shows an explicit no-data state in which every sensor-derived field is None and every signal invalid, so the pages show `--` or `Unavailable`. In live mode the fields with no source above are None too, not defaults. The toast on losing data reads "Live data lost · showing no data". Gear, indicators, headlights and parking brake keep working. Without the variable the dashboard behaves as before (simulation fallback). Code: `sw7_live_only.py` and the `LIVE_ONLY_PATCHES` in `tests/dashboard_patches.py`.

## 4. Finding the Pi 4 on any network (added 3 Oct 2026)

Why: on 3 Oct the Pi 4 moved from the laptop hotspot (192.168.137.82) to a phone hotspot (10.74.67.244); the dashboard, set to the old address, silently fell back to simulated data. No single address is reliable on a vehicle, so the dashboard finds the Pi 4 by itself.

### 4.1 Wired link (primary)
An Ethernet cable joins the Pi 4 and the Pi 5. Each gets a fixed address on a private subnet with no gateway, so Wi-Fi keeps the default route for internet:
- Pi 4 `eth0`: `10.20.0.1/24`
- Pi 5 `eth0`: `10.20.0.2/24`
Configured with a NetworkManager profile named `sw7-link` (`deploy/setup_sw7_link.sh pi4|pi5`, run with sudo once on each Pi).

### 4.2 Beacon (any network)
The Pi 4 bridge sends a UDP broadcast every 2 s to port **50808** on every IPv4 interface's broadcast address (and 255.255.255.255), payload one JSON object:
```json
{"sw7": "pi4", "v": 1, "host": "pi4-camera", "camera_port": 8080, "telemetry_port": 8081, "seq": 12}
```
The receiver takes the Pi 4's address from the packet's source address, not from the payload.

### 4.3 Resolution on the dashboard (Pi 5)
A shared resolver (`DashboardIntegration/sw7_endpoints.py`, class `Pi4Resolver`) gives the camera page and the live-data provider the current Pi 4 address. Candidates, in order:
1. `127.0.0.1` (localhost), so that a single Pi 5 running the bridge and the detector itself needs no setup;
2. `TUKZIE_PI4_HOST` environment variable or the `pi4_host=` line in `~/.config/sw7/endpoints.conf`, if set (explicit override);
3. the wired address `10.20.0.1`;
4. the most recent beacon source address (beacons older than 10 s are ignored); the beacon is received with a `QUdpSocket`, inside the Qt event loop;
5. `pi4-camera.local`;
6. the last address that worked, saved in `~/.config/sw7/last_pi4_host`.

A candidate is accepted when `GET http://<host>:8081/telemetry` answers within 3 s with valid JSON (raised from 1 s on 3 Oct: phone hotspots add 0.1 to 0.8 s per round trip). Each position is read when its turn comes, so a beacon that arrives during a search is still used; if nothing answers, the search repeats after 2 s, then backs off (4, 8, 16, up to 30 s), and runs at once when a beacon arrives. After 3 consecutive failed polls of the current host (about 1.5 s at the 500 ms poll), the resolver searches again from the top. The current host and how it was found (localhost, override, wired, beacon, mdns, saved) are emitted as the Qt signal `host_changed(host, how)` (`("", "searching")` while searching) and shown on the ride card as "Pi 4: 10.20.0.1 (wired)" or "Pi 4: searching". The camera is at `http://<host>:8080` (same host as telemetry for now). `TUKZIE_TELEMETRY_URL` and `TUKZIE_CAMERA_URL`, if set, bypass the resolver; `TUKZIE_CAMERA_URL` alone moves only the camera.

### 4.4 Pre-test check
`BenchTest/sw7_check.py` runs from the laptop or the Pi 5 before every test session and reports pass/fail per item: Pi 4 found (and how), camera `/alerts` answering with fps, telemetry fresh (ESP32 age under 3 s), IMU rates and drops, all three ToF sensors valid, detector process running, bridge service active, Pi 4 under-voltage flag, Pi 5 reachable, dashboard running on the Pi 5. Exit code 0 only if all critical items pass.

## 5. Camera and ToF fusion block (added 4 Oct 2026)

The bridge fuses the camera detector's detections with the three ToF sensors (`CameraDetection/sensor_fusion.py`, geometry in `CameraDetection/fusion_config.json`). Additive only: sections 2 to 4 are unchanged, and a client that ignores the new key is unaffected.

Detector (port 8080, needs `--preview`, as in its service): `GET /detections` returns the latest frame's detections of the approved classes above the confidence threshold: `class`, `confidence`, `bbox` (normalised `[x0, y0, x1, y1]`), `bearing_deg` (0 = camera axis, negative = left; from the box centre and `--hfov-deg`, default 53.5), `est_distance_m` (pinhole width estimate, focal length not yet calibrated), `band`; plus `frame_t_mono`, `t_mono` (time served), `fps`, `hfov_deg`, `bands`. No images. `/alerts` is unchanged.

Bridge (port 8081): with `--fusion on`, or `--fusion auto` (default) once the detector has answered, `/telemetry` gains a `fusion` key, absent (not null) while fusion is inactive:

```json
"fusion": {
  "hazards": [
    {"class": "person", "source": "fused", "sensor": "ahead", "bearing_deg": -3.1, "distance_m": 0.98,
     "band": "immediate", "confidence": 0.71, "camera_distance_m": 1.31, "tof_distance_m": 0.98, "tof_dt_ms": 12},
    {"class": "obstacle", "source": "tof", "sensor": "right", "bearing_deg": 35.0, "distance_m": 0.62,
     "band": "immediate", "confidence": null, "camera_distance_m": null, "tof_distance_m": 0.62, "tof_dt_ms": null}
  ],
  "age_ms": 80, "camera_fps": 14.8, "camera_age_ms": 160, "config": "fusion_config.json"
}
```

`source` is `fused` (camera class, ToF distance), `camera` (no ToF match; camera estimate) or `tof` (ToF only, class `obstacle`, debounced over 3 readings). `band` is recomputed from `distance_m` with the detector's thresholds. Hazards are sorted nearest first. `camera_age_ms` is null when the detector is not answering (then only ToF obstacles appear). The same object is served at `GET /hazards` (503 while inactive). Every update can be appended to `--fusion-log` (off by default; given a path only for a C9 test session, as routine logging of distances and bearings is outside the data handling designed for the camera) (`BenchTest/TEST_PROCEDURES.md`).

Dashboard use: none yet. The front-obstacle mapping of section 3 (`tof.ahead_mm`) stays as decided on 2 Oct. A later step could show the nearest `fused` or `tof` hazard with its class and side, once C9 has been run on the Pi.

## 6. Raw IMU stream: capture files and clock alignment (added 22 Oct 2026)

Firmware 0.7.5 sends every IMU sample (200 Hz) as RAW lines, plus RAWH (scale factors and counters, every 5 s) and RAWS (one per sync-pin edge, every 500 ms). Format, CRC and units: `TelemetryUnit/RAW_STREAM.md`; reference decoder: `TelemetryUnit/tools/raw_stream_decode.py`. Status: written and tested offline with simulated streams (`CameraDetection/tests/test_bridge_raw.py`, `BenchTest/tests/test_raw_capture.py`); not yet run on the Pis.

### 6.1 Where the raw lines are saved

| Node | Link | Read by | Files |
|---|---|---|---|
| rear (Makerfabs board, IMU 1 and 2) | UART `/dev/serial0`, 460800, on the Pi 4 | `CameraDetection/telemetry_bridge.py` (`telemetry-bridge.service`) | Pi 4: `/home/ogeder/rawlog/rear_raw_YYYY-MM-DD_HHMMSS.txt` |
| front (ESP32-S3, IMU 1) | USB serial on the Pi 5 (`/dev/serial/by-id/*Espressif*`, usually `/dev/ttyACM0`) | `BenchTest/raw_capture.py` (`sw7-front-node.service`) | Pi 5: `/home/piadam/roadtest/raw_front/front_raw_YYYY-MM-DD_HHMMSS.txt` |
| rear sync edges | rear GPIO15 to Pi 4 GPIO17 (fitted) | `CameraDetection/sync_logger.py` on the Pi 4, as before | the `--out` CSV it was started with |
| front sync edges | front GPIO15 to Pi 5 GPIO17 (not fitted yet, 6.3) | `sync_logger.py` (`sw7-front-sync.service`) | Pi 5: `/home/piadam/roadtest/raw_front/front_sync_YYYY-MM-DD_HHMMSS.csv` |

Line format in both capture files: `<host_epoch_s> <line exactly as received>`, where `host_epoch_s` is that Pi's wall clock (`time.time()`, Unix seconds, 6 decimals) when the serial read that completed the line returned. Reads are paced at about 20 ms, so lines read together share a time. The bridge's file holds only lines with a RAW, RAWH or RAWS type word, including those that fail their CRC (so losses can be counted); the front file holds every line (DASH, boot log, command replies). A trailing `\r` is removed, nothing else.

Files: the name is the Pi's local time when the file was opened; a new file at each service start, every hour and at 100 MB; flushed every second; writing pauses while the disk has under 1000 MB free (counted in `not_written`, reason in `paused`); nothing is ever deleted unless the bridge is given `--raw-keep-mb`. Size: rear about 15 kB/s (54 MB per hour), front about 7.5 kB/s. The bridge creates its directory on the first raw line, so the Pi 5's bridge (no serial port) never writes anything. Options: `--raw-dir`, `--no-raw-capture`, `--raw-max-mb`, `--raw-rotate-s`, `--raw-min-free-mb`, `--raw-keep-mb` (bridge); `--out`, `--no-capture`, `--max-mb`, `--rotate-s`, `--min-free-mb` (raw_capture.py).

Reading them: the reference decoder reads both files as they are (it finds the type word behind the time field) and ignores the host time: `python TelemetryUnit/tools/raw_stream_decode.py <file> --out <csv dir>`. For the host time, take the first field of each line. For a DASH line in a front file, drop the first field and parse the rest as in section 1.

The front node's latest DASH line and the capture counts are served by raw_capture.py at `http://<pi5>:8083/telemetry` in the same shape as section 2 (`esp32`, `tof` null, `bridge` with `program: "raw_capture"`, `connected`, `other_lines` and the `raw` block). The road recorder (`BenchTest/road_logger.py`) polls it twice a second as source `front_node`, next to `rear`, `front`, `rear_alerts` and `front_alerts`.

The rear files stay on the Pi 4. To put a session's files with the recorder file on the Pi 5: `rsync -av ogeder@10.20.0.1:/home/ogeder/rawlog/ /home/piadam/roadtest/raw_rear/` (or `scp` them to the laptop).

### 6.2 Clocks

- Each ESP32: `t_us`, esp_timer microseconds since its boot (RAW `t0_us` and steps, RAWS `t_us`). Crystal accuracy, so tens of ppm of drift; restarts at 0 on every reset (seq restarts too, which marks the reset in the file).
- Each Pi: the wall clock (`host_epoch_s` in the capture files, `t_wall_s` in the sync CSV, `t` in the recorder file) and CLOCK_MONOTONIC (`t_mono_ns` in the sync CSV, the kernel's edge timestamp; also Picamera2's frame clock).
- Pi 4 and Pi 5: chrony over the wired link (`deploy/setup_sw7_chrony.sh`): the Pi 5 serves, the Pi 4 follows, offset well under 1 ms when locked.

The chain for every sample: ESP32 `t_us` to its own Pi's clock (per node, 6.3 or 6.4), then the two Pis onto one base (6.5).

### 6.3 ESP32 time to Pi time from the sync edges (preferred)

Each node toggles its sync pin every 500 ms and sends one RAWS line per edge: edge counter, new level, and `t_us` read just after the pin was written. The Pi logs the same edge on a GPIO input with a kernel timestamp (`sync_logger.py`: `edge` rise or fall, `t_mono_ns`, `t_wall_s`).

Pairing: a RAWS line reaches the Pi a few ms to a few tens of ms after its edge. For each RAWS, take the logged GPIO edge with the same level (1 = rise, 0 = fall) nearest before the RAWS line's `host_epoch_s`. Edges are 500 ms apart, so this cannot pick the wrong edge while the delay stays under 250 ms. Then fit `t_pi = a + b * t_us` by least squares over the run (or per few minutes), dropping pairs with residuals over 1 ms; `b - 1` is the ESP32 crystal's drift. Fit on `t_mono_ns` (kernel timestamps, tens of microseconds of noise) and move to the wall clock with the median of `t_wall_s - t_mono_ns / 1e9` over the CSV, as `t_wall_s` alone carries Python scheduling jitter. Every RAW sample's Pi time is then `a + b * t_us`. Expected accuracy: well under 1 ms (not measured yet).

Rear: the wire is in place (rear ESP32 GPIO15 to Pi 4 physical pin 11, GPIO17; test C6) and `sync_logger.py` runs on the Pi 4. Its CSV must be recorded for every run that needs the raw data.

Front: the front node drives its own sync pin (GPIO15, `-D SYNC_PULSE_PIN=15` in `[env:front_node]`), but no Pi 5 input is wired to it yet. Steps for the student, before a run that needs front-to-rear alignment better than a few ms:

1. Fit a wire from the front ESP32's GPIO15 to the Pi 5's physical pin 11 (GPIO17), and a ground wire from the ESP32's GND to the Pi 5's physical pin 9. Both boards are 3.3 V logic, no level shifting. The board is not confirmed yet: if the sync pin is moved by build flag, use that pin. GPIO17 is free on the Pi 5 (the front ToF sensors use I2C on pins 3 and 5 and XSHUT on GPIO22, 23, 24, pins 15, 16, 18).
2. Copy `CameraDetection/sync_logger.py` to `/home/piadam/sync_logger.py`. Check the header chip name with `gpiodetect` (the `pinctrl-rp1` chip: `gpiochip0` on current Pi OS kernels, `gpiochip4` on older ones), then test for 10 s: `python3 /home/piadam/sync_logger.py --chip gpiochip0 --line 17 --duration 10 --out /tmp/front_sync_test.csv`. Pass: about 20 edges, median interval 500 ms, none outside 500 +/- 20 ms.
3. Install `deploy/sw7-front-sync.service` (change `--chip` in it if step 2 needed another chip): `sudo cp sw7-front-sync.service /etc/systemd/system/`, `sudo systemctl daemon-reload`, `sudo systemctl enable --now sw7-front-sync.service`. It writes `/home/piadam/roadtest/raw_front/front_sync_<start time>.csv`, a new file at every start.

### 6.4 Without a sync wire (front node until 6.3 is done)

The host receive times give a coarser alignment. A RAW line is sent once its last sample is taken, so for each RAW line, `host_epoch_s - t_last_us / 1e6` (with `t_last_us` the time of the line's last sample) is the clock offset plus a delay that is never negative (USB or UART transfer, the firmware sender task, the Pi's 20 ms read pacing). Take the lower envelope: the minimum of that difference in each 10 s window, then fit a straight line through those minima for offset and drift. Expected error a few ms (not measured); enough to line up road events, not enough for sample-level front-to-rear comparisons at 200 Hz (5 ms per sample), which need the wire. The same method on the rear files is a cross-check of 6.3.

### 6.5 Across the two Pis

Both Pis' wall clocks are kept together by chrony over the wired link (`setup_sw7_chrony.sh`, run once on each Pi). Before and after each session, record `chronyc tracking` on the Pi 4 (the "System time" line is its offset from the Pi 5) and keep it with the session files, for example from the Pi 5: `ssh ogeder@10.20.0.1 chronyc tracking > /home/piadam/roadtest/chrony_pi4_$(date +%H%M).txt`. With the clocks locked, rear sample times (Pi 4 wall clock, from 6.3) and front sample times (Pi 5 wall clock) are on one time base to within that offset, under 1 ms, and on the same base as the recorder file's `t`.
