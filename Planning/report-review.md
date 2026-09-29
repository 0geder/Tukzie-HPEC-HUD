# Examiner-style review of the SW-7 report draft

Reviewed: "OKTSAM001 SW7 Report Draft.pdf", 71 PDF pages, dated 29 September 2026, with the .tex sources.
Criteria used: Lecture 2 (slides 3, 7, 9, 10, 12), the Intro Lecture (slides 4, 10, 11), the GA descriptors in "GA Tracking Form incl GA5.pdf" (pages 3 to 5), and the SW-7 brief (pages 20 to 22 of the topics list).
Context used: PROJECT_LOG.md and Planning/brief-compliance.md.

Page convention: "p." is the PDF page. In the main body the printed page number is the PDF page minus 10 (Chapter 1 starts on PDF p.11, printed page 1).

The official marking rubric ("Marking rubrics on Amathuba", L2 slide 14) was not available. Every grade and rating below is an estimate from the GA descriptors and the handout requirements, not from the rubric.

Checked after the review: the calibration arithmetic flagged in section 4 is confirmed. 10.35 to 10.39 m/s2 times 0.9773 gives 10.12 to 10.15, and 9.55 to 9.60 times 0.9901 gives 9.46 to 9.51, so the stated factors cannot produce the stated convergence to 9.80 to 9.81. The factors that would are about 0.946 and 1.024.

## 1. Overall verdict

Chapters 1 to 3 hold a lot of real, careful engineering work. The literature review is critical and well synthesised, and the bench work is detailed and honest about its limits. The report is not yet a report, though. Chapter 4 (Results, p.54 to 55), Chapter 5 (Discussion, p.56) and Chapter 6 (Conclusions, p.57) contain only one-line placeholders, the abstract opens with "Draft abstract, to be revised once field results are available" (p.5), and none of the four research questions is answered anywhere. Every measured result sits inside Methodology, which reads as a chronological lab diary ("In a later lab session", p.31; "during this development session", p.27 and p.34). The HUD, which is in the title, the Terms of Reference, the scope and RQ2, has no methodology section at all.

Indicative grade band as it stands today: fail (below 50). The course fails any student who fails a GA (Intro Lecture slide 10). With no results analysis and no conclusions, GA4 ("analysis and interpretation of data ... to provide valid conclusions") and the GA1 phrase "reaching substantiated conclusions" cannot be credited. On its own, the quality of what is already written (Introduction, Literature Review, Methodology) is at about the low to mid 60s level. If the bench data already collected were moved into a proper Results chapter with analysis, and Discussion and Conclusions were written, the low to mid 60s are likely even without vehicle data. With on-vehicle data answering RQ1, RQ3 and RQ4, the cuts to length, and the compliance items fixed, the 70s are realistic. 75+ needs field results that are analysed with statistics and tied back to the literature.

Length: the declaration states 19 370 words (p.2) against the GA6 range of "10 000 to 15 000 words". The body runs from printed page 1 to 49, against a limit of 50, and three chapters are still empty. The student has said length will be cut later, so it is not treated as the main quality judgement here. The risk is real, though: the handout warns of "severe penalties for overly long reports, including outright failure" (L2 slide 7), and filling Results, Discussion and Conclusions will add roughly 6 to 10 pages.

## 2. Graduate attributes

GA10 is included because L2 slide 3 lists "GA10 Engineering Professionalism (partial)", Intro slide 4 lists "*GA 10: Professionalism", and L2 slide 9 names "demonstrating ability to consider ethical implications" as the attribute "most commonly failed".

