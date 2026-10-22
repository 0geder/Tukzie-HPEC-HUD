"""Front-to-rear delay by cross-correlation, and speed = wheelbase / delay.

The rear wheels meet a road feature one wheelbase after the front wheel, so the rear vertical acceleration is, in
part, a delayed copy of the front one. The delay is the lag of the cross-correlation peak, searched between
cfg.delay_min_s and cfg.delay_max_s, refined to sub-sample precision by a parabola through the peak and its two
neighbours. Confidence: the pass is cut into cfg.delay_window_s windows (50 % overlap), each window gives a delay
and a peak correlation; the reported delay is the whole-pass estimate with a percentile bootstrap 95 % CI of the
median over windows whose peak correlation is at least min_corr.

Limits to state with any result: the two nodes are separate ESP32 boards, so their samples are put on one clock
through each node's map to the host clock (readers.fit_clock); an error in that map is a direct error in the delay
(10 ms is 3 % at a 0.3 s delay). The trike has one front wheel and two rear wheels on different tracks, so the
correlation can be weak even with a good clock.
"""
import numpy as np
from scipy import signal as ss


def xcorr_delay(x, y, fs, min_lag_s=0.0, max_lag_s=1.0):
    """Delay (s) of y relative to x (positive: y lags x) and the normalised correlation at the peak."""
    x = np.asarray(x, float) - np.mean(x)
    y = np.asarray(y, float) - np.mean(y)
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    den = np.sqrt(np.sum(x ** 2) * np.sum(y ** 2))
    if n < 4 or den == 0:
        return float("nan"), float("nan")
    c = ss.correlate(y, x, mode="full", method="fft") / den
    lags = np.arange(-n + 1, n)
    lo, hi = int(np.ceil(min_lag_s * fs)), int(np.floor(max_lag_s * fs))
    m = (lags >= lo) & (lags <= hi)
    if not m.any():
        return float("nan"), float("nan")
    cm = c[m]
    j = int(np.argmax(cm))
    k = np.flatnonzero(m)[j]
    frac = 0.0
    if 0 < k < len(c) - 1:
        y0, y1, y2 = c[k - 1], c[k], c[k + 1]
        d = y0 - 2 * y1 + y2
        if d < 0:
            frac = 0.5 * (y0 - y2) / d
    return float((lags[k] + frac) / fs), float(cm[j])


def _common(front, rear, t0, t1, fs):
    """Front and rear band-passed signals on one uniform grid over [t0, t1); samples outside chunks are NaN."""
    tg = np.arange(t0, t1, 1.0 / fs)
    out = []
    for v in (front, rear):
        y = np.full(len(tg), np.nan)
        for c in v.chunks:
            m = (tg >= c.t[0]) & (tg <= c.t[-1])
            y[m] = np.interp(tg[m], c.t, c.bp)
        out.append(y)
    return tg, out[0], out[1]


def front_rear_delay(front, rear, t0, t1, fs=200.0, wheelbase_m=None, min_lag_s=0.03, max_lag_s=1.5,
                     window_s=5.0, min_corr=0.3, n_boot=2000, seed=1, clock_sd_s=None):
    """Delay and speed for one pass from two dsp.Vertical objects on the same (host) clock."""
    tg, a, b = _common(front, rear, t0, t1, fs)
    ok = np.isfinite(a) & np.isfinite(b)
    res = {"t0": t0, "t1": t1, "overlap_s": float(ok.sum() / fs)}
    if ok.sum() < 2 * max_lag_s * fs:
        res.update({"delay_s": np.nan, "corr": np.nan, "note": "too little overlapping data"})
        return res
    a0, b0 = np.where(ok, a, 0.0), np.where(ok, b, 0.0)
    d, c = xcorr_delay(a0, b0, fs, min_lag_s, max_lag_s)
    res.update({"delay_s": d, "corr": c})
    # windowed estimates
    w = int(window_s * fs)
    ds, cs = [], []
    for s in range(0, len(tg) - w + 1, max(w // 2, 1)):
        sl = slice(s, s + w)
        if ok[sl].mean() < 0.9:
            continue
        dw, cw = xcorr_delay(a0[sl], b0[sl], fs, min_lag_s, min(max_lag_s, window_s / 2))
        ds.append(dw)
        cs.append(cw)
    ds, cs = np.array(ds), np.array(cs)
    good = np.isfinite(ds) & (cs >= min_corr)
    res.update({"windows": int(len(ds)), "windows_used": int(good.sum())})
    if good.sum() >= 3:
        rng = np.random.default_rng(seed)
        g = ds[good]
        bs = np.median(g[rng.integers(0, len(g), (n_boot, len(g)))], axis=1)
        res.update({"delay_median_s": float(np.median(g)), "delay_ci_lo": float(np.quantile(bs, 0.025)),
                    "delay_ci_hi": float(np.quantile(bs, 0.975)), "delay_window_sd_s": float(np.std(g, ddof=1))})
    else:
        res.update({"delay_median_s": np.nan, "delay_ci_lo": np.nan, "delay_ci_hi": np.nan})
    if clock_sd_s is not None:
        res["clock_sd_s"] = clock_sd_s
    if wheelbase_m:
        res["speed_mps"] = wheelbase_m / d if d and np.isfinite(d) and d > 0 else np.nan
        lo, hi = res.get("delay_ci_lo", np.nan), res.get("delay_ci_hi", np.nan)
        res["speed_ci_lo"] = wheelbase_m / hi if np.isfinite(hi) and hi > 0 else np.nan
        res["speed_ci_hi"] = wheelbase_m / lo if np.isfinite(lo) and lo > 0 else np.nan
    return res
