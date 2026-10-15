"""SW-7 FRONT sensor pod (Raspberry Pi 5 only): every size in one place (mm and degrees).

Layout of 15 Oct 2026: the Pi 5 is at the front with its own camera (OV5647 in the same yellow case) and its own ToF
board (same JCP board, same three VL53L0X carriers). The Pi 4 and the ESP32 stay in the original pod
(CAD/Sensor_Pod) at the rear. This variant = the same sensor head + a shorter box for a Raspberry Pi 5 with the
official Active Cooler.

Everything that is not redefined here is imported from CAD/Sensor_Pod/build/params.py (the sensor head, the camera,
the ToF board, the flange, the lid section, the mount), so the head parts come out identical to the original ones.
Same pod frame: X right, Y forward, Z up, origin at the centre of the sensor board's rear edge on its PCB top.

Source labels: measured (student), official (datasheet or drawing), estimated (MEASURE), design (my choice).
Sources used for the Pi 5:
  [D1] Raspberry Pi 5 mechanical drawing, datasheets.raspberrypi.com/rpi5/raspberry-pi-5-mechanical-drawing.pdf
  [D2] Raspberry Pi Active Cooler product brief (Jan 2026), datasheets.raspberrypi.com/cooling/
       raspberry-pi-active-cooler-product-brief.pdf: 63.5 x 42.5 footprint, fan 30 x 30, height 13.70
  [D3] Raspberry Pi AI HAT+ product brief (Oct 2024), datasheets.raspberrypi.com/ai-hat-plus/
       raspberry-pi-ai-hat-plus-product-brief.pdf: 65 x 56.5 board on the Pi's 58 x 49 holes, a 10 x 16 slot over the
       CAM/DISP connectors, a 5 x 18 notch for the PCIe flat cable, Hailo package 17 x 17, "supplied with 16mm stacking
       header, spacers, and screws to enable fitting on Raspberry Pi 5 with Raspberry Pi Active Cooler in place"
The student's Pi 5 carries the AI HAT+ over the Active Cooler (coordinator, 16 Oct): stack = Pi 5, cooler, 16 mm
spacers, AI HAT+, Hailo (with an optional small heatsink).
Positions read off the drawing at its 1:1 scale (not dimensioned on it) are marked "scaled from [D1]".
"""
import importlib.util
import math
import os

_ORIG = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "Sensor_Pod", "build", "params.py")
_spec = importlib.util.spec_from_file_location("sw7_pod_params_original", _ORIG)
_orig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_orig)
globals().update({k: v for k, v in vars(_orig).items() if not k.startswith("__")})

# Names from the original that do not exist in this variant (no ESP32, LiPo, GNSS, LTE, buck, divider).
for _k in ("ESP_X0", "ESP_Y0", "ESP_L", "ESP_W", "ESP_STANDOFF", "ESP_HOLES", "GNSS_PATCH", "BUCK", "GNSS_WIN",
           "GNSS_WIN_T", "DIVIDER_Y", "LTE_SMA", "GLAND", "USB_HATCH", "HATCH_BOSSES", "HATCH_COVER", "PI_X0",
           "PI_X1", "PI_Y0", "PI_Y1", "PI_HOLES", "PI_FAN"):
    globals().pop(_k, None)

# ---------------- Raspberry Pi 5 [D1] ----------------
# Board frame (bx, by): bx along the 85 mm edge from the USB-C end, by from the micro-HDMI / USB-C edge.
PI5_L, PI5_W, PI5_T = 85.0, 56.0, 1.6             # official [D1]; PCB thickness estimated
PI5_HOLES_B = [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)]   # official [D1]: 58 x 49, 3.5 from the edges, M2.5
PI5_USBC_BX = 11.2                                 # official [D1]
PI5_HDMI_BX = (25.8, 39.2)                         # official [D1]: HDMI0, HDMI1
PI5_ETH_BY = 10.2                                  # official [D1]: Ethernet centre
PI5_USB_BY = (29.1, 47.0)                          # official [D1]: the two USB-A stacks (centres)
PI5_PORT_OVERHANG = 3.0                            # official [D1]: USB / Ethernet stand 3 mm past the board end
PI5_ETH_SIZE = (21.0, 16.2, 13.5)                  # length bx (incl. overhang), width by, height: scaled from [D1]; height estimated
PI5_USB_SIZE = (17.5, 14.5, 16.0)                  # same, USB-A stacks: scaled from [D1]; height estimated (MEASURE)
PI5_FPC_B = [(47.0, 49.8), (53.2, 56.0)]           # bx ranges of the two 22-pin CAM/DISP connectors, scaled from [D1]
PI5_FPC_BY = (0.7, 16.2)                           # by range of both connectors, scaled from [D1]
PI5_FPC_H = 5.0                                    # estimated: connector height above the PCB (MEASURE)
PI5_FPC_USE = 0                                    # design: the camera uses the connector nearer the micro-HDMI ports
#   (bx 47.0 to 49.8): then the ribbon runs on the pod centreline from the window and folds towards -X. Which of CAM/DISP 0 and 1 that is: read the silkscreen, set the camera index in software.
PI5_HEADER_BY = (51.23, 53.77)                     # official (Pi HAT spec): rows of the 40-pin header
PI5_PIN1_BX = 8.37                                 # official (Pi HAT spec): pin 1 / 2 column; pitch 2.54
HEADER_BASE_H = 2.5                                # official: header plastic height
DUPONT_L = 14.0                                    # estimated: Dupont housing length (MEASURE)
TOF_PINS = (1, 3, 5, 6, 15, 16, 18)                # from the wiring: 3V3, SDA, SCL, GND, XSHUT x3
PI5_UNDERSIDE = 1.5                                # estimated: tallest part on the underside of the Pi 5

