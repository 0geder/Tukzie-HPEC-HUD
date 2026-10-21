"""Results-chapter plots from data already recorded in BenchTest/logs.

Run from anywhere: python Report/figures/results/make_results_plots.py
Writes PDF (vector) and PNG preview for each figure into this folder and
prints the numbers quoted in README_snippets.tex.
"""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LOGS = ROOT / "BenchTest" / "logs"

# Okabe-Ito, colour-blind safe
BLUE, VERM, GREEN, PINK, ORANGE, SKY, GREY = (
    "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#7f7f7f")

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "Nimbus Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 9,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.grid": True,
    "grid.color": "#cccccc",
    "grid.linewidth": 0.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "legend.frameon": False,
    "pdf.fonttype": 42,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
})
W = 6.3


def save(fig, name):
    fig.savefig(HERE / f"{name}.pdf")
    fig.savefig(HERE / f"{name}.png", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- plot 1
IMU_RE = re.compile(r"\[\s*([\d.]+)s\] (IMU[12]): (\d+) samples .*dt_us\[min=(\d+) avg=(\d+) max=(\d+)\]\s+dropped=(\d+)")


def parse_imu(path):
    rows = {"IMU1": [], "IMU2": []}
    flushes, events = [], []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = IMU_RE.search(line)
        if m:
            rows[m.group(2)].append((float(m.group(1)), int(m.group(4)), int(m.group(6)), int(m.group(7))))
            continue
        m = re.search(r"\[\s*([\d.]+)s\] \[LOG\] flushed .* in ([\d.]+) ms", line)
        if m:
            flushes.append((float(m.group(1)), float(m.group(2))))
        m = re.search(r"\[\s*([\d.]+)s\] \[CMD\] local flash logging (OFF|on)", line)
        if m:
            events.append((float(m.group(1)), m.group(2)))
    return {k: np.array(v) for k, v in rows.items()}, flushes, events


def plot_imu():
    v5, _, ev5 = parse_imu(LOGS / "2026-09-29_v050_bench_test.log")
    v6, fl6, _ = parse_imu(LOGS / "2026-10-01_v060_bench_test.log")
    off_t = [t for t, s in ev5 if s == "OFF"][0]
    on_t = [t for t, s in ev5 if s == "on"][0]

    fig, axes = plt.subplots(2, 1, figsize=(W, 3.9), sharey=True)
    for ax, d, lab in ((axes[0], v5, "(a) v0.5.0, direct write every 10 s"),
                       (axes[1], v6, "(b) v0.6.0, buffered writes")):
        for k, c, mk in (("IMU1", BLUE, "o"), ("IMU2", VERM, "s")):
            a = d[k]
            ax.plot(a[:, 0], a[:, 2] / 1000, color=c, lw=0.8, marker=mk, ms=2.2,
                    label=f"{k} max interval")
        ax.axhline(5.0, color=GREY, lw=0.6, ls=":")
        ax.set_ylabel("Max interval (ms)")
        ax.text(0.0, 1.02, lab, transform=ax.transAxes, va="bottom", ha="left", fontsize=8)
    axes[0].axvspan(off_t, on_t, color=GREY, alpha=0.15, lw=0)
    axes[0].text((off_t + on_t) / 2, 25, "flash logging off", ha="center", fontsize=8, color="#444444")
    for i, (t, ms) in enumerate(fl6):
        axes[1].axvline(t, color=GREEN, lw=0.8, ls="--", label="flush" if i == 0 else None)
    axes[1].set_xlabel("Time since start of capture (s)")
    axes[0].set_ylim(0, 45)
    h, l = axes[1].get_legend_handles_labels()
    fig.legend(h, l, loc="upper right", ncol=3, bbox_to_anchor=(1.0, 1.01))
    axes[0].set_xlim(0, max(v5["IMU1"][:, 0].max(), 1) + 5)
    axes[1].set_xlim(0, v6["IMU1"][:, 0].max() + 5)
    fig.tight_layout(h_pad=1.2, rect=(0, 0, 1, 0.96))
    save(fig, "imu_write_gaps")

    # numbers
    print("== Plot 1 IMU")
    for name, d in (("v0.5.0", v5), ("v0.6.0", v6)):
        for k in ("IMU1", "IMU2"):
            a = d[k]
            print(name, k, "windows", len(a), "samples", int(a[:, 1].sum()),
                  "dropped", int(a[:, 3].sum()), "max over 10ms:", int((a[:, 2] > 10000).sum()),
                  "max of max", a[:, 2].max())
    for k in ("IMU1", "IMU2"):
        a = v5[k]
        on = a[(a[:, 0] < off_t) | (a[:, 0] > on_t)]
        off = a[(a[:, 0] > off_t + 1) & (a[:, 0] < on_t)]
        big = on[on[:, 2] > 10000]
        print("v050", k, "logging-on windows", len(on), "gaps>10ms", len(big),
              "range", big[:, 2].min(), big[:, 2].max(), "| off windows", len(off), "max off", off[:, 2].max())
    ft = np.array([t for t, _ in fl6])
    for k in ("IMU1", "IMU2"):
        a = v6[k]
        big = a[a[:, 2] > 10000]
        lag = [min(t - ft[ft <= t]) if (ft <= t).any() else None for t in big[:, 0]]
        rest = a[a[:, 2] <= 10000]
        print("v060", k, "gaps>10ms", len(big), "values", big[:, 2], "s after flush", lag,
              "max elsewhere", rest[:, 2].max())
    print("v060 flush durations ms", [ms for _, ms in fl6])
    print("v050 off/on", off_t, on_t)


# ---------------------------------------------------------------- plot 2
def plot_latency():
    runs = [
        ("Pi 4, 4 threads,\n30 Sep", LOGS / "2026-09-30_c4_latency" / "run1_4t.csv", BLUE),
        ("Pi 4, 4 threads,\nlive view, 30 Sep", LOGS / "2026-09-30_c4_latency" / "run2_4t_preview.csv", SKY),
        ("Pi 4, 1 thread,\n30 Sep", LOGS / "2026-09-30_c4_latency" / "run3_1t.csv", ORANGE),
        ("Pi 5, 4 threads,\nlive view, 15 Oct", LOGS / "2026-10-15_pi5_detector_timing.csv", VERM),
    ]
    data = []
    print("== Plot 2 latency (total_ms = readout to result)")
    for lab, p, c in runs:
        a = np.genfromtxt(p, delimiter=",", names=True)
        tot = a["total_ms"]
        data.append(tot)
        dur = (a["sensor_ns"][-1] - a["sensor_ns"][0]) / 1e9
        print(lab.replace("\n", " "), "n", len(tot), "median %.1f p95 %.1f max %.1f min %.1f" % (
            np.median(tot), np.percentile(tot, 95), tot.max(), tot.min()),
            "| infer median %.1f queue median %.1f" % (np.median(a["infer_ms"]), np.median(a["queue_ms"])),
            "| fps %.1f" % ((len(tot) - 1) / dur))

    fig, axes = plt.subplots(1, 2, figsize=(W, 2.6), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    for (lab, _, c), d in zip(runs, data):
        x = np.sort(d)
        y = np.arange(1, len(x) + 1) / len(x)
        ax.plot(x, y, color=c, lw=1.4, label=lab.replace("\n", " "))
    ax.set_xlabel("Readout to result (ms)")
    ax.set_ylabel("Fraction of frames")
    ax.set_xlim(0, 260)
    ax.set_ylim(0, 1.02)
    ax.text(0.01, 0.99, "(a)", transform=ax.transAxes, va="top")
    ax = axes[1]
    bp = ax.boxplot(data, vert=True, widths=0.55, patch_artist=True, showfliers=True,
                    whis=(5, 95), medianprops=dict(color="black", lw=1.0),
                    flierprops=dict(marker=".", ms=2, mec=GREY, mfc=GREY))
    for patch, (_, _, c) in zip(bp["boxes"], runs):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
        patch.set_edgecolor("black")
        patch.set_linewidth(0.6)
    ax.set_xticks(range(1, 5))
    ax.set_xticklabels(["Pi 4\n4 t", "Pi 4\n4 t, view", "Pi 4\n1 t", "Pi 5\n4 t, view"])
    ax.set_ylabel("Readout to result (ms)")
    ax.set_ylim(0, 260)
    ax.grid(axis="x", visible=False)
    ax.text(0.01, 0.99, "(b)", transform=ax.transAxes, va="top")
    axes[0].legend(loc="lower right", fontsize=7, handlelength=1.4)
    fig.tight_layout(w_pad=1.2)
    save(fig, "detector_latency")


# ---------------------------------------------------------------- plot 3
SAST = timezone(timedelta(hours=2))


def plot_road():
    f = LOGS / "roadtest_2026-10-19" / "2026-10-19_171534_roadtest.jsonl"
    recs, seen, rear_rows, rear_with = [], set(), 0, 0
    bad = 0
    for line in f.open(encoding="utf-8"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if r.get("src") != "rear":
            continue
        rear_rows += 1
        e = (r.get("data") or {}).get("esp32")
        if not e or e.get("seq") is None:
            continue
        rear_with += 1
        if e["seq"] in seen:
            continue
        seen.add(e["seq"])
        recs.append((r["t"], e["seq"], e.get("vib"), e.get("i"), e.get("v")))
    recs.sort(key=lambda x: x[1])
    t = np.array([x[0] for x in recs])
    seq = np.array([x[1] for x in recs])
    vib = np.array([np.nan if x[2] is None else x[2] for x in recs], float)
    cur = np.array([np.nan if x[3] is None else x[3] for x in recs], float)
    volt = np.array([np.nan if x[4] is None else x[4] for x in recs], float)

    lo = datetime(2026, 10, 19, 17, 15, tzinfo=SAST).timestamp()
    hi = datetime(2026, 10, 19, 18, 50, tzinfo=SAST).timestamp()
    w = (t >= lo) & (t <= hi)
    t, seq, vib, cur, volt = t[w], seq[w], vib[w], cur[w], volt[w]

    # break lines at missing seq
    brk = np.where(np.diff(seq) != 1)[0]
    span = seq[-1] - seq[0] + 1
    missing = span - len(seq)

    def broken(y):
        tt = np.insert(t.astype(float), brk + 1, np.nan)
        yy = np.insert(y.astype(float), brk + 1, np.nan)
        return tt, yy

    drive = (np.abs(cur) > 1) | (vib > 0.3)
    dts = [datetime.fromtimestamp(x, SAST).replace(tzinfo=None) for x in t]

    fig, axes = plt.subplots(2, 1, figsize=(W, 3.8), sharex=True)
    for ax, y, c, lab in ((axes[0], vib, BLUE, "Vibration, std (m/s$^2$)"),
                          (axes[1], cur, VERM, "Battery current (A)")):
        tt, yy = broken(y)
        x = [datetime.fromtimestamp(v, SAST).replace(tzinfo=None) if np.isfinite(v) else np.nan for v in tt]
        x = mdates.date2num([v if v == v else datetime(1970, 1, 1) for v in x])
        x[~np.isfinite(tt)] = np.nan
        ax.plot(x, yy, color=c, lw=0.5)
        ax.set_ylabel(lab)
        # shade driving seconds
        xd = mdates.date2num(dts)
        ax.fill_between(xd, 0, 1, where=drive, transform=ax.get_xaxis_transform(),
                        color=GREEN, alpha=0.12, lw=0, step="mid")
    axes[1].axhline(0, color=GREY, lw=0.5)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    axes[1].xaxis.set_major_locator(mdates.MinuteLocator(byminute=range(0, 60, 10)))
    axes[1].set_xlabel("Local time, 19 October 2026 (UTC+2)")
    axes[1].set_xlim(mdates.date2num(datetime(2026, 10, 19, 17, 15)), mdates.date2num(datetime(2026, 10, 19, 18, 50)))
    # marker
    mk = datetime(2026, 10, 19, 17, 58, 41)
    for ax in axes:
        ax.axvline(mdates.date2num(mk), color="black", lw=0.6, ls="--")
    axes[0].text(mdates.date2num(mk), 0.97, " drive marker 17:58:41", transform=axes[0].get_xaxis_transform(),
                 va="top", fontsize=7)
    fig.tight_layout(h_pad=0.4)
    save(fig, "road_session_1019")

    print("== Plot 3 road 19 Oct")
    print("bad json lines", bad, "rear rows", rear_rows, "rear rows with esp32", rear_with,
          "unique seq total", len(recs))
    print("window 17:15-18:50 unique records", len(seq), "seq", seq[0], "to", seq[-1],
          "span", span, "missing", missing, "(%.1f %%)" % (100 * missing / span), "breaks", len(brk))
    print("first/last local", dts[0], dts[-1])
    print("drive-flag records", int(drive.sum()))
    gaps = np.diff(seq)[brk] - 1
    print("largest seq gaps", sorted(gaps)[-5:])
    print("vib median %.3f max %.3f; vib median when driving %.3f, not driving %.3f" % (
        np.nanmedian(vib), np.nanmax(vib), np.nanmedian(vib[drive]), np.nanmedian(vib[~drive])))
    print("current min %.1f max %.1f, median while |i|>1: %.1f" % (
        np.nanmin(cur), np.nanmax(cur), np.nanmedian(cur[np.abs(cur) > 1])))
    print("records |i|>1:", int((np.abs(cur) > 1).sum()), "vib>0.3:", int((vib > 0.3).sum()))
    print("voltage range %.2f to %.2f, first %.2f last %.2f" % (np.nanmin(volt), np.nanmax(volt), volt[np.isfinite(volt)][0], volt[np.isfinite(volt)][-1]))
    print("cur nan", int(np.isnan(cur).sum()), "vib nan", int(np.isnan(vib).sum()))
    if drive.any():
        print("first/last drive record", dts[np.argmax(drive)], dts[len(drive) - 1 - np.argmax(drive[::-1])])


# ---------------------------------------------------------------- plot 4
def plot_t15():
    p = LOGS / "2026-10-11_sync_outage_test.log"
    pts = []
    off_t = on_t = conn_t = clear_t = None
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\[\s*([\d.]+)s\]", line)
        if not m:
            continue
        ts = float(m.group(1))
        if "> AT+CFUN=4" in line:
            off_t = ts
        elif "> AT+CFUN=1" in line:
            on_t = ts
        elif "[MQTT] Connected." in line and on_t and conn_t is None:
            conn_t = ts
        elif "backlog cleared" in line:
            clear_t = ts
        b = re.search(r"backlog=(\d+)", line)
        if b and "DASH" not in line:
            rp = re.search(r"replayed=(\d+)", line)
            la = re.search(r"live_acked=(\d+)", line)
            pts.append((ts, int(b.group(1)), int(rp.group(1)) if rp else None, int(la.group(1)) if la else None))
    a = np.array([(x[0], x[1]) for x in pts])
    rep = np.array([(x[0], x[2]) for x in pts if x[2] is not None])
    live = np.array([(x[0], x[3]) for x in pts if x[3] is not None])

    fig, ax = plt.subplots(figsize=(W, 2.5))
    ax.axvspan(off_t, on_t, color=GREY, alpha=0.15, lw=0)
    ax.text((off_t + on_t) / 2 + 80, 66, "radio off (AT+CFUN=4), 10 min", ha="center", fontsize=8, color="#444444")
    ax.plot(a[:, 0], a[:, 1], color=BLUE, marker="o", ms=3, lw=1.2, label="Backlog on device (records)")
    ax.plot(rep[:, 0], rep[:, 1] - rep[0, 1], color=VERM, marker="s", ms=3, lw=1.2,
            label="Replayed and acknowledged (records)")
    ax.axvline(conn_t, color="black", lw=0.7, ls="--")
    ax.text(conn_t - 4, 40, "MQTT reconnected", rotation=90, ha="right", va="center", fontsize=7)
    ax.axvline(clear_t, color=GREEN, lw=0.7, ls="--")
    ax.text(clear_t + 5, 25, "backlog cleared", rotation=90, ha="left", va="center", fontsize=7)
    ax.set_xlabel("Time since start of capture (s)")
    ax.set_ylabel("Records")
    ax.set_ylim(0, 72)
    ax.set_xlim(0, a[-1, 0] + 10)
    ax.legend(loc="upper left")
    fig.tight_layout()
    save(fig, "t15_outage_backlog")

    print("== Plot 4 T15")
    print("sync status points", len(a), "off", off_t, "on", on_t, "connected", conn_t, "cleared", clear_t)
    print("outage s %.1f, reconnect after on %.1f s, clear after connect %.1f s" % (on_t - off_t, conn_t - on_t, clear_t - conn_t))
    print("max backlog", a[:, 1].max(), "replayed start/end", rep[0, 1], rep[-1, 1], "live_acked start/end", live[0, 1], live[-1, 1])
    print("backlog points:", [(round(x, 1), int(y)) for x, y in a])
    rp = (LOGS / "2026-10-11_t15" / "2026-10-11_t15_replay.csv").read_text().splitlines()
    print("server replay.csv:", rp)


if __name__ == "__main__":
    plot_imu()
    plot_latency()
    plot_road()
    plot_t15()
