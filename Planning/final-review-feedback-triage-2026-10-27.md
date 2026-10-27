# Maisha Magavha's second review (27 Oct 2026): triage against the current source

Source: `Samson_Final_Report_Review_Feedback.pdf` (11 pages, outside the repository), "Reviewed by Maisha Magavha, 27 October 2026", of the report dated 26 October. Every point below was checked against the .tex source as it stood on the morning of 27 October (files dated up to 27 Oct 01:00). No report file was edited. Line numbers are current source lines and will drift as the other agent edits.

Categories: 1 = valid, quick fix; 2 = valid, needs road data; 3 = valid, state as limitation; 4 = already fixed; 5 = not valid or no action.

Counts: 1: 34; 2: 7; 3: 13; 4: 17; 5: 2 (73 points).

Body is at 49 of 50 pages, so most fixes below are replacements of similar length. Simon's priority (road results first) still holds; the quick fixes are for the gaps around the road write-up.

## Top quick fixes, ranked by marks per minute

| # | Point | File | Old text (exact) | New text |
|---|---|---|---|---|
| 1 | 2a | main .tex, abstract | `On the bench, both sensors held 200\,Hz with no dropped samples, apart from flash-write pauses of up to 44\,ms;` | `On the bench, both sensors were read at 200\,Hz with no queue losses, but each flash write left a gap of up to 44\,ms that the later reads do not fill;` |
| 2 | 2b | Conclusions.tex l13 | `On the bench (Section~\ref{sec:res-telemetry}), acquisition loses no samples and pauses only at the once-a-minute flash write (33 to 44\,ms).` | `On the bench (Section~\ref{sec:res-telemetry}), acquisition loses no queued samples, but the once-a-minute flash write leaves a gap of 33 to 44\,ms that is not recovered.` |
| 3 | P5, 9a | Conclusions.tex l13 | `after a 10-minute outage every logged record was stored once in the database, the store-and-forward behaviour Section~\ref{sec:lit-sync} calls for.` ... `RQ3 is answered on the bench. Latency to the database and completeness on the moving vehicle were not measured.` | `after a 10-minute outage the 60 queued records were replayed automatically and every logged record was stored once, 24 of them only after a backfill from the unit's log.` ... `RQ3 is partly answered: component latencies and recovery are measured on the bench, but end-to-end latency to the database and completeness on the moving vehicle were not measured.` |
| 4 | 1e | Conclusions.tex l22 | `The brief asked for four deliverables. Three were produced and the driver interface in a changed form; the environmental and air-quality payload named in the first was not delivered` | `The brief asked for three deliverables. The first, the hardware module, was produced with its inertial payload, with the head-up display replaced by the existing dashboard by agreement, but its environmental and air-quality payload was not delivered` (and change the last sentence `The fourth deliverable is this report.` to `The third deliverable is this report.`) |
| 5 | 1e | Introduction.tex l14 | `The brief \cite{winberg2026} asked for (1) an HPEC telemetry unit with a deterministic multi-threaded architecture; (2) a driver interface, originally a windshield head-up display (HUD); (3) synchronisation with a central database over 4G/LTE; and (4) a technical report validating the data and the system.` | `The brief \cite{winberg2026} asked for (1) a telemetry module with environmental, air-quality and inertial sensors and an optical windshield head-up display (HUD); (2) a deterministic multi-threaded software architecture for sensor fusion, ride metrics and the display; and (3) a technical report validating the data, edge latency and synchronisation with a central database over 4G/LTE.` |
| 6 | 4a | Methodology.tex l151 | `Both are well inside the proposed 10\,\% criterion against the video speed, so timing does not limit the method; correlation does,` | `Both are inside the proposed 10\,\% criterion against the video speed if the unknown offsets are within their proposed bound, which is not yet measured; correlation is the larger risk,` |
| 7 | 1c | Conclusions.tex l34 | `so road accuracy rests on repeatability (Section~\ref{sec:requirements-mapping})` | `so on the road only repeatability can be assessed, not accuracy against the true road input (Section~\ref{sec:requirements-mapping})` |
| 8 | L3 | Introduction.tex l53 (Table 1.1, R12) | `Single glances within the 2\,s NHTSA guidance \cite{nhtsa2013}` | `Single glances within 2\,s, a project target stricter than a single NHTSA criterion \cite{nhtsa2013}` (also Method.tex l9 `the 2\,s single-glance limit for the display` to `a 2\,s single-glance target for the display`) |
| 9 | 1d | main .tex, Terms of Reference l148 | `\item acquire synchronised inertial, battery, positioning and camera data on the vehicle;` | `\item acquire synchronised inertial, battery, positioning, camera and environmental (air-quality) data on the vehicle;` and l146 `integrated with the vehicle's existing dashboard.` to `with a windshield head-up display, replaced by agreement with the supervisor by integration with the vehicle's existing dashboard.` |
| 10 | 8a | Conclusions.tex l11 | `Only live data are shown, and a record more than 3\,s old is shown as absent.` | `Only live data are shown: a record more than 3\,s old stops being sent and is shown as absent within a further 2.5\,s, though individual fields are not aged separately.` |

