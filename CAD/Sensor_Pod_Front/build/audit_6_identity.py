"""Audit 6 (front pod): are the head parts and the rail plate the same as the original pod's (already printed)?

For each pair (front pod part, original part in CAD/Sensor_Pod/print_parts) it compares, from the saved files:
volume, surface area, centre of mass, principal moments, bounding box and face count. Same to 0.01 mm3 / 0.01 mm
means the same printed part; the original's G-code can be reused.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from swlib import sw, OPENED, PRINT, OUT, call0

ORIG = os.path.join(os.path.dirname(OUT), "Sensor_Pod", "print_parts")
PAIRS = [("SW7_FPod_Head_Upper", "SW7_Pod_Head_Upper"), ("SW7_FPod_Head_Tray", "SW7_Pod_Head_Tray"),
         ("SW7_FPod_Camera_Retainer", "SW7_Pod_Camera_Retainer"), ("SW7_FPod_Rail_Plate", "SW7_Pod_Rail_Plate")]


def props(path):
    m = sw.OpenDoc(path, 1)
    OPENED.append(m.GetTitle)
    mp = m.Extension.CreateMassProperty
    nf = sum(len(call0(b, "GetFaces") or []) for b in m.GetBodies2(0, False) or [])
    out = {"volume mm3": round(mp.Volume * 1e9, 2), "area mm2": round(mp.SurfaceArea * 1e6, 2),
           "centre mm": [round(v * 1000, 3) for v in mp.CenterOfMass],
           "box mm": [round(v * 1000, 3) for v in m.GetPartBox(True)], "faces": nf}
    sw.CloseDoc(m.GetTitle)
    return out


same_all = True
for new, old in PAIRS:
    a = props(os.path.join(PRINT, new + ".SLDPRT"))
    b = props(os.path.join(ORIG, old + ".SLDPRT"))
    same = all((abs(x - y) < 0.011 if not isinstance(x, list) else all(abs(p - q) < 0.011 for p, q in zip(x, y)))
               for x, y in zip(a.values(), b.values()))
    same_all &= same
    print(f"{new:28s} vs {old:26s} {'SAME' if same else 'DIFFERENT'}")
    for key in a:
        print(f"    {key:12s} {a[key]}   original {b[key]}")
print("ALL IDENTICAL" if same_all else "NOT ALL IDENTICAL")
