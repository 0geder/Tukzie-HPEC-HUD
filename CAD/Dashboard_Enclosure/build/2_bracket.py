"""Dashboard bracket: stays strapped to the tuk-tuk at the meter, and the display shell's dovetail rail slides down
into it. Closed at the bottom so the shell cannot drop through, an M4 thumb screw from the side locks it, a
saddle sits on the tube and two slots take hose clamps or 9 mm cable ties.
Frame: channel runs along Z (vertical when fitted, open end +Z), the shell side faces +Y."""
import os
import pythoncom
import win32com.client
from win32com.client import VARIANT

NONE = VARIANT(pythoncom.VT_DISPATCH, None)
mm = 0.001
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = {
    "BrW": 56.0,        # across the rail
    "BrL": 80.0,        # along the rail
    "BrH": 18.0,
    "RailW": 30.0, "RailW2": 38.0, "RailH": 6.0,   # must match the shell
    "Slide": 0.3,       # clearance each side of the rail
    "StopT": 6.0,       # closed end
    "TubeD": 32.0,      # MEASURE: diameter of the tube or bar the bracket straps to
    "SaddleD": 3.0,     # how deep the saddle sits into the bracket
    "StrapX": 17.0, "StrapW": 9.0, "StrapT": 3.5, "StrapY0": 5.0,
    "LockY": 15.0, "LockD": 3.3,   # M4 tapping hole (or 4.2 with a heat-set insert)
}
G = P
sw = win32com.client.GetActiveObject("SldWorks.Application")
sw.SetUserPreferenceToggle(10, False)
m = sw.NewDocument(sw.GetUserPreferenceStringValue(8), 0, 0, 0)
sm, fm, eq = m.SketchManager, m.FeatureManager, m.GetEquationMgr
for k, v in P.items():
    eq.Add2(-1, f'"{k}" = {v}', True)


def vol():
    return round(m.Extension.CreateMassProperty.Volume * 1e9, 1)


def select(name, kind):
    if not m.Extension.SelectByID2(name, kind, 0, 0, 0, False, 0, NONE, 0):
        raise SystemExit(f"could not select {kind} {name}")


def sketch(plane):
    m.ClearSelection2(True)
    select(plane, "PLANE")
    sm.InsertSketch(True)
    sm.AddToDB = True
    return m.GetActiveSketch2.Name


def close_and_select(name):
    sm.AddToDB = False
    sm.InsertSketch(True)
    m.ClearSelection2(True)
    select(name, "SKETCH")


def poly(pts):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        sm.CreateLine(x1 * mm, y1 * mm, 0, x2 * mm, y2 * mm, 0)


def cut2(name, t1, t2, d1, d2, flip=False, single=False):
    """Cut both ways from the sketch plane (t = 0 blind, 1 through all); checks material was removed."""
    before = vol()
    close_and_select(name)
    f = fm.FeatureCut4(single, flip, False, t1, t2, d1 * mm, d2 * mm, False, False, False, False, 0, 0,
                       False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
    if f is None or vol() >= before - 0.001:
        raise SystemExit(f"cut from {name} removed nothing")
    return f


# 1. Block.
s = sketch("Front Plane")
w, h = G["BrW"] / 2, G["BrH"]
poly([(-w, 0), (w, 0), (w, h), (-w, h)])
close_and_select(s)
blk = fm.FeatureExtrusion2(True, False, False, 6, 0, G["BrL"] * mm, 0, False, False, False, False,
                           0, 0, False, False, False, False, True, True, True, 0, 0, False)
blk.Name = "Bracket Block"
eq.Add2(-1, '"D1@Bracket Block" = "BrL"', True)
print("block", vol())

# 2. Dovetail channel: open through the +Z end, stops StopT short of the -Z end.
s = sketch("Front Plane")
a = G["RailW"] / 2 + G["Slide"]
b = G["RailW2"] / 2 + G["Slide"]
y_bot = h - G["RailH"] - G["Slide"]
poly([(-a, h + 0.5), (a, h + 0.5), (b, y_bot), (-b, y_bot)])
ch = cut2(s, 0, 0, G["BrL"] / 2 + 1, G["BrL"] / 2 - G["StopT"])
ch.Name = "Dovetail Channel"
z_open = m.GetPartBox(True)
print("channel", vol())

# 3. Tube saddle along X under the bracket.
s = sketch("Right Plane")
r = G["TubeD"] / 2
sm.CreateCircleByRadius(0, (G["SaddleD"] - r) * mm, 0, r * mm)
sad = cut2(s, 1, 1, 0, 0)
sad.Name = "Tube Saddle"
print("saddle", vol())

# 4. Strap slots through the length, between the saddle and the channel floor.
s = sketch("Front Plane")
for sx in (-1, 1):
    x0 = sx * G["StrapX"] - G["StrapW"] / 2
    poly([(x0, G["StrapY0"]), (x0 + G["StrapW"], G["StrapY0"]),
          (x0 + G["StrapW"], G["StrapY0"] + G["StrapT"]), (x0, G["StrapY0"] + G["StrapT"])])
st = cut2(s, 1, 1, 0, 0)
st.Name = "Strap Slots"
print("straps", vol())

# 5. Locking screw hole through the +X wall into the channel.
s = sketch("Right Plane")
sm.CreateCircleByRadius(0, G["LockY"] * mm, 0, G["LockD"] / 2 * mm)
before = vol()
close_and_select(s)
lk = fm.FeatureCut4(True, False, False, 1, 0, 0, 0, False, False, False, False, 0, 0,
                    False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
if lk is None or vol() >= before - 0.001:
    if lk is not None:
        m.EditUndo2(1)
    m.ClearSelection2(True)
    select(s, "SKETCH")
    lk = fm.FeatureCut4(True, True, False, 1, 0, 0, 0, False, False, False, False, 0, 0,
                        False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
lk.Name = "Lock Screw Hole"
print("lock", vol())

m.EditRebuild3
path = os.path.join(OUT, "SW7_Dash_Bracket.SLDPRT")
print("save:", m.SaveAs3(path, 0, 1), path)
m.ShowNamedView2("*Isometric", 7)
m.ViewZoomtofit2
m.SaveBMP(os.path.join(os.environ.get("SW7_SHOT_DIR", OUT), "dash_bracket_iso.bmp"), 1000, 700)
print("box mm:", [round(v * 1000, 2) for v in m.GetPartBox(True)])
