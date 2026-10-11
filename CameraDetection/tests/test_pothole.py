"""Offline tests of CameraDetection/pothole_detector.py: road-band tiling, letterbox maths,
decode and NMS back to full-frame coordinates, the 2-of-3 debounce, the settings precedence,
and (when the ncnn package is installed) the run-2 model on a fixed picture.
Run: python CameraDetection/tests/test_pothole.py (or with pytest)."""
import json
import os
import sys
import tempfile
import types
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pothole_detector as p  # noqa: E402

MODEL = os.path.join(os.path.dirname(HERE), "training", "runs", "run2_sa_band_tiles_640",
                     "yolo11n_sa_band_tiles_320_ncnn_model")
IMAGE = os.path.join(HERE, "data", "pothole_slievebane_road.jpg")
try:
    import ncnn  # noqa: F401
    HAVE_NCNN = True
except ImportError:
    HAVE_NCNN = False


def to_input(box, tile, r, left, top):
    """Inverse of the decode: a full-frame box -> (cx, cy, w, h) in letterboxed-input pixels."""
    x1, y1, x2, y2 = box
    ix1, iy1 = (x1 - tile[0]) * r + left, (y1 - tile[1]) * r + top
    ix2, iy2 = (x2 - tile[0]) * r + left, (y2 - tile[1]) * r + top
    return (ix1 + ix2) / 2, (iy1 + iy2) / 2, ix2 - ix1, iy2 - iy1


