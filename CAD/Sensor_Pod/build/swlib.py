"""Small SolidWorks API layer for the sensor pod scripts, built on the lessons from CAD/Dashboard_Enclosure/build.

Everything takes pod coordinates in mm (X right, Y forward, Z up). Model axes: X = pod X, Y = pod Z, Z = -pod Y.
Checked on SolidWorks 2025 (12 Oct 2026):
  Top Plane sketch (u, v)   -> pod (X, Y) = (u, v), normal +pod Z
  Front Plane sketch (u, v) -> pod (X, Z) = (u, v), normal -pod Y
  Right Plane sketch (u, v) -> pod (Y, Z) = (u, v), normal +pod X
  FeatureExtrusion2: third argument False extrudes along +normal.
  FeatureCut4: second argument flips the side kept (never use it), third argument True cuts along +normal.
  Draft: Ddir1 True is outward. Offset planes: flag 8, plus 256 for a negative offset.
  An angled plane = a Top-plane sketch line selected with its end point (mark 1), InsertRefPlane(2, 0, 4, ...).
Every cut is checked by volume; a cut that removes nothing stops the script.
"""
import atexit
import math
import os
import time
import types
import pythoncom
import win32com.client
from win32com.client import VARIANT

NONE = VARIANT(pythoncom.VT_DISPATCH, None)
mm = 0.001
BASE = {"Z": "Top Plane", "Y": "Front Plane", "X": "Right Plane"}
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
PRINT = os.path.join(OUT, "print_parts")
REF = os.path.join(OUT, "reference_parts")
PREV = os.path.join(OUT, "previews")

sw = win32com.client.GetActiveObject("SldWorks.Application")
sw.SetUserPreferenceToggle(10, False)      # no dimension pop-ups while scripting
OPENED = []          # titles of documents this run created or opened; closed at exit, even after an error


@atexit.register
def _close_all():
    for t in OPENED:
        try:
            sw.CloseDoc(t)
        except Exception:
            pass


def model_pt(x, y, z):
    return (x * mm, z * mm, -y * mm)


def invoke(obj, name, kind, *args):
    """Call a method or property by dispatch id (late binding cannot see some of them by name)."""
    o = obj._oleobj_
    return o.Invoke(o.GetIDsOfNames(name), 0, kind, True, *args)


def call0(obj, name):
    """Zero-argument API call: late binding exposes some as properties and some as methods."""
    a = getattr(obj, name)
    return a() if isinstance(a, types.MethodType) else a


def arr(vals):
    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [float(v) for v in vals])


