# SW7 final presentation: speaker script

Word-for-word talk for the 16 to 17 November presentation, slide by slide. The full script is the same text as the
speaker notes in SW7_Final_Presentation.pptx (and SW7_Talking_Points.md, generated from build_deck.js). If you change
a sentence here, change it in build_deck.js too, or the two drift apart.

Updated 20 October 2026 with the results since 11 October: the two-sided layout, detection on the Pi 5, the
approaching-object warning, the enclosures and power budget, and the first road session (19 October). The Approach
slide was folded into the Firmware slide (one line), and the bench-photo slide was replaced by the two-sided system.

Length: 1,275 words over 14 slides. At about 140 words a minute that is 9 minutes 08 seconds of
speaking. Fourteen slide changes and short pauses add about 25 seconds, so expect to finish near 9:35 at a calm pace.
Under 10 minutes is the rule. If you are behind, use the cuts below; each saves 10 to 30 seconds.

Checkpoints: be on slide 6 by 3:00, on slide 10 by 5:55, on slide 13 by 8:00. If you reach slide 10 later than
6:15, use the cuts for slides 10 to 13.

How to read it: say each number slowly and once. Pause for a breath after each slide title. Slow down on slide 7
(the power fault) and slide 13 (the road session); those are the parts the examiners will remember.

Status words used on the slides: tested (measured on the hardware), tested offscreen (automated tests without the
real touchscreen or vehicle), synthetic (tested on generated data only), checked in CAD (geometry only, not printed),
untested or open (built, no result to claim).

| Slide | Title | Words | Target | Running total |
|---|---|---|---|---|
| 1 | Title | 56 | 0:24 | 0:24 |
| 2 | Why this matters | 78 | 0:33 | 0:57 |
| 3 | Aim and research questions | 93 | 0:40 | 1:37 |
| 4 | The system: front and rear, joined by one cable | 104 | 0:45 | 2:22 |
| 5 | Firmware: deterministic acquisition first | 83 | 0:36 | 2:58 |
| 6 | Result: 200 Hz acquisition and dual-IMU fusion | 89 | 0:38 | 3:36 |
| 7 | Seven fault investigations: symptom, test, cause, fix | 109 | 0:47 | 4:23 |
| 8 | Result: timing, position, and no data lost in an outage | 91 | 0:39 | 5:02 |
| 9 | Hazard detection: twice as fast at the front | 98 | 0:42 | 5:44 |
| 10 | Approaching objects: time to contact from box growth | 102 | 0:44 | 6:28 |
| 11 | Both cameras on the existing dashboard | 89 | 0:38 | 7:06 |
| 12 | On the vehicle: enclosures, heat and power | 88 | 0:38 | 7:44 |
| 13 | First road session, 19 October | 114 | 0:49 | 8:33 |
| 14 | Conclusions and next steps | 81 | 0:35 | 9:08 |

---

## Slide 1: Title (0:24, running 0:24)

Key number: 72 volt trike.

Script:
Good morning. I'm Samson Okuthe, and my project is SW-7, supervised by Associate Professor Simon Winberg with Sampath
Jayalath. It is part of TUKZIE, a 72 volt electric cargo trike for last-mile freight. I built its on-board
electronics: a telemetry unit that measures how the trike rides, and safety alerts on the dashboard it already has.

If short on time (about 20 s):
Good morning. I'm Samson Okuthe, project SW-7, supervised by Associate Professor Simon Winberg. I built the on-board
electronics for TUKZIE, a 72 volt electric cargo trike: ride telemetry, and safety alerts on its existing dashboard.

---

## Slide 2: Why this matters (0:33, running 0:57)

Key number: 2 seconds (longest single glance, NHTSA).

Script:
Electric trikes make economic sense for freight in African cities: on delivery routes in Dar es Salaam, an electric
cargo tricycle cut the operating cost per kilometre by 45.5 percent against a motorcycle. But anything that takes the
driver's eyes off the road is a risk; NHTSA guidance limits a single glance to two seconds. So the problem is to
combine edge telemetry with short, safety-only alerts on a low-cost trike, and to measure whether each part works.

