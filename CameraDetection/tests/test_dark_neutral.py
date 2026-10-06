"""DarkNeutraliser: dark pixels lose their colour cast, real colours keep theirs."""
import json, os, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hazard_detector import DarkNeutraliser, dark_neutral_setting

n = DarkNeutraliser(50, 110)
out = n(np.array([[[40, 12, 45]]], dtype=np.uint8))[0, 0].astype(int)   # purple-black from infrared
assert max(out) - min(out) <= 2 and max(out) <= 50, out                    # now neutral and still dark
# Colour cards measured in the detector's frames on 1 Oct (blue, red, green, grey, white): unchanged
cards = np.array([[[1, 86, 216], [222, 8, 77], [6, 124, 103], [124, 129, 138], [186, 199, 197]]], dtype=np.uint8)
assert (n(cards) == cards).all(), n(cards)
mid = n(np.array([[[80, 40, 85]]], dtype=np.uint8))[0, 0].astype(int)    # dim purple in the ramp
assert 0 < mid[2] - mid[1] < 45, mid                                      # dim purple partly pulled, not removed
frame = np.random.default_rng(0).integers(0, 256, (480, 640, 3), dtype=np.uint8)
assert n(frame).shape == frame.shape and n(frame).dtype == np.uint8

assert dark_neutral_setting("30,90", "/nonexistent") == (30, 90)
assert dark_neutral_setting(None, "/nonexistent") is None
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "o.json")
    json.dump({"dark_neutral": [50, 110]}, open(p, "w")); assert dark_neutral_setting(None, p) == (50, 110)
    json.dump({"dark_neutral": "off"}, open(p, "w")); assert dark_neutral_setting(None, p) is None
print("dark neutral: all checks pass")
