# SW-7 road run 2: test plan and run sheet

Written 22 Oct 2026 (Workstream A). Item IDs (A1, B2, ...) refer to `Planning/run2-readiness/outstanding-register.md`, which holds each test's pass criterion, ground truth and analysis. This plan holds the session: who, what to bring, the gate before the day, the pre-checks, the minute-by-minute run sheet with the exact marker texts, the video ground truth and the checks after the run.

Run 1 (19 Oct) is the lesson: no markers, no raw samples, no GNSS antenna, no speed reference, a third of the per-second records lost on USB. Every step below exists to close one of those.

Date and venue are set by the student. The run does not go ahead until every bench-gate item has passed at least 2 days before (time to fix and re-test).

Update 24 Oct: the lab part (phase L) was done on 23 Oct (stand runs, IMU calibration in the mounted position; `Planning/run2-remaining-2026-10-26.md`). The road part (phase V) is on Monday 26 Oct on campus, about 2 hours, and was redesigned so that the data support valid statistics: three marked sections where the venue allows, counterbalanced speeds, 5 to 6 passes per speed per section, coasting passes at matched speed, bins along each section as the ICC rows, pothole and bump results as descriptive counts, and block V5 with a cardboard or mannequin target only. The analysis package was changed to match (`BenchTest/analysis`, 24 Oct).

## Changes of 25 Oct (lessons from the GPS tests of 24 to 25 Oct; these override the steps below where they differ)

