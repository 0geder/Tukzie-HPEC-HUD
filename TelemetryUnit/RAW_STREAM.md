# Raw IMU stream (firmware v0.7.5, re-init marking v0.7.7)

Every IMU sample, at 200 Hz, goes to the Pi as text lines on the same link as the 1 Hz DASH line. The full definition, with the byte layout, is in `include/raw_stream.h`; this page is the short version for the Pi side. Reference decoder: `tools/raw_stream_decode.py` (standard library only), checked against the firmware's own encoder by `test_host/run.py`.

## Where it goes

| Node | Build | Link |
|---|---|---|
| rear (Makerfabs A7670X, IMU 1; IMU 2 only if built with `-D ENABLE_IMU2=1`, off since v0.7.7) | `pio run` (env esp32-s3-devkitc-1) | UART IO41 TX / IO42 RX, 460800 8N1. Not on USB. |
| front (generic ESP32-S3, IMU 1) | `pio run -e front_node` | USB serial; also the UART if built with `-D LINK_UART_ENABLE=1` |

`!raw off` and `!raw on` switch it at run time (default on). `!status` prints the counters.

## Lines

Every line ends in `\n` and starts with its type word. Read lines and split by the first word; ignore anything else (boot log, debug prints). DASH is unchanged and still starts with `DASH `.

```
RAW 2 <node> <imu> <seq0> <t0_us> <n> <hex> <crc>
RAWH 2 <node> <imu> <accel_counts_per_g> <gyro_counts_per_dps> <rate_hz> <dlpf_hz> <fw> <rawdrop> <rdfail> <stuck> <crc>
RAWS 2 <node> <edge> <level> <t_us> <crc>
```

- `crc`: CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) of every byte from the type word up to the character before the space in front of the CRC, 4 lowercase hex digits. Check value: "123456789" gives 29b1. A line that fails is dropped whole.
- `node`: `rear` or `front`. `imu`: 1 or 2.
- RAW: up to 10 consecutive samples of one IMU (50 ms). `seq0` and `t0_us` (esp_timer microseconds since boot) belong to the first sample; then n records of 16 bytes as 32 hex characters: seq step (1 byte), time step in us (2 bytes, big-endian), flags (1 byte: bit 0 sync pin level, bit 1 stuck, bit 2 first sample after the sensor was re-initialised, v0.7.7), then ax ay az gx gy gz as signed 16-bit big-endian counts.
- `seq` counts 5 ms acquisition slots, read or not. A gap in seq is a missing sample: a failed I2C read (rdfail), a sample the stream dropped (rawdrop), or (v0.7.7) time the sensor was down: after 1 s of failed reads with a re-init that failed too, it is not read until a re-init works. The first sample after a re-init has flag bit 2 set, and an extra RAWH for that IMU follows at once.
- RAWH, per IMU at start and every 5 s: scale factors (4096 counts per g, 65.5 counts per deg/s), 200 Hz, 94 Hz sensor low-pass, firmware, and the counters since boot. a [m/s^2] = count / 4096 * 9.80665; w [rad/s] = count / 65.5 * pi / 180. No calibration is applied to raw counts.
- RAWS, one per edge of the sync output (every 500 ms): edge counter, new level, esp_timer time read just after the pin was written. With the Pi's own timestamp of the same edge on its GPIO, pairs of (t_us, Pi time) give clock offset and drift. The front node drives its own sync pin (GPIO15 unless set by build flag), so it needs a second Pi GPIO input.

## Counters (also in DASH, appended at the end; older fields unchanged)

| Field | Meaning |
|---|---|
| `"node"` | `"rear"` or `"front"` |
| `"rdfail":[a,b]` | I2C reads that failed (not acknowledged, or short) |
| `"stuck":[a,b]` | good reads with all six values equal to the previous good read (registers not updating) |
| `"rawdrop":[a,b]` | samples never sent on the raw stream: the queue to the sender was full, or no port took the line |
| `"reinit":[a,b]` | v0.7.7: re-inits that worked (sensor woken and configured again after 1 s of failed or identical reads, or found after being absent at boot). Not in RAWH, whose field count the readers check. |
| `"imu_up":[a,b]` | v0.7.7: 1 read, 0 down (missing, re-init retried every 1 s, then 5 s), -1 not enabled in this build |

The front node's arrays have one element. The rear unit's keep two with IMU2 off, the second 0 (imu_up -1). Over a whole capture, for each IMU: missing seq numbers = rdfail + rawdrop + slots spent down.

## Link budget

460800 baud, 8N1: 46080 bytes/s.

| Line | Size | Rate | Bytes/s |
|---|---|---|---|
| RAW, rear, 10 samples | about 363 B (374 worst case) | 20 per IMU per s | about 7260 per IMU |
| RAW, 2 IMUs | | | about 14500 |
| RAWH | about 70 B | 2 per 5 s | about 30 |
| RAWS | about 45 B | 2 per s | about 90 |
| DASH | about 380 B (576 max) | 1 per s | about 380 |
| Total | | | about 15000, 33 % of the link |

36 bytes per sample on the wire (hex text, chosen over binary so the stream is line-based like DASH and can be read in a terminal); binary would be about 2.3 times smaller but is not needed at this rate.

## How it stays out of the IMU timing

The IMU tasks put each sample on a 200-deep queue with no wait; a full queue drops and counts the sample. A sender task at the lowest priority on core 0 (the IMU tasks are on core 1) batches and writes each line with one write call, and only when the port's 8 KB TX buffer keeps 768 bytes free after it (640 in v0.7.5), so the DASH line always fits. If a port stays full for 50 ms the line is given up and its samples are counted in rawdrop.

## Bench test after flashing (not yet run)

See the v0.7.5 entry in `CHANGELOG.md`.
