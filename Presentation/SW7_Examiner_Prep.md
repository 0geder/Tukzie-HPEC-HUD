# SW-7 examiner, second marker and Open Day preparation

State of the evidence: 20 October 2026 (firmware v0.7.4; two-sided layout since 15 October; first road session on 19 October, data checked on 20 October). Section K covers the work since 11 October. Older answers that said "before the road test" have been updated where the road session changed them; update again after the second session.

This file builds on Presentation/SW7_QA_Prep.md and SW7_Talking_Points.md; it does not replace them. It adds first-principles theory, what the cited papers actually say, the hostile questions from the two report reviews, the graduate attributes, and a list of things not to say.

How to answer any question, in three moves: the number, how and where it was measured, and its limit. Example: "102 ms median from the sensor's own readout timestamp to the detection, over a one-minute bench run on 30 September with nothing else running on the Pi; the integrated Pi with the bridge and live view gave about 120 ms."

Format: report section and log files are given as "Evidence". Where I could not open a source myself, the item says "not opened" or "unverified". Course facts: 10 minute talk plus 5 minutes of questions (Lecture 2); report 90 percent and oral 10 percent of the mark (Intro Lecture slide 10, as recorded in Planning/brief-compliance.md).

Contents
1. The story: 60 seconds and 2 minutes
2. Question bank
   - A. Problem, scope, brief, the HUD change, TRL
   - B. Literature and the research gap
   - C. Theory from first principles
   - D. Design decisions
   - E. Results and every key number
   - F. The seven fault investigations
   - G. Weak points and hostile questions
   - H. Graduate attributes
   - I. Teamwork and inherited work
   - J. Open Day visitors
   - K. New since 11 October: two sides, approaching objects, power, the first road session
3. Numbers cheat sheet
4. Glossary
5. Things not to say
6. What I could not verify

---

## 1. The story

### 60-second version

TUKZIE is UCT's programme for an electric cargo trike for last-mile freight; the test vehicle is a 72 V trike. When I started, its dashboard ran entirely on simulated data and nothing measured how the trike rides. I built an ESP32-S3 telemetry unit with a built-in LTE modem: it samples two IMUs at a fixed 200 Hz, reads the battery over Bluetooth and position from GNSS, computes ride-vibration features on the board, logs everything locally and sends it over LTE to a database, replaying the backlog after a coverage loss. A Raspberry Pi 4 runs a camera object detector and three time-of-flight distance sensors, fuses them, and feeds the vehicle's existing dashboard, which now shows only live data and hazard alerts. With my supervisor's agreement this replaced the windshield HUD in the brief. Everything is verified on the bench, each stage against a pass criterion; seven faults were found by testing and fixed. Since 15 October the system has two sides: a Pi 5 at the front runs its own camera and detector beside the dashboard (51 to 54 ms), the Pi 4 and the telemetry unit sit at the rear by the battery, and both cameras show on one dashboard page with a warning for approaching objects. On 19 October the whole system was mounted and recorded on the road for 108.6 minutes: the IMUs and the battery link held, but GNSS had no fix and no raw samples were kept, so the ride questions wait for a second session.

### 2-minute version

The problem. A vehicle meant for fleets and later autonomy needs to know how it rides, what state its battery is in and where it is, and its driver needs hazard information without being distracted. The trike vibrates hard, has little power and computing, and loses mobile coverage. The brief asked for an HPEC telemetry unit, a windshield HUD, LTE synchronisation with a central database, and a report validating it.

What I built. On the ESP32-S3, FreeRTOS keeps acquisition on its own core: one task per IMU at the highest priority, each on a 5 ms period with vTaskDelayUntil, samples time-stamped in microseconds and pushed into bounded queues that drop and count rather than block. In every session both IMUs ran at 200.0 to 200.5 Hz with zero dropped samples. Each IMU is calibrated against gravity, which removed an 8 percent disagreement between two identical sensors, and the two are fused with a disagreement figure. Over LTE the unit publishes with MQTT QoS 1; in the outage test on 11 October a 10-minute radio cut built a backlog of 60 records, the modem reconnected 5.2 s after the radio returned, and the database ended with 112 of 112 records, none missing, none duplicated. GNSS agreed with a phone to a median of 2.7 m.

The driver side. The dashboard already showed speed and battery, so a second display would compete for attention; the supervisor agreed on 1 October and the title changed on 2 October. The Pi 4 detector runs a pretrained 8-bit SSD-MobileNet: 102 ms median from sensor readout to result at 19.5 frames per second on the bench, about 120 ms on the fully loaded Pi. Three time-of-flight sensors give close-range distance, fused with the camera's class and bearing. On the dashboard I added a camera page, a Sensors page and an immediate-hazard banner, and a live-only mode so that missing data shows as "--" and is never replaced by simulated values.

What testing found. Seven investigations, each told as symptom, candidate causes, deciding test, cause and fix: for example flash writes stalling both IMUs, a battery checksum failing by exactly three, and the Pi 4 browning out because the LTE modem drew its transmit current through the Pi's USB port.

What changed after 11 October. Detection moved to the Pi 5 beside the display (51 to 54 ms against 118 to 122 ms); a time-to-contact warning for approaching objects was added (synthetic tests within 2 percent, not tested on a real approach); enclosures and a power budget (about 20 W) were designed; and the first road session on 19 October met R1 and R5 on the vehicle but recorded no GNSS fix, raw samples or run markers.

What is left. A second, shorter road session with the raw stream, GNSS and timed runs answers RQ1 and RQ4 on the vehicle; glance time (RQ2), the approach test C11, the fusion calibration test C9, the database latency and a separate supply for the telemetry unit also remain.

---

## 2. Question bank

Each entry: the question, a short model answer, the likely follow-up and how to answer it, and the evidence.

### A. Problem, scope, brief, the HUD change, TRL

A1. What problem does this project solve, in one sentence?
Answer: It gives the TUKZIE trike its first reliable record of how it rides, what its battery is doing and where it is, and shows the driver only live, safety-relevant information on the dashboard it already has. Before this the dashboard ran on simulated values and nothing on the vehicle was measured.
Follow-up: "Why does a trike need this?" Fleet operators confirm cost and energy benefits only by measuring their own vehicles (the logistics studies measured in service), and a three-wheeler's ride and stability depend on payload and surface, so passenger-car thresholds do not transfer.
Evidence: Report 1.1 and 2.2; dashboard inspection of 2 Oct in Methodology "Dashboard integration".

A2. What did the brief ask for?
Answer: Four things: an HPEC telemetry unit with a deterministic multi-threaded architecture for polling, signal processing, display rendering and networking; a windshield HUD; logging and LTE transmission to a central database; and a report validating ingestion accuracy, edge latency and remote synchronisation. It also listed environmental and air-quality sensing (microclimate, "plastic burning" anomalies) and fleet notifications.
Follow-up: "Which of those did you not deliver?" The HUD (replaced by agreement), the SEN55 air-quality sensor (received, cable missing), the 8x8 ToF sensor (three VL53L0X stand in), the motor Hall tap, fleet notifications (never defined), and route optimisation (not in SW-7).
Evidence: Planning/EEE4022S 2026 Topics Winberg_Taken By Samson.pdf pp. 20 to 22; Report 1.2 and 1.5; Planning/brief-compliance.md.

A3. Why did you drop the windshield HUD?
Answer: Three reasons. The trike's existing PySide6 dashboard on a Pi 5 already shows speed and battery, most of what a HUD would show. A second display competes for the same attention, and a head-up position does not by itself make a display safe: HUD use changes attention demand (Liu 2003), and multi-screen setups raise cognitive load (Zhu 2021). A windshield HUD on a removable, low-cost, vibrating unit in daylight also has hard optical problems: double images from the two glass surfaces (Qin 2017), an eye box per installation, and luminance. The camera alerts serve the move towards autonomy better than another screen.
Follow-up: "Who agreed and when?" The supervisor by email on 1 October 2026; the course coordinator (Prof. Chowdhury) captured the title change on 2 October. "What was lost?" The optical projection subsystem (Deliverable 1, second half), the HUD rendering path as the brief worded it, and the novelty claim G4 (a telemetry-fed HUD on a three-wheeler). Say it plainly: that part of the brief is not met; it was replaced.
Evidence: PROJECT_LOG D26; Report 1.2 and 2.6; brief-compliance.md section 2.

A4. Isn't dashboard integration a smaller project than a HUD?
Answer: Different, not smaller. The HUD's hard parts were optical; the dashboard's hard parts were data integrity: there was no live input at all, so I built the USB line, the Pi 4 bridge, network discovery, a live-data provider, live-only mode and the pages, applied as 63 checked edits to a copy of the team's code. The supervisor also asked for the ToF and sensor-fusion side as a research aspect, which was added.
Follow-up: "So what is your research contribution?" The measured integration (timing, loss, recovery, latency) on this vehicle class, not any single component (see B1).
Evidence: Methodology "Dashboard integration"; PROJECT_LOG D26.

A5. What does HPEC mean in your project? An ESP32 is not high-performance computing.
Answer: In the report, "high performance" means predictable completion of time-critical work within a small power budget, not throughput: a fixed 5 ms acquisition period with measured jitter and zero loss, on-board feature extraction, and fusion before data leave the vehicle. The compute-heavy vision runs on the Pi 4.
Follow-up: "Then why use the term?" It is the brief's term; I defined it in Chapter 2 and measured the properties that matter (jitter, loss, latency).
Evidence: Report 2.5; Barnell 2018 cited for HPEC (not opened by me).

A6. What are your research questions, and which are answered?
Answer: RQ1, accuracy and repeatability of the dynamic-response measurement: answered for the instrument on the bench, not yet for the vehicle. RQ2, information hierarchy, layout and update strategy on the dashboard: answered for hierarchy and update strategy, not for glance time. RQ3, latency, loss and recovery: answered on the bench up to the database (T15), latency to the database not yet measured. RQ4, features that separate road from powertrain vibration: not answered; it needs vehicle data and the Hall tap.
Follow-up: see G1 for the mismatch between RQs and requirements.
Evidence: Report Chapter 6.

A7. What were the requirements and acceptance criteria?
Answer: Thirteen, R1 to R13, each with a pass criterion fixed before the test and a test ID: for example R1, both IMUs at 195 Hz or more with zero drops; R4, a parsed position within 10 m of a phone; R9, acknowledged publishes, recovery without intervention and a full read-back; R11, only live values on the display; R12, glances within 2 s. Met on the bench: R1, R3, R6, R7 (person class), R9 (to a test broker), R10, R11. Partly met: R2, R4, R5, R8. Outstanding: R12, R13.
Follow-up: "R4 is marked partly met, why?" The median (2.7 m) passes but the 95th percentile (11.0 m) is just over 10 m.
Evidence: Report Tables 1.1 and 4.4 (results summary).

A8. What TRL did you target and reach?
Answer: The target was TRL 6, a prototype demonstrated in a relevant environment (the vehicle). I have reached an integrated system validated on the bench, which on the NASA scale is about TRL 4 (validation in the laboratory); TRL 5 and 6 need the vehicle tests. The report's Conclusions say this in words ("a working bench prototype rather than the demonstration in a relevant environment").
Follow-up: "Why not state the TRL number in the report?" Fair; the critical review flagged it and it should be added.
Evidence: Report 1.2 and Conclusions "Overall"; Kimmel 2020 cited (not opened by me; TRL definitions from the standard NASA scale).

A9. What is the vehicle exactly?
Answer: TUKZIE Rev 0, a Jinpeng 72 V electric cargo trike; nameplates give a sensored three-phase permanent-magnet hub motor, 72 V DC, 35 A, controller limit 90 A (about 2.5 kW rated input), and the vehicle plate model L2e-U, 3.9 kW rated output, 42 km/h.
Follow-up: "Why do 2.5 kW and 3.9 kW differ?" They come from different plates (motor input rating against vehicle rated output) and the report does not reconcile them; I would not rely on either for analysis. The critical review noted this.
Evidence: Report 1.1; Adams and Rasara 2026 vacation-work report.

A10. What is in scope but not delivered?
Answer: SEN55 air-quality sensor (received, no 6-way JST GH cable), VL53L5CX 8x8 ToF (not arrived; three VL53L0X stand in), the motor Hall tap (counter built and loopback-tested, tap not wired), the HUD (replaced), and a partner broker (data go to a public test broker and my own database on the Pi 5).
Evidence: Report 1.5; REMAINING_WORK.md.

A11. Why was the camera added? The brief does not mention one.
Answer: The brief asks for "active driver alerts based on localized sensor feeds". The camera hazard detector was added on the supervisor's direction, and ToF proximity sensing after a later request for a live nearby-object alert. ML needed a revised ethics application, which was approved with conditions on 23 September before the detector processed live frames.
Follow-up: on ethics, see G9.
Evidence: Report 1.2; PROJECT_LOG D16.

A12. Is anything controlled by your system?
Answer: No. Everything is advisory. The detector and fusion only report; nothing touches the motor, brakes or steering.
Evidence: Report 1.5 and Methodology "Detection".

### B. Literature and the research gap

B1. What is the research gap?
Answer: The search found no system that integrates, on a light electric cargo trike: fixed-rate dual-IMU acquisition with measured jitter and loss, on-board ride features, camera detection fused with time-of-flight ranging, LTE telemetry with local logging, and presentation on the vehicle's own dashboard with missing data shown as absent. The contribution claimed is that integration and its measurement on this vehicle class, not any single component.
Follow-up: "Each part is known, so where is the novelty?" Exactly; I narrowed the claim to integration plus measurement. The literature reports accuracy or mean latency, rarely jitter, queue behaviour or measured outage recovery, and display guidance comes almost entirely from passenger cars.
Evidence: Report 2.10.

B2. How did you search?
Answer: An automated pipeline on OpenAlex, arXiv and Crossref with a fixed query set (ride characterisation, three-wheeler dynamics, cellular telemetry, MQTT, IMU calibration and fusion, camera hazard detection on edge hardware, driver displays, BMS protocols), run three times from 19 September, holding 733 records in Research/research.db, plus a targeted search of the three-wheeler market and open-source projects. Every DOI was re-resolved, and Google Scholar was not scraped. A gap ledger records each claim and the evidence for and against it.
Follow-up: "Why not IEEE Xplore or Scopus?" Not available to the pipeline through an API; that is a limit of the search and the gap claim is bounded by it. Most screening was from abstracts.
Evidence: Research/research.db (733 sources, 1,013 relevance rows, 3 run-log rows, checked); Research/gap_ledger.json; PROJECT_LOG D10, D11.

B3. Which claims did the search narrow?
Answer: Two. G1 originally claimed no published dual-IMU ride characterisation with cellular telemetry on a three-wheeler; an open-architecture motorcycle telemetry unit (Electronics 2026: STM32H745, 9-DoF IMU, RTK-GNSS, CAN-FD, 4G LTE, dual-core partitioning) is architecturally close, so G1 was narrowed to the dual spatially separated IMUs, the ride-quality framing and the vehicle class. G3 claimed no work on local buffering during cellular outages; the mechanism exists in prior work, so it was narrowed to "recovery is rarely measured". G4, a telemetry-fed HUD on a three-wheeler, fell away with the HUD.
Follow-up: "Did you read that motorcycle paper in full?" The ledger says it was reviewed from the abstract with a note to read the full text. Be honest about that.
Evidence: Research/gap_ledger.json (G1 to G4, evidence entries); PROJECT_LOG D11.

B4. What would falsify your gap claim?
Answer: One published or open-source system on a light three-wheeled vehicle that combines fixed-rate multi-IMU acquisition with reported jitter and loss, on-board ride features, cellular telemetry with local logging and measured recovery, and camera-based hazard alerts on the vehicle's display. The ledger is set up to log exactly such a source as "challenges".
Follow-up: "What if it exists in a language or database you did not search?" Then the claim falls; that is why it is worded as bounded by the search.
Evidence: Research/gap_ledger.json structure (claims with challenge evidence).

B5. What is the difference between IRI, vehicle response and ride comfort?
Answer: IRI is a property of the road: computed from a measured profile through a standard quarter-car model at 80 km/h, in m/km. An accelerometer on a vehicle measures the vehicle's response, which mixes road, tyres, suspension, chassis, payload, speed and mounting. Comfort is a third thing: ISO 2631-1 frequency-weights the acceleration to describe what a seated person feels. My features are vehicle response without ISO weighting, so I claim a repeatable, vehicle-specific response index, not an IRI and not comfort.
Follow-up: "Could you estimate IRI?" Only with a validated vehicle model (Gonzalez 2008 needed an assumed model), which a trike does not have; it would need calibration against a profiled road.
Evidence: Report 2.3; Yiliguoqi 2026 describes IRI as a standard vehicle at 80 km/h over the measured profile (opened); FHWA 2016 and Gonzalez 2008 not opened.

B6. What did Yiliguoqi et al. (2026) find, and why does it matter?
Answer: An SVM on smartphone accelerometer and gyroscope data sampled at only 10 Hz classified road roughness levels correctly 80 to 100 percent of the time, across four vehicles on repeated 50 m segments. It shows learned classifiers can work on cheap sensors, but the result is tied to their phones, routes, labels and thresholds and they say generalisation across vehicles is not known. So on the trike a transparent statistical baseline should come before any classifier.
Evidence: References/Papers/IMU-Based Ride Smoothness and Road Roughness/s41598-025-34396-3.pdf (opened); Report 2.4.

B7. What did Bui et al. (2026) do?
Answer: An ESP32-based inertial framework for real-time pavement classification and pothole detection with an abnormality index, using 6 s windows at 100 Hz with RMS and other statistics, plus GPS interpolation that brought localisation error under 3 m below 50 km/h. It supports running rough-road detection on an edge microcontroller.
Evidence: References/Papers/IMU-Based Ride Smoothness and Road Roughness/Signal_Processing...Microcontrollers.pdf (opened).

B8. What did Li et al. (2018) contribute to your design?
Answer: They classified road roughness online from the mean square of unsprung-mass acceleration divided by vehicle speed over a sliding window, because the same road driven faster gives a larger response. I adopted the speed normalisation, with two differences: my sensors are on the body, not the unsprung mass, and I use the variance of the magnitude (since v0.7.2), not the raw mean square.
Follow-up: "So your index is not Li's index?" Correct, it is a speed-normalised response measure, not a validated roughness class.
Evidence: Report 3.4.2; References.tex comment (verified from the abstract by the project; I did not open the PDF).

