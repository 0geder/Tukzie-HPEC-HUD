# Report length cut and restructure, 11 Oct 2026 (plan and cut log)

The full text before the cut is in Report/archive_full_2026-10-11/; anything below can be restored from there.

## Limits (Planning/brief-compliance.md)

10,000 to 15,000 words "plus tables, diagrams and appendices"; 50 content pages excluding the table of contents,
appendices and references; Times New Roman 11 pt, single spacing.

## Result

| Chapter | Words before | Words after | Pages before | Pages after |
|---|---|---|---|---|
| 1 Introduction | 1,848 | 907 | 6 | 4 |
| 2 Literature | 2,938 | 1,709 | 7 | 4 |
| 3 Methodology | 24,076 | 4,650 | 47 | 13 |
| 4 Results | 1,325 | 1,734 | 5 | 6 |
| 5 Discussion | 1,052 | 1,093 | 3 | 3 |
| 6 Conclusions | 520 | 502 | 2 | 2 |
| 7 Recommendations | 482 | 523 | 2 | 2 |
| Body | 32,241 | 11,118 | 72 | 34 |

TeXcount text words. The PDF went from 103 to 70 pages; about 3,900 words and 16 pages of headroom remain for the
road-test and database-sync results. Build clean (no undefined references); about 9 overfull boxes remain (the
document-wide \nohyphens wrapper in Chapters 1 and 2, long file paths in the evidence table). Three references
became uncited and were removed (canomarin2016, currano2021, liu2023groundingdino); 44 remain, in citation order.

## Targets used

Introduction 1,300; Literature 2,100; Methodology 6,000; Results 1,900; Discussion 1,200; Conclusions 500;
Recommendations 650 (about 13,650); the result came in lower.

## Restructure (MSc review comments)

1. Methodology is final design plus verification: overview with an architecture comparison table (workload, power,
   memory, interfaces, latency); hardware; firmware; signal processing (all equations kept); BMS; positioning;
   other inputs; the camera in four parts (capture and synchronisation, detection, range sensing and fusion,
   dashboard integration); communications and logging; verification.
2. Start-up tests consolidated into one table (tab:startup-checks).
3. BMS: one "Current status (11 October 2026)" paragraph.
4. Faults kept in the body as short findings: modem under-voltage on the Pi USB, JSON NaN found by log read-back,
   ToF start-up hang and its fix, flash-write pause, GNSS layout and power-key problems, BMS checksum.
5. Introduction: vehicle problem and deliverables first; research questions, requirements R1 to R13 and
   acceptance criteria separated (criteria from BenchTest/TEST_PROCEDURES.md, removability from SW7-VIT-001).
6. Literature: HUD optics cut to two sentences; five dashboard issues developed (layout, legibility and contrast,
   interaction, alert priority, data validity and update age); novelty bounded by the search run (OpenAlex, arXiv,
   Crossref, 3 runs, 733 records in Research/research.db, gap_ledger.json).
7. Results rebuilt against R1 to R13 with a status table; Discussion follows the research questions and the five
   display issues.
8. Recommendations reprioritised: acquisition integrity, calibration, power, synchronisation, backlog recovery,
   display failure behaviour, ride analysis, then obstacle detection (one paragraph).
9. Vehicle test design (sec:field-test-design) summarises the SW7-VIT-001 stationary and ground phases and safety.

## Moved

- New Appendix E, Configuration and Development Record (appendixe.tex): E.1 configuration table for firmware
  v0.7.3 (platform espressif32 7.0.1, Arduino core 2.0.17, libraries, flags, flash and DIO, default_16MB.csv
  layout, pins, 400 kHz I2C, IMU settings, periods, MQTT and log settings, every task with core, priority and
  stack, every queue depth); E.2 fault table (33 rows: symptom, cause, fix) replacing the narrative fault
  subsections; E.3 supporting detail (Pi 4 discovery figure, colour-card table, pothole data and training
  figures, map and navigation).
- Camera casing figure to Appendix B.

## Cut log by chapter

- Chapter 1: the urbanisation paragraph (one clause kept with its citation); the HPEC and HUD background; "Purpose
  of the study" (three paragraphs, including the unsourced UCT Radar Remote Sensing Group sentence); the 639 kg
  remark; the software thread list; most limitation bullets; the bold plan of development. The old RQ table is
  replaced by R1 to R13.
- Chapter 2: Sebwa energy details (0.54 kWh, 97.59 %); the long logistics-to-telemetry argument; condensed
  Gonzalez, Sattar and Alatoom paragraphs; the producer and consumer paragraph; the HUD design paragraph (to two
  sentences); the Currano sentence; the VL53L5CX forward reference. Added the dashboard-issues paragraph and the
  bounded novelty claim.
- Chapter 3: sections 3.2 to 3.8 (board, start-up, UART, power key, AT procedure, GNSS polling, baseline criteria
  table, single IMU, flash and PSRAM) reduced to table rows; the IMU sample-structure table; sync subsections (pin
  error, end-to-end checks, connection fault, combined capture, lens cover) reduced to one paragraph; GNSS
  subsections 3.10.1 to 3.10.4; BMS scanning, first contact and old status subsections (one status paragraph and
  fault rows); Pi provisioning, partitioning and network; the OpenSCAD narrative; "Why one sensor" and the planned
  VL53L5CX procedure; the long latency narrative (numbers moved to Results); colour cast, pothole, map and
  simulated drive details (to Appendix E); the Tier-1 auto-rickshaw remark; the pre-test check narrative (a table
  row); Pi 5 voice and Hailo (Hailo kept in E.3 and the architecture table).
- Chapter 4: absorbed the Methodology numbers on disagreement, still-period levels, the disturbance test, GNSS
  loss timing, the dashboard line and bridge, and Sensors page values.
- Chapter 7: the Grounding DINO sentence and the six-step obstacle-detection plan.
- Appendices: A (one reference changed to the new appendix, BMS wording), B (casing figure), E (new).

## Outstanding results

Every outstanding result is a \outstanding{...} macro that prints "[Outstanding: ...]": road-test data (Results
4.1 to 4.4, 4.9, 5.2), pothole on the Pi and its held-out score, database sync (Methodology, Results 4.7,
Discussion), fusion test C9 and focal-length calibration, a sustained BMS session with a meter check, glance and
alert-to-screen timing on the Pi 5, revised Conclusions answers.

## For the student

- Ethics letter appendix: course requires it, rule D20 says leave it out; decide with Prof. Winberg.
- Font: pdflatex uses newtx (a Times clone); XeTeX gives real Times New Roman.
- \parskip is 6 mm; optional to reduce.
- The abstract still opens "Draft abstract"; write it last.
- Appendix A still needs AI prompt examples and GA 10 (brief-compliance H16, H8).
- Check the acceptance numbers in the requirements table, especially the 10 m GNSS criterion (R4 partly met: 95th
  percentile 11.0 m).
- BMS pack identity still to confirm with the vehicle team.
