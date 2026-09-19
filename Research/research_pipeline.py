"""
SW-7 automated research and evidence pipeline.

Queries open scholarly APIs on this project's actual scope, stores results
with full provenance in SQLite, deduplicates, triages by relevance, tracks
research-gap claims as falsifiable propositions with an evidence ledger,
and emits a dated digest plus a BibTeX file for the thesis.

Sources used (all free, documented, and permitted for automated access):
  - OpenAlex      https://api.openalex.org      (no key required)
  - arXiv         http://export.arxiv.org/api   (no key required)
  - Crossref      https://api.crossref.org      (used for DOI verification)

Deliberately NOT Google Scholar: it has no public API, blocks automated
access with CAPTCHAs, and forbids scraping in its terms. A pipeline built
on it fails silently and takes the database's credibility with it. The
sources above cover substantially the same literature with proper,
verifiable DOI metadata.

Usage:
    python research_pipeline.py              # full run: ingest + digest
    python research_pipeline.py --verify     # re-verify stored DOIs only
    python research_pipeline.py --no-fetch   # regenerate outputs from DB
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).parent
DB_PATH = HERE / "research.db"
DIGEST_DIR = HERE / "digests"
BIBTEX_PATH = HERE / "sw7_autoreferences.bib"
GAP_LEDGER_PATH = HERE / "gap_ledger.json"

# OpenAlex offers a faster "polite pool" if you identify yourself with an
# email in the request. No email is sent by default - add your own here
# only if you want that, it is not required for the API to work.
OPENALEX_MAILTO = None

REQUEST_TIMEOUT = 30
SLEEP_AFTER_OPENALEX = 1.0
# arXiv asks for roughly 3s between calls and returns HTTP 429 if you push
# harder - a 1s gap lost results to rate limiting on a real run.
SLEEP_AFTER_ARXIV = 3.5


# ---------------------------------------------------------------------------
# Project scope: research questions and the queries that serve each
# ---------------------------------------------------------------------------

RESEARCH_QUESTIONS = {
    "RQ1": {
        "title": "Vehicle dynamic response characterisation from onboard inertial sensing",
        "keywords": ["vibration", "accelerometer", "imu", "ride", "iso 2631",
                     "whole-body vibration", "road roughness", "vehicle dynamics",
                     "suspension", "rms acceleration"],
        "queries": [
            "whole body vibration ISO 2631 vehicle ride comfort measurement",
            "road roughness estimation smartphone accelerometer vehicle",
            "IMU based vehicle ride quality characterisation",
            "three wheeler auto rickshaw vibration dynamics",
        ],
    },
    "RQ2": {
        "title": "Embedded telemetry architecture and cellular uplink for low-cost vehicles",
        "keywords": ["telemetry", "mqtt", "cellular", "lte", "iot", "embedded",
                     "real-time", "freertos", "gateway", "edge"],
        "queries": [
            "MQTT vehicular telemetry cellular IoT embedded system",
            "low cost vehicle telematics system design developing countries",
            "real time embedded data acquisition FreeRTOS sensor fusion vehicle",
        ],
    },
    "RQ3": {
        "title": "Camera-based hazard awareness on constrained edge hardware",
        "keywords": ["object detection", "monocular", "edge", "embedded vision",
                     "raspberry pi", "tflite", "hazard", "adas", "collision"],
        "queries": [
            "monocular camera hazard detection embedded edge device vehicle",
            "lightweight object detection Raspberry Pi ADAS real time",
            "monocular distance estimation vehicle camera pinhole",
        ],
    },
    "RQ4": {
        "title": "Heads-up display design and driver attention",
        "keywords": ["head-up display", "hud", "driver attention", "windshield",
                     "augmented reality", "glance", "workload"],
        "queries": [
            "automotive head-up display driver attention workload evaluation",
            "windshield HUD design human factors driving",
        ],
    },
    "RQ5": {
        "title": "Battery management telemetry and safety for light electric vehicles",
        "keywords": ["bms", "battery management", "state of charge", "lithium",
                     "electric vehicle", "telemetry", "cell balancing"],
        "queries": [
            "battery management system telemetry electric vehicle monitoring",
            "state of charge estimation light electric vehicle BMS data",
        ],
    },
}

# Gap claims are stated as propositions that can be challenged by evidence.
# A gap that has survived attempts to disprove it is defensible; one that was
# asserted once and never revisited is not.
DEFAULT_GAP_CLAIMS = [
    {
        "id": "G1",
        "claim": "No published system combines synchronised dual-IMU ride "
                 "characterisation with cellular telemetry on a three-wheeled "
                 "cargo/passenger electric vehicle.",
        "related_rqs": ["RQ1", "RQ2"],
    },
    {
        "id": "G2",
        "claim": "Camera-based hazard awareness has not been integrated with "
                 "vehicle-dynamics telemetry on auto-rickshaw-class vehicles in "
                 "the published or open-source literature.",
        "related_rqs": ["RQ1", "RQ3"],
    },
    {
        "id": "G3",
        "claim": "Existing low-cost vehicle telematics work does not address "
                 "local buffering and recovery of telemetry when the cellular "
                 "uplink is intermittent, which is the normal condition in the "
                 "target deployment environment.",
        "related_rqs": ["RQ2"],
    },
]


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    doi TEXT,
    title TEXT NOT NULL,
    title_norm TEXT NOT NULL,
    authors TEXT,
    year INTEGER,
    venue TEXT,
    url TEXT,
    abstract TEXT,
    source_api TEXT NOT NULL,
    query_used TEXT,
    cited_by INTEGER,
    retrieved_at TEXT NOT NULL,
    verified_at TEXT,
    verify_status TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_title_norm ON sources(title_norm);
CREATE INDEX IF NOT EXISTS idx_doi ON sources(doi);

CREATE TABLE IF NOT EXISTS relevance (
    source_id INTEGER NOT NULL,
    rq_id TEXT NOT NULL,
    score REAL NOT NULL,
    rationale TEXT NOT NULL,
    assessed_at TEXT NOT NULL,
    PRIMARY KEY (source_id, rq_id)
);

CREATE TABLE IF NOT EXISTS run_log (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    new_sources INTEGER DEFAULT 0,
    queries_run INTEGER DEFAULT 0,
    notes TEXT
);
"""


