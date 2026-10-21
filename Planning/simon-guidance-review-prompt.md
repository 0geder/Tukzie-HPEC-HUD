# Prompt: check the SW-7 report against Prof. Winberg's guidance and example theses

Written 21 Oct 2026. Run read-only: the reviewer changes no file. Findings come back as a report; edits are decided afterwards.

## Inputs

Guidance and examples (folder `Projects/SimonsResources/`). Plain-text copies, split by page as `=== [page N] ===`, are in the session scratchpad `simons/`:
- GRT1 Welcome, GRT2 LitReview, GRT3 Research Methodology (M), GRT4 Design, GRT5 Experiment Refinement and Results, GRT6 Intro and Writeup (lecture slides).
- Example_BSc_Theses: McIntosh (2024), Vattakunnel (2025), Maketekete (2025), Magavha (2025), Halday (2025).

The report:
- Source: `Tukzie-HPEC-HUD/Report/*.tex` (main file `Project Report Template.tex`; chapters Introduction, Literature, Methodology, Results, Discussion, Conclusions, Recommendations; appendices a to h).
- Compiled text by PDF page: `simons/SW7_report_current.txt` (116 PDF pages; body chapters run from about PDF page 12 to 60).
- Known facts that are not errors: the HUD was replaced by dashboard integration with the supervisor's agreement; the final layout has the Raspberry Pi 5 camera at the front and the Raspberry Pi 4 camera at the rear; the first bench versions had the Pi 4 at the front, which may be described as history if labelled so.

## Rules (no hallucination)

1. Every guidance item must quote the source verbatim, with file and page: `GRT3 p12: "..."`. If a slide is only a heading or picture and its meaning is unclear, say "unclear" and do not interpret it.
2. Keep three kinds of statement apart and label each:
   - GUIDANCE: what the lectures say.
   - PRACTICE: what the example theses do, with which thesis and page.
   - OPINION: the reviewer's judgement. Use it sparingly and mark it.
3. Every judgement about the report cites where: `.tex` file and line, or PDF page from `SW7_report_current.txt`.
4. Do not use outside knowledge of UCT, ECSA or general thesis advice as if it came from the lectures. If something expected is absent from the lectures, say "not covered in the lectures".
5. If a rule cannot be checked from the files, write "cannot check" and why. Never fill a gap with a guess.
6. Count what can be counted (pages, words, figures, references, chapters) with a script, and report the number and how it was counted.
7. Write in plain words, no em dashes, no unnecessary bold.

## Tasks

A. Lectures. From GRT1 to GRT6, list every concrete instruction about the report and the project: structure, chapter content, length, literature review, research questions and hypotheses, methodology, design, experiments and results, discussion, conclusions, writing style, figures, referencing, appendices, GAs, ethics, AI use, deadlines and presentation. For each, give the verbatim quote and page, then check the report: MEETS / PARTLY / DOES NOT MEET / CANNOT CHECK, with the evidence and, for anything short of MEETS, the smallest change that would meet it.

B. Example theses. Measure, for each of the five and for SW-7: page count of the body, chapter list and order, words or pages per chapter, number of figures, tables and references, how research questions or objectives are stated, how the literature review ends (gap, summary), how results are presented (tables, plots, statistics), how the discussion links back to the literature, and what appendices they carry. Then state where SW-7 differs from the common practice of the five, and whether the difference matters against the lecture guidance. Do not judge the quality of the example theses.

C. Camera layout consistency. Find every sentence, caption, table and figure reference in the report about where a camera or detector is, or what it faces. The final layout is: Raspberry Pi 5 beside the display, front camera and front ToF board; Raspberry Pi 4 beside the battery, rear camera, rear ToF board, the telemetry unit and the sync pulse. Flag any statement that says or implies a single camera, a front camera on the Pi 4, or the Pi 4 as the only detector, unless it is clearly labelled as an earlier bench stage. Give file, line, the current text and replacement text.

## Output

1. Lecture checklist table (task A), grouped by lecture.
2. Example-thesis comparison table and the differences that matter (task B).
3. Camera consistency list with replacement text (task C).
4. The ten changes with the most effect on the mark, each tied to a GUIDANCE quote, most important first, and whether each is wording only or needs new work.
