"""IMU pod step 3: redo the strap slots at StrapX = 13 (clear of the board pilot holes), with the slot sketch
dimensioned and linked to the globals, then save the part."""
import os
import pythoncom
import win32com.client
from win32com.client import VARIANT

NONE = VARIANT(pythoncom.VT_DISPATCH, None)
mm = 0.001
OUT = r"C:\Users\0geda\OneDrive - University of Cape Town\Documents\PlatformIO\Projects\Tukzie-HPEC-HUD\CAD\IMU_Pod"

sw = win32com.client.GetActiveObject("SldWorks.Application")
m = sw.ActiveDoc
sm, fm, eq = m.SketchManager, m.FeatureManager, m.GetEquationMgr


def vol():
    return round(m.Extension.CreateMassProperty.Volume * 1e9, 1)


def select(name, kind, append=False):
    if not m.Extension.SelectByID2(name, kind, 0, 0, 0, append, 0, NONE, 0):
        raise SystemExit(f"could not select {kind} {name}")


def set_global(name, value):
    for i in range(eq.GetCount):
        if eq.Equation(i).split("=")[0].strip().strip('"') == name:
            eq.Equation(i, f'"{name}" = {value}')
            return
    eq.Add2(-1, f'"{name}" = {value}', True)


# Remove the first strap-slot cut and its sketch.
m.ClearSelection2(True)
select("Cut-Extrude5", "BODYFEATURE")
m.Extension.DeleteSelection2(1)            # swDelete_Absorbed: also deletes the sketch
print("after delete", vol())

set_global("StrapX", 13.0)
sx_, swd, st, sz0 = 13.0, 6.0, 3.5, 1.5
m.ClearSelection2(True)
select("Front Plane", "PLANE")
sm.InsertSketch(True)
name = m.GetActiveSketch2.Name
for sx in (-1, 1):
    x0 = sx * sx_ - swd / 2
    sm.CreateCornerRectangle(x0 * mm, sz0 * mm, 0, (x0 + swd) * mm, (sz0 + st) * mm, 0)
sm.InsertSketch(True)
m.ClearSelection2(True)
select(name, "SKETCH")
slot = fm.FeatureCut4(False, False, False, 1, 1, 0, 0, False, False, False, False, 0, 0,
                      False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
slot.Name = "Strap Slots"
print("strap slots:", slot.Name, "volume", vol())

# Name the other features for the student.
for old, new in (("Boss-Extrude1", "Pod Body"), ("Cut-Extrude1", "Board Pocket"), ("Cut-Extrude2", "Board Pilot Holes"),
                 ("Cut-Extrude3", "Lid Pilot Holes"), ("Cut-Extrude4", "Cable Exit")):
    f = m.FeatureByName(old)
    if f is not None:
        f.Name = new
m.EditRebuild3

os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, "SW7_IMU_Pod_Base.SLDPRT")
errs = m.Extension.SaveAs3(path, 0, 1, NONE, NONE, 0, 0) if False else None
ok = m.SaveAs3(path, 0, 1)                 # swSaveAsCurrentVersion, swSaveAsOptions_Silent
print("saved:", ok, path)
print("box mm:", [round(v * 1000, 2) for v in m.GetPartBox(True)], "volume", vol())
