"""Offline tests of BenchTest/raw_capture.py (front IMU node capture on the Pi 5):
a scripted serial port with DASH, RAW lines, noise, an unplug and a
re-enumeration; checks the capture file, the counts and the HTTP reply.

Run: python BenchTest/tests/test_raw_capture.py (or with pytest)."""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
sys.path.insert(0, BENCH)
import raw_capture as rc  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(BENCH), "CameraDetection", "tests"))
from test_bridge_raw import DEC, RAWH1, RAWS1, build_stream, chunks  # noqa: E402

DASH_F = 'DASH {"seq":7,"up_ms":7000,"fw":"0.7.5","node":"front","imu_hz":[200.0],"rdfail":[0],"stuck":[0],"rawdrop":[0]}'


class Port:
    def __init__(self, parts, on_empty):
        self.parts = list(parts)
        self.on_empty = on_empty

    def read(self):
        if not self.parts:
            return self.on_empty()
        c = self.parts.pop(0)
        if isinstance(c, Exception):
            raise c
        return c

    def close(self):
        pass


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="sw7front_")
        self.real = (rc.open_serial, rc.find_port, rc.SERIAL_RETRY_S, rc.READ_IDLE_S)

    def tearDown(self):
        rc.open_serial, rc.find_port, rc.SERIAL_RETRY_S, rc.READ_IDLE_S = self.real
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_stream_unplug_and_http(self):
        data, exp = build_stream()
        stream2 = (DASH_F + "\n" + RAWS1 + "\n").encode()
        done = threading.Event()
        seen = {}
        script = [
            ("/dev/ttyACM0", chunks(data, 3) + [OSError("device reports readiness to read but returned no data")]),
            OSError("no ESP32 serial device found"),
            ("/dev/ttyACM1", chunks(stream2, 4)),
        ]
        state = rc.FrontState("auto", rc.CaptureFile(self.dir))

        def find(spec):
            item = script[0] if script else None
            if isinstance(item, Exception):
                script.pop(0)
                seen["missing"] = state.snapshot()
                raise item
            return item[0] if item else "/dev/ttyACM1"

        def opener(port, baud):
            if not script:
                return Port([], lambda: (done.set(), time.sleep(0.01), b"")[2])
            _, parts = script.pop(0)
            return Port(parts, lambda: (done.set(), time.sleep(0.01), b"")[2])

        rc.find_port, rc.open_serial, rc.SERIAL_RETRY_S, rc.READ_IDLE_S = find, opener, 0.05, 0.0
        stop = threading.Event()
        httpd = rc.start_http(state, "127.0.0.1", 0)
        reader = rc.Reader(state, stop, "auto")
        try:
            reader.start()
            self.assertTrue(done.wait(10))
            time.sleep(0.05)
            with urllib.request.urlopen("http://127.0.0.1:%d/telemetry" % httpd.server_address[1], timeout=3) as r:
                snap = json.loads(r.read())
            with urllib.request.urlopen("http://127.0.0.1:%d/" % httpd.server_address[1], timeout=3) as r:
                page = r.read().decode()
        finally:
            stop.set()
            reader.join(3)
            httpd.shutdown()
            httpd.server_close()
        self.assertIsNone(seen["missing"]["esp32"])            # null while unplugged
        self.assertFalse(seen["missing"]["bridge"]["connected"])
        e, b = snap["esp32"], snap["bridge"]
        self.assertEqual((e["node"], e["seq"]), ("front", 7))
        self.assertIn("age_ms", e)
        self.assertIsNone(snap["tof"])
        self.assertEqual((b["serial_port"], b["connected"], b["lines"], b["bad_lines"]), ("/dev/ttyACM1", True, 3, 0))
        r = b["raw"]
        self.assertEqual((r["raw"], r["rawh"], r["raws"], r["bad_crc"]), (exp["raw"], exp["rawh"], exp["raws"] + 1, 2))
        self.assertEqual(b["other_lines"], 2)          # boot line and the [imu] print; the opening fragment is not counted
        self.assertIn("front node: seq 7", page)
        self.assertEqual(reader.opens, 2)
        # Every line, fragment and noise included, is in the file behind a host time.
        files = sorted(os.listdir(self.dir))
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].startswith("front_raw_"))
        path = os.path.join(self.dir, files[0])
        with open(path, "rb") as f:
            got = [ln.split(b" ", 1)[1].decode() for ln in f.read().splitlines()]
        want = data.decode().replace("\r", "").splitlines() + stream2.decode().splitlines()
        self.assertEqual(got, want)
        self.assertEqual(r["bytes_written"], os.path.getsize(path))
        if DEC is not None:
            res = DEC.decode_file(path)
            for key, samples in exp["samples"].items():
                self.assertEqual(len(res["samples"][key]), len(samples))
            self.assertEqual(len(res["sync"]), 3)

    def test_free_space_and_disabled(self):
        cap = rc.CaptureFile(self.dir, retry_s=0.0)
        cap.disk_free = lambda d: 0
        cap.write_line(RAWH1.encode(), 1.0)
        self.assertEqual((cap.not_written, cap.bytes_written), (1, 0))
        self.assertIn("disk free", cap.paused)
        cap.disk_free = lambda d: 10**12
        cap.write_line(RAWH1.encode(), 1.0)
        cap.close()
        self.assertIsNone(cap.paused)
        self.assertEqual(len(os.listdir(self.dir)), 1)
        off = rc.CaptureFile(os.path.join(self.dir, "never"), enabled=False)
        off.write_line(RAWH1.encode(), 1.0)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "never")))

    def test_size_rotation(self):
        cap = rc.CaptureFile(self.dir, max_mb=0.001)
        for _ in range(20):
            cap.write_line(RAWH1.encode(), 1.0)
        cap.close()
        self.assertGreater(len(os.listdir(self.dir)), 1)

    def test_find_port(self):
        self.assertEqual(rc.find_port("/dev/ttyACM3"), "/dev/ttyACM3")
        if os.name == "nt":
            with self.assertRaises(OSError):
                rc.find_port("auto")

    def test_main_runs_without_port(self):
        import signal
        old = signal.getsignal(signal.SIGTERM)
        try:
            t0 = time.monotonic()
            self.assertEqual(rc.main(["--port", "COM239" if os.name == "nt" else "/dev/ttyNONE",
                                      "--out", self.dir, "--http-port", "0", "--duration", "1"]), 0)
            self.assertLess(time.monotonic() - t0, 6)
        finally:
            signal.signal(signal.SIGTERM, old)
        self.assertEqual(os.listdir(self.dir), [])      # no raw line, no file


if __name__ == "__main__":
    unittest.main(verbosity=2)
