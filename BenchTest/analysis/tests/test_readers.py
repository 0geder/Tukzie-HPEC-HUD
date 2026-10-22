import os
import shutil
import subprocess

import numpy as np
import pytest

from BenchTest.analysis import readers as rd
from BenchTest.analysis import segment as sg
from BenchTest.analysis.config import Config, G0

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HEADER = os.path.join(ROOT, "TelemetryUnit", "include", "raw_stream.h")


def _samples(n=25, seed=0):
    rng = np.random.default_rng(seed)
    seq = np.cumsum(np.r_[100, np.ones(n - 1, int)])
    seq[12:] += 3                                       # three missing samples
    t_us = 123456789 + (seq - seq[0]) * 5000 + rng.integers(-30, 30, n)
    counts = rng.integers(-32768, 32767, (n, 6))
    counts[0, :3] = [0, 0, 4096]
    flags = rng.integers(0, 4, n).astype(np.uint8)
    return seq, t_us, counts, flags


def test_crc_reference_value():
    # CRC-16/CCITT-FALSE check value of "123456789" is 0x29B1
    assert rd.crc16_ccitt_false(b"123456789") == 0x29B1


def test_raw_v2_roundtrip_and_damage(tmp_path):
    seq, t_us, counts, flags = _samples()
    lines = [rd.encode_raw_header("rear", 1, rawdrop=2, rdfail=1, stuck=0)]
    for a in range(0, len(seq), 10):
        b = min(a + 10, len(seq))
        lines.append(rd.encode_raw_line("rear", 1, seq[a:b], t_us[a:b], counts[a:b], flags[a:b],
                                        host_t=1792430000.0 + a / 200))
    lines.append(rd.encode_raw_sync("rear", 1, 1, 123500000))
    lines.append(rd.encode_raw_sync("rear", 2, 0, 124000000))
    bad = lines[2].replace("RAW 2 rear 1", "RAW 2 rear 2")      # CRC no longer matches
    text = "boot log line\nDASH {...}\n" + "".join(lines[:2]) + bad + "".join(lines[2:])
    p = tmp_path / "rear_raw.txt"
    p.write_text(text, encoding="utf-8")
    out = rd.read_raw_stream(str(p))
    assert list(out) == [("rear", 1)]
    s = out[("rear", 1)]
    assert np.array_equal(s.seq, seq) and np.array_equal(s.t_us, t_us) and np.array_equal(s.flags, flags)
    assert np.allclose(s.acc, counts[:, :3] * G0 / 4096)
    assert np.allclose(s.gyr, counts[:, 3:] / 65.5 * np.pi / 180)
    assert s.stats["lines_rejected"]["RAW"] == 1 and s.stats["duplicates"] == 0
    assert s.stats["seq_gaps_samples"] == 3 and s.stats["rdfail"] == 1 and s.stats["rawdrop"] == 2
    assert s.header["accel_counts_per_g"] == 4096
    assert np.isfinite(s.host_t).all() and s.sync["edge"].tolist() == [1, 2]


