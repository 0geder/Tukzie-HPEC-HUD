"""Position-aligned bin ICC for a session driven as laps without section lines (27 Oct 2026).

    python -m BenchTest.analysis.position_icc --session <folder> --out <folder>/analysis [--cell 8]

The pipeline's bin ICC (run.py) bins each pass by distance from its start marker, which only lines up places on the
road when every pass starts at the same line. Run 2 was driven as laps in a car park with markers derived from speed,
so each pass starts somewhere else on the loop. Here each IMU sample is placed on the road by the phone's GNSS fix
(1 Hz RMC, linearly interpolated to the sample time), the ground is cut into square cells, and the rows of the ICC
are the cells that every pass in the group drove through for at least min_s seconds. Direction of travel is ignored:
the same patch of road is the same row. The cell is chosen to be about twice the phone's position error, so the fix
error moves samples into a neighbouring cell rather than across the loop.

Groups (from the derived markers and the GNSS location): smooth loop 10 km/h passes p1 to p5, rough strip 10 km/h
passes p7 to p10. Outputs repeatability_position_icc.csv/.tex in <out>/tables and a line in the printed summary.
"""
import argparse
import glob
import os

import numpy as np

from . import config as cfgmod
from . import dsp
from . import readers as rd
from . import report as rp
from . import run as rn
from . import segment as sg
from . import stats as stt

GROUPS = {"smooth loop 10 km/h": ["R2 A v10 p1", "R2 A v10 p2", "R2 A v10 p3", "R2 A v10 p4", "R2 A v10 p5"],
          "rough strip 10 km/h": ["R2 A v10 p7", "R2 A v10 p8", "R2 A v10 p9", "R2 A v10 p10"]}


def phone_track(session):
    """Phone GNSS fixes (Pi epoch, east m, north m) from the RMC lines, local flat-earth frame."""
    tt, la, lo = [], [], []

    def deg(x, h):
        d = int(float(x) / 100)
        v = d + (float(x) - d * 100) / 60
        return -v if h in "SW" else v

    for p in sorted(glob.glob(os.path.join(session, "*phone_gps*.txt"))):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                f = line.split(" ", 1)
                if len(f) < 2 or "RMC," not in f[1]:
                    continue
                q = f[1].split(",")
                try:
                    if q[2] != "A":
                        continue
                    tt.append(float(f[0])); la.append(deg(q[3], q[4])); lo.append(deg(q[5], q[6]))
                except (ValueError, IndexError):
                    continue
    o = np.argsort(tt)
    t, la, lo = np.array(tt)[o], np.array(la)[o], np.array(lo)[o]
    lat0, lon0 = float(np.median(la)), float(np.median(lo))
    x = (lo - lon0) * 111320.0 * np.cos(np.radians(lat0))
    y = (la - lat0) * 111320.0
    return t, x, y


def load_verts(session, out, cfg):
    """Vertical streams per node, as run.analyse_session builds them (host time stamp clock)."""
    rec_files = sorted(glob.glob(os.path.join(session, "*_roadtest.jsonl")))
    markers, _ = rd.read_markers(rec_files, os.path.join(session, "roadtest_markers.txt"))
    runs = [sg.classify_run(r, cfg) for r in sg.runs_from_markers(markers, cfg.start_word, cfg.stop_word, None)]
    verts = {}
    for node, plist in rn._find_raw(session, cfg).items():
        p, _ = rn._pick_raw(plist, runs, os.path.join(out, "_raw"), node)
        for (nd, _imu), s in rd.read_raw_stream(p, node).items():
            if np.isfinite(s.host_t).sum() < 2:
                continue
            verts[f"{nd}{s.imu}"] = dsp.make_vertical(s, cfg, rd.fit_clock(s.t_s, s.host_t)[:2])
    return verts, {r.name: (r.t0, r.t1) for r in runs}


def cell_values(vert, t0, t1, track, cell, min_s):
    """a_w and sigma per ground cell for one pass: {(i, j): (a_w, sigma, seconds)}."""
    tg, xg, yg = track
    wk, bp, ts, fs = [], [], [], None
    for c in vert.chunks:
        m = (c.t >= t0) & (c.t < t1)
        if m.any():
            wk.append(c.wk[m]); bp.append(c.bp[m]); ts.append(c.t[m]); fs = c.fs
    if not wk:
        return {}
    wk, bp, ts = np.concatenate(wk), np.concatenate(bp), np.concatenate(ts)
    ok = (ts >= tg[0]) & (ts <= tg[-1])
    wk, bp, ts = wk[ok], bp[ok], ts[ok]
    x, y = np.interp(ts, tg, xg), np.interp(ts, tg, yg)
    ij = np.stack([np.floor(x / cell), np.floor(y / cell)], axis=1).astype(int)
    out = {}
    for key in {tuple(k) for k in ij}:
        m = (ij[:, 0] == key[0]) & (ij[:, 1] == key[1])
        n = int(m.sum())
        if n >= min_s * fs:
            out[key] = (dsp.rms(wk[m]), dsp.rms(bp[m] - bp[m].mean()), n / fs)
    return out


def group_icc(per_pass, metric):
    """ICC with the cells every pass covered as rows. per_pass: {name: {cell: (a_w, sigma, s)}}."""
    k = 0 if metric == "a_w" else 1
    common = set.intersection(*[set(v) for v in per_pass.values()]) if per_pass else set()
    cells = sorted(common)
    table = {p: [v[c][k] for c in cells] for p, v in per_pass.items()}
    res = stt.bin_icc(table, 5, 3)
    return res, cells


def analyse(session, out, cell=8.0, min_s=1.0, cfg=None):
    cfg = cfg or cfgmod.load_config(session)
    track = phone_track(session)
    verts, win = load_verts(session, out, cfg)
    rows = []
    for key in sorted(verts):
        for gname, names in GROUPS.items():
            names = [n for n in names if n in win]
            per = {n: cell_values(verts[key], *win[n], track, cell, min_s) for n in names}
            for metric in ("a_w", "sigma"):
                res, cells = group_icc(per, metric)
                rows.append({"stream": key, "group": gname, "metric": metric, "cell_m": cell, "min_s": min_s,
                             "cells_per_pass": " ".join(str(len(v)) for v in per.values()),
                             **rn._icc_cols(res)})
    tdir = os.path.join(out, "tables")
    os.makedirs(tdir, exist_ok=True)
    rp.write_table(rows, os.path.join(tdir, f"repeatability_position_icc_{int(cell)}m"))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="position-aligned bin ICC from phone GNSS")
    ap.add_argument("--session", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cell", type=float, default=8.0, help="ground cell side, m")
    ap.add_argument("--min-s", type=float, default=1.0, help="least time a pass spends in a cell for it to count, s")
    a = ap.parse_args(argv)
    for r in analyse(a.session, a.out, a.cell, a.min_s):
        ci = r["ICC(2,1) CI"]
        print(f"{r['stream']:7s} {r['group']:20s} {r['metric']:6s} rows={r['n_rows']:3d} k={r['k_passes']} "
              f"cells/pass=[{r['cells_per_pass']}] ICC(2,1)={r['ICC(2,1)']:.2f} CI={ci} ICC(3,1)={r['ICC(3,1)']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
