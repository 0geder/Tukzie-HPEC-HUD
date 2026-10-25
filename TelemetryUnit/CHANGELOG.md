# TelemetryUnit firmware changelog

Firmware changes, newest first. The repository-wide record is CHANGELOG.md at the root; this file holds the firmware detail and the bench test for each version.

## v0.7.9, 25 Oct 2026 (flashed on the rear node and bench-tested; front node not reflashed)

Finding of 24 to 25 Oct 2026: with a SIM whose data connection fails (CMQTTCONNECT codes 3 and 15, CMQTTACCQ errors, AGPS refused, each attempt about 21 s) while the public broker accepted the laptop in 0.4 s, ModemTask spent most of its time in MQTT reconnect waits and polled the GNSS about once in 30 s instead of every 3 s; the receiver fixed only in gaps between attempts (Report Appendix E, GNSS polls starved during broker failures).

### Changes

- New commands !mqtt off and !mqtt on (rear node, run in ModemTask, include/cmd_link.h). Off tears down a live session and stops all connection attempts; on resets the backoff and connects at once. The choice is kept in NVS (namespace mqttcfg, key enabled, default on), so a power cycle on the vehicle keeps it. !mqtt with publishing off replies instead of reconnecting.
- Records are still written to the flash log and the ledger with publishing off, and replay once it is back on.
- mqtt_secrets.h moved aside (to the git-ignored mqtt_secrets.melo.h), so the build uses the default public broker test.mosquitto.org, topic sw7/telemetry.

### Bench test (rear node, 25 Oct, USB on the laptop, antenna under open sky)

- !mqtt off: 33 GNSS replies in 100 s (every 3.0 s), all 33 3D fixes.
- Reset: "Publishing is off" printed at boot (setting kept) and a 3D fix with 35 satellites, HDOP 1.11, 9.6 s after the reset.

## v0.7.8, 22 Oct 2026 (built, host-tested, not flashed)

Field finding of 22 Oct 2026: '!' commands sent from the Pi over the UART link (Serial2, RX IO42) reached the rear unit but were acted on only about 20 to 25 s later. Cause: the rear unit read its commands (Pi UART and USB) in ModemTask's loop, which also runs the MQTT reconnect. With the modem attached but without network (AT+CSQ 99,99), each reconnect step (CMQTTDISC 5 s, CMQTTREL 3 s, CMQTTSTOP 5 s, CMQTTSTART 12 s, CMQTTCONNECT 30 s) waits for its timeout, and AGPS (30 s) and cell position (25 s) do the same, so the loop did not get back to its input for many seconds.

### Changes

- New CommandTask on both nodes (core 0, priority 1, polls every 10 ms; the front node already had one). It reads USB serial and the Pi UART, assembles the lines and runs at once every command that does not use the modem or the state ModemTask writes. Line assembly and the run-now or defer decision are in the new include/cmd_link.h (pure C++, host-tested). Line rules are the same as v0.7.7: on the Pi UART a line of 2 or more characters starting with '!'; on the rear USB console a '!' at the start of a line, everything else goes to the modem; up to 64 characters kept.
- Run at once in CommandTask: !help, !status, !sync (status print), !raw on/off, !dash on/off, !log on, !gnssraw, and unknown commands (reply only). These only read state for printing or set one flag (volatile bool, one write), which is what other tasks already do. !status and !sync print counters that ModemTask may be updating; a print can mix values from just before and just after an update, nothing is written.
- Queued for ModemTask (4-deep queue, a reply "queued for the modem task" at once): !modem off/on (Serial1, power key), !mqtt (mqttConnected and the reconnect timer, which the reconnect also writes), !agps and !cellpos (timers ModemTask rewrites after each attempt), !log off, !log flush, !log dump and !recal (flushLocalLog: the RAM log buffer and the ledger save, written by ModemTask without a lock; !log dump is also a long paced print), !log clear and !sync drop (sync ledger and replay offset). Kept in ModemTask so no lock is needed; a fifth command while 4 wait is refused with a message and counted.
- ModemTask runs the queue at the top of every pass and after each step that can wait on the modem (reconnect, GNSS poll, AGPS, cell position, the 10 s publish). The MQTT reconnect (teardown and connect), AGPS and cell position waits now stop as soon as a command is queued (checked every 1 to 5 ms in mqttSendCommand, mqttAwaitResult and readModemUntil, only while ModemTask has set modemYieldToCommands around those calls). A stopped reconnect is not counted as a failure: the backoff is kept and the attempt is made again on the next pass, after the command. A stopped AGPS or cell-position request is retried on its normal schedule. Publishes, the GNSS poll (2 s) and the signal poll (1 s) are not stopped, so a queued command waits at most a few seconds; during the modem's boot sequence (up to about 40 s with the power-key wait) queued commands wait until it ends, while run-at-once commands work from the start. A reply the modem sends after a wait was stopped is printed by the pass-through as usual.
- AT pass-through on the rear USB console: CommandTask passes the non-'!' bytes to ModemTask through a 256-byte queue and ModemTask writes them to Serial1 (only ModemTask writes Serial1). When the queue is full CommandTask stops reading, so bytes wait in the USB buffer as before. Same behaviour as v0.7.7, including during a reconnect (bytes reach the modem when the loop next passes).
- Counters: DASH "cmd":[rx,now,queued,done] appended as the last field (lines received, run at once, queued, queued ones run; queued minus done = waiting). Front node: queued and done stay 0. !status has a "commands:" line with the same counts plus refused. DASH_LINE_MAX and RAW_DASH_RESERVE 768 to 832 (52 bytes more in the worst case, about 20 in practice). RAW_STREAM.md and tools/raw_stream_decode.py list the field. DashboardIntegration/TELEMETRY_LINK.md still gives an older maximum (the bridge accepts 4096).
- IMU tasks, their core, priority and pacing unchanged. Version string v0.7.8.