B9. What did Perez-Gonzalez et al. (2025) build, and how is it different?
Answer: An electric-racing telemetry system: ESP32 acquisition, a Raspberry Pi 4B for analytics with Node-RED, and LoRaWAN, field-validated with a packet delivery ratio above 99 percent and average end-to-end latency below 1 s. It supports the split between deterministic acquisition and higher-level processing that I used. Differences: LoRa on a track with their own gateway, not LTE in a city; no dual IMU ride characterisation; no camera.
Evidence: References/Papers/HPEC Telemetry Unit/preprints202508.0986.v1.pdf (the preprint version opened; the report cites the published Vehicles 2025 paper).

B10. What does the cargo-trike economics literature say?
Answer: Sebwa et al. (2025), Dar es Salaam: an e-tricycle cut cost per km by about 45.5 percent against a motorcycle, 62.5 percent against a tuk-tuk and 86 percent against a light-duty car on the routes measured. Saenz et al. (2016), Portland: 51 to 72 percent greenhouse-gas reduction for a tricycle logistics service. Both were measured in service, which is why an operator needs on-vehicle telemetry.
Follow-up: "Your system does not measure energy, so why cite this?" Fair: it motivates the vehicle and telemetry in general; my unit measures battery state and ride, not energy per km yet. The critical review made this point.
Evidence: References/Papers/Urban Electric Cargo Trike/The Journal of Engineering - 2025 - Sebwa...pdf (opened, p. with "45.5% and 62.5%"); Saenz not opened.

B11. Which edge-computing sources do you rely on?
Answer: Shi et al. (2016) for the case for edge computing: processing near the sensors reduces response time, bandwidth and dependence on a remote service. For my system that means alerts work without coverage and only compact features go over LTE instead of raw 200 Hz data.
Evidence: Report 2.5 (Shi 2016 not opened by me).

B12. What does NHTSA's guidance actually say?
Answer: The 2013 visual-manual guidelines recommend tasks be completable with single glances away from the road of 2 s or less (mean glance 2 s or less, 85 percent of glances 2 s or less) and a cumulative eyes-off-road time of 12 s or less per task. NHTSA also defines driving to include being temporarily stopped at a traffic light or in traffic, which is why I keep long tasks to the parked state.
Follow-up: "Does it ban head-down displays?" No; it limits glance duration and task time.
Evidence: Research/DashboardDesign/papers/2013_NHTSA_visual-manual-distraction-guidelines.pdf (opened, Federal Register vol. 78 no. 81, pp. 24818 onward).

B13. What other display guidance did you use?
Answer: ISO 15008 character height of 20 arc minutes recommended, 16 acceptable (as reported by Reimer 2014 and You 2021), which at about 70 cm from the 10.1-inch 1280 by 800 panel is a capital height of about 24 px. Reimer et al. (2014): a humanist typeface cut total glance time by 10.6 percent among male drivers. Kim et al.: touch-key performance improved up to about 17.5 mm. Euro NCAP 2026: digital touch targets at least 10 by 10 mm with 4 mm separation. Strayer et al. (2017): destination entry averaged 40 s on production systems, so it belongs to the parked state. Park and Im (2020): fewer than six symbols at a time.
Follow-up: "Did you check your pages against these?" Not yet; the 24 px check and daylight contrast are outstanding. Say so.
Evidence: Research/DashboardDesign/papers/ (Reimer, Strayer, Euro NCAP, Kim opened; the local Kim copy is the 2011 KIIE version with the 17.5 mm figure, the report cites the 2014 Applied Ergonomics paper); Park 2020 and ISO 15008 not opened.

B14. Why is "data validity and update age" your own design issue? It is not in the guidance.
Answer: The guidance covers legibility and workload, not stale data. But a display that keeps showing a value after its source stopped presents an estimate as a measurement. I saw exactly this: the inherited dashboard fell back to simulated values with no sign and showed 82 percent battery that was the simulator's value. So I made it a requirement (R11).
Evidence: Report 2.6 and Methodology "Data validity".

B15. What does the proximity-sensing literature say?
Answer: De Simone et al. (2018) used ultrasonic ranges for obstacle avoidance on unmanned ground vehicles; Noomwongs et al. (2025) combined RTK-GNSS with a 2D LiDAR on a low-speed micro EV because vision alone needed computing such vehicles lack. Caroleo et al. (2026) characterised the VL53L5CX: near-linear on white targets, standard deviation near 50 mm beyond 400 mm, only 18.8 to 34.4 percent valid readings on black targets, and about 15 minutes of warm-up drift. So ToF range on dark targets and in sunlight must be measured on the vehicle.
Follow-up: "But you use the VL53L0X, not the VL53L5CX." Correct, the stand-in has no reviewed characterisation in the report; that is a known gap (critical review item 5).
Evidence: Report 2.8; Caroleo, De Simone and Noomwongs not opened by me. Note: the report text describes De Simone as "retrofitted agricultural machines" while its title says unmanned ground vehicles; the critical review flagged this, so describe it by its title.

B16. What literature supports the detector choice?
Answer: SSD (Liu et al. 2016): one network predicts class scores and box offsets for a fixed set of default boxes on several feature maps, followed by non-maximum suppression; 74.3 percent mAP on VOC2007 at 59 fps on a desktop GPU, against Faster R-CNN at 7 fps. MobileNet (Howard et al. 2017): depthwise separable convolutions using 8 to 9 times less computation than standard convolutions. Jacob et al. (2018): integer-only 8-bit inference that is faster on ordinary CPUs with little accuracy loss, shown on COCO detection. COCO (Lin et al. 2014): 91 object types, 2.5 million labelled instances in 328,000 images (detectors use 80 of them). Alqahtani et al.: on edge devices SSD MobileNet V1 gave the lowest latency and energy but the lowest accuracy (mAP about 16 against 27 to 32 for the alternatives).
Follow-up: "These are not cited in the report." Correct; they are in Report/references_pdf/camera_ml and the critical review says they should be. Admit it.
Evidence: Report/references_pdf/camera_ml/ (liu2016_ssd, howard2017_mobilenets, jacob2018_quantization, lin2014_coco, alqahtani2024_edge_benchmark, all opened).

B17. What about obstacle and debris detection beyond COCO classes?
Answer: It is a separate research area: HazardNet uses synthetic debris models, SegmentMeIfYouCan is an anomaly-segmentation benchmark, and Tanveer et al. (2026) trained YOLOv8-n on rare roadside obstacles (they report 98.1 percent mAP@0.5 and 68 fps on their hardware). Any of these would need its speed measured on the Pi; until then the ToF "obstacle" output covers close range.
Evidence: Report Recommendation 8; Report/references_pdf/ (Tanveer abstract opened).

B18. Is monocular distance from a box width a recognised method?
Answer: It is the pinhole relation, the simplest approach. Zhu and Fang (2019) note that classic geometric methods like inverse perspective mapping perform poorly for distant objects and curved roads and propose learning distance end to end. My width heuristic is coarser still, which is why the output is a coarse band and why I fuse ToF at close range.
Evidence: Report/references_pdf/camera_ml/zhu2019_monocular_distance.pdf (opened).

B19. What does your literature say about MQTT and store-and-forward?
Answer: Honestly, the cellular section cites only the brief for the measures (completeness, backlog, delay, duplicates, recovery); there is no MQTT standard or reliability study cited. The QoS semantics I rely on are in the modem manual (QoS 0 at most once, 1 at least once, 2 exactly once; a publish reports failure if no server response arrives within the timeout).
Follow-up: "Then how do you know your design is right?" I tested it end to end (T15) rather than assume it, and I can explain the protocol from first principles (C27 to C31).
Evidence: Report 2.7; critical review item 5; SIMCom A76XX manual v1.09 p. 406 (opened).

B20. Which source is weakest in your reference list?
Answer: Be ready to name: Park and Im 2020 is a HUD study applied to a dashboard without a transfer argument; De Simone is described inaccurately; the brief is cited for MQTT technical claims; the Nienaber, Kroon and Booysen pothole dataset, the Roboflow set, Ultralytics, LiteRT, NCNN, OpenStreetMap and OSRM are named but not cited. These are on the revision list.
Evidence: Planning/report-critical-review.md item 6.

### C. Theory from first principles

Sampling and filtering

C1. Why 200 Hz?
Answer: ISO 2631-1 evaluates whole-body vibration up to 80 Hz, and to represent content up to 80 Hz without aliasing the sampling rate must exceed twice that, 160 Hz (Nyquist). 200 Hz gives a 100 Hz Nyquist frequency, 20 Hz of margin, and keeps the I2C load light. Measured 200.0 to 200.5 Hz on both IMUs.
Follow-up: "ISO does not set a sampling rate." Correct; 160 Hz is the Nyquist rate for the 80 Hz band, not an ISO rule, and the report's "160 Hz ISO bound" wording should change. Also, since I do not apply ISO weighting, the real justification is the band I want to see: road and powertrain response, which on this trike is not yet measured.
Evidence: Report 3.3; critical review item 4.

C2. Your filter was 260 Hz at 200 Hz sampling. What happens to a 150 Hz vibration?
Answer: It aliases. A tone at f folds to |f - k fs| for the nearest integer k, so 150 Hz appears at |150 - 200| = 50 Hz, inside my band, indistinguishable from real 50 Hz vibration. With the 260 Hz filter, content between 100 and 260 Hz passes nearly unattenuated and folds into 0 to 100 Hz. That was a design error I state as a limitation.
Follow-up: "Why choose 260 Hz?" To avoid attenuating the 80 Hz band; the next setting, 94 Hz, starts to roll off below 80 Hz. "What did you do?" v0.7.4, flashed on 11 October, uses 94 Hz, which suppresses most content above Nyquist at a small cost near 80 Hz. The proper fix is to sample the MPU6050 faster (its accelerometer runs internally at 1 kHz) and low-pass and decimate digitally to 200 Hz. "So your bench data and road data use different filters." Yes: the bench results were taken at 260 Hz and the road test will use 94 Hz; R1 timing was re-checked under v0.7.4 in the T15 log (200 Hz, 0 drops), but resting vibration values are not directly comparable across the change.
Evidence: Report 3.3; main.cpp line 577 (MPU6050_BAND_94_HZ); REMAINING_WORK 1.2; BenchTest/logs/2026-10-11_sync_outage_test.log. The 1 kHz internal accelerometer rate is from the MPU-6050 documentation, not in the repository.

C3. What is the anti-aliasing filter's phase delay, and does it matter?
Answer: The digital low-pass adds a few milliseconds of group delay (more at 94 Hz than at 260 Hz). It is the same for both IMUs and every sample is time-stamped after the read, so it shifts all inertial events by a near-constant amount; for 1 s windows and after-the-fact labelling it does not matter. For frame-exact camera alignment it would have to be included.
Evidence: Reasoning; filter delay figures are from the MPU-6050 register map, not in the repository (unverified here).

Features

C4. Define each ride feature.
Answer: Over a 1 s window of N = 200 calibrated magnitudes a_k: mean mu; RMS = sqrt(mean of a_k squared); standard deviation sigma = sqrt(mean of a_k squared minus mu squared), which is the RMS about the mean; peak-to-peak = max minus min; crest factor = max over RMS; mean absolute jerk = average of |a_k minus a_k-1| divided by the sample interval; threshold count = samples above mu + 2 sigma.
Follow-up: "Write sigma in terms of RMS." sigma squared = RMS squared minus mu squared. At rest RMS is about g and sigma is small.
Evidence: Report equations 3.1 to 3.3.

C5. Why use the magnitude rather than the vertical axis?
Answer: The mounting had not been related to a vehicle frame, and the magnitude does not depend on orientation. The cost: you cannot tell which axis a disturbance came from, and the magnitude rectifies (it is never negative), so it is not a linear signal: a vertical oscillation of amplitude A on top of g changes the magnitude by about A, but lateral oscillation changes it only to second order.
Follow-up: "What would you do on the vehicle?" Mount both IMUs with known orientation (X forward, Z up), estimate the gravity direction at rest and project onto the vertical; then compute vertical-axis features and ISO weighting.
Evidence: Report 3.4; Planning/mounting-and-enclosures.md (pod design with axis arrow). The second-order point is my derivation.

C6. Gravity is in your magnitude. Doesn't that ruin the RMS?
Answer: Yes, for RMS: at rest it reads about 9.8 m/s2 and the crest factor about 1. That is why sigma is the vibration measure: it removes the constant part. Peak-to-peak and jerk also ignore a constant. The resting vibration level 0.041 m/s2 is sigma.
Follow-up: "And the speed index?" Up to v0.7.1 it used RMS squared, which gravity dominates (about 96 m2/s4 at rest), so it mostly measured gravity divided by speed. v0.7.2 uses the variance sigma squared. This was found in report review, not by a test, which is a fair criticism of my own checking.
Evidence: Report 3.4 and 3.4.2; Appendix E fault table.

C7. Why the variance, not sigma, in the speed index?
Answer: To follow Li et al., who use a mean-square (energy-like) quantity over speed; the variance is the mean square of the fluctuation once the constant is removed, so it keeps their energy form without gravity. Units: (m/s2)2 per unit speed; since the speed units are unconfirmed, R is only for relative comparison within one dataset.
Follow-up: "Why should vibration energy scale linearly with speed?" It is an empirical normalisation from their data, not a law; on the trike it is a hypothesis to test with repeated runs at several speeds (the ground-phase test).
Evidence: Report equation 3.5 and 3.4.2.

C8. What is the crest factor of a sine, and why is it your self-test?
Answer: For x = A sin(wt): RMS = A over root 2, peak-to-peak = 2A, crest factor = root 2 = 1.414. These are closed-form, so at every boot the firmware feeds a synthetic 5 Hz sine of 200 samples through the feature code and checks each within 5 percent. It catches arithmetic or windowing bugs, not sensor errors.
Follow-up: "5 Hz in 200 samples at 200 Hz is exactly five cycles. Why does that matter?" A whole number of cycles makes the window RMS equal the theoretical value; a partial cycle would bias it.
Evidence: Report 3.4; main.cpp self-test. The whole-cycle point is my reasoning.

C9. Your jerk uses a fixed dt. What happens after a stall?
Answer: After a 30 to 40 ms pause, vTaskDelayUntil catches up: missed wake times have passed, so it returns immediately and several samples are read in quick succession (the 25 September log shows minimum intervals of 0.785 ms). The samples carry true timestamps, but the jerk formula divides by the nominal 5 ms, so jerk across the gap is mis-scaled, and the bunched reads may return repeated register values. Lost samples are counted, not interpolated.
Follow-up: "Fix?" Compute jerk with the measured timestamp differences, flag windows containing a gap, or read the IMU's hardware FIFO so samples are spaced by the sensor's own clock.
Evidence: BenchTest/logs/2026-09-25_bench_fusion_shake.log (min dt 785 us, max 29.9 ms); critical review item 4. The repeated-register point is my reasoning.

C10. Did the plus or minus 8 g range clip?
Answer: Probably once: the largest window peak-to-peak in the hand test was 77.6 m/s2, within 1 m/s2 of 8 g (78.5 m/s2), so if one axis dominated that peak was clipped. Clipped samples are not flagged, so a clipped window under-reports its peak. The range is provisional until the vehicle's peaks are known; flagging samples at the limit is a recommendation.
Evidence: Report 4.3 and 3.3.

Calibration

C11. Derive your calibration factor.
Answer: At rest the true magnitude is g0 = 9.80665 m/s2. Average 200 stationary magnitudes m_bar; the factor is s = g0 / m_bar, stored in NVS and rejected outside 0.5 to 2.0 (a moving or faulty sensor). RMS, sigma, peak-to-peak and jerk scale linearly with s; crest factor and threshold count are ratios and are unaffected.
Follow-up: "Why only one factor?" The features use only the magnitude, so one factor corrects exactly what is used.
Evidence: Report equation 3.4.

C12. Why does a single factor fail when the sensor is turned?
Answer: A MEMS accelerometer has a per-axis offset b and scale k: a_meas = k(a_true) + b. At rest in one orientation, the magnitude error comes from whichever axes carry gravity; turn the sensor and different axes carry it, so the magnitude changes and one scale no longer fits. That is why the factors differed between boards and why resting readings drifted (9.93 and 10.10 m/s2 later).
Follow-up: "What is the proper method?" A six-position calibration: each axis up and down, solving for offset and scale per axis (or an ellipsoid fit over many orientations), which makes the magnitude orientation-independent.
Evidence: Report 3.4.1, 4.2, Recommendation 2.

C13. Your calibration numbers do not add up. 10.35 times 0.9773 is not 9.81.
Answer: Correct, and the report now explains it. The 10.35 to 10.39 and 9.55 to 9.56 readings were earlier the same day; the stored factors 0.9773 and 0.9901 imply the sensors read 10.03 and 9.90 at the moment of calibration, so the uncalibrated readings had shifted between sessions, most likely because the sensors were moved. The "8 percent" is the earlier disagreement; at calibration they were about 1.3 percent apart.
Follow-up: "So the abstract's '8 percent reduced to noise' overstates it?" Yes, the critical review says the same; the honest statement is "an 8 percent disagreement seen earlier; after calibration both read 9.80 to 9.81 in that orientation".
Evidence: Report 4.2; report-review.md arithmetic note; critical review item 2.

C14. Are the IMUs calibrated right now?
Answer: No. In the T15 log of 11 October (v0.7.4) the resting RMS of the magnitude reads about 10.87 m/s2 on IMU1 and 10.12 on IMU2, so the stored factors no longer fit after the rewiring. They must be recalibrated with !recal once mounted on the vehicle, before any ride data are interpreted.
Evidence: BenchTest/logs/2026-10-11_sync_outage_test.log ([RIDE1] rms=10.871, [RIDE2] rms=10.124; my reading of the log, not in the report).

Fusion

C15. Derive inverse-variance fusion and show it reduces to the mean.
Answer: For two unbiased estimates x1, x2 with independent noise variances v1, v2, the minimum-variance linear combination is x_f = (x1/v1 + x2/v2) / (1/v1 + 1/v2), with variance v_f = 1 / (1/v1 + 1/v2). If v1 = v2 = v, x_f = (x1 + x2)/2 and v_f = v/2, so the noise standard deviation falls by root 2.
Follow-up: "Is the equal-noise assumption tested?" Not formally. Same part, settings and calibration make it plausible; it could be checked from each sensor's resting variance (at rest in the T15 log the two sigmas are about 0.022 and 0.030 m/s2, so not identical). On the vehicle it is untested.
Evidence: Report 3.4.3; PROJECT_LOG D24; T15 log values are my reading.