If short on time (about 25 s):
Electric cargo trikes cut operating cost per kilometre by 45.5 percent against a motorcycle in Dar es Salaam. But
NHTSA allows two seconds per glance. The problem: edge telemetry plus safety-only alerts, each part measured.

---

## Slide 3: Aim and research questions (0:40, running 1:37)

Key number: Only RQ3's loss and recovery is fully tested; RQ1 held its rate on the road.

Script:
Four research questions, and where each honestly stands. RQ1, how accurately and repeatably a low-cost unit
characterises the ride: the instrument is verified, and on the first road session it held its rate, but repeatability
is not measured yet. RQ2, alerts on the existing dashboard with the least distraction: this replaced the head-up
display with my supervisor's agreement. It is built; glance time is not measured. RQ3, latency, loss and recovery:
loss and recovery pass a ten-minute outage test; latency needs GNSS time. RQ4, road against powertrain vibration,
needs the second road session.

If short on time (about 30 s):
Four questions. RQ1: the instrument is verified and held its rate on the road; repeatability is not measured. RQ2:
built on the existing dashboard; glance time not measured. RQ3: loss and recovery pass; latency open. RQ4 needs the
second road session.

---

## Slide 4: The system: front and rear, joined by one cable (0:45, running 2:22)

Key number: Ethernet 1000 Mb/s, 0.22 to 0.25 ms round trip.

Script:
Since the fifteenth of October the system has two sides, joined by one Ethernet cable. At the front, a Raspberry Pi 5
behind the dashboard runs its own camera, the detector, a time-of-flight board and the fusion, so a front alert never
crosses the network. At the rear, beside the battery, the Pi 4 runs the rear camera and sensors and carries the
telemetry unit: an ESP32-S3 with LTE and GNSS, two IMUs at 200 hertz and the battery link. Two findings drove this:
the battery's Bluetooth did not reach the front, and the Pi 5 runs the detector more than twice as fast.

If short on time (about 30 s):
Two sides joined by Ethernet. Front: the Pi 5 behind the dashboard with its own camera, detector and distance sensors.
Rear: the Pi 4 beside the battery with the rear camera and the telemetry unit. The battery's Bluetooth did not reach
the front, and the Pi 5 is twice as fast.

---

## Slide 5: Firmware: deterministic acquisition first (0:36, running 2:58)

Key number: 5 ms fixed period per IMU task; 94 Hz filter in v0.7.4.

Script:
The firmware runs on FreeRTOS across two cores. Core 1 holds one task per IMU at the highest priority, on a fixed 5
millisecond period. They never block: each sample is time-stamped into a bounded queue, and if it is full the sample
is dropped and counted. Core 0 does the modem, GNSS, MQTT and the flash log, in one task because the modem's serial
line has no lock. Version 0.7.4 adds sequence numbers, backlog replay and a 94 hertz filter against aliasing.

If short on time (about 25 s):
Core 1 runs one task per IMU on a fixed 5 millisecond period; they never block, and a full queue drops and counts a
sample. Core 0 does the modem and the log. Version 0.7.4 adds sequence numbers, replay and a 94 hertz filter.

---

## Slide 6: Result: 200 Hz acquisition and dual-IMU fusion (0:38, running 3:36)

Key number: 149 of 149 windows fused, under 1 ms skew.

Script:
Both IMUs run at 200 hertz with no dropped samples, counted, not assumed. Flash writes cause one gap of under 45
milliseconds a minute, and the queue holds the samples through it. A gravity factor per sensor brings both to 9.80 or
9.81, but only in that orientation, so it is redone once mounted. Fusion is an equal-weight mean; windows pair only if
they end within half a window, and the disagreement is reported. In a 150 second session all 149 windows fused with
under a millisecond of skew.

If short on time (about 25 s):
Both IMUs at 200 hertz, no dropped samples; one flash gap a minute. Calibration brings both to 9.8, but only in that
orientation. Fusion: 149 of 149 windows, under a millisecond of skew.

Careful: Do not say "8 percent reduced to noise". The 8 percent came from an earlier session than the calibration.

---

## Slide 7: Seven fault investigations: symptom, test, cause, fix (0:47, running 4:23)

Key number: Under-voltage 14 s after the modem came up; none in 4 h once moved; 76.9 C in the closed box.

