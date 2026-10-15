"""Audit 2 (front pod): does every fastener have a matching hole in both parts it joins, on the same axis?

Reads the cylindrical faces of the saved parts (not params.py), so a script mistake shows up. For each joint it
looks, at every intended screw position, for a hole of the right size in each part, coaxial within 0.05 mm.
All parts are modelled in the pod frame, so no transforms are needed.
"""
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import *          # noqa: F401,F403
from swlib import sw, OPENED, PRINT, OUT, call0

DASH = os.path.join(os.path.dirname(OUT), "Dashboard_Enclosure")
POD = {n: os.path.join(PRINT, f"SW7_FPod_{n}.SLDPRT") for n in
       ("Head_Upper", "Head_Tray", "Camera_Retainer", "Box_Base", "Box_Lid", "Sunshade", "Rear_Port_Cover",
        "Side_Port_Cover", "Rail_Plate")}
# The original pod's printed rail plate, to show it bolts to this box unchanged.
POD["Original_Rail_Plate"] = os.path.join(os.path.dirname(OUT), "Sensor_Pod", "print_parts", "SW7_Pod_Rail_Plate.SLDPRT")
AX = {"X": 0, "Y": 1, "Z": 2}


def holes(path):
    """[(axis, (u, v) perpendicular coords in pod mm, radius mm, (lo, hi) extent along the axis)]."""
    m = sw.OpenDoc(path, 1)
    OPENED.append(m.GetTitle)
    out = []
    for body in m.GetBodies2(0, False) or []:
        for f in call0(body, "GetFaces") or []:
            s = call0(f, "GetSurface")
            if not call0(s, "IsCylinder"):
                continue
            p = call0(s, "CylinderParams")       # origin xyz, axis xyz, radius (model metres)
            o = (p[0] * 1000, -p[2] * 1000, p[1] * 1000)          # model -> pod
            a = (p[3], -p[5], p[4])
            ai = max(range(3), key=lambda i: abs(a[i]))
            if abs(abs(a[ai]) - 1) > 1e-6:
                continue
            axis = "XYZ"[ai]
            uv = tuple(round(o[i], 2) for i in range(3) if i != ai)
            box = call0(f, "GetBox")             # x0 y0 z0 x1 y1 z1 (model)
            lo_m, hi_m = box[:3], box[3:]
            lo = (lo_m[0] * 1000, -hi_m[2] * 1000, lo_m[1] * 1000)
            hi = (hi_m[0] * 1000, -lo_m[2] * 1000, hi_m[1] * 1000)
            out.append((axis, uv, round(p[6] * 1000, 2), (round(lo[ai], 1), round(hi[ai], 1))))
    sw.CloseDoc(m.GetTitle)
    return out


H = {n: holes(p) for n, p in POD.items()}
H["Dash_Bracket"] = holes(os.path.join(DASH, "SW7_Dash_Bracket.SLDPRT"))


def find(part, axis, uv, r_lo, r_hi):
    for a, q, r, ext in H[part]:
        if a == axis and math.dist(q, uv) < 0.05 and r_lo - 0.01 <= r <= r_hi + 0.01:
            return r, ext
    return None


def check(name, axis, points, a_part, a_r, b_part, b_r):
    """points in the plane perpendicular to the axis, in pod coordinates order (X,Y,Z minus the axis)."""
    print(f"\n{name}  ({a_part} r {a_r} / {b_part} r {b_r}, axis {axis})")
    bad = 0
    for uv in points:
        ha, hb = find(a_part, axis, uv, *a_r), find(b_part, axis, uv, *b_r)
        ok = ha is not None and hb is not None
        bad += not ok
        print(f"  {str(tuple(round(v, 1) for v in uv)):18s} {a_part}: {ha}   {b_part}: {hb}   {'OK' if ok else 'MISSING'}")
    return bad


ins = (INSERT_M3_D / 2, INSERT_M3_D / 2)
clr = (M3_CLEAR / 2, M3_CLEAR / 2)
bad = 0
up = [(x, z) for x, z in FLANGE_BOLTS if z > HEAD_SPLIT_Z]
low = [(x, z) for x, z in FLANGE_BOLTS if z < HEAD_SPLIT_Z]
bad += check("Flange, head upper to box", "Y", up, "Head_Upper", ins, "Box_Base", clr)
bad += check("Flange, tray to box", "Y", low, "Head_Tray", ins, "Box_Base", clr)
bad += check("Head seam screws", "X", [(y, z) for _, y, z in SEAM_SCREWS], "Head_Upper", ins, "Head_Tray", clr)
bad += check("Lid screws", "Z", LID_SCREWS, "Box_Lid", clr, "Box_Base", ins)
bad += check("Rear port cover screws", "Y", REAR_BOSSES, "Rear_Port_Cover", clr, "Box_Base", ins)
bad += check("Side port cover screws", "X", SIDE_BOSSES, "Side_Port_Cover", clr, "Box_Base", ins)
bad += check("Rail plate bolts", "Z", RAIL_BOLTS, "Rail_Plate", clr, "Box_Base", ins)
bad += check("Original pod rail plate on this box", "Z", RAIL_BOLTS, "Original_Rail_Plate", clr, "Box_Base", ins)
bad += check("Camera retainer screws", "Z", RETAINER_SCREWS, "Camera_Retainer", (1.2, 1.2), "Head_Upper",
             (M2_PILOT / 2, M2_PILOT / 2))
bad += check("Sunshade posts", "Z", SUNSHADE_POSTS, "Box_Lid", clr, "Sunshade", (1.25, 1.25))
print(f"\nboard-mounting pilots (estimated positions; the other side is the real board):")
for name, part, pts, r in (("Sensor board", "Head_Tray", BOARD_HOLES, BOARD_HOLE_PILOT / 2),
                           ("Pi 5 (M2.5 clearance from below)", "Box_Base", PI_HOLES, M25_CLEAR / 2)):
    for uv in pts:
        h = find(part, "Z", uv, r, r)
        bad += h is None
        print(f"  {name:12s} {str(uv):18s} {h if h else 'MISSING'}")
print(f"\n{'ALL FASTENER HOLES MATCH' if bad == 0 else f'{bad} FASTENER POSITIONS MISSING A HOLE'}")
