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
  "bridge": { "version": "1.0", "serial_port": "/dev/ttyACM0", "lines": 1234, "bad_lines": 2 }
}
```

`age_ms` is the time since that part was last updated, so the dashboard can mark stale data. The bridge must keep serving when the ESP32 is unplugged or the ToF sensors are absent (those parts become null).

## 3. Pi 5 dashboard: live-data provider

`DashboardIntegration/live_data_provider.py` polls `http://<pi4>:8081/telemetry` twice a second (address from the environment variable `TUKZIE_TELEMETRY_URL`, default `http://192.168.137.82:8081`) with Qt networking only, maps fields onto the dashboard's `VehicleState` and passes them to `VehicleStateManager.ingest_live_state()`. Mapping:

| Bridge field | Dashboard field | Note |
|---|---|---|
| `esp32.soc` | `soc_pct` | |
| `esp32.v * esp32.i / 1000` | `signed_battery_power_kw` | sign convention to be checked on the vehicle |
| `esp32.lat`, `esp32.lon` | `latitude`, `longitude` | only when `fix` is true |
| `esp32.fix` | GPS entry of `signal_validity` | |
| `esp32.spd_raw` | `speed_kmh` | NOT mapped until the units are confirmed; shown on the ride card only |
| `esp32.rpm` | (ride card) | |
| `tof.ahead_mm / 1000` | `front_obstacle_distance_m` | nearest valid of the three if the field expects one value |
| `esp32.vib`, `vib_dis`, `imu_hz`, `drops`, `csq`, `mqtt` | ride-quality card (new) | the dashboard has no fields for these |

Parts of the dashboard state with no source here (gear, throttle, brake, tyres, doors, motor temperature) are left to the existing behaviour. When the bridge cannot be reached, or `esp32.age_ms` exceeds 3000, the provider stops sending, so the dashboard's own stale-data fallback takes over.
