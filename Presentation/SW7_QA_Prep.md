# SW7 presentation: question preparation

Likely questions from the examiners and the open day, with short answers based on the report, the test logs and the code (state on 1 October 2026). Where something has not been measured, the answer says so. Saying "not measured yet, and this is how I would measure it" is a strong answer; guessing a number is not.

How to answer: give the number, say how it was measured, then state the limit. For example: "102 ms median, measured from the sensor's own readout timestamp over a one-minute run on the bench; not yet on the vehicle."

Contents
1. Scope and decisions
2. IMUs and signal processing
3. Firmware and real-time behaviour
4. Cellular, logging and data
5. GNSS
6. Battery and motor
7. Camera and detector
8. Distance sensors
9. Time synchronisation
10. Dashboard
11. Testing and engineering method
12. Power, cost, mounting, environment
13. Questions to expect that expose gaps
14. Numbers to know by heart

---

## 1. Scope and decisions

Why did you drop the windshield HUD?
The TUKZIE trike already runs a dashboard (PySide6 on a Pi 5) that shows speed, battery and status, which is most of what a HUD would show. A second display would compete for the driver's attention, which works against the glance-time argument in the first place. And the programme is moving towards autonomy, where the camera's hazard alerts are more useful than another screen. So the alerts go on the existing dashboard. The supervisor agreed on 1 October 2026, and the title change to "Development of an Embedded HPEC Telemetry Unit and Dashboard Integration for the TUKZIE Rev 0 Platform" was approved by the course coordinator on 2 October. He also pointed to the time-of-flight and sensor-fusion side as a research aspect.

But a dashboard is head-down. Doesn't that contradict your 2 s glance argument?
The 2 s guidance limits the length of each glance; it does not ban head-down displays. The page is designed to be read in one short glance: one row per hazard, the class and a distance band in the dashboard's red, amber and green status colours. Whether a driver actually reads it within 2 s has not been measured. That is the open part of RQ2, and an audible cue for the immediate band would reduce the need to look at all.

Why a Raspberry Pi 4 and not the Pi 5?
The Pi 5 runs the team's dashboard and there was one storage card. Keeping the camera on its own Pi 4 means a camera crash or update cannot take the dashboard down. The cost is a network hop between them.

Why the ESP32-S3 board?
It has two cores, so timing-critical acquisition (core 1) can be separated from blocking modem work (core 0). It has BLE built in for the battery. And this Makerfabs board carries the A7670X LTE modem with GNSS, so one board covers cellular, position and Bluetooth.

What is new here? These are all known parts.
Each part is well known. Our literature check found no system that combines ride telemetry, cellular publishing and camera hazard alerts on a three-wheeled cargo vehicle at this cost. The contribution is the integration, measured part by part, on the target hardware.

## 2. IMUs and signal processing

Why 200 Hz?
ISO 2631-1 weights whole-body vibration up to 80 Hz, so sampling must exceed 160 Hz. 200 Hz gives margin without overloading the I2C bus. Measured: 200.0 to 200.5 Hz on both sensors, zero dropped samples.

Your low-pass filter is set to 260 Hz but you sample at 200 Hz. What about aliasing? (Likely from a signal-processing examiner.)
That's correct, and it's a limitation. Nyquist is 100 Hz, so content between 100 and 260 Hz can fold back into the band. The widest filter was chosen so the 80 Hz band of interest isn't attenuated; the next setting, 94 Hz, would cut into it. The proper fix is to sample faster (the MPU6050 can run at 1 kHz) and filter and decimate digitally to 200 Hz. This is not yet in the report and should be added as a limitation.

Why use the acceleration magnitude, not one axis?
The magnitude is the same whatever way the sensor is mounted, and the mounting orientation wasn't fixed yet. The cost: you can't tell which axis a disturbance came from. Orientation compensation is future work.

