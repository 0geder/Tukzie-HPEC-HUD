"""Sensor pod step 5: the assembly, an interference check and the preview pictures.

Every pod part is modelled in the pod frame, so it goes in at the origin. The dashboard's bar clamp (bracket and cap)
is turned 180 deg about the vertical so its closed end faces forward, and moved down under the rail plate.
The interference check lists every pair of parts that overlap; overlaps with the view cones mean something blocks
a sensor.
"""
import os
import sys
import pythoncom
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import *          # noqa: F401,F403
from swlib import sw, OPENED, PRINT, REF, OUT, invoke, arr, snap, call0, NONE

mm = 0.001
DASH = os.path.join(os.path.dirname(OUT), "Dashboard_Enclosure")
BAR = os.path.join(DASH, "reference_parts", "REF_Handlebar_22mm.SLDPRT")
# Bracket frame (CAD/Dashboard_Enclosure/build/2_bracket.py): channel open face at bracket y = 18, bar at y = -12,
# channel closed inner face at z = +34. Model coordinates here: X = pod X, Y = pod Z, Z = -pod Y.
RAIL_FRONT_Y = MOUNT_Y + 36.0                       # front end of the 72 mm rail
TY = (BOX_BOT_Z - RAIL_PLATE[2]) - 18.0             # bracket top face against the plate's underside
TZ = -RAIL_FRONT_Y + 34.0                           # model z shift: after the 180 deg turn the stop's inner face
#   (bracket z +34 -> model z -34) lands on the rail's front end (pod y -30 -> model z +30)
TURN = [-1, 0, 0, 0, 1, 0, 0, 0, -1]
IDENT = [1, 0, 0, 0, 1, 0, 0, 0, 1]

parts = [os.path.join(PRINT, f) for f in sorted(os.listdir(PRINT)) if f.endswith(".SLDPRT") and not f.startswith("~$")]
refs = [os.path.join(REF, f) for f in sorted(os.listdir(REF)) if f.endswith(".SLDPRT") and not f.startswith("~$")]
placements = [(p, IDENT, (0, 0, 0)) for p in parts + refs]
placements += [(os.path.join(DASH, "SW7_Dash_Bracket.SLDPRT"), TURN, (0, TY, TZ)),
               (os.path.join(DASH, "SW7_Dash_Clamp_Cap.SLDPRT"), TURN, (0, TY, TZ)),
               (BAR, IDENT, (0, TY - 12.0, TZ))]

asm = sw.NewDocument(sw.GetUserPreferenceStringValue(9), 0, 0, 0)
title = asm.GetTitle
OPENED.append(title)
mu = sw.GetMathUtility
for path, rot, t in placements:
    if not os.path.exists(path):
        print("missing", path)
        continue
    d = sw.OpenDoc(path, 1)
    sw.ActivateDoc(title)
    c = asm.AddComponent5(path, 0, "", False, "", 0, 0, 0)
    if c is None:
        raise SystemExit("could not add " + path)
    xf = invoke(mu, "CreateTransform", pythoncom.DISPATCH_METHOD,
                arr(list(rot) + [t[0] * mm, t[1] * mm, t[2] * mm, 1, 0, 0, 0]))
    co = c._oleobj_
    co.Invoke(co.GetIDsOfNames("Transform2"), 0, pythoncom.DISPATCH_PROPERTYPUT, False, xf)
    if d is not None and d.GetTitle != title:
        sw.CloseDoc(d.GetTitle)
    print("placed", os.path.basename(path))

sw.ActivateDoc(title)
call0(asm, "EditRebuild3")
path = os.path.join(OUT, "SW7_Sensor_Pod_Assembly.SLDASM")
# Fix every component in place (all are modelled in their final positions), and hide the view cones in the default
# display: they are reference volumes for clearance checks, not parts. Show them with right-click > Show.
asm.ClearSelection2(True)
for comp in asm.GetComponents(True):
    comp.Select4(True, NONE, False)
asm.FixComponent()
asm.ClearSelection2(True)
for comp in asm.GetComponents(True):
    if comp.Name2.startswith("REF_View_Cones"):
        comp.Visible = 0
print("fixed:", sum(1 for c in asm.GetComponents(True) if c.IsFixed), "of", len(asm.GetComponents(True)))
print("save", asm.SaveAs3(path, 0, 1), path)

# Interference check.
try:
    idm = asm.InterferenceDetectionManager
    idm.TreatCoincidenceAsInterference = False
    idm.IncludeMultibodyPartInterferences = False
    found = idm.GetInterferences
    print("interferences:", 0 if not found else len(found))
    for it in (found or []):
        comps = [x.Name2 for x in it.Components]
        print(f"  {round(it.Volume * 1e9, 1)} mm3: {' / '.join(comps)}")
    idm.Done()
except Exception as ex:
    print("interference check failed:", ex)

for view, png in (("*Isometric", "assembly_iso.png"), ("front_iso", "assembly_front_iso.png"),
                  ("*Right", "assembly_side.png"), ("*Back", "assembly_front.png")):
    snap(asm, png, view)
print("box mm:", [round(v / mm, 1) for v in asm.GetBox(0)])
