"""Debug helper: python views.py <part path> <prefix> [views...] -> scratch PNGs of named views."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swlib
from swlib import sw, OPENED
path, prefix = os.path.abspath(sys.argv[1]), sys.argv[2]
views = sys.argv[3:] or ["*Back", "*Right", "front_iso", "*Bottom"]
m = sw.OpenDoc(path, 2 if path.lower().endswith(".sldasm") else 1)
OPENED.append(m.GetTitle)
swlib.PREV = os.environ.get("SHOTS", swlib.PREV)
for v in views:
    swlib.snap(m, f"{prefix}_{v.strip('*').lower()}.png", v, 1000, 700)
