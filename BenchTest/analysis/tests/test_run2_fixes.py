"""Fixes of 24 Oct 2026 for run 2: RQ4 band and order tracking, bins as ICC rows, descriptive pothole counts, and the
run-sheet marker grammar ("R2 A v10 p1 start" ... "end")."""
import json

import numpy as np
import pytest

from BenchTest.analysis import dsp, pothole as ph, powertrain as pt, run, segment as sg, stats
from BenchTest.analysis.config import Config
from synth import bandnoise, pothole_shape, write_session

FS = 200.0


# ---------------------------------------------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------------------------------------------

def test_run2_marker_grammar():
    mk = [(0.0, "R2 session start lab"), (10.0, "R2 STANDS M r2 start"), (70.0, "R2 STANDS M r2 end"),
          (80.0, "R2 STANDS M r2 meter V=72.1 I=4.2"), (100.0, "R2 A v10 p1 start"), (130.0, "R2 A v10 p1 end"),
          (140.0, "R2 NOTE A v15 p3 not steady"), (150.0, "R2 A coast p2 start"), (170.0, "R2 A coast p2 end"),
          (180.0, "R2 R v15 p4 start"), (200.0, "R2 R v15 p4 end"), (210.0, "R2 B v10 p5 start"),
          (220.0, "R2 B v10 p5 end"), (230.0, "R2 V5 object start"), (240.0, "R2 V5 object end"),
          (250.0, "R2 session end venue")]
    runs = [sg.classify_run(r, Config()) for r in sg.runs_from_markers(mk)]
    got = [(r.name, r.kind, r.section, r.setting, r.pass_no, r.closed) for r in runs]
    assert got == [
        ("R2 STANDS M r2", "stationary", "", "M", 2, True),
        ("R2 A v10 p1", "smooth", "A", "10kmh", 1, True),
        ("R2 A coast p2", "coast", "A", "coast", 2, True),
        ("R2 R v15 p4", "rough", "R", "15kmh", 4, True),
        ("R2 B v10 p5", "bump", "B", "10kmh", 5, True),
        ("R2 V5 object", "event", "V5", "", None, True),
    ]
    assert runs[1].duration == 30.0


def test_old_grammar_unchanged():
    runs = [sg.classify_run(r, Config()) for r in sg.runs_from_markers(
        [(0.0, "S2 smooth pass3 18kmh start"), (20.0, "S2 smooth pass3 18kmh stop")])]
    assert [(r.section, r.kind, r.pass_no, r.setting) for r in runs] == [("S2", "smooth", 3, "18kmh")]


# ---------------------------------------------------------------------------------------------------------------
# Bins and ICC
# ---------------------------------------------------------------------------------------------------------------

def test_section_bins_from_crossings_scale_to_length():
    # speed rises linearly from 2 to 4 m/s over 10 s: 30 m driven, section declared 50 m between the lines
    v = lambda t: 2.0 + 0.2 * t
    edges, how = sg.section_bins(0.0, 10.0, 50.0, 5.0, v, window_from_lines=True)
    assert len(edges) == 11 and edges[0] == pytest.approx(0) and edges[-1] == pytest.approx(10)
    # distance fraction at edge j is j/10: solve 2t + 0.1 t^2 = 3 j
    for j, t in enumerate(edges):
        assert 2 * t + 0.1 * t * t == pytest.approx(3.0 * j, abs=0.02)
    assert "scaled to the 50 m section" in how


def test_section_bins_without_speed_are_time_fractions():
    edges, how = sg.section_bins(100.0, 118.0, 50.0, 5.0, None)
    assert np.allclose(edges, np.linspace(100, 118, 11)) and "constant speed assumed" in how


def test_section_bins_from_markers_with_speed():
    edges, how = sg.section_bins(0.0, 10.0, 50.0, 5.0, lambda t: 3.0)
    assert len(edges) == 7 and np.allclose(np.diff(edges), 5.0 / 3.0)       # 30 m: six whole 5 m bins
    assert "from the start marker" in how


