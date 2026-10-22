"""Signal processing for the raw 200 Hz IMU stream.

Chain (per IMU, per contiguous chunk of samples):
  1. chunking: a time gap over cfg.max_gap_s splits the stream; shorter gaps (missing sequence numbers) are filled
     by linear interpolation on a uniform grid at the chunk's measured mean rate, and the count is reported;
  2. gravity direction: each axis low-passed at cfg.gravity_lp_hz (2nd-order Butterworth, zero phase); the unit
     vector g_hat(t) of that low-passed specific force points up (an accelerometer at rest reads +1 g upward);
  3. vertical acceleration a_v = a . g_hat - |g_lp|: the dynamic vertical specific force, positive up, so a wheel
     dropping into a hole gives a negative excursion and the impact at the far edge a positive spike;
  4. band-pass cfg.band_lo_hz to cfg.band_hi_hz (Butterworth, order cfg.band_order per edge, zero phase);
  5. ISO 2631-1 Wk weighting of a_v (wk_filter), giving a_w (r.m.s.) and VDV;
  6. per-second features on the band-passed signal: sigma, crest factor on (a - mean), peak-to-peak, jerk after a
     cfg.jerk_lp_hz low-pass differentiated with the measured sample times, and a clipping flag.

ISO 2631-1:1997 Annex A, weighting Wk (vertical, seated, z axis), as implemented in wk_response():
  band limiting   high-pass  f1 = 0.4 Hz,  Q1 = 1/sqrt(2)     H_h = s^2 / (s^2 + w1 s/Q1 + w1^2)
                  low-pass   f2 = 100 Hz,  Q2 = 1/sqrt(2)     H_l = w2^2 / (s^2 + w2 s/Q2 + w2^2)
  a-v transition  f3 = f4 = 12.5 Hz, Q4 = 0.63             H_t = (1 + s/w3) / (1 + s/(Q4 w4) + s^2/w4^2)
  upward step     f5 = 2.37 Hz, Q5 = 0.91, f6 = 3.35 Hz, Q6 = 0.91
                                                     H_s = (s^2 + w5 s/Q5 + w5^2) / (s^2 + w6 s/Q6 + w6^2)
  Wk = H_h H_l H_t H_s, with w_i = 2 pi f_i.
Verification (tests/test_dsp.py): |Wk| at the 37 one-third-octave nominal frequencies 0.1 to 400 Hz agrees with the
tabulated Wk factors of ISO 2631-1 Table 3 (as transcribed in WK_TABLE3 below) within 0.3 %. Both the parameters
and the table were transcribed from the standard as recalled, not read from a copy in this repository (the
repository holds no copy of ISO 2631-1); their mutual agreement to three figures at 37 points is the check. Read
both against the standard before the result is cited.
"""
from dataclasses import dataclass, field

import numpy as np
from scipy import signal as ss

from .config import G0, Config

# ---------------------------------------------------------------------------------------------------------------
# ISO 2631-1 Wk
# ---------------------------------------------------------------------------------------------------------------
WK_PARAMS = {"f1": 0.4, "Q1": 2 ** -0.5, "f2": 100.0, "Q2": 2 ** -0.5, "f3": 12.5, "f4": 12.5, "Q4": 0.63,
             "f5": 2.37, "Q5": 0.91, "f6": 3.35, "Q6": 0.91}

# ISO 2631-1 Table 3, Wk weighting factor x 1000 at the nominal one-third-octave frequencies (transcribed, see above)
WK_TABLE3 = {0.1: 31.2, 0.125: 48.6, 0.16: 79.0, 0.2: 121, 0.25: 182, 0.315: 263, 0.4: 352, 0.5: 418, 0.63: 459,
             0.8: 477, 1.0: 482, 1.25: 484, 1.6: 494, 2.0: 531, 2.5: 631, 3.15: 804, 4.0: 967, 5.0: 1039,
             6.3: 1054, 8.0: 1036, 10.0: 988, 12.5: 902, 16.0: 768, 20.0: 636, 25.0: 513, 31.5: 405, 40.0: 314,
             50.0: 246, 63.0: 186, 80.0: 132, 100.0: 88.7, 125.0: 54.0, 160.0: 28.5, 200.0: 15.2, 250.0: 7.9,
             315.0: 3.98, 400.0: 1.95}


