# Prompt: report clean-up pass

Written 2026-09-29. Act on it with "act on the clean-up prompt".

---

Do a clean-up pass on the SW-7 report (Tukzie-HPEC-HUD/Report/*.tex) using
Planning/report-review.md as the checklist. The goal is to remove
everything an examiner would read as carelessness, without restructuring
chapters or cutting length (length is a later pass, per the student).

1. Drafting artefacts. Remove or rewrite every note-to-self and
   out-of-register phrase: "Chapter 2/Chapter 3 as appropriate", "before
   the report claims which physical pack this section characterises",
   "the student observed", "for the report", repository paths in running
   text (move them to Appendix C), the remark about credentials and a
   language model (keep the fact that the credentials were not used, drop
   the reason given), "dissertation", and similar. Keep the abstract's
   draft note, which the student asked to keep.
2. Cross-references. Replace every hard-coded section, chapter or figure
   number with \ref to a label, adding labels where missing, and fix the
   wrong ones listed in the review (Fig 3.1 "Sec. 3.12", "Section 3.7",
   "Section 3.11" twice, "Chapter 4" methodology, "Section 3.19 above",
   "Chapter 5 (Results)", Appendix C's "Figures B.3 and 3.2 in Appendix B").
   Grep for "Section~[0-9]", "Chapter~[0-9]", "Section [0-9]", "Chapter [0-9]"
   and "Figure [0-9]" to find any others.
3. Calibration numbers. Correct them from the evidence, not from
   arithmetic alone. Evidence (session transcript, 18 Sept 2026): before
   calibration, on the bare development board, IMU1 read 10.345 to 10.388
   and IMU2 9.552 to 9.556 m/s2 at rest (12:51 to 12:54). The bare board
   later loaded stored factors 0.9773 and 0.9901, after which both read
   9.80 to 9.81 (14:34); the measurement lines of that calibration were not
   captured. Those factors imply mean magnitudes of 10.03 and 9.90 m/s2 at
   the moment of calibration, so the resting readings had changed between
   the sessions. On the target board, first boot measured means of 9.4387
   and 9.5725 m/s2, giving 1.0390 and 1.0245 (20:54). State each set with
   its board and time, say that the implied values are inferred from the
   factors, name the likely cause (the sensors were moved or re-seated
   between sessions, and a magnitude reading changes with orientation when
   per-axis errors are uncorrected) without claiming it as proven, and draw
   the consequence: recalibrate in the final mounted orientation (the
   !recal command) and consider the multi-position calibration in the test
   plan. Fix the "5 to 8%" wording: the uncalibrated readings were about 8%
   apart, 5.7% above and 2.6% below standard gravity. Apply the same
   correction wherever the numbers appear (abstract, poster, deck, logs).
4. Consistency. One sampling figure (200 Hz; state the 160 Hz minimum as
   the requirement), LTE Cat-1 not LTE-M, "high-performance embedded
   computing (HPEC)" everywhere, one department name, no contradiction on
   augmented reality, chapter numbers correct, "report" not "dissertation".
5. GA appendix (A.1). The GA form has been submitted and signed by the
   supervisor as satisfactory. Rewrite A.1 as one short paragraph per GA,
   specific to SW-7, citing report sections, consistent with what the
   student wrote on the signed form and with the supervisor's comments on
   it (GA Tracking Form/OKTSAM001 GA Tracking Form - Signed.pdf). Do not
   quote or cite the form's approval, just keep the content consistent.
   Do not claim anything the report does not show.
6. Rebuild with Tectonic, check for undefined references and errors,
   check no em dashes were introduced, recount the prose words and update
   the declaration line, update PROJECT_LOG.md and CHANGELOG.md, commit
   and push.

Rules: no em dashes, no unnecessary bold, no mention of the ethics
application or approval in the report, no invented content, every
changed number traceable to a log or the transcript.