def test_bin_icc_known_answer_and_n_guard():
    rng = np.random.default_rng(4)
    profile = rng.uniform(0.3, 1.5, 10)                                       # roughness of ten 5 m bins
    table = {p: profile + 0.02 * rng.standard_normal(10) for p in range(1, 7)}
    r = stats.bin_icc(table)
    assert (r["n_rows"], r["k_passes"]) == (10, 6) and r["icc2_1"] > 0.98
    assert r["icc2_1_ci"][0] < r["icc2_1"] < r["icc2_1_ci"][1] and "optimistic" in r["status"]
    noise = {p: 1.0 + 0.1 * rng.standard_normal(10) for p in range(1, 7)}
    assert stats.bin_icc(noise)["icc2_1"] < 0.4
    few = stats.bin_icc({1: profile[:4], 2: profile[:4], 3: profile[:4]})
    assert np.isnan(few["icc2_1"]) and few["status"].startswith("n too small") and "rows 4" in few["status"]
    two = stats.bin_icc({1: profile, 2: profile})
    assert np.isnan(two["icc2_1"]) and "passes 2" in two["status"]


def test_single_section_icc_is_refused():
    rows = [{"section": "A 10kmh", "pass_no": p, "a_w": 0.5 + 0.01 * p} for p in range(1, 7)]
    rep = stats.repeatability(rows, metrics=("a_w",), n_boot=200)
    assert np.isnan(rep["icc"]["a_w"]["icc2_1"]) and rep["icc"]["a_w"]["status"].startswith("n too small")
    assert rep["per_section"][0]["n"] == 6 and np.isfinite(rep["per_section"][0]["cv"])


def test_bin_metrics_of_known_signal():
    t = 1.79e9 + np.arange(int(20 * FS)) / FS
    x = np.where(t - t[0] < 10, 1.0, 2.0) * np.sin(2 * np.pi * 8.0 * (t - t[0]))
    c = dsp.Chunk(t=t, fs=FS, acc=None, av=x, bp=x, wk=x, lp=x, clip=np.zeros(len(t), bool), tm=t, lpm=x)
    b = dsp.bin_metrics(dsp.Vertical("n", 1, [c]), [t[0], t[0] + 10, t[0] + 20, t[0] + 30])
    assert b[0]["a_w"] == pytest.approx(1 / np.sqrt(2), rel=1e-3)
    assert b[1]["a_w"] == pytest.approx(2 / np.sqrt(2), rel=1e-3)
    assert np.isnan(b[2]["a_w"])                                              # no data: no value


def test_wilson_and_poisson_known_values():
    lo, hi = stats.wilson_ci(5, 5)
    assert lo == pytest.approx(0.5655, abs=1e-4) and hi == 1.0
    lo, hi = stats.wilson_ci(4, 5)
    assert lo == pytest.approx(0.3755, abs=1e-4) and hi == pytest.approx(0.9638, abs=1e-4)
    assert stats.poisson_upper(0) == pytest.approx(-np.log(0.05), rel=1e-6)   # 3.00 events: the rule of three


# ---------------------------------------------------------------------------------------------------------------
# RQ4
# ---------------------------------------------------------------------------------------------------------------

def _psd(x, cfg):
    return pt.welch(x, FS, cfg.welch_seg_s)


def test_rq4_band_sees_the_40_to_70_hz_stand_lines():
    """Road noise (2 to 25 Hz, so that its filter skirts stay clear of the lines) plus the three stand lines: the old
    2 to 40 Hz measure found no line energy; the RQ4 band (0.5 to 80 Hz) gives the lines' share of the total."""
    rng = np.random.default_rng(11)
    cfg = Config()
    n = int(120 * FS)
    t = np.arange(n) / FS
    lines = 0.2 * sum(np.sin(2 * np.pi * f * t + k) for k, f in enumerate(cfg.pt_stand_lines_hz))
    stand = 0.02 * rng.standard_normal(n) + lines
    road = bandnoise(n, FS, 2, 25, 1.0, rng) + lines
    res = pt.powertrain({"M": _psd(stand, cfg)}, {"p1": _psd(road, cfg)}, cfg)
    assert [round(p["f_hz"], 2) for p in res["peaks"]["M"]] == [42.75, 49.0, 64.0]
    r = res["ratios"][0]
    assert r["band_hz"] == "0.5-80" and r["lines_hz"] == [42.75, 49.0, 64.0]
    line_power = 3 * 0.2 ** 2 / 2
    assert r["line_share"] == pytest.approx(line_power / (1.0 + line_power), abs=0.01)
    assert r["share_40-80"] == pytest.approx(r["line_share"], abs=0.01)
    assert "fixed stand lines" in r["line_method"] and "no speed" in r["line_method"]
    # the previous measure: line bands clipped to 2 to 40 Hz hold none of the three lines
    f, p = _psd(road, cfg)
    m = np.zeros(len(f), bool)
    for fl in res["lines_hz"]:
        m |= np.abs(f - fl) <= cfg.peak_halfwidth_hz
    assert not (m & (f >= cfg.band_lo_hz) & (f <= cfg.band_hi_hz)).any()


