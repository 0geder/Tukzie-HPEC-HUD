"""Audit 1 (dashboard): components, placements, interference with a probe proof, and the contact graph.

1. Opens SW7_Dash_Assembly.SLDASM, lists every component with fixed state, transform and assembly-frame box.
2. Interference detection with touching faces not counted, every overlap with its volume.
3. Probe: adds a copy of the cross joiner shifted 2 mm into the shell's back plate (Y + 2 mm) and checks it is
   reported, so an empty result in step 2 can be trusted.
4. Interference detection with touching counted (TreatCoincidenceAsInterference): the contact graph. A printed part
   touching nothing is floating.
Suppressed components are resolved for the audit. Nothing is saved; the probe copy is deleted and the assembly is closed without saving.
"""
import os
import sys
import pythoncom
import win32com.client
from win32com.client import VARIANT

NONE = VARIANT(pythoncom.VT_DISPATCH, None)
mm = 0.001
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
sw = win32com.client.GetActiveObject("SldWorks.Application")
ASM = os.path.join(OUT, "SW7_Dash_Assembly.SLDASM")
asm = sw.OpenDoc(ASM, 2)
if asm is None:
    raise SystemExit("could not open " + ASM)
title = asm.GetTitle
opened = [title]


def comps():
    return list(asm.GetComponents(True) or [])


print("components (assembly frame, mm):")
for c in comps():
    t = c.Transform2.ArrayData
    b = c.GetBox(False, False)
    box = [round(v * 1000, 1) for v in b] if b else None
    rot = [round(v) for v in t[:9]]
    print(f"  {c.Name2:38s} fixed={c.IsFixed} supp={c.IsSuppressed} rot={rot} "
          f"t=({t[9]*1000:.1f},{t[10]*1000:.1f},{t[11]*1000:.1f}) box={box}")
    print(f"      file: {c.GetPathName}")
suppressed = [c for c in comps() if c.IsSuppressed]
print("suppressed in the saved assembly:", [c.Name2 for c in suppressed])
for c in suppressed:                       # resolved for this audit only; the assembly is not saved
    print("  unsuppress", c.Name2, "->", c.SetSuppression2(2))
asm.EditRebuild3
for c in suppressed:
    b = c.GetBox(False, False)
    print("  ", c.Name2, "box now", [round(v * 1000, 1) for v in b] if b else None)
mates = [f for f in (asm.FeatureManager.GetFeatures(True) or []) if f.GetTypeName2 == "MateCoincident"]
print("mates:", len(mates))


def interferences(touch):
    idm = asm.InterferenceDetectionManager
    idm.TreatCoincidenceAsInterference = touch
    idm.IncludeMultibodyPartInterferences = False
    idm.TreatSubAssembliesAsComponents = False
    found = idm.GetInterferences or []
    out = []
    for it in found:
        names = sorted(x.Name2 for x in it.Components)
        out.append((names, round(it.Volume * 1e9, 2)))
    idm.Done()
    return out


hard = interferences(False)
print(f"\nhard interferences (touching not counted): {len(hard)}")
for names, v in hard:
    print(f"  {v:10.2f} mm3  {' / '.join(names)}")

probe = os.path.join(OUT, "print_parts", "SW7_Dash_Cross_Joiner.SLDPRT")
d = sw.OpenDoc(probe, 1)
if d is not None:
    opened.append(d.GetTitle)
sw.ActivateDoc(title)
c = asm.AddComponent5(probe, 0, "", False, "", 0, 0, 0)
mu = sw.GetMathUtility
mo = mu._oleobj_
xf = mo.Invoke(mo.GetIDsOfNames("CreateTransform"), 0, pythoncom.DISPATCH_METHOD, True,
               VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                       [1.0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 2 * mm, 0, 1, 0, 0, 0]))
co = c._oleobj_
co.Invoke(co.GetIDsOfNames("Transform2"), 0, pythoncom.DISPATCH_PROPERTYPUT, False, xf)
asm.EditRebuild3
probe_hits = [h for h in interferences(False) if c.Name2 in h[0]]
print(f"\nprobe (cross joiner copy, 3 mm plate at Y 0..3 inside the 3 mm back plate): "
      f"{'DETECTED' if probe_hits else 'NOT DETECTED - check is not trustworthy'} {probe_hits}")
asm.ClearSelection2(True)
c.Select4(False, NONE, False)
asm.Extension.DeleteSelection2(0)
asm.EditRebuild3
print("components after probe removal:", len(comps()))

touch = interferences(True)
graph = {}
for names, v in touch:
    for a in names:
        graph.setdefault(a, set()).update(n for n in names if n != a)
print("\ncontacts (touching or overlapping):")
for c in comps():
    n = c.Name2
    print(f"  {n:38s} -> {', '.join(sorted(graph.get(n, []))) or 'NOTHING (floating)'}")
for t in reversed(opened):
    sw.CloseDoc(t)
