# SW7 presentation: question preparation

Likely questions from the examiners and the open day, with short answers based on the report, the test logs and the code (state on 11 October 2026, updated the same day after the outage test T15; section 18 adds the work up to 20 October, including the first road session). Where something has not been measured, the answer says so. Saying "not measured yet, and this is how I would measure it" is a strong answer; guessing a number is not.

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
13. New since 6 October
14. Questions to expect that expose gaps
15. Numbers to know by heart
16. New since the 11 October morning update (T15, pothole path, dashboard, report)
17. The critical review's weak points: questions an examiner who read the report closely will ask
18. New since 11 October: two sides, approaching objects, power, the first road session

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
ISO 2631-1 weights whole-body vibration up to about 80 Hz. The standard sets no sampling rate; 160 Hz is simply the Nyquist rate for 80 Hz, so 200 Hz gives some margin without overloading the I2C bus. Measured: 200.0 to 200.5 Hz on both sensors, zero dropped samples. Be careful: ISO weighting itself is not implemented, so the standard justifies the band, not a comfort figure (section 17).

Your low-pass filter is set to 260 Hz but you sample at 200 Hz. What about aliasing? (Likely from a signal-processing examiner.)
That's correct, and it's a limitation. Nyquist is 100 Hz, so content between 100 and 260 Hz can fold back into the band. The widest filter was chosen so the 80 Hz band of interest isn't attenuated; the next setting, 94 Hz, would cut into it. The proper fix is to sample faster (the MPU6050 can run at 1 kHz) and filter and decimate digitally to 200 Hz. The report states this as a limitation. Firmware v0.7.4, flashed on 11 October, moves the filter to 94 Hz, which reduces aliasing at the cost of some attenuation near the top of the 80 Hz band. The bench results on the slides were taken with the 260 Hz filter, so R1 has to be re-checked on v0.7.4 (the T15 log already shows 200.0 to 200.5 Hz, zero drops, on v0.7.4).

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
The variance of the acceleration magnitude divided by GNSS speed, following Li et al. 2018, because the same road driven faster shakes more. Up to v0.7.1 it used the mean square, which gravity dominates; v0.7.2 uses the variance (section 13). Two differences from that study: our sensors are on the body rather than the axle, and we use the magnitude. It is undefined below a minimum speed, and it hasn't yet been computed from real driving.

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
Not in the outage test (T15, 11 Oct, tested). Firmware v0.7.4 gives every record a boot number and a sequence number, remembers which ones the broker acknowledged, and replays the rest from flash after reconnecting. The radio was switched off for 10 minutes: 60 records built up, the modem reconnected 5.2 s after the radio came back, and the backlog drained in about 37 to 43 s. The SQLite database on the Pi 5 held 112 of 112 records of that boot, no missing sequence numbers and no duplicates, and 111 of 111 against the unit's own log read back over USB. Limits: one run, indoors, on the public broker; 24 records had to be backfilled from the unit's log (section 16).

Which broker? Is it secure?
For testing, the public `test.mosquitto.org`, unauthenticated and without TLS, and only for the test. It also does not queue messages for a subscriber that is away, which T15 showed (section 16). The firmware supports a username and password. A real deployment needs a team broker with credentials and TLS. The vac-work team's broker credentials were deliberately not copied into this code.

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
SSD-MobileNet v1, pretrained on COCO and quantised to 8-bit TensorFlow Lite. It runs on the Pi 4's CPU without an accelerator: 36 ms per inference using four threads. Newer models such as YOLO variants are more accurate, especially for small or distant objects, but slower on this CPU. The live detector is not retrained; a separate pothole model was trained (section 10).

What is the latency?
Measured from the sensor's own readout timestamp to the alert result: median 102 ms, 95th percentile 120 ms, maximum 136 ms, at 19.5 fps. Of that, 52 ms is readout and the camera's image processing, 12 ms preprocessing, 36 ms inference, and under 0.2 ms alert logic. With one thread it was 186 ms at 7 fps. The CPU reached 65.7 °C with no throttling. These are bench figures for the detector alone, with no bridge, fusion polling or viewed preview. With the full system running on a healthy Pi 4 it is 14.6 fps, 118 to 122 ms median and 146 to 148 ms at the 95th percentile, and that is the figure to quote for the system (section 17).

Is 0.2 s fast enough?
The three-frame debounce means an alert is raised at the detector about 0.26 s after an object appears with the full system running (about 2.2 m of travel at 30 km/h), or 0.2 s with the detector alone. The bridge's and dashboard's polling and drawing add a delay that has not been measured. A driver's reaction time is typically over a second, so the detector is a small part of the total. The detector advises; it never controls the vehicle.

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
The planned VL53L5CX (8×8 zones over 63°, up to 4 m) has not arrived. As a stand-in, three VL53L0X on a UCT micromouse sensor board face left, ahead and right: single-zone sensors with about 2 m range. All three share one address at power-up, so each shutdown pin is released in turn and the sensor given its own address (0x30, 0x31, 0x32). They read at about 31 times a second each, and covering each one confirmed the labels. Accuracy against a tape measure is still to check. Since 10 Oct a 0.5 s I/O timeout stops one stuck sensor freezing the reader (section 13).

