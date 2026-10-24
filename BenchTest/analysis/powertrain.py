"""Powertrain against road (RQ4): Welch spectra of stationary runs per motor setting and of road passes.

Band. Every RQ4 number uses the RQ4 band cfg.pt_band_lo_hz to cfg.pt_band_hi_hz (default 0.5 to 80 Hz) of the
unfiltered vertical acceleration (dsp.Chunk.av), not the 2 to 40 Hz ride band: the stand runs of 23 Oct put the
powertrain lines at 40 to 70 Hz (42.75, 49.0 and 64.0 Hz, rear and front), which a 2 to 40 Hz band cannot see. The
upper edge stays below Nyquist (100 Hz at 200 Hz) and below the MPU-6050 low-pass corner (DLPF 94 Hz). Each output
row names the band it used ("band_hz") and gives the energy in each of cfg.pt_sub_bands as well (register B3).

Lines. A narrow-band peak is a local maximum of the spectrum in dB that stands at least cfg.peak_prominence_db above
the background (a running median over cfg.peak_background_hz) and is at most 2 * cfg.peak_halfwidth_hz wide at half
its prominence. Peaks found in the stationary runs are the powertrain lines (motor, gearing, inverter). On the road
the lines move with speed, so for each pass the lines are placed by one of two methods (named in "line_method"):
  orders   a line at order o of the wheel rotation lies at o * v / C (v the pass speed, C the measured drive-wheel
           circumference); the tolerance is cfg.peak_halfwidth_hz plus o * sd(v) / C, so speed changes within the
           pass widen the band. Orders come from cfg.pt_orders, else from the stand peaks divided by the wheel rate
           on the stands (cfg.stand_wheel_hz, from the slow-motion video of the wheel mark).
  fixed    without a speed, a circumference or orders: the stand lines (this session's, else cfg.pt_stand_lines_hz
           from 23 Oct) with +-cfg.peak_halfwidth_hz. Valid only near the stand wheel speed; stated in the output.
Line share = energy within the line bands / energy in the whole RQ4 band. The stationary-to-road ratio is a stand
run's RQ4-band energy over the road pass's. A small line share means the road response is not dominated by the
powertrain at those lines.

Coasting (register B2): coast_vs_powered compares each coasting pass with the powered passes on the same section whose
mean speed is within cfg.coast_match_mps, band by band, in dB.
"""
import numpy as np
from scipy import signal as ss
from scipy.ndimage import median_filter


