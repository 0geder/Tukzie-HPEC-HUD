"""Handlebar clamp bracket. It stays bolted to the handlebar; the display shell's dovetail rail slides down into it
and an M4 thumb screw from underneath drops into a detent in the rail, so the display clips on and off without tools.

Two parts:
  SW7_Dash_Bracket.SLDPRT     dovetail channel on top (closed at the bottom end), upper half of the bar clamp below,
                              two M5 heat-set insert holes.
  SW7_Dash_Clamp_Cap.SLDPRT   lower half of the clamp, two plain M5 clearance holes (bolt heads with washers).
Wrap the bar with a 1 mm rubber strip (a piece of bicycle inner tube) under the clamp: it grips, stops the chrome
from being scratched and takes up small differences in bar size.

Frame: the bar runs along X (left to right), the channel along Z (vertical when fitted), the display side faces
+Y. The clamp's split plane, and the bar's centre, is at Y = ClampY. The script prints which Z end is closed; that
end goes down. Three things stop the display falling: the closed end of the channel carries its weight, the thumb
screw in the rail's detent stops it lifting out over bumps, and the two M5 bolts clamp the bar.

Revision 2 (12 Oct, engineering review D1, D2, D5, D6, D8, D15): cap 17 mm thick so the bore no longer cuts through
it; clamp 52 mm across the bar with the M5 inserts at +/-18.5 (3.2 mm wall to the bore, 4.3 mm to the outside);
blind 10 mm insert holes; a 1.5 mm squeeze gap at the split; a parallel dovetail (rail offset 0.35 mm); the lock
moved from the side (its head hit the rail plate) to a vertical M4 insert under the channel at Z -30."""
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
    "BrH": 18.0,        # channel block height
    "RailW": 30.0, "RailW2": 38.0, "RailH": 6.0,   # must match the rail plate
    "Slide": 0.3,       # clearance each side of the rail
    "StopT": 6.0,       # closed end of the channel
    "TubeD": 22.2,      # MEASURE: handlebar diameter (22.2 mm = 7/8 in is standard; 25.4 mm = 1 in on some bars)
    "Liner": 1.0,       # rubber strip under the clamp
    "ClampW": 40.0,     # clamp length along the bar (needs this much straight bar)
    "ClampZ": 26.0,     # clamp half-size across the bar (review D2)
    "ClampY": -12.0,    # split plane, below the channel block
    "CapT": 17.0,       # cap thickness below the split plane (review D1)
    "Gap": 0.75,        # taken off each split face: 1.5 mm squeeze gap (review D6)
    "BoltZ": 18.5,      # M5 bolt positions either side of the bar (review D2)
    "InsertD": 6.4, "InsertL": 10.0,   # M5 heat-set insert hole
    "BoltD": 5.5,                      # M5 x 30 socket head with a washer, from below
    "LockZ": -30.0,     # M4 lock: vertical, from underneath, 4 mm in from the rail's upper end
    "LockInsD": 5.6, "LockInsL": 8.0, "LockClear": 4.5,   # M4 heat-set insert, then clearance into the channel
    "DovOff": 0.35,     # dovetail: channel = rail offset this much normal to the flanks (review D8)
}
G = P
R = (G["TubeD"] + 2 * G["Liner"]) / 2
sw = win32com.client.GetActiveObject("SldWorks.Application")
sw.SetUserPreferenceToggle(10, False)


