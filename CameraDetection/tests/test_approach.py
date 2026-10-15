"""Offline tests of the approaching-object warnings: the IoU tracker and the
time to contact from box growth in hazard_detector.py, the ToF closing rate
in sensor_fusion.py, the alert and detection schema, and the per-frame cost.
Synthetic box sequences and ToF histories only; no camera, no Pi.

Run from anywhere: python CameraDetection/tests/test_approach.py (or pytest)."""
import json
import os
import random
import sys
import tempfile
import threading
import time
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import hazard_detector as hd  # noqa: E402
import sensor_fusion as sf  # noqa: E402

F = 600.0        # focal length used to make the boxes (and to estimate closing speed)
W, H = 640, 480


def car_box(d, x_c=0.5, y_c=0.6, real_w=1.8, real_h=1.5, jitter=0.0, rng=None):
    """Normalised (x0, y0, x1, y1) of a car at d metres, optional relative jitter of width and height."""
    w = real_w * F / (d * W)
    h = real_h * F / (d * H)
    if jitter and rng is not None:
        w *= 1.0 + rng.uniform(-jitter, jitter)
        h *= 1.0 + rng.uniform(-jitter, jitter)
    return (x_c - w / 2, y_c - h / 2, x_c + w / 2, y_c + h / 2)


class Snap:
    """A track's state after one frame (the Track object itself changes)."""

    def __init__(self, tr):
        self.track = tr
        self.id, self.ttc_s, self.ttc_reason = tr.id, tr.ttc_s, tr.ttc_reason
        self.closing_mps, self.approaching = tr.closing_mps, tr.approaching
        self.samples = list(tr.samples)


def run(seq, fps=15.0, cls="car", t0=100.0):
    """Feed a list of boxes (or None for a missed frame) through one
    ApproachMonitor. Returns (monitor, per-frame Snap or None, events)."""
    m = hd.ApproachMonitor(F, W)
    tracks, events = [], []
    for k, box in enumerate(seq):
        t = t0 + k / fps
        dets = [] if box is None else [(cls, 0.8, box)]
        trs, ev = m.update(dets, t)
        tracks.append(Snap(trs[0]) if trs else None)
        events.extend((k, s, tr.id, tr.approach.band) for s, tr in ev)
    return m, tracks, events


class TheilSenTests(unittest.TestCase):
    def test_line_and_outlier(self):
        ts = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
        ys = [1.0 + 2.0 * t for t in ts]
        ys[2] += 5.0           # one gross outlier does not move the fit
        a, b, neg = hd.theil_sen(ts, ys)
        self.assertAlmostEqual(b, 2.0, places=6)
        self.assertAlmostEqual(a, 1.0, places=6)
        self.assertLess(neg, 0.5)

    def test_same_as_fusion_copy(self):
        rng = random.Random(1)
        ts = [k * 0.033 for k in range(9)]
        ys = [rng.uniform(0, 1) for _ in ts]
        self.assertEqual(hd.theil_sen(ts, ys), sf.theil_sen(ts, ys))
        self.assertIsNone(hd.theil_sen([1.0, 1.0], [0.0, 1.0]))

    def test_iou(self):
        self.assertAlmostEqual(hd.box_iou((0, 0, 1, 1), (0, 0, 1, 1)), 1.0)
        self.assertAlmostEqual(hd.box_iou((0, 0, 1, 1), (0.5, 0, 1.5, 1)), 1 / 3)
        self.assertEqual(hd.box_iou((0, 0, 1, 1), (2, 2, 3, 3)), 0.0)