| GA | What the descriptor and brief ask for | Rating now | Evidence in the report | Additions that would lift it |
|---|---|---|---|---|
| GA1 Problem solving | Descriptor: "Identify, formulate, research literature and analyse complex engineering problems reaching substantiated conclusions using first principles of mathematics...". Brief: "architect an embedded pipeline that cleanly executes parallel execution paths: high-frequency sensor polling, compute-heavy signal processing ..., graphical HUD rendering, and networking stacks, ensuring no process blocking occurs." | Weak | Clear formulation: 1.2.1 (p.12), four RQs, Table 1.1 (p.13). First-principles choices: 200 Hz from ISO 2631-1 and the sampling theorem (3.11.1, p.28); vTaskDelayUntil against drift (p.29); non-blocking queues (p.29); magnitude chosen for rotation invariance (3.15, p.34); speed normalisation (3.15.3, p.36). Parallel paths: Fig 3.1 (p.29). | Write Conclusions that answer each RQ. Add numbered equations for every feature (RMS, crest factor, jerk, threshold count, speed index, disagreement figure, pinhole distance). Report the flash-write stall (p.52) as a direct test of "no process blocking" and fix it or bound it. Add a latency budget across acquisition, processing, logging and publishing. The "graphical HUD rendering" path is missing: either build a rendering path or state the agreed substitute and measure it. |
| GA4 Investigations, experiments, data analysis | Descriptor: "research methods, including research-based knowledge, design of experiments, analysis and interpretation of data, and synthesis of information to provide valid conclusions." Brief: "construct field testing procedures to evaluate the accuracy and reliability of the edge-sensor array under real driving conditions ... isolate true road roughness from nominal engine vibrations." | Weak | Good hypothesis-driven bench investigations: GNSS field count (3.13, p.32 to 33), BMS service UUID (3.16.4, p.40), flash-write stall test with logging on and off (3.20.1, p.52), calibration under dynamic disturbance (3.15.2, p.36), lens-cover offset bound (3.12.5, p.32). No field procedure appears in the report. RQ4 is "Self-test only" (Table 1.1, p.13). No frequency-domain feature is implemented although RQ4 asks for "time- and frequency-domain features". | Put the field test procedure (the SW7-VIT-001 plan) into Methodology as a designed experiment: independent variables (speed, payload, surface, motor on or off), repetitions, controls, acceptance criteria and safety. Run at least the stationary powertrain baseline with the wheel raised. Present distributions rather than single values (jitter histogram, feature distributions for still, powertrain-only and road), with repeat counts and spread. Add a spectral feature (band energy or PSD) or narrow RQ4 to the time domain. |
| GA5 Engineering tools | Descriptor: "create, select and apply and recognise limitations of appropriate techniques, resources and modern engineering and IT tools, including prediction and modelling". Brief: "deploy advanced embedded profiling utilities, hardware debuggers, and cloud telemetry instrumentation tools ... operate within the explicit bounds of the processing hardware, the available electrical draw from the main 72V battery, and wireless bandwidth limits." | Adequate | PlatformIO, FreeRTOS, ESP-IDF timers (3.2, 3.11); chip-detection and ROM-banner evidence (3.10, p.27); OpenSCAD with full CSG render (3.19.6, p.46); rpicam, TFLite/LiteRT (3.19.7); Web Serial dashboard and bench console (p.37); per-stage camera latency instrumentation (p.50). Limitations are stated well throughout. | Add the three brief items that are absent: a power budget (measured current of the ESP32 unit and Pi 4, related to the 72 V supply through the converter), a bandwidth budget (payload bytes times publish rate against the LTE plan), and either a debugger or trace session or a justified reason why serial instrumentation was used instead. Report the camera p50 and p95 latency figures, since the tooling already exists. Add a "prediction and modelling" element, for example a predicted vs measured jitter or latency, or a simple quarter-car argument for where road energy should appear in the spectrum. |
| GA6 Professional communication | Descriptor: "communicate effectively ... Written reports (10 000 to 15 000 words plus tables, diagrams and appendices) should cover material at exit-level." Handout: 50-page limit, IEEE references, stated word count. | Weak | Format compliant: Times New Roman 11 pt single spacing (the fonts embedded in the PDF confirm this), word count stated (p.2). The literature review is well written. Against: 19 370 words; three empty chapters; a draft abstract; notes to self left in the text ("discussed further in Chapter 2/Chapter 3 as appropriate", p.40; "should be confirmed ... before the report claims which physical pack this section characterises", p.40; "they will determine a latency target for the report", p.50); broken cross-references (section 4 below); Fig 3.1 is ASCII text art (p.29); Fig 3.2 is a screenshot with unreadable axes on a page that is mostly white space (p.39); 31 of 70 references are never cited. | Write the three chapters. Remove every drafting artefact. Convert the lab-diary narrative into structured design and test sections. Replace Fig 3.1 with a drawn diagram and add a system block diagram at the start of Chapter 3. Plot the logged data directly with labelled axes and units. Clean up the references. Cut to 15 000 words. |
| GA8 Individual work | Descriptor: "function effectively as an individual". Brief context: much of the platform is inherited from vacation-work teams. | Adequate | The individual decisions are visible: Pi 4 rather than Pi 5 so the inherited deployment is not put at risk (3.19, p.43); VL53L5CX over VL53L1X (p.48); keeping MQTT inside the modem task because the UART has no lock (3.20, p.51); the data-handling design of the detector (p.47). A.1 (p.65) gives two lines. | State in Chapter 1 or 3 exactly what was inherited (dashboard, BMS reference parser, drivetrain report [62]) and what was built. The AI-use declaration must match the actual extent of AI assistance (see section 3), otherwise authorship of the work is open to question. Expand A.1 with a short paragraph listing the student's own design decisions and the evidence for each. |
| GA9 Independent learning | Descriptor: "Reflection of self-learning to begin to recognise if what has been covered meets the needs of the activity", "Openness to constructive feedback, awareness of own limitations". | Adequate | Strong raw evidence of self-correction against primary sources: board schematic (3.12.1, 3.18.1), AT manual v1.09 (3.13.2, 3.20.3), live tests overturning assumptions (3.13.1, 3.16.4). Limitations stated repeatedly. | This evidence is scattered through a diary and never reflected on. Add a short reflective section, in Discussion or in A.1, covering what had to be learned (FreeRTOS timing, BLE GATT, A76xx AT set, TFLite on the Pi), how, what went wrong, and what would be done differently. Put the faults into one table (symptom, hypothesis, test, cause, lesson) instead of eight narrative subsections. |
| GA10 Professionalism and ethics (partial) | L2: "demonstrating ability to consider ethical implications (most commonly failed)". Brief: "thorough ethics proposal emphasizing the safety of testing ... the projector device ... needs to be easily removable". | Weak | Some good material: the detector's data minimisation (no frames stored, no face or plate recognition, five logged fields, advisory only, p.47); credentials kept out of code and the public broker used only for path validation (3.20, p.51 and p.52). There is no ethics, safety or risk section. The removability requirement appears only as a "limitation" (p.15). There is no ethics approval letter appendix (see the checklist). | Add a short professional and ethical considerations section: test safety (72 V pack, trike on stands, approved area), camera privacy framed under POPIA, data security of the telemetry path, and removability of mounted equipment. Add GA10 to Appendix A. The ethics letter conflict is flagged for the supervisor below. |

