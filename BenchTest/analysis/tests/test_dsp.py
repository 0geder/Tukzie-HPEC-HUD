import numpy as np
import pytest

from BenchTest.analysis import dsp
from BenchTest.analysis.config import Config, G0
from BenchTest.analysis.readers import ImuStream
from synth import imu_counts_from_vertical

FS = 200.0


def test_wk_response_matches_iso_table3():
    """|Wk| from the Annex A transfer function against the Table 3 factors at 37 nominal frequencies."""
    for f, w1000 in dsp.WK_TABLE3.items():
        g = abs(dsp.wk_response(f)) * 1000
        assert g == pytest.approx(w1000, rel=0.004), f


def test_wk_known_points():
    # values every Wk user knows: about 0.48 at 1 Hz, peak just above 1 near 5 to 6.3 Hz, 0.5 near 25 Hz
    assert abs(dsp.wk_response(1.0)) == pytest.approx(0.482, abs=0.002)
    f = np.linspace(1, 20, 2000)
    fpk = f[np.argmax(abs(dsp.wk_response(f)))]
    assert 5.0 < fpk < 7.0 and abs(dsp.wk_response(fpk)) == pytest.approx(1.055, abs=0.01)


@pytest.mark.parametrize("f", [1.0, 2.0, 4.0, 6.3, 12.5, 31.5, 63.0])
def test_sine_through_wk_has_wk_gain(f):
    t = np.arange(int(40 * FS)) / FS
    x = 1.0 * np.sin(2 * np.pi * f * t)
    y = dsp.wk_filter(x, FS)
    mid = slice(int(10 * FS), int(30 * FS))
    gain = np.sqrt(2) * dsp.rms(y[mid])
    assert gain == pytest.approx(abs(dsp.wk_response(f)), rel=0.01)


def test_vdv_and_rms_of_known_sine():
    A, f, T = 2.0, 5.0, 10.0
    t = np.arange(int(T * FS)) / FS
    x = A * np.sin(2 * np.pi * f * t)
    assert dsp.rms(x) == pytest.approx(A / np.sqrt(2), rel=1e-3)
    assert dsp.vdv(x, FS) == pytest.approx(A * (3 * T / 8) ** 0.25, rel=1e-3)


def _stream(av, jitter_us=0, rng=None, tilt=(8.0, -5.0)):
    rng = rng or np.random.default_rng(0)
    acc, up = imu_counts_from_vertical(av, rng, tilt)
    n = len(av)
    t_us = (np.arange(n) * 5000 + (rng.integers(-jitter_us, jitter_us + 1, n) if jitter_us else 0)).astype(np.int64)
    return ImuStream("rear", 1, np.arange(n, dtype=np.int64), t_us, acc, np.zeros((n, 3)), np.full(n, np.nan)), up


def test_vertical_projection_and_bandpass_recover_amplitude():
    t = np.arange(int(60 * FS)) / FS
    av = 1.0 * np.sin(2 * np.pi * 5.0 * t)
    s, up = _stream(av)
    v = dsp.make_vertical(s, Config())
    c = v.chunks[0]
    assert np.allclose(c.g_hat, up, atol=1e-3)
    mid = slice(int(10 * FS), int(50 * FS))
    assert np.sqrt(2) * dsp.rms(c.bp[mid]) == pytest.approx(1.0, rel=0.02)
    assert abs(np.mean(c.av[mid])) < 0.01                      # gravity removed


def test_per_second_features_of_sine_with_measured_timestamps():
    A, f = 1.5, 5.0
    t = np.arange(int(30 * FS)) / FS
    s, _ = _stream(A * np.sin(2 * np.pi * f * t), jitter_us=200, rng=np.random.default_rng(3))
    v = dsp.make_vertical(s, Config())
    rows = dsp.per_second(v, 5.0, 25.0)
    assert len(rows) == 20
    sig = np.median([r["sigma"] for r in rows])
    crest = np.median([r["crest"] for r in rows])
    jerk = np.median([r["jerk"] for r in rows])
    assert sig == pytest.approx(A / np.sqrt(2), rel=0.02)
    assert crest == pytest.approx(np.sqrt(2), rel=0.03)
    assert jerk == pytest.approx(4 * A * f, rel=0.05)           # mean |da/dt| of a sine = 4 A f
    assert not any(r["clipped"] for r in rows)


def test_clipping_flag_at_configured_range():
    t = np.arange(int(10 * FS)) / FS
    av = 0.2 * np.sin(2 * np.pi * 3 * t)
    s, _ = _stream(av)
    s.acc[1100, 2] = 8.0 * G0
    v = dsp.make_vertical(s, Config())
    rows = dsp.per_second(v, 0, 10)
    flagged = [r["t"] for r in rows if r["clipped"]]
    assert len(flagged) == 1 and flagged[0] <= 1100 / FS < flagged[0] + 1


def test_gap_splits_chunks_and_small_gaps_are_filled():
    t = np.arange(int(20 * FS)) / FS
    s, _ = _stream(0.5 * np.sin(2 * np.pi * 4 * t))
    keep = np.ones(len(t), bool)
    keep[1000] = False                      # one missing sample: filled
    keep[2000:2040] = False                 # 200 ms: splits
    for k in ("seq", "t_us", "acc", "gyr", "host_t"):
        setattr(s, k, getattr(s, k)[keep])
    v = dsp.make_vertical(s, Config())
    assert len(v.chunks) == 2 and v.stats["filled_samples"] == 1


def test_speed_index_gate():
    out = dsp.speed_index([1.0, 1.0, 2.0], [0.5, 2.0, 4.0], v_min=1.0)
    assert np.isnan(out[0]) and out[1] == pytest.approx(0.5) and out[2] == pytest.approx(1.0)
