# Q&A marking guide: model answers (17 Nov 2026)

The marking guide (photo, WhatsApp 17 Nov 02:13) scores each question asked 0 to 3: 3 excellent, 2 satisfactory, 1 poor, 0 asked but no meaningful answer. Q&A % = total / (3 x questions scored) x 100. Unasked questions do not count, so a short, specific answer to every question asked matters more than a long one.

For every answer use three moves: the number, how it was measured, and its limit. Where a line says [your words], only you can answer it truthfully; the text there is a prompt, not a script.

Sources: final report and SW7_Examiner_Prep.md (section letters in brackets).

## 1. Problem formulation and solving (GA1)

1A. Most technically difficult problem?
Keeping the 200 Hz sampling deterministic while the same board did slow, blocking work: flash logging, Bluetooth to the battery, the LTE modem and GNSS. The sharpest example was the flash stall: every flash write left a 33 to 44 ms gap in the samples even though no sample was dropped.

1B. Why complex rather than straightforward?
Several causes produced the same symptom (the modem, MQTT publishing and flash writes all ran on the same board), the fault only appeared when all parts ran together, and "zero dropped samples" hid it, because the queue absorbed the backlog. The power fault was the same kind: each part worked alone, and only the combination failed (the modem browning out the Pi 4 through its USB port).

1C. How did you solve it?
- Software: each IMU has its own top-priority FreeRTOS task on a fixed 5 ms period (vTaskDelayUntil), with bounded queues that drop and count rather than block, and all blocking I/O on the other core.
- Diagnosis: I added a command to switch logging off while publishing kept running; the gaps disappeared (worst 5.9 ms), which isolated flash.
- System design: the inertial nodes on the vehicle keep no flash log and only stream, which removed the gap; the telemetry unit keeps the log for store-and-forward.
- Assumption checked: that the queue protects timing. It protects against loss, not against gaps, so I measured both.

1D. Most important assumption?
That vibration measured on the body at the IMU mount represents the trike's ride response, and that repeat passes over the same loop at the same speed see the same road, so pass-to-pass spread measures the instrument and not the road. No reference accelerometer was used, so I can claim repeatability, not road accuracy.

## 2. Individual work (GA8)

2A. New knowledge learned independently, and how?
FreeRTOS timing, BLE GATT and the battery's JBD protocol, the A76XX modem AT command set, MQTT, on-device detection with LiteRT, and ISO 2631-1 weighting. I learned from primary sources and checked my assumptions against them: the GNSS reply layout from raw replies, the battery checksum from a frame I knew was right, the MQTT result codes from the modem manual, and the W_k filter against a published table (within 0.005 dB at 37 frequencies). [your words: add how, e.g. datasheets, manuals, papers, using Claude to explain, trial on the bench]

2B. What existed at the start, and what did you develop?
Existing: the trike, the PySide6 dashboard v1.1 on the Pi 5 written by vacation-work teams (pages, simulator, voice, visual style), the drivetrain report, and an earlier battery Bluetooth implementation that leaked a client on each reconnection. Mine: the ESP32-S3 firmware (acquisition, calibration, features, fusion, battery rewrite, GNSS parser, MQTT, logging, store-and-forward), the camera detectors and bridge, ToF reader and fusion, the dashboard add-ons and live-only mode (63 checked edits applied to a copy, never their folder), the database, the test tools, the road-test analysis, and the enclosures. (I1)

2C. One design decision that was entirely yours?
Replacing the windshield HUD with alerts on the existing dashboard. The trike already had a driver display showing speed and battery; a second display competes for the same attention; a windshield HUD on a removable, vibrating, low-cost unit has hard optical problems (double images, eye box, daylight luminance). I made the case and my supervisor agreed by email on 1 October. Alternatives if asked: live-only mode after the dashboard showed a simulated 82 % battery as if it were real (D10), or moving detection to the Pi 5 (51 to 54 ms against 118 to 122 ms).

## 3. Literature and technical understanding

3A. Which academic work influenced the approach most?
ISO 2631-1 and Li et al. (2018). ISO 2631-1 set the band (up to 80 Hz, hence 200 Hz sampling above the 160 Hz Nyquist rate) and the a_w measure. Li et al. classified roughness online from acceleration normalised by speed, which gave me the speed-normalised index I_v. On the driver side, NHTSA 2013 set the 2 s single-glance limit behind keeping alerts short.

3B. What did you implement differently?
Li et al. put the sensor on the unsprung mass; mine are on the body. I use the variance of the magnitude rather than the raw mean square, because the mean square kept gravity in it (a bug found in review and fixed). And their index was a validated roughness class; mine is a vehicle-specific response index, not validated against a profiled road. I also found I_v was not speed-invariant on the road (1.14, 1.59, 2.44 at 10, 15, 20 km/h).

3C. Limitation in the literature that motivated the work?
Systems report accuracy or mean latency, but rarely timing jitter, data loss or measured recovery after an outage, and display guidance comes almost entirely from passenger cars. Nothing integrated two IMUs, edge features, camera and ToF alerts, and LTE with local logging on a light electric cargo trike. So the contribution is the integration and its measurement on this vehicle class, not any single part. (B1)