Next in line (11 to 20): L4 Kimmel reference; P2 Table K.4 TTC; P3 J.9 SEN55 cable; 5d feature self-test scope; 2d Table K.2 counts; C2 E.3.7 short dips; 3a Discussion "logging independently"; 4d Eq. 4.10; 6e J.20 powertrain band; A3 K.3 clipping.

## All points

### Overall and major issue 1: road objectives and scope

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| 1a | RQ1 and RQ4 results outstanding (Sections 5.1, 5.3, 6.2, 7.1) | 2 | 11 `\outstanding{}` placeholders remain (Results 8, Discussion 2, Conclusions 1). Fill from today's road run. |
| 1b | Do not write the expected answer into the conclusion; narrow title, abstract and conclusions if the road data fail | 2 | Conclusions l17 placeholder is phrased as "RQ1 answered with the CV and ICC ...". When filling it, report the measured CV, ICC and $I_v$ result whether or not they meet the 10 % and 0.75 criteria. If the road run fails, the abstract's last sentence already lists these as open. |
| 1c | "Road accuracy rests on repeatability" conflicts with the narrower accuracy definition | 1 | Conclusions l34 (top 10, #7). Introduction l27 `so the road part of RQ1 is answered by repeatability.` to `so for the road part of RQ1 only repeatability can be assessed, not accuracy.` |
| 1d | Terms of Reference omit environmental and air-quality payload | 1 | Verified: main .tex l146 to l154 lists no environmental sensing and no HUD. Top 10, #9. |
| 1e | Section 1.2 recasts the brief as four deliverables; brief lists three | 1 | Verified against the brief (`Desktop/Fourth Year/EEE4022S/EEE4022S 2026 Topics Winberg_Taken By Samson.pdf`): Deliverable 1 hardware module with environmental, air-quality and IMU payload plus optical HUD; 2 deterministic software architecture; 3 validation report. Introduction l14 and Conclusions l22 both say four. Top 10, #4 and #5. |
| 1f | Map each original deliverable to delivered, changed, partly demonstrated, not delivered | 1 | Conclusions l22 already does most of this; the #4 rewrite completes it. No table needed. |

### Major issue 2: acquisition accounting

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| 2a | Abstract "no dropped samples" conflicts with Section 4.3.2 | 1 | Abstract still says it. Top 10, #1. |
| 2b | "Acquisition loses no samples" on page 44 | 1 | Conclusions l13 still says it. Top 10, #2. |
| 2c | R1 criterion too weak; report slots, reads, repeats, missed deadlines, overflows, transport losses separately | 2 / 3 | Results l22 placeholder already asks for sequence gaps, sample intervals and read-failure, stuck, late and raw-drop counts from the road run: report each separately there. Limitation for Section 5.10 or 6.1: `R1 as defined counts queue losses, not missed sampling instants; the flash-write gaps are visible only in the sample timestamps.` |
| 2d | Table K.2: 5,110 in 20 s and 6,800 in 30 s imply more than 200 Hz; 69 edges span 34 s | 1 | Arithmetic confirmed. Lab notebook (22 Oct, l310 to l312) gives the same figures with no capture boundaries, so the durations were nominal. appendixk.tex l44: `At 115\,200\,baud: 5,110 samples in 20\,s, 0 missing, line 85\,\% full. At 921\,600\,baud: 6,800 samples in 30\,s, 0 missing by sequence,` to `At 115\,200\,baud: 5,110 samples in a capture of about 20\,s, 0 missing, line 85\,\% full. At 921\,600\,baud: 6,800 samples in a capture of about 30\,s (34\,s by its 69 sync edges; the durations were not timed, so no rate is taken from these counts), 0 missing by sequence,`. Same change in appendixc.tex l53. |

### Major issue 3: network failures and local logging

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| 3a | GNSS polled once in 30 s (E.3.9) and log interval up to 58 s (K.3.1) because the modem task is shared; against the brief's no-blocking requirement | 3 + 1 | Both facts are in the source (appendixe l267, appendixk l81). The brief does say "ensuring no process blocking occurs" (GA1). Quick fix, Discussion.tex l34: `Logging independently of the connection gave the store-and-forward behaviour the review called for.` to `Logging every record to flash whatever the connection gave the store-and-forward behaviour the review called for, but the records are built in the modem task, so a failing connection stretched the 10\,s log interval to up to 58\,s and the 3\,s GNSS poll to about 30\,s (Sections~\ref{sec:resx-flashlog} and~\ref{sec:inv-gnss-hang}).` |
| 3b | Retest with broker unavailable, failed registration, modem timeouts | 3 | Add to Recommendations item 5 (Connectivity), after `Measure latency to the database and completeness on the moving vehicle;`: `bound each modem transaction and build log records outside the modem task, so that a failed connection cannot delay GNSS polls or local records;` |

### Major issue 4: synchronisation and speed from delay

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| 4a | Table 4.3 counts an unknown offset at a proposed 2 ms and concludes timing does not limit the method | 1 | Methodology l151 still says "so timing does not limit the method". Top 10, #6. Table row l166 `Worst-case sum & 5.3\,ms & \\` to `Worst-case sum & 5.3\,ms & Provisional: the fixed offsets are unmeasured \\` |
| 4b | Monotonic clocks on each Pi vs chrony-synchronised wall clocks: complete time conversion not shown | 3 | Verified: Methodology l204 and appendixj l167 put GPIO edges and frames on the monotonic clock; Method l83 syncs the Pis with chrony (wall clock); the stand-run caption cuts windows "by the Raspberry Pis' synchronised clocks". No text maps the two monotonic clocks to a common epoch. Limitation, Discussion 6.7 (Validity) end: `The mapping from each Pi's monotonic clock to the shared chrony time was not measured, so front-to-rear timing rests on host receive times until it is.` |
| 4c | Mallet check mixes electrical offset with chassis propagation; cross-correlation may follow a shared chassis response | 3 + 2 | Table 4.3 row l165 still proposes the mallet zero. Replace `In-situ zero from ten mallet strikes midway between the nodes; proposed criterion $\pm 2$\,ms, counted at that bound until measured` with `Ten mallet strikes midway between the nodes, which may include propagation through the frame; counted at a proposed $\pm 2$\,ms until measured`. Validating the lag against the side-video speed over bump passes is road data (Results l65 placeholder). |
| 4d | Eq. 4.10: independent standard uncertainties or worst-case limits? | 1 | Eq. 4.10 is root-sum-square but Table 4.3 is a worst-case sum. Methodology l151, after `with no GNSS.` insert `The two terms are combined as independent; the timing term itself is a worst-case sum.` |

### Major issue 5: signal-processing interpretation

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| 5a | Magnitude can show peaks at twice a horizontal frequency; stand peaks are not yet mechanical frequencies | 1 | Eq. 4.3 (Methodology l97 to l100) already has the squared horizontal term; the 2f consequence is not drawn. Results l56, after `so powertrain vibration reaches the front through the frame (Figure~\ref{fig:res-stands}).` insert `These are peaks in the sampled magnitude: horizontal motion enters it squared (Equation~\ref{eq:magnitude}) and can appear at twice its frequency.` Reanalysis by axis: road analysis already uses a vertical projection (appendixj l294), so it applies to run-2 data. |
| 5b | Aliasing discussion should stay conditional | 4 | Methodology l80 is conditional ("could be images of"). No change. |
| 5c | R2 checks the calibration's own definition | 4 | Results l29: `These are the factors' own definition, not an independent check`; Table 5.3 R2 status: `mounted factors not yet rechecked`. |
| 5d | R3: the sine test checks RMS, peak-to-peak and crest factor only | 1 | Verified (appendixj l107, appendixk l65). Conclusions l9 `The features are computed correctly.` to `The boot self-test confirms RMS, peak-to-peak and crest factor; jerk, the threshold count and windows with gaps are not checked separately.` Results l34 `R3 is met: the features are computed and combined as designed,` to `R3 is met as defined: RMS, peak-to-peak and crest factor match a synthetic sine and the fusion behaves as designed,` |

### Major issue 6: road-analysis risks

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| 6a | J.3 raw line timestamps only the first sample; are times after a flash pause preserved? | 1 (text), 5 (substance) | The format does preserve them: `TelemetryUnit/RAW_STREAM.md` and `BenchTest/analysis/readers.py` l194 and l270 carry a per-sample sequence step and time step in microseconds, and the reader rebuilds times by cumulative sum. The report text omits this. appendixj l86 `with the slot sequence number and microsecond time of the first;` to `with the slot sequence number and microsecond time of the first and each later sample's sequence and time steps, so the actual time of every sample, including catch-up reads after a flash pause, is kept;` |
| 6b | Wk digital response unverified; does Wk see the 2 to 40 Hz signal? | 4 + 1 | Digital response: appendixj l295 already says the sampled filter was not checked. Input: code (`dsp.py` l12, l217; `config.py` l41) applies Wk to the unfiltered vertical, but the text is ambiguous. appendixj l295 `$a_v$ is weighted by the ISO~2631-1 $W_k$ filter` to `the unfiltered $a_v$, not the 2 to 40\,Hz band, is weighted by the ISO~2631-1 $W_k$ filter` |
| 6c | Mounting location; chassis measurement is not occupant exposure | 3 | Methodology l139 says body-mounted for $I_v$; not said for $a_w$. Add to appendixj l295 end: `Measured on the frame, not at the seat, $a_w$ and VDV describe the vehicle's response, not the occupant's exposure.` |
| 6d | VDV depends on duration; same distance at different speeds | 2 | Address when writing run-2 results: compare VDV per unit time or state the duration of each pass. |
| 6e | Powertrain ratio uses 2 to 40 Hz although the lines are at 40 to 70 Hz | 1 | Stale text: code uses 0.5 to 80 Hz (`config.py` l81, `powertrain.py` l5) and Method l113 says 0.5 to 80 Hz. appendixj l299 `the energy within $\pm 1$\,Hz of those lines is compared with that from 2 to 40\,Hz,` to `the energy within $\pm 1$\,Hz of those lines is given as a fraction of the energy from 0.5 to 80\,Hz of the unfiltered $a_v$, a spectral association, not a proven cause,` |
| 6f | Pothole thresholds swept on the same passes; under 1 km gives an imprecise, not undefined, rate | 1 | appendixj l300 `swept over the passes and reported as counts` to `swept over the same passes, so the result is exploratory tuning, and reported as counts`; and `under 1\,km of driving cannot estimate a false-alarm rate per km, so none is claimed.` to `under 1\,km of driving gives only a wide interval, so no rate per km is claimed.` |

### Major issue 7: hazard validation

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| 7a | R7 shows the detector runs, not useful hazard detection; 1,342 and 741 alerts unchecked | 4 + 2 | Results l105 `not yet checked against video`; Discussion l27 `How many road alerts were correct is unknown`; Table 5.3 R7 is "Partly met". Road placeholder V5 (Results l107) supplies the first check. |
| 7b | 0.26 s onset is computed, not measured; TTC needs more frames | 4 + 1 | Table 5.3 R7: `onset computed from rate and latency, not timed at the screen`. Optional: Results l86 after `about 0.26\,s, or 2.2\,m at 30\,km/h, after an object appears.` add `A time-to-contact warning needs at least five tracked frames more.` |
| 7c | First fused output 0.096 vs 0.874 m does not show which was correct | 4 | appendixc l40 and appendixk l151 say "before calibration" and "not checked against a tape". |
| 7d | Side sensors at 90 degrees do not overlap the camera's +/-26.75 degrees view; update Figure J.3 | 1 + 3 | appendixj l189 discusses only the first +/-35 degree defaults. After `so most objects to the side can be reported only by a time-of-flight sensor, without a class.` add `At $\pm 90$\textdegree\ the side cones do not overlap the camera's view at all, so only the ahead sensor is fused; the side sensors are independent lateral obstacle sensing.` Figure J.3 redraw: limitation, its caption already says the bearings were changed. |
| 7e | Bounded approach test with reference distances, still and receding targets, two objects in one cone | 3 | Recommendations item 8 covers most of it. No change needed beyond 7d. |

### Major issue 8: display validity and legibility

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| 8a | 3 s provider limit plus 2.5 s dashboard wait gives about 5.5 s; composite record not per field | 1 + 3 | Verified (appendixj l203). Conclusions l11, top 10 #10. Per-field age is already Recommendation 6 (`mark each field stale by its own age`). |
| 8b | Warning text 11 px against about 21 px; fix it without a study | 3 | Identified in Results l145 and Discussion l39 (`Enlarging the banner to about 24\,px capitals is the first change`). Not realistic to change and re-verify on the vehicle today; keep as stated. |
| 8c | Table G.1 64 px touch rule conflicts with measured sizes | 1 (minor) | Partly valid: 64 px at 0.170 mm/px is 10.9 mm, the measured median; 25 of 26 are at least 10 mm, smallest 7.5 mm. appendixg l86 `Touch targets & At least 64\,px & Use on a moving vehicle \\` to `Touch targets & At least 64\,px (10.9\,mm), met by about half the buttons (Section~\ref{sec:resx-display}) & Use on a moving vehicle \\` |

### Major issue 9: database recovery and retention

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| 9a | Distinguish automatic outage replay from backfill | 1 | Results l112 and abstract already distinguish. Conclusions l13 (top 10 #3) and Table 5.3 R9 l179: `after a 10-minute outage 112 of 112 records stored,` to `after a 10-minute outage 112 of 112 records stored (60 replayed automatically, 24 backfilled from the log),`. Confirm with the student that the backfill was run by hand; if so add `by hand`. |
| 9b | PUBACK is not a database commit | 4 | Results l112 and Discussion l34: the broker acknowledges with no subscriber present, so completeness rests on the log comparison. |
| 9c | Zero duplicate rows is not zero duplicate arrivals | 1 (minor) | Results l124 `0 missing sequence numbers; 0 duplicates` to `0 missing sequence numbers; 0 duplicate rows (repeats are removed by the record key)` |
| 9d | Power cut loses up to a minute; 3 MB cap truncates; state the retention horizon | 3 | Both in appendixj l248. appendixk l179 gives 2.2 MB for 6,020 records (about 16.7 h at 10 s), so 3 MB is roughly a day at that rate. Limitation in Discussion 6.4 if space: `The 3\,MB log holds about a day of records at one per 10\,s, and a power cut before a flush loses up to a minute.` |

### Major issue 10: power

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| 10a | Final power system unresolved (restarts, under-voltage, LiPo) | 2 + 3 | Results l158 placeholder asks for supply flags and resets over the road run. Report the final arrangement and counts from today. |
| 10b | Table K.5 uses Pi 5 before the front camera and two IMUs on the rear board | 1 | Pi 5 row already says "measured before the front camera unit was added". appendixk l212 `ESP32-S3, A7670 modem (with GNSS) and two IMUs` to `Telemetry unit (ESP32-S3, A7670 modem with GNSS) and the two IMU nodes` (values unchanged, still estimates). |
| 10c | 100 V, 40 W and 2 A fuse not justified | 1 | appendixk l219 `and be rated to at least 100\,V for transients, and deliver at least 40\,W at 5\,V for the peaks, with a fuse of about 2\,A on its 72\,V input.` to `and, as a first estimate to be checked against measured transients, inrush and concurrent load, be rated to at least 100\,V, deliver at least 40\,W at 5\,V and have a fuse of about 2\,A on its 72\,V input.` |

### Explanation and presentation

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| P1 | Figure J.2 shows an earlier architecture; final task-and-queue diagram needed | 3 | Not feasible today within the page limit. One line in the J.2 caption: `Firmware as of v0.7.4; from v0.7.6 the statistics and ride tasks are on core 0 and the IMU is on its own node.` (check against the figure before adding). |
| P2 | Table K.4: TTC "not yet run on either Pi" despite approaching alerts on 19 Oct | 1 | Verified: appendixk l153 vs l172 (366 and 261 front, 183 and 36 rear approaching alerts). `0.27\,ms per frame on the laptop; not yet run on either Pi or against a real approach (test C11)` to `0.27\,ms per frame on the laptop; ran on both Pis on the road session of 19 October, not yet tested against a real approach (test C11)` |
| P3 | J.9 says the SEN55 lacks a cable; elsewhere it was damaged | 1 | Verified: appendixj l160 vs appendixd l119 and Methodology l191. `It has been received but is not connected, for want of a six-way JST GH cable;` to `It came without its cable; wired instead through its test pads, it was damaged when the supply pad lifted, and a replacement is to be fitted with the cable;` |
| P4 | J.18 says the display and pod come off without tools; F.10 says the clamp and shell were not printed | 1 | Verified: appendixj l271 vs appendixf l354. `The display and the sensor pod come off the vehicle without tools, on a bar clamp with a dovetail rail and a locking thumb screw,` to `As designed, the display and the sensor pod come off the vehicle without tools, on a bar clamp with a dovetail rail and a locking thumb screw (not yet printed, Section~\ref{sec:mech-status}),` (check the label name of F.10 first; it may differ). |
| P5 | Abstract, Table 5.3, Chapter 7 from one evidence record; RQ3 only partly answered | 1 | Conclusions l13 says "RQ3 is answered on the bench". Top 10, #3. Also Conclusions l11 `RQ2 is answered (Sections ...) for the design and its legibility,` to `RQ2 is partly answered (Sections ...): a design, and a legibility check that it fails for the warnings,` |
| P6 | "Met on the bench" as an overall label when the criterion checks a component | 1 | Conclusions l24 `Five are met on the bench: fixed-rate acquisition, calibration, the on-board features, store-and-forward telemetry and the link to the dashboard (R1 to R3, R9 and R10).` to `Five are met on the bench as their criteria are defined (R1 to R3, R9 and R10), though R1 to R3 check components rather than the property named: no gap is recovered, the calibration is not independently checked and only three features are tested.` |

### Front matter and Chapter 1

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| F1 | Retain AI declaration and attribution | 5 | No action; appendixa keeps both. |
| F2 | Motor input and plate output ratings not automatically comparable | 4 | Introduction l6 now says `the two disagree and neither was measured`. Optional: `the two are not directly comparable (input against output, conditions not stated) and neither was measured`. |
| F3 | Table 1.1 acceptance review: R2, R3, R6, R7 are component checks | 1 | Covered by P6; R6 and R7 statuses in Table 5.3 are already "Partly met" with the reason. |
| F4 | Keep R12 untested | 4 | Table 5.3 R12 "Not tested". |
| F5 | Do not describe newly selected criteria as fixed before tests already performed | 3 | Introduction l32 says criteria were fixed before each test except T1; Conclusions l4 says "criteria fixed before each test". Cannot be verified from the source. Student to confirm; if any criterion (for example R7's 0.5 s onset or R8's 5 cm) was set after its test, change Introduction l32 to `except T1 and <IDs>`. |

### Chapter 2

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| L1 | Search not reproducible from "a fixed query set" and 733 records | 1 + 3 | The queries exist in `Research/research_pipeline.py` (l60 onwards) and each record's query and retrieval time in `research.db`. Literature l9, after `giving 733 records (\texttt{Research/research.db})` insert `; the exact queries are in \texttt{Research/research\_pipeline.py}, and each record keeps its query and retrieval time`. Selection and deduplication rules: limitation, not stated. |
| L2 | Novelty bounded by coverage | 4 | Literature l9: `The gap claim ... is bounded by these searches`; Table 2.1 blank means not described. |
| L3 | R12 "single glances within 2 s" over-attributes to NHTSA | 1 | Introduction l8 was fixed on 26 Oct, but Table 1.1 R12 (l53), Introduction l32 (`the 2\,s glance limit is NHTSA's`), Method l9 and Recommendations (`against the 2\,s limit`, `against the 2\,s single-glance limit`) still say it. Top 10, #8; Introduction l32 to `the 2\,s glance target follows NHTSA's guidance`. |
| L4 | Reference [9] kimmel2020 lists Kimmel, Weiss and Mazzuchi; NASA record differs | 1 | References.tex l41. No local copy and no source-check entry found. The NTRS record for SP-20205003605 is, to my knowledge, by W. M. Kimmel with a different group of co-authors (Beauchamp, Frerking and others); confirm at https://ntrs.nasa.gov/citations/20205003605. Safe replacement now: `\bibitem{kimmel2020} W. M. Kimmel \emph{et al.}, \emph{Technology Readiness Assessment Best Practices Guide}, NASA/SP-20205003605, NASA, 2020.` Per the source-check rule, file the PDF and log it in `Planning/source-checks.md`. |

### Chapter 3

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| M1 | State the data cut-off; replace mixed future and past tense | 2 | 14 references to the road part on 26 October (Method l36, l70; Results l56; placeholders). The road run is today, 27 October: update every date and the tense once it is done. Method l70 `the road part (26 October) runs counterbalanced passes` to past tense with the real date. |
| M2 | V-model justified as mandated by TRL 6 | 1 | Method l9 `and Technology Readiness Level 6 \cite{kimmel2020} requires bench validation of each part before testing in the relevant environment.` to `and the target, Technology Readiness Level 6, a prototype demonstrated in a relevant environment \cite{kimmel2020}, is reached only after each part has been checked on the bench.` |
| M3 | Record approvals and risk-assessment date; do not imply a driver study | 4 | Method l118 gives the approval date, reference, conditions and that the risk assessment was signed before 19 October; Method l43 says no participants. |
| M4 | First-session labels use vibration (circular) | 4 | Results l39 `so that the separation is partly by construction`. |
| M5 | Per-pass speed, exclusions, usable samples; 50 m video speed is not instantaneous in each 5 m bin | 2 | Write into the run-2 results: say the video gives a mean speed per section and that bins assume it. |

### Chapter 4

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| D1 | Current task schedule, bounded modem transactions, data-age propagation | 3 | Covered by 3a, 3b, 8a and P1. |
| D2 | $I_v$ derivation is a hypothesis; speed units unconfirmed | 4 | Methodology l139 (`The assumptions are the model's, not measured facts`, `The GNSS speed is unchecked`); Results l72 (`units unconfirmed`). |
| D3 | Replace the provisional timing-budget conclusion; show current camera-to-range geometry | 1 | Same as 4a and 7d. |

### Chapter 5

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| R-1 | Table 5.3: separate implementation and validation status | 3 | Too large for the page limit; P6 and the existing status wording carry most of it. |
| R-2 | Reconcile road-session time ranges and record counts | 1 (check) | Counts reconcile (3,464 distinct, 27 with damaged fields, 3,437 readable). Times: recorder 17:15 to 19:04 (Method l68, appendixc l49, 108.6 min); figure 17:15 to 18:50 (rear unit stopped answering 18:49, consistent); appendixk l172 says alerts `(17:15 to 19:10)`. Student to check the alert-log end time; if it is the recorder span, change to `(17:15 to 19:04)`. |
| R-3 | Do not present the historical two-sensor fusion as validation of the separate-node comparison | 4 | Table 5.3 R3: `Met for the fused design (to v0.7.6); the nodes are now compared, not fused`. |

### Chapters 6 to 8

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| C1 | Answers follow the evidence: RQ1 and RQ4 partial, RQ2 design plus failure, RQ3 component timing | 1 | RQ1 already "partly answered" (Conclusions l9). RQ2 and RQ3 per P5 and top 10 #3. |
| C2 | E.3.7 rules out short dips from 5 s logs | 1 | appendixe l242 `Those were abrupt losses of power, from a loose connector, the source or the supply's overload protection, not a brown-out or overheating.` to `They point to abrupt losses of power, from a loose connector, the source or the supply's overload protection, rather than overheating; a dip shorter than the 5\,s logging interval cannot be ruled out.` |
| C3 | Zero loss in a finite soak does not prove the trigger was reproduced | 4 | Results l20 `The soak shows that v0.7.6 ran through the fault's conditions, not that the trigger was present.` |
| C4 | Incomplete original function placed in future work | 4 | Introduction l61 `In scope but not delivered, so future work`, naming the SEN55. |
| C5 | Priorities: power, freshness, road validation before voice and styling | 4 + 1 | Recommendations list power, display freshness and validation first; voice and fleet are under future directions. Add 3b to item 5. |

### Appendices and reproducibility

| ID | Point | Cat | Evidence and action |
|---|---|---|---|
| A1 | Name the source-code revision of the submitted report | 1 | At submission, tag the commit and add to Method l92 after the repository URL: `; the report was built from commit \texttt{<hash>} (tag \texttt{report-submission})`. |
| A2 | Was the nan log regenerated or repaired offline? | 1 | It was repaired in a copy: `BenchTest/logs/2026-10-01_telemetry_log_dump.clean.jsonl` exists beside the original. appendixk l179 `and after the v0.6.3 substitution all 6,020 parse.` to `and with \texttt{nan} replaced by \texttt{null} in a cleaned copy all 6,020 parse; the firmware writes \texttt{null} from v0.6.3.` |
| A3 | K.3: 77.6 m/s2 peak-to-peak magnitude does not establish clipping | 1 | appendixk l65 `within 1\,m/s\textsuperscript{2} of the $\pm 8\,g$ range, so that peak was probably clipped.` to `close to the $\pm 8\,g$ range, though the range applies to each axis and the per-axis samples were not kept, so clipping cannot be confirmed.` |
| A4 | Distinguish CAD checks from physical tests in Appendix F | 4 | appendixf l354: `the physical tests ... have not been run`. |
| A5 | G.5 synthetic-voice results called upper bounds | 1 | appendixg l151 `so these are upper bounds.` to `so these are bench observations, likely better than a driver would achieve on the road.` |

### Not valid or no action

- F1: retain the AI declaration (agreement, no action).
- 6a substance: the raw format does keep per-sample times (only the report text needs the clause given above).

## Notes for the editing agent

- Do 2a, 2b and P5 together: the abstract, Conclusions RQ3 and Table 5.3 must say the same thing about samples and backfill.
- Several fixes are page-neutral replacements; the additions with most length are 3a, 5a, 7d and P6 (each one sentence).
- Before using L4, confirm the author list at NTRS; "et al." is safe if there is no time.
