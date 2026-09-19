# Automated research and evidence pipeline

Keeps this project's literature base, research-gap claims and citation set
current and verifiable instead of gathered once by hand and going stale.
Design rationale is in `../Planning/automated-research-pipeline.md`.

## Running it

```
python research_pipeline.py                 # ingest + verify + regenerate outputs
python research_pipeline.py --verify        # verify stored DOIs only
python research_pipeline.py --no-fetch      # regenerate outputs from existing DB
python research_pipeline.py --limit-queries 2   # quick run
```

Only `requests` is needed beyond the standard library.

## What it produces

| File | What it is |
|---|---|
| `research.db` | SQLite store: every record with full provenance (source API, query used, retrieval timestamp, verification status) |
| `digests/digest-YYYY-MM-DD.md` | Dated run report: what's new, what threatens a gap claim, top sources per research question |
| `gap_ledger.json` | The falsifiable gap claims and their evidence ledger |
| `sw7_autoreferences.bib` | BibTeX ready to merge into `References.tex` |

## Sources

OpenAlex, arXiv and Crossref — all free, documented, and permitted for
automated use. Google Scholar is deliberately not used: no public API, active
CAPTCHA blocking, and scraping forbidden by its terms. A pipeline built on it
fails silently and takes the database's credibility down with it.

## Honest limitations — read these before trusting output

**Relevance scores are a keyword-overlap heuristic, not a semantic
judgement.** They order a reading queue. A high score is a reason to read a
paper, never a reason to cite it.

**The gap ledger does not decide anything.** It surfaces items most likely to
threaten a claim so they actually get read. Marking each as *supports*,
*challenges* or *neutral* requires a human reading the paper. A claim with no
reviewed challenges is not a defended claim — it is just an unexamined one.

**DOI verification is capped per run** (40, to stay polite to Crossref), so a
large database takes several runs to fully verify. Entries that fail are
marked `UNVERIFIED` in the BibTeX — do not cite those without checking them
yourself. On the first real run, 2 of 40 failed verification; that is exactly
the class of error this pass exists to catch.

**arXiv rate-limits.** It returns HTTP 429 if queried faster than roughly
every 3 seconds. The script paces itself accordingly and logs any query that
still fails rather than silently dropping it.

## Current state

First full run (2026-09-19): 492 sources ingested across 5 research
questions, 228 scoring high enough for the BibTeX export.

Notable: the run surfaced *"Design and Experimental Evaluation of an
Open-Architecture Multi-Sensor Telemetry System for Real-Time Motorcycle
Dynamics Acquisition"* (2026, Electronics) against gap claim G1 — close
enough prior art that G1 needs reading and probably narrowing. That is the
pipeline working as intended.
