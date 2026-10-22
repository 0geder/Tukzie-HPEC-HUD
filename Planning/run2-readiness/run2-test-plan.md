# SW-7 road run 2: test plan and run sheet

Written 22 Oct 2026 (Workstream A). Item IDs (A1, B2, ...) refer to `Planning/run2-readiness/outstanding-register.md`, which holds each test's pass criterion, ground truth and analysis. This plan holds the session: who, what to bring, the gate before the day, the pre-checks, the minute-by-minute run sheet with the exact marker texts, the video ground truth and the checks after the run.

Run 1 (19 Oct) is the lesson: no markers, no raw samples, no GNSS antenna, no speed reference, a third of the per-second records lost on USB. Every step below exists to close one of those.

Date and venue are set by the student. The run does not go ahead until every bench-gate item has passed at least 2 days before (time to fix and re-test).

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
| P17 | Course: A0 to A50 measured | 50.00 m within 0.10 m by tape; cones at A-30, A-10, A0, A50, A70; bump measured | Yes |
| P18 | Side phone frames the A0 and A50 lines (or one phone per cone) | A 10 s test clip shows both lines | Yes (A14 ground truth) |
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

### Phase V: venue, vehicle on the ground (120 min, 95 min after tier 1, 79 min after tier 2)

| Time | Step | Exact markers | Register items | Cut |
|---|---|---|---|---|
| 0:00 to 0:15 | Set the course (P17); measure the bump (height, length along the path, position) and any depression that meets the pothole definition (depth with straightedge and rule, width); side phone placed (P18). Meanwhile TTFF: reset the rear node at 0:00, 0:05 and 0:10 | `R2 GNSS reset 1` (2, 3); `R2 NOTE bump height <mm> length <mm>`; `R2 NOTE pothole depth <mm> width <mm>` if one exists | A16, A24, P15 to P20 | keep (TTFF tier 1: one reset instead of three) |
| 0:15 to 0:20 | Recalibration of both nodes in the mounted position, vehicle level and still, then 60 s still | `R2 RECAL front start`, `R2 RECAL front end`, `R2 RECAL rear start`, `R2 RECAL rear end`, `R2 S0b still start`, `R2 S0b still end` | A6 | keep |
| 0:20 to 0:23 | Slate 1: tap slate filmed by phone 1 and phone 2; start both recordings | `R2 SLATE 1` | A22, E10 | keep |
| 0:23 to 0:59 | Block A, powered, section A, same line and direction. Order of speeds (km/h): 10, 15, 20, 20, 15, 10, three times (18 passes). Reach the target by A-30, hold it to A50, brake after A70, loop back outside the section. One forward-video screen check of the map during one pass | For each pass: `R2 A v10 p1 start` when leaving A-30, `R2 A v10 p1 end` after stopping beyond A70. Sequence: v10 p1, v15 p1, v20 p1, v20 p2, v15 p2, v10 p2, v10 p3, v15 p3, v20 p3, v20 p4, v15 p4, v10 p4, v10 p5, v15 p5, v20 p5, v20 p6, v15 p6, v10 p6. A pass not steady: `R2 NOTE A v15 p3 not steady` | A1, A5, A8, A11, A13, A14, A17, A23, A24 (false alarms), C1, C12, D4, D5 | keep; tier 2: five passes per speed (drop p6 of each speed), saves 6 min |
| 0:59 to 1:11 | Block C, coast: reach 20 km/h by A-30, release the throttle at A-10, coast through A50, brake after A70 (6 passes) | `R2 A coast p1 start`, `R2 A coast p1 end` (p1 to p6) | B2, B3 | keep |
| 1:11 to 1:31 | Block B, speed bump: 5 passes at 10 km/h, then 5 at 15 km/h, same line | `R2 B v10 p1 start`, `R2 B v10 p1 end` (p1 to p5), then `R2 B v15 p1 start` ... `R2 B v15 p5 end` | A5, A21, A24 | keep 10 km/h; tier 2: drop 15 km/h, saves 10 min (A21 then on 5 passes) |
| 1:31 to 1:41 | Block P, pothole: 5 passes at 10 km/h, front wheel through the depression. Only if one meets the definition (25 mm deep, 150 mm across), and only at a speed the driver judges safe | `R2 P v10 p1 start`, `R2 P v10 p1 end` (p1 to p5) | A24, C12 | tier 1 |
| 1:41 to 1:46 | Block V5: walking pace towards a parked object, then towards the author standing 10 m ahead (driver stops by 5 m) | `R2 V5 object start`, `R2 V5 object end`, `R2 V5 person start`, `R2 V5 person end` | C10 | tier 1 |
| 1:46 to 1:56 | Display: photos from the eye point in sun and in shade, 4 pages x 3 photos, grey card in view; illuminance | `R2 DISPLAY sun start`, `R2 DISPLAY sun end`, `R2 DISPLAY shade start`, `R2 DISPLAY shade end` | C15 | tier 1 (move to a sunny day at the lab) |
| 1:56 to 2:00 | S0c: still, 60 s; slate 2; stop the phones | `R2 S0c still start`, `R2 S0c still end`, `R2 SLATE 2`, `R2 session end venue` | A6 (end-of-session drift), A9, A22 | keep |

