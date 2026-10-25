# Run 2 placeholders: success template and fallback text

Written 25 Oct 2026. The report has 11 `\outstanding{...}` placeholders (macro in Project Report Template.tex, line 47). On Monday night each one is replaced by either:
- the "success" text, with the numbers from `summary.json` and the logs; or
- the "fallback" text, if the data were not obtained.

No bracket may remain in the submitted PDF. Check with `grep -n "outstanding{" Report/*.tex`, which must return nothing. Then delete the macro or leave it unused. Each fallback names what is missing and why, and keeps the requirement and its status honest.

Rules for filling:
- Numbers come only from files: summary.json, recorder session, raw captures, meter markers, video crossings.
- Say "n = ..." for every count.
- Keep the word count level, because the body is at 14,946 of a 15,000 guide. Replace, don't add.

| # | Location | Success: fill with | Fallback, if not obtained |
|---|---|---|---|
| 1 | Results 5.1 (R1), line 22 | "On the road part of run 2 (26 October), over N s of driving, the raw streams held X Hz with G sequence gaps (front) and G (rear); the longest interval was T ms; read failures R, stuck S, late L, raw drops D." Update the R1 row of Table 5.3 | "The road part of run 2 did not produce [reason], so acquisition on the moving vehicle rests on road session 1 (above) and the stand runs of 23 October, which had no sequence gaps in 114,000 samples per node." R1 stays "not met on the vehicle" |
| 2 | Results 5.3 (R3, RQ1, RQ4), line 64 | Per section and speed: mean a_w, sigma, CV with its bootstrap CI; ICC with CI and its status line; front-to-rear delay and speed against the video; stand lines assigned to orders if the wheel rate was filmed; coasting against powered share. One figure (a_w or I_v against speed) | "Run 2's road part [did not take place / produced no usable passes: reason]. Repeatability over road passes (RQ1) and the road share of the powertrain lines (RQ4) were therefore not measured; the analysis that would compute them ran on the data of 23 October and reproduced the stand lines (Section J.20)." |
| 3 | Results 5.4 (R4), line 73 | Receiver TTFF in the open; phone and receiver speed against the video over section A: mean difference and spread per speed, n passes; units of spd_raw confirmed | "The vehicle's receiver fixed outdoors on 24 October (above), but its speed and the phone's were not compared with a known speed on the vehicle. Speed is therefore taken from the video wherever it is used." R4: "partly met" |
| 4 | Results 5.5 (R5), line 79 | Meter against BMS voltage: key off, 3 readings, mean difference; at 30 s into each stand run, n readings, mean and largest difference. R5 becomes "met" if within the criterion | "The BMS voltage was not compared with a meter; R5 stays partly met. The record behaves like a real pack: the voltage fell by 0.32 and 0.51 V at 3.3 and 4.6 A on the stands of 23 October and recovered at rest (Section K.5)." Add that table to K.5 |
| 5 | Results 5.6 (R7, R8), line 112 | V5: per approach, whether and when an alert was raised against the forward video; counts "n = ..., descriptive" | "Block V5 was not run, so the detector has no check against video on the vehicle; R7 stays partly met." |
| 6 | Results 5.7 (R10, RQ3), line 144 | Share of DASH sequence numbers received per node; if LTE published: records at the database against the flash log, and latency from utc_ms to ingest (median, 95th percentile) | If no LTE: "Publishing was switched off for the run because the node's SIM had no working data connection (Section E.3), so latency and completeness at the database on the moving vehicle were not measured; the local link delivered P % of DASH records." If no DASH data: say which source failed |
| 7 | Results 5.8 (R12), line 150 | Not planned for Monday (moved to a sunny lab day). Fill only if done | "Display photographs in sunlight were not taken; contrast in daylight remains unmeasured (Section 6.5)." |
| 8 | Results 5.9 (integration, R13), line 158 | Resets per unit, recorder completeness per source, supply flags, removal time against about 20 min | "R13: the system was removed from the vehicle without tools, but the removal was not timed." Plus whatever resets were observed, or "not recorded" |
| 9 | Discussion 6.2, line 18 | Interpretation of #2: is the CV below 10 %, the ICC above 0.75, I_v speed-invariant (slope and CI)? What does the coasting comparison say about which band is powertrain? | "Without road passes, RQ1's repeatability and RQ4's road share stay open; what the data do show is a stable sensor at rest (CV 1.7 to 4.2 % over 10 s windows) whose vibration follows the motor load on the stands (r 0.80 with current), with the powertrain at 40 to 70 Hz at both ends." |
| 10 | Discussion 6.3, line 26 | Interpretation of #5: hits, misses, false alerts in the closed area; what that implies for the band and TTC thresholds | "No forward video of the closed area was taken, so the alerts on the vehicle remain unchecked against ground truth." |
| 11 | Conclusions, line 14 | One or two sentences per RQ with the headline numbers from #2 and #9. Then rewrite the abstract's last sentence | "RQ1 and RQ4 remain open on the road: the instrument and the analysis are verified, the powertrain's lines are located on the stands, and the road passes that would answer both are the first item of Chapter 8." Check that Recommendation 1 says so |

## After filling (Monday night)

1. `grep -n "outstanding{" Report/*.tex` returns nothing.
2. Update Table 5.3 rows R1, R4, R5, R7, R9, R10, R13 to match.
3. Rewrite the abstract's last two sentences and the "Overall" paragraph of Chapter 7.
4. Run `python Report/wordcount.py`: the body must stay at or under 15,000, and the declaration's count must be updated.
5. Rebuild: Bibliography must start no later than body page 51 (50 pages maximum).
6. Deck slides 3, 13 and 14 and the poster's section 6: replace "pending" with the results (memory rule: update the presentation too).
7. Upload the presubmission before midnight.
