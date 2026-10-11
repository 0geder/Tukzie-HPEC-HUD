# SW7 final presentation: talking points

Generated from the speaker notes by Presentation/source/build_deck.js; edit the notes there, not here. The timed version with cuts is SW7_Speaker_Script.md.

12 slides, 10 minutes plus questions. 1349 words in total, about 9.6 minutes at 140 words a minute.

## Slide 1: Title (67 words)

Good morning. I'm Samson Okuthe, and my project is SW-7, supervised by Associate Professor Simon Winberg with Sampath Jayalath as co-supervisor. It is part of TUKZIE, a 72 volt electric cargo trike for last-mile freight. I built its on-board electronics: a telemetry unit that measures how the trike rides and sends the data to a central database, and safety alerts on the dashboard the trike already has.

## Slide 2: Why this matters (92 words)

First, electric trikes make economic sense for freight in African cities. On delivery routes studied in Dar es Salaam, an electric cargo tricycle cut the operating cost per kilometre by 45.5 percent against a motorcycle, and by up to 86 percent against a light car. Second, anything that takes the driver's eyes off the road is a risk. NHTSA guidance limits a single glance to two seconds. So the open problem is to combine edge telemetry with short, safety-only driver information on a low-cost trike, and to measure whether each part works.

## Slide 3: Aim and research questions (120 words)

These are my four research questions, and where each one honestly stands. RQ1 asks how accurately and repeatably a low-cost unit can characterise the trike's ride. The instrument is verified on the bench; repeatability on the vehicle is not measured yet. RQ2 asks how to show safety alerts on the existing dashboard with the least distraction. It moved from a head-up display to that dashboard with my supervisor's agreement, because a second screen adds distraction. Glance time is not measured yet. RQ3 asks about latency, data loss and recovery. Loss and recovery now pass a ten-minute outage test; end-to-end latency still needs GNSS time outdoors. RQ4, separating road from powertrain vibration, has passed self-tests only, because it needs road data.

## Slide 4: The system on the bench (107 words)

This is the system on the bench. The telemetry unit is an ESP32-S3 with a built-in LTE modem that also gives GNSS. It samples two MPU6050 IMUs at 200 hertz each, reads the battery over Bluetooth, and has a hardware counter for the motor's Hall sensor. Every record goes to a local log and over LTE to a central database on the team's Pi 5. A Raspberry Pi 4 runs the camera detector and three time-of-flight distance sensors. One wire links the boards: the ESP32 pulses it every half second and the Pi logs each edge, so camera and IMU data can be lined up in time.

## Slide 5: Firmware: deterministic acquisition first (114 words)

The firmware runs on FreeRTOS across the two cores. Core 1 holds the timing-critical work: one task per IMU at the highest priority, each on a fixed 5 millisecond period. They never print or block: each sample is time-stamped and pushed into a bounded queue, and if it is full the sample is dropped and counted. Core 0 does the blocking work: the modem, GNSS, MQTT and the flash log, in one task because the modem's serial line has no lock. Version 0.7.4, flashed in October, gives every record a sequence number, replays the backlog after an outage, and moves the IMU filter from 260 to 94 hertz, against aliasing at 200 hertz sampling.

## Slide 6: Approach: prove each stage before building on it (77 words)

My method was staged verification. Each interface was brought up alone on the real board, against a pass criterion written before the test. Then both IMUs at 200 hertz, calibrated; then the ride features and fusion, each self-tested at boot; then the log, the LTE publish and the replay to the database. The last stage, the moving vehicle, is drawn dashed. This order is why the faults I'll show next could each be traced to one change.

## Slide 7: Result: 200 Hz acquisition and dual-IMU fusion (128 words)

