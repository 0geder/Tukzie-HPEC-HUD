"""Powertrain against road (RQ4): Welch spectra of stationary runs per motor setting and of road passes.

A narrow-band peak is a local maximum of the spectrum in dB that stands at least cfg.peak_prominence_db above the
background (a running median over cfg.peak_background_hz) and is at most 2 * cfg.peak_halfwidth_hz wide at half
its prominence. Peaks found in the stationary runs are the powertrain lines (motor, gearing, inverter). For each
road pass the band energy ratio is the energy within +-cfg.peak_halfwidth_hz of those lines divided by the energy
in the analysis band cfg.band_lo_hz to cfg.band_hi_hz; and the stationary-to-road ratio is the stationary run's
band energy over the road pass's. A small ratio means the road response is not dominated by the powertrain.
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


def powertrain(stationary, road, cfg):
    """stationary: {setting: (f, P)}; road: {pass name: (f, P)}. Returns peaks, ratios and a flat table."""
    peaks = {s: narrow_peaks(f, p, cfg.peak_prominence_db, cfg.peak_background_hz, 2 * cfg.peak_halfwidth_hz,
                             f_lo=cfg.band_lo_hz / 2, f_hi=min(f[-1], 0.45 * cfg.fs)) if len(f) else []
             for s, (f, p) in stationary.items()}
    lines = sorted({round(pk["f_hz"], 2) for v in peaks.values() for pk in v})
    rows = []
    for name, (f, p) in road.items():
        if not len(f):
            continue
        tot = band_energy(f, p, cfg.band_lo_hz, cfg.band_hi_hz)
        m = np.zeros(len(f), bool)
        for fl in lines:
            m |= np.abs(f - fl) <= cfg.peak_halfwidth_hz
        m &= (f >= cfg.band_lo_hz) & (f <= cfg.band_hi_hz)
        line_e = float(np.trapezoid(np.where(m, p, 0.0), f)) if m.any() else 0.0
        row = {"pass": name, "band_energy": tot, "line_energy_ratio": line_e / tot if tot > 0 else np.nan}
        for s, (fs_, ps_) in stationary.items():
            if len(fs_):
                se = band_energy(fs_, ps_, cfg.band_lo_hz, cfg.band_hi_hz)
                row[f"stationary_{s}_over_road"] = se / tot if tot > 0 else np.nan
        rows.append(row)
    return {"peaks": peaks, "lines_hz": lines, "ratios": rows}
