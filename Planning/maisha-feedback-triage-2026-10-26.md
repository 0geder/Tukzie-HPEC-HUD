# Maisha Magavha's review of 26 Oct 2026: what was done with each point

Source: SW7_Revised_Project_Report_Feedback.pdf (9 pages), outside the repository. Checked against the report text on 26 Oct. Simon's guidance (26 Oct) takes priority: the run-2 results matter more than wording.

## Fixed on 26 Oct (claims contradicted by the report's own record)

| Point | Change |
|---|---|
| "No lost samples" in Chapter 7 against Section 4.3.2 | Chapter 7: read at 200 Hz with no queue overflows; flash pauses up to 44 ms; catch-up reads are new readings, not the missed instants |
| "None is lost" in Section J.2 | J.2: no queue entry is lost, but the catch-up reads are fresh readings (MPU6050 output registers hold the latest sample) |
| "RQ1 answered for the instrument on the bench" | Chapter 7: RQ1 partly answered |
| "In every bench session" (Results 5.1) | Limited to the sessions of Table 5.1 |
| "Outages lose nothing" (Table 4.7) | Radio outages replayed from the log; the record key prevents duplicate rows |
| 5.3 ms "at most" (Section 4.5) | Budgeted at 5.3 ms, provisional until the fixed offsets are measured |
| K.9 assumes lithium iron phosphate while K.5 says unconfirmed | K.9: "for 24 cells if they are lithium iron phosphate, which is not confirmed" |
| NHTSA 2 s as a limit on every glance | Introduction: acceptance criteria across test drivers, glances mostly 2 s or less and 12 s in total |
| W_k check to 400 Hz with 200 Hz sampling | J.20: the table check covers the analogue prototype; the sampled filter was not checked separately |
| Deliverables: environmental payload | Chapter 7: three produced, the interface changed, the air-quality payload not delivered (Section 1.5) |

## Not valid now or already handled

- "One power plate must be wrong" (Introduction): already reworded before this draft ("the two disagree and neither was measured").
- Figure J.3 at +/-35 degrees: its caption already says these are the first defaults and the bearings were later set to +/-90.

## For the run-2 write-up (27 Oct)

- RQ4 "share of the road spectrum": state the signal and denominator (band energy 40 to 70 Hz over 0.5 to 80 Hz total, on the unfiltered stream), not 2 to 40 Hz.
- Analysis: windows with flash gaps or catch-up bursts flagged before Welch spectra; clipping from per-axis samples, not magnitude.
- Pothole thresholds: in-sample, exploratory unless separate passes are used.
- Speed from front-to-rear delay: validate against the side video before calling it a method.
- Power: the new Pi 4 board shows no under-voltage when the Makerfabs board is not on its USB; report the final power arrangement and the under-voltage count from the run.
- Database: give direct, replayed and backfilled counts separately.

## Limitations to state, not fixable by tomorrow

- Timing: node-to-Pi-to-analysis timestamp transformation and fitted offsets not measured; mallet-strike delays may include structural propagation.
- Display freshness: 3 s provider limit plus the dashboard's 2.5 s watchdog; field-level ages not tested.
- Warning path: class alerts, time-to-contact warnings and displayed warnings not separately validated; association accuracy of fusion not tested beyond the parked checks.
- Table K.2 sample counts (5,110 in 20 s, 6,800 in 30 s) need the capture durations checked.
- Requirement criteria (R1, R2, R3, R6, R7) verify components, not the system; say so in Section 5.10.
