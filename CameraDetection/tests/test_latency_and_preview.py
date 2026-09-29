"""Offline test of CameraDetection/hazard_detector.py with a fake camera and model
(tests/fakes). Run from anywhere: python CameraDetection/tests/test_latency_and_preview.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "fakes"))
sys.path.insert(1, os.path.dirname(HERE))
os.chdir(os.path.dirname(HERE))   # labelmap.txt and outputs next to the detector

import sys, time, threading
import hazard_detector as h
sys.argv = ["hazard_detector.py", "--duration", "6", "--log-path", "t.jsonl", "--timing-log", "timing.csv"]
h.main()
# encoder thread test without binding a port
ps = h.PreviewServer.__new__(h.PreviewServer)
ps._lock = threading.Condition(); ps._jpeg = None; ps._pending = None
ps._pending_cv = threading.Condition(); ps._running = True
t = threading.Thread(target=ps._encode_loop, daemon=True); t.start()
import numpy as np
t0 = time.monotonic()
for k in range(20):
    ps.publish(np.zeros((480,640,3),np.uint8), [{'box':(10,10,200,300),'class':'person','confidence':0.6,'distance_m':2.0,'band':'immediate'}], "7.0 fps  sensor-to-result 180 ms")
print("20 publishes took %.1f ms (should be ~0, non-blocking)" % ((time.monotonic()-t0)*1000))
time.sleep(2.0); print("latest jpeg bytes:", len(ps._jpeg or b""), (ps._jpeg or b"")[:2])
ps._running = False