## 3. Required-contents checklist

| Item (source) | Status | Where | Note |
|---|---|---|---|
| Cover page: title, author, supervisor, purpose, date (L2 s10) | Present | p.1 | Title still promises a "Windshield HUD" that does not exist in the report. L2 s7 says "Be sure that your project title and descriptions reflect the work you have done". The department is given as "Dept. of Electrical and Electronics Engineering" and also as "Department of Electrical Engineering" on the same page. |
| Abstract (L2 s10) | Partial | p.5 | Begins "Draft abstract, to be revised...". It has no conclusion sentence and does not mention the HUD outcome. |
| Table of contents (L2 s10) | Present | p.6 to 10 | No list of figures or list of tables. These are not required, but examiners expect them. |
| Declaration (L2 s10, "new standard") | Present, wording not checked | p.2 | The four standard clauses and a signature image. The "new standard" text was not in the sources, so it could not be checked. L2 s11 says plagiarism includes AI tools; consider adding a clause that points to A.3. |
| Word count of body under the declaration (L2 s7, Intro s11) | Present | p.2 | 19 370, which is over the GA6 range of 10 000 to 15 000. |
| Format: single column, Times New Roman 11 pt, single spacing (Intro s11, L2 s7) | Present | whole PDF | Confirmed from the embedded fonts (TimesNewRomanPSMT) and the dominant 10.9 pt text size. |
| Maximum 50 content pages (Intro s11, L2 s7) | At risk | printed p.1 to 49 | 49 pages with three chapters empty. |
| Introduction | Present | p.11 to 16 | See section 4. |
| Literature review | Present | p.17 to 22 | See section 4. |
| Methodology and/or design | Present, over length | p.23 to 53 | 31 of the 49 body pages. Results are embedded in it. No HUD section. |
| Results and analysis | Missing | p.54 to 55 | Eight headings, each with one sentence describing what will go there. |
| Discussion | Missing | p.56 | One paragraph of planned themes. |
| Conclusions | Missing | p.57 | One sentence of intent. |
| Recommendations | Partial | p.58 to 59 | Only 7.1 (generic obstacle detection). There are no recommendations on the telemetry unit, the flash stall, the BMS link, the HUD or field testing, although Chapter 3 lists many of these as future work. |
| References, IEEE style (L2 s10) | Partial | p.60 to 64 | See section 6. |
| Appendices, simulation and extra results (L2 s10) | Present | p.65 to 71 | App B figures and App C evidence index are useful. |
| GA appendix describing how the six GAs were met, "specific to your particular project" (L2 s7, Intro s11) | Partial | p.65 | A thin table. GA6 says only "This report." GA10 is absent. The entries point to sections but do not describe how each GA was met. |
| Ethics approval letter as a separate appendix (L2 s7) | Missing | none | Risk for the supervisor to decide (see below). |
| AI-use appendix with example prompts, what was submitted and what was received and used (L2 s12) | Partial | p.66 | A general statement with no prompts. It is limited to report organisation, wording and LaTeX. The body itself mentions a language model (p.51), and the lens-cover test describes "the operator sending an explicit message ... immediately answered by querying the Raspberry Pi's wall clock" (p.32), which suggests an assistant was running commands. The project log refers to Claude Code session transcripts, agents and an automated research pipeline. If AI helped with code, debugging or literature search, A.3 must say so, with example prompts. As written, the statement looks narrower than the actual use, and L2 s11 treats uncredited AI work as plagiarism. |
| Title and descriptions match the work (L2 s7) | Partial | p.1, p.3, p.5, p.14 | The title, Terms of Reference, abstract and Scope bullet ("An optical Head-Up Display subsystem projecting critical telemetry...", p.14) all describe a HUD. The HUD decision is pending, but as it stands the report describes a deliverable that it never reports on. |

