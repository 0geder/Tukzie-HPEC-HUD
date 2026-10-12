"""Build the SW-7 IMU pod in SolidWorks through its API, driven by global variables (Tools > Equations).

Step 1: base block with a board pocket. Dimensions in mm here, metres in the API.
Placeholders marked MEASURE are typical GY-521 (MPU-6050) values, to be replaced with the student's measurements.
"""
import os
import pythoncom
import win32com.client
from win32com.client import VARIANT

OUT_DIR = r"C:\Users\0geda\OneDrive - University of Cape Town\Documents\PlatformIO\Projects\Tukzie-HPEC-HUD\CAD\IMU_Pod"
PARAMS = [                      # name, value (mm), meaning
    ("PodL", 44.0, "pod length along the vehicle (X)"),
    ("PodW", 30.0, "pod width (Z)"),
    ("PodH", 12.0, "pod height (Y)"),
    ("BoardL", 21.5, "MEASURE: GY-521 board length"),
    ("BoardW", 16.5, "MEASURE: GY-521 board width"),
    ("Clear", 0.6, "clearance around the board"),
    ("PocketD", 5.0, "pocket depth from the top"),
]
NONE = VARIANT(pythoncom.VT_DISPATCH, None)
mm = 0.001


def connect():
    sw = win32com.client.GetActiveObject("SldWorks.Application")
    sw.Visible = True
    return sw


def new_part(sw):
    template = sw.GetUserPreferenceStringValue(8)
    model = sw.NewDocument(template, 0, 0, 0)
    if model is None:
        raise SystemExit("could not create a part from " + template)
    return model


def select(model, name, kind, append=False):
    ok = model.Extension.SelectByID2(name, kind, 0, 0, 0, append, 0, NONE, 0)
    if not ok:
        raise SystemExit(f"could not select {kind} {name}")


def add_globals(model):
    eq = model.GetEquationMgr
    for name, value, _ in PARAMS:
        eq.Add2(-1, f'"{name}" = {value}', True)
    return eq


def dim(model, seg, value_mm, at):
    """Select a sketch segment, add a dimension placed at `at` (m), set its value; returns the dimension name."""
    model.ClearSelection2(True)
    seg.Select4(False, NONE)
    dd = model.AddDimension2(at[0], at[1], at[2])
    d = dd.GetDimension2(0)
    d.SystemValue = value_mm * mm
    return d.FullName          # e.g. D1@Sketch1@Part1


def link(eq, full_name, expr):
    short = "@".join(full_name.split("@")[:2])
    eq.Add2(-1, f'"{short}" = {expr}', True)


def extrude_boss(model, depth_mm):
    fm = model.FeatureManager
    return fm.FeatureExtrusion2(True, False, False, 0, 0, depth_mm * mm, 0, False, False, False, False,
                                0, 0, False, False, False, False, True, True, True, 0, 0, False)


def cut_blind(model, depth_mm, flip=False):
    fm = model.FeatureManager
    return fm.FeatureCut4(True, flip, False, 0, 0, depth_mm * mm, 0, False, False, False, False, 0, 0,
                          False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)


def main():
    sw = connect()
    model = new_part(sw)
    eq = add_globals(model)
    sm = model.SketchManager

    # Base block on the Top plane, extruded up.
    select(model, "Top Plane", "PLANE")
    sm.InsertSketch(True)
    segs = sm.CreateCenterRectangle(0, 0, 0, 22 * mm, 15 * mm, 0)
    lines = [s for s in segs if s is not None]
    n1 = dim(model, lines[0], 44.0, (0, 0, -25 * mm))
    n2 = dim(model, lines[1], 30.0, (30 * mm, 0, 0))
    sm.InsertSketch(True)
    base = extrude_boss(model, 12.0)
    print("base:", base.Name if base else None, n1, n2)
    link(eq, n1, '"PodL"')
    link(eq, n2, '"PodW"')
    model.EditRebuild3

    os.makedirs(OUT_DIR, exist_ok=True)
    print("lines from rectangle:", len(lines))


if __name__ == "__main__":
    main()
