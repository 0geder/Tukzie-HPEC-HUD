"""End to end: a synthetic run-2 session with known answers, and the real run-1 recording of 19 Oct 2026."""
import json
import os

import numpy as np
import pytest

from BenchTest.analysis import readers as rd, segment as sg, run
from synth import write_session

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RUN1 = os.path.join(ROOT, "BenchTest", "logs", "roadtest_2026-10-19")
RUN1_FILE = os.path.join(RUN1, "2026-10-19_171534_roadtest.jsonl")


@pytest.fixture(scope="module")
def synth_result(tmp_path_factory):
    d = tmp_path_factory.mktemp("session")
    truth = write_session(str(d))
    out = tmp_path_factory.mktemp("out")
    rc = run.main(["--session", str(d), "--out", str(out)])
    assert rc == 0
    with open(out / "summary.json", encoding="utf-8") as f:
        return truth, json.load(f), out


def test_synthetic_session_raw_and_dedup(synth_result):
    truth, S, out = synth_result
    assert S["dash"]["rear"]["bad_json_lines"] == 1
    assert S["dash"]["rear"]["rows"] == 2 * S["dash"]["rear"]["unique"]
    for key in ("front1", "rear1", "rear2"):
        r = S["raw"][key]
        assert r["seq_gaps_samples"] == 30 and r["scale_source"] == "RAWH" and r["rdfail"] == 30
        assert r["lines_rejected"]["RAW"] == 0 and "host receive" in r["clock"]
    assert len(S["runs"]) == len(truth["runs"]) == 16
    assert not S["skipped"].get("raw")


def test_synthetic_repeatability(synth_result):
    _, S, _ = synth_result
    # three sections are too few rows for an ICC with sections as rows: said so, CV only (NaN is null in the JSON)
    icc = S["repeatability"]["rear1"]["icc"]["a_w"]
    assert icc["n_sections"] == 3 and icc["icc2_1"] is None and icc["status"].startswith("n too small")
    cvs = [r for r in S["repeatability"]["rear1"]["per_section"] if r["metric"] == "a_w"]
    assert {r["section"] for r in cvs} == {"S1 18kmh", "S2 18kmh", "S3 18kmh"}
    assert all(r["cv"] < 0.1 for r in cvs)
    assert all(np.isfinite(r["cv"]) for r in S["repeatability"]["rear1"]["per_section"]
               if r["metric"] == "index_sigma2_per_v")
    # bins along each section as rows: 100 m passes (20 s at 5 m/s), 5 m bins, the partial last bin dropped
    bins = [r for r in S["repeatability"]["rear1"]["bins"] if r["metric"] == "a_w"]
    per = [r for r in bins if not r["group"].startswith("sections")]
    assert len(per) == 3
    for r in per:
        assert (r["n_rows"], r["k_passes"]) == (19, 3) and r["ICC(2,1)"] > 0.9
        assert r["ICC(2,1) CI"][0] < r["ICC(2,1)"] < r["ICC(2,1) CI"][1]
        assert "integrated speed" in r["bins_method"]
    pooled = [r for r in bins if r["group"].startswith("sections")]
    assert len(pooled) == 1 and pooled[0]["n_rows"] == 57 and pooled[0]["ICC(2,1)"] > 0.95


def test_synthetic_delay_and_speed(synth_result):
    truth, S, _ = synth_result
    ds = [r for r in S["delay"] if "smooth" in r["run"]]
    assert len(ds) == 9
    for r in ds:
        assert r["delay_s"] == pytest.approx(truth["delay"], abs=0.01)
        assert r["speed_mps"] == pytest.approx(truth["speed"], rel=0.03)


def test_synthetic_powertrain(synth_result):
    _, S, _ = synth_result
    pk = S["powertrain"]["peaks"]
    assert set(pk) == {"low", "high"}
    for v in pk.values():
        assert any(abs(p["f_hz"] - 37.0) < 0.3 for p in v)