### Verification on the laptop

- test_host/run.py: all PASS. New test_cmd_link PASS (49 checks: link and console line assembly, CRLF, split reads, over-long lines, '!' mid-line forwarded, lone '!', normalize, every deferred and run-at-once command classified); test_sync_ledger, test_raw_stream, test_imu_pacing (254), test_imu_recovery (1201) and raw_stream_decode.py selftest PASS.
- pio run (rear): SUCCESS, RAM 16.2 % (53172 bytes, +96), flash 16.1 % (1058293 bytes, +1904). The new task stack (4 KB) and the two queues (about 0.6 KB) come from the heap at boot.
- pio run -e front_node: SUCCESS, RAM 7.5 % (24452 bytes, +72), flash 10.0 % (335881 bytes, +212).
- Not flashed. The timing (acted on within about 20 ms) follows from the 10 ms poll and has not been measured on hardware.

### Bench test (rear unit, modem without network, Pi bridge running)

Setup: flash v0.7.8, check the banner "Firmware v0.7.8". Leave the modem attached without network (no SIM, or antenna off: AT+CSQ gives 99,99) so the monitor shows "[MQTT] Reconnecting..." attempts. On the Pi, watch the raw line rate on the bridge (or count lines starting with RAW per second on /dev/serial0).

1. During a reconnect attempt (just after "[MQTT] Reconnecting..." appears), send from the Pi: stty -F /dev/serial0 460800 raw, then python3 -c "import os; fd=os.open('/dev/serial0', os.O_WRONLY | os.O_NOCTTY); os.write(fd, b'!raw off\n')" (with the bridge running it already holds the port at 460800 baud; skip stty then). Pass: the raw line rate on the bridge drops to 0 within 1 s; DASH lines continue; the next DASH "cmd" has rx and now each +1.
2. Send "!raw on" the same way. Pass: the raw rate is back to normal (about 2 x 200 samples per second in batches) within 1 s; "cmd" rx and now +1.
3. Repeat 1 and 2 five times at random moments over a few minutes. Pass: every time within 1 s.
4. Queued command: send "!mqtt" from the Pi during a reconnect attempt. Pass: the monitor shows "'!mqtt' queued for the modem task" at once, then within about 3 s "[MQTT] Reconnect stopped to run a queued command" and "[CMD] MQTT reconnect requested"; DASH "cmd" queued and done +1 each.
5. USB console: type AT+CSQ in the monitor. Pass: the modem reply appears as before. Type !status: the reply appears at once, with the "commands:" line.
6. Front node: send !raw off and !raw on on its USB serial. Pass: the raw stream stops and resumes within 1 s; DASH "cmd" counts rx and now.

## v0.7.7, 22 Oct 2026 (built, host-tested, not flashed)

Bench finding of 22 Oct 2026 on v0.7.6: with an MPU6050's wires pulled and refitted while running, v0.7.6 counted the read failures (rdfail) and skipped slots (late) without stalling, but after the refit the sensor was back in its power-on sleep state and returned the same reading every time (stuck rising 200 per second, vib 0.0) until the board was reset. The firmware configured each sensor only once, at boot.

### Changes

