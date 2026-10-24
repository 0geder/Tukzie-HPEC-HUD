# Bench validations, Sunday 25 October 2026

Purpose: close the "not measured" items that the strict examiners counted against the report, without the vehicle and
without any person as a subject. Each item names the requirement, what to bring, the steps, the marker or file, and what
goes into the report. Total about 2.5 h with two people. Log every step in Planning/lab-notebook.md.

Bring: 5 m tape and steel rule; masking tape and a marker; a chair (a COCO class the detector recognises) and a string to
pull it; three boxes or blocks with flat faces; multimeter; a phone that films at 240 frames/s; an LED (any colour) and a
330 ohm resistor with two jumper leads; the laptop on the same network as the Pis.

## 1. Camera focal length, front and rear (C5, report R7/R8 distance bands) - 20 min
1. Front: the three objects of 19 Oct (cardboard box 82 px at 1 m, yellow block 37.5 px at 2 m, white box 63 px at 3 m,
   photo BenchTest/logs/calibration/20261019_markers_1m_2m_3m.jpg). Measure each object's real width across the face that
   faced the camera, 3 readings each, to the millimetre. Send the numbers: focal = pixels x distance / width.
2. Rear: put one box at 1.00, 2.00 and 3.00 m on the tape in front of the Pi 4 camera (lens to front face), one frame each
   with BenchTest/focal_cal.py; measure the box width.
Report: focal length per camera with the spread over the three distances, against the 600 px setting.

## 2. Time-of-flight against a tape (C7, R8) - 30 min
Front ToF wires must be reseated first (Pi 5 pins 1, 3, 5, 6); rear left sensor checked.
1. Flat board (box face) square to each sensor at 0.30, 0.50, 0.75 and 1.00 m (and 1.20 m) on the tape.
2. At each distance read 10 values from the bridge (front http://<pi5>:8082/telemetry, rear http://<pi4>:8081/telemetry);
   Claude can log them: say "tof front ahead 0.5" and the distance when the board is in place.
Report: error and spread per sensor and distance; the largest distance within 5 % sets max_range_m.

## 3. Camera and ToF fusion (C9, R8) - 20 min
The chair on the camera axis at 0.5 and 1.0 m (front of the chair to the sensor plane), 20 s each, nobody in view.
Read the fused hazard from the bridge (source "fused", distance). Report: median fused distance error at 0.5 and 1.0 m
against the criterion of 5 cm or less.

## 4. Approaching-object warning (C11, time to contact) - 20 min
The chair pulled towards the camera by the string at a steady walking pace from 6 m, tape marks every metre, side phone
filming at 240 frames/s, five pulls. Detector logs each "approaching" alert with its time to contact. From the video,
fit distance against time for the speed; true TTC = distance / speed at the alert. Report: TTC error per pull.

## 5. Alert to screen (C8, R7) - 15 min
Phone at 240 frames/s filming the chair being pulled into the camera's view AND the dashboard at the same time. Count
frames from the chair entering the frame to the banner appearing, five repeats per camera. Report: median and range of
the time to the screen, against the computed 0.26 s onset at the detector.

## 6. Camera-to-IMU alignment (R6) - 25 min
1. LED plus 330 ohm in series from the front node's sync pin (GPIO5, the wire to Pi 5 pin 11) to GND, LED in front of
   the Pi 5 camera, room dim. Leave the existing sync wire in place.
2. On the Pi 5: sudo systemctl stop pi5-hazard-detector; then
   python3 led_offset.py --sync <today's front_sync CSV> --seconds 60 --fps 50 --out ~/roadtest/led_offset_front.json
   (BenchTest/led_offset.py, copied to the Pi). Restart the detector afterwards.
3. Same on the Pi 4 with the rear node's sync pin (IO15 to Pi 4 pin 11).
Report: the offset bound (lower, upper) and spread per camera, replacing "the camera-to-IMU offset is not yet measured".

## 7. Battery voltage against the meter (R5, D1) - 10 min
Key off: multimeter on the pack terminals, three readings 30 s apart, read the BMS at the same moments (Claude reads it).
Report: difference per reading against the "matches a meter" criterion (proposed: within 0.5 V).

## 8. Eye-to-screen distance (R12 legibility) - 5 min
From the driver's eye position to the panel, three readings. The legibility result in the report assumes 0.70 m.