C16. But your two sensors are at different points. Why average two different signals?
Answer: This is the strongest criticism and I accept it. Inverse-variance fusion assumes both measure the same quantity; two mounting points do not. The fused value is best read as an average exposure across the two points, and the disagreement figure D exists precisely to show when they differ. The per-sensor features are kept and published too, so nothing is lost. On the vehicle I would report per-point features as primary (seat base for what the driver feels, near an axle for road input) and use the pair for redundancy and for the transfer between points.
Follow-up: "Then why two IMUs at all?" Redundancy (fallback after 3 s of silence), a check on mounting effects, and two measurement points; the report does not yet state the mounting points or purpose, which the critical review asks for.
Evidence: Report 3.4.3; critical review item 3; mounting-and-enclosures.md proposal (IMU1 under the seat, IMU2 near the front wheel or rear axle, not fitted).

C17. Define the disagreement figure and interpret D = 1.68.
Answer: D = |sigma1 - sigma2| / max(sigma_f, 0.05), where sigma_f is the mean of the two. Since |a - b| / ((a + b)/2) is at most 2, D near 2 means one sensor sees almost all the vibration. D = 1.68 occurred at 72 s in the 25 September session, the first second of the hand disturbance: IMU1 sigma 3.009, IMU2 0.266 m/s2, because one board was knocked harder. The 0.05 floor stops D blowing up at rest, where both sigmas are noise.
Follow-up: "At rest is D meaningless?" Largely: near rest both sigmas are below or near the floor, so D reflects noise; it is meaningful when vibration is well above 0.05 m/s2. The report's phrase "on a hand-held board" should say "disturbed by hand".
Evidence: Report equation 3.6; BenchTest/logs/2026-09-25_bench_fusion_shake.log lines 1333 to 1335.

C18. What are the pairing and fallback rules?
Answer: A pair of windows is fused only if they ended within half a window (500 ms), so they overlap by at least half; if one sensor produces nothing for 3 s, the output falls back to the other and says so. Five boot self-tests check the averaging, D, that R needs both sensors, rejection of a misaligned pair and the fallback. In the 150 s session, 149 of 149 windows were fused from both sensors with skew under 1 ms.
Evidence: Report 3.4.3 and 4.3; T1.

Timing and synchronisation

C19. How do you relate camera time to IMU time?
Answer: A pulse wire. The ESP32 toggles GPIO15 every 500 ms with vTaskDelayUntil and logs each edge's microsecond time; the Pi logs each edge on GPIO17 with a kernel timestamp from the GPIO character device (libgpiod), on the same monotonic clock as the camera's SensorTimestamp. Matching edges gives the mapping between the two clocks. Result: 121 edges, median interval 500.06 ms, range 499.72 to 500.41 ms.
Follow-up: "What does 500.06 against 500.000 tell you?" If both are right, the two clocks run at slightly different rates, about 0.01 percent, roughly 0.4 s per hour, which is why the edges are logged continuously and fitted, not used once as an offset. (My calculation from the logged median, not in the report; with a 0.7 ms spread over 121 edges it is only indicative.)
Evidence: Report 3.7.1 and Table 4.2; BenchTest/logs/2026-09-30_sync_edges_run2.csv.

C20. Why not NTP or GNSS time on both?
Answer: The ESP32 is on cellular while the Pi is on Wi-Fi, NTP over cellular gives tens of milliseconds at best, and the Pi has no GNSS. One wire is simple, deterministic and independent of any network. GNSS UTC on the ESP32 is used separately for the database latency figure.
Evidence: QA_Prep section 9; Server/README (utc_ms from GNSS).

C21. Why did the first Pi logger have a 413.6 ms gap?
Answer: It timestamped edges in a Python callback (gpiozero), so the time was when Python got round to it, subject to scheduling and the interpreter. Kernel timestamps are taken in the interrupt path, which narrowed the spread to under 0.7 ms.
Evidence: Report 3.7.1.

C22. What is the actual frame-to-IMU alignment?
Answer: Two parts. The clock mapping from the pulse is sub-millisecond. The offset between a frame's SensorTimestamp and the true moment of exposure was bounded only by a lens-cover test, under about 1 s, limited by human reporting. An LED driven by the sync pin and filmed would measure it to a frame. Sub-second is enough for labelling ride events after the fact, not for frame-exact work.
Evidence: Report 3.7.1; Appendix E "Camera timing".

FreeRTOS

C23. How does vTaskDelayUntil differ from vTaskDelay?
Answer: vTaskDelay(5 ms) waits 5 ms from now, so execution time and preemption add up and the period drifts. vTaskDelayUntil(&lastWake, 5 ms) wakes at lastWake + 5 ms, computed from the previous target, so variable execution time does not accumulate. If a target has already passed (after a stall) it returns at once, which is the catch-up in C9.
Evidence: Report 3.3; main.cpp lines 633 to 636.

C24. Describe the task layout and why.
Answer: Core 1: Imu1Task and Imu2Task at priority 3 (highest), StatsTask and SyncTask at 2, RideChar1 and RideChar2 at 1. Core 0: ModemTask (GNSS, MQTT, log), BmsTask, DashTask and HallTask, all at 1. Acquisition is alone at the top on core 1, away from the blocking work (modem UART, BLE stack, flash). Acquisition never prints, because serial output blocks for a variable time.
Follow-up: "Why are all modem functions in one task?" The modem UART has no lock; two tasks sending AT commands would interleave and corrupt both streams. One owner serialises access without a mutex.
Evidence: Appendix E Table E.1; main.cpp lines 2848 to 2868; PROJECT_LOG D3.

C25. What happens if a consumer is slow?
Answer: Each IMU sample goes into two bounded queues (100 samples, 500 ms, for statistics; 400 for its ride task) with a zero timeout. If a queue is full, the new sample is dropped and counted rather than blocking, so a slow consumer can never stall acquisition. The drop counters were zero in every session, which proves rather than assumes no loss.
Follow-up: "Why two queues?" So adding the feature consumer cannot change the already-validated acquisition accounting.
Evidence: main.cpp lines 601 to 631; Report 3.3.

C26. Why did flash writes stall a task on the other core?
Answer: On the ESP32, writing or erasing flash disables the instruction cache on both cores, so any code executing from flash pauses until the write completes; that included both IMU tasks, which is why both stalled together although they are on separate buses. Fixes: buffer (done, 8 KB, flush once a minute), put acquisition code and its data in internal RAM (IRAM), or read the IMU FIFO so the sensor keeps sampling through the pause.
Evidence: Report 3.10 and 3.11; Recommendation 1.

Buses and interfaces

C27. Why two I2C buses when the MPU6050 has an AD0 address pin?
Answer: AD0 would let two MPU6050s share a bus at 0x68 and 0x69. I used separate buses (GPIO8/9 and GPIO17/18, 400 kHz, both at 0x68) so each IMU task has its own bus with no contention or locking between the two 200 Hz tasks, and a fault on one bus cannot hang the other. It also leaves 0x69 free on bus 1 for the SEN55.
Follow-up: "What sets the pull-ups?" The IMU modules' own pull-ups to 3.3 V; I measured about 3.3 V idle (T8), important because ESP32 inputs are not 5 V tolerant. For the ToF board, which has no I2C pull-ups, the Pi's 1.8 kOhm pull-ups on pins 3 and 5 are used.
Evidence: Report 3.2; Appendix B tables; T8.

C28. How long does an IMU read take on the bus?
Answer: A burst read of the 14 data bytes plus address and register bytes is roughly 18 bytes, about 160 bits with acknowledgements, so around 0.4 to 0.5 ms at 400 kHz, under a tenth of the 5 ms period. (My estimate; not measured.)
Evidence: estimate only.

C29. How do three VL53L0X with the same address share one bus?
Answer: All three start at 0x29. Each XSHUT (shutdown) line goes to its own Pi GPIO (22, 23, 24). The reader holds all three in shutdown, wakes one, writes it a new address (0x30), wakes the next (0x31), then the last (0x32). If one XSHUT wire comes off, its 10 kOhm pull-up keeps that sensor on at 0x29 from power-up, where it collides with each sensor being woken, so none start; that is the inferred cause of the hang.
Evidence: Report 3.8.3 and 3.12.6; Appendix B.

C30. UART and USB CDC: how do the boards talk?
Answer: Modem: hardware UART at 115200 bit/s 8N1 on GPIO47/48. ESP32 to Pi 4: native USB as a CDC serial device (/dev/ttyACM0), one compact JSON "DASH" line per second, at most about 300 bytes. USB CDC ignores the baud setting; it is a USB bulk transfer. Opening the port did not reset the ESP32 (checked: sequence number already 64 when the bridge started).
Follow-up: "Why a damaged line in T11 v0.7.1?" One sequence number was missing because a line interleaved with another task's serial output; the bridge counts it as bad and uses the next. A dedicated output path or a mutex on Serial would fix it.
Evidence: Appendix E Table E.1; T11, T12.

C31. Explain BLE GATT and the JBD protocol.
Answer: BLE GATT organises data as services containing characteristics. The JBD BMS uses service 0xFF00, a notify characteristic 0xFF01 for replies and a write characteristic 0xFF02 for requests. The unit writes the basic-info query DD A5 03 00 FF FD 77 every 3 s (start byte DD, A5 read, register 03, length 00, checksum FF FD, end 77) and parses the reply framed by its declared length, not by the 0x77 terminator, which can occur inside the data.
Follow-up: "What is the checksum?" 0x10000 minus the sum of the status/register byte pair and the data bytes, as a 16-bit value. For the query, 0x10000 - (0x03 + 0x00) = 0xFFFD. My firmware included the register byte in the reply sum, so every real frame failed by exactly 3.
Evidence: Report 3.5 and 3.12.3; main.cpp lines 889 to 920.

C32. How do you know a checksum-valid BMS frame is right?
Answer: A second, independent plausibility check against a 72 V pack, and field offsets confirmed byte for byte against a teammate's independently written parser. The value 74.78 V, 0 A, 60 percent is plausible (3.12 V per cell for 24 cells) but has not been compared with a meter or the pack's app.
Follow-up: "Which pack is it?" It advertises as DB24SA01L24S150ABU, a 24-cell, 150 A designation, while inherited documentation says the traction pack is lead-acid without a BMS, so it is probably a separate lithium pack; to be confirmed with the vehicle team.
Evidence: Report 3.5; T7.

GNSS

C33. What do fix mode, HDOP and satellite count mean?
Answer: Fix mode 2 is a 2D fix (no altitude), 3 a 3D fix; I required mode 3. HDOP is horizontal dilution of precision, how much the satellite geometry amplifies range errors; around 1 is good. Measured: 23 to 25 satellites (GPS, BeiDou, Galileo), HDOP about 0.9 to 1.5.
Evidence: Report 4.4; T3.

C34. Why did the first fix take 105 s, and what does assisted GNSS change?
Answer: From a cold start the receiver must find satellites and decode orbit data (ephemeris) from the broadcast itself, which takes tens of seconds per satellite; 51 s and 105 s were measured. Assisted GNSS (AT+CAGPS, v0.7.3) downloads orbit data over LTE so the receiver can skip decoding it; it returned success, refreshed every 2 h. Whether it shortens the time to first fix has not been measured.
Follow-up: "And the 60 to 90 s with no reply?" Normal GNSS warm-up after switch-on; other modem commands answered at once, so only the GNSS was waiting.
Evidence: Report 3.6, 3.12.2 and 4.4.

C35. How accurate is the network position?
Answer: AT+CLBS returns a position from the cell towers: on the bench it answered in about 0.7 s with a stated accuracy of 550 m and was about 30 m from the outdoor fix. The 30 m is one reading and luck; the honest figure is the stated 550 m, which is why the map draws a circle, and it is never used for speed, heading or the ride index.
Evidence: Report 3.6.

C36. Is 2.7 m median an accuracy?
Answer: No, it is agreement with a phone, which has its own few-metre error. Over 104 fixes: median 2.7 m, 95 percent within 11.0 m, maximum 12.3 m. Against the 10 m criterion the median passes and the 95th percentile does not.
Follow-up: "What would give true accuracy?" A surveyed point or an RTK reference.
Evidence: Report 4.4; BenchTest/logs/2026-09-30_gnss_rooftop_v052.log.

C37. What units is GNSS speed in?
Answer: The manual says knots ("Speed Over Ground. Unit is knots"), so the evidence points to knots; I kept it unconfirmed on the fitted modem because it read 0 to 5.8 while stationary and I have not checked it against a known speed. It is not mapped to the dashboard speed until checked on the road test.
Follow-up: "Is R computed while stationary, with v_min = 1 and readings up to 5.8?" It could be, which is a real problem: R needs a minimum speed in confirmed units and stationary noise rejected (for example with a fix-quality or position-change check).
Evidence: SIMCom A76XX manual v1.09 (opened, the +CGNSSINFO speed field); Report 4.4; critical review questions.

C38. How does the parser reject bad replies?
Answer: It anchors on the latitude hemisphere letter and reads fields relative to it, which fits the 9-, 17- and 18-field layouts seen; it accepts a fix only if the coordinate, date and time formats are valid and the implied jump from the previous fix is under 100 m/s. That rejected replies garbled by a competing query.
Evidence: Report 3.6.

LTE and AT commands

C39. What is LTE Cat 1 and why is it suitable?
Answer: A low-rate LTE category (roughly 10 Mbit/s down, 5 up) on the normal LTE network, so it works wherever 4G does, unlike LTE-M or NB-IoT which need operator support. My records are about 0.7 to 1.1 KB every 10 s, so the link is far from limiting.
Follow-up: "Bandwidth budget?" About 250 to 400 KB an hour of payload, 2 to 3 MB per 8-hour day, an estimate from record size excluding MQTT and TCP overhead, not a measured bill.
Evidence: Report 3.2 (Cat-1); Server/README (record size). Cat 1 rates are general knowledge, not in the repository.

C40. How does the firmware publish with AT commands?
Answer: AT+CMQTTSTART, AT+CMQTTACCQ (client), AT+CMQTTCONNECT (broker, keep-alive 60 s, clean session), then per message AT+CMQTTTOPIC and AT+CMQTTPAYLOAD with the raw bytes after a ">" prompt, and AT+CMQTTPUB=0,1,60 (client 0, QoS 1, 60 s timeout). The modem returns OK and then a separate result line, +CMQTTPUB: 0,0 for success; since v0.5.0 the firmware waits for that line instead of trusting OK.
Follow-up: "Why does that matter?" The manual shows OK can precede a failure code; the first version reported success that had not happened.
Evidence: main.cpp lines 1730 to 1800; SIMCom manual section 18.2.6 p. 406 (opened).

C41. How is a coverage loss detected and recovered?
Answer: From the modem's own unsolicited report (lost network or dropped client) or after three failed publishes. The old session is shut down in the order the manual requires; retries at 30 s doubling to 5 minutes; since v0.5.3 it also reconnects as soon as the modem reports packet data is back. Test: radio off 60 s; loss seen after 0.8 s (modem report) or 20.7 s (three failures); v0.5.0 reconnected 36 s after the radio returned although data were back in 2.4 s; v0.5.3 about 5 s.
Evidence: Report 3.10 and 4.7; T6.

MQTT, store-and-forward and the database

C42. Explain MQTT QoS 0, 1 and 2.
Answer: QoS 0: sent once, no acknowledgement, can be lost. QoS 1: the sender keeps the message until it receives a PUBACK and resends otherwise, so delivery is at least once and duplicates are possible. QoS 2: a four-step handshake (PUBLISH, PUBREC, PUBREL, PUBCOMP) for exactly once, at more cost. I use QoS 1 and make the database idempotent, which gives effectively-once storage without QoS 2's overhead.
Follow-up: "What does PUBACK actually guarantee?" Only that the broker received it, not that any subscriber stored it. See C44.
Evidence: SIMCom manual QoS definitions (opened); general MQTT 3.1.1 semantics (standard not in the repository).

C43. How does store-and-forward work in v0.7.4?
Answer: Every record gets a boot number (incremented in NVS) and a sequence number that never repeats, also across reboots (reserved from NVS in blocks of 64). Each record is logged to flash whether or not MQTT is up. A record is marked done only when +CMQTTPUB: 0,0 arrives. After an outage the unit reads unacknowledged records back from the log, oldest first, and republishes them with "replay": true at up to about 3 per second while new records continue. Records that can no longer be sent (log truncated, cleared, logging off) are counted as lost, never skipped silently.
Evidence: Server/README "How a record gets from the unit to the database"; TelemetryUnit/include/sync_ledger.h.

C44. What does idempotent ingest mean and why do you need it?
Answer: Storing a record twice has the same effect as storing it once. The ingest keys each row on (device, boot, seq), so a replay or a QoS 1 redelivery is counted as a duplicate and not stored again. Without it, at-least-once delivery would put duplicates in the database.
Follow-up: "What about the gap between broker ack and storage?" A real weakness: the public broker acknowledges a record even when my ingest is not subscribed and does not queue it, so that record is marked done on the unit and never resent. In T15 this is why 24 records were backfilled from the unit's log. Fixes: a broker under our control with persistent sessions and queued QoS 1 messages, or an application-level acknowledgement from the database back to the unit.
Evidence: Server/README "Known limits"; TEST_PROCEDURES T15; BenchTest/logs/2026-10-11_t15/2026-10-11_t15_summary.csv (imported_from_log 24).

C45. What is a persistent session, and what went wrong with it?
Answer: With clean session off, the broker remembers a client's subscriptions and queues QoS 1 messages while it is offline. During T15 the ingest's persistent session on test.mosquitto.org stopped delivering while still connected: records reached the broker but none reached the database for over an hour. Persistent sessions are now opt-in, and log read-back is the safety net on this broker.
Evidence: TEST_PROCEDURES T15 "Found and fixed during the test" (commit 892219f).

C46. Why SQLite?
Answer: A single-file, serverless database that runs on the Pi 5 as a normal user with no administrator, needs no separate service, supports a unique key for dedupe, and is enough for one vehicle's 10 s records. A fleet would move to a server database.
Evidence: Server/README.

C47. How is end-to-end latency to the database measured, and why is it missing?
Answer: Receive time on the Pi 5 (NTP-synchronised) minus the device's UTC from its GNSS time. Indoors there was no fix, so no device UTC and no latency figure; it needs the road test.
Evidence: TEST_PROCEDURES T15 (latency not measured); t15_summary.csv (latency_live_n 0).

Object detection and ML