- Automatic IMU recovery (ImuTask, imuReinit, imuTryReinit in src/main.cpp; decisions in the new include/imu_recovery.h). Every read is good, failed or stuck. After 1 s (200 slots) of bad reads ending in a failure, or 1 s of identical reads, the IMU task wakes the sensor and writes its boot settings again: PWR_MGMT_1 0x01 (awake, PLL clock), PWR_MGMT_2 0, sample rate divider 0, DLPF 94 Hz, +-500 deg/s, +-8 g, then reads them back. The calibration factor in NVS is not touched. Up to 8 short I2C transactions, no delays, and it stops at the first one that fails, so a try costs well under 1 ms (a missing sensor fails its address in tens of microseconds). The Adafruit begin() used at boot is not reused here: it resets the sensor and waits 200 ms.
- Back-off: if the re-init fails, the sensor is marked down: it is not read, and only a re-init is tried, every 1 s for 10 tries, then every 5 s (0.2 tries per second, about 25 us each, for a sensor that stays missing). A re-init that works but leaves the readings stuck is retried on the same schedule, so a broken sensor cannot make a tight loop (host test: 128 re-inits in 10 min). One good read clears the count. All thresholds are build flags: IMU_REINIT_FAIL_SLOTS, IMU_REINIT_STUCK_SLOTS (200 each), IMU_REINIT_FAST_SLOTS (200), IMU_REINIT_FAST_TRIES (10), IMU_REINIT_SLOW_SLOTS (1000).
- A sensor absent at boot starts down and is tried on the same schedule, so one plugged in later is picked up within 1 s (within 5 s after the first 10 s).
- I2C timeout 10 ms per transaction (IMU_I2C_TIMEOUT_MS; the core's default was 50 ms), so a hung bus holds the IMU task for at most 10 ms per try. Before every 3rd failed try in a row (IMU_BUS_RESET_EVERY, 0 = never), and only if a transaction on that bus timed out since the last good read, the I2C driver is restarted (Wire end and begin). A missing sensor that just does not answer (no acknowledge) does not trigger it. Safe because each bus is used only by its own IMU task after setup.
- Slot numbers now advance every 5 ms whether the sensor is read, down or being re-initialised, so time down shows as a seq gap of the same length. Raw stream: flag bit 2 (RAW_FLAG_REINIT) on the first sample after a re-init, and an extra RAWH for that IMU right after it. Same format version 2: older readers keep the flag byte as it is (BenchTest/analysis/readers.py and the bridge do not check the bit). RAWH has no new field, because tools/raw_stream_decode.py and BenchTest/analysis/readers.py both reject a RAWH whose field count is not 12.
- DASH line, two fields at the end: "reinit":[a,b] re-inits that worked per IMU since boot, "imu_up":[a,b] 1 read, 0 down (retrying), -1 not enabled in this build. Front node: one element each. DASH_LINE_MAX 704 to 768 and RAW_DASH_RESERVE 704 to 768 (53 bytes more in the worst case, 33 in practice). DashboardIntegration/TELEMETRY_LINK.md still gives an older maximum (the bridge accepts 4096).
- !status shows each IMU as up or DOWN with reinit, tries and bus restarts; the 2 s stats output has a new "IMU recovery" line. tools/raw_stream_decode.py counts re-init-flagged samples and prints reinit and imu_up from the last DASH line.
- Rear build: IMU2 off by default (ENABLE_IMU2 0 on both nodes), because the second sensor moved to the front node. -D ENABLE_IMU2=1 brings it back (built and checked). With it off, the IMU2 task and its ride task are not started; vib comes from IMU1 alone (fusion falls back to one sensor, vib_dis null, as it already did when IMU2 was missing).
- Array shapes with IMU2 off: the rear DASH keeps two-element arrays, the second element a plain 0: imu_hz [200.0,0.0], drops [n,0], rdfail [n,0], stuck [n,0], rawdrop [n,0], qmax [n,0], late [n,0], reinit [n,0]; cons_age_ms [stats,ride1,-1] (-1 = that consumer never ran); imu_up [1,-1]. Chosen over null and over one-element arrays after reading the readers: DashboardIntegration/ride_quality_card.py needs exactly two elements (shows "200 / 0 Hz"); CameraDetection/telemetry_bridge.py only parses the JSON; BenchTest/analysis/readers.py only checks that the keys are there; DashboardIntegration/tests/test_live_data_provider.py already has a [400.0, 0.0] case; and imu_hz [x, 0.0] is what v0.7.6 sent for an unconnected IMU2. null would make BenchTest/sw7_check.py report "imu_hz missing or invalid" instead of a low rate. sw7_check.py's "IMU rates" check fails either way on a one-IMU unit (it wants both at 200 Hz); it needs updating by its owner (outside TelemetryUnit/).
- Version string v0.7.7.

### Verification on the laptop

- test_host/run.py: all PASS. test_sync_ledger PASS (40 checks), test_raw_stream PASS (2326 checks, unchanged), test_imu_pacing PASS (254 checks), new test_imu_recovery PASS (1201 checks), raw_stream_decode.py selftest PASS.
- test_imu_recovery: single cases (read kinds, back-off schedule, thresholds set separately and switched off, a run mixing failed and stuck reads, slot wrap, bus restart cadence, the re-init flag through the raw encoder and decoder), then a slot-level model of the IMU task, the same calls in the same order as ImuTask, driving a simulated MPU6050 that comes back asleep (repeating one reading) after losing power. Results: healthy for 10 min, no re-init and nothing lost; power pulled 3 s, good again 200 slots (1.0 s) after the refit, reinit 1; power glitch 0.3 s, good again 1.0 s after the refit (the first reading after the refit differs from the last one before the pull, so the stuck run starts at the refit); SDA pulled 3 s, the same; SDA pulled 0.5 s, reads resume by themselves, no re-init; absent at boot and plugged in at 7 s, found at once (on a 1 s try); missing 10 min, 127 failed tries (0.21 per s), found within 5 s of plugging in; broken sensor that never updates, 128 re-inits in 10 min; three pulls in a row, one recovery each; across the 32-bit slot wrap; faster thresholds by flag.
- pio run (rear, IMU2 off): SUCCESS, RAM 16.2 % (53076 bytes), flash 16.1 % (1056389 bytes).
- pio run with -D ENABLE_IMU2=1 (rear, separate build folder): SUCCESS, RAM 53108 bytes, flash 1056589 bytes.
- pio run -e front_node: SUCCESS, RAM 7.4 % (24380 bytes), flash 10.0 % (335669 bytes).
- Not flashed. The register values are from the Adafruit library source (2.2.x) and the MPU-6050 register map; that a woken sensor returns to normal output with them has only been modelled, not seen on hardware.

### Bench test (either node, IMU1, Pi bridge or the serial monitor)

Setup: flash v0.7.7, check the banner "Firmware v0.7.7" and "IMU1 found and configured" (rear also "IMU2 disabled"). Stream as usual and log DASH every second (the v0.7.6 logging loop on the Pi, adding "reinit" and "imu_up" to the keys), or watch the 2 s "IMU health" and "IMU recovery" lines in the monitor.

1. Power wire: pull IMU1's VCC wire for about 3 s and refit it. Expect while out: rdfail rising for 1 s, then imu_up [0,...], rdfail stops rising (the sensor is not read while down), seq gap in the raw stream. Pass: within about 1.5 s of the refit stuck stops rising, imu_up back to 1, reinit +1, vib a number again (not 0.0, not null) within the next 2 s, drops [0,0], cons_age_ms under 200 throughout (ride2 -1 on the rear with IMU2 off), late not rising during the pull.
2. Short glitch: tap the VCC wire out and back in (under 0.5 s). Pass: the same as 1 (the sensor comes back asleep; stuck rises for about 1 s, then reinit +1).
3. SDA wire: pull SDA for about 3 s and refit. Pass: as 1. Pull it for under 1 s: reads resume by themselves, reinit unchanged.
4. Long absence: pull VCC for 30 s. Pass: !status shows "DOWN (retrying)" and tries rising about once per second for the first 10 s, then once per 5 s; idle[1] stays above 0 (core 1 not loaded); after the refit the sensor is back within 5 s, reinit +1.
5. Absent at boot: power up with IMU1 unplugged ("IMU1 not found"), plug it in after 10 s. Pass: imu_up goes to 1 within 5 s and vib appears. The calibration factor is the stored one (no calibration runs after boot; a sensor never calibrated keeps 1.0 until the next boot).
6. Raw stream: decode the capture with tools/raw_stream_decode.py. Pass: one re-init-flagged sample per recovery, a RAWH right after it, the seq gap matches the time the sensor was out or stuck plus up to 1 s.
7. Rear only, IMU2 off: DASH has imu_hz [200.0,0.0], drops [0,0], imu_up [1,-1]; the dashboard ride card shows "200 / 0 Hz". Optional: build with -D ENABLE_IMU2=1 and check both IMUs again.

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
