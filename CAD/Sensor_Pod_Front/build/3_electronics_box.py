"""Front pod electronics box (Raspberry Pi 5 only): base, lid, two cable port covers and the sunshade.

Derived from CAD/Sensor_Pod/build/3_electronics_box.py. Removed: the ESP32 bay, the divider and its lead notches,
the ESP32 standoffs, the LiPo space, the 5 V buck anchors, the GNSS thinned roof, the LTE SMA hole, the gland and the
middle lid screws. The box is 112.5 mm long instead of 142.5.
Base: the Pi 5 with the Active Cooler and the AI HAT+ stacked on it, on four 10 mm standoffs (M2.5 x 18 from
under the floor into the HAT kit's spacers), its 40-pin header towards the head, the micro-HDMI / USB-C edge at
the rear and the USB / Ethernet end at +X. Front wall: the head's cable window and the four flange holes (unchanged).
A 22 mm gap between the front wall and the Pi leaves room for a hex key on the flange bolts, the Dupont housings on
the header and the ribbon's S-bend. The Active Cooler blows towards -X under the HAT, so the exhaust slots are in the -X wall at that height;
upper slot rows in both side walls let air cross over the HAT and the Hailo; the intake is through floor slots
behind 3 mm upstands at the +X end. Every side opening is under a drip ledge with a 45 deg underside.
The box is 18 mm taller than the original (BOX_TOP_Z 28) for the HAT stack. Cable ports: the rear wall
(USB-C power, micro-HDMI 0 to the display) and the +X wall (Ethernet to the rear Pi 4, USB-A for the display's touch)
each have an opening, a flat cover with U-notches for the cables, four M3 insert bosses and a tie block per cable.
Lid: as the original (drip skirt, M3 screws into insert bosses), without the GNSS window.
Print: base floor down; lid outer face down; covers flat; sunshade plate down, posts up.
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
TIE_W, TIE_H = 3.0, 2.0       # tunnel for a 2.5 mm cable tie

b = Part(G)
print("box base")
b.prism("Z", [("poly", chamfer_poly(-BX, BX, RY, FY, 0, c))], ZB, ZT, "Box Block")
fr = BOX_REAR_FACET
b.cut_through("X", [("poly", [(RY - 1, ZB + fr + 1), (RY + fr + 1, ZB - 1), (RY - 1, ZB - 1)])], "Rear Bottom Facet")
b.shell((0.0, -60.0, ZT), WALL, "Shell")

# Front wall: cable window and flange bolt holes (as the original, so the same head bolts on).
x0, x1, z0, z1 = CABLE_WIN
b.cut("Y", [("rect", x0, z0, x1, z1)] + [("circle", x, z, M3_CLEAR / 2) for x, z in FLANGE_BOLTS],
      FYI - 0.5, FY + 0.5, "Cable Window and Flange Holes")

# Pi 5 standoffs. The AI HAT+ kit spacers sit on top of the Pi, so the Pi is held by M2.5 x 16 pan heads from
# under the floor (counterbored), through the standoff and the Pi into the spacers. A wider base round each
# counterbore (audit 4: a plain 6 mm standoff left a 0.32 mm skin over the counterbore).
b.prism("Z", [("circle", x, y, 3.0) for x, y in PI_HOLES], FLOOR - 0.5, FLOOR + PI_STANDOFF, "Pi Standoffs")
b.prism("Z", [("circle", x, y, 4.25) for x, y in PI_HOLES], FLOOR - 0.5, FLOOR + 2.5, "Pi Standoff Bases")
b.cut("Z", [("circle", x, y, M25_CLEAR / 2) for x, y in PI_HOLES], ZB - 0.5, FLOOR + PI_STANDOFF + 0.5,
      "Pi Screw Holes")
b.cut("Z", [("circle", x, y, M25_HEAD[0] / 2) for x, y in PI_HOLES], ZB - 0.5, ZB + M25_HEAD[1], "Pi Counterbores")

# Lid screw bosses with M3 inserts.
for i, (x, y) in enumerate(LID_SCREWS):
    b.prism("Z", [("circle", x, y, 4.0)], FLOOR - 0.5, ZT, f"Lid Boss {i + 1}")
b.cut("Z", [("circle", x, y, INSERT_M3_D / 2) for x, y in LID_SCREWS], ZT - INSERT_M3_L, ZT + 0.5, "Lid Insert Holes")

# Floor vents with upstands: intake at the +X end, a small exhaust / drain at the -X end under the cooler exhaust.
for name, (o0, o1, y0, y1) in (("Intake", INTAKE), ("Floor Exhaust", FLOOR_EXHAUST)):
    slots = [y0 + 5.0 + 6.0 * i for i in range(int((y1 - y0 - 8.0) // 6.0) + 1)]
    b.prism("Z", [("rect", o0, y0, o1, y1), ("rect", o0 + 2, y0 + 2, o1 - 2, y1 - 2)], FLOOR - 0.5,
            FLOOR + VENT_UPSTAND, f"{name} Upstand")
    b.cut("Z", [("rect", o0 + 4, y - 1.5, o1 - 4, y + 1.5) for y in slots], ZB - 1, FLOOR + 0.5, f"{name} Slots")



def ledge(wall, z):
    """Drip ledge profile on an outer wall face at `wall` (pod coordinate, sign = outward), root at z: 45 deg
    underside out to LEDGE_L, 1 mm tip, sloped top back to the wall."""
    s_ = 1 if wall > 0 else -1
    return [("poly", [(wall - s_ * 0.2, z), (wall + s_ * LEDGE_L, z + LEDGE_L), (wall + s_ * LEDGE_L, z + LEDGE_L + LEDGE_TIP),
                      (wall - s_ * 0.2, z + LEDGE_L + LEDGE_TIP + 2)])]


# Exhaust slots in the -X wall at fin height (between the Pi and the HAT), under a drip ledge; upper rows in both
# side walls for cross-flow over the HAT and the Hailo, under their own ledges.
sz0, sz1 = SIDE_VENT_Z
y0v, y1v = SIDE_VENT_Y[0] - 4, SIDE_VENT_Y[-1] + 4
b.cut("X", [("rect", y - 1.5, sz0, y + 1.5, sz1) for y in SIDE_VENT_Y], -BX - 0.5, -XI + 0.5, "Exhaust Vents")
b.prism("Y", ledge(-BX, SIDE_LEDGE_Z), y0v, y1v, "Exhaust Drip Ledge")
for sx in (-1, 1):
    u0, u1 = UPPER_VENT_Z[sx]
    side = "L" if sx < 0 else "R"
    a0, a1 = sorted((sx * (XI - 0.5), sx * (BX + 0.5)))
    b.cut("X", [("rect", y - 1.5, u0, y + 1.5, u1) for y in SIDE_VENT_Y], a0, a1, f"Upper Vents {side}")
    b.prism("Y", ledge(sx * BX, UPPER_LEDGE_Z), y0v, y1v, f"Upper Drip Ledge {side}")

# Rear cable port: opening, insert bosses, a tie block under each cable.
rx0, rx1, rz0, rz1 = REAR_PORT
b.cut("Y", [("rect", rx0, rz0, rx1, rz1)], RY - 0.5, RYI + 0.5, "Rear Port Opening")
b.prism("Y", [("circle", x, z, 4.0) for x, z in REAR_BOSSES], RYI - 0.1, RYI + 6.5, "Rear Port Bosses")
b.prism("Y", [("rect", x - 4, FLOOR - 0.5, x + 4, z) for x, z in REAR_BOSSES if z < rz0], RYI - 0.1, RYI + 6.5,
        "Rear Port Boss Roots")
b.cut("Y", [("circle", x, z, INSERT_M3_D / 2) for x, z in REAR_BOSSES], RY - 0.5, RY + INSERT_M3_L + 0.5,
      "Rear Port Insert Holes")
b.prism("X", ledge(RY, REAR_LEDGE_Z), REAR_BOSSES[0][0] - COVER_MARGIN[0], REAR_BOSSES[-1][0] + COVER_MARGIN[0],
        "Rear Port Drip Ledge")
for kind, x in REAR_NOTCHES:
    b.prism("Z", [("rect", x - 6, RYI - 0.1, x + 6, RYI + 6)], FLOOR - 0.5, rz0, f"Rear Tie Block {kind}")
    b.cut("X", [("rect", RYI + 3 - TIE_W / 2, FLOOR + 1.5, RYI + 3 + TIE_W / 2, FLOOR + 1.5 + TIE_H)], x - 7, x + 7,
          f"Rear Tie Tunnel {kind}")

# +X cable port.
sy0, sy1, sz0_, sz1_ = SIDE_PORT
b.cut("X", [("rect", sy0, sz0_, sy1, sz1_)], XI - 0.5, BX + 0.5, "Side Port Opening")
b.prism("X", [("circle", y, z, 4.0) for y, z in SIDE_BOSSES], XI - 6.5, XI + 0.1, "Side Port Bosses")
b.cut("X", [("circle", y, z, INSERT_M3_D / 2) for y, z in SIDE_BOSSES], BX - INSERT_M3_L - 0.5, BX + 0.5,
      "Side Port Insert Holes")
for kind, y in SIDE_NOTCHES:
    b.prism("Z", [("rect", XI - 6, max(y - 6, sy0), XI + 0.1, min(y + 6, sy1))], FLOOR - 0.5, sz0_,
            f"Side Tie Block {kind}")    # clipped to the opening (audit 4: 0.3 / 0.6 mm slivers past its ends)
    b.cut("Y", [("rect", XI - 3 - TIE_W / 2, FLOOR + 1.5, XI - 3 + TIE_W / 2, FLOOR + 1.5 + TIE_H)], y - 7, y + 7,
          f"Side Tie Tunnel {kind}")

# Tie anchor for the jumper bundle and the ribbon slack in the front gap.
b.prism("Z", [("rect", -6, -24, 6, -17)], FLOOR - 0.5, FLOOR + 3.5, "Bundle Tie Anchor")
b.cut("X", [("rect", -22.5, FLOOR, -18.5, FLOOR + TIE_SLOT[1])], -7, 7, "Bundle Tie Slot")

# Rail plate bosses with M3 inserts from below (same pattern as the original, so the original rail plate fits).
# 6 high as the original: 2.4 mm over the insert, 4 mm under the Pi's PCB (standoffs 10).
b.prism("Z", [("circle", x, y, 4.0) for x, y in RAIL_BOLTS], FLOOR - 0.5, FLOOR + 6, "Rail Plate Bosses")
b.cut("Z", [("circle", x, y, INSERT_M3_D / 2) for x, y in RAIL_BOLTS], ZB - 0.5, ZB + INSERT_M3_L, "Rail Insert Holes")

b.save(os.path.join(PRINT, "SW7_FPod_Box_Base.SLDPRT"), "box_base_iso.png")
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
L.cut("Z", [("circle", x, y, M3_CLEAR / 2) for x, y in LID_SCREWS + SUNSHADE_POSTS], ZT - 1, ZT + LID_T + 1,
      "Screw Holes")
L.save(os.path.join(PRINT, "SW7_FPod_Box_Lid.SLDPRT"), "box_lid_iso.png", "front_iso")
L.close_doc()


# ---------- Rear port cover ----------
print("rear port cover")
mx, mz = COVER_MARGIN
cx0, cx1 = REAR_BOSSES[0][0] - mx, REAR_BOSSES[-1][0] + mx
cz0 = min(z for _, z in REAR_BOSSES) - mz
h = Part(G)
h.prism("Y", [("rect", cx0, cz0, cx1, COVER_TOP_Z)], RY - COVER_T, RY, "Cover Plate")
h.cut("Y", [("rect", x - CABLE_D[kind] / 2, cz0 - 1, x + CABLE_D[kind] / 2, rz0 + CABLE_D[kind])
            for kind, x in REAR_NOTCHES], RY - COVER_T - 1, RY + 1, "Cable Notches")
h.cut("Y", [("circle", x, z, M3_CLEAR / 2) for x, z in REAR_BOSSES], RY - COVER_T - 1, RY + 1, "Screw Holes")
h.save(os.path.join(PRINT, "SW7_FPod_Rear_Port_Cover.SLDPRT"))
h.close_doc()

# ---------- +X port cover ----------
print("side port cover")
cy0, cy1 = SIDE_BOSSES[0][0] - mx, SIDE_BOSSES[-1][0] + mx
cz0 = min(z for _, z in SIDE_BOSSES) - mz
h = Part(G)
h.prism("X", [("rect", cy0, cz0, cy1, COVER_TOP_Z)], BX, BX + COVER_T, "Cover Plate")
h.cut("X", [("rect", y - CABLE_D[kind] / 2, cz0 - 1, y + CABLE_D[kind] / 2, sz0_ + CABLE_D[kind])
            for kind, y in SIDE_NOTCHES], BX - 1, BX + COVER_T + 1, "Cable Notches")
h.cut("X", [("circle", y, z, M3_CLEAR / 2) for y, z in SIDE_BOSSES], BX - 1, BX + COVER_T + 1, "Screw Holes")
h.save(os.path.join(PRINT, "SW7_FPod_Side_Port_Cover.SLDPRT"))
h.close_doc()

# ---------- Sunshade ----------
print("sunshade")
hx, sy0_, sy1_, gap, st = SUNSHADE
z0s = ZT + LID_T
u = Part(G)
u.prism("Z", [("poly", chamfer_poly(-hx, hx, sy0_, sy1_, 4, 4))], z0s + gap, z0s + gap + st, "Shade Plate")
u.prism("Z", [("circle", x, y, 4.0) for x, y in SUNSHADE_POSTS], z0s, z0s + gap + 0.1, "Posts")
u.cut("Z", [("circle", x, y, 1.25) for x, y in SUNSHADE_POSTS], z0s - 0.5, z0s + gap + 1, "Post Pilots")
u.save(os.path.join(PRINT, "SW7_FPod_Sunshade.SLDPRT"))
u.close_doc()