class Part:
    def __init__(self, globals_=None):
        time.sleep(1)
        self.m = sw.NewDocument(sw.GetUserPreferenceStringValue(8), 0, 0, 0)
        if self.m is None:
            raise SystemExit("could not create a part")
        OPENED.append(self.m.GetTitle)
        self.sm, self.fm, self.eq = self.m.SketchManager, self.m.FeatureManager, self.m.GetEquationMgr
        self.planes = {}
        for k, v in (globals_ or {}).items():
            self.eq.Add2(-1, f'"{k}" = {round(float(v), 4)}', True)

    # ---- queries ----
    def vol(self):
        return round(self.m.Extension.CreateMassProperty.Volume * 1e9, 1)

    def box(self):
        """Pod-frame bounding box: x0, x1, y0, y1, z0, z1."""
        b = [v / mm for v in self.m.GetPartBox(True)]
        return [round(v, 1) for v in (b[0], b[3], -b[5], -b[2], b[1], b[4])]

    def size(self):
        b = self.box()
        return [round(b[1] - b[0], 1), round(b[3] - b[2], 1), round(b[5] - b[4], 1)]

    # ---- planes and sketches ----
    def select(self, name, kind, append=False, mark=0):
        if not self.m.Extension.SelectByID2(name, kind, 0, 0, 0, append, mark, NONE, 0):
            raise SystemExit(f"could not select {kind} {name}")

    def plane(self, axis, n):
        """Plane normal to the axis at normal coordinate n (model coordinates along the base plane normal)."""
        n = round(n, 4)
        if abs(n) < 1e-6:
            return BASE[axis]
        key = (axis, n)
        if key not in self.planes:
            self.m.ClearSelection2(True)
            self.select(BASE[axis], "PLANE")
            p = self.fm.InsertRefPlane(8 | (256 if n < 0 else 0), abs(n) * mm, 0, 0, 0, 0)
            if p is None:
                raise SystemExit(f"plane {axis} {n} failed")
            p.Name = f"P{axis}{'m' if n < 0 else ''}{abs(n):g}".replace(".", "_")
            self.planes[key] = p.Name
        return self.planes[key]

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

    def draw(self, shapes, xf=None):
        """shapes: ("poly", [(u, v), ...]) | ("rect", u0, v0, u1, v1) | ("circle", u, v, r) in sketch-plane mm,
        or with xf given, ("poly3", [(x, y, z) pod]) | ("circle3", (x, y, z), r)."""
        for s in shapes:
            k = s[0]
            if k == "rect":
                _, u0, v0, u1, v1 = s
                s = ("poly", [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
                k = "poly"
            if k == "poly":
                pts = s[1]
                for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
                    self.sm.CreateLine(x1 * mm, y1 * mm, 0, x2 * mm, y2 * mm, 0)
            elif k == "circle":
                self.sm.CreateCircleByRadius(s[1] * mm, s[2] * mm, 0, s[3] * mm)
            elif k == "poly3":
                pts = [self.to_sketch(xf, p) for p in s[1]]
                for a, b in zip(pts, pts[1:] + pts[:1]):
                    self.sm.CreateLine(a[0], a[1], 0, b[0], b[1], 0)
            elif k == "circle3":
                c = self.to_sketch(xf, s[1])
                self.sm.CreateCircleByRadius(c[0], c[1], 0, s[2] * mm)
            else:
                raise ValueError(k)

    def to_sketch(self, xf, p):
        mu = sw.GetMathUtility
        pt = win32com.client.Dispatch(invoke(mu, "CreatePoint", pythoncom.DISPATCH_METHOD, arr(model_pt(*p))))
        return pt.MultiplyTransform(xf).ArrayData

    @staticmethod
    def nrange(axis, a, b):
        return (-b, -a) if axis == "Y" else (a, b)

    # ---- features ----
    def _extrude(self, name, depth, rev, merge=True, draft=0.0):
        self.close(name)
        return self.fm.FeatureExtrusion2(True, False, rev, 0, 0, depth * mm, 0, draft > 0, False, True, False,
                                         math.radians(draft), 0, False, False, False, False, merge, True, True,
                                         0, 0, False)

    def _cut(self, name, depth, rev, draft=0.0):
        self.close(name)
        return self.fm.FeatureCut4(True, False, rev, 0, 0, depth * mm, 0, draft > 0, False, True, False,
                                   math.radians(draft), 0, False, False, False, False, False, True, True, True,
                                   True, False, 0, 0, False, False)

    def prism(self, axis, shapes, a, b, label, merge=True):
        """Solid between pod coordinates a < b along the axis (Z: Top, Y: Front, X: Right sketch plane)."""
        n0, n1 = self.nrange(axis, a, b)
        s = self.sketch(self.plane(axis, n0))
        self.draw(shapes)
        before = self.vol()
        f = self._extrude(s, n1 - n0, False, merge)
        if f is None:
            raise SystemExit(f"{label}: extrusion failed")
        f.Name = label
        print(f"  {label}: +{round(self.vol() - before, 1)} mm3")
        return f

    def cut(self, axis, shapes, a, b, label, need=True):
        n0, n1 = self.nrange(axis, a, b)
        s = self.sketch(self.plane(axis, n0))
        self.draw(shapes)
        before = self.vol()
        f = self._cut(s, n1 - n0, True)
        return self._check(f, before, label, need)

    def cut_through(self, axis, shapes, label, need=True):
        """Through all, both directions."""
        s = self.sketch(BASE[axis])
        self.draw(shapes)
        before = self.vol()
        self.close(s)
        f = self.fm.FeatureCut4(False, False, False, 1, 1, 0, 0, False, False, False, False, 0, 0, False, False,
                                False, False, False, True, True, True, True, False, 0, 0, False, False)
        return self._check(f, before, label, need)

    def _check(self, f, before, label, need):
        removed = round(before - self.vol(), 1)
        if f is None or removed <= 0.001:
            if f is not None:
                self.m.EditUndo2(1)
            if need:
                raise SystemExit(f"{label}: cut removed nothing")
            print(f"  {label}: nothing to remove (skipped)")
            return None
        f.Name = label
        print(f"  {label}: -{removed} mm3")
        return f

    def planar_face(self, face_pt, normal):
        """The planar face through the pod point face_pt whose outward normal is the pod direction `normal`."""
        want_n = (normal[0], normal[2], -normal[1])
        p = model_pt(*face_pt)
        for body in self.m.GetBodies2(0, False):
            for f in call0(body, "GetFaces"):
                srf = call0(f, "GetSurface")
                if not call0(srf, "IsPlane"):
                    continue
                pp = call0(srf, "PlaneParams")                     # normal (3), root point (3)
                n = pp[:3]
                if call0(f, "FaceInSurfaceSense"):
                    n = [-v for v in n]
                if sum(a * b for a, b in zip(n, want_n)) < 0.999:
                    continue
                if abs(sum((p[i] - pp[3 + i]) * n[i] for i in range(3))) > 1e-6:
                    continue
                cp = f.GetClosestPointOn(*p)
                if cp is not None and math.dist(cp[:3], p) < 1e-6:
                    return f
        return None

    def shell(self, face_pt, t, label, normal=(0, 0, 1)):
        """Hollow the solid, removing the planar face through face_pt with outward normal `normal` (pod)."""
        self.m.ClearSelection2(True)
        f = self.planar_face(face_pt, normal)
        if f is None or not f.Select4(False, NONE):
            raise SystemExit(f"{label}: no face at {face_pt}")
        before = self.vol()
        self.m.InsertFeatureShell(t * mm, False)
        if self.vol() >= before:
            raise SystemExit(f"{label}: shell failed")
        f = self.m.FeatureByPositionReverse(0)
        f.Name = label
        print(f"  {label}: -{round(before - self.vol(), 1)} mm3")

    def beam_plane(self, x, y, bearing):
        """Vertical plane through (x, y) normal to a horizontal beam at the bearing (0 = +Y, 90 = +X).
        Returns (plane name, sign): sign +1 if the beam points along the plane's +normal."""
        b = math.radians(bearing)
        d = (math.sin(b), math.cos(b))
        self.m.ClearSelection2(True)
        self.select("Top Plane", "PLANE")
        self.sm.InsertSketch(True)
        self.sm.AddToDB = True
        self.sm.CreateLine((x - 10 * d[0]) * mm, (y - 10 * d[1]) * mm, 0, x * mm, y * mm, 0)
        sk = self.m.GetActiveSketch2.Name
        self.sm.AddToDB = False
        self.sm.InsertSketch(True)
        self.m.ClearSelection2(True)
        self.select("Line1@" + sk, "EXTSKETCHSEGMENT")
        self.select("Point2@" + sk, "EXTSKETCHPOINT", True, 1)
        p = self.fm.InsertRefPlane(2, 0, 4, 0, 0, 0)
        if p is None:
            raise SystemExit("beam plane failed")
        self.m.ClearSelection2(True)
        self.select(p.Name, "PLANE")
        self.sm.InsertSketch(True)
        xf = self.m.GetActiveSketch2.ModelToSketchTransform
        z = self.to_sketch(xf, (x + d[0], y + d[1], 0))[2]
        self.sm.InsertSketch(True)
        return p.Name, (1 if z > 0 else -1)

    def beam_feature(self, chip, bearing, shape, start, length, draft, label, cut=True, merge=True):
        """Drafted extrusion or cut along a horizontal beam from the chip (x, y, z).
        shape: ("rect", w, h) or ("circle", r), drawn at `start` mm along the beam."""
        x, y, z = chip
        b = math.radians(bearing)
        d = (math.sin(b), math.cos(b))
        t = (math.cos(b), -math.sin(b))
        sx, sy = x + d[0] * start, y + d[1] * start
        pname, sign = self.beam_plane(sx, sy, bearing)
        s = self.sketch(pname)
        xf = self.m.GetActiveSketch2.ModelToSketchTransform
        if shape[0] == "rect":
            w, h = shape[1] / 2, shape[2] / 2
            pts = [(sx + t[0] * u, sy + t[1] * u, z + v) for u, v in ((-w, -h), (w, -h), (w, h), (-w, h))]
            self.draw([("poly3", pts)], xf)
        else:
            self.draw([("circle3", (sx, sy, z), shape[1])], xf)
        before = self.vol()
        if cut:
            f = self._cut(s, length, sign > 0, draft)
            return self._check(f, before, label, True)
        f = self._extrude(s, length, sign < 0, merge, draft)
        if f is None:
            raise SystemExit(label + " failed")
        f.Name = label
        print(f"  {label}: +{round(self.vol() - before, 1)} mm3")
        return f

    # ---- output ----
    def save(self, path, shot=None, view="*Isometric"):
        call0(self.m, "EditRebuild3")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        err = self.m.SaveAs3(path, 0, 1)
        print("save", os.path.basename(path), "error code", err, "size", self.size(), "box", self.box())
        if err != 0:
            raise SystemExit("save failed (is the file open in SolidWorks? look for a ~$ lock file)")
        if shot:
            snap(self.m, shot, view)
        return err

    def close_doc(self):
        sw.CloseDoc(self.m.GetTitle)
        time.sleep(1)


def hide_refs(m):
    """Hide reference planes and sketches so the pictures show only solids."""
    f = m.FirstFeature
    while f is not None:
        t = f.GetTypeName2
        if t in ("RefPlane", "ProfileFeature", "3DProfileFeature"):
            m.ClearSelection2(True)
            f.Select2(False, 0)
            call0(m, "BlankRefGeom" if t == "RefPlane" else "BlankSketch")
        f = f.GetNextFeature
    m.ClearSelection2(True)


def snap(m, png, view="*Isometric", w=1400, h=1000):
    """view: a named view, or "front_iso" (isometric from the front-right-above of the pod)."""
    os.makedirs(PREV, exist_ok=True)
    hide_refs(m)
    if view == "front_iso":
        m.ShowNamedView2("*Isometric", -1)
        m.ActiveView.RotateAboutAxis(-math.pi / 2, 0, 0, 0, 0, 1, 0)
    else:
        m.ShowNamedView2(view, -1)
    call0(m, "ViewZoomtofit2")
    bmp = os.path.join(PREV, png.replace(".png", ".bmp"))
    m.SaveBMP(bmp, w, h)
    try:
        from PIL import Image
        Image.open(bmp).save(os.path.join(PREV, png))
        os.remove(bmp)
    except Exception as e:      # keep the BMP if Pillow is missing
        print("png conversion skipped:", e)


def chamfer_poly(x0, x1, y0, y1, c_front=0.0, c_rear=0.0):
    """Rectangle (u0..u1, v0..v1) with 45 deg corner chamfers c_front on the +v corners and c_rear on the -v ones."""
    pts = []
    pts += [(x0 + c_rear, y0), (x1 - c_rear, y0)] if c_rear else [(x0, y0), (x1, y0)]
    pts += [(x1, y0 + c_rear)] if c_rear else []
    pts += [(x1, y1 - c_front), (x1 - c_front, y1), (x0 + c_front, y1), (x0, y1 - c_front)] if c_front \
        else [(x1, y1), (x0, y1)]
    pts += [(x0, y0 + c_rear)] if c_rear else []
    return pts
