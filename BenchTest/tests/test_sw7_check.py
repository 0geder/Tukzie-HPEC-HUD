"""Offline tests of BenchTest/sw7_check.py: a local fake HTTP server stands in
for the Pi 4 bridge (/telemetry) and detector (/alerts), a local UDP packet
for the beacon, and stubbed command output for the ssh checks. No Pi, no
CameraDetection code.

Run: python BenchTest/tests/test_sw7_check.py (or with pytest)."""
import contextlib
import copy
import io
import json
import os
import socket
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import sw7_check as chk  # noqa: E402

SCRIPT = os.path.join(ROOT, "sw7_check.py")

GOOD = {
    "esp32": {"seq": 5, "up_ms": 5000, "fw": "0.7.0", "soc": 60, "v": 74.8, "i": 0.0, "bms_age_s": 0.4,
              "fix": False, "lat": None, "lon": None, "spd_raw": None, "vib": 0.12, "vib_dis": 0.03,
              "imu_hz": [200.1, 199.8], "drops": [3, 1], "rpm": None, "csq": 18, "mqtt": True, "age_ms": 420},
    "tof": {"left_mm": 812, "ahead_mm": 1490, "right_mm": 650, "age_ms": 35},
    "bridge": {"version": "1.0", "serial_port": "/dev/ttyACM0", "lines": 10, "bad_lines": 0},
}
ALERTS = {"active": [], "fps": 7.2, "latency_ms": 140}


class FakePi4:
    """/telemetry and /alerts on one free localhost port. telemetry may be
    a dict or a function of the request number."""

    def __init__(self, telemetry=None, alerts=None, serve_alerts=True):
        self.telemetry = GOOD if telemetry is None else telemetry
        self.alerts = ALERTS if alerts is None else alerts
        self.requests = 0
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if self.path == "/telemetry":
                    t = fake.telemetry
                    body = t(fake.requests) if callable(t) else t
                    fake.requests += 1
                elif self.path == "/alerts" and serve_alerts:
                    body = fake.alerts
                else:
                    self.send_error(404)
                    return
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def variant(**esp32):
    d = copy.deepcopy(GOOD)
    d["esp32"].update(esp32)
    return d


def run_check(fake, *extra, camera_port=None):
    args = chk.parse_args(["--pi4", "127.0.0.1", "--telemetry-port", str(fake.port),
                           "--camera-port", str(camera_port or fake.port), "--no-ssh", "--pi5", "none",
                           "--drops-window", "0.3", "--json"] + list(extra))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = chk.run(args)
    result = json.loads(out.getvalue())
    return code, result, {i["name"]: i for i in result["checks"]}


