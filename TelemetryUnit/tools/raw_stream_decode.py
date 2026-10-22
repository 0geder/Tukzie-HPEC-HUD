"""Reference decoder for the raw IMU stream, firmware v0.7.5, format version 2.

The format is described in TelemetryUnit/include/raw_stream.h and
TelemetryUnit/RAW_STREAM.md. This file is the reference for the Pi side: the
recorder and the analysis can import parse_line() or copy it.

Usage:
  python raw_stream_decode.py CAPTURE [--out DIR]
      Decodes a capture (the bytes read from the UART or USB serial, any
      other lines included), prints a summary per node and IMU (samples,
      missing seq numbers, bad lines, sync edges, the last counters from the
      RAWH and DASH lines) and, with --out, writes one CSV per node and IMU
      with counts and SI units, plus a CSV of the sync edges.
  python raw_stream_decode.py --selftest CAPTURE EXPECTED_CSV
      Checks the decoder against a capture and the samples the C++ host test
      (test_host/test_raw_stream.cpp) wrote for it. Used by test_host/run.py.

Standard library only (Python 3.6 or newer)."""
import argparse
import csv
import json
import math
import os
import sys

FORMAT_VERSION = 2
RECORD_HEX = 32          # 16 bytes per sample
MAX_BATCH = 10
FLAG_SYNC = 0x01
FLAG_STUCK = 0x02
GRAVITY = 9.80665
DEFAULT_ACCEL_COUNTS_PER_G = 4096.0
DEFAULT_GYRO_COUNTS_PER_DPS = 65.5


def crc16_ccitt_false(data):
    """CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, no reflection, no final XOR."""
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def _check_crc(body):
    """body is the line from its type word, newline removed. Returns the part
    before the CRC, or None if the CRC is missing or wrong."""
    if len(body) < 6 or body[-5] != " ":
        return None
    if any(c not in "0123456789abcdef" for c in body[-4:]):
        return None
    got = int(body[-4:], 16)
    payload = body[:-5]
    if crc16_ccitt_false(payload.encode("ascii", errors="replace")) != got:
        return None
    return payload


def _find(line, word):
    """Position of a type word in the line, at the start or after other text
    (another task's output can land in front of a line on USB serial); -1 if absent.
    The CRC then decides whether what follows is a good line."""
    return line.find(word)


def parse_line(line):
    """Classifies one line of text (str, newline optional).

    Returns (kind, obj):
      ("raw", {"node", "imu", "samples": [{"seq", "t_us", "flags", "v": [ax..gz]}]})
      ("rawh", {"node", "imu", "accel_counts_per_g", "gyro_counts_per_dps",
                "rate_hz", "dlpf_hz", "fw", "rawdrop", "rdfail", "stuck"})
      ("raws", {"node", "edge", "level", "t_us"})
      ("dash", dict)          the DASH JSON object
      ("bad", reason)         a raw line that failed its CRC or layout, or bad DASH JSON
      ("ignore", None)        any other line
    """
    line = line.rstrip("\r\n")
    p = _find(line, "RAWH %d " % FORMAT_VERSION)
    if p >= 0:
        payload = _check_crc(line[p:])
        if payload is None:
            return "bad", "rawh crc"
        f = payload.split(" ")
        if len(f) != 12:
            return "bad", "rawh fields"
        try:
            return "rawh", {"node": f[2], "imu": int(f[3]), "accel_counts_per_g": float(f[4]),
                            "gyro_counts_per_dps": float(f[5]), "rate_hz": int(f[6]), "dlpf_hz": int(f[7]),
                            "fw": f[8], "rawdrop": int(f[9]), "rdfail": int(f[10]), "stuck": int(f[11])}
        except ValueError:
            return "bad", "rawh values"
    p = _find(line, "RAWS %d " % FORMAT_VERSION)
    if p >= 0:
        payload = _check_crc(line[p:])
        if payload is None:
            return "bad", "raws crc"
        f = payload.split(" ")
        if len(f) != 6:
            return "bad", "raws fields"
        try:
            return "raws", {"node": f[2], "edge": int(f[3]), "level": int(f[4]), "t_us": int(f[5])}
        except ValueError:
            return "bad", "raws values"
    p = _find(line, "RAW %d " % FORMAT_VERSION)
    if p >= 0:
        payload = _check_crc(line[p:])
        if payload is None:
            return "bad", "raw crc"
        f = payload.split(" ")
        if len(f) != 8:
            return "bad", "raw fields"
        try:
            node, imu, seq, t, n, hexs = f[2], int(f[3]), int(f[4]), int(f[5]), int(f[6]), f[7]
            if not 1 <= n <= MAX_BATCH or len(hexs) != n * RECORD_HEX:
                return "bad", "raw length"
            data = bytes.fromhex(hexs)
        except ValueError:
            return "bad", "raw values"
        samples = []
        for k in range(n):
            r = data[16 * k:16 * k + 16]
            if k > 0:
                seq = (seq + r[0]) & 0xFFFFFFFF
                t += (r[1] << 8) | r[2]
            v = []
            for a in range(6):
                u = (r[4 + 2 * a] << 8) | r[5 + 2 * a]
                v.append(u - 65536 if u >= 32768 else u)
            samples.append({"seq": seq, "t_us": t, "flags": r[3], "v": v})
        return "raw", {"node": node, "imu": imu, "samples": samples}
    if line.startswith("DASH "):
        try:
            obj = json.loads(line[5:])
        except ValueError:
            return "bad", "dash json"
        return ("dash", obj) if isinstance(obj, dict) else ("bad", "dash json")
    return "ignore", None