def welch(x, fs, seg_s=4.0):
    n = min(len(x), int(seg_s * fs))
    if n < 16:
        return np.array([]), np.array([])
    return ss.welch(np.asarray(x, float), fs=fs, nperseg=n, noverlap=n // 2, detrend="constant")


def psd_of(vert, t0, t1, seg_s=4.0, key="av"):
    """Welch PSD of a dsp.Vertical attribute over [t0, t1), averaged over chunks weighted by their segment count."""
    acc_p, wsum, f_ref = None, 0.0, None
    for c in vert.chunks:
        m = (c.t >= t0) & (c.t < t1)
        x = getattr(c, key)[m]
        if len(x) < int(seg_s * c.fs):
            continue
        f, p = welch(x, c.fs, seg_s)
        if f_ref is None:
            f_ref, acc_p = f, np.zeros_like(p)
        if len(f) != len(f_ref):
            p = np.interp(f_ref, f, p)
        w = len(x) / (seg_s * c.fs)
        acc_p += w * p
        wsum += w
    if f_ref is None:
        return np.array([]), np.array([])
    return f_ref, acc_p / wsum


def narrow_peaks(f, p, prominence_db=10.0, background_hz=5.0, max_width_hz=2.0, f_lo=0.5, f_hi=None):
    f, p = np.asarray(f), np.asarray(p)
    if len(f) < 8:
        return []
    df = f[1] - f[0]
    db = 10 * np.log10(np.maximum(p, 1e-30))
    k = max(3, int(round(background_hz / df)) | 1)
    bg = median_filter(db, size=k, mode="nearest")
    rel = db - bg
    idx, props = ss.find_peaks(rel, height=prominence_db, width=(None, max(1.0, max_width_hz / df)),
                               rel_height=0.5)
    out = []
    f_hi = f_hi if f_hi is not None else f[-1]
    for j, i in enumerate(idx):
        if f_lo <= f[i] <= f_hi:
            out.append({"f_hz": float(f[i]), "above_background_db": float(rel[i]), "psd": float(p[i]),
                        "width_hz": float(props["widths"][j] * df)})
    return out


def band_energy(f, p, lo, hi):
    m = (f >= lo) & (f <= hi)
    return float(np.trapezoid(p[m], f[m])) if m.sum() > 1 else 0.0


def _band_name(lo, hi):
    return f"{lo:g}-{hi:g}"


def orders_from_stands(peaks, stand_wheel_hz, merge=0.02):
    """Orders (line frequency / wheel rate) from stand peaks at settings whose wheel rate was measured.

    peaks: {setting: [peak dicts]}; stand_wheel_hz: {setting: wheel rev/s}. Orders within `merge` (relative) of each
    other are merged (mean). Returns a sorted list.
    """
    raw = sorted(pk["f_hz"] / stand_wheel_hz[s] for s, v in peaks.items() for pk in v
                 if stand_wheel_hz.get(s) and stand_wheel_hz[s] > 0)
    out = []
    for o in raw:
        if out and abs(o - out[-1][-1]) <= merge * o:
            out[-1].append(o)
        else:
            out.append([o])
    return [float(np.mean(g)) for g in out]


def line_bands(cfg, fixed_hz, orders=(), speed=np.nan, speed_sd=np.nan):
    """[(centre Hz, half-width Hz)] for one pass and the method text, inside the RQ4 band."""
    lo, hi = cfg.pt_band_lo_hz, cfg.pt_band_hi_hz
    C = cfg.wheel_circumference_m
    if orders and C and np.isfinite(speed) and speed >= cfg.v_min_mps:
        w = speed / C
        dw = speed_sd / C if np.isfinite(speed_sd) else 0.0
        bands = [(o * w, cfg.peak_halfwidth_hz + o * dw) for o in orders]
        how = (f"orders {', '.join(f'{o:.2f}' for o in orders)} x wheel rate {w:.3f} Hz (v {speed:.2f} m/s, "
               f"C {C:g} m)")
    else:
        missing = [n for n, ok in (("orders", bool(orders)), ("wheel circumference", bool(C)),
                                   ("speed", np.isfinite(speed) and speed >= cfg.v_min_mps)) if not ok]
        bands = [(fl, cfg.peak_halfwidth_hz) for fl in fixed_hz]
        how = (f"fixed stand lines +-{cfg.peak_halfwidth_hz:g} Hz (no {', no '.join(missing)}; valid only near the "
               f"stand wheel speed)")
    return [(c, h) for c, h in bands if lo <= c <= hi], how


def band_row(f, p, cfg, bands):
    """Energies of one spectrum: RQ4 band, sub-bands and line bands, with shares of the RQ4 band."""
    lo, hi = cfg.pt_band_lo_hz, cfg.pt_band_hi_hz
    tot = band_energy(f, p, lo, hi)
    m = np.zeros(len(f), bool)
    for c, h in bands:
        m |= np.abs(f - c) <= h
    m &= (f >= lo) & (f <= hi)
    line_e = float(np.trapezoid(np.where(m, p, 0.0), f)) if m.any() else 0.0
    row = {"band_hz": _band_name(lo, hi), "band_energy": tot, "line_energy": line_e,
           "line_share": line_e / tot if tot > 0 else np.nan,
           "lines_hz": [round(c, 2) for c, _ in bands], "line_halfwidth_hz": [round(h, 2) for _, h in bands]}
    for a, b in cfg.pt_sub_bands:
        e = band_energy(f, p, a, b)
        row[f"E_{_band_name(a, b)}"] = e
        row[f"share_{_band_name(a, b)}"] = e / tot if tot > 0 else np.nan
    return row


def powertrain(stationary, road, cfg, speeds=None):
    """stationary: {setting: (f, P)} (may be empty); road: {pass name: (f, P)};
    speeds: {pass name: (mean m/s, sd m/s, source text)}.

    Returns peaks, lines, orders, per-pass rows and the per-stand rows, every number in the RQ4 band.
    """
    speeds = speeds or {}
    peaks = {s: narrow_peaks(f, p, cfg.peak_prominence_db, cfg.peak_background_hz, 2 * cfg.peak_halfwidth_hz,
                             f_lo=cfg.pt_band_lo_hz, f_hi=min(f[-1], cfg.pt_band_hi_hz)) if len(f) else []
             for s, (f, p) in stationary.items()}
    lines = sorted({round(pk["f_hz"], 2) for v in peaks.values() for pk in v})
    if lines:
        fixed, fixed_src = lines, "stand runs of this session"
    else:
        fixed, fixed_src = list(cfg.pt_stand_lines_hz), "stand runs of 23 Oct (config pt_stand_lines_hz)"
    if cfg.pt_orders:
        orders, orders_src = list(cfg.pt_orders), "config pt_orders"
    else:
        orders = orders_from_stands(peaks, cfg.stand_wheel_hz) if cfg.stand_wheel_hz else []
        orders_src = "stand peaks / stand_wheel_hz" if orders else "none (no pt_orders and no stand wheel rate)"
    stand_rows = []
    for s, (f, p) in stationary.items():
        if len(f):
            b, _ = line_bands(cfg, fixed)
            stand_rows.append({"setting": s, **band_row(f, p, cfg, b),
                               "line_method": f"stand lines +-{cfg.peak_halfwidth_hz:g} Hz ({fixed_src})"})
    rows = []
    for name, (f, p) in road.items():
        if not len(f):
            continue
        v, vsd, src = speeds.get(name, (np.nan, np.nan, ""))
        b, how = line_bands(cfg, fixed, orders, v, vsd)
        row = {"pass": name, **band_row(f, p, cfg, b), "line_method": how, "speed_mps": v, "speed_source": src}
        for s, (fs_, ps_) in stationary.items():
            if len(fs_):
                se = band_energy(fs_, ps_, cfg.pt_band_lo_hz, cfg.pt_band_hi_hz)
                row[f"stationary_{s}_over_road"] = se / row["band_energy"] if row["band_energy"] > 0 else np.nan
        rows.append(row)
    return {"peaks": peaks, "lines_hz": lines, "fixed_lines_hz": fixed, "fixed_lines_source": fixed_src,
            "orders": orders, "orders_source": orders_src, "band_hz": [cfg.pt_band_lo_hz, cfg.pt_band_hi_hz],
            "ratios": rows, "stands": stand_rows}


def coast_vs_powered(rows, kinds, sections, cfg):
    """Coasting against powered passes at matched mean speed (register B2), per band in dB.

    rows: powertrain()["ratios"]; kinds, sections: {pass name: kind / section}. For each coasting pass with a speed,
    the powered passes (any kind but coast) on the same section with |v - v_coast| <= cfg.coast_match_mps are averaged
    and 10 log10(powered / coast) is given for the RQ4 band, each sub-band and the line energy.
    """
    keys = ["band_energy", "line_energy"] + [f"E_{_band_name(a, b)}" for a, b in cfg.pt_sub_bands]
    out = []
    for r in rows:
        if kinds.get(r["pass"]) != "coast":
            continue
        v = r.get("speed_mps", np.nan)
        res = {"coast_pass": r["pass"], "section": sections.get(r["pass"], ""), "speed_mps": v,
               "match_tol_mps": cfg.coast_match_mps}
        if not np.isfinite(v):
            res["note"] = "no speed for this coasting pass: not matched"
            out.append(res)
            continue
        mates = [q for q in rows if kinds.get(q["pass"]) not in ("coast", None) and
                 sections.get(q["pass"]) == res["section"] and np.isfinite(q.get("speed_mps", np.nan)) and
                 abs(q["speed_mps"] - v) <= cfg.coast_match_mps]
        res["powered_passes"] = [q["pass"] for q in mates]
        res["n_powered"] = len(mates)
        for k in keys:
            pw = np.mean([q[k] for q in mates]) if mates else np.nan
            res[f"dB_{k}"] = float(10 * np.log10(pw / r[k])) if mates and r[k] > 0 and pw > 0 else np.nan
        if not mates:
            res["note"] = "no powered pass on this section within the speed tolerance"
        out.append(res)
    return out
