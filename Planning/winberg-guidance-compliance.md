# SW-7 report against Prof. Winberg's guidance (GRT1 to GRT6) and the example theses

Checked 21 Oct 2026 with the prompt in `Planning/simon-guidance-review-prompt.md`. Sources: `Projects/SimonsResources/` (six GRT lecture decks, five example BSc theses from 2024 and 2025). Quotes are verbatim, with the lecture and page.

## Added to the report on 21 Oct

| Guidance | What the report now has |
|---|---|
| GRT1 p37, GRT3 p24: Methodology and Design are separate ("put all the design details into the Design chapter") | Chapter 3 Methodology (`Method.tex`, `chap:method`) and Chapter 4 Design (`Methodology.tex`, `chap:design`) |
| GRT3 p7, p12: phases, overview diagram, "We recommend considering the V-Model" | V-model figure (`fig:vmodel`), phases-as-run table (`tab:phases`) with dates |
| GRT3 p28, p29: data collection, data analysis | `sec:data-collection`, `sec:data-analysis` |
| GRT3 p34: site selection; reminder of the previous chapter; preparing for the next | `sec:site-selection`; opening from the Chapter 2 gap; closing paragraphs |
| GRT3 p34, p35: methods summary table (RQ, site, data collection, analysis, appendix) | `tab:methods` |
| GRT4 p11, p12: design overview, link to requirements, "Maintenance Design" | Design overview, R and RQ tags per section, `sec:maintenance` |
| GRT5 p18: "Be generous with the visuals"; GRT5 p13 graphs | Four results plots from recorded data: `fig:res-imu-gaps`, `fig:res-latency`, `fig:res-road`, `fig:res-t15` |
| GRT5 p24: results overview referring back to the methodology | Opening paragraph of Results |
| GRT2 p24: structure of the review, tool options with pros and cons, an elegant close | Structure paragraph, `sec:lit-platforms`, closing summary of methods carried forward |
| GRT5 p11: "Use some diagrams too in the lit review!!" | `fig:lit-map` (themes onto RQ1 to RQ4) |
| GRT6 p12: "State objective", "Important Terminology" | Objective sentence; `sec:terms` with `tab:terms` |
| GRT1 p26: Gantt chart "useful for inclusion into writeup" | `fig:timeline` in Appendix E |
| GRT5 p14: "Leave no figure unmentioned!!" | The six wiring tables referenced in Appendix D |
| GRT1 p32 ELO10: ethics | `sec:ethics` and the approval letter as Appendix H |
| Photographic evidence of the vehicle work | Appendix I (`app:road1`): pod, system on the vehicle, dashboard; video list. Faces and the number plate blurred or cropped |

## Still open

1. 19 `\outstanding{}` markers (GRT5 p21: "Might not have time to show sufficient results"). Fill from the second road session or rewrite as stated limitations.
2. Glance test for R12 and RQ2 (needs a driver and the supervisor's confirmation under the ethics approval). A no-participant design check against the legibility figures is possible now.
3. Venue, route and people present for the 19 Oct session (`sec:field-test-design`).
4. Final file name, GRT1 p41: "Final Report – Samson Okuthe (OKTSAM001).pdf".

## Length (to do next)

- GRT1 p38: "50 pages is OK, 80-100 verging on too much. (excl. Appendices)". GRT1 p40: "try not to exceed 40 pages in the main body", "18,000 words for a 40 credit BSc project is adequate", "Reports should be a Maximum 30,000 words".
- After the additions: body about 65 pages, 23,012 words text only (`Report/wordcount.py`). The course handout's 50-page limit is the binding one.
- Plan: move Design detail (fault investigations, detailed tables, long subsystem text) to the appendices.

## Example theses (for comparison)

Median of the five: 66 body pages, about 15,400 words, literature review 11 pages (17 %), 25 body figures and 9 tables, 48 references, appendices 9 pages. SW-7 before the additions: 49 pages, 6 body figures, 1 in Results, literature review 5 pages, 60 references.