C48. How does SSD-MobileNet work, briefly?
Answer: MobileNet is the feature extractor, built from depthwise separable convolutions (a per-channel spatial filter followed by a 1x1 channel mix), 8 to 9 times cheaper than standard convolutions. SSD attaches small prediction heads to several feature maps of different resolution; at each location a set of default boxes of several shapes gets class scores and box offsets in one pass; overlapping boxes are then pruned by non-maximum suppression. One pass, no separate region proposal, so it is fast.
Evidence: liu2016_ssd.pdf, howard2017_mobilenets.pdf (opened).

C49. What is non-maximum suppression?
Answer: Many default boxes fire on one object. NMS sorts detections by confidence, keeps the best, removes any other box of the same class whose intersection over union with it exceeds a threshold, and repeats. I also wrote NMS myself for the NCNN pothole path, since there was no PyTorch on the Pi.
Evidence: liu2016_ssd.pdf; Appendix E "Pothole model" (NMS written for NCNN).

C50. What does 8-bit quantisation do?
Answer: Weights and activations are stored as 8-bit integers with a scale and zero point per tensor, so inference uses integer arithmetic: about four times smaller than 32-bit floats and faster on a CPU without a float accelerator, at a small accuracy cost (Jacob et al. 2018). It is what makes the detector run at about 20 fps on the Pi 4's CPU.
Evidence: jacob2018_quantization.pdf (opened).

C51. What is COCO, and what can your detector not see?
Answer: COCO has 91 object types (80 used for detection) photographed in everyday scenes. It has no potholes, debris, speed bumps or South African minibus taxis as a class, and its viewpoints are not a low trike camera. I report only person, bicycle, car, motorcycle, bus, truck and dog, the categories in the ethics application, at confidence 0.5 or more.
Evidence: lin2014_coco.pdf; hazard_detector.py lines 93 to 115.

C52. Explain precision, recall, mAP@50 and mAP@50-95.
Answer: Precision: of the boxes the model reported, the fraction that were right. Recall: of the real objects, the fraction found. A detection counts as right when its intersection over union with a labelled box is at least a threshold. Average precision is the area under the precision-recall curve for one class; mAP averages over classes. mAP@50 uses IoU 0.5; mAP@50-95 averages over IoU 0.5 to 0.95 in steps of 0.05, so it also rewards tight boxes. Run 2 at 640: mAP@50 0.714, mAP@50-95 0.349, precision 0.811, recall 0.623.
Follow-up: "Why is mAP@50-95 so much lower?" Pothole edges are vague and small, so boxes rarely overlap labels tightly.
Evidence: CameraDetection/training/runs/run2_sa_band_tiles_640/README.md.

C53. Validation set versus held-out test set: why does it matter for your 0.714?
Answer: Training used the validation tiles to choose the best epoch (54 of 60), so the validation score is optimistically biased: it was used to make a decision. A held-out test set, never used for any decision, gives an unbiased estimate. The South African dataset has its own test folder (605 images); the held-out score is still to be computed with score_heldout.py, which refuses to report the validation split as held out.
Follow-up: "Any data leakage?" Tiles were split by frame, so the three tiles of one frame are always in the same split; no tile-level leakage. But frames were shuffled randomly into train and validation, so if the dataset contains near-consecutive dashcam frames, near-duplicates can sit on both sides and inflate the validation score further. The dataset's own test folder avoids that.
Evidence: run2 README; CameraDetection/training/make_notebook.py lines 106 to 112 (split by frame stem, random shuffle) and cell 2g (tiles from split frames).

C54. Why tiling, and what does it cost?
Answer: South African potholes have a median size of 100 by 26 px in 3680 by 2760 frames; shrinking the whole frame to 640 makes them about 17 by 4.5 px, too small to detect, which is why run 1 scored 0.000. All pothole centres lie between 48 and 62 percent of the frame height, so run 2 crops the band from 42 to 68 percent and cuts three overlapping 1280 px tiles: a median pothole becomes about 50 by 13 px. The cost is three inferences per frame: 0.55 to 0.75 s for three tiles beside the main detector on the Pi 4.
Evidence: Appendix E "Pothole model"; TEST_PROCEDURES C10.

C55. Why is the pothole path off on the Pi?
Answer: The criterion was fps and latency within 10 percent of the detector without it (14.6 fps, 121 ms median). Only one setting met it: one thread at 0.25 Hz, giving 13.9 fps and 125 ms; at 1 Hz the detector fell to 12.0 fps and 138 ms. The 640 export took 2.2 s and missed the pothole in the test picture. So it is experimental and off by default; a picture check found a pothole at confidence 0.63 with an alert using the same five fields.
Evidence: TEST_PROCEDURES C10.

Distance, ToF and fusion

C56. Derive distance from box width.
Answer: Pinhole camera: an object of real width W at distance d projects to w = f W / d pixels, so d = f W / w, with f the focal length in pixels. f follows from the field of view: f = (image width / 2) / tan(HFOV / 2) = 320 / tan(26.75 degrees), about 635 px for 640 px and 53.5 degrees. The code uses a 600 px placeholder until calibration (test C5), so distances are about 6 percent short from f alone.
Follow-up: "Other errors?" The assumed width (1.8 m for a car against real cars from about 1.6 to 2.0 m, about plus or minus 11 percent), viewing angle (a side-on bicycle looks much wider than 0.6 m, so it reads at roughly a third of its true distance), partial occlusion and lens distortion. Hence coarse bands: immediate under 3 m, warning under 8 m, monitoring under 15 m.
Evidence: hazard_detector.py lines 43, 93 to 124, 151 to 155; PROJECT_LOG 4.2. The 635 px and error percentages are my arithmetic.

C57. How is bearing computed?
Answer: From the box centre x (normalised, 0.5 at the centre) through the pinhole model: bearing = atan((2x - 1) tan(HFOV/2)), not linear in x. Negative is left.
Evidence: hazard_detector.py lines 158 to 166.

C58. What are the limits of time-of-flight sensing?
Answer: A ToF sensor times infrared light to the nearest surface in its cone. Sunlight adds infrared background and shortens range; dark or angled targets return less light, so fewer valid readings (Caroleo: 18.8 to 34.4 percent valid on black for the VL53L5CX); it gives distance, not identity; and it reports the nearest surface, which need not be the object the camera saw. The VL53L0X stand-ins reach about 2 m indoors; I use 1.2 m. At 30 km/h, 1.2 m is about 0.14 s of travel, so they serve manoeuvring, not road speed.
Evidence: Report 2.8, 3.8.3, Discussion "Hazard sensing".

C59. Explain your camera-ToF fusion rules.
Answer: The bridge polls the detector at 5 Hz. A detection is matched to a sensor if its bearing lies in that sensor's cone widened by a 5 degree gate and the sensor's nearest sample is within 200 ms, valid and in range; the nearest reading wins and each sensor serves one detection. Matched: a "fused" hazard with the camera's class and the ToF distance. Unmatched: the camera estimate. A sensor with three valid in-range readings and no match reports an unclassified "obstacle". Camera data older than 1 s are ignored. With the default geometry (sensors at -35, 0, +35 degrees, 12.5 degree half-angle; camera plus or minus 26.75 degrees) the side cones overlap the camera's view only at its outer edges.
Follow-up: "Is it validated?" No: 29 offline tests pass; the live run shows matching works, but C9 (calibrate cones and focal length, then walk across, stand at 0.5, 1.0, 1.5 m against a tape, a box outside the classes, a person at 2.5 m) has not been run.
Evidence: Report 3.8.3; CameraDetection/fusion_config.json; TEST_PROCEDURES C9.

C60. Your first fused hazard: camera 0.874 m, ToF 0.096 m. Which was right?
Answer: I cannot say from that run, because no tape distance was recorded; the right ToF read 0.17 m at the same moment and the detector was at 6.2 fps on a browning-out Pi. It shows the matching works on live data and that an uncalibrated camera distance can be a whole band wrong at close range. The accuracy claim waits for C9.
Evidence: TEST_PROCEDURES C9 "First fused hazard"; critical review item 10.

Latency

C61. How did you measure detector latency, and from where to where?
Answer: Every frame carries Picamera2's SensorTimestamp, the time the first pixel was read out, on the same monotonic clock as time.monotonic_ns. The detector records readout to capture (queue), preprocessing, inference, alert logic and total, and reports median, 95th percentile and maximum every 5 s. Bench: 102 ms median, 120 p95, 136 max at 19.5 fps; queue 52, pre 12, inference 36, alert logic 0.1. It excludes exposure time and anything after the detector.
Follow-up: "Why is the queue 52 ms?" It covers readout itself and the camera's image processing (ISP) before the frame reaches the detector.
Evidence: Report Table 4.3; BenchTest/logs/2026-09-30_c4_latency/.

C62. What is the latency from hazard to the driver's eyes?
Answer: Not measured end to end. It adds up as: detector about 0.1 s, three-frame onset about two frame intervals more (about 0.2 s total at 19.5 fps, about 0.25 s at 14.6), the bridge's 5 Hz fusion poll (up to 0.2 s), the dashboard's 0.5 s poll and rendering. Worst case is probably near 1 s for the fused banner, around 0.7 s for the camera page. The "alert listed in 0.5 s" figure is time after opening the page with a person already in view, not onset latency. Pushing alerts (websocket or server-sent events) would cut the polling.
Evidence: Report 4.5 and 4.8; critical review item 2 and 10; the sum is my estimate.

C63. Is about 0.2 s fast enough? Where does your 0.5 s criterion come from?
Answer: At 30 km/h, 0.2 s is about 1.7 m of travel, small against a typical driver reaction time of over a second. The 0.5 s onset criterion in R7 was set as "comfortably below reaction time", not derived from stopping distance at 42 km/h, which the critical review rightly says it should be. Present it as a provisional engineering target.
Evidence: Report Table 1.1 and 4.5; critical review item 10.

C64. Why is the integrated Pi slower: 19.5 fps against 14.6?
Answer: The 19.5 fps benchmark ran with nothing else; the 14.6 fps check ran with the telemetry bridge, fusion polling at 5 Hz and the live preview being viewed, at 66 C; inference rose from 36 to about 51 ms. I have not isolated which load causes it, so I quote both with their conditions.
Evidence: BenchTest/logs/2026-10-10_bench_observations.md.

Power

C65. What is USB current limiting and why did it matter?
Answer: A Pi's USB ports share a current budget from the Pi's own 5 V supply (the Pi 5 limits them to 600 mA in total on a 3 A supply). An LTE modem draws short transmit bursts of well over its average current; drawn through the Pi's USB port, they pulled the Pi's supply below its under-voltage threshold. The fix is a separate supply (a powered hub) for the telemetry unit.
Evidence: Report 3.12.7 and Discussion "Integration and power". Modem burst current was not measured.

C66. What do the throttling flags mean?
Answer: vcgencmd get_throttled returns bits: bit 0 under-voltage now, 1 frequency capped now, 2 throttled now, 3 soft temperature limit now; bits 16 to 19 the same "since boot". 0x50005 = under-voltage and throttling now and since boot (4 October, detector at 6.1 fps). 0xd0000 = under-voltage, throttling and soft temperature limit since boot (10 October, 81 C without a fan). 0x0 after the fix.
Evidence: BenchTest/sw7_check.py lines 206 to 222; TEST_PROCEDURES T13; bench_observations.md.

C67. What is brown-out, and how did it show up?
Answer: The supply sags below what the processor needs; the Pi first flags under-voltage and throttles to 600 MHz, and if it sags further it resets. On 10 October, with the unit on the Pi's USB port, the Pi restarted three times in about 20 minutes; with the unit moved off, none in 4 hours.
Evidence: Report 3.12.7; bench_observations.md.

C68. What is the system's power consumption?
Answer: Not measured. That is an open brief requirement (GA5 asks to operate within the electrical draw of the 72 V battery). The plan is a fused DC-DC converter from the vehicle supply and current measured on each rail.
Evidence: Report 3.1 and Recommendation 3.

### D. Design decisions

D1. Why an ESP32 plus a Pi rather than one board?
Answer: The two deciding requirements pull in opposite directions. R1 needs a guaranteed 5 ms period with no loss: an MCU under FreeRTOS holds it (200.0 to 200.5 Hz measured), but cannot run a camera network at a useful rate. R7 needs detection at a useful frame rate: the Pi runs it (19.5 fps), but a general-purpose Linux scheduler gives no guarantee of a 5 ms period. Splitting keeps each part where it is predictable; the cost is a second supply, a USB link and a sync wire.
Follow-up: "Pi 5 with the Hailo-8 accelerator?" It could run the detector at camera rate and remove the Wi-Fi hop, but the accelerator was not enabled on the PCIe bus and was not tested.
Evidence: Report Table 3.1.

D2. Why the Makerfabs ESP32-S3 A7670X board?
Answer: One board gives a dual-core MCU (acquisition on one core, blocking work on the other), BLE for the battery, native USB, and an LTE Cat 1 modem with GNSS, so processor, modem and GNSS could be tested without a separate modem circuit.
Follow-up: "Any problems with it?" The microSD chip-select passes through a resistor (R23) marked not fitted, so logging uses internal flash; and UART0 goes to a separate CH340K port, which caused the serial-routing fault.
Evidence: Report 3.2; Appendix E "Serial routing".

D3. Why the MPU6050?
Answer: It was available, cheap, well supported (Adafruit library), with selectable range and digital low-pass filter, and adequate noise for a first response measurement. The report does not justify it against alternatives; a lower-noise part (for example one with a deeper FIFO and higher output data rates) would be the upgrade. Be honest: it was an availability choice.
Follow-up: "What would you choose now?" A sensor with a hardware FIFO and anti-aliasing designed for vibration, read through the FIFO so flash pauses do not matter.
Evidence: critical review item 3 (selection not justified).

D4. Why two IMUs and where will they be mounted?
Answer: Redundancy, a check on mounting effects, and two measurement points. Proposed: IMU1 on the frame under the driver's seat (the ISO 2631-1 seat-base point, what the driver feels) and IMU2 on the frame near the front wheel or rear axle (closer to the road input), both hard-mounted, not on plastic panels, in the same orientation. This is a proposal to confirm with the supervisor on the vehicle.
Evidence: Planning/mounting-and-enclosures.md (proposal, nothing fitted).

D5. Why SSD-MobileNet and not YOLO on the Pi 4?
Answer: Measured, not assumed. YOLO11n through NCNN at 320 input ran at 7.9 fps and 175 ms median (258 ms p95, inference 111 ms) against SSD-MobileNet's 19.5 fps and 102 ms. With a three-frame onset, YOLO would give roughly 0.4 to 0.5 s onset against about 0.2 s. YOLO is more accurate, especially for small objects, which is why the pothole model uses it, but not for the live alerts on this CPU.
Follow-up: "That YOLO run was 15 s with nothing in view." Yes, a trial; full 60 s runs are still to do.
Evidence: TEST_PROCEDURES C8a; Appendix E "Pothole model".

D6. Why LiteRT, not tflite-runtime?
Answer: There are no tflite-runtime wheels for Python 3.13 on Pi OS Trixie; LiteRT (ai-edge-litert) is Google's successor with the same model format.
Evidence: PROJECT_LOG D29.

D7. Why a ToF stand-in?
Answer: The VL53L5CX (8x8 zones over 63 degrees, one device for left, centre and right) had not arrived by 30 September. Three VL53L0X on a UCT micromouse sensor board give left, ahead and right with about 2 m range, so the fusion and the dashboard could be built and tested now. When the VL53L5CX arrives it has a five-step bench validation plan.
Evidence: Report 3.8.3; Appendix E "Planned VL53L5CX validation".

D8. Why are the ToF sensors on the Pi and not the ESP32?
Answer: The Pi sits at the front beside the camera, its I2C bus is free, the fusion runs there, and the ESP32's 200 Hz acquisition stays untouched.
Evidence: Report 3.8.3.

D9. Why a public broker?
Answer: Only to prove the cellular path. test.mosquitto.org is unauthenticated and unencrypted, so it was never a destination for real data, and the vacation-work team's broker credentials were deliberately not put into this code (their documentation says they must not be shared with an AI assistant). The firmware reads a broker, user and password from a git-ignored header, so moving to the team's broker is a configuration change.
Evidence: Report 3.10; PROJECT_LOG D4; CHANGELOG 6 Oct (mqtt_secrets.h).

D10. Why live-only on the dashboard?
Answer: On 3 October the Pi 4 changed address, the dashboard could not reach it and silently fell back to its simulator, so invented but plausible numbers were on screen, including 82 percent battery that was the simulator's value. On a vehicle that is worse than showing nothing. In live-only mode the simulator never runs; missing data shows "--" or "Unavailable", and data older than 3 s or lost for 2.5 s return the display to that state, never to simulation.
Evidence: Report 3.8.4 "Data validity".

D11. Why patch the team's dashboard rather than write your own?
Answer: It is the vehicle's existing driver display with the team's visual language and features (speed, battery, voice); a second app would be a second display. I did not change their code: a deploy script copies their installed v1.1 and applies 63 edits, each of which must match its anchor text exactly once or nothing is written, and refuses to touch their folder. Their service is disabled, not removed; one command restores it.
Follow-up: "What if their code changes?" An edit whose anchor no longer matches makes the deploy stop rather than produce a broken mix; the edits are listed for the team to review.
Evidence: Report 3.8.4; DashboardIntegration/README.md.

D12. Why OpenStreetMap tiles and Photon search, and not the team's web map?
Answer: The team's Leaflet web map (QtWebEngine) segfaulted about 2 s after being shown on the Pi 5, with online or offline data, and a native crash takes the whole dashboard down. I drew OSM tiles directly with Qt instead, within the OSM tile policy (two requests at a time, identifying user agent, no bulk download), cached for 30 days, with routes from the public OSRM service. Destination search uses Photon, a free OpenStreetMap-based geocoder that needs no API key (DashboardIntegration/sw7_search.py).
Follow-up: "Is OSM attributed?" Not yet in the report; the licence requires attribution and the critical review lists it.
Evidence: DashboardIntegration/PI5_MAP_CRASH.md; Appendix E "Dashboard map"; destination search in REMAINING_WORK 3.1.

D13. Why the Pi 4 for the camera rather than the Pi 5?
Answer: The Pi 5 runs the inherited dashboard and there was one storage card; developing on it would have put a working deployment at risk, and a camera crash cannot take the dashboard down this way. The cost is a network hop.
Evidence: PROJECT_LOG D6; Report 3.1.