def test_rq4_without_stand_run_uses_23_oct_lines():
    rng = np.random.default_rng(12)
    cfg = Config()
    res = pt.powertrain({}, {"p1": _psd(bandnoise(int(60 * FS), FS, 2, 25, 1.0, rng), cfg)}, cfg)
    assert res["fixed_lines_hz"] == [42.75, 49.0, 64.0] and "23 Oct" in res["fixed_lines_source"]
    assert res["ratios"][0]["line_share"] < 0.02


def test_rq4_order_tracking_follows_speed():
    """Orders from the stand (wheel at 4 rev/s, line at 48 Hz: order 12); on the road at 3 m/s with C = 1.5 m the
    wheel turns at 2 rev/s, so the line is at 24 Hz, where the fixed 48 Hz band would miss it."""
    rng = np.random.default_rng(13)
    cfg = Config()
    cfg.update({"wheel_circumference_m": 1.5, "stand_wheel_hz": {"H": 4.0}})
    n = int(120 * FS)
    t = np.arange(n) / FS
    stand = 0.02 * rng.standard_normal(n) + 0.3 * np.sin(2 * np.pi * 48.0 * t)
    road = bandnoise(n, FS, 2, 40, 1.0, rng) + 0.3 * np.sin(2 * np.pi * 24.0 * t)
    res = pt.powertrain({"H": _psd(stand, cfg)}, {"p1": _psd(road, cfg)}, cfg, {"p1": (3.0, 0.0, "video")})
    assert res["orders"] == [pytest.approx(12.0)] and "stand_wheel_hz" in res["orders_source"]
    r = res["ratios"][0]
    assert r["lines_hz"] == [24.0] and r["line_method"].startswith("orders 12.00")
    assert r["line_share"] > 0.04
    no_speed = pt.powertrain({"H": _psd(stand, cfg)}, {"p1": _psd(road, cfg)}, cfg)["ratios"][0]
    assert no_speed["lines_hz"] == [48.0] and no_speed["line_share"] < 0.01
    # speed spread in the pass widens the band: order 12, sd 0.15 m/s, C 1.5 m: +1.2 Hz
    wide = pt.powertrain({"H": _psd(stand, cfg)}, {"p1": _psd(road, cfg)}, cfg, {"p1": (3.0, 0.15, "GNSS")})
    assert wide["ratios"][0]["line_halfwidth_hz"] == [pytest.approx(cfg.peak_halfwidth_hz + 1.2)]


def test_coast_vs_powered_matched_speed():
    rng = np.random.default_rng(14)
    cfg = Config()
    n = int(60 * FS)
    t = np.arange(n) / FS
    road = lambda: bandnoise(n, FS, 2, 25, 1.0, rng)
    line = 0.5 * np.sin(2 * np.pi * 64.0 * t)
    psd = {"c1": _psd(road(), cfg), "p1": _psd(road() + line, cfg), "p2": _psd(road() + line, cfg),
           "p3": _psd(road() + line, cfg)}
    speeds = {"c1": (5.0, 0.1, "v"), "p1": (5.1, 0.1, "v"), "p2": (4.9, 0.1, "v"), "p3": (7.0, 0.1, "v")}
    res = pt.powertrain({}, psd, cfg, speeds)
    out = pt.coast_vs_powered(res["ratios"], {"c1": "coast", "p1": "smooth", "p2": "smooth", "p3": "smooth"},
                              dict.fromkeys(psd, "A"), cfg)
    assert len(out) == 1 and out[0]["powered_passes"] == ["p1", "p2"]      # p3 is 7 m/s: not matched
    assert out[0]["dB_line_energy"] > 10 and abs(out[0]["dB_E_4-8"]) < 1.0


# ---------------------------------------------------------------------------------------------------------------
# Potholes: counts, not rates
# ---------------------------------------------------------------------------------------------------------------

def _cands(seconds, seed, events=(), bump_at=None):
    rng = np.random.default_rng(seed)
    n = int(seconds * FS)
    x = bandnoise(n, FS, 1, 60, 0.5, rng)
    for te in events:
        k = int(te * FS)
        x[k:k + len(pothole_shape(FS))] += pothole_shape(FS, 6.0)
    if bump_at is not None:
        h = np.sin(np.pi * np.arange(int(0.15 * FS)) / (0.15 * FS))
        k = int(bump_at * FS)
        x[k:k + 2 * len(h)] += 6.0 * np.r_[h, -h]
    t = 1.79e9 + seed * 1000 + np.arange(n) / FS
    return t, ph.candidates(t, dsp.bandpass(x, FS, 2, 40, 4), FS, Config())


