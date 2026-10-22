"""Road-characterisation pipeline, one command, no hand steps.

    python -m BenchTest.analysis.run --session BenchTest/logs/roadtest_2026-10-19 --out <folder>
        [--config file.json] [--wheelbase 1.9] [--labels labels.csv] [--tz 2]

Session folder contents used:
  *_roadtest.jsonl          recorder file(s) (BenchTest/road_logger.py), all read in name order
  roadtest_markers.txt      extra markers (only time-stamped lines; the recorder already copies the others in)
  *raw*.txt|.log|.csv       raw IMU stream per node ("front"/"rear" in the name), or cfg.raw_files
  labels.csv                video labels (time, type), or --labels / cfg.labels_csv
  session.json              config overrides (keys of config.Config)

Writes to --out: tables/*.csv and *.tex, figures/*.pdf and *.png, summary.json. Every analysis that cannot run on
the data present (no raw stream, no markers, no speed, no wheelbase, no labels) is skipped and the reason is
written in summary.json under "skipped", so nothing is filled with a placeholder.
"""
import argparse
import glob
import os
import sys

import numpy as np

from . import config as cfgmod
from . import delay as dl
from . import dsp
from . import pothole as ph
from . import powertrain as pt
from . import readers as rd
from . import report as rp
from . import segment as sg
from . import stats as stt


def _speed_fn(dash, cfg):
    if dash is None or not len(dash):
        return None
    ok = dash.fix & np.isfinite(dash.spd_raw)
    if ok.sum() < 2:
        return None
    t, v = dash.t[ok], dash.spd_raw[ok] * cfg.spd_raw_to_mps

    def f(x):
        if x < t[0] - 2 or x > t[-1] + 2:
            return np.nan
        j = np.searchsorted(t, x)
        near = min(abs(x - t[min(j, len(t) - 1)]), abs(x - t[max(j - 1, 0)]))
        return float(np.interp(x, t, v)) if near <= 3.0 else np.nan
    return f


def _find_raw(session, cfg):
    if cfg.raw_files:
        return {n: os.path.join(session, p) for n, p in cfg.raw_files.items()}
    out = {}
    for p in sorted(glob.glob(os.path.join(session, "*raw*"))):
        if os.path.splitext(p)[1].lower() not in (".txt", ".log", ".csv"):
            continue
        b = os.path.basename(p).lower()
        node = "front" if "front" in b else "rear" if "rear" in b else os.path.splitext(b)[0]
        out[node] = p
    return out