def wk_response(f, band_limiting=True, p=WK_PARAMS):
    """Complex frequency response of Wk at frequencies f (Hz)."""
    s = 2j * np.pi * np.asarray(f, float)
    w = {k: 2 * np.pi * v for k, v in p.items() if k.startswith("f")}
    ht = (1 + s / w["f3"]) / (1 + s / (p["Q4"] * w["f4"]) + (s / w["f4"]) ** 2)
    hs = (s ** 2 + w["f5"] * s / p["Q5"] + w["f5"] ** 2) / (s ** 2 + w["f6"] * s / p["Q6"] + w["f6"] ** 2)
    h = ht * hs
    if band_limiting:
        h = h * s ** 2 / (s ** 2 + w["f1"] * s / p["Q1"] + w["f1"] ** 2)
        h = h * w["f2"] ** 2 / (s ** 2 + w["f2"] * s / p["Q2"] + w["f2"] ** 2)
    return h


def wk_filter(x, fs, band_limiting=True):
    """Apply Wk to a uniformly sampled signal by multiplying its spectrum by the analog response (causal phase).

    Exact for the analog weighting at every frequency up to fs/2; at fs = 200 Hz the 100 Hz band-limiting pole lies
    at the Nyquist frequency, where a bilinear-transform IIR would distort, which is why the spectral method is used.
    The signal is zero-padded to at least twice its length so the impulse-response tail does not wrap.
    """
    x = np.asarray(x, float)
    n = len(x)
    if n == 0:
        return x.copy()
    nfft = 1 << int(np.ceil(np.log2(2 * n + 16)))
    X = np.fft.rfft(x, nfft)
    f = np.fft.rfftfreq(nfft, 1.0 / fs)
    return np.fft.irfft(X * wk_response(f, band_limiting), nfft)[:n]


def rms(x):
    x = np.asarray(x, float)
    return float(np.sqrt(np.mean(x ** 2))) if len(x) else float("nan")


def vdv(x, fs):
    """Vibration dose value (ISO 2631-1 eq. 5): (integral of a^4 dt)^(1/4), m/s^1.75."""
    x = np.asarray(x, float)
    return float((np.sum(x ** 4) / fs) ** 0.25)


# ---------------------------------------------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------------------------------------------

def _sosfiltfilt(sos, x):
    x = np.asarray(x, float)
    padlen = min(3 * (2 * len(sos) + 1) * 4, max(len(x) - 1, 0))
    if len(x) < 4:
        return x.copy()
    return ss.sosfiltfilt(sos, x, axis=0, padlen=padlen)


def lowpass(x, fs, fc, order=2):
    if fc >= fs / 2:
        return np.asarray(x, float).copy()
    return _sosfiltfilt(ss.butter(order, fc, "low", fs=fs, output="sos"), x)


def bandpass(x, fs, lo, hi, order=4):
    hi = min(hi, 0.45 * fs)
    return _sosfiltfilt(ss.butter(order, [lo, hi], "band", fs=fs, output="sos"), x)


# ---------------------------------------------------------------------------------------------------------------
# Chunking and vertical projection
# ---------------------------------------------------------------------------------------------------------------

@dataclass
class Chunk:
    t: np.ndarray            # uniform grid, host epoch s (or device s if no clock map)
    fs: float
    acc: np.ndarray          # N x 3 on the grid, m/s^2
    av: np.ndarray           # dynamic vertical specific force, m/s^2
    bp: np.ndarray           # band-passed av
    wk: np.ndarray           # Wk-weighted av
    lp: np.ndarray           # av low-passed at jerk_lp_hz
    clip: np.ndarray         # any axis at or beyond the clipping level (on the grid)
    tm: np.ndarray           # measured sample times, same clock as t
    lpm: np.ndarray          # lp at the measured times
    filled: int = 0          # samples filled by interpolation (missing sequence numbers)
    g_hat: np.ndarray = None


