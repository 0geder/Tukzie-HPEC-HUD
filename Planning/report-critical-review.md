# Critical review of the report, Stage A (diagnosis only), 11 Oct 2026

Run by a review agent with the student's "Academic Report Review: Authenticity, Coherence, and Technical Depth"
prompt, Stage A only: no file was edited. It read every body chapter, References.tex, appendices A to E,
brief-compliance.md, report-review.md, report-cut-plan.md and the PROJECT_LOG status, and checked key numbers
against BenchTest/logs, TEST_PROCEDURES.md, Research/research.db, TelemetryUnit/src/main.cpp and the SIMCom manual.
It did not open other cited papers; claims about them are marked "verify". Line numbers refer to the .tex files
as of the 11 Oct cut (commit 782fa23) and will drift.

## 1. Overall

Honest, specific and evidence-led; almost every number traces to a repository log. The cut produced a clean
design-plus-verification Methodology and a requirement-organised Results chapter; the literature review compares
sources and states what transfers to a trike. The main weakness is a mismatch between what the research questions
ask, what R1 to R13 test, and what the Conclusions claim; some headline figures come from best-case or
mis-described conditions; two design choices (dual-IMU averaging; 200 Hz with a 260 Hz filter) are not argued from
first principles; the camera subsystem has no literature behind it although the gap claim depends on it; a few
citations do not support their sentence, and one dataset is named but not cited. All fixable within the word budget.

## 2. Weaknesses, ranked

1. Requirements do not measure the research questions. RQ1 (accuracy and repeatability of the dynamic-response
   characterisation) maps to R1 to R4 and R6, which test sampling, calibration, self-tests and GNSS; none has a
   repeatability criterion (e.g. coefficient of variation over repeated traversals). RQ2 asks which hierarchy,
   layout and update strategy, which needs alternatives compared; one design exists. RQ4 asks about time- and
   frequency-domain features; none frequency-domain is implemented and RQ4 maps only to R3 (a synthetic-sine
   self-test). R2 (resting 9.80 to 9.82 right after a gravity calibration) is circular, and the later session
   fails it (9.93, 10.10) while the summary says "Met at calibration". R6 measures pulse-edge regularity on the Pi,
   not camera-frame to IMU-sample alignment. R7 is measured at the detector, not at the driver.
2. Headline figures from best-case or mis-described conditions. Abstract and Conclusions: "102 ms at 19.5 fps" was
   a run without the bridge, fusion polling or a viewed preview; the integrated healthy-Pi run (14.6 fps, 118 to
   122 ms median, 146 to 148 ms p95; BenchTest/logs/2026-10-10_bench_observations.md) is not mentioned. "Alerts in
   0.5 s" is time after opening the page with a person already in view, not alert-onset latency. R10 "record 0.37 s
   old" was measured at a laptop; R11 evidence was laptop offscreen. The abstract's "8 % disagreement reduced to
   noise": at calibration the sensors were 10.03 and 9.90 (1.3 % apart); the 8 % came from an earlier session.
3. Dual-IMU design has no rationale and is inconsistent: equal-weight averaging assumes the same signal, while D is
   justified because the sensors are at different points; mounting points and the purpose of two sensors are not
   stated; MPU6050 selection not justified. Discussion: D = 1.68 "on a hand-held board" (it was disturbed by hand);
   near rest sigma (0.041) is below the 0.05 floor, so noise alone gives D about 1.6.
4. Sampling chain broken and firmware versions inconsistent. 200 Hz justified from the ISO 2631-1 80 Hz band, but
   ISO weighting is not implemented and the 260 Hz filter aliases; "160 Hz the ISO 2631-1 bound" (ISO sets no
   sampling bound; 160 Hz is Nyquist for 80 Hz). The 25 Sep log shows max intervals to 29.9 ms and min to 0.8 ms
   (vTaskDelayUntil catch-up): "zero dropped samples" hides 30 to 40 ms gaps then bunched samples while jerk uses a
   fixed dt; Appendix C lists "25 to 30 ms gaps every 12 s", Results R1 does not. Firmware state disagrees:
   Methodology says 260 Hz current, Discussion and Recommendation 1 say v0.7.4 moves to 94 Hz, Table E.1 is v0.7.3,
   main.cpp is already v0.7.4 with 94 Hz. Bench results and road test will use different filters.
