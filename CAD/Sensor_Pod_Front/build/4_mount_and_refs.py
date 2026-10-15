"""Front pod step 4: the rail plate and the reference parts for the assembly and the clearance audits.

Rail plate: the original pod's plate, built by the same code with the same parameters (same dovetail, same bolt
pattern X +/-22, Y -91 and -49), so it is the same part and slides into the shared bar clamp
(CAD/Dashboard_Enclosure SW7_Dash_Bracket and SW7_Dash_Clamp_Cap). audit_6_identity.py compares it with the original.

Reference parts (not printed), in reference_parts/:
  REF_FPod_Sensor_Board, REF_FPod_Camera_Case, REF_FPod_View_Cones: as the original pod.
  REF_FPod_Pi5_with_Cooler: Pi 5 PCB, underside parts, ports from the official drawing [D1], the Active Cooler [D2]
    (fins and fan block), the 40-pin header with the stacking socket, the four 16 mm spacers, the AI HAT+ [D3] with
    its slot and notch, the Hailo with a heatsink allowance, the stacking pins above the HAT, the seven Dupont
    housings on pins 1, 3, 5, 6, 15, 16, 18, and the PCIe flat cable loop.
  REF_FPod_Cables: the four plugs and their cables out through the notches (0.3 mm smaller than the notch all round),
    the camera ribbon from the window to the CAM/DISP connector (params.ribbon_box_path), and the jumper bundle.
Tool stand-ins (not in the assembly), in reference_tools/: a 2.5 mm hex key on each lower flange bolt, with the bolt
  head, used by audit_5_clearances.py to show the bolts can be reached with the Pi in place.
"""
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import *          # noqa: F401,F403
from swlib import Part, PRINT, REF, OUT

TOOLS = os.path.join(OUT, "reference_tools")
ZB = BOX_BOT_Z
PLATE_Y = 84.0
PLATE_T = RAIL_PLATE[2]
RAIL_L = 72.0
DETENT_D, DETENT_DEPTH, DETENT_OFF = 4.5, 2.0, 28.0
PT = pcb_top()                 # -16.4
PB = PT - PI5_T

# ---------- Rail plate (same code and values as CAD/Sensor_Pod/build/4_mount_and_refs.py) ----------
print("rail plate")
G = {"PlateX": RAIL_PLATE[0], "PlateY": PLATE_Y, "PlateT": PLATE_T, "RailW": RAIL_W, "RailW2": RAIL_W2,
     "RailH": RAIL_H, "RailL": RAIL_L}
p = Part(G)
hx, y0, y1 = RAIL_PLATE[0] / 2, MOUNT_Y - PLATE_Y / 2, MOUNT_Y + PLATE_Y / 2
zt, zb = ZB, ZB - PLATE_T
p.prism("Z", [("rect", -hx, y0, hx, y1)], zb, zt, "Rail Plate")
a, b = RAIL_W / 2, RAIL_W2 / 2
k = (b - a) / RAIL_H
p.prism("Y", [("poly", [(-(a - 0.5 * k), zb + 0.5), (a - 0.5 * k, zb + 0.5), (b, zb - RAIL_H), (-b, zb - RAIL_H)])],
        MOUNT_Y - RAIL_L / 2, MOUNT_Y + RAIL_L / 2, "Dovetail Rail")
p.cut("Z", [("circle", x, y, M3_CLEAR / 2) for x, y in RAIL_BOLTS], zb - 0.5, zt + 0.5, "M3 Holes")
p.cut("Z", [("circle", x, y, 3.0) for x, y in RAIL_BOLTS], zb - 0.5, zb + 3.5, "Counterbores")
p.cut("Z", [("circle", 0.0, MOUNT_Y + sy * DETENT_OFF, DETENT_D / 2) for sy in (-1, 1)],
      zb - RAIL_H - 0.5, zb - RAIL_H + DETENT_DEPTH, "Lock Detents")
p.save(os.path.join(PRINT, "SW7_FPod_Rail_Plate.SLDPRT"), "rail_plate_iso.png")
p.close_doc()

