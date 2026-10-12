"""Audit of the IMU pod (base and lid), on the saved parts. Nothing is saved.

1. Per part: solid body count, IBody2.Check3 fault count, bounding box against the Prusa Mini 180 mm cube, every
   cylindrical face (holes), the board pocket size and depth, and each sketch's constrained status and dimensions.
2. Lid screws: each lid clearance hole must be coaxial (0.05 mm) with a base pilot hole.
3. A temporary assembly (not saved) with the lid on the base: interference detection, a probe (a second lid
   pushed 1 mm into the base) to prove the check reports overlaps, then contacts with touching counted.
Thin walls are measured separately with ../../Dashboard_Enclosure/build/audit_4_walls.py on these two files.
"""
import math
import os
import types
import pythoncom
import win32com.client
from win32com.client import VARIANT

NONE = VARIANT(pythoncom.VT_DISPATCH, None)
mm = 0.001
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
BASE = os.path.join(OUT, "SW7_IMU_Pod_Base.SLDPRT")
LID = os.path.join(OUT, "SW7_IMU_Pod_Lid.SLDPRT")
STATUS = {1: "unknown", 2: "under defined", 3: "fully defined", 4: "over defined", 5: "no solution"}
sw = win32com.client.GetActiveObject("SldWorks.Application")


def call0(obj, name):
    a = getattr(obj, name)
    return a() if isinstance(a, types.MethodType) else a


def audit(path):
    m = sw.OpenDoc(path, 1)
    try:
        bodies = list(m.GetBodies2(0, False) or [])
        box = [round(v * 1000, 2) for v in m.GetPartBox(True)]
        size = [round(box[i + 3] - box[i], 2) for i in range(3)]
        print(f"\n== {os.path.basename(path)}\n  bodies {len(bodies)}  Check3 faults {[b.Check3.Count for b in bodies]}"
              f"  box {box}  size {size}  fits 180 cube {all(s <= 180 for s in size)}"
              f"  volume {round(m.Extension.CreateMassProperty.Volume * 1e9)} mm3")
        holes, planes = [], []
        for b in bodies:
            for f in call0(b, "GetFaces") or []:
                s = call0(f, "GetSurface")
                fb = [round(v * 1000, 2) for v in f.GetBox]
                if call0(s, "IsCylinder"):
                    p = call0(s, "CylinderParams")
                    holes.append((round(p[0] * 1000, 2), round(p[2] * 1000, 2), round(p[6] * 1000, 2),
                                  (fb[1], fb[4])))
                elif call0(s, "IsPlane"):
                    planes.append(([round(v, 2) for v in f.Normal], fb, round(f.GetArea * 1e6, 1)))
        print("  cylinders (x, z, radius, y range):")
        for h in sorted(holes):
            print("    ", h)
        up = [p for p in planes if p[0] == [0.0, 1.0, 0.0] or p[0] == [-0.0, 1.0, -0.0]]
        print("  upward planar faces (y, x range, z range, area):")
        for n, fb, a in sorted(up, key=lambda q: q[1][1]):
            print(f"     y {fb[1]:6.2f}  x {fb[0]}..{fb[3]}  z {fb[2]}..{fb[5]}  area {a}")
        f = m.FirstFeature
        sk = []
        while f is not None:
            if f.GetTypeName2 == "ProfileFeature":
                s = f.GetSpecificFeature2
                n = 0
                dd = f.GetFirstDisplayDimension
                while dd is not None:
                    n += 1
                    dd = f.GetNextDisplayDimension(dd)
                sk.append((f.Name, STATUS.get(s.GetConstrainedStatus, s.GetConstrainedStatus),
                           len(s.GetSketchSegments or []), n))
            f = f.GetNextFeature
        print("  sketches (name, status, segments, dimensions):", sk)
        eq = m.GetEquationMgr
        print("  equations:", [eq.Equation(i) for i in range(eq.GetCount)])
        return holes, box
    finally:
        sw.CloseDoc(m.GetTitle)


hb, bbox = audit(BASE)
hl, lbox = audit(LID)
print("\nLid screws (lid clearance r 1.45 over base pilot r 1.1, coaxial within 0.05 mm):")
bad = 0
for x, z, r, _ in hl:
    if abs(r - 1.45) > 0.01:
        continue
    ok = [h for h in hb if math.dist((h[0], h[1]), (x, z)) < 0.05 and abs(h[2] - 1.1) < 0.01]
    bad += not ok
    print(f"  ({x}, {z})  base: {ok[0] if ok else 'MISSING'}")
print("  all lid screws matched" if bad == 0 else f"  {bad} lid screws without a base hole")

# Temporary assembly: base at the origin, lid on top (its Y 0 face on the base's top face at Y = base height).
asm = sw.NewDocument(sw.GetUserPreferenceStringValue(9), 0, 0, 0)
title = asm.GetTitle
opened = []
mo = sw.GetMathUtility._oleobj_


def place(path, y):
    d = sw.OpenDoc(path, 1)
    if d is not None:
        opened.append(d.GetTitle)
    sw.ActivateDoc(title)
    c = asm.AddComponent5(path, 0, "", False, "", 0, 0, 0)
    xf = mo.Invoke(mo.GetIDsOfNames("CreateTransform"), 0, pythoncom.DISPATCH_METHOD, True,
                   VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [1.0, 0, 0, 0, 1, 0, 0, 0, 1, 0, y * mm, 0, 1, 0, 0, 0]))
    co = c._oleobj_
    co.Invoke(co.GetIDsOfNames("Transform2"), 0, pythoncom.DISPATCH_PROPERTYPUT, False, xf)
    return c


def interferences(touch):
    idm = asm.InterferenceDetectionManager
    idm.TreatCoincidenceAsInterference = touch
    found = idm.GetInterferences or []
    out = [(sorted(x.Name2 for x in it.Components), round(it.Volume * 1e9, 2)) for it in found]
    idm.Done()
    return out


try:
    top = bbox[4]
    cb = place(BASE, 0)
    cl = place(LID, top)
    asm.EditRebuild3
    print(f"\ntemporary assembly: lid placed at Y {top}")
    print("  hard interferences:", interferences(False))
    probe = place(LID, top - 1.0)
    asm.EditRebuild3
    hits = [h for h in interferences(False) if probe.Name2 in h[0]]
    print("  probe (second lid 1 mm into the base):", "DETECTED" if hits else "NOT DETECTED", hits)
    asm.ClearSelection2(True)
    probe.Select4(False, NONE, False)
    asm.Extension.DeleteSelection2(0)
    asm.EditRebuild3
    print("  contacts with touching counted:", interferences(True))
finally:
    sw.CloseDoc(title)
    for t in opened:
        sw.CloseDoc(t)
