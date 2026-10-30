# SW7 final presentation: talking points

Generated from the speaker notes by Presentation/source/build_deck.js; edit the notes there, not here. The timed version with cuts is SW7_Speaker_Script.md.

14 slides, 10 minutes plus questions. 1449 words in total, about 10.4 minutes at 140 words a minute.

## Slide 1: Title (56 words)

Good morning. I'm Samson Okuthe, and my project is SW-7, supervised by Associate Professor Simon Winberg with Sampath Jayalath. It is part of TUKZIE, a 72 volt electric cargo trike for last-mile freight. I built its on-board electronics: a telemetry unit that measures how the trike rides, and safety alerts on the dashboard it already has.

## Slide 2: Why this matters (78 words)

Electric trikes make economic sense for freight in African cities: on delivery routes in Dar es Salaam, an electric cargo tricycle cut the operating cost per kilometre by 45.5 percent against a motorcycle. But anything that takes the driver's eyes off the road is a risk; NHTSA guidance limits a single glance to two seconds. So the problem is to combine edge telemetry with short, safety-only alerts on a low-cost trike, and to measure whether each part works.

## Slide 3: Aim and research questions (96 words)

Four research questions, and where each honestly stands. RQ1, how accurately and repeatably a low-cost unit characterises the ride: verified on the bench; road repeatability waits for Monday's run. RQ2, alerts on the existing dashboard with the least distraction: this replaced the head-up display with my supervisor's agreement. It is built and its legibility measured; glance time needs a participant. RQ3, latency, loss and recovery: loss and recovery pass a ten-minute outage test; latency needs GNSS time. RQ4, road against powertrain vibration: the stands found the powertrain's lines; their road share waits for the road run.

## Slide 4: The system: front and rear, joined by one cable (120 words)

Since the fifteenth of October the system has two sides, joined by one Ethernet cable. At the front, a Raspberry Pi 5 behind the dashboard runs its own camera, the detector, a time-of-flight board and the fusion, so a front alert never crosses the network. At the rear, beside the battery, the Pi 4 runs the rear camera and sensors and carries the telemetry unit: an ESP32-S3 with LTE, GNSS, the battery link and one IMU at 200 hertz. A second node with its own IMU now sits at the front, so both ends are measured. Two findings drove this: the battery's Bluetooth did not reach the front, and the Pi 5 runs the detector more than twice as fast.

## Slide 5: Firmware: deterministic acquisition first (83 words)

The firmware runs on FreeRTOS across two cores. Core 1 holds one task per IMU at the highest priority, on a fixed 5 millisecond period. They never block: each sample is time-stamped into a bounded queue, and if it is full the sample is dropped and counted. Core 0 does the modem, GNSS, MQTT and the flash log, in one task because the modem's serial line has no lock. Version 0.7.4 adds sequence numbers, backlog replay and a 94 hertz filter against aliasing.

## Slide 6: Result: 200 Hz acquisition and dual-IMU fusion (124 words)

Both IMUs run at 200 hertz with no dropped samples, counted, not assumed. Flash writes cause one gap of under 45 milliseconds a minute, and the queue holds the samples through it. A gravity factor per sensor brings both to 9.80 or 9.81, but only in that orientation: with bench factors the parked vehicle read 10.04 and 10.34, so both were recalibrated mounted, not yet rechecked. In a 150 second session all 149 windows fused with under a millisecond of skew. One limit: the 94 hertz filter only partly suppresses aliasing, so a line at 40 to 70 hertz could be an image of one at 136 to 157. A speed sweep tells them apart: a motor line rises with speed, its image falls.

## Slide 7: Seven fault investigations: symptom, test, cause, fix (109 words)

Because each stage was tested before the next, every fault could be traced to one change. Seven needed a real diagnosis; here is the one that mattered most. The Pi 4 kept throttling and rebooting. A logger recorded its power flags every two seconds: clear with nothing attached, then under-voltage fourteen seconds after the telemetry unit's modem came up on its USB port. Moved off, no restarts in four hours. It came back in the closed box: 76.9 degrees and a brown-out restart. So the unit needs its own supply, and the lids gained vents. The Pi 5's restarts while mounting were different: abrupt power loss, not a brown-out.

## Slide 8: Result: timing, position, and no data lost in an outage (113 words)

