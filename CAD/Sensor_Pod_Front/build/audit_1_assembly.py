"""Audit 1 (front pod): is the interference result trustworthy, which parts touch which, and which parts float.

1. Opens SW7_Front_Sensor_Pod_Assembly.SLDASM and lists every component with its fixed / floating state.
2. Runs interference detection (touching faces not counted) and lists every overlap with its volume.
3. Proves the check works: adds a copy of the box base shifted 5 mm and checks that the overlap is reported.
4. Runs it again with touching faces counted, giving the contact graph: a printed part touching nothing is floating.
Nothing is saved; the test copy is removed again.
"""
import os
import sys
import pythoncom
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from swlib import sw, OPENED, OUT, invoke, arr, PRINT, NONE

mm = 0.001
ASM = os.path.join(OUT, "SW7_Front_Sensor_Pod_Assembly.SLDASM")
asm = sw.OpenDoc(ASM, 2)
if asm is None:
    raise SystemExit("could not open " + ASM)
OPENED.append(asm.GetTitle)
sw.ActivateDoc(asm.GetTitle)


def comps():
    return list(asm.GetComponents(True) or [])


print("components:")
for c in comps():
    print(f"  {c.Name2:40s} fixed={c.IsFixed}  suppressed={c.IsSuppressed}")


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

# Proof that the check detects a real overlap.
probe = os.path.join(PRINT, "SW7_FPod_Box_Base.SLDPRT")
d = sw.OpenDoc(probe, 1)
sw.ActivateDoc(asm.GetTitle)
c = asm.AddComponent5(probe, 0, "", False, "", 0, 0, 0)
mu = sw.GetMathUtility
xf = invoke(mu, "CreateTransform", pythoncom.DISPATCH_METHOD, arr([1, 0, 0, 0, 1, 0, 0, 0, 1, 5 * mm, 0, 0, 1, 0, 0, 0]))
co = c._oleobj_
co.Invoke(co.GetIDsOfNames("Transform2"), 0, pythoncom.DISPATCH_PROPERTYPUT, False, xf)
asm.EditRebuild3
probe_hits = [h for h in interferences(False) if c.Name2 in h[0]]
print(f"\nprobe (box base copy shifted 5 mm): {'DETECTED' if probe_hits else 'NOT DETECTED - check is not trustworthy'}"
      f" {probe_hits[:2]}")
asm.ClearSelection2(True)
c.Select4(False, NONE, False)
asm.EditDelete
asm.EditRebuild3

touch = interferences(True)
graph = {}
for names, v in touch:
    for a in names:
        graph.setdefault(a, set()).update(n for n in names if n != a)
print("\ncontacts (touching or overlapping):")
for c in comps():
    n = c.Name2
    print(f"  {n:40s} -> {', '.join(sorted(graph.get(n, []))) or 'NOTHING (floating)'}")
sw.CloseDoc(asm.GetTitle)
