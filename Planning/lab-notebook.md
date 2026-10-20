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

### 16:01: recheck on the vehicle
- Ethernet between the Pis now linked: carrier on both sides; the Pi 5 reaches the rear bridge over the cable in 6 ms.
- Raspberry Pi 5: up 37 min, no restart; supply 5.07 V now, lowest 4.90 V in the last 5 min (still marginal);
  57.1 C; front camera 21.6 frames/s, 57 ms; front ToF clear (nothing within range); dashboard running.
- Raspberry Pi 4: up 1 h 18 min, no restart, but under-voltage and throttling active at the moment of the check
  (0x50005) and 16 under-voltage messages this boot; ESP32 still on its USB; 52.5 C; rear camera 14.5 frames/s,
  151 ms (throttling raises the delay from about 120 ms). Rear ToF: left 75 mm, right 24 mm (objects close to the
  side sensors on the vehicle).
- ESP32: IMUs 200 Hz, no drops; BMS 60 %, 74.58 V, 0.0 A, 1.8 s old; modem signal 11 of 31 (weak at the vehicle's
  position); MQTT down; dashboard lines lost 222 of 3,544 (6.3 %).

### About 17:00: restarts on the bench, from the Pi 5 power log
- Both Pis had restarted again since 16:01: the Pi 5 was 5 minutes into a new boot, the Pi 4 about 52 minutes.
- The Pi 5 power log (sw7-powerwatch, every 5 s, kept across restarts) shows four restarts since 14:28. In the last
  reading before each one the supply was normal (4.95 to 5.08 V), the throttle flags clean (0x0) and the temperature
  57 to 59 C, at load 2.8 to 5.0. The lowest supply in the two minutes before each was 4.89 to 4.97 V.
- So the Pi 5 is not browning out slowly or overheating: power is lost abruptly within the 5 s between readings. Likely
  causes: the USB-C plug or the supply's input working loose or being knocked during the mounting work, the source
  cutting out, or the supply's overcurrent protection tripping on a short peak. The journal did not keep the earlier
  boots (restarts within its 5-minute flush interval), so there is no kernel message either way.
- Pi 4: 15 under-voltage messages this boot, flags 0x50000, 69.6 C; ESP32 still on its USB. Rear camera 14.5 frames/s,
  127 ms; rear ToF right 242 mm.
- Ethernet: no carrier on either side again (the cable was unplugged or knocked loose).
- Front ToF: left 697 mm, ahead 312 mm (reading normally). BMS 60 %, 74.58 V. Modem signal 17. Lines lost 9.7 %.

### 17:15: road-test recorder moved onto the vehicle
- The laptop recorder only works if the laptop rides along with its hotspot. The recorder now runs on the Raspberry Pi 5
  as a service (sw7-roadlog, starts at boot): front sensors read locally (127.0.0.1), rear sensors and the ESP32 over the
  Ethernet cable (10.20.0.1), twice a second, to /home/piadam/roadtest/<date>_roadtest.jsonl. Markers: lines appended to
  /home/piadam/roadtest/roadtest_markers.txt.
- First 12 s: front 24 of 24 polls, rear 0 of 11, because the Ethernet cable was unplugged. On the road the cable is the
  only link to the rear unit, so it must be plugged in and tied down.
- Timing caution: the Pi clock is set by the network; without internet on the road, a restart leaves it wrong. GNSS
  time in the ESP32 record (once it has a fix) is the reference for aligning the logs.

### 17:20: Ethernet re-connected, recorder complete
- Cable link up at 1000 Mb/s, 0.25 ms round trip; rear bridge answers in 2 ms.
- Recorder on the Pi 5, last 10 s: front, front alerts, rear and rear alerts each 20 of 20 polls. Rear sample: IMUs
  200 Hz, BMS 60 %, 74.57 V, rear ToF right 222 mm. All four sources now record on the vehicle without the laptop.

### 17:30: how driving and reversing will be known
- No signal in the system gives the gear or direction. The ESP32 record has GNSS speed and course and the vibration
  features; GNSS course is the direction of motion, not the vehicle's heading, and is unreliable at reversing speeds.
- Driving or parked: labelled afterwards from battery current (motor working), vibration (running or moving) and GNSS
  speed (moving; separates driving from the motor running on stands). GNSS speed units still to confirm outdoors.
- Reversing: from run markers and video for now. Options for a direct signal: (1) the trike's reverse switch or reverse
  beeper through an optocoupler into a free ESP32 pin (best; touches the 72 V wiring, needs supervisor approval);
  (2) the IMUs' forward acceleration at moving off (firmware change); (3) front against rear camera scale change.
- Report: Methodology, vehicle tests (recorder and state labelling) updated, commit 947e67d.