Your RMS includes gravity, doesn't it?
Yes. The RMS of the magnitude sits near 9.8 m/s² at rest. The standard deviation, which is the RMS about the mean, is the vibration measure; peak-to-peak and jerk also ignore the constant part. The resting vibration level of 0.041 m/s² is the standard deviation. A proper ISO 2631 figure would also apply the standard's frequency weighting, which is not implemented yet.

Why calibrate with a single scale factor?
The features use the magnitude only, so one factor per sensor corrects exactly what is used. It holds only in the orientation it was measured in: the target board's readings drifted to 9.93 and 10.10 m/s² after the sensors were moved. So it will be redone once mounted (the `!recal` command). A six-position, per-axis calibration would remove the orientation dependence.

Why ±8 g?
To give headroom for pothole and kerb impacts without clipping. It is provisional until field data shows the real peaks. The hand test reached 77.6 m/s² peak-to-peak, which is within range.

Why two IMUs? How is the fusion justified?
Redundancy, lower noise, and a check on mounting differences. Both are the same part with the same settings, so equal noise is assumed, and inverse-variance weighting then reduces to the mean. The equal-noise assumption could be checked from each sensor's resting variance; that hasn't been done formally. A disagreement figure is reported so the average does not hide differences, windows are paired only if they end within 500 ms (half the 1 s window, so they overlap by at least half), and if one sensor goes silent for 3 s the output falls back to the other.

How do you know the features separate road from powertrain vibration (RQ4)?
Not yet. They pass synthetic self-tests (a sine wave with known RMS and crest factor, within 5%) and respond to a hand disturbance. Separation needs road data. The plan: run the motor with the trike stationary (powertrain only), drive over known bumps, and use the Hall-sensor motor speed, since motor vibration follows motor speed and road vibration follows the road.

What is the speed-normalised index?
Mean-square acceleration divided by GNSS speed, following Li et al. 2018, because the same road driven faster shakes more. Two differences from that study: our sensors are on the body rather than the axle, and we use the magnitude. It is undefined below a minimum speed, and it hasn't yet been computed from real driving.

## 3. Firmware and real-time behaviour

How do you guarantee 200 Hz?
Each IMU has its own task on core 1 at the highest priority, using `vTaskDelayUntil` with a 5 ms period, so delays don't accumulate. Acquisition never prints or blocks. Each sample is time-stamped with the microsecond timer, given a sequence number, and pushed into a bounded queue of 100 samples (500 ms). If the queue were full the sample would be dropped and counted. The drop count was zero in every run.

What were the 40 ms stalls?
Writing to the ESP32's flash suspends the instruction cache on both cores, so code running from flash pauses, including the IMU tasks. Proof: with logging switched off, the worst gap was 5.9 ms, and no gap exceeded 10 ms. The fix in v0.6.0 buffers records in memory and writes once a minute, so the stalls are six times less frequent. Each stall is no shorter. No samples are lost, because the queue absorbs about 8 samples per stall, and each sample carries its true timestamp. Removing the stalls entirely needs the acquisition code in instruction RAM, or the IMU's own hardware FIFO.

Why is all modem traffic in one task?
The modem's serial line has no lock. Two tasks sending AT commands would interleave and corrupt each other.

How is the motor speed counted without disturbing the IMUs?
The ESP32's hardware pulse counter counts both edges with a 12.5 µs glitch filter. A low-priority task reads it once a second. Bench loopback check: 666 edges in 333.3 s, exactly 2.00 per second.

## 4. Cellular, logging and data

How does the data get to the cloud?
JSON over MQTT using the modem's own AT command set (`AT+CMQTT*`), with QoS 1 and a 60 s keep-alive, every 10 s. The firmware checks each command's result code, not just the `OK`. The manual says `OK` can precede a failure, and the first version had treated it as success.

What happens if the signal drops?
Tested by switching the radio off for 60 s. The firmware saw the loss 0.8 s later from the modem's report (or after three failed publishes, 20.7 s), retried at 30 s and then 60 s, and reconnected about 5 s after the radio came back. There were no failed publishes afterwards.

