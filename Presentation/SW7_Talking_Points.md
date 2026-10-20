# SW7 final presentation: talking points

Generated from the speaker notes by Presentation/source/build_deck.js; edit the notes there, not here. The timed version with cuts is SW7_Speaker_Script.md.

14 slides, 10 minutes plus questions. 1275 words in total, about 9.1 minutes at 140 words a minute.

## Slide 1: Title (56 words)

Good morning. I'm Samson Okuthe, and my project is SW-7, supervised by Associate Professor Simon Winberg with Sampath Jayalath. It is part of TUKZIE, a 72 volt electric cargo trike for last-mile freight. I built its on-board electronics: a telemetry unit that measures how the trike rides, and safety alerts on the dashboard it already has.

## Slide 2: Why this matters (78 words)

Electric trikes make economic sense for freight in African cities: on delivery routes in Dar es Salaam, an electric cargo tricycle cut the operating cost per kilometre by 45.5 percent against a motorcycle. But anything that takes the driver's eyes off the road is a risk; NHTSA guidance limits a single glance to two seconds. So the problem is to combine edge telemetry with short, safety-only alerts on a low-cost trike, and to measure whether each part works.

## Slide 3: Aim and research questions (93 words)

Four research questions, and where each honestly stands. RQ1, how accurately and repeatably a low-cost unit characterises the ride: the instrument is verified, and on the first road session it held its rate, but repeatability is not measured yet. RQ2, alerts on the existing dashboard with the least distraction: this replaced the head-up display with my supervisor's agreement. It is built; glance time is not measured. RQ3, latency, loss and recovery: loss and recovery pass a ten-minute outage test; latency needs GNSS time. RQ4, road against powertrain vibration, needs the second road session.

## Slide 4: The system: front and rear, joined by one cable (104 words)

Since the fifteenth of October the system has two sides, joined by one Ethernet cable. At the front, a Raspberry Pi 5 behind the dashboard runs its own camera, the detector, a time-of-flight board and the fusion, so a front alert never crosses the network. At the rear, beside the battery, the Pi 4 runs the rear camera and sensors and carries the telemetry unit: an ESP32-S3 with LTE and GNSS, two IMUs at 200 hertz and the battery link. Two findings drove this: the battery's Bluetooth did not reach the front, and the Pi 5 runs the detector more than twice as fast.

## Slide 5: Firmware: deterministic acquisition first (83 words)

The firmware runs on FreeRTOS across two cores. Core 1 holds one task per IMU at the highest priority, on a fixed 5 millisecond period. They never block: each sample is time-stamped into a bounded queue, and if it is full the sample is dropped and counted. Core 0 does the modem, GNSS, MQTT and the flash log, in one task because the modem's serial line has no lock. Version 0.7.4 adds sequence numbers, backlog replay and a 94 hertz filter against aliasing.

## Slide 6: Result: 200 Hz acquisition and dual-IMU fusion (89 words)

Both IMUs run at 200 hertz with no dropped samples, counted, not assumed. Flash writes cause one gap of under 45 milliseconds a minute, and the queue holds the samples through it. A gravity factor per sensor brings both to 9.80 or 9.81, but only in that orientation, so it is redone once mounted. Fusion is an equal-weight mean; windows pair only if they end within half a window, and the disagreement is reported. In a 150 second session all 149 windows fused with under a millisecond of skew.

## Slide 7: Seven fault investigations: symptom, test, cause, fix (109 words)

Because each stage was tested before the next, every fault could be traced to one change. Seven needed a real diagnosis; here is the one that mattered most. The Pi 4 kept throttling and rebooting. A logger recorded its power flags every two seconds: clear with nothing attached, then under-voltage fourteen seconds after the telemetry unit's modem came up on its USB port. Moved off, no restarts in four hours. It came back in the closed box: 76.9 degrees and a brown-out restart. So the unit needs its own supply, and the lids gained vents. The Pi 5's restarts while mounting were different: abrupt power loss, not a brown-out.

## Slide 8: Result: timing, position, and no data lost in an outage (91 words)

The sync wire gives a median interval of 500.06 milliseconds over 121 edges, with under 0.7 of spread, so camera and IMU clocks line up. On a rooftop, GNSS was a median 2.7 metres from a phone. The outage test: I switched the radio off for ten minutes. The unit reconnected 5.2 seconds after it came back and cleared 60 records in about 40 seconds; the database holds 112 of 112. The public test broker does not queue, so the log read-back is the safety net, and latency needs GNSS time.

## Slide 9: Hazard detection: twice as fast at the front (98 words)

The detector is a pretrained 8-bit SSD-MobileNet. On the Pi 4 with the whole system running it takes 118 to 122 milliseconds from sensor readout to result, at 14.6 frames per second. On the Pi 5 beside the dashboard it is 51 to 54 milliseconds at 19.2 frames per second, with no throttling. At 30 kilometres an hour that is about 0.6 metres less travel before an alert. An alert needs three frames to raise and five to clear, and no frame is ever stored. My pothole model works on a test image but is off by default.

## Slide 10: Approaching objects: time to contact from box growth (102 words)

Distance bands say how near an object is, not whether it is coming closer. For an object closing at constant speed, the inverse of its box width falls in a straight line to zero at contact. So time to contact is the width over its rate of growth, after Lee in 1976, and it needs no focal length or object size. I fit that line robustly over the last 0.6 seconds, and warn below 4 seconds, immediate below 2. In 40 synthetic tests it is within 2 percent, at 0.27 milliseconds a frame. It has not been tested on a real approach.

## Slide 11: Both cameras on the existing dashboard (89 words)

This is where RQ2 lands, on the dashboard the team already runs. The Surroundings page now has a Front and Rear switch, which moves the picture, alerts, distances and hazards together, each from that side's own unit. The rear view is mirrored like a reversing camera. The banner shows warnings from both sides, names the side, and puts an approaching object first. It shows only live data, never a simulated value. It is tested offscreen and live on the Pi 5; glance time on the vehicle is still open.

## Slide 12: On the vehicle: enclosures, heat and power (88 words)

The enclosures were modelled from scripts in SOLIDWORKS, each checked for interference, fasteners and thin walls: a display mount, a front pod for the Pi 5 and its AI HAT, and a screwless IMU pod. After the Pi 4 reached 76.9 degrees in its closed box, both lids gained an exhaust grille under a rain hood. The power budget is about 20 watts, 0.27 amps from the 72 volt pack, under one percent of the motor's rated input. Only the Pi 5 is measured; the rest are estimates.

## Slide 13: First road session, 19 October (114 words)

On the nineteenth of October the whole system was mounted and the first road session run. A recorder on the Pi 5 captured all four sources for 108.6 minutes, about 19.5 of them driving, with no laptop on board. Both IMUs held 200 hertz with no drops, so R1 is met on the vehicle. The battery link held under load: up to 46.9 amps, the pack falling from 74.6 to 72.8 volts. The cameras raised 1,342 front and 741 rear alerts, not yet checked against video. But GNSS had no fix, and there were no raw samples or run markers, so RQ1 and RQ4 are not answered yet. A second, shorter session is planned.

## Slide 14: Conclusions and next steps (81 words)

To conclude. Every subsystem runs together, now on the vehicle: two IMUs at 200 hertz, fused; a database that lost nothing across an outage; detection in about 50 milliseconds at the front; an approaching-object warning; and both cameras on the existing dashboard. What remains is the second road session with raw data and GNSS for RQ1 and RQ4, the real approach test, glance time for RQ2, and a separate supply for the telemetry unit. Thank you, I'm happy to take questions.
