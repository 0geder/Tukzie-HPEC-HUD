"""Markers from the data, for a session driven without typed markers (27 Oct 2026).

    python -m BenchTest.analysis.auto_markers --session <folder> [--write] [--from HH:MM --to HH:MM]

Reads the phone's NMEA log (*phone_gps*.txt, "<Pi epoch> <sentence>") for speed and the recorder files
(*_roadtest.jsonl, src "rear", esp32.i) for battery current, and finds:
  - road passes: moving stretches between stops (speed under 2 km/h for at least 4 s), at least 8 s long; the pass
    window is the steady part, where speed is within 25 % of the stretch's 75th percentile; the target speed is the
    nearest of 10, 15 and 20 km/h when within 30 %, otherwise the rounded speed;
  - coasting: a pass whose steady part has battery current under 1 A for at least 70 % of the records;
  - stand runs: current above 2 A for at least 20 s while the phone reads under 1 km/h (wheel raised); the setting
    L, M or H is given by the run's mean current in thirds of the current range across the stand runs;
  - still periods (S0): at least 50 s with speed under 0.5 km/h and current under 0.5 A, the first and the last.
It prints the markers, and with --write appends them to <session>/roadtest_markers.txt as time-stamped lines
("<epoch> R2 A v10 p1 start"), which the analysis reads like typed markers. Every marker it writes is derived,
so the report must say so: pass windows from GNSS speed and current, not from typed markers or video.
"""
import argparse
import glob
import json
import os
import time

import numpy as np


def phone_speed(session):
    tt, vv = [], []
    for p in sorted(glob.glob(os.path.join(session, "*phone_gps*.txt"))):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                f = line.split(" ", 1)
                if len(f) < 2 or "RMC," not in f[1]:
                    continue
                parts = f[1].split(",")
                try:
                    if parts[2] != "A" or parts[7] == "":
                        continue
                    tt.append(float(f[0])); vv.append(float(parts[7]) * 1.852)
                except (ValueError, IndexError):
                    continue
    o = np.argsort(tt)
    return np.array(tt)[o], np.array(vv)[o]


def vehicle_speed(session):
    """The vehicle receiver's speed (esp32.spd_raw, knots per the A76XX manual) from the recorder, with a fix only."""
    tt, vv = [], []
    for p in sorted(glob.glob(os.path.join(session, "*_roadtest.jsonl"))):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"src":"rear"' not in line.replace(" ", ""):
                    continue
                try:
                    d = json.loads(line)
                    e = (d.get("data") or {}).get("esp32") or {}
                    if e.get("fix") is True and e.get("spd_raw") is not None:
                        tt.append(float(d["t"])); vv.append(float(e["spd_raw"]) * 1.852)
                except (ValueError, KeyError, TypeError):
                    continue
    o = np.argsort(tt)
    return np.array(tt)[o], np.array(vv)[o]


def combined_speed(session):
    """Phone speed where the phone has a fix; the vehicle receiver's where it does not (gaps over 3 s)."""
    tp, vp = phone_speed(session)
    tv, vv = vehicle_speed(session)
    if not len(tv):
        return tp, vp, 0
    if len(tp):
        gap = np.array([np.min(np.abs(tp - x)) > 3.0 for x in tv])
    else:
        gap = np.ones(len(tv), bool)
    t = np.concatenate([tp, tv[gap]]); v = np.concatenate([vp, vv[gap]])
    o = np.argsort(t)
    return t[o], v[o], int(gap.sum())


def battery_current(session):
    tt, ii = [], []
    for p in sorted(glob.glob(os.path.join(session, "*_roadtest.jsonl"))):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"src":"rear"' not in line.replace(" ", ""):
                    continue
                try:
                    d = json.loads(line)
                    e = (d.get("data") or {}).get("esp32") or {}
                    if e.get("i") is not None and (e.get("bms_age_s") or 0) < 5:
                        tt.append(float(d["t"])); ii.append(float(e["i"]))
                except (ValueError, KeyError, TypeError):
                    continue
    o = np.argsort(tt)
    return np.array(tt)[o], np.array(ii)[o]


def _runs(mask):
    """(start, end) index pairs of True runs."""
    out, start = [], None
    for k, m in enumerate(mask):
        if m and start is None:
            start = k
        elif not m and start is not None:
            out.append((start, k - 1)); start = None
    if start is not None:
        out.append((start, len(mask) - 1))
    return out


def find_passes(t, v, it, iv):
    moving = v > 2.0
    segs, cur = [], None
    for a, b in _runs(moving):
        if cur is not None and t[a] - t[cur[1]] < 4.0:          # stop shorter than 4 s: same stretch
            cur = (cur[0], b)
        else:
            if cur is not None:
                segs.append(cur)
            cur = (a, b)
    if cur is not None:
        segs.append(cur)
    passes = []
    for a, b in segs:
        if t[b] - t[a] < 8.0:
            continue
        vs = v[a:b + 1]
        top = np.percentile(vs, 75)
        steady = np.where(np.abs(vs - top) <= 0.25 * top)[0]
        if len(steady) < 4:
            continue
        t0, t1 = t[a + steady[0]], t[a + steady[-1]]
        vm = float(np.median(vs[steady]))
        target = min((10, 15, 20), key=lambda x: abs(x - vm))
        label = target if abs(target - vm) <= 0.3 * target else int(round(vm))
        sel = (it >= t0) & (it <= t1)
        coast = bool(sel.sum() >= 3 and np.mean(np.abs(iv[sel]) < 1.0) >= 0.7)
        passes.append({"t0": t0, "t1": t1, "v_median": vm, "label": label, "coast": coast})
    return passes


