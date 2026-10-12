"""Assembly of the whole dashboard mount on a dummy handlebar, to check fit and show how it goes together.

Makes three reference parts (not printed): a 22.2 mm handlebar, the display as a 272 x 187 x 20 mm block and a
Raspberry Pi 5 with its cooler and port stack, then places everything in the shell's frame (shell face down, +Y is
the screen side, +X the driver's right, +Z down when fitted)."""
import os
import pythoncom
import win32com.client
from win32com.client import VARIANT

NONE = VARIANT(pythoncom.VT_DISPATCH, None)
mm = 0.001
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
PP = os.path.join(OUT, "print_parts")
REF = os.path.join(OUT, "reference_parts")
os.makedirs(REF, exist_ok=True)
SHOTS = os.environ.get("SW7_SHOT_DIR", OUT)

sw = win32com.client.GetActiveObject("SldWorks.Application")
sw.SetUserPreferenceToggle(10, False)
mu = sw.GetMathUtility


def new_part():
    m = sw.NewDocument(sw.GetUserPreferenceStringValue(8), 0, 0, 0)
    return m, m.SketchManager, m.FeatureManager


def sketch_top(m, sm):
    m.ClearSelection2(True)
    m.Extension.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, NONE, 0)
    sm.InsertSketch(True)
    sm.AddToDB = True
    return m.GetActiveSketch2.Name


def extrude(m, sm, fm, name, depth, merge=True):
    sm.AddToDB = False
    sm.InsertSketch(True)
    m.ClearSelection2(True)
    m.Extension.SelectByID2(name, "SKETCH", 0, 0, 0, False, 0, NONE, 0)
    return fm.FeatureExtrusion2(True, False, False, 0, 0, depth * mm, 0, False, False, False, False,
                                0, 0, False, False, False, False, merge, True, True, 0, 0, False)


def rect(sm, x0, z0, x1, z1):
    sm.CreateCornerRectangle(x0 * mm, -z0 * mm, 0, x1 * mm, -z1 * mm, 0)   # Top plane sketch y is -Z


def save(m, path):
    m.EditRebuild3
    err = m.SaveAs3(path, 0, 1)
    sw.CloseDoc(m.GetTitle)
    return err


# Reference parts.
m, sm, fm = new_part()
m.ClearSelection2(True)
m.Extension.SelectByID2("Right Plane", "PLANE", 0, 0, 0, False, 0, NONE, 0)
sm.InsertSketch(True)
sm.CreateCircleByRadius(0, 0, 0, 22.2 / 2 * mm)
bar_sketch = m.GetActiveSketch2.Name
sm.InsertSketch(True)
m.ClearSelection2(True)
m.Extension.SelectByID2(bar_sketch, "SKETCH", 0, 0, 0, False, 0, NONE, 0)
fm.FeatureExtrusion2(True, False, False, 6, 0, 600 * mm, 0, False, False, False, False,
                     0, 0, False, False, False, False, True, True, True, 0, 0, False)
BAR = os.path.join(REF, "REF_Handlebar_22mm.SLDPRT")
print("bar", save(m, BAR))

m, sm, fm = new_part()
s = sketch_top(m, sm)
rect(sm, -136, -93.5, 136, 93.5)
extrude(m, sm, fm, s, 20)
DISP = os.path.join(REF, "REF_Display_272x187x20.SLDPRT")
print("display", save(m, DISP))

# Pi 5 in its own frame: board on Y 0..1.6, parts above. Placed flipped (Y and Z negated) on the cradle, so the
# USB end, drawn here at -Z, ends up at +Z (down).
m, sm, fm = new_part()
s = sketch_top(m, sm)
rect(sm, -126, -42.5, -70, 42.5)
extrude(m, sm, fm, s, 1.6)
s = sketch_top(m, sm)
rect(sm, -125, -44.5, -71, -26)        # USB and Ethernet stack, 16 mm tall, 2 mm overhang
extrude(m, sm, fm, s, 17.6)
s = sketch_top(m, sm)
rect(sm, -118, -12, -78, 28)           # active cooler, about 13.7 mm
extrude(m, sm, fm, s, 15.3)
PI = os.path.join(REF, "REF_Pi5_with_cooler.SLDPRT")
print("pi", save(m, PI))