D14. Why local logging to internal flash?
Answer: The microSD slot's chip-select is not connected (R23 not fitted), so a LittleFS file system in the 3.375 MiB data partition is used, capped at 3 MB, about 18 hours at 160 KB an hour. LittleFS is power-loss tolerant and wear-levels.
Follow-up: "Truncation, not rotation?" Yes, a limitation; rotation is a recommendation. With v0.7.4 a truncated, unsent record is counted as lost.
Evidence: Report 3.10; Appendix E Table E.1.

D15. Why JSON and not a binary format?
Answer: Human-readable, self-describing, parseable everywhere, which mattered for debugging and for the dashboard contract; the cost is size (0.7 to 1.1 KB per record). At one record per 10 s the bandwidth is negligible on LTE Cat 1. A binary encoding (CBOR, protobuf) would be the choice for a fleet.
Evidence: Server/README; reasoning.

D16. Why the three-frame on, five-frame off hysteresis?
Answer: A single-frame clear made one standing person produce 16 alerts in 47 s, because confidence hovered around the 0.5 threshold. Three frames to raise suppresses one-frame false positives; five empty frames to clear (about 0.25 to 0.35 s) stops flicker; escalating to a nearer band also needs three frames.
Evidence: Report 3.7.2; PROJECT_LOG D28.

### E. Results and every key number

E1. Sampling: what exactly did you show?
Answer: Both IMUs at 200.0 to 200.5 Hz with zero dropped samples in every recorded session, including with BLE, modem and dashboard line running (400 to 401 samples per 2 s window). It shows the scheduling holds on the bench. It does not show behaviour under vehicle vibration, heat or supply noise.
Follow-up: "Zero drops but 25 to 30 ms gaps?" See E2.
Evidence: Report Table 4.1; T1, T2, T9, T11.

E2. Then what were the 25 to 30 ms and 33 to 40 ms gaps?
Answer: Flash writes. In the 25 September session the maximum interval reached 25 to 30 ms in about one window in six, every 12 s. With a write every 10 s (v0.5.0), 33 to 40 ms at every write; with logging off, worst 5.9 ms. With buffered logging (v0.6.0), 37 to 40 ms about once a minute, all within 3.5 s of a flush, worst 5.9 ms elsewhere. No samples were lost because the queue absorbs the backlog and samples carry true timestamps, but each pause leaves about eight missing sample instants, then bunched samples.
Follow-up: "So 'zero dropped samples' hides gaps?" Yes, the two are different measures, and the report should state both. During T15 under v0.7.4 (replay reading the log) I count 10 windows with a gap over 10 ms out of 368, worst 44.1 ms, all at 200 Hz with no drops.
Evidence: Report 4.1; PROJECT_LOG F6; T15 log (my count).

E3. Calibration factors?
Answer: Development board first calibration: 0.9773 and 0.9901, then both 9.80 to 9.81 m/s2. Target board first boot: measured 9.4387 and 9.5725, factors 1.0390 and 1.0245; later 9.93 and 10.10 (1.3 and 2.9 percent high). R2 met at calibration, not later.
Evidence: Report 4.2; T4.

E4. Features and fusion on the bench?
Answer: Self-tests pass at every boot; 149 of 149 windows fused, skew under 1 ms (222 lines because either task can print a window). Still: sigma median 0.041, max 0.067 m/s2. Hand disturbance: sigma up to 9.35, largest window peak-to-peak 77.6 m/s2. D 0.00 to 1.68. It shows the features compute and combine as designed; it does not show how they respond to road or motor.
Evidence: Report 4.3; BenchTest/logs/2026-09-25_bench_fusion_shake.log.

E5. GNSS numbers?
Answer: 3D fix in 105 s from cold (51 s earlier), 23 to 25 satellites, HDOP about 0.9 to 1.5; 104 fixes: median 2.7 m, 95 percent within 11.0 m, max 12.3 m from a phone. Network position 0.7 s, 550 m stated.
Evidence: Report 4.4; T3.

E6. Battery numbers?
Answer: 14 consecutive valid records over about 140 s on the vehicle: 74.78 V, 0.00 A, 60 percent (3.12 V per cell), at -88 to -93 dBm, then the link dropped. Not compared with a meter.
Evidence: Report 4.5; T7, T10.

E7. Detector numbers, and which is "the" figure?
Answer: Two conditions, both measured. Bench (30 September, nothing else running, 4 threads): 19.5 fps, 102 ms median, 120 p95, 136 max, CPU 65.7 C, no throttling; with the live-view server 17.3 fps, 105/127; one thread 7.0 fps, 186/207. Integrated healthy Pi (11 October, bridge, fusion and preview viewed, 66 C): 14.6 to 14.7 fps, 118 to 122 ms median, 146 to 148 p95. The integrated figure represents the vehicle configuration better.
Evidence: Report Table 4.3; bench_observations.md.

E8. T15: what does 112 of 112 mean?
Answer: In the 10-minute outage test on 11 October (v0.7.4, ingest on the Pi 5, public broker, indoors): 60 records built up, lost 0; the modem reconnected 5.2 s after the radio returned; the unit's backlog was zero 48.0 s after the radio returned (42.8 s after reconnecting). The database held 112 of 112 records of that boot, 0 missing sequence numbers, 0 duplicates; the 60 replays arrived in 37.3 s (1.58 per second); against the unit's own log, 111 of 111 logged records were stored.
Follow-up: "Did all 112 arrive over MQTT?" No, and say it first: 24 were backfilled from the unit's log, two published while the ingest was being restarted and the rest from before an ingest fix. So the test shows completeness of the system including log read-back, and that replay works; on this broker the log is the safety net. Latency was not measured (no GNSS time indoors).
Evidence: TEST_PROCEDURES T15; BenchTest/logs/2026-10-11_t15/2026-10-11_t15_summary.csv; 2026-10-11_sync_outage_test.log.

E9. Read-back of 6,020 records?
Answer: On 1 October the whole stored log was read back over USB with an indexed, length-checked, repeated dump: 6,020 records (2.2 MB, about 16.7 hours) complete after four passes. 5,545 (92 percent) were not valid JSON because missing values were printed as nan; after the v0.6.3 change to null, all parse.
Follow-up: "Why four passes?" The serial link also carries other output, so some records arrived damaged; each pass keeps intact records by index and length, and repeats until every index is present. The one missing index was a record written during the dump.
Evidence: Report 3.12.4 and 4.7; T10.

E10. MQTT and recovery numbers?
Answer: 47 of 47 publishes acknowledged, forced reconnection in 0.4 s; radio off 60 s: loss seen in 0.8 s or 20.7 s, retries at 30 and 60 s, reconnect about 5 s after the radio returned (v0.5.3; 36 s in v0.5.0).
Evidence: Report 4.7; T2, T6.

E11. Dashboard link numbers?
Answer: DASH line: 40 of 40 lines in 40 s, no missing sequence numbers, valid JSON, at most 272 bytes, IMUs unaffected. Through the bridge: record 0.37 s old at a laptop; pre-test check 0.5 s old, telemetry answering in 18 ms. Camera page: video in 0.6 s, 14.2 fps decoded against 14.8, longest gap 0.22 s, person alert listed 0.5 s after opening, offline state within a second.
Follow-up: "Those are laptop measurements." Yes; the Pi 5 run was offscreen against the live bridge. Onset to screen on the Pi 5 is outstanding.
Evidence: Report 4.7 and 4.8; T11, T12, B2.

E12. ToF results?
Answer: Three sensors answered at about 31 readings per second each; a cover test confirmed left, ahead and right in order; after the hang fix, a three-minute hand test gave 80 to 264 mm ahead and 157 to 199 mm right with a hand about 20 cm away. That is functional, not accuracy: no tape check yet.
Evidence: Report 4.6 and 3.12.6; BenchTest/logs/2026-10-10_tof_hand_test.txt.

E13. Pothole numbers?
Answer: Run 1 (public 608-image set): 59.7 percent mAP@50 on its own test images, 0.000 on 605 South African test images (1,238 potholes). Run 2 (road-band tiles): 0.714 mAP@50 at 640 and 0.566 at 320 on validation tiles. Pi path off by default for speed.
Evidence: Report Table 4.2; Appendix E.

E14. Pi 4 power and temperature numbers?
Answer: Under-voltage 14 s after the unit was plugged into the Pi's USB, recurring, throttle to 600 MHz, detector 14.3 to 12 fps; three restarts in 20 min, none in 4 h after moving it. 81 C without a fan; with a fan 48 to 49 C after boot, 57 C later, 66 C after 5 hours of detector and bridge.
Evidence: Report 3.12.7; bench_observations.md.

E15. Touch numbers?
Answer: Reading the touch controller over 25 taps: contact reported with the first position in every tap, so the panel adds no measurable delay; taps lasted 200 to 640 ms and the buttons act on release; load average 0.04.
Evidence: Report 4.8.

### F. The seven fault investigations

Tell each in five beats: symptom, candidate causes, deciding test, cause and fix, lesson.

F1. Boot loop after enabling the full flash
Symptom: with 16 MB flash and a matching partition table, the chip reset about once a second at the same program counter.
Candidates: PSRAM setting, the flash override, the code, the hardware.
Deciding tests: adding a PSRAM type left the same loop at the same PC (not PSRAM alone); removing every override restored running (not code or hardware); the ROM boot banner reported dual-I/O (DIO) flash while the setting asked for quad-I/O, and chip detection confirmed 8 MB PSRAM.
Cause and fix: wrong flash access mode; 16 MB with DIO set together with the partition table booted and mounted LittleFS.
Lesson: change one setting at a time; size, mode and table must be set together.
Evidence: Report 3.12.1.

F2. Modem power key, GNSS warm-up and reply layout
Symptom: wrong field count indoors; 60 to 90 s with no GNSS reply; first fix near latitude and longitude zero; a later capture with no reply at all.
Candidates: a reply layout different from the 13 fields assumed; normal warm-up; a modem that was not running.
Deciding tests: the raw reply logging showed 9 empty fields indoors and 17 or 18 with a fix, in decimal degrees, so the parser had read satellite counts as position; a modem running for minutes answered every poll, and during warm-up answered other commands, so only GNSS waited; the silent capture also ignored MQTT commands, so the modem was off: the boot power-key pulse toggled a running modem off after each reflash.
Cause and fix: parser anchored on the hemisphere letter (v0.5.3); power key pulsed only if AT gets no answer (v0.5.2).
Lesson: log raw replies; design tests that separate overlapping symptoms; allow warm-up before recording.
Evidence: Report 3.12.2.

F3. Battery connection and checksum
Symptom: no advertisements, then a link that dropped, then frames all rejected on checksum.
Candidates: pack absent or scanner idle; characteristics under another service; stuck BLE stack; wrong checksum.
Deciding tests: logging every advertiser showed none at all in a room full of devices, so the scanner was idle (it waited for an address set only after discovery); a teammate's parser found the characteristics directly, so search every service; a power cycle did not change failures, ruling out a stuck stack; the firmware's own query frame DD A5 03 00 FF FD 77 shows the checksum excludes the register byte, and replies failed by exactly 3.
Cause and fix: v0.5.4 corrects the sum and prints failing frames; 14 valid records followed on the vehicle.
Lesson: a community-reverse-engineered formula is a hypothesis; check it against a frame you know is right.
Evidence: Report 3.12.3.

F4. Invalid JSON found only by reading the log back
Symptom: 5,545 of 6,020 records failed to parse; earlier transfers had lost characters.
Candidates: damage in transfer, or records wrong as stored.
Deciding test: indexed, length-checked, repeated dump: all 6,020 intact after four passes, so not transfer; every failing record contained nan.
Cause and fix: missing values printed as nan (not valid JSON); v0.6.3 writes null.
Lesson: the same text had gone out over MQTT and watching the live stream had not shown it; read back the whole record, and count parse failures at the receiver.
Evidence: Report 3.12.4.

F5. Camera colour cast
Symptom: the live view was pink.
Candidates: the detector's channel order, the camera itself, no infrared-cut filter.
Deciding tests: a still taken outside the detector with the standard tuning was also pink (not channel order); with the NoIR tuning the wall was neutral (the module has no IR-cut filter).
Cause and fix: NoIR tuning plus saturation 1.8 (blue card 1/86/216, red 222/8/77); black objects then looked purple, corrected in the live view only, because the correction took 84 to 171 ms a frame.
Lesson: one test per hypothesis; measure the fix with colour cards. Still to do: daylight recheck, and whether the cast changed detection confidence.
Evidence: Report 3.12.5; Appendix E Table E.3.

F6. ToF start-up hang
Symptom: all distances null (6 October), then the reader froze (10 October).
Candidates: one sensor not answering; the driver waiting for ever.
Deciding tests: an I2C scan showed only the left sensor; start-up stopped at the first failure and lost all three, so it was changed to skip, log and re-probe every 60 s; then the freeze: the driver's I/O timeout defaults to zero, meaning wait for ever. With a 0.5 s timeout all three timed out while a device stayed at 0x29 even with every XSHUT low: one sensor not under its shutdown line.
Cause and fix: inferred loose XSHUT wire (pull-up keeps that sensor on at the shared address); reseated wiring, 0.5 s timeout; all three opened.
Lesson: a default that waits for ever turns one fault into a system hang; the cause was inferred, not seen, so say so.
Evidence: Report 3.12.6.

F7. Pi 4 under-voltage and reboots
Symptom: under-voltage and 600 MHz throttling through much of the bench work; 6.1 fps on 4 October; on 6 October no boot until everything was unplugged.
Candidates: the Pi's own supply under detector load; the ToF board; the telemetry unit on its USB; heat.
Deciding test: a 2 s logger of power and temperature flags, I2C addresses and USB devices: clear with nothing attached (supply cleared); ToF board disconnected throughout; soft temperature limit from 17:45 with no under-voltage (heat separate); unit plugged in at 17:58:05 and 14 s later, when its modem came up, under-voltage started and recurred, detector 14.3 to 12 fps. On 10 October: three restarts in 20 minutes with the unit on the Pi, none in 4 hours after moving it.
Cause and fix: the modem's transmit current through the Pi's USB port; the unit needs its own supply (powered hub), the Pi a 5.1 V 3 A supply and a fan.
Lesson: the fault was in how parts were powered together, not in any part; only integration showed it. The 6 October boot failure was probably the same fault but not reproduced; the modem current was not measured.
Evidence: Report 3.12.7; BenchTest/logs/2026-10-06_pi4_power_watch.log.

F8. Which investigation are you proudest of, and why?
Answer: Pick the flash stall or the Pi power one. The flash stall: three candidates (modem, MQTT, flash), a runtime command to switch logging off while publishing continued, and the gaps vanished (worst 5.9 ms), which isolated flash; then a fix chosen on cost and risk and retested. Or the power fault: a logger designed so each change in the flags could be matched to one device.
Evidence: Report 3.10 and 3.12.7.

### G. Weak points and hostile questions

G1. Your requirements do not measure your research questions. RQ1 asks about accuracy and repeatability; R1 to R4 test sampling and calibration.
Answer: That is fair. R1 to R4 establish that the instrument is sound; they do not measure repeatability of the vehicle characterisation. The measure that answers RQ1 is a repeatability criterion such as the coefficient of variation of sigma and R over repeated traversals of the same section at a set speed and payload, which the ground-phase test is designed to collect. I would add that row to the requirements.
Follow-up: "And R2 is circular." Yes, resting at 9.80 to 9.82 right after a gravity calibration only checks the arithmetic; the meaningful test is drift after recalibration in the mounted position, and the later session fails it.
Evidence: critical review item 1.

G2. RQ2 asks "which" layout. You built one. How can you answer "which"?
Answer: I cannot compare alternatives with the evidence I have. What I can answer is how: the design follows five issues from the literature (layout and clutter, legibility, interaction, alert priority, data validity), and I measured the update path and the no-data behaviour. RQ2 is better phrased as "how should", and glance time remains unmeasured.
Evidence: critical review item 1; Report Discussion "Driver display".

G3. RQ4 asks for time- and frequency-domain features. You have none in the frequency domain.
Answer: Correct. Only time-domain features are implemented, and the firmware stores per-window features, not raw 200 Hz samples, so I cannot compute spectra offline from current logs. Either RQ4 narrows to the time domain, or I add a raw capture mode for a session (streaming samples over USB to the Pi) or an on-board band-energy feature. The method for separation is designed: Hall motor speed as a reference, stationary motor runs at several speeds, coast-down.
Evidence: Report Recommendation 7; main.cpp commands (no raw IMU logging command); critical review questions.

G4. You have no vehicle data. Isn't this just a bench project?
Answer: Most results are bench results and I label them so. The first road session (19 October) gave vehicle data: 108.6 minutes recorded, about 16 minutes of driving, both IMUs at 200 Hz with no drops and one 2 s stall but a third of the per-second records lost on the USB link (R1 partly met on the vehicle), and the battery link held under load up to 46.9 A (R5 partly met (no meter check)). It did not give GNSS, raw samples or run markers, so RQ1 and RQ4 are not answered on the vehicle yet; a second, shorter session is planned (see K4).
Follow-up: "Why so late?" Vehicle access depended on lab scheduling, and I chose to verify each interface before mounting. In hindsight I should have pushed for a stationary powertrain run much earlier (see G16).
Evidence: Report 3.13; PROJECT_LOG "Waiting on someone".

G5. Your headline figures are best case.
Answer: Partly true. 102 ms at 19.5 fps was with nothing else on the Pi; with the bridge, fusion and preview it is about 120 ms at 14.6 fps. "Alerts in 0.5 s" was time after opening the page with a person in view, not onset latency. 0.37 s record age was at a laptop. I should quote both conditions every time, and I will.
Evidence: critical review item 2; bench_observations.md.

G6. A public, unauthenticated broker with no TLS. Isn't that a security failure?
Answer: For real data it would be. It was used only to prove the path with bench data; anyone can read or write sw7/telemetry there, and the ingest rejects records that do not match the schema. The firmware supports credentials from a git-ignored header. The unit currently uses plain TCP: TLS needs the modem's SSL context configured (the A7670X supports it), and a broker we control with credentials, TLS and topic access rules is the next step.
Follow-up: "Could someone inject fake data into your database?" On the public broker, yes, if they matched the schema and device ID; that is why it is a test setup only. Authenticated brokers and per-device credentials stop it.
Evidence: Server/README "Known limits" and "Pointing it at Melokuhle's broker"; Report Recommendation 5. Modem TLS support: general knowledge of the A76XX command set, not tested.