Why on the Pi and not the ESP32?
The Pi sits at the front next to the camera, its I2C bus is free, and the ESP32's 200 Hz acquisition stays untouched.

Will they work outdoors?
Sunlight reduces time-of-flight range, and dark targets give fewer valid readings. A published characterisation of the VL53L5CX found the valid-reading rate dropping to 19 to 34% on black targets. This must be measured on the vehicle, not assumed.

Do the camera and the time-of-flight sensors work together?
Yes in software, not yet validated on the Pi. Since 4 Oct the bridge on the Pi 4 fuses them: the camera gives the class and a bearing (from the box centre and the 53.5° field of view), and a detection whose bearing falls in a sensor's cone, with a ToF sample within 200 ms and in range, takes the ToF distance ("fused"). A sensor that sees something the camera does not, for three readings in a row, reports an "obstacle" on its own, which covers objects outside the detector's classes. 29 offline tests pass. The dashboard does not use the fused hazards yet.

How will you validate the fusion?
Test C9 in TEST_PROCEDURES.md, not yet run. First calibrate: the camera axis on a taped floor line, the field of view with a narrow target at the edges of the view at 0.8 m, and each sensor's cone by moving a 4 cm tube across in 2 cm steps. Then four checks: a person walking across at 1 m (bearing rises steadily, sensors in spatial order), a person standing at 0.5, 1.0 and 1.5 m on a tape (fused error 5 cm or less up to 1.0 m, camera only beyond 1.2 m), a box outside the camera's classes at 0.8 m (ToF obstacle), and a person at 2.5 m (camera only).

What are its limits?
The sensor angles are defaults (-35, 0, +35°, 12.5° half-angle, 1.2 m) until calibrated. With those, the side cones overlap the camera's view only at its edges (about the outer 9° each side), so most side objects can only be reported by ToF without a class. A ToF sensor reports the nearest surface in its cone, which need not be the object the camera saw, and there is no tracking between frames.

Why is the fusion log off by default?
Data minimisation, by design. The detector normally keeps five fields per alert with a coarse distance band. A continuous log of distances and bearings is more than the system needs, so the bridge writes it only when a path is given for a C9 session, and even then numbers only, no images.

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
Yes: up to 0.5 s on top of the detector's onset of about 0.26 s, so roughly 0.8 s worst case to the screen, an estimate, not a measurement. Pushing alerts (a websocket or server-sent events) or polling faster would cut that. The page test showed the alert 0.5 s after the page opened, with a person already in view: that is not alert latency, and the time from a hazard appearing to the alert on the Pi 5 screen has not been measured.

How does the telemetry reach the dashboard?
The dashboard had no live input at all: every page ran on simulated data. The telemetry unit now prints one compact JSON line per second on USB to the Pi 4, which sits in the same front box. A bridge on the Pi 4 serves that, plus the three ToF distances, over the local network, and a live-data provider in the dashboard reads it twice a second. So the driver's display does not depend on mobile coverage. Tested: 40 of 40 lines in 40 s, IMUs unaffected at 200 Hz, live record 0.37 s old at the laptop.

Why not send it straight to the Pi 5, or use the MQTT data?
MQTT runs every 10 s over LTE, but the dashboard falls back to simulation after 2.5 s without data, and coverage drops. The ESP32 and Pi 4 already share the front box, so the Pi 4 is the natural gateway: the dashboard gets everything (camera, alerts, telemetry) from one link.

Why is the speed on the dashboard zero?
Deliberately not mapped yet: the GNSS speed units (knots per the manual) are not confirmed on this modem. It is shown raw on the ride card until checked against a known speed.

Did you try YOLO?
Yes, measured, not assumed. YOLO11n via NCNN on the Pi 4 (no PyTorch): 7.9 fps and 175 ms median from sensor to result at 320 input, against SSD-MobileNet's 19.5 fps and 102 ms. A pothole model trained in Colab reached 59.7% mAP@50 on its own test images but 0% on South African street images, so local training data and a higher-resolution crop of the road ahead are needed.

Has it run on the real dashboard?
A separate copy of the team's v1.1 was made on the Pi 5 on 2 Oct with the edits of the time, and it ran there with the native map. The team's own copy is never changed: a deploy command makes a fresh copy, applies the edits (now 50, each must match exactly once or nothing is written) and starts it. A recorded end-to-end test on the Pi 5, telemetry unit to screen, is still to be made. The edits are listed for the dashboard team to review.

What is live-only mode, and why?
On 3 Oct the Pi 4 changed address (laptop hotspot to phone hotspot). The dashboard could not reach it and silently fell back to its simulator, so invented but plausible numbers were on screen. Earlier the battery showed 82%, the simulator's last value, before the BMS had reported. On a vehicle that is worse than showing nothing. With TUKZIE_LIVE_ONLY=1 (set by our start script) the simulation never runs: missing data shows "--" or "Unavailable", and losing data for 2.5 s goes back to that, never to simulation. Tested offscreen; not yet on the Pi 5 with the real bridge.

