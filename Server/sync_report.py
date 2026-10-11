"""SW-7 sync report: how complete and how fast the central database is.

Reads the SQLite database written by sw7_ingest.py and, optionally, a copy of
the telemetry unit's own log saved with BenchTest/log_dump.py (!log dump), and
reports:

  - records stored per device and boot, the seq range, and every missing seq
    (gaps inside a boot; the jump in seq between boots is not a gap);
  - duplicates received (replays or redeliveries of records already stored);
  - replayed records, grouped into replay episodes (one per outage), with how
    long each backlog took to drain and at what rate;
  - end-to-end latency, server receive time minus device UTC (only for records
    whose device time is known, i.e. after a GNSS fix), median, 95th
    percentile and maximum, separately for live and replayed records;
  - with a log copy: records generated (in the log) against records stored,
    which also catches records missing at the start or end of a boot.

Output: text on stdout and, with --csv PREFIX, PREFIX_summary.csv,
PREFIX_boots.csv, PREFIX_latency.csv and PREFIX_replay.csv for the report.

Usage:
  python Server/sync_report.py [--db Server/sw7_telemetry.db] [--log dump.jsonl]
        [--dev NAME] [--boot N ...] [--since 2026-10-12T09:00] [--until ...]
        [--csv BenchTest/logs/2026-10-12_sync] [--check] [--max-p95-ms 5000]
With --check the exit code is 1 if any seq is missing or the live latency
95th percentile is above --max-p95-ms (default 5000), else 0.
Standard library only.
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "sw7_telemetry.db")
REPLAY_EPISODE_GAP_MS = 60_000   # replayed records more than 60 s apart start a new episode
RECORD_PERIOD_MS = 10_000        # firmware MQTT_PUBLISH_INTERVAL_MS


def percentile(values, p):
    """Nearest-rank percentile (p in 0..100) of a non-empty list; None if empty."""
    if not values:
        return None
    v = sorted(values)
    k = max(1, -(-len(v) * p // 100))   # ceil(n * p / 100), at least 1
    return v[int(k) - 1]


def median(values):
    if not values:
        return None
    v = sorted(values)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def ranges(seqs):
    """[1,2,3,7,9,10] -> [(1,3),(7,7),(9,10)]"""
    out = []
    for s in sorted(seqs):
        if out and s == out[-1][1] + 1:
            out[-1][1] = s
        else:
            out.append([s, s])
    return [tuple(r) for r in out]


def fmt_ranges(rs, limit=12):
    parts = [f"{a}" if a == b else f"{a}-{b}" for a, b in rs[:limit]]
    if len(rs) > limit:
        parts.append(f"... ({len(rs) - limit} more ranges)")
    return ", ".join(parts) if parts else "none"


def parse_time_ms(text):
    """ISO date-time to Unix ms; a time without a zone is local time."""
    t = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.astimezone()
    return int(t.timestamp() * 1000)


def load_db(path, dev=None, boots=None, since_ms=None, until_ms=None):
    if not os.path.exists(path):
        raise SystemExit(f"database not found: {path}")
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    q = ("SELECT dev, boot, seq, replay, recv_ms, device_utc_ms, up_ms, dup_count, "
         "topic = 'log-import' AS imported FROM telemetry WHERE 1=1")
    args = []
    if dev:
        q += " AND dev = ?"
        args.append(dev)
    if boots:
        q += f" AND boot IN ({','.join('?' * len(boots))})"
        args += list(boots)
    if since_ms is not None:
        q += " AND recv_ms >= ?"
        args.append(since_ms)
    if until_ms is not None:
        q += " AND recv_ms <= ?"
        args.append(until_ms)
    rows = [dict(r) for r in db.execute(q + " ORDER BY dev, boot, seq", args)]
    rejects = db.execute("SELECT COUNT(*) FROM rejects").fetchone()[0]
    db.close()
    return rows, rejects


def load_log(path, dev=None, boots=None):
    """Records with seq from a log_dump.py copy (one JSON record per line; nan accepted)."""
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                rec = json.loads(re.sub(r":\s*-?nan\b", ":null", line))
            except ValueError:
                continue
            if not isinstance(rec.get("seq"), int) or not isinstance(rec.get("boot"), int):
                continue
            if dev and rec.get("dev") != dev:
                continue
            if boots and rec["boot"] not in boots:
                continue
            out.append({"dev": rec.get("dev") or "?", "boot": rec["boot"], "seq": rec["seq"],
                        "up_ms": rec.get("up_ms"), "device_utc_ms": rec.get("utc_ms")})
    return out


def analyse(rows, log=None, rejects=0):
    """Pure analysis of stored rows (dicts as from load_db) and optional log records."""
    by_boot = {}
    for r in rows:
        by_boot.setdefault((r["dev"], r["boot"]), []).append(r)
    log_by_boot = {}
    for r in log or []:
        log_by_boot.setdefault((r["dev"], r["boot"]), set()).add(r["seq"])

    boots = []
    total_missing = 0
    for key in sorted(set(by_boot) | set(log_by_boot)):
        rs = by_boot.get(key, [])
        stored = {r["seq"] for r in rs}
        logged = log_by_boot.get(key, set())
        universe = stored | logged
        lo, hi = (min(universe), max(universe)) if universe else (0, -1)
        missing = sorted(set(range(lo, hi + 1)) - stored)
        total_missing += len(missing)
        b = {
            "dev": key[0], "boot": key[1], "first_seq": lo, "last_seq": hi,
            "expected": hi - lo + 1 if universe else 0,
            "stored": len(stored),
            "missing": len(missing), "missing_ranges": ranges(missing),
            "replayed": sum(1 for r in rs if r["replay"]),
            "imported": sum(1 for r in rs if r.get("imported")),
            "duplicates": sum(r["dup_count"] for r in rs),
        }
        if log is not None:
            b["in_log"] = len(logged)
            b["in_log_not_db"] = len(logged - stored)
            b["in_db_not_log"] = len(stored - logged)
        boots.append(b)

    lat_rows, live_lat, replay_lat = [], [], []
    for r in rows:
        if r["device_utc_ms"] is None or r.get("imported"):
            continue
        lat = r["recv_ms"] - r["device_utc_ms"]
        lat_rows.append({"dev": r["dev"], "boot": r["boot"], "seq": r["seq"], "replay": r["replay"],
                         "device_utc_ms": r["device_utc_ms"], "recv_ms": r["recv_ms"], "latency_ms": lat})
        (replay_lat if r["replay"] else live_lat).append(lat)

    def stats(v):
        return {"n": len(v), "median_ms": median(v), "p95_ms": percentile(v, 95),
                "min_ms": min(v) if v else None, "max_ms": max(v) if v else None,
                "negative": sum(1 for x in v if x < 0)}

    episodes = []
    rep = sorted((r for r in rows if r["replay"] and not r.get("imported")), key=lambda r: r["recv_ms"])
    for r in rep:
        if not episodes or r["recv_ms"] - episodes[-1][-1]["recv_ms"] > REPLAY_EPISODE_GAP_MS:
            episodes.append([])
        episodes[-1].append(r)
    ep_out = []
    for i, ep in enumerate(episodes, 1):
        first, last = ep[0]["recv_ms"], ep[-1]["recv_ms"]
        drain_s = (last - first) / 1000
        ups = [r["up_ms"] for r in ep if r["up_ms"] is not None and r["boot"] == ep[0]["boot"]]
        outage_s = ((max(ups) - min(ups)) + RECORD_PERIOD_MS) / 1000 if ups else None
        oldest = [first - r["device_utc_ms"] for r in ep if r["device_utc_ms"] is not None]
        ep_out.append({
            "episode": i, "records": len(ep), "boots": len({(r['dev'], r['boot']) for r in ep}),
            "first_recv_ms": first, "last_recv_ms": last, "drain_s": drain_s,
            "rate_per_s": (len(ep) - 1) / drain_s if drain_s > 0 else None,
            "outage_span_s": outage_s,
            "oldest_record_age_s": max(oldest) / 1000 if oldest else None,
        })

    summary = {
        "records_stored": len(rows),
        "boots": len(boots),
        "expected_in_seq_ranges": sum(b["expected"] for b in boots),
        "missing_seq": total_missing,
        "replayed_stored": sum(b["replayed"] for b in boots),
        "imported_from_log": sum(b["imported"] for b in boots),
        "duplicates_received": sum(b["duplicates"] for b in boots),
        "rejected_messages": rejects,
        "replay_episodes": len(ep_out),
        "latency_live": stats(live_lat),
        "latency_replay": stats(replay_lat),
    }
    if log is not None:
        logged = {(r["dev"], r["boot"], r["seq"]) for r in log}
        stored = {(r["dev"], r["boot"], r["seq"]) for r in rows}
        summary["log_records"] = len(logged)
        summary["log_records_stored"] = len(logged & stored)
        summary["log_records_missing_in_db"] = len(logged - stored)
        summary["db_records_not_in_log"] = len(stored - logged)
        summary["completeness_vs_log_pct"] = 100.0 * len(logged & stored) / len(logged) if logged else None
    return {"summary": summary, "boots": boots, "latency": lat_rows, "episodes": ep_out}


def _ms(v):
    return "n/a" if v is None else f"{v:.0f} ms" if abs(v) < 10_000 else f"{v / 1000:.1f} s"


def format_text(res):
    s = res["summary"]
    out = ["SW-7 sync report", "================"]
    out.append(f"Records stored: {s['records_stored']} in {s['boots']} boot(s); "
               f"expected from seq ranges: {s['expected_in_seq_ranges']}; missing seq: {s['missing_seq']}")
    if s["imported_from_log"]:
        out.append(f"Backfilled from a device log copy (not received over MQTT): {s['imported_from_log']}")
    out.append(f"Replayed (first copy was a replay): {s['replayed_stored']}; duplicates received and ignored: "
               f"{s['duplicates_received']}; rejected messages (all time): {s['rejected_messages']}")
    if "log_records" in s:
        pct = s["completeness_vs_log_pct"]
        out.append(f"Against the device log: {s['log_records']} generated, {s['log_records_stored']} stored "
                   f"({'n/a' if pct is None else f'{pct:.2f}%'}), {s['log_records_missing_in_db']} missing in the "
                   f"database, {s['db_records_not_in_log']} stored but not in the log")
    out.append("")
    out.append("Per boot:")
    for b in res["boots"]:
        line = (f"  {b['dev']} boot {b['boot']}: seq {b['first_seq']}-{b['last_seq']}, stored {b['stored']} "
                f"of {b['expected']}, missing {b['missing']} [{fmt_ranges(b['missing_ranges'])}], "
                f"replayed {b['replayed']}, duplicates {b['duplicates']}"
                + (f", backfilled {b['imported']}" if b["imported"] else ""))
        if "in_log" in b:
            line += f", in log {b['in_log']} (not stored {b['in_log_not_db']})"
        out.append(line)
    out.append("")
    for name in ("latency_live", "latency_replay"):
        L = s[name]
        label = "Live latency" if name == "latency_live" else "Replay age at arrival"
        if L["n"] == 0:
            out.append(f"{label}: no records with device UTC (no GNSS time)")
        else:
            out.append(f"{label} (receive - device UTC, n={L['n']}): median {_ms(L['median_ms'])}, "
                       f"95th percentile {_ms(L['p95_ms'])}, min {_ms(L['min_ms'])}, max {_ms(L['max_ms'])}"
                       + (f", {L['negative']} negative (clock offset)" if L["negative"] else ""))
    out.append("")
    if not res["episodes"]:
        out.append("Replay episodes: none")
    for e in res["episodes"]:
        start = dt.datetime.fromtimestamp(e["first_recv_ms"] / 1000).strftime("%Y-%m-%d %H:%M:%S")
        rate = "n/a" if e["rate_per_s"] is None else f"{e['rate_per_s']:.2f}/s"
        span = "n/a" if e["outage_span_s"] is None else f"{e['outage_span_s']:.0f} s"
        out.append(f"Replay episode {e['episode']} from {start}: {e['records']} records drained in "
                   f"{e['drain_s']:.1f} s ({rate}); records span {span} of device time")
    return "\n".join(out)


def write_csv(prefix, res):
    os.makedirs(os.path.dirname(os.path.abspath(prefix)) or ".", exist_ok=True)
    paths = []

    def w(name, header, rows):
        p = f"{prefix}_{name}.csv"
        with open(p, "w", newline="", encoding="utf-8") as f:
            cw = csv.writer(f)
            cw.writerow(header)
            cw.writerows(rows)
        paths.append(p)

    s = res["summary"]
    flat = []
    for k, v in s.items():
        if isinstance(v, dict):
            flat += [(f"{k}_{k2}", v2) for k2, v2 in v.items()]
        else:
            flat.append((k, v))
    w("summary", ["metric", "value"], flat)
    bh = ["dev", "boot", "first_seq", "last_seq", "expected", "stored", "missing", "missing_ranges",
          "replayed", "imported", "duplicates", "in_log", "in_log_not_db", "in_db_not_log"]
    w("boots", bh, [[b.get(h) if h != "missing_ranges" else fmt_ranges(b[h], 1000) for h in bh]
                    for b in res["boots"]])
    lh = ["dev", "boot", "seq", "replay", "device_utc_ms", "recv_ms", "latency_ms"]
    w("latency", lh, [[r[h] for h in lh] for r in res["latency"]])
    eh = ["episode", "records", "boots", "first_recv_ms", "last_recv_ms", "drain_s", "rate_per_s",
          "outage_span_s", "oldest_record_age_s"]
    w("replay", eh, [[e[h] for h in eh] for e in res["episodes"]])
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description="SW-7 central database completeness and latency report")
    ap.add_argument("--db", default=os.environ.get("SW7_DB", DEFAULT_DB))
    ap.add_argument("--log", help="device log copy from BenchTest/log_dump.py (.jsonl)")
    ap.add_argument("--dev")
    ap.add_argument("--boot", type=int, action="append", help="only this boot (repeatable)")
    ap.add_argument("--since", help="receive time from, ISO (local time unless Z or +hh:mm)")
    ap.add_argument("--until", help="receive time to, ISO")
    ap.add_argument("--csv", metavar="PREFIX", help="write PREFIX_summary/boots/latency/replay.csv")
    ap.add_argument("--check", action="store_true", help="exit 1 unless zero missing and latency within limit")
    ap.add_argument("--max-p95-ms", type=float, default=5000)
    a = ap.parse_args(argv)
    since = parse_time_ms(a.since) if a.since else None
    until = parse_time_ms(a.until) if a.until else None
    rows, rejects = load_db(a.db, a.dev, a.boot, since, until)
    log = load_log(a.log, a.dev, a.boot) if a.log else None
    if log is not None and (since is not None or until is not None):
        # Keep log records in the stored boots' seq span, so the window does not count as missing.
        span = {}
        for r in rows:
            k = (r["dev"], r["boot"])
            lo, hi = span.get(k, (r["seq"], r["seq"]))
            span[k] = (min(lo, r["seq"]), max(hi, r["seq"]))
        log = [r for r in log if (r["dev"], r["boot"]) in span
               and span[(r["dev"], r["boot"])][0] <= r["seq"] <= span[(r["dev"], r["boot"])][1]]
    res = analyse(rows, log, rejects)
    print(format_text(res))
    if a.csv:
        for p in write_csv(a.csv, res):
            print(f"wrote {p}")
    if a.check:
        s = res["summary"]
        p95 = s["latency_live"]["p95_ms"]
        ok_missing = s["missing_seq"] == 0 and s.get("log_records_missing_in_db", 0) == 0
        ok_lat = p95 is None or p95 <= a.max_p95_ms
        print(f"CHECK missing seq = 0: {'PASS' if ok_missing else 'FAIL'}")
        print(f"CHECK live latency p95 <= {a.max_p95_ms:.0f} ms: "
              f"{'PASS' if ok_lat and p95 is not None else 'FAIL' if not ok_lat else 'NOT MEASURED (no device UTC)'}")
        return 0 if ok_missing and ok_lat else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
