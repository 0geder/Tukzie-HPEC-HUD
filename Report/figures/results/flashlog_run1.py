"""Run-1 flash log of the rear telemetry unit, read back on 22 Oct 2026.

Run from anywhere: python Report/figures/results/flashlog_run1.py

Input:  BenchTest/logs/flashlog_2026-10-22/rear_flash_log_dump.jsonl
        (log_dump.py output; one record every 10 s, each holding the ride
        features of the latest 1 s window per IMU, the fused values and BMS)
        BenchTest/logs/roadtest_2026-10-19/2026-10-19_171534_roadtest.jsonl
        (recorder on the Pi 5; used only to map the unit's uptime to local time
        and to compare the battery current)
Output: flashlog_run1.pdf / .png (figure) and flashlog_run1_summary.txt
        (every number quoted in the report) in this folder.

States: driving = |battery current| > 1 A at the record (the current is a
snapshot, so coasting and braking are missed); parked = |I| <= 1 A and fused
std <= 0.3 m/s^2; other = low current but fused std above 0.3 m/s^2 (coasting
in the drive period, or handling outside it). Other is reported, not merged.
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DUMP = ROOT / "BenchTest" / "logs" / "flashlog_2026-10-22" / "rear_flash_log_dump.jsonl"
REC = ROOT / "BenchTest" / "logs" / "roadtest_2026-10-19" / "2026-10-19_171534_roadtest.jsonl"
LOCAL = timezone(timedelta(hours=2))
BOOT = 109

BLUE, VERM, GREY = "#0072B2", "#D55E00", "#7f7f7f"
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "Nimbus Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 9, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.grid": True, "grid.color": "#cccccc", "grid.linewidth": 0.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
    "legend.frameon": False, "pdf.fonttype": 42, "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
})
W = 6.3
out = []


def say(s=""):
    print(s)
    out.append(s)


# ------------------------------------------------------------ read the dump
lines = DUMP.read_text(encoding="utf-8").splitlines()
recs, bad = [], 0
for l in lines:
    try:
        recs.append(json.loads(l))
    except json.JSONDecodeError:
        bad += 1
say(f"dump lines {len(lines)}, parsed {len(recs)}, unparsable {bad}")
boots = sorted({r["boot"] for r in recs})
for b in boots:
    rr = [r for r in recs if r["boot"] == b]
    say(f"  boot {b}: fw {rr[0]['fw']}, {len(rr)} records, uptime "
        f"{min(r['up_ms'] for r in rr)/3.6e6:.2f} to {max(r['up_ms'] for r in rr)/3.6e6:.2f} h")

R = sorted([r for r in recs if r["boot"] == BOOT], key=lambda r: r["seq"])
seq = np.array([r["seq"] for r in R])
say(f"boot {BOOT}: {len(R)} records, seq {seq.min()} to {seq.max()} "
    f"({seq.max()-seq.min()+1} expected, {seq.max()-seq.min()+1-len(R)} not parsed or not read)")
up = np.array([r["up_ms"] for r in R]) / 1000.0
dt = np.diff(up)
say(f"record spacing (consecutive seq only): min {dt[np.diff(seq)==1].min():.1f} s, median "
    f"{np.median(dt[np.diff(seq)==1]):.1f} s, p95 {np.percentile(dt[np.diff(seq)==1],95):.1f} s, "
    f"max {dt[np.diff(seq)==1].max():.1f} s; nominal 10 s")
say(f"  spacing <= 10.5 s in {(dt[np.diff(seq)==1] <= 10.5).sum()} of {(np.diff(seq)==1).sum()} intervals; "
    f"mean {(up[-1]-up[0])/(len(up)-1):.1f} s")


def f(path):
    a, b = path.split(".")
    return np.array([np.nan if (r.get(a) or {}).get(b) is None else float(r[a][b]) for r in R])


cur = f("bms.i")
volt = f("bms.v")
soc = f("bms.soc")

# --------------------------------------------- uptime -> local time (recorder)
offs, rec_i = [], []
with REC.open(encoding="utf-8") as fh:
    for l in fh:
        try:
            d = json.loads(l)
        except json.JSONDecodeError:
            continue
        if d.get("src") != "rear":
            continue
        e = ((d.get("data") or {}).get("esp32")) or {}
        if e.get("up_ms") is None:
            continue
        age = (e.get("age_ms") or 0) / 1000.0
        offs.append(d["t"] - age - e["up_ms"] / 1000.0)
        if e.get("i") is not None:
            rec_i.append(float(e["i"]))
off = float(np.median(offs))
say(f"uptime to epoch offset (median of {len(offs)} recorder rows) {off:.1f} s, "
    f"spread p5..p95 {np.percentile(offs,5)-off:.2f}..{np.percentile(offs,95)-off:.2f} s")
t = np.array([datetime.fromtimestamp(off + u, LOCAL) for u in up])
say(f"boot {BOOT} spans {t[0]:%d %b %H:%M} to {t[-1]:%d %b %H:%M} local time")
say(f"recorder rear current min {min(rec_i):.2f} A; flash log current min {np.nanmin(cur):.2f} A, "
    f"max {np.nanmax(cur):.2f} A")
say(f"voltage {np.nanmax(volt):.2f} to {np.nanmin(volt):.2f} V; SOC {np.nanmax(soc):.0f} to {np.nanmin(soc):.0f} %")

drive = np.abs(cur) > 1.0
fstd = f("fused.std")
park = ~drive & ~np.isnan(cur) & (fstd <= 0.3)
other = ~drive & ~park
say(f"driving records (|I|>1 A) {drive.sum()}, parked {park.sum()}, current missing {np.isnan(cur).sum()}")
di = np.where(drive)[0]
inwin = (np.arange(len(R)) >= di[0]) & (np.arange(len(R)) <= di[-1])
say(f"  other (|I|<=1 A, fused std > 0.3): {other.sum()}, of which {(other & inwin).sum()} inside the "
    f"drive period and {(other & ~inwin).sum()} outside it")
xo = fstd[other & ~inwin]
say(f"  other outside the drive period: fused std median {np.median(xo):.2f}, max {xo.max():.2f}; "
    f"times {t[other & ~inwin][0]:%H:%M} to {t[other & ~inwin][-1]:%H:%M}")
say(f"  records in the drive period {inwin.sum()} ({(t[di[-1]]-t[di[0]]).total_seconds()/60:.1f} min)")
say(f"  driving records between {t[di[0]]:%H:%M:%S} and {t[di[-1]]:%H:%M:%S}")
say(f"  driving current median {np.median(cur[drive]):.2f} A")

# ------------------------------------------------------ features by state
feats = ["rms", "std", "p2p", "crest", "jerk"]
say("")
say("per-IMU 1 s features, median [p95] (max): parked | driving")
for imu in ("imu1", "imu2"):
    for k in feats:
        x = f(f"{imu}.{k}")
        p, d = x[park & ~np.isnan(x)], x[drive & ~np.isnan(x)]
        say(f"  {imu} {k:5s}: {np.median(p):.3f} [{np.percentile(p,95):.3f}] ({p.max():.3f}) | "
            f"{np.median(d):.3f} [{np.percentile(d,95):.3f}] ({d.max():.3f})  n={len(p)}|{len(d)}")
for k in ("std", "dis", "p2p", "jerk"):
    x = f(f"fused.{k}")
    p, d = x[park & ~np.isnan(x)], x[drive & ~np.isnan(x)]
    say(f"  fused {k:5s}: {np.median(p):.3f} [{np.percentile(p,95):.3f}] ({p.max():.3f}) | "
        f"{np.median(d):.3f} [{np.percentile(d,95):.3f}] ({d.max():.3f})")
src = f("fused.src")
say(f"  fused src values: {dict(zip(*np.unique(src[~np.isnan(src)], return_counts=True)))}")

s1, s2 = f("imu1.std"), f("imu2.std")
ok = drive & ~np.isnan(s1) & ~np.isnan(s2)
r = np.corrcoef(s1[ok], s2[ok])[0, 1]
rl = np.corrcoef(np.log(s1[ok]), np.log(s2[ok]))[0, 1]
ratio = s1[ok] / s2[ok]
say("")
say(f"driving: IMU1/IMU2 std ratio median {np.median(ratio):.2f} (p5 {np.percentile(ratio,5):.2f}, "
    f"p95 {np.percentile(ratio,95):.2f}); Pearson r {r:.2f} (log {rl:.2f}), n={ok.sum()}")
say(f"driving: IMU1 std > IMU2 std in {(s1[ok] > s2[ok]).sum()} of {ok.sum()} records")
oko = other & inwin & ~np.isnan(s1) & ~np.isnan(s2)
say(f"other in drive period: IMU1/IMU2 std ratio median {np.median(s1[oko]/s2[oko]):.2f}, "
    f"r {np.corrcoef(s1[oko], s2[oko])[0,1]:.2f}, n={oko.sum()}")
d_all = f("fused.dis")
say(f"fused dis, other in drive period: median {np.median(d_all[oko]):.3f}, p95 {np.percentile(d_all[oko],95):.3f}")
okp = park & ~np.isnan(s1) & ~np.isnan(s2)
say(f"parked: IMU1/IMU2 std ratio median {np.median(s1[okp]/s2[okp]):.2f}")
r1, r2 = f("imu1.rms"), f("imu2.rms")
say(f"parked rms (gravity reading): IMU1 median {np.nanmedian(r1[park]):.3f}, IMU2 {np.nanmedian(r2[park]):.3f} m/s^2")

pl = np.array([(x.hour == 21) or (x.hour == 22 and x.minute < 40) for x in t]) & park
say(f"parked 21:00 to 22:40: {pl.sum()} records, sigma median IMU1 {np.nanmedian(s1[pl]):.3f}, IMU2 {np.nanmedian(s2[pl]):.3f}; "
    f"IMU1 p5..p95 {np.nanpercentile(s1[pl],5):.3f}..{np.nanpercentile(s1[pl],95):.3f}, "
    f"IMU2 {np.nanpercentile(s2[pl],5):.3f}..{np.nanpercentile(s2[pl],95):.3f}")
q = park & ~pl
say(f"parked outside 21:00 to 22:40: sigma median IMU1 {np.nanmedian(s1[q]):.3f}, IMU2 {np.nanmedian(s2[q]):.3f}")
(HERE / "flashlog_run1_summary.txt").write_text("\n".join(out) + "\n", encoding="utf-8")

# ------------------------------------------------------------------ figure
fig = plt.figure(figsize=(W, 5.0))
gs = fig.add_gridspec(3, 2, height_ratios=[1.1, 0.7, 1.3], hspace=0.8, wspace=0.3)
a1 = fig.add_subplot(gs[0, :])
a2 = fig.add_subplot(gs[1, :], sharex=a1)
a3 = fig.add_subplot(gs[2, 0])
a4 = fig.add_subplot(gs[2, 1])

# break lines where records are missing (gap > 15 s)
gap = np.r_[False, np.diff(seq) > 1]


def broken(y):
    y = y.copy()
    y[gap] = np.nan
    return y


a1.plot(t, broken(s1), color=BLUE, lw=0.8, label="IMU1")
a1.plot(t, broken(s2), color=VERM, lw=0.8, label="IMU2")
a1.set_yscale("log")
a1.set_ylabel(r"$\sigma$ (m/s$^2$)")
a1.legend(loc="lower right", bbox_to_anchor=(1.0, 0.98), ncol=2)
a1.set_title("(a) Vibration level per IMU (latest 1 s window in each record)", loc="left", fontsize=9)
a2.plot(t, broken(cur), color=GREY, lw=0.8)
a2.set_ylabel("Current (A)")
a2.set_title("(b) Battery current (negative: discharge)", loc="left", fontsize=9)
a2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=LOCAL))
for ax in (a1, a2):
    ax.axvspan(t[di[0]], t[di[-1]], color="#e8f3ec", zorder=0, lw=0)
plt.setp(a1.get_xticklabels(), visible=False)
a2.set_xlabel("Local time, 19 to 20 October 2026")

a3.scatter(s2[okp], s1[okp], s=8, color=GREY, alpha=0.5, lw=0, label=f"Parked ({okp.sum()})")
a3.scatter(s2[oko], s1[oko], s=9, color=VERM, alpha=0.7, lw=0, label=f"Low current, drive period ({oko.sum()})")
a3.scatter(s2[ok], s1[ok], s=10, color=BLUE, alpha=0.8, lw=0, label=f"Driving ({ok.sum()})")
lim = [0.01, 10]
a3.plot(lim, lim, color="black", lw=0.6, ls=":")
a3.set_xscale("log"); a3.set_yscale("log"); a3.set_xlim(lim); a3.set_ylim(lim)
a3.set_xlabel(r"IMU2 $\sigma$ (m/s$^2$)"); a3.set_ylabel(r"IMU1 $\sigma$ (m/s$^2$)")
a3.legend(loc="upper left", fontsize=6.5, handletextpad=0.2, borderaxespad=0.2)
a3.set_title("(c) IMU1 against IMU2, same window", loc="left", fontsize=9)

dis = f("fused.dis")
bp = a4.boxplot([dis[park & ~np.isnan(dis)], dis[drive & ~np.isnan(dis)]], whis=(5, 95),
                widths=0.5, showfliers=False, patch_artist=True,
                medianprops=dict(color="black", lw=1.2))
for b, c in zip(bp["boxes"], (GREY, BLUE)):
    b.set_facecolor(c); b.set_alpha(0.35); b.set_edgecolor(c)
a4.set_xticks([1, 2], ["Parked", "Driving"])
a4.set_ylabel("Disagreement $D$")
a4.set_title("(d) Fused disagreement", loc="left", fontsize=9)

fig.savefig(HERE / "flashlog_run1.pdf")
fig.savefig(HERE / "flashlog_run1.png", dpi=200)
print("written", HERE / "flashlog_run1.pdf")
