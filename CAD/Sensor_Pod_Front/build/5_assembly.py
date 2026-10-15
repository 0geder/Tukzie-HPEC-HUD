"""Front pod step 5: the assembly, an interference check, an exploded assembly and the renders.

As the original: every pod part is modelled in the pod frame and goes in at the origin, fixed. The dashboard's bar
clamp (bracket and cap) is turned 180 deg about the vertical so its closed end faces forward, under the rail plate.
Renders go to renders/: iso, front iso, front, side, top with the lid and sunshade hidden, a section on the
internals view (box hidden: the Pi 5 stack and the cable paths), and the exploded assembly.
"""
import os
import sys
import pythoncom
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import *          # noqa: F401,F403
import swlib
from swlib import sw, OPENED, PRINT, REF, OUT, invoke, arr, snap, call0, NONE

mm = 0.001
swlib.PREV = os.path.join(OUT, "renders")
DASH = os.path.join(os.path.dirname(OUT), "Dashboard_Enclosure")
BAR = os.path.join(DASH, "reference_parts", "REF_Handlebar_22mm.SLDPRT")
RAIL_FRONT_Y = MOUNT_Y + 36.0
TY = (BOX_BOT_Z - RAIL_PLATE[2]) - 18.0
TZ = -RAIL_FRONT_Y + 34.0
TURN = [-1, 0, 0, 0, 1, 0, 0, 0, -1]
IDENT = [1, 0, 0, 0, 1, 0, 0, 0, 1]


def listing(d):
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".SLDPRT") and not f.startswith("~$")]


parts, refs = listing(PRINT), listing(REF)
CLAMP = [(os.path.join(DASH, "SW7_Dash_Bracket.SLDPRT"), TURN, (0, TY, TZ)),
         (os.path.join(DASH, "SW7_Dash_Clamp_Cap.SLDPRT"), TURN, (0, TY, TZ)),
         (BAR, IDENT, (0, TY - 12.0, TZ))]

# Exploded offsets in pod mm (X, Y, Z), turned into model (X, Z, -Y) below.
EXPLODE = {"Head_Upper": (0, 70, 60), "Camera_Retainer": (0, 70, 30), "Camera_Case": (0, 70, 30),
           "Head_Tray": (0, 70, 0), "Sensor_Board": (0, 70, 15), "View_Cones": None,
           "Box_Lid": (0, 0, 90), "Sunshade": (0, 0, 130), "Rear_Port_Cover": (0, -40, 0),
           "Side_Port_Cover": (40, 0, 0), "Rail_Plate": (0, 0, -40), "Pi5_with_Cooler": (0, 0, 45),
           "Cables": None}


def build(placements, title_hint):
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
    sw.ActivateDoc(title)
    call0(asm, "EditRebuild3")
    asm.ClearSelection2(True)
    for comp in asm.GetComponents(True):
        comp.Select4(True, NONE, False)
    asm.FixComponent()
    asm.ClearSelection2(True)
    for comp in asm.GetComponents(True):
        if "View_Cones" in comp.Name2:
            comp.Visible = 0
    print(title_hint, "fixed:", sum(1 for c in asm.GetComponents(True) if c.IsFixed), "of",
          len(asm.GetComponents(True)))
    return asm


def show(asm, names, visible):
    for comp in asm.GetComponents(True):
        if any(n in comp.Name2 for n in names):
            comp.Visible = 1 if visible else 0


asm = build([(p, IDENT, (0, 0, 0)) for p in parts + refs] + CLAMP, "assembly")
path = os.path.join(OUT, "SW7_Front_Sensor_Pod_Assembly.SLDASM")
print("save", asm.SaveAs3(path, 0, 1), path)
try:
    idm = asm.InterferenceDetectionManager
    idm.TreatCoincidenceAsInterference = False
    idm.IncludeMultibodyPartInterferences = False
    found = idm.GetInterferences
    print("interferences:", 0 if not found else len(found))
    for it in (found or []):
        print(f"  {round(it.Volume * 1e9, 1)} mm3: {' / '.join(x.Name2 for x in it.Components)}")
    idm.Done()
except Exception as ex:
    print("interference check failed:", ex)

for view, png in (("*Isometric", "assembly_iso.png"), ("front_iso", "assembly_front_iso.png"),
                  ("*Right", "assembly_side.png"), ("*Back", "assembly_front.png")):
    snap(asm, png, view)
show(asm, ["Box_Lid", "Sunshade", "Dash_", "Handlebar"], False)
snap(asm, "assembly_top_no_lid.png", "*Top")
snap(asm, "assembly_iso_no_lid.png", "front_iso")
show(asm, ["Box_Lid", "Sunshade", "Dash_", "Handlebar"], True)

# Internals: the box walls, lid, covers, head upper and clamp hidden, so the Pi 5 stack, the ribbon path through the
# HAT slot and the jumper hairpin show (in place of a section view, which did not render through the API).
inner = ["Box_Base", "Box_Lid", "Sunshade", "Port_Cover", "Head_Upper", "Dash_", "Handlebar", "Rail_Plate"]
show(asm, inner, False)
snap(asm, "assembly_internals_side.png", "*Right")
snap(asm, "assembly_internals_iso.png", "front_iso")
show(asm, inner, True)
print("box mm:", [round(v / mm, 1) for v in asm.GetBox(0)])
sw.CloseDoc(asm.GetTitle)

# Exploded copy (separate file, same parts moved apart).
ex = []
for p in parts + refs:
    key = next((k for k in EXPLODE if k in os.path.basename(p)), None)
    off = EXPLODE.get(key, (0, 0, 0)) if key else (0, 0, 0)
    if off is None:
        continue
    ex.append((p, IDENT, (off[0], off[2], -off[1])))
easm = build(ex, "exploded")
print("save", easm.SaveAs3(os.path.join(OUT, "SW7_Front_Sensor_Pod_Exploded.SLDASM"), 0, 1))
snap(easm, "assembly_exploded.png", "front_iso")
snap(easm, "assembly_exploded_rear.png", "*Isometric")