class TilingTests(unittest.TestCase):
    def test_training_frames_match_cell_2g(self):
        # cell 2g on 3680 x 2760: rows int(0.42 H) to int(0.68 H), xs [0, (W - 1280) // 2, W - 1280]
        tiles = p.band_tiles(3680, 2760)
        self.assertEqual(tiles, [(0, 1159, 1280, 1876), (1200, 1159, 2480, 1876), (2400, 1159, 3680, 1876)])

    def test_camera_640x480(self):
        tiles = p.band_tiles(640, 480)
        self.assertEqual(tiles, [(0, 201, 223, 326), (208, 201, 431, 326), (417, 201, 640, 326)])
        # same aspect ratio as a training tile (1280 x 717), within a pixel of rounding
        self.assertAlmostEqual(223 / 125, 1280 / 717, delta=0.02)
        # the three tiles cover the whole width and overlap
        self.assertEqual(tiles[0][0], 0)
        self.assertEqual(tiles[-1][2], 640)
        self.assertLess(tiles[1][0], tiles[0][2])
        self.assertLess(tiles[2][0], tiles[1][2])

    def test_custom_band(self):
        self.assertEqual(p.band_rows(480, (0.5, 0.9)), (240, 432))

    def test_letterbox_params(self):
        r, nw, nh, left, top = p.letterbox_params(223, 125, 320)
        self.assertAlmostEqual(r, 320 / 223)
        self.assertEqual((nw, nh, left), (320, 179, 0))
        self.assertEqual(top, (320 - 179) // 2)

    def test_letterbox_image(self):
        img, r, left, top = p.letterbox(np.full((125, 223, 3), 7, np.uint8), 320)
        self.assertEqual(img.shape, (320, 320, 3))
        self.assertEqual(img[0, 0, 0], 114)            # padding above
        self.assertEqual(img[160, 160, 0], 7)          # content in the middle
        self.assertEqual(img[top - 1, 10, 0], 114)
        self.assertEqual(img[top, 10, 0], 7)


class DecodeTests(unittest.TestCase):
    def setUp(self):
        self.tiles = p.band_tiles(640, 480)
        self.r, _, _, self.left, self.top = p.letterbox_params(223, 125, 320)

    def pred_for(self, boxes_scores, tile, anchors=2100):
        pred = np.zeros((5, anchors), np.float32)
        for k, (box, s) in enumerate(boxes_scores):
            pred[:4, k] = to_input(box, tile, self.r, self.left, self.top)
            pred[4, k] = s
        return pred

    def test_round_trip_to_frame(self):
        tile = self.tiles[1]
        box = (250.0, 250.0, 310.0, 264.0)   # inside the centre tile
        b, s = p.decode_tile(self.pred_for([(box, 0.8)], tile), tile, self.r, self.left, self.top)
        self.assertEqual(len(b), 1)
        np.testing.assert_allclose(b[0], box, atol=1e-3)
        self.assertAlmostEqual(float(s[0]), 0.8, places=5)

    def test_threshold(self):
        tile = self.tiles[0]
        pred = self.pred_for([((10, 210, 40, 220), 0.49), ((50, 210, 90, 230), 0.51)], tile)
        b, s = p.decode_tile(pred, tile, self.r, self.left, self.top, conf=0.5)
        self.assertEqual(len(b), 1)
        np.testing.assert_allclose(b[0], (50, 210, 90, 230), atol=1e-3)

    def test_clipped_to_tile(self):
        tile = self.tiles[2]
        # a box reaching into the padding above the band is clipped to the tile
        pred = self.pred_for([((500, 190, 540, 215), 0.9)], tile)
        b, _ = p.decode_tile(pred, tile, self.r, self.left, self.top)
        self.assertAlmostEqual(b[0][1], 201, places=3)

    def test_overlap_merged_across_tiles(self):
        # one pothole in the overlap of the left and centre tiles is found by both
        box = (210.0, 260.0, 220.0, 270.0)
        t0, t1 = self.tiles[0], self.tiles[1]
        d0 = p.decode_tile(self.pred_for([(box, 0.6)], t0), t0, self.r, self.left, self.top)
        d1 = p.decode_tile(self.pred_for([((210.5, 260.0, 220.0, 270.5), 0.7)], t1), t1, self.r, self.left,
                           self.top)
        merged = p.merge_tiles([d0, d1, (np.zeros((0, 4)), np.zeros(0))])
        self.assertEqual(len(merged), 1)
        self.assertAlmostEqual(merged[0][4], 0.7, places=5)
        self.assertEqual(merged[0][5], 1)       # kept from the centre tile

    def test_separate_potholes_kept(self):
        a = (np.array([[10, 210, 40, 220.]]), np.array([0.6]))
        b = (np.array([[500, 300, 540, 320.]]), np.array([0.55]))
        self.assertEqual(len(p.merge_tiles([a, b])), 2)
        self.assertEqual(p.merge_tiles([]), [])

    def test_nms(self):
        boxes = [[0, 0, 10, 10], [1, 1, 10, 10], [20, 20, 30, 30]]
        self.assertEqual(p.nms(boxes, [0.5, 0.9, 0.3]), [1, 2])

    def test_record(self):
        rec = p.pothole_record((96.0, 240.0, 160.0, 264.0, 0.61234, 0), 640, 480, 53.5)
        self.assertEqual(rec["class"], "pothole")
        self.assertEqual(rec["bbox"], [0.15, 0.5, 0.25, 0.55])
        self.assertLess(rec["bearing_deg"], 0)      # left of centre
        self.assertEqual(rec["confidence"], 0.612)
        self.assertIsNone(rec["band"])
        self.assertIsNone(rec["est_distance_m"])
        self.assertTrue(rec["experimental"])
        self.assertEqual(rec["tile"], "left")
        # same bearing model as the main detector
        sys.path.insert(0, os.path.join(HERE, "fakes"))
        import hazard_detector as hd
        self.assertAlmostEqual(rec["bearing_deg"], round(hd.bearing_deg(0.2, 53.5), 2))


class DebounceTests(unittest.TestCase):
    def test_two_of_three(self):
        d = p.RunDebouncer()
        self.assertIsNone(d.update(True))          # 1 of 1
        self.assertIsNone(d.update(False))         # 1 of 2
        self.assertEqual(d.update(True), "active")  # 2 of 3
        self.assertTrue(d.active)

    def test_single_flickers_never_alert(self):
        d = p.RunDebouncer()
        out = [d.update(s) for s in [True, False, False, True, False, False, True, False, False]]
        self.assertEqual(out, [None] * 9)

    def test_clear_after_three_empty_runs(self):
        d = p.RunDebouncer()
        d.update(True)
        self.assertEqual(d.update(True), "active")
        self.assertIsNone(d.update(False))
        self.assertIsNone(d.update(True))          # resets the empty streak
        self.assertIsNone(d.update(False))
        self.assertIsNone(d.update(False))
        self.assertEqual(d.update(False), "cleared")
        self.assertFalse(d.active)
        self.assertIsNone(d.update(True))          # needs 2 of 3 again after a clear

    def test_bad_args(self):
        with self.assertRaises(ValueError):
            p.RunDebouncer(k=4, n=3)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, os.path.join(HERE, "fakes"))
        import hazard_detector as hd
        self.hd = hd
        self.dir = tempfile.mkdtemp()
        self.opts = os.path.join(self.dir, "detector_options.json")

    def args(self, **kw):
        base = dict(potholes=None, pothole_model=None, pothole_threads=None, pothole_rate=None,
                    pothole_band=None, pothole_conf=None)
        base.update(kw)
        return types.SimpleNamespace(**base)

    def test_defaults(self):
        s = self.hd.pothole_settings(self.args(), self.opts, self.dir)
        self.assertEqual(s["enabled"], self.hd.POTHOLES_DEFAULT)
        self.assertEqual(s["band"], (0.42, 0.68))
        self.assertEqual((s["threads"], s["rate"], s["conf"], s["reserve_core"]), (1, 0.25, 0.5, False))

    def test_options_file_then_cli(self):
        with open(self.opts, "w") as f:
            json.dump({"potholes": False, "pothole_band": [0.5, 0.8], "pothole_conf": 0.6}, f)
        s = self.hd.pothole_settings(self.args(), self.opts, self.dir)
        self.assertFalse(s["enabled"])
        self.assertEqual(s["band"], (0.5, 0.8))
        self.assertEqual(s["conf"], 0.6)
        s = self.hd.pothole_settings(self.args(potholes="on", pothole_band="0.4,0.7"), self.opts, self.dir)
        self.assertTrue(s["enabled"])
        self.assertEqual(s["band"], (0.4, 0.7))

    def test_bad_band(self):
        with self.assertRaises(ValueError):
            self.hd.pothole_settings(self.args(pothole_band="0.7,0.4"), self.opts, self.dir)

    def test_read_imgsz(self):
        self.assertEqual(p.read_imgsz(MODEL), 320)
        self.assertEqual(p.read_imgsz(MODEL.replace("_320_", "_640_")), 640)


@unittest.skipUnless(HAVE_NCNN and os.path.isdir(MODEL), "needs the ncnn package and the run-2 model")
class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PIL import Image
        cls.model = p.PotholeModel(MODEL, threads=2)
        cls.rgb = np.asarray(Image.open(IMAGE).convert("RGB"))

    def test_fixed_picture(self):
        # On 11 Oct 2026 the run-2 320 model found one pothole on this picture, conf 0.63, box
        # about (242, 250, 307, 263): a small pothole in the band, mid-distance on the road.
        dets = self.model.detect_frame(self.rgb)
        self.assertGreaterEqual(len(dets), 1)
        x1, y1, x2, y2, s, tile = max(dets, key=lambda d: d[4])
        self.assertGreaterEqual(s, 0.5)
        self.assertTrue(201 <= y1 < y2 <= 326)        # inside the road band
        self.assertLess(abs((x1 + x2) / 2 - 274), 20)
        self.assertLess(abs((y1 + y2) / 2 - 256), 10)

    def test_blank_picture(self):
        self.assertEqual(self.model.detect_frame(np.full((480, 640, 3), 128, np.uint8)), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