Ethics letter risk for the supervisor. The student's standing decision (Log D20) is that the report does not mention the ethics application or approval. L2 slide 7 says "Ethics approval letter – Attach the ethics approval letter as a separate appendix", and the brief says the student "is required to prepare a thorough ethics proposal emphasizing the safety of testing". The camera detector processes images of the public, and the brief's ethics questionnaire said a revised application would be needed for any ML. An examiner who finds an ML camera system and no ethics appendix may treat GA10 as not demonstrated. Not resolved here. Raise it with A/Prof. Winberg before the pre-submission window opens on 6 October.

## 4. Chapter-by-chapter review

### Front matter (p.1 to 10)

Strengths: complete cover, a signed declaration with a word count, and a concise Terms of Reference.

Weaknesses: the draft abstract (p.5). The Terms of Reference says "embedded high-performance-computing telemetry unit", while the rest of the report uses HPEC, "high-performance embedded computing". The abstract states that the detector runs "at about 7 frames per second, with distance calibration outstanding, to be complemented by a multi-zone time-of-flight sensor", which reports plans rather than findings.

Fixes: write the abstract last, as problem, approach, key numbers, and the answer to each RQ. Make the terminology consistent. Add lists of figures and tables.

### Chapter 1 Introduction (p.11 to 16)

Strengths: good motivation with sourced numbers (UN 68% [2], Dar es Salaam cost savings [3], NHTSA 2 s and 12 s glance limits [6]). The problem statement in 1.2.1 (p.12) is precise: "acquire synchronised data reliably on a high-vibration, power-constrained vehicle; distinguish road-induced motion from vehicle-specific dynamics; maintain bounded processing and display latency; and preserve telemetry during intermittent cellular connectivity". Table 1.1 mapping RQs to requirements and verification is a strong device.

