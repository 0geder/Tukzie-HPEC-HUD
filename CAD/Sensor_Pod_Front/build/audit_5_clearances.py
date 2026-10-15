"""Audit 5 (front pod): clearances round the Pi 5, its cooler and the cables, tool access, and cable bends.

1. Minimum distance (IModelDoc2.ClosestDistance, in the assembly) between each stand-in body of the Pi 5 + cooler
   and the cables, and the box base, lid, port covers and rail plate.
2. Fan intake: height from the top of the cooler's fan block to the lid's underside and to the ribbon above it.
3. Tool access: the 2.5 mm hex key stand-ins on the two lower flange bolts are added with the lid, sunshade and
   cables suppressed (the jumpers and ribbon are unplugged before the head comes off); every hard interference
   involving a key is listed. None means the head can come off with the Pi in place.
4. Cable bends: radius of every bend in the ribbon path (circumradius of consecutive path points) and the jumper
   hairpin; ribbon length against the 200 mm Pi 5 camera cable.
Nothing is saved; the key part is removed again.
"""
import math
import os
import sys
import pythoncom
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import *          # noqa: F401,F403
from swlib import sw, OPENED, OUT, invoke, arr, NONE, call0

mm = 0.001
ASM = os.path.join(OUT, "SW7_Front_Sensor_Pod_Assembly.SLDASM")
KEYS = os.path.join(OUT, "reference_tools", "TOOL_FPod_Hex_Keys.SLDPRT")
asm = sw.OpenDoc(ASM, 2)
if asm is None:
    raise SystemExit("could not open " + ASM)
OPENED.append(asm.GetTitle)
sw.ActivateDoc(asm.GetTitle)
asm = sw.ActiveDoc


def comp(key):
    for c in asm.GetComponents(True):
        if key in c.Name2:
            return c
    raise SystemExit("no component " + key)


def closest(a, b):
    o = asm._oleobj_
    return o.InvokeTypes(o.GetIDsOfNames("ClosestDistance"), 0, 1, (5, 0),
                         ((9, 1), (9, 1), (16396, 3), (16396, 3)), a, b, None, None)


def bodies(c):
    """(name, body) of every solid body of a component, in the assembly's context."""
    out = []
    for bd in c.GetBodies2(0) or []:
        out.append((bd.Name, bd))
    return out


def dist_bodies(c1, c2):
    res = []
    for n1, b1 in bodies(c1):
        best = (9e9, None, None, None)
        for n2, b2 in bodies(c2):
            try:
                d, p1, p2 = closest(b1, b2)
            except Exception as e:
                print("   closest failed", n1, n2, e)
                continue
            if d * 1000 < best[0]:
                best = (d * 1000, n2, p1, p2)
        res.append((n1, best))
    return res


def pod(p):
    return tuple(round(v, 1) for v in (p[0] / mm, -p[2] / mm, p[1] / mm))


print("1. clearances (mm), pod frame points")
pi, cab = comp("Pi5_with_Cooler"), comp("FPod_Cables")
targets = ["FPod_Box_Base", "FPod_Box_Lid", "FPod_Rear_Port_Cover", "FPod_Side_Port_Cover", "FPod_Rail_Plate"]
for src in (pi, cab):
    for tname in targets:
        t = comp(tname)
        for n1, (d, n2, p1, p2) in dist_bodies(src, t):
            if d < 9e8:
                flag = "  CONTACT" if d < 0.05 else ""
                print(f"  {src.Name2:28s} {n1:22s} -> {tname:22s} {d:6.2f}  at {pod(p1)} -> {pod(p2)}{flag}")
print("\n1b. per feature of the Pi 5 stack (the stack is one body, whose minimum is the intended standoff contact)")


def feat_dist(c, feat, targets):
    """Minimum distance from the faces of feature `feat` of component c to any body of the target components
    (or to (component, body-name prefix) pairs)."""
    best = (9e9, None, None)
    for f in c.FeatureByName(feat).GetFaces or []:
        for t in targets:
            tc, prefix = t if isinstance(t, tuple) else (t, "")
            for n, bd in bodies(tc):
                if not n.startswith(prefix):
                    continue
                d, p1, p2 = closest(f, bd)
                if d / mm < best[0]:
                    best = (d / mm, f"{tc.Name2}:{n}", pod(p1))
    return best


base, lid = comp("FPod_Box_Base"), comp("FPod_Box_Lid")
covers = [comp("FPod_Rear_Port_Cover"), comp("FPod_Side_Port_Cover")]
for feat, targets in (("Underside Parts 1", [base]), ("Underside Parts 2", [base]), ("Underside Parts 3", [base]),
                      ("microSD Card", [base]), ("Cooler Fins", [base]), ("Ethernet", [base] + covers),
                      ("USB-A Stacks", [base] + covers), ("Micro-HDMI", [base] + covers), ("USB-C", [base] + covers),
                      ("AI HAT+ PCB", [base, lid]), ("Hailo And Heatsink", [base, lid]),
                      ("Stacking Pins", [lid, (cab, "Ribbon")]), ("Dupont Housings", [lid, (cab, "Ribbon")]),
                      ("AI HAT+ PCB", [(cab, "Ribbon")]), ("PCIe Flat Cable Loop", [base])):
    d, who, at = feat_dist(pi, feat, targets)
    print(f"  {feat:22s} -> {who:45s} {d:6.2f} mm  at {at}")
