# SW7 final presentation: speaker script

Word-for-word talk for the 16 to 17 November presentation, slide by slide. The full script is the same text as the
speaker notes in SW7_Final_Presentation.pptx (and SW7_Talking_Points.md, generated from build_deck.js). If you change
a sentence here, change it in build_deck.js too, or the two drift apart.

Length: 1,349 words. At about 140 words a minute that is 9 minutes 37 seconds of speaking. Slide changes and short
pauses add a few seconds each, so expect to finish close to 9:50 at a calm pace. Under 10 minutes is the rule. If you
are behind, use the 30-second cuts below; each cut saves 10 to 30 seconds.

Checkpoints: be on slide 7 by 4:10, on slide 10 by 7:05, on slide 12 by 9:00. If you reach slide 10 later than
7:20, use the cuts for slides 10 and 11.

How to read it: say each number slowly and once. Pause for a breath after each slide title. Where the script says
"here is one in full" or "the main new result", slow down; those are the parts the examiners will remember.

Status words used on the slides: tested (measured on the hardware), tested offscreen (automated tests without the
real touchscreen or vehicle), off by default or in progress (built, no result to claim).

| Slide | Title | Words | Target | Running total |
|---|---|---|---|---|
| 1 | Title | 67 | 0:29 | 0:29 |
| 2 | Why this matters | 92 | 0:39 | 1:08 |
| 3 | Aim and research questions | 120 | 0:51 | 1:59 |
| 4 | The system on the bench | 107 | 0:46 | 2:45 |
| 5 | Firmware | 114 | 0:49 | 3:34 |
| 6 | Approach | 77 | 0:33 | 4:07 |
| 7 | 200 Hz acquisition and fusion | 128 | 0:55 | 5:02 |
| 8 | Seven fault investigations | 141 | 1:00 | 6:02 |
| 9 | Timing, position, outage test | 141 | 1:00 | 7:02 |
| 10 | Camera and distance sensing | 139 | 1:00 | 8:02 |
| 11 | Dashboard | 131 | 0:56 | 8:58 |
| 12 | Conclusions | 92 | 0:39 | 9:37 |

---

## Slide 1: Title (0:29, running 0:29)

Key number: 72 volt trike.

Script:
Good morning. I'm Samson Okuthe, and my project is SW-7, supervised by Associate Professor Simon Winberg with
Sampath Jayalath as co-supervisor. It is part of TUKZIE, a 72 volt electric cargo trike for last-mile freight. I
built its on-board electronics: a telemetry unit that measures how the trike rides and sends the data to a central
database, and safety alerts on the dashboard the trike already has.

If short on time (about 20 s):
Good morning. I'm Samson Okuthe, project SW-7, supervised by Associate Professor Simon Winberg. I built the on-board
electronics for TUKZIE, a 72 volt electric cargo trike: a telemetry unit that measures the ride and sends it to a
central database, and safety alerts on the trike's existing dashboard.

---

## Slide 2: Why this matters (0:39, running 1:08)

Key number: 2 seconds (longest single glance, NHTSA).

Script:
First, electric trikes make economic sense for freight in African cities. On delivery routes studied in Dar es
Salaam, an electric cargo tricycle cut the operating cost per kilometre by 45.5 percent against a motorcycle, and by
up to 86 percent against a light car. Second, anything that takes the driver's eyes off the road is a risk. NHTSA
guidance limits a single glance to two seconds. So the open problem is to combine edge telemetry with short,
safety-only driver information on a low-cost trike, and to measure whether each part works.

If short on time (30 s):
Electric cargo trikes cut operating cost per kilometre by 45.5 percent against a motorcycle on routes in Dar es
Salaam. But anything that takes the driver's eyes off the road is a risk: NHTSA allows two seconds per glance. The
problem is to combine edge telemetry with short, safety-only driver information on a low-cost trike, and to measure
each part.

---

## Slide 3: Aim and research questions (0:51, running 1:59)

Key number: four research questions; only RQ3's loss and recovery is fully tested.

Script:
These are my four research questions, and where each one honestly stands. RQ1 asks how accurately and repeatably a
low-cost unit can characterise the trike's ride. The instrument is verified on the bench; repeatability on the
vehicle is not measured yet. RQ2 asks how to show safety alerts on the existing dashboard with the least
distraction. It moved from a head-up display to that dashboard with my supervisor's agreement, because a second
screen adds distraction. Glance time is not measured yet. RQ3 asks about latency, data loss and recovery. Loss and
recovery now pass a ten-minute outage test; end-to-end latency still needs GNSS time outdoors. RQ4, separating road
from powertrain vibration, has passed self-tests only, because it needs road data.

If short on time (30 s):
Four research questions. RQ1, ride characterisation: the instrument is verified, repeatability on the vehicle is
not. RQ2, alerts on the existing dashboard rather than a head-up display, agreed with my supervisor: built, glance
time not measured. RQ3: loss and recovery pass a ten-minute outage test, latency is still open. RQ4: self-tests only,
it needs road data.

---

