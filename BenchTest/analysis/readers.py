"""Readers: the Pi recorder JSONL, markers, the raw IMU stream, video labels, and the device-to-host clock map.

Recorder file (BenchTest/road_logger.py): one JSON object per line, {"t": laptop/Pi epoch s, "src": ..., "data": ...}
with src in front, rear, front_alerts, rear_alerts, marker. A rear (or front) reply's data.esp32 is the unit's 1 Hz
DASH record (seq, up_ms, vib, i, v, imu_hz, drops, spd_raw, fix, lat, lon, ...). The bridge repeats its latest
record and the recorder polls twice a second, so records are reduced to one per sequence number, keeping the first
row in file order (as the report does). Lines that are not valid JSON are counted and skipped.

Raw IMU stream: see RAW_FORMAT below and read_raw_stream(). The format constants live only in RAW_FORMAT, so a
change in the firmware's raw_stream.h means editing that dict and, at most, parse_raw_line().
"""
from dataclasses import dataclass, field
from datetime import datetime
import csv
import json
import math
import os
import re

import numpy as np

from .config import G0

# --------------------------------------------------------------------------------------------------------------------
# Recorder file
# --------------------------------------------------------------------------------------------------------------------


def iter_recorder(paths):
    """Yield (record, None) for each valid JSON line and (None, line_no) for each bad one, over one or more files."""
    if isinstance(paths, (str, os.PathLike)):
        paths = [paths]
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as f:
            for n, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line), None
                except json.JSONDecodeError:
                    yield None, n


@dataclass
class Dash:
    """Deduplicated 1 Hz DASH records of one unit, sorted by (boot, sequence number)."""
    t: np.ndarray            # host time of the first row carrying this seq, epoch s
    seq: np.ndarray
    up_ms: np.ndarray        # device uptime, ms (NaN if absent)
    vib: np.ndarray
    i: np.ndarray
    v: np.ndarray
    spd_raw: np.ndarray
    fix: np.ndarray          # bool
    lat: np.ndarray
    lon: np.ndarray
    readable: np.ndarray     # bool: every field in cfg.readable_fields present
    raw: list                # the esp32 dicts, same order
    boot: np.ndarray = None  # boot index (0 for the first), records sorted by (boot, seq)
    stats: dict = field(default_factory=dict)

    def __len__(self):
        return len(self.seq)


def _num(x):
    try:
        return float(x) if x is not None and not isinstance(x, bool) else math.nan
    except (TypeError, ValueError):
        return math.nan


def read_dash(paths, src="rear", readable_fields=("vib", "i", "v", "imu_hz", "drops")):
    """Deduplicated DASH records of one source. A record is identified by (boot, seq): the unit's sequence number
    restarts when it reboots (the 19 Oct session has two later files after restarts, with seq 31 to 273 again), so
    a new boot is counted whenever up_ms goes back by more than 2 s (or, without up_ms, seq goes back by more than 5).
    Files are read in the order given (sorted by name, which is the start time)."""
    rows = with_rec = bad = 0
    first = {}
    boot, last_up, last_seq = 0, None, None
    for rec, badline in iter_recorder(paths):
        if rec is None:
            bad += 1
            continue
        if rec.get("src") != src:
            continue
        rows += 1
        e = (rec.get("data") or {}).get("esp32")
        if not isinstance(e, dict) or e.get("seq") is None:
            continue
        with_rec += 1
        sq, up = e["seq"], _num(e.get("up_ms"))
        if last_seq is not None:
            if (math.isfinite(up) and last_up is not None and math.isfinite(last_up) and up < last_up - 2000) or                     (not math.isfinite(up) and sq < last_seq - 5):
                boot += 1
        last_seq, last_up = sq, up
        if (boot, sq) not in first:
            first[(boot, sq)] = (rec["t"], e)
    keys = sorted(first)
    es = [first[k][1] for k in keys]
    d = Dash(
        t=np.array([first[k][0] for k in keys], float),
        seq=np.array([k[1] for k in keys], np.int64),
        up_ms=np.array([_num(e.get("up_ms")) for e in es]),
        vib=np.array([_num(e.get("vib")) for e in es]),
        i=np.array([_num(e.get("i")) for e in es]),
        v=np.array([_num(e.get("v")) for e in es]),
        spd_raw=np.array([_num(e.get("spd_raw")) for e in es]),
        fix=np.array([bool(e.get("fix")) for e in es]),
        lat=np.array([_num(e.get("lat")) for e in es]),
        lon=np.array([_num(e.get("lon")) for e in es]),
        readable=np.array([all(k in e for k in readable_fields) for e in es], bool),
        raw=es,
        boot=np.array([k[0] for k in keys], np.int64),
    )
    per_boot = []
    for b_ in range(boot + 1):
        sq = d.seq[d.boot == b_]
        if len(sq):
            span = int(sq[-1] - sq[0] + 1)
            per_boot.append({"boot": b_, "unique": int(len(sq)), "seq_first": int(sq[0]), "seq_last": int(sq[-1]),
                             "seq_span": span, "missing": span - int(len(sq))})
    d.stats = {"src": src, "rows": rows, "rows_with_record": with_rec, "unique": len(d), "bad_json_lines": bad,
               "boots": len(per_boot), "seq_first": per_boot[0]["seq_first"] if per_boot else None,
               "seq_last": per_boot[0]["seq_last"] if per_boot else None,
               "seq_span": sum(p["seq_span"] for p in per_boot), "missing": sum(p["missing"] for p in per_boot),
               "per_boot": per_boot}
    return d


