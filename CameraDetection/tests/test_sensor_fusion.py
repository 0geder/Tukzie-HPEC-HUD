"""Offline tests of the camera and ToF fusion: sensor_fusion.py, the
detector's GET /detections (hazard_detector.py) and the fusion block of
telemetry_bridge.py. No camera, no ToF sensors, no Raspberry Pi.

Run from anywhere: python CameraDetection/tests/test_sensor_fusion.py
(or with pytest)."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(REPO, "BenchTest"))
import sensor_fusion as sf  # noqa: E402
import hazard_detector as hd  # noqa: E402
import fusion_report  # noqa: E402

from test_telemetry_bridge import BridgeProcess, get, get_json, SAMPLE  # noqa: E402

CFG = sf.load_config(None)
T = 1000.0   # frame time used throughout, local monotonic seconds


def x_for_bearing(b, hfov=53.5):
    import math
    return 0.5 + math.tan(math.radians(b)) / (2 * math.tan(math.radians(hfov / 2)))


def det(cls, bearing, est, conf=0.8, width=0.1):
    x = x_for_bearing(bearing)
    return {"class": cls, "confidence": conf, "bbox": [x - width / 2, 0.2, x + width / 2, 0.9],
            "bearing_deg": bearing, "est_distance_m": est, "band": sf.band_for(est)}


def hist(values, t_end=T, n=5, period=0.05):
    """n identical ToF samples ending at t_end."""
    return [(t_end - (n - 1 - k) * period, dict(values)) for k in range(n)]


NONE3 = {"left": None, "ahead": None, "right": None}


class BearingTests(unittest.TestCase):
    def test_bearing_from_x(self):
        self.assertAlmostEqual(sf.bearing_from_x(0.5, 53.5), 0.0)
        self.assertAlmostEqual(sf.bearing_from_x(1.0, 53.5), 26.75, places=6)
        self.assertAlmostEqual(sf.bearing_from_x(0.0, 53.5), -26.75, places=6)
        self.assertAlmostEqual(sf.bearing_from_x(0.2, 53.5, mirror=True), -sf.bearing_from_x(0.2, 53.5))
        # pinhole, not linear: halfway from the centre to the edge is more than half the half-angle
        self.assertAlmostEqual(sf.bearing_from_x(0.75, 53.5), 14.15, places=2)
        for b in (-26.0, -10.0, 0.0, 7.5, 20.0):
            self.assertAlmostEqual(sf.bearing_from_x(x_for_bearing(b), 53.5), b, places=6)

    def test_detector_and_fusion_agree(self):
        for x in (0.0, 0.1, 0.37, 0.5, 0.81, 1.0):
            self.assertAlmostEqual(hd.bearing_deg(x, 53.5), sf.bearing_from_x(x, 53.5), places=9)
        self.assertEqual(hd.DEFAULT_HFOV_DEG, CFG["camera_hfov_deg"])

    def test_detection_record(self):
        # model box is (ymin, xmin, ymax, xmax); record bbox is (x0, y0, x1, y1), clipped
        r = hd.detection_record("person", 0.734, (0.1, 0.4, 1.2, 0.6), 640, 600.0, 53.5)
        self.assertEqual(r["bbox"], [0.4, 0.1, 0.6, 1.0])
        self.assertAlmostEqual(r["bearing_deg"], 0.0, places=2)
        self.assertAlmostEqual(r["est_distance_m"], 0.5 * 600 / 128, places=3)
        self.assertEqual(r["band"], "immediate")
        self.assertEqual(r["confidence"], 0.734)
        self.assertEqual(set(r), {"class", "confidence", "bbox", "bearing_deg", "est_distance_m", "band"})
        left = hd.detection_record("car", 0.9, (0.3, 0.0, 0.5, 0.1), 640, 600.0, 53.5)
        self.assertLess(left["bearing_deg"], -20)


class BandTests(unittest.TestCase):
    def test_bands_match_detector(self):
        self.assertEqual([tuple(b) for b in sf.DEFAULT_BANDS], [tuple(b) for b in hd.DISTANCE_BANDS])
        for d in (None, 0.4, 3.0, 3.01, 7.9, 14.0, 15.0, 15.1, 40.0):
            self.assertEqual(sf.band_for(d), hd.distance_band(d), d)

    def test_band_recomputed_from_fused_distance(self):
        # camera says 5 m (warning), ToF ahead 0.9 m: the fused band is immediate
        hz = sf.fuse([det("person", 0.0, 5.0)], T, hist({"left": None, "ahead": 900, "right": None}),
                     CFG, now=T + 0.1)
        self.assertEqual(len(hz), 1)
        h = hz[0]
        self.assertEqual((h["source"], h["sensor"], h["distance_m"], h["band"]), ("fused", "ahead", 0.9, "immediate"))
        self.assertEqual((h["camera_distance_m"], h["tof_distance_m"]), (5.0, 0.9))
        # camera-only keeps the camera band; beyond 15 m no band
        hz = sf.fuse([det("car", 0.0, 5.0), det("bus", 3.0, 20.0)], T, hist(NONE3), CFG, now=T + 0.1)
        self.assertEqual([(h["class"], h["source"], h["band"]) for h in hz],
                         [("car", "camera", "warning"), ("bus", "camera", None)])

    def test_detector_bands_take_priority(self):
        hz = sf.fuse([det("car", 0.0, 5.0)], T, [], CFG, bands=[(6.0, "near"), (20.0, "far")], now=T)
        self.assertEqual(hz[0]["band"], "near")


class AssociationTests(unittest.TestCase):
    def fuse(self, dets, tof, frame_t=T, history=None, now=None):
        return sf.fuse(dets, frame_t, history if history is not None else hist(tof), CFG,
                       now=T + 0.1 if now is None else now)

    def test_inside_cone(self):
        # ahead cone: 0 +/- (12.5 + 5 gate)
        for b in (0.0, -12.0, 17.0):
            hz = self.fuse([det("person", b, 2.0)], {"left": None, "ahead": 800, "right": None})
            self.assertEqual(hz[0]["source"], "fused", b)
            self.assertEqual(hz[0]["distance_m"], 0.8)
            self.assertAlmostEqual(hz[0]["bearing_deg"], b, places=1)

    def test_outside_cone(self):
        # 19 degrees is outside the ahead cone (up to 17.5 with the gate) and inside the right
        # cone (17.5 to 52.5), which reads nothing: camera-only, and ahead's reading becomes a
        # ToF-only obstacle.
        hz = self.fuse([det("person", 19.0, 2.0)], {"left": None, "ahead": 800, "right": None})
        srcs = sorted((h["source"], h["class"]) for h in hz)
        self.assertEqual(srcs, [("camera", "person"), ("tof", "obstacle")])
        cam = [h for h in hz if h["source"] == "camera"][0]
        self.assertEqual(cam["distance_m"], 2.0)
        self.assertIsNone(cam["tof_distance_m"])
        # a narrower config with no gate: 13 degrees is outside the ahead cone
        cfg = sf.load_config(None)
        cfg["gate_deg"] = 0.0
        hz = sf.fuse([det("person", 13.0, 2.0)], T, hist({"left": None, "ahead": 800, "right": None}), cfg, now=T)
        self.assertEqual(sorted(h["source"] for h in hz), ["camera", "tof"])

    def test_out_of_range(self):
        # 1.5 m is beyond max_range_m 1.2: no fusion and no ToF-only obstacle
        hz = self.fuse([det("person", 0.0, 1.6)], {"left": None, "ahead": 1500, "right": None})
        self.assertEqual([(h["source"], h["distance_m"]) for h in hz], [("camera", 1.6)])
        hz = self.fuse([det("person", 0.0, 1.6)], {"left": None, "ahead": None, "right": None})
        self.assertEqual([h["source"] for h in hz], ["camera"])

    def test_stale_timestamps(self):
        tof = {"left": None, "ahead": 800, "right": None}
        # every ToF sample at least 250 ms after the frame: no association
        hz = self.fuse([det("person", 0.0, 2.0)], None, history=hist(tof, t_end=T + 0.45), now=T + 0.45)
        self.assertEqual(sorted(h["source"] for h in hz), ["camera", "tof"])
        # nearest sample 150 ms before the frame: associated, dt reported
        h = sf.fuse([det("person", 0.0, 2.0)], T, hist(tof, t_end=T - 0.15), CFG, now=T)[0]
        self.assertEqual((h["source"], h["tof_dt_ms"]), ("fused", -150))
        # camera frame older than camera_stale_ms: detections dropped, ToF still reported
        hz = sf.fuse([det("person", 0.0, 2.0)], T, hist(tof, t_end=T + 1.5), CFG, now=T + 1.5)
        self.assertEqual([(h["class"], h["source"]) for h in hz], [("obstacle", "tof")])

    def test_two_objects_two_sensors(self):
        tof = {"left": 700, "ahead": 1000, "right": None}
        hz = self.fuse([det("car", 0.0, 1.2), det("person", -24.0, 0.9)], tof)
        got = sorted((h["class"], h["source"], h["sensor"], h["distance_m"]) for h in hz)
        self.assertEqual(got, [("car", "fused", "ahead", 1.0), ("person", "fused", "left", 0.7)])
        self.assertEqual([h["distance_m"] for h in hz], [0.7, 1.0])   # nearest first

    def test_two_objects_one_cone(self):
        # both in the ahead cone; the sensor goes to the one whose camera estimate is nearer its reading
        tof = {"left": None, "ahead": 1000, "right": None}
        hz = self.fuse([det("person", -5.0, 3.5), det("dog", 6.0, 1.1)], tof)
        by = {h["class"]: h for h in hz}
        self.assertEqual(by["dog"]["source"], "fused")
        self.assertEqual(by["person"]["source"], "camera")
        self.assertEqual(by["person"]["distance_m"], 3.5)

    def test_closest_tof_wins(self):
        # wide cones so one bearing falls in two: the nearer reading is used
        cfg = sf.load_config(None)
        for s in cfg["sensors"].values():
            s["half_angle_deg"] = 30.0
        hz = sf.fuse([det("person", -18.0, 1.0)], T, hist({"left": 600, "ahead": 1100, "right": None}), cfg, now=T)
        fused = [h for h in hz if h["source"] == "fused"][0]
        self.assertEqual((fused["sensor"], fused["distance_m"]), ("left", 0.6))
        # the ahead sensor was not used and reads in range: reported as an obstacle
        self.assertIn(("obstacle", "tof", "ahead"), [(h["class"], h["source"], h["sensor"]) for h in hz])

    def test_fields(self):
        h = self.fuse([det("person", 0.0, 2.0)], {"left": None, "ahead": 800, "right": None})[0]
        self.assertEqual(set(h), {"class", "source", "sensor", "bearing_deg", "distance_m", "band", "confidence",
                                  "camera_distance_m", "tof_distance_m", "tof_dt_ms"})
        json.dumps(h)


class DebounceTests(unittest.TestCase):
    def test_three_readings(self):
        near = {"left": None, "ahead": 600, "right": None}
        h2 = [(T - 0.05, dict(NONE3))] + hist(near, n=2)
        self.assertEqual(sf.fuse([], None, h2, CFG, now=T), [])
        h3 = hist(near, n=3)
        hz = sf.fuse([], None, h3, CFG, now=T)
        self.assertEqual([(h["class"], h["source"], h["sensor"], h["distance_m"], h["band"], h["confidence"])
                          for h in hz], [("obstacle", "tof", "ahead", 0.6, "immediate", None)])
        self.assertEqual(hz[0]["bearing_deg"], 0.0)

    def test_gap_resets(self):
        near = {"left": None, "ahead": 600, "right": None}
        h = hist(near, t_end=T - 0.1, n=3) + [(T - 0.05, dict(NONE3)), (T, dict(near))]
        self.assertEqual(sf.fuse([], None, h, CFG, now=T), [])
        # out of range in the middle also resets
        far = {"left": None, "ahead": 1300, "right": None}
        h = hist(near, t_end=T - 0.1, n=2) + [(T - 0.05, far), (T, dict(near))]
        self.assertFalse(sf.tof_debounced(h, "ahead", CFG["sensors"]["ahead"], 3))

    def test_latest_value_used(self):
        h = [(T - 0.1, {"left": 900, "ahead": None, "right": None}),
             (T - 0.05, {"left": 800, "ahead": None, "right": None}),
             (T, {"left": 700, "ahead": None, "right": None})]
        hz = sf.fuse([], None, h, CFG, now=T)
        self.assertEqual([(h["sensor"], h["distance_m"], h["bearing_deg"]) for h in hz], [("left", 0.7, -35.0)])

    def test_associated_sensor_not_reported_twice(self):
        hz = sf.fuse([det("person", 0.0, 1.0)], T, hist({"left": None, "ahead": 900, "right": None}), CFG, now=T)
        self.assertEqual([h["source"] for h in hz], ["fused"])


class ConfigTests(unittest.TestCase):
    def test_partial_file(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump({"_note": "x", "gate_deg": 2.0, "sensors": {"left": {"bearing_deg": -30.0}}}, f)
        try:
            cfg = sf.load_config(path)
        finally:
            os.remove(path)
        self.assertEqual(cfg["gate_deg"], 2.0)
        self.assertEqual(cfg["sensors"]["left"], {"bearing_deg": -30.0, "half_angle_deg": 12.5, "max_range_m": 1.2})
        self.assertEqual(cfg["sensors"]["ahead"]["bearing_deg"], 0.0)
        self.assertNotIn("_note", cfg)

    def test_shipped_config(self):
        cfg = sf.load_config(os.path.join(ROOT, "fusion_config.json"))
        self.assertEqual(set(cfg["sensors"]), {"left", "ahead", "right"})
        self.assertEqual([cfg["sensors"][n]["bearing_deg"] for n in ("left", "ahead", "right")], [-35.0, 0.0, 35.0])
        self.assertEqual(cfg["max_dt_ms"], 200)


class DetectionsEndpointTests(unittest.TestCase):
    """The detector's real PreviewServer on a free port."""

    def test_detections_and_alerts(self):
        ps = hd.PreviewServer(0)
        port = ps._httpd.server_address[1]
        try:
            def fetch(path):
                with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=3) as r:
                    return r.headers.get("Content-Type"), json.loads(r.read())
            ctype, d = fetch("/detections")
            self.assertEqual(ctype, "application/json")
            self.assertEqual((d["detections"], d["frame_t_mono"]), ([], None))
            rec = hd.detection_record("person", 0.7, (0.1, 0.45, 0.9, 0.55), 640, 600.0, 53.5)
            ps.set_detections([rec], 123.456, 14.84)
            ps.set_alerts([], 14.84, 90.0)
            _, d = fetch("/detections")
            self.assertEqual(d["detections"], [rec])
            self.assertEqual(d["frame_t_mono"], 123.456)
            self.assertEqual(d["fps"], 14.8)
            self.assertEqual(d["hfov_deg"], 53.5)
            self.assertEqual(d["bands"], [[3.0, "immediate"], [8.0, "warning"], [15.0, "monitoring"]])
            self.assertIsInstance(d["t_mono"], float)
            self.assertNotIn("image", json.dumps(d))
            _, a = fetch("/alerts")
            self.assertEqual(set(a), {"active", "fps", "latency_ms"})   # /alerts unchanged
            # what the fusion makes of it
            resp, frame_t = sf.fetch_detections("http://127.0.0.1:%d/detections" % port)
            self.assertEqual(resp["detections"][0]["class"], "person")
            self.assertIsNotNone(frame_t)
        finally:
            ps.close()