Is data lost during an outage?
Not locally: every record is also written to flash. But the backlog is not yet re-sent over MQTT when the connection returns; that is a stated limitation. The stored log was read back in full: 6,020 records.

Which broker? Is it secure?
For testing, the public `test.mosquitto.org`, unauthenticated and without TLS, and only for the test. The firmware supports a username and password. A real deployment needs a team broker with credentials and TLS. The vac-work team's broker credentials were deliberately not copied into this code.

How much data does it use?
About one record of roughly 700 bytes every 10 s, about 250 KB an hour, under 2 MB for an 8-hour day. This is an estimate from the record size, not a measured data bill.

What is the log's capacity?
A 3 MB cap in a 3.5 MB flash partition, at about 160 KB an hour, so about 18 hours. It is then truncated, not rotated. Rotation is future work.

What was the nan problem?
Reading the log back found 5,545 of 6,020 records contained `nan` (for example, the position before a GNSS fix). JSON does not allow `nan`, so those records were invalid, and the same text was going out over MQTT. Firmware v0.6.3 writes `null`, and all records now parse.

## 5. GNSS

How accurate is the position?
On a rooftop: 104 fixes, median 2.7 m from a phone's position, 95% within 11.0 m, maximum 12.3 m. The phone has its own few-metre error, so this is agreement with a reference, not absolute accuracy.

What went wrong first?
The parser assumed degrees-and-minutes in fixed field positions. The real reply is decimal degrees with 17 (sometimes 18) fields. The first parser read satellite counts as the position, which put the fix near 0°, 0°. The parser now anchors on the hemisphere letter, checks the format, and rejects jumps over 100 m/s.

How fast is a fix?
105 s from a cold start in one session, 51 s in another, with 23 to 25 satellites.

What units is the speed in?
The manual says knots. That isn't confirmed on this modem yet, and it read 0 to 5.8 while stationary. It will be checked against a known speed on the vehicle.

## 6. Battery and motor

How do you read the battery?
Over BLE using the JBD protocol, read-only (the basic-information query). The firmware only reads, never writes settings to the BMS.

What was the checksum fault?
The firmware summed the register byte as well. The JBD checksum covers only the status, length and data bytes. The protocol's own query frame shows the rule, and every real frame was failing by exactly 3. After the fix: 14 valid readings, 74.78 V, 0 A, 60%, which is plausible for 24 cells at rest (3.12 V per cell). Not yet compared with the pack's app.

The signal was weak. Is that a problem?
Yes: −88 to −93 dBm, near the limit for holding a link, which is why the connections were intermittent. The unit may need to sit within about 1 m of the pack's Bluetooth module.

Why an optocoupler for the Hall tap?
The Hall signal is 5 or 12 V and referenced to the drivetrain's ground. The optocoupler passes the pulses as light, so the two grounds stay separate and a fault on the motor side cannot reach the ESP32. Still to do: read the module's series resistor, measure the wire's voltage, and get the pole-pair count for the rpm formula (rpm = edge rate × 60 / (2 × pole pairs)).

## 7. Camera and detector

Which model and why?
SSD-MobileNet v1, pretrained on COCO and quantised to 8-bit TensorFlow Lite. It runs on the Pi 4's CPU without an accelerator: 36 ms per inference using four threads. Newer models such as YOLO variants are more accurate, especially for small or distant objects, but slower on this CPU. No training was done in this project.

What is the latency?
Measured from the sensor's own readout timestamp to the alert result: median 102 ms, 95th percentile 120 ms, maximum 136 ms, at 19.5 fps. Of that, 52 ms is readout and the camera's image processing, 12 ms preprocessing, 36 ms inference, and under 0.2 ms alert logic. With one thread it was 186 ms at 7 fps. The CPU reached 65.7 °C with no throttling. These are bench figures.

Is 0.2 s fast enough?
The three-frame debounce means an alert comes about 0.2 s after an object appears, about 1.7 m of travel at 30 km/h. A driver's reaction time is typically over a second, so the detector is a small part of the total. The detector advises; it never controls the vehicle.