# --------------------------------------------------------------------------------------------------------------------
# Markers
# --------------------------------------------------------------------------------------------------------------------

_TS_PREFIX = re.compile(r"^\s*(\d{9,11}(?:\.\d+)?|\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:\.\d+)?(?:[+-]\d\d:?\d\d|Z)?)\s+(.*)$")


def parse_time(s, tz_default=None):
    """Epoch seconds from a float string or an ISO 8601 date-time (naive times use tz_default, else local time)."""
    s = str(s).strip()
    try:
        return float(s)
    except ValueError:
        pass
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None and tz_default is not None:
        dt = dt.replace(tzinfo=tz_default)
    return dt.timestamp()


def read_markers(recorder_paths=None, txt_path=None, dedup_s=2.0):
    """Markers as a time-sorted list of (t, text).

    From the recorder file: every src == "marker" row (typed markers and lines appended to roadtest_markers.txt,
    which the recorder copies in with its own time). From roadtest_markers.txt itself: only lines that start with a
    time stamp (epoch or ISO), since a bare line has no time; bare lines are returned in `untimed` for the summary.
    The same text within dedup_s is kept once.
    """
    out, untimed = [], []
    if recorder_paths:
        for rec, _ in iter_recorder(recorder_paths):
            if rec and rec.get("src") == "marker" and rec.get("text"):
                out.append((float(rec["t"]), str(rec["text"]).strip()))
    if txt_path and os.path.isfile(txt_path):
        with open(txt_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                m = _TS_PREFIX.match(line)
                if m:
                    out.append((parse_time(m.group(1)), m.group(2).strip()))
                else:
                    untimed.append(line)
    out.sort()
    kept = []
    for t, text in out:
        if any(text == k[1] and abs(t - k[0]) <= dedup_s for k in kept):
            continue
        kept.append((t, text))
    kept_texts = {k[1] for k in kept}
    return kept, [u for u in untimed if u not in kept_texts]


# --------------------------------------------------------------------------------------------------------------------
# Raw IMU stream
# --------------------------------------------------------------------------------------------------------------------

# Format version 2, from TelemetryUnit/include/raw_stream.h (firmware v0.7.5, 22 Oct 2026; v1 was never flashed).
# Every line ends in " <crc>": CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) of the bytes from the first letter of
# the type word up to the character before that space, 4 lowercase hex digits. Three line types:
#   RAW  2 <node> <imu> <seq0> <t0_us> <n> <hex> <crc>
#        hex: n records of 16 bytes: dseq (u8), dt_us (u16 BE), flags (u8: bit0 sync level, bit1 stuck),
#             ax ay az gx gy gz (i16 BE counts)
#   RAWH 2 <node> <imu> <accel_counts_per_g> <gyro_counts_per_dps> <rate_hz> <dlpf_hz> <fw> <rawdrop> <rdfail> <stuck>
#   RAWS 2 <node> <edge> <level> <t_us>                       (sync pulse edge, device time)
# Anything before the type word on a line (for example a receive time stamp the Pi adds) is taken as the host
# receive time if it parses as a time (epoch s or ISO 8601); otherwise ignored. The Pi-side file layout is not
# fixed yet: this reader accepts any text file whose lines contain these records, mixed with DASH or other lines.
RAW_FORMAT = {
    "version": 2,
    "record_bytes": 16,
    "max_batch": 10,
    "accel_counts_per_g": 4096.0,          # +-8 g, used until a RAWH line gives the value
    "gyro_counts_per_dps": 65.5,           # +-500 deg/s
    "flag_sync": 0x01,
    "flag_stuck": 0x02,
    "crc_poly": 0x1021,
    "crc_init": 0xFFFF,
}
_RAW_RE = re.compile(r"RAW[HS]? %d " % RAW_FORMAT["version"])

# CSV fallback, one sample per row, header required:
#   node,seq,t_us,ax,ay,az,gx,gy,gz       (optional columns: imu, host_t, flags)
#   accelerations in m/s^2, angular rates in rad/s, t_us device microseconds.
CSV_COLUMNS = ("node", "seq", "t_us", "ax", "ay", "az", "gx", "gy", "gz")


def crc16_ccitt_false(data: bytes, poly=RAW_FORMAT["crc_poly"], init=RAW_FORMAT["crc_init"]):
    crc = init
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ poly) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def parse_raw_line(line):
    """Parse one line. Returns None if it holds no raw record, {"type": ..., "bad": True} if it is damaged, else
    a dict: RAW -> node, imu, seq[n], t_us[n], flags[n], counts[n, 6]; RAWH -> node, imu, accel_counts_per_g,
    gyro_counts_per_dps, rate_hz, dlpf_hz, fw, rawdrop, rdfail, stuck; RAWS -> node, edge, level, t_us. Every
    dict carries "host" (receive time from a prefix, or None)."""
    m = _RAW_RE.search(line)
    if m is None:
        return None
    k = m.start()
    body = line[k:].rstrip("\r\n")
    typ = body.split(" ", 1)[0]
    bad = {"type": typ, "bad": True}
    sp = body.rfind(" ")
    if sp < 0 or len(body) - sp - 1 != 4:
        return bad
    try:
        if crc16_ccitt_false(body[:sp].encode("ascii")) != int(body[sp + 1:], 16):
            return bad
    except (ValueError, UnicodeEncodeError):
        return bad
    parts = body[:sp].split(" ")
    host = None
    pre = line[:k].strip()
    if pre:
        try:
            host = parse_time(pre.split()[-1])
        except ValueError:
            host = None
    try:
        if typ == "RAW":
            if len(parts) != 8:
                return bad
            node, hx = parts[2], parts[7]
            imu, seq0, t0, n = (int(p) for p in parts[3:7])
            rb = RAW_FORMAT["record_bytes"]
            if not (1 <= n <= RAW_FORMAT["max_batch"]) or len(hx) != 2 * rb * n:
                return bad
            rec = np.frombuffer(bytes.fromhex(hx), np.uint8).reshape(n, rb)
            dseq = rec[:, 0].astype(np.int64)
            dt = (rec[:, 1].astype(np.int64) << 8) | rec[:, 2]
            return {"type": "RAW", "host": host, "node": node, "imu": imu, "seq": seq0 + np.cumsum(dseq),
                    "t_us": t0 + np.cumsum(dt), "flags": rec[:, 3].astype(np.uint8),
                    "counts": rec[:, 4:].copy().view(">i2").reshape(n, 6).astype(np.int64)}
        if typ == "RAWH":
            if len(parts) != 12:
                return bad
            return {"type": "RAWH", "host": host, "node": parts[2], "imu": int(parts[3]),
                    "accel_counts_per_g": float(parts[4]), "gyro_counts_per_dps": float(parts[5]),
                    "rate_hz": float(parts[6]), "dlpf_hz": float(parts[7]), "fw": parts[8],
                    "rawdrop": int(parts[9]), "rdfail": int(parts[10]), "stuck": int(parts[11])}
        if typ == "RAWS":
            if len(parts) != 6:
                return bad
            return {"type": "RAWS", "host": host, "node": parts[2], "edge": int(parts[3]), "level": int(parts[4]),
                    "t_us": int(parts[5])}
    except ValueError:
        return bad
    return bad