How does the dashboard find the Pi 4?
By itself, in order: localhost, an explicit override, the wired address 10.20.0.1 (planned Ethernet link), a UDP beacon the bridge broadcasts every 2 s on port 50808, pi4-camera.local, then the last address that worked. A host counts when /telemetry answers within 3 s (1 s failed on the phone hotspot). Three failed polls start a new search; empty searches back off from 2 to 30 s (the 2 s repeat had filled the Pi 5 log with 6,828 warnings). The ride card shows the host and how it was found.

How do you know everything is up before a test?
The pre-test check, sw7_check.py: Pi 4 found, camera fps, telemetry fresh, IMU rates, three ToF valid, services running, Pi 4 under-voltage flags, Pi 5 and dashboard in live-only mode; READY only if every critical item passes. It finds the Pi 5 even on a phone hotspot that drops pings, by scanning for open ssh ports and asking the hostname. 16 offline tests pass; the first result against the real system is not yet recorded.

Why did the map crash, and what replaced it?
Diagnosed over ssh on 2 Oct without touching the team's install: the web engine alone works, but the dashboard's Leaflet web map segfaults about 2 s after the dashboard is shown on the real display, with online or offline data. Python cannot catch a native crash, so it takes the whole dashboard down; and the web map was created in the background even in native mode. Our edit stops that. The team's native map only had vector roads, so I wrote a street-tile map without the web engine: OpenStreetMap tiles drawn with Qt, cached on disk (works offline where already driven), within the OSM tile policy (two requests at a time, identifying user agent, no bulk download), heading-up follow with smooth movement, "Waiting for GPS fix", and a REPLAY badge. Course and altitude come from firmware v0.7.1. Tested offscreen only, with a generated route along UCT roads that is clearly marked as a replay and is not recorded data; not yet run on the Pi 5.

Anything else found on the Pi 5?
The screen blanked after 600 s without a touch (X11 screensaver and power management), now turned off by the start script. The team measured their game-controller poller at about 53% of a core; the vehicle is touch only, so our start script switches it off.

