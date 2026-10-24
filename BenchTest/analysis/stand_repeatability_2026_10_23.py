"""Within-run repeatability of the stand runs of 23 October 2026 (run 2, lab part).

Each stand run (and the rest window) is cut into consecutive 10 s windows. Per window and node: the dynamic RMS of
the acceleration magnitude, the RMS in the 40 to 70 Hz band (the powertrain band found on the stands) and the
frequency of the largest spectral line between 30 and 80 Hz. The spread over the windows (CV) shows how repeatable
the measure is while the condition is held, which is the closest the existing data come to RQ1's repeatability;
it is not repeatability over road passes, which needs run 2's road part. The two runs were at different, unrecorded
throttle settings, so they are compared with each other only as different conditions.
Run: python BenchTest/analysis/stand_repeatability_2026_10_23.py
"""
import json
import os
import sys

import numpy as np
from scipy.signal import welch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ss", os.path.join(HERE, "stand_spectra_2026_10_23.py"))
# Reuse the window times, sources and the decoder wrapper without running the figure code.
src = open(os.path.join(HERE, "stand_spectra_2026_10_23.py"), encoding="utf-8").read()
ns = {"__file__": os.path.join(HERE, "stand_spectra_2026_10_23.py")}
exec(src.split("results, spectra = {}, {}")[0], ns)
magnitude, epoch, WINDOWS, SOURCES, FS, LOGS = (ns[k] for k in ("magnitude", "epoch", "WINDOWS", "SOURCES", "FS", "LOGS"))

WIN_S = 10.0


def window_stats(x):
    x = x - x.mean()
    f, p = welch(x, fs=FS, window="hann", nperseg=int(2 * FS), noverlap=int(FS), detrend="linear")
    df = f[1] - f[0]
    band = (f >= 40) & (f <= 70)
    line = (f >= 30) & (f <= 80)
    return {"rms": float(np.sqrt(np.mean(x ** 2))),
            "band_40_70_rms": float(np.sqrt(np.sum(p[band]) * df)),
            "peak_hz": float(f[line][np.argmax(p[line])])}


def cv(v):
    v = np.asarray(v, float)
    return float(100 * v.std(ddof=1) / v.mean()) if len(v) > 1 and v.mean() else None


out = {}
for node, path in SOURCES.items():
    for name, (h0, h1) in WINDOWS.items():
        got = magnitude(path, epoch(h0), epoch(h1))
        if got is None:
            continue
        m, gaps = got
        n = int(WIN_S * FS)
        wins = [window_stats(m[i:i + n]) for i in range(0, len(m) - n + 1, n)]
        rms = [w["rms"] for w in wins]
        band = [w["band_40_70_rms"] for w in wins]
        peaks = [w["peak_hz"] for w in wins]
        out[f"{node} | {name}"] = {
            "windows": len(wins), "gaps": gaps,
            "rms_mean": float(np.mean(rms)), "rms_cv_pct": cv(rms),
            "band_mean": float(np.mean(band)), "band_cv_pct": cv(band),
            "peak_hz": peaks,
        }
        r = out[f"{node} | {name}"]
        print(f"{node:5s} {name:15s} n={r['windows']:2d} gaps={gaps}  RMS {r['rms_mean']:.4f} CV {r['rms_cv_pct']:.1f}%"
              f"  40-70Hz {r['band_mean']:.4f} CV {r['band_cv_pct']:.1f}%  peaks {sorted(set(round(p, 1) for p in peaks))}")

json.dump(out, open(os.path.join(LOGS, "stand_repeatability_1023.json"), "w"), indent=1)
print("saved", os.path.join(LOGS, "stand_repeatability_1023.json"))