# Active Cooler [D2]: footprint 63.5 x 42.5 mounted on the two heatsink holes (bx 3, by 9.3) and (bx 60.6, by 47)
COOLER_B = (0.0, 63.5, 6.3, 48.8)                  # bx0, bx1, by0, by1: [D2] placed on the [D1] heatsink holes
COOLER_FAN_B = (33.5, 63.5, 18.8, 48.8)            # fan block (30 x 30, [D2]) at the Ethernet-end, header-side corner
COOLER_H = 15.0                                    # [D2] 13.70 plus 1.3 estimated for the SoC and pad: top above PCB top (MEASURE)
COOLER_EXHAUST = "-bx"                             # [D2] drawing: the blower blows through the fins towards the USB-C end


# AI HAT+ [D3], in the same board frame (its holes sit on the Pi's holes; it overhangs the header edge by 0.5)
HAT_W, HAT_D, HAT_T = 65.0, 56.5, 1.6              # official [D3]; thickness estimated (MEASURE)
HAT_SPACER = 16.0                                  # official [D3] "16mm stacking header, spacers": Pi PCB top to HAT
#   PCB bottom (MEASURE the kit spacers)
HAT_SLOT_B = (47.5, 57.5, 0.0, 16.0)               # official [D3]: bx0, bx1, by0, by1 of the slot over CAM/DISP
HAT_NOTCH_B = (0.0, 5.0, 21.0, 39.0)               # official [D3]: notch for the PCIe flat cable at the USB-C end
HAILO_B = (22.6, 39.6, 18.3, 35.5)                 # [D3] 17 x 17 package; position scaled from the drawing
HAILO_H = 10.0                                     # estimated: package 2 plus a small stick-on heatsink 8 (MEASURE;
#   2 without a heatsink)
STACK_PINS_H = 6.0                                 # estimated: stacking header pins standing above the HAT (MEASURE)
DUPONT_SEAT = 0.5                                  # estimated: Dupont housing bottom above the HAT top
PCIE_FFC_LOOP = 6.0                                # estimated: the PCIe flat cable loops this far past the Pi's
#   USB-C end (bx < 0), between Pi and HAT (MEASURE)
HAILO_AIR_GAP_MIN = 8.0                            # design: free height over the Hailo (heatsink) to the lid
M25_CLEAR, M25_HEAD = 2.7, (5.5, 2.2)              # Pi screws from below: clearance, counterbore diameter and depth

# Placement in the pod: header edge forward (towards the head), Ethernet / USB end at +X, micro-HDMI edge at the rear.
PI_X0 = -55.0               # design: board USB-C end. Leaves 15 mm to the -X wall for the cooler exhaust and
#   37 mm from the USB / Ethernet port faces to the +X wall for the plugs
PI_Y1 = -36.5               # design: header edge. 22.2 mm from the front wall's inner face, so a 2.5 mm hex key
#   (ISO 2936 short arm 18 mm) reaches the lower flange bolts with the Pi in place (original pod defect 3)
PI_Y0 = PI_Y1 - PI5_W       # -92.5: micro-HDMI / USB-C edge
PI_STANDOFF = 10.0          # design: PCB bottom 10 above the floor's inner face (Pi 4: 8). Raised after audit 4 so
#   the rail plate bosses keep a 2.4 mm cap over their inserts and still clear the Pi's underside (Ethernet and USB
#   pins) by 4 mm. With the HAT the Pi is held by the stack: M2.5 x 18 pan heads from under the floor, through the
#   standoff and the Pi into the kit spacers


def b2p(bx, by):
    """Pi 5 board coordinates to pod (X, Y)."""
    return PI_X0 + bx, PI_Y0 + by


