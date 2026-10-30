# Final presentation: speaker script

Word-for-word talk for the panel on 16 or 17 November 2026: 10 minutes, then 5 minutes of examiner questions. Rewritten on 30 October 2026 from the submitted report (Embedded Telemetry with Road-Surface Characterisation and Camera-Based Hazard Detection for the TUKZIE Electric Trike) and the 27 October road analysis (BenchTest/logs/run2_road_2026-10-27/analysis/run2_summary_numbers.txt). Every number below is in the report; the section is given in brackets in the timing table.

The script is written by topic, not by slide, because the deck is being rebuilt. Move to the next slide when the topic changes.

Length: 1,287 words (the optional "Add if ahead" line excluded). At a calm 130 words a minute that is just under 10 minutes; use the alert markers below to recover if you run late. The timekeeper alerts at 5 and at 8 minutes; the markers below show where you should be when each alert sounds.

How to read it: say each number slowly and once. Pause after each topic. Slow down on the flash-write gap, the road results and the alert legibility; those are what the examiners will remember.

| Topic | Words | Ends at about | Report |
|---|---|---|---|
| 1. Why it matters | 119 | 0:55 | 1.1, 2.2 |
| 2. Aim and four research questions | 123 | 1:52 | 1.2, 1.3, 1.4 |
| 3. The system as driven on 27 October | 114 | 2:44 | 1.5, 4.1, K.9 |
| 4. Deterministic acquisition and the flash-write gap | 113 | 3:36 | 5.1, 6.1 |
| 5. Fault investigations | 97 | 4:21 | E.3.7, 5.9, 6.6 |
| 6. Telemetry and store-and-forward | 92 | 5:04 (5-minute alert) | 5.7 |
| 7. Hazard detection | 77 | 5:39 | 5.6, 6.3 |
| 8. Dashboard | 108 | 6:29 | 5.8, 6.5 |
| 9. 27 October road results | 172 | 7:48 (8-minute alert) | 5.1, 5.2, 5.3, 5.7 |
| 10. Powertrain against road | 73 | 8:22 | 5.3, 6.2 |
| 11. Conclusions per research question | 136 | 9:25 | 7.1 to 7.3 |
| 12. Next steps and close | 63 | 9:54 | 8.1, abstract |
| Total | 1,287 | 9:54 at 130 words a minute | |

---

## 1. Why it matters

Good morning. I'm Samson Okuthe, and my project is Embedded Telemetry with Road-Surface Characterisation and Camera-Based Hazard Detection for the TUKZIE Electric Trike, supervised by Associate Professor Simon Winberg with Sampath Jayalath.

Where electric cargo trikes have been measured in delivery work, they cost far less to run than the motorcycles they replace; in Dar es Salaam, a little over half as much. TUKZIE is UCT's 72 volt trike for last-mile freight. But when I started, its dashboard showed only simulated values. Nothing measured how it rides, read its battery or recorded a journey. And any warning we add must respect the driver's eyes: NHTSA guidance asks that glances away from the road mostly last two seconds or less.

## 2. Aim and four research questions

So the aim was a telemetry unit that acquires synchronised inertial, battery, position and camera data, characterises the ride on board, keeps its data through coverage gaps, and shows the driver only essential safety information. With my supervisor's agreement, the windshield head-up display in the brief became integration with the dashboard the trike already has, because a second display competes for the same attention.

Four research questions. RQ1: how accurately and repeatably can a low-cost system characterise the ride? RQ2: how should safety alerts be presented on the existing dashboard? RQ3: what latency, loss and recovery can the data chain achieve? RQ4: which features separate road vibration from the motor's own? Thirteen requirements turned these into tests, each criterion fixed before its test.

## 3. The system as driven on 27 October

This is the system as driven on the twenty-seventh of October. At each end of the trike an ESP32-S3 node samples an inertial sensor at 200 hertz and streams every sample with a checksum. A third ESP32, the telemetry unit, reads the battery over Bluetooth, takes GNSS position, logs every record to flash and publishes it over LTE. At the rear a Raspberry Pi 4 runs a camera detector beside three time-of-flight sensors; at the front a Raspberry Pi 5 does the same and runs the dashboard. One Ethernet cable joins them, so the driver's display never depends on coverage. Measured at the portable power station feeding it, the whole system drew 27 watts.

## 4. Deterministic acquisition and the flash-write gap

The firmware is built around deterministic acquisition. Each IMU has its own highest-priority task on a fixed 5 millisecond period, and samples go into bounded queues that drop and count rather than block. On the bench both IMUs held 200 hertz with no dropped samples.

But no dropped samples is not the same as even spacing. Every flash write pauses the processor, leaving a gap of 33 to 44 milliseconds that later reads do not fill. Buffering the log made the gap rarer, not shorter. The real fix was architectural: the two inertial nodes keep no flash log, and on the vehicle each held 200.00 hertz with no interval longer than 5.2 milliseconds.

## 5. Fault investigations

Testing each stage before the next meant every fault could be traced. The most consequential: the Raspberry Pi 4 kept throttling and restarting. A logger recorded its power flags every two seconds: clear with nothing attached, then under-voltage fourteen seconds after the telemetry unit's LTE modem came up on its USB port. Moved off, no restarts in four hours, against three in twenty minutes before. It came back on the vehicle whenever the unit drew from that port, including one restart on the road day. So my first recommendation: the telemetry unit needs its own regulated supply.

