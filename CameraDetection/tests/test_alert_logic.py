"""Offline test of CameraDetection/hazard_detector.py with a fake camera and model
(tests/fakes). Run from anywhere: python CameraDetection/tests/test_alert_logic.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "fakes"))
sys.path.insert(1, os.path.dirname(HERE))
os.chdir(os.path.dirname(HERE))   # labelmap.txt and outputs next to the detector

import sys, time
import hazard_detector as h
h.CONFIDENCE_THRESHOLD = 0.5
# Cap to 100 frames by making the clock advance 0.14 s per call
_real_monotonic = time.monotonic   # restored at the end (pytest runs the files in one process)
t = [0.0]
def fake_mono():
    t[0] += 0.0705
    return t[0]
time.monotonic = fake_mono
sys.argv = ["hazard_detector.py", "--duration", "14", "--log-path", "test_alerts.jsonl"]
try:
    h.main()
finally:
    time.monotonic = _real_monotonic