@dataclass
class Vertical:
    node: str
    imu: int
    chunks: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def select(self, t0, t1, key):
        """Concatenate attribute `key` over the grid samples with t0 <= t < t1, with chunk boundaries."""
        parts = []
        for c in self.chunks:
            m = (c.t >= t0) & (c.t < t1)
            if m.any():
                parts.append((c, m))
        return parts


def _gravity(acc, fs, fc):
    n = len(acc)
    if n < 10 * fs / max(fc, 1e-3) / 10:      # shorter than ~1/fc: use the chunk mean
        g = np.repeat(acc.mean(axis=0, keepdims=True), n, axis=0)
    else:
        g = lowpass(acc, fs, fc, order=2)
    return g


def make_vertical(stream, cfg: Config = None, clock=None, t_range=None):
    """Process one ImuStream into a Vertical (chunks of projected, filtered signals).

    clock: (offset, rate) from readers.fit_clock / dash_clock to put times on the host clock; else device time
    (or the per-sample host time if every sample has one and no clock is given). t_range limits the time span.
    """
    cfg = cfg or Config()
    t_dev = stream.t_us * 1e-6
    if clock is not None:
        t = clock[0] + clock[1] * t_dev
    else:
        t = t_dev
    acc, seq = stream.acc, stream.seq
    if t_range is not None:
        m = (t >= t_range[0]) & (t < t_range[1])
        t, acc, seq = t[m], acc[m], seq[m]
    out = Vertical(stream.node, stream.imu)
    if len(t) < 2:
        return out
    clip_level = cfg.clip_fraction * cfg.accel_range_g * G0
    brk = np.flatnonzero(np.diff(t) > cfg.max_gap_s) + 1
    filled_total = 0
    for a, b in zip(np.r_[0, brk], np.r_[brk, len(t)]):
        if b - a < max(8, int(0.5 * cfg.fs)):
            continue
        tc, ac, sc = t[a:b], acc[a:b], seq[a:b]
        n_grid = int(sc[-1] - sc[0] + 1)
        fs = (n_grid - 1) / (tc[-1] - tc[0]) if tc[-1] > tc[0] else cfg.fs
        tg = tc[0] + np.arange(n_grid) / fs
        # place samples on the grid by sequence number, fill the missing ones by interpolation in time
        acc_g = np.column_stack([np.interp(tg, tc, ac[:, k]) for k in range(3)])
        filled = n_grid - len(tc)
        filled_total += filled
        g = _gravity(acc_g, fs, cfg.gravity_lp_hz)
        gn = np.linalg.norm(g, axis=1)
        g_hat = g / gn[:, None]
        av = np.sum(acc_g * g_hat, axis=1) - gn
        bp = bandpass(av, fs, cfg.band_lo_hz, cfg.band_hi_hz, cfg.band_order)
        wk = wk_filter(av, fs)
        lp = lowpass(av, fs, cfg.jerk_lp_hz, order=4)
        clip = np.any(np.abs(acc_g) >= clip_level, axis=1)
        out.chunks.append(Chunk(t=tg, fs=fs, acc=acc_g, av=av, bp=bp, wk=wk, lp=lp, clip=clip, tm=tc,
                                lpm=np.interp(tc, tg, lp), filled=filled, g_hat=g_hat.mean(axis=0)))
    out.stats = {"chunks": len(out.chunks), "filled_samples": filled_total,
                 "samples": int(sum(len(c.t) for c in out.chunks)),
                 "fs_measured": [round(c.fs, 3) for c in out.chunks][:20]}
    return out


# ---------------------------------------------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------------------------------------------

def window_features(x, tm=None, lpm=None, clip=None, fs=200.0):
    """Features of one window. x: band-passed vertical; tm, lpm: measured times and 20 Hz low-passed signal there."""
    x = np.asarray(x, float)
    d = x - x.mean()
    sd = float(np.sqrt(np.mean(d ** 2)))
    out = {"n": len(x), "sigma": sd, "crest": float(np.max(np.abs(d)) / sd) if sd > 0 else float("nan"),
           "p2p": float(x.max() - x.min()), "rms": rms(x)}
    if tm is not None and len(tm) > 1:
        dt = np.diff(tm)
        ok = dt > 0
        out["jerk"] = float(np.mean(np.abs(np.diff(lpm))[ok] / dt[ok])) if ok.any() else float("nan")
    else:
        out["jerk"] = float("nan")
    out["clipped"] = bool(np.any(clip)) if clip is not None else False
    return out