# ---------- Sensor board with carriers (as the original) ----------
print("reference: sensor board")
r = Part()
r.prism("Z", [("poly", board_outline())], -PCB_T, 0.0, "PCB")
r.prism("Z", [("rect", -J2_X, J2_Y[0], J2_X, J2_Y[1])], -BELOW_PCB - DUPONT_DROP, 0.0, "J2 Header And Dupont Plugs")
for name, x, y, z, bearing in tof_chips():
    bb = math.radians(bearing)
    dx, dy = math.sin(bb), math.cos(bb)
    tx, ty = math.cos(bb), -math.sin(bb)
    w, d = 8.0, 2.0
    pts = [(x - tx * w / 2 - dx * d, y - ty * w / 2 - dy * d), (x + tx * w / 2 - dx * d, y + ty * w / 2 - dy * d),
           (x + tx * w / 2, y + ty * w / 2), (x - tx * w / 2, y - ty * w / 2)]
    r.prism("Z", [("poly", pts)], 0.0, ABOVE_PCB, f"ToF Carrier {name}")
r.save(os.path.join(REF, "REF_FPod_Sensor_Board.SLDPRT"))
r.close_doc()

# ---------- Camera case ----------
print("reference: camera")
c = Part()
x0, x1, cy0, cy1, cz0, cz1 = cam_box()
c.prism("Z", [("rect", x0, cy0, x1, cy1)], cz0, cz1, "Camera Case")
c.save(os.path.join(REF, "REF_FPod_Camera_Case.SLDPRT"))
c.close_doc()


def brect(bx0, by0, bx1, by1):
    (X0, Y0), (X1, Y1) = b2p(bx0, by0), b2p(bx1, by1)
    return ("rect", X0, Y0, X1, Y1)


# ---------- Pi 5 with Active Cooler ----------
print("reference: Pi 5")
q = Part()
q.prism("Z", [brect(0, 0, PI5_L, PI5_W)], PB, PT, "Pi 5 PCB")
for i, rr in enumerate(((7, 1, 58, 55), (1, 7, 84, 49), (65, 1, 84, 55))):    # clear of the four standoffs
    q.prism("Z", [brect(*rr)], PB - PI5_UNDERSIDE, PB, f"Underside Parts {i + 1}")
q.prism("Z", [brect(-2.5, 22, 14, 34)], PB - PI5_UNDERSIDE, PB, "microSD Card")          # estimated
bx0, bx1, by0, by1 = COOLER_B
fx0, fx1, fy0, fy1 = COOLER_FAN_B
q.prism("Z", [brect(bx0, by0, fx0, by1)], PT + 1.3, PT + COOLER_H, "Cooler Fins")
q.prism("Z", [brect(fx0, fy0, fx1, fy1)], PT + 1.3, PT + COOLER_H, "Cooler Fan")
HB, HT = hat_bot(), hat_top()
q.prism("Z", [brect(7.1, 49.96, 57.9, 55.04)], PT, HB, "40-pin Header And Stacking Socket")
for i, (hx_, hy_) in enumerate(PI5_HOLES_B):
    X_, Y_ = b2p(hx_, hy_)
    q.prism("Z", [("circle", X_, Y_, 2.75)], PT, HB, f"HAT Spacer {i + 1}")
# AI HAT+ board: outline minus the CAM/DISP slot and the PCIe notch [D3]
s0, s1, t0, t1 = HAT_SLOT_B
n0, n1, m0, m1 = HAT_NOTCH_B
q.prism("Z", [("poly", [b2p(*p_) for p_ in [(0, 0), (s0, 0), (s0, t1), (s1, t1), (s1, 0), (HAT_W, 0), (HAT_W, HAT_D),
                                            (0, HAT_D), (0, m1), (n1, m1), (n1, m0), (0, m0)]])], HB, HT, "AI HAT+ PCB")
q.prism("Z", [brect(HAILO_B[0], HAILO_B[2], HAILO_B[1], HAILO_B[3])], HT, HT + HAILO_H, "Hailo And Heatsink")
q.prism("Z", [brect(7.1, 49.96, 57.9, 55.04)], HT, HT + STACK_PINS_H, "Stacking Pins")
dup = []
for n in TOF_PINS:
    x, y = pin_xy(n)
    dup.append(("rect", x - 1.25, y - 1.25, x + 1.25, y + 1.25))