@dataclass
class ImuStream:
    node: str
    imu: int
    seq: np.ndarray
    t_us: np.ndarray
    acc: np.ndarray          # N x 3, m/s^2, sensor axes (+x forward: lid arrow)
    gyr: np.ndarray          # N x 3, rad/s
    host_t: np.ndarray       # N, host receive time of the sample's line (NaN if unknown)
    flags: np.ndarray = None  # N, uint8 (bit 0 sync level, bit 1 stuck)
    header: dict = None      # latest RAWH for this IMU
    sync: dict = None        # this node's RAWS edges: {"edge", "level", "t_us", "host"} arrays
    stats: dict = field(default_factory=dict)

    @property
    def t_s(self):
        return self.t_us * 1e-6

    def __len__(self):
        return len(self.seq)


def _finish(node, imu, seq, t_us, acc, gyr, host, flags, stats):
    order = np.argsort(seq, kind="stable")
    seq, t_us, acc, gyr, host, flags = (x[order] for x in (seq, t_us, acc, gyr, host, flags))
    keep = np.ones(len(seq), bool)
    keep[1:] = np.diff(seq) != 0
    stats["duplicates"] = int((~keep).sum())
    seq, t_us, acc, gyr, host, flags = (x[keep] for x in (seq, t_us, acc, gyr, host, flags))
    stats["samples"] = int(len(seq))
    stats["seq_gaps_samples"] = int(np.sum(np.clip(np.diff(seq) - 1, 0, None))) if len(seq) > 1 else 0
    stats["stuck_flagged"] = int(np.sum((flags & RAW_FORMAT["flag_stuck"]) != 0))
    if len(t_us) > 1 and np.any(np.diff(t_us) < 0):
        stats["warning"] = "device time goes backwards against seq (reboot inside the file?)"
    return ImuStream(node, int(imu), seq, t_us, acc, gyr, host, flags, stats=stats)


