"""Sensor head, lower tray: carries the sensor board on four M2 pillars, the space under it for the J2 Dupont plugs
(fitted from below) and their bend, a tie anchor for the jumper bundle, the lower half of the cable window and the
lower pair of flange bosses. The upper shell's skirt drops into the rebate round the top of the walls (lip seam);
two M3 screws through the side walls hold the front of the seam. Black lower part with front and side facets, as on
the concept renders. Print open side up, no supports.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import *          # noqa: E402,F401
import params as P            # noqa: E402
from swlib import Part, PRINT  # noqa: E402

G = {k: v for k, v in vars(P).items() if k.isupper() and isinstance(v, (int, float))}
HX, FY, RY, ZB, ZS = HEAD_X, HEAD_FRONT_Y, HEAD_REAR_Y, HEAD_BOT_Z, HEAD_SPLIT_Z
t = Part(G)
print("lower tray")
t.prism("Z", [("poly", inner_plan(0))], ZB, ZS, "Tray Block")

# Facets: lower front (side view) and lower sides (front view).
zf, yb = LOWER_FRONT_FACET
a, b = (FY, zf), (yb, ZB)
d = (b[0] - a[0], b[1] - a[1])
a2, b2 = (a[0] - 0.2 * d[0], a[1] - 0.2 * d[1]), (b[0] + 0.2 * d[0], b[1] + 0.2 * d[1])
t.cut_through("X", [("poly", [a2, (FY + 5, a2[1]), (FY + 5, b2[1]), b2])], "Lower Front Facet")
c = LOWER_SIDE_FACET
for sx in (-1, 1):
    tri = [(sx * (HX + 1), ZB + c + 1), (sx * (HX + 1), ZB - 1), (sx * (HX - c - 1), ZB - 1)]
    t.cut_through("Y", [("poly", tri)], f"Lower Side Facet {'L' if sx < 0 else 'R'}")

t.shell((0.0, 10.0, ZS), WALL, "Shell")

# Lip seam rebate for the upper shell's skirt.
t.cut("Z", [("poly", inner_plan(WALL - SKIRT_FIT))], ZS - SKIRT_H - SKIRT_FIT, ZS + 1, "Seam Rebate")

# Board pillars (M2 self-tapping), PCB bottom at -PCB_T.
floor = ZB + WALL
t.prism("Z", [("circle", x, y, 2.5) for x, y in BOARD_HOLES], floor - 0.5, -PCB_T, "Board Pillars")
t.cut("Z", [("circle", x, y, BOARD_HOLE_PILOT / 2) for x, y in BOARD_HOLES], -PCB_T - 8, -PCB_T + 0.5, "Board Pilots")

# Cable window, lower half (jumper bundle).
x0, x1, z0, z1 = CABLE_WIN
t.cut("Y", [("rect", x0, z0, x1, ZS + 1)], RY - 1, RY + WALL + 0.5, "Cable Window")

# Flange bosses, lower pair, M3 heat-set inserts from the rear face.
lows = [(x, z) for x, z in FLANGE_BOLTS if z < ZS]
t.prism("Y", [("circle", x, z, 4.0) for x, z in lows], RY + WALL - 0.2, RY + WALL + INSERT_M3_L, "Flange Bosses")
t.cut("Y", [("circle", x, z, INSERT_M3_D / 2) for x, z in lows], RY - 0.5, RY + INSERT_M3_L + 0.5, "Flange Insert Holes")

# Seam screws through the side walls into the upper shell's blocks.
for side, y, z in SEAM_SCREWS:
    xa, xb = sorted((side * (HX - WALL - 0.5), side * (HX + 1)))
    t.cut("X", [("circle", y, z, M3_CLEAR / 2)], xa, xb, f"Seam Screw Hole {'L' if side < 0 else 'R'}")

# Tie anchor for the jumper bundle behind the board: a bridge with a tunnel along X.
t.prism("Z", [("rect", -6, -9, 6, -2)], floor - 0.5, floor + 4.5, "Bundle Tie Anchor")
t.cut("X", [("rect", -7.5, floor, -3.5, floor + TIE_SLOT[1])], -7, 7, "Bundle Tie Slot")

# Drain hole at the low front of the floor.
t.cut("Z", [("circle", 0, 34.0, 1.5)], ZB - 1, floor + 0.5, "Drain Hole")

t.save(os.path.join(PRINT, "SW7_FPod_Head_Tray.SLDPRT"), "head_tray_iso.png", "front_iso")
t.close_doc()