# Assembly.
asm = sw.NewDocument(sw.GetUserPreferenceStringValue(9), 0, 0, 0)
asm_title = asm.GetTitle
FLIP_X = [1, 0, 0, 0, -1, 0, 0, 0, -1]                 # 180 deg about X: y -> -y, z -> -z
FLIP_X_TURN_Y = [0, 0, -1, 0, -1, 0, -1, 0, 0]         # also turned 90 deg about Y (long axis along Z)
IDENT = [1, 0, 0, 0, 1, 0, 0, 0, 1]
BR_T = (0.0, -22.0, 61.0)   # bracket: open face against the rail plate (Y -4); stop inner face (bracket Z +34) on
#   the rail's lower end (Z 95); the 72 mm rail runs Z 23 to 95, and the lock (bracket Z -30) lands on the
#   detent at Z 31 (plate centre 59 - 28)

placements = [
    (os.path.join(OUT, "SW7_Dash_Back_Shell.SLDPRT"), IDENT, (0, 0, 0)),
    (DISP, IDENT, (0, 5.5, 0)),                          # front face under the 1.5 mm lips at Y 25.5
    (os.path.join(PP, "SW7_Dash_Rail_Plate.SLDPRT"), FLIP_X, (0, 0, 59)),
    (os.path.join(PP, "SW7_Dash_Cross_Joiner.SLDPRT"), FLIP_X, (0, 0, 0)),
    (os.path.join(PP, "SW7_Dash_Joiner_Plate.SLDPRT"), FLIP_X, (0, 0, -82)),
    (os.path.join(PP, "SW7_Dash_Joiner_Plate.SLDPRT"), FLIP_X_TURN_Y, (124, 0, 0)),
    (os.path.join(PP, "SW7_Dash_Pi5_Cradle.SLDPRT"), IDENT, (0, 0, 0)),
    (PI, FLIP_X, (0, -10, -10)),   # on the cradle standoffs (review D9)
    (os.path.join(OUT, "SW7_Dash_Bracket.SLDPRT"), IDENT, BR_T),
    (os.path.join(OUT, "SW7_Dash_Clamp_Cap.SLDPRT"), IDENT, BR_T),
    (BAR, IDENT, (0, BR_T[1] - 12.0, BR_T[2])),
]
for path, rot, t in placements:
    d = sw.OpenDoc(path, 1)
    sw.ActivateDoc(asm_title)
    c = asm.AddComponent5(path, 0, "", False, "", 0, 0, 0)
    if c is None:
        raise SystemExit("could not add " + path)
    arr = [float(v) for v in rot] + [t[0] * mm, t[1] * mm, t[2] * mm, 1.0, 0.0, 0.0, 0.0]
    # Late binding cannot see CreateTransform or the Transform2 setter by name, so call them by dispatch id.
    mo = mu._oleobj_
    xf = mo.Invoke(mo.GetIDsOfNames("CreateTransform"), 0, pythoncom.DISPATCH_METHOD, True,
                   VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, arr))
    co = c._oleobj_
    co.Invoke(co.GetIDsOfNames("Transform2"), 0, pythoncom.DISPATCH_PROPERTYPUT, False, xf)
    print("placed", os.path.basename(path), t)
    if d is not None and d.GetTitle != asm_title:
        sw.CloseDoc(d.GetTitle)

sw.ActivateDoc(asm_title)
asm.EditRebuild3
# Every part is modelled in its final position, so fix all of them in place (review D9: they were floating).
asm.ClearSelection2(True)
for comp in asm.GetComponents(True):
    comp.Select4(True, NONE, False)
asm.FixComponent()   # needs the call parentheses under late binding
asm.ClearSelection2(True)
print("fixed:", sum(1 for comp in asm.GetComponents(True) if comp.IsFixed), "of", len(asm.GetComponents(True)))
path = os.path.join(OUT, "SW7_Dash_Assembly.SLDASM")
print("save asm:", asm.SaveAs3(path, 0, 1), path)
for view, shot in (("*Isometric", "asm_iso.bmp"), ("*Back", "asm_back.bmp"), ("*Right", "asm_side.bmp")):
    asm.ShowNamedView2(view, -1)
    asm.ViewZoomtofit2
    asm.SaveBMP(os.path.join(SHOTS, shot), 1200, 800)
print("box mm:", [round(v * 1000, 1) for v in asm.GetBox(0)])
