"""Sensor head, upper shell, and the camera retainer plate.

The upper shell is open underneath. It holds the camera case in a cradle (two rails, rear lips and a top bar; the
case slides up from below and the retainer plate screws under it), carries the camera window, the three flared ToF
windows with drip hoods, the light-bar groove and the brow. It sits on the sensor tray (2_sensor_tray.py) with a
lip seam at Z = HEAD_SPLIT_Z: a skirt on this part drops into a rebate in the tray walls. Two M3 flange bolts from
inside the box hold its rear; two M3 screws through the tray's side walls hold its front.
Modelled in place, pod frame (see params.py). Print: roof down is not possible (brow, sloped facets), so print it
standing on its open bottom (the seam face) with supports only under the brow and the hoods.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import *          # noqa: E402,F401
import params as P            # noqa: E402
from swlib import Part, PRINT, chamfer_poly   # noqa: E402

G = {k: v for k, v in vars(P).items() if k.isupper() and isinstance(v, (int, float))}
part = Part(G)
HX, FY, RY = HEAD_X, HEAD_FRONT_Y, HEAD_REAR_Y
prof, slope = side_profile()
print("upper shell")

# 1. Solid: side profile extruded across the width.
part.prism("X", [("poly", prof)], -HX, HX, "Head Block")

# 2. Facets: 45 deg top corners (front view), vertical front corners (plan view).
c = ROOF_CHAMFER
for sx in (-1, 1):
    tri = [(sx * (HX - c - 1), HEAD_TOP_Z + 1), (sx * (HX + 1), HEAD_TOP_Z + 1), (sx * (HX + 1), HEAD_TOP_Z - c - 1)]
    part.cut_through("Y", [("poly", tri)], f"Roof Corner Facet {'L' if sx < 0 else 'R'}")


def corner_facets(label, need=True):
    k = CORNER_CHAMFER
    for sx in (-1, 1):
        tri = [(sx * (HX - k - 12), FY + 12), (sx * (HX + 1), FY + 12), (sx * (HX + 1), FY - k - 1)]
        part.cut_through("Z", [("poly", tri)], f"{label} {'L' if sx < 0 else 'R'}", need)


corner_facets("Front Corner Facet")

# 3. Hollow it, open at the seam.
part.shell((0.0, 20.0, HEAD_SPLIT_Z), WALL, "Shell", (0, 0, -1))

# 4. Brow over the camera window (drip edge underneath), its ends cut on the same corner facets.
z_face_top = HEAD_TOP_Z - slope * (FY - ROOF_SLOPE_Y)
brow = [(FY - 1.0, VISOR_Z), (FY + VISOR, VISOR_Z), (FY + VISOR, VISOR_Z + 2.5), (FY - 1.0, z_face_top + slope * 1.0)]
part.prism("X", [("poly", brow)], -(HX - 0.5), HX - 0.5, "Brow")
corner_facets("Brow Corner Facet", need=False)
part.cut("Y", [("rect", -(HX - 2), VISOR_Z - 0.01, HX - 2, VISOR_Z + 0.8)], FY + VISOR - 2.5, FY + VISOR - 1.5,
         "Brow Drip Groove")

# 5. Lip seam skirt, inside the tray's rebate.
outer = inner_plan(WALL)
inner = inner_plan(WALL + SKIRT_T)
part.prism("Z", [("poly", outer), ("poly", inner)], HEAD_SPLIT_Z - SKIRT_H, HEAD_SPLIT_Z + 0.01, "Seam Skirt")

# 6. Front seam screw blocks on the side walls (horizontal M3 inserts from the tray side walls).
for side, y, z in SEAM_SCREWS:
    x0, x1 = sorted((side * (HX - WALL - SKIRT_FIT), side * (HX - WALL - 6.5)))
    part.prism("Z", [("rect", x0, y - 4, x1, y + 4)], z - 4.5, HEAD_SPLIT_Z, f"Seam Block {'L' if side < 0 else 'R'}")
    xa_, xb_ = sorted((side * (HX - WALL + 0.2), side * (HX - WALL - 6.5)))
    part.prism("Z", [("rect", xa_, y - 4, xb_, y + 4)], HEAD_SPLIT_Z - 0.01, 0.0, f"Seam Block Root {'L' if side < 0 else 'R'}")
    xa, xb = sorted((side * (HX - WALL - SKIRT_FIT + 0.1), side * (HX - WALL - SKIRT_FIT - INSERT_M3_L)))
    part.cut("X", [("circle", y, z, INSERT_M3_D / 2)], xa, xb, f"Seam Insert {'L' if side < 0 else 'R'}")

# 7. Cable window through the rear wall and skirt (ribbon on top, jumper bundle below).
x0, x1, z0, z1 = CABLE_WIN
part.cut("Y", [("rect", x0, HEAD_SPLIT_Z - SKIRT_H - 1, x1, z1)], RY - 1, RY + WALL + 0.5, "Cable Window")

# 8. Flange bosses (upper pair) with M3 heat-set insert holes, inserts from the rear face.
ups = [(x, z) for x, z in FLANGE_BOLTS if z > HEAD_SPLIT_Z]
part.prism("Y", [("circle", x, z, 4.0) for x, z in ups], RY + WALL - 0.2, RY + WALL + INSERT_M3_L, "Flange Bosses")
part.cut("Y", [("circle", x, z, INSERT_M3_D / 2) for x, z in ups], RY - 0.5, RY + INSERT_M3_L + 0.5,
         "Flange Insert Holes")

# 9. Camera cradle: rails, rear lips, top bar; M2 pilots for the retainer.
cx0, cx1, cy0, cy1, cz0, cz1 = cam_box()
rx = cx1 + CAM_FIT
rail_y0 = cy0 - 1.35
for sx in (-1, 1):
    a, b = sorted((sx * rx, sx * (rx + 4.0)))
    part.prism("Z", [("rect", a, rail_y0, b, FY - WALL + 0.5)], cz0, cz1 + 0.8, f"Camera Rail {'L' if sx < 0 else 'R'}")
    a, b = sorted((sx * (rx - 2.0), sx * (rx + 0.5)))
    part.prism("Z", [("rect", a, rail_y0, b, cy0 - CAM_FIT)], cz0, cz1 - 1.0, f"Camera Rear Lip {'L' if sx < 0 else 'R'}")
part.prism("Z", [("rect", -(rx + 4.0), 34.0, rx + 4.0, 38.0)], cz1 + CAM_FIT, cz1 + 1.8, "Camera Top Bar")
part.cut("Z", [("circle", x, y, M2_PILOT / 2) for x, y in RETAINER_SCREWS], cz0 - 0.5, cz0 + 7.0, "Retainer Pilots")

# 10. Windows. Camera: from the lens opening, flared at half the HFOV plus margin. ToF: from each chip, 1 mm larger
#     than the package, flared at 12.5 + 5 deg, through the wall.
lx, ly, lz = lens()
part.beam_feature((lx, ly, lz), 0.0, ("rect", CAM_LENS_OPEN, CAM_LENS_OPEN), 0.0, ray_exit(lx, ly, 0) + 1.5,
                  CAM_HFOV / 2 + CAM_FOV_MARGIN, "Camera Window")
flare = TOF_FOV / 2 + TOF_MARGIN_DEG
for name, x, y, z, bearing in tof_chips():
    part.beam_feature((x, y, z), bearing, ("rect", TOF_PKG[0] + 2 * TOF_WIN_MARGIN, TOF_PKG[1] + 2 * TOF_WIN_MARGIN),
                      0.0, ray_exit(x, y, bearing) + 1.5, flare, f"ToF Window {name}")

# 11. Drip hoods. Ahead: a sloped ledge above the ahead window. Sides (bearing 90): ledges above the side windows.
#     With the sensors on the front corners (bearing 35) the ahead hood runs the full width instead.
full = abs(TOF_SIDE_BEARING) < 60
hx = HX - CORNER_CHAMFER - 1 if full else 13.0
hood = [(FY - 0.5, HOOD_Z), (FY + HOOD_L, HOOD_Z), (FY + HOOD_L, HOOD_Z + 1.0), (FY - 0.5, HOOD_Z + 1.0 + HOOD_L * 0.6)]
part.prism("X", [("poly", hood)], -hx, hx, "ToF Hood Ahead")
if not full:
    sx_, sy_ = TOF_SIDE_POS[TOF_SIDE_BEARING]
    d = HX - sx_
    half_h = TOF_PKG[1] / 2 + TOF_WIN_MARGIN + d * math.tan(math.radians(flare))
    half_w = TOF_PKG[0] / 2 + TOF_WIN_MARGIN + d * math.tan(math.radians(flare))
    zh = TOF_Z + half_h + 1.0
    for sx in (-1, 1):
        prof_ = [(sx * (HX - 0.5), zh), (sx * (HX + SIDE_HOOD_L), zh), (sx * (HX + SIDE_HOOD_L), zh + 1.0),
                 (sx * (HX - 0.5), zh + 1.0 + SIDE_HOOD_L * 0.6)]
        part.prism("Y", [("poly", prof_)], sy_ - half_w - 2, min(sy_ + half_w + 2, FY - CORNER_CHAMFER - 0.5),
                   f"ToF Hood {'Left' if sx < 0 else 'Right'}")

# 12. Light-bar groove across the front face, under the ToF "eyes" (the concept's red line).
part.cut("Y", [("rect", -HX - 1, LIGHTBAR_Z[0], HX + 1, LIGHTBAR_Z[1])], FY - LIGHTBAR_DEPTH, FY + 1, "Light-Bar Groove")

# 13. Ribbon tie anchor on the rear wall, above the cable window (tie runs through the tunnel along X).
part.prism("Y", [("rect", -8, z1 + 3, 8, z1 + 9)], RY + WALL - 0.2, RY + WALL + 4.0, "Ribbon Tie Anchor")
part.cut("X", [("rect", RY + WALL + 0.5, z1 + 4, RY + WALL + 0.5 + TIE_SLOT[1], z1 + 4 + TIE_SLOT[0])], -9, 9,
         "Ribbon Tie Slot")

# 14. Drip lip on the rear face over the box lid's front edge, so water running down the head misses the lid seam.
lip = [(RY + 0.1, BOX_TOP_Z + LID_T + 0.5), (RY - 4.0, BOX_TOP_Z + LID_T + 0.5), (RY - 4.0, BOX_TOP_Z + LID_T + 1.5),
       (RY + 0.1, BOX_TOP_Z + LID_T + 4.0)]
part.prism("X", [("poly", lip)], -(HX - 1.0), HX - 1.0, "Rear Drip Lip")

part.save(os.path.join(PRINT, "SW7_Pod_Head_Upper.SLDPRT"), "head_upper_iso.png", "front_iso")
part.close_doc()

# ---------- Camera retainer: plate under the case, ribbon slot, four M2 clearance holes ----------
print("camera retainer")
r = Part(G)
r.prism("Z", [("rect", -(rx + 4.0), rail_y0, rx + 4.0, FY - WALL - 0.3)], cz0 - 2.0, cz0, "Retainer Plate")
r.cut("Z", [("rect", -RIBBON_W / 2 - 1, cy0 + 0.8, RIBBON_W / 2 + 1, cy0 + 8.3)], cz0 - 3, cz0 + 1, "Ribbon Slot")
r.cut("Z", [("circle", x, y, 1.2) for x, y in RETAINER_SCREWS], cz0 - 3, cz0 + 1, "M2 Clearance Holes")
r.save(os.path.join(PRINT, "SW7_Pod_Camera_Retainer.SLDPRT"))
r.close_doc()
