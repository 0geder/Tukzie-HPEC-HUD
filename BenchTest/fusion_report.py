#!/usr/bin/env python3
"""Summaries of the camera and ToF fusion log for test C9
(BenchTest/TEST_PROCEDURES.md). The log is written by the telemetry
bridge (--fusion-log, one JSON line per fused update, see
CameraDetection/sensor_fusion.py). Use one log file per test step.

  python fusion_report.py summary LOG
  python fusion_report.py f1 LOG [--class person]
  python fusion_report.py f2 LOG:TAPE_M [LOG:TAPE_M ...] [--class person] [--tol 0.05]
  python fusion_report.py f3 LOG --tape 0.8
  python fusion_report.py f4 LOG --tape 2.5 [--class person]

--skip-s N drops the first N seconds of each log (walking into place).
Distances in metres. Pass rules are the ones in C9.
"""
import argparse
import json
import statistics
import sys


def load(path, skip_s=0.0):
    recs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except ValueError:
                continue
    if recs and skip_s > 0:
        t0 = recs[0]["t_mono"]
        recs = [r for r in recs if r["t_mono"] - t0 >= skip_s]
    return recs


def target(rec, cls=None):
    """The nearest hazard of class cls (any camera class if None, never a
    ToF-only obstacle), or None."""
    hs = [h for h in rec.get("hazards", [])
          if h["source"] != "tof" and (cls is None or h["class"] == cls)]
    hs.sort(key=lambda h: (h["distance_m"] is None, h["distance_m"] or 0.0))
    return hs[0] if hs else None


def err_stats(values, tape):
    """Count, median value, median and maximum absolute error against tape."""
    if not values:
        return None
    errs = [abs(v - tape) for v in values]
    return {"n": len(values), "median": statistics.median(values),
            "med_err": statistics.median(errs), "max_err": max(errs), "errs": errs}


def fmt(x, nd=3):
    return "-" if x is None else ("%.*f" % (nd, x))


def summary(recs):
    out = {"updates": len(recs), "by_source": {}, "by_class": {}}
    for r in recs:
        for h in r.get("hazards", []):
            out["by_source"][h["source"]] = out["by_source"].get(h["source"], 0) + 1
            out["by_class"][h["class"]] = out["by_class"].get(h["class"], 0) + 1
    if len(recs) > 1:
        out["duration_s"] = recs[-1]["t_mono"] - recs[0]["t_mono"]
    fps = [r["camera_fps"] for r in recs if r.get("camera_fps")]
    out["camera_fps_median"] = statistics.median(fps) if fps else None
    out["camera_absent"] = sum(1 for r in recs if r.get("camera_age_ms") is None)
    return out


def f1(recs, cls):
    """Bearing sequence of the walk-across: runs of the same source and sensor."""
    runs = []
    t0 = recs[0]["t_mono"] if recs else 0.0
    for r in recs:
        h = target(r, cls)
        key = (h["source"], h["sensor"]) if h else ("none", None)
        t = r["t_mono"] - t0
        b = h["bearing_deg"] if h else None
        if runs and runs[-1]["key"] == key:
            run = runs[-1]
            run["t1"] = t
            run["n"] += 1
            if b is not None:
                run["b"].append(b)
        else:
            runs.append({"key": key, "t0": t, "t1": t, "n": 1, "b": [] if b is None else [b]})
    bearings = [b for run in runs for b in run["b"]]
    steps = [b2 - b1 for b1, b2 in zip(bearings, bearings[1:]) if abs(b2 - b1) > 0.5]
    direction = 0
    if steps:
        direction = 1 if sum(1 for s in steps if s > 0) >= len(steps) / 2 else -1
    monotonic = (sum(1 for s in steps if s * direction > 0) / len(steps)) if steps else None
    order = [run["key"][1] for run in runs if run["key"][0] == "fused"]
    order = [s for i, s in enumerate(order) if i == 0 or s != order[i - 1]]
    return {"runs": runs, "monotonic_fraction": monotonic, "direction": direction, "fused_sensor_order": order}


def f2(recs, tape, cls, tol):
    with_obj = [target(r, cls) for r in recs]
    with_obj = [h for h in with_obj if h is not None]
    fused = [h["distance_m"] for h in with_obj if h["source"] == "fused"]
    camera = [h["camera_distance_m"] for h in with_obj if h["camera_distance_m"] is not None]
    fs = err_stats(fused, tape)
    cs = err_stats(camera, tape)
    out = {"tape": tape, "updates": len(recs), "with_object": len(with_obj),
           "fused_fraction": (len(fused) / len(with_obj)) if with_obj else 0.0, "fused": fs, "camera": cs}
    if fs:
        out["fused_within_tol"] = sum(1 for e in fs["errs"] if e <= tol) / fs["n"]
    if tape <= 1.2:
        out["pass"] = bool(fs and fs["med_err"] <= tol and out["fused_fraction"] >= 0.8)
    else:
        out["pass"] = out["fused_fraction"] <= 0.1   # beyond ToF range: expected camera-only
    return out


