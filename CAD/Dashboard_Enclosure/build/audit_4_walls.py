"""Audit 4: thinnest material between faces, measured in SolidWorks (IModelDoc2.ClosestDistance).

For every pair of faces of a part that do not share an edge, the closest distance is measured. It counts as a wall
(material between the faces) only when the line between the two closest points leaves each face into the solid,
i.e. against or along each face's outward normal (planes and
cylinders only; other surfaces are skipped). Walls under LIMIT mm are listed, thinnest first, with the face types.
Usage: python audit_4_walls.py [limit_mm] part.SLDPRT ...   Nothing is saved.
"""
import os
import sys
import time
import types
import pythoncom
import win32com.client

sw = win32com.client.GetActiveObject("SldWorks.Application")
args = sys.argv[1:]
LIMIT = float(args.pop(0)) if args and args[0].replace(".", "").isdigit() else 2.0
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
if not args:
    args = [os.path.join(OUT, f) for f in ("SW7_Dash_Bracket.SLDPRT", "SW7_Dash_Clamp_Cap.SLDPRT")] + \
           [os.path.join(OUT, "print_parts", f) for f in sorted(os.listdir(os.path.join(OUT, "print_parts")))
            if f.endswith(".SLDPRT")]


def call0(obj, name):
    a = getattr(obj, name)
    return a() if isinstance(a, types.MethodType) else a


def closest(m, f1, f2):
    o = m._oleobj_
    return o.InvokeTypes(o.GetIDsOfNames("ClosestDistance"), 0, 1, (5, 0),
                         ((9, 1), (9, 1), (16396, 3), (16396, 3)), f1, f2, None, None)


def outward(face, p):
    """Outward normal (away from the material) at point p, for planes and cylinders; None otherwise."""
    s = call0(face, "GetSurface")
    if call0(s, "IsPlane"):
        return list(face.Normal)
    if call0(s, "IsCylinder"):
        c = call0(s, "CylinderParams")
        o, a = c[0:3], c[3:6]
        w = [p[k] - o[k] for k in range(3)]
        t = sum(w[k] * a[k] for k in range(3))
        r = [w[k] - t * a[k] for k in range(3)]
        n = sum(v * v for v in r) ** 0.5 or 1
        sg = -1 if face.FaceInSurfaceSense else 1      # SolidWorks cylinder normals point at the axis; checked
                                                       # against GetTessNorms on a hole and on a standoff
        return [sg * v / n for v in r]
    return None


def kind(face):
    s = call0(face, "GetSurface")
    if call0(s, "IsCylinder"):
        return f"cyl r{round(call0(s, 'CylinderParams')[6] * 1000, 2)}"
    if call0(s, "IsPlane"):
        n = [round(v, 2) for v in face.Normal]
        return f"plane n{n}"
    return "other"


for path in args:
    t0 = time.time()
    m = sw.OpenDoc(path, 1)
    try:
        faces = [f for b in (m.GetBodies2(0, False) or []) for f in (call0(b, "GetFaces") or [])]
        adj = {}
        for i, f in enumerate(faces):
            adj[i] = set()
            for e in call0(f, "GetEdges") or []:
                for g in e.GetTwoAdjacentFaces2 or []:
                    if g is not None:
                        adj[i].add(id(g))
        ids = {}
        for i, f in enumerate(faces):
            ids[i] = f
        walls = []
        for i in range(len(faces)):
            for j in range(i + 1, len(faces)):
                fi, fj = faces[i], faces[j]
                if any(fj.IsSame(g) if hasattr(fj, "IsSame") else False for g in []):
                    pass
                d, p1, p2 = closest(m, fi, fj)
                d *= 1000
                if d >= LIMIT or d < 1e-4:
                    continue
                v = [p2[k] - p1[k] for k in range(3)]
                n1, n2 = outward(fi, p1), outward(fj, p2)
                if n1 is None or n2 is None:
                    continue
                if sum(v[k] * n1[k] for k in range(3)) <= 1e-9 and sum(-v[k] * n2[k] for k in range(3)) <= 1e-9:
                    walls.append((round(d, 2), kind(fi), kind(fj), [round(x * 1000, 1) for x in p1],
                                  [round(x * 1000, 1) for x in p2]))
        walls.sort()
        print(f"\n== {os.path.basename(path)}: {len(faces)} faces, walls under {LIMIT} mm: {len(walls)}"
              f"  ({time.time() - t0:.0f} s)")
        seen = set()
        for w in walls:
            key = (w[0], w[1], w[2])
            if key in seen:
                continue
            seen.add(key)
            print(f"  {w[0]:5.2f} mm  {w[1]:24s} {w[2]:24s} at {w[3]} -> {w[4]}")
            if len(seen) >= 15:
                break
    finally:
        sw.CloseDoc(m.GetTitle)