def per_second(vert: Vertical, t0=-np.inf, t1=np.inf, window_s=1.0):
    """Per-window features over [t0, t1): list of dicts with t (window start) and the window_features keys."""
    rows = []
    for c in vert.chunks:
        lo, hi = max(t0, c.t[0]), min(t1, c.t[-1] + 1 / c.fs)
        if hi - lo < window_s:
            continue
        nw = int((hi - lo) // window_s)
        for k in range(nw):
            a, b = lo + k * window_s, lo + (k + 1) * window_s
            m = (c.t >= a) & (c.t < b)
            mm = (c.tm >= a) & (c.tm < b)
            if m.sum() < 0.8 * window_s * c.fs:
                continue
            r = window_features(c.bp[m], c.tm[mm], c.lpm[mm], c.clip[m], c.fs)
            r["t"] = a
            rows.append(r)
    return rows


def pass_metrics(vert: Vertical, t0, t1, cfg: Config = None, speed_fn=None):
    """Metrics of one pass over [t0, t1): a_w, VDV, overall sigma, per-second medians, clipping, speed index.

    speed_fn(t) -> speed in m/s (NaN where unknown); the index sigma^2 / v uses only windows with v >= v_min.
    """
    cfg = cfg or Config()
    wk, bp, n, fs = [], [], 0, cfg.fs
    vdv4 = 0.0
    clipped = 0
    for c in vert.chunks:
        m = (c.t >= t0) & (c.t < t1)
        if not m.any():
            continue
        wk.append(c.wk[m])
        bp.append(c.bp[m])
        vdv4 += np.sum(c.wk[m] ** 4) / c.fs
        clipped += int(c.clip[m].sum())
        n += int(m.sum())
        fs = c.fs
    if n == 0:
        return {"n": 0}
    wk, bp = np.concatenate(wk), np.concatenate(bp)
    secs = per_second(vert, t0, t1, cfg.window_s)
    sig = np.array([r["sigma"] for r in secs]) if secs else np.array([])
    out = {"n": n, "coverage": n / (fs * (t1 - t0)) if t1 > t0 else float("nan"),
           "a_w": rms(wk), "vdv": float(vdv4 ** 0.25), "sigma": rms(bp - bp.mean()),
           "sigma_1s_median": float(np.median(sig)) if len(sig) else float("nan"),
           "crest_1s_median": float(np.median([r["crest"] for r in secs])) if secs else float("nan"),
           "jerk_1s_median": float(np.nanmedian([r["jerk"] for r in secs])) if secs else float("nan"),
           "p2p_max": float(bp.max() - bp.min()), "clipped_samples": clipped, "windows": len(secs)}
    if speed_fn is not None and secs:
        v = np.array([speed_fn(r["t"] + cfg.window_s / 2) for r in secs], float)
        ok = np.isfinite(v) & (v >= cfg.v_min_mps)
        out["speed_mean"] = float(np.nanmean(v)) if np.isfinite(v).any() else float("nan")
        out["index_sigma2_per_v"] = float(np.mean(sig[ok] ** 2 / v[ok])) if ok.any() else float("nan")
        out["index_windows"] = int(ok.sum())
    return out


def speed_index(sigma, v, v_min=1.0):
    """sigma^2 / v where v >= v_min, NaN elsewhere (report eq. speed-index)."""
    sigma, v = np.asarray(sigma, float), np.asarray(v, float)
    out = np.full(np.broadcast(sigma, v).shape, np.nan)
    ok = np.isfinite(v) & (v >= v_min)
    out[ok] = (np.broadcast_to(sigma, out.shape)[ok] ** 2) / np.broadcast_to(v, out.shape)[ok]
    return out