print("\n  cables -> Pi 5 (plugs are meant to touch their ports):")
for n1, (d, n2, p1, p2) in dist_bodies(cab, pi):
    print(f"  {n1:22s} {d:6.2f}  at {pod(p1)}")

print("\n2. air gaps in the stack (horizontal top face of a stand-in feature, model Y = pod Z)")


def top_face(c, feat):
    best = None
    for f in c.FeatureByName(feat).GetFaces or []:
        b = f.GetBox
        if abs(b[1] - b[4]) < 1e-7 and (best is None or b[4] > best[1][4]):
            best = (f, b)
    return best


lid = comp("FPod_Box_Lid")
tf = top_face(pi, "Cooler Fan")
zb = min(f.GetBox[1] for f in pi.FeatureByName("AI HAT+ PCB").GetFaces) / mm
print(f"  cooler fan top Z {tf[1][4] / mm:.2f}, HAT underside Z {zb:.2f}: gap {zb - tf[1][4] / mm:.2f} mm "
      f"(set by the official 16 mm spacers; the fan draws from the sides between the Pi and the HAT)")
for feat, need in (("Hailo And Heatsink", HAILO_AIR_GAP_MIN), ("Dupont Housings", None)):
    tf = top_face(pi, feat)
    d_ = min(closest(tf[0], bd)[0] for _, bd in bodies(lid)) / mm
    print(f"  {feat} top Z {tf[1][4] / mm:.2f} to the lid {d_:.2f} mm" + (f" (required {need})" if need else ""))
print("  jumper hairpin and ribbon to the lid: see section 1 (FPod_Cables -> FPod_Box_Lid)")

print("\n3. hex key access to the lower flange bolts, Pi 5 fitted")
hidden = []
for c in asm.GetComponents(True):
    if any(k in c.Name2 for k in ("Box_Lid", "Sunshade", "FPod_Cables", "View_Cones")):
        c.SetSuppression2(0)
        hidden.append(c)
d = sw.OpenDoc(KEYS, 1)
sw.ActivateDoc(asm.GetTitle)
k = asm.AddComponent5(KEYS, 0, "", False, "", 0, 0, 0)
mu = sw.GetMathUtility
xf = invoke(mu, "CreateTransform", pythoncom.DISPATCH_METHOD, arr([1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]))
co = k._oleobj_
co.Invoke(co.GetIDsOfNames("Transform2"), 0, pythoncom.DISPATCH_PROPERTYPUT, False, xf)
call0(asm, "EditRebuild3")
idm = asm.InterferenceDetectionManager
idm.TreatCoincidenceAsInterference = False
idm.IncludeMultibodyPartInterferences = False
hits = []
for it in idm.GetInterferences or []:
    names = [x.Name2 for x in it.Components]
    if any(k.Name2 == n for n in names):
        hits.append((names, round(it.Volume * 1e9, 2)))
idm.Done()
print(f"  interferences involving the keys: {len(hits)}")
for h in hits:
    print("   ", h)
for n1, (dd, n2, p1, p2) in dist_bodies(k, pi):
    print(f"  {n1:22s} -> Pi 5 + cooler {dd:6.2f} mm at {pod(p1)} -> {pod(p2)}")
asm.ClearSelection2(True)
k.Select4(False, NONE, False)
call0(asm, "EditDelete")
for c in hidden:
    c.SetSuppression2(2)
call0(asm, "EditRebuild3")
if d is not None:
    sw.CloseDoc(d.GetTitle)

print("\n4. cable bends")
pts, bends = ribbon_box_path()


def circ(a, b, c):
    A, B, C = math.dist(b, c), math.dist(a, c), math.dist(a, b)
    s = (A + B + C) / 2
    area = math.sqrt(max(s * (s - A) * (s - B) * (s - C), 0))
    return math.inf if area < 1e-9 else A * B * C / (4 * area)


radii = [circ(*pts[i:i + 3]) for i in range(len(pts) - 2)]
finite = [r for r in radii if r < 1e6]
print(f"  ribbon path bends: minimum radius {min(finite):.2f} mm (required {BEND_R}), "
      f"radii {sorted(set(round(r, 1) for r in finite))}")
print("  plus one 45 deg crease fold at the turn towards the connector (see the review)")
head, box = ribbon_total_length()
print(f"  ribbon length: camera to window {head:.1f} + window to connector {box:.1f} = {head + box:.1f} mm; "
      f"cable {RIBBON_SPEC_LEN:.0f} mm leaves {RIBBON_SPEC_LEN - head - box:.1f} mm slack")
print(f"  jumper hairpin over the board edge: centreline radius {BEND_R} mm (stand-in 4 to 6 mm)")
sw.CloseDoc(asm.GetTitle)
