# Prompt: finish the camera tests and bring up the stand-in ToF

Written 30 Sep 2026, then acted on in the same session.

## Context

- The Pi 4 camera detector runs (C1, C2 pass). Still open: colour check
  (C3), latency (C4), distance calibration (C5), the dashboard page against
  the live detector (B2), and the detector as a service on the Pi.
- The student has printed the solid colour cards (blue, red, green, grey,
  plus white paper) for C3.
- The ordered VL53L5CX (8x8 zones) has not arrived. As a stand-in the
  student will use the time-of-flight sensors from a UCT micromouse sensor
  board ("JCP 2025 Sense v1.0", photos 20260930_0335*.jpg). That board has
  three small ToF breakouts on headers J4, J5 and J6, one on each edge; the
  two side edges are angled, so the three sensors face left, ahead and
  right. Its 2x16 header carries 3V3, 5V, GND, SDA ("DA"), SCL ("CL") and
  three shutdown lines ("SH1" to "SH3"), which is the usual way to give
  several same-address ToF sensors different I2C addresses. The exact ToF
  part is not printed in the photos.
- Photos of the same date also identify the optocoupler: a bestep single
  channel PC817 module (input + and -, with series resistor R1 and an
  indicator LED; output VCC, OUT, GND with pull-up R2).

## Tasks

1. Deploy the current `hazard_detector.py` to the Pi (the Pi copy is an
   older version without `--threads`, `--tuning`, `--timing-log`).
2. Run C4 without the student: three one-minute runs (4 threads no
   preview; 4 threads with preview; 1 thread), each with `--timing-log`.
   Summarise per stage (median, 95th percentile) and record in
   TEST_PROCEDURES, the report and Appendix C.
3. Prepare C3 so it takes the student a minute: a script on the Pi that
   captures one still, and on the laptop a check of the card colours in it.
4. ToF stand-in: decide where it connects, enable I2C on that board, and
   write a probe that identifies the chip by its model-ID register
   (VL53L0X, VL53L1X or VL6180X, all at address 0x29), so the right driver
   is used. Write wiring steps that only need the pin labels the student
   can read. Keep the report's VL53L5CX design; record the stand-in as a
   stand-in.
5. Record the optocoupler part in the project log (closes the "part number
   not recorded" item of D31, except the input voltage rating, which
   depends on R1).
6. Record everything (TEST_PROCEDURES, CHANGELOG, PROJECT_LOG, report),
   commit and push.

## Rules

No em dashes, no unnecessary bold. Do not invent results: anything not
measured is marked untested. Do not change the ESP32's 200 Hz acquisition.
