"""Poster figure: rear IMU vertical vibration on one smooth-loop pass and one rough-strip pass, 27 Oct 2026.

    python Presentation/source/make_poster_imu_trace.py

Uses the analysis pipeline's own streams (position_icc.load_verts), so the trace is the ISO 2631-1 Wk-weighted
vertical acceleration that a_w is computed from. Writes assets/imu_smooth_rough.png at poster resolution.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, REPO)
from BenchTest.analysis import config as cfgmod  # noqa: E402
from BenchTest.analysis import dsp  # noqa: E402
from BenchTest.analysis import position_icc as pi  # noqa: E402

SESSION = os.path.join(REPO, "BenchTest", "logs", "run2_road_2026-10-27")
OUT = os.path.join(SESSION, "analysis")
PASSES = [("Smooth loop", "R2 A v10 p2", "#14305C"), ("Rough strip", "R2 A v10 p8", "#B45309")]
SPAN = 40.0   # seconds shown from each pass


def trace(vert, t0, t1):
    wk, ts = [], []
    for c in vert.chunks:
        m = (c.t >= t0) & (c.t < t1)
        if m.any():
            wk.append(c.wk[m]); ts.append(c.t[m])
    wk, ts = np.concatenate(wk), np.concatenate(ts)
    return ts - ts[0], wk


def main():
    cfg = cfgmod.load_config(SESSION)
    verts, win = pi.load_verts(SESSION, OUT, cfg)
    rear = verts["rear1"]
    plt.rcParams.update({"font.family": "Calibri", "font.size": 22, "mathtext.fontset": "custom", "mathtext.it": "Calibri:italic"})
    fig, axes = plt.subplots(2, 1, figsize=(10, 5.0), sharex=True, sharey=True)
    for ax, (label, name, col) in zip(axes, PASSES):
        t, a = trace(rear, *win[name])
        m = t <= SPAN
        aw = dsp.rms(a)
        ax.plot(t[m], a[m], color=col, lw=0.8)
        ax.set_title(f"{label}: a$_w$ = {aw:.2f} m/s²", loc="left", color=col, fontweight="bold", fontsize=24)
        ax.set_ylim(-30, 30)
        ax.set_yticks([-25, 0, 25])
        ax.tick_params(labelsize=20)
        ax.grid(axis="y", color="#B9C7DA", lw=0.8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        print(name, "a_w", round(aw, 3), "s", round(t[-1], 1), "peak", round(float(np.abs(a[m]).max()), 1))
    axes[1].set_xlabel("Time into pass (s), 10 km/h", fontsize=22)
    fig.supylabel("Vertical vibration (m/s²)", fontsize=20)
    fig.tight_layout()
    out = os.path.join(HERE, "assets", "imu_smooth_rough.png")
    fig.savefig(out, dpi=300, facecolor="#E8F0FA")
    print("wrote", out)


if __name__ == "__main__":
    main()