def decode_file(path):
    """Decodes a capture file. Returns a dict with samples per (node, imu),
    sync edges, the last RAWH per (node, imu), DASH objects and counts."""
    res = {"samples": {}, "sync": [], "rawh": {}, "dash": [], "counts": {}}
    counts = res["counts"]
    with open(path, "rb") as fh:
        for raw in fh:
            text = raw.decode("ascii", errors="replace")
            kind, obj = parse_line(text)
            counts[kind] = counts.get(kind, 0) + 1
            if kind == "raw":
                key = (obj["node"], obj["imu"])
                res["samples"].setdefault(key, []).extend(obj["samples"])
            elif kind == "raws":
                res["sync"].append(obj)
            elif kind == "rawh":
                res["rawh"][(obj["node"], obj["imu"])] = obj
            elif kind == "dash":
                res["dash"].append(obj)
    return res


def missing_seq(samples):
    """Missing sample count from the seq numbers (read failures + drops)."""
    if not samples:
        return 0
    seqs = sorted(set(s["seq"] for s in samples))
    return (seqs[-1] - seqs[0] + 1) - len(seqs)


def summary(res):
    out = ["lines: " + ", ".join("%s=%d" % kv for kv in sorted(res["counts"].items()))]
    for key in sorted(res["samples"]):
        s = res["samples"][key]
        dts = [b["t_us"] - a["t_us"] for a, b in zip(s, s[1:]) if b["seq"] - a["seq"] == 1]
        rate = 1e6 / (sum(dts) / len(dts)) if dts else float("nan")
        h = res["rawh"].get(key)
        out.append("%s imu%d: %d samples, %d missing by seq, %d stuck-flagged, mean rate %.2f Hz%s"
                   % (key[0], key[1], len(s), missing_seq(s), sum(1 for x in s if x["flags"] & FLAG_STUCK), rate,
                      "" if h is None else ", last RAWH rawdrop=%d rdfail=%d stuck=%d"
                      % (h["rawdrop"], h["rdfail"], h["stuck"])))
    out.append("sync edges: %d" % len(res["sync"]))
    if res["dash"]:
        last = res["dash"][-1]
        out.append("last DASH: " + ", ".join("%s=%s" % (k, last.get(k)) for k in
                                              ("node", "imu_hz", "drops", "rdfail", "stuck", "rawdrop")))
    return "\n".join(out)


