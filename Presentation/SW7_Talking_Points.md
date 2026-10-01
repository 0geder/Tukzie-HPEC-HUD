# SW7 final presentation: talking points

Generated from the speaker notes by Presentation/source/build_deck.js; edit the notes there, not here.

12 slides, 10 minutes plus questions. 1488 words in total, about 9.9 minutes at 150 words a minute.

## Slide 1: Title (92 words)

Good morning. I'm Samson Okuthe, and my project is SW-7, supervised by Associate Professor Simon Winberg with Sampath Jayalath as co-supervisor. It is part of the TUKZIE programme, which is building a 72 volt electric cargo trike for last-mile freight. My part is the on-board electronics: a telemetry unit that measures how the trike rides, and a way of showing the driver only what matters for safety. In the next ten minutes I'll cover why this is needed, how I built and tested it, what the results show, and what is left.

## Slide 2: Why this matters (111 words)

Two facts frame the project. First, electric trikes can make economic sense for freight in African cities: on the routes a 2025 study examined in Dar es Salaam, an electric cargo tricycle cut operating cost per kilometre by 45.5 percent against a motorcycle and up to 86 percent against a light car. Second, anything that pulls the driver's eyes off the road is a risk. NHTSA guidance says a single glance away should not exceed two seconds, so the driver should see only short, safety-relevant alerts. The open problem is bringing edge telemetry and that kind of sparse driver information together on a low-cost trike, and measuring whether each part works.

## Slide 3: Aim and research questions (136 words)

The aim is a low-cost unit that characterises the trike's ride at the edge and gives the driver only safety-relevant information. I split that into four research questions, and I've marked honestly where each one stands. RQ1, two IMUs at 200 hertz agreeing within noise, is verified on the bench. RQ3, bounded latency, measured data loss and recovery, is also verified on the bench: no dropped samples, a measured camera latency, and automatic recovery after the signal is cut. It still needs the moving vehicle. RQ4, separating road from powertrain vibration, passes its self-tests but needs road data. RQ2 changed during the project, with my supervisor's agreement. The trike already has a dashboard that shows what a HUD would show, and a second display adds distraction, so the camera's alerts now go on that dashboard instead.

## Slide 4: The system on the bench (131 words)

This is the whole system on the bench. The telemetry unit is an ESP32-S3 on a Makerfabs board with a built-in A7670X LTE modem, which also gives GNSS. Two MPU6050 IMUs are sampled at 200 hertz each, the battery management system is read over Bluetooth Low Energy, and a hardware counter is ready for the motor's Hall sensor. On the camera side, a Raspberry Pi 4 runs the object detector, and three time-of-flight distance sensors facing left, ahead and right. The two boards share one wire: the ESP32 sends a pulse every half second that the Pi logs, so camera and IMU data can be lined up in time. I use the Pi 4 rather than the team's Pi 5, so the dashboard running on the Pi 5 is not disturbed.

## Slide 5: Firmware: deterministic acquisition first (118 words)

The firmware runs on FreeRTOS and is split across the two cores. Core 1 holds everything timing-critical: one task per IMU at the highest priority, each holding a 5 millisecond period with vTaskDelayUntil so the rate cannot drift. The acquisition tasks never print or block. They time-stamp each sample with a microsecond clock and push it into a bounded queue; if a queue is full the sample is dropped and counted, so a slow consumer can never stall acquisition. Core 0 handles the slow, blocking work: the modem, GNSS, MQTT and the flash log in one task, because the modem's serial line has no lock, plus the battery link and the Hall counter, which counts pulses in hardware.

## Slide 6: Approach: prove each stage before building on it (106 words)

My method was staged verification. Each interface was brought up on its own on the real board, with a pass criterion written down before the test, before anything was built on top of it. Then both IMUs at 200 hertz, calibrated against gravity. Then the ride features and the fusion, each with a self-test at boot. Then the local log and the LTE publish. The last stage, validation on the moving vehicle, is still to come, and it's drawn dashed for that reason. This order paid off: most of the faults I'll show shortly would have been very hard to trace if I'd integrated everything first.