1. Rear node GPS. Rear node runs v0.7.9 with publishing OFF (`!mqtt off`, kept after restarts), because failing MQTT reconnects starved the GPS polls (Report Appendix E). Power the rear node outdoors at least 10 min before the first pass, antenna seated on the GNSS connector and facing the sky, and confirm a 3D fix (P15) before the road phase. Only if the SIM has been checked and has data: send `!mqtt on`, then do P14.
2. Speed truth is the side video only. The phone's speed read zero in 251 of 716 fixes at walking pace, and the rear receiver reads up to 6.97 standing still. Every pass is timed on video between the section lines; no untimed passes. Phone and receiver speeds are compared against the video afterwards.
3. Stand runs at a held setting. On 23 Oct the current ramped from 2.7 to 5.9 A within one run, and the vibration followed it (r 0.80), so the runs could not show repeatability. The driver reaches the setting, holds it for 10 s, and only then is the start marker typed; the setting is called out and typed in the marker; the wheel is filmed at 240 frames/s.
4. Forward video. Phone 1 films forward on every pass and during V5, so detections can be checked against what was in view. Handled as decision D36: kept off git, faces and plates blurred before any copy is shown, only vehicles and objects labelled.
5. BMS against the meter. Key off (3 readings) and 30 s into each stand run (D1); this is the only step that turns R5 from partly met into met.
6. Dashboard speed. Before the road phase, check that the dash shows LIVE and a speed with the phone moving; the phone stays where it sees the sky. Deploy the speed fix first (phone speed kept when the Pi 4 drops out) if it is ready.
7. Pi 4 supply. A stronger supply for the Pi 4 and the rear node on its own supply (Saturday's two restarts were under-voltage).

## 1. Bench gate (before the day)

| Gate | Register items | Pass (summary; full criterion in the register) |
|---|---|---|
| G1 Regulated supply and 90-minute soak of v0.7.5 on both nodes, wired UART, recorder polling the Pi 4 | A2, A3, A4, D8, D9 | 0 resets, 0 queue drops, I2C counters 0, raw count within 0.5 % of 200 Hz, no missing DASH sequence, rear source answers at least 99.5 % of polls |
| G2 Run-1 flash log read out and checksummed (before anything can overwrite it) | A25 | Every index received, every record parses |
| G3 Six-position calibration of both IMUs | A7 | Residuals within the register's criterion |
| G4 Weighting, VDV and gravity projection verified on synthetic signals | A12 | Within 0.1 dB and 1 % of closed form |
| G5 chrony between the Pis and the 20-tap zero-delay test on a common plate | A20 | Offset at most 1 ms; tap delay median within 2 ms |
| G6 Outdoor session at the lab: fix through the fitted antenna, payload without position, latency dry run | A15, D6, D4 (dry run) | 3D fix; 0 of 100 payloads with a position; ingest on the laptop receives records |
| G7 Clock offset ESP32 to Pi 4 from edge logs | A18 | Residual at most 1 ms (95th percentile) |
| G8 Camera items | C4, C5, C6, C7, C8, C11, C2, C14 | As in the register |
| G9 Pack capacity from the BMS, power per unit, mechanical measurements, data index, T14 | D3, E1, E5, E9, E13 | As in the register |
| G10 Pothole path speed check on the Pi 5 (for C12) | C12 precondition | Detector within 10 % of its rate with the path on |

G1, G2 and G5 are blocking: without them the run cannot answer RQ1 or RQ4. G3, G4, G7 and G10 are needed for the analysis but not for collecting data; if one has not passed, the run can go ahead and the item is analysed after it. G8 and G9 do not depend on the run.

## 2. People and roles

| Role | Who | Duties |
|---|---|---|
| Investigator and observer | Samson (only investigator named in the approval) | Runs the session; writes every marker; keeps the paper run sheet with phone-clock times; tap slates; reads the meters; stops the session if a stop rule is met |
| Driver | Yusuf, or another team member licensed to ride it (operates the vehicle only; not measured) | Holds the target speed and line; follows the block instructions; stops at any signal from the marshal |
| Safety marshal and camera | A third team member | Second person at the key whenever 72 V is on (stands phase); keeps the venue clear; starts and checks the side phone; holds the slow-motion phone on the stands |

Minimum by the rules: two people whenever the 72 V system is energised (SW7-VIT-001 section 7, checklist section 0). With only two, the side phone runs unattended on its tripod and the observer acts as marshal; the road phase is then run with nobody else within the venue.

Ethics: no person is a subject; nobody's glances or behaviour are measured; no faces are filmed on purpose; any frame showing a bystander or a number plate is blurred before upload (Workstream E); the forward and side videos stay off git.

## 3. Equipment

Measurement: 30 m tape (or measuring wheel) and 5 m tape; 1 m straightedge and steel rule (obstacle depth and height); spirit level; 8 cones; chalk and masking tape; rubber mallet; pen for slates; CAT III multimeter with rated leads; DC clamp meter rated above 40 A; USB inline meter (5 A, PD capable); thermometer for ambient; luxmeter if available (else a phone app, marked indicative); grey card; stopwatch; reflective tape for the wheel mark.

Video: phone 1 (forward, on a handlebar mount, 60 frames/s); phone 2 (side, tripod, 60 frames/s); phone 3 or phone 2 again for slow motion on the stands (240 frames/s); power banks; at least 20 GB free on each phone.

Computers and links: laptop with charger, NTP-synchronised, ingest and the marker command ready; phone uplink for the laptop; Ethernet cable between the Pis tied down; spare cable; the run-2 supplies for every unit (regulated supply for the rear node from G1); spare fuses for the converter if used.

Safety: rated stands and chocks; insulated gloves; fire extinguisher suitable for lithium batteries; first-aid kit; cones for the exclusion area.

Paper: this run sheet printed; the register's [proposed] criteria as fixed by the student; the risk assessment.

## 4. Pre-checks on the day

Stop rule for the pre-checks: if any item marked blocking fails and cannot be fixed within 15 minutes, the road phase does not start; the stationary phase may still run.

| ID | Check | Pass | Blocking |
|---|---|---|---|
| P1 | Risk assessment signed and valid; supervisor told the date, venue and people | Yes | Yes |
| P2 | Stands rated and stable, chocks in place, extinguisher present, two people present | Yes | Yes (stands phase) |
| P3 | Every unit up: Pi 5 dashboard, Pi 4, rear node, front node | All up; uptimes written on the sheet | Yes |
| P4 | `python BenchTest/sw7_check.py` | `RESULT: READY`; warnings written down | Yes |
| P5 | Raw stream from both nodes, 60 s | 200 Hz within 0.5 %, 0 drops, I2C counters 0 | Yes |
| P6 | `chronyc tracking` on the Pi 4 | Offset at most 1 ms | Yes (for A21) |
| P7 | Recorder `sw7-roadlog` active; Ethernet carrier on both sides | All four sources 20 of 20 polls in 10 s | Yes |
| P8 | Marker path: write `R2 TEST marker` | Appears in the session file within 2 s | Yes |
| P9 | Raw-stream files on both Pis | Both growing | Yes |
| P10 | Sync pulse on the Pi 4 (`time gpiomon -c gpiochip0 -n 20 17 > /dev/null`) | About 10 s for 20 edges | No (A19 only) |
| P11 | BMS in the record | Voltage present, record under 3 s old | No (D1, D2, B2 coast check need it) |
| P12 | Supplies and flags | Pi 5 supply at least 5.0 V in powerwatch; `vcgencmd get_throttled` 0x0 on both Pis; rear node supply at least 4.75 V | Yes |
| P13 | Temperatures | Pi 4, Pi 5 and ambient written down | No |
| P14 | Laptop ingest subscribed; 10 payloads checked for position | Records arriving; 0 with a position | No (D4, D5 only) |
| P15 | Venue: GNSS 3D fix after the TTFF resets (A16) | Fix, satellites and HDOP written down | No (speed falls back to video) |
| P16 | Venue: laptop reaches the Pi 5 from the observer's position, with the trike at A70 | `ssh` answers | No (fallback: run sheet times, then markers added afterwards marked "via runsheet") |
| P17 | Course: sections A, R and B measured (phase V) | A: 50.00 m within 0.10 m by tape, cones at A-30, A-10, A0, A50, A70; R: start and end lines taped, length written down; B: bump height and length measured | Yes (A); R and B: no (minimum viable cut) |
| P18 | Side phone frames the A0 and A50 lines (or one phone per cone); a second phone for R and B if available | A 10 s test clip shows both lines of each filmed section | Yes for A (A14 ground truth and the ICC bins) |
| P19 | Battery state of charge | At least 50 % at the start of the road phase [proposed]; stop at 30 % | Yes |
| P20 | Venue clear, marshal in position | Yes | Yes |

## 5. Markers

The recorder on the Pi 5 appends every line of `/home/piadam/roadtest/roadtest_markers.txt` to the session file with the Pi time. From the laptop (Pi 5 address found in P16):

```
m() { ssh piadam@<pi5-address> "echo '$*' >> /home/piadam/roadtest/roadtest_markers.txt"; }
m R2 A v10 p1 start
```

Write the same text, with the phone-clock time, on the paper sheet for every marker. If the laptop cannot reach the Pi 5, write only the sheet; the markers are added after the run with the suffix `via runsheet`.

Marker grammar: `R2 <block> <condition> <repeat> <start|end>`; free notes as `R2 NOTE <text>`; any reset as `R2 RESET <unit>`; meter readings typed into the marker so that they are in the data file.

How the analysis reads them (`BenchTest/analysis/segment.py`): `start` opens a run and `end` (or `stop`) closes it; the block letter is the section (A smooth, R rough, B bump, P pothole); `coast` in the condition marks a coasting pass; `v10` is the target speed in km/h; `p1` or `r1` is the repeat; `STANDS` with `L`, `M`, `H` or `idle` is a stand run. Every other block (S0, TAP, SLATE, RECAL, V5, DISPLAY, R13, NOTE) is an event, never a road pass, and `R2 session ...` never opens a run. Type the start and end of each road pass as the front wheel reaches the section lines: without video for that section, the markers are the pass window.

## 6. Run sheet

Times are from the start of each phase. Durations of passes are estimates (about 2 min per pass for a 100 m run and the loop back); the counts of passes, not the clock, are what matter. Cut tiers: tier 1 is cut first if time runs short; tier 2 next; nothing marked keep is cut, because those steps carry RQ1 and RQ4.

### Phase L: lab, drive wheel raised on stands (72 min)

| Time | Step | Exact markers | Register items | Cut |
|---|---|---|---|---|
| 0:00 to 0:10 | Safety set-up: stands checked, chocks, extinguisher, exclusion area, second person | `R2 session start lab` | P1, P2 | keep |
| 0:10 to 0:25 | Power-up and pre-checks P3 to P14 | `R2 TEST marker` | P3 to P14 | keep |
| 0:25 to 0:35 | Measure: wheelbase (front axle to rear axle, tape, 3 readings), drive-wheel circumference (tape round the tyre, 3 readings), IMU positions from each axle, eye-to-screen distance from the seat; tape marks across every mount; photos of every mount | `R2 NOTE wheelbase <m> <m> <m>`, `R2 NOTE circumference <m> <m> <m>` | A21, B1, C15, E6, E11 | keep |
| 0:35 to 0:38 | S0: still, 72 V off, nobody touching the vehicle, 120 s | `R2 S0 still start`, `R2 S0 still end` | A9 | keep |
| 0:38 to 0:42 | Mallet strikes on the frame midway between the nodes, 10 strikes 3 s apart; then a tap slate (three pen taps on the handlebar stem next to the front pod) filmed by phone 1 and phone 2 | `R2 TAP frame start`, `R2 TAP frame end`, `R2 SLATE 0` | A21, A22 | keep |
| 0:42 to 0:46 | BMS voltage against the meter, key off, 3 readings 30 s apart | `R2 BMS keyoff m1 V=<meter>` (m2, m3) | D1 | keep |
| 0:46 to 0:49 | 72 V on (second person at the key); idle, wheel still, 60 s | `R2 STANDS idle r1 start`, `R2 STANDS idle r1 end` | B1 | keep |
| 0:49 to 1:07 | Stand runs, 60 s each, 60 s between, order L M H H M L L M H. At 30 s into each: meter voltage and clamp current typed as a marker; phone 3 films the wheel mark at 240 frames/s for 10 s | `R2 STANDS L r1 start`, `R2 STANDS L r1 meter V=<v> I=<a>`, `R2 STANDS L r1 end`; then M r1, H r1, H r2, M r2, L r2, L r3, M r3, H r3 | B1, D1, D2 | tier 2: drop the third repeat (L r3, M r3, H r3), saves 6 min |
| 1:07 to 1:12 | 72 V off; wheel down; stands away | `R2 STANDS done` | | keep |

Transfer to the venue: not in the budget; the recorder keeps running if the Pis stay powered, otherwise note the restart (`R2 RESET pi5`).

### Phase V: campus venue, vehicle on the ground, Monday 26 Oct (120 min; minimum viable cut below)

Revised 24 Oct so that the road data support valid statistics within about two hours. Why each change was made:

- One 50 m section gives no variation between road sections, so an ICC with sections as rows cannot be computed from it. The analysis now cuts each pass into 5 m bins between the section lines (10 bins on a 50 m section), with the bins as the ICC rows and the passes as the repeated measurements, and pools the bins of several sections at the same speed. It needs at least 5 rows and 3 passes. With fewer it reports "n too small for an ICC: CV only".
- Bins are only the same places on every pass if the pass windows are the crossings of the section lines. Those crossing times come from the side video (`crossings.csv`, section 8). Without video for a section, the analysis uses the markers and says so.
- Pothole and bump detection over well under 1 km with at most 5 events cannot give a false-alarm rate per km or an ROC. The analysis reports counts per pass (hits, misses, false alarms, bump flagged) with the distance driven, plus a threshold sweep, all labelled "descriptive, n = ...".
- The powertrain lines are at 40 to 70 Hz (stand runs, 23 Oct). RQ4 now uses 0.5 to 80 Hz. Lines are tracked as orders of the wheel rate when the pass speed (video), the drive-wheel circumference and the stand wheel rate are known. Otherwise the 23 Oct lines are used with plus or minus 1 Hz, which is valid only near the stand wheel speed.

Course (P17), if the venue allows: three distinct marked sections on campus.

| Section | Block letter | Surface | Length | Bins | Purpose |
|---|---|---|---|---|---|
| A | A | Smooth tar, straight, level | 50 m by tape (cones A-30, A-10, A0, A50, A70) | 10 x 5 m | RQ1 repeatability and speed dependence, RQ4 powered and coasting, false-alarm counts |
| R | R | Rough or patched tar or paving, straight | 30 to 50 m by tape (R0, R-end) | 6 to 10 x 5 m | Second, different surface: ICC pooled over A and R, roughness contrast |
| B | B | Speed bump, measured (height, length along the path) | 20 m with the bump in the middle | events | Bump counts (must not be called a pothole), front-to-rear delay |

Lay A and R one after the other on one straight if the campus has one, so each lap is one pass over each section. The bump (B) is driven separately, at 10 km/h only. If only one straight exists, R is dropped and the minimum viable cut applies. Side video: phone 2 frames the A0 and A50 lines; phone 3 (or phone 2 moved for that block) frames R and B. A section without video falls back to the markers.

| Time | Step | Exact markers | Register items | Cut |
|---|---|---|---|---|
| 0:00 to 0:15 | Set the course (P17): tape A, R and B, cones; measure the bump (height, length along the path, position) and any depression that meets the pothole definition; place the side phones (P18). Measure if not done: wheelbase (3 readings), drive-wheel circumference (3 readings, tape round the tyre), section lengths. TTFF: reset the rear node at 0:00 | `R2 session start venue`; `R2 GNSS reset 1`; `R2 NOTE bump height <mm> length <mm>`; `R2 NOTE wheelbase <m> <m> <m>`; `R2 NOTE circumference <m> <m> <m>`; `R2 NOTE length A <m> R <m>` | A16, A21, A24, B1, P15 to P20 | keep |
| 0:15 to 0:18 | S0: still, 60 s, vehicle level; slate 1 (tap slate) filmed by phone 1 and phone 2; start all recordings | `R2 S0 still start`, `R2 S0 still end`, `R2 SLATE 1` | A6, A9, A22, E10 | keep |
| 0:18 to 0:54 | Block A then R, powered, same line and direction, each lap one pass over A then one over R. Speeds (km/h) counterbalanced: 10 15 20 20 15 10 10 15 20 20 15 10 10 15 20 20 15 10 (18 laps, 6 per speed). Reach the target by A-30, hold it through the end of R, brake after it, loop back outside the sections. One forward-video map check in one lap | Per lap, typed as the front wheel reaches each line: `R2 A v10 p1 start` at A0, `R2 A v10 p1 end` at A50, `R2 R v10 p1 start` at R0, `R2 R v10 p1 end` at R-end. Repeat number counts per speed: v10 p1, v15 p1, v20 p1, v20 p2, v15 p2, v10 p2, ... v10 p6. A lap not steady: `R2 NOTE A v15 p3 not steady` and drive one more lap with the next repeat number | A1, A5, A8, A10, A11, A13, A14, A17, A23, A24 (false-alarm counts), C1, C12, D4, D5 | keep 5 laps per speed (15 laps, 30 min); tier 2: drop the sixth lap of each speed, saves 6 min |
| 0:54 to 1:06 | Block C, coasting on A, at matched speed: reach 20 km/h by A-30, release the throttle at A-10, coast through A50, brake after A70 (6 passes). The analysis compares each coasting pass with the powered passes on A whose mean speed is within 1 km/h, so the 15 and 20 km/h powered passes give the match. If the campus has a gentle downhill on A, coast there and the speed holds better | `R2 A coast p1 start` at A0, `R2 A coast p1 end` at A50 (p1 to p6) | B2, B3 | keep 4 passes; tier 2: drop p5 and p6, saves 4 min |
| 1:06 to 1:18 | Block B, speed bump: 6 passes at 10 km/h, same line, front wheel over the middle of the bump | `R2 B v10 p1 start` 10 m before the bump, `R2 B v10 p1 end` 10 m after it (p1 to p6) | A5, A21, A24 | keep 5 passes |
| 1:18 to 1:26 | Block P, pothole: 5 passes at 10 km/h, front wheel through the depression. Only if one meets the definition (25 mm deep, 150 mm across), and only at a speed the driver judges safe | `R2 P v10 p1 start`, `R2 P v10 p1 end` (p1 to p5) | A24, C12 | tier 1 |
| 1:26 to 1:31 | Block V5: walking pace towards a parked object, then towards a cardboard box or shop mannequin standing 10 m ahead in place of a person (driver stops by 5 m). Never a person as the target | `R2 V5 object start`, `R2 V5 object end`, `R2 V5 target start`, `R2 V5 target end` | C10 | tier 1 |
| 1:31 to 1:34 | S0c: still, 60 s; slate 2; stop the phones | `R2 S0c still start`, `R2 S0c still end`, `R2 SLATE 2`, `R2 session end venue` | A6 (end-of-session drift), A9, A22 | keep |
| 1:34 to 2:00 | Margin for repeated laps, a reset, or the stands if the hoist is free (L M H H M L, 60 s each, meter and clamp at 30 s, 240 frames/s video of the wheel mark for the wheel rate, which the order tracking needs) | `R2 STANDS L r1 start`, `R2 STANDS L r1 meter V=<v> I=<a>`, `R2 STANDS L r1 end`, ... | B1, D1, D2 | first to go |

The display photos (C15) move to a sunny day at the lab.

Stop rules during the road phase: any unit or cable loose, smell or heat, an IMU at 0 Hz (stop, check, reset, keep still 10 s, `R2 RESET <unit>`, repeat the pass), state of charge at 30 %, anyone entering the area, or the driver's call. A repeated pass gets the next repeat number; the aborted one is kept and noted.

What the full venue phase gives, and the statistics it supports:

| Question | Data | Statistic (as the analysis reports it) |
|---|---|---|
| RQ1 repeatability | A and R, 6 passes at each of 3 speeds | CV of per-pass a_w per section and speed with bootstrap 95 % CI (n = 6); ICC(2,1) with 10 bins (A) or 6 to 10 bins (R) as rows and 6 passes as columns, and pooled over A and R (16 to 20 rows), with the McGraw and Wong CI, stated as optimistic because neighbouring bins are not independent |
| Speed dependence (A13) | 3 speeds x 6 passes per section, video speed | log-log slope of sigma^2 and a_w on v with its CI |
| RQ4 | Powered passes at 3 speeds, 6 coasting passes, stand lines of 23 Oct (and Monday's if the stands are done) | Line energy as a share of the 0.5 to 80 Hz band per pass, by order tracking when the circumference and stand wheel rate are known; coasting against powered at matched speed in dB per band |
| Potholes and bumps | 6 bump passes, up to 5 pothole passes, about 1.8 km on A and R | Counts per pass and in total, with the distance; threshold sweep; "descriptive, n = ..."; no false-alarm rate per km |

### Minimum viable cut (about 60 min at the venue)

If time, the venue or the battery allow only one section: section A and the bump only.

| Step | Passes | Time |
|---|---|---|
| Course A and B, circumference, wheelbase, phones | | 15 min |
| S0 still and slate 1 | | 3 min |
| Block A powered, 10 and 20 km/h counterbalanced: 10 20 20 10 10 20 20 10 10 20 | 5 per speed | 20 min |
| Block C coasting from 20 km/h | 4 | 8 min |
| Block B bump at 10 km/h | 5 | 8 min |
| Block V5 with the cardboard target (if 5 min remain) | 2 | 5 min |
| S0c still, slate 2 | | 3 min |

What the minimum still answers: RQ1 repeatability on one surface (CV per speed with n = 5; bin ICC with 10 rows x 5 passes per speed), speed dependence from two speeds (slope only, no check of the shape), RQ4 lines and coasting against powered at the passes' mean speeds, bump counts (descriptive, n = 5), front-to-rear delay on 5 bump passes, GNSS speed against video. What it loses: the second surface (no pooled ICC, no roughness contrast), 15 km/h, the pothole block and C10 if V5 is cut.

### Phase R: back at the lab (55 min)

| Time | Step | Exact markers | Register items | Cut |
|---|---|---|---|---|
| 0:00 to 0:05 | Inspect every mount against its tape mark; photos | `R2 NOTE mounts <result>` | E6 | keep |
| 0:05 to 0:25 | Removal timed: stopwatch from the first cut tie to the vehicle matching the "standard" photo list, checked by the second person | `R2 R13 removal start`, `R2 R13 removal end` (written before the recorder is stopped by the removal) | E4 | keep |
| 0:25 to 0:55 | Data copy and post-run checks (section 8) | | all | keep |

### Time budget

| Plan | Lab | Venue | Back at the lab | Total (excluding transfer) |
|---|---|---|---|---|
| Lab part (done 23 Oct) | 72 min | | | |
| Monday full (A and R 18 laps, 6 coast, 6 bump, P, V5, margin) | | 120 min | 55 min | 2 h 55 min |
| Monday tier 1 and 2 cut (A and R 15 laps, 4 coast, 5 bump, no P or V5) | | 70 min | 55 min | 2 h 5 min |
| Monday minimum viable cut (A and B only) | | 57 to 62 min | 55 min | about 2 h |

What the tier 1 and 2 cut still answers: RQ1 repeatability on two surfaces (CV per section and speed with n = 5, bin ICC per section and pooled over A and R), speed dependence at 10, 15 and 20 km/h counterbalanced, RQ4 (powered passes, 4 coasting passes at matched speed, the 23 Oct stand lines), front-to-rear delay (5 bump passes), bump counts, GNSS speed against video, R13. What it loses: C10, C12 at a pothole, C15 on the day (done later at the lab), and some precision in A11 and A21. The minimum viable cut is given under phase V.

## 7. Video ground truth

| Video | Where | Settings | Used for | Alignment |
|---|---|---|---|---|
| Side | Tripod far enough back to frame the A0 and A50 lines (about 60 m for a 50 m section with a normal phone lens); if the venue does not allow it, one phone at each cone line, both filming a common flash at the start and end of each block. A second phone for R and B if available | 60 frames/s, landscape, fixed focus and exposure | Speed over the measured section (A14); the crossing times of the section lines, which are the pass windows and fix the 5 m bins for the ICC (A11); obstacle crossing times (A24) | Front wheel at a cone line, frame counted; slates; written to `crossings.csv` and `labels.csv` (section 8) |
| Forward | Handlebar mount, looking ahead at the road | 60 frames/s | Journey evidence (E10), event context (A24, C12), map check (A17) | Tap slate in view at the start and end of each block |
| Wheel | Handheld beside the raised wheel, reflective mark in view | 240 frames/s, 10 s per stand run | Wheel rpm on the stands (B1) | Marker typed at the start of each clip |

Names after the run: `R2_<phase>_<block>_<camera>_<n>.mp4` (for example `R2_V_A_side_1.mp4`), with SHA-256 in the data index (Workstream B). Originals stay off git.

## 8. Post-run data checks (same day)

| Check | Pass | If it fails |
|---|---|---|
| Recorder session file(s) from both phases present; size and row count written down | Rows from `R2 session start lab` to `R2 session end venue`; rear and front sources answered at least 99 % of polls (D9) | Note the gap and its time; the raw-stream files still hold the IMU data |
| Markers | Every planned start has an end; count matches the run sheet; text matches the grammar | Add missing ones from the paper sheet with `via runsheet` |
| Raw streams from both nodes copied | Sample count per node within 0.5 % of 200 x recorded seconds; queue drops 0; I2C counters reported | Note; A1 reports the loss |
| GNSS | Fix in at least 95 % of driving seconds (A17) | Speed from video only |
| BMS | A record each second while driving; current present in every coast pass | Coast passes without current are not usable for B2 |
| Alert logs | `~/alerts_live.jsonl` copied from both Pis; line counts written down | |
| Flash log | Read back with `python BenchTest/log_dump.py` until complete; parses; sequence continuous; then cleared only after checksumming | Repeat the dump |
| Database | `Server/sync_report.py`: missing, duplicates, backfilled (D5) | Backfill from the flash log and report separately |
| Videos | Every block has a side and a forward file, both slates visible | List missing blocks |
| Power and temperature logs | Pi 5 powerwatch and the Pi 4 logger copied; maximum temperature and any throttling flag written down (E3) | |
| Checksums and backup | SHA-256 of every file; copy to OneDrive; run `tools/build_data_index.py` (E9) | Do not delete anything from the Pis until the copy is verified |
| Quick look | The analysis pipeline runs on the session without hand steps and finds every pass from the markers and from the GNSS crossings (A23); `summary.json` lists every run with its section, kind, speed and repeat, and nothing important is under "skipped" | Fix the segmentation before any result is reported |
| Analysis inputs | In the session folder: `session.json` with `wheelbase_m`, `wheel_circumference_m`, `section_lengths_m` (for example `{"A": 50.0, "R": 40.0}`) and, if the stands were run with the wheel video, `stand_wheel_hz` (for example `{"L": 3.1}`, rev/s); `crossings.csv` (`run,t_in,t_out`, Pi epoch seconds of the front wheel at the start and end lines, from the side video via the slates; `run` exactly as the marker name, for example `R2 A v10 p1`); `labels.csv` (`time,type`, with types `pothole` and `speed bump`) | Without `crossings.csv` the pass windows are the markers and the output says so; without the circumference or the stand wheel rate, RQ4 uses the fixed 23 Oct lines and says so |
| Run the analysis | `python -m pytest BenchTest/analysis/tests -q`, then `python -m BenchTest.analysis.run --session BenchTest/logs/<session folder> --out BenchTest/logs/<session folder>/analysis` from the repository root | Read `summary.json`: "skipped", "notes", "bands", the ICC "status" lines and the pothole "wording" before quoting any number |
| Lab notebook | Entry in `Planning/lab-notebook.md`: what was done, measured, where the files are | |
