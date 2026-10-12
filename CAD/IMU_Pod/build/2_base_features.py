"""IMU pod step 2, on the active part: top reference plane, board pocket, board holes, lid holes, cable exit,
strap slots. All key sizes linked to global variables. Prints the volume after each feature so a wrong cut
direction shows at once."""
import pythoncom
import win32com.client
from win32com.client import VARIANT

NONE = VARIANT(pythoncom.VT_DISPATCH, None)
mm = 0.001
NEW_GLOBALS = [
    ("HoleSpacing", 15.2, "MEASURE: distance between the two GY-521 mounting holes"),
    ("HoleOffset", 5.6, "MEASURE: holes' offset from the board centre, across the board"),
    ("PilotD", 2.2, "pilot hole for M2.5 self-tapping screws in PETG"),
    ("FloorHoleD", 4.0, "depth of board and lid pilot holes"),
    ("LidInset", 4.0, "lid screw distance from each outside edge"),
    ("StrapX", 9.0, "strap slot centre distance from the middle"),
    ("StrapW", 6.0, "strap slot width (5 mm cable ties; 9 for a hose clamp)"),
    ("StrapT", 3.5, "strap slot height"),
    ("StrapZ0", 1.5, "strap slot bottom above the base"),
    ("CableW", 8.0, "cable exit width"),
]

sw = win32com.client.GetActiveObject("SldWorks.Application")
m = sw.ActiveDoc
sm, fm, eq = m.SketchManager, m.FeatureManager, m.GetEquationMgr
names = [eq.Equation(i).split("=")[0].strip().strip('"') for i in range(eq.GetCount)]
for n, v, _ in NEW_GLOBALS:
    if n not in names:
        eq.Add2(-1, f'"{n}" = {v}', True)
G = {eq.Equation(i).split("=")[0].strip().strip('"'): eq.Equation(i).split("=", 1)[1].strip()
     for i in range(eq.GetCount)}


def val(name):
    return float(G[name])


def vol():
    p = m.Extension.CreateMassProperty
    return round(p.Volume * 1e9, 1)       # mm^3


def select(name, kind, append=False):
    if not m.Extension.SelectByID2(name, kind, 0, 0, 0, append, 0, NONE, 0):
        raise SystemExit(f"could not select {kind} {name}")


def link(full_name, expr):
    short = "@".join(full_name.split("@")[:2])
    eq.Add2(-1, f'"{short}" = {expr}', True)


def dim(seg, value_mm, at):
    m.ClearSelection2(True)
    seg.Select4(False, NONE)
    dd = m.AddDimension2(*at)
    d = dd.GetDimension2(0)
    d.SystemValue = value_mm * mm
    return d.FullName


def dim_points(p1, p2, value_mm, at):
    """Dimension between two sketch points (horizontal or vertical decided by placement)."""
    m.ClearSelection2(True)
    p1.Select4(False, NONE)
    p2.Select4(True, NONE)
    dd = m.AddDimension2(*at)
    d = dd.GetDimension2(0)
    d.SystemValue = value_mm * mm
    return d.FullName


def cut(depth_mm, flip, through=False):
    end = 1 if through else 0          # swEndCondThroughAll = 1, swEndCondBlind = 0
    return fm.FeatureCut4(True, flip, False, end, 0, depth_mm * mm, 0, False, False, False, False, 0, 0,
                          False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)


def cut_checked(depth_mm, through=False, both=False):
    """Cut; if it removed nothing (wrong side), undo and flip."""
    before = vol()
    sketch = m.SketchManager.ActiveSketch
    sm.InsertSketch(True)
    f = cut(depth_mm, False, through)
    if f is None or vol() >= before:
        if f is not None:
            m.EditUndo2(1)
        m.ClearSelection2(True)
        select(last_sketch[0], "SKETCH")
        f = cut(depth_mm, True, through)
    return f


print("start volume", vol())
H = val("PodH")

# Reference plane at the top face (offset PodH from Top Plane).
select("Top Plane", "PLANE")
plane = fm.InsertRefPlane(8, H * mm, 0, 0, 0, 0)       # 8 = distance
plane.Name = "Pod Top"
link(plane.GetDefinition and "D1@Pod Top@x", '"PodH"') if False else None
eq.Add2(-1, '"D1@Pod Top" = "PodH"', True)

