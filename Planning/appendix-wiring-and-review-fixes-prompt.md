# Wiring appendix and Maisha's review fixes (brief)

Written 10 Oct 2026 from the student's request: add how everything is connected to the appendix, with the
screenshot from `Rasp Pi 4 pins.pdf` and a connection table, and the same for every other board that has a
document with its connections; then act on the review comments from Maisha Magavha (MSc), in
`../../Commented Report.pdf` (built 3 Oct, 26 comments).

## Part A: wiring appendix

1. A new appendix chapter, "Wiring and Connections", placed after the supporting figures.
2. One figure per source document, cropped from the document itself, cited:
   - Raspberry Pi 4 40-pin header (`References/Hardware/Rasp Pi 4 pins.pdf`).
   - Makerfabs ESP32-S3 A7670X pinout (already Figure in Appendix B; referenced, not duplicated).
   - Sensirion SEN5x connector and pin table (datasheet page 13).
   - Sensor board (JCP 2025 Sense v1.0) photo showing the 2x16 header J2 and its pin 1, 2, 31, 32 marks.
3. One table per link, with both ends named by connector, pin number and signal:
   Pi 4 to sensor board (ToF), Pi 4 to ESP32 (USB data and the sync pulse), ESP32 to IMU1 and IMU2,
   ESP32 antennas, ESP32 to SEN55 (planned, untested), Pi 4 camera, power.
4. Sources only: `BenchTest/TEST_PROCEDURES.md` (C5 sync wire, ToF wiring), `TelemetryUnit/src/main.cpp`
   (pin defines), `CameraDetection/tof_reader.py`, the SEN5x datasheet, the Makerfabs pinout. Anything not
   verified on the hardware is marked as planned or unverified.
5. Short wiring rules: power off first, continuity check, 3.3 V only for the sensors, strain relief.

## Part B: review fixes (Maisha)

Do now, in the current .tex:
- Overstated or wrong claims: "head-up telemetry", "ensures that no process blocks another", "deterministic"
  acquisition, "minimum-variance unbiased" fusion, "every major subsystem", store-and-forward without replay,
  SEN55 "not yet received" and VOC/NOx as concentrations, TRL 6 as a target, the 639 kg plate value,
  the 149 windows and 222 lines.
- Equations for the ride features, calibration and fusion, as LaTeX equation environments.
- References: remove entries that are never cited.

Later, with the length cut and the road test: restructuring (merge start-up tests and status statements, split
the camera section, cut windshield optics, architecture comparison table), the configuration table, Results
tables with conditions and repetitions, Discussion answering each research question.

## Rules

- No em dashes; no unnecessary bold (memory: writing style).
- Every claim traceable to a file in the repository; nothing invented.
- Build the report after each part and check for undefined references.
- Commit and push after each part (no co-author line).
