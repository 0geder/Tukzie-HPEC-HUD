"""Dashboard display back shell (master): a tray the 272 x 187 mm display stack presses into from the front, with
snap lips on the long walls, a cable exit on the -X short side (driver's left), vent slots and M3 bolt holes. 3_split_and_plates.py
cuts it into four quarters that fit a Prusa Mini (180 x 180 mm bed) and makes the rail plate, which bolts across the
centre, joins the quarters and carries the dovetail for the bracket. Modelled face down: back plate at Y = 0,
opening facing +Y, +X is the driver's right.
All key sizes are global variables (Tools > Equations)."""
import os
import pythoncom
import win32com.client
from win32com.client import VARIANT

NONE = VARIANT(pythoncom.VT_DISPATCH, None)
mm = 0.001
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = {
    "DispL": 272.0,     # measured tight by the student, 12 Oct (Waveshare drawing says 274.12; the measurement wins)
    "DispW": 187.0,     # measured tight by the student, 12 Oct
    "DispT": 20.0,      # student's estimate: whole stack thickness incl. the Pi 5 behind it
    "Clr": 0.6,         # clearance each side
    "Wall": 2.5,
    "BackT": 3.0,
    "CableRoom": 4.0,   # extra depth behind the stack for plugs and cables
    "LipW": 1.2,        # snap lip overhang on the long walls
    "LipT": 1.5,        # snap lip thickness
    "CableW": 58.0,     # connector span 43 to 45 mm (measured) plus 6 to 7 mm each side for the plug bodies
    "CableH": 16.0,
    "BoltD": 3.4,       # M3 clearance
}
# Bolt hole centres (x, z) in mm, shared with 3_split_and_plates.py.
RAIL_CZ = 53.0      # rail plate centre: low on the back, so the display stands above the handlebar
RAIL_HOLES = [(sx * 40, RAIL_CZ + sz * 35) for sx in (-1, 1) for sz in (-1, 1)] +              [(sx * 52, RAIL_CZ + sz * 13) for sx in (-1, 1) for sz in (-1, 1)]
# Joiners: one straight across the top of the X split, one straight across the right of the Z split, one cross
# plate at the centre (one bolt per quarter). The rail plate bridges the bottom of the X split and the Pi 5 cradle
# the left of the Z split.
JOINER_HOLES = [(sx * 12, -82) for sx in (-1, 1)] + [(124, sz * 12) for sz in (-1, 1)] +                [(sx * 12, sz * 12) for sx in (-1, 1) for sz in (-1, 1)]
# Pi 5 cradle (4_pi5_cradle.py): four bolts of its own, two either side of the Z split.
PI_HOLES = [(-110, 12), (-110, -12), (-86, 12), (-86, -12)]   # clear of the standoffs at x -122.5 and -73.5
L = P["DispL"] + 2 * P["Clr"] + 2 * P["Wall"]
W = P["DispW"] + 2 * P["Clr"] + 2 * P["Wall"]
IL, IW = P["DispL"] + 2 * P["Clr"], P["DispW"] + 2 * P["Clr"]
H = P["BackT"] + P["DispT"] + P["CableRoom"]

sw = win32com.client.GetActiveObject("SldWorks.Application")
sw.SetUserPreferenceToggle(10, False)
m = sw.NewDocument(sw.GetUserPreferenceStringValue(8), 0, 0, 0)
sm, fm, eq = m.SketchManager, m.FeatureManager, m.GetEquationMgr
for k, v in P.items():
    eq.Add2(-1, f'"{k}" = {v}', True)
eq.Add2(-1, '"ShellL" = "DispL" + 2 * "Clr" + 2 * "Wall"', True)
eq.Add2(-1, '"ShellW" = "DispW" + 2 * "Clr" + 2 * "Wall"', True)
eq.Add2(-1, '"ShellH" = "BackT" + "DispT" + "CableRoom"', True)


def vol():
    return round(m.Extension.CreateMassProperty.Volume * 1e9, 1)


def select(name, kind):
    if not m.Extension.SelectByID2(name, kind, 0, 0, 0, False, 0, NONE, 0):
        raise SystemExit(f"could not select {kind} {name}")


def dim(seg, value_mm, at):
    m.ClearSelection2(True)
    seg.Select4(False, NONE)
    d = m.AddDimension2(*at).GetDimension2(0)
    d.SystemValue = value_mm * mm
    return "@".join(d.FullName.split("@")[:2])


def sketch(plane):
    m.ClearSelection2(True)
    select(plane, "PLANE")
    sm.InsertSketch(True)
    return m.GetActiveSketch2.Name


def close_and_select(name):
    sm.InsertSketch(True)
    m.ClearSelection2(True)
    select(name, "SKETCH")


def cut(depth_mm, flip, through=False):
    return fm.FeatureCut4(True, flip, False, 1 if through else 0, 0, depth_mm * mm, 0, False, False, False, False,
                          0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)


def cut_either_way(name, depth_mm, through=False):
    before = vol()
    close_and_select(name)
    f = cut(depth_mm, False, through)
    if f is None or vol() >= before - 0.001:
        if f is not None:
            m.EditUndo2(1)
        m.ClearSelection2(True)
        select(name, "SKETCH")
        f = cut(depth_mm, True, through)
    if f is None or vol() >= before - 0.001:
        raise SystemExit(f"cut from {name} removed nothing")
    return f


def plane_at(y_mm, name, expr):
    m.ClearSelection2(True)
    select("Top Plane", "PLANE")
    p = fm.InsertRefPlane(8, y_mm * mm, 0, 0, 0, 0)
    p.Name = name
    eq.Add2(-1, f'"D1@{name}" = {expr}', True)
    return p