def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def norm_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = doi.strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d or None


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------

def fetch_openalex(query: str, per_page: int = 25) -> list[dict]:
    params = {"search": query, "per-page": per_page,
              "select": "id,doi,title,publication_year,authorships,"
                        "primary_location,cited_by_count,abstract_inverted_index"}
    if OPENALEX_MAILTO:
        params["mailto"] = OPENALEX_MAILTO
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        print(f"  [openalex] FAILED  {query!r}: {exc}")
        return []

    out = []
    for w in data.get("results", []):
        authors = ", ".join(
            a.get("author", {}).get("display_name", "")
            for a in (w.get("authorships") or [])[:6]
        ).strip(", ")
        venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
        # OpenAlex stores abstracts as an inverted index; reconstruct it.
        abstract = None
        inv = w.get("abstract_inverted_index")
        if inv:
            positions: list[tuple[int, str]] = []
            for word, idxs in inv.items():
                positions.extend((i, word) for i in idxs)
            abstract = " ".join(w for _, w in sorted(positions))[:4000]
        out.append({
            "doi": norm_doi(w.get("doi")),
            "title": (w.get("title") or "").strip(),
            "authors": authors or None,
            "year": w.get("publication_year"),
            "venue": venue,
            "url": w.get("doi") or w.get("id"),
            "abstract": abstract,
            "cited_by": w.get("cited_by_count"),
            "source_api": "openalex",
            "query_used": query,
        })
    return out


ARXIV_NS = {"a": "http://www.w3.org/2005/Atom"}


def fetch_arxiv(query: str, max_results: int = 15) -> list[dict]:
    params = {"search_query": f"all:{query}", "start": 0,
              "max_results": max_results, "sortBy": "relevance"}
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        root = ET.fromstring(r.text)
    except Exception as exc:
        print(f"  [arxiv]    FAILED  {query!r}: {exc}")
        return []

    out = []
    for entry in root.findall("a:entry", ARXIV_NS):
        title = (entry.findtext("a:title", "", ARXIV_NS) or "").strip()
        summary = (entry.findtext("a:summary", "", ARXIV_NS) or "").strip()
        published = entry.findtext("a:published", "", ARXIV_NS) or ""
        link = entry.findtext("a:id", "", ARXIV_NS)
        authors = ", ".join(
            (a.findtext("a:name", "", ARXIV_NS) or "")
            for a in entry.findall("a:author", ARXIV_NS)[:6]
        )
        doi = entry.findtext("{http://arxiv.org/schemas/atom}doi")
        year = None
        if published[:4].isdigit():
            year = int(published[:4])
        out.append({
            "doi": norm_doi(doi),
            "title": re.sub(r"\s+", " ", title),
            "authors": authors or None,
            "year": year,
            "venue": "arXiv (preprint)",
            "url": link,
            "abstract": re.sub(r"\s+", " ", summary)[:4000],
            "cited_by": None,
            "source_api": "arxiv",
            "query_used": query,
        })
    return out


