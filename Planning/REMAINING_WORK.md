# SW-7 remaining work tracker

Started 11 Oct 2026. One list of everything still to do, in priority order, with who does it and where it is
written up. Update the Status column as items finish. Deadlines: road test Wed 14 Oct; report pre-submission by
about 22 Oct (window closes 26 Oct); final report 27 Oct 23:59; presentations 16 to 17 Nov; Open Day 18 Nov.

Owner key: Agent = a background agent started 11 Oct (the coordinator reviews, commits and deploys its work);
Student = needs Samson (hardware, purchases, people); Claude = the main session.

## Priority 1: before the road test (14 Oct)

| # | Item | Owner | Brief / record | Status |
|---|---|---|---|---|
| 1.1 | Central database (SQLite ingest on the Pi 5), sequence numbers, backlog replay after an outage, sync report (completeness, latency) | Agent | Planning/central-database-sync-prompt.md, Server/ | Done 11 Oct (7a754c6); ingest running on the Pi 5 as a user service; host and server tests pass |
| 1.2 | Firmware v0.7.4: the above plus the IMU low-pass filter at 94 Hz (anti-aliasing) | Agent (same) | as 1.1 | Flashed 11 Oct, running |
| 1.3 | Road test protocol and printable checklist | Agent | Planning/road-test-2026-10-14.md, Planning/road-test-checklist.md | Drafted; writing the files waits for the student's permission (declined once) |
| 1.4 | Pothole model (run 2) running on the Pi 4 beside the main detector, debounced, experimental | Agent | Planning/pothole-integration-prompt.md | Built, off by default (too slow on the Pi 4 beside the main detector: only 0.25 Hz fits); held-out score script ready for Colab |
| 1.5 | Hub with its own power adapter for the ESP32 (the modem browns out the Pi 4 otherwise) | Student | Report Appendix C | Open |
| 1.6 | 5.1 V 3 A supply for the Pi 4 | Student | Appendix C | Open |
| 1.7 | Send the joint road-test email; confirm the EcoFlow with Melokuhle | Student | chat 9 to 10 Oct | Open |
| 1.8 | Ask Melokuhle for broker details (host, port, user, TLS) and agree a topic | Student | Planning/central-database-sync-prompt.md | Open |
| 1.9 | Flash v0.7.4 and run the bench outage test before Wednesday | Claude + Student | BenchTest/TEST_PROCEDURES.md (T15), BenchTest/sync_outage_test.py | Done 11 Oct: PASS, 112 of 112 records, 60 replayed in 37 s; latency to measure outdoors |
| 1.10 | Temporary mounts on the trike for camera and sensor board, Pi 4 box, ESP32 near the pack for the BMS | Student | road-test plan | Open |

## Priority 2: report (pre-submission about 22 Oct)

