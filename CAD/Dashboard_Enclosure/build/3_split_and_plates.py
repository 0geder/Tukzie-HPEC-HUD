"""Cut the master back shell into four quarters for the Prusa Mini (180 x 180 x 180 mm), and make the rail plate
and the joiner plate. Everything is in the shell's frame (back face at Y = 0, outside towards -Y), so the parts
line up in an assembly. The plates are modelled lying on their bolting face (Y = 0), rail or plate upwards, so
in the assembly they are flipped onto the shell's back face; the hole pattern is symmetric so that is all.

  rail plate   120 x 86 x 4 mm, low on the back (centre Z = RAIL_CZ), eight M3, across the bottom of the X split;
               carries the dovetail rail (30 to 38 mm, 6 mm high, 80 mm long) that slides into SW7_Dash_Bracket.
  joiner plate 44 x 20 x 3 mm, two: top of the X split and right of the Z split.
  cross joiner 40 x 40 x 3 mm, at the centre, one M3 into each quarter.
"""
import importlib.util
import os
import time
import pythoncom
import win32com.client
from win32com.client import VARIANT

NONE = VARIANT(pythoncom.VT_DISPATCH, None)
mm = 0.001
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
MASTER = os.path.join(OUT, "SW7_Dash_Back_Shell.SLDPRT")
QDIR = os.path.join(OUT, "print_parts")

# Hole layout comes from the shell script so the two cannot drift apart.
src = open(os.path.join(HERE, "1_back_shell.py"), encoding="utf-8").read()
ns = {}
exec(src[src.index("RAIL_CZ ="):src.index("L = P[")], ns)
RAIL_HOLES, RAIL_CZ = ns["RAIL_HOLES"], ns["RAIL_CZ"]
R = {"PlateW": 120.0, "PlateH": 86.0, "PlateT": 4.0, "RailW": 30.0, "RailW2": 38.0, "RailH": 6.0, "RailL": 80.0,
     "JoinL": 44.0, "JoinW": 20.0, "JoinT": 3.0, "JoinPitch": 24.0, "BoltD": 3.4}

sw = win32com.client.GetActiveObject("SldWorks.Application")
sw.SetUserPreferenceToggle(10, False)
os.makedirs(QDIR, exist_ok=True)


