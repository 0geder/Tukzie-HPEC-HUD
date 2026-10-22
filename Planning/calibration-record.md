# Calibration record

One line per calibration, with the date, the conditions and the result, so the report can cite where each factor
came from. Newest last.

| Date | Item | Conditions | Result | Status |
|---|---|---|---|---|
| 2026-10-22 13:00 | Front node IMU1 (MPU6050, front ESP32, v0.7.5) | !recal sent from the Pi 5 over USB; board still (vib 0.029 to 0.032 m/s^2 in the 5 s before) | mean magnitude 9.7729 m/s^2, scale 1.0035, stored in NVS (first boot 21 Oct: 9.7718, 1.0036). Raw counts at rest 4,096.6 = 1.000 g. Gravity direction in sensor axes (0.105, 0.751, 0.652), 49.3 deg from z. Noise s.d. 29, 17, 19 counts (0.007, 0.004, 0.005 g) | Valid for this orientation only; redo after final mounting on the frame |
| 2026-10-22 | Rear unit IMU1 and IMU2 | not done: rear unit on v0.7.4.1 in the consumer-stall fault (drops rising, vib null) | | Redo after flashing v0.7.6, mounted, stationary |
| | Camera focal length, front and rear | needs targets of known width at measured distances (or a checkerboard) | | To do |
| | ToF sensors against a tape (C9), front and rear | 0.5, 1.0, 1.5 m, 10 readings each | | To do |
| | BMS voltage against a meter | pack terminals, vehicle off and under load | | To do |