def test_synthetic_pothole_calibration_and_evaluation(synth_result):
    _, S, out = synth_result
    cal = S["pothole"]["threshold"]
    assert cal["chosen"]["detection_rate"] == 1.0 and cal["chosen"]["false_alarms"] == 0
    assert cal["basis"] == ["labelled"]
    assert cal["descriptive"].startswith("descriptive, n = 5 obstacle events, 9 smooth passes")
    c = S["pothole"]["counts"]
    assert (c["events_expected"], c["hits"], c["misses"], c["false_alarms"]) == (5, 5, 0, 0)
    assert c["wording"].startswith("descriptive, n = 14 passes") and "per km is claimed" in c["wording"]
    assert c["false_alarms_upper95"] == pytest.approx(2.996, abs=0.001)
    ev = S["pothole"]["evaluation"]
    assert (ev["labels"], ev["tp"], ev["fn"]) == (5, 5, 0) and ev["fp"] == 0


def test_synthetic_outputs_written(synth_result):
    _, S, out = synth_result
    for name in ("pass_metrics", "runs", "driving_segments", "front_rear_delay", "pothole_sweep", "pothole_counts",
                 "powertrain_peaks", "powertrain_ratios", "powertrain_stands", "repeatability_bin_icc_rear1"):
        for ext in (".csv", ".tex"):
            assert (out / "tables" / (name + ext)).is_file(), name + ext
    for name in ("session", "psd", "pothole_sweep", "pass_aw_rear1"):
        for ext in (".pdf", ".png"):
            assert (out / "figures" / (name + ext)).is_file(), name + ext
    tex = (out / "tables" / "pass_metrics.tex").read_text(encoding="utf-8")
    assert tex.startswith("% generated") and "\\begin{tabular}" in tex and "—" not in tex


# ---------------------------------------------------------------------------------------------------------------
# Real recording, road session 1 (19 Oct 2026). Expected numbers from the report (Results, Method) and
# Planning/lab-notebook.md, 21 Oct.
# ---------------------------------------------------------------------------------------------------------------
needs_run1 = pytest.mark.skipif(not os.path.isfile(RUN1_FILE), reason="run-1 recording not on this machine")


@needs_run1
def test_run1_dedup_and_driving_rule():
    d = rd.read_dash(RUN1_FILE)
    assert d.stats["unique"] == 3464 and d.stats["rows_with_record"] == 10287 and d.stats["boots"] == 1
    assert (d.stats["seq_first"], d.stats["seq_last"], d.stats["missing"]) == (4549, 10105, 2093)
    drv = sg.label_driving(d.i, d.vib)
    assert int(drv.sum()) == 607
    assert int((drv & d.readable).sum()) == 605
    assert np.nanmedian(d.vib[~drv & d.readable]) == pytest.approx(0.03, abs=0.0005)
    assert np.nanmedian(d.vib[drv & d.readable]) == pytest.approx(1.39, abs=0.005)
    assert int((~drv & d.readable).sum()) == 2832
    # the report and notebook give "3.1"; numpy's default (linear) 95th percentile is 3.174, so 3.2 to two figures
    assert np.nanpercentile(d.vib[drv & d.readable], 95) == pytest.approx(3.174, abs=0.001)
    assert np.nanmax(d.vib[drv]) == pytest.approx(5.09, abs=0.005)
    # segments: 26 after 18:15, 965 s counted inclusively (lab notebook 21 Oct)
    segs = sg.driving_segments(d.seq.astype(float), drv, 10.0)
    k1815 = d.seq[np.searchsorted(d.t, 1792426500.0)]
    after = [s for s in segs if s[0] >= k1815]
    assert len(after) == 26 and sum(b - a + 1 for a, b in after) == 965


@needs_run1
def test_run1_pipeline_runs_dash_only(tmp_path):
    """The whole folder: the main file plus the two short files after the Pi 5 restarts (ESP32 rebooted too, so its
    seq restarted: 99 and 16 more records, 2 of them driving). The report's numbers are the main file's."""
    S = run.analyse_session(RUN1, str(tmp_path))
    assert S["dash"]["rear"]["boots"] == 3 and S["dash"]["rear"]["unique"] == 3464 + 99 + 16
    assert S["dash"]["rear"]["per_boot"][0]["unique"] == 3464
    dr = S["driving"]
    assert (dr["records_driving"], dr["records_driving_readable"]) == (609, 607)
    assert dr["vib_max_driving"] == pytest.approx(5.09, abs=0.005)
    assert dr["gnss_fix_records"] == 0
    assert "raw" in S["skipped"] and "runs" in S["skipped"]
    assert (tmp_path / "figures" / "session.pdf").is_file()
    assert (tmp_path / "tables" / "driving_segments.tex").is_file()