Weaknesses:
- Table 1.1 says the mapping is "intended to be revisited directly in Chapter 5 (Results)" (p.13). Results is Chapter 4.
- The RQ1 row's requirement, "Dual-IMU acquisition at ≥160 Hz ... with per-sensor magnitude agreement", tests acquisition, not "how accurately and repeatably" the system characterises dynamic response. The requirement does not measure the question.
- Inconsistent numbers and terms: "IMU at ≥100 Hz" (p.15) against ≥160 Hz (Table 1.1) and 200 Hz everywhere else; "MQTT/HTTP over 4G/LTE-M" (p.15) while the hardware is LTE Cat-1 (p.23); "a safe, augmented-reality interface" (p.12) against "not full holographic or augmented-reality integration" (p.15).
- A TRL 6 target is claimed (p.12) but never reassessed.
- "This work aligns with the UCT Radar Remote Sensing Group's focus on advanced sensing" appears twice (p.13 and p.14) with no source, and its relevance is not explained.
- Limitations (p.15) include items that are not limitations ("The system is designed as a removable module") and one that is not true today ("Time constraints limit extensive field testing to urban routes only"; no field testing has been done).
- The Scope lists the HUD, the SEN55 and the ToF as components of the system (p.14), but none of the three has been built or integrated. The brief's air-quality purpose, "detect environmental anomalies (e.g., plastic burning)", is not mentioned anywhere in the report.

Fixes: correct the chapter numbers; restate RQ1's requirement as a measurable accuracy or repeatability target (for example, coefficient of variation of the index over repeated traversals); make the numbers and terms consistent; move removability to the design requirements; separate "in scope and delivered" from "in scope but not delivered", and say which is which.

### Chapter 2 Literature Review (p.17 to 22)

Strengths: this is the best chapter. It is critical rather than a list. Each source is weighed against the TUKZIE context, for example "that range is tied to the authors' phones, routes, labels, IRI thresholds, and limited test segments; it cannot be treated as an expected accuracy for the TUKZIE" (p.19), and the IRI vs vehicle response vs ISO 2631 comfort distinction (p.18 and p.19). 2.1 sets an evaluation framework, and 2.9 synthesises three concrete gaps. It reads at exit level.

Weaknesses:
- The balance no longer matches the work. 2.6 on the HUD is the longest section, yet there is no HUD. The camera object detector, now a major subsystem, is not reviewed at all: SSD, MobileNet, COCO, quantised inference on the Pi and monocular distance estimation are not covered, and the only "literature check" for it sits in Methodology with no citation (p.51).
- 2.7 (cellular synchronisation) has no academic or standards citation apart from the brief [22]: no MQTT specification, no QoS or store-and-forward literature.
- No RTOS or real-time timing literature supports 2.5 (jitter, vTaskDelayUntil, bounded queues).
- No air-quality or SEN55 literature, although the brief asks for it.
- No comparison table of related systems (sensors, sampling rate, processing platform, link, validation). Such a table would make the synthesis in 2.9 easy to check.
- Minor: 2.8 cites [64] and says it will be used "directly in that chapter"; the review should end on what it means for the design, not on forward references.

Fixes: shorten 2.6 by about half, especially if the HUD is dropped. Add a short 2.x on lightweight object detection and monocular ranging (3 or 4 sources; they are already downloaded in Report/references_pdf/camera_ml). Cite the MQTT standard and one reliability study in 2.7. Add a related-work comparison table.

### Chapter 3 Methodology (p.23 to 53)

Strengths: the engineering is real and well evidenced. The staged, single-variable debugging (3.10, p.27), the defensive GNSS parser that exposed the nine-field response (3.13.1, p.33), the logging on/off experiment that isolated the flash-write stall (p.52), and the per-stage latency instrumentation (p.50) are exactly the kind of work examiners reward. Limitations are stated plainly, for example "The rules have not yet been run against live frames" (p.49).

