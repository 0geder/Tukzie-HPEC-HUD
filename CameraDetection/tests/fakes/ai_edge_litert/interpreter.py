import numpy as np, os
# Script: per frame, list of (class_id, score, box). Person (class 0) present
# throughout with single-frame dropouts, walks nearer (box widens) at frame 60,
# leaves at frame 90. A one-frame far person and a one-frame near person
# at frame 20 checks nearest-band-wins.
def script(n):
    near = (0.1, 0.35, 0.9, 0.65)   # ~192 px wide -> ~1.6 m -> immediate
    far  = (0.4, 0.45, 0.6, 0.52)   # ~45 px wide  -> ~6.7 m -> warning
    if n >= 90: return []
    if n in (7, 15, 33, 41, 50, 71): return []           # single missed frames
    if n == 20: return [(0, 0.9, far), (0, 0.55, near)]  # far confident + near weak
    if n < 60: return [(0, 0.6, far)]
    return [(0, 0.6, near)]
class Interpreter:
    def __init__(self, model_path, num_threads=None): self.n = -1
    def allocate_tensors(self): pass
    def get_input_details(self): return [{'index': 0, 'shape': [1, 300, 300, 3], 'dtype': np.uint8}]
    def get_output_details(self): return [{'index': i} for i in range(4)]
    def set_tensor(self, i, d): pass
    def invoke(self): self.n += 1
    def get_tensor(self, i):
        dets = script(self.n)
        boxes = np.zeros((1, 10, 4), np.float32); cls = np.zeros((1, 10), np.float32); sc = np.zeros((1, 10), np.float32)
        for k, (c, s, b) in enumerate(dets):
            boxes[0, k] = b; cls[0, k] = c; sc[0, k] = s
        return [boxes, cls, sc, np.array([len(dets)], np.float32)][i]
