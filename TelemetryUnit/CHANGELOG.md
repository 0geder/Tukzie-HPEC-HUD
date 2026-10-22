# TelemetryUnit firmware changelog

Firmware changes, newest first. The repository-wide record is CHANGELOG.md at the root; this file holds the firmware detail and the bench test for each version.

## v0.7.5, 22 Oct 2026 (built, host-tested, not flashed)

For the second road run (Planning/run2-readiness-prompt.md, workstream D).

### Changes

- Raw IMU stream to the Pi (src/main.cpp RawSenderTask, include/raw_stream.h, RAW_STREAM.md). Every sample of every IMU, as RAW lines of up to 10 samples with node, IMU, slot sequence, esp_timer time, sync pin level and stuck flag per sample, raw 16-bit counts, CRC-16. RAWH lines (scale factors and counters, every 5 s) and RAWS lines (one per sync edge with its esp_timer time) let the Pi convert units and align clocks. Rear unit: on the UART link only. Why: the road characterisation needs the 200 Hz signal, and up to v0.7.4.1 only 1 s features left the board.
- Non-blocking path: the IMU tasks put each sample on a separate 200-deep queue with no wait (full: dropped and counted); a sender task at the lowest priority on core 0 batches and writes each line in one call, only when the port keeps 640 bytes free for the DASH line, and gives a line up after 50 ms of a full port (its samples counted too). Serial2 TX buffer 2 KB to 8 KB. Link budget: about 15 kB/s of the 46 kB/s at 460800 baud.
- IMU read checked (ImuTask, readImuRaw): one 14-byte I2C burst read with the bus result checked, in place of Adafruit getEvent(), which always returns true (on a failed read it converted whatever was in its buffer) and read the two range registers again on every sample (three transactions per sample, now one). The floats for the ride features are computed with the driver's own arithmetic, so they are unchanged. A failed read sends nothing and is counted (rdfail); a read identical in all six values to the previous good one is counted as stuck. Slot numbers advance on every period, so gaps show in the raw stream.
- DASH line: "node", "rdfail":[a,b], "stuck":[a,b], "rawdrop":[a,b] appended at the end; every existing field unchanged (CameraDetection/telemetry_bridge.py only needs the "DASH " prefix and valid JSON). DASH_LINE_MAX 480 to 576 bytes; DashboardIntegration/TELEMETRY_LINK.md still says 480 and needs the same change by whoever owns it (the bridge accepts 4096).
- !status prints the node, raw stream state, lines sent and per-IMU rdfail, stuck and rawdrop (queue and port parts), sync edges. New commands !raw off and !raw on. StatsTask prints an "IMU health" line every 2 s.
- Front IMU node build (platformio.ini [env:front_node], NODE_FRONT=1): same source, one IMU, no modem, BLE, GNSS, MQTT, flash log or Hall counter. DASH with fewer fields (seq, up_ms, fw, vib, imu_hz, drops, node, rdfail, stuck, rawdrop) and the raw stream (node "front") on USB serial, on a UART too with -D LINK_UART_ENABLE=1. IMU pins (default SDA 8, SCL 9), sync pin (default 15) and UART pins are build flags; the board is not confirmed yet. A small CommandTask handles !help, !status, !dash, !raw, !recal. [platformio] default_envs keeps plain "pio run" and upload on the rear unit, and front_node has no upload_port, so it cannot be flashed to COM10 by mistake.
- Privacy (include/payload_privacy.h, mqttPublish): "lat", "lon" and "acc_m" are removed from every published record, live and replayed, because the default broker (test.mosquitto.org) is public. The local log and the DASH line to the Pi keep them. -D MQTT_INCLUDE_POSITION=1 (or a define in mqtt_secrets.h, see mqtt_secrets.example.h) publishes them to a private broker.
- Version string v0.7.5.

### Verification on the laptop

- test_host/run.py: test_sync_ledger PASS (unchanged); test_raw_stream PASS, 2326 checks: CRC check value, exact record layout, limits (longest RAW line 374 bytes, RAWH 76, RAWS 51), decoder round trip, every single-character corruption caught, a minute of simulated two-IMU traffic with read failures, stuck reads, queue overflows and full-port losses (for each IMU: produced = decoded + queue drops + port drops, and missing seq numbers = rdfail + queue drops + port drops), position scrub. tools/raw_stream_decode.py --selftest PASS: the Python decoder recovers the same 21982 samples from the capture the C++ test wrote, rejects the damaged line and reads RAW lines with other text in front.
- pio run (rear): SUCCESS, RAM 16.1 % (52764 of 327680 bytes), flash 16.1 % (1053645 of 6553600 bytes).
- pio run -e front_node: SUCCESS, RAM 7.3 % (23876 bytes), flash 9.5 % (318577 of 3342336 bytes).
- Not flashed; nothing below has been run on hardware yet.

### Bench test before run 2 (rear unit, on the bench, Pi connected by the UART)

1. Flash with `pio run -t upload`, open the monitor. Pass: banner "Firmware v0.7.5, node rear"; both IMUs found.
2. Timing unchanged: leave it 10 minutes still. The 2 s stats lines must show IMU1 and IMU2 at 200.0 Hz, dropped=0, dt max no worse than on v0.7.4.1 (compare with the last v0.7.4.1 log). The "IMU health" line: rdfail and stuck 0 (a few stuck at rest would be a finding to write down, not a pass).
3. Raw stream: on the Pi, capture the UART for 10 minutes (for example `cat /dev/serial0 > raw.txt` with the port set to 460800 raw, the bridge stopped, or the recorder once it saves RAW lines), then `python TelemetryUnit/tools/raw_stream_decode.py raw.txt --out raw_csv`. Pass: per IMU about 120000 samples, 0 missing by seq, mean rate 200 Hz, bad lines 0, sync edges about 1200, last RAWH and DASH rawdrop [0,0], rdfail [0,0].
4. DASH still parsed: run CameraDetection/telemetry_bridge.py on the UART with the raw stream on. Pass: its DASH line count rises by 1 per second and bad lines stay 0; the dashboard shows live values. The bridge now reads everything waiting per call and saves the raw lines to /home/ogeder/rawlog/; check its CPU on the Pi 4 at 15 kB/s (0.2 % of a laptop core in the offline test).
5. Stress: on the laptop send !log dump and wait for the GNSS and MQTT cycles while the capture runs. Pass: rawdrop stays 0, IMU dropped stays 0.
6. Read failure: briefly pull IMU2's SDA wire. Pass: rdfail[1] rises, the gap appears as missing seq in the capture, IMU1 unaffected, IMU2 recovers when reconnected (if it does not, the sensor needs re-initialising: a finding).
7. Privacy: with MQTT connected, subscribe to the topic (BenchTest/mqtt_broker_check.py or mosquitto_sub). Pass: no "lat", "lon" or "acc_m" keys in the messages; !log dump still shows them.
Front node: the same steps 1 to 4 on USB serial, with "node front" and one IMU.