def f3(recs, tape, sensor="ahead"):
    tof = []
    cam_hits = 0
    for r in recs:
        hs = r.get("hazards", [])
        obs = [h for h in hs if h["source"] == "tof" and h["sensor"] == sensor]
        if obs:
            tof.append(obs[0]["distance_m"])
        if any(h["source"] != "tof" for h in hs):
            cam_hits += 1
    out = {"updates": len(recs), "tof_only": len(tof),
           "tof_fraction": len(tof) / len(recs) if recs else 0.0,
           "camera_or_fused_updates": cam_hits, "tof": err_stats(tof, tape) if tape is not None else None}
    out["pass"] = out["tof_fraction"] >= 0.9 and cam_hits == 0
    return out


def f4(recs, tape, cls):
    hs = [target(r, cls) for r in recs]
    hs = [h for h in hs if h is not None]
    cam = [h for h in hs if h["source"] == "camera"]
    fused = [h for h in hs if h["source"] == "fused"]
    out = {"updates": len(recs), "with_object": len(hs), "camera_only": len(cam), "fused": len(fused),
           "camera": err_stats([h["camera_distance_m"] for h in cam if h["camera_distance_m"] is not None], tape)
           if tape is not None else None}
    out["pass"] = bool(hs) and len(fused) == 0 and len(hs) >= 0.9 * len(recs)
    return out


def print_stats(label, s):
    if not s:
        print("  %-8s none" % label)
        return
    print("  %-8s n=%d median %s m, error median %s m, max %s m" % (
        label, s["n"], fmt(s["median"]), fmt(s["med_err"]), fmt(s["max_err"])))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("test", choices=("summary", "f1", "f2", "f3", "f4"))
    ap.add_argument("logs", nargs="+", help="log files; for f2 LOG:TAPE_M")
    ap.add_argument("--class", dest="cls", default=None, help="camera class to follow (default: any)")
    ap.add_argument("--tape", type=float, default=None, help="tape distance, m (f3, f4)")
    ap.add_argument("--tol", type=float, default=0.05, help="f2 pass tolerance, m (default 0.05)")
    ap.add_argument("--sensor", default="ahead", help="f3: sensor facing the box (default ahead)")
    ap.add_argument("--skip-s", type=float, default=0.0)
    a = ap.parse_args(argv)
    ok = True
    for spec in a.logs:
        path, tape = spec, a.tape
        if a.test == "f2":
            path, _, t = spec.rpartition(":")
            if not path or not t:
                ap.error("f2 needs LOG:TAPE_M, e.g. c9_f2_050.jsonl:0.5")
            tape = float(t)
        recs = load(path, a.skip_s)
        print("%s  %s  (%d updates)" % (a.test.upper(), path, len(recs)))
        if not recs:
            print("  empty log")
            ok = False
            continue
        if a.test == "summary":
            s = summary(recs)
            print("  %.1f s, camera fps median %s, %d updates without camera" % (
                s.get("duration_s", 0.0), fmt(s["camera_fps_median"], 1), s["camera_absent"]))
            print("  hazards by source: %s" % s["by_source"])
            print("  hazards by class: %s" % s["by_class"])
        elif a.test == "f1":
            r = f1(recs, a.cls)
            for run in r["runs"]:
                src, sensor = run["key"]
                b = run["b"]
                print("  %6.1f-%6.1f s  %-6s %-6s n=%3d  bearing %s" % (
                    run["t0"], run["t1"], src, sensor or "", run["n"],
                    "%.1f to %.1f" % (b[0], b[-1]) if b else "-"))
            print("  direction %s, %s of bearing steps in that direction, fused sensors in order: %s" % (
                {1: "left to right", -1: "right to left", 0: "none"}[r["direction"]],
                "-" if r["monotonic_fraction"] is None else "%.0f%%" % (100 * r["monotonic_fraction"]),
                " > ".join(r["fused_sensor_order"]) or "none"))
        elif a.test == "f2":
            r = f2(recs, tape, a.cls, a.tol)
            print("  tape %.3f m: object in %d of %d updates, fused in %.0f%%" % (
                tape, r["with_object"], r["updates"], 100 * r["fused_fraction"]))
            print_stats("fused", r["fused"])
            print_stats("camera", r["camera"])
            if "fused_within_tol" in r:
                print("  fused within %.2f m of the tape: %.0f%%" % (a.tol, 100 * r["fused_within_tol"]))
            print("  %s" % ("PASS" if r["pass"] else "FAIL"))
            ok = ok and r["pass"]
        elif a.test == "f3":
            r = f3(recs, a.tape, a.sensor)
            print("  ToF-only obstacle (%s) in %d of %d updates (%.0f%%); updates with a camera or fused hazard: %d" % (
                a.sensor, r["tof_only"], r["updates"], 100 * r["tof_fraction"], r["camera_or_fused_updates"]))
            print_stats("tof", r["tof"])
            print("  %s" % ("PASS" if r["pass"] else "FAIL"))
            ok = ok and r["pass"]
        elif a.test == "f4":
            r = f4(recs, a.tape, a.cls)
            print("  object in %d of %d updates: camera-only %d, fused %d" % (
                r["with_object"], r["updates"], r["camera_only"], r["fused"]))
            print_stats("camera", r["camera"])
            print("  %s" % ("PASS" if r["pass"] else "FAIL"))
            ok = ok and r["pass"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