## 4. Failure and debugging (GA5)

4A. Approach to find problems?
List the candidate causes, then design one test that separates them, changing one thing at a time. I relied on serial instrumentation rather than a debugger, because the property under test was timing and halting the cores changes it: rate, min, mean and max interval and drop counters every 2 s, raw modem replies, and per-stage camera timing.

4B. One failure and the tests that isolated it?
The Pi 4 kept showing under-voltage and restarting. Candidates: its own supply, the ToF board, the telemetry unit on its USB port, heat. I wrote a logger of power and temperature flags, I2C devices and USB devices every 2 s. It was clean with nothing attached; the ToF board was unplugged throughout; heat raised a separate soft-temperature flag; the telemetry unit was plugged in at 17:58:05 and 14 s later, when its modem came up, under-voltage started. Then three restarts in 20 minutes with the unit on the Pi, none in 4 hours after moving it. Cause: the modem's transmit current through the Pi's USB port. (F7)

4C. What did you try that did not work?
- Boot loop: adding a PSRAM setting left the same loop; the real cause was the flash access mode (DIO, not QIO). (F1)
- Battery: I assumed the pack was absent; logging every advertiser showed none at all, so the scanner was idle. The community checksum formula was also wrong by exactly 3. (F3)
- Camera colour: I suspected the channel order; a still taken outside the detector was also pink, so it was the missing IR-cut filter. (F5)
- Pothole model: the first model scored 59.7 % mAP@50 on its own test set and 0.000 on 605 South African images; the retrained one on road-band tiles reached 0.714 but was too slow for the live path. (E13)

## 5. Software / algorithm development

5A. One important section of code?
The IMU acquisition task in the ESP32 firmware. Each IMU has its own task at the highest priority on core 1. It wakes every 5 ms with vTaskDelayUntil (fixed period, so no drift), burst-reads 14 bytes over its own I2C bus at 400 kHz, timestamps and sequence-numbers the sample, and pushes it into a bounded queue. If the queue is full it drops and counts rather than blocking. Every 2 s it reports rate, interval statistics and drops. All blocking work (BLE, modem, flash) runs on core 0. Alternative: the store-and-forward ledger, which logs every record to flash first, publishes over MQTT, marks acknowledged records and replays the rest after an outage.

5B. Why this algorithm rather than an alternative?
A fixed-period top-priority task gives a guaranteed sample instant; a loop with delay() drifts, and an interrupt-driven read cannot do I2C safely in an ISR. Separate buses rather than the AD0 address pin mean the two tasks never contend or lock. For detection, SSD-MobileNet rather than YOLO because I measured both on the Pi 4: 19.5 fps and 102 ms against 7.9 fps and 175 ms. (D5)

5C. How did you verify the code was implemented accurately?
Built-in self-tests at every boot (known sine signals through the features), sequence numbers and checksums on every sample, and offline test suites: 29 fusion tests, 22 pothole tests, 40 firmware ledger checks with 900 randomised outage simulations, 11 server tests, 40 synthetic time-to-contact tests. The W_k filter was checked against a published table (within 0.005 dB). Limit: the self-test sine had no constant offset, so it could not catch gravity in the mean square; a review did. (G14)

5D. Parameters with the greatest effect on performance?
- Sampling rate and anti-alias filter: they set which vibration can be seen at all; with the filter at 260 Hz, content between 100 and 260 Hz folded into the band (fixed to 94 Hz).
- Detection confidence threshold (0.5) and the hysteresis frames (3 on, 5 off): they trade false alerts against how quickly an alert appears.
- Thread count on the Pi detector: 4 threads gave 19.5 fps, 1 thread 7.0 fps.
- Publish interval and retry timing for LTE: they set the backlog after an outage and how quickly it drains.

5E. If you doubled or halved parameter X?
- Sampling rate doubled to 400 Hz: Nyquist goes to 200 Hz, so aliasing falls, but each read takes about 0.4 to 0.5 ms of a 2.5 ms period and the stream doubles; the Pi-side link and transport loss (0.08 % at the rear) would be the first to suffer.
- Onset frames doubled from 3 to 6: at about 19 fps the alert appears roughly 0.15 s later (about 1.3 m at 30 km/h), with fewer one-frame false alerts.
- Confidence threshold halved to 0.25: more detections and more false alerts; raised, fewer alerts and more misses (I have not measured precision and recall, so I would expect, not claim).
- Repeatability window: halving the cell length along the road leaves fewer samples per cell, so place-by-place spread goes up and ICC down.

5F. Code you are least confident about, and why?
The time-to-contact estimator for approaching objects. It passes 40 synthetic tests (within 2 % at constant speed, no false alerts in 5,000 frames of receding or jittering boxes), but it has never been checked on a real approaching object; the 261 front car alerts marked approaching on the road were not checked against video. It assumes constant closing speed and is noisy on small boxes. Second choice: the vehicle GNSS parser, which held a stale position and zero speed from 12:13 while flagged fixed.

