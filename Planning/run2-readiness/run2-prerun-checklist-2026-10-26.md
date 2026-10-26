# Run 2: checks before driving, Monday 26 Oct 2026

Status at 12:10 from `python BenchTest/sw7_check.py` and checks over ssh. Do the blocks in order. Block A must be green before any test that records data. Write every marker on the paper sheet as well, with the phone-clock time.

Marker from the laptop:

```
m() { ssh -i ~/.ssh/pi4_camera_key piadam@Pirate5.local "echo '$*' >> /home/piadam/roadtest/roadtest_markers.txt"; }
```

## A. System up (blocking, about 15 min)

| # | Check | Pass | Status 12:10 |
|---|---|---|---|
| A1 | Rear ESP32 USB cable into the Pi 4 (keep its own battery connected as well) | `esp32 data fresh` PASS in sw7_check | FAIL: no ESP32 on the Pi 4's USB |
| A2 | Pi 4 supply | `vcgencmd get_throttled` 0x0; no restart during A to C | FAIL: 0x50000, restarted at about 12:03 |
| A3 | `python BenchTest/sw7_check.py` | `RESULT: READY` | NOT READY (A1) |
| A4 | Raw stream from both nodes, 60 s | 200 Hz within 0.5 %, 0 drops, I2C counters 0 | after A1 |
| A5 | Recorder `sw7-roadlog` and raw files on both Pis growing | all sources answer; files grow | sw7-roadlog active |
| A6 | Marker path: `m R2 TEST marker` | in the session file within 2 s | to do |
| A7 | Phone hotspot on, Share GPS connected | Pi 5 `/gps` fix true; dashboard speed shows | sw7-phone-gps active |
| A8 | Rear node LTE publishing | records reach the Pi 5 database, none with a position | PASS: live 0.7.9 records; ingest moved to broker.hivemq.com |
| A9 | Dashboard and speaker | dashboard up; a spoken prompt on the Mamba | PASS: dashboard restarted 12:03, audio on the speaker |
| A10 | Battery state of charge | at least 50 % before the road; stop at 30 % | to read |

## B. Parked checks (Phase S, 72 V off unless stated)

Minimum if time is short: B1, B2, B3, B5 (about 30 min).

| # | Check | Requirement | Steps | Marker | Time |
|---|---|---|---|---|---|
| B1 | Eye-to-screen distance | R12 | seated eye to panel, 3 readings | `R2 NOTE eye <m> <m> <m>` | 2 min |
| B2 | BMS against the meter, key off | R5 | meter on the pack terminals, 3 readings 30 s apart | `R2 BMS keyoff m1 V=<v>` (m2, m3) | 5 min |
| B3 | C9 camera and ToF fusion, front | R8 | chair on the camera axis at 0.5 m and 1.0 m, 20 s each, nobody in view | `R2 C9 front 0.5 start` / `end` | 10 min |
| B4 | C7 ToF against the tape, front | R8 | flat box face at 0.3, 0.5, 0.75, 1.0 m from each sensor | `R2 C7 front <sensor> <m> start` / `end` | 15 min |
| B5 | C8 alert to screen | R7 | phone at 240 frames/s films the chair pulled into view and the dashboard together, 5 pulls | `R2 C8 p1 start` (p1 to p5) | 10 min |
| B6 | C5 focal length | R7, R8 | the three objects at 1, 2, 3 m in front of each camera; real widths by tape | `R2 C5 <object> <m>` | 15 min |
| B7 | C11 approaching chair | R7 | chair pulled from 6 m at walking pace, tape marks every metre, side phone, 5 pulls | `R2 C11 p1 start` / `end` | 15 min |
| B8 | Rear C9 and C7 | R8 | as B3 and B4 behind the vehicle | as above with `rear` | 15 min |
| B9 | Dashboard voice | R7 | start a route on the Map page; "In 200 metres..." heard on the speaker | `R2 NOTE voice ok` | 3 min |

## C. On the stands (two people, 72 V on, about 20 min)

| # | Check | Steps | Marker |
|---|---|---|---|
| C1 | Stand runs | settings L M H H M L, 60 s each; meter volts and clamp amps at 30 s; hold the throttle steady | `R2 STANDS L p1 start` / `end` |
| C2 | Mallet strikes and tap slate | 10 strikes, one tap slate on camera | `R2 TAP start` / `end` |

## D. Measurements (tape)

Wheelbase (3 readings), drive-wheel circumference (3 readings), IMU pod positions from the axles; 50 m section taped with cones at A-30, A-10, A0, A50, A70; bump height and length.

## E. Road (minimum that answers RQ1 and RQ4)

Still 60 s (`R2 S0`); passes at 10, 15, 20 km/h, 5 each, counterbalanced, start and end at the lines; 3 coasting passes; 5 bump passes at 10 km/h; still 60 s; removal timed (R13). Speed from the phone GPS and the ESP32 GNSS together.

## Deferred

Voice commands through the speaker's microphone (on hold, 26 Oct); LED offset (S9).