# 1. Solid block.
s = sketch("Top Plane")
segs = [x for x in sm.CreateCenterRectangle(0, 0, 0, L / 2 * mm, W / 2 * mm, 0) if x is not None]
dL = dim(segs[0], L, (0, 0, -(W / 2 + 15) * mm))
dW = dim(segs[1], W, ((L / 2 + 15) * mm, 0, 0))
close_and_select(s)
body = fm.FeatureExtrusion2(True, False, False, 0, 0, H * mm, 0, False, False, False, False,
                            0, 0, False, False, False, False, True, True, True, 0, 0, False)
body.Name = "Shell Block"
eq.Add2(-1, f'"{dL}" = "ShellL"', True)
eq.Add2(-1, f'"{dW}" = "ShellW"', True)
eq.Add2(-1, '"D1@Shell Block" = "ShellH"', True)
print("block", vol())

# 2. Front opening, narrower across the width by the lips.
plane_at(H, "Shell Front", '"ShellH"')
s = sketch("Shell Front")
segs = [x for x in sm.CreateCenterRectangle(0, 0, 0, IL / 2 * mm, (IW / 2 - P["LipW"]) * mm, 0) if x is not None]
d1 = dim(segs[0], IL, (0, 0, -(W / 2 + 25) * mm))
d2 = dim(segs[1], IW - 2 * P["LipW"], ((L / 2 + 25) * mm, 0, 0))
f = cut_either_way(s, P["LipT"])
f.Name = "Front Opening"
eq.Add2(-1, f'"{d1}" = "DispL" + 2 * "Clr"', True)
eq.Add2(-1, f'"{d2}" = "DispW" + 2 * "Clr" - 2 * "LipW"', True)
eq.Add2(-1, '"D1@Front Opening" = "LipT"', True)
print("opening", vol())

# 3. Display pocket under the lips, cut down from a plane LipT below the front.
plane_at(H - P["LipT"], "Under Lip", '"ShellH" - "LipT"')
s = sketch("Under Lip")
segs = [x for x in sm.CreateCenterRectangle(0, 0, 0, IL / 2 * mm, IW / 2 * mm, 0) if x is not None]
d1 = dim(segs[0], IL, (0, 0, -(W / 2 + 35) * mm))
d2 = dim(segs[1], IW, ((L / 2 + 35) * mm, 0, 0))
f = cut_either_way(s, H - P["LipT"] - P["BackT"])
f.Name = "Display Pocket"
eq.Add2(-1, f'"{d1}" = "DispL" + 2 * "Clr"', True)
eq.Add2(-1, f'"{d2}" = "DispW" + 2 * "Clr"', True)
eq.Add2(-1, '"D1@Display Pocket" = "ShellH" - "LipT" - "BackT"', True)
print("pocket", vol())

# 4. Vent slots in the back plate, two rows near the -X short side (the connector side, the driver's left),
#    kept clear of the bolt holes.
plane_at(P["BackT"], "Back Inner", '"BackT"')
s = sketch("Back Inner")
sm.AddToDB = True
for i in range(8):
    x0 = -(66 + i * 8) - 3
    for z0, z1 in ((28, 84), (-84, -28)):
        sm.CreateCornerRectangle(x0 * mm, z0 * mm, 0, (x0 + 3) * mm, z1 * mm, 0)
sm.AddToDB = False
f = cut_either_way(s, P["BackT"] + 1)
f.Name = "Vent Slots"
print("vents", vol())

# 5. Cable exit through the -X short wall: the display's HDMI, USB and power plugs come out on the driver's left
#    (photo 2026-10-12_display_on_desk_cables_left.jpg). The cut goes from the Right plane in whichever direction
#    moves the centre of mass towards +X, i.e. removes material on the -X side.
s = sketch("Right Plane")
y0 = P["BackT"] + 2
sm.AddToDB = True
sm.CreateCornerRectangle(-P["CableW"] / 2 * mm, y0 * mm, 0, P["CableW"] / 2 * mm, (y0 + P["CableH"]) * mm, 0)
sm.AddToDB = False
cx0 = m.Extension.CreateMassProperty.CenterOfMass[0]
close_and_select(s)
f = cut(L / 2 + 1, False)
if f is None or m.Extension.CreateMassProperty.CenterOfMass[0] <= cx0:
    if f is not None:
        m.EditUndo2(1)
    m.ClearSelection2(True)
    select(s, "SKETCH")
    f = cut(L / 2 + 1, True)
if f is None or m.Extension.CreateMassProperty.CenterOfMass[0] <= cx0:
    raise SystemExit("cable exit did not land on the -X wall")
f.Name = "Cable Exit (-X short side)"
print("cable exit", vol())

# 6. M3 bolt holes through the back plate: eight for the rail plate across the centre (two per quarter) and
#    eight for the joiner plates across the outer ends of the split lines (the Pi 5 cradle takes the left
#    pair) and two more for the cradle.
s = sketch("Back Inner")
sm.AddToDB = True
for x, z in RAIL_HOLES + JOINER_HOLES + PI_HOLES:
    sm.CreateCircleByRadius(x * mm, z * mm, 0, P["BoltD"] / 2 * mm)
sm.AddToDB = False
f = cut_either_way(s, P["BackT"] + 1)
f.Name = "Bolt Holes"
print("bolt holes", vol())

m.EditRebuild3
os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, "SW7_Dash_Back_Shell.SLDPRT")
print("save:", m.SaveAs3(path, 0, 1), path)
m.ShowNamedView2("*Isometric", 7)
m.ViewZoomtofit2
m.SaveBMP(os.path.join(os.environ.get("SW7_SHOT_DIR", OUT), "dash_shell_iso.bmp"), 1200, 800)
print("box mm:", [round(v * 1000, 2) for v in m.GetPartBox(True)])