PI_HOLES = [b2p(*h) for h in PI5_HOLES_B]

# ---------------- Electronics box ----------------
BOX_TOP_Z = 28.0            # design: raised from 10 for the AI HAT+ stack (Dupont jumpers on the stacking pins
#   above the HAT, their R5 bend, and 8 mm of air over the Hailo heatsink). Lid underside = BOX_TOP_Z
BOX_X = 72.4                # same width as the original (same lid and head-to-box look); half-width outside
BOX_REAR_Y = -124.4         # design: rear plugs (23 mm micro-HDMI / USB-C overmould, estimated) end at Y -115.5,
#   6.5 mm short of the rear wall's inner face. The original box ran to -154.4
BOX_LEN = BOX_FRONT_Y - BOX_REAR_Y
LID_SCREWS = [(sx * 66.5, -18.5) for sx in (-1, 1)] + [(sx * 64.0, BOX_REAR_Y + 8.4) for sx in (-1, 1)]

# Cable ports: wall opening, a flat cover with U-notches open at its bottom edge, M3 inserts in four bosses, and a
# cable-tie block inside under each cable (strain relief). The lid's drip skirt hangs over the cover's top edge.
#   Rear wall: USB-C power and micro-HDMI 0 (display). +X wall: Ethernet (to the rear Pi 4) and USB-A (display touch).
CABLE_D = {"usbc": 5.0, "hdmi": 7.0, "eth": 7.0, "usba": 5.0}   # notch widths = cable OD + foam. MEASURE the cables
REAR_PORT = (-50.0, -22.0, -16.0, 0.0)     # X0, X1, Z0 (sill), Z1 of the opening in the rear wall
REAR_NOTCHES = [("usbc", PI_X0 + PI5_USBC_BX), ("hdmi", PI_X0 + PI5_HDMI_BX[0])]   # (cable, X)
REAR_BOSSES = [(x, z) for x in (-57.0, -16.0) for z in (-19.5, 2.5)]   # (X, Z). X -57 merges the left pair into
#   the rear lid boss (at -56 they were exactly tangent and the feature failed). Lower pair at Z -19.5 (was -22.3):
#   audit 4 measured 0.10 mm from their insert holes to the rear bottom facet; a root block joins them to the floor
SIDE_PORT = (-88.0, -58.0, -15.0, 1.0)     # Y0, Y1, Z0 (sill), Z1 of the opening in the +X wall
SIDE_NOTCHES = [("eth", PI_Y0 + PI5_ETH_BY), ("usba", PI_Y0 + PI5_USB_BY[0])]     # (cable, Y)
SIDE_BOSSES = [(y, z) for y in (-94.0, -52.0) for z in (-22.3, 2.5)]               # (Y, Z)
COVER_T = 3.0
COVER_MARGIN = (5.5, 4.5)   # cover overlap past the opening: sideways, below (top edge stays under the lid skirt)
COVER_TOP_Z = 6.5           # lid skirt bottom is at BOX_TOP_Z - LID_TONGUE_H = 7.0

# Vents: blower exhaust leaves the fins towards -X, so the exhaust slots are in the -X wall at fin height, under a
# drip ledge; the intake is through floor slots with 3 mm upstands at the +X end, plus a small floor exhaust and drain
# at the -X end.
SIDE_VENT_Y = [-84.0 + 6.0 * i for i in range(7)]   # slot centres, 3 wide
SIDE_VENT_Z = (-14.0, -2.0)  # -X wall, lower row: the cooler's exhaust, between the Pi and the HAT
SIDE_LEDGE_Z = -0.5
UPPER_VENT_Z = {-1: (8.0, 16.0), 1: (10.0, 16.0)}    # upper rows in the -X and +X walls: cross-flow over the HAT and
#   the Hailo (the +X row starts above the side port cover)
UPPER_LEDGE_Z = 17.0         # ledge root; its top is 24.5, under the lid skirt (25.0)
REAR_LEDGE_Z = 8.0           # over the rear port cover
LEDGE_L = 4.0                # drip ledges project 4 mm with a 45 deg underside (prints without support)
LEDGE_TIP = 1.5              # drip edge thickness (1.0 in the first build; audit 4)
INTAKE = (38.0, 58.0, -86.0, -46.0)        # X0, X1, Y0, Y1 of the floor intake upstand
FLOOR_EXHAUST = (-69.5, -57.0, -86.0, -46.0)

# Sunshade over the Pi bay
SUNSHADE = (50.0, -102.0, -20.0, 5.0, 2.0)
SUNSHADE_POSTS = [(sx * 44.0, y) for sx in (-1, 1) for y in (-24.0, -98.0)]

