# Examiner review of the SW-7 report, 24 Oct 2026

Built PDF reviewed: Report/Project Report Template.pdf (built 24 Oct, 16:29, from commit a595a51). The body runs from page 1 to page 49 and the PDF has 168 pages in all.

Reviewed against: the Intro Lecture, Lecture 2 and GRT5 slides (References/Course), the ethics letter (Appendix H), the rubric weights and checklists in the review prompt, and the repository.

Not available on this machine, so not verified: the course handout, the rubric itself (band wording), the marking schedule, the signed GA tracking form and the SW-7 topic sheet. Any band named below is an estimate in generic terms (Excellent, Good, Satisfactory, Poor), not the rubric's own wording.

## 1. Verdict

| Criterion (weight) | Likely band now | Moves up one band if |
|---|---|---|
| Problem statement and literature (20%) | Good, close to Excellent | RQ1 asks only what can be shown; the Table 2.1 dashes rest on more than abstracts |
| Design and theory (20%) | Excellent | Already there; keep it consistent with what was built |
| Practical work (30%) | Good, close to Excellent | Run 2 produces road data; C9 and C11 run on Sunday |
| Results and conclusions (20%) | Satisfactory to Good | RQ1 and RQ4 answered with road data; road results gathered in one place |
| Presentation (10%) | Good | The contradictions in Section 6 below fixed; Table 3.2 referenced; dense prose loosened |

Estimate: about 75% as it stands, and about 79 to 80% if run 2 succeeds and is written up well.

Highest-leverage change: decide now how run 2's results go into Chapter 5. Write one road-session section with a fallback version, so the report is complete and within 50 pages whatever happens on Monday.

## 2. Blocking issues

1. Eleven "[Outstanding: run 2 ...]" placeholders (Sections 5.1 to 5.9, 6.2, 6.3, Chapter 7). If one is submitted as written, it reads as an unfinished draft. Prepare a fallback sentence for each now, in the form "Not obtained: the road part of run 2 (26 October) did not produce X because Y", and use it wherever Monday fails.
2. Page budget. The body is at 49 of 50 pages, before any run-2 content. Moving Figures 5.3 and 5.5 to Appendix K now frees about one page.
3. GA8 contradicts Section 3.7. Appendix A.1 calls Yusuf "a team member, who was not measured". Section 3.7 calls him "the laboratory owner, who conducts no research". Because GA8 and GA10 evidence must agree, use the Section 3.7 wording in both places, or the approved GA8 draft.
4. Wrong test count. Section 3.6.1, Appendix A.3 and Appendix J.20 say the analysis package has "42 tests". `pytest --collect-only` gives 61. Appendix A.3 uses this number as evidence of verification, so a wrong figure there undermines the point it makes.
5. Video claim with no video. GA6 (Appendix A.1) says video evidence of the road sessions is included (Appendix I). The video table is only compiled if video_links.tex exists, and it doesn't, so the PDF has no video. Either add the links or reword GA6 to say the videos are held, blurred, and available on request.
6. Ethics timing (GA10). The approval is dated 6 October, but Table 3.1 shows bench work and first battery frames from late September. Add the sentence, once the student confirms it is accurate: "Before the approval of 6 October only the equipment was developed and checked on the bench, with no people involved; all data collection for the study followed the approval." Note that Table 3.1 lists "first battery frames on the vehicle (30 September to 1 October)". That work involved no people, but the sentence must cover it accurately.
7. Checks only the student can do:
   - the declaration wording against the official form;
   - the cover-page items against the handout;
   - consistency with the signed GA form;
   - the topic and ID in the teaching team's spreadsheet.

## 3. Rubric-by-rubric improvements

### Problem statement and literature (20%)