How do you get the distance bands?
From the pinhole model: distance = focal length × real width / width in pixels, with a fixed average width per class (for example 1.8 m for a car). Two limits: the focal length is not calibrated yet (test C5), and real objects vary in width and angle. The bands (immediate, warning, monitoring) are deliberately coarse.

How accurate is the detection? Precision and recall?
Not measured. Only the person class has been confirmed on live frames (confidence 0.50 to 0.73). A proper evaluation needs a recorded drive with labelled frames, which is future work. Don't claim a number.

Why do alerts not flicker?
An alert is raised after 3 consecutive frames and cleared only after 5 frames with the class absent (about 0.25 s at 19.5 fps). Before that change, one person standing still produced 16 alerts in 47 s. Escalating to a nearer band also needs 3 frames. Checked offline with scripted sequences and live with the dashboard.

Why was the image pink?
The module has no infrared-cut filter. Proof: the same scene was pink with the standard tuning and neutral with the NoIR tuning, in stills taken outside the detector, so it wasn't the detector's channel order. The NoIR tuning alone washed colours out (a blue card measured 120, 124, 125). Adding saturation 1.8 restored them: blue card 1, 86, 216; red 222, 8, 77. Daylight recheck still to do.

What about night, rain and sun glare?
Not tested. The NoIR module is more sensitive to infrared, which could help at night with an infrared light. Rain and glare will reduce detection. This is outdoor testing still to do.

What about privacy?
Frames exist only in memory and are never saved. Each alert logs five fields: class, distance band, confidence, timestamp, status. There is no face or number-plate recognition and no identification of anyone. Inference runs locally on the Pi. The live view is for bench checks only and is not stored.

## 8. Distance sensors

What are the time-of-flight sensors?
The planned VL53L5CX (8×8 zones over 63°, up to 4 m) has not arrived. As a stand-in, three VL53L0X on a UCT micromouse sensor board face left, ahead and right: single-zone sensors with about 2 m range. All three share one address at power-up, so each shutdown pin is released in turn and the sensor given its own address (0x30, 0x31, 0x32). They read at about 31 times a second each, and covering each one confirmed the labels. Accuracy against a tape measure is still to check.

Why on the Pi and not the ESP32?
The Pi sits at the front next to the camera, its I2C bus is free, and the ESP32's 200 Hz acquisition stays untouched.

Will they work outdoors?
Sunlight reduces time-of-flight range, and dark targets give fewer valid readings. A published characterisation of the VL53L5CX found the valid-reading rate dropping to 19 to 34% on black targets. This must be measured on the vehicle, not assumed.

Do the camera and the time-of-flight sensors work together?
Not yet. The idea: the camera says what and roughly where, the time-of-flight sensor gives a measured distance in its direction, so an object ahead seen by both gets a measured distance instead of the pinhole estimate.

## 9. Time synchronisation

How are the camera and IMU data lined up?
The ESP32 toggles a pin every 500 ms and logs its own timestamp at each edge. The Pi logs each edge with a kernel timestamp (libgpiod) on the same monotonic clock as the camera frames. Matching the edges relates the two clocks. Result: median interval 500.06 ms, spread under 0.7 ms over 121 edges.

Why not NTP or GPS time?
The ESP32 is on cellular while the Pi is on the local network, and NTP over cellular gives tens of milliseconds at best. GNSS time is available on the ESP32 but not on the Pi. One wire is simple, deterministic and doesn't depend on any network.

What is the frame-level alignment?
Bounded under about 1 s, using a lens-cover test reported by a person, so the bound comes from human reaction time. A tighter bound needs an LED driven from the sync pin and filmed. That is adequate for labelling ride events after the fact, but not for frame-exact work.

What went wrong?
A loose jumper twice gave false or missing edges. On the vehicle this needs a latched connector.

## 10. Dashboard

How does the dashboard get the alerts?
The detector serves its active alerts as a small JSON record (the five fields plus frame rate and latency), and the page polls it twice a second. Video comes as an MJPEG stream only while the page is visible, and only the newest frame is decoded. It uses Qt networking and widgets only, not the web-engine component that crashed on the Pi 5.