Stop rules during the road phase: any unit or cable loose, smell or heat, an IMU at 0 Hz (stop, check, reset, keep still 10 s, `R2 RESET <unit>`, repeat the pass), state of charge at 30 %, anyone entering the area, or the driver's call. A repeated pass gets the next repeat number; the aborted one is kept and noted.

### Phase R: back at the lab (55 min)

| Time | Step | Exact markers | Register items | Cut |
|---|---|---|---|---|
| 0:00 to 0:05 | Inspect every mount against its tape mark; photos | `R2 NOTE mounts <result>` | E6 | keep |
| 0:05 to 0:25 | Removal timed: stopwatch from the first cut tie to the vehicle matching the "standard" photo list, checked by the second person | `R2 R13 removal start`, `R2 R13 removal end` (written before the recorder is stopped by the removal) | E4 | keep |
| 0:25 to 0:55 | Data copy and post-run checks (section 8) | | all | keep |

### Time budget

| Plan | Lab | Venue | Back at the lab | Total (excluding transfer) |
|---|---|---|---|---|
| Full | 72 min | 120 min | 55 min | 4 h 7 min |
| Tier 1 cut (P, V5, display, two TTFF resets) | 72 min | 95 min | 55 min | 3 h 42 min |
| Tier 1 and 2 cut (minimum) | 66 min | 79 min | 55 min | 3 h 20 min |

What the minimum still answers: RQ1 repeatability and speed dependence (5 passes at each of 10, 15 and 20 km/h, counterbalanced), RQ4 (two repeats of each stand setting, 6 coast passes, the powered passes), front-to-rear delay (5 bump passes), GNSS speed against video, BMS against the meter, R1 and R2 on the vehicle, R13. What it loses: C10, C12 at a pothole, C15 on the day (done later at the lab), and some precision in A11 and A21.

## 7. Video ground truth

| Video | Where | Settings | Used for | Alignment |
|---|---|---|---|---|
| Side | Tripod far enough back to frame the A0 and A50 lines (about 60 m for a 50 m section with a normal phone lens); if the venue does not allow it, one phone at each cone line, both filming a common flash at the start and end of each block | 60 frames/s, landscape, fixed focus and exposure | Speed over the measured section (A14), pass boundaries (A11, A23), obstacle crossing times (A24) | Front wheel at a cone line, frame counted; slates |
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
| Quick look | The analysis pipeline runs on the session without hand steps and finds every pass from the markers and from the GNSS crossings (A23) | Fix the segmentation before any result is reported |
| Lab notebook | Entry in `Planning/lab-notebook.md`: what was done, measured, where the files are | |
