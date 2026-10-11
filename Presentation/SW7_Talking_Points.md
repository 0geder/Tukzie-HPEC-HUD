# SW7 final presentation: talking points

Generated from the speaker notes by Presentation/source/build_deck.js; edit the notes there, not here.

12 slides, 10 minutes plus questions. 1376 words in total, about 9.2 minutes at 150 words a minute.

## Slide 1: Title (76 words)

Good morning. I'm Samson Okuthe, and my project is SW-7, supervised by Associate Professor Simon Winberg with Sampath Jayalath as co-supervisor. It is part of TUKZIE, a 72 volt electric cargo trike for last-mile freight. I built its on-board electronics: a telemetry unit that measures how the trike rides, and a way of showing the driver only what matters for safety. I'll cover why, how I built and tested it, the results, and what is left.

## Slide 2: Why this matters (96 words)

Two facts frame the project. First, electric trikes make economic sense for freight in African cities: on routes studied in Dar es Salaam in 2025, an electric cargo tricycle cut operating cost per kilometre by 45.5 percent against a motorcycle and up to 86 percent against a light car. Second, anything that takes the driver's eyes off the road is a risk: NHTSA guidance limits a single glance to two seconds. The open problem is combining edge telemetry with that kind of sparse, safety-only driver information on a low-cost trike, and measuring whether each part works.

## Slide 3: Aim and research questions (104 words)

The aim is a low-cost unit that characterises the ride at the edge and shows the driver only safety-relevant information. There are four research questions, marked honestly. RQ1, two IMUs at 200 hertz agreeing within noise, is verified on the bench. RQ3, bounded latency, measured loss and recovery, is verified on the bench but still needs the moving vehicle. RQ4, separating road from powertrain vibration, passes its self-tests but needs road data. RQ2 changed with my supervisor's agreement: the trike already has a dashboard showing what a HUD would show, and a second display adds distraction, so the alerts now go on that dashboard.

## Slide 4: The system on the bench (109 words)

This is the whole system on the bench. The telemetry unit is an ESP32-S3 with a built-in LTE modem that also gives GNSS. It samples two MPU6050 IMUs at 200 hertz each, reads the battery management system over Bluetooth, and has a hardware counter ready for the motor's Hall sensor. A Raspberry Pi 4 runs the camera detector and three time-of-flight distance sensors facing left, ahead and right, apart from the team's Pi 5 so their dashboard is not disturbed. One wire links the boards: the ESP32 pulses it every half second and the Pi logs each edge, so camera and IMU data can be lined up in time.

## Slide 5: Firmware: deterministic acquisition first (104 words)

The firmware runs on FreeRTOS across the two cores. Core 1 holds the timing-critical work: one task per IMU at the highest priority, each on a fixed 5 millisecond period, so the rate cannot drift. These tasks never print or block. Each sample is time-stamped in microseconds and pushed into a bounded queue; if it is full the sample is dropped and counted, so a slow consumer can never stall acquisition. Core 0 does the blocking work: the modem, GNSS, MQTT and the flash log in one task, because the modem's serial line has no lock, plus the battery link and the Hall counter.

## Slide 6: Approach: prove each stage before building on it (76 words)

My method was staged verification. Each interface was brought up alone on the real board, against a pass criterion written before the test. Then both IMUs at 200 hertz, calibrated; then the ride features and fusion, each self-tested at boot; then the log and the LTE publish. The last stage, the moving vehicle, is drawn dashed: the first road test is planned for 14 October. This order is why the faults I'll show could be traced.

## Slide 7: Result: 200 Hz acquisition and dual-IMU fusion (131 words)

First results. Both IMUs run at 200 hertz with zero dropped samples, which the drop counters prove rather than assume. Two identical accelerometers disagreed by about 8 percent at rest; a per-sensor calibration against gravity brought that down to noise. With equal noise, inverse-variance fusion reduces to the mean. Windows are paired only if they end within half a window, the disagreement is reported, and if one sensor is silent for three seconds the other takes over. In this 150 second session all 149 windows were fused with under a millisecond of skew. A review also caught that my speed-normalised index used the mean square, which gravity dominates; version 0.7.2 uses the variance. The calibration only holds in the orientation it was taken in, so it will be redone once mounted.