### 17:40: camera case for the Pi 5's camera sliced
- The Pi 5's front camera (OV5647) gets the same printed case as the Pi 4's: case bottom, case top and the 30 degree
  corner mount from Projects/Pi Camera Mount. One bed, all flat on the bed with no supports needed: 1 h 27 min, 14 g.
  Files: Desktop/Fourth Year/EEE4022S/3D Prints/pi5_camera/.

### 17:45: cover for the sensor board holder (head upper, bed 08)
- The cover over the modified head tray is the original head upper (bed 08): checked earlier against the modified tray,
  no clash. Printed roof down: 8 h 25 min, 85 g. Opened in PrusaSlicer 2.9.6 and copied to the USB stick.
- The Pi 5 camera case sliced at 17:40 was a misunderstanding of "camera bracket"; kept in 3D Prints/pi5_camera in case
  it is wanted.

### 17:55: measurement gap for the single road test
- Finding: the live DASH line carries one vibration number per second (vib, vib_dis); the full ride features exist only
  in the ESP32's 10 s flash log, and the raw 200 Hz samples are not saved anywhere. A drive recorded as things stand
  would not support RQ1 (feature repeatability) or RQ4 (spectral separation of powertrain and road).
- Work started (agent, branch to be reviewed): firmware v0.7.5 with a raw 200 Hz stream of both IMUs on a separate
  non-blocking path (drops counted, never blocking the IMU tasks), the full 1 s features and the forward acceleration in
  each DASH line; the Pi 4 bridge saving the raw stream and the ESP32's other output to files; an analysis tool for
  state labelling, spectra and repeatability. To be bench-tested (IMU timing unchanged) before flashing.

### Drive start (v0.7.4 firmware; the raw-stream firmware not ready in time)
- Pre-drive check: recorder on the Pi 5 active, all four sources 20 of 20 polls in 10 s, 20,559 records in the session
  file so far; IMUs 200 Hz, no drops; BMS 59 %, 74.54 V; no GNSS fix yet; modem signal 17; Pi 5 up 1 h 5 min, flags
  clean, Ethernet linked. Marker "drive session starting" written to the Pi 5 marker file.
- Known limits of this drive: live ride features are one vibration number per second (full features in the ESP32's
  10 s flash log); no raw 200 Hz IMU data unless a phone accelerometer is taped beside IMU 1; MQTT down; no gear signal.

### 18:35: run under way (reported by the student)
- The student reported the run in progress at about 18:35. The Pis were out of reach of the laptop (no reply to ping or
  ssh at 18:22 and 18:35), so the run was not watched live; it is recorded on the Pi 5 (sw7-roadlog). Run start and
  end times are being written on the run sheet, to be turned into markers afterwards.

## 20 October 2026: road-test data check (drive of 19 October)

Files copied from the Pis to BenchTest/logs/roadtest_2026-10-19/ (recordings, both alert logs, Pi 5 power log; not
committed to git because of their size, kept on OneDrive).
- Main recording 17:15:34 to 19:04:10 (108.6 min, 51,489 records, no damaged lines). The Pi 5 did not restart during
  the drive (its restarts were at 19:04 and 19:10, after it); two short recordings follow from those restarts.
- Driving, found from battery current and vibration: 16 active segments between 18:15 and 18:49, 19.5 min of motor
  current or high vibration in total, plus short ones at 17:58 and 18:04 (possibly the stationary runs).
- Coverage during the drive: front sensors and alerts throughout; rear and ESP32 throughout the drive (the only rear
  gap, 409 s from 18:06:34, was before it).
- Captured:
  - IMUs: 200 Hz in all but 2 of 10,287 records, no drops (R1 on the vehicle).
  - Battery under load: current up to 46.9 A (discharge, logged as negative), pack from 74.6 down to 72.8 V under load,
    charge 60 to 58 % (R5).
  - Vibration (one number per second): median 0.031 parked, 95th percentile 2.0, maximum 5.09 while driving.
  - Front alerts 17:15 to 19:10: 1,342 (person 815, car 513, of which 261 car "approaching", plus 366 person
    approaching); rear alerts: 741 (car 201, of which 36 approaching).
- Not captured:
  - GNSS fix: none in any record, so no position or speed for the whole drive (R4; speed dependence for RQ4; the
    moving label must come from current and vibration instead).
  - Raw 200 Hz IMU samples (not supported by v0.7.4); full 1 s ride features only in the ESP32 flash log (10 s
    records), still to be read out.
  - Run markers: only "drive session starting"; run times have to come from the run sheet or video.
  - MQTT upload (down), so no sync latency.

- Report updated with the first road session (commit 91f9598): Results R1, R4, R5, ride states, camera alerts on the
  road and recorder coverage; Discussion (what the session supports and cannot yet answer); Methodology (session
  run); Conclusions note; requirements table rows R1, R4 and R5.
