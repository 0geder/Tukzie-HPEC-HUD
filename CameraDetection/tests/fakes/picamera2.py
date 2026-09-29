import numpy as np, time
class _Req:
    def __init__(self):
        self.ts = time.monotonic_ns() - 40_000_000   # frame read out 40 ms ago
    def make_array(self, name): return np.zeros((480, 640, 3), dtype=np.uint8)
    def get_metadata(self): return {"SensorTimestamp": self.ts}
    def release(self): pass
class Picamera2:
    def create_preview_configuration(self, main): return main
    def configure(self, c): pass
    def start(self): pass
    def stop(self): print("CAMERA STOPPED")
    def capture_request(self): time.sleep(0.02); return _Req()