def read_raw_stream(path, node=None):
    """Read one raw-stream file into {(node, imu): ImuStream}. Auto-detects RAW v2 lines or the CSV fallback.

    node: used for CSV rows without a node column; RAW lines carry their own node name.
    Counts are scaled by the latest RAWH line of that IMU, or RAW_FORMAT defaults if there is none.
    """
    node = node or ("front" if "front" in os.path.basename(path).lower() else
                    "rear" if "rear" in os.path.basename(path).lower() else "node")
    with open(path, encoding="utf-8", errors="replace") as f:
        head = f.readline()
    cols = [c.strip().lower() for c in head.split(",")]
    if all(c in cols for c in CSV_COLUMNS):
        return _read_raw_csv(path, node)
    by, hdr, sync = {}, {}, {}
    seen = {"RAW": 0, "RAWH": 0, "RAWS": 0}
    bad = {"RAW": 0, "RAWH": 0, "RAWS": 0}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            p = parse_raw_line(line)
            if p is None:
                continue
            seen[p["type"]] = seen.get(p["type"], 0) + 1
            if p.get("bad"):
                bad[p["type"]] = bad.get(p["type"], 0) + 1
                continue
            if p["type"] == "RAW":
                by.setdefault((p["node"], p["imu"]), []).append(p)
            elif p["type"] == "RAWH":
                hdr[(p["node"], p["imu"])] = p
            else:
                sync.setdefault(p["node"], []).append(p)
    sync_arr = {nd: {k: np.array([np.nan if e[k] is None else e[k] for e in ev], float)
                     for k in ("edge", "level", "t_us", "host")} for nd, ev in sync.items()}
    out = {}
    for (nd, imu), chunks in by.items():
        h = hdr.get((nd, imu))
        cpg = h["accel_counts_per_g"] if h else RAW_FORMAT["accel_counts_per_g"]
        cpd = h["gyro_counts_per_dps"] if h else RAW_FORMAT["gyro_counts_per_dps"]
        seq = np.concatenate([c["seq"] for c in chunks])
        t_us = np.concatenate([c["t_us"] for c in chunks])
        cnt = np.concatenate([c["counts"] for c in chunks]).astype(float)
        flags = np.concatenate([c["flags"] for c in chunks])
        host = np.concatenate([np.full(len(c["seq"]), np.nan if c["host"] is None else c["host"]) for c in chunks])
        st = {"format": "RAW v%d" % RAW_FORMAT["version"], "lines": len(chunks), "lines_seen": dict(seen),
              "lines_rejected": dict(bad), "scale_source": "RAWH" if h else "default (no RAWH line)",
              "clipped_counts": int(np.sum((cnt[:, :3] >= 32767) | (cnt[:, :3] <= -32768)))}
        if h:
            st.update({k: h[k] for k in ("rate_hz", "dlpf_hz", "fw", "rawdrop", "rdfail", "stuck")})
        s = _finish(nd, imu, seq, t_us, cnt[:, :3] * (G0 / cpg), cnt[:, 3:] * (math.pi / 180.0 / cpd), host,
                    flags, st)
        s.header, s.sync = h, sync_arr.get(nd)
        out[(nd, imu)] = s
    return out