Weaknesses:
- Structure. The chapter is a development chronology, not a methodology. Sections such as 3.3 to 3.8 (board bring-up), 3.19.2 to 3.19.4 (USB drive partitioning, hotspot band, SSH, Wi-Fi regulatory domain) and 3.18.1 (serial routing) spend several pages on set-up faults that earn few marks at exit level. There is no system overview or block diagram before the detail begins. A reader reaches p.43 (Fig 3.3) before seeing the whole system.
- Results are buried here. Almost every number in the report is in Chapter 3: 200.0 to 200.5 Hz with no drops, 149 of 149 fused windows, skew below 1 ms (p.37 to 38); calibration factors and rest magnitudes (p.35 to 37); sync intervals of 500.1 to 500.3 ms (p.31); an offset under about 1 s (p.32); the 33 to 40 ms stalls with logging on against 5.9 ms with it off (p.52); 47 of 47 publishes and a 0.4 s reconnect (p.53); 7 fps and confidence 0.50 to 0.73 (p.49). Chapter 4 even says "Bench-level validation results are reported alongside their methods in Chapter 3" (p.54). That sentence tells the examiner that the Results chapter is empty by design.
- HUD. There is no section at all.
- Numeric inconsistency (confirmed, see the note at the top). The resting magnitudes of "approximately 10.35–10.39" and "9.55–9.60 m/s2" (p.35) need factors of about 0.946 and 1.024 to reach 9.807 m/s2, but the stated factors are "0.9773 and 0.9901" (p.36), which cannot produce "converged to 9.80–9.81". On the target board, the factors 1.0390 and 1.0245 gave rest magnitudes of 9.93 and 10.10 m/s2 (p.37). The "5–8% relative to each other, and against the true value" wording (p.35) also mixes two different comparisons. An examiner who does this arithmetic will doubt the rest of the numbers. Check the logs and restate.
- The fusion disagreement figure "ranged from 0.00 to 1.68" (p.37). For |a-b|/mean the maximum is 2, so 1.68 means the sensors disagreed almost completely in some windows. This is not discussed.
- The lens-cover method (p.32) depends on "the operator sending an explicit message at the instant of covering, immediately answered by querying the Raspberry Pi's wall clock". It is unclear who or what answered, and the sub-second bound is limited by that human and network loop. Say what the channel was, or replace the method with the LED-on-sync-pin method already proposed.
- Cross-reference errors:
  - Fig 3.1 says "GNSS polling (Sec. 3.12)", but GNSS is in 3.7 and 3.13 (p.29).
  - "the manual serial bridge established in Section 3.7" should be 3.6 (p.33).
  - "on the same basis later found to be unsafe in Section 3.11" (p.30): 3.11 contains no such finding.
  - "the empirical baselining work already described in Section 3.11" (p.35): the baselining is in 2.4.
  - "the experimental methodology described in Chapter 4" (p.34): Chapter 4 is Results.
  - "Section 3.19 above identifies the absence of a rigid camera mount" (p.46): that is in 3.19.5.
  - Appendix C says "Figures B.3 and 3.2 in Appendix B" (p.69), but Fig 3.2 is in Chapter 3.
- Drafting artefacts and out-of-register text: "discussed further in Chapter 2/Chapter 3 as appropriate" and "before the report claims which physical pack this section characterises" (p.40); "the student observed" (p.50); "they will determine a latency target for the report" (p.50); a repository log path in running text (p.52); the remark that the broker documentation "explicitly states its credentials must not be shared with a language model" (p.51).
- Figures: Fig 3.1 is monospaced text, not a figure. Fig 3.2 (p.39) is a dashboard screenshot with axis text too small to read and no axis titles, floated onto a page that is two-thirds empty. There are no plots generated from the logs, no wiring diagram, and no schematic of the IMU, sync and power connections.
- Equations: none of the features or indices is written as an equation, although the report relies on them.

Fixes: restructure into requirements and architecture (with a block diagram), hardware, firmware architecture, signal processing (with equations), BMS, camera and proximity, communications and logging, and test methodology (bench and field experiment design). Move all measured outcomes to Chapter 4. Collapse the set-up faults into one fault table in an appendix, keeping two or three of the best (flash DIO, GNSS field count, flash-write stall) in the body as short examples of method. That alone should save 3000 to 5000 words.

### Chapter 4 Results (p.54 to 55)

Only placeholders. Each heading says what will appear, for example "Achieved sample rate, inter-sample jitter distribution, and dropped-sample counts for both IMUs, first on the bench and then on the moving vehicle" (4.1). 4.8 promises "All subsystems operating together on the vehicle over a defined route", which has not happened.

Fixes: fill 4.1, 4.2, 4.5 and 4.6 now from the bench logs already collected (Appendix C lists them), using tables and two or three plots generated from the logs: a jitter histogram with logging on and off, a time series of the 150 s session with labelled axes, and the calibration before and after. Report 4.4 honestly as partial (decode verified, connection intermittent). Label each result "bench" or "vehicle". Add the vehicle results when they exist. Tie each subsection to its RQ and its Table 1.1 row.

### Chapter 5 Discussion (p.56)

Placeholder only. The planned themes are the right ones.