class CameraTtcTests(unittest.TestCase):
    def test_constant_speed_gives_right_ttc(self):
        # car from 25 m at 6 m/s, at the Pi 5's 19 fps and the Pi 4's 14.7 fps
        for fps in (19.0, 14.7):
            v, d0 = 6.0, 25.0
            n = int(3.5 * fps)
            seq = [car_box(d0 - v * k / fps) for k in range(n)]
            m, tracks, _ = run(seq, fps)
            checked = 0
            for k, tr in enumerate(tracks):
                if k < 10:
                    continue
                truth = (d0 - v * k / fps) / v
                self.assertIsNotNone(tr.ttc_s, (fps, k, tr.ttc_reason))
                self.assertAlmostEqual(tr.ttc_s, truth, delta=0.02 * truth + 0.02, msg=(fps, k))
                # closing speed from the distance estimate: right here only because F matches
                self.assertAlmostEqual(tr.closing_mps, v, delta=0.05 * v)
                checked += 1
            self.assertGreater(checked, 30)
            self.assertEqual(len({tr.id for tr in tracks}), 1)

    def test_constant_speed_with_box_noise(self):
        # 1.5 % box noise per frame (SSD jitter on a steady object is about this)
        rng = random.Random(7)
        fps, v, d0 = 14.7, 5.0, 20.0
        seq = [car_box(d0 - v * k / fps, jitter=0.015, rng=rng) for k in range(int(3.0 * fps))]
        _, tracks, events = run(seq, fps)
        errs = []
        for k, tr in enumerate(tracks):
            truth = (d0 - v * k / fps) / v
            if k >= 12 and truth < 4.0 and tr.ttc_s is not None:
                errs.append(abs(tr.ttc_s - truth) / truth)
        self.assertGreater(len(errs), 15)
        errs.sort()
        self.assertLess(errs[len(errs) // 2], 0.15, errs)       # median error under 15 %
        self.assertIn("active", [e[1] for e in events])

    def test_alert_onset_and_escalation(self):
        fps, v, d0 = 15.0, 5.0, 30.0
        seq = [car_box(d0 - v * k / fps) for k in range(int(5.5 * fps))]
        m, tracks, events = run(seq, fps)
        statuses = [(s, band) for _, s, _, band in events]
        self.assertEqual(statuses[0], ("active", "warning"))
        self.assertIn(("escalated", "immediate"), statuses)
        k_on = events[0][0]
        truth_on = (d0 - v * k_on / fps) / v
        # taken 3 frames after the TTC first fell under 4 s
        self.assertTrue(3.6 < truth_on < 4.0, truth_on)
        k_imm = [k for k, s, _, _ in events if s == "escalated"][0]
        self.assertTrue(1.6 < (d0 - v * k_imm / fps) / v < 2.0)
        self.assertTrue(tracks[-1].approaching)

    def test_receding_and_constant_size_no_alert(self):
        fps = 15.0
        receding = [car_box(5.0 + 4.0 * k / fps) for k in range(60)]
        m, tracks, events = run(receding, fps)
        self.assertEqual(events, [])
        self.assertTrue(all(tr.ttc_s is None for tr in tracks))
        self.assertLess(tracks[-1].closing_mps, -3.5)      # moving away: negative closing speed
        still = [car_box(6.0) for _ in range(60)]
        m, tracks, events = run(still, fps)
        self.assertEqual(events, [])
        self.assertTrue(all(tr.ttc_s is None for tr in tracks))
        self.assertAlmostEqual(tracks[-1].closing_mps, 0.0, places=6)

    def test_jitter_does_not_trigger(self):
        # a still object with 3 % box jitter, 1000 frames, five seeds: never an approaching alert
        for seed in range(5):
            rng = random.Random(seed)
            seq = [car_box(6.0, jitter=0.03, rng=rng) for _ in range(1000)]
            m, tracks, events = run(seq, 15.0)
            self.assertEqual(events, [], seed)
            self.assertFalse(any(tr.approaching for tr in tracks))

    def test_slow_approach_is_not_alerted(self):
        # walking pace toward a far car: TTC far above 4 s, no alert
        fps, v, d0 = 15.0, 1.0, 15.0
        seq = [car_box(d0 - v * k / fps) for k in range(60)]
        _, tracks, events = run(seq, fps)
        self.assertEqual(events, [])

    def test_clipped_box_rejected(self):
        fps, v, d0 = 15.0, 6.0, 20.0
        # a fast approach with the car cut by the left image edge throughout
        seq = []
        for k in range(45):
            x0, y0, x1, y1 = car_box(d0 - v * k / fps, x_c=0.02)
            seq.append((0.0, y0, x1, y1))
        _, tracks, events = run(seq, fps)
        self.assertEqual(events, [])
        self.assertTrue(all(s.ttc_reason in ("few_frames", "clipped") for s in tracks))
        self.assertEqual(tracks[-1].ttc_reason, "clipped")
        self.assertIsNone(tracks[-1].closing_mps)
        # cut by the right edge only once near (under 7 m): no TTC from then on
        seq = []
        for k in range(45):
            x0, y0, x1, y1 = car_box(d0 - v * k / fps, x_c=0.88)
            seq.append((x0, y0, min(1.0, x1), y1))
        _, tracks, _ = run(seq, fps)
        for box, s in zip(seq, tracks):
            if box[2] >= 1.0 - hd.TTC_EDGE_MARGIN:
                self.assertIsNone(s.ttc_s)
                self.assertEqual(s.ttc_reason, "clipped")
        # clipped only at the bottom: width is fine, height check skipped, TTC still given
        seq = [car_box(d0 - v * k / fps, y_c=0.95) for k in range(30)]
        _, tracks, _ = run(seq, fps)
        self.assertEqual(tracks[-1].ttc_reason, "ok")

    def test_scale_ttc_reasons(self):
        mk = lambda ws, hs=None: [(k / 15.0, (0.5 - w / 2, 0.3, 0.5 + w / 2, 0.3 + (hs[k] if hs else w)))
                                  for k, w in enumerate(ws)]
        self.assertEqual(hd.scale_ttc(mk([0.1, 0.11]))[1], "few_frames")
        growing = [0.1 * (1 + 0.05 * k) for k in range(9)]
        self.assertEqual(hd.scale_ttc(mk(growing))[1], "ok")
        # width grows but the height does not (an object turning, not approaching)
        self.assertEqual(hd.scale_ttc(mk(growing, [0.2] * 9))[1], "height_disagrees")
        self.assertEqual(hd.scale_ttc(mk(list(reversed(growing))))[1], "not_growing")
        tiny = [0.1 * (1 + 0.004 * k) for k in range(9)]
        self.assertEqual(hd.scale_ttc(mk(tiny))[1], "slow")
        zig = [0.1, 0.13, 0.1, 0.131, 0.101, 0.132, 0.1, 0.133, 0.102]
        self.assertEqual(hd.scale_ttc(mk(zig, [0.1] * 9))[1], "inconsistent")


class TrackerTests(unittest.TestCase):
    def test_id_persists_through_missed_frames(self):
        seq = [car_box(8.0 - 0.1 * k) for k in range(20)]
        seq[5] = None              # one missed frame
        seq[10] = seq[11] = None   # two missed frames
        _, tracks, _ = run(seq)
        ids = {tr.id for tr in tracks if tr is not None}
        self.assertEqual(ids, {1})

    def test_three_missed_frames_start_a_new_track(self):
        seq = [car_box(8.0) for _ in range(20)]
        seq[8] = seq[9] = seq[10] = None
        _, tracks, _ = run(seq)
        self.assertEqual([tr.id for tr in tracks[:8]], [1] * 8)
        self.assertEqual({tr.id for tr in tracks[11:]}, {2})

    def test_two_objects_and_class_groups(self):
        m = hd.ApproachMonitor(F, W)
        a, b = car_box(8.0, x_c=0.25), car_box(8.0, x_c=0.75)
        for k in range(5):
            trs, _ = m.update([("car", 0.8, a), ("person", 0.7, b)], k / 15.0)
            self.assertEqual([tr.id for tr in trs], [1, 2])
        # the model calls the car a truck for one frame: same track (vehicle group)
        trs, _ = m.update([("truck", 0.6, a), ("person", 0.7, b)], 5 / 15.0)
        self.assertEqual([tr.id for tr in trs], [1, 2])
        self.assertEqual(trs[0].cls, "truck")
        # a person where the car was: a new track, not the car's
        trs, _ = m.update([("person", 0.6, a)], 6 / 15.0)
        self.assertNotIn(trs[0].id, (1,))

    def test_samples_window(self):
        seq = [car_box(10.0 - 0.2 * k) for k in range(40)]
        m, tracks, _ = run(seq, 15.0)
        tr = tracks[-1]
        span = tr.samples[-1][0] - tr.samples[0][0]
        self.assertLessEqual(span, hd.TTC_WINDOW_S + 1e-6)
        self.assertGreaterEqual(len(tr.samples), 9)

    def test_dropped_approaching_track_logs_clear(self):
        fps, v, d0 = 15.0, 5.0, 20.0
        seq = [car_box(d0 - v * k / fps) for k in range(int(2.0 * fps))] + [None] * 4
        _, _, events = run(seq, fps)
        self.assertEqual(events[0][1], "active")
        self.assertEqual(events[-1][1], "cleared")


class HysteresisTests(unittest.TestCase):
    def test_no_flicker_around_threshold(self):
        st = hd.ApproachState()
        evs = [st.update(x) for x in [3.9, 3.9, 3.9]]
        self.assertEqual(evs[-1], "active")
        evs = [st.update(x) for x in [4.2, 3.9, 4.6, 3.8, 4.9, 4.1] * 5]
        self.assertEqual([e for e in evs if e], [])     # never cleared: release is at 5 s
        self.assertEqual(st.band, "warning")
        evs = [st.update(5.5) for _ in range(5)]
        self.assertEqual(evs, [None] * 4 + ["cleared"])

    def test_invalid_frames_clear_after_five(self):
        st = hd.ApproachState()
        for _ in range(3):
            st.update(1.5)
        self.assertEqual(st.band, "immediate")
        evs = [st.update(None) for _ in range(4)] + [st.update(1.5)]
        self.assertEqual([e for e in evs if e], [])
        evs = [st.update(None) for _ in range(5)]
        self.assertEqual(evs[-1], "cleared")

    def test_onset_needs_three_consecutive(self):
        st = hd.ApproachState()
        self.assertEqual([st.update(x) for x in [3.0, 3.0, None, 3.0, 3.0]], [None] * 5)
        self.assertEqual(st.update(3.0), "active")

    def test_lowered_after_five(self):
        st = hd.ApproachState()
        for _ in range(3):
            st.update(1.0)
        evs = [st.update(x) for x in [2.2, 2.4, 2.6, 2.8, 3.0, 3.0, 3.0, 3.0]]
        # 2.2 and 2.4 are inside the 2.5 s release; five frames above it lower the band
        self.assertEqual([e for e in evs if e], ["lowered"])
        self.assertEqual(st.band, "warning")


class SchemaTests(unittest.TestCase):
    NEW = {"side", "track_id", "approaching", "ttc_s", "closing_mps"}

    def approaching_monitor(self):
        fps, v, d0 = 15.0, 5.0, 20.0
        seq = [car_box(d0 - v * k / fps) for k in range(int(2.0 * fps))]
        m, tracks, _ = run(seq, fps)
        return m, tracks[-1].track

    def test_track_fields(self):
        m, tr = self.approaching_monitor()
        f = hd.track_fields(tr, "rear")
        self.assertEqual(set(f), self.NEW)
        self.assertEqual((f["side"], f["track_id"], f["approaching"]), ("rear", 1, True))
        self.assertIsInstance(f["ttc_s"], float)
        self.assertIsInstance(f["closing_mps"], float)
        self.assertEqual(hd.track_fields(None, "front"),
                         {"side": "front", "track_id": None, "approaching": False, "ttc_s": None,
                          "closing_mps": None})
        json.dumps(f)

    def test_detection_entry_keeps_old_fields(self):
        _, tr = self.approaching_monitor()
        rec = hd.detection_record("car", 0.8, (0.3, 0.3, 0.7, 0.7), 640, F, 53.5)
        e = dict(rec, **hd.track_fields(tr, "front"))
        self.assertEqual(set(e), set(rec) | self.NEW)
        self.assertEqual({k: e[k] for k in rec}, rec)

    def test_alerts_list(self):
        m, tr = self.approaching_monitor()
        side = "front"
        # 1) a class-level distance alert held by the approaching track: band raised to its approach band
        rec = {"class": "car", "distance_band": "monitoring", "confidence": 0.8, "timestamp": "x",
               "alert_status": "active"}
        out = hd.alerts_list({"car": rec}, {"car": tr.id}, {}, m, {}, side)
        self.assertEqual(len(out), 1)
        self.assertEqual(set(out[0]), set(hd.ALERT_LOG_FIELDS) | self.NEW)
        self.assertEqual(out[0]["distance_band"], tr.approach.band)
        self.assertTrue(out[0]["approaching"])
        self.assertEqual(rec["distance_band"], "monitoring")      # the logged record itself is not changed
        # 2) no distance alert (car beyond 15 m, say): the approaching track has its own entry
        out = hd.alerts_list({}, {}, {}, m, {}, side)
        self.assertEqual([(e["class"], e["track_id"], e["approaching"]) for e in out], [("car", 1, True)])
        self.assertEqual(set(out[0]), set(hd.ALERT_LOG_FIELDS) | self.NEW)
        # 3) a more urgent distance band is not lowered by the approach band
        rec2 = dict(rec, distance_band="immediate")
        tr.approach.band = "warning"
        out = hd.alerts_list({"car": rec2}, {"car": tr.id}, {}, m, {}, side)
        self.assertEqual(out[0]["distance_band"], "immediate")
        # 4) the class's track is gone: its last fields are used
        last = hd.track_fields(None, side)
        last["track_id"] = 99
        out = hd.alerts_list({"person": dict(rec, **{"class": "person"})}, {"person": 99}, {"person": last},
                             hd.ApproachMonitor(), {}, side)
        self.assertEqual(out[0]["track_id"], 99)

    def test_log_approach(self):
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        try:
            hd.log_approach(path, "car", "warning", 0.812, "active", 3, 3.14159, "rear")
            hd.log_approach(path, "car", None, 0.0, "cleared", 3, None, "rear")
            with open(path) as f:
                recs = [json.loads(line) for line in f]
        finally:
            os.remove(path)
        self.assertEqual(set(recs[0]), set(hd.APPROACH_LOG_FIELDS))
        self.assertEqual((recs[0]["ttc_s"], recs[0]["track_id"], recs[0]["side"], recs[0]["approaching"]),
                         (3.1, 3, "rear", True))
        self.assertEqual((recs[1]["alert_status"], recs[1]["ttc_s"], recs[1]["distance_band"]), ("cleared", None, None))
        self.assertTrue(set(hd.ALERT_LOG_FIELDS) < set(hd.APPROACH_LOG_FIELDS))

    def test_side_setting(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            self.assertEqual(hd.side_setting(None, path + ".missing"), "front")
            with open(path, "w") as f:
                json.dump({"side": "rear"}, f)
            self.assertEqual(hd.side_setting(None, path), "rear")
            self.assertEqual(hd.side_setting("front", path), "front")
            with open(path, "w") as f:
                json.dump({"side": "left"}, f)
            with self.assertRaises(ValueError):
                hd.side_setting(None, path)
        finally:
            os.remove(path)

    def test_endpoints_echo_side(self):
        ps = hd.PreviewServer(0)
        port = ps._httpd.server_address[1]
        try:
            def fetch(path):
                with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=3) as r:
                    return json.loads(r.read())
            _, tr = self.approaching_monitor()
            rec = dict(hd.detection_record("car", 0.8, (0.3, 0.3, 0.7, 0.7), 640, F, 53.5),
                       **hd.track_fields(tr, "rear"))
            ps.set_detections([rec], 10.0, 14.7, 53.5, None, None, "rear")
            ps.set_alerts([], 14.7, 120.0, None, "rear")
            d = fetch("/detections")
            self.assertEqual(d["side"], "rear")
            self.assertEqual(d["detections"][0]["track_id"], 1)
            self.assertTrue(d["detections"][0]["approaching"])
            a = fetch("/alerts")
            self.assertEqual(set(a), {"active", "fps", "latency_ms", "side"})
            # without a side the top level is as before
            ps.set_alerts([], 14.7, 120.0)
            self.assertEqual(set(fetch("/alerts")), {"active", "fps", "latency_ms"})
        finally:
            ps.close()


class TofClosingTests(unittest.TestCase):
    S = sf.DEFAULT_CONFIG["sensors"]["ahead"]

    def hist(self, ranges_mm, hz=30.0, t0=50.0, name="ahead"):
        return [(t0 + k / hz, {"left": None, "ahead": None, "right": None, name: r})
                for k, r in enumerate(ranges_mm)]

    def test_approaching_gives_right_ttc(self):
        v = 0.5
        rs = [1150 - v * 1000 * k / 30.0 for k in range(15)]
        closing, ttc = sf.tof_closing(self.hist(rs), "ahead", self.S)
        self.assertAlmostEqual(closing, v, delta=0.01)
        self.assertAlmostEqual(ttc, rs[-1] / 1000.0 / v, delta=0.05)

    def test_none_and_out_of_range_ignored(self):
        v = 0.8
        rs = [1100 - v * 1000 * k / 30.0 for k in range(12)]
        rs[3], rs[6], rs[9] = None, 1900, None    # null, and beyond max_range_m (1.2 m)
        closing, ttc = sf.tof_closing(self.hist(rs), "ahead", self.S)
        self.assertAlmostEqual(closing, v, delta=0.02)
        self.assertIsNotNone(ttc)

    def test_still_with_noise_is_not_approaching(self):
        rng = random.Random(3)
        for _ in range(50):
            rs = [800 + rng.uniform(-10, 10) for _ in range(12)]
            closing, ttc = sf.tof_closing(self.hist(rs), "ahead", self.S)
            self.assertIsNone(ttc)
            self.assertLess(abs(closing), sf.TOF_MIN_CLOSING_MPS)

    def test_receding_and_too_few(self):
        rs = [500 + 600 * k / 30.0 for k in range(12)]
        closing, ttc = sf.tof_closing(self.hist(rs), "ahead", self.S)
        self.assertLess(closing, -0.5)
        self.assertIsNone(ttc)
        self.assertEqual(sf.tof_closing(self.hist([900, 880, 860, None, None, None]), "ahead", self.S), (None, None))
        self.assertEqual(sf.tof_closing([], "ahead", self.S), (None, None))

    def test_old_samples_outside_window(self):
        # a fast fall long ago, still now: only the last 0.3 s counts
        rs = [1100 - 40 * k for k in range(10)] + [700] * 12
        closing, ttc = sf.tof_closing(self.hist(rs), "ahead", self.S)
        self.assertIsNone(ttc)
        self.assertAlmostEqual(closing, 0.0, places=6)

    def test_thresholds_match_detector(self):
        self.assertEqual((sf.TTC_WARNING_S, sf.TTC_IMMEDIATE_S), (hd.TTC_WARNING_S, hd.TTC_IMMEDIATE_S))


class FusedTtcTests(unittest.TestCase):
    CFG = sf.load_config(None)
    T = 1000.0

    def det(self, bearing, est, **extra):
        import math
        x = 0.5 + math.tan(math.radians(bearing)) / (2 * math.tan(math.radians(53.5 / 2)))
        d = {"class": "person", "confidence": 0.8, "bbox": [x - 0.05, 0.2, x + 0.05, 0.9],
             "bearing_deg": bearing, "est_distance_m": est, "band": sf.band_for(est)}
        d.update(extra)
        return d

    def closing_hist(self, name="ahead", start=1000, v=0.6, n=12):
        return [(self.T - (n - 1 - k) / 30.0, {"left": None, "ahead": None, "right": None,
                                               name: start - v * 1000 * k / 30.0}) for k in range(n)]

    def test_fused_prefers_tof(self):
        cam = dict(side="front", track_id=4, approaching=False, ttc_s=9.0, closing_mps=0.1)
        hz = sf.fuse([self.det(0.0, 1.5, **cam)], self.T, self.closing_hist(), self.CFG, now=self.T + 0.05)
        h = hz[0]
        self.assertEqual((h["source"], h["ttc_source"], h["approaching"], h["side"]), ("fused", "tof", True, "front"))
        self.assertAlmostEqual(h["closing_mps"], 0.6, delta=0.02)
        self.assertAlmostEqual(h["ttc_s"], h["tof_distance_m"] / 0.6, delta=0.05)

    def test_fused_falls_back_to_camera_without_tof_rate(self):
        hist = [(self.T - 0.05, {"left": None, "ahead": 900, "right": None}),
                (self.T, {"left": None, "ahead": 890, "right": None})]
        cam = dict(side="rear", track_id=4, approaching=True, ttc_s=1.8, closing_mps=0.5)
        h = sf.fuse([self.det(0.0, 1.5, **cam)], self.T, hist, self.CFG, now=self.T)[0]
        self.assertEqual((h["source"], h["ttc_source"], h["ttc_s"], h["approaching"], h["side"]),
                         ("fused", "camera", 1.8, True, "rear"))

    def test_camera_only_beyond_tof_range(self):
        cam = dict(side="front", track_id=7, approaching=True, ttc_s=2.7, closing_mps=4.1)
        hz = sf.fuse([self.det(0.0, 12.0, **cam)], self.T, [], self.CFG, now=self.T, side="rear")
        h = hz[0]
        self.assertEqual((h["source"], h["ttc_source"], h["ttc_s"], h["closing_mps"], h["approaching"]),
                         ("camera", "camera", 2.7, 4.1, True))
        self.assertEqual(h["side"], "rear")     # the bridge's --side wins
        # an older detector without the new fields
        h = sf.fuse([self.det(0.0, 12.0)], self.T, [], self.CFG, now=self.T)[0]
        self.assertEqual((h["ttc_s"], h["closing_mps"], h["approaching"], h["ttc_source"], h["side"]),
                         (None, None, False, None, None))

    def test_tof_only_obstacle_approaching(self):
        hz = sf.fuse([], None, self.closing_hist("left", 900, 0.5), self.CFG, now=self.T, side="front")
        h = hz[0]
        self.assertEqual((h["class"], h["source"], h["sensor"], h["ttc_source"], h["approaching"], h["side"]),
                         ("obstacle", "tof", "left", "tof", True, "front"))
        self.assertAlmostEqual(h["ttc_s"], h["distance_m"] / 0.5, delta=0.05)

    def test_hazard_fields(self):
        h = sf.fuse([self.det(0.0, 1.5)], self.T, self.closing_hist(), self.CFG, now=self.T)[0]
        self.assertTrue({"ttc_s", "closing_mps", "approaching", "ttc_source", "side"} <= set(h))
        json.dumps(h)


class FusionRunnerSideTests(unittest.TestCase):
    def test_side_from_bridge_or_detector(self):
        import http.server

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                now = time.monotonic()
                body = json.dumps({"detections": [], "frame_t_mono": now - 0.05, "t_mono": now,
                                   "fps": 19.0, "side": "front"}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        url = "http://127.0.0.1:%d/detections" % httpd.server_address[1]
        hist = [(time.monotonic() - 0.1 + k * 0.03, {"left": None, "ahead": 600 - 15 * k, "right": None})
                for k in range(5)]
        try:
            got = []
            r = sf.FusionRunner(threading.Event(), lambda: hist, got.append, url=url, mode="on")
            r.step()
            self.assertEqual(got[-1]["hazards"][0]["side"], "front")
            r = sf.FusionRunner(threading.Event(), lambda: hist, got.append, url=url, mode="on", side="rear")
            r.step()
            self.assertEqual(got[-1]["hazards"][0]["side"], "rear")
            self.assertEqual(set(got[-1]), {"hazards", "t_mono", "camera_fps", "camera_age_ms", "config"})
        finally:
            httpd.shutdown()
            httpd.server_close()


class PerFrameCostTests(unittest.TestCase):
    def test_cost(self):
        """Tracker, TTC, alert list and per-detection fields for six objects a
        frame (two approaching, four still with jitter), 1500 frames."""
        rng = random.Random(0)
        m = hd.ApproachMonitor(F, W)
        xs = [0.15, 0.3, 0.45, 0.6, 0.75, 0.9]
        costs = []
        for k in range(1500):
            t = k / 15.0
            dets = []
            for j, x in enumerate(xs):
                d = (25.0 - 6.0 * (t % 3.5)) if j < 2 else 8.0 + j
                cls = "car" if j % 2 == 0 else "person"
                dets.append((cls, 0.7, car_box(d, x_c=x, real_w=0.5 if cls == "person" else 1.8,
                                                jitter=0.015, rng=rng)))
            t0 = time.perf_counter()
            trs, _ = m.update(dets, t)
            fields = [hd.track_fields(tr, "front") for tr in trs]
            hd.alerts_list({}, {}, {}, m, {}, "front")
            costs.append((time.perf_counter() - t0) * 1000.0)
            self.assertEqual(len(fields), 6)
        costs = costs[50:]
        costs.sort()
        med, p95 = costs[len(costs) // 2], costs[int(0.95 * (len(costs) - 1))]
        print("\nper-frame cost, 6 objects: median %.3f ms, p95 %.3f ms, max %.3f ms" % (med, p95, costs[-1]))
        self.assertLess(med, 2.0)


class DetectorRunTests(unittest.TestCase):
    """main() with the fake camera and a fake model that shows a car closing
    at about 10 m/s: an approaching alert is logged and served."""

    def test_main_logs_and_serves_approach(self):
        sys.path.insert(0, os.path.join(HERE, "fakes"))
        import ai_edge_litert.interpreter as fake_interp
        real_script, real_preview = fake_interp.script, hd.PreviewServer
        cwd = os.getcwd()

        def approach_script(n):
            d = 30.0 - 0.25 * n
            if d < 2.5:
                return []
            x0, y0, x1, y1 = car_box(d)
            return [(2, 0.8, (y0, x0, y1, x1))]       # class 2 = car once "???" is dropped

        snaps = []

        class FakePreview(hd.PreviewServer):
            def __init__(self, port, host="127.0.0.1", colour_fix=None):
                self._lock = threading.Condition()
                self._alerts_json = b""
                self._detections = None

            def publish(self, *a):
                pass

            def set_alerts(self, *a):
                super().set_alerts(*a)
                snaps.append(json.loads(self._alerts_json))

            def close(self):
                pass

        fd, log = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        fake_interp.script = approach_script
        hd.PreviewServer = FakePreview
        argv = sys.argv
        try:
            os.chdir(ROOT)
            sys.argv = ["hazard_detector.py", "--duration", "5", "--log-path", log, "--preview", "--side", "rear"]
            hd.main()
            with open(log) as f:
                recs = [json.loads(line) for line in f]
        finally:
            sys.argv = argv
            os.chdir(cwd)
            fake_interp.script, hd.PreviewServer = real_script, real_preview
            os.remove(log)
        appr = [r for r in recs if r.get("approaching")]
        self.assertTrue(appr, recs)
        self.assertEqual(set(appr[0]), set(hd.APPROACH_LOG_FIELDS))
        self.assertEqual((appr[0]["class"], appr[0]["alert_status"], appr[0]["side"]), ("car", "active", "rear"))
        self.assertIsInstance(appr[0]["ttc_s"], float)
        self.assertLess(appr[0]["ttc_s"], hd.TTC_WARNING_S)
        # distance-alert lines keep exactly the five fields
        self.assertTrue(all(set(r) == set(hd.ALERT_LOG_FIELDS) for r in recs if "approaching" not in r))
        served = [e for s in snaps for e in s["active"] if e["approaching"]]
        self.assertTrue(served)
        self.assertTrue(all(s.get("side") == "rear" for s in snaps))
        self.assertEqual(served[-1]["side"], "rear")
        self.assertIn(served[-1]["distance_band"], ("warning", "immediate"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