Script:
Because each stage was tested before the next, every fault could be traced to one change. Seven needed a real
diagnosis; here is the one that mattered most. The Pi 4 kept throttling and rebooting. A logger recorded its power
flags every two seconds: clear with nothing attached, then under-voltage fourteen seconds after the telemetry unit's
modem came up on its USB port. Moved off, no restarts in four hours. It came back in the closed box: 76.9 degrees and
a brown-out restart. So the unit needs its own supply, and the lids gained vents. The Pi 5's restarts while mounting
were different: abrupt power loss, not a brown-out.

If short on time (about 35 s):
Seven faults needed a real diagnosis. The key one: the Pi 4 rebooted because the telemetry unit's modem on its USB
port pulled its supply down, found by logging power flags every two seconds. It came back in the closed box, so the
unit needs its own supply and the lids gained vents.

Careful: The Pi 5 restarts on 19 October were not a brown-out: its logger showed normal supply, flags and temperature just
before each one. Say "abrupt power loss", not "under-voltage".

---

## Slide 8: Result: timing, position, and no data lost in an outage (0:39, running 5:02)

Key number: 112 of 112 records stored after a 10-minute outage.

Script:
The sync wire gives a median interval of 500.06 milliseconds over 121 edges, with under 0.7 of spread, so camera and
IMU clocks line up. On a rooftop, GNSS was a median 2.7 metres from a phone. The outage test: I switched the radio off
for ten minutes. The unit reconnected 5.2 seconds after it came back and cleared 60 records in about 40 seconds; the
database holds 112 of 112. The public test broker does not queue, so the log read-back is the safety net, and latency
needs GNSS time.

If short on time (about 30 s):
Sync wire: 500.06 milliseconds, under 0.7 of spread. GNSS: 2.7 metres from a phone on a rooftop. Radio off for ten
minutes: reconnected in 5.2 seconds, 112 of 112 records in the database. Latency still needs GNSS time.

---

## Slide 9: Hazard detection: twice as fast at the front (0:42, running 5:44)

Key number: 51 to 54 ms on the Pi 5 against 118 to 122 ms on the Pi 4.

Script:
The detector is a pretrained 8-bit SSD-MobileNet. On the Pi 4 with the whole system running it takes 118 to 122
milliseconds from sensor readout to result, at 14.6 frames per second. On the Pi 5 beside the dashboard it is 51 to 54
milliseconds at 19.2 frames per second, with no throttling. At 30 kilometres an hour that is about 0.6 metres less
travel before an alert. An alert needs three frames to raise and five to clear, and no frame is ever stored. My
pothole model works on a test image but is off by default.

If short on time (about 30 s):
The same detector takes about 120 milliseconds on the Pi 4 with the whole system, and 51 to 54 on the Pi 5 beside the
dashboard. Three frames to raise, five to clear, no frame stored. The pothole model is off by default.

Careful: Never say "alerts in 0.5 seconds" as alert latency. That was the time after opening the page with a person already in
view. The screen-side delay is not measured.

---

## Slide 10: Approaching objects: time to contact from box growth (0:44, running 6:28)

Key number: Within 2 percent in 40 synthetic tests; 0.27 ms per frame.

Script:
Distance bands say how near an object is, not whether it is coming closer. For an object closing at constant speed,
the inverse of its box width falls in a straight line to zero at contact. So time to contact is the width over its
rate of growth, after Lee in 1976, and it needs no focal length or object size. I fit that line robustly over the last
0.6 seconds, and warn below 4 seconds, immediate below 2. In 40 synthetic tests it is within 2 percent, at 0.27
milliseconds a frame. It has not been tested on a real approach.

If short on time (about 30 s):
Time to contact is the box width over its rate of growth, so it needs no calibration. Warning below 4 seconds,
immediate below 2. Synthetic tests within 2 percent; not yet tested on a real approach.

Careful: Do not claim the 261 road alerts marked approaching were correct; they have not been checked against video.

---

## Slide 11: Both cameras on the existing dashboard (0:38, running 7:06)

Key number: One page, Front | Rear switch; rear mirrored.

