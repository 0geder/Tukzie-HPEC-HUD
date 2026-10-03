"""Offline tests of CameraDetection/telemetry_bridge.py: no ESP32, no ToF
sensors. Runs the bridge as a real process in --replay and --fake-tof mode
on a free port and checks /telemetry against DashboardIntegration/
TELEMETRY_LINK.md section 2.

Run from anywhere: python CameraDetection/tests/test_telemetry_bridge.py
(or with pytest)."""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import telemetry_bridge as tb  # noqa: E402

BRIDGE = os.path.join(ROOT, "telemetry_bridge.py")
SAMPLE = os.path.join(HERE, "dash_sample.txt")
MISSING_PORT = "/dev/ttyACM_missing" if os.name != "nt" else "COM239"

CONTRACT_KEYS = {"seq", "up_ms", "fw", "soc", "v", "i", "bms_age_s", "fix", "lat", "lon", "spd_raw",
                 "vib", "vib_dis", "imu_hz", "drops", "rpm", "csq", "mqtt"}

GOOD = 'DASH {"seq":1,"up_ms":1000,"fw":"0.7.0","soc":60,"v":74.8,"i":0.0,"bms_age_s":0.4,' \
       '"fix":false,"lat":null,"lon":null,"spd_raw":null,"vib":0.12,"vib_dis":0.03,' \
       '"imu_hz":[200.1,200.2],"drops":[0,0],"rpm":null,"csq":18,"mqtt":true}'
MALFORMED = 'DASH {"seq":2,"up_ms":2000,"soc":60,"v":74.'
WITH_NAN = 'DASH {"seq":3,"up_ms":3000,"soc":60,"v":nan,"i":0.0}'
WITH_JSON_NAN = 'DASH {"seq":4,"up_ms":4000,"soc":NaN,"v":74.8}'
NOT_OBJECT = 'DASH [1,2,3]'
NOT_DASH = '[imu] IMU2 rate 200.2 Hz'


def get(port, path):
    with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=3) as r:
        return r.status, r.headers.get("Content-Type"), r.read()


def get_json(port):
    status, ctype, body = get(port, "/telemetry")
    assert status == 200 and ctype == "application/json", (status, ctype)
    return json.loads(body)


