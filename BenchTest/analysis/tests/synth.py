"""Synthetic signals with known answers, shared by the tests."""
import numpy as np

from BenchTest.analysis.config import G0


def bandnoise(n, fs, lo, hi, sd, rng):
    from scipy import signal as ss
    x = rng.standard_normal(n + 2000)
    sos = ss.butter(4, [lo, hi], "band", fs=fs, output="sos")
    y = ss.sosfilt(sos, x)[2000:]
    return y * sd / y.std()


def pothole_shape(fs, amp=6.0, drop_s=0.06, gap_s=0.03, ring_hz=12.0):
    """Drop (negative half sine), then a spike twice as high, then decaying ringing; positive up."""
    t1 = np.arange(int(drop_s * fs)) / fs
    drop = -amp * np.sin(np.pi * t1 / drop_s)
    t2 = np.arange(int(gap_s * fs)) / fs
    spike = 2 * amp * np.sin(np.pi * t2 / gap_s)
    t3 = np.arange(int(0.3 * fs)) / fs
    ring = -0.8 * amp * np.exp(-t3 / 0.06) * np.sin(2 * np.pi * ring_hz * t3)
    return np.r_[drop, spike, ring]


def imu_counts_from_vertical(av, rng, tilt_deg=(8.0, -5.0), noise=0.02):
    """Sensor-axis acceleration (m/s^2) for a mount tilted from vertical, given the dynamic vertical av (up)."""
    rx, ry = np.radians(tilt_deg)
    up = np.array([np.sin(ry), -np.sin(rx) * np.cos(ry), np.cos(rx) * np.cos(ry)])
    acc = (G0 + av)[:, None] * up[None, :]
    acc += noise * rng.standard_normal(acc.shape)
    return acc, up


