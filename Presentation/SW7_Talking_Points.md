# SW7 final presentation: talking points

12 slides, 10 minutes plus 5 minutes of questions, about 50 seconds per slide. These match the speaker notes in the deck.

## Slide 1: Title

Good morning. I'm Samson Okuthe, and my project is SW-7, supervised by Associate Professor Simon Winberg with Sampath Jayalath as co-supervisor. It is part of the TUKZIE programme, which is building a 72 volt electric cargo trike for last-mile freight. My part is the on-board electronics: a telemetry unit that measures how the trike rides, and a windshield head-up display that shows the driver only what matters for safety. In the next ten minutes I'll cover why this is needed, how I built and tested it, what the bench results show, and what is left.

## Slide 2: Why this matters

Two facts frame the project. First, electric trikes can make economic sense for freight in African cities: on the routes a 2025 study examined in Dar es Salaam, an electric cargo tricycle cut operating cost per kilometre by 45.5 percent against a motorcycle and up to 86 percent against a light car. Second, any display that pulls the driver's eyes down is a risk. NHTSA guidance says a single glance away from the road should not exceed two seconds. So the question is whether we can put edge telemetry and a head-up display together on a low-cost trike, which the literature treats as an open problem. I'll keep the background short and move to what I built.

## Slide 3: Aim and research questions

The aim is a low-cost unit that characterises the trike's ride at the edge and shows only safety-relevant data head-up. I split that into four research questions, and I've marked honestly where each one stands. RQ1, dual-IMU acquisition at 200 hertz with the sensors agreeing within noise, is verified on the bench. RQ3, the data path from sensor to cloud, is verified on the bench for acquisition and the MQTT publish, but not yet on the vehicle. RQ4, the ride features, passes its self-test but needs real road data. RQ2, the HUD, depends on the field test and is still outstanding.

## Slide 4: The system on the bench

This is the whole system on the bench, with each part labelled. On the right is the telemetry unit: an ESP32-S3 on a Makerfabs board with a built-in A7670X LTE modem, which also gives us GNSS. Two MPU6050 IMUs are sampled at 200 hertz each, and the battery management system is read over Bluetooth Low Energy. On the left is a Raspberry Pi 4 with the camera. The two boards share one wire: the ESP32 toggles a sync pulse that the Pi logs, so camera frames and IMU data can be lined up in time. The Pi 4 is used rather than the team's Pi 5 so the existing vehicle dashboard on the Pi 5 is not disturbed.

## Slide 5: Firmware: deterministic acquisition first

The firmware runs on FreeRTOS and is split across the two cores. Core 1 holds everything timing-critical: one task per IMU at the highest priority, each holding a 5 millisecond period with vTaskDelayUntil so the rate cannot drift. The acquisition tasks never print or block. They time-stamp each sample with a microsecond clock and push it into a bounded queue; if a queue is full the sample is dropped and counted, so a slow consumer can never stall acquisition. Separate tasks compute the ride features over one-second windows and fuse the two sensors. Core 0 handles the slow, blocking work: the modem, GNSS, MQTT, the flash log and the battery link.

## Slide 6: Approach: prove each stage before building on it

My method was staged verification. Each interface was brought up on its own on the real board, with a defined pass criterion, before anything was built on top of it. Then both IMUs were acquired at 200 hertz and calibrated against gravity. Then the ride features and the fusion, each with a self-test at boot. Then the local log and the LTE publish. The last stage, validation on the moving vehicle, is still to come, and it's drawn dashed for that reason. This order paid off: several of the faults I'll show later would have been invisible if I'd integrated everything first.

## Slide 7: Result: 200 Hz acquisition and dual-IMU fusion

First results. Both IMUs run at 200 hertz with zero dropped samples, and the drop counters prove that rather than assuming it. Two nominally identical accelerometers disagreed by about 8 percent at rest; per-sensor calibration against true gravity brought that down to measurement noise, which meets RQ1. The two are then fused into one ride estimate. With equal noise on both sensors, inverse-variance weighting reduces to a plain mean. Windows are only paired if they ended within half a window of each other, a disagreement figure is reported rather than hidden, and if one sensor goes silent for three seconds the output falls back to the other. The chart is a recorded 150 second session: still, then disturbed by hand from about 75 seconds. All 149 windows were fused from both sensors with skew under a millisecond, and all five boot self-tests passed. One honest finding: the stored calibration on the board was not the one first measured, and the resting readings were 1.3 and 2.9 percent above gravity, so the sensors will be recalibrated before the field test.

## Slide 8: Result: camera alignment and the cellular path

Two more bench results. On the camera side, a 15 second combined test produced 439 frames, consistent with about 29 frames a second, and 33 sync edges, consistent with the 2 hertz pulse. A dedicated calibration then bounded the offset between the camera clock and the IMU clock to under about one second, which is enough for labelling ride events after the fact. On the network side, the full chain worked end to end on real hardware: SIM, registration, data context, MQTT connect, and an acknowledged publish, tested against a public broker. Registration was intermittent, so this proves the mechanism, not reliability under vehicle conditions. Telemetry is also logged to the board's own flash so nothing depends on coverage.

## Slide 9: What testing found, and how it was fixed

Testing each stage on real hardware found faults that would have been hard to trace later. The GNSS reply was assumed to have 13 fields; the real modem gave 9, and the manual documents 16 with speed in knots. The parser checks the count, so this showed up in the log instead of producing wrong positions. The BLE service lookup assumed the wrong parent service; it now searches all services, and my frame decoding matched an independent parser byte for byte. The microSD chip-select resistor isn't fitted, so logging moved to internal flash. A boot loop came from a flash-size mismatch. And one open finding: the flash writes line up with 25 to 30 millisecond stalls on both IMUs every 12 seconds. No samples were lost, and disabling the log for one session will confirm the cause.

## Slide 10: Camera casing and hazard awareness

On supervisor direction, the camera's role grew from a visual record to a hazard-awareness function. I designed a three-part casing and 3D printed it: a bottom shell and top cover that protect the camera and its ribbon cable, and a 30 degree corner mount to fix it to the trike. A second casing houses a second camera. The casings are printed but not yet fixed to the vehicle. The detector is a pretrained, 8-bit SSD-MobileNet chosen to fit the Pi 4, with no training of my own. It reports only a few object types in three coarse distance bands. It has now run on live bench footage at about 7 frames a second and detects a person reliably; the other object types and the distance calibration are still to be tested. For a live near-object alert I chose a VL53L5CX time-of-flight sensor with an 8 by 8 zone grid, so it can tell left, centre and right apart. It has been sourced and is awaiting delivery.

## Slide 11: Field test on the TUKZIE Rev 0 (placeholder)

PLACEHOLDER: replace this slide once the on-vehicle test has been done. Planned content: the ride features against known road and powertrain events for RQ4; end-to-end latency, data loss and recovery over LTE on the moving vehicle for RQ3; the HUD and glance observation for RQ2; and the first outdoor GNSS fix, which confirms the field order and speed units and lets the speed-normalised index be computed.

## Slide 12: Conclusions, next steps and questions

To conclude. Every subsystem runs together on the target board: two IMUs at 200 hertz with no loss, calibrated and fused live, battery and GNSS interfaces, a local log, an acknowledged cellular publish, and a camera aligned to the IMU data within a second. Testing each stage on real hardware found and fixed several faults that assumptions had hidden. What's left is the part that answers the ride and HUD questions: recalibrate the IMUs, run the field test on the trike, confirm the flash-write stall, integrate the time-of-flight and air-quality sensors, and build the HUD. Thank you, I'm happy to take questions.
