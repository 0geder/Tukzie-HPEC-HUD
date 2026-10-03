# Automated research and evidence pipeline (SW-7)

Historical: written before the HUD was replaced by dashboard integration on 2 Oct 2026.

Written 2026-09-19. Purpose: a continuously-running system that keeps this
project's literature base, research-gap claims, component comparisons and
test-method comparisons current and defensible, instead of being gathered
once by hand and going stale.

This is written as an execution prompt. It is deliberately specific about
*how*, because the failure modes here are not effort - they are fabricated
citations, silent staleness, and a research gap that nobody has actually
tried to disprove.

---

## Design decisions that make this work rather than break

**Use real APIs, not Google Scholar scraping.** Scholar has no public API,
actively blocks automated access with CAPTCHAs, and forbids scraping in its
terms. A scraper built on it dies quietly and takes the database's
credibility with it. The same literature is reachable through APIs that are
free, documented, and allowed:

- **OpenAlex** (no key required, enormous coverage, citation counts, venues)
- **Semantic Scholar Academic Graph** (free key, citation graph, TLDRs)
- **arXiv API** (preprints, strong for robotics/sensing)
- **Crossref** (authoritative DOI metadata for verification)
- **IEEE Xplore API** (needs a key; check UCT institutional access - this
  matters because a lot of vehicle-telemetry work lives in IEEE venues)

**Every record carries provenance.** Title, authors, year, venue, DOI, URL,
abstract, the API it came from, and the retrieval timestamp. A record with
no resolvable DOI/URL is quarantined, never cited.

**Nothing enters the thesis un-verified.** Before any item is written into
`References.tex`, a verification pass re-resolves its DOI/URL and confirms
the title matches. Fabricated or drifted citations are an academic
integrity failure, not a formatting bug - this pass is the point of the
whole system, not an optional extra.

---

## Execution prompt

> Build an automated research and evidence pipeline for the SW-7 project
> (embedded HPEC telemetry unit and windshield HUD for the TUKZIE Rev 0
> three-wheeled electric vehicle). It runs on a schedule, updates a local
> database, and produces artifacts that feed the thesis directly.
>
> **1. Ingestion.** Query OpenAlex, Semantic Scholar, arXiv and Crossref on
> a fixed query set covering this project's actual scope: whole-body
> vibration and ride characterisation (ISO 2631), three-wheeler /
> auto-rickshaw dynamics, embedded vehicle telemetry over cellular, MQTT
> for vehicular IoT, IMU calibration and sensor fusion for vehicle
> dynamics, monocular camera hazard detection on edge hardware, automotive
> HUD design and driver attention, and BMS telemetry protocols. Store
> results in SQLite with full provenance and deduplicate by DOI, then by
> normalised title. Record which query produced each hit.
>
> **2. Relevance triage.** For each new record, score relevance against
> each of the project's research questions, with a written one-line
> rationale per score, not a bare number. Anything scoring high goes into a
> review queue; the rest stays searchable but out of the way.
>
> **3. Falsifiable gap ledger.** Maintain the project's research-gap
> claims as explicit, individually-stated propositions (e.g. "no existing
> published system combines synchronised dual-IMU ride characterisation
> with cellular telemetry on a three-wheeled cargo vehicle"). Every claim
> has an evidence ledger of records marked *supports*, *challenges*, or
> *neutral*, each with a note. When a newly-ingested record challenges a
> claim, flag it loudly in the next report. The goal is a gap that has
> survived active attempts to disprove it - that is what makes it
> defensible under examination, rather than a gap asserted once and never
> revisited.
>
> **4. Component comparison matrix.** A maintained table of candidate and
> in-use components (IMUs, air-quality sensors, transparent OLED/HUD
> options, optocouplers, cameras, ToF alternatives), with columns for
> key specs, real current price, real current stock at the project's
> approved vendors, and a sourced justification for the chosen option.
> Every cell that states a fact carries a source URL and a checked-on
> date. Prices and stock go stale fast - re-check on each scheduled run
> and mark changes.
>
> **5. Test-method comparison matrix.** The same treatment for
> methodology: how comparable published work actually measures ride
> quality, validates IMU calibration, quantifies telemetry latency, and
> evaluates hazard detection - with the specific metrics, sample rates,
> and experimental designs they used, cited. This is what lets the report
> justify its own experimental design by reference to established practice
> instead of inventing one and hoping.
>
> **6. Verification pass.** Before anything is exported to the thesis,
> re-resolve every DOI/URL and confirm the metadata still matches. Any
> record that fails is quarantined and reported, never silently cited.
>
> **7. Outputs, regenerated each run.** A dated digest of what is new and
> what changed; the gap ledger with any newly-challenged claims at the
> top; the two comparison matrices; and a BibTeX file ready to merge into
> `References.tex`. Outputs are written as files in the repo so their
> history is tracked in git.
>
> **8. Scheduling.** Run on a schedule (weekly is enough for literature;
> component price/stock checks can run more often). Each run appends to
> the digest history rather than overwriting it, so the research trail
> itself is auditable.
>
> **Hard rules.** Never invent a citation, a price, a stock status, or a
> quote. If a source cannot be verified, say so explicitly in the output
> rather than filling the gap with something plausible. Distinguish
> everywhere between what a source actually claims and what this project
> infers from it.

---

## Why this is worth the build rather than just searching manually

- A research gap that has been actively attacked and survived is a
  materially stronger claim than one asserted from a single search, and
  this is exactly the thing an examiner probes.
- Component and test-method choices become *justified* rather than
  *asserted*, with the comparison evidence already assembled.
- The literature base stops decaying between the day it was gathered and
  the day the report is submitted.
- The digest history is itself evidence of systematic, ongoing
  investigation - directly relevant to GA4 and GA9.

## Sequencing note

This pipeline strengthens the *written* argument around the work. It does
not produce ride data. The Results, Discussion and Conclusions chapters
remain gated on the real vehicle field test, and no amount of literature
automation substitutes for that - the two efforts should run in parallel,
not one instead of the other.