Polling twice a second adds delay, doesn't it?
Yes: up to 0.5 s on top of the detector's 0.2 s, so about 0.7 s worst case to the screen. Pushing alerts (a websocket or server-sent events) or polling faster would cut that. The page test showed the alert 0.5 s after the page opened.

Has it run on the real dashboard?
Not yet. It was tested inside a copy of the dashboard's code on a laptop, against the live camera. Adding it to the dashboard needs four small edits to the dashboard team's files, which are left for that team to review.

## 11. Testing and engineering method

What was your method?
Staged verification: bring up each interface alone on the target board with a pass criterion written before the test, then build the next stage on it. Every test, its pass criterion, result and log file is in BenchTest/TEST_PROCEDURES.md and Appendix C of the report.

Give an example of engineering judgement.
The flash stalls. Three things could have caused them: the modem, the MQTT publish, or the flash writes. The firmware got a command to switch logging off while publishing continued. The gaps disappeared (worst 5.9 ms), which isolated the flash. Then the fix was chosen from three options (buffer the log, instruction RAM, sensor FIFO) on cost and risk, and re-tested: same worst gap outside flushes, six times fewer stalls.

Another one?
The pink image. Three hypotheses (channel order, camera, missing infrared filter), each with its own test. The stills outside the detector ruled out channel order, the tuning-file comparison confirmed the filter, and the colour cards measured the fix.

How many times did you repeat tests?
Most tests are one or two runs. The numbers are bench measurements, not statistics over many trials. Repeating them on the vehicle is the next step.

What would you do differently?
Reach the vehicle earlier. Sample faster and decimate, to avoid aliasing. Use the IMU's FIFO from the start, so flash pauses never matter. Write the JSON encoder to handle missing values from day one.

## 12. Power, cost, mounting, environment

What is the power consumption?
Not measured yet. The power budget is outstanding. The modem's transmit bursts and the Pi 4 (several watts under load) dominate. The plan is a DC-DC converter from the vehicle supply, and the current needs measuring on each rail.

What does it cost?
A bill of materials has not been totalled yet. Prepare this before the presentation if possible.

How will it survive the vehicle?
Not tested. The camera casing (three 3D-printed parts with a 30° corner mount) exists. Enclosures for the telemetry unit and the Pi are planned. Vibration, heat and water are untested. The jumper wires already failed under handling on the bench, so the vehicle needs latched connectors.

## 13. Questions to expect that expose gaps

Be ready to say these plainly:
- No on-vehicle test yet. RQ3 and RQ4 are answered on the bench only.
- RQ2's glance time is not measured.
- The aliasing above 100 Hz (see section 2).
- Detection accuracy is not evaluated, and distance bands are not calibrated.
- The backlog is not re-sent after an outage.
- No power budget or BOM yet.
- The BMS reading is not cross-checked with the app.
- The IMU calibration must be redone once mounted.

## 14. Numbers to know by heart

| What | Number |
|---|---|
| IMU rate | 200.0 to 200.5 Hz, 0 dropped |
| Fused windows | 149 of 149 from both IMUs, skew under 1 ms |
| IMU disagreement before calibration | about 8% |
| Flash stall | 33 to 40 ms; worst 5.9 ms with logging off; now once a minute |
| Camera latency | 102 ms median, 120 ms p95, 19.5 fps |
| Alert onset | about 0.2 s, 1.7 m at 30 km/h |
| GNSS | 2.7 m median, 95% within 11 m, fix in 105 s |
| MQTT | 47 of 47 acknowledged; reconnect about 5 s after signal returns |
| Log read-back | 6,020 records |
| Sync pulse | 500.06 ms median, spread under 0.7 ms |
| Battery | 74.78 V, 60%, signal −88 to −93 dBm |
| Time-of-flight | 3 sensors, about 31 readings/s each |
| Dashboard | live view in 0.6 s; person alert listed in 0.5 s |