| # | Item | Owner | Brief / record | Status |
|---|---|---|---|---|
| 2.1 | Length cut 31k to about 14k words, about 70 to 50 pages, restructure per the MSc review | Agent | Planning/report-cut-plan.md, archive in Report/archive_full_2026-10-11/ | Done 11 Oct (782fa23): 11,118 words, 34 body pages; outstanding results marked [Outstanding] |
| 2.2 | Road-test results into Results and Discussion, answer RQ1 to RQ4 explicitly | Claude | after 14 Oct | Waiting on the test |
| 2.3 | Database sync and latency results (Deliverable 3) | Claude | after 1.9 and the test | Waiting |
| 2.4 | Pothole held-out test score (Colab cell 5b or the agent's script) | Student (Colab) | 1.4 brief | Open |
| 2.5 | Ethics appendix decision with Prof. Winberg (course requires it; the student's rule D20 says leave it out) | Student | Planning/report-review.md | Open |
| 2.6 | Configuration table (versions, pins, bus speeds, priorities, queues, partitions) | Agent (2.1) | report-cut-plan.md | Done (Appendix E.1, firmware v0.7.3) |
| 2.7 | Final format checks (font, spacing, word count line, AI prompt examples, GA 10) | Agent (2.1) then Claude | Planning/brief-compliance.md | In progress |
| 2.9 | Appendix F (enclosures and mounts) and Appendix G (dashboard interface design) | Claude | Report/appendixf.tex, appendixg.tex | Done 12 to 13 Oct; G to get the three-planes screenshots after deploy |
| 2.8 | Ask Maisha for a second look at the pre-submission draft | Student | | Open |

## Priority 3: features and presentation

| # | Item | Owner | Brief / record | Status |
|---|---|---|---|---|
| 3.1 | Uber-style destination search: current location as start, instant recents, fast relevant suggestions | Agent | Planning/destination-search-prompt.md | Done 11 Oct (4cab2e8), deployed; not yet tried by hand on the touchscreen |
| 3.2 | Deck, poster, talking points, Q&A updated with all results since 6 Oct; talk down to 10 minutes | Agent | Presentation/ | Done 11 Oct (eee1296), about 9.2 min; refresh after the road test and v0.7.4 |
| 3.3 | SEN55 environmental sensor: firmware read, dashboard, bench test; air-quality anomaly rule (PM2.5 with VOC rise) | Claude | wiring in Report Appendix C | Blocked: JST GH 6-pin cable |
| 3.4 | Sensor pod, dashboard mount and IMU pods designed, audited and sliced | Claude | CAD/, Report Appendix F, Desktop/Fourth Year/EEE4022S/3D Prints/ | Done 12 Oct (revision 2, 13 beds, about 75 h, 0.9 kg PLA); printing from 13 Oct; measurements still to confirm (F outstanding list) |
| 3.5 | Offline map stage 1 (whole Western Cape vector map), stage 2 (offline routing), offline voice | Claude | Planning/map-offline-navigation-prompt.md | Not started (about 1.5 GB of downloads; after the report) |
| 3.6 | USB speaker for the Pi 5 (Bluetooth earphones work for testing) | Student | | Open |
| 3.7 | Fusion calibration test C9 | Claude + Student | BenchTest/TEST_PROCEDURES.md | Open |
| 3.8 | Stale-BMS marking on the dashboard | Claude | | Open |
| 3.9 | Dashboard redesign: layout pass, data ownership (7 pages), paper theme, refinement, three planes | Agents + Claude | Planning/three-planes-hero-prompt.md, Report Appendix G | Refinement deployed 12 Oct (5baa5f2); three planes deployed 13 Oct (864ce27) |
| 3.10 | Right ToF returned no range (answers on I2C, signal 0 to 13) | Student | Results R6 to R8 row | Resolved 14 Oct: ranging 0.63 to 0.67 m after adjustment |
| 3.11 | 9.3 % unusable DASH lines at the Pi 4 bridge over 4.7 h | Claude | Results R10 | Open: log the bad lines and find the cause |
| 3.12 | Side ToF direction: 90 degrees as built or 35 degrees as fusion_config.json assumes | Student | Appendix F | Open: decide before the pod is fitted |

## Priority 4: future work unless time allows

| # | Item | Owner | Note |
|---|---|---|---|
| 4.1 | AI HAT on the Pi 5: remove the password line from /boot/firmware/config.txt, add dtparam=pciex1 and pciex1_gen=3, then Hailo setup | Student + Claude | Do the config.txt clean-up soon regardless |
| 4.2 | Hall RPM: motor pole pairs, optocoupler tap on the vehicle | Student (supervisor approval, D31) | |
| 4.3 | MQTT over TLS | Claude | Depends on the broker |
| 4.4 | Debris (rocks, branches) detector | | No dataset; close range covered by ToF only |

## Today, Tue 13 Oct (road test tomorrow)

1. Print: start 07 (clamp, 9 h; print it twice) and 05 (rail plate, 4 h 20 min); then 13 and 06; the shell quarters and the pod after the road test unless a second MINI is free.
2. Right ToF: peel the film, check the view, hand test with Claude watching; swap the board if still blind.
3. Hardware for tomorrow: powered USB hub for the ESP32 (1.5), 5.1 V 3 A Pi 4 supply (1.6), temporary mounts (1.10).
4. People: send the joint road-test email and confirm the EcoFlow (1.7); broker details from Melokuhle (1.8).
5. Allow the road-test protocol files to be written (1.3), print the checklist.
6. Check the three-planes dashboard on the Pi 5 by touch; say if anything should change.
7. Report: ethics appendix decision with Prof. Winberg (2.5); pothole held-out score in Colab (2.4) if time allows.

## Done on 10 to 11 Oct (for reference)

ToF hang fixed and all three sensors reading; Pi 4 reboot cause found (modem on Pi USB); fan fitted; firmware
v0.7.2 (variance-based index) and v0.7.3 (assisted GNSS, mobile-network position) flashed; Maisha's wording fixes,
equations, clipping and aliasing limits, references cut to 47; wiring appendix; network-position circle;
Simulate drive fixed for touch; simulated drive in step on every page with LIVE/SIMULATED marking; Route Guidance
panel removed; spoken turn-by-turn directions; finger scrolling everywhere; two-finger carousel page swipe;
Bluetooth audio on the Pi 5 and Google voice installed.