5. No camera literature (SSD, MobileNet, COCO, int8 quantisation, monocular width ranging), though PDFs are in
   Report/references_pdf/camera_ml; the edge-pattern paragraph is uncited; cellular section cites only the brief;
   proximity section reviews the VL53L5CX (not used) and nothing on the VL53L0X (used); obstacle literature first
   appears in Recommendation 8; the jitter gap is generalised from one comparator; the cargo-trike section motivates
   telemetry by energy and cost, which the system does not measure.
6. Attribution: Nienaber, Kroon and Booysen dataset named but not cited; also uncited: the 608-image pothole set,
   YOLO11/Ultralytics, SSD-MobileNet/COCO, LiteRT, NCNN, OpenStreetMap and OSRM (licence requires attribution). The
   brief is cited for MQTT/HTTP technical claims. simcoma76xx is cited for "reply formats differ between firmware
   versions" (one manual cannot show that); the same manual says speed over ground is in knots (PDF p.493) while the
   report says units unconfirmed. Verify: barnell2018, unwup2019, desimone2018 (described as agricultural machines;
   title says unmanned ground vehicles), park2020 (HUD study applied to a dashboard without a transfer argument).
   The AI declaration covers only wording and LaTeX; repository shows wider use; course requires example prompts.
   No ethics appendix (H9), and the camera images the public.
7. Contradictions: R13 stated as fact in Methodology ("returned to standard in about 20 minutes") but "not yet
   installed" in Results; power fault "is the cause" vs "likely reason", strongest evidence (three reboots in 20 min
   on the Pi USB, none in 4 h after) not cited; R12 test "on vehicle" but no glance method in the test design; "a
   driver's display should not depend on coverage" vs both Pis on a phone hotspot (Appendix D); Appendix C 0.69 m
   "listed as immediate" conflicts with band rules; Appendix C intro points to the Methodology chapter; GA1 entry
   cites a section that no longer holds the fault; notation: R is both the ride index and requirement prefix, units
   of R not stated; mAP as 59.7 % and 0.714; fps vs frames/s.
8. Structure and brief coverage: "Dashboard integration", the title deliverable, is a subsection of the camera
   subsystem; "fewer than six symbols" not reconciled with the Sensors page; the 24 px capital-height target never
   checked against the dashboard fonts; brief items with no requirement, result or recommendation: environmental
   and air-quality sensing, wireless bandwidth limits, ESP32 edge-processing latency (D3b; no acquisition-to-broker
   figure), hardware debuggers; "low-cost" never quantified.
9. Introduction: "camera alerts serve the move to autonomy better than a second screen" is a non sequitur; 2.5 kW
   vs 3.9 kW not explained and unused; Sebwa repeated; NHTSA 2 s / 12 s appears five times; TRL reached never stated.
10. Hazard sensing beyond the evidence: "fast enough for its purpose" with a 0.5 s criterion that has no derivation
    (reaction time, stopping distance at 42 km/h); the driver path adds the bridge's 5 Hz poll, the dashboard's
    0.5 s poll and rendering, unmeasured; the 0.874 m vs 0.096 m case cannot show which distance was right (the
    right sensor read 0.17 m at the same moment, detector at 6.2 fps).

## 3. Questions for the student

- Dual IMU: where will each IMU be mounted (body, near the rear axle, under the cargo bed)? What is the second
  sensor for? If at different points, why average? When and in what state did D = 1.68 occur; sigma1 and sigma2?
- What frequency band does road and powertrain response on this trike occupy? Is ISO 2631-1 the right
  justification for 200 Hz when its weighting is not applied?
- After a 30 to 40 ms stall, does the task read stale or fresh registers? Should features use measured timestamps?
- Which firmware runs on 14 Oct (v0.7.4, 94 Hz)? Will R1 be re-verified on it first?
- What repeatability criterion answers RQ1 (e.g. CV of sigma and R over N traversals at a set speed)?
- RQ4: narrow to time domain, or compute a spectral feature offline? Is raw 200 Hz data logged, or only features?
- RQ2: were alternative layouts or alert strategies considered? If not, reframe as "how should"? How many elements
  are on screen while driving?