## Slide 7: Result: 200 Hz acquisition and dual-IMU fusion (143 words)

First results. Both IMUs run at 200 hertz with zero dropped samples, and the drop counters prove that rather than assuming it. Two identical accelerometers disagreed by about 8 percent at rest; a per-sensor calibration against gravity brought that down to noise. The two are then fused. With equal noise on both, inverse-variance weighting reduces to the mean. Windows are paired only if they end within half a window of each other, a disagreement figure is reported rather than hidden, and if one sensor goes silent for three seconds the output falls back to the other. In this recorded 150 second session all 149 windows were fused from both sensors with under a millisecond of skew. One honest finding: the calibration only holds in the orientation it was taken in, so it will be redone once the sensors are mounted on the trike.

## Slide 8: What testing found, and how it was fixed (137 words)

Testing each stage on real hardware against a stated pass criterion found six faults that assumptions had hidden. The GNSS reply had a different layout from the one assumed, so the first outdoor fix put the trike in the sea; the parser now anchors on the hemisphere letter. The modem was switching itself off after every reprogramming, because its power key toggles. The battery checksum included one byte too many, so every real frame failed by exactly three. Flash writes stalled both IMUs; I proved it by switching the log off, and the log is now buffered and written six times less often. Reading the log back showed most records were invalid JSON. And the pink camera image came from a module with no infrared filter, which I showed by comparing tuning files on the same scene.

## Slide 9: Result: timing, position and the cellular link (127 words)

Three more bench results. Timing: the Pi now takes each sync edge's time from the kernel, and over 121 edges the median interval was 500.06 milliseconds with a spread under 0.7 milliseconds, so the camera and IMU clocks can be related precisely. A loose jumper twice produced false edges, so the vehicle needs a latched connector. Position: on a rooftop, 104 fixes were a median of 2.7 metres from a phone's position, and 95 percent within 11 metres. Cellular: 47 of 47 publishes were acknowledged. When I cut the radio for 60 seconds, the firmware detected the loss in under a second and reconnected about 5 seconds after the signal came back. Every record is also logged to flash, and all 6,020 stored records were read back.

## Slide 10: Camera hazard detection and distance sensing (138 words)

The camera's role grew, on supervisor direction, from a visual record to hazard awareness. I designed and 3D printed the three-part casing on the left, with a 30 degree corner mount. The detector is a pretrained 8-bit SSD-MobileNet sized for the Pi 4, with no training of my own. Using all four cores it runs at 19.5 frames per second, with a median of 102 milliseconds from the sensor to a result. With the three-frame debounce an alert comes about 0.2 seconds after an object appears, about 1.7 metres at 30 kilometres per hour. An alert clears only after five empty frames, which stopped one person producing 16 alerts in 47 seconds. Only five fields are logged and no frame is stored. For close range, three time-of-flight sensors stand in until the 8 by 8 zone sensor arrives.

## Slide 11: Hazard alerts on the existing dashboard (126 words)

This is where RQ2 now lands. Instead of a separate windshield display, I wrote a camera page for the dashboard the TUKZIE team already runs. Three reasons: that dashboard already carries what a HUD would show, two displays compete for the driver's attention, and the programme's move towards autonomy makes the camera's alerts more useful than a second screen. The page shows the live view and the active alerts in the dashboard's own status colours. Tested against the live camera, it showed video 0.6 seconds after opening, listed this person alert half a second after opening, and switched to an offline state within a second of the camera stopping. The glance-time question is still open, and so is running it on the dashboard's own Pi 5.

## Slide 12: Conclusions and next steps (123 words)

To conclude. Every subsystem runs together on the target board: two IMUs at 200 hertz with no loss, calibrated and fused; GNSS within about 3 metres; the battery read over Bluetooth; a cellular link that recovers by itself; a full local log; and camera alerts in about a tenth of a second, shown on the existing dashboard. Each fault was found by a test with a stated pass criterion, then fixed and tested again. What's left is the vehicle: mount and recalibrate the unit in place, then the field test that answers the ride and latency questions on the move, calibrate the camera's distance bands, and fit the zoned distance and air-quality sensors when they arrive. Thank you, I'm happy to take questions.
