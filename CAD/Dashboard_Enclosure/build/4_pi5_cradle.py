"""Raspberry Pi 5 cradle for the back of the dashboard shell, on the left (connector) side.

Modelled in the shell's frame: the cradle's base sits on the shell's back face (Y = 0) and everything grows towards
-Y, so its coordinates are the shell's and the bolt holes line up directly. It bolts through the shell with four M3:
two either side of the Z split line, so it also joins the two left quarters. It sits 10 mm above centre
to keep the USB end 13 mm clear of the handlebar.

The Pi screws to four standoffs with M2.5 x 6 screws (pilot 2.2 mm), component side out, USB and Ethernet end
pointing down (+Z) so the cables hang and water runs off. Screws rather than snap clips: the vehicle shakes, and
clips on a 1.6 mm board walk loose. The bolts under the board go in first.
Pi 5 (official drawing): 85 x 56 mm, holes 58 x 49 mm, 3.5 mm from the non-USB end and the long edges."""
import os
import pythoncom
import win32com.client
from win32com.client import VARIANT

NONE = VARIANT(pythoncom.VT_DISPATCH, None)
mm = 0.001
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "print_parts")

src = open(os.path.join(HERE, "1_back_shell.py"), encoding="utf-8").read()
ns = {}
exec(src[src.index("RAIL_CZ ="):src.index("L = P[")], ns)
BOLTS = ns["PI_HOLES"]

P = {"BaseT": 3.0, "StandH": 7.0, "StandD": 6.0, "PilotD": 2.2, "BoltD": 3.4,
     "PiCX": -98.0, "PiCZ": -20.0,          # centre of the Pi's hole pattern on the shell's back
     "HoleL": 58.0, "HoleW": 49.0}
X0, X1, Z0, Z1 = -131.0, -65.0, -57.5, 37.5     # base outline (66 x 95 mm)

sw = win32com.client.GetActiveObject("SldWorks.Application")
sw.SetUserPreferenceToggle(10, False)
m = sw.NewDocument(sw.GetUserPreferenceStringValue(8), 0, 0, 0)
sm, fm, eq = m.SketchManager, m.FeatureManager, m.GetEquationMgr
for k, v in P.items():
    eq.Add2(-1, f'"{k}" = {v}', True)


def vol():
    return round(m.Extension.CreateMassProperty.Volume * 1e9, 1)


def box():
    return [round(v * 1000, 1) for v in m.GetPartBox(True)]


def sketch(plane):
    m.ClearSelection2(True)
    m.Extension.SelectByID2(plane, "PLANE", 0, 0, 0, False, 0, NONE, 0)
    sm.InsertSketch(True)
    sm.AddToDB = True
    return m.GetActiveSketch2.Name


def close(name):
    sm.AddToDB = False
    sm.InsertSketch(True)
    m.ClearSelection2(True)
    m.Extension.SelectByID2(name, "SKETCH", 0, 0, 0, False, 0, NONE, 0)


def extrude_down(name, depth, merge=True):
    """Extrude towards -Y; tries both directions and keeps the one that grows downwards."""
    for rev in (False, True):
        close(name)
        f = fm.FeatureExtrusion2(True, False, rev, 0, 0, depth * mm, 0, False, False, False, False,
                                 0, 0, False, False, False, False, merge, True, True, 0, 0, False)
        if f is not None and box()[4] < 0.05:
            return f
        if f is not None:
            m.EditUndo2(1)
    raise SystemExit("could not extrude " + name + " downwards")


def zs(z):
    return -z          # Top plane sketch y is -Z


# Base plate.
s = sketch("Top Plane")
sm.CreateCornerRectangle(X0 * mm, zs(Z0) * mm, 0, X1 * mm, zs(Z1) * mm, 0)
f = extrude_down(s, P["BaseT"])
f.Name = "Cradle Base"
print("base", vol(), box())

# Standoffs, from the Top plane through the base (merged).
STAND = [(P["PiCX"] + sx * P["HoleW"] / 2, P["PiCZ"] + sz * P["HoleL"] / 2) for sx in (-1, 1) for sz in (-1, 1)]
s = sketch("Top Plane")
for x, z in STAND:
    sm.CreateCircleByRadius(x * mm, zs(z) * mm, 0, P["StandD"] / 2 * mm)
f = extrude_down(s, P["BaseT"] + P["StandH"])
f.Name = "Standoffs"
print("standoffs", vol(), box())

# Pilot holes in the standoffs and bolt holes in the base, through everything.
s = sketch("Top Plane")
for x, z in STAND:
    sm.CreateCircleByRadius(x * mm, zs(z) * mm, 0, P["PilotD"] / 2 * mm)
for x, z in BOLTS:
    sm.CreateCircleByRadius(x * mm, zs(z) * mm, 0, P["BoltD"] / 2 * mm)
before = vol()
close(s)
f = fm.FeatureCut4(False, False, False, 1, 1, 0, 0, False, False, False, False, 0, 0,
                   False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
if f is None or vol() >= before:
    raise SystemExit("holes failed")
f.Name = "Pilot and Bolt Holes"
print("holes", vol())

# Orientation mark: a notch in the bottom (+Z, USB end) edge.
s = sketch("Top Plane")
sm.CreateCornerRectangle((P["PiCX"] - 4) * mm, zs(Z1 - 3) * mm, 0, (P["PiCX"] + 4) * mm, zs(Z1 + 1) * mm, 0)
close(s)
f = fm.FeatureCut4(False, False, False, 1, 1, 0, 0, False, False, False, False, 0, 0,
                   False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
if f is not None:
    f.Name = "USB End Notch"

m.EditRebuild3
os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, "SW7_Dash_Pi5_Cradle.SLDPRT")
print("save:", m.SaveAs3(path, 0, 1), path)
m.ShowNamedView2("*Isometric", 7)
m.ViewZoomtofit2
m.SaveBMP(os.path.join(os.environ.get("SW7_SHOT_DIR", OUT), "dash_pi5_cradle.bmp"), 1000, 700)
print("box mm:", box(), "bolts", BOLTS, "standoffs", STAND)
