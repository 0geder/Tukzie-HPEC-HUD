# SW-7 central database (Server/)

The brief asks for telemetry "logged locally and transmitted via a cellular module (4G/LTE) to a central database". The telemetry unit logs every 10 s record to its own flash and publishes it over LTE to an MQTT broker. A broker only relays messages, so this folder is the central database: a small program that subscribes to the broker and stores every record in SQLite, and a report that shows how complete and how fast that copy is.

It does not depend on any partner's server. It works with any MQTT broker, so it can be pointed at Melokuhle Bango's gateway broker (JBM11) once its details are known (see the last section).

## Files

- `sw7_ingest.py`: MQTT to SQLite. Checks each record and stores it once per (dev, boot, seq), so replays and redeliveries never duplicate. Records from firmware before v0.7.4 (no seq) and anything malformed go to a `rejects` table with the reason. `--import-log` backfills from a copy of the unit's log.
- `sync_report.py`: completeness (missing seq per boot, duplicates, replays, comparison with the unit's log), backlog drain and end-to-end latency (median, 95th percentile), as text and CSV. `--check` gives a pass/fail exit code for tests.
- `run_ingest.sh`, `sw7-ingest.service`: start script and systemd user unit for the Pi 5 (no sudo).
- `sw7_ingest.env.example`: broker settings template; copy to `sw7_ingest.env` (git-ignored).
- `tests/test_server.py`: laptop tests, no hardware or internet (records fed directly, plus the MQTT path through a minimal fake broker on 127.0.0.1).

## Record format (firmware v0.7.4)

Every record starts with its identity, then the existing fields:

```
{"dev":"sw7-esp32-telemetry","fw":"0.7.4","boot":12,"seq":3456,"up_ms":5234000,"utc_ms":1791800000000,
 "imu1":{...},"imu2":{...},"fused":{...},"bms":{...},"gnss":{...},"cell":{...},"hall":{...}}
```

- `boot` goes up by one at every boot (NVS). `seq` goes up by one per record and never repeats, also across reboots (reserved from NVS in blocks of 64, so it jumps at a reboot; that jump is not a gap).
- `utc_ms` is the unit's UTC from the GNSS time, null until the first fix after boot.
- A record resent after an outage has `"replay":true` added at the front. Same topic.

Stored columns: dev, boot, seq, replay, recv_ms (server time), device_utc_ms, up_ms, fw, lat, lon (only with a GNSS fix), cell_lat, cell_lon, vib (fused std), soc, speed_raw (units not yet confirmed), csq, topic, dup_count, raw JSON.

## Run on the Pi 5 (Pirate5), as piadam, no sudo

Laptop (PowerShell, repo root), copy the files:
```
scp -i ~/.ssh/pi4_camera_key Server/sw7_ingest.py Server/sync_report.py Server/run_ingest.sh Server/sw7-ingest.service Server/sw7_ingest.env.example Server/requirements.txt piadam@<pi5-ip>:sw7_server/
```
Pi 5, once:
```
cd ~/sw7_server
python3 -m venv venv && venv/bin/pip install -r requirements.txt
chmod +x run_ingest.sh
cp sw7_ingest.env.example sw7_ingest.env      # edit only if not using test.mosquitto.org
mkdir -p ~/.config/systemd/user && cp sw7-ingest.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now sw7-ingest
```
Check and report:
```
systemctl --user status sw7-ingest
cd ~/sw7_server && venv/bin/python sync_report.py
venv/bin/python sync_report.py --since 2026-10-12T09:00 --csv reports/2026-10-12 --check
```
The user unit runs while piadam's systemd instance runs. On the Pi 5 that is always, because the desktop session is logged in automatically. Without a logged-in session it stops; `loginctl enable-linger piadam` keeps it running but may need an administrator.

User services on this Pi have no persistent journal (`journalctl --user` showed nothing on 11 Oct). Use `systemctl --user status sw7-ingest`, which shows the last lines.

The Pi 5's clock must be right for the latency figure. It runs NTP (`timedatectl`: synchronised, 11 Oct 2026).

## Run on the laptop

```
python -m pip install paho-mqtt
python Server/sw7_ingest.py                      # Ctrl+C to stop; database Server/sw7_telemetry.db
python Server/sync_report.py --check
python Server/tests/test_server.py               # offline tests
```

## Settings

Order of precedence: command-line options, environment variables, `sw7_ingest.env`, defaults.

| Variable | Default |
| --- | --- |
| SW7_MQTT_HOST | test.mosquitto.org |
| SW7_MQTT_PORT | 1883 (8883 with TLS) |
| SW7_MQTT_USER, SW7_MQTT_PASSWORD | none |
| SW7_MQTT_TOPIC | sw7/telemetry |
| SW7_MQTT_TLS | 0 |
| SW7_CLIENT_ID | sw7-ingest-hostname |
| SW7_DB | Server/sw7_telemetry.db (next to the script) |

## How a record gets from the unit to the database

1. Every 10 s the unit builds a record, appends it to the RAM log buffer (written to flash about once a minute) and, if MQTT is up, publishes it with QoS 1.
2. If the broker acknowledges it (`+CMQTTPUB: 0,0`), the unit marks that seq as done. The A76XX manual is read here as reporting that result once the PUBACK arrives; this is an assumption until test T15 confirms it end to end.
3. After an outage the unit reads the unacknowledged records back from its log, oldest first, and republishes them with `"replay":true`, at most about 3 per second, while new records keep going out every 10 s. State machine: `TelemetryUnit/include/sync_ledger.h`.
4. Records that can no longer be sent (log truncated at its 3 MB cap, `!log clear`, logging off) are counted as lost on the unit (`!sync`), never skipped silently.
5. The ingest stores each (dev, boot, seq) once.

Known limits:
- If the ingest is not running, the broker still acknowledges records to the unit, which then does not resend them. test.mosquitto.org did not queue records for the stopped ingest (11 Oct 2026: 0 of 5 delivered after a restart, persistent session, QoS 1). Keep the ingest running, and backfill gaps from the unit's log: `BenchTest/log_dump.py COM10 dump.jsonl`, then `python Server/sw7_ingest.py --import-log dump.jsonl`. Backfilled rows are marked (topic `log-import`) and left out of the latency and replay figures. A broker under our control (Mosquitto with persistence) would queue them instead.
- A power cut loses the unit's unflushed RAM lines (up to a minute) and up to a minute of its lost count; the report shows them as missing only if later records of the same boot arrived.
- test.mosquitto.org is public: anyone can read or write `sw7/telemetry`. Fine for bench tests, not for real vehicle data. Records from someone else's device would show up under another `dev`.

## Pointing it at Melokuhle's broker later

1. Firmware: copy `TelemetryUnit/include/mqtt_secrets.example.h` to `mqtt_secrets.h` and fill in host, port, user, password and topic; build and flash. The unit uses plain TCP (no TLS in the AT command set used now), so the broker must accept a non-TLS connection on some port, or the firmware needs the modem's SSL context set up first.
2. Server: put the same host, port, user, password and topic in `sw7_ingest.env` on the Pi 5 (`SW7_MQTT_TLS=1` if the ingest should use TLS), then `systemctl --user restart sw7-ingest`.
3. Check with `python BenchTest/mqtt_broker_check.py` from the laptop first.
Questions for Melokuhle: host and port; TLS or not and on which port; whether each client needs its own user; which topics we may publish and subscribe to (ACL); whether the broker keeps persistent sessions and queues QoS 1 messages for offline subscribers; maximum message size (our records are about 0.7 to 1.1 KB); and whether their server already stores our records, in which case this database is a second, independent copy.

## Status (11 Oct 2026)

Tested:
- Laptop: `tests/test_server.py`, 11 tests pass (parsing, dedupe, rejects, reopen, log backfill, report gaps/replay/latency/CSV/--check, end to end through a fake broker with paho-mqtt 2.1.0). Same 11 pass on the Pi 5 (Python 3.13.5, paho-mqtt 2.1.0 in ~/sw7_server/venv).
- Real broker: synthetic v0.7.4 records published from the laptop to test.mosquitto.org were stored by the ingest on the laptop (10 of 10, replays and a duplicate handled) and on the Pi 5 (20 of 20, 5 replays, 0 missing). Those latency numbers are laptop to broker to Pi and include the laptop's clock offset; they are not the unit's latency.
- The Pi 5 user service `sw7-ingest` was started on 11 Oct 2026 (05:36) on sw7/telemetry at test.mosquitto.org. Within the first minute it received 5 records in the v0.7.3 layout, published over LTE by the unit then running (on the Pi 4); they went to `rejects` (no seq). This shows the cellular path into the database host, but not storage of real records.

Not tested:
- Anything with real v0.7.4 records: the firmware is compiled but not flashed. Test T15 in `BenchTest/TEST_PROCEDURES.md` is the end-to-end validation (outage, replay, zero missing, latency).
- Melokuhle's broker (details not known).
