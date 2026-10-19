# SW-7 lab notebook

Running record of the integration and vehicle work, kept as it happens so the report can be written from it.
Each entry: time, what was done, what was measured, where the evidence is, and what it means for the report.
Tested results are marked as measured; anything assumed is marked as an estimate.

## 19 October 2026: preparing to mount everything on the TUKZIE for testing

### Status at the start of the day (live check, about 13:20)
- Raspberry Pi 5 (front): dashboard, front camera and detector (22.1 frames/s, 102 ms readout to result), front
  time-of-flight board (all three sensors reading: 206, 229, 338 mm), ingest service, power logger: all running.
  Supply 4.996 V under load, 59 C.
- Raspberry Pi 4 (rear): rear camera and detector (14.4 frames/s, 126 ms), rear time-of-flight board, bridge: running.
  It had restarted about 9 minutes earlier; under-voltage flagged since boot (0x50000), 61 C.
- ESP32 telemetry unit: both IMUs 200 Hz, no drops. BMS: no data (out of Bluetooth range). MQTT: down (broker
  unreachable since 14 Oct). GNSS: no fix indoors. Database: 464 records, none new since 14 Oct.
- Ethernet link between the Pis: no carrier at the time of the check.
- SEN55: not found on the Pi 4's I2C bus (no device at 0x69).

### Front time-of-flight board on the Raspberry Pi 5
- Earlier the board showed no power: with the shutdown lines released all three read low and nothing answered on
  I2C, which pointed at the 3V3 or GND jumper. After the student rewired it the board came up: all three sensors
  at their own addresses (0x30, 0x31, 0x32) and ranging. Wiring: J2 3 (3V3) to Pi pin 1, J2 23 (GND) to pin 6,
  J2 31/32 (SDA/SCL) to pins 3/5, XSHUT left/ahead/right (J2 21/9/7) to pins 15/16/18.
- Report: Methodology two-sided layout (wiring figure already in), Results R8 (front board now reading).

### Raspberry Pi 4 keeps restarting (diagnosed)
- Evidence: after a restart the kernel logged "Undervoltage detected" four times in the first 70 s (13, 39, 43, 69 s);
  the flags show under-voltage since boot. The ESP32 (with its LTE modem) is on the Pi 4's own USB port.
- Cause: the known supply fault (Methodology, Raspberry Pi 4 under-voltage): the modem's transmit bursts drawn
  through the Pi's USB pull its supply down until it resets. Earlier evidence: 3 restarts in 20 minutes on the Pi's
  USB, none in 4 hours off it.
- Fix needed before mounting: ESP32 on a powered hub or its own 5 V supply; the official 5.1 V 3 A supply for the
  Pi 4 with a short cable; fan checked.

### Raspberry Pi 5 restarts (under investigation)
- The Pi 5 dropped off the network several times. After one drop it came back with an uptime under a minute: it is
  restarting, not losing Wi-Fi (0 Wi-Fi disconnects in that boot). Flags clean after the restart, but they reset at
  each boot, and the journal kept only the current boot.
- Changes made: persistent journal (/var/log/journal); a power logger service (sw7-powerwatch) writing supply
  voltage, throttle flags, temperature and load every 5 s to /home/piadam/powerwatch.log.
- First readings: supply 5.09 V at boot, 5.05 V at 61 s, 4.96 V at 66 s as the detector started (load 2.8).
  A sinking supply under load points to a weak supply or cable (the Pi 5 needs 5 V 5 A). Not yet confirmed: the
  next restart's last log lines will show it.

### Camera focal-length calibration (test C5), front camera (Pi 5)
- Detector setting: 600 px (uncalibrated). Expected from the camera's specification (3.6 mm lens, 640 x 480 from a
  2592-pixel-wide sensor): about 635 px (estimate).
- Trike at about 10 ft (3.05 m): detected as "motorcycle", box 220 px, detector said 2.18 m. Width across the box
  not yet measured. Proof: BenchTest/logs/calibration/20261019_120755_front_trike_10ft.jpg.