Is the camera and ToF fusion actually working?
Running, not yet validated. On 6 Oct, before calibration, the live record showed a fused hazard: person, ahead sensor, camera estimate 0.874 m, ToF 0.096 m, reported 0.096 m, immediate. That shows the matching works on live data and why it matters: the uncalibrated camera distance was off by almost 0.8 m at close range. The proof is test C9 (calibrate the cones and focal length, then walk across, stand at 0.5/1.0/1.5 m against a tape, a box outside the camera's classes, a person beyond ToF range). Until C9 is run I do not claim an accuracy.

Where does the driver see the ToF and the fused hazards?
On the Sensors page (three distance gauges, amber under 1.0 m, red under 0.5 m, hazards nearest first, battery, GPS, ride and link) and in a red banner that appears over any page for an immediate hazard, or amber if the link to the Pi 4 is lost for 5 s. Tapping the banner opens the Sensors page. Tested offscreen against the live bridge, deployed 6 Oct, not yet checked by touch on the vehicle.

Is your dashboard actually the one that runs on the trike?
Yes, since 6 Oct. The Pi 5 boots to a bare X display, so desktop auto-start files are never read; the team's build was started by a system service. Ours now has an equivalent service and theirs is disabled, with their files untouched, so one command switches back. After a restart ours came up under the new service.

The touch felt slow. Why?
Measured, not guessed: reading the touch controller directly over 25 taps, it reports contact in the same instant as the first position, so the panel adds no delay. Taps lasted 200 to 640 ms and Qt buttons act on release, so a long press feels slow; the visible pointer adds to it. Fixes: act on press in the nav bar, hide the pointer, then time touch to redraw.

How do you know the display is safe to glance at?
I don't yet, which is why glance time is still open. The design review uses published figures: NHTSA's 2 s single glance and 12 s per task, ISO 15008 character size of 20 arc minutes (about 24 px capital height at 70 cm on this panel), contrast of at least 7:1 for values read while moving, touch targets of 10 mm or more (Euro NCAP 2026), and parked-only analytics because NHTSA counts waiting at a light as driving.

Why did the pothole model need retraining?
Run 1 scored 59.7 % mAP@50 on its own test set but 0.000 on South African street footage: whole frames shrink a median pothole to about 17 by 4.5 px. Run 2 crops the road band (42 to 68 % of the height) into three tiles, so a median pothole is about 50 by 13 px, and fine-tunes from run 1. Run 2 (6 Oct, 60 epochs): mAP@50 0.714 at 640 (precision 0.81, recall 0.62) and 0.566 at 320, on the validation tiles. Say plainly that validation was also used to pick the best epoch, so it is optimistic, and that it is per tile; the held-out test tiles and a run on the Pi come next.

What is the AI HAT on the Pi 5 for?
A Hailo-8 accelerator (26 TOPS). It would let the detector run on the Pi 5 at the camera's frame rate and remove the Wi-Fi hop between the two Pis. Fitted but not yet enumerated (external PCIe not enabled); untested.

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

What evidence is there for the power supply requirement?
The Pi 4 must have a supply that does not sag: under-voltage makes it throttle the processor, which would cut the detector's frame rate (19.5 fps on the bench with no throttling, 30 Sep). The pre-test check reads the Pi 4's under-voltage and throttling flags every session so this is caught. The cause has since been found: the telemetry unit's LTE modem drawing its transmit current through the Pi's USB port (section 13). The power-watch log is BenchTest/logs/2026-10-06_pi4_power_watch.log.

What is the power consumption?
Not measured yet. The power budget is outstanding. The modem's transmit bursts and the Pi 4 (several watts under load) dominate. The plan is a DC-DC converter from the vehicle supply, and the current needs measuring on each rail.

What does it cost?
A bill of materials has not been totalled yet. Prepare this before the presentation if possible.

How will it survive the vehicle?
Not tested. The camera casing (three 3D-printed parts with a 30° corner mount) exists. Enclosures for the telemetry unit and the Pi are planned. Vibration, heat and water are untested. The jumper wires already failed under handling on the bench, so the vehicle needs latched connectors.

## 13. New since 6 October (likely questions)

Status words used here: tested (measured on the hardware), tested offscreen (automated tests without the real display and vehicle), in progress (being built, no result to claim).

Why did the Raspberry Pi 4 keep rebooting? (tested)
A logger recorded its power and temperature flags every 2 s. With nothing attached the flags were clear at 1.8 GHz. Fourteen seconds after the telemetry unit was plugged into the Pi's USB port, when its LTE modem came up, under-voltage started and came and went every few seconds, with the processor throttled to 600 MHz and the detector slowed from 14.3 to 12 fps. The modem's transmit bursts were drawn through the Pi's USB port. The fix is a powered USB hub for the telemetry unit and a 5.1 V 3 A supply for the Pi 4 (check whether both are fitted before saying the fix is done). The same applies to the Pi 5, whose USB ports share 600 mA on a 3 A supply. Limitation: the hub fix has not yet been shown on a long run.

Why the fan? (tested)
The Pi 4 reached its soft temperature limit at 65 to 69 C with the detector running, and 81 C without a fan; with a fan it ran at 48 to 66 C. A throttled Pi lowers the detector's frame rate, so cooling is a requirement, not a comfort. It still has to be tested in a closed box in the sun.

What was the distance-sensor hang? (tested)
If one sensor stopped answering on the I2C bus, the read blocked, so the whole reader froze and all three distances went stale. Each read now has a 0.5 s I/O timeout: a stuck sensor is skipped and logged, the others keep reading, and the bridge re-probes the missing one every 60 s. After the fix all three read again; in a hand test the ahead sensor gave 80 to 264 mm and the right sensor 157 to 199 mm. That is a functional check, not an accuracy test: accuracy against a tape measure is part of test C9, not yet run.

Why did the speed-normalised index change in v0.7.2? (flashed; index not yet exercised)
It divided the mean square of the acceleration magnitude by speed. The mean square includes gravity, about 96 m²/s⁴ at rest, so the index mostly measured gravity divided by speed. v0.7.2 uses the variance, which removes the constant part. It was found in the review of the report, not by a test, which is a fair criticism of my own checking. It needs GNSS speed from real driving before it means anything.

What do assisted GNSS and the network position give you? (tested on the bench; effect on fix time untested)
v0.7.3 downloads satellite orbit data over LTE (AT+CAGPS; the modem replied +AGPS: success) and repeats it every two hours, so the receiver need not decode it from the satellites before the first fix. Whether that shortens the 105 s cold start has not been measured; that needs an outdoor test. Indoors, with no fix, the modem's network position (AT+CLBS) is read every minute: on the bench it answered in about 0.7 s with a stated accuracy of 550 m, and was about 30 m from the outdoor fix. That 30 m is one reading and is luck as much as accuracy; the honest figure is the stated 550 m, which is why the map draws a circle rather than a point.

How does the spoken navigation work, and does it work offline? (tested offscreen; heard through Bluetooth earphones on the Pi 5)
Turns come from the map's turn banner, which places a manoeuvre where the road name changes and types it from the bearing change, because the team's route planner returns no turn steps. The voice says the route start, an early prompt about 200 m before a turn (about 30 s at 25 km/h), the turn itself (chained with a close next turn) and arrival, each once, and drops a phrase if it is delayed past its use. It goes through the team's own voice system, so their volume and mute apply. The voice is Google's online text-to-speech (gTTS); the Microsoft Edge voice was tried and refused by its server. Limitations: gTTS needs mobile data, so there is no voice offline; turns found from road-name changes can miss a turn that keeps the same road name; no speaker is fitted yet. An offline map, offline routing and an offline voice are planned, not started.

Isn't a simulated drive misleading, especially at Open Day? (tested offscreen)
It exists for indoor demonstrations, where there is no GNSS fix. It is marked on every page: a yellow strip "SIMULATED DRIVE, not live data", and a status chip that reads SIMULATED (otherwise LIVE, REPLAY or NO DATA). Obstacles, camera hazards and the Sensors page stay live during it, a real GNSS fix stops it at once, and ending it restores the live values and removes the simulated points from the Analytics history. It never writes into the live state. Say "this is simulated" when demonstrating it.

Swiping between pages while driving? (tested offscreen; not on the vehicle)
Two fingers sideways change page (three on the map, where two fingers zoom). The page follows the fingers and changes only on release past a third of the width or on a flick; resting a hand, pinching or a vertical move never changes it. Whether any touch interaction is acceptable while moving is exactly the open glance-time question; the safety alerts (the red banner and the voice) need no touch.

What happened to the Route Guidance panel?
Hidden: the turn banner on the map gives the same information in less space, so the map uses the full width. One setting restores it.

Camera frame rate: 19.5 or 14.6 fps?
Both are measured, under different conditions. 19.5 fps and 102 ms median (95th percentile 120 ms) was the 30 Sep benchmark on a properly powered Pi 4. The later check on a healthy Pi 4 gave 14.6 fps and about 120 ms from camera to detection. I have not yet broken down the difference, so quote each with its conditions. An alert needs three frames, so onset is about 0.2 to 0.3 s either way.

What changed in the report since the first draft?
A wiring appendix (Pi 4 header, sensor board and SEN5x pinouts, a connection table per link, the powered-hub and fan requirements), equations for the ride features, calibration, index and fusion, overstated claims corrected after an MSc reviewer's comments, clipping and aliasing stated as limits, and the reference list cut to the 47 sources actually cited.

What is still in progress? (no results to claim)
- Superseded the same day: the central database, v0.7.4, destination search and the pothole path are now done or built; see section 16.
- Still open: end-to-end latency (needs GNSS time), the pothole held-out score, a team broker with credentials.
- First road session on 19 October: R1 and R5 met on the vehicle; no GNSS fix, raw samples or run markers, so RQ1 and RQ4 wait for a second, shorter session (see section 18).

## 14. Questions to expect that expose gaps

Be ready to say these plainly:
- No on-vehicle test yet. RQ3 and RQ4 are answered on the bench only.
- RQ2's glance time is not measured.
- The aliasing above 100 Hz (see section 2).
- Detection accuracy is not evaluated, and distance bands are not calibrated.
- End-to-end latency, sensor to database, is not measured (no GNSS time indoors). Loss and recovery are (T15).
- Only one outage run, on a public broker that does not queue.
- The pothole path is too slow beside the main detector on a Pi 4 (off by default) and has no held-out score.
- The new dashboard items (search, status-bar pill, swipe) are tested offscreen, not by hand on the vehicle.
- Spoken directions need mobile data (online voice); no speaker fitted yet.
- The powered hub for the telemetry unit has not been proven on a long run.
- No power budget or BOM yet.
- The BMS reading is not cross-checked with the app.
- The IMU calibration must be redone once mounted.

## 15. Numbers to know by heart

| What | Number |
|---|---|
| IMU rate | 200.0 to 200.5 Hz, 0 dropped |
| Fused windows | 149 of 149 from both IMUs, skew under 1 ms |
| IMU disagreement before calibration | about 8% in an earlier session; at calibration 10.03 and 9.90 (1.3% apart); after: 9.80 and 9.81 |
| Flash stall | 33 to 40 ms; worst 5.9 ms with logging off; now once a minute |
| Camera latency, full system | 14.6 fps, 118 to 122 ms median, 146 to 148 ms p95 (quote this one) |
| Camera latency, detector alone | 102 ms median, 120 ms p95, 19.5 fps (benchmark) |
| Alert onset at the detector | about 0.26 s, 2.2 m at 30 km/h in the full system (0.2 s, 1.7 m detector alone); screen delay on the Pi 5 not measured |
| GNSS | 2.7 m median, 95% within 11 m, fix in 105 s |
| MQTT | 47 of 47 acknowledged; reconnect about 5 s after signal returns |
| Outage test T15 | 10 min radio off, 60 records built up, reconnect 5.2 s, drained in 37 to 43 s, 112 of 112 stored, 111 of 111 vs the unit's log |
| Log read-back | 6,020 records |
| Sync pulse | 500.06 ms median, spread under 0.7 ms |
| Battery | 74.78 V, 60%, signal −88 to −93 dBm |
| Time-of-flight | 3 sensors, about 31 readings/s each |
| Dashboard | live view in 0.6 s; person row 0.5 s after opening the page (not alert latency) |
| Destination search | offline matches 1 to 20 ms; Photon 1.1 to 1.4 s on the Pi 5 |
| First fused hazard | camera 0.874 m, ToF 0.096 m, reported 0.096 m (before calibration) |
| Touch panel | contact reported with the first position (no panel delay); taps 200 to 640 ms |
| Map prefetch | 656 tiles, 11.9 MB, 320 s, zoom 11 to 16 |
| Pothole model | run 1: 0.000 mAP@50 on South African frames; run 2: 0.714 (640), 0.566 (320), validation tiles |
| Camera, later check | 14.6 fps, about 120 ms camera to detection, healthy Pi 4 |
| Pi 4 brown-out | under-voltage 14 s after the modem came up on the Pi's USB; 600 MHz throttle |
| Pi 4 temperature | 81 C without a fan, 48 to 66 C with one |
| Pothole path | test image 0.63; only 0.25 Hz within 10% of the detector's speed (13.9 fps, 125 ms vs 14.6 fps, 121 ms); off by default |
| Report | 13,476 words (text only, tables removed); seven fault investigations |
| ToF after the hang fix | 0.5 s timeout; hand test 80 to 264 mm ahead, 157 to 199 mm right |
| Network position | about 0.7 s, 550 m stated, about 30 m from the outdoor fix |
| Voice prompt | about 200 m before a turn (about 30 s at 25 km/h) |
| Glance rules | 2 s single glance, 12 s per task (NHTSA); 20 arcmin text (ISO 15008) |

## 16. New since the 11 October morning update

Status words: tested (measured on the hardware), tested offscreen (automated tests, not by hand on the real screen or vehicle), off by default (built and checked, not in normal use).

How did you test that no data is lost? (tested, T15)
Firmware v0.7.4 was flashed and the ingest service ran on the Pi 5. The test script switched the modem's radio off (AT+CFUN=4) for 600 s after 60 s of normal flow. During the outage 60 records built up and the unit's lost counter stayed at 0. The modem reconnected 5.2 s after the radio came back; the unit's backlog was 0 about 43 s after reconnecting, and in the database the 60 replayed records arrived over 37.3 s, about 1.6 a second. The report from the database: 112 of 112 records of that boot stored, 0 missing sequence numbers, 0 duplicates; and against the unit's own log, read back over USB, 111 of 111 logged records stored. The pass criteria were written before the test. Limits: one run, indoors, laptop-powered, public broker.

Why 112 records in the database but 111 in the log?
The database had one record of that boot that was not in the log dump. Every record in the log is in the database, which is what the check is for. It is one record and I would not over-read it; the likely reason is a record published but not yet flushed to flash when the log was read, which I have not confirmed.

What is the latency to the database?
Not measured. The latency is receive time minus the device's UTC, and the device only has UTC once GNSS has a fix, which it did not have indoors. The pass criterion (median 2 s or less, 95th percentile 5 s or less) is written down and provisional. It needs an outdoor or road run.

What went wrong during the test? (found and fixed)
Records reached the broker but none reached the database for over an hour. The ingest used a persistent broker session (so the broker would keep messages for it while it was away), and on test.mosquitto.org that saved session stopped delivering while still connected. Persistent sessions are now opt-in (an environment variable), and the ingest was verified storing again on the Pi 5. Also, 24 records were backfilled from the unit's log with the ingest's import option: two were published while the ingest was being restarted, the rest before the fix.

So the public broker loses data?
It acknowledges a record even when no subscriber is listening, and it does not queue it. So an acknowledgement from the broker does not prove the database has the record. On this broker the safety net is reading the unit's log back and importing what is missing, which is what closed the gap in T15. A team broker with credentials, TLS and persistent sessions that work would remove that step; the team's broker details are still to be obtained.

What does "+CMQTTPUB: 0,0 means acknowledged" assume?
That the modem reports success only after the broker's QoS 1 PUBACK arrives. The 900 randomised host simulations test the ledger logic around it, not the modem. T15 is the evidence that, in practice, nothing marked as acknowledged went missing.

Does the replay disturb the IMUs?
In the T15 log both IMUs stayed at 200.0 to 200.5 Hz with zero dropped samples. The longest single sample interval in that log is 44 ms, a little above the 33 to 40 ms flash stalls. I have not yet checked whether it fell during the replay; that is the honest answer if asked.

The pothole model: does it work on the Pi? (built, off by default)
It runs and finds the pothole in a test picture at confidence 0.63, centre tile, with an alert after two runs; 22 of 22 offline tests pass. But it costs the main detector. With the path off the service runs at 14.6 fps and 121 ms; at 2 threads up to 4 Hz it fell to 11.7 fps and 137 ms. Only one run every four seconds (0.25 Hz: 13.9 fps, 125 ms) stays within 10 %, and that is too slow to warn a moving vehicle. The cost is in the main model's inference (52 ms rising to 65 to 72 ms), because both compete for the Pi 4's shared cache and memory bandwidth; pinning the worker to its own core made it worse. So it is off by default. Options: a smaller input on only the road tiles, int8, running only when moving, or the Pi 5 with an accelerator.

How good is the pothole model really?
0.714 mAP@50 on validation tiles, which were also used to choose the best epoch, so it is optimistic. The held-out test score is not made yet (the script is ready). It has not seen a road or this vehicle's camera. The fair claim is "it works on a test picture", nothing more.

Tell me about the destination search. (tested offscreen; deployed on the Pi 5)
Type-ahead like Uber: recent places and the team's offline map matches appear at once (1 to 20 ms), and Photon suggestions, biased to where the trike is, are merged in when they arrive (1.1 to 1.4 s on the Pi 5, 0.72 to 1.26 s from the laptop). Stale answers are dropped and repeats come from a cache. 33 offscreen checks pass. Not yet tried by hand on the touchscreen, and the no-internet path is tested offscreen only. Photon was chosen over Nominatim because Nominatim is not meant for type-ahead and gave no results for partial words.

Isn't typing a destination a distraction?
It is meant for planning before moving, like any navigation app. Whether to lock it while moving is part of the open glance-time question (RQ2).

Why move the obstacle warning into the status bar? (tested offscreen)
The red banner covered the status bar and the top of every page. Now it is a compact red pill on the right of the status bar: tap opens the Sensors page, Hide snoozes it. It is still on every page, so the warning is not lost.

How does the swipe avoid accidental page changes? (tested offscreen)
Nothing moves until the fingers move sideways together past about 30 px; the page follows the fingers and changes only on release, past a third of the width or on a flick faster than 650 px/s, measured from the touchscreen's own event times so a busy screen does not make a flick look slow. Resting a hand, pinching or a vertical move never changes the page. Two fingers on most pages, three on the map, where two fingers zoom.

What changed in the report?
It was cut and restructured to 13,476 words (text only, tables removed), and seven fault investigations are told in full as symptom, candidate causes, the deciding test, cause and fix, and consequence (Methodology, fault investigations). A critical review of the report found overstated or unclear points; section 17 has the answers.

## 17. The critical review's weak points (questions an examiner who read the report will ask)

Do your requirements actually measure your research questions?
Partly, and I would say so. RQ1 asks how accurately and repeatably the ride is characterised; the requirements behind it test sampling, calibration, self-tests and GNSS, which show the instrument works, not that it is repeatable on the vehicle. Repeatability needs repeated traversals of the same road at a set speed, with the spread of the features (for example the coefficient of variation) as the measure; that is in the vehicle plan, not done. RQ2 asks "which layout and update strategy"; I built one design, so the honest answer is "how", with glance time still to measure. RQ4 asks about time- and frequency-domain features; only time-domain features are implemented, and they pass a synthetic self-test, so RQ4 is not answered without road data. RQ3 is the best covered: loss and recovery are measured (T15), latency is not.

Your calibration result is circular, isn't it?
Yes for the immediate check: reading 9.80 to 9.81 right after calibrating to gravity proves the arithmetic, not accuracy. The meaningful test is drift: a later session on the target board read 9.93 and 10.10, 1.3 and 2.9 % above gravity, because the factor holds only in the orientation it was measured in. That is why it will be redone once mounted. And the 8 % disagreement came from an earlier session than the calibration; at calibration the two read 10.03 and 9.90, about 1.3 % apart. I no longer say "8 % reduced to noise".

Why two IMUs, and why average them?
The intent was redundancy (one fails, the other carries on, which the 3 s fallback does), lower noise, and a check on each other through the disagreement figure. Averaging only makes sense if both sensors see the same motion, that is, if they are mounted close together on the same part. If they are mounted at different points, they measure different things and should be reported separately, with the disagreement as a comparison, not averaged. The mounting points are not fixed yet. [Student: decide and state the planned mounting before the talk.] Also, the largest disagreement in the bench session (1.68) happened while the board was disturbed by hand, and near rest the noise alone gives a disagreement of about 1.6, so that figure does not show a real difference between the sensors. Why the MPU6050: low cost, available, I2C, and adequate range and rate for a first prototype; its noise and its limited anti-alias filtering are limits.

Sampling rate and aliasing: is your chain consistent?
Not fully, and I would say what changed. 200 Hz was chosen for the 80 Hz band of ISO 2631-1, but the ISO weighting itself is not implemented, so the standard justifies the band only. With a 260 Hz filter, content between 100 and 260 Hz could fold back; v0.7.4 (flashed 11 Oct) uses 94 Hz, which reduces that but also attenuates near the top of the band. All bench results on the slides were with 260 Hz; the road test runs on v0.7.4, so R1 must be re-checked on it. Also, "zero dropped samples" is true, but the flash stalls cause 30 to 40 ms gaps followed by bunched samples as the task catches up, and the jerk feature uses a fixed time step. The better design is the IMU's own FIFO or sampling faster and decimating, and computing features with the measured timestamps.

Which detector figure represents the vehicle: 19.5 fps or 14.6 fps?
14.6 fps, 118 to 122 ms median, 146 to 148 ms at the 95th percentile, measured on 11 October from the service's own timing lines with the whole system running. 19.5 fps and 102 ms was the detector alone on 30 September, with no bridge, no fusion polling and no viewed preview. I have not isolated the cause of the difference. The alert is raised about 0.26 s after an object appears at the detector; the time to the driver's screen is not measured.

Where does your 0.5 s onset criterion come from?
It is a design target, not derived, and that is a fair criticism. A derivation would start from the stopping distance at the trike's top speed (about 42 km/h) and a typical driver reaction time of over a second: at 42 km/h, 0.5 s is about 6 m of travel, small next to the reaction distance but not negligible. The figure that matters is hazard onset to the Pi 5 screen, including the bridge's 5 Hz poll and the dashboard's 0.5 s poll, and that is not measured.

Isn't a public broker a security and reliability problem?
Yes, for anything beyond a bench test. It is unauthenticated, has no TLS, and does not queue (T15). It was used only for bench tests. For deployment: the team's broker with credentials and TLS, and persistent sessions shown to work; the firmware already supports a username and password.

Is the camera work supported by literature?
The report's literature review is weakest here: lightweight detectors (SSD, MobileNet), COCO, 8-bit quantisation and monocular distance from box width are used but not reviewed, and the datasets need citing. That is a revision item, not something to defend as complete.

You say "low-cost". How low?
The bill of materials has not been totalled, so there is no number yet. The parts are commodity boards and sensors. [Student: total the BOM before the talk if possible.]

What about the ethics of a camera on a public road?
Frames are processed in memory and never stored; each alert keeps five fields only (class, distance band, confidence, time, status); there is no face or plate recognition. Whether an ethics appendix is required is with the supervisor. Adding the pothole class should be checked against the approval ("road obstacles") before field use.

The dashboard runs over a phone hotspot on the bench. Is that acceptable on the vehicle?
No, and it is no longer used on the vehicle. Since 15 October a dedicated Ethernet cable joins the Pi 5 and the Pi 4 (10.20.0.1 and 10.20.0.2, 1000 Mb/s, 0.22 to 0.25 ms round trip), so the driver's display does not depend on a phone or on coverage. It came loose twice during mounting on 19 October, so it must be tied down.

---

## 18. New since 11 October (two sides, approaching objects, power, the first road session)

State: 20 October 2026. Fuller answers with follow-ups are in SW7_Examiner_Prep.md section K.

Why did you move detection to the Pi 5? (tested on the bench)
The same detector runs at 19.2 frames/s and 51 to 54 ms median from readout to result on the Pi 5 with the dashboard running, against 118 to 122 ms at 14.6 frames/s on the Pi 4 with the whole system. At 30 km/h that is about 0.6 m less travel before an alert. The battery's Bluetooth also did not reach the telemetry unit at the front, so the unit moved to the rear. With detection beside the display, a front alert no longer crosses the network. Cost: 64 to 73 percent of the Pi 5's CPU in total; the rear stays on the slower Pi 4.

How does time to contact work without a calibrated camera? (synthetic only)
Image width is proportional to 1/distance, so for constant closing speed 1/w falls in a straight line to zero at contact, and tau = w / (dw/dt) (Lee 1976; Dagan et al. 2004). Focal length and object size cancel. A robust Theil-Sen line over the last 0.6 s, with gates on frame count, slope agreement, growth and image edges. Warning under 4 s, immediate under 2 s. Limits: untested on a real approach (C11); assumes constant speed; noisy for small distant boxes; pose changes alter width; a still object ahead counts as approaching while the trike moves (intended forward-collision behaviour).

What did the first road session show? (tested on the vehicle, 19 October)
Recorded on the Pi 5 for 108.6 minutes, about 16 of driving, no laptop on board. Both IMUs at 200 Hz with no drops and one 2 s stall, but a third of the one-second records lost on the USB link: R1 partly met on the vehicle. Battery link held under load: up to 46.9 A, 74.6 to 72.8 V, 60 to 58 percent: R5 partly met (no meter check). Parked and driving separate clearly in the vibration value. 1,342 front and 741 rear alerts, not checked against video.

Why no GNSS fix on the road?
No GNSS antenna had been connected, so there was no fix in any of the 3,464 records. The receiver and parser worked on the bench (fix in 105 s, 2.7 m median). R4 is untested on the vehicle rather than failed; the antenna is now fitted.

Why is RQ4 still not answered?
It needs raw 200 Hz samples for spectra (v0.7.4 keeps one-second features only), a speed reference (no GNSS, no Hall tap) and marked runs including the stationary powertrain baseline. The session had none of these. The second, shorter session with firmware v0.7.5 (raw stream), working GNSS and timed runs is planned. The same gaps stop RQ1's repeatability.

How much power does it use, and what about the brown-outs?
About 20 W typical, 0.27 A from the 72 V pack, under 1 percent of the motor's 2.5 kW rated input; only the Pi 5 is measured. Converter: full 60 to 88 V range, rated 100 V, 40 W at 5 V, fused, off with the vehicle. Brown-outs: the LTE modem's transmit bursts through the Pi 4's USB port; it recurred in the closed box on 16 October (76.9 C, restart with under-voltage present). The telemetry unit needs its own supply, which is not yet fitted. The Pi 5's four restarts on 19 October were abrupt power losses (normal readings just before), not brown-outs, and it did not restart during the drive.

What ethics conditions applied to the road session?
Approval EBE/03305/2026 with conditions: a signed physical risk assessment before driving, a closed area not a public road, two people whenever the 72 V system is on, only me as investigator, no faces recorded, glance observation only if the supervisor confirms it is covered, vehicle returned to standard; plus the camera conditions (no frames stored, five fields per alert). [Student: confirm from your run sheet that each was met before saying so; the report does not yet record the venue or the risk-assessment signature.]

Why is the rear view mirrored?
Like a car's reversing camera, so the driver's left is on the left; the rear sensors' left and right are swapped to match. The banner labels each warning Front or Rear and puts approaching objects first.

Are the enclosures printed?
The rear box and a first IMU pod (whose fit test led to revision 3). The display mount, front pod for the Pi 5 and AI HAT+, and vented lids are checked in CAD only. The Pi 4 reached 76.9 C in the closed box, which is why both lids now have an exhaust grille under a rain hood; the vented temperature is not measured yet.
