"""IMU pod revision 2: the engineering review's geometry fixes (ENGINEERING_REVIEW.md).

I1  Base: lid pilot holes shortened from 8 to 6 mm, so their bottom (Y 6) stays 1 mm above the strap tunnels' roof
    (Y 5). Lid screws M2.5 x 6.
I4  Lid: a rib under the lid presses on the board's free edge through a 1 mm foam pad, so the edge cannot flap.
    Rib 12 mm long (X -6 to 6, clear of the MPU-6050 in the middle of the board), 2 mm wide, centred 1.5 mm in from
    the board's free edge (Z +7), 2.4 mm deep: its face sits 1.0 mm above the board top (lid underside Y 12, board
    top Y 8.6).
Each change is checked by volume.
"""
import os
import pythoncom
import win32com.client
from win32com.client import VARIANT

NONE = VARIANT(pythoncom.VT_DISPATCH, None)
mm = 0.001
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sw = win32com.client.GetActiveObject("SldWorks.Application")
sw.SetUserPreferenceToggle(10, False)


def vol(m):
    return round(m.Extension.CreateMassProperty.Volume * 1e9, 1)


# I1: base lid pilot depth.
base = sw.OpenDoc(os.path.join(HERE, "SW7_IMU_Pod_Base.SLDPRT"), 1)
f = base.FeatureByName("Lid Pilot Holes")
if f is None:
    raise SystemExit("no Lid Pilot Holes feature")
d = None
for name in ("D1@Lid Pilot Holes", "D1@" + f.Name):
    d = base.Parameter(name)
    if d is not None:
        break
v0 = vol(base)
print("lid pilot depth was", round(d.SystemValue / mm, 2), "mm")
d.SystemValue = 6.0 * mm
base.EditRebuild3
print("lid pilot depth now", round(base.Parameter("D1@Lid Pilot Holes").SystemValue / mm, 2), "mm; volume", v0, "->", vol(base))
print("save base:", base.SaveAs3(base.GetPathName, 0, 1))
sw.CloseDoc(base.GetTitle)

# I4: lid rib.
lid = sw.OpenDoc(os.path.join(HERE, "SW7_IMU_Pod_Lid.SLDPRT"), 1)
sm, fm = lid.SketchManager, lid.FeatureManager
lid.ClearSelection2(True)
lid.Extension.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, NONE, 0)
sm.InsertSketch(True)
sm.AddToDB = True
sm.CreateCornerRectangle(-6 * mm, -(7 - 1) * mm, 0, 6 * mm, -(7 + 1) * mm, 0)   # Top-plane sketch y is -Z
sk = lid.GetActiveSketch2.Name
sm.AddToDB = False
sm.InsertSketch(True)
want = 12 * 2 * 2.4
for rev in (False, True):
    v0 = vol(lid)
    lid.ClearSelection2(True)
    lid.Extension.SelectByID2(sk, "SKETCH", 0, 0, 0, False, 0, NONE, 0)
    rib = fm.FeatureExtrusion2(True, False, rev, 0, 0, 2.4 * mm, 0, False, False, False, False, 0, 0,
                               False, False, False, False, True, True, True, 0, 0, False)
    box = [v / mm for v in lid.GetPartBox(True)]
    if rib is not None and abs(vol(lid) - v0 - want) < 1 and box[1] < -2.3:
        rib.Name = "Board Hold-Down Rib"
        print("rib added", round(vol(lid) - v0, 1), "mm3 (expected", want, "), lid box Y", round(box[1], 2), "to", round(box[4], 2))
        break
    if rib is not None:
        lid.EditUndo2(1)
else:
    raise SystemExit("rib failed")
lid.EditRebuild3
print("save lid:", lid.SaveAs3(lid.GetPathName, 0, 1))
sw.CloseDoc(lid.GetTitle)