# ---------------------------------------------------------------------------
# Relevance triage
#
# This is a transparent keyword-overlap heuristic, NOT a semantic judgement.
# It exists to order a review queue so a human (or a language model in a
# separate, explicit step) reads the most likely-relevant items first. A high
# score is a reason to look, never a reason to cite.
# ---------------------------------------------------------------------------

def score_relevance(rec: dict, rq_id: str, rq: dict) -> tuple[float, str]:
    haystack = f"{rec.get('title','')} {rec.get('abstract','') or ''}".lower()
    hits = [k for k in rq["keywords"] if k in haystack]
    if not hits:
        return 0.0, "no scope keywords matched"
    score = min(len(hits) / max(len(rq["keywords"]) * 0.4, 1), 1.0)
    title_hits = [k for k in hits if k in (rec.get("title") or "").lower()]
    if title_hits:
        score = min(score + 0.15, 1.0)
    rationale = f"matched {len(hits)} scope terms ({', '.join(hits[:5])})"
    if title_hits:
        rationale += f"; in title: {', '.join(title_hits[:3])}"
    return round(score, 3), rationale


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def store_records(conn: sqlite3.Connection, records: list[dict]) -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new_count = 0
    for rec in records:
        if not rec.get("title"):
            continue
        tnorm = norm_title(rec["title"])
        if not tnorm:
            continue
        existing = conn.execute(
            "SELECT id FROM sources WHERE title_norm = ? OR (doi IS NOT NULL AND doi = ?)",
            (tnorm, rec.get("doi")),
        ).fetchone()
        if existing:
            continue
        cur = conn.execute(
            """INSERT INTO sources (doi,title,title_norm,authors,year,venue,url,
                                    abstract,source_api,query_used,cited_by,retrieved_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rec.get("doi"), rec["title"], tnorm, rec.get("authors"), rec.get("year"),
             rec.get("venue"), rec.get("url"), rec.get("abstract"), rec["source_api"],
             rec.get("query_used"), rec.get("cited_by"), now),
        )
        sid = cur.lastrowid
        new_count += 1
        for rq_id, rq in RESEARCH_QUESTIONS.items():
            score, rationale = score_relevance(rec, rq_id, rq)
            if score > 0:
                conn.execute(
                    """INSERT OR REPLACE INTO relevance
                       (source_id,rq_id,score,rationale,assessed_at) VALUES (?,?,?,?,?)""",
                    (sid, rq_id, score, rationale, now),
                )
    conn.commit()
    return new_count


# ---------------------------------------------------------------------------
# DOI verification - nothing reaches the thesis unverified
# ---------------------------------------------------------------------------

def verify_dois(conn: sqlite3.Connection, limit: int = 40) -> dict:
    rows = conn.execute(
        """SELECT id, doi, title FROM sources
           WHERE doi IS NOT NULL AND verified_at IS NULL LIMIT ?""", (limit,)
    ).fetchall()
    stats = {"checked": 0, "ok": 0, "mismatch": 0, "unresolved": 0}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for row in rows:
        stats["checked"] += 1
        status = "unresolved"
        try:
            r = requests.get(f"https://api.crossref.org/works/{row['doi']}",
                             timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                titles = r.json().get("message", {}).get("title") or []
                if titles and norm_title(titles[0])[:60] == norm_title(row["title"])[:60]:
                    status = "ok"
                elif titles:
                    status = "title-mismatch"
                else:
                    status = "resolved-no-title"
        except Exception:
            status = "unresolved"
        if status == "ok":
            stats["ok"] += 1
        elif status == "title-mismatch":
            stats["mismatch"] += 1
        else:
            stats["unresolved"] += 1
        conn.execute("UPDATE sources SET verified_at=?, verify_status=? WHERE id=?",
                     (now, status, row["id"]))
        time.sleep(0.3)
    conn.commit()
    return stats


# ---------------------------------------------------------------------------
# Gap ledger
# ---------------------------------------------------------------------------

def load_gap_ledger() -> dict:
    if GAP_LEDGER_PATH.exists():
        try:
            return json.loads(GAP_LEDGER_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"claims": DEFAULT_GAP_CLAIMS, "evidence": []}


def save_gap_ledger(ledger: dict) -> None:
    GAP_LEDGER_PATH.write_text(json.dumps(ledger, indent=2), encoding="utf-8")


def flag_challenges(conn: sqlite3.Connection, ledger: dict) -> list[dict]:
    """Surface newly-ingested high-relevance items against each gap claim.

    This does NOT decide whether a claim is disproved - it cannot, that needs
    a human reading the paper. It surfaces the items most likely to threaten
    a claim so they actually get read, instead of a gap going unchallenged
    by default.
    """
    flags = []
    seen = {(e["claim_id"], e["source_id"]) for e in ledger.get("evidence", [])}
    for claim in ledger["claims"]:
        rqs = claim.get("related_rqs", [])
        if not rqs:
            continue
        # A gap claim of the form "nobody has combined X and Y" is only
        # threatened by work that addresses X *and* Y. Matching on any single
        # research question floods the claim with irrelevant hits - e.g. a
        # ride-comfort paper appearing to challenge a claim about camera and
        # telemetry integration. So when a claim spans multiple RQs, require
        # the source to score on at least two of them.
        placeholders = ",".join("?" * len(rqs))
        min_rq_coverage = 2 if len(rqs) >= 2 else 1
        rows = conn.execute(
            f"""SELECT s.id, s.title, s.year, s.url, s.venue,
                       AVG(r.score) AS avg_score, COUNT(DISTINCT r.rq_id) AS rq_hits
                FROM sources s JOIN relevance r ON r.source_id = s.id
                WHERE r.rq_id IN ({placeholders}) AND r.score >= 0.5
                GROUP BY s.id
                HAVING rq_hits >= ?
                ORDER BY rq_hits DESC, avg_score DESC, s.year DESC LIMIT 5""",
            (*rqs, min_rq_coverage),
        ).fetchall()
        for row in rows:
            if (claim["id"], row["id"]) in seen:
                continue
            flags.append({
                "claim_id": claim["id"], "claim": claim["claim"],
                "source_id": row["id"], "title": row["title"],
                "year": row["year"], "url": row["url"], "venue": row["venue"],
                "avg_score": round(row["avg_score"], 3),
            })
            ledger.setdefault("evidence", []).append({
                "claim_id": claim["id"], "source_id": row["id"],
                "stance": "unreviewed",
                "note": "auto-surfaced as potentially relevant; needs human review",
                "flagged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
    return flags


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

def bibtex_key(row: sqlite3.Row) -> str:
    first_author = (row["authors"] or "anon").split(",")[0].split()[-1:] or ["anon"]
    word = re.sub(r"[^a-zA-Z]", "", (row["title"] or "x").split()[0] or "x")
    return f"{first_author[0].lower()}{row['year'] or 'nd'}{word.lower()[:8]}"


def write_bibtex(conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        """SELECT s.* FROM sources s JOIN relevance r ON r.source_id = s.id
           WHERE r.score >= 0.5 GROUP BY s.id ORDER BY s.year DESC"""
    ).fetchall()
    seen_keys: set[str] = set()
    lines = ["% Auto-generated by research_pipeline.py - DO NOT EDIT BY HAND.",
             "% Every entry below came from a real API response with provenance",
             "% recorded in research.db. Entries whose DOI failed verification are",
             "% marked; do not cite those without checking them yourself.", ""]
    for row in rows:
        key = bibtex_key(row)
        base, n = key, 2
        while key in seen_keys:
            key = f"{base}{n}"; n += 1
        seen_keys.add(key)
        entry_type = "misc" if (row["venue"] or "").startswith("arXiv") else "article"
        lines.append(f"@{entry_type}{{{key},")
        lines.append(f"  title  = {{{row['title']}}},")
        if row["authors"]:
            lines.append(f"  author = {{{row['authors']}}},")
        if row["year"]:
            lines.append(f"  year   = {{{row['year']}}},")
        if row["venue"]:
            lines.append(f"  journal= {{{row['venue']}}},")
        if row["doi"]:
            lines.append(f"  doi    = {{{row['doi']}}},")
        if row["url"]:
            lines.append(f"  url    = {{{row['url']}}},")
        if row["verify_status"] and row["verify_status"] != "ok":
            lines.append(f"  note   = {{UNVERIFIED: {row['verify_status']}}},")
        lines.append("}")
        lines.append("")
    BIBTEX_PATH.write_text("\n".join(lines), encoding="utf-8")
    return len(rows)


def write_digest(conn: sqlite3.Connection, new_count: int, flags: list[dict],
                 verify_stats: dict | None) -> Path:
    DIGEST_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    path = DIGEST_DIR / f"digest-{stamp}.md"

    total = conn.execute("SELECT COUNT(*) c FROM sources").fetchone()["c"]
    lines = [f"# Research digest - {stamp}", "",
             f"- New sources this run: **{new_count}**",
             f"- Total sources in database: **{total}**"]
    if verify_stats:
        lines.append(f"- DOI verification: {verify_stats['ok']} ok, "
                     f"{verify_stats['mismatch']} title-mismatch, "
                     f"{verify_stats['unresolved']} unresolved "
                     f"(of {verify_stats['checked']} checked)")
    lines += ["", "Relevance scores below are a transparent keyword-overlap heuristic "
                  "for ordering a reading queue. They are not a semantic judgement, "
                  "and a high score is a reason to read a paper, never a reason to "
                  "cite it.", ""]

    if flags:
        lines += ["## Items to read against the gap claims", "",
                  "These were auto-surfaced because they score highly on the research "
                  "questions a claim depends on. Read them and mark each as *supports*, "
                  "*challenges* or *neutral* in `gap_ledger.json`. A gap claim with no "
                  "reviewed challenges is not yet a defended claim.", ""]
        by_claim: dict[str, list[dict]] = {}
        for f in flags:
            by_claim.setdefault(f["claim_id"], []).append(f)
        for cid, items in by_claim.items():
            lines.append(f"### {cid}: {items[0]['claim']}")
            lines.append("")
            for it in items:
                yr = it["year"] or "n.d."
                lines.append(f"- **{it['title']}** ({yr}, {it['venue'] or 'n/a'}) "
                             f"— score {it['avg_score']} — {it['url']}")
            lines.append("")
    else:
        lines += ["## Gap claims", "",
                  "No new high-relevance items surfaced against the current claims "
                  "this run.", ""]

    lines += ["## Top-scoring sources per research question", ""]
    for rq_id, rq in RESEARCH_QUESTIONS.items():
        rows = conn.execute(
            """SELECT s.title, s.year, s.venue, s.url, s.cited_by, r.score, r.rationale
               FROM sources s JOIN relevance r ON r.source_id = s.id
               WHERE r.rq_id = ? ORDER BY r.score DESC, s.cited_by DESC NULLS LAST
               LIMIT 6""", (rq_id,)
        ).fetchall()
        lines.append(f"### {rq_id} — {rq['title']}")
        lines.append("")
        if not rows:
            lines.append("_No matching sources yet._")
        for row in rows:
            cites = f", cited {row['cited_by']}x" if row["cited_by"] else ""
            lines.append(f"- **{row['title']}** ({row['year'] or 'n.d.'}"
                         f"{cites}) — score {row['score']} — _{row['rationale']}_")
            lines.append(f"  {row['url']}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true", help="regenerate outputs only")
    ap.add_argument("--verify", action="store_true", help="run DOI verification only")
    ap.add_argument("--limit-queries", type=int, default=0,
                    help="cap number of queries (for a quick run)")
    args = ap.parse_args()

    conn = db_connect()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run = conn.execute("INSERT INTO run_log (started_at) VALUES (?)", (started,))
    run_id = run.lastrowid
    conn.commit()

    new_count, queries_run = 0, 0
    verify_stats = None

    if args.verify:
        print("Verifying stored DOIs against Crossref...")
        verify_stats = verify_dois(conn)
        print(f"  {verify_stats}")
    elif not args.no_fetch:
        all_queries = [(rq_id, q) for rq_id, rq in RESEARCH_QUESTIONS.items()
                       for q in rq["queries"]]
        if args.limit_queries:
            all_queries = all_queries[:args.limit_queries]
        for rq_id, query in all_queries:
            print(f"[{rq_id}] {query}")
            recs = fetch_openalex(query)
            print(f"  openalex: {len(recs)} results")
            time.sleep(SLEEP_AFTER_OPENALEX)
            arx = fetch_arxiv(query)
            print(f"  arxiv:    {len(arx)} results")
            time.sleep(SLEEP_AFTER_ARXIV)
            added = store_records(conn, recs + arx)
            new_count += added
            queries_run += 1
            print(f"  -> {added} new")
        print("\nVerifying a batch of DOIs against Crossref...")
        verify_stats = verify_dois(conn)
        print(f"  {verify_stats}")

    ledger = load_gap_ledger()
    flags = flag_challenges(conn, ledger)
    save_gap_ledger(ledger)

    n_bib = write_bibtex(conn)
    digest = write_digest(conn, new_count, flags, verify_stats)

    conn.execute(
        "UPDATE run_log SET finished_at=?, new_sources=?, queries_run=? WHERE id=?",
        (datetime.now(timezone.utc).isoformat(timespec="seconds"),
         new_count, queries_run, run_id))
    conn.commit()

    print(f"\nNew sources:      {new_count}")
    print(f"Gap-claim flags:  {len(flags)}")
    print(f"BibTeX entries:   {n_bib} -> {BIBTEX_PATH.name}")
    print(f"Digest:           {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