last_sketch = [None]


def sketch_on(plane_name):
    m.ClearSelection2(True)
    select(plane_name, "PLANE")
    sm.InsertSketch(True)
    s = sm.ActiveSketch
    last_sketch[0] = s.Name if hasattr(s, "Name") else m.GetActiveSketch2.Name
    return s


def finish_cut(depth_mm, through=False, label=""):
    name = last_sketch[0]
    before = vol()
    sm.InsertSketch(True)                  # close the sketch, leaves it selected
    m.ClearSelection2(True)
    select(name, "SKETCH")
    f = cut(depth_mm, False, through)
    if f is None or vol() >= before - 0.01:
        if f is not None:
            m.EditUndo2(1)
        m.ClearSelection2(True)
        select(name, "SKETCH")
        f = cut(depth_mm, True, through)
    print(f"{label}: {f.Name if f else 'FAILED'}  volume {vol()}")
    return f


# 1. Board pocket.
sketch_on("Pod Top")
bl = val("BoardL") + 2 * val("Clear")
bw = val("BoardW") + 2 * val("Clear")
segs = [s for s in sm.CreateCenterRectangle(0, 0, 0, bl / 2 * mm, bw / 2 * mm, 0) if s is not None]
nL = dim(segs[0], bl, (0, 0, -bw * mm))
nW = dim(segs[1], bw, (bl * mm, 0, 0))
pocket = finish_cut(val("PocketD"), label="pocket")
link(nL, '"BoardL" + 2 * "Clear"')
link(nW, '"BoardW" + 2 * "Clear"')
eq.Add2(-1, f'"D1@{pocket.Name}" = "PocketD"', True)

# 2. Board pilot holes, from the pocket floor down.
sketch_on("Pod Top")
hs, ho, r = val("HoleSpacing"), val("HoleOffset"), val("PilotD") / 2
for sx in (-1, 1):
    sm.CreateCircleByRadius(sx * hs / 2 * mm, ho * mm, 0, r * mm)
holes = finish_cut(val("PocketD") + val("FloorHoleD"), label="board holes")
eq.Add2(-1, f'"D1@{holes.Name}" = "PocketD" + "FloorHoleD"', True)

# 3. Lid pilot holes at the four corners.
sketch_on("Pod Top")
L, W, inset = val("PodL"), val("PodW"), val("LidInset")
for sx in (-1, 1):
    for sz in (-1, 1):
        sm.CreateCircleByRadius(sx * (L / 2 - inset) * mm, sz * (W / 2 - inset) * mm, 0, r * mm)
lidholes = finish_cut(val("FloorHoleD") + 4, label="lid holes")

# 4. Cable exit through the +X end wall, as deep as the pocket.
sketch_on("Pod Top")
cw = val("CableW")
sm.CreateCornerRectangle((bl / 2 - 1) * mm, -cw / 2 * mm, 0, (L / 2 + 1) * mm, cw / 2 * mm, 0)
cable = finish_cut(val("PocketD") - 1.5, label="cable exit")

# 5. Strap slots right through the width, under the pocket floor (sketch on the Front plane).
sketch_on("Front Plane")
sx_, swd, st, sz0 = val("StrapX"), val("StrapW"), val("StrapT"), val("StrapZ0")
for sx in (-1, 1):
    x0 = sx * sx_ - swd / 2
    sm.CreateCornerRectangle(x0 * mm, sz0 * mm, 0, (x0 + swd) * mm, (sz0 + st) * mm, 0)
name = last_sketch[0]
before = vol()
sm.InsertSketch(True)
m.ClearSelection2(True)
select(name, "SKETCH")
# Through all in both directions (FeatureCut4 with both directions through all).
slot = fm.FeatureCut4(False, False, False, 1, 1, 0, 0, False, False, False, False, 0, 0,
                      False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
print(f"strap slots: {slot.Name if slot else 'FAILED'}  volume {vol()}")

m.EditRebuild3
print("box mm:", [round(v * 1000, 2) for v in m.GetPartBox(True)])
