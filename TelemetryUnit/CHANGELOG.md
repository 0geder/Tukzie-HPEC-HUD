# TelemetryUnit firmware changelog

Firmware changes, newest first. The repository-wide record is CHANGELOG.md at the root; this file holds the firmware detail and the bench test for each version.

## v0.7.6, 22 Oct 2026 (built, host-tested, not flashed)

Fix for the rear-unit fault of 21 and 22 Oct 2026 (lab notebook): after 25 to 45 min on its own LiPo, with the modem silent, the drop counters rose at about 168/s (IMU1) and 46/s (IMU2), imu_hz stayed at 200 and 200, vib was null, until a reset.

### What the code says about the fault (v0.7.4.1, the firmware in the field)

- imu_hz is written only by StatsTask, at the end of each 2 s report. A value frozen at exactly 200.0 while drops climb means StatsTask had stopped completing reports. vib null means both ride tasks had stopped publishing windows as well (fusion falls back to one IMU if only one stops).
- StatsTask drains both IMU queues in the same pass, at most a full queue (100) of each, so any slow-but-running consumer drops the same number from two 200 Hz producers. Rates of 168 and 46 cannot come from the consumer side. With the consumer stopped, every sample sent is dropped, so the drop rates are the producers' own rates: the IMU1 task was running at about 168 Hz and IMU2 at about 46 Hz (v0.7.4.1 sends on every pass, since getEvent() never reports a failure).
- An IMU task below 200 Hz is behind its vTaskDelayUntil schedule, and a task behind schedule returns from vTaskDelayUntil at once, so it only ever waits inside the I2C driver. StatsTask (priority 2), both ride tasks (priority 1) and SyncTask (2) were on core 1 under the two IMU tasks (priority 3). So the signature is: core 1 fully used at priority 3 and above (the IMU tasks plus interrupt work), nothing below it running.
- Ruled out by reading the code: (1) modem, MQTT, GNSS, AGPS, cell position and BLE work all run on core 0 (ModemTask, BmsTask, Bluedroid pinned to core 0 in the SDK config), and every wait loop there yields (vTaskDelay 1 to 5 ms, or delay(), which is vTaskDelay); none can take CPU from core 1. (2) No lock is shared between the IMU consumers and the modem path; the USB console lock has a 100 ms timeout and with no USB host the write is discarded at once. (3) Nothing on the IMU, queue or ride path allocates; Serial.printf mallocs for lines over 64 bytes but returns 0 if that fails. (4) No counter arithmetic gives 168 and 46 (above).
- Not settled by the code: what loaded core 1 and slowed the IMU tasks. The interrupts of the drivers started in setup() run on core 1: UART2 (the Pi link, RX on IO42, which floats against the Pi's default pull-down while the Pi reboots; on 21 Oct the link was being rewired and on 22 Oct both Pis restarted), both I2C controllers (IMU2 was not detected after a reset on 21 Oct, so its bus is suspect) and USB Serial/JTAG. The weak battery (brown-out on 21 Oct) and the silent modem were common to both days. The bench test below separates these.

### Changes

- Consumers off the IMU core (setup): StatsTask and both ride tasks now run on core 0 at priority 2 (CONSUMER_CORE, CONSUMER_PRIORITY), above every other task of this firmware there (modem, BLE, DASH, raw sender, Hall, command, all priority 1). Core 1 keeps only the two IMU tasks (priority 3) and SyncTask (2). The queues work across cores; the consumers' code is unchanged. IMU acquisition timing is unchanged (same tasks, same core, same priority, same period); core 1 has fewer tasks than before.
- Bounded catch-up (ImuTask, imuWaitNextSlot, include/imu_pacing.h): an IMU task more than 20 periods (100 ms) behind gives up the missed slots instead of running them back to back, so it sleeps at least every 20 periods or so. Slot numbers advance by the same count (the gap shows as missing seq in the raw stream) and the slots are counted ("late"). Below 100 ms nothing changes: the 33 to 40 ms flash-write pause is still caught up exactly as before.
- StatsTask rates over the real elapsed time (was the nominal 2 s), and a new "IMU pacing" line every 2 s.
- DASH line, four fields at the end (every older field unchanged): "cons_age_ms":[stats,ride1,ride2] ms since each consumer last ran (normal: under 10 and under 60; -1 never ran), "qmax":[a,b] highest IMU queue fill since boot (100 = full), "late":[a,b] slots given up, "idle":[core0,core1] idle-hook calls in the last second (0 = that core never idled). The front node has one IMU in cons_age_ms, qmax and late. DASH_LINE_MAX 576 to 704 and RAW_DASH_RESERVE 640 to 704 (static_assert that the reserve holds a whole DASH line). DashboardIntegration/TELEMETRY_LINK.md still gives the older maximum (the bridge accepts 4096).
- !status prints consumer ages, late and qmax. New commands !modem off (AT+CPOF: powers the modem down, so it stops answering, for the bench test) and !modem on (pulses the power key if the modem does not answer).
- Version string v0.7.6.

### Verification on the laptop

- test_host/run.py: test_sync_ledger PASS, test_raw_stream PASS (2326 checks), new test_imu_pacing PASS (254 checks: single cases including the 32-bit tick wrap and phase; a tick-level model of the IMU loop showing that a 6 ms or 22 ms read never sleeps without the bound and sleeps regularly with it, lag bounded, samples + skipped = slot number, and a 40 ms stall caught up identically with and without it; consumer age and high-water helpers), raw_stream_decode.py selftest PASS.
- pio run (rear): SUCCESS, RAM 16.2 % (52948 bytes), flash 16.1 % (1055049 bytes).
- pio run -e front_node: SUCCESS, RAM 7.4 % (24260 bytes), flash 10.0 % (334221 bytes).
- Not flashed. AT+CPOF is in the A76XX command set but has not been tried on this board.

### Bench reproduction and pass test (rear unit, Pi 4 on the UART link)

Setup: rear board on its own LiPo, USB unplugged (opening COM10 resets the board; unplugging does not). Pi 4 bridge running on /dev/serial0. Log the ESP32 block every 5 s on the Pi:

    while true; do curl -s localhost:8081/telemetry | python3 -c 'import sys,json; e=json.load(sys.stdin).get("esp32") or {}; print(json.dumps({k: e.get(k) for k in ("up_ms","drops","imu_hz","vib","csq","cons_age_ms","qmax","late","idle","rdfail","rawdrop","age_ms")}))' >> ~/esp_health_$(date +%F_%H%M).jsonl; sleep 5; done

1. Reproduce first on v0.7.4.1 (commit 8fb5f5e), so the trigger is known. Flash, open the monitor, wait for "Entering pass-through mode", type AT+CPOF (pass-through to the modem), then unplug the USB. Check csq goes null. Run 60 min. If drops start rising, note the time and the up_ms. If not, repeat 60 min runs adding one factor each: (a) reboot the Pi 4 once at about 10 min (sudo reboot); (b) pull the IO42 wire (Pi TX to ESP RX) for 10 s and refit it; (c) the part-discharged LiPo used on 21 Oct; (d) wiggle the IMU2 wires (IO17/18). The factor that starts the drops is the trigger.
2. Flash v0.7.6 (pio run -t upload), check the banner "Firmware v0.7.6, node rear" and both IMUs found, unplug the USB. Silence the modem from the Pi: printf '!modem off\n' > /dev/serial0. Run 60 min under the same conditions, including the factor found in step 1.
3. Pass, over the whole 60 min: drops stay [0,0]; vib is a number in every line after the first few seconds; imu_hz 200.0 (199.5 to 200.5) for both; cons_age_ms under 200 for all three; late [0,0]; qmax under 50; idle above 0 for both cores in every line; rawdrop [0,0]; csq null throughout (the modem really was silent). Then !modem on and check csq returns.
4. If the trigger still bites, the new fields say where: idle[1] at 0 with late rising means core 1 is saturated (look at the Pi link and the I2C buses); rdfail[1] rising means IMU2's bus is failing; idle[0] at 0 with cons_age_ms high means core 0 is saturated (modem or BLE).

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