class Part:
    def __init__(self, m):
        self.m, self.sm, self.fm = m, m.SketchManager, m.FeatureManager

    def vol(self):
        return round(self.m.Extension.CreateMassProperty.Volume * 1e9, 1)

    def sketch(self, plane):
        self.m.ClearSelection2(True)
        if not self.m.Extension.SelectByID2(plane, "PLANE", 0, 0, 0, False, 0, NONE, 0):
            raise SystemExit("no plane " + plane)
        self.sm.InsertSketch(True)
        self.sm.AddToDB = True
        return self.m.GetActiveSketch2.Name

    def close(self, name):
        self.sm.AddToDB = False
        self.sm.InsertSketch(True)
        self.m.ClearSelection2(True)
        self.m.Extension.SelectByID2(name, "SKETCH", 0, 0, 0, False, 0, NONE, 0)

    def rect(self, x0, y0, x1, y1):
        self.sm.CreateCornerRectangle(x0 * mm, y0 * mm, 0, x1 * mm, y1 * mm, 0)

    def poly(self, pts):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            self.sm.CreateLine(x1 * mm, y1 * mm, 0, x2 * mm, y2 * mm, 0)

    def cut_all(self, name, label):
        before = self.vol()
        self.close(name)
        f = self.fm.FeatureCut4(False, False, False, 1, 1, 0, 0, False, False, False, False, 0, 0,
                                False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
        if f is None or self.vol() >= before - 0.001:
            raise SystemExit(label + " removed nothing")
        f.Name = label
        return f

    def extrude(self, name, depth, flip=False, mid=False):
        self.close(name)
        return self.fm.FeatureExtrusion2(True, flip, False, 6 if mid else 0, 0, depth * mm, 0, False, False, False,
                                         False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)

    def box(self):
        return [round(v * 1000, 1) for v in self.m.GetPartBox(True)]

    def save(self, path, shot=None):
        self.m.EditRebuild3
        err = self.m.SaveAs3(path, 0, 1)
        if shot:
            self.m.ShowNamedView2("*Isometric", 7)
            self.m.ViewZoomtofit2
            self.m.SaveBMP(shot, 1000, 700)
        return err


shots = os.environ.get("SW7_SHOT_DIR", QDIR)

# Quarters (skip with SW7_PLATES_ONLY=1).
for sx in (() if os.environ.get("SW7_PLATES_ONLY") else (1, -1)):
    for sz in (1, -1):
        m = sw.OpenDoc(MASTER, 1)
        if m is None:
            raise SystemExit("could not open " + MASTER)
        p = Part(m)
        s = p.sketch("Top Plane")
        p.rect(-sx * 200, -200, 0, 200)                 # remove the other half across X
        p.cut_all(s, "Keep one half (X)")
        s = p.sketch("Top Plane")
        p.rect(-200, 0, 200, sz * 200)                  # remove one half across Z (sketch y is -Z on the Top plane)
        p.cut_all(s, "Keep one quarter (Z)")
        b = p.box()
        side = ("R" if b[0] >= -0.1 else "L") + ("B" if b[2] >= -0.1 else "T")
        name = {"RT": "Right_Top", "RB": "Right_Bottom", "LT": "Left_Top", "LB": "Left_Bottom"}[side]
        path = os.path.join(QDIR, f"SW7_Dash_Shell_Q_{name}.SLDPRT")
        print(name, "box", b, "size", round(b[3] - b[0], 1), "x", round(b[5] - b[2], 1), "x", round(b[4] - b[1], 1),
              "save", p.save(path))
        sw.CloseDoc(m.GetTitle)

# Rail plate.
m = sw.NewDocument(sw.GetUserPreferenceStringValue(8), 0, 0, 0)
p = Part(m)
eq = m.GetEquationMgr
for k, v in R.items():
    eq.Add2(-1, f'"{k}" = {v}', True)
s = p.sketch("Top Plane")
p.rect(-R["PlateW"] / 2, -R["PlateH"] / 2, R["PlateW"] / 2, R["PlateH"] / 2)   # centred; sits at Z = RAIL_CZ
f = p.extrude(s, R["PlateT"])                       # plate Y 0..PlateT; Y = 0 is the face against the shell
f.Name = "Rail Plate"
s = p.sketch("Front Plane")
a, b2, t, rh = R["RailW"] / 2, R["RailW2"] / 2, R["PlateT"], R["RailH"]
p.poly([(-a, t - 0.5), (a, t - 0.5), (b2, t + rh), (-b2, t + rh)])
rail = p.extrude(s, R["RailL"], mid=True)
rail.Name = "Dovetail Rail"
s = p.sketch("Top Plane")
for x, z in RAIL_HOLES:
    p.sm.CreateCircleByRadius(x * mm, (z - RAIL_CZ) * mm, 0, R["BoltD"] / 2 * mm)   # pattern is symmetric
p.cut_all(s, "Bolt Holes")
print("rail plate box", p.box(), "volume", p.vol(),
      "save", p.save(os.path.join(QDIR, "SW7_Dash_Rail_Plate.SLDPRT"), os.path.join(shots, "dash_rail_plate.bmp")))
sw.CloseDoc(m.GetTitle)

# Joiner plate (one part, print two).
time.sleep(2)
m = sw.NewDocument(sw.GetUserPreferenceStringValue(8), 0, 0, 0)
p = Part(m)
s = p.sketch("Top Plane")
p.rect(-R["JoinL"] / 2, -R["JoinW"] / 2, R["JoinL"] / 2, R["JoinW"] / 2)
f = p.extrude(s, R["JoinT"])
f.Name = "Joiner Plate"
s = p.sketch("Top Plane")
for sx in (-1, 1):
    p.sm.CreateCircleByRadius(sx * R["JoinPitch"] / 2 * mm, 0, 0, R["BoltD"] / 2 * mm)
p.cut_all(s, "Bolt Holes")
print("joiner box", p.box(), "save", p.save(os.path.join(QDIR, "SW7_Dash_Joiner_Plate.SLDPRT")))
sw.CloseDoc(m.GetTitle)

# Cross joiner at the centre, one bolt into each quarter.
time.sleep(2)
m = sw.NewDocument(sw.GetUserPreferenceStringValue(8), 0, 0, 0)
p = Part(m)
s = p.sketch("Top Plane")
p.rect(-20, -20, 20, 20)
f = p.extrude(s, R["JoinT"])
f.Name = "Cross Joiner"
s = p.sketch("Top Plane")
for sx in (-1, 1):
    for sz in (-1, 1):
        p.sm.CreateCircleByRadius(sx * 12 * mm, sz * 12 * mm, 0, R["BoltD"] / 2 * mm)
p.cut_all(s, "Bolt Holes")
print("cross joiner box", p.box(), "save", p.save(os.path.join(QDIR, "SW7_Dash_Cross_Joiner.SLDPRT")))
sw.CloseDoc(m.GetTitle)