q.prism("Z", dup, HT + DUPONT_SEAT, dupont_top(), "Dupont Housings")
# PCIe flat cable between the Pi's connector and the HAT, looping out past the Pi's USB-C end
q.prism("Z", [brect(-PCIE_FFC_LOOP, m0 + 1, -0.3, m1 - 1)], PT - 1.0, HT, "PCIe Flat Cable Loop")
e0 = PI5_L + PI5_PORT_OVERHANG
el, ew, eh = PI5_ETH_SIZE
q.prism("Z", [brect(e0 - el, PI5_ETH_BY - ew / 2, e0, PI5_ETH_BY + ew / 2)], PT, PT + eh, "Ethernet")
ul, uw, uh = PI5_USB_SIZE
q.prism("Z", [brect(e0 - ul, yc - uw / 2, e0, yc + uw / 2) for yc in PI5_USB_BY], PT, PT + uh, "USB-A Stacks")
q.prism("Z", [brect(PI5_USBC_BX - 4.5, -0.5, PI5_USBC_BX + 4.5, 7.3)], PT, PT + 3.2, "USB-C")
q.prism("Z", [brect(xc - 3.75, -0.5, xc + 3.75, 7.5) for xc in PI5_HDMI_BX], PT, PT + 3.4, "Micro-HDMI")
q.prism("Z", [brect(a0, PI5_FPC_BY[0], a1, PI5_FPC_BY[1]) for a0, a1 in PI5_FPC_B], PT, PT + PI5_FPC_H,
        "CAM-DISP Connectors")
q.save(os.path.join(REF, "REF_FPod_Pi5_with_Cooler.SLDPRT"))
q.close_doc()

# ---------- Cables: plugs, cables through the notches, ribbon, jumper bundle ----------
print("reference: cables")
w = Part()
PORT_ZC = {"usbc": PT + 1.6, "hdmi": PT + 1.7, "eth": PT + 6.8, "usba": PT + 4.0}   # estimated port centre heights
for kind, x in REAR_NOTCHES:
    pw, ph = PLUG_WH[kind]
    zc = PORT_ZC[kind]
    w.prism("Y", [("rect", x - pw / 2, zc - ph / 2, x + pw / 2, zc + ph / 2)], PI_Y0 - PLUG_L[kind], PI_Y0 - 0.5,
            f"Plug {kind}")         # from the port face (the ports stand 0.5 past the board edge)
    d = CABLE_D[kind]
    w.prism("Y", [("circle", x, REAR_PORT[2] + d / 2, d / 2 - 0.3)], BOX_REAR_Y - 30, PI_Y0 - PLUG_L[kind] + 0.5,
            f"Cable {kind}")
xe = PI_X0 + PI5_L + PI5_PORT_OVERHANG
for kind, y in SIDE_NOTCHES:
    pw, ph = PLUG_WH[kind]
    zc = PORT_ZC[kind]
    w.prism("X", [("rect", y - pw / 2, zc - ph / 2, y + pw / 2, zc + ph / 2)], xe, xe + PLUG_L[kind], f"Plug {kind}")
    d = CABLE_D[kind]
    w.prism("X", [("circle", y, SIDE_PORT[2] + d / 2, d / 2 - 0.3)], xe + PLUG_L[kind] - 0.5, BOX_X + 30,
            f"Cable {kind}")

# Ribbon: 0.6 thick stand-in (0.3 mm cable, doubled at the fold), RIBBON_W_PI wide.
pts, _ = ribbon_box_path()
fold = next(i for i, p_ in enumerate(pts) if abs(p_[1] - fpc_xy()[1]) < 1e-6)
t = 0.3


def strip(p1, p2):
    (u1, v1), (u2, v2) = p1, p2
    L_ = math.hypot(u2 - u1, v2 - v1)
    nu, nv = -(v2 - v1) / L_ * t, (u2 - u1) / L_ * t
    return [("poly", [(u1 + nu, v1 + nv), (u2 + nu, v2 + nv), (u2 - nu, v2 - nv), (u1 - nu, v1 - nv)])]


lane = pts[0][0]
for i in range(fold):
    a_, b_ = pts[i], pts[i + 1]
    w.prism("X", strip((a_[1], a_[2]), (b_[1], b_[2])), lane - RIBBON_W_PI / 2, lane + RIBBON_W_PI / 2,
            f"Ribbon {i}")
