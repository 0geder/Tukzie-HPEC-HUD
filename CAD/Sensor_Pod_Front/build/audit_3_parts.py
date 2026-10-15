"""Audit 3 (front pod, copied from the dashboard audit): per-part checks on the saved files.

For each part: solid body count and IBody2.Check3 fault count, bounding box against the Prusa Mini 180 mm cube,
volume, the M3/M5 holes it carries (part frame), each sketch's constrained status and how many dimensions it has,
and the downward-facing planar area for the print orientation given in PRINT_UP (faces steeper than 45 deg from
vertical that are not on the bed need a bridge or support). Nothing is saved.
Usage: python audit_3_parts.py [part paths...]   (default: every front pod part)
"""
import os
import sys
import types
import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
PP = os.path.join(OUT, "print_parts")
sw = win32com.client.GetActiveObject("SldWorks.Application")
STATUS = {1: "unknown", 2: "under defined", 3: "fully defined", 4: "over defined", 5: "no solution",
          6: "invalid", 7: "autosolve off"}
# Print orientation for each part: the model axis (and sign) that points up on the printer.
PRINT_UP = {      # model axis pointing up on the printer (model Y = pod up); the chosen orientations, see
    #   Desktop/Fourth Year/EEE4022S/3D Prints/front_pod/orientation_scores.txt
    "SW7_FPod_Box_Base": (0, 1, 0),          # floor on the bed
    "SW7_FPod_Box_Lid": (0, -1, 0),          # outer face on the bed
    "SW7_FPod_Rear_Port_Cover": (0, 0, 1),   # outer face on the bed (the plate's normal is pod Y = model -Z)
    "SW7_FPod_Side_Port_Cover": (-1, 0, 0),  # outer face on the bed
    "SW7_FPod_Sunshade": (0, -1, 0),         # top plate on the bed, posts up
    "SW7_FPod_Rail_Plate": (0, -1, 0),       # plate on the bed, rail up
    "SW7_FPod_Head_Upper": (0, -1, 0),       # roof on the bed (as printed for the original, 14 Oct)
    "SW7_FPod_Head_Tray": (0, 1, 0),         # floor on the bed
    "SW7_FPod_Camera_Retainer": (0, 1, 0),
}


def call0(obj, name):
    a = getattr(obj, name)
    return a() if isinstance(a, types.MethodType) else a


def audit(path):
    m = sw.OpenDoc(path, 1)
    if m is None:
        print("could not open", path)
        return None
    name = os.path.splitext(os.path.basename(path))[0]
    up = next((v for k, v in PRINT_UP.items() if name.startswith(k)), (0, 1, 0))
    bodies = list(m.GetBodies2(0, False) or [])
    faults = []
    for b in bodies:
        try:
            faults.append(b.Check3.Count)
        except Exception as e:
            faults.append(f"Check3 failed: {e}")
    box = [v * 1000 for v in m.GetPartBox(True)]
    size = [round(box[i + 3] - box[i], 2) for i in range(3)]
    vol = round(m.Extension.CreateMassProperty.Volume * 1e9)
    fits = all(s <= 180 for s in size)
    print(f"\n== {name}\n  bodies {len(bodies)}  Check3 faults {faults}  box {[round(v, 2) for v in box]}\n"
          f"  size {size} mm  fits 180 cube: {fits}  volume {vol} mm3")
    holes = set()
    down_area, down_faces = 0.0, []
    lo_up = min(box[i] * up[i] + box[i + 3] * up[i] if up[i] else 1e9 for i in range(3)) if False else None
    bed = min(box[i] if up[i] > 0 else -box[i + 3] for i in range(3) if up[i]) if any(up) else 0
    for b in bodies:
        for f in call0(b, "GetFaces") or []:
            s = call0(f, "GetSurface")
            if call0(s, "IsCylinder"):
                p = call0(s, "CylinderParams")
                a = p[3:6]
                ai = max(range(3), key=lambda i: abs(a[i]))
                uv = tuple(round(p[i] * 1000, 2) for i in range(3) if i != ai)
                holes.add(("XYZ"[ai], uv, round(p[6] * 1000, 2)))
            elif call0(s, "IsPlane"):
                n = list(f.Normal)
                d = sum(n[i] * up[i] for i in range(3))
                if d < -0.707:
                    fb = [v * 1000 for v in f.GetBox]
                    hgt = min(fb[i] * up[i] if up[i] > 0 else -fb[i + 3] for i in range(3) if up[i])
                    if hgt - bed > 0.05:
                        a = f.GetArea * 1e6
                        down_area += a
                        down_faces.append((round(a, 1), round(hgt - bed, 2), [round(v, 1) for v in fb]))
    print(f"  holes (axis, centre in model mm, radius): {len(holes)}")
    for h in sorted(holes):
        print("    ", h)
    print(f"  print up = model {up}; downward faces above the bed (bridge or support): {len(down_faces)}, "
          f"{round(down_area)} mm2")
    for d in sorted(down_faces, reverse=True)[:8]:
        print("     area", d[0], "height above bed", d[1], "face box", d[2])
    f = m.FirstFeature
    sk = []
    while f is not None:
        if f.GetTypeName2 == "ProfileFeature":
            s = f.GetSpecificFeature2
            ndim = 0
            dd = f.GetFirstDisplayDimension
            while dd is not None:
                ndim += 1
                dd = f.GetNextDisplayDimension(dd)
            segs = len(s.GetSketchSegments or [])
            sk.append((f.Name, STATUS.get(s.GetConstrainedStatus, s.GetConstrainedStatus), segs, ndim))
        f = f.GetNextFeature
    print(f"  sketches (name, status, segments, dimensions): {sk}")
    sw.CloseDoc(m.GetTitle)
    return holes


paths = sys.argv[1:] or [os.path.join(PP, f) for f in sorted(os.listdir(PP)) if f.endswith(".SLDPRT")
                         and not f.startswith("~$")]
H = {os.path.basename(p): audit(p) for p in paths}