- How will glance time be measured on the vehicle (video, frame counting, trials)? Is it in SW7-VIT-001 and the
  ethics approval?
- Where does the 0.5 s onset criterion come from? Onset-to-screen time on the Pi 5 including both polls?
- Which configuration represents the vehicle: 19.5 fps / 102 ms or 14.6 fps / 120 ms? Why did C4 avoid
  under-voltage?
- GNSS speed: the manual says knots; any evidence otherwise? With stationary readings up to 5.8 and v_min = 1, is R
  computed while stationary?
- Why four read-back passes, and does "complete" mean no record failed in every pass?
- Which pack is the BMS on (24S, 150 A, LFP?) given lead-acid documentation? Plausibility range used?
- On the vehicle, which Wi-Fi links the Pi 4 and Pi 5? Does the dashboard depend on a phone?
- Unit cost (bill of materials) to support "low-cost"? Payload size times publish rate against the data plan?
- SEN55: descoped with a recommendation, or integrated before submission?
- AI use: contribution to firmware, scripts and literature search; which example prompts go in Appendix A; ethics
  letter ruling from the supervisor?
- Pothole model: validation tiles from frames whose other tiles were in training (leakage)? Held-out score?

## 4. Revision plan (body about 11,100 words; keep about 2,000 for road-test results, 400 for sync)

1. Realign RQs, requirements and conclusions (narrow RQ2 to "how", RQ4 to time domain or an offline spectral
   feature; add an RQ1 repeatability row; reframe R2 as drift after recalibration and R6 as edge regularity; define
   R7 at the driver). About +150 words.
2. Correct headline figures (abstract, R7, R10, R11, Conclusions): both detector configurations, where each was
   measured, "alerts in 0.5 s" restated, the 8 % claim corrected. About +80.
3. Dual-IMU rationale and mounting plan; rewrite the D interpretation. About +120.
4. Rebuild the sampling argument (band, Nyquist, filter version, catch-up, dt); make firmware versions consistent
   across Methodology, Discussion, Recommendations and Table E.1. About +100.
5. Citations and attribution (datasets, Ultralytics, SSD, MobileNet, COCO, quantisation, OSM/OSRM, LiteRT; MQTT
   source instead of the brief; fix the simcom sentence and note knots; verify desimone2018, park2020; expand the AI
   declaration; settle the ethics appendix). About +40 body words.
6. One literature paragraph on lightweight detection and monocular ranging (camera_ml PDFs) tied to the
   SSD-MobileNet choice and width heuristic; cite or cut the edge-pattern paragraph; move Recommendation 8's
   citations; trim the repeated Sebwa sentence. About +200 / -80.
7. Fix the contradictions in item 7. About +30.
8. Dashboard integration as its own Methodology section; element count and 24 px font check; glance method in the
   vehicle test design. About +120.
9. Brief coverage: SEN55 and environmental sensing, bandwidth budget, ESP32 path latency, BOM cost (or drop
   "low-cost"). About +100.
10. Introduction reasoning fixes, kW figures, TRL reached. About 0.
11. Hazard paragraph: derive the onset requirement; reword the 0.874 m vs 0.096 m case as inconclusive pending C9.
    About +60.

Total about +1,000 words, leaving about 2,900 for road-test and sync results.

## 5. Leave alone

Literature: road roughness and ride response (IRI vs response vs comfort) and the data-validity and update-age
synthesis. Methodology: firmware architecture paragraphs, feature equations and self-test, BMS status, GNSS parser,
the two logging findings, the ToF finding, the detector data-handling paragraph, Table 3.1 (apart from the dual-IMU
point). Results: the latency breakdown table, R9's recovery narrative, the requirement summary format. Discussion:
"Data integrity and connectivity" and "Validity and limitations". Recommendations 1 to 7. Appendix C and Appendix
E's fault table (fix their stale intro and cross-references).