def _read_raw_csv(path, node):
    by = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            row = {k.strip().lower(): v for k, v in row.items() if k}
            by.setdefault((row.get("node") or node, int(row.get("imu") or 1)), []).append(row)
    out = {}
    for (nd, imu), rows in by.items():
        g = lambda k: np.array([float(r[k]) for r in rows])
        host = np.array([float(r["host_t"]) if r.get("host_t") not in (None, "") else np.nan for r in rows])
        flags = np.array([int(r["flags"]) if r.get("flags") not in (None, "") else 0 for r in rows], np.uint8)
        out[(nd, imu)] = _finish(nd, imu, g("seq").astype(np.int64), g("t_us").astype(np.int64),
                                 np.column_stack([g("ax"), g("ay"), g("az")]),
                                 np.column_stack([g("gx"), g("gy"), g("gz")]), host, flags,
                                 {"format": "CSV fallback", "rows": len(rows)})
    return out


def write_raw_csv(path, stream: ImuStream):
    """Write an ImuStream in the CSV fallback format (used by the tests and for hand-made data)."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(list(CSV_COLUMNS) + ["imu", "host_t"])
        for k in range(len(stream)):
            w.writerow([stream.node, int(stream.seq[k]), int(stream.t_us[k]), *("%.9g" % x for x in stream.acc[k]),
                        *("%.9g" % x for x in stream.gyr[k]), stream.imu,
                        "" if not np.isfinite(stream.host_t[k]) else "%.6f" % stream.host_t[k]])


def _with_crc(body, host_t=None):
    crc = crc16_ccitt_false(body.encode("ascii"))
    return ("%.3f " % host_t if host_t is not None else "") + body + " %04x\n" % crc


def encode_raw_line(node, imu, seq, t_us, counts, flags=None, host_t=None):
    """Python mirror of rawEncodeLine() in raw_stream.h (v2), for tests and simulated sessions."""
    out = bytearray()
    for k in range(len(seq)):
        dseq = 0 if k == 0 else int(seq[k] - seq[k - 1])
        dt = 0 if k == 0 else int(t_us[k] - t_us[k - 1])
        fl = int(flags[k]) & 0x03 if flags is not None else 0
        out += bytes([dseq & 0xFF, (dt >> 8) & 0xFF, dt & 0xFF, fl])
        out += np.asarray(counts[k], ">i2").tobytes()
    body = "RAW %d %s %d %d %d %d %s" % (RAW_FORMAT["version"], node, imu, int(seq[0]), int(t_us[0]), len(seq),
                                         out.hex())
    return _with_crc(body, host_t)


def encode_raw_header(node, imu, cpg=4096, cpd=65.5, rate=200, dlpf=44, fw="0.7.5", rawdrop=0, rdfail=0, stuck=0,
                      host_t=None):
    body = "RAWH %d %s %d %d %.1f %d %d %s %d %d %d" % (RAW_FORMAT["version"], node, imu, cpg, cpd, rate, dlpf, fw,
                                                       rawdrop, rdfail, stuck)
    return _with_crc(body, host_t)


def encode_raw_sync(node, edge, level, t_us, host_t=None):
    return _with_crc("RAWS %d %s %d %d %d" % (RAW_FORMAT["version"], node, edge, level, t_us), host_t)


def sync_clock(stream: ImuStream, pi_edge_times=None):
    """Clock map (offset, rate, residual_sd_s) from the node's RAWS edges.

    pi_edge_times: the Pi's own GPIO time stamps of the same edges (epoch s), in order, one per RAWS edge in the
    file; then a straight-line fit. If None, the RAWS lines' host prefixes (receive times) are used with the
    lower-envelope fit. The Pi-side edge log format is not fixed yet, hence the plain array argument.
    """
    s = stream.sync
    if s is None or len(s["t_us"]) < 2:
        return None
    dev = s["t_us"] * 1e-6
    if pi_edge_times is not None:
        host = np.asarray(pi_edge_times, float)[: len(dev)]
        dev = dev[: len(host)]
        rate, off = np.polyfit(dev, host, 1)
        return float(off), float(rate), float(np.std(host - (off + rate * dev)))
    if np.isfinite(s["host"]).sum() < 2:
        return None
    return fit_clock(dev, s["host"], bin_s=10.0)


# --------------------------------------------------------------------------------------------------------------------
# Clock map: device time (esp_timer / up_ms) to host epoch time
# --------------------------------------------------------------------------------------------------------------------

def fit_clock(dev_s, host_s, bin_s=60.0):
    """Fit host = offset + rate * dev from (device time, host receive time) pairs.

    Receive time = send time + a non-negative delay, so the lower envelope is used: the minimum of (host - dev) in
    each bin_s bin, then a least-squares line through those minima. Returns (offset, rate, residual_sd_s).
    """
    dev_s, host_s = np.asarray(dev_s, float), np.asarray(host_s, float)
    ok = np.isfinite(dev_s) & np.isfinite(host_s)
    dev_s, host_s = dev_s[ok], host_s[ok]
    if len(dev_s) < 2:
        raise ValueError("need at least two time pairs")
    d = host_s - dev_s
    b = np.floor((dev_s - dev_s.min()) / bin_s).astype(int)
    xs, ys = [], []
    for k in np.unique(b):
        m = b == k
        j = np.argmin(d[m])
        xs.append(dev_s[m][j])
        ys.append(d[m][j])
    xs, ys = np.array(xs), np.array(ys)
    if len(xs) >= 2:
        slope, icpt = np.polyfit(xs, ys, 1)
        res = float(np.std(ys - (icpt + slope * xs)))
    else:
        slope, icpt, res = 0.0, float(ys[0]), math.nan
    return float(icpt), float(1.0 + slope), res


def dash_clock(dash: Dash):
    """Clock map for a unit from its DASH records' up_ms and the recorder's receive time."""
    return fit_clock(dash.up_ms / 1000.0, dash.t)


# --------------------------------------------------------------------------------------------------------------------
# Video labels
# --------------------------------------------------------------------------------------------------------------------

def read_labels(path, tz_default=None):
    """Labels CSV with header `time,type` (time: epoch s or ISO 8601). Returns (t[], type[])."""
    ts, ty = [], []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
            if not row.get("time"):
                continue
            ts.append(parse_time(row["time"], tz_default))
            ty.append(row.get("type", "").lower())
    return np.array(ts, float), np.array(ty, object)