G7. A screen in a moving vehicle is a distraction. Is your dashboard safe?
Answer: I do not know yet, and I say so: glance time is unmeasured. The design reduces demand: immediate hazards raise a banner over any page, lower bands appear only on the camera and Sensors pages, spoken directions mean the driver need not look, long tasks like destination entry belong to the parked state (NHTSA counts waiting at a light as driving), and live-only mode stops the display showing invented numbers. The safety alerts need no touch. The test is a controlled, low-risk glance observation on the vehicle against the 2 s and 12 s guidance.
Follow-up: "Then why allow page swipes while moving?" A fair point; whether any touch interaction is acceptable while moving is exactly the open question, and locking interaction above a speed is an option once speed is confirmed.
Evidence: Report Discussion "Driver display"; QA_Prep section 13.

G8. You put a camera on public roads. What about privacy?
Answer: Data minimisation was fixed in code before the detector first saw live frames: frames exist only in memory and are never written to disk; each alert logs five fields (class, band, confidence, timestamp, status); no face or number-plate recognition, no identification of anyone, no tracking; inference is local; the live view is for bench checks and not stored; the fusion log is off by default and holds numbers only. In South Africa this would be framed under POPIA; the report does not yet discuss it.
Follow-up: "Who approved this?" See G9.
Evidence: Report 3.7.2 and 3.8.3; report-review.md GA10 suggestion (POPIA).

G9. Was there ethics approval, and why is it not in the report?
Answer: Answer truthfully if asked. The first application said no ML in version one; a revised application covering the camera detector was approved with conditions on 23 September (only the approved object categories, no frames stored, the five logged fields), before the detector processed live frames on 28 September. The report currently does not include the letter; the course asks for it as an appendix, and whether to include it is an open item with my supervisor.
Follow-up: "The ride tests on the vehicle?" Test safety is in the plan: a second person when the 72 V system is energised, rated stands and chocks, removable mounting only.
Evidence: PROJECT_LOG D16, D20, F22; Planning/REMAINING_WORK 2.5; Lecture 2 slide 7 (ethics letter appendix); Report 3.13. Note: D20 is the student's own rule about the report; deciding what to say orally is the student's call.

G10. How did you use AI, and is this your work?
Answer: Be truthful and specific. I used Claude (an AI assistant, through Claude Code) extensively: for drafting and reviewing firmware and scripts, running and analysing tests with me, the literature search pipeline, and report wording and LaTeX. The project log credits decisions as "student" or "student with Claude". I made the design decisions, ran every hardware test, wired and built the hardware, designed and printed the casing, chose the components, and I can explain and defend every line in this report. The AI declaration in Appendix A currently covers only organisation, wording and LaTeX, which is narrower than the real use; it should be broadened with example prompts, as the course requires.
Follow-up: "Give an example where you overruled or corrected it." Prepare one from your own memory (do not invent one in the room). Candidates from the record: the casing (the assistant's OpenSCAD bracket was not used; you designed and printed your own, D8 and D19), the HUD decision (yours, D26), the ToF stand-in choice (yours, 30 Sept).
Evidence: PROJECT_LOG decisions register (who column), D8, D19, D26; Report Appendix A.3; Lecture 2 slides on AI use (example prompts required); report-review.md section 3 and critical review item 6.

G11. What does it cost? You call it low-cost.
Answer: I have not totalled a bill of materials, so I should not claim a number. The parts are commodity: an ESP32-S3 LTE board, two MPU6050 modules, a Raspberry Pi 4 with a camera module, three ToF sensors. Without a costed BOM, "low-cost" is unquantified, which the critical review points out.
Follow-up: "Then drop the word?" Either drop it or add the BOM before submission. (Action for the student: total the BOM before 16 November.)
Evidence: QA_Prep section 12; critical review item 8.

G12. What is the power budget against the 72 V battery?
Answer: About 20 W typical (0.27 A from the 72 V pack), 35 W peak, under 1 percent of the motor's rated input; only the Pi 5 is measured, the rest are datasheet and published estimates. Details and the converter requirements are in K6. The main power finding stands: the modem must not be powered from a Pi's USB port.
Evidence: Report Results power-budget table; Recommendation 3.

G13. What about the hardware debuggers the brief mentions?
Answer: I did not use a JTAG debugger. I chose serial instrumentation (rate, min, mean and max interval and drop counters every 2 s; per-stage camera timing) because the property under test is timing, and halting the cores with a debugger changes timing. The ESP32-S3 has a built-in USB JTAG that could be used for crash analysis. Admit the gap against the brief.
Evidence: brief-compliance G5; ESP32-S3 USB JTAG is general knowledge, not tested.

G14. Your speed-index bug was found by review, not by testing. What does that say about your verification?
Answer: That the self-test checked the formula as implemented, not whether the formula was the right one. The sine self-test has no constant offset, so gravity in the mean square could not show up there. A test with a known offset plus vibration would have caught it. Lesson: test with signals that look like the real input, including DC.
Evidence: Report 3.4.2; Appendix E fault table. The "no offset in the sine" point is my reasoning.

G15. How many times did you repeat each test? Where are your statistics?
Answer: Most tests are one or two runs; the numbers are bench measurements, reported as medians, percentiles and ranges where many samples exist within a run (latency per frame, 104 GNSS fixes, 121 sync edges), not statistics over repeated trials. Repetition and distributions across traversals are the next step on the vehicle.
Evidence: QA_Prep section 11.

G16. What would you do differently?
Answer: Get on the vehicle earlier, at least a stationary powertrain run. Sample the IMUs faster and decimate, with the FIFO, from the start. Write the JSON encoder to handle missing values from day one. Define the requirements so they measure the research questions (a repeatability criterion). Power each board separately from the start. Cite the camera literature as I went.
Evidence: QA_Prep section 11; critical review.

G17. Your camera has no literature review behind it, but your gap claim depends on it.
Answer: True of the report as it stands; the sources (SSD, MobileNet, COCO, quantisation, monocular distance, an edge benchmark) are in the repository and I can discuss them (B16 to B18). A paragraph on lightweight detection and monocular ranging is on the revision list.
Evidence: critical review items 5 and 6.

G18. R6 measures pulse regularity, not frame-to-IMU alignment.
Answer: Correct: R6 shows the two clocks can be related precisely. The frame-to-exposure offset is bounded only to under 1 s by the lens-cover test; the LED method would measure it properly. R6 should be renamed "edge regularity".
Evidence: critical review item 1; Report 3.7.1.

G19. Isn't the dashboard dependent on a phone hotspot? You said it must not depend on coverage.
Answer: On the bench both Pis were on a laptop or phone hotspot. The hotspot provides the local Wi-Fi link, not mobile data, so the display works without coverage as long as the local network exists; but a phone in the loop is not acceptable on the vehicle. The resolver already supports a wired Ethernet address (10.20.0.1/2) with a setup script; its use on the vehicle is not yet recorded.
Evidence: Appendix B "Network"; Appendix E "Raspberry Pi 4 discovery"; critical review item 7.

G20. Did your 112 of 112 really prove synchronisation with a central database?
Answer: It proves no record was lost end to end in that test, with 60 replayed after a 10-minute outage and no duplicates; but 24 of the 112 came from log backfill, so on this public broker the guarantee relies on the log. The database is my own SQLite on the Pi 5, not a TUKZIE central server; pointing it at Melokuhle's broker is configuration. Latency is not yet measured.
Evidence: TEST_PROCEDURES T15; Server/README.

G21. The SEN55 and air quality were in the brief. Why drop them?
Answer: Not dropped, not delivered: the sensor arrived but needs a six-way JST GH cable; the wiring and a simple anomaly rule (PM2.5 with a VOC rise above a rolling baseline, tagged with position) are planned. I note that VOC and NOx indices take up to 1 and 6 hours to meet specification after switch-on, so short drives give indicative values only.
Evidence: Report 3.7 "Other vehicle inputs"; REMAINING_WORK 3.3; brief-compliance section 3.

G22. Is the alert hysteresis tested on live data, or only offline?
Answer: Both: offline with scripted sequences through the unchanged loop (all pass), and seen raising and clearing person alerts on live frames in the detector's log. Clearing was not seen on the dashboard page itself because the person stayed in view.
Evidence: Report 3.7.2 and 4.8; TEST_PROCEDURES C2, B2.

G23. Only the person class is confirmed. Is your detector tested at all for vehicles?
Answer: No. Only person has been confirmed on live frames (confidence 0.50 to 0.73); cars, bicycles and others have not been tested, nor outdoors, in daylight, rain or glare. Precision and recall on this camera are not measured; that needs labelled frames from a recorded drive.
Evidence: Report 4.6.

G24. The report says R13 removability is met in one place and outstanding in another.
Answer: Outstanding is right: removable mounting is planned (no drilling, return to standard in about 20 minutes in the plan) but nothing is installed yet. The Methodology wording should say "planned".
Evidence: critical review item 7.

### H. Graduate attributes

For each: one strong example to lead with, and a likely probing question.

GA1, problem solving.
Strong example: partitioning the system so that no process blocks acquisition (brief GA1 wording): IMU tasks alone at top priority on core 1 with vTaskDelayUntil, bounded drop-and-count queues, all blocking I/O on core 0, and the result measured (200 Hz, zero drops), plus the flash-stall diagnosis showing one remaining source of blocking and bounding it.
Probe: "Show from first principles why 200 Hz, and what your 260 Hz filter did to it." Answer with C1 and C2, including the 150 Hz to 50 Hz example and the v0.7.4 change.

GA4, investigations and experiments.
Strong example: the Pi 4 power fault or the flash stall: a hypothesis per candidate cause and a test that separates them (logging on and off with publishing continuing; a 2 s flag log matched to each device plugged in). Also T15: written pass criteria before the test (zero missing, replays stored once, drain within 2 minutes).
Probe: "What was the control, and what result would have falsified your hypothesis?" For the flash stall: control was the same run with publishing on and logging off; if the gaps had remained, flash was falsified.

GA5, engineering tools.
Strong example: per-frame latency measured from the camera's own SensorTimestamp with per-stage medians and 95th percentiles; the pre-test check sw7_check.py; offline test suites with stand-ins (29 fusion tests, 22 pothole tests, 40 firmware ledger checks with 900 randomised outage simulations, 11 server tests); NCNN with hand-written decode and NMS when PyTorch could not be installed; Colab training.
Probe: "What are the limitations of your tools?" Serial instrumentation instead of a debugger (and why); laptop offscreen tests do not prove behaviour on the Pi 5; the phone reference for GNSS has its own error; validation scores are optimistic.

GA6, professional communication.
Strong example: the report cut from about 31,000 words to a 13,476-word body inside 50 pages, organised by requirement with an evidence index (Appendix C) tying every number to a log; the deck, poster and talking points.
Probe: "Your abstract claims an 8 percent disagreement reduced to noise. Is that accurate?" Answer with C13 and correct it yourself.

GA8, individual work.
Strong example: own decisions with evidence: the HUD replacement case made to the supervisor (D26), the Pi 4 rather than Pi 5 (D6), the ToF stand-in, the VL53L5CX choice (D17), the camera casing designed and printed (D19), and every hardware test run on the bench.
Probe: "Which parts did you write yourself, and how did you use AI?" Answer with G10 and I1. Be exact about inherited work.

GA9, independent learning.
Strong example: learning FreeRTOS timing, BLE GATT, the A76XX AT command set, on-device inference and model training from primary sources, and correcting assumptions against them: the GNSS layout from raw replies, the JBD checksum from the protocol's own frame, MQTT result codes from the manual.
Probe: "What did you get wrong, and how did you find out?" The speed index (gravity in the mean square), the 260 Hz filter, the nan records; each found, owned and fixed.

GA10 (professionalism and ethics) is not one of the six assessed in Appendix A but Lecture 2 calls ethics "most commonly failed": have G8, G9 and D9 ready.

Evidence: Report Appendix A; Planning/report-review.md section 2; GA Tracking Form (signed 24 Sept, "DP satisfied").

### I. Teamwork and inherited work

I1. What did you inherit and what is yours?
Answer: Inherited: the vehicle; the PySide6 dashboard v1.1 on the Pi 5 written by vacation-work teams (pages, simulator, voice system, team visual style); the drivetrain characterisation report (Adams and Rasara); an earlier BMS implementation that leaked a client on each reconnection, which I rewrote; a teammate's BMS parser used only as an independent cross-check; the vac-work broker, which I did not use. Mine: the telemetry unit firmware (acquisition, calibration, features, fusion, BMS rewrite, GNSS parser, MQTT, logging, store-and-forward), the Pi 4 detector, bridge, ToF reader and fusion, the dashboard add-ons and live-only mode, the central database, the bench tools and tests, the pothole training, and the camera casing.
Follow-up: "Is the dashboard look yours?" No: the visual language is the team's and I kept it deliberately.
Evidence: Report 3.5, 3.8.4 and Acknowledgments; DashboardIntegration/README.md.

I2. Who are Melokuhle and Sharaav, and how do you work with them?
Answer: Two other students building onto the same trike. Melokuhle Bango (JBM11) builds a gateway that sends telemetry over MQTT to a remote server; my firmware and database take any broker from configuration, so pointing at that broker is a settings change once its details (host, port, user, TLS, topic) are known; we are also coordinating the road test. Sharaav (SW-6) and I agreed a preliminary UART link (115200 8N1, CSV speed and battery percent from SW-6 to SW-7); it became optional when the dashboard took battery from my BMS link, and it was not implemented.
Follow-up: "Did you share mounting?" Positions are to be confirmed on the trike with both of them and the lab (Yusuf Vawda for access).
Evidence: Server/README; Planning/central-database-sync-prompt.md; Planning/sharaav-interface-definition.md; mounting-and-enclosures.md.

I3. Did you change another team's code?
Answer: No. The patch set applies to a separate copy, refuses to touch the team's folder, and their service is disabled, not removed. The edits are listed for the team to review.
Evidence: Report 3.8.4.

I4. How did you work with your supervisors?
Answer: Regular meetings, a draft Introduction and Methodology early, the GA tracking form signed on 24 September ("DP satisfied"), the HUD decision by email with reasons (agreed 1 October), the camera added on the supervisor's direction, and the ToF and fusion side at his suggestion. The co-supervisor provided the dashboard Pi 5 and hardware on 2 October.
Evidence: PROJECT_LOG D26; signed GA form.

### J. Open Day visitors (one-sentence answers)

J1. What is this? A small computer that measures how an electric delivery trike rides and warns the driver about people and cars nearby, on the screen the trike already has.
J2. Why a trike? Electric cargo trikes are a cheap, clean way to deliver goods in African cities; one study in Dar es Salaam found running costs per kilometre less than half those of a motorcycle.
J3. What do the little boards do? This one measures shaking 200 times a second with two motion sensors, reads the battery and GPS, and sends data over the mobile network; that one runs the camera.
J4. Can it see potholes? Not yet on the trike: the camera recognises people and vehicles, and I trained a separate pothole model that is still too slow for this small computer.
J5. Does it record people? No, pictures are never saved; it only notes things like "person, close, at this time".
J6. Does it drive the trike? No, it only warns the driver; it never touches the brakes or steering.
J7. What happens with no signal? It keeps everything on board and sends the backlog when the signal returns; in a test it lost nothing over a 10-minute outage.
J8. How fast does it spot someone? About a twentieth of a second at the front, where the detector runs beside the screen, and about a tenth at the rear; raising an alert needs three frames in a row.
J9. Is that a real drive on the screen? When the yellow "SIMULATED" strip is showing it is a demonstration, not live data; the badge always says LIVE, REPLAY, NO DATA or SIMULATED.
J10. How far can the distance sensors see? About a metre in this version, for close manoeuvring; the camera covers further away.
J11. How much does it cost? I have not added it up yet; the parts are all off-the-shelf hobby-grade boards. (Better: total the BOM before Open Day.)
J12. What did you learn? That testing each piece against a clear pass mark finds problems you would never guess, like the mobile modem browning out the camera computer through a USB cable.
J13. What next? A second drive with the raw motion data and working GPS, then using it to tell road bumps apart from the motor's own vibration.
J14. Is this a head-up display? It was going to be, but the trike already has a dashboard, so the warnings go there instead of adding a second screen.
J15. Who made it? I did, as my final-year project, building on the dashboard and vehicle work of earlier student teams.
J16. Why two cameras? There is a camera at the front and one at the back; the driver flips between them on one page, and the rear view is mirrored like a car's reversing camera.
J17. Can it tell if something is coming at you? It watches how fast an object's outline grows in the picture; growing fast means it will reach you soon, and it warns under 4 seconds. That part is tested on simulated data so far, not on a real approaching car.
J18. Has it been on the road? Yes, once, on 19 October, for about 20 minutes of driving; the motion sensors and the battery reading worked, the GPS did not get a fix, so a second drive is planned.

### K. New since 11 October: two sides, approaching objects, power, the first road session

These are the questions an examiner will ask about the work added between 12 and 20 October. Numbers are from the report (Methodology 3.8.6 and 3.8.7, the Pi 4 under-voltage investigation, vehicle tests; Results R1, R4, R5, hazard sensing and the power budget; Discussion; Appendix F and G) and Planning/lab-notebook.md (19 and 20 October).

K1. Why did you move detection to the Raspberry Pi 5?
Answer: Two findings on the bench, and one design reason. The same 8-bit SSD-MobileNet with the dashboard running on the Pi 5 ran at 19.2 frames/s with a median of 51 to 54 ms from sensor readout to result (95th percentile 61 to 63 ms, inference 28 ms), against 118 to 122 ms at 14.6 frames/s on the Pi 4 with the whole system. At 30 km/h that is about 0.6 m less travel before an alert, the same order as the stand-in time-of-flight sensors' whole 1.2 m range. Second, the battery's Bluetooth link did not reach the telemetry unit at the front, so the unit had to move to the rear, near the pack, where the link held for the first time. Third, with detection beside the display a front alert no longer crosses the network to reach the screen.
Follow-up: "What did it cost?" CPU load on the Pi 5: 64 to 73 percent in total with the dashboard, at 53 to 54 C, no throttling, in a 60 s run on 15 October. The rear still uses the Pi 4's slower detector (126 to 151 ms on the vehicle on 19 October while throttled). The AI HAT+ is in the front pod design but the detector does not use it yet.
Follow-up: "Why not a Wi-Fi link?" A dedicated Ethernet cable with fixed addresses (1000 Mb/s, 0.22 to 0.25 ms round trip) keeps the driver's display independent of a phone hotspot or coverage; Wi-Fi stays free for internet. On 19 October the cable came loose twice during mounting, so it must be tied down.
Evidence: Report Results Table (hazard sensing, Pi 5 row), Methodology "Two-sided layout", Discussion "Hazard sensing"; lab notebook 19 Oct 16:01 and 17:20.

K2. How does your time to contact work without calibrating the camera, and what are its limits?
Answer: For an object closing at constant speed, its image width w is proportional to 1/distance, so 1/w falls in a straight line in time and reaches zero at contact. Time to contact is tau = w / (dw/dt), the expansion measure of Lee (1976) used in production forward-collision warning (Dagan et al. 2004). Focal length and real object size cancel out, so it needs no calibration. A small tracker keeps each object's identity by box overlap; a Theil-Sen line (robust to outlier boxes) is fitted to 1/w against the frames' sensor timestamps over the last 0.6 s. It is used only with at least 5 frames over 0.25 s, 75 percent of pairwise slopes agreeing, at least 5 percent growth, no box touching the image's side edges, and the height giving a time within a factor of 2. Warning under 4 s, immediate under 2 s, after the usual three-frame onset; released above 5 s (2.5 s for immediate).
Limits, in order: (1) accuracy on a real approach is untested (test C11); only 40 synthetic tests pass, within 2 percent at constant speed, with no alerts in 5,000 frames of receding, still or jittering boxes, 0.27 ms per frame on a laptop. (2) It assumes constant closing speed; braking or accelerating objects bias it. (3) It is noisy for small, distant boxes, because a pixel of box jitter is a large fraction of w; the agreement and growth gates suppress that at the cost of later warnings. (4) Box width changes with pose (a person turning, a car turning) as well as distance. (5) While the trike moves, a stationary object ahead "approaches"; that is intended (a forward-collision warning), but it means it is not a moving-object detector. (6) Partly occluded or edge-cut boxes are rejected.
Follow-up: "Then what is the focal length for?" Only the distance bands and the closing speed in m/s. Focal calibration was attempted on 19 October: a person's box gave about 605 px against about 635 px expected from the lens, but a person is a poor target (pose, arms, objects behind); three objects at 1, 2 and 3 m were photographed, and their real widths still have to be measured. So the bands remain indicative.
Follow-up: "Did it work on the road?" The front detector marked 261 car alerts as approaching (and the rear 36), but none has been checked against video, so I make no accuracy claim.
Evidence: Report Methodology "Approaching objects: time to contact", Results (approaching-object row; road alerts), Discussion "Hazard sensing"; lab notebook 19 Oct "Camera focal-length calibration".

K3. Why was there no GNSS fix on the road?
Answer: No GNSS antenna had been connected to the board, so the receiver could not see any satellites. That was an installation omission, not a receiver fault: on the bench the same receiver gave a fix 105 s after a cold start and a 2.7 m median against a phone. There is no position or speed for that drive, so R4 is untested on the vehicle rather than failed. The antenna is now fitted for the second session.
Follow-up: "What will you do?" Check the antenna connector and give the patch a clear view of the sky with no metal above it, confirm a fix outdoors before driving (it is on the checklist), and log the raw GNSS replies so a missing fix can be diagnosed.
Follow-up: "What did losing it cost?" Speed (needed for the speed-normalised index and the speed dependence in RQ4), GNSS time for aligning the logs and video, and the latency measurement. Driving was identified instead from battery current and vibration.
Evidence: Report Results "Position (R4)"; lab notebook 20 Oct "Not captured".

K4. Why is RQ4 not answered yet, when you drove for about 16 minutes?
Answer: Separating powertrain from road vibration needs three things the first session did not have: the raw 200 Hz samples for spectra (firmware v0.7.4 stores one-second features, and the live record carries only one vibration number a second), a speed reference (no GNSS fix, and the Hall tap is not fitted), and marked runs, including the stationary powertrain baseline on stands (only the "drive session starting" marker was written). What the session does show is that parked and driving separate clearly: one-second vibration median 0.031 parked against a 95th percentile of 2.0 and a maximum of 5.09 while driving, together with battery current up to 46.9 A. The same gaps stop RQ1's repeatability over repeated traversals.
Follow-up: "So what next?" A second, shorter session with the raw stream (firmware v0.7.5, being bench-tested so that the IMU timing is unchanged), a working GNSS antenna, timed runs written as markers, and the stationary baseline at each motor setting.
Evidence: Report Results R3 and Discussion "Ride characterisation"; lab notebook 19 Oct 17:55 and 20 Oct.

K5. Is R1 really met on the vehicle?
Answer: Partly. No samples were dropped, and the rate held in all but six of 3,437 readable records; one, while driving, shows IMU1 stalled for about 2 s. But the recorder received only 3,464 distinct one-second records over a 5,557 s span: a third of the seconds were lost on the USB link, which is why the unit now uses a wired serial link. The gap distribution on the moving vehicle is not shown, because that needs the raw sample stream (v0.7.5).
Evidence: Report Results R1 and the summary table.

K6. Power: what is the budget, and what caused the brown-outs?
Answer: The added electronics draw about 20 W typical, 0.27 A from the 72 V pack through an 88 percent converter, 35 W in short peaks; that is about 0.8 percent of the motor's 2.5 kW rated input. Only the Pi 5 is measured (2.2 to 3.0 W on its internal rails); the display, the Pi 4 and the telemetry unit are estimates until inline meters are used. The pack is 24 cells with a 150 A BMS (from its Bluetooth name), about 60 to 88 V, so the converter must take the full range, be rated to 100 V, deliver at least 40 W at 5 V and be fused at about 2 A. Parked, the full system would empty a 7.2 kWh pack (the dashboard's figure, not confirmed) in about 15 days, so it must switch off with the vehicle.
The brown-outs: the telemetry unit's LTE modem draws transmit bursts of up to about 2 A through the Pi 4's USB port and pulls its supply into under-voltage (14 s after the modem came up; 3 restarts in 20 minutes, none in 4 hours once moved). It recurred on 16 October in the closed box: 68.6 to 76.9 C over about 70 minutes, a restart with under-voltage present at that moment (0x50005), and the share of unreadable dashboard lines rising from about 2 to 10 percent. On 19 October the Pi 4 logged 11 to 16 under-voltage warnings per boot because the unit was still on its USB port. The fix is a separate supply for the telemetry unit (still to be fitted), plus vented lids.
Follow-up: "And the Pi 5 restarts?" Four restarts during the mounting work on 19 October. A logger recorded its supply, flags and temperature every 5 s; the last reading before each restart was normal (4.95 to 5.08 V, flags clean, 57 to 59 C), lowest 4.89 to 4.97 V in the two minutes before. So they were abrupt losses of power, from a loose connector, the source or the supply's overload protection, not a brown-out or overheating. It did not restart during the drive.
Evidence: Report Results "Integration and power" and the power-budget table; Methodology Pi 4 under-voltage investigation and its recurrence paragraph; Discussion "Integration and power".

