# Central database and store-and-forward sync (brief, 11 Oct 2026)

## Why

The brief asks for telemetry "logged locally and transmitted via a cellular module (4G/LTE) to a central database", and the report must validate "successful remote data synchronisation with the central database". Up to firmware v0.7.3 the unit logs every 10 s record to LittleFS and publishes the same record over MQTT when the link is up, but:

- nothing receives the records into a database (the broker is a relay, not a store);
- the log does not record which records the broker acknowledged, and nothing is resent after an outage, so records made during a coverage gap only exist on the board;
- records carry no sequence number, boot id or device time, so completeness and latency cannot be measured.

This is the biggest remaining gap against the brief.

## What

1. Firmware v0.7.4, store-and-forward that can be validated.
   - Every record gets `dev`, `fw`, `boot` (NVS counter, +1 per boot), `seq` (monotonic across reboots, reserved from NVS in blocks of 64 so NVS is written about every 10 minutes, not every record), `up_ms` and `utc_ms` (device UTC from the GNSS time, null until the first fix). The same line goes to the local log and to MQTT.
   - A ledger tracks the highest `seq` up to which every record is acknowledged by the broker (QoS 1, `+CMQTTPUB: 0,0`) or counted as lost. After a reconnect, the modem task reads unacknowledged records back from the LittleFS log in order and republishes them with `"replay":true` on the same topic, at most about 3 per second, while live records keep flowing every 10 s. All modem access stays on ModemTask (core 0); nothing runs on core 1.
   - Records that can no longer be sent (log truncated at 3 MB, log cleared, logging off, failed flash write) are counted as lost, never skipped silently.
   - `!sync` prints the ledger; `!sync drop` gives up the backlog (counted as lost).
   - Also in v0.7.4: MPU6050 digital low-pass filter 94 Hz instead of 260 Hz (sampling is 200 Hz, so content above the 100 Hz Nyquist frequency would alias).
2. Server/ (our own central database, independent of any partner's).
   - `sw7_ingest.py`: subscribes to any MQTT broker (environment variables or a config file), validates each record and stores it in SQLite, idempotent on (dev, boot, seq), so a replayed or redelivered record is never stored twice. Runs on the Pi 5 as a normal user in a venv.
   - `sync_report.py`: completeness (gaps per boot, duplicates, replayed count, optional comparison with a `!log dump` copy), backlog drain and end-to-end latency (median, 95th percentile), as text and CSV.
3. Bench test T15 (outage and replay) in `BenchTest/TEST_PROCEDURES.md`, with pass criteria for completeness, drain time and latency.
4. Laptop tests without hardware: host-side C++ test of the firmware ledger (including a randomised outage, reboot and truncation simulation) and Python tests of ingest and report, including the MQTT path through a local fake broker.

## Partner broker

Melokuhle Bango's gateway (JBM11) sends tuk-tuk telemetry over MQTT to a remote server. Its broker details are not known yet. The design takes any broker from `include/mqtt_secrets.h` (firmware) and environment variables or `Server/sw7_ingest.env` (server), so pointing both at that broker later is a configuration change, while our database does not depend on theirs.

## Status (tested vs untested, 11 Oct 2026)

Tested on the laptop and the Pi 5:
- Firmware ledger logic (`TelemetryUnit/include/sync_ledger.h`): `python TelemetryUnit/test_host/run.py`, 40 checks pass, including 900 randomised runs of 3,000 records each with outages, failed and unacknowledged publishes, power cuts, soft reboots, log truncation, log clears and logging switched off. Each run ends with the backlog at zero and every record the server never got counted as lost, except what a power cut takes (unflushed RAM lines and lost counts since the last NVS save).
- Firmware v0.7.4 compiles (RAM 15.3%, flash 16.0%).
- Server: `python Server/tests/test_server.py`, 11 tests pass on the laptop and on the Pi 5, including the MQTT path through a fake broker. Synthetic v0.7.4 records through test.mosquitto.org: 10 of 10 stored on the laptop and 20 of 20 on the Pi 5, replays and duplicates handled, 0 missing.
- The Pi 5 ingest service is running and received live v0.7.3 records from the unit over LTE (rejected as expected, since they have no seq).
- test.mosquitto.org did not queue records for a stopped ingest (persistent session, QoS 1, 0 of 5). Hence `--import-log` backfill from the unit's log.

Not tested:
- v0.7.4 on the board (not flashed): seq and boot persistence, replay after a real outage, the assumption that `+CMQTTPUB: 0,0` means the PUBACK arrived, GNSS UTC on the board, effect of replay log reads and NVS writes on IMU timing, the 94 Hz filter on real vibration. Bench test T15 covers these.
- Melokuhle's broker.