def write_session(folder, seed=0, fs=200.0, speed=5.0, wheelbase=1.8):
    """A complete synthetic run-2 session: recorder JSONL with markers and 1 Hz rear DASH records, and one raw
    capture per node ("<host_epoch_s> <line>" lines, RAW/RAWH/RAWS v2), plus a video labels CSV.

    Known answers: front-to-rear delay wheelbase / speed; section roughness repeats across passes (ICC near 1);
    stationary runs carry a 37 Hz line; each obstacle pass has one pothole 5 s after its start.
    """
    import json
    import os
    from BenchTest.analysis import readers as rd

    rng = np.random.default_rng(seed)
    t_boot = 1792430000.0
    t0 = t_boot + 60.0
    plan = []                                     # (name, kind, duration)
    plan += [("stationary low", "st", 30.0), ("stationary high", "st", 30.0)]
    for p in range(1, 4):
        for s, _ in (("S1", 0.4), ("S2", 0.8), ("S3", 1.4)):
            plan.append((f"{s} smooth pass{p} 18kmh", s, 20.0))
    for p in range(1, 6):
        plan.append((f"S9 plank pass{p} 18kmh", "ob", 10.0))
    level = {"S1": 0.4, "S2": 0.8, "S3": 1.4}
    templates = {s: bandnoise(int(20 * fs) + 400, fs, 1, 60, 1.0, np.random.default_rng(100 + j))
                 for j, s in enumerate(level)}
    gap = 5.0
    total = sum(d for _, _, d in plan) + gap * (len(plan) + 1) + 2.0
    n = int(total * fs)
    t = t0 + np.arange(n) / fs
    road = 0.03 * rng.standard_normal(n)          # parked: sensor noise only
    moving = np.zeros(n, bool)
    markers, labels, runs = [], [], []
    cur = t0 + gap
    lag = int(round(wheelbase / speed * fs))
    shape = pothole_shape(fs, 6.0)
    for name, kind, dur in plan:
        a, b = int((cur - t0) * fs), int((cur + dur - t0) * fs)
        m = b - a
        if kind == "st":
            amp = 0.3 if "low" in name else 0.6
            road[a:b] += amp * np.sin(2 * np.pi * 37.0 * np.arange(m) / fs)
        elif kind == "ob":
            road[a:b] += bandnoise(m, fs, 1, 60, 0.4, rng)
            k = a + int(5.0 * fs)
            road[k:k + len(shape)] += shape
            labels.append((t[k] + 0.06, "pothole"))
            moving[a:b] = True
        else:
            road[a:b] += level[kind] * templates[kind][200:200 + m] + 0.05 * level[kind] * rng.standard_normal(m)
            moving[a:b] = True
        markers.append((cur, name + " start"))
        markers.append((cur + dur, name + " stop"))
        runs.append((name, cur, cur + dur))
        cur += dur + gap
    front = road
    rear = np.r_[np.zeros(lag), road[:-lag]] + 0.1 * rng.standard_normal(n)
    os.makedirs(folder, exist_ok=True)
    for node, av, imus in (("front", front, (1,)), ("rear", rear, (1, 2))):
        lines = []
        for imu in imus:
            acc, _ = imu_counts_from_vertical(av, rng, (8.0, -5.0) if imu == 1 else (-3.0, 6.0))
            counts = np.zeros((n, 6), np.int64)
            counts[:, :3] = np.clip(np.round(acc / G0 * 4096), -32768, 32767)
            seq = np.arange(n) + 1000
            t_us = np.round((t - t_boot) * 1e6 + rng.integers(-20, 20, n)).astype(np.int64)
            keep = np.ones(n, bool)
            keep[rng.choice(n, 30, replace=False)] = False          # 30 missing samples (rdfail)
            idx = np.flatnonzero(keep)
            for j in range(0, len(idx), 10):
                sl = idx[j:j + 10]
                host = t[sl[-1]] + 0.004 + rng.exponential(0.01)
                lines.append((host, rd.encode_raw_line(node, imu, seq[sl], t_us[sl], counts[sl], None, host)))
            for h in np.arange(t[0], t[-1], 5.0):
                lines.append((h + 0.001, rd.encode_raw_header(node, imu, rdfail=30, host_t=h + 0.001)))
        for e, h in enumerate(np.arange(t[0], t[-1], 0.5)):
            lines.append((h + 0.002, rd.encode_raw_sync(node, e + 1, (e + 1) % 2, int((h - t_boot) * 1e6),
                                                         host_t=h + 0.002)))
        lines.sort(key=lambda x: x[0])
        with open(os.path.join(folder, f"{node}_raw_capture.txt"), "w", encoding="ascii", newline="\n") as f:
            f.write("boot: some log text\n")
            f.writelines(l for _, l in lines)
    recs = [{"t": t0, "src": "marker", "text": "session start"}]
    recs += [{"t": tm, "src": "marker", "text": tx} for tm, tx in markers]
    for k, ts in enumerate(np.arange(t[0], t[-1], 1.0)):
        j = int((ts - t0) * fs)
        mv = moving[j]
        seg = road[j:j + int(fs)]
        e = {"seq": 5000 + k, "up_ms": int((ts - t_boot) * 1000), "vib": float(np.std(seg)), "i": -12.0 if mv else 0.0,
             "v": 74.0, "imu_hz": [200.0, 200.0], "drops": [0, 0], "fix": True,
             "spd_raw": speed / 0.514444 if mv else 0.0, "lat": -33.95, "lon": 18.46}
        for rep in range(2):                                         # the bridge repeats records
            recs.append({"t": ts + 0.3 + 0.5 * rep, "src": "rear", "data": {"esp32": e}})
    recs.sort(key=lambda r: r["t"])
    with open(os.path.join(folder, "2026-11-01_100000_roadtest.jsonl"), "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
        f.write('{"truncated\n')
    with open(os.path.join(folder, "labels.csv"), "w", encoding="utf-8") as f:
        f.write("time,type\n")
        for tm, ty in labels:
            f.write(f"{tm:.3f},{ty}\n")
    with open(os.path.join(folder, "session.json"), "w", encoding="utf-8") as f:
        json.dump({"wheelbase_m": wheelbase}, f)
    return {"runs": runs, "labels": labels, "delay": lag / fs, "speed": speed}