## Slide 4: The system on the bench (0:46, running 2:45)

Key number: 200 Hz on each of two IMUs.

Script:
This is the system on the bench. The telemetry unit is an ESP32-S3 with a built-in LTE modem that also gives GNSS.
It samples two MPU6050 IMUs at 200 hertz each, reads the battery over Bluetooth, and has a hardware counter for the
motor's Hall sensor. Every record goes to a local log and over LTE to a central database on the team's Pi 5. A
Raspberry Pi 4 runs the camera detector and three time-of-flight distance sensors. One wire links the boards: the
ESP32 pulses it every half second and the Pi logs each edge, so camera and IMU data can be lined up in time.

If short on time (30 s):
The telemetry unit is an ESP32-S3 with LTE and GNSS. It samples two IMUs at 200 hertz, reads the battery over
Bluetooth, logs locally and sends every record to a database on the team's Pi 5. A Pi 4 runs the camera and three
distance sensors, and one sync wire lines up camera and IMU time.

---

## Slide 5: Firmware (0:49, running 3:34)

Key number: 5 ms fixed period per IMU task (and 94 Hz filter in v0.7.4).

Script:
The firmware runs on FreeRTOS across the two cores. Core 1 holds the timing-critical work: one task per IMU at the
highest priority, each on a fixed 5 millisecond period. They never print or block: each sample is time-stamped and
pushed into a bounded queue, and if it is full the sample is dropped and counted. Core 0 does the blocking work: the
modem, GNSS, MQTT and the flash log, in one task because the modem's serial line has no lock. Version 0.7.4, flashed
in October, gives every record a sequence number, replays the backlog after an outage, and moves the IMU filter from
260 to 94 hertz, against aliasing at 200 hertz sampling.

If short on time (30 s):
Core 1 runs one task per IMU at top priority on a fixed 5 millisecond period; they never block, and a full queue
drops and counts a sample. Core 0 does the modem, MQTT and the log. Version 0.7.4 adds sequence numbers and backlog
replay, and moves the IMU filter to 94 hertz against aliasing.

---

## Slide 6: Approach (0:33, running 4:07)

Key number: 5 stages; stages 1 to 4 done on the bench.

Script:
My method was staged verification. Each interface was brought up alone on the real board, against a pass criterion
written before the test. Then both IMUs at 200 hertz, calibrated; then the ride features and fusion, each
self-tested at boot; then the log, the LTE publish and the replay to the database. The last stage, the moving
vehicle, is drawn dashed. This order is why the faults I'll show next could each be traced to one change.

If short on time (20 s):
Staged verification: each stage tested against a pass criterion written in advance before the next was built on it.
Four stages are done on the bench; the vehicle is the fifth. That is why each fault could be traced to one change.

---

## Slide 7: 200 Hz acquisition and dual-IMU fusion (0:55, running 5:02)

Key number: 149 of 149 windows fused, under 1 ms skew.

Script:
First results. Both IMUs run at 200 hertz with no dropped samples, counted, not assumed. Flash writes cause gaps of
33 to 40 milliseconds, now once a minute, and the queue holds the samples through each one. Uncalibrated, the two
accelerometers read about 8 percent apart in an earlier session. A factor per sensor against gravity brings both to
9.80 or 9.81 at calibration, but it only holds in that orientation, so it will be redone once mounted. With equal
noise, inverse-variance fusion reduces to the mean. Windows are paired only if they end within half a window, the
disagreement is reported, and if one sensor goes silent the other takes over. In a 150 second session all 149
windows were fused with under a millisecond of skew.

If short on time (30 s):
Both IMUs run at 200 hertz with no dropped samples; flash writes cause short gaps, now once a minute. A gravity
calibration brings both sensors to 9.8, but only in that orientation, so it is redone once mounted. Fusion is an
equal-weight mean with the disagreement reported: 149 of 149 windows fused, under a millisecond of skew.

Careful: do not say "8 percent reduced to noise". The 8 percent came from an earlier session than the calibration.

---

## Slide 8: Seven fault investigations (1:00, running 6:02)

Key number: under-voltage 14 s after the modem came up; 3 restarts in 20 minutes, then none in 4 hours.

Script:
The report works through seven faults that needed a real diagnosis: symptom, candidate causes, deciding test, and
fix. Here is one in full. The Raspberry Pi 4 kept throttling and rebooting. It could have been its own supply, the
distance-sensor board, the telemetry unit on its USB port, or heat. A logger recorded the power flags every two
seconds. With nothing attached, the flags were clear. Fourteen seconds after the telemetry unit was plugged in, when
its modem came up, under-voltage began. With the unit on the Pi, there were three restarts in twenty minutes; moved
off the Pi, none in four hours. The others follow the same pattern, from a GNSS reply in an unexpected layout to a
battery checksum off by exactly three. The outage test found an eighth: a broker setting that silently stopped
delivery to the database.

