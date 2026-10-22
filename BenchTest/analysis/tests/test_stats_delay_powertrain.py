import numpy as np
import pytest

from BenchTest.analysis import stats, delay, powertrain, dsp
from BenchTest.analysis.config import Config
from synth import bandnoise

FS = 200.0

# Shrout and Fleiss (1979), Table 2: 6 targets rated by 4 judges
SF = np.array([[9, 2, 5, 8], [6, 1, 3, 2], [8, 4, 6, 8], [7, 1, 2, 6], [10, 5, 6, 9], [6, 2, 4, 7]], float)


def test_icc_shrout_fleiss_example():
    r = stats.icc(SF)
    assert r["icc2_1"] == pytest.approx(0.29, abs=0.005)
    assert r["icc3_1"] == pytest.approx(0.71, abs=0.005)
    lo, hi = r["icc3_1_ci"]
    assert lo < r["icc3_1"] < hi
    lo, hi = r["icc2_1_ci"]
    assert lo < r["icc2_1"] < hi


def test_icc_perfectly_repeated_passes_is_one():
    sections = np.array([0.4, 0.9, 1.6, 2.2])
    Y = np.repeat(sections[:, None], 5, axis=1)
    r = stats.icc(Y)
    assert r["icc2_1"] == 1.0 and r["icc3_1"] == 1.0 and r["icc3_1_ci"] == (1.0, 1.0)


def test_icc_noise_only_is_near_zero():
    rng = np.random.default_rng(5)
    r = stats.icc(rng.normal(1.0, 0.1, (40, 5)))
    assert abs(r["icc3_1"]) < 0.15 and r["icc3_1_ci"][0] < 0 < r["icc3_1_ci"][1]


def test_cv_and_bootstrap_ci():
    rng = np.random.default_rng(1)
    x = rng.normal(10.0, 1.0, 200)
    c = stats.cv(x)
    lo, hi = stats.bootstrap_ci(x, stats.cv, 2000)
    assert c == pytest.approx(0.1, abs=0.015) and lo < 0.1 < hi and hi - lo < 0.05


def test_repeatability_table():
    rows = [{"section": s, "pass_no": p, "a_w": base * (1 + 0.01 * p)}
            for s, base in (("S1", 0.5), ("S2", 1.0), ("S3", 2.0)) for p in range(1, 6)]
    rep = stats.repeatability(rows, metrics=("a_w",), n_boot=500)
    assert len(rep["per_section"]) == 3
    assert rep["icc"]["a_w"]["icc3_1"] > 0.99 and rep["icc"]["a_w"]["passes_used"] == [1, 2, 3, 4, 5]


def test_pure_delay_recovered_by_cross_correlation():
    rng = np.random.default_rng(7)
    n = int(60 * FS)
    x = bandnoise(n + 400, FS, 2, 40, 1.0, rng)
    d_true = 0.2375                                    # not a whole number of samples
    t = np.arange(n + 400) / FS
    y = np.interp(t - d_true, t, x)                    # rear = front delayed
    y = y + 0.3 * rng.standard_normal(len(y))
    d, c = delay.xcorr_delay(x[200:-200], y[200:-200], FS, 0.03, 1.5)
    assert d == pytest.approx(d_true, abs=1.5e-3) and c > 0.8


def _vert(t, x):
    c = dsp.Chunk(t=t, fs=FS, acc=None, av=x, bp=x, wk=x, lp=x, clip=np.zeros(len(t), bool), tm=t, lpm=x)
    return dsp.Vertical("n", 1, [c])


def test_front_rear_delay_gives_speed_with_ci():
    rng = np.random.default_rng(8)
    n = int(60 * FS)
    t = 1.79e9 + np.arange(n) / FS
    x = bandnoise(n, FS, 2, 40, 1.0, rng)
    d_true = 0.30
    y = np.interp(t - d_true, t, x) + 0.5 * rng.standard_normal(n)
    r = delay.front_rear_delay(_vert(t, x), _vert(t, y), t[0] + 2, t[-1] - 2, FS, wheelbase_m=1.8)
    assert r["delay_s"] == pytest.approx(d_true, abs=2e-3)
    assert r["delay_ci_lo"] <= d_true + 2e-3 and r["delay_ci_hi"] >= d_true - 2e-3
    assert r["speed_mps"] == pytest.approx(6.0, rel=0.01)


def test_powertrain_peak_found_in_stationary_and_ratio_small_on_road():
    rng = np.random.default_rng(9)
    n = int(120 * FS)
    t = np.arange(n) / FS
    stat = 0.02 * rng.standard_normal(n) + 0.3 * np.sin(2 * np.pi * 37.0 * t)
    noise = bandnoise(n, FS, 2, 40, 1.0, rng)
    road = noise + 0.3 * np.sin(2 * np.pi * 37.0 * t)
    cfg = Config()
    fs_, ps_ = powertrain.welch(stat, FS, cfg.welch_seg_s)
    fr, pr = powertrain.welch(road, FS, cfg.welch_seg_s)
    fn, pn = powertrain.welch(noise, FS, cfg.welch_seg_s)
    res = powertrain.powertrain({"low": (fs_, ps_)}, {"pass1": (fr, pr), "noise": (fn, pn)}, cfg)
    pk = res["peaks"]["low"]
    assert len(pk) == 1 and pk[0]["f_hz"] == pytest.approx(37.0, abs=0.3)
    # the 0.3 amplitude line adds power 0.045 to a road power of about 1.045; the +-1 Hz band also holds road noise
    r_road, r_noise = (r["line_energy_ratio"] for r in res["ratios"])
    assert r_road - r_noise * (1.0 / 1.045) == pytest.approx(0.045 / 1.045, abs=0.01)
    assert res["ratios"][0]["stationary_low_over_road"] == pytest.approx((0.045 + 0.0004 * 38 / 100) / 1.045,
                                                                         abs=0.01)