def write_csv(res, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for (node, imu), samples in sorted(res["samples"].items()):
        h = res["rawh"].get((node, imu), {})
        acc = h.get("accel_counts_per_g", DEFAULT_ACCEL_COUNTS_PER_G)
        gyr = h.get("gyro_counts_per_dps", DEFAULT_GYRO_COUNTS_PER_DPS)
        path = os.path.join(out_dir, "raw_%s_imu%d.csv" % (node, imu))
        with open(path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["seq", "t_us", "sync", "stuck", "ax", "ay", "az", "gx", "gy", "gz",
                        "ax_mps2", "ay_mps2", "az_mps2", "gx_rads", "gy_rads", "gz_rads"])
            for s in samples:
                v = s["v"]
                w.writerow([s["seq"], s["t_us"], s["flags"] & FLAG_SYNC, (s["flags"] & FLAG_STUCK) >> 1] + v +
                           ["%.5f" % (c / acc * GRAVITY) for c in v[:3]] +
                           ["%.6f" % (c / gyr * math.pi / 180.0) for c in v[3:]])
        print("wrote", path)
    path = os.path.join(out_dir, "sync_edges.csv")
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["node", "edge", "level", "t_us"])
        for e in res["sync"]:
            w.writerow([e["node"], e["edge"], e["level"], e["t_us"]])
    print("wrote", path)


def selftest(capture, expected_csv):
    res = decode_file(capture)
    want = []
    meta = {}
    with open(expected_csv) as fh:
        for row in fh:
            row = row.strip()
            if row.startswith("#"):
                for kv in row[1:].split():
                    k, v = kv.split("=")
                    meta[k] = int(v)
                continue
            if not row or row.startswith("node,"):
                continue
            f = row.split(",")
            want.append((f[0], int(f[1]), int(f[2]), int(f[3]), int(f[4]), [int(x) for x in f[5:11]]))
    got = []
    # Rebuild the decode order: the C++ test lists samples in line order.
    with open(capture, "rb") as fh:
        for raw in fh:
            kind, obj = parse_line(raw.decode("ascii", errors="replace"))
            if kind == "raw":
                for s in obj["samples"]:
                    got.append((obj["node"], obj["imu"], s["seq"], s["t_us"], s["flags"], s["v"]))
    fails = []
    if got != want:
        n = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
        fails.append("samples differ: got %d, want %d, first difference at %d" % (len(got), len(want), n))
    c = res["counts"]
    for key, kind in (("raw_lines", "raw"), ("bad_lines", "bad"), ("sync_lines", "raws"), ("dash_lines", "dash")):
        if key in meta and c.get(kind, 0) != meta[key]:
            fails.append("%s: got %d, want %d" % (key, c.get(kind, 0), meta[key]))
    if c.get("rawh", 0) == 0:
        fails.append("no RAWH lines decoded")
    print(summary(res))
    # CRC check value and a hand-made line.
    if crc16_ccitt_false(b"123456789") != 0x29B1:
        fails.append("crc check value")
    if parse_line("RAW 2 rear 1 5 5 1 00000000000000000000000000000000 0000")[0] != "bad":
        fails.append("bad crc not caught")
    if fails:
        print("decoder selftest FAIL:\n  " + "\n  ".join(fails))
        return 1
    print("decoder selftest PASS: %d samples identical to the C++ encoder's, %d RAW, %d bad, %d RAWS, %d RAWH, "
          "%d DASH lines" % (len(got), c.get("raw", 0), c.get("bad", 0), c.get("raws", 0), c.get("rawh", 0),
                            c.get("dash", 0)))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("capture")
    ap.add_argument("expected", nargs="?")
    ap.add_argument("--out", help="directory for the CSV files")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        if not a.expected:
            ap.error("--selftest needs CAPTURE and EXPECTED_CSV")
        return selftest(a.capture, a.expected)
    res = decode_file(a.capture)
    print(summary(res))
    if a.out:
        write_csv(res, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