# ---------------- Cables inside the box (for the reference bodies and the bend checks) ----------------
RIBBON_W_PI = 11.5          # estimated: 22-pin end of the Pi 5 camera cable (22-to-15 way). MEASURE
RIBBON_RUN_Z = 12.0         # design: the ribbon crosses over the HAT, clear of the stacking pins, and drops through
#   the HAT's CAM/DISP slot into the connector
RIBBON_SPEC_LEN = 200.0     # official Pi 5 camera cable lengths are 200, 300 and 500 mm: use the 200 mm one
PLUG_L = {"usbc": 23.0, "hdmi": 23.0, "eth": 30.0, "usba": 35.0}   # estimated plug + overmould lengths from the
#   port face (MEASURE): the box is sized on these
PLUG_WH = {"usbc": (8.5, 6.5), "hdmi": (11.5, 7.5), "eth": (14.0, 13.0), "usba": (16.0, 8.0)}   # estimated
HEXKEY = (2.5, 18.0)        # ISO 2936 2.5 mm key: across flats, short arm length
M3_HEAD = (5.5, 3.0)        # ISO 4762 M3 socket head: diameter, height


def pin_xy(n):
    """Pod (X, Y) of 40-pin header pin n (odd pins on the inner row, nearer the board centre)."""
    col = (n + 1) // 2 - 1
    by = PI5_HEADER_BY[0] if n % 2 else PI5_HEADER_BY[1]
    return b2p(PI5_PIN1_BX + 2.54 * col, by)


def pcb_top():
    return BOX_BOT_Z + WALL + PI_STANDOFF + PI5_T


def hat_bot():
    return pcb_top() + HAT_SPACER


def hat_top():
    return hat_bot() + HAT_T


def dupont_top():
    return hat_top() + DUPONT_SEAT + DUPONT_L


def fpc_xy():
    """Centre (X, Y) of the camera's CAM/DISP connector."""
    bx0, bx1 = PI5_FPC_B[PI5_FPC_USE]
    return b2p((bx0 + bx1) / 2, (PI5_FPC_BY[0] + PI5_FPC_BY[1]) / 2)


def ribbon_box_path():
    """Ribbon centreline from the cable window to the CAM/DISP connector, as 3D points (X, Y, Z), and the list of
    bends [(name, radius)]. Path: leaves the head's window at Z 2 heading -Y (width along X); S-bend (two R5) up to
    RIBBON_RUN_Z; straight run over the HAT; one 45 deg crease fold that turns it to -X (width now along Y, as the
    connector needs); R5 bend down into the connector."""
    r = BEND_R
    fx, fy = fpc_xy()
    z_top = pcb_top() + PI5_FPC_H
    lane_x = fx + r + 2.0                           # 0.4: on the centreline, straight out of the head
    pts = [(0.0, HEAD_REAR_Y, 2.0)]
    # S-bend up from Z 2 to RIBBON_RUN_Z: two arcs of angle a with 2r(1 - cos a) = dz
    dz = RIBBON_RUN_Z - 2.0
    a = math.acos(1 - dz / (2 * r))
    y0 = HEAD_REAR_Y - 6.0
    pts.append((0.0, y0, 2.0))
    n = 6
    for i in range(1, n + 1):
        t = a * i / n
        pts.append((0.0, y0 - r * math.sin(t), 2.0 + r * (1 - math.cos(t))))
    yc, zc = pts[-1][1], pts[-1][2]
    for i in range(1, n + 1):
        t = a * i / n
        pts.append((0.0, yc - r * (math.sin(a) - math.sin(a - t)), zc + r * (math.cos(a - t) - math.cos(a))))
    pts = [(lane_x, y, z) for _, y, z in pts]
    pts.append((lane_x, fy, RIBBON_RUN_Z))          # fold point
    pts.append((fx + r, fy, RIBBON_RUN_Z))          # -X to the bend
    for i in range(1, n + 1):
        t = (math.pi / 2) * i / n
        pts.append((fx + r - r * math.sin(t), fy, RIBBON_RUN_Z - r * (1 - math.cos(t))))
    pts.append((fx, fy, z_top - 3.0))               # into the connector, 3 mm insertion
    return pts, [("window S-bend 1", r), ("window S-bend 2", r), ("45 deg crease fold", 0.0), ("down into FPC", r)]


def path3_length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def ribbon_total_length():
    """Head part of the original path (camera to the window) plus the box part."""
    head = 0.0
    pts = ribbon_path()
    for a, b in zip(pts, pts[1:]):
        if b[0] < HEAD_REAR_Y:
            head += math.dist(a, (HEAD_REAR_Y, a[1] + (b[1] - a[1]) * (a[0] - HEAD_REAR_Y) / (a[0] - b[0])))
            break
        head += math.dist(a, b)
    return head, path3_length(ribbon_box_path()[0])