def analyse_session(session, out, cfg=None, labels=None, tz_h=2.0, make_figures=True):
    cfg = cfg or cfgmod.load_config(session)
    tdir, fdir = os.path.join(out, "tables"), os.path.join(out, "figures")
    S = {"session": os.path.abspath(session), "config": cfg.to_dict(), "skipped": {}, "notes": [], "outputs": []}
    rec_files = sorted(glob.glob(os.path.join(session, "*_roadtest.jsonl")))
    S["recorder_files"] = [os.path.basename(p) for p in rec_files]

    # ---- 1. DASH records, dedup, driving --------------------------------------------------------------------
    dash = {}
    for src in ("rear", "front"):
        d = rd.read_dash(rec_files, src, cfg.readable_fields) if rec_files else None
        if d is not None and len(d):
            dash[src] = d
    S["dash"] = {k: v.stats for k, v in dash.items()}
    rear = dash.get("rear")
    segs = []
    if rear is not None:
        drv = sg.label_driving(rear.i, rear.vib, cfg.drive_current_a, cfg.drive_vib)
        segs = sg.driving_segments(rear.t, drv, cfg.drive_join_s)
        rdbl = rear.readable
        vd, vp = rear.vib[drv & rdbl], rear.vib[~drv & rdbl]
        S["driving"] = {
            "rule": f"|i| > {cfg.drive_current_a} A or vib > {cfg.drive_vib}; segments at most {cfg.drive_join_s} s "
                    "apart joined",
            "records_driving": int(drv.sum()), "records_driving_readable": int((drv & rdbl).sum()),
            "records_parked_readable": int((~drv & rdbl).sum()),
            "vib_median_parked": float(np.nanmedian(vp)) if len(vp) else None,
            "vib_median_driving": float(np.nanmedian(vd)) if len(vd) else None,
            "vib_p95_driving": float(np.nanpercentile(vd, 95)) if len(vd) else None,
            "vib_max_driving": float(np.nanmax(vd)) if len(vd) else None,
            "current_max_abs": float(np.nanmax(np.abs(rear.i))) if np.isfinite(rear.i).any() else None,
            "segments": len(segs),
            "segment_seconds_inclusive": float(sum(b - a + 1 for a, b in segs)),
            "gnss_fix_records": int(rear.fix.sum()),
        }
        rows = [{"segment": k + 1, "start_epoch": a, "end_epoch": b, "duration_s": b - a + 1,
                 "records": int(np.sum((rear.t >= a) & (rear.t <= b))),
                 "vib_median": float(np.nanmedian(rear.vib[(rear.t >= a) & (rear.t <= b)]))}
                for k, (a, b) in enumerate(segs)]
        S["outputs"].append(rp.write_table(rows, os.path.join(tdir, "driving_segments")))
    else:
        S["skipped"]["driving"] = "no rear DASH records in the recorder file"

    # ---- 2. markers and runs ------------------------------------------------------------------------------------
    markers, untimed = rd.read_markers(rec_files, os.path.join(session, "roadtest_markers.txt"))
    t_end = max((d.t[-1] for d in dash.values()), default=None)
    runs = [sg.classify_run(r, cfg) for r in sg.runs_from_markers(markers, cfg.start_word, cfg.stop_word, t_end)]
    S["markers"] = [{"t": t, "text": x} for t, x in markers]
    S["markers_untimed"] = untimed
    S["runs"] = [{"name": r.name, "t0": r.t0, "t1": r.t1, "duration_s": r.duration, "closed": r.closed,
                  "section": r.section, "kind": r.kind, "setting": r.setting, "pass_no": r.pass_no} for r in runs]
    if runs:
        S["outputs"].append(rp.write_table(S["runs"], os.path.join(tdir, "runs")))
    else:
        S["skipped"]["runs"] = (f"no '{cfg.start_word}'/'{cfg.stop_word}' marker pairs in the session "
                                f"({len(markers)} markers found)")
    if make_figures and rear is not None:
        S["outputs"].append(rp.fig_session(rear, None, segs, markers, os.path.join(fdir, "session"), tz_h))

    # DASH-only per-run table (works without the raw stream)
    if runs and rear is not None:
        rows = []
        for r in runs:
            m = (rear.t >= r.t0) & (rear.t < r.t1)
            rows.append({"run": r.name, "kind": r.kind, "section": r.section, "records": int(m.sum()),
                         "vib_median": float(np.nanmedian(rear.vib[m])) if m.any() else np.nan,
                         "vib_p95": float(np.nanpercentile(rear.vib[m], 95)) if m.any() else np.nan,
                         "current_median_abs": float(np.nanmedian(np.abs(rear.i[m]))) if m.any() else np.nan})
        S["outputs"].append(rp.write_table(rows, os.path.join(tdir, "runs_dash")))

    # ---- 3. raw streams ----------------------------------------------------------------------------------------
    raw_paths = _find_raw(session, cfg)
    verts = {}
    S["raw"] = {}
    for node, p in raw_paths.items():
        streams = rd.read_raw_stream(p, node)
        for (nd, imu), s in streams.items():
            key = f"{nd}{s.imu}"
            host = s.host_t
            clock, basis = None, "device time (no clock map)"
            pi_edges = cfg.sync_edges.get(nd) if cfg.sync_edges else None
            sc = rd.sync_clock(s, pi_edges) if s.sync is not None else None
            if sc is not None and pi_edges is not None:
                clock, basis = sc[:2], "RAWS sync edges against the Pi's GPIO time stamps"
            elif np.isfinite(host).sum() >= 2:
                clock, basis = rd.fit_clock(s.t_s, host)[:2], "host receive time stamps on the raw lines"
            elif nd in dash and np.isfinite(dash[nd].up_ms).sum() >= 2:
                clock, basis = rd.dash_clock(dash[nd])[:2], f"{nd} DASH up_ms against recorder time"
            v = dsp.make_vertical(s, cfg, clock)
            verts[key] = v
            S["raw"][key] = {"file": os.path.basename(p), **s.stats, **v.stats, "clock": basis}
    if not verts:
        S["skipped"]["raw"] = ("no raw IMU stream file in the session (firmware v0.7.4 had none); a_w, VDV, "
                               "per-second features, repeatability, delay, powertrain and pothole analyses need it")
        rp.write_json(S, os.path.join(out, "summary.json"))
        return S

    speed_fn = _speed_fn(rear, cfg)
    if speed_fn is None:
        S["notes"].append("no GNSS speed (no fix): speed index and speed-dependent threshold use no speed")
    passes = [r for r in runs if r.kind in ("smooth", "obstacle", "other")]
    stationary = [r for r in runs if r.kind == "stationary"]

    # ---- 4. per-pass metrics --------------------------------------------------------------------------------------
    pm_rows = []
    for key, v in verts.items():
        for r in passes + stationary:
            m = dsp.pass_metrics(v, r.t0, r.t1, cfg, speed_fn)
            if m.get("n", 0) == 0:
                continue
            km = m.get("speed_mean", np.nan) * r.duration / 1000 if np.isfinite(m.get("speed_mean", np.nan)) else np.nan
            pm_rows.append({"stream": key, "run": r.name, "section": r.section, "kind": r.kind,
                            "pass_no": r.pass_no, "setting": r.setting, "duration_s": r.duration, "km": km, **m})
    if pm_rows:
        S["outputs"].append(rp.write_table(pm_rows, os.path.join(tdir, "pass_metrics")))
    else:
        S["skipped"]["pass_metrics"] = "no marked run overlaps the raw stream"

    # ---- 5. repeatability --------------------------------------------------------------------------------------------
    S["repeatability"] = {}
    for key in verts:
        rows = [r for r in pm_rows if r["stream"] == key and r["kind"] in ("smooth", "other")]
        if len(rows) < 2:
            continue
        rep = stt.repeatability(rows, n_boot=cfg.n_boot, seed=cfg.seed)
        S["repeatability"][key] = rep
        S["outputs"].append(rp.write_table(rep["per_section"], os.path.join(tdir, f"repeatability_cv_{key}")))
        icc_rows = [{"metric": m, "sections": d["n_sections"], "passes": d["k_passes"], "ICC(2,1)": d["icc2_1"],
                     "ICC(2,1) CI": d["icc2_1_ci"], "ICC(3,1)": d["icc3_1"], "ICC(3,1) CI": d["icc3_1_ci"]}
                    for m, d in rep["icc"].items()]
        if icc_rows:
            S["outputs"].append(rp.write_table(icc_rows, os.path.join(tdir, f"repeatability_icc_{key}")))
        if make_figures:
            S["outputs"].append(rp.fig_pass_metric(rows, "a_w", "$a_w$ (m/s$^2$)",
                                                   os.path.join(fdir, f"pass_aw_{key}")))
    if not S["repeatability"]:
        S["skipped"]["repeatability"] = "fewer than two marked smooth passes on the raw stream"

    # ---- 6. front to rear delay ------------------------------------------------------------------------------------
    fk = next((k for k in verts if k.startswith("front")), None)
    rk = next((k for k in verts if k.startswith("rear")), None)
    if fk and rk and passes:
        rows = []
        for r in passes:
            d = dl.front_rear_delay(verts[fk], verts[rk], r.t0, r.t1, cfg.fs, cfg.wheelbase_m, cfg.delay_min_s,
                                    cfg.delay_max_s, cfg.delay_window_s, n_boot=cfg.n_boot, seed=cfg.seed)
            rows.append({"run": r.name, **d})
        S["delay"] = rows
        S["outputs"].append(rp.write_table(rows, os.path.join(tdir, "front_rear_delay")))
        if not cfg.wheelbase_m:
            S["notes"].append("wheelbase_m not set: delay reported, speed not computed")
    else:
        S["skipped"]["delay"] = "needs raw streams from both a front and a rear node and marked passes"

    # ---- 7. powertrain ------------------------------------------------------------------------------------------------
    key0 = rk or next(iter(verts))
    st_psd = {}
    for r in stationary:
        f, p = pt.psd_of(verts[key0], r.t0, r.t1, cfg.welch_seg_s)
        if len(f):
            st_psd[r.setting or r.name] = (f, p)
    road_psd = {r.name: pt.psd_of(verts[key0], r.t0, r.t1, cfg.welch_seg_s) for r in passes}
    road_psd = {k: v for k, v in road_psd.items() if len(v[0])}
    if st_psd:
        res = pt.powertrain(st_psd, road_psd, cfg)
        S["powertrain"] = {"stream": key0, "peaks": res["peaks"], "lines_hz": res["lines_hz"]}
        prow = [{"setting": s, **pk} for s, v in res["peaks"].items() for pk in v]
        S["outputs"].append(rp.write_table(prow or [{"setting": s, "f_hz": None} for s in res["peaks"]],
                                           os.path.join(tdir, "powertrain_peaks")))
        if res["ratios"]:
            S["outputs"].append(rp.write_table(res["ratios"], os.path.join(tdir, "powertrain_ratios")))
        if make_figures:
            S["outputs"].append(rp.fig_psd(st_psd, road_psd, res["lines_hz"], os.path.join(fdir, "psd"),
                                           (cfg.band_lo_hz, cfg.band_hi_hz)))
    else:
        S["skipped"]["powertrain"] = "no marked stationary run on the raw stream"

    # ---- 8. potholes ----------------------------------------------------------------------------------------------------
    lab_path = labels or cfg.labels_csv or (os.path.join(session, "labels.csv")
                                             if os.path.isfile(os.path.join(session, "labels.csv")) else None)
    if lab_path and not os.path.isabs(lab_path) and not os.path.isfile(lab_path):
        lab_path = os.path.join(session, lab_path)
    lt, ly = rd.read_labels(lab_path) if lab_path and os.path.isfile(lab_path) else (np.array([]), np.array([]))
    S["pothole"] = {"stream": key0}
    pr = []
    for r in passes:
        cands = ph.candidates_vertical(verts[key0], r.t0, r.t1, cfg, speed_fn)
        row = next((x for x in pm_rows if x["stream"] == key0 and x["run"] == r.name), {})
        t_ev = None
        if r.kind == "obstacle" and len(lt):
            m = (lt >= r.t0) & (lt < r.t1)
            t_ev = float(lt[m][0]) if m.any() else None
        pr.append({"name": r.name, "kind": r.kind, "cands": cands, "km": row.get("km", np.nan),
                   "speed": row.get("speed_mean", np.nan), "t_event": t_ev})
    smooth = [p for p in pr if p["kind"] == "smooth"]
    obst = [p for p in pr if p["kind"] == "obstacle"]
    a, b = cfg.ph_threshold_a, cfg.ph_threshold_b
    if smooth and obst:
        cal = ph.calibrate(smooth, obst, cfg)
        a, b = cal["a"], cal["b"]
        S["pothole"]["calibration"] = {k: cal[k] for k in ("a", "b", "c", "rule", "chosen", "basis", "smooth_km",
                                                           "obstacle_events")}
        S["outputs"].append(rp.write_table(cal["roc"], os.path.join(tdir, "pothole_roc")))
        if make_figures:
            S["outputs"].append(rp.fig_roc(cal["roc"], cal["chosen"], os.path.join(fdir, "pothole_roc")))
    elif a is None:
        S["skipped"]["pothole_calibration"] = "needs marked smooth and obstacle passes (or ph_threshold_a in config)"
    if a is not None:
        t0 = min(c.t[0] for c in verts[key0].chunks) if verts[key0].chunks else 0
        t1 = max(c.t[-1] for c in verts[key0].chunks) + 1 if verts[key0].chunks else 0
        drive_segs = segs or [(t0, t1)]
        events = []
        for sa, sb in drive_segs:
            events += ph.detect(ph.candidates_vertical(verts[key0], sa, sb + 1, cfg, speed_fn), a, b)
        S["pothole"]["events"] = len(events)
        S["outputs"].append(rp.write_table(events or [{"t": None}], os.path.join(tdir, "pothole_events")))
        if len(lt):
            km = np.nan
            if speed_fn is not None:
                tt = np.concatenate([np.arange(sa, sb + 1, 1.0) for sa, sb in drive_segs])
                vv = np.array([speed_fn(x) for x in tt])
                km = float(np.nansum(vv) / 1000) if np.isfinite(vv).any() else np.nan
            ev = ph.evaluate(events, lt, ly, cfg.ph_label_tol_s, ("pothole",), (t0, t1), km)
            ev["km"] = km
            S["pothole"]["evaluation"] = ev
            S["outputs"].append(rp.write_table([{k: v for k, v in ev.items() if k != "matches"}],
                                               os.path.join(tdir, "pothole_evaluation")))
        else:
            S["skipped"]["pothole_evaluation"] = "no video labels CSV"
    rp.write_json(S, os.path.join(out, "summary.json"))
    return S


def main(argv=None):
    ap = argparse.ArgumentParser(description="SW-7 road characterisation pipeline")
    ap.add_argument("--session", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--config")
    ap.add_argument("--wheelbase", type=float, help="front to rear axle distance, m (measured)")
    ap.add_argument("--labels", help="video labels CSV (time,type)")
    ap.add_argument("--tz", type=float, default=2.0, help="local time offset for figures, hours")
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args(argv)
    cfg = cfgmod.load_config(a.session, a.config, {"wheelbase_m": a.wheelbase})
    S = analyse_session(a.session, a.out, cfg, a.labels, a.tz, not a.no_figures)
    print("summary:", os.path.join(a.out, "summary.json"))
    for k, v in S["skipped"].items():
        print(f"  skipped {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