class FakeDetector:
    """A fake GET /detections: a person at the left edge of the view
    (bearing -24, inside the left ToF cone with the gate) and a car
    straight ahead at 6 m (beyond ToF range)."""

    def __init__(self):
        fake = self
        self.requests = 0

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                fake.requests += 1
                now = time.monotonic()
                body = json.dumps({
                    "detections": [det("person", -24.0, 1.4, conf=0.71, width=0.08),
                                   det("car", 0.0, 6.0, conf=0.9, width=0.2)],
                    "frame_t_mono": now - 0.08, "t_mono": now, "fps": 14.8, "hfov_deg": 53.5,
                    "bands": [[3.0, "immediate"], [8.0, "warning"], [15.0, "monitoring"]],
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class BridgeFusionTests(unittest.TestCase):
    """The bridge as a process: --replay, --fake-tof, --fusion on against
    the fake detector. Fake ToF: left 650 to 950 mm, ahead 1500 mm and
    more (out of range), right 550 to 750 mm except about 1 to 5 s after
    start (8190, null)."""

    @classmethod
    def setUpClass(cls):
        cls.det = FakeDetector()
        fd, cls.log = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        cls.b = BridgeProcess("--replay", SAMPLE, "--replay-interval", "0.05", "--fake-tof", "--no-beacon",
                              "--fusion", "on", "--detections-url", "http://127.0.0.1:%d/detections" % cls.det.port,
                              "--fusion-log", cls.log, "--duration", "8")

    @classmethod
    def tearDownClass(cls):
        cls.b.close()
        cls.det.close()
        os.remove(cls.log)

    def wait_fusion(self):
        deadline = time.monotonic() + 4
        d = get_json(self.b.port)
        while ("fusion" not in d or not d["fusion"]["hazards"]) and time.monotonic() < deadline:
            time.sleep(0.1)
            d = get_json(self.b.port)
        return d

    def test_fusion_block(self):
        d = self.wait_fusion()
        self.assertEqual(set(d), {"esp32", "tof", "bridge", "fusion"})
        f = d["fusion"]
        self.assertEqual(set(f), {"hazards", "age_ms", "camera_fps", "camera_age_ms", "config"})
        self.assertEqual(f["config"], "fusion_config.json")
        self.assertEqual(f["camera_fps"], 14.8)
        self.assertTrue(0 <= f["age_ms"] < 1000, f["age_ms"])
        self.assertTrue(50 <= f["camera_age_ms"] < 500, f["camera_age_ms"])
        by = {h["class"]: h for h in f["hazards"]}
        p = by["person"]
        self.assertEqual((p["source"], p["sensor"], p["band"]), ("fused", "left", "immediate"))
        self.assertTrue(0.6 <= p["tof_distance_m"] <= 1.0, p)
        self.assertEqual(p["distance_m"], p["tof_distance_m"])
        self.assertEqual(p["camera_distance_m"], 1.4)
        self.assertAlmostEqual(p["bearing_deg"], -24.0, places=0)
        self.assertLessEqual(abs(p["tof_dt_ms"]), 200)
        c = by["car"]
        self.assertEqual((c["source"], c["distance_m"], c["band"], c["tof_distance_m"]), ("camera", 6.0, "warning", None))
        self.assertTrue(all(h["source"] != "tof" or h["sensor"] == "right" for h in f["hazards"]))

    def test_hazards_endpoint_and_status(self):
        self.wait_fusion()
        status, ctype, body = get(self.b.port, "/hazards")
        self.assertEqual((status, ctype), (200, "application/json"))
        self.assertEqual(set(json.loads(body)), {"hazards", "age_ms", "camera_fps", "camera_age_ms", "config"})
        _, _, body = get(self.b.port, "/")
        self.assertIn(b"fusion: ", body)

    def test_right_tof_only_obstacle_comes_and_goes(self):
        seen = set()
        deadline = time.monotonic() + 7
        while time.monotonic() < deadline and len(seen) < 2:
            hz = get_json(self.b.port).get("fusion", {}).get("hazards", [])
            seen.add(any(h["source"] == "tof" and h["sensor"] == "right" for h in hz))
            time.sleep(0.1)
        self.assertEqual(seen, {True, False})

    def test_zz_log(self):
        self.assertEqual(self.b.wait_exit(15), 0)
        out = "".join(self.b.output)
        self.assertIn("Fusion on", out)
        self.assertIn("Fusion: ", out)
        with open(self.log, encoding="utf-8") as f:
            recs = [json.loads(line) for line in f if line.strip()]
        self.assertGreater(len(recs), 20)     # 5 Hz for about 8 s
        r = recs[-1]
        self.assertEqual(set(r), {"t", "t_mono", "camera_fps", "camera_age_ms", "tof_mm", "hazards"})
        self.assertEqual(set(r["tof_mm"]), {"left", "ahead", "right"})
        self.assertTrue(any(h["source"] == "fused" for rec in recs for h in rec["hazards"]))
        # the report script reads it
        s = fusion_report.summary(recs)
        self.assertGreater(s["by_source"]["fused"], 10)
        self.assertGreater(s["by_source"]["camera"], 10)


class BridgeAutoModeTests(unittest.TestCase):
    def test_no_detector_no_block(self):
        # auto mode with nothing answering: the /telemetry JSON is unchanged and /hazards says inactive
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        free = s.getsockname()[1]
        s.close()
        b = BridgeProcess("--serial-port", "COM239" if os.name == "nt" else "/dev/ttyACM_missing", "--fake-tof",
                          "--no-beacon", "--detections-url", "http://127.0.0.1:%d/detections" % free,
                          "--fusion-log", "")
        try:
            time.sleep(1.0)
            d = get_json(b.port)
            self.assertEqual(set(d), {"esp32", "tof", "bridge"})
            with self.assertRaises(urllib.error.HTTPError) as cm:
                get(b.port, "/hazards")
            self.assertEqual(cm.exception.code, 503)
            _, _, body = get(b.port, "/")
            self.assertIn(b"fusion: waiting for the detector", body)
        finally:
            b.close()


def write_log(path, recs):
    with open(path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")


def rec(t, hazards):
    return {"t": "x", "t_mono": t, "camera_fps": 14.0, "camera_age_ms": 100,
            "tof_mm": {"left": None, "ahead": None, "right": None}, "hazards": hazards}


def hz(cls, source, sensor, dist, cam=None, tof=None, bearing=0.0):
    return {"class": cls, "source": source, "sensor": sensor, "bearing_deg": bearing, "distance_m": dist,
            "band": sf.band_for(dist), "confidence": None if source == "tof" else 0.7,
            "camera_distance_m": cam, "tof_distance_m": tof, "tof_dt_ms": None}


class ReportTests(unittest.TestCase):
    def test_f2_pass_and_fail(self):
        good = [rec(i * 0.2, [hz("person", "fused", "ahead", 0.52, cam=0.8, tof=0.52)]) for i in range(20)]
        r = fusion_report.f2(good, 0.5, "person", 0.05)
        self.assertTrue(r["pass"])
        self.assertAlmostEqual(r["fused"]["med_err"], 0.02)
        self.assertAlmostEqual(r["camera"]["med_err"], 0.3)
        bad = [rec(i * 0.2, [hz("person", "fused", "ahead", 0.6, cam=0.8, tof=0.6)]) for i in range(20)]
        self.assertFalse(fusion_report.f2(bad, 0.5, "person", 0.05)["pass"])
        far = [rec(i * 0.2, [hz("person", "camera", None, 1.9, cam=1.9)]) for i in range(20)]
        self.assertTrue(fusion_report.f2(far, 1.5, "person", 0.05)["pass"])

    def test_f1_f3_f4(self):
        walk = [rec(i * 0.2, [hz("person", "camera" if i < 5 else "fused", None if i < 5 else "ahead",
                                 1.0, cam=1.2, tof=1.0, bearing=-25 + 3 * i)]) for i in range(15)]
        r = fusion_report.f1(walk, "person")
        self.assertEqual(r["direction"], 1)
        self.assertEqual(r["monotonic_fraction"], 1.0)
        self.assertEqual(r["fused_sensor_order"], ["ahead"])
        box = [rec(i * 0.2, [hz("obstacle", "tof", "ahead", 0.79, tof=0.79)]) for i in range(10)]
        self.assertTrue(fusion_report.f3(box, 0.8)["pass"])
        person = [rec(i * 0.2, [hz("person", "camera", None, 2.8, cam=2.8, bearing=2.0)]) for i in range(10)]
        r = fusion_report.f4(person, 2.5, "person")
        self.assertTrue(r["pass"])
        self.assertAlmostEqual(r["camera"]["med_err"], 0.3)

    def test_cli(self):
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        try:
            write_log(path, [rec(i * 0.2, [hz("person", "fused", "ahead", 0.98, cam=1.3, tof=0.98)]) for i in range(10)])
            self.assertEqual(fusion_report.main(["f2", "%s:1.0" % path, "--class", "person"]), 0)
            self.assertEqual(fusion_report.main(["summary", path]), 0)
            self.assertEqual(fusion_report.main(["f4", path, "--tape", "2.5"]), 1)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
