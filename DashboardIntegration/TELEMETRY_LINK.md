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

The line must be built without heap-heavy String concatenation in a timing-critical task and must never block the IMU tasks (core 1). Maximum length 400 bytes.

## 2. Pi 4 bridge: HTTP on port 8081

`CameraDetection/telemetry_bridge.py` reads the ESP32's USB serial port (`/dev/ttyACM0` by default, configurable), keeps the latest `DASH` record, reads the three ToF sensors itself (same wiring and code as `tof_reader.py`), and serves:

`GET /telemetry` returns `application/json`:

```json
{
  "esp32": { ...latest DASH object..., "age_ms": 420 },     // null if no line received yet
  "tof":   { "left_mm": 812, "ahead_mm": 1490, "right_mm": null, "age_ms": 35 },  // null if sensors absent; 8190 or out of range -> null
  "bridge": { "version": "1.0", "serial_port": "/dev/ttyACM0", "lines": 1234, "bad_lines": 2,
              "replay": false, "replay_file": null }
}
```

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
