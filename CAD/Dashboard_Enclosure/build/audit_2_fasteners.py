"""Audit 2 (dashboard): does every bolt position have a hole of the right size in both parts it joins, coaxial?

Reads the cylindrical faces of the saved parts (not the build scripts), maps them into the assembly frame with each
component's own transform from SW7_Dash_Assembly.SLDASM, and then:
  - for every M3 hole in the back shell, lists which plates have a coaxial M3 hole (within 0.05 mm);
  - for every M3 hole in a plate or the cradle, checks the shell has one behind it;
  - checks the bracket's M5 insert holes against the cap's M5 clearance holes;
  - checks the cradle's Pi standoff pilots against the Raspberry Pi 5 hole pattern (58 x 49 mm);
  - measures the dovetail: normal gap between each rail flank and the channel flank parallel to it.
Nothing is saved.
"""
import math
import os
import types
import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
sw = win32com.client.GetActiveObject("SldWorks.Application")


def call0(obj, name):
    a = getattr(obj, name)
    return a() if isinstance(a, types.MethodType) else a


def xf_pt(t, p):
    r, s = t[:9], t[9:12]
    return tuple(p[0] * r[i] + p[1] * r[3 + i] + p[2] * r[6 + i] + s[i] for i in range(3))


def xf_vec(t, v):
    r = t[:9]
    return tuple(v[0] * r[i] + v[1] * r[3 + i] + v[2] * r[6 + i] for i in range(3))


asm = sw.OpenDoc(os.path.join(OUT, "SW7_Dash_Assembly.SLDASM"), 2)
title = asm.GetTitle
COMP = {}
for c in asm.GetComponents(True) or []:
    COMP[c.Name2] = (c.GetPathName, list(c.Transform2.ArrayData))
sw.CloseDoc(title)

part_cache = {}


def part_faces(path):
    """(holes, planes) in part metres: holes [(origin, axis, r)], planes [(normal, point)]."""
    if path in part_cache:
        return part_cache[path]
    m = sw.OpenDoc(path, 1)
    holes, planes = [], []
    for body in m.GetBodies2(0, False) or []:
        for f in call0(body, "GetFaces") or []:
            s = call0(f, "GetSurface")
            if call0(s, "IsCylinder"):
                p = call0(s, "CylinderParams")
                holes.append((tuple(p[0:3]), tuple(p[3:6]), p[6]))
            elif call0(s, "IsPlane"):
                p = call0(s, "PlaneParams")
                n = list(p[0:3])
                if f.FaceInSurfaceSense:
                    n = [-v for v in n]
                planes.append((tuple(n), tuple(p[3:6]), round(f.GetArea * 1e6, 1)))
    sw.CloseDoc(m.GetTitle)
    part_cache[path] = (holes, planes)
    return holes, planes


def holes_asm(name):
    path, t = COMP[name]
    out = []
    for o, a, r in part_faces(path)[0]:
        O = [v * 1000 for v in xf_pt(t, o)]
        A = xf_vec(t, a)
        ai = max(range(3), key=lambda i: abs(A[i]))
        if abs(abs(A[ai]) - 1) > 1e-6:
            continue
        uv = tuple(round(O[i], 2) for i in range(3) if i != ai)
        key = ("XYZ"[ai], uv, round(r * 1000, 2))
        if key not in out:
            out.append(key)
    return out


H = {n: holes_asm(n) for n in COMP}


def find(name, axis, uv, r_lo, r_hi):
    return [h for h in H[name] if h[0] == axis and math.dist(h[1], uv) < 0.05 and r_lo - 0.01 <= h[2] <= r_hi + 0.01]


SHELL = "SW7_Dash_Back_Shell-1"
PLATES = [n for n in COMP if any(k in n for k in ("Rail_Plate", "Joiner", "Cradle"))]
bad = 0
print("M3 holes in the back shell (axis Y, X Z in assembly mm) and what is bolted through each:")
for ax, uv, r in sorted(H[SHELL], key=lambda h: h[1]):
    if ax != "Y" or abs(r - 1.7) > 0.01:
        continue
    mates = [n for n in PLATES if find(n, "Y", uv, 1.7, 1.7)]
    print(f"  {str(uv):18s} -> {', '.join(mates) if mates else 'NOTHING'}")
    bad += not mates
print("\nM3 holes in each plate and the cradle, with the shell hole behind it:")
for n in PLATES:
    for ax, uv, r in sorted(H[n], key=lambda h: h[1]):
        if ax != "Y" or abs(r - 1.7) > 0.01:
            continue
        ok = bool(find(SHELL, "Y", uv, 1.7, 1.7))
        bad += not ok
        print(f"  {n:28s} {str(uv):18s} {'OK' if ok else 'NO SHELL HOLE'}")
print("\nM5 clamp bolts (bracket insert r 3.2 / cap clearance r 2.75):")
for ax, uv, r in H["SW7_Dash_Bracket-1"]:
    if abs(r - 3.2) > 0.01:
        continue
    cap = find("SW7_Dash_Clamp_Cap-1", ax, uv, 2.75, 2.75)
    bad += not cap
    print(f"  {ax} {uv}  cap: {'OK' if cap else 'MISSING'}")
print("\nCradle standoff pilots (r 1.1), Pi 5 pattern should be 49 x 58 mm:")
pil = sorted(h[1] for h in H["SW7_Dash_Pi5_Cradle-1"] if abs(h[2] - 1.1) < 0.01)
print("  ", pil)
xs, zs = sorted({p[0] for p in pil}), sorted({p[1] for p in pil})
print(f"   spacing X {round(xs[-1] - xs[0], 2)}  Z {round(zs[-1] - zs[0], 2)}")
_, tpi = COMP["REF_Pi5_with_cooler-1"]
print("   reference Pi board placed at X -126..-70; its holes would be 3.5 mm in from the non-USB end and the long"
      " edges; standoff Z range vs reference Pi board Z range shows whether the reference is on the standoffs.")
print("\nOther cylinders in the bracket and cap (assembly frame):")
for n in ("SW7_Dash_Bracket-1", "SW7_Dash_Clamp_Cap-1"):
    for h in H[n]:
        print(f"  {n:24s} {h}")

print("\nDovetail flanks (inclined planes), normal gap between the rail flank and the parallel channel flank:")


def planes_asm(name):
    path, t = COMP[name]
    out = []
    for n, p, area in part_faces(path)[1]:
        N = xf_vec(t, n)
        if max(abs(v) for v in N) > 0.999:
            continue
        out.append((N, [v * 1000 for v in xf_pt(t, p)], area))
    return out


rail = planes_asm("SW7_Dash_Rail_Plate-1")
chan = planes_asm("SW7_Dash_Bracket-1")
for N, P, a in rail:
    for N2, P2, a2 in chan:
        if sum(x * y for x, y in zip(N, N2)) < -0.999:          # facing each other
            gap = sum((P2[i] - P[i]) * N[i] for i in range(3))
            ang = math.degrees(math.acos(min(1, abs(N[1]))))
            print(f"  rail normal {tuple(round(v, 3) for v in N)} area {a}  channel area {a2}  normal gap {gap:.3f} mm"
                  f"  (flank normal {ang:.1f} deg from the plate normal)")
print(f"\n{'ALL BOLT POSITIONS HAVE MATCHING HOLES' if bad == 0 else f'{bad} BOLT POSITIONS WITHOUT A MATCHING HOLE'}")