K7. What were the ethics conditions for the road session, and were they met?
Answer: Ethics approval EBE/03305/2026 was granted with conditions. For the vehicle work the road-test checklist lists them: a physical risk assessment signed by the lab owner before any driving; a closed area such as a parking area or field, not a public road; two people present whenever the 72 V system is on; only I run the study (the approval names no other investigators), and a team member may drive; no recording of faces; glance observation of another driver only if the supervisor confirms it is covered (otherwise skipped); the vehicle returned to standard afterwards. The camera conditions from September still hold: only the approved object categories, frames never stored, five fields per alert, inference on board, advisory only.
Honest status: the report says the session followed the checklist, but it does not yet record the venue, the people present or the signed risk assessment; those are listed as outstanding. [Student: before the talk, confirm from your own run sheet that the risk assessment was signed, where the session took place and who was present, and say only what you can show. Glance time was not measured, so the human-participant question did not arise.]
Follow-up: "Your camera recorded people on the road." It recorded no images. The detector raised 815 person alerts on the front side, each kept as five fields (class, band, confidence, time, status) with no image and no identity; the tracker's identifiers restart at 1 at each start-up. Saved calibration frames that showed a colleague were blurred, and frames with other people are not kept.
Evidence: Planning/road-test-2026-10-16-checklist.md section 0; Report Methodology "Detection" (data handling) and "Vehicle tests"; lab notebook 19 Oct (privacy note).

K8. Why is the rear view mirrored, and how does the driver know which side a warning is from?
Answer: Like a car's reversing camera, so the driver's left is on the left of the screen; the rear distance sensors' left and right are swapped to match. The banner shows warnings from both sides labelled "Front" or "Rear", with approaching objects first and their time to contact, and tapping it opens that side. A side that drops out shows its own offline state, never zeros or the other side's values. Tested offscreen with four fake servers and live on the Pi 5; glance time is still unmeasured.
Follow-up: "Does reverse gear switch to the rear?" Only the dashboard's own gear state does; there is no gear signal from the vehicle. A direct signal would need the reverse switch tapped through an optocoupler, which touches the 72 V wiring and needs the supervisor's approval.
Evidence: Methodology "Two-sided layout" and "Vehicle tests"; DashboardIntegration/README "Front and rear cameras".

K9. Are the enclosures on the vehicle?
Answer: The designs are a display mount (bar clamp with a dovetail rail), sensor pods for the rear (Pi 4 and telemetry unit) and the front (Pi 5 with the AI HAT+), IMU pods (revision 3, push-fit, no screws) and vented lids. They were modelled from scripts in SOLIDWORKS and audited for interference, fastener alignment and thin walls. Printed so far: the rear box (in which the Pi 4 reached 76.9 C) and a first IMU pod for a fit test, which led to revision 3. The rest are checked in CAD only; the dovetail coupon, clamp slip test and insert pull-out tests have not been run, and the temperature in the vented boxes has not been measured.
Evidence: Report Appendix F; Discussion "Integration and power".

K10. What did the recorder on the vehicle capture, and how do you know when the trike was moving?
Answer: A service on the Pi 5 saves every reply of four sources twice a second: front time-of-flight, fusion and alerts locally, and the rear unit's record and alerts over the cable. On 19 October it ran from 17:15 to 19:04, 108.6 minutes and 51,489 records, with no laptop on board; the only rear gap, 409 s, was before the drive. With no gear or speed signal, each second is labelled afterwards from battery current (motor working) and vibration (running or moving); GNSS speed would separate driving from running on stands once it works.
Evidence: Report Methodology "Vehicle tests"; Results "Integration and power"; lab notebook 20 Oct.

---

## 3. Numbers cheat sheet

| What | Number | Source |
|---|---|---|
| IMU rate | 200.0 to 200.5 Hz, 0 dropped, every session | T1, T2, T9; Report Table 4.1 |
| Samples per 2 s window | 400 to 401 | Report Table 4.1 |
| Gaps, 25 Sep log | max 25 to 30 ms (29.9), min 0.785 ms catch-up, about 1 window in 6, every 12 s | 2026-09-25 log; PROJECT_LOG F6 |
| Gaps, v0.5.0 log on / off | 33 to 40 ms every 10 s / worst 5.9 ms | T2 |
| Gaps, v0.6.0 buffered | 37 to 40 ms about once a minute, within 3.5 s of a flush; flush 71 to 202 ms | T9 |
| Gaps, v0.7.4 during T15 | 10 of 368 windows over 10 ms, worst 44.1 ms, 0 drops (my count) | 2026-10-11_sync_outage_test.log |
| Queues | 100 samples (500 ms) stats, 400 ride, per IMU | Appendix E Table E.1 |
| IMU settings | plus or minus 8 g, 500 deg/s, filter 260 Hz (94 Hz since v0.7.4), I2C 400 kHz, 0x68 on two buses | Table E.1; main.cpp |
| Nyquist | 100 Hz at 200 Hz; ISO band to 80 Hz needs over 160 Hz | Report 3.3 |
| Uncalibrated disagreement | 10.35 to 10.39 vs 9.55 to 9.56 m/s2, +5.7 / -2.6 percent, about 8 percent | Report 3.4.1 |
| Calibration factors | dev board 0.9773, 0.9901 (then 9.80 to 9.81); target board 1.0390, 1.0245 (from 9.4387, 9.5725) | Report 4.2; T4 |
| Drift | later 9.93 and 10.10 m/s2; on 11 Oct about 10.87 and 10.12 (my reading) | Report 4.2; T15 log |
| g0 | 9.80665 m/s2; factor accepted 0.5 to 2.0; 200 samples | Report eq. 3.4 |
| Still vibration sigma | median 0.041, max 0.067 m/s2 | Report 4.3 |
| Hand disturbance | sigma 9.35; largest p2p 77.6 m/s2 (8 g = 78.5) | Report 4.3 |
| Disagreement D | 0.00 to 1.68; 1.68 at 72 s (sigma 3.009 vs 0.266); floor 0.05 m/s2 | Report 4.3; 25 Sep log |
| Fusion | 149 of 149 windows, skew under 1 ms, 5 of 5 self-tests, pair within 0.5 s, fallback 3 s | T1 |
| Sine self-test | 5 Hz, 200 samples, RMS A/root2, p2p 2A, CF root2, within 5 percent | Report 3.4 |
| GNSS fix | 105 s cold (51 s earlier), 23 to 25 sats, HDOP 0.9 to 1.5 | T3 |
| GNSS vs phone | 104 fixes, median 2.7 m, p95 11.0 m, max 12.3 m | T3 |
| GNSS warm-up | 60 to 90 s; start-up sequence about 27 s | Report 3.12.2; Appendix E |
| Network position | about 0.7 s, 550 m stated, about 30 m off (one reading) | Report 3.6 |
| GNSS speed | 0 to 5.8 while stationary; manual says knots | Report 4.4; SIMCom manual |
| BMS | 14 records, about 140 s, 74.78 V, 0.00 A, 60 percent, 3.12 V/cell, -88 to -93 dBm | T7, T10 |
| BMS query | DD A5 03 00 FF FD 77 every 3 s; checksum 0x10000 minus sum | main.cpp |
| MQTT | 47 of 47; reconnect 0.4 s; QoS 1; keep-alive 60 s; every 10 s; retry 30 s doubling to 300 s | T2; Table E.1 |
| Signal loss | detected 0.8 s / 20.7 s; reconnect 36 s (v0.5.0) vs about 5 s (v0.5.3); data back in 2.4 s | T6 |
| CSQ | 22 to 31 (24 to 26 about -65 dBm) | T9, T11, Report Table 3.2 |
| T15 outage | 600 s, 60 records backlog, lost 0, reconnect 5.2 s, unit backlog 0 after 48.0 s | T15 |
| T15 database | 112 of 112, 0 missing, 0 duplicates, 60 replays in 37.3 s (1.58/s), 111 of 111 vs log, 24 backfilled from log, latency not measured | T15; t15_summary.csv |
| Laptop and server tests | firmware ledger 40 checks incl. 900 randomised simulations; server 11 tests; 20 of 20 synthetic records | T15 |
| Log read-back | 6,020 records, 2.2 MB, 16.7 h, four passes; 5,545 (92 percent) had nan | T10 |
| Log | 3 MB cap, 3.375 MiB partition, about 160 KB/h, 8 KB buffer, flush 60 s | Report 3.10; Table E.1 |
| Record size | about 0.7 to 1.1 KB; about 2 to 3 MB per 8-hour day (estimate) | Server/README |
| DASH line | 40 of 40 in 40 s, at most 272 bytes (298 in v0.7.1); 0.37 s old at laptop; pre-test 0.5 s, 18 ms | T11, T12, T13 |
| Sync pulse | 121 edges, median 500.06 ms, range 499.72 to 500.41; ESP32 side 500,000 to 500,001 us | C6; Report 3.7.1 |
| Lens-cover offset | under about 1 s | Report 3.7.1 |
| Detector bench | 19.5 fps, 102 / 120 / 136 ms; queue 52, pre 12, inference 36, alert 0.1; 65.7 C | C4 |
| Detector variants | live view 17.3 fps 105/127; 1 thread 7.0 fps 186/207 (inference 126) | C4 |
| Detector integrated | 14.6 to 14.7 fps, 118 to 122 ms median, p95 146 to 148, inference 51 to 52 | bench_observations.md |
| Under-voltage detector | 6.1 fps (4 Oct); 14.3 to 12 fps at brown-out | Report 3.12.7 |
| Alert onset | about 0.2 s, about 1.7 m at 30 km/h; 102 ms = 0.85 m at 30 km/h | Report 4.6 |
| Hysteresis | 3 frames on, 5 off; was 16 alerts in 47 s | Report 3.7.2 |
| Detector settings | confidence 0.5; bands under 3 / 8 / 15 m; car 1.8 m, person 0.5 m; focal placeholder 600 px (about 635 expected from 53.5 deg) | hazard_detector.py |
| Person confidence | 0.50 to 0.73 | C1 |
| YOLO11n NCNN 320 | 7.9 fps, 175 ms median, 258 p95, inference 111 ms (15 s trial) | C8a |
| Pothole run 1 | 608 images, 59.7 percent mAP@50 (P 66, R 50) on own test; 0.000 on 605 SA images (1,238 potholes) | Appendix E |
| SA dataset | 4,337 images 3680x2760; 1,987 with 5,029 potholes; median 100x26 px (17x4.5 at 640); centres 48 to 62 percent | Appendix E |
| Pothole run 2 | band 42 to 68 percent, 3 tiles 1280 px; mAP@50 0.714 (P 0.811, R 0.623), mAP@50-95 0.349 at 640; 0.566 / 0.246 at 320; best epoch 54 of 60; validation tiles | run2 README |
| Pothole on Pi | 3 tiles 0.55 to 0.75 s; only 0.25 Hz within 10 percent (13.9 fps, 125 ms); test picture conf 0.63 | C10 |
| ToF | 3 x VL53L0X, about 31 readings/s each, 0x29 to 0x30/31/32, XSHUT GPIO22/23/24, about 2 m (1.2 m used), timeout 0.5 s, re-probe 60 s | C7; Report 3.8.3 |
| ToF hand test | ahead 80 to 264 mm, right 157 to 199 mm | 2026-10-10_tof_hand_test.txt |
| Fusion geometry | sensors -35/0/+35 deg, half-angle 12.5, gate 5, 200 ms, camera stale 1 s, debounce 3, poll 5 Hz; camera plus or minus 26.75 deg | fusion_config.json |
| First fused hazard | camera 0.874 m, ToF 0.096 m, reported 0.096 m, 6.2 fps, conf 0.60 | C9 |
| Pi 4 temperature | 81 C no fan; 48 C after boot, 57 C, 66 C after 5 h with fan | bench_observations.md |
| Pi 4 power | under-voltage 14 s after modem up; 600 MHz; 3 restarts in 20 min vs 0 in 4 h; flags 0x50005, 0xd0000 | Report 3.12.7 |
| Pi 5 USB | 600 mA total on a 3 A supply | Report 3.12.7 |
| Dashboard | poll 0.5 s; age limit 3 s; watchdog 2.5 s; beacon 2 s, UDP 50808; probe 3 s; back-off 2 to 30 s; 63 edits | Report 3.8.4; Appendix E |
| Camera page | video 0.6 s; 14.2 fps decoded vs 14.8; gap 0.22 s; alert row 0.5 s after opening | B2 |
| Touch | 25 taps, 200 to 640 ms, no panel delay, load 0.04 | Report 4.8 |
| Map | 656 tiles, 11.9 MB, zoom 11 to 16; cache 30 days; replay track 2,993 m, 650 points, 18 km/h | Appendix E |
| Hall counter | 666 edges in 333.3 s = 2.00/s; filter 12.5 us; rpm = edge rate x 60 / (2 x pole pairs) | T9; Report 3.7 |
| Vehicle | 72 V; motor 72 V 35 A, controller 90 A, about 2.5 kW; plate L2e-U, 3.9 kW, 42 km/h | Report 1.1 |
| Literature | 733 records, 3 runs from 19 Sep; 47 cited references | research.db; References.tex |
| Report | 13,476 body words (declaration, 11 Oct); 50-page limit | Report front matter |
| Display guidance | 2 s glance, 12 s task (NHTSA); 20 arcmin, about 24 px at 70 cm (ISO 15008); 10x10 mm touch, 4 mm gap (Euro NCAP); 40 s destination entry (Strayer); 10.6 percent (Reimer); fewer than 6 symbols (Park) | Report 2.6; papers |
| Economics | 45.5 percent vs motorcycle, 62.5 vs tuk-tuk, 86 vs light car (Sebwa); 51 to 72 percent GHG (Saenz) | Sebwa PDF; Report 2.2 |
| Course | talk 10 min, Q&A 5 min; deck now 14 slides, 1,275 words (about 9:08 spoken); report 90 percent, oral 10 percent | Lecture 2; brief-compliance.md; SW7_Speaker_Script.md |
| Detector, Pi 5 front (15 Oct, 60 s) | 19.2 fps; 51 to 54 ms median readout to result, 61 to 63 ms p95, inference 28 ms; CPU 64 to 73 percent, 53 to 54 C | Report hazard-sensing table |
| Detector, Pi 4 whole system (11 Oct) | 14.6 to 14.7 fps; 118 to 122 ms median, 146 to 148 ms p95 | Report hazard-sensing table |
| On the vehicle (19 Oct, lab check) | front 17.5 to 22.0 fps, 53 to 102 ms; rear 14.4 to 14.5 fps, 126 to 151 ms (Pi 4 throttled) | Report Results "Integration and power" |
| Ethernet link | 1000 Mb/s; 0.22 ms (15 Oct), 0.25 ms (19 Oct) round trip; 10.20.0.1 and 10.20.0.2 | Methodology "Two-sided layout"; Results |
| Time to contact | tau = w / (dw/dt); Theil-Sen over 0.6 s; at least 5 frames over 0.25 s, 75 percent agreement, 5 percent growth; warning under 4 s, immediate under 2 s; 40 synthetic tests within 2 percent; 0.27 ms per frame | Methodology; Results |
| Road session (19 Oct) | 17:15:34 to 19:04:10, 108.6 min, 51,489 records; about 16 min driving (18:15 to 18:49); 3,464 distinct ESP32 records, 38 % of seconds missing | Results; lab notebook 20 Oct |
| Road: IMUs | 0 dropped; 200 Hz in 3,431 of 3,437 readable records, one 2 s IMU1 stall | Results R1 |
| Road: battery | up to 46.9 A; 74.6 to 72.8 V under load; 60 to 58 percent | Results R5 |
| Road: vibration | median 0.03 parked; driving median 1.39, p95 3.1, max 5.09 (each record counted once) | Results R3 |
| Road: alerts | front 1,342 (person 815, car 513, 261 car approaching); rear 741 (car 201, 36 approaching); not checked against video | Results hazard sensing |
| Road: GNSS | no fix in any of 3,464 records (no antenna fitted) | Results R4 |
| Power budget | 17 W typical, 31 W peak at 5 V; 20 W (0.27 A) typical, 35 W (0.5 A) peak from 72 V at 88 percent; about 0.8 percent of 2.5 kW; Pi 5 measured 2.2 to 3.0 W | Results power-budget table |
| Pack | DB24SA01L24S150ABU: 24 cells, 150 A BMS; 74.7 V at 60 percent (3.11 V per cell), about 60 to 88 V | Results R5 |
| Closed box (16 Oct) | Pi 4 68.6 to 76.9 C over about 70 min; flags 0xD0000, brown-out restart at 0x50005; lost dashboard lines 2 to 10 percent | Methodology Pi 4 investigation |
| Pi 5 restarts (19 Oct) | 4 during mounting; last readings 4.95 to 5.08 V, flags clean, 57 to 59 C; lowest 4.89 to 4.97 V in the 2 min before | Methodology Pi 4 investigation (recurrence) |

