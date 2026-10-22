import numpy as np
import pytest

from BenchTest.analysis import pothole as ph, dsp
from BenchTest.analysis.config import Config
from synth import bandnoise, pothole_shape

FS = 200.0


def _road(seconds, seed, events=(), amp=6.0, noise_sd=0.8):
    rng = np.random.default_rng(seed)
    n = int(seconds * FS)
    x = bandnoise(n, FS, 1, 60, noise_sd, rng)
    shape = pothole_shape(FS, amp)
    for te in events:
        k = int(te * FS)
        x[k:k + len(shape)] += shape
    t = 1.79e9 + np.arange(n) / FS
    bp = dsp.bandpass(x, FS, 2, 40, 4)
    return t, bp


def _pass(name, seconds, seed, events=(), speed=5.0):
    cfg = Config()
    t, bp = _road(seconds, seed, events)
    c = ph.candidates(t, bp, FS, cfg, np.full(len(t), speed))
    return {"name": name, "cands": c, "km": speed * seconds / 1000, "speed": speed,
            "t_event": t[0] + events[0] + 0.09 if events else None}


def test_synthetic_pothole_recovered_and_no_false_alarm_on_noise():
    cfg = Config()
    smooth = [_pass(f"s{k}", 120, 100 + k) for k in range(5)]
    obst = [_pass(f"o{k}", 20, 200 + k, events=(10.0,)) for k in range(5)]
    cal = ph.calibrate(smooth, obst, cfg)
    assert cal["chosen"]["detection_rate"] == 1.0
    # independent test signals: noise only, and noise with three potholes
    t, bp = _road(300, 999)
    ev = ph.detect(ph.candidates(t, bp, FS, cfg, np.full(len(t), 5.0)), cal["a"], cal["b"])
    assert ev == []
    times = (20.0, 47.3, 81.9)
    t, bp = _road(100, 1000, times)
    ev = ph.detect(ph.candidates(t, bp, FS, cfg, np.full(len(t), 5.0)), cal["a"], cal["b"])
    assert len(ev) == 3
    for e, te in zip(ev, times):
        assert 0.0 < e["t"] - (t[0] + te) < 0.2          # spike at the far edge, after the drop
        assert e["t_drop"] < e["t"] and 0.02 <= e["duration_s"] <= 0.3
    lab_t = np.array([t[0] + te + 0.1 for te in times] + [t[0] + 60.0])
    r = ph.evaluate(ev, lab_t, ["pothole", "pothole", "pothole", "speed bump"], tol_s=0.5)
    assert (r["tp"], r["fp"], r["fn"], r["recall"]) == (3, 0, 0, 1.0)


def test_speed_bump_order_is_not_a_pothole():
    """A bump rises first (up, then down over 0.3 s): no drop-then-spike candidate of comparable size."""
    cfg = Config()
    n = int(10 * FS)
    t = np.arange(n) / FS
    h = np.sin(np.pi * np.arange(int(0.15 * FS)) / (0.15 * FS))
    x = np.zeros(n)
    x[1000:1000 + 2 * len(h)] = 6.0 * np.r_[h, -h]
    c = ph.candidates(t, dsp.bandpass(x, FS, 2, 40, 4), FS, cfg)
    y = np.zeros(n)
    y[1000:1000 + len(pothole_shape(FS))] = pothole_shape(FS, 6.0)
    cp = ph.candidates(t, dsp.bandpass(y, FS, 2, 40, 4), FS, cfg)
    p_bump = max([e["p2p"] for e in c] + [0.0])
    p_hole = max(e["p2p"] for e in cp)
    assert p_bump < 0.5 * p_hole


def test_threshold_is_speed_dependent():
    assert ph.threshold(np.array([0.0, 5.0, np.nan]), 2.0, 0.5).tolist() == [2.0, 4.5, 2.0]
