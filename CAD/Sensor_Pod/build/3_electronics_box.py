"""Electronics box behind the sensor head: base, lid, USB hatch cover and sunshade.

Base: Pi 4 bay at the front (M2.5 standoffs, fan intake and exhaust slots in the floor behind 3 mm upstands, side
slots under a drip ledge on the +X wall; nothing in the roof), a divider, and the ESP32 bay at the rear (M2
standoffs, LiPo underneath, 5 V buck on tie anchors). Notches in the divider for the ESP32's USB lead (-X) and the
5 V lead to the Pi (+X). Front wall: the cable window and four M3 holes for the flange bolts into the head. Rear
wall: SMA bulkhead for the LTE antenna and a PG7 gland or grommet for the vehicle feed. -X wall: a hatch over the Pi's
USB ports (flash drive, ESP32 lead). Floor: four heat-set insert bosses for the dovetail rail plate.
Lid: 2.4 mm roof with an outer drip skirt (lip seam), thinned to GNSS_WIN_T over the ESP32 so the GNSS patch sees
the sky through plastic only, six M3 screws. Sunshade: a second roof on posts over the Pi bay, 5 mm air gap.
Print: base open side up; lid top face down; hatch cover flat; sunshade plate down, posts up.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import *          # noqa: E402,F401
import params as P            # noqa: E402
from swlib import Part, PRINT, chamfer_poly  # noqa: E402

G = {k: v for k, v in vars(P).items() if k.isupper() and isinstance(v, (int, float))}
BX, FY, RY, ZB, ZT = BOX_X, BOX_FRONT_Y, BOX_REAR_Y, BOX_BOT_Z, BOX_TOP_Z
FLOOR = ZB + WALL
XI = BX - WALL
FYI, RYI = FY - WALL, RY + WALL
c = BOX_REAR_CHAMFER

b = Part(G)
print("box base")
b.prism("Z", [("poly", chamfer_poly(-BX, BX, RY, FY, 0, c))], ZB, ZT, "Box Block")
fr = BOX_REAR_FACET
b.cut_through("X", [("poly", [(RY - 1, ZB + fr + 1), (RY + fr + 1, ZB - 1), (RY - 1, ZB - 1)])], "Rear Bottom Facet")
b.shell((0.0, -80.0, ZT), WALL, "Shell")

# Divider with the two lead notches.
b.prism("Z", [("rect", -XI - 0.1, DIVIDER_Y - 2, XI + 0.1, DIVIDER_Y)], FLOOR - 0.5, ZT - 2, "Divider")
b.cut("Y", [("rect", -XI - 0.5, FLOOR, -46.0, -8.0), ("rect", 44.0, FLOOR, XI + 0.5, -14.0)],
      DIVIDER_Y - 2.5, DIVIDER_Y + 0.5, "Divider Lead Notches")

# Front wall: cable window and flange bolt holes.
x0, x1, z0, z1 = CABLE_WIN
b.cut("Y", [("rect", x0, z0, x1, z1)] + [("circle", x, z, M3_CLEAR / 2) for x, z in FLANGE_BOLTS],
      FYI - 0.5, FY + 0.5, "Cable Window and Flange Holes")

# Standoffs.
b.prism("Z", [("circle", x, y, 3.0) for x, y in PI_HOLES], FLOOR - 0.5, FLOOR + PI_STANDOFF, "Pi Standoffs")
b.cut("Z", [("circle", x, y, M25_PILOT / 2) for x, y in PI_HOLES], FLOOR + 1, FLOOR + PI_STANDOFF + 0.5, "Pi Pilots")
b.prism("Z", [("circle", x, y, 2.5) for x, y in ESP_HOLES], FLOOR - 0.5, FLOOR + ESP_STANDOFF, "ESP32 Standoffs")
b.cut("Z", [("circle", x, y, M2_PILOT / 2) for x, y in ESP_HOLES], FLOOR + 1, FLOOR + ESP_STANDOFF + 0.5,
      "ESP32 Pilots")

# Lid screw bosses with M3 inserts.
for i, (x, y) in enumerate(LID_SCREWS):
    b.prism("Z", [("circle", x, y, 4.0)], FLOOR - 0.5, ZT, f"Lid Boss {i + 1}")
b.cut("Z", [("circle", x, y, INSERT_M3_D / 2) for x, y in LID_SCREWS], ZT - INSERT_M3_L, ZT + 0.5, "Lid Insert Holes")

# Floor vents with upstands: intake under the +X end of the Pi bay, exhaust under the -X (USB) end.
slots_y = [-30.0 - 6.0 * i for i in range(9)]
for name, (o0, o1) in (("Intake", (47.0, 69.0)), ("Exhaust", (-62.0, -46.0))):
    b.prism("Z", [("rect", o0, -82, o1, -26), ("rect", o0 + 2, -80, o1 - 2, -28)], FLOOR - 0.5, FLOOR + VENT_UPSTAND,
            f"{name} Upstand")
    b.cut("Z", [("rect", o0 + 4, y - 1.5, o1 - 4, y + 1.5) for y in slots_y], ZB - 1, FLOOR + 0.5, f"{name} Slots")

# Side vents low in the +X wall of the Pi bay, under a drip ledge.
b.cut("X", [("rect", y - 1.5, FLOOR + 2, y + 1.5, FLOOR + 10) for y in slots_y], XI - 0.5, BX + 0.5, "Side Vents")
ledge = [(BX - 0.2, FLOOR + 12), (BX + 4, FLOOR + 12), (BX + 4, FLOOR + 13), (BX - 0.2, FLOOR + 15.5)]
b.prism("Y", [("poly", ledge)], -82, -26, "Side Vent Drip Ledge")

# USB hatch in the -X wall, with insert bosses for the cover.
hy0, hy1, hz0, hz1 = USB_HATCH
b.cut("X", [("rect", hy0, hz0, hy1, hz1)], -BX - 0.5, -XI + 0.5, "USB Hatch Opening")
b.prism("X", [("circle", y, z, 4.0) for y, z in HATCH_BOSSES], -XI - 0.1, -XI + 6.5, "Hatch Bosses")
b.cut("X", [("circle", y, z, INSERT_M3_D / 2) for y, z in HATCH_BOSSES], -BX - 0.5, -BX + INSERT_M3_L + 0.5,
      "Hatch Insert Holes")

# Rear wall: LTE SMA bulkhead and the cable gland.
b.cut("Y", [("circle", LTE_SMA[0], LTE_SMA[1], LTE_SMA[2] / 2), ("circle", GLAND[0], GLAND[1], GLAND[2] / 2)],
      RY - 0.5, RYI + 0.5, "SMA and Gland Holes")

# Tie anchors: jumper bundle in front of the Pi, two for the buck.
b.prism("Z", [("rect", -6, -24, 6, -17)], FLOOR - 0.5, FLOOR + 3.5, "Bundle Tie Anchor")
b.cut("X", [("rect", -22.5, FLOOR, -18.5, FLOOR + TIE_SLOT[1])], -7, 7, "Bundle Tie Slot")
bx0, by0, bw, bl, bh = BUCK
for i, y in enumerate((by0 + 10, by0 + bl - 10)):
    b.prism("Z", [("rect", bx0 + bw / 2 - 5, y - 3.5, bx0 + bw / 2 + 5, y + 3.5)], FLOOR - 0.5, FLOOR + 3.5,
            f"Buck Tie Anchor {i + 1}")
    b.cut("X", [("rect", y - 2, FLOOR, y + 2, FLOOR + TIE_SLOT[1])], bx0 + bw / 2 - 6, bx0 + bw / 2 + 6,
          f"Buck Tie Slot {i + 1}")

# Rail plate bosses with M3 inserts from below.
b.prism("Z", [("circle", x, y, 4.0) for x, y in RAIL_BOLTS], FLOOR - 0.5, FLOOR + 6, "Rail Plate Bosses")
b.cut("Z", [("circle", x, y, INSERT_M3_D / 2) for x, y in RAIL_BOLTS], ZB - 0.5, ZB + INSERT_M3_L, "Rail Insert Holes")

b.save(os.path.join(PRINT, "SW7_Pod_Box_Base.SLDPRT"), "box_base_iso.png")
b.close_doc()

# ---------- Lid ----------
print("box lid")
L = Part(G)
s = LID_FIT + LID_SKIRT
k = 2 - 2 ** 0.5
outer = chamfer_poly(-BX - s, BX + s, RY - s, FY, 0, c + s * k)
inner = chamfer_poly(-BX - LID_FIT, BX + LID_FIT, RY - LID_FIT, FY, 0, c + LID_FIT * k)
L.prism("Z", [("poly", outer)], ZT, ZT + LID_T, "Lid Plate")
u_shape = [outer[i] for i in (3, 2, 1, 0, 5, 4)] + [inner[i] for i in (4, 5, 0, 1, 2, 3)]   # open at the front
L.prism("Z", [("poly", u_shape)], ZT - LID_TONGUE_H, ZT + 0.01, "Drip Skirt")
for sx in (-1, 1):       # front skirt only outside the head
    a0, a1 = sorted((sx * (HEAD_X + 0.6), sx * (BX + s)))
    L.prism("Z", [("rect", a0, FY, a1, FY + LID_FIT + LID_SKIRT)], ZT - LID_TONGUE_H, ZT + LID_T,
            f"Front Skirt {'L' if sx < 0 else 'R'}")
gx0, gx1, gy0, gy1 = GNSS_WIN
L.cut("Z", [("rect", gx0, gy0, gx1, gy1)], ZT - 0.5, ZT + LID_T - GNSS_WIN_T, "GNSS Thin Window")
L.cut("Z", [("circle", x, y, M3_CLEAR / 2) for x, y in LID_SCREWS + SUNSHADE_POSTS], ZT - 1, ZT + LID_T + 1,
      "Screw Holes")
L.save(os.path.join(PRINT, "SW7_Pod_Box_Lid.SLDPRT"), "box_lid_iso.png", "front_iso")
L.close_doc()

# ---------- USB hatch cover ----------
print("hatch cover")
y0, y1, z0_, z1_, th = HATCH_COVER
h = Part(G)
h.prism("X", [("rect", y0, z0_, y1, z1_)], -BX - th, -BX, "Cover Plate")
h.prism("X", [("rect", hy0 + 0.5, hz0 + 0.5, hy1 - 0.5, hz1 - 0.5)], -BX - 0.01, -XI, "Locating Plug")
h.cut("X", [("circle", y, z, M3_CLEAR / 2) for y, z in HATCH_BOSSES], -BX - th - 1, -BX + 1, "Screw Holes")
h.save(os.path.join(PRINT, "SW7_Pod_USB_Hatch_Cover.SLDPRT"))
h.close_doc()

# ---------- Sunshade ----------
print("sunshade")
hx, sy0, sy1, gap, st = SUNSHADE
z0s = ZT + LID_T
u = Part(G)
u.prism("Z", [("poly", chamfer_poly(-hx, hx, sy0, sy1, 4, 4))], z0s + gap, z0s + gap + st, "Shade Plate")
u.prism("Z", [("circle", x, y, 4.0) for x, y in SUNSHADE_POSTS], z0s, z0s + gap + 0.1, "Posts")
u.cut("Z", [("circle", x, y, 1.25) for x, y in SUNSHADE_POSTS], z0s - 0.5, z0s + gap + 1, "Post Pilots")
u.save(os.path.join(PRINT, "SW7_Pod_Sunshade.SLDPRT"))
u.close_doc()
