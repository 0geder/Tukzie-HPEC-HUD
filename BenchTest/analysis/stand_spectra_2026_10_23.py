"""Spectra of the stand runs of 23 October 2026 (run 2, lab part): rest against the drive wheel turning, rear and front.

Windows are cut from the raw-stream captures by the Pi timestamp at the start of each line (Pi clocks chrony-synced),
decoded with TelemetryUnit/tools/raw_stream_decode.py, and the acceleration magnitude (m/s^2, firmware calibration
not applied: the raw stream carries counts) is detrended and passed to a Welch estimate (4 s Hann segments, 50 %
overlap, 200 Hz). Output: a figure for the report, and the RMS, the 1 to 80 Hz band RMS and the five largest spectral
peaks of each window, printed and saved as JSON beside the figure.
Run: python BenchTest/analysis/stand_spectra_2026_10_23.py
"""
import csv
import json
import os
import subprocess
import sys
import tempfile
import time

import numpy as np
from scipy.signal import welch, find_peaks
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOGS = os.path.join(REPO, "BenchTest", "logs", "run2_lab_2026-10-23")
DECODER = os.path.join(REPO, "TelemetryUnit", "tools", "raw_stream_decode.py")
OUT_FIG = os.path.join(REPO, "Report", "figures", "results", "stand_spectra_1023.pdf")
OUT_JSON = os.path.join(LOGS, "stand_spectra_1023.json")
FS = 200.0


def epoch(hms):
    return time.mktime(time.strptime("2026-10-23 " + hms, "%Y-%m-%d %H:%M:%S"))


# rest windows lie between runs, at least 60 s from any current; runs trimmed 5 s at each end
WINDOWS = {
    "rest": ("15:58:00", "16:07:30"),
    "run 1 (3.2 A)": ("15:53:16", "15:55:45"),
    "run 2 (4.5 A)": ("16:08:17", "16:10:15"),
}
SOURCES = {
    "rear": os.path.join(LOGS, "pi4_rawlog", "rear_raw_2026-10-23_151718.txt"),
    "front": os.path.join(LOGS, "pi5_raw_front", "front_raw_2026-10-22_143608.txt"),
}


def magnitude(path, t0, t1):
    with tempfile.TemporaryDirectory() as tmp:
        cut = os.path.join(tmp, "cut.txt")
        with open(path, encoding="ascii", errors="replace") as f, open(cut, "w", encoding="ascii") as g:
            for line in f:
                head, _, rest = line.partition(" ")
                try:
                    t = float(head)
                except ValueError:
                    continue
                if t0 <= t <= t1:
                    g.write(rest)
        subprocess.run([sys.executable, DECODER, cut, "--out", tmp], check=True, capture_output=True)
        csvs = [p for p in os.listdir(tmp) if p.startswith("raw_") and p.endswith("imu1.csv")]
        if not csvs:
            return None
        rows = list(csv.DictReader(open(os.path.join(tmp, csvs[0]))))
    a = np.array([[float(r["ax_mps2"]), float(r["ay_mps2"]), float(r["az_mps2"])] for r in rows])
    seq = np.array([int(r["seq"]) for r in rows])
    return np.linalg.norm(a, axis=1), int(np.sum(np.diff(seq) != 1))


results, spectra = {}, {}
for node, path in SOURCES.items():
    for name, (h0, h1) in WINDOWS.items():
        got = magnitude(path, epoch(h0), epoch(h1))
        if got is None:
            print(f"{node} {name}: no samples")
            continue
        m, gaps = got
        x = m - m.mean()
        f, p = welch(x, fs=FS, window="hann", nperseg=int(4 * FS), noverlap=int(2 * FS), detrend="linear")
        band = (f >= 1) & (f <= 80)
        band_rms = float(np.sqrt(np.trapezoid(p[band], f[band])))
        pk, _ = find_peaks(p, distance=4)
        top = sorted(((float(p[i]), float(f[i])) for i in pk if f[i] >= 1), reverse=True)[:5]
        results[f"{node} {name}"] = {
            "samples": int(len(m)), "seq_gaps": gaps, "mean_g_mps2": float(m.mean()),
            "rms_dynamic_mps2": float(x.std()), "band_rms_1_80Hz_mps2": band_rms,
            "peaks_hz_psd": [(round(fr, 2), float(f"{pw:.3g}")) for pw, fr in top],
        }
        spectra[(node, name)] = (f, p)
        r = results[f"{node} {name}"]
        print(f"{node:5s} {name:14s} n={r['samples']:6d} gaps={gaps} |a| mean {r['mean_g_mps2']:.3f}  "
              f"dyn RMS {r['rms_dynamic_mps2']:.4f}  1-80 Hz {band_rms:.4f}  peaks {[pk_[0] for pk_ in r['peaks_hz_psd']]}")

json.dump(results, open(OUT_JSON, "w"), indent=1)

fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
styles = {"rest": ("0.55", 1.0), "run 1 (3.2 A)": ("#c0612b", 1.1), "run 2 (4.5 A)": ("#2b5fa8", 1.1)}
for ax, node in zip(axes, SOURCES):
    for name in WINDOWS:
        if (node, name) in spectra:
            f, p = spectra[(node, name)]
            col, lw = styles[name]
            ax.semilogy(f, p, color=col, lw=lw, label=name)
    ax.set_title(f"{node} IMU", fontsize=10)
    ax.set_xlabel("frequency (Hz)")
    ax.set_xlim(0, 100)
    ax.grid(alpha=0.3, which="both")
axes[0].set_ylabel("PSD of |a| ((m/s$^2$)$^2$/Hz)")
axes[1].legend(fontsize=8, loc="upper right")
fig.tight_layout()
os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
fig.savefig(OUT_FIG)
fig.savefig(OUT_FIG.replace(".pdf", ".png"), dpi=110)
print("figure:", OUT_FIG)