The sync wire gives a median interval of 500.06 milliseconds over 121 edges, with under 0.7 of spread, so camera and IMU clocks line up. On a rooftop, GNSS was a median 2.7 metres from a phone. On the vehicle it has not fixed yet, so a phone now streams its GNSS over its hotspot as the speed reference. The outage test: I switched the radio off for ten minutes. The unit reconnected 5.2 seconds after it came back and cleared 60 records in about 40 seconds; the database holds 112 of 112. The public test broker does not queue, so the log read-back is the safety net, and latency needs GNSS time.

## Slide 9: Hazard detection: twice as fast at the front (98 words)

The detector is a pretrained 8-bit SSD-MobileNet. On the Pi 4 with the whole system running it takes 118 to 122 milliseconds from sensor readout to result, at 14.6 frames per second. On the Pi 5 beside the dashboard it is 51 to 54 milliseconds at 19.2 frames per second, with no throttling. At 30 kilometres an hour that is about 0.6 metres less travel before an alert. An alert needs three frames to raise and five to clear, and no frame is ever stored. My pothole model works on a test image but is off by default.

## Slide 10: Approaching objects: time to contact from box growth (119 words)

Distance bands say how near an object is, not whether it is coming closer. For an object closing at constant speed, the inverse of its box width falls in a straight line to zero at contact. So time to contact is the width over its rate of growth, after Lee in 1976, and it needs no focal length or object size. I fit that line robustly over the last 0.6 seconds, and warn below 4 seconds, immediate below 2. A one percent jitter in box width gives about plus or minus 0.3 seconds at 4 seconds. In 40 synthetic tests it is within 2 percent, at 0.27 milliseconds a frame. It has not been tested on a real approach.

## Slide 11: The existing dashboard: both cameras, and legibility (107 words)

This is where RQ2 lands, on the dashboard the team already runs. A Front and Rear switch moves the picture, alerts and distances together, the rear mirrored; the banner names the side and puts an approaching object first; only live data is shown. Glance time needs a participant, but legibility does not, so I measured it. At 0.70 metres the speed digits subtend 84 arc minutes, far above the 20 ISO 15008 recommends; the alert banner subtends 9, and the labels a median of 9, against 16 acceptable. So the speed is legible at a glance; the warnings are not. Enlarging them comes before any glance study.

## Slide 12: On the vehicle: enclosures, heat and power (88 words)

The enclosures were modelled from scripts in SOLIDWORKS, each checked for interference, fasteners and thin walls: a display mount, a front pod for the Pi 5 and its AI HAT, and a screwless IMU pod. After the Pi 4 reached 76.9 degrees in its closed box, both lids gained an exhaust grille under a rain hood. The power budget is about 20 watts, 0.27 amps from the 72 volt pack, under one percent of the motor's rated input. Only the Pi 5 is measured; the rest are estimates.

## Slide 13: On the vehicle: road session and stand runs (156 words)

On the nineteenth of October the whole system was mounted and the first road session run. A recorder on the Pi 5 ran for 108.6 minutes, about 16 of them driving, with no laptop on board. One IMU stall of about 2 seconds, not in the drop count, means R1 is not met on the vehicle, and 38 percent of the records were lost on USB, now replaced by wires. The battery link held at up to 46.9 amps. With no GNSS antenna and no raw samples, RQ1 and RQ4 stayed open. On the twenty-third, with the drive wheel raised, the rear vibration rose five to seven times, between about 40 and 70 hertz, and the front showed the same lines, so the powertrain reaches the front through the frame. Throttle settings were not recorded, so the lines are not yet assigned to motor orders. Monday's road run answers RQ1 and RQ4; the analysis is ready.

## Slide 14: Conclusions and next steps (102 words)

To conclude. Every subsystem runs together, now on the vehicle: two nodes at 200 hertz with no counted drops; a database that lost nothing across an outage; detection in about 50 milliseconds at the front; an approaching-object warning; and both cameras on the existing dashboard. On the stands the powertrain showed at 40 to 70 hertz, at both ends; the dashboard's warnings are too small. What remains is Monday's road run for RQ1 and RQ4, larger warnings and then glance time for RQ2, the real approach test, and a separate supply for the telemetry unit. Thank you, I'm happy to take questions.
