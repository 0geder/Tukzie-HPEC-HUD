"""Pothole detector per Planning/pothole-definition.md (proposal of 22 Oct 2026).

Input: vertical acceleration, band-passed 2 to 40 Hz, positive up (dsp.Chunk.bp). Signature of a pothole: a drop as
the wheel falls in, then a sharp positive spike at the far edge, within 0.3 s.

Candidate (no threshold yet): every local maximum (spike) at sample p with, in the preceding cfg.ph_window_s, a
minimum (drop) at q such that
  - the drop is negative and comes first (drop-then-spike order),
  - duration t_p - t_q is within cfg.ph_min_dur_s to cfg.ph_max_dur_s,
  - the drop is at least cfg.ph_drop_fraction of the peak-to-peak (a + spike alone is not a pothole),
  - no rise before the drop larger than half the spike within half a window (a speed bump rises first);
features: peak-to-peak bp[p] - bp[q], duration, drop, spike, speed at the time. Candidates closer than
cfg.ph_refractory_s keep only the largest.
Event: a candidate with peak-to-peak >= threshold(v) = a + b v (speed-dependent threshold, step 4).

Calibration (steps 2 to 4): smooth passes give the false-alarm distribution, obstacle passes (plank drop or a
measured pothole) the event amplitude. If an obstacle pass has a labelled time, the candidate nearest it within
cfg.ph_label_tol_s is the event; otherwise the largest candidate in the pass is taken (stated in the output).
The speed shape g(v) = 1 + c v is fitted from smooth-road noise (per-pass 99th percentile of candidate p2p against
mean speed); the scale k is swept over every candidate score p2p / g(v), giving the ROC table (detection rate on
obstacle passes, false alarms per km on smooth passes). The chosen k is among those with false alarms per km at
most cfg.ph_fa_per_km (without speed, so no distance: no false alarm on smooth passes) that reach the highest
detection rate; of those, the middle of the range is taken, for the largest margin on both sides.
Then a = k and b = k c.
"""
import numpy as np
from scipy import signal as ss


