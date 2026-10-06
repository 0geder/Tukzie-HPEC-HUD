"""Offline test of CameraDetection/hazard_detector.py with a fake camera and model
(tests/fakes). Run from anywhere: python CameraDetection/tests/test_alerts_endpoint.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "fakes"))
sys.path.insert(1, os.path.dirname(HERE))
os.chdir(os.path.dirname(HERE))   # labelmap.txt and outputs next to the detector

import sys, json, threading, time
import hazard_detector as h
# Real set_alerts on an object that never binds a port
class FakePreview(h.PreviewServer):
    def __init__(self, port, host="127.0.0.1"):
        self._lock = threading.Condition(); self._alerts_json = b""
        self.snapshots = []
    def publish(self, *a): pass
    def set_alerts(self, *a):
        super().set_alerts(*a); self.snapshots.append(self._alerts_json)
    def close(self): pass
_real_preview, _real_monotonic = h.PreviewServer, time.monotonic   # restored at the end (pytest runs the files in one process)
holder = {}
def make(port, host="127.0.0.1", colour_fix=None):
    holder["p"] = FakePreview(port, host); return holder["p"]
h.PreviewServer = make
sys.argv = ["x", "--duration", "30", "--log-path", "t3.jsonl", "--preview"]
import time
t=[0.0]
def mono():
    t[0]+=0.0705; return t[0]
time.monotonic = mono
try:
    h.main()
finally:
    h.PreviewServer, time.monotonic = _real_preview, _real_monotonic
snaps = holder["p"].snapshots
distinct = []
for s in snaps:
    if not distinct or distinct[-1] != s: distinct.append(s)
for s in distinct: print(s.decode()[:230])