def find_stands(t, v, it, iv):
    if not len(it):
        return []
    still = np.array([(np.interp(x, t, v) if len(t) else 0.0) < 1.0 for x in it])
    out = []
    for a, b in _runs((iv > 2.0) & still):
        # split where the current level steps (settings run back to back): 5-record median changes by over 30 %
        cuts, k = [a], a + 5
        while k <= b - 5:
            m0, m1 = np.median(iv[max(cuts[-1], k - 5):k]), np.median(iv[k:k + 5])
            if abs(m1 - m0) > 0.3 * max(m0, m1):
                cuts.append(k); k += 10
            else:
                k += 1
        cuts.append(b + 1)
        for c0, c1 in zip(cuts, cuts[1:]):
            if it[c1 - 1] - it[c0] >= 20.0:
                out.append({"t0": it[c0], "t1": it[c1 - 1], "i_mean": float(np.mean(iv[c0:c1]))})
    if out:
        lo, hi = min(s["i_mean"] for s in out), max(s["i_mean"] for s in out)
        for s in out:
            k = 0 if hi - lo < 0.5 else min(2, int(3 * (s["i_mean"] - lo) / (hi - lo + 1e-9)))
            s["setting"] = "LMH"[k]
    return out


def find_still(t, v, it, iv):
    out = []
    for a, b in _runs(v < 0.5):
        if t[b] - t[a] < 50.0:
            continue
        # within a stop, the stretches with no battery current (motor off), at least 50 s
        quiet = np.array([not np.any((np.abs(it - x) <= 1.5) & (np.abs(iv) >= 0.5)) for x in t[a:b + 1]])
        for c0, c1 in _runs(quiet):
            ta, tb = t[a + c0], t[a + c1]
            if tb - ta >= 50.0:
                out.append({"t0": ta + 5, "t1": ta + 65 if tb - ta > 70 else tb})
    return [out[0], out[-1]] if len(out) > 1 else out


def build(session, t_from=None, t_to=None):
    t, v, n_vehicle = combined_speed(session)
    if n_vehicle:
        print(f"note: {n_vehicle} vehicle-receiver speed records fill gaps in the phone log")
    it, iv = battery_current(session)
    if t_from is not None:
        keep = (t >= t_from) & (t <= t_to); t, v = t[keep], v[keep]
        keep = (it >= t_from) & (it <= t_to); it, iv = it[keep], iv[keep]
    if len(t) < 10:
        raise SystemExit("not enough phone GPS fixes in the session to find passes")
    lines, counts = [], {}
    for s in find_still(t, v, it, iv):
        lines += [(s["t0"], "R2 S0 still start"), (s["t1"], "R2 S0 still end")]
    for n, s in enumerate(find_stands(t, v, it, iv), 1):
        lines += [(s["t0"], f"R2 STANDS {s['setting']} r{n} start"), (s["t1"], f"R2 STANDS {s['setting']} r{n} end")]
    for p in find_passes(t, v, it, iv):
        key = "coast" if p["coast"] else f"v{p['label']}"
        counts[key] = counts.get(key, 0) + 1
        name = f"R2 A {'coast v' + str(p['label']) if p['coast'] else 'v' + str(p['label'])} p{counts[key]}"
        lines += [(p["t0"], name + " start"), (p["t1"], name + " end")]
    return sorted(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--write", action="store_true", help="append the markers to <session>/roadtest_markers.txt")
    ap.add_argument("--from", dest="t_from", help="HH:MM local time, limit to the test window")
    ap.add_argument("--to", dest="t_to")
    a = ap.parse_args()
    tf = tt = None
    if a.t_from and a.t_to:
        day = time.localtime()
        def ep(hm):
            h, m = map(int, hm.split(":"))
            return time.mktime((day.tm_year, day.tm_mon, day.tm_mday, h, m, 0, 0, 0, -1))
        tf, tt = ep(a.t_from), ep(a.t_to)
    lines = build(a.session, tf, tt)
    for t, text in lines:
        print(time.strftime("%H:%M:%S", time.localtime(t)), text)
    print(f"{len(lines)} markers")
    if a.write:
        with open(os.path.join(a.session, "roadtest_markers.txt"), "a", encoding="utf-8") as fh:
            fh.write("# derived by auto_markers.py from phone GNSS speed and BMS current, %s\n"
                     % time.strftime("%Y-%m-%d %H:%M"))
            for t, text in lines:
                fh.write("%.3f %s\n" % (t, text))
        print("appended to", os.path.join(a.session, "roadtest_markers.txt"))


if __name__ == "__main__":
    main()