@pytest.mark.skipif(not (shutil.which("g++") and os.path.isfile(HEADER)), reason="g++ or raw_stream.h missing")
def test_python_decoder_matches_firmware_encoder(tmp_path):
    """Compile the firmware's rawEncodeLine/rawEncodeHeader/rawEncodeSync and decode their output here."""
    with open(HEADER, encoding="utf-8") as f:
        if "#define RAW_FORMAT_VERSION %d" % rd.RAW_FORMAT["version"] not in f.read():
            pytest.skip("raw_stream.h is not format version %d" % rd.RAW_FORMAT["version"])
    seq, t_us, counts, flags = _samples(10, seed=4)
    init = ",".join("{%du,%dLL,%du,{%s}}" % (seq[k], t_us[k], flags[k], ",".join(str(int(c)) for c in counts[k]))
                    for k in range(10))
    src = tmp_path / "enc.cpp"
    src.write_text(
        '#include "raw_stream.h"\n#include <cstdio>\nint main(){RawSample s[10]={%s};char b[RAW_LINE_MAX];\n'
        'if(rawEncodeLine(b,sizeof b,"front",1,s,10)) fputs(b,stdout);\n'
        'if(rawEncodeHeader(b,sizeof b,"front",1,4096,65.5f,200,44,"0.7.5",5,6,7)) fputs(b,stdout);\n'
        'if(rawEncodeSync(b,sizeof b,"front",9,1,1234567)) fputs(b,stdout);return 0;}\n' % init, encoding="utf-8")
    exe = tmp_path / "enc.exe"
    r = subprocess.run(["g++", "-std=c++17", "-O1", "-I", os.path.dirname(HEADER), str(src), "-o", str(exe)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    txt = subprocess.run([str(exe)], capture_output=True, text=True, check=True).stdout
    lines = txt.splitlines(keepends=True)
    assert len(lines) == 3
    assert lines[0] == rd.encode_raw_line("front", 1, seq, t_us, counts, flags)
    assert lines[1] == rd.encode_raw_header("front", 1, rawdrop=5, rdfail=6, stuck=7)
    assert lines[2] == rd.encode_raw_sync("front", 9, 1, 1234567)
    p = rd.parse_raw_line(lines[0])
    assert np.array_equal(p["seq"], seq) and np.array_equal(p["counts"], counts)
    h = rd.parse_raw_line(lines[1])
    assert (h["rawdrop"], h["rdfail"], h["stuck"], h["gyro_counts_per_dps"]) == (5, 6, 7, 65.5)


def test_csv_fallback(tmp_path):
    n = 50
    s = rd.ImuStream("front", 1, np.arange(n), np.arange(n) * 5000, np.tile([0, 0, G0], (n, 1)),
                     np.zeros((n, 3)), np.full(n, np.nan))
    p = tmp_path / "front_raw.csv"
    rd.write_raw_csv(str(p), s)
    out = rd.read_raw_stream(str(p))
    r = out[("front", 1)]
    assert r.stats["format"] == "CSV fallback" and len(r) == n and np.allclose(r.acc[:, 2], G0)


def test_markers_and_runs(tmp_path):
    rec = tmp_path / "x_roadtest.jsonl"
    rec.write_text("\n".join([
        '{"t":1792430100.0,"src":"marker","text":"session start"}',
        '{"t":1792430110.0,"src":"marker","text":"S1 smooth pass1 20kmh start"}',
        '{"t":1792430140.0,"src":"marker","text":"S1 smooth pass1 20kmh stop"}',
        '{"t":1792430150.0,"src":"marker","text":"stationary low start"}',
        'garbage',
        '{"t":1792430180.0,"src":"marker","text":"stationary low stop"}',
        '{"t":1792430190.0,"src":"marker","text":"S2 plank pass3 start"}',
    ]) + "\n", encoding="utf-8")
    txt = tmp_path / "roadtest_markers.txt"
    txt.write_text("1792430200.5 S2 plank pass3 stop\nno time on this line\n", encoding="utf-8")
    mk, untimed = rd.read_markers([str(rec)], str(txt))
    assert [m[1] for m in mk][-1] == "S2 plank pass3 stop" and untimed == ["no time on this line"]
    runs = [sg.classify_run(r, Config()) for r in sg.runs_from_markers(mk)]
    assert [(r.name, r.kind, r.section, r.pass_no, r.setting) for r in runs] == [
        ("S1 smooth pass1 20kmh", "smooth", "S1", 1, "20kmh"),
        ("stationary low", "stationary", "", None, "low"),
        ("S2 plank pass3", "obstacle", "S2", 3, ""),
    ]
    assert runs[0].duration == 30.0 and runs[2].t1 == 1792430200.5
    # the recorder's own "session start" marker does not open a run
    assert all(r.closed for r in runs)


def test_fit_clock_lower_envelope():
    rng = np.random.default_rng(2)
    dev = np.arange(0, 3600, 1.0)
    host = 1.79e9 + 1.00002 * dev + 0.05 + rng.exponential(0.2, len(dev))   # latency >= 0
    off, rate, res = rd.fit_clock(dev, host)
    assert rate == pytest.approx(1.00002, abs=2e-6)
    assert off == pytest.approx(1.79e9 + 0.05, abs=0.02)


def test_driving_rule_and_join():
    cur = np.array([0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -5, 0])
    vib = np.array([0, 0, 0.5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, np.nan])
    d = sg.label_driving(cur, vib)
    assert d.tolist() == [False, True, True] + [False] * 11 + [True, False]
    t = np.arange(16.0)
    assert sg.driving_segments(t, d, 10) == [(1.0, 2.0), (14.0, 14.0)]
    assert sg.driving_segments(t, d, 12) == [(1.0, 14.0)]


REF = os.path.join(ROOT, "TelemetryUnit", "tools", "raw_stream_decode.py")


@pytest.mark.skipif(not os.path.isfile(REF), reason="reference decoder not present")
def test_parser_agrees_with_reference_decoder():
    """readers.parse_raw_line mirrors TelemetryUnit/tools/raw_stream_decode.py.parse_line (imported by path)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("raw_stream_decode", REF)
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)
    assert ref.FORMAT_VERSION == rd.RAW_FORMAT["version"]
    assert ref.RECORD_HEX == 2 * rd.RAW_FORMAT["record_bytes"] and ref.MAX_BATCH == rd.RAW_FORMAT["max_batch"]
    assert ref.DEFAULT_ACCEL_COUNTS_PER_G == rd.RAW_FORMAT["accel_counts_per_g"]
    assert ref.DEFAULT_GYRO_COUNTS_PER_DPS == rd.RAW_FORMAT["gyro_counts_per_dps"]
    seq, t_us, counts, flags = _samples(25, seed=11)
    lines = [rd.encode_raw_line("rear", 2, seq[a:a + 10], t_us[a:a + 10], counts[a:a + 10], flags[a:a + 10],
                                host_t=1792430000.0 + a) for a in range(0, 25, 10)]
    lines += [rd.encode_raw_header("front", 1, rawdrop=3, rdfail=4, stuck=5, host_t=1792430001.25),
              rd.encode_raw_sync("front", 7, 1, 99999, host_t=1792430001.5)]
    damaged = [lines[0][:60] + ("0" if lines[0][60] != "0" else "1") + lines[0][61:],
               lines[3].replace(" 3 4 5 ", " 3 4 6 "), "1792430002.0 RAW 2 rear 1 5 5 1 " + "0" * 32 + " 0000\n"]
    for ln in lines + damaged:
        kind, obj = ref.parse_line(ln)
        mine = rd.parse_raw_line(ln)
        if kind == "bad":
            assert mine is not None and mine.get("bad"), ln
            continue
        assert mine["type"].lower() == kind and mine["node"] == obj["node"]
        assert mine["host"] == pytest.approx(float(ln.split(" ", 1)[0]))
        if kind == "raw":
            assert mine["seq"].tolist() == [s["seq"] for s in obj["samples"]]
            assert mine["t_us"].tolist() == [s["t_us"] for s in obj["samples"]]
            assert mine["flags"].tolist() == [s["flags"] for s in obj["samples"]]
            assert mine["counts"].tolist() == [s["v"] for s in obj["samples"]]
        elif kind == "rawh":
            for k in ("imu", "accel_counts_per_g", "gyro_counts_per_dps", "rate_hz", "dlpf_hz", "fw", "rawdrop",
                      "rdfail", "stuck"):
                assert mine[k] == obj[k], k
        else:
            assert (mine["edge"], mine["level"], mine["t_us"]) == (obj["edge"], obj["level"], obj["t_us"])
    # the Pi capture layout "<host_epoch_s> <line>" with other text in between
    assert rd.parse_raw_line("1792430003.5 DASH {}\n") is None