def candidates(t, bp, fs, cfg, speed=None, min_p2p=0.0):
    """Drop-then-spike candidates in one contiguous signal. speed: array like bp (m/s) or None."""
    bp = np.asarray(bp, float)
    t = np.asarray(t, float)
    W = int(round(cfg.ph_window_s * fs))
    pk, _ = ss.find_peaks(bp, height=0.0)
    out = []
    for p in pk:
        a = max(0, p - W)
        if p - a < 2:
            continue
        q = a + int(np.argmin(bp[a:p]))
        drop, spike = bp[q], bp[p]
        if drop >= 0:
            continue
        p2p = spike - drop
        dur = (p - q) / fs
        if p2p < min_p2p or not (cfg.ph_min_dur_s <= dur <= cfg.ph_max_dur_s):
            continue
        if -drop < cfg.ph_drop_fraction * p2p:
            continue
        pre = bp[max(0, q - W // 2):q]
        if len(pre) and pre.max() > 0.5 * spike:
            continue
        v = float(speed[p]) if speed is not None else float("nan")
        out.append({"t": float(t[p]), "t_drop": float(t[q]), "drop": float(drop), "spike": float(spike),
                    "p2p": float(p2p), "duration_s": float(dur), "speed": v})
    return suppress(out, cfg.ph_refractory_s)


def suppress(cands, refractory_s):
    keep = []
    for c in sorted(cands, key=lambda c: -c["p2p"]):
        if all(abs(c["t"] - k["t"]) >= refractory_s for k in keep):
            keep.append(c)
    return sorted(keep, key=lambda c: c["t"])


def threshold(v, a, b=0.0):
    v = np.asarray(v, float)
    return a + b * np.where(np.isfinite(v), v, 0.0)


def detect(cands, a, b=0.0):
    return [c for c in cands if c["p2p"] >= threshold(c["speed"], a, b)]


def candidates_vertical(vert, t0, t1, cfg, speed_fn=None):
    """Candidates of a dsp.Vertical over [t0, t1), chunk by chunk."""
    out = []
    for c in vert.chunks:
        m = (c.t >= t0) & (c.t < t1)
        if m.sum() < 4:
            continue
        sp = np.array([speed_fn(x) for x in c.t[m]]) if speed_fn is not None else None
        out += candidates(c.t[m], c.bp[m], c.fs, cfg, sp)
    return out


def calibrate(smooth, obstacle, cfg):
    """smooth, obstacle: lists of dicts {"name", "cands", "km" (or NaN), "speed" (mean, or NaN), "t_event" (opt)}.

    Returns {"a", "b", "c", "k", "roc": [rows], "obstacle_events": [...], "basis": text}.
    """
    # speed shape from smooth-road noise
    xs = [(p["speed"], np.quantile([c["p2p"] for c in p["cands"]], 0.99)) for p in smooth
          if p["cands"] and np.isfinite(p.get("speed", np.nan))]
    c_shape = 0.0
    if len({round(x[0], 1) for x in xs}) >= 2:
        sl, ic = np.polyfit([x[0] for x in xs], [x[1] for x in xs], 1)
        c_shape = max(0.0, sl / ic) if ic > 0 else 0.0
    g = lambda v: 1.0 + c_shape * (v if np.isfinite(v) else 0.0)
    smooth_scores = np.array([c["p2p"] / g(c["speed"]) for p in smooth for c in p["cands"]])
    km = float(np.nansum([p.get("km", np.nan) for p in smooth])) if smooth else 0.0
    have_km = smooth and all(np.isfinite(p.get("km", np.nan)) for p in smooth) and km > 0
    ev, basis = [], []
    for p in obstacle:
        cs = p["cands"]
        if not cs:
            ev.append({"name": p["name"], "score": 0.0, "p2p": np.nan, "speed": p.get("speed", np.nan)})
            continue
        if p.get("t_event") is not None:
            near = [c for c in cs if abs(c["t"] - p["t_event"]) <= cfg.ph_label_tol_s]
            c = max(near, key=lambda c: c["p2p"]) if near else None
            basis.append("labelled")
        else:
            c = max(cs, key=lambda c: c["p2p"])
            basis.append("largest candidate")
        ev.append({"name": p["name"], "score": c["p2p"] / g(c["speed"]) if c else 0.0,
                   "p2p": c["p2p"] if c else np.nan, "speed": c["speed"] if c else np.nan})
    ob_scores = np.array([e["score"] for e in ev])
    ks = np.unique(np.r_[smooth_scores, ob_scores, 0.0])
    ks = np.r_[ks, ks.max() * 1.01 + 1e-9] if len(ks) else np.array([1.0])
    roc = []
    for k in ks:
        fa = int(np.sum(smooth_scores >= k))
        roc.append({"k": float(k), "detection_rate": float(np.mean(ob_scores >= k)) if len(ob_scores) else np.nan,
                    "false_alarms": fa, "fa_per_km": fa / km if have_km else np.nan})
    if have_km:
        ok = [r for r in roc if r["fa_per_km"] <= cfg.ph_fa_per_km]
        rule = f"smallest k with false alarms per km <= {cfg.ph_fa_per_km}"
    else:
        ok = [r for r in roc if r["false_alarms"] == 0]
        rule = "smallest k with no false alarm on smooth passes (distance unknown)"
    if ok:
        # highest detection rate within the false-alarm limit; among the k that reach it, the middle of the range
        # (maximum margin between smooth-road noise and obstacle events), not its edge
        dmax = max(r["detection_rate"] for r in ok)
        ks_ok = [r["k"] for r in ok if r["detection_rate"] == dmax]
        k = 0.5 * (min(ks_ok) + max(ks_ok))
        fa = int(np.sum(smooth_scores >= k))
        best = {"k": float(k), "detection_rate": float(np.mean(ob_scores >= k)) if len(ob_scores) else np.nan,
                "false_alarms": fa, "fa_per_km": fa / km if have_km else np.nan}
        rule += "; middle of the k range with the highest detection rate"
    else:
        best = roc[-1]
        k = best["k"]
    return {"a": k, "b": k * c_shape, "c": c_shape, "k": k, "rule": rule, "chosen": best, "roc": roc,
            "obstacle_events": ev, "basis": sorted(set(basis)), "smooth_km": km if have_km else np.nan}


def evaluate(events, label_t, label_type, tol_s=0.5, types=("pothole",), t_range=None, km=np.nan):
    """Match detections to video labels of the given types (nearest, one-to-one, within tol_s)."""
    lt = np.asarray(label_t, float)
    ly = np.asarray(label_type, object)
    m = np.array([any(ty in str(x).lower() for ty in types) for x in ly], bool) if len(ly) else np.zeros(0, bool)
    lt = lt[m]
    if t_range is not None:
        lt = lt[(lt >= t_range[0]) & (lt < t_range[1])]
        events = [e for e in events if t_range[0] <= e["t"] < t_range[1]]
    used = np.zeros(len(lt), bool)
    tp = 0
    matches = []
    for e in sorted(events, key=lambda e: -e["p2p"]):
        if not len(lt):
            break
        d = np.abs(lt - e["t"])
        d[used] = np.inf
        j = int(np.argmin(d))
        if d[j] <= tol_s:
            used[j] = True
            tp += 1
            matches.append((e["t"], float(lt[j])))
    fp = len(events) - tp
    fn = int(len(lt) - used.sum())
    return {"labels": int(len(lt)), "detections": len(events), "tp": tp, "fp": fp, "fn": fn,
            "recall": tp / len(lt) if len(lt) else np.nan,
            "precision": tp / len(events) if events else np.nan,
            "fa_per_km": fp / km if np.isfinite(km) and km > 0 else np.nan, "matches": matches}