First results. Both IMUs run at 200 hertz with no dropped samples, counted, not assumed. Flash writes cause gaps of 33 to 40 milliseconds, now once a minute, and the queue holds the samples through each one. Uncalibrated, the two accelerometers read about 8 percent apart in an earlier session. A factor per sensor against gravity brings both to 9.80 or 9.81 at calibration, but it only holds in that orientation, so it will be redone once mounted. With equal noise, inverse-variance fusion reduces to the mean. Windows are paired only if they end within half a window, the disagreement is reported, and if one sensor goes silent the other takes over. In a 150 second session all 149 windows were fused with under a millisecond of skew.

## Slide 8: Seven fault investigations: symptom, test, cause, fix (141 words)

The report works through seven faults that needed a real diagnosis: symptom, candidate causes, deciding test, and fix. Here is one in full. The Raspberry Pi 4 kept throttling and rebooting. It could have been its own supply, the distance-sensor board, the telemetry unit on its USB port, or heat. A logger recorded the power flags every two seconds. With nothing attached, the flags were clear. Fourteen seconds after the telemetry unit was plugged in, when its modem came up, under-voltage began. With the unit on the Pi, there were three restarts in twenty minutes; moved off the Pi, none in four hours. The others follow the same pattern, from a GNSS reply in an unexpected layout to a battery checksum off by exactly three. The outage test found an eighth: a broker setting that silently stopped delivery to the database.

## Slide 9: Result: timing, position, and no data lost in an outage (141 words)

Timing first: over 121 sync edges the median interval was 500.06 milliseconds with a spread under 0.7, so camera and IMU clocks line up precisely. Position: on a rooftop, 104 fixes were a median of 2.7 metres from a phone, and indoors the modem gives a network position stated to 550 metres. The main new result is the outage test. With version 0.7.4 I switched the radio off for ten minutes. The unit built up 60 records, reconnected 5.2 seconds after the radio came back, and cleared the backlog in about 40 seconds. The database on the Pi 5 holds 112 of 112 records, and 111 of 111 against the unit's own log, so nothing was lost. Two limits: the public test broker does not queue, so reading the log back is the safety net, and latency needs GNSS time outdoors.

## Slide 10: Camera hazard detection and distance sensing (139 words)

The camera's role grew, on supervisor direction, from a visual record to hazard awareness. I designed and 3D printed this casing. The live detector is a pretrained 8-bit SSD-MobileNet. On its own it ran at 19.5 frames per second, 102 milliseconds from sensor to result. With everything else running on a healthy Pi 4 it is 14.6 frames per second and about 120 milliseconds, and that is the figure for the system. An alert needs three frames to raise and five empty frames to clear, and no frame is stored. COCO has no potholes, so I trained my own model: 0.71 mAP at 50 on validation tiles. On the Pi it finds the pothole in a test image at confidence 0.63, but only one run every four seconds fits beside the main detector, so it is off by default.

## Slide 11: Hazard alerts and navigation on the existing dashboard (131 words)

This is where RQ2 lands: my pages on the dashboard the team already runs, the default at boot on their Pi 5. It shows only real values, with a chip that always reads LIVE, REPLAY, NO DATA or SIMULATED. On the left, the Sensors page shows the distance gauges and fused hazards. An immediate hazard now shows as a red pill in the status bar, so it no longer covers the page. In the middle is navigation with spoken directions, in a simulated drive that is clearly marked. On the right is the new destination search: offline matches in under 20 milliseconds, and online suggestions in just over a second on the Pi. Pages change with a two-finger swipe. These are tested offscreen; glance time on the vehicle is still open.

## Slide 12: Conclusions and next steps (92 words)

To conclude. Every subsystem runs together on the target hardware: two IMUs at 200 hertz, calibrated and fused; GNSS within about 3 metres; the battery over Bluetooth; a full local log; and now a central database that lost nothing across a ten-minute outage. Camera detection takes about 120 milliseconds in the full system, and hazards, navigation and search run on the existing dashboard. What remains is the vehicle: end-to-end latency with GNSS time, repeatability for RQ1, road data for RQ4, and glance time for RQ2. Thank you, I'm happy to take questions.