---

## 4. Glossary

| Term | Meaning |
|---|---|
| ACK, PUBACK | Acknowledgement; in MQTT QoS 1 the broker's reply confirming it received a PUBLISH |
| A7670X | SIMCom LTE Cat 1 modem with GNSS on the Makerfabs board |
| AGPS / A-GNSS | Assisted GNSS: satellite orbit data downloaded over the network to speed up a fix |
| AI | Artificial intelligence |
| AP, mAP | Average precision; mean over classes. mAP@50 at IoU 0.5; mAP@50-95 averaged over IoU 0.5 to 0.95 |
| API | Application programming interface |
| AT commands | Text commands to a modem ("AT..."), answered with OK, ERROR or result lines |
| BLE | Bluetooth Low Energy |
| BMS | Battery-management system |
| BOM | Bill of materials |
| CDC | USB Communications Device Class (virtual serial port) |
| CF | Crest factor, peak over RMS |
| CLBS | The modem's cell-tower (network) position command |
| COCO | Common Objects in Context, the dataset the detector was trained on |
| CSI | Camera Serial Interface (the Pi camera ribbon) |
| CSQ | Modem signal quality value (AT+CSQ) |
| CSV | Comma-separated values |
| D | The dual-IMU disagreement figure |
| DASH line | The 1 Hz JSON line from the ESP32 to the Pi 4 for the dashboard |
| DIO / QIO | Dual / quad I/O flash access modes |
| DLPF | Digital low-pass filter (in the MPU6050) |
| DP | Duly performed (course requirement to be allowed to submit) |
| DPMS | Display power management (screen blanking) |
| ESP32-S3 | Espressif dual-core microcontroller used in the telemetry unit |
| FIFO | First-in first-out buffer (the IMU's hardware sample buffer) |
| FreeRTOS | Real-time operating system on the ESP32 |
| fps | Frames per second |
| GA | Graduate attribute (GA1, 4, 5, 6, 8, 9; GA10 professionalism) |
| GATT | Generic Attribute Profile: BLE services and characteristics |
| GNSS | Global navigation satellite systems (GPS, BeiDou, Galileo, GLONASS) |
| GPIO | General-purpose input/output pin |
| HDOP / PDOP / VDOP | Horizontal / position / vertical dilution of precision |
| HPEC | High-performance embedded computing |
| HTTP | Hypertext Transfer Protocol |
| HUD | Head-up display |
| Hz | Hertz |
| I2C | Two-wire serial bus (SDA data, SCL clock) |
| IMU | Inertial measurement unit (accelerometer and gyroscope) |
| IoU | Intersection over union of two boxes |
| IoV / IoT | Internet of Vehicles / of Things |
| IRAM | Instruction RAM on the ESP32 (code there keeps running during flash writes) |
| IRI | International Roughness Index (m/km, quarter car at 80 km/h) |
| ISO 2631-1 | Standard for evaluating whole-body vibration (weighting up to 80 Hz) |
| ISO 15008 | Standard for legibility of in-vehicle visual displays |
| ISP | Image signal processor in the camera pipeline |
| JBD | Jiabaida BMS protocol |
| JSON | JavaScript Object Notation |
| JTAG | Hardware debugging interface |
| LiteRT | Google's runtime for TensorFlow Lite models (ai-edge-litert) |
| LittleFS | Power-loss-tolerant flash file system |
| LoRa / LoRaWAN | Long-range low-power radio / its network protocol |
| LTE Cat 1 | Low-rate 4G LTE category |
| MCU | Microcontroller |
| mDNS | Multicast DNS (name.local lookup) |
| MEMS | Micro-electromechanical systems (the IMU technology) |
| MJPEG | Motion JPEG video stream |
| ML | Machine learning |
| MQTT | Lightweight publish and subscribe messaging protocol |
| NCNN | Tencent's lightweight neural-network inference library |
| NHTSA | US National Highway Traffic Safety Administration |
| NMS | Non-maximum suppression |
| NoIR | Camera module without an infrared-cut filter |
| NTP | Network Time Protocol |
| NVS | Non-volatile storage on the ESP32 |
| OSM / OSRM | OpenStreetMap / Open Source Routing Machine |
| p50 / p95 | Median / 95th percentile |
| PC817 | Optocoupler used for the Hall tap |
| PCIe | PCI Express bus (for the Hailo-8 on the Pi 5) |
| POPIA | South Africa's Protection of Personal Information Act |
| PSRAM | External pseudo-static RAM on the ESP32 module (unused) |
| QoS | MQTT quality of service level 0, 1 or 2 |
| R | Speed-normalised index sigma squared over v (also R1 to R13 are requirements) |
| RMS | Root mean square |
| RQ | Research question |
| RTK | Real-time kinematic GNSS (centimetre-level) |
| SEN55 | Sensirion particulate, VOC, NOx, humidity and temperature sensor |
| SoC | State of charge |
| SQLite | Single-file database |
| SSD | Single Shot MultiBox Detector |
| TLS | Transport Layer Security (encryption) |
| ToF | Time of flight (distance sensor) |
| TRL | Technology readiness level |
| TTC | Time to collision |
| UART | Universal asynchronous receiver-transmitter (serial port) |
| UDP | User Datagram Protocol (the Pi 4 beacon) |
| USB | Universal Serial Bus |
| VIT | Vehicle integration and test plan (SW7-VIT-001) |
| VL53L0X / VL53L5CX | Single-zone / 8x8-zone ToF sensors |
| XSHUT | ToF sensor shutdown pin, used to assign addresses |
| YOLO | You Only Look Once detector family (YOLO11n used for potholes) |

---

## 5. Things not to say

| Do not say | Why | Say instead |
|---|---|---|
| "It works on the trike." or "The road test is done." | One road session: R1 and R5 met on the vehicle, but no GNSS, raw samples or run markers. | "The first road session met R1 and R5 on the vehicle; the ride questions need the second session." |
| "The approaching-object warning works." | Synthetic tests only; C11 not run; road alerts not checked against video. | "It is within 2 percent on synthetic data; a real approach test is next." |
| "261 cars approached the trike." | Not checked against video; a still object ahead counts while driving. | "The front detector marked 261 car alerts as approaching; I have not checked them against video." |
| "The Pi 5 browned out." | Its logger showed normal values just before each restart. | "Abrupt power loss, probably a connector, the source or the supply's protection, not a brown-out." |
| "The power budget is 20 W." (as measured) | Only the Pi 5 is measured. | "About 20 W, of which only the Pi 5 share is measured." |
| "The enclosures are on the vehicle." | Only the rear box and a first IMU pod are printed. | "Designed and checked in CAD; the rear box and an IMU pod are printed so far." |
| "Reverse gear switches to the rear camera." | There is no gear signal from the vehicle. | "The dashboard's own gear state does; a vehicle gear signal is not wired." |
| "Detection takes 50 ms." (for the whole system) | Front only, on the Pi 5; the rear Pi 4 is about 120 ms or more. | "51 to 54 ms at the front on the Pi 5; the rear is still the Pi 4." |
| "The IMUs are calibrated." | Calibration holds only in the orientation measured; on 11 Oct they read about 10.87 and 10.12 m/s2 at rest. | "Calibrated at the time; must be redone once mounted, which the firmware does with one command." |
| "Calibration reduced an 8 percent error to noise." | At calibration they were 1.3 percent apart; the 8 percent was an earlier session. | "An 8 percent disagreement seen earlier; after calibration both read 9.80 to 9.81 in that orientation." |
| "Zero dropped samples, so no gaps." | 33 to 40 ms pauses at each flush. | "Zero lost samples; one 37 to 40 ms pause a minute at the log flush, then bunched samples." |
| "The detector latency is 102 ms." (alone) | Best case with nothing else running. | "102 ms on the bench alone, about 120 ms on the fully loaded Pi." |
| "Alerts reach the driver in 0.5 s." | That was time after opening the page with a person in view. | "Alert onset is about 0.2 s at the detector; time to the screen on the Pi 5 is not yet measured." |
| "The fusion gives accurate distance." | C9 not run; first fused case cannot say which reading was right. | "The matching works on live data; accuracy is test C9, not yet run." |
| "The pothole model is 71 percent accurate." | mAP@50 on validation tiles used to pick the epoch; not accuracy; per tile. | "0.714 mAP@50 on validation tiles, optimistic; the held-out score is next, and it is too slow for the Pi 4 at present." |
| "It detects hazards / vehicles." | Only the person class confirmed live. | "It reports seven road-user classes; only person has been confirmed on live frames." |
| "GNSS is accurate to 2.7 m." | Agreement with a phone; p95 11 m. | "A median of 2.7 m from a phone's position, 95 percent within 11 m." |
| "The network position is 30 m accurate." | One reading; stated accuracy 550 m. | "Stated to 550 m; it happened to be about 30 m off once." |
| "Speed is in km/h" or "speed is unknown." | The manual says knots; not confirmed on this modem. | "The manual says knots; I will confirm against a known speed on the road." |
| "No data is ever lost." | T15 needed 24 records backfilled from the log; the public broker acks without delivering; a power cut loses up to a minute of unflushed records. | "In the outage test nothing was lost end to end, with the device log as the safety net on this broker." |
| "Synchronised with the central database." (unqualified) | It is my SQLite on the Pi 5 via a public broker; latency unmeasured. | "Stored in a database on the Pi 5 through MQTT, completeness tested; latency and the partner broker are next." |
| "The dashboard is safe to use while driving." | Glance time not measured. | "Designed against the 2 s guidance; glance time is the open part of RQ2." |
| "RQ4 is answered." | No vehicle data, no frequency-domain features. | "The method is designed; RQ4 needs the Hall tap and vehicle data." |
| "Low-cost" as a proven claim | No BOM. | "Commodity parts; I have not totalled the cost yet" (or give the BOM once done). |
| "AI only helped with wording." | The repository records much wider use. | "I used an AI assistant for code, test analysis, literature search and wording; I made the decisions, ran the tests and can defend every result." |
| "The ToF sensors are accurate to 5 percent." | No tape check yet. | "They respond correctly to a hand; accuracy against a tape is in test C9." |
| "The battery reading is correct." | Not compared with a meter or the app. | "Plausible for 24 cells at rest; not yet checked against a meter." |
| "ISO 2631-1 requires 200 Hz." | ISO sets the band, not a sampling rate. | "The ISO band goes to 80 Hz, so Nyquist needs over 160 Hz." |
| "My features measure ride comfort." | No ISO weighting, magnitude not vertical. | "They measure vibration exposure, a vehicle-specific response, not comfort or IRI." |
| "The two IMUs measure the same thing, so averaging is optimal." | They are at different points. | "The average is an exposure across two points; D shows when they differ, and per-sensor values are kept." |
| "The flash stall is fixed." | Only less frequent; same length. | "Six times less often, same length; removing it needs IRAM, the IMU FIFO or logging elsewhere." |
| "The power problem is solved." | The powered hub and 5.1 V 3 A supply are open items; no long run shown. | "The cause is found; the fix is a separate supply, still to be proven on a long run." |
| "TRL 6." | Not demonstrated in a relevant environment. | "A bench-validated integrated prototype, about TRL 4; TRL 6 needs the vehicle." |
| "Nobody has done this before." | The gap is bounded by a search and narrowed twice. | "My search found no system integrating these on this vehicle class; the contribution is the integration and its measurement." |
| Any number you are unsure of | Guessing loses more than admitting. | "I don't have that number; this is how I would measure it." |

---

## 6. What I could not verify

- Papers cited but not opened by me (statements rely on the report, the project's notes or abstracts): Li et al. 2018 (the project verified it from the abstract), Caroleo 2026, Gonzalez 2008, Sattar 2018, FHWA 2016, ISO 2631-1, ISO 15008, Shi 2016, Barnell 2018, Liu 2003, Smith 2016, Zhu 2021, Park 2020, Hauslschmid 2015 and 2016, Mareska 2022, De Simone 2018, Noomwongs 2025, Saenz 2016, Kimmel 2020 (TRL definitions given from the standard NASA scale), the Electronics 2026 motorcycle paper (reviewed by the project from its abstract).
- Opened and checked: the brief, Sebwa 2025, Yiliguoqi 2026, Bui 2026, Alatoom 2025 (title and abstract only), Perez-Gonzalez (preprint version), NHTSA 2013, Reimer 2014, Strayer 2017, Euro NCAP 2026, Kim (2011 KIIE version, not the 2014 paper cited), Qin 2017 (title), SSD, MobileNets, Jacob 2018, COCO, Alqahtani, Zhu 2019, Tanveer 2026 (abstract), SIMCom A76XX manual v1.09 (CMQTTPUB and GNSS speed sections).
- General engineering facts not in the repository and stated from general knowledge: MPU6050 internal rates and filter delays, LTE Cat 1 data rates, MQTT QoS 2 handshake names, ESP32-S3 built-in USB JTAG, A7670X TLS support, the I2C read-time estimate, the clock-rate difference from the 500.06 ms median, the focal-length and width-error arithmetic, and the end-to-end alert latency sum.
- Not found in the repository: a bill of materials or any cost figure; a power measurement other than the Pi 5's internal readings; the venue, the people present and the signed risk assessment for the 19 October session; SW-6's own project topic; the ethics approval letter itself (the application PDF and the log record of approval on 23 September are present).
- PROJECT_LOG.md's status board stops around 1 October; later facts come from TEST_PROCEDURES.md, REMAINING_WORK.md, the 10 to 11 October logs and the current report.
- Readings from logs that are my own analysis, not in the report: the 11 October resting magnitudes (10.87, 10.12), the T15 gap count (10 of 368 windows over 10 ms, worst 44.1 ms), and the D = 1.68 sensor values.
