# SW-7 brief compliance audit

Prepared 28 September 2026, against repo state at commit b57f742 (with firmware v0.5.0 at dfc6542). 29 days remain to the final report deadline of 27 October.

Sources read:
- Brief: "EEE4022S 2026 Topics Winberg_Taken By Samson.pdf", SW-7 entry, pages 20 to 22 of the topics list (PDF pages 1 to 3). Cited below as "Brief p20" etc., using the printed page number.
- "EEE4022S Final Year Project 2026 Intro Lecture.pdf" (13 slides). Cited as "Intro L. s6" (slide number).
- "EEE4022S Final Year Project 2026 Lecture 2.pdf" (30 slides). Cited as "L2 s7".
- "GA Tracking Form incl GA5.pdf" (blank template with GA descriptors on pages 3 to 5) and "OKTSAM001 GA Tracking Form - Signed.pdf". Cited as "GA template p4" and "Signed GA form p1".
- Repo: PROJECT_LOG.md (cited as "Log" with section or decision number), Report/*.tex, Report/OKTSAM001 SW7 Report Draft.pdf (built 28 Sept, 85 pages), HUDTelemetryUnit/src/main.cpp, CameraDetection/, DashboardIntegration/, BenchTest/, Planning/, Presentation/.

Status values: met, partly met, not met, changed by a decision pending the supervisor (written "pending supervisor").

Main-body page count, checked in the PDF: Chapter 1 starts on PDF page 11 (printed page 1) and Chapter 7 ends on PDF page 72 (printed page 62). The bibliography starts on PDF page 73. The main body is 62 pages.

## 1. Requirements matrix

### 1.1 Project brief: description

| # | Requirement (quoted) | Source | Status | Evidence | What is left |
|---|---|---|---|---|---|
| B1 | "perform real-time edge processing on an array of integrated vehicle and environmental sensors" | Brief p20 | partly met | Vehicle sensors run on the ESP32-S3 under FreeRTOS: two IMUs at 200 Hz, GNSS, BMS over BLE (7d989cb; Log 4.1). No environmental sensor is integrated (Methodology.tex line 362: SEN55 "not yet received or integrated") | Integrate SEN55. Run on the vehicle |
| B2 | "monitoring powertrain performance" | Brief p20 | partly met | BMS frame decode gives pack voltage, current, remaining Ah and SoC (main.cpp lines 890 to 896). BMS link is intermittent and the bench log shows no pack connected (Log 4.1, BMS). No motor-side signal: the Hall-sensor tap is planned (Planning/SW7-VIT-001 Rev E, Phase A "Hall tap and pole-pair count"; Log 4.6 optocouplers) but not built | Sustained BMS session (Results 4.4 placeholder). Hall tap through the optocouplers, if the supervisor agrees (D31) |
| B3 | "ride smoothness (via IMU data)" | Brief p20 | partly met | 1 s window features, speed-normalised index, sine self-test, calibration, dual-IMU fusion (d6f73bb, 5e3e6d9, 8fb96f3; Methodology 3.15). Bench only; the speed index has never been computed with a GNSS fix (Log F9) | On-vehicle data. Outdoor GNSS fix |
| B4 | "microclimate profiles" | Brief p20 | not met | SEN55-SDN-T ordered locally, not received (Methodology.tex line 362; Log 4.6). No code in main.cpp (no SEN5x reference) | Receive, integrate, log T and RH on the route |
| B5 | "localized air quality metrics to detect environmental anomalies (e.g., plastic burning)" | Brief p20 | not met | As B4. The report frames SEN55 as recording conditions along a route (Methodology.tex line 362) and does not mention anomaly detection or burning anywhere in Report/*.tex | Integrate SEN55 and add an anomaly rule (see section 3). Add the anomaly aim to the report |
| B6 | "the unit will drive a dynamic graphical user interface projected as a Heads-Up Display (HUD) onto a custom handlebar-mounted front windshield visor" | Brief p20 | pending supervisor | No HUD code or hardware in the repo. HUD on hold (Log D26, pending). Front camera page for the existing dashboard exists instead (7b0601f) | Supervisor decision (section 2) |
| B7 | "This HUD will map critical telemetry (speed, battery State-of-Charge, fleet notifications)" | Brief p20 | pending supervisor | The existing vac-work dashboard shows a speedometer and SoC (Tukzie-Vac-Work-2026/Dashboard Team/Dashboard+ASIS/Dashboard+ASIS/README.md lines 10 and 13). That is another team's work, not SW-7's. SW-7 has SoC from the BMS (main.cpp line 896) but does not send it to any display. Speed from SW-6 over UART (D15) is not implemented (Log 4.1). Fleet notifications: not found anywhere in the repo | Decide whether SW-7 must feed its own speed and SoC to the dashboard. Fleet notifications: not found, needs a decision to drop or define |
| B8 | "render active driver alerts based on localized sensor feeds" | Brief p20 | partly met | Camera alerts: /alerts endpoint (57dd18e) and the Front camera page listing alerts in red, amber, green (DashboardIntegration/README.md). Tested offscreen on a laptop only, not on the Pi 5, not against the live detector, and the four wiring edits are not applied | Run the page on the Pi 5 with the live detector. ToF alerts once the sensor arrives |
| B9 | "Telemetry will be logged locally" | Brief p20 | partly met | LittleFS log, mount verified (20d2fa6, 6d3a080). Read-back not done; no replay of unsent lines; flash writes suspected of 25 to 30 ms acquisition stalls (Log F6) | Read back and check the log. Confirm the stall with !log off (v0.5.0, not flashed) |
| B10 | "transmitted via a cellular module (4G/LTE) to a central database for route optimization" | Brief p20 | partly met | One acknowledged MQTT publish over LTE to test.mosquitto.org (+CMQTTPUB: 0,0; Methodology 3.20.2). No central database: the broker is a placeholder or the public test broker (D4). Retry after failed connect written in v0.5.0, untested (F8). Route optimisation: not found in SW-7 | Agree a destination database with the TUKZIE team or stand one up. Repeated publishes on the vehicle |

### 1.2 Project brief: deliverables

| # | Requirement (quoted) | Source | Status | Evidence | What is left |
|---|---|---|---|---|---|
| D1a | "An integrated HPEC telemetry hardware module housing the environmental, air quality, and IMU sensor payload" | Brief p20 | partly met | ESP32-S3 with modem and two IMUs run together on the target board (Methodology 3.18). No environmental or air-quality sensor. No enclosure for the telemetry unit found (the only printed casing is for the camera, CameraMount/casing). Not mounted on the vehicle | SEN55, an enclosure or mounting, and vehicle fit-up |
| D1b | "alongside an optical HUD projection subsystem" | Brief p20 | pending supervisor | Not built (Log D26). Report Scope still lists it (Introduction.tex, Scope bullet "An optical Head-Up Display subsystem projecting critical telemetry...") | Section 2 |
| D2a | "A deterministic multi-threaded software architecture" | Brief p20 | met on the bench | Eight FreeRTOS tasks pinned by core and priority, 5 ms vTaskDelayUntil, bounded queues with drop counters (main.cpp lines 1880 to 1888; Log 4.1). 200.0 to 200.5 Hz with no drops (BenchTest/logs/2026-09-25_bench_fusion_shake.log). Caveat: periodic 25 to 30 ms gaps (F6) | Confirm or fix F6. Repeat on the vehicle |
| D2b | "executing real-time sensor fusion" | Brief p20 | partly met | Dual-IMU equal-weight fusion, 5/5 boot self-tests, 149 of 149 windows fused (8fb96f3, 6d3a080; Methodology 3.15.4). Homogeneous fusion only. See section 3 | Section 3 |
| D2c | "signal processing for ride-smoothness metrics" | Brief p20 | met on the bench | RMS, std, peak-to-peak, crest factor, jerk, crossings, speed-normalised index, sine self-test within 5 percent (Log 4.1; Methodology 3.15) | Real road data |
| D2d | "and low-latency GUI rendering for the HUD" | Brief p20 | pending supervisor | No HUD. The Front camera page decodes only the newest frame and streams only while visible (DashboardIntegration/README.md), but no render latency has been measured. The 182 ms in that README is an example value, not a measurement (Log 4.2) | Section 2. Measure frame age on screen |
| D3a | "A structured technical report validating data ingestion accuracy" | Brief p20 to p21 | partly met | Bench validation in Methodology: calibration against gravity, GNSS field count, BMS decode matched an independent parser (Methodology 3.13, 3.15.2, 3.16). Results chapter is placeholders (PDF pp 67 to 68) | Field accuracy results in Chapter 4 |
| D3b | "edge processing latency" | Brief p21 | not met | Camera per-stage timing is instrumented (4e3da88) but no figures are recorded (Log 4.2). No ESP32 processing-latency figure found in the report | Record camera p50/p95 latency. Time the ESP32 feature and publish path |
| D3c | "and successful remote data synchronization with the central database" | Brief p21 | not met | One publish to a public test broker, no database, no replay of the local backlog (Methodology 3.20.1 to 3.20.2) | As B10 |

### 1.3 Project brief: GA rows, skills and extra information

| # | Requirement (quoted) | Source | Status | Evidence | What is left |
|---|---|---|---|---|---|
| G1 | "The student must architect an embedded pipeline that cleanly executes parallel execution paths: high-frequency sensor polling, compute-heavy signal processing algorithms for ride characterization, graphical HUD rendering, and networking stacks, ensuring no process blocking occurs." | Brief p21, GA 1 | partly met, HUD path pending supervisor | Polling, processing and networking run as separate tasks on separate cores (main.cpp lines 1880 to 1888; Log D3). No HUD rendering path. F6 shows flash writes briefly stall both acquisition tasks, so "no process blocking" is not yet demonstrated | F6 test and fix. A rendering path, or the agreed substitute (section 2) |
| G4 | "The student will construct field testing procedures to evaluate the accuracy and reliability of the edge-sensor array under real driving conditions." | Brief p21, GA 4 | partly met | Procedures exist: Vehicle Integration and Test Plan (Planning/SW7-VIT-001 Rev E), ToF five-step bench plan (Methodology). The plan says the trike is "permanently raised" on stands and road testing (Phase B) "is being taken to the project supervisors separately". No vehicle test has happened (Log 1). No road-test approval or date is recorded (Log, Waiting on someone) | Phase A sessions on the stands, and a Phase B road run if it can be approved |
| G4b | "They will compile and systematically analyze logged spatial and electrical datasets to successfully isolate true road roughness from nominal engine vibrations." | Brief p21, GA 4 | not met | No vehicle dataset exists. RQ4 is "Self-test only" (Table 1.1). The planned "stationary powertrain vibration baseline" and "coast-down powertrain separation" are in SW7-VIT-001 Phases A and B | A stationary powertrain run (wheel raised) gives the motor baseline even without road access. A road run gives the road signal |
| G5 | "The student will deploy advanced embedded profiling utilities, hardware debuggers, and cloud telemetry instrumentation tools." | Brief p21, GA 5 | partly met | Profiling: StatsTask rate and jitter counters, camera per-stage timing and --timing-log (4e3da88). Hardware debuggers: not found (no JTAG or debugger use recorded). Cloud instrumentation: only the public broker publish | Record at least one debugger or trace session, or state why serial instrumentation was chosen. Cloud-side receipt check |
| G5b | "They will be required to analyze and operate within the explicit bounds of the processing hardware, the available electrical draw from the main 72V battery, and wireless bandwidth limits." | Brief p21, GA 5 | partly met | Processing bounds: Pi 4 chosen detector sized for no accelerator (D5), about 7 fps. Electrical draw from the 72 V battery: not found (no power budget or current measurement in report or repo). Wireless bandwidth: not found (publish every 10 s is set, not analysed) | Measure supply current of ESP32 unit and Pi 4. Compute payload size times rate against the LTE plan |
| S1 | "Proficiency in embedded C/C++ or Python within real-time operating systems (e.g., FreeRTOS) or Embedded Linux environments." | Brief p21 | met | main.cpp (FreeRTOS, C++); hazard_detector.py on Pi OS | None |
| S2 | "Hands-on experience with sensor protocols (I2C, SPI, UART) and graphical interface development tools." | Brief p21 | met | I2C IMUs, UART modem, BLE BMS; PySide6 page, Web Serial dashboard | None |
| S3 | "Familiarity with cellular IoT modules (MQTT/HTTP over 4G/LTE-M)." | Brief p21 | met | AT+CMQTT over the A7670X (59fdd82) | None |
| E1 | "Student is required to prepare a thorough ethics proposal emphasizing the safety of testing, such as in unused parking area or permission to use a field, where the system can be tested on an actual trike vehicle." | Brief p21 | met for the application; road-test permission not recorded | Planning/Ethical Application.pdf. Revised application approved with conditions on 23 Sept (Log D16, transcript). The approval letter itself was not found in the repo. No venue for a road test is recorded | Record the test venue and permission. Keep the approval letter for the appendix (see H10) |
| E2 | "the projector device (or custom windshield) needs to be easily removable so as to ensure the vehicle can quickly be adjusted to a standard setup without any obstructions or interference from devices used in this project." | Brief p21 | pending supervisor | No projector exists. Report Limitations says "The system is designed as a removable module" (Introduction.tex). The camera casing has a clip-on 30 degree corner mount (CameraMount/casing) but is not fixed to the vehicle | If the HUD is dropped, apply the same rule to the camera, ToF and telemetry unit mounts and show it |
| E3 | Ethics questionnaire Q3 note: "should the student ... consider the baseline system is sufficiently progress to merit experimenting with ML, then a revised ethics application will be prepared a submitted." | Brief p22 | met | Revised application approved with conditions, ML in scope (Log D16) | None |

### 1.4 Research questions (from the report, tied to the brief)

| # | Requirement (quoted) | Source | Status | Evidence | What is left |
|---|---|---|---|---|---|
| RQ1 | "How accurately and repeatably can a low-cost edge-processing system characterise the trike's dynamic response to road- and powertrain-induced excitation in real time" | Report 1.2.1 | partly met | Table 1.1 "Bench-verified" for acquisition and calibration. Nothing on the trike | Vehicle data |
| RQ2 | "Which HUD information hierarchy, layout, and update strategy can present safety-critical telemetry while limiting visual clutter and driver distraction?" | Report 1.2.1 | pending supervisor | Table 1.1 "Outstanding". HUD on hold (D26) | Section 2 |
| RQ3 | "What end-to-end latency, data-loss, and recovery performance can be achieved across sensor acquisition, edge processing, local logging, and 4G/LTE synchronisation?" | Report 1.2.1 | partly met | Acquisition drop counts and one publish. No latency figures, no recovery test | Latency and outage-recovery measurement |
| RQ4 | "Which time- and frequency-domain features most effectively separate road-induced vibration from repeatable motor and powertrain vibration?" | Report 1.2.1 | not met | "Self-test only" (Table 1.1). No frequency-domain features implemented (Log 4.1 lists time-domain features only) | Powertrain baseline plus road data. Add a spectral feature or narrow the RQ to time domain |

### 1.5 Course handouts: report

| # | Requirement (quoted) | Source | Status | Evidence | What is left |
|---|---|---|---|---|---|
| H1 | "Single column format" | Intro L. s11; L2 s7 | met | Report PDF | None |
| H2 | "Font type – Times New Roman" (Intro L.), "Times New Roman font, font size 11" (L2) | Intro L. s11; L2 s7 | not met | The PDF uses LMRoman12 at 12 pt (fonts read from PDF page 13). Project Report Template.tex line 8: \documentclass[a4paper,12pt]{report} | Switch to Times New Roman (fontspec under XeTeX/Tectonic) at 11 pt |
| H3 | "Line spacing - single line space" | Intro L. s11 | not met | \onehalfspacing in Project Report Template.tex; \parskip = 6mm | Single spacing. This, with H2, will also cut many pages |
| H4 | "Maximum number of content pages for the report should be 50, i.e. excluding Table of Contents, Appendix, References. Severe penalties for overly long reports, including outright failure." | Intro L. s11; L2 s7 | not met | 62 pages (PDF pp 11 to 72). Log F15 | Reformat (H2, H3) first, then cut. Results, Discussion and Conclusions still have to be added inside the 50 |
| H5 | "Stipulate number of words of the body of your report under your Plagiarism declaration." | Intro L. s11; L2 s7 | not met | Declaration page (PDF p2) has no word count | Add the count |
| H6 | "Written reports (10 000 to 15 000 words plus tables, diagrams and appendices)" | GA template p4, GA 6 descriptor | likely not met | A rough count of PDF pp 11 to 72 gives about 18,800 words (this count includes tables, captions and running heads, so the body alone is lower, but probably still over 15,000) | Measure properly (texcount) and cut to 15,000 or less |
| H7 | "Be sure that your project title and descriptions reflect the work you have done" | L2 s7 | pending supervisor | Title, Terms of Reference, abstract, Scope and RQ2 all describe a windshield HUD (PDF pp 1, 3, 5, 15). Kept until the supervisor agrees (Log 6) | Update after the decision |
| H8 | "GA Appendix: As part of your project report, include an appendix that describes how you met the six Graduate Attributes for your particular project." | L2 s7; Intro L. s11 | partly met | Appendix A.1 covers GA 1, 4, 5, 6, 8, 9 (PDF pp 81 to 82). GA 6 entry is only "This report." GA 10 is listed as partial in L2 s3 and as "*GA 10: Professionalism" in Intro L. s4, and not covered | Expand the entries with results, add GA 10 |
| H9 | "Ethics approval letter – Attach the ethics approval letter as a separate appendix." | L2 s7 | not met, conflicts with a student rule | No such appendix. Log D20: "The report must not mention the ethics application, approval or protocol number". The approval letter file was not found in the repo | This is a course requirement. Raise D20 with the supervisor before submission |
| H10 | Report contents: "Cover Page (Title, Author, Supervisor, Purpose & Date)" | L2 s10 | met | PDF p1 | Title may change (H7) |
| H11 | "Abstract, ToC, Declaration (see the new standard), word count of the body of the report." | L2 s10 | partly met | Abstract is marked draft (PDF p5). ToC and declaration present. "New standard" declaration: not checked, the standard text was not in the sources. No word count | Final abstract, word count, check the declaration wording against Amathuba |
| H12 | "Introduction", "Literature review", "Methodology &/ Design" | L2 s10 | met, over length | Chapters 1 to 3 (PDF pp 11 to 66) | Cut |
| H13 | "Results & Analysis" | L2 s10 | not met | Chapter 4 is one-line placeholders (PDF pp 67 to 68) | Write it. Bench results already in Methodology can move here |
| H14 | "Conclusions & Recommendations" | L2 s10 | partly met | Conclusions is a one-paragraph placeholder (PDF p70). Recommendations 7.1 is written (PDF pp 71 to 72). Discussion placeholder (PDF p69) | Write Discussion and Conclusions |
| H15 | "Bibliography/References (IEEE style)" | L2 s10 | met | 70 entries, IEEE (PDF pp 73 to 80) | None |
| H16 | "We want you to include, in one of the Appendices, example(s) of what prompts were used, what you submitted to the AI to write/improve, and what you received and used." | L2 s12 | partly met | Appendix A.3 is a general statement with no example prompts (PDF p82) | Add two or three concrete prompt examples |
| H17 | "Pre-submission drafts: multiple submissions", "FINAL submission – SINGLE submission" (Turnitin) | L2 s6 | not yet due | Pre-submission opens 6 Oct | Submit a draft in the pre-submission tab early |
| H18 | "Final Project Report submission on Amathuba", 27 Oct 23h59 | Intro L. s6; L2 s2 | not yet due | | See section 5 |
| H19 | "Late submission: 1 day late -5%, 2 days late -15%, no marking after 48h (2 days) late" | Intro L. s10 | information | | |
| H20 | "Any GA failed = course failed, report mark<50% = course failed" | Intro L. s10 | at risk for GA 4 | GA 4 evidence depends on field data (G4, G4b) | Field data |

### 1.6 Course handouts: DP, GA form, presentation, poster, Open Day

| # | Requirement (quoted) | Source | Status | Evidence | What is left |
|---|---|---|---|---|---|
| P1 | "GA Tracking Forms due - 25 Sep, 23h59PM" | Intro L. s6; L2 s2 | met | Signed 24 Sept by student and supervisor, DP circled Y, "DP satisfied" (Signed GA form p1; GA Tracking Form/OKTSAM001 GA Tracking Form - Signed.pdf, 18d7e24) | None. GA6 text is stale (F13) but signed, leave as is |
| P2 | "DP requirements: Meetings with supervisor to discuss progress towards satisfying the Gas, signed and completed GA tracking form, oral & poster presentation, participation in Open Day" | Intro L. s10; L2 s4 | partly met | GA form done. Presentation, poster and Open Day are in November | Attend all three |
| P3 | "Ethics forms due – 13 Aug, 23h59" | Intro L. s6 | not verified | Submission date of the first application is not recorded in the log. Revised application approved 23 Sept (D16) | None if already done |
| P4 | "Presentation should be no longer than 10 minutes", "Questions & Answers: 5 min" | L2 s25 | partly met | 12-slide deck, talking points timed for 10 minutes (Presentation/SW7_Talking_Points.md) | Rehearse and time |
| P5 | "Bring Presentation on Flash Drive (No google slides)" | L2 s26 | met in format | SW7_Final_Presentation.pptx | Copy to a flash drive |
| P6 | Deck content: "Approach, results, interpretation, conclusions: very important!" | L2 s27 | partly met | Slide 11 is a field-test placeholder. Slide 12 still says "Build and evaluate the HUD". Slide 10 already says the detector runs live at about 7 fps (the log's F13 note about slide 10 is out of date) | Field results, pivot wording |
| P7 | "Size A1 Portrait" | L2 s17 | met | SW7_Poster_A1.pptx is 84.1 x 118.9 cm, one page | None |
| P8 | "Your name, your supervisor, your affiliation (University of Cape Town)" | L2 s20 | met | Poster header | None |
| P9 | "Title 70 pt", "Headings 56 pt", "Body Text: 32 pt" (typical) | L2 s21 | partly met | Poster font sizes range 24 to 78 pt; some text is below 32 pt | Enlarge small text if space allows |
| P10 | "Maybe provide QR code to Github repository?" | L2 s20 | optional, not found | No QR code found in the poster text | Optional |
| P11 | Poster content currency | L2 s19 | partly met | Poster "Next" still says "build the HUD"; no camera results | Update after the decision and field test |
| P12 | "Open Day will take place on 18 November 2026" | L2 s24 | not yet due | | A demo: live camera page and telemetry dashboard are the obvious exhibits |

## 2. What the HUD pivot changes

Decision D26 (28 Sept, pending supervisor): the HUD is on hold, and the existing vehicle dashboard plus the forward camera is used instead. The student's reasons: the dashboard already carries what the HUD would show, two displays distract, and the camera fits the programme's move towards autonomy. Nothing below is decided.

Brief text the pivot touches:
- Title: "Windshield HUD" (Brief p20).
- Description: "drive a dynamic graphical user interface projected as a Heads-Up Display (HUD) onto a custom handlebar-mounted front windshield visor", mapping "speed, battery State-of-Charge, fleet notifications" and rendering "active driver alerts based on localized sensor feeds" (Brief p20).
- Deliverable 1: "alongside an optical HUD projection subsystem" (Brief p20).
- Deliverable 2: "low-latency GUI rendering for the HUD" (Brief p20).
- GA 1 row: "graphical HUD rendering" as one of the parallel execution paths (Brief p21).
- Extra information: the removable projector rule (Brief p21).
- In the report: RQ2, Table 1.1 row RQ2, Scope bullet for the optical HUD, the "Graphical HUD rendering" thread in 1.3.1, Results 4.7, Literature 2.6, gap G4 (D11), the title, Terms of Reference and abstract. Deck slide 12 and the poster "Next" line.
- L2 s7: "Be sure that your project title and descriptions reflect the work you have done". If the pivot is agreed, the title and descriptions have to change with it.

What exists that could stand in:
- The vac-work dashboard on the Pi 5 already shows speed and SoC (its README lines 10 and 13) and has an advisory panel with voice output (lines 17 and 46). This is another team's work and should be credited as such.
- SW-7's Front camera page (DashboardIntegration/front_camera_page.py, 7b0601f): live annotated view, alert list in the dashboard's colours, fps and latency display, and an alerts_changed(list) signal so the driving page could show a toast without the video. Tested offscreen only.
- The detector's /alerts endpoint (57dd18e) and per-stage latency instrumentation (4e3da88).
- Report Literature.tex line 75 already argues that "HUD benefits diminish when visual complexity, optical limitations, and cognitive workload are ignored", and D13 records the luminance problem (a sunlight-readable combiner needs 50,000 to 100,000 nit sources; MCU panels reach about 1,000).

Options for the supervisor:

Option A. Replace the HUD with alerts on the existing dashboard, and say so openly.
- Deliverable 1 optical projection: descoped, with the reasons written up (luminance, distraction, duplication of the dashboard). It is not met under this option, and the report should say that rather than claim it.
- Deliverable 2 GUI rendering: argued as met by the Front camera page and an alert toast on the driving page, provided render latency is measured (sensor timestamp to frame on screen, and alert onset to toast).
- GA 1 rendering path: the detector, the /alerts server and the dashboard page form a separate rendering path that must not block acquisition or networking. That argument needs a measurement on the Pi 5.
- RQ2 reworded, for example: "How should camera and proximity alerts be presented on the existing dashboard to limit distraction, and what end-to-end alert latency does the system achieve?" Evidence would be the alert hierarchy (bands, hysteresis D28), measured latency, and a glance observation if a road run happens.
- Work needed: wire the page into the dashboard (four edits, needs the dashboard team), test on the Pi 5 against the live detector, build the toast, measure latency. Change the title and scope.

Option B. Keep a reduced head-up element for alerts only.
- For example a small light bar or a single-symbol display in the forward view, driven by /alerts (and later the ToF), with speed and SoC left on the dashboard.
- This keeps some of Deliverable 1 and the GA 1 rendering path in their original form and answers the "two displays" objection by showing only one thing head-up.
- Effort and hardware are not scoped in the repo, and it must meet the removable rule (E2). It is the riskiest option in 29 days.

Option C. Keep the HUD in the report as design and analysis only.
- RQ2 answered by an information-hierarchy design and a feasibility analysis (luminance, optics, glance guidance), with the build recorded as future work in Chapter 7.
- The dashboard camera page is reported as the implemented driver interface.
- Lowest effort. Deliverable 1 projection and Deliverable 2 HUD rendering stay not met, and the report must say so.

Under every option the title, Terms of Reference, abstract, Scope, Table 1.1 and Results 4.7 need editing once the decision is made.

## 3. Sensor fusion

What the brief asks: Deliverable 2, "A deterministic multi-threaded software architecture executing real-time sensor fusion" (Brief p20). The brief does not say which sensors are to be fused.

What is achieved:
- Dual-IMU fusion on the ESP32 (8fb96f3, verified live in 6d3a080; Methodology 3.15.4; D24). Equal-weight mean of RMS, std, peak-to-peak, jerk and speed index from two MPU6050s; a disagreement figure; pairs fused only if the windows ended within 0.5 s; 3 s single-sensor fallback; 5 boot self-tests pass. In the 150 s bench session, 149 of 149 windows were fused from both sensors with skew under 1 ms (BenchTest/logs/2026-09-25_bench_fusion_shake.log).
- This is real-time and runs on the target board. It is fusion of two identical sensors measuring the same quantity (redundancy averaging). Inverse-variance weighting reduces to the mean because the sensors are the same part with the same settings (D24). It has only run on the bench.
- The speed-normalised roughness index combines IMU and GNSS speed. It is implemented but has never produced a value, because there has been no GNSS fix (F9).
- Camera to IMU time alignment within about 1 s (sync pulse, lens-cover test). This is time alignment, not fusion.

What is not achieved:
- No fusion across different sensor types has produced data.
- The camera and ToF are not fused: the ToF sensor is not received or integrated (Log 4.6; Methodology). Arrival of the VL53L5CX is not recorded in the log beyond "sourced, not received".

What camera plus ToF fusion could add:
- The camera gives object class and a distance from bounding-box width with one fixed width per class and an uncalibrated 600 px focal length (Log 4.2). The heuristic reads a side-on bicycle at about a third of its true distance (camera-integration-prompt.md estimate).
- The VL53L5CX gives measured distance in an 8x8 grid over 63 degrees, rated to 4 m, with no classification (Methodology).
- Fusing them: map each detection's bounding-box columns to ToF zone columns, and inside the ToF range use the measured distance for the band, keeping the camera's class. Outside the ToF range, fall back to the camera estimate. The same pairing can calibrate the focal length (Recommendations 7.1 already proposes calibrating against the ToF).
- Practical points: the ToF is currently planned for the ESP32 (Methodology: "a value published alongside the rest of the telemetry"), while the detector runs on the Pi 4. Fusion is simpler if the ToF is wired to the Pi 4's I2C. The two fields of view must be aligned and measured. Outdoor ToF range under sunlight has to be measured, not assumed from the datasheet.
- This would give heterogeneous fusion that is easy to explain and directly improves the driver alerts, which also helps the pivot argument in section 2.

What SEN55 is for in the brief:
- "microclimate profiles, and localized air quality metrics to detect environmental anomalies (e.g., plastic burning)" (Brief p20). That is anomaly detection, not fusion.
- A simple approach once the sensor arrives: log PM1 to PM10, VOC index, NOx index, T and RH with GNSS position; flag an anomaly when PM2.5 or the VOC index rises above a rolling baseline by a set margin, and tag the location. The SEN55 is ordered and not received (Methodology.tex line 362), and arrival is not recorded in the log.

Plain summary: real-time sensor fusion exists, but only between two identical IMUs on the bench. Fusion across different sensors has not been demonstrated. The environmental and air-quality function in the brief has not started beyond ordering the part.

## 4. Completion estimate

Weighting. The report is 90 percent of the course mark and the oral 10 percent (Intro L. s10), and any failed GA fails the course. The report can only be as complete as the work it reports, so I weighted areas by how much of the examined report and GA evidence depends on them, not by hours already spent.

| Area | Weight | Estimate | Weighted | Basis |
|---|---|---|---|---|
| Report (writing and compliance) | 25% | 40% | 10.0 | Chapters 1 to 3 written; Results, Discussion, Conclusions empty; 62 of 50 pages; wrong font, size and spacing; no word count, ethics appendix or AI prompt examples |
| Field testing and analysis (GA 4, RQ1, RQ3, RQ4) | 20% | 5% | 1.0 | Test plan exists; no vehicle session, no dataset, no road-test approval recorded |
| Telemetry unit firmware and data path | 15% | 70% | 10.5 | Acquisition, calibration, features, fusion, BMS decode, local log, MQTT all working on the bench; v0.5.0 unflashed; no GNSS fix; BMS intermittent; no SW-6 link; no database; F6 open |
| Sensor payload (SEN55, ToF, powertrain tap) | 10% | 10% | 1.0 | Parts chosen and ordered, optocouplers received; nothing integrated |
| Camera hazard detector | 10% | 60% | 6.0 | Live at about 7 fps, person confirmed, /alerts, service file; focal length, other classes, latency figures, outdoor and vehicle tests outstanding |
| Driver interface (HUD or dashboard substitute) | 10% | 25% | 2.5 | No HUD. Dashboard camera page built and tested offscreen only; decision pending |
| Presentation, poster, Open Day | 5% | 55% | 2.75 | Deck and A1 poster exist in the right format; field results and pivot wording missing; not rehearsed |
| Administration (GA form, DP, ethics) | 5% | 100% | 5.0 | GA form signed with DP, revised ethics approved |
| Overall | 100% | | about 39% | Rounded: about 40 percent, with a plausible range of 35 to 45 percent |

The three things that would move the estimate most before 27 October:

1. Get vehicle data. Run the Phase A sessions in SW7-VIT-001 on the raised trike, in particular the energised powertrain run (the stationary powertrain vibration baseline). If at all possible, add a short Phase B road run in an approved area. This is the only source of evidence for GA 4 ("under real driving conditions", "isolate true road roughness from nominal engine vibrations"), RQ1, RQ3 and RQ4, and for the Results chapter. It needs a date from Yusuf Vawda and a supervisor decision on Phase B. Neither is recorded.
2. Make the report compliant and fill it. Switch to Times New Roman 11 pt with single spacing, then cut to 50 pages and 15,000 words. Move bench results out of Methodology into Results and Analysis. Write Discussion and Conclusions. Add the word count, the ethics approval letter appendix (after resolving D20 with the supervisor), AI prompt examples and GA 10. Use the pre-submission window from 6 October.
3. Settle the HUD question at the supervisor meeting, then close the driver-interface deliverable in the agreed form. Under Option A this means running the Front camera page on the Pi 5 against the live detector, measuring render and alert latency, and changing the title, RQ2 and scope. If the VL53L5CX arrives, camera plus ToF distance fusion would strengthen both this item and the sensor-fusion deliverable.

## 5. Deadlines from the handouts

| Date (2026) | Event | Source | Status |
|---|---|---|---|
| 30 Jul | Lectures start, topics final, introductory lecture | Intro L. s6; L2 s2 | Past |
| 13 Aug, 23h59 | Ethics forms due | Intro L. s6; L2 s2 | Past; first submission date not recorded; revised application approved 23 Sept |
| 17 Aug to 4 Sep, 14 to 18 Sep | Students to maintain GA forms | Intro L. s6; L2 s2 | Past |
| 17 Sep | Lecture 2 | Intro L. s6; L2 s2 | Past |
| 25 Sep, 23h59 | GA tracking forms due | Intro L. s6; L2 s2 | Done, signed 24 Sept |
| 2 Oct | DP list published | Intro L. s6; L2 s2 | Upcoming |
| 6 Oct | Pre-submission of project report opens, open till 26 Oct | Intro L. s6; L2 s2 | Upcoming |
| 26 Oct | Pre-submission closes | Intro L. s6; L2 s2 | Upcoming |
| 27 Oct, 23h59 | Final project report submission on Amathuba (single Turnitin submission) | Intro L. s6; L2 s2, s6 | Upcoming, 29 days away |
| 28 Oct | Report 1 day late: minus 5 percent | Intro L. s10 | |
| 29 Oct | Report 2 days late: minus 15 percent; no marking after 48 h | Intro L. s10 | |
| 2 to 13 Nov | Marking period | Intro L. s6; L2 s2 | |
| 16 and 17 Nov | Oral and poster presentation | L2 s2, s24 | Upcoming |
| 18 Nov | Open Day (class picture, demos, open day presentation and prizegiving) | L2 s2, s24 | Upcoming |

Notes on the dates:
- The Intro Lecture (s6) gives the presentations as 16, 17 and 18 Nov with Open Day on 19 Nov. Lecture 2 (s2 and s24) gives 16 and 17 Nov with Open Day on 18 Nov. Lecture 2 is later, so this audit uses its dates.
- Lecture 2 s9 says "Assessment process is currently being revised", but "the dates of oral presentations and Open Day will remain the same". Slide 25 says presentation times "may change".

## Requirements that could not be fully mapped

- "fleet notifications" (Brief p20): not found anywhere in the repo or report; no definition of what a fleet notification is.
- "for route optimization" (Brief p20): not found in SW-7. The vac-work dashboard has route-aware features, but that is not this project.
- "hardware debuggers" (Brief p21, GA 5): no record of any debugger use.
- "the available electrical draw from the main 72V battery" and "wireless bandwidth limits" (Brief p21, GA 5): no measurement or analysis found.
- "Declaration (see the new standard)" (L2 s10): the new standard text was not in the sources, so the declaration wording could not be checked.
- Ethics approval letter (L2 s7): the letter file was not found in the repo, and D20 conflicts with the requirement to attach it.
- Marking rubrics (L2 s14 "Marking rubrics on Amathuba"): not in the sources, so marking weights inside the report could not be checked.
