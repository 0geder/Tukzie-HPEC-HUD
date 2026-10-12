"""IMU pod lid: 2 mm plate, four M2.5 clearance holes matching the base's lid pilot holes, an arrow engraved
0.6 mm deep pointing +X (vehicle forward) so both pods go on in the same orientation. Globals mirror the base."""
import os
import pythoncom
import win32com.client
from win32com.client import VARIANT

NONE = VARIANT(pythoncom.VT_DISPATCH, None)
mm = 0.001
OUT = r"C:\Users\0geda\OneDrive - University of Cape Town\Documents\PlatformIO\Projects\Tukzie-HPEC-HUD\CAD\IMU_Pod"
P = {"PodL": 44.0, "PodW": 30.0, "LidT": 2.0, "LidInset": 4.0, "ClearD": 2.9, "EngraveD": 0.6}

sw = win32com.client.GetActiveObject("SldWorks.Application")
sw.SetUserPreferenceToggle(10, False)          # no dimension popup while scripting
m = sw.NewDocument(sw.GetUserPreferenceStringValue(8), 0, 0, 0)
sm, fm, eq = m.SketchManager, m.FeatureManager, m.GetEquationMgr
for k, v in P.items():
    eq.Add2(-1, f'"{k}" = {v}', True)


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
    return f


L, W, T = P["PodL"], P["PodW"], P["LidT"]
# Plate.
s = sketch("Top Plane")
segs = [x for x in sm.CreateCenterRectangle(0, 0, 0, L / 2 * mm, W / 2 * mm, 0) if x is not None]
dL = dim(segs[0], L, (0, 0, -(W / 2 + 6) * mm))
dW = dim(segs[1], W, ((L / 2 + 6) * mm, 0, 0))
close_and_select(s)
plate = fm.FeatureExtrusion2(True, False, False, 0, 0, T * mm, 0, False, False, False, False,
                             0, 0, False, False, False, False, True, True, True, 0, 0, False)
plate.Name = "Lid Plate"
eq.Add2(-1, f'"{dL}" = "PodL"', True)
eq.Add2(-1, f'"{dW}" = "PodW"', True)
eq.Add2(-1, '"D1@Lid Plate" = "LidT"', True)
print("plate", vol())

# Reference plane at the lid's top face; holes and arrow are cut down from it (as on the base).
m.ClearSelection2(True)
select("Top Plane", "PLANE")
top = fm.InsertRefPlane(8, T * mm, 0, 0, 0, 0)
top.Name = "Lid Top"
eq.Add2(-1, '"D1@Lid Top" = "LidT"', True)

# Clearance holes.
s = sketch("Lid Top")
r, inset = P["ClearD"] / 2, P["LidInset"]
for sx in (-1, 1):
    for sz in (-1, 1):
        sm.CreateCircleByRadius(sx * (L / 2 - inset) * mm, sz * (W / 2 - inset) * mm, 0, r * mm)
holes = cut_either_way(s, T + 1)
holes.Name = "Clearance Holes"
print("holes", vol())

s = sketch("Lid Top")
# shaft 14 x 3 mm from x=-9 to x=5, head triangle from x=5 to x=11
pts = [(-9, -1.5), (5, -1.5), (5, -4.5), (11, 0), (5, 4.5), (5, 1.5), (-9, 1.5)]
for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
    sm.CreateLine(x1 * mm, y1 * mm, 0, x2 * mm, y2 * mm, 0)
arrow = cut_either_way(s, P["EngraveD"])
arrow.Name = "Forward Arrow (+X)"
eq.Add2(-1, f'"D1@{arrow.Name}" = "EngraveD"', True)
print("arrow", vol())

m.EditRebuild3
os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, "SW7_IMU_Pod_Lid.SLDPRT")
print("save error code:", m.SaveAs3(path, 0, 1), path)
m.ShowNamedView2("*Isometric", 7)
m.ViewZoomtofit2
m.SaveBMP(r"C:/Users/0geda/AppData/Local/Temp/claude/c--Users-0geda-OneDrive---University-of-Cape-Town-Documents-PlatformIO-Projects/02999ba8-77fc-45f7-8817-da26b024fcdd/scratchpad/imu_lid_iso.bmp", 1000, 700)
print("box mm:", [round(v * 1000, 2) for v in m.GetPartBox(True)])