Script:
This is where RQ2 lands, on the dashboard the team already runs. The Surroundings page now has a Front and Rear
switch, which moves the picture, alerts, distances and hazards together, each from that side's own unit. The rear view
is mirrored like a reversing camera. The banner shows warnings from both sides, names the side, and puts an
approaching object first. It shows only live data, never a simulated value. It is tested offscreen and live on the Pi
5; glance time on the vehicle is still open.

If short on time (about 25 s):
Surroundings now switches between front and rear, the rear mirrored like a reversing camera, and the banner names the
side and puts approaching objects first. Tested offscreen and live on the Pi 5; glance time is open.

Careful: Do not say "reverse gear selects the rear" as a vehicle feature: there is no gear signal from the vehicle yet.

---

## Slide 12: On the vehicle: enclosures, heat and power (0:38, running 7:44)

Key number: About 20 W, 0.27 A from the 72 V pack; only the Pi 5 measured.

Script:
The enclosures were modelled from scripts in SOLIDWORKS, each checked for interference, fasteners and thin walls: a
display mount, a front pod for the Pi 5 and its AI HAT, and a screwless IMU pod. After the Pi 4 reached 76.9 degrees
in its closed box, both lids gained an exhaust grille under a rain hood. The power budget is about 20 watts, 0.27 amps
from the 72 volt pack, under one percent of the motor's rated input. Only the Pi 5 is measured; the rest are
estimates.

If short on time (about 25 s):
The enclosures were modelled from scripts and checked in CAD; the lids gained vents after 76.9 degrees in the closed
box. The power budget is about 20 watts, under one percent of the motor's rated input; only the Pi 5 is measured.

Careful: Only the rear box and a first IMU pod have been printed; say "checked in CAD" for the rest.

---

## Slide 13: First road session, 19 October (0:49, running 8:33)

Key number: 108.6 min recorded, about 16 min driving; 200 Hz with no drops, but a third of records lost on USB.

Script:
On the nineteenth of October the whole system was mounted and the first road session run. A recorder on the Pi 5
ran for 108.6 minutes, about 16 of them driving, with no laptop on board. Both IMUs held 200
hertz with no drops and one short stall, but a third of the per-second records were lost on the USB link, now replaced by wires, so R1 is only partly met on the vehicle. The battery link held under load: up to 46.9 amps, the pack falling
from 74.6 to 72.8 volts. The cameras raised 1,342 front and 741 rear alerts, not yet checked against video. But GNSS
had no fix, and there were no raw samples or run markers, so RQ1 and RQ4 are not answered yet. A second, shorter
session is planned.

If short on time (about 35 s):
On 19 October the whole system was mounted and driven: 108.6 minutes recorded on the Pi 5, about 16 of driving. The
IMUs held 200 hertz and the battery link held at up to 46.9 amps. No GNSS fix, raw samples or run markers, so RQ1 and
RQ4 wait for a second session.

Careful: Say "first road session", not "road test complete". Do not give a venue or route that is not in your own run sheet.

---

## Slide 14: Conclusions and next steps (0:35, running 9:08)

Key number: Detection about 50 ms at the front; nothing lost across an outage.

Script:
To conclude. Every subsystem runs together, now on the vehicle: two IMUs at 200 hertz, fused; a database that lost
nothing across an outage; detection in about 50 milliseconds at the front; an approaching-object warning; and both
cameras on the existing dashboard. What remains is the second road session with raw data and GNSS for RQ1 and RQ4, the
real approach test, glance time for RQ2, and a separate supply for the telemetry unit. Thank you, I'm happy to take
questions.

If short on time (about 20 s):
Every subsystem runs together, now on the vehicle. What remains is the second road session with raw data and GNSS, the
real approach test, glance time and a separate supply for the telemetry unit. Thank you, I'm happy to take questions.

---

## Before 16 November: update after the second road session

If the second, shorter session happens before the talk (raw stream with firmware v0.7.5, GNSS fix, timed runs,
powertrain baseline on stands), slides 3, 13 and 14 and this script must change: move any RQ1 or RQ4 result from
"open" to "tested", add the GNSS result for R4, and keep anything not measured marked as open. Rebuild with
build_deck.js so the notes and the talking points match, then re-time the script (it must stay under 10 minutes).