class BridgeProcess:
    """Starts telemetry_bridge.py with --port 0 and reads back the port it bound."""

    def __init__(self, *args):
        env = dict(os.environ, PYTHONUNBUFFERED="1")
        self.p = subprocess.Popen([sys.executable, BRIDGE, "--host", "127.0.0.1", "--port", "0"] + list(args),
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        self.output = []
        self.port = None
        found = threading.Event()

        def pump():
            for line in self.p.stdout:
                self.output.append(line)
                m = re.search(r"http://[^:]+:(\d+)/telemetry", line)
                if m and self.port is None:
                    self.port = int(m.group(1))
                    found.set()
        threading.Thread(target=pump, daemon=True).start()
        if not found.wait(10):
            self.p.kill()
            raise AssertionError("bridge did not start: %s" % "".join(self.output))

    def wait_exit(self, timeout=10):
        return self.p.wait(timeout)

    def close(self):
        if self.p.poll() is None:
            self.p.kill()
        self.p.wait(5)
        self.p.stdout.close()


class ParseTests(unittest.TestCase):
    def test_classification(self):
        self.assertEqual(tb.parse_dash_line(GOOD + "\r\n")[0], "ok")
        self.assertEqual(tb.parse_dash_line(GOOD)[1]["imu_hz"], [200.1, 200.2])
        for bad in (MALFORMED, WITH_NAN, WITH_JSON_NAN, NOT_OBJECT, "DASH ", 'DASH {"v":Infinity}'):
            self.assertEqual(tb.parse_dash_line(bad), ("bad", None), bad)
        for other in (NOT_DASH, "", "DASH", "dash {}", " DASH {}"):
            self.assertEqual(tb.parse_dash_line(other), ("ignore", None), other)

    def test_counting(self):
        s = tb.TelemetryState("test")
        for line in (GOOD, MALFORMED, WITH_NAN, NOT_DASH, WITH_JSON_NAN, NOT_OBJECT):
            s.handle_line(line)
        snap = s.snapshot()
        self.assertEqual(snap["bridge"]["lines"], 5)      # DASH lines only
        self.assertEqual(snap["bridge"]["bad_lines"], 4)
        self.assertEqual(snap["esp32"]["seq"], 1)         # bad lines never replace the good one
        s.clear_esp32()
        self.assertIsNone(s.snapshot()["esp32"])

    def test_clean_mm(self):
        import tof_reader
        for raw, want in ((812, 812), (812.6, 812), (8190, None), (8000, None), (0, None),
                          (-5, None), (None, None), ("x", None), (float("nan"), None)):
            self.assertEqual(tof_reader.clean_mm(raw), want, raw)


class ReplayFakeTofTests(unittest.TestCase):
    """Replay of the sample file plus fake ToF, as a separate process."""

    @classmethod
    def setUpClass(cls):
        cls.b = BridgeProcess("--replay", SAMPLE, "--replay-interval", "0.05", "--fake-tof", "--duration", "9")

    @classmethod
    def tearDownClass(cls):
        cls.b.close()

    def test_shape_and_values(self):
        deadline = time.monotonic() + 3
        d = get_json(self.b.port)
        while d["esp32"] is None and time.monotonic() < deadline:
            time.sleep(0.05)
            d = get_json(self.b.port)
        self.assertEqual(set(d), {"esp32", "tof", "bridge"})

        e = d["esp32"]
        self.assertIsNotNone(e)
        self.assertEqual(set(e), CONTRACT_KEYS | {"age_ms"})
        self.assertIsInstance(e["age_ms"], int)
        self.assertTrue(0 <= e["age_ms"] < 1000, e["age_ms"])
        self.assertEqual(e["fw"], "0.7.0")
        self.assertIn(e["soc"], (59, 60))
        self.assertEqual(len(e["imu_hz"]), 2)
        self.assertIsNone(e["rpm"])
        if not e["fix"]:
            self.assertIsNone(e["lat"])

        t = d["tof"]
        self.assertEqual(set(t), {"left_mm", "ahead_mm", "right_mm", "age_ms"})
        self.assertIsInstance(t["age_ms"], int)
        self.assertTrue(0 <= t["age_ms"] < 1000, t["age_ms"])
        for k in ("left_mm", "ahead_mm"):
            self.assertIsInstance(t[k], int)
            self.assertTrue(0 < t[k] < 8000)

        bb = d["bridge"]
        self.assertEqual(set(bb), {"version", "serial_port", "lines", "bad_lines"})
        self.assertEqual(bb["version"], "1.0")
        self.assertEqual(bb["bad_lines"], 0)          # the sample file is all good or non-DASH
        self.assertGreater(bb["lines"], 0)

    def test_tof_right_goes_null(self):
        # The fake right sensor reports 8190 (nothing in range) from about
        # 1 s to 5 s after start; that must come out as null, and numbers otherwise.
        seen = set()
        deadline = time.monotonic() + 7
        while time.monotonic() < deadline and len(seen) < 2:
            seen.add(get_json(self.b.port)["tof"]["right_mm"] is None)
            time.sleep(0.1)
        self.assertEqual(seen, {True, False})

    def test_status_page_and_404(self):
        status, ctype, body = get(self.b.port, "/")
        self.assertEqual(status, 200)
        self.assertTrue(ctype.startswith("text/plain"))
        self.assertIn(b"telemetry bridge", body)
        status, _, _ = get(self.b.port, "/telemetry?x=1")
        self.assertEqual(status, 200)
        with self.assertRaises(urllib.error.HTTPError) as cm:
            get(self.b.port, "/nope")
        self.assertEqual(cm.exception.code, 404)

    def test_zz_exits_cleanly(self):
        # --duration 9 ends the run through the same shutdown path as Ctrl+C.
        self.assertEqual(self.b.wait_exit(15), 0)
        self.assertIn("Stopped.", "".join(self.b.output))


class BadLineTests(unittest.TestCase):
    def test_bad_lines_counted(self):
        fd, path = tempfile.mkstemp(suffix=".txt", text=True)
        with os.fdopen(fd, "w") as f:
            f.write("\n".join([GOOD, MALFORMED, WITH_NAN, NOT_DASH, WITH_JSON_NAN, NOT_OBJECT]) + "\n")
        b = BridgeProcess("--replay", path, "--replay-interval", "0.02", "--no-tof")
        try:
            time.sleep(1.0)
            d = get_json(b.port)
            lines, bad = d["bridge"]["lines"], d["bridge"]["bad_lines"]
            self.assertGreaterEqual(lines, 10)
            # 5 DASH lines per pass of the file, 4 of them bad (allow for a partial pass)
            good = lines - bad
            passes = lines / 5.0
            self.assertTrue(abs(good - passes) <= 1.0, (lines, bad))
            self.assertEqual(d["esp32"]["seq"], 1)
            self.assertNotIn("nan", json.dumps(d).lower())
            self.assertIsNone(d["tof"])
            self.assertEqual(d["bridge"]["serial_port"], "replay:%s" % path)
        finally:
            b.close()
            os.remove(path)


class NoSerialPortTests(unittest.TestCase):
    def test_keeps_serving_without_port_or_sensors(self):
        # No --no-tof: the real ToF path runs and finds no sensor libraries
        # or hardware on this laptop, so tof must stay null without a crash.
        b = BridgeProcess("--serial-port", MISSING_PORT)
        try:
            time.sleep(1.5)
            for _ in range(3):
                d = get_json(b.port)
                self.assertIsNone(d["esp32"])
                self.assertIsNone(d["tof"])
                self.assertEqual(d["bridge"], {"version": "1.0", "serial_port": MISSING_PORT,
                                               "lines": 0, "bad_lines": 0})
                time.sleep(0.3)
            self.assertIsNone(b.p.poll())   # still running
            out = "".join(b.output)
            self.assertIn("not available", out)
        finally:
            b.close()


class FakeSerialTests(unittest.TestCase):
    """The serial loop with a scripted device: split chunks, a fragment
    on open, an unplug, the port missing for a while, then back again."""

    def test_reassembly_and_reconnect(self):
        script = [
            # first connection: starts mid-line, then lines split across reads
            [b'"x":1}\nDA', b'SH {"seq":10,"soc":60}\r\n[log] hi\n', b'DASH {"seq":11', b',"soc":60}\n', OSError("unplugged")],
            OSError("No such file"),           # port missing on the next attempt
            [b'DASH {"seq":12,"soc":61}\n'],   # re-enumerated
        ]
        opened = []
        state = tb.TelemetryState("fake")
        snaps = {}

        class Dev:
            def __init__(self, chunks):
                self.chunks = list(chunks)

            def read(self):
                if not self.chunks:
                    time.sleep(0.01)
                    return b""
                c = self.chunks.pop(0)
                if isinstance(c, Exception):
                    snaps["before_unplug"] = state.snapshot()
                    raise c
                return c

            def close(self):
                pass

        def fake_open(port, baud):
            item = script.pop(0) if script else []
            opened.append(port)
            if isinstance(item, Exception):
                snaps["while_missing"] = state.snapshot()
                raise item
            return Dev(item)

        real_open, real_retry = tb.open_serial, tb.SERIAL_RETRY_S
        tb.open_serial, tb.SERIAL_RETRY_S = fake_open, 0.05
        stop = threading.Event()
        try:
            src = tb.LineSource(state, stop, port="/dev/ttyACM0")
            src.start()
            deadline = time.monotonic() + 3
            snap = state.snapshot()
            while time.monotonic() < deadline:
                snap = state.snapshot()
                if snap["esp32"] is not None and snap["esp32"]["seq"] == 12:
                    break
                time.sleep(0.02)
        finally:
            stop.set()
            src.join(2)
            tb.open_serial, tb.SERIAL_RETRY_S = real_open, real_retry
        before = snaps["before_unplug"]
        self.assertEqual(before["esp32"]["seq"], 11)
        self.assertEqual(before["bridge"]["lines"], 2)    # the opening fragment is skipped
        self.assertIsNone(snaps["while_missing"]["esp32"])   # null while unplugged
        self.assertEqual(snap["esp32"]["seq"], 12)
        self.assertEqual(snap["esp32"]["soc"], 61)
        self.assertEqual(snap["bridge"]["lines"], 3)
        self.assertEqual(snap["bridge"]["bad_lines"], 0)
        self.assertGreaterEqual(len(opened), 3)


class InProcessCloseTests(unittest.TestCase):
    def test_close_is_quick(self):
        br = tb.Bridge(serial_port=MISSING_PORT, host="127.0.0.1", port=0, fake_tof=True).start()
        time.sleep(0.3)
        self.assertIsNotNone(get_json(br.port)["tof"])
        t0 = time.monotonic()
        br.close()
        self.assertLess(time.monotonic() - t0, 3.5)
        self.assertFalse(br.source.is_alive())
        self.assertFalse(br.tof.is_alive())


def beacon_receiver():
    """A UDP socket on a free localhost port, 3 s timeout."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    s.settimeout(3)
    return s, s.getsockname()[1]


IP_JSON_SAMPLE = json.dumps([
    {"ifname": "lo", "flags": ["LOOPBACK", "UP"],
     "addr_info": [{"family": "inet", "local": "127.0.0.1", "prefixlen": 8}]},
    {"ifname": "eth0", "flags": ["BROADCAST", "UP"],
     "addr_info": [{"family": "inet", "local": "10.20.0.1", "prefixlen": 24, "broadcast": "10.20.0.255"}]},
    {"ifname": "wlan0", "flags": ["BROADCAST", "UP"],
     "addr_info": [{"family": "inet", "local": "10.74.67.244", "prefixlen": 22}]},     # no broadcast key
    {"ifname": "tun0", "flags": ["POINTOPOINT", "UP"],
     "addr_info": [{"family": "inet", "local": "10.8.0.2", "prefixlen": 32}]},
    {"ifname": "odd"},
])


class BeaconTests(unittest.TestCase):
    """TELEMETRY_LINK.md 4.2: UDP discovery beacon on port 50808."""

    def check_payload(self, d, telemetry_port):
        self.assertEqual(set(d), {"sw7", "v", "host", "camera_port", "telemetry_port", "seq"})
        self.assertEqual(d["sw7"], "pi4")
        self.assertEqual(d["v"], 1)
        self.assertEqual(d["camera_port"], 8080)
        self.assertEqual(d["telemetry_port"], telemetry_port)
        self.assertIsInstance(d["host"], str)
        self.assertTrue(d["host"])
        self.assertIsInstance(d["seq"], int)

    def test_in_process_beacon_received(self):
        rx, port = beacon_receiver()
        stop = threading.Event()
        b = tb.Beacon(stop, telemetry_port=8081, port=port, interval_s=0.1, targets=["127.0.0.1"])
        b.start()
        try:
            got = []
            for _ in range(3):
                data, addr = rx.recvfrom(2048)
                got.append(json.loads(data))
                self.assertEqual(addr[0], "127.0.0.1")
        finally:
            stop.set()
            b.join(2)
            rx.close()
        for d in got:
            self.check_payload(d, 8081)
        self.assertEqual([d["seq"] for d in got], sorted(d["seq"] for d in got))
        self.assertLess(got[0]["seq"], got[-1]["seq"])
        self.assertFalse(b.is_alive())
        self.assertEqual(b.send_errors, 0)

    def test_send_failures_counted_not_fatal(self):
        # One target refuses (as an interface with no route would); the
        # other targets still get the packet and nothing is raised.
        class Sock:
            def __init__(self):
                self.sent = []

            def sendto(self, data, addr):
                if addr[0] == "10.99.99.255":
                    raise OSError(101, "Network is unreachable")
                self.sent.append((data, addr))

        b = tb.Beacon(threading.Event(), telemetry_port=8081, port=50808,
                      targets=["255.255.255.255", "10.99.99.255", "10.20.0.255"])
        s = Sock()
        b.send_once(s)
        b.send_once(s)
        self.assertEqual(b.sent, 4)
        self.assertEqual(b.send_errors, 2)
        self.assertIn("10.99.99.255", b.last_error)
        self.assertEqual([a for _, a in s.sent[:2]], [("255.255.255.255", 50808), ("10.20.0.255", 50808)])
        self.assertEqual(json.loads(s.sent[-1][0])["seq"], 1)

    def test_thread_survives_socket_errors(self):
        # Every send raising something unexpected must not end the thread.
        stop = threading.Event()
        b = tb.Beacon(stop, telemetry_port=8081, interval_s=0.05, targets=["127.0.0.1"])

        def boom(sock):
            raise RuntimeError("unexpected")
        b.send_once = boom
        b.start()
        try:
            time.sleep(0.4)
            self.assertTrue(b.is_alive())
            self.assertGreaterEqual(b.send_errors, 3)
        finally:
            stop.set()
            b.join(2)
        self.assertFalse(b.is_alive())

    def test_bridge_process_sends_beacon(self):
        rx, port = beacon_receiver()
        b = BridgeProcess("--serial-port", MISSING_PORT, "--no-tof", "--beacon-port", str(port),
                          "--beacon-target", "127.0.0.1", "--beacon-interval", "0.2")
        try:
            data, addr = rx.recvfrom(2048)
            self.check_payload(json.loads(data), b.port)
            self.assertEqual(addr[0], "127.0.0.1")
            _, _, body = get(b.port, "/")
            self.assertIn(b"beacon: UDP port %d" % port, body)
            self.assertEqual(set(get_json(b.port)["bridge"]),
                             {"version", "serial_port", "lines", "bad_lines"})   # JSON shape unchanged
        finally:
            b.close()
            rx.close()

    def test_no_beacon_flag(self):
        import socket
        rx, port = beacon_receiver()
        rx.settimeout(1.0)
        b = BridgeProcess("--serial-port", MISSING_PORT, "--no-tof", "--no-beacon", "--beacon-port", str(port),
                          "--beacon-target", "127.0.0.1", "--beacon-interval", "0.2")
        try:
            with self.assertRaises(socket.timeout):
                rx.recvfrom(2048)
            _, _, body = get(b.port, "/")
            self.assertIn(b"beacon: off", body)
        finally:
            b.close()
            rx.close()

    def test_parse_ip_json(self):
        self.assertEqual(tb.parse_ip_json(IP_JSON_SAMPLE), ["10.20.0.255", "10.74.67.255"])
        for junk in ("", "not json", "{}", "[1, 2]", None):
            self.assertEqual(tb.parse_ip_json(junk), [], junk)

    def test_default_targets_never_raise(self):
        targets = tb.default_beacon_targets()
        self.assertEqual(targets[0], "255.255.255.255")
        self.assertEqual(len(targets), len(set(targets)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