class Part:
    def __init__(self):
        self.m = sw.NewDocument(sw.GetUserPreferenceStringValue(8), 0, 0, 0)
        self.sm, self.fm, self.eq = self.m.SketchManager, self.m.FeatureManager, self.m.GetEquationMgr
        for k, v in P.items():
            self.eq.Add2(-1, f'"{k}" = {v}', True)

    def vol(self):
        return round(self.m.Extension.CreateMassProperty.Volume * 1e9, 1)

    def box(self):
        return [round(v * 1000, 1) for v in self.m.GetPartBox(True)]

    def select(self, name, kind):
        if not self.m.Extension.SelectByID2(name, kind, 0, 0, 0, False, 0, NONE, 0):
            raise SystemExit(f"could not select {kind} {name}")

    def sketch(self, plane):
        self.m.ClearSelection2(True)
        self.select(plane, "PLANE")
        self.sm.InsertSketch(True)
        self.sm.AddToDB = True
        return self.m.GetActiveSketch2.Name

    def close(self, name):
        self.sm.AddToDB = False
        self.sm.InsertSketch(True)
        self.m.ClearSelection2(True)
        self.select(name, "SKETCH")

    def poly(self, pts):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            self.sm.CreateLine(x1 * mm, y1 * mm, 0, x2 * mm, y2 * mm, 0)

    def boss_mid(self, name, length):
        self.close(name)
        return self.fm.FeatureExtrusion2(True, False, False, 6, 0, length * mm, 0, False, False, False, False,
                                         0, 0, False, False, False, False, True, True, True, 0, 0, False)

    def cut(self, name, t1, t2, d1, d2, single=False, flip=False, label=""):
        before = self.vol()
        self.close(name)
        f = self.fm.FeatureCut4(single, flip, False, t1, t2, d1 * mm, d2 * mm, False, False, False, False, 0, 0,
                                False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
        ok = f is not None and self.vol() < before - 0.001
        if not ok and single:
            if f is not None:
                self.m.EditUndo2(1)
            self.close(name)
            f = self.fm.FeatureCut4(single, not flip, False, t1, t2, d1 * mm, d2 * mm, False, False, False, False,
                                    0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0,
                                    False, False)
            ok = f is not None and self.vol() < before - 0.001
        if not ok:
            raise SystemExit(f"{label} removed nothing")
        f.Name = label
        print(f"{label}: volume {self.vol()}")
        return f

    def save(self, fname, shot):
        self.m.EditRebuild3
        path = os.path.join(OUT, fname)
        print("save:", self.m.SaveAs3(path, 0, 1), path)
        self.m.ShowNamedView2("*Isometric", 7)
        self.m.ViewZoomtofit2
        self.m.SaveBMP(os.path.join(os.environ.get("SW7_SHOT_DIR", OUT), shot), 1000, 700)
        print("box mm:", self.box())


def channel_profile():
    """Rail (from rail_plate geometry): half width RailW/2 at the plate face, RailW2/2 at RailH from it. The channel is
    that profile offset DovOff normal to the flanks, the floor DovOff below the rail's outer face. Bracket frame: the
    plate face is at Y = BrH."""
    import math
    a, b, hgt = G["RailW"] / 2, G["RailW2"] / 2, G["RailH"]
    k = (b - a) / hgt                                   # flank: half width grows k per mm from the plate face
    off = G["DovOff"] * math.sqrt(1 + k * k)            # horizontal shift for a normal offset
    h = G["BrH"]
    y_floor = h - hgt - G["DovOff"]
    half = lambda y: a + k * (h - y) + off
    return [(-half(h + 0.5), h + 0.5), (half(h + 0.5), h + 0.5), (half(y_floor), y_floor), (-half(y_floor), y_floor)]


def cut_dir(p, sketch_name, depth, want_y_up, label):
    """Single-direction blind cut from the Top plane (Y = 0); keeps the direction that removes material on the wanted
    side (checked by the centre of mass moving away from it)."""
    for rev in (False, True):
        y0 = p.m.Extension.CreateMassProperty.CenterOfMass[1]
        v0 = p.vol()
        p.close(sketch_name)
        f = p.fm.FeatureCut4(True, False, rev, 0, 0, depth * mm, 0, False, False, False, False, 0, 0,
                             False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
        if f is not None and p.vol() < v0 - 0.001:
            moved_down = p.m.Extension.CreateMassProperty.CenterOfMass[1] < y0
            if moved_down == want_y_up:                  # removing material above lowers the centre of mass
                f.Name = label
                print(f"{label}: volume {p.vol()}")
                return f
            p.m.EditUndo2(1)
    raise SystemExit(label + " failed")


def blind_hole(p, sketch_name, r, depth, label, existing_r=0.0):
    """Blind hole from the Top plane in whichever direction removes the expected volume (pi r^2 depth less any hole
    already there); refuses a cut that removes a different amount, so a flipped or inverted cut cannot slip through."""
    import math
    want = math.pi * (r * r - existing_r * existing_r) * depth
    for rev in (False, True):
        v0 = p.vol()
        p.close(sketch_name)
        f = p.fm.FeatureCut4(True, False, rev, 0, 0, depth * mm, 0, False, False, False, False, 0, 0,
                             False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
        removed = v0 - p.vol()
        if f is not None and abs(removed - want) <= 0.1 * want:
            f.Name = label
            print(f"{label}: removed {round(removed, 1)} mm3 (expected {round(want, 1)})")
            return f
        if f is not None:
            p.m.EditUndo2(1)
    raise SystemExit(f"{label}: no direction removed the expected {round(want, 1)} mm3")


def bolt_circles(p, d):
    for sz in (-1, 1):
        p.sm.CreateCircleByRadius(0, sz * G["BoltZ"] * mm, 0, d / 2 * mm)   # Top-plane-parallel sketch: y is -Z


# ---------- Bracket (upper half) ----------
b = Part()
# 1. Channel block.
s = b.sketch("Front Plane")
w, h = G["BrW"] / 2, G["BrH"]
b.poly([(-w, 0), (w, 0), (w, h), (-w, h)])
blk = b.boss_mid(s, G["BrL"])
blk.Name = "Channel Block"
# 2. Clamp boss under it, across the bar (profile in the YZ plane, extruded along X).
s = b.sketch("Right Plane")
cz, cy = G["ClampZ"], G["ClampY"]
b.poly([(-cz, cy + G["Gap"]), (cz, cy + G["Gap"]), (cz, 0.5), (-cz, 0.5)])
boss = b.boss_mid(s, G["ClampW"])
boss.Name = "Clamp Upper Half"
print("bracket solid", b.vol(), b.box())
# 3. Dovetail channel: open through one end, stops StopT short of the other.
s = b.sketch("Front Plane")
b.poly(channel_profile())
b.cut(s, 0, 0, G["BrL"] / 2 + 1, G["BrL"] / 2 - G["StopT"], label="Dovetail Channel")
# 4. Bar bore, centred on the split plane.
s = b.sketch("Right Plane")
b.sm.CreateCircleByRadius(0, cy * mm, 0, R * mm)
b.cut(s, 1, 1, 0, 0, label="Handlebar Bore")
# 5. M5 heat-set insert holes: blind from the split face, InsertL deep (the Top plane is at Y 0, above the boss;
#    cutting down from it by |split face| reaches the split face, so cut the whole boss height where the insert goes).
s = b.sketch("Top Plane")
bolt_circles(b, G["InsertD"])
cut_dir(b, s, abs(cy + G["Gap"]), False, "M5 Insert Holes")
# 6. Lock: M4 insert from underneath at LockZ, clearance hole on into the channel.
s = b.sketch("Top Plane")
b.sm.CreateCircleByRadius(0, -G["LockZ"] * mm, 0, G["LockClear"] / 2 * mm)
b.cut(s, 1, 1, 0, 0, label="Lock Clearance Hole")
s = b.sketch("Top Plane")
b.sm.CreateCircleByRadius(0, -G["LockZ"] * mm, 0, G["LockInsD"] / 2 * mm)
blind_hole(b, s, G["LockInsD"] / 2, G["LockInsL"] - 0.0, "Lock Insert Hole", existing_r=G["LockClear"] / 2)
print("closed end side (sign of COM z):", round(b.m.Extension.CreateMassProperty.CenterOfMass[2] * 1000, 3))
b.save("SW7_Dash_Bracket.SLDPRT", "dash_bracket_iso.bmp")
sw.CloseDoc(b.m.GetTitle)

# ---------- Clamp cap (lower half) ----------
c = Part()
s = c.sketch("Right Plane")
c.poly([(-cz, cy - G["CapT"]), (cz, cy - G["CapT"]), (cz, cy - G["Gap"]), (-cz, cy - G["Gap"])])
cap = c.boss_mid(s, G["ClampW"])
cap.Name = "Clamp Lower Half"
s = c.sketch("Right Plane")
c.sm.CreateCircleByRadius(0, cy * mm, 0, R * mm)
c.cut(s, 1, 1, 0, 0, label="Handlebar Bore")
s = c.sketch("Top Plane")
bolt_circles(c, G["BoltD"])
c.cut(s, 1, 1, 0, 0, label="M5 Clearance Holes")
c.save("SW7_Dash_Clamp_Cap.SLDPRT", "dash_clamp_cap_iso.bmp")
print("cap box", c.box())
