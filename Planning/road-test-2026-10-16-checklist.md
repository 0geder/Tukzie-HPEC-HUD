# SW-7 road test, 16 October 2026: checklist and run sheet

Goal: collect the vehicle data the report is waiting for (RQ1 to RQ4, R1 to R13) in one session, and close the testing phase.
Tick each box. Write every run on the run sheet at the end. If a step fails, write what happened and carry on with the next run;
a recorded failure is still a result.

## 0. Before leaving the lab (go / no-go)

Safety and ethics (EBE/03305/2026, approved with conditions):
- [ ] Physical risk assessment signed by the lab owner (condition of the ethics approval). No signature, no driving.
- [ ] Supervisor (Prof. Winberg) knows the test is today, where, and who is there.
- [ ] Venue is a closed area (parking area or field), not a public road. Venue name: ____________________
- [ ] Two people present whenever the 72 V system is on. Names: ____________________
- [ ] Only Samson runs the study (the approval names no other investigators). A team member may drive the vehicle; do not film or record anyone's face. Glance observation of another driver is a human-participant activity: skip it unless the supervisor confirms it is covered (see run S8).
- [ ] Battery charged, tyres checked, brakes tested, a fire extinguisher nearby.

Packing list:
- [ ] Laptop (hotspot host and recorder), its charger, phone for the uplink (USB tether) and its cable
- [ ] Pi 5 + display + AI HAT stack, its 5 V 5 A supply; Pi 4 + ESP32, the 5.1 V 3 A supply for the Pi 4
- [ ] Powered USB hub or separate supply for the ESP32 if used; ESP32 USB-C cable
- [ ] Both cameras, both ToF boards, both IMU pods, all jumpers, the camera ribbons
- [ ] Ethernet cable (3 m) if bought; otherwise the laptop hotspot links the Pis
- [ ] Power for the Pis on the vehicle (EcoFlow or the converter); extension lead if charging on site
- [ ] Cable ties (plenty), double-sided tape, insulation tape, scissors or side cutters
- [ ] Bar clamps, rail plates, printed pods and covers; M3/M4/M5 screws and inserts if fitted
- [ ] Tape measure (5 m), chalk or masking tape and markers for distance marks, 2 to 3 cones or boxes
- [ ] Phone for video and a stopwatch; this checklist and a pen

## 1. Mounting on the trike (vehicle off)

- [ ] IMU 1 pod on the handlebar stem, IMU 2 pod on the rear chassis: tape underneath plus two cable ties each, arrow pointing forward. Note the exact positions: IMU 1 ________ IMU 2 ________
- [ ] Front pod / camera and front ToF board facing forward, level, camera upright (picture not tilted). Side ToF sensors looking straight out sideways.
- [ ] Rear camera and rear ToF board facing backward, level.
- [ ] Pi 4 + ESP32 at the rear near the battery (Bluetooth range to the BMS: within about 2 m).
- [ ] Pi 5 behind the display on the handlebar mount; display readable from the seat.
- [ ] Cables tied along the frame every 20 to 30 cm, clear of the wheels, motor, phase wires and anything hot; loops at each Pi.
- [ ] Photograph every mount (for the report).
- [ ] Time how long it takes to remove and refit one mount without tools (R13): ______ s

## 2. Power-up and pre-test check

- [ ] Laptop hotspot on (MyHotspot); laptop uplink on the phone.
- [ ] Power both Pis, then the ESP32 (or press RST on the ESP32 once everything is mounted and still).
- [ ] Keep the trike still for 10 s after the ESP32 starts (IMUs read their starting state).
- [ ] Run `python BenchTest/sw7_check.py` on the laptop. Result: READY / NOT READY. Warnings: ____________
- [ ] Ask Claude to "check everything", or read these yourself:
  - [ ] Both IMUs 200 Hz, drops 0
  - [ ] BMS: voltage and SoC arriving (not "no reading"). Voltage on the dashboard ______ V; on a meter ______ V (R5)
  - [ ] GNSS fix (may take a few minutes outdoors; wait for it). Time to first fix: ______ (R4)
  - [ ] Front camera (Pi 5) and rear camera (Pi 4) live on the dashboard; Front | Rear toggle works
  - [ ] ToF hand test: hand 20 cm in front of each of the six sensors; the right one changes on the dashboard
  - [ ] Pi 4 temperature ______ C, Pi 5 temperature ______ C; no new throttling