If short on time (30 s):
Seven faults needed a real diagnosis. One example: the Pi 4 kept rebooting. Logging its power flags every two
seconds showed under-voltage starting 14 seconds after the telemetry unit's modem came up on its USB port. Moved off
the Pi, no restarts in four hours. The others, from GNSS to the battery checksum, were found and fixed the same way.

---

## Slide 9: Timing, position, and no data lost in an outage (1:00, running 7:02)

Key number: 112 of 112 records stored after a 10-minute outage.

Script:
Timing first: over 121 sync edges the median interval was 500.06 milliseconds with a spread under 0.7, so camera and
IMU clocks line up precisely. Position: on a rooftop, 104 fixes were a median of 2.7 metres from a phone, and indoors
the modem gives a network position stated to 550 metres. The main new result is the outage test. With version 0.7.4
I switched the radio off for ten minutes. The unit built up 60 records, reconnected 5.2 seconds after the radio came
back, and cleared the backlog in about 40 seconds. The database on the Pi 5 holds 112 of 112 records, and 111 of 111
against the unit's own log, so nothing was lost. Two limits: the public test broker does not queue, so reading the
log back is the safety net, and latency needs GNSS time outdoors.

If short on time (30 s):
The sync wire gives a 500.06 millisecond interval with under 0.7 of spread, and GNSS is 2.7 metres from a phone.
The new result: I switched the radio off for ten minutes. The unit reconnected in 5.2 seconds, cleared 60 records in
about 40, and the database holds 112 of 112. Latency still needs GNSS time outdoors.

---

## Slide 10: Camera hazard detection and distance sensing (1:00, running 8:02)

Key number: about 120 ms at 14.6 fps in the full system (102 ms at 19.5 fps detector alone).

Script:
The camera's role grew, on supervisor direction, from a visual record to hazard awareness. I designed and 3D printed
this casing. The live detector is a pretrained 8-bit SSD-MobileNet. On its own it ran at 19.5 frames per second, 102
milliseconds from sensor to result. With everything else running on a healthy Pi 4 it is 14.6 frames per second and
about 120 milliseconds, and that is the figure for the system. An alert needs three frames to raise and five empty
frames to clear, and no frame is stored. COCO has no potholes, so I trained my own model: 0.71 mAP at 50 on
validation tiles. On the Pi it finds the pothole in a test image at confidence 0.63, but only one run every four
seconds fits beside the main detector, so it is off by default.

If short on time (30 s):
The detector is a pretrained SSD-MobileNet: about 120 milliseconds at 14.6 frames per second with the full system
running. Alerts need three frames to raise and five to clear, and no frame is stored. My pothole model works on a
test image, but only one run every four seconds fits beside the main detector, so it is off by default.

Careful: never say "alerts in 0.5 seconds" as alert latency. That was the time after opening the page with a person
already in view.

---

## Slide 11: Hazard alerts and navigation on the existing dashboard (0:56, running 8:58)

Key number: offline search matches in under 20 ms; Photon 1.1 to 1.4 s on the Pi 5.

Script:
This is where RQ2 lands: my pages on the dashboard the team already runs, the default at boot on their Pi 5. It
shows only real values, with a chip that always reads LIVE, REPLAY, NO DATA or SIMULATED. On the left, the Sensors
page shows the distance gauges and fused hazards. An immediate hazard now shows as a red pill in the status bar, so
it no longer covers the page. In the middle is navigation with spoken directions, in a simulated drive that is
clearly marked. On the right is the new destination search: offline matches in under 20 milliseconds, and online
suggestions in just over a second on the Pi. Pages change with a two-finger swipe. These are tested offscreen; glance
time on the vehicle is still open.

If short on time (30 s):
My pages run on the team's dashboard, the default at boot on their Pi 5, showing only real values with a LIVE or
SIMULATED chip. Sensors and hazards on the left, navigation with spoken directions in the middle, and the new
destination search on the right. Tested offscreen; glance time on the vehicle is still open.

---

## Slide 12: Conclusions and next steps (0:39, running 9:37)

Key number: nothing lost across a 10-minute outage.

Script:
To conclude. Every subsystem runs together on the target hardware: two IMUs at 200 hertz, calibrated and fused;
GNSS within about 3 metres; the battery over Bluetooth; a full local log; and now a central database that lost
nothing across a ten-minute outage. Camera detection takes about 120 milliseconds in the full system, and hazards,
navigation and search run on the existing dashboard. What remains is the vehicle: end-to-end latency with GNSS time,
repeatability for RQ1, road data for RQ4, and glance time for RQ2. Thank you, I'm happy to take questions.

If short on time (25 s):
Every subsystem runs together on the target hardware, and the database lost nothing across a ten-minute outage.
What remains is the vehicle: latency with GNSS time, repeatability, road data and glance time. Thank you, I'm happy
to take questions.

---

## Before 16 November: update after the road test

The road test was planned for 14 October, before this talk. If it happens, slides 3, 6, 9 and 12 and this script
must change: replace "planned 14 October" with what was measured, and move any RQ1, RQ3 or RQ4 result from "open" to
"tested". Rebuild with build_deck.js so the notes and the talking points match, then re-time the script.