Fixes: for each RQ, compare the findings with the literature in Chapter 2 (for example, the jitter and outage behaviour against the metrics 2.5 says studies usually omit; the sub-second alignment against what event labelling needs; the 7 fps detector against the Pi 4's constraints). Then state the threats to validity: bench only, one pair of sensors, magnitude not a vertical axis, no GNSS fix.

### Chapter 6 Conclusions (p.57)

Placeholder only. At the moment no research question is answered anywhere in the report.

Fixes: one short paragraph per RQ, each stating answered, partly answered, or not answered, with the evidence and the number. Then the contribution and its limits. Keep it to about one page.

### Chapter 7 Recommendations (p.58 to 59)

Strengths: a well-sourced, sensible 7.1 on open-set obstacle detection, with a staged plan.

Weaknesses: this is the only recommendation, and it is about a subsystem added late. The many items flagged as future work in Chapter 3 are not collected here: PSRAM dio_opi (p.27 to 28), log replay and rotation (p.52), IRAM placement or buffered logging to remove the stall (p.52), a secure connector for the sync line (p.31), focal-length calibration (p.47), BMS reliability (p.41), orientation compensation (p.34). The phrase "within the scope or timeline of this dissertation" (p.58): this is a project report, not a dissertation.

Fixes: add a prioritised list of 6 to 8 recommendations, and shorten 7.1 by half.

### Appendices (p.65 to 71)

Strengths: Appendix C, the evidence index with dates and file names, is excellent practice and supports GA4 and GA6. The terminal excerpts on p.71 are useful.

Weaknesses: A.1 is too thin for an appendix that decides whether each GA is passed. A.3 has no prompts. There is no ethics appendix.

## 5. Top 10 fixes ranked by marks gained per hour

| Rank | Fix | Effort | Why it pays |
|---|---|---|---|
| 1 | Consistency pass: remove every drafting artefact (draft-abstract line, "Chapter 2/Chapter 3 as appropriate", "before the report claims", "the student observed", "for the report", the log path, the language-model remark), fix the seven cross-reference errors listed in section 4, make the numbers and terms consistent (≥100 Hz, LTE-M, HPEC), and resolve the calibration-factor arithmetic on p.35 to 37. | 2 to 3 hours | Cheap, and each of these reads to an examiner as carelessness. The calibration numbers in particular damage trust in all the other figures. |
| 2 | Rewrite Appendix A.1 as a paragraph per GA that is specific to SW-7, citing results and sections, and add GA10. | 2 to 3 hours | Examiners check GAs against this appendix, and any GA failed means the course is failed. |
| 3 | Rewrite A.3 to cover all real AI use (code, debugging, literature search, writing) with two or three example prompts, what was submitted, and what was kept. | 1 to 2 hours | A required item (L2 s12) and an integrity risk if it understates use. |
| 4 | Write Chapter 6 Conclusions: answer each RQ with the evidence status and numbers. | 3 to 4 hours | Removes the "no substantiated conclusions" problem for GA1 and GA4, even before field data. |
| 5 | Write Chapter 4 Results from the existing bench logs: move the numbers out of Methodology, add three tables and two or three plots made from the logs, and label bench vs vehicle. | 1 to 1.5 days | The single biggest structural gain. It turns existing work into credited results. |
| 6 | Reference clean-up: delete or cite the 31 uncited entries, remove the irrelevant and placeholder ones ([47], [48], [57], [58], [38]), renumber in order of first citation, and add sources for the uncited key claims in section 6. | 2 to 3 hours | GA6 and academic credibility. Padding the bibliography is noticed. |
| 7 | Add a field-test design section to Methodology (from SW7-VIT-001): variables, conditions, repetitions, acceptance criteria, and safety and removability measures. | 3 to 4 hours | Directly answers the brief's GA4 text ("construct field testing procedures") and supports GA10, even if the road run is limited. |
| 8 | Write Chapter 5 Discussion against the Chapter 2 literature, including threats to validity and a short reflective paragraph for GA9. | 1 day | Required chapter. It carries the "interpretation" and "synthesis" in the GA4 descriptor. |
| 9 | Close the brief's GA5 items: record the camera p50 and p95 latency (the tooling exists), measure the supply current of the ESP32 unit and Pi 4 for a power budget against the 72 V source, and compute a bandwidth budget. | 0.5 to 1 day | These are explicit brief requirements that are currently absent. They also give Results content. |
| 10 | Compress Methodology: add a system block diagram, replace the ASCII Fig 3.1, add equations for all features, and move the set-up faults into an appendix fault table. | 1 to 1.5 days | Brings the report to 15 000 words and 50 pages and makes it read as engineering rather than a diary. |

Outside this ranking: vehicle data (at least the stationary powertrain baseline, and ideally a short approved road run) is the largest absolute gain available. It is the only route to answering RQ1 and RQ4 and to meeting the brief's GA4 text in full. It is not ranked because the effort depends on vehicle access. The HUD scope decision and the ethics letter decision both need the supervisor. Once the HUD decision is made, update the title, the Terms of Reference, the abstract, the Scope, RQ2, Table 1.1 and 4.7 in one pass.

## 6. Reference quality

Style consistency:
- 31 of 70 entries are never cited in the body: [1] and [29] to [58]. They include entries unrelated to the project: [47] cardiac telemetry in non-intensive care, [48] epilepsy video telemetry units, [35] a supercomputer digital twin, and [38] cloud security in a journal of uncertain standing. [57] (M. S. Tšoeu and M. Braae, "Control Systems," IEEE, vol. 34, no. 3) and [58] (Tapson, Instrumentation) look like leftovers from the template, and [57] has no journal title. Either cite each entry where it supports a claim or delete it.
- Numbering is not in order of first citation, which IEEE requires. [62] is cited on p.14 before [14] to [17], [59] to [61] appear before [63], and [1] is never cited.
- Title capitalisation is mixed. Most entries use sentence case, but [63] to [68] use title case.
- [40] renders with each word on its own line (p.62), which is a BibTeX or line-break problem.

Entries with missing or doubtful fields:
- [7] NASA guide: no publisher or place.
- [11] is dated 2016 but carries arXiv:1803.08383, which is a March 2018 identifier. Check the year.
- [21] Jinpeng user manual: no year and no place.
- [23] conference paper: no pages and no location.
- [50]: no DOI or pages.
- [69] PLOS ONE: no volume or article number.
- [59], [60], [61] are web sources with access dates, which is correct. [60] is hosted on a third-party site (Waveshare); cite the SIMCom source if one exists.

Key claims with no source:
- "consistent with the sensitivity and bias tolerance permitted by the accelerometer's own datasheet" (p.35), and the MPU6050 260 Hz filter setting (p.30). There is no MPU6050 datasheet in the references.
- "Writing to flash on the ESP32 briefly suspends code executing from flash on both cores" (p.52). This is the central explanation of a key result and needs ESP-IDF documentation.
- The behaviour of vTaskDelayUntil and esp_timer_get_time (p.29). Cite the FreeRTOS and ESP-IDF documentation.
- The SSD-MobileNet-v1 detector, the COCO dataset and TFLite quantisation (p.47): no citations for the model, the dataset or the pinhole-camera relationship. The papers are already in Report/references_pdf/camera_ml with BibTeX.
- The JBD protocol checksum and frame layout, "following community-documented reverse-engineering" (p.38): the community source is not cited.
- "a Tier-1 automotive supplier case study describing telematics and HUD products for auto-rickshaws" (p.51): not cited.
- The Pi 4 5 GHz regulatory-domain behaviour and the Broadcom/Cypress regulatory hint (p.44 and p.45): not cited. These sections may be cut anyway.
- The GNSS speed units "differ between knots and km/h across firmware revisions" (p.33), and the GNSS warm-up being "consistent with normal GNSS receiver behaviour" (p.34): not cited.
- The suitability of MQTT and HTTP (2.7, p.22): no MQTT specification cited.
- "This work aligns with the UCT Radar Remote Sensing Group's focus" (p.13 and p.14): no source.

Writing quality, briefly. The prose is clear at sentence level, but it is long-winded and defensive. "Rather than" appears 104 times in the PDF. Phrases that defend the author instead of reporting the work recur: "reported honestly here rather than smoothed over" (p.52), "stated here rather than left implicit" (p.47), "This is reported rather than discounted" (p.31), "Both findings are reported as found" (p.37). One honest limitation sentence per result is enough, and the Results and Discussion chapters are the place for it. Tense drifts between past (what was done), present (what the firmware does) and future (what will be done) within single sections, for example 3.19.7. Use past tense for work done, present tense for the design as it stands, and keep plans in Chapter 7. Many sentences exceed 50 words (for example, the first paragraph of 3.19.4 on p.45). Split them.
