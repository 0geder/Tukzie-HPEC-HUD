"""Offline tests of the raw IMU capture in CameraDetection/telemetry_bridge.py
(firmware 0.7.5 RAW, RAWH and RAWS lines, TelemetryUnit/RAW_STREAM.md).

A byte stream with DASH lines, raw-stream lines, a corrupted raw line, boot
noise and a fragment on open is fed through the real serial reader loop
(LineSource) with a scripted port, in random chunk sizes. The capture file
is then checked line by line and decoded with the firmware's reference
decoder (TelemetryUnit/tools/raw_stream_decode.py), which must get back
every sample that was encoded.

Run: python CameraDetection/tests/test_bridge_raw.py (or with pytest)."""
import importlib.util
import json
import os
import random
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
import telemetry_bridge as tb  # noqa: E402

DECODER_PATH = os.path.join(REPO, "TelemetryUnit", "tools", "raw_stream_decode.py")


def load_decoder():
    if not os.path.exists(DECODER_PATH):
        return None
    spec = importlib.util.spec_from_file_location("raw_stream_decode", DECODER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DEC = load_decoder()


def crc_py(data):
    """Bitwise CRC-16/CCITT-FALSE, written out independently of the bridge."""
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def with_crc(payload):
    return "%s %04x" % (payload, crc_py(payload.encode()))


def raw_line(node, imu, seq0, t0, samples):
    """samples: list of (seq, t_us, flags, [ax..gz]); consecutive, steps < 256 and < 65536 us."""
    recs = []
    prev = None
    for seq, t, flags, v in samples:
        ds, dt = (0, 0) if prev is None else (seq - prev[0], t - prev[1])
        prev = (seq, t)
        rec = bytes([ds, dt >> 8, dt & 0xFF, flags]) + b"".join((x & 0xFFFF).to_bytes(2, "big") for x in v)
        recs.append(rec.hex())
    return with_crc("RAW 2 %s %d %d %d %d %s" % (node, imu, seq0, t0, len(samples), "".join(recs)))


def make_samples(seq0, t0, n, seed):
    rnd = random.Random(seed)
    out = []
    seq, t = seq0, t0
    for k in range(n):
        if k:
            seq += 1 if rnd.random() > 0.1 else 2     # an occasional missing slot
            t += 5000 + rnd.randint(-40, 40)
        out.append((seq, t, (k // 3) & 1 | (2 if k == 7 else 0), [rnd.randint(-32768, 32767) for _ in range(6)]))
    return out


DASH1 = 'DASH {"seq":1,"up_ms":1000,"fw":"0.7.5","node":"rear","rdfail":[0,0],"stuck":[0,0],"rawdrop":[0,0]}'
DASH2 = 'DASH {"seq":2,"up_ms":2000,"fw":"0.7.5","node":"rear","rdfail":[0,1],"stuck":[0,0],"rawdrop":[3,0]}'
RAWH1 = with_crc("RAWH 2 rear 1 4096 65.5 200 94 0.7.5 0 0 0")
RAWH2 = with_crc("RAWH 2 rear 2 4096 65.5 200 94 0.7.5 0 0 0")
RAWS1 = with_crc("RAWS 2 rear 41 1 20500123")
RAWS2 = with_crc("RAWS 2 rear 42 0 21000119")


def build_stream():
    """Returns (bytes, expected) for a stream with every kind of line."""
    s1 = make_samples(1000, 5000000, 10, 1)
    s2 = make_samples(1000, 5000210, 10, 2)
    s3 = make_samples(1012, 5060000, 7, 3)
    r1 = raw_line("rear", 1, s1[0][0], s1[0][1], s1)
    r2 = raw_line("rear", 2, s2[0][0], s2[0][1], s2)
    r3 = raw_line("rear", 1, s3[0][0], s3[0][1], s3)
    bad = r2[:40] + ("0" if r2[40] != "0" else "1") + r2[41:]          # one hex digit changed: CRC fails
    noisy = "[imu] task print " + r3                                    # print landed in front (USB case)
    good_raw = [r1, r2, noisy, RAWH1, RAWH2, RAWS1, RAWS2]
    lines = [
        '5,"x":1}',                       # fragment on open: skipped, not counted
        "ESP-ROM:esp32s3-20210327",       # boot noise: ignored
        DASH1, RAWH1, RAWH2, r1, r2, RAWS1,
        "[imu] IMU2 rate 200.2 Hz",
        bad, noisy, RAWS2, DASH2,
        "RAW junk without crc",           # has a type word: counted, bad CRC, written
    ]
    data = ("\n".join(lines) + "\n").encode()
    data = data.replace(RAWS1.encode() + b"\n", RAWS1.encode() + b"\r\n")   # one CRLF ending
    expected = {
        "dash": 2,
        "written": [ln for ln in lines if tb.classify_raw(ln.encode()) is not None],
        "raw": 3, "rawh": 2, "raws": 2, "bad_crc": 2,
        "samples": {("rear", 1): s1 + s3, ("rear", 2): s2},
        "good_raw": good_raw,
    }
    return data, expected


def chunks(data, seed):
    rnd = random.Random(seed)
    out, i = [], 0
    while i < len(data):
        n = rnd.choice((1, 3, 17, 64, 200, 700))
        out.append(data[i:i + n])
        i += n
    return out


class ScriptedPort:
    def __init__(self, parts, done):
        self.parts = list(parts)
        self.done = done

    def read(self):
        if not self.parts:
            self.done.set()
            time.sleep(0.01)
            return b""
        return self.parts.pop(0)

    def close(self):
        pass


def run_reader(data, raw, seed=0):
    """Feeds data through LineSource._run_serial with a scripted port; returns the state."""
    state = tb.TelemetryState("fake", raw=raw)
    done = threading.Event()
    real_open, real_idle = tb.open_serial, tb.READ_IDLE_S
    tb.open_serial, tb.READ_IDLE_S = (lambda port, baud: ScriptedPort(chunks(data, seed), done)), 0.0
    stop = threading.Event()
    src = tb.LineSource(state, stop, port="/dev/fake")
    try:
        src.start()
        assert done.wait(10), "reader did not consume the stream"
        time.sleep(0.05)
    finally:
        stop.set()
        src.join(3)
        tb.open_serial, tb.READ_IDLE_S = real_open, real_idle
    return state


class CrcTests(unittest.TestCase):
    def test_check_value_and_lines(self):
        import binascii
        self.assertEqual(binascii.crc_hqx(b"123456789", 0xFFFF), 0x29B1)
        self.assertTrue(tb.raw_crc_ok(RAWH1.encode()))
        self.assertFalse(tb.raw_crc_ok(RAWH1[:-1].encode() + b"0" if RAWH1[-1] != "0" else RAWH1[:-1].encode() + b"1"))
        self.assertFalse(tb.raw_crc_ok(b"RAW 2 rear 1 5 5 1 00000000000000000000000000000000 0000"))
        self.assertFalse(tb.raw_crc_ok(RAWH1.upper().encode()))      # CRC digits must be lowercase
        self.assertEqual(tb.classify_raw(RAWS1.encode()), ("raws", True))
        self.assertEqual(tb.classify_raw(RAWH1.encode()), ("rawh", True))
        self.assertEqual(tb.classify_raw(b"x " + RAWH1.encode()), ("rawh", True))
        self.assertIsNone(tb.classify_raw(DASH1.encode()))
        self.assertIsNone(tb.classify_raw(b"[raw] stream on"))

    @unittest.skipIf(DEC is None, "reference decoder not found")
    def test_agrees_with_reference_decoder(self):
        rnd = random.Random(5)
        for _ in range(300):
            payload = "RAWS 2 front %d %d %d" % (rnd.randint(0, 10**6), rnd.randint(0, 1), rnd.randint(0, 2**40))
            line = with_crc(payload)
            if rnd.random() < 0.5:
                i = rnd.randrange(len(line))
                line = line[:i] + rnd.choice("0123456789abcdefRAW ") + line[i + 1:]
            want = DEC.parse_line(line)[0] == "raws"
            got = tb.classify_raw(line.encode())
            self.assertEqual(got is not None and got[1], want, line)


class StreamTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="sw7raw_")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def files(self):
        return sorted(os.path.join(self.dir, f) for f in os.listdir(self.dir))

    def test_stream_through_reader(self):
        data, exp = build_stream()
        for seed in range(4):
            shutil.rmtree(self.dir, ignore_errors=True)
            raw = tb.RawCapture(self.dir)
            t0 = time.time()
            state = run_reader(data, raw, seed)
            snap = state.snapshot()
            b, r = snap["bridge"], snap["bridge"]["raw"]
            # DASH handling unchanged: 2 DASH lines, latest kept, new fields passed through.
            self.assertEqual((b["lines"], b["bad_lines"]), (exp["dash"], 0))
            self.assertIsNone(snap["esp32"])                   # cleared when the reader stopped
            # Raw counts.
            self.assertEqual(r["lines"], len(exp["written"]))
            self.assertEqual((r["raw"], r["rawh"], r["raws"], r["bad_crc"]),
                             (exp["raw"], exp["rawh"], exp["raws"], exp["bad_crc"]))
            self.assertEqual((r["not_written"], r["write_errors"], r["files"], r["paused"]), (0, 0, 1, None))
            # One file, every raw line verbatim behind a host epoch time.
            files = self.files()
            self.assertEqual(len(files), 1)
            self.assertTrue(os.path.basename(files[0]).startswith("rear_raw_"))
            self.assertEqual(r["file"], os.path.basename(files[0]))
            with open(files[0], "rb") as f:
                content = f.read()
            self.assertEqual(r["bytes_written"], len(content))
            got = content.decode().splitlines()
            self.assertEqual(len(got), len(exp["written"]))
            for g, w in zip(got, exp["written"]):
                ts, line = g.split(" ", 1)
                self.assertEqual(line, w)
                self.assertTrue(t0 - 1 <= float(ts) <= time.time() + 1, ts)
                self.assertRegex(ts, r"^\d+\.\d{6}$")
            # The reference decoder reads the file as it is and gets every sample back.
            if DEC is not None:
                res = DEC.decode_file(files[0])
                self.assertEqual(res["counts"].get("raw"), 3)
                self.assertEqual(res["counts"].get("bad"), 1)     # "RAW junk" has no version: the decoder ignores it
                self.assertEqual(len(res["sync"]), 2)
                for key, want in exp["samples"].items():
                    got_s = [(s["seq"], s["t_us"], s["flags"], s["v"]) for s in res["samples"][key]]
                    self.assertEqual(got_s, [tuple(x) for x in want], key)

    def test_dash_still_served_with_raw_stream(self):
        data, _ = build_stream()
        raw = tb.RawCapture(self.dir)
        state = tb.TelemetryState("fake", raw=raw)
        seen = {}
        done = threading.Event()

        class Port(ScriptedPort):
            def read(inner):
                if not inner.parts:
                    seen["snap"] = state.snapshot()
                return ScriptedPort.read(inner)

        real_open = tb.open_serial
        tb.open_serial = lambda port, baud: Port(chunks(data, 9), done)
        stop = threading.Event()
        src = tb.LineSource(state, stop, port="/dev/fake")
        try:
            src.start()
            self.assertTrue(done.wait(10))
        finally:
            stop.set()
            src.join(3)
            tb.open_serial = real_open
        e = seen["snap"]["esp32"]
        self.assertEqual(e["seq"], 2)
        self.assertEqual(e["rawdrop"], [3, 0])
        self.assertEqual(e["node"], "rear")

    def test_size_rotation(self):
        raw = tb.RawCapture(self.dir, max_mb=0.002)          # 2000 bytes per file
        line = make_samples(0, 0, 10, 4)
        text = raw_line("rear", 1, 0, 0, line).encode()       # about 370 bytes
        for _ in range(30):
            self.assertEqual(raw.handle(text, 1.0), "raw")
        raw.close()
        files = self.files()
        self.assertGreater(len(files), 4)
        self.assertEqual(len(set(files)), len(files))
        sizes = [os.path.getsize(p) for p in files]
        self.assertTrue(all(s <= 2000 for s in sizes), sizes)
        self.assertEqual(sum(sizes), raw.stats()["bytes_written"])
        self.assertEqual(raw.stats()["files"], len(files))

    def test_time_rotation(self):
        raw = tb.RawCapture(self.dir, rotate_s=0.0)
        raw.handle(RAWS1.encode(), 1.0)
        time.sleep(1.1)                                   # new name needs a new second
        raw.handle(RAWS2.encode(), 2.0)
        raw.close()
        self.assertEqual(len(self.files()), 2)

    def test_free_space_guard(self):
        raw = tb.RawCapture(self.dir, retry_s=0.0)
        raw.disk_free = lambda d: 10 * 10**6               # 10 MB free, limit 1000 MB
        for _ in range(5):
            raw.handle(RAWS1.encode(), 1.0)
        st = raw.stats()
        self.assertEqual((st["lines"], st["not_written"], st["bytes_written"], st["file"]), (5, 5, 0, None))
        self.assertIn("disk free", st["paused"])
        self.assertEqual(self.files(), [])
        raw.disk_free = lambda d: 10**12                   # space again: resumes
        raw.handle(RAWS2.encode(), 2.0)
        raw.close()
        st = raw.stats()
        self.assertIsNone(st["paused"])
        self.assertEqual(st["not_written"], 5)
        self.assertEqual(len(self.files()), 1)
        # and drops out again when the disk fills while a file is open
        raw = tb.RawCapture(self.dir, retry_s=0.0)
        raw.handle(RAWS1.encode(), 1.0)
        raw.disk_free = lambda d: 0
        raw.handle(RAWS2.encode(), 1.0)
        raw.close()
        self.assertEqual(raw.stats()["not_written"], 1)

    def test_unwritable_dir_is_not_fatal(self):
        blocker = os.path.join(self.dir, "afile")
        open(blocker, "w").close()
        raw = tb.RawCapture(os.path.join(blocker, "sub"))   # cannot create a directory under a file
        self.assertEqual(raw.handle(RAWS1.encode(), 1.0), "raws")
        st = raw.stats()
        self.assertEqual((st["lines"], st["not_written"]), (1, 1))
        self.assertIn("cannot create", st["paused"])

    def test_disabled_counts_but_writes_nothing(self):
        d = os.path.join(self.dir, "never")
        raw = tb.RawCapture(d, enabled=False)
        data, exp = build_stream()
        state = run_reader(data, raw, 1)
        r = state.snapshot()["bridge"]["raw"]
        self.assertFalse(os.path.exists(d))
        self.assertEqual((r["capture"], r["dir"], r["file"], r["bytes_written"]), (False, None, None, 0))
        self.assertEqual((r["raw"], r["bad_crc"]), (exp["raw"], exp["bad_crc"]))

    def test_keep_mb_prunes_oldest(self):
        for i in range(5):
            with open(os.path.join(self.dir, "rear_raw_2026-10-0%d_120000.txt" % (i + 1)), "wb") as f:
                f.write(b"x" * 1000)
        with open(os.path.join(self.dir, "other.txt"), "wb") as f:
            f.write(b"y" * 5000)                               # not a capture file: never touched
        raw = tb.RawCapture(self.dir, keep_mb=0.0025)
        raw.handle(RAWS1.encode(), 1.0)
        raw.close()
        names = sorted(os.listdir(self.dir))
        self.assertIn("other.txt", names)
        self.assertNotIn("rear_raw_2026-10-01_120000.txt", names)
        self.assertNotIn("rear_raw_2026-10-03_120000.txt", names)
        self.assertIn("rear_raw_2026-10-04_120000.txt", names)

    def test_flush_every_second(self):
        raw = tb.RawCapture(self.dir, flush_s=0.2)
        raw.handle(RAWS1.encode(), 1.0)
        path = os.path.join(self.dir, raw.stats()["file"])
        deadline = time.monotonic() + 2
        while os.path.getsize(path) == 0 and time.monotonic() < deadline:
            raw.tick()
            time.sleep(0.05)
        self.assertGreater(os.path.getsize(path), 0)
        raw.close()

    def test_cpu_cost_at_link_rate(self):
        """60 s of the rear stream (about 15 kB/s) through the reader loop
        and capture; prints the time, fails only if grossly slow."""
        lines = []
        seq = 0
        for k in range(60 * 20):
            for imu in (1, 2):
                s = make_samples(seq, k * 50000, 10, k * 2 + imu)
                lines.append(raw_line("rear", imu, s[0][0], s[0][1], s))
            seq += 10
            if k % 10 == 0:
                lines.append(RAWS1)
            if k % 20 == 0:
                lines.append(DASH1)
        data = ("\n".join(lines) + "\n").encode()
        parts = [data[i:i + 300] for i in range(0, len(data), 300)]   # 300-byte reads, as at 20 ms
        raw = tb.RawCapture(self.dir)
        state = tb.TelemetryState("fake", raw=raw)
        done = threading.Event()
        real_open, real_idle = tb.open_serial, tb.READ_IDLE_S
        tb.open_serial, tb.READ_IDLE_S = (lambda p, b: ScriptedPort(parts, done)), 0.0
        stop = threading.Event()
        src = tb.LineSource(state, stop, port="/dev/fake")
        c0 = time.process_time()
        try:
            src.start()
            self.assertTrue(done.wait(60))
        finally:
            stop.set()
            src.join(3)
            tb.open_serial, tb.READ_IDLE_S = real_open, real_idle
        cpu = time.process_time() - c0
        r = state.snapshot()["bridge"]["raw"]
        self.assertEqual(r["raw"], 60 * 20 * 2)
        self.assertEqual(r["bad_crc"], 0)
        print("\n  %.0f kB (60 s of stream) in %.2f s CPU on this machine (%.1f %% of one core)"
              % (len(data) / 1e3, cpu, cpu / 60 * 100))
        self.assertLess(cpu, 6.0)


class PySerialLoopbackTests(unittest.TestCase):
    """The real pyserial read path (in_waiting, read) on pyserial's loop:// port,
    fed in real time at about 15 kB/s."""

    def test_loopback_real_time(self):
        try:
            import serial
        except ImportError:
            self.skipTest("pyserial not installed")
        data, exp = build_stream()
        lines = []
        for k in range(40):                       # 2 s of two-IMU traffic
            for imu in (1, 2):
                s = make_samples(k * 10, k * 50000, 10, 100 + k * 2 + imu)
                lines.append(raw_line("rear", imu, s[0][0], s[0][1], s))
        data += ("\n".join(lines) + "\n").encode()
        port = serial.serial_for_url("loop://", timeout=0.5)

        class LoopPort(tb._PySerialPort):
            def __init__(self, s):
                self._serial_mod = serial
                self._s = s

        d = tempfile.mkdtemp(prefix="sw7raw_")
        raw = tb.RawCapture(d)
        state = tb.TelemetryState("loop", raw=raw)
        real_open = tb.open_serial
        tb.open_serial = lambda p, b: LoopPort(port)
        stop = threading.Event()
        src = tb.LineSource(state, stop, port="loop://")
        try:
            src.start()
            for i in range(0, len(data), 300):     # 300 bytes every 20 ms = 15 kB/s
                port.write(data[i:i + 300])
                time.sleep(0.02)
            deadline = time.monotonic() + 3
            while state.snapshot()["bridge"]["raw"]["raw"] < exp["raw"] + 80 and time.monotonic() < deadline:
                time.sleep(0.05)
        finally:
            stop.set()
            src.join(3)
            tb.open_serial = real_open
        r = state.snapshot()["bridge"]["raw"]
        b = state.snapshot()["bridge"]
        try:
            # The first line ('5,"x":1}') is the fragment skipped on open.
            self.assertEqual((r["raw"], r["bad_crc"], r["rawh"], r["raws"]), (exp["raw"] + 80, 2, 2, 2))
            self.assertEqual((b["lines"], b["bad_lines"]), (2, 0))
            if DEC is not None:
                res = DEC.decode_file(os.path.join(d, r["file"]))
                self.assertEqual(res["counts"]["raw"], exp["raw"] + 80)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class BridgeEndpointTests(unittest.TestCase):
    def test_telemetry_and_status_page(self):
        d = tempfile.mkdtemp(prefix="sw7raw_")
        br = tb.Bridge(serial_port="COM239" if os.name == "nt" else "/dev/ttyACM_missing", host="127.0.0.1",
                       port=0, tof=False, beacon=False, raw_dir=d).start()
        try:
            br.raw.handle(RAWS1.encode(), 1.0)
            br.raw.handle(b"RAW 2 rear 1 0 0 1 " + b"0" * 32 + b" 0000", 1.0)
            with urllib.request.urlopen("http://127.0.0.1:%d/telemetry" % br.port, timeout=3) as resp:
                r = json.loads(resp.read())["bridge"]["raw"]
            self.assertEqual((r["lines"], r["raws"], r["bad_crc"], r["capture"], r["dir"]), (2, 1, 1, True, d))
            self.assertTrue(r["file"].startswith("rear_raw_"))
            with urllib.request.urlopen("http://127.0.0.1:%d/" % br.port, timeout=3) as resp:
                page = resp.read().decode()
            self.assertIn("raw: 2 lines (RAW 0, RAWH 0, RAWS 1), 1 bad CRC", page)
        finally:
            br.close()
            shutil.rmtree(d, ignore_errors=True)

    def test_no_raw_capture_flag(self):
        sys.path.insert(0, HERE)
        from test_telemetry_bridge import BridgeProcess, get_json, MISSING_PORT
        b = BridgeProcess("--serial-port", MISSING_PORT, "--no-tof", "--no-beacon", "--no-raw-capture",
                          "--raw-dir", os.path.join(tempfile.gettempdir(), "sw7_never"))
        try:
            r = get_json(b.port)["bridge"]["raw"]
            self.assertEqual((r["capture"], r["dir"], r["lines"]), (False, None, 0))
        finally:
            b.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