class CheckTests(unittest.TestCase):
    def test_all_good(self):
        fake = FakePi4()
        try:
            code, res, items = run_check(fake)
        finally:
            fake.close()
        self.assertEqual(code, 0)
        self.assertTrue(res["ok"])
        self.assertEqual(res["pi4"], "127.0.0.1")
        for name in ("Pi 4 found", "telemetry /telemetry", "esp32 data fresh", "IMU rates",
                     "esp32 firmware", "ToF sensors", "camera /alerts", "IMU drops"):
            self.assertEqual(items[name]["status"], "PASS", items[name])
        self.assertIn("7.2 fps", items["camera /alerts"]["value"])
        self.assertIn("0.7.0", items["esp32 firmware"]["value"])
        self.assertIn("age 420 ms", items["esp32 data fresh"]["value"])
        self.assertTrue(items["IMU rates"]["critical"])
        self.assertFalse(items["ToF sensors"]["critical"])
        self.assertEqual(items["Pi 4 ssh"]["status"], "WARN")

    def test_stale_esp32_fails(self):
        fake = FakePi4(variant(age_ms=3500))
        try:
            code, _, items = run_check(fake)
        finally:
            fake.close()
        self.assertEqual(code, 1)
        self.assertEqual(items["esp32 data fresh"]["status"], "FAIL")

    def test_esp32_null_fails(self):
        d = copy.deepcopy(GOOD)
        d["esp32"] = None
        fake = FakePi4(d)
        try:
            code, _, items = run_check(fake)
        finally:
            fake.close()
        self.assertEqual(code, 1)
        self.assertEqual(items["esp32 data fresh"]["status"], "FAIL")
        self.assertEqual(items["IMU rates"]["status"], "FAIL")

    def test_low_imu_rate_fails(self):
        fake = FakePi4(variant(imu_hz=[200.0, 180.5]))
        try:
            code, _, items = run_check(fake)
        finally:
            fake.close()
        self.assertEqual(code, 1)
        self.assertEqual(items["IMU rates"]["status"], "FAIL")
        self.assertIn("180.5", items["IMU rates"]["value"])

    def test_camera_down_fails(self):
        fake = FakePi4(serve_alerts=False)
        try:
            code, _, items = run_check(fake, camera_port=free_port())
        finally:
            fake.close()
        self.assertEqual(code, 1)
        self.assertEqual(items["camera /alerts"]["status"], "FAIL")

    def test_tof_null_and_drops_rising_only_warn(self):
        def telemetry(n):
            d = copy.deepcopy(GOOD)
            d["tof"]["right_mm"] = None
            d["esp32"]["drops"] = [3 + 2 * n, 1]
            return d
        fake = FakePi4(telemetry)
        try:
            code, _, items = run_check(fake)
        finally:
            fake.close()
        self.assertEqual(code, 0)
        self.assertEqual(items["ToF sensors"]["status"], "WARN")
        self.assertIn("right null", items["ToF sensors"]["value"])
        self.assertEqual(items["IMU drops"]["status"], "WARN")
        self.assertIn("+2 / +0", items["IMU drops"]["value"])

    def test_pi4_not_found(self):
        args = chk.parse_args(["--pi4", "127.0.0.1", "--telemetry-port", str(free_port()),
                               "--no-ssh", "--pi5", "none", "--json"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = chk.run(args)
        res = json.loads(out.getvalue())
        self.assertEqual(code, 1)
        self.assertIsNone(res["pi4"])
        self.assertEqual(res["checks"][0]["status"], "FAIL")


class DiscoveryTests(unittest.TestCase):
    def test_finds_local_first(self):
        fake = FakePi4()
        try:
            args = chk.parse_args(["--telemetry-port", str(fake.port)])
            host, how, _, _, tried = chk.discover_pi4(args, beacon=lambda *a: self.fail("beacon not needed"))
        finally:
            fake.close()
        self.assertEqual(host, "127.0.0.1")
        self.assertIn("local", how)
        self.assertEqual(tried, ["127.0.0.1"])

    def test_order_when_nothing_answers(self):
        args = chk.parse_args(["--candidates", "192.168.137.82", "10.74.67.244"])
        probed = []

        def probe(host, port):
            probed.append(host)
            return False
        host, how, _, _, tried = chk.discover_pi4(args, probe=probe, beacon=lambda p, w: (None, "no beacon"))
        self.assertIsNone(host)
        self.assertEqual(probed, ["127.0.0.1", "10.20.0.1", "pi4-camera.local", "192.168.137.82", "10.74.67.244"])
        self.assertIn("beacon: no beacon", tried)

    def test_beacon_source_and_ports_used(self):
        fake = FakePi4()
        bport = free_port()
        stop = threading.Event()

        def send():
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            noise = b'{"sw7": "other"}'
            good = json.dumps({"sw7": "pi4", "v": 1, "host": "pi4-camera", "camera_port": 8080,
                               "telemetry_port": fake.port, "seq": 1}).encode()
            while not stop.is_set():
                for pkt in (b"junk", noise, good):
                    s.sendto(pkt, ("127.0.0.1", bport))
                stop.wait(0.1)
            s.close()
        threading.Thread(target=send, daemon=True).start()
        calls = []

        def probe(host, port):
            calls.append((host, port))
            if len(calls) <= 2:          # 127.0.0.1 and 10.20.0.1 do not answer
                return False
            return chk.probe_telemetry(host, port)
        try:
            # The default telemetry port is wrong on purpose: the beacon's port must be used.
            args = chk.parse_args(["--beacon-port", str(bport), "--beacon-wait", "3"])
            host, how, tp, cp, _ = chk.discover_pi4(args, probe=probe)
        finally:
            stop.set()
            fake.close()
        self.assertEqual(host, "127.0.0.1")
        self.assertIn("beacon", how)
        self.assertIn("pi4-camera", how)
        self.assertEqual(tp, fake.port)
        self.assertEqual(cp, 8080)
        self.assertEqual(calls[2], ("127.0.0.1", fake.port))

    def test_beacon_timeout(self):
        t0 = time.monotonic()
        src, info = chk.listen_beacon(free_port(), 0.3)
        self.assertIsNone(src)
        self.assertIn("no beacon", info)
        self.assertLess(time.monotonic() - t0, 2)


class SshParsingTests(unittest.TestCase):
    def run_with(self, fn, output, ok=True, **argv):
        real = chk.run_remote
        chk.run_remote = lambda *a, **k: (ok, output)
        rep = chk.Report(quiet=True)
        try:
            fn(rep, *argv.get("pos", ()))
        finally:
            chk.run_remote = real
        return {i["name"]: i for i in rep.items}

    def test_pi4_services_and_power(self):
        args = chk.parse_args([])
        out = "bridge=active\ndetector=inactive\ndetector_pids=1234 \nthrottled=0x50000\ntemp=61.3\n"
        items = self.run_with(chk.check_pi4_ssh, out, pos=("10.20.0.1", args))
        self.assertEqual(items["telemetry-bridge service"]["status"], "PASS")
        self.assertEqual(items["hazard-detector service"]["status"], "WARN")
        self.assertIn("by hand", items["hazard-detector service"]["value"])
        self.assertEqual(items["Pi 4 power (throttled)"]["status"], "WARN")
        self.assertIn("under-voltage since boot", items["Pi 4 power (throttled)"]["value"])
        self.assertEqual(items["Pi 4 temperature"]["status"], "PASS")

    def test_pi4_ssh_fails_is_warn(self):
        args = chk.parse_args([])
        items = self.run_with(chk.check_pi4_ssh, "Permission denied (publickey).", ok=False,
                              pos=("10.20.0.1", args))
        self.assertEqual(list(items), ["Pi 4 ssh"])
        self.assertEqual(items["Pi 4 ssh"]["status"], "WARN")

    def test_pi5_dashboard(self):
        args = chk.parse_args(["--pi5", "Pirate5.local"])
        out = "host=Pirate5\npid=4321\nlive_only=1\ncommit=0123456789abcdef0123456789abcdef01234567\n"
        items = self.run_with(chk.check_pi5, out, pos=(args,))
        self.assertEqual(items["Pi 5 reachable"]["status"], "PASS")
        self.assertEqual(items["SW-7 dashboard running"]["status"], "PASS")
        self.assertIn("0123456789", items["SW-7 dashboard running"]["value"])
        self.assertEqual(items["TUKZIE_LIVE_ONLY"]["status"], "PASS")
        items = self.run_with(chk.check_pi5, "host=Pirate5\npid=4321\nlive_only=<unset>\n", pos=(args,))
        self.assertEqual(items["TUKZIE_LIVE_ONLY"]["status"], "WARN")
        items = self.run_with(chk.check_pi5, "host=Pirate5\n", pos=(args,))
        self.assertEqual(items["SW-7 dashboard running"]["status"], "FAIL")
        self.assertFalse(items["SW-7 dashboard running"]["critical"])

    def test_decode_throttled(self):
        self.assertEqual(chk.decode_throttled("0x0")[0], "PASS")
        st, desc = chk.decode_throttled("0x50005")
        self.assertEqual(st, "FAIL")
        self.assertIn("under-voltage now", desc)
        self.assertIn("throttled since boot", desc)
        self.assertEqual(chk.decode_throttled("")[0], "WARN")
        self.assertEqual(chk.decode_throttled(None)[0], "WARN")


class ProcessTests(unittest.TestCase):
    def test_command_line(self):
        fake = FakePi4()
        try:
            base = [sys.executable, SCRIPT, "--pi4", "127.0.0.1", "--telemetry-port", str(fake.port),
                    "--camera-port", str(fake.port), "--no-ssh", "--drops-window", "0.2"]
            p = subprocess.run(base, capture_output=True, text=True, timeout=30)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn("PASS  camera /alerts", p.stdout)
            self.assertIn("RESULT: READY", p.stdout)
            p = subprocess.run(base + ["--json"], capture_output=True, text=True, timeout=30)
            self.assertEqual(p.returncode, 0)
            self.assertTrue(json.loads(p.stdout)["ok"])
        finally:
            fake.close()
        p = subprocess.run(base, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 1)
        self.assertIn("NOT READY", p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