- [ ] Known not available today: the database upload (Melo's broker is unreachable). All data is still logged locally.

## 3. Start recording (keep running the whole session)

- [ ] On the laptop: `python BenchTest/road_logger.py`. It records both Pis twice a second to `BenchTest/logs/<date>_roadtest.jsonl` (ride features, IMU rates, GNSS, BMS, ToF, fusion, all camera alerts).
- [ ] Type a marker before and after every run, for example `S3 run1 start 10kmh` and `S3 run1 end`. The markers are what make the data usable.
- [ ] The ESP32 also writes its own 10 s records to flash; dump them after the session (step 6).
- [ ] Phone video of each moving run from outside the vehicle (no faces), started with a clap or the stopwatch in view, so the video time can be matched to the log.

Data limit to know: the system records one ride-feature summary per second (RMS, crest factor, jerk, peak-to-peak and the speed index per 1 s window), not the raw 200 Hz IMU samples. Frequency spectra (RQ4) need the raw samples. If Claude adds the raw stream before the test, run R1 below is part of the plan; otherwise use the 1 s features and, as a raw reference, a phone accelerometer app (for example phyphox) taped next to IMU 1 during runs S1 and S3.

## 4. Test runs (in this order)

S1. Noise floor, vehicle off (R1, RQ1)
- [ ] Trike still, 72 V off, 60 s. Marker `S1 off`.

S2. Powertrain only, drive wheel raised on stands (RQ4)
- [ ] Wheel raised and the trike secured; second person at the key.
- [ ] Motor at each setting for 60 s: idle / low / medium / high. Markers `S2 low start` ... `S2 low end`, etc. Note the dashboard speed or wheel rpm for each: ______ / ______ / ______
- [ ] Wheel down, vehicle stopped.

S3. Repeated runs on one stretch (RQ1 repeatability, RQ4 speed dependence)
- [ ] Mark a straight stretch of about 50 to 100 m with tape at start and end. Surface type: ____________
- [ ] 5 runs at a steady 10 km/h, then 5 runs at a steady 20 km/h, same direction, same line. Marker each start and end.
- [ ] Keep the speed as steady as possible; note any run that was not steady.

S4. Known features (RQ1, R3)
- [ ] 3 passes over a speed bump or a pothole at about 10 km/h. Note the feature position: ____________

S5. Hazard sensing on the move (R6 to R8)
- [ ] A cone or box placed ahead: drive slowly towards it from 15 m and stop at 2 m. 3 times. Check the front banner appears and the distance falls.
- [ ] Repeat reversing towards a box behind (rear camera and rear ToF, dashboard in Rear).

S6. Approaching object, trike stationary (C11 V3; time to contact)
- [ ] Only in a closed area, with a second person watching. Trike parked, everything recording.
- [ ] A car approaches the trike's front from 30 m at about 10 km/h and stops at a cone 5 m away. Then at 20 km/h. Then the same from behind.
- [ ] Tape marks at 30, 20, 10 and 5 m; video shows when the car crosses each mark.
- [ ] Note when the dashboard showed "APPROACHING" and the seconds it gave.

S7. ToF distance check at rest (C9; R8)
- [ ] Flat board at 0.5 m, 1.0 m and 1.5 m (tape measure) in front of each of the six sensors. Write the dashboard reading:
  front ahead ____ / ____ / ____, front left ____ / ____ / ____, front right ____ / ____ / ____
  rear ahead ____ / ____ / ____, rear left ____ / ____ / ____, rear right ____ / ____ / ____

S8. Display in daylight (R11, R12)
- [ ] Photograph the dashboard from the driver's seat in full sun and in shade (Drive, Surroundings Front and Rear).
- [ ] Note what is hard to read: ____________
- [ ] Glance timing only if the supervisor confirmed it is covered by the ethics approval; otherwise skip.

S9. Thermal and power over the session
- [ ] Note the Pi 4 and Pi 5 temperatures every 15 minutes, or ask Claude to read them. Any throttling: ______

## 5. Things to watch during the runs

- [ ] Dashboard banner and Surroundings behave sensibly (alerts appear and clear).
- [ ] If an IMU drops to 0 Hz: stop, check the wires, press RST on the ESP32, keep still 10 s, add a marker `RESET`, carry on.
- [ ] If a Pi disconnects: note the time and the marker; the recorder keeps going and records the gap.
- [ ] Battery level: stop at 30 %.

## 6. After the session (before leaving the site if possible)

- [ ] Type `q` in the recorder; note the file name: ____________________
- [ ] Copy the alert logs: Pi 4 `~/alerts_live.jsonl`, Pi 5 `~/alerts_live.jsonl` (Claude can fetch them).
- [ ] Dump the ESP32 flash log with `python BenchTest/log_dump.py` (ESP32 on the laptop USB, or ask Claude).
- [ ] Copy the phone videos and photos to the laptop; name them with the run ids.
- [ ] Back up the whole `BenchTest/logs` folder (USB stick or OneDrive).
- [ ] Remove the mounts and confirm the vehicle is back to standard (ethics condition).

## Run sheet

| Run id | Start time | End time | Target speed | Surface / feature | Steady? | Notes |
|---|---|---|---|---|---|---|
| S1 off | | | 0 | | | |
| S2 low | | | | stands | | |
| S2 medium | | | | stands | | |
| S2 high | | | | stands | | |
| S3 10 km/h run 1 to 5 | | | 10 | | | |
| S3 20 km/h run 1 to 5 | | | 20 | | | |
| S4 bump 1 to 3 | | | 10 | | | |
| S5 front / rear | | | slow | | | |
| S6 front 10 / 20, rear 10 / 20 | | | car | | | |
| S7 ToF check | | | 0 | | | |
| S8 daylight photos | | | 0 | | | |

## What each run answers

| Run | Research question / requirement |
|---|---|
| S1, S3 | RQ1 (repeatability of ride features), R1 on the vehicle |
| S2, S3 | RQ4 (powertrain against road vibration) |
| S4 | RQ1, R3 (features respond to a known event) |
| S5, S6, S7 | R6 to R8, the approach warning (C11) and the ToF calibration (C9) |
| S8 | RQ2, R11, R12 (legibility; glance only if cleared) |
| Section 1 timing | R13 (removable mounting) |
| S9 | Power and thermal limits (GA 5) |
| Whole session | RQ3 local logging and loss (the database part waits for the broker) |