- Person at 2 m: box 166 px (median of 8 s, spread 52 px); with an assumed 0.55 m width, focal 605 px.
  Person at 3 m: rejected, the person's box merged with the trike behind (155 px against about 90 px for the body).
  One earlier 2 m sample rejected: the person was walking. Lesson: a person's box is a poor calibration target
  (pose, arms, objects behind).
- Better method used: three objects on the floor at measured distances. Pixel widths measured from the frame:
  cardboard box 82 px at 1 m, yellow block 37.5 px at 2 m, white box 63 px at 3 m. Real widths still to measure;
  at 635 px they would be 12.9, 11.8 and 29.8 cm. Proof: BenchTest/logs/calibration/20261019_markers_1m_2m_3m.jpg.
- Privacy: a colleague in the background was blurred out of the saved frames; frames showing other people are not
  kept.
- Tool: BenchTest/focal_cal.py (records the box width, saves a proof frame and the detections per run).

### Mechanical
- Modified head tray (student's design, SW7_Pod_Head_Tray modified.SLDPRT): two added features, a 30 mm block and a
  4 mm plate, each with two 4 mm holes 64.0 mm apart. One solid body; no clash with the head upper or the camera
  retainer; overlaps the original electronics box by about 10.6 cm3, which does not apply to the front pod (no box
  behind the head). Sliced: 6 h 20 min, 76 g (supports from the bed).
- Holding part (student's design): C-channel 60 x 60 x 95 mm, 4 mm walls, 14 mm lips leaving a 32 mm slot.
  Sliced standing on its end: 7 h 10 min, 90 g (5 walls, 50 % infill) or 6 h 00 min, 70 g.
- Files: Desktop/Fourth Year/EEE4022S/3D Prints/tray_mod/.

### SEN55
- Wiring options given: Pi 4 bus shared with the time-of-flight board (pins 2/4 for 5 V, a GND, pins 3/5 for SDA/SCL,
  Int.Sel to GND, pin 6 Boot 0 not connected) or the ESP32 (5V, GND, IO17, IO18). The Pi 4 option needs no firmware
  change. The VDD test pad was damaged while soldering; VDD to be taken from the connector's pin-1 leg.

### 15:52: first check with everything mounted on the TUKZIE
- Raspberry Pi 5 (front): up 28 min with no restart; dashboard, front camera and detector (22.0 frames/s, 93 ms),
  ToF service and power logger running. Supply 5.00 V now, lowest 4.93 V in the last 5 minutes at load 4.2 (marginal;
  the Pi 5 wants 5.1 V). 57.6 C, flags clean.
- Front time-of-flight board: all three sensors answer at 0x30 to 0x32 but return nothing (8190, signal 0 to 21):
  nothing within their 1.2 m range in front of the mounted vehicle, so the dashboard correctly shows no reading.
  The service log showed I/O errors and a re-open about 30 minutes earlier (during mounting), since recovered.
  Hand test on the vehicle still to do.
- Raspberry Pi 4 (rear): up 1 h 8 min, no restart in that time, but 11 "Undervoltage detected" messages this boot;
  the ESP32 is still on the Pi 4's own USB (through its internal hub). Rear camera 14.5 frames/s, 131 ms. Rear ToF
  reading (left 42 mm, right 270 mm: parts of the vehicle or the mount close to the sensors; check their view). 62.8 C.
- ESP32: both IMUs 200 Hz, no drops. BMS now reporting on the vehicle: 60 %, 74.58 V, 0.0 A, record 2.2 s old,
  because the unit now sits near the pack (it did not reach the BMS from the bench). Dashboard lines lost: 191 of
  3,208 (6.0 %). Modem signal not reported at the time; no GNSS fix (indoors).
- Ethernet between the Pis: no carrier on either side (cable not connected or not seated).
- SEN55: not on the Pi 4 bus.
- For the report: first sustained BMS on the vehicle (R5), mounted-system check before the stationary tests.