- RQ1 (Section 1.3) asks "how accurately and repeatably". No ground truth for ride response exists, and Chapter 7 answers only for the instrument and repeatability. Either drop "accurately and" (awaiting the student's decision), or define accuracy as the instrument's accuracy (rate, loss, calibration) in one clause.
- Table 2.1's caption says "-" means "not described in the source as reviewed here (its abstract and the passages cited)". For the five systems in the table, read the full text and change the caption to "not described in the paper". This is the gap claim's main support. Pérez-González et al. [30] and Alatoom and Smadi [14] matter most.
- Section 2.7 cites ISO 15008 only through [38, 39]. Download those papers, check the 20 and 16 arc-minute figures, and record them in source-checks.md. The current wording, "as reported in", is honest; keep it.
- Table 1.1: R12's test column says "on vehicle", which is not a test identifier. Name the procedure, or write "not testable under the current approval (Section 3.7)". Do not change R12's criterion to legibility after the test; Section 1.4 claims every criterion was fixed beforehand.
- Section 1.1 is good. Its last sentence is long; split it at "and presents".

### Design and theory (20%)

- Table 4.4: the worst-case sum of 5.3 ms includes the ±2 ms "proposed criterion" for the unknown fixed offsets. State in the table that this row is the criterion, not a measurement: "Bounded by the criterion until the mallet test".
- Table 4.6, Colour row: it says "The dashboard's own status colours", but Section 6.5 and Appendix G describe dark ink on a light ground with words beside every colour. Make the row match what is deployed.
- Table 4.1 gives the Pi 4 at 19.5 frames/s and 102 ms. Elsewhere it is 14.6 frames/s and 118 to 122 ms. Both are correct but describe different conditions; add "(detector alone)" to the first pair.
- Equations 4.3 to 4.12 and the Table 4.4 arithmetic were all checked and are correct. These figures were recomputed:
  - alias attenuations of 5.8 and 9.5 dB;
  - n_p = 9;
  - 120 ppm;
  - 6.8ε and 7.8ε;
  - a slope-to-end ratio of 11.5;
  - a growth gate at τ of 12 s;
  - 5.3 ms is 1.8% of 0.3 s;
  - 20 W is 0.28% of the pack per hour, so a full pack runs down in 15 days.
- Equations eq:magnitude, eq:road-psd, eq:iv-derivation, eq:delay-speed and eq:ttc are never referenced by number. That's acceptable, but citing one or two in Chapter 6 (for example "Equation 4.9 predicts...") ties the theory to the discussion.

### Practical work (30%)

- Quantity and rigour are strong:
  - fault investigations with deciding tests (Section E.3);
  - synthetic self-tests;
  - an outage test against the database;
  - a data index with checksums.
- These tests are listed as not run: T14 on the Pis, C5, C8, and the tape parts of C9 and C11. Each one run on Sunday turns a "not measured" into a number, especially C9 (fusion distance) and C11 (time to contact).
- Section 6.7 says most results are single runs. Where a second run already exists in the logs (detector runs, sync pulse), give a range across runs in the text.
- R13 (removal time) needs only a stopwatch on Monday. Schedule it.

### Results and conclusions (20%)

- Gather every run-2 road result into one new Section 5.10, "Road session 2 (26 October)", placed before the summary table. In Sections 5.1 to 5.9, replace each placeholder with one sentence pointing to it. This:
  - matches GRT5's progression (bench first, then the vehicle);
  - keeps RQ1 and RQ4 together;
  - leaves one place to change if Monday fails.
- Chapter 7, RQ4: once the road data exist, state which feature separates road from powertrain vibration (for example "the 40 to 70 Hz band's share falls from X in powered to Y in coasting passes"), not only that the analysis exists.
- The R9 status says "partly met on the vehicle (read-back 2,000 of 2,022)". Give the reason for the missing 22 in the body; it is in Appendices K.3.1 and C. Also make clear that nothing was published from the vehicle.
- The conclusions are honest and correctly limited. Keep the "short of TRL 6" sentence.

### Presentation (10%)

- Table 3.2 (tab:methods) is never referenced in the text. Add "(Table 3.2)" to the first sentence of Section 3.8.
- Figure G (fig:ui-pages-a) is never referenced. Reference it in Section G.4.
- Overfull lines:
  - Appendix A.3, where `Planning/*-prompt.md` runs 64 pt into the margin;
  - one reference line 82 pt over (see References in the log).
- The prose is accurate but dense: long sentences joined by semicolons and colons, especially in Chapters 5 and 6. Splitting the longest sentence in each paragraph of Chapters 5 to 7 helps a second marker.

## 4. GA evidence audit

| GA | Evidence present | Add or strengthen |
|---|---|---|
| GA1 | Yes: the 200 Hz derivation, aliasing, buffer sizing, the Iv derivation, TTC, fault root causes | Nothing essential |
| GA4 | Yes: criteria fixed beforehand (Section 1.4), deciding tests (Section E.3), the run-2 design with independent ground truth and intervals | The Appendix A.1 cross-reference "comparing logging on and off (Section 4.7)" should be Section 4.3.2 and Figure 5.1. After Monday, report the ICC with its 95% interval as promised. |
| GA5 | Yes: tool limits checked (BMS checksum, ISO weighting checked against published tables) | Correct "42 tests" to 61 |
| GA6 | Partly: report, deck, poster and data index | Fix the video claim (blocking issue 5) |
| GA8 | Yes, but inconsistent | Fix the Yusuf wording; use the approved GA8 draft |
| GA9 | Yes: primary sources, gap ledger, lessons from run 1 | Nothing essential |
| GA10 | Yes: approval, conditions met, data minimisation, position removed, honest reporting | Add the pre-approval sentence (blocking issue 6). Keep "not measured" wherever true. |

## 5. Results chapter restructure

Proposed order:

1. 5.1 Inertial acquisition (R1), bench.
2. 5.2 Calibration (R2), bench, then mounted on 23 October.
3. 5.3 Ride features and fusion (R3), with the stand runs of 23 October.
4. 5.4 Position (R4).
5. 5.5 Battery (R5).
6. 5.6 Hazard sensing (R6 to R8).
7. 5.7 Telemetry and recovery (R9, R10).
8. 5.8 Display (R11, R12).
9. 5.9 Integration and power.
10. 5.10 Road session 2 (new: RQ1, RQ4, R4 speed, R10 and R13 on the vehicle).
11. 5.11 Summary table.

Figures:

| Figure | Decision | Reason |
|---|---|---|
| 5.1 | Keep | Core evidence for R1 |
| 5.2 | Keep | The only view of road session 1 |
| 5.3 | Move to Appendix K | Four panels for a result the text already states (ratio 1.06, r of 0.97) |
| 5.4 | Keep | The only RQ4 evidence so far |
| 5.5 | Move to Appendix K | Duplicates Table 5.1 |
| 5.6 | Keep | The RQ3 headline |
| New: Iv against speed per section, or CV and ICC | Add after Monday | The RQ1 answer |
| New: spectra of powered against coasting passes | Add after Monday | The RQ4 answer |

## 6. Consistency and traceability fixes

1. Appendix A.1, GA8: "Yusuf, a team member, who was not measured" should read "Yusuf, the laboratory owner, who conducted no research and was not measured".
2. Section 3.6.1, Appendix A.3 and Appendix J.20: "42 tests" should be "61 tests" (re-count before submitting).
3. Appendix A.1, GA6: "Video evidence ... is prepared" should say "is held off the repository, blurred, and available on request", unless the links are added.
4. Appendix A.1, GA4: "(Section 4.7)" should be "(Section 4.3.2, Figure 5.1)".
5. Table 4.6, Colour row: match it to Appendix G (ink on paper, a word beside every colour mark).
6. Table 4.1: add "(detector alone)" to 19.5 frames/s and 102 ms.
7. Table 4.4: add "proposed criterion, not measured" to the fixed-offsets row and to the sum.
8. Table 1.1, R12: replace "on vehicle" in the test column with a procedure or "not testable under the approval".
9. After the dashboard decision: if the larger banner is deployed, R12, Sections 5.8, 6.5 and 7, and Recommendation 6 change. If not, they stand as written.

Numbers checked against the appendices and logs, and consistent: 14,834 words; 3,464 of 10,287 rows; 2,093 of 5,557 (37.7%); 605 of 607; 112 of 112; 37.3 and 37.9 s; 1.61 per second; 0.9919 and 1.0094; 2,580 samples; 42.75, 49.0 and 64.0 Hz; 46.9 and 48.03 A.

## 7. Format and submission checklist

- [x] Cover: title (approved 23 Oct), author, supervisor and co-supervisor, purpose statement, date
- [x] Plagiarism declaration, six points, with the AI sentence in point 4 and the word count under it (14,834)
- [ ] Section order: the template puts the declaration before the abstract; check against the handout
- [x] Abstract, ToC, Introduction, Literature, Methodology, Design, Results, Discussion, Conclusions, Recommendations
- [x] IEEE references, numbered by first citation, 85 entries, all cited, none missing
- [x] GA appendix (A.1: GA1, 4, 5, 6, 8, 9, and 10 in part)
- [x] Ethics letter as its own appendix (H)
- [x] AI appendix with concrete prompts, what was submitted and what came back (A.3). It would be stronger with one short quoted excerpt of returned text next to what was kept.
- [x] Times New Roman 11 pt (XeLaTeX), single column, single spacing
- [x] Body 49 of 50 pages; keep it there after run 2
- [ ] Words: 14,834 against a 15,000 guide; run 2 text will need equal cuts
- [ ] File name: EEE4022S 2026 FINAL REPORT OKTSAM001 OKUTHE S - WINBERG.pdf
- [ ] Topic and ID confirmed in the teaching team's spreadsheet
- [ ] Presubmission uploaded by Mon 26 Oct as a fallback

## 8. Prioritised to-do

| # | Item | Class |
|---|---|---|
| 1 | Fallback sentences for all 11 placeholders, so no bracket is submitted | Must fix |
| 2 | Fix the GA8 wording about Yusuf; approve the GA8 draft | Must fix |
| 3 | Fix the "42 tests" count to 61 (three places) | Must fix |
| 4 | Fix the GA6 video claim | Must fix |
| 5 | Pre-approval ethics sentence in Section 3.7 (once confirmed) | Must fix |
| 6 | Move Figures 5.3 and 5.5 to Appendix K; create Section 5.10 for run 2 | Must fix (page budget) |
| 7 | Run C9 and C11 on Sunday; time R13 on Monday | Should fix |
| 8 | RQ1 wording decision | Should fix |
| 9 | Reference Table 3.2 and the Appendix G figure; fix the two overfull lines | Should fix |
| 10 | Table 4.4, 4.1 and 4.6 notes; R12 test column; GA4 cross-reference | Should fix |
| 11 | Read the full texts behind Table 2.1; file the ISO 15008 papers | Should fix |
| 12 | Loosen the densest sentences in Chapters 5 to 7 | Nice to have |
| 13 | One quoted AI input and output excerpt in A.3 | Nice to have |
| 14 | Upload a presubmission on 26 Oct | Must do |