## Slide 8: What testing found, and how it was fixed (154 words)

Testing each stage against a stated pass criterion found faults that assumptions had hidden. The GNSS reply had a different layout from the one assumed, so the first fix put the trike in the sea; the parser now anchors on the hemisphere letter. The battery checksum included one byte too many, so every real frame failed by exactly three. Flash writes stalled both IMUs; switching the log off proved it, and the log is now written six times less often. The pink image came from a camera with no infrared filter. Two are new. The Pi 4 kept browning out and rebooting because the ESP32's LTE modem drew its transmit current through the Pi's USB port; the ESP32 now needs its own powered hub, and a fan brought the Pi down from 81 degrees. And the distance-sensor reader froze when one sensor stopped answering; a half-second timeout now skips it, and all three read.

## Slide 9: Result: timing, position and the cellular link (120 words)

Three more bench results. Timing: the Pi takes each sync edge's time from the kernel, and over 121 edges the median interval was 500.06 milliseconds with a spread under 0.7, so the camera and IMU clocks can be related precisely. Position: on a rooftop, 104 fixes were a median of 2.7 metres from a phone's position. Version 0.7.3 does what a phone does: assisted GNSS loads satellite data over LTE, and indoors the modem gives a network position in 0.7 seconds, stated to 550 metres, and here about 30 metres from the outdoor fix. Cellular: 47 of 47 publishes were acknowledged, and after a 60 second radio cut the link recovered by itself about 5 seconds after the signal returned.

## Slide 10: Camera hazard detection and distance sensing (146 words)

The camera's role grew, on supervisor direction, from a visual record to hazard awareness. I designed and 3D printed this casing. The live detector is a pretrained 8-bit SSD-MobileNet sized for the Pi 4: 19.5 frames per second and 102 milliseconds median from sensor to result in the benchmark, and 14.6 frames per second, about 120 milliseconds, in the latest check on a healthy Pi 4. An alert needs three frames to raise and five empty frames to clear, which stopped one person causing 16 alerts in 47 seconds; no frame is stored. COCO has no potholes, so I trained my own model: zero on South African dashcam footage at first, 0.71 mAP at 50 on validation tiles after training on the road band. Running it on the Pi is in progress. Three time-of-flight sensors cover close range until the 8 by 8 zone sensor arrives.

## Slide 11: Hazard alerts and navigation on the existing dashboard (148 words)

This is where RQ2 lands: my pages on the dashboard the team already runs, now the default at boot on their Pi 5, with their own build untouched. The Pi 4 sends ESP32, distance and camera data twice a second, and the dashboard shows only real values, with dashes where data is missing. On the left, the Sensors page shows the distance gauges and fused hazards, and a red banner covers any page for an immediate hazard. On the right is navigation: a Google-style turn banner with spoken directions. For indoor demonstrations a simulated drive moves every page in step under a yellow SIMULATED strip, and a status chip always reads LIVE, REPLAY, NO DATA or SIMULATED, so simulated numbers are never taken for real ones. Pages change with a two-finger swipe, three on the map. Still open: glance time on the vehicle, against the NHTSA two-second rule.

## Slide 12: Conclusions and next steps (112 words)

To conclude. Every subsystem runs together on the target hardware: two IMUs at 200 hertz with no loss, calibrated and fused; GNSS within about 3 metres, with a network position indoors; the battery over Bluetooth; a cellular link that recovers by itself; a full local log; camera alerts in about a tenth of a second; and hazards, navigation and spoken directions on the existing dashboard. Each fault was found by a test, fixed and tested again. In progress: a central database with backlog replay, and the pothole model on the Pi. Next is the vehicle: the road test on 14 October, then the fusion calibration. Thank you, I'm happy to take questions.
