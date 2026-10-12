"""Dashboard display back shell: a tray the 272 x 187 mm display stack presses into from the front, with snap lips
on the long walls, a cable exit, vent slots over the Pi 5 and a dovetail rail on the back that slides into the
vehicle bracket (2_bracket.py). Modelled lying face down: back plate at Y = 0, opening facing +Y.
All key sizes are global variables (Tools > Equations)."""
import os
import pythoncom
import win32com.client
from win32com.client import VARIANT

NONE = VARIANT(pythoncom.VT_DISPATCH, None)
mm = 0.001
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = {
    "DispL": 272.0,     # measured: display outer length (whiteboard)
    "DispW": 187.0,     # measured: display outer width
    "DispT": 20.0,      # student's estimate: whole stack thickness incl. the Pi 5 behind it
    "Clr": 0.6,         # clearance each side
    "Wall": 2.5,
    "BackT": 3.0,
    "CableRoom": 4.0,   # extra depth behind the stack for plugs and cables
    "LipW": 1.2,        # snap lip overhang on the long walls
    "LipT": 1.5,        # snap lip thickness
    "RailW": 30.0,      # dovetail rail width at the back face
    "RailW2": 38.0,     # dovetail rail width at its outer face
    "RailH": 6.0,
    "RailL": 90.0,
    "CableW": 60.0,
    "CableH": 12.0,
}
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

# 4. Vent slots in the back plate, right of the rail, over where the Pi 5 sits.
plane_at(P["BackT"], "Back Inner", '"BackT"')
s = sketch("Back Inner")
for i in range(8):
    x0 = 40 + i * 9
    sm.CreateCornerRectangle(x0 * mm, -25 * mm, 0, (x0 + 3) * mm, 25 * mm, 0)
f = cut_either_way(s, P["BackT"] + 1)
f.Name = "Vent Slots"
print("vents", vol())

# 5. Cable exit through one long wall (the bottom edge when mounted), above the back plate.
s = sketch("Front Plane")
y0 = P["BackT"] + 3
sm.CreateCornerRectangle(-P["CableW"] / 2 * mm, y0 * mm, 0, P["CableW"] / 2 * mm, (y0 + P["CableH"]) * mm, 0)
f = cut_either_way(s, W / 2 + 1)
f.Name = "Cable Exit"
print("cable exit", vol())

# 6. Dovetail rail on the back face, running along the shell's short direction (vertical when mounted).
s = sketch("Front Plane")
rw, rw2, rh = P["RailW"] / 2, P["RailW2"] / 2, P["RailH"]
pts = [(-rw, 0.5), (rw, 0.5), (rw2, -rh), (-rw2, -rh)]   # 0.5 mm overlap into the back plate so it merges
sm.AddToDB = True                                          # no grid snapping: it moved these corners by 1 mm
for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
    sm.CreateLine(x1 * mm, y1 * mm, 0, x2 * mm, y2 * mm, 0)
sm.AddToDB = False
close_and_select(s)
before = vol()
rail = fm.FeatureExtrusion2(True, False, False, 6, 0, P["RailL"] * mm, 0, False, False, False, False,
                            0, 0, False, False, False, False, True, True, True, 0, 0, False)   # 6 = mid plane
rail.Name = "Dovetail Rail"
eq.Add2(-1, '"D1@Dovetail Rail" = "RailL"', True)
print("rail", vol(), "added", round(vol() - before, 1))

m.EditRebuild3
os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, "SW7_Dash_Back_Shell.SLDPRT")
print("save:", m.SaveAs3(path, 0, 1), path)
m.ShowNamedView2("*Isometric", 7)
m.ViewZoomtofit2
m.SaveBMP(os.path.join(os.environ.get("SW7_SHOT_DIR", OUT), "dash_shell_iso.bmp"), 1200, 800)
print("box mm:", [round(v * 1000, 2) for v in m.GetPartBox(True)])