## 6. Telemetry and store-and-forward

Telemetry has to survive coverage gaps. Every record carries a sequence number, is logged before it is sent, and is replayed if the broker did not acknowledge it. In the outage test I switched the radio off for ten minutes. The unit reconnected 5.2 seconds after it returned, and the database held all 112 records of that boot, once each. Honestly, 24 of them came from a backfill from the unit's log, because the public broker acknowledges a record with no subscriber listening. On that broker, the log is the safety net.

> 5-MINUTE ALERT: you should be here, finishing the outage test and starting "Each Pi runs a pretrained 8-bit SSD-MobileNet". If you are still on the fault investigations, drop the sentence about the road day, finish it, and give the outage test in two sentences.

## 7. Hazard detection

Each Pi runs a pretrained 8-bit SSD-MobileNet detector. On the Pi 4 with the whole system running, the median from camera readout to result was 118 to 122 milliseconds; on the Pi 5 beside the dashboard, 51 to 54. On the road the front ran at 23 frames a second. No frame is ever stored. What I cannot tell you is how many road alerts were correct: no forward video was kept, so precision is future work.

Add if ahead: "An alert needs three frames, so at the rear it is raised about a quarter of a second after an object appears."

## 8. Dashboard

On the dashboard, the first problem was data validity: the inherited dashboard silently showed simulated values when its link was down. It now shows only live data, and a dash when a value is missing. A banner over every page shows an immediate hazard and names its side.

Glance time needs a participant, but legibility does not. At the measured eye distance of 0.62 metres, the speed digits subtend 94 arc minutes, far above the 20 ISO 15008 recommends. The alert banner subtends 10, below even the minimum of 12. The speed is legible at a glance; the warnings are not. Enlarging them comes before any glance study.

## 9. 27 October road results

On the twenty-seventh we drove laps of a car park at 10, 15 and 20 kilometres an hour, with a phone streaming GNSS as the speed reference. The front node delivered 1.79 million samples with no gap; the rear lost 910, 0.08 percent, in transport. Over the wired serial link the recorder received 4,196 of 4,201 per-second records, 99.9 percent.

On a smooth loop, five passes at 10 kilometres an hour gave a weighted acceleration that varied by only 5.0 percent at the rear and 5.3 at the front, half the 10 percent allowed. A rougher strip read about twice as high. Only three passes were driven at 15 and 20, too few to judge: the car park was short and the trike, without its body, was unstable in the corners. And at rest the sensors read 9.845 and 9.941 against 9.81, so the calibration did not hold once mounted. Place by place, in 8 metre cells, the passes did not agree: an intraclass correlation of 0.16 at the rear, against 0.75.

> 8-MINUTE ALERT: you should be here, starting "For RQ4". If you are not yet on the powertrain, skip it and say only "the motor carries 0.9 to 3.1 percent of the road's vibration energy", then go to the conclusions.

## 10. Powertrain against road

For RQ4, stand runs with the drive wheel raised found the powertrain's lines at 42.75, 49 and 64 hertz, reaching the front through the frame. On the road those lines held only 0.9 to 3.1 percent of the energy in powered passes, while 65 to 84 percent lay between 4 and 8 hertz, and a coasting pass read the same as a powered one. At these speeds the road dominates, not the motor.

## 11. Conclusions per research question

To conclude. RQ1 is partly answered: the instrument repeats over whole passes but not place by place, and the calibration did not hold on the vehicle. RQ2 is answered for the design and its legibility, not for its effect on the driver. RQ3: recovery is measured on the bench, and on the road the wired link carried 99.9 percent, but LTE latency rests on nine records, a median of 0.44 seconds, and the link did not reconnect after 11:51. RQ4: at these speeds the motor carries 1 to 3 percent of the energy. Of thirteen requirements, five are met, seven in part, and glance time is untested. What is new is not any one part: no system I reviewed combines these on a light electric cargo trike, so the contribution is that integration and its measurement.

## 12. Next steps and close

Next: a regulated supply for the telemetry unit, a fixed LTE reconnection, larger warnings and then a glance study, road alerts checked against forward video, and marked straight sections with side video, three passes per speed, for a place-by-place answer.

Videos of the system on the road and of its development are at tuksense dot site. Thank you; I'm happy to take questions.

---

## Careful (do not say)

- "R10 is met on the vehicle." Say: 4,196 of 4,201 records, 99.9 percent; 5 missed, so partly met.
- "The GNSS updated every 25 seconds." Wrong: its position updated about every 4 seconds, near the 3 second poll, and from 12:13 it held a stale position while still flagged as fixed (5.4).
- "The power budget is 20 watts, measured." Say: 27 W measured at the power station's display, between the 17 W typical and 31 W peak estimates; only the total is measured, not each load (K.9).
- "Alerts reach the driver in a quarter of a second." The 0.26 s is at the detector; the delay to the screen is not measured.
- "The ICC shows the instrument is unreliable." Say: the whole-pass CV is 5 percent; place by place the passes disagree, which with 1 Hz phone positions cannot be separated from the line each lap took (6.2).
- "TRL 6." Say: a prototype run on the vehicle, short of the demonstration in a relevant environment set as the target (7.3).