fy = pts[fold][1]
w.prism("Z", [("rect", lane - RIBBON_W_PI / 2, fy - RIBBON_W_PI / 2, lane + RIBBON_W_PI / 2, fy + RIBBON_W_PI / 2)],
        RIBBON_RUN_Z - 2 * t, RIBBON_RUN_Z + 2 * t, "Ribbon Fold")
z_conn = PT + PI5_FPC_H
for i in range(fold, len(pts) - 1):
    a_, b_ = pts[i], pts[i + 1]
    if b_[2] < z_conn:
        b_ = (b_[0], b_[1], z_conn + 0.01)
    w.prism("Y", strip((a_[0], a_[2]), (b_[0], b_[2])), fy - RIBBON_W_PI / 2, fy + RIBBON_W_PI / 2, f"Ribbon {i}")

# Jumper bundle (seven wires, 2 mm stand-in layer): through the window's lower half, across the front gap, up in
# front of the Pi, an R5 hairpin over the board edge and down into the housings.
hy = (pin_xy(1)[1] + pin_xy(2)[1]) / 2          # housing row centre, Y -40
top = dupont_top()                                # housing top, on the stacking pins above the HAT
rise_y = hy + 2 * BEND_R
w.prism("Z", [("rect", -18, HEAD_REAR_Y - 6, -8, HEAD_REAR_Y)], -13, -11, "Jumpers Window")
w.prism("Z", [("rect", -47.5, rise_y - 1, -8, HEAD_REAR_Y - 6)], -13, -11, "Jumpers Across")
w.prism("X", [("rect", rise_y - 1, -13, rise_y + 1, top + 1)], -47.5, -25.5, "Jumpers Rise")
arc = [(hy + BEND_R + (BEND_R + 1) * math.cos(math.pi * i / 8), top + 1 + (BEND_R + 1) * math.sin(math.pi * i / 8))
       for i in range(9)]
arc += [(hy + BEND_R + (BEND_R - 1) * math.cos(math.pi * i / 8), top + 1 + (BEND_R - 1) * math.sin(math.pi * i / 8))
        for i in range(8, -1, -1)]
w.prism("X", [("poly", arc)], -47.5, -25.5, "Jumpers Hairpin")
w.prism("X", [("rect", hy - 1, top + 0.01, hy + 1, top + 1)], -47.5, -25.5, "Jumpers Into Housings")
w.save(os.path.join(REF, "REF_FPod_Cables.SLDPRT"))
w.close_doc()

# ---------- View cones ----------
print("reference: view cones")
v = Part()
for name, x, y, z, bearing in tof_chips():
    v.beam_feature((x, y, z), bearing, ("circle", 1.2), 0.0, TOF_CONE_LEN, TOF_FOV / 2, f"ToF Cone {name}",
                   cut=False, merge=False)
lx, ly, lz = lens()
v.beam_feature((lx, ly, lz), 0.0, ("circle", 1.5), 0.0, 60.0, CAM_HFOV / 2, "Camera FOV (horizontal)",
               cut=False, merge=False)
v.save(os.path.join(REF, "REF_FPod_View_Cones.SLDPRT"))
v.close_doc()

# ---------- Tools: hex key on each lower flange bolt ----------
print("tools: hex keys")
af, arm = HEXKEY
hd, hh = M3_HEAD
FYI = BOX_FRONT_Y - WALL
kk = Part()
for x, z in [(x, z) for x, z in FLANGE_BOLTS if z < HEAD_SPLIT_Z]:
    kk.prism("Y", [("circle", x, z, hd / 2)], FYI - hh, FYI, f"Bolt Head {x:+.0f}", merge=False)
    y_end = FYI - hh + 2.0 - arm                    # key 2 mm into the socket, short arm along -Y
    kk.prism("Y", [("circle", x, z, af / 2 * 1.155)], y_end, FYI - hh + 2.0 - 0.01, f"Key Short Arm {x:+.0f}",
             merge=False)
    kk.prism("Z", [("circle", x, y_end + af / 2 * 1.155, af / 2 * 1.155)], z, BOX_TOP_Z + 30, f"Key Long Arm {x:+.0f}",
             merge=False)
kk.save(os.path.join(TOOLS, "TOOL_FPod_Hex_Keys.SLDPRT"))
kk.close_doc()
print("done")