5G. How did you validate the system?
Against 13 requirements, each with a pass mark fixed before its test, first on the bench and then on the trike. Bench: 200 Hz with zero drops; 112 of 112 records in the database after a 10-minute radio outage (24 of them by backfill from the log). Road, 27 October: front node 1,791,190 samples with no gap, 4,196 of 4,201 records over the wired link, smooth loop at 10 km/h with a CV of 5.0 % (rear) and 5.3 % (front) against 10 %. Result: 5 met, 7 partly met, 1 not tested.

5H. What was your ground truth?
It depends on the quantity:
- Sampling and loss: the sequence numbers and timestamps on every sample.
- Calibration: gravity, 9.81 m/s2, at rest.
- Position and speed: a phone's GNSS.
- Detection latency: the camera sensor's own readout timestamp.
- Powertrain: the stand runs on 23 October with the drive wheel raised, so the motor ran with no road input.
- Ride accuracy: none. There was no reference accelerometer or profiled road, so I claim repeatability, not road accuracy. That is the main limit of RQ1.

## 6. Use of AI tools

6A. Which AI tools, and where?
[your words, be complete and truthful] Claude, through Claude Code, used throughout: drafting and reviewing firmware and scripts, helping run and analyse tests, the literature search pipeline, the report wording and LaTeX, and the slides and poster. The project log records each decision as "student" or "student with Claude". I wired and built the hardware, ran every test on the bench and the trike, designed and printed the enclosures, and made the design decisions. Add any other tool you used (ChatGPT, Copilot, image tools). Note: the Appendix A declaration is narrower than this; if asked, say so. (G10)

6B. Inappropriate use in this project's context?
Letting AI invent or "fill in" a number, a test result or a reference that was never measured or read; submitting code you cannot explain; or giving it private data, such as the vacation-work team's broker credentials, whose documentation says not to share them with an AI. I kept those credentials out deliberately.

6C. Appropriate use?
Using it as a tool under your own checking: drafting a parser and then testing it against real modem replies; explaining a datasheet; reviewing the report for claims without evidence (that review found the gravity bug in the speed index). Every number in the report traces to a log or a source I opened. [your words: one example where you overruled it, e.g. you designed and printed your own enclosure rather than the generated bracket]

## 7. Results and interpretation

7A. Most important result, and why?
The 27 October road repeatability: five passes of the smooth loop at 10 km/h gave a whole-pass a_w of 1.78 m/s2 at the rear with a CV of 5.0 % (front 1.16, 5.3 %), half the 10 % allowed, and the rough strip read about twice as high. It is the first evidence the unit measures the ride repeatably on the vehicle itself, which is RQ1.

7B. Most surprising result?
How little the motor contributed. On the stand the motor raised rear vibration 5 to 7 times, with lines at 42.75, 49.0 and 64.0 Hz, yet on the road those lines held only 0.9 to 3.1 % of the energy in powered passes, and a coasting pass read a_w 1.80 against 1.78 powered. At these speeds the road dominates. (Alternative: front-to-rear delay could not be found; the correlation peak sat at 0.09 to 0.10 s at every speed, so it was body motion or clock offset, not the wheelbase.)

7C. Any result that contradicts the conclusion?
Yes, and I report it. Place by place along the loop, repeatability was poor: ICC 0.16 at the rear against 0.75, at most 0.32 in sensitivity checks. So the unit repeats over a whole pass but cannot yet map a specific spot. Also I_v rose with speed (1.14, 1.59, 2.44), against my hypothesis that it would be speed-invariant, and calibration did not hold on the vehicle (9.845 and 9.941 against 9.81). That is why RQ1 is "partly answered".

## 8. Further technical improvement

8A. Two more weeks: first improvement, and why?
A regulated supply of its own for the telemetry unit, plus the LTE reconnection fix. The modem browning out the Pi 4 through its USB port recurred on the road day (restart at 11:21), and LTE stopped reconnecting from 11:51; both undermine everything else. Then marked road sections with side video, so place-by-place repeatability and the road alerts can be checked.

## 9. Reflection

9A. Two things you would do differently?
- Get onto the vehicle much earlier, at least a stationary powertrain run in September instead of late October.
- Write requirements that measure the research questions directly (a repeatability criterion for RQ1 from the start), rather than only instrument checks.
(Others: power each board separately from day one; read the IMU through its FIFO so flash pauses do not matter.)

9B. Biggest technical mistake?
The anti-aliasing filter left at 260 Hz with 200 Hz sampling: any vibration between 100 and 260 Hz folded into the measured band (150 Hz appears at 50 Hz). Fixed by setting it to 94 Hz. [Alternatives: soldering wires to the SEN55's test pads, which lifted the supply pad and killed the sensor; or powering the modem from the Pi's USB port.]

## Things to check before the talk

- Cell length for the ICC: the plan (Method, Appendix J) said 5 m bins; the result was computed in 8 m cells aligned by the phone's GNSS position (Results 5.3, position_icc.py). If asked, say 8 m, and that the phone's GNSS error of several metres is one reason place-by-place agreement was poor.
- 6A and 9B are yours to answer from memory; do not use a prompt above you cannot back up.