def test_pass_counts_and_descriptive_wording():
    cfg = Config()
    passes, lt, ly = [], [], []
    for k in range(3):
        t, c = _cands(20, 300 + k, events=(8.0,))
        passes.append({"name": f"P{k}", "kind": "obstacle", "cands": c, "km": 0.05, "t0": t[0], "t1": t[-1]})
        lt.append(t[0] + 8.09)
        ly.append("pothole")
    t, c = _cands(20, 400)
    passes.append({"name": "A1", "kind": "smooth", "cands": c, "km": 0.05, "t0": t[0], "t1": t[-1]})
    rows = ph.pass_counts(passes, 4.0, 0.0, cfg, lt, ly)
    assert [(r["expected"], r["hits"], r["misses"]) for r in rows] == [(1, 1, 0)] * 3 + [(0, 0, 0)]
    s = ph.counts_summary(rows)
    assert (s["events_expected"], s["hits"], s["false_alarms"]) == (3, 3, 0) and s["km_driven"] == pytest.approx(0.2)
    assert s["wording"].startswith("descriptive, n = 4 passes, 3 expected events, 0.200 km driven")
    assert s["hit_ci_wilson"][0] == pytest.approx(0.4385, abs=1e-3)          # 3 of 3: wide, as it should be
    sw = ph.sweep(passes, cfg, label_t=lt, label_type=ly)
    hits = [r["hits"] for r in sorted(sw, key=lambda r: r["k"])]
    fas = [r["false_alarms"] for r in sorted(sw, key=lambda r: r["k"])]
    assert hits == sorted(hits, reverse=True) and fas == sorted(fas, reverse=True)
    assert hits[0] == 3 and hits[-1] <= 1


def test_bump_detection_counted_as_bump_flagged_not_hit():
    cfg = Config()
    t, c = _cands(20, 500, bump_at=6.0)
    p = {"name": "B1", "kind": "bump", "cands": c, "km": 0.05, "t0": t[0], "t1": t[-1]}
    rows = ph.pass_counts([p], 0.0, 0.0, cfg, [t[0] + 6.1], ["speed bump"])
    assert rows[0]["hits"] == 0 and rows[0]["expected"] == 0
    assert rows[0]["detections"] == rows[0]["bump_flagged"] + rows[0]["false_alarms"]


# ---------------------------------------------------------------------------------------------------------------
# Pipeline with video crossings
# ---------------------------------------------------------------------------------------------------------------

def test_pipeline_with_crossings(tmp_path):
    """Crossings 2 s inside each smooth pass (16 s at 5 m/s = 80 m, declared 80 m): windows from the video, ten 8 m
    bins per pass scaled to the section, the video speed used for RQ4 and the RQ4 band recorded."""
    sess, out = tmp_path / "s", tmp_path / "o"
    truth = write_session(str(sess))
    with open(sess / "crossings.csv", "w", encoding="utf-8") as f:
        f.write("run,t_in,t_out\n")
        for name, a, b in truth["runs"]:
            if "smooth" in name:
                f.write(f"{name},{a + 2:.3f},{b - 2:.3f}\n")
    with open(sess / "session.json", "w", encoding="utf-8") as f:
        json.dump({"wheelbase_m": 1.8, "section_length_m": 80.0, "icc_bin_m": 8.0}, f)
    S = run.analyse_session(str(sess), str(out), make_figures=False)
    assert S["crossings"]["runs"] == 9
    assert S["bands"]["rq4_hz"] == [0.5, 80.0] and S["bands"]["ride_hz"] == [2.0, 40.0]
    bins = [r for r in S["repeatability"]["rear1"]["bins"] if r["metric"] == "a_w" and r["group"] == "S1 18kmh"]
    assert bins[0]["n_rows"] == 10 and "scaled to the 80 m section" in bins[0]["bins_method"]
    rq4 = {r["pass"]: r for r in S["powertrain"]["ratios"]}
    r = rq4["S1 smooth pass1 18kmh"]
    assert r["speed_source"] == "video crossings" and r["speed_mps"] == pytest.approx(5.0, rel=1e-6)
    assert r["band_hz"] == "0.5-80"
