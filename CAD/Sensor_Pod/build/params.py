"""SW-7 front sensor pod: every size in one place (mm and degrees).

Pod frame used by every script and every part (all parts are modelled in place, so the assembly needs no mates):
  X to the right when looking forward, Y forward, Z up.
  Origin: centre of the sensor board's long (86 mm, rear) edge, on the top surface of its PCB.
SolidWorks model axes: model X = pod X, model Y = pod Z (up), model Z = -pod Y. So the SolidWorks *Back view looks at
the pod's face and *Front looks at its rear.

Source labels: measured (student), official (datasheet or design file), estimated (check), design (my choice).
Change a value here and rerun the build scripts in order (see README.md).
"""
import math

# ---------------- Sensor board (JCP 2025 Sense v1.0) ----------------
BOARD_REAR = 86.0          # measured: long straight edge (rear)
BOARD_FRONT = 41.0         # measured: front edge (photo suggests 44 to 47: MEASURE)
BOARD_END = 22.0           # measured: the two short end edges, square to the rear edge
BOARD_ANGLED = 30.0        # measured (one side only): the angled edges
BOARD_DEPTH = BOARD_END + math.sqrt(BOARD_ANGLED ** 2 - ((BOARD_REAR - BOARD_FRONT) / 2) ** 2)   # derived, 41.8
PCB_T = 1.6                # estimated
ABOVE_PCB = 14.0           # measured: tallest parts above the PCB (ToF carriers on their headers)
BELOW_PCB = 6.0            # measured: pin tails under the PCB
MID_PARTS_H = 9.0          # estimated: jumpers J1/J3 and the U1 socket in the middle of the board (ribbon runs over)
BOARD_HOLES = [(sx * 11.3, y) for sx in (-1, 1) for y in (11.8, 34.9)]   # estimated from the photo: M2, MEASURE
BOARD_HOLE_PILOT = 1.6     # M2 self-tapping into PETG
J2_X = 19.0                # estimated: 2 x 16 header spans X -19..+19
J2_Y = (0.8, 6.3)          # estimated: plug housings around rows at Y 2.1 and 5.0
DUPONT_DROP = 14.0         # estimated: Dupont housing length below the PCB, plugs on J2 from below
BEND_R = 5.0               # design: minimum bend radius for the ribbon and the jumper bundle
BOARD_GAP = 3.0            # design: board to wall gap (3 until the front edge and depth are measured, then 1.5)

# ---------------- ToF sensors (VL53L0X on carriers J4 left, J5 ahead, J6 right) ----------------
TOF_FOV = 25.0             # official (ST DS11555 5.1): full cone
TOF_MARGIN_DEG = 5.0       # design: window flare = 12.5 + 5 = 17.5 deg half-angle
TOF_WIN_MARGIN = 1.0       # design: window starts 1 mm larger than the package on each side
TOF_PKG = (4.4, 2.4)       # official: VL53L0X package
TOF_Z = 9.0                # estimated: chip centre height above the PCB top. MEASURE
TOF_AHEAD = (0.0, 43.0)    # estimated: ahead chip on the J5 carrier face, about 1 mm proud of the front edge
# tof_side_bearing: 90 = as built (carriers on J4/J6 look straight out sideways, photos 12 Oct).
# 35 = remote-mounted carriers aimed as CameraDetection/fusion_config.json assumes (bearings -35, 0, +35).
# The fusion config and the as-built board DISAGREE; the finger test in the layout file settles it (C9 calibration).
TOF_SIDE_BEARING = 90.0
TOF_SIDE_POS = {90.0: (24.5, 32.0),          # estimated from the photo (X -26 / +23 measured off the photo)
                35.0: (30.0, 38.0)}           # design: carriers on leads, behind the front corner facets
TOF_CONE_LEN = 70.0        # reference cone length drawn in the assembly

# ---------------- Camera (OV5647 v1 NoIR in the yellow printed case) ----------------
CAM_W, CAM_H, CAM_D = 29.2, 28.2, 12.35   # measured (STL): width X, height Z, depth Y
CAM_FRONT_Y = 43.0         # design: case front face
CAM_BOTTOM_Z = 17.0        # design: case bottom, 3 mm above the 14 mm carriers
CAM_LENS_UP = 11.6         # measured (STL): lens centre above the case bottom
CAM_LENS_OPEN = 9.6        # measured (STL): lens opening in the case cover
CAM_HFOV, CAM_VFOV = 53.5, 41.41          # official (Raspberry Pi camera docs)
CAM_FOV_MARGIN = 3.0       # design: window flare = 26.75 + 3 = 29.75 deg
CAM_FIT = 0.3              # design: case clearance in the cradle
RIBBON_W, RIBBON_T, RIBBON_LEN = 16.0, 0.3, 150.0   # width estimated, length from the report (15 cm): MEASURE
RIBBON_EXIT_Y = 35.0       # measured (STL): ribbon leaves the case bottom 1.2..7.6 mm in front of its rear face

# ---------------- Sensor head ----------------
WALL = 2.4                 # design: head and box walls, roof and floor
HEAD_X = BOARD_REAR / 2 + BOARD_GAP + WALL           # 48.4 half-width outside
HEAD_REAR_Y = -11.9        # outer face of the head's rear wall (flange face)
CAM_FOAM = 2.8             # design: foam ring between the camera case front and the front wall
HEAD_FRONT_Y = CAM_FRONT_Y + CAM_FOAM + WALL   # 48.2: outer front face
HEAD_TOP_Z = 50.6          # roof outer
HEAD_BOT_Z = -28.4         # floor outer (same as the box)
HEAD_SPLIT_Z = -4.0        # upper shell / lower tray split (lip seam), under the PCB
SKIRT_T, SKIRT_H, SKIRT_FIT = 1.2, 3.0, 0.3          # lip seam: skirt on the upper shell inside the tray walls
VISOR = 7.8                # design: brow over the camera window projects this far past the front face
VISOR_Z = 40.0             # design: brow underside (drip edge)
ROOF_SLOPE_Y = 40.0        # design: where the sloped front roof facet meets the flat roof
ROOF_CHAMFER = 10.0        # design: 45 deg top corner facets (front view)
REAR_CHAMFER = 10.0        # design: rear top facet (side view)
CORNER_CHAMFER = 6.0       # design: vertical front corner facets (plan view)
LOWER_FRONT_FACET = (-10.0, 41.0)  # design: lower front facet runs from Z -10 at the front face back to Y 41 at the floor
LOWER_SIDE_FACET = 6.0     # design: lower side facets (front view), tray only
LIGHTBAR_Z = (1.5, 3.5)    # design: light-bar groove on the front face
LIGHTBAR_DEPTH = 1.0
HOOD_Z = 14.0              # design: ahead ToF drip hood underside
HOOD_L = 6.0               # design: hood projection (cone clear if L < 3.2 x height above the beam edge)
SIDE_HOOD_L = 4.0          # design: hoods over the side windows
CABLE_WIN = (-20.0, 20.0, -24.0, 8.0)   # design: X0, X1, Z0, Z1 of the window through the head and box walls
FLANGE_BOLTS = [(-32.0, 2.0), (32.0, 2.0), (-32.0, -20.0), (32.0, -20.0)]   # (X, Z): M3 from inside the box into
#   heat-set inserts in bosses on the head's rear wall; the top two hold the upper shell, the bottom two the tray
SEAM_SCREWS = [(-1, 34.0, -8.0), (1, 34.0, -8.0)]   # (side, Y, Z): M3 through the tray side walls into the upper
#   shell's inner blocks (front of the lip seam); the flange bolts hold the rear
RETAINER_SCREWS = [(sx * 16.9, y) for sx in (-1, 1) for y in (31.0, 43.5)]   # M2 x 6 into the camera rails
INSERT_M3_D, INSERT_M3_L = 4.0, 6.0     # M3 heat-set insert hole
M3_CLEAR = 3.4
M2_PILOT = 1.6
M25_PILOT = 2.2
TIE_SLOT = (4.0, 2.0)      # cable-tie anchor slot (width, height) under a bridge

# ---------------- Electronics box ----------------
BOX_X = 72.4               # half-width outside
BOX_FRONT_Y = HEAD_REAR_Y  # box front wall outer face touches the head flange
BOX_REAR_Y = -154.4
BOX_BOT_Z = HEAD_BOT_Z
BOX_TOP_Z = 10.0           # top of the base walls; the lid sits on it
LID_T = 2.4
LID_SKIRT = 1.6            # outer drip skirt and inner tongue thickness
LID_TONGUE_H = 3.0
LID_FIT = 0.3
GNSS_WIN_T = 1.2           # thinned roof over the GNSS patch (plastic only, no metal or carbon fill)
DIVIDER_Y = -86.0          # front face of the Pi / ESP32 divider (2 thick)
LID_SCREWS = [(sx * 66.5, y) for sx in (-1, 1) for y in (-18.5, -92.0, -148.0)]

# Raspberry Pi 4 (official mechanical drawing): 85 x 56, M2.5 holes 58 x 49, 3.5 from the edges
PI_X0, PI_X1 = -40.0, 45.0   # design: USB-A / Ethernet end at -X, USB-C edge forward
PI_Y1 = -26.3                # front (USB-C, HDMI) edge
PI_Y0 = PI_Y1 - 56.0
PI_STANDOFF = 8.0            # design: PCB bottom 8 above the floor's inner face
PI_HOLES = [(41.5, -29.8), (-16.5, -29.8), (41.5, -78.8), (-16.5, -78.8)]
PI_FAN = (16.0, -58.0, 30.0, 10.0)   # centre X, Y, size (measured 30), thickness (estimated 10)

# Makerfabs ESP32-S3 A7670X (official .brd): 75 x 52, M2 holes on 71 x 48, 2 from the edges
ESP_X0, ESP_Y0 = -46.0, -149.0     # design: board corner with the two side USB-C ports
ESP_L, ESP_W = 75.0, 52.0
ESP_STANDOFF = 12.0                # design: room for the LiPo underneath (LiPo thickness: MEASURE)
ESP_HOLES = [(ESP_X0 + x, ESP_Y0 + y) for x in (2.0, 73.0) for y in (2.0, 50.0)]
GNSS_PATCH = (25.0, 25.0, 8.0)     # estimated (active patch); MEASURE
BUCK = (32.0, -148.0, 35.0, 56.0, 20.0)   # placeholder 5 V buck: X0, Y0, width X, length Y, height

# Openings in the box
USB_HATCH = (-80.0, -48.0, -18.0, 0.0)    # Y0, Y1, Z0, Z1 in the -X wall: reach the flash drive without the lid off
HATCH_BOSSES = [(-86.0, -23.0), (-86.0, 3.0), (-42.0, -23.0), (-42.0, 3.0)]   # (Y, Z) M3 inserts for the cover
HATCH_COVER = (-90.0, -38.0, -27.0, 6.5, 3.0)   # Y0, Y1, Z0, Z1, thickness
LTE_SMA = (10.0, 0.0, 6.5)       # X, Z, hole diameter for an SMA bulkhead on the rear wall
GLAND = (55.0, -14.0, 12.5)      # X, Z, hole diameter: PG7 gland or rubber grommet for the vehicle 5 V / 12 V feed
VENT_UPSTAND = 3.0

# ---------------- Mount (quick-release dovetail plus tube clamp) ----------------
TUBE_D = 22.2              # estimated (brief): handlebar / tube; MEASURE (25.4 on some bars)
TUBE_LINER = 1.0           # rubber strip under the clamp
MOUNT_Y = -70.0            # design: clamp centre under the box, near the centre of mass
RAIL_PLATE = (60.0, 64.0, 6.0)      # X, Y, thickness (bolt heads counterbored 3.5)
RAIL_W, RAIL_W2, RAIL_H = 30.0, 38.0, 6.0   # dovetail (matches the dashboard rail)
RAIL_BOLTS = [(sx * 22.0, MOUNT_Y + sy * 22.0) for sx in (-1, 1) for sy in (-1, 1)]
BRACKET = (56.0, 60.0, 18.0)        # channel block X, Y, Z
SLIDE = 0.3
STOP_T = 6.0
CLAMP_W, CLAMP_HALF, CLAMP_DROP, CAP_T = 40.0, 20.0, 12.0, 12.0
CLAMP_BOLT_OFF = 16.6
M5_INSERT_D, M5_CLEAR = 6.4, 5.5
LOCK_D = 3.3
POD_TILT_DEG = 0.0         # set on the vehicle by turning the clamp round the tube before tightening

SUNSHADE = (50.0, -84.0, -20.0, 5.0, 2.0)   # half-width X, Y0, Y1, air gap, thickness: second roof over the Pi bay
SUNSHADE_POSTS = [(sx * 44.0, y) for sx in (-1, 1) for y in (-24.0, -80.0)]
PRINT_LIMIT = 180.0        # Prusa Mini


def tof_chips():
    """[(name, x, y, z, bearing_deg)] in the pod frame; bearing 0 = straight ahead, positive to the right."""
    sx, sy = TOF_SIDE_POS[TOF_SIDE_BEARING]
    return [("Left", -sx, sy, TOF_Z, -TOF_SIDE_BEARING),
            ("Ahead", TOF_AHEAD[0], TOF_AHEAD[1], TOF_Z, 0.0),
            ("Right", sx, sy, TOF_Z, TOF_SIDE_BEARING)]


def board_outline():
    a = (BOARD_REAR - BOARD_FRONT) / 2
    return [(-BOARD_REAR / 2, 0), (BOARD_REAR / 2, 0), (BOARD_REAR / 2, BOARD_END),
            (BOARD_FRONT / 2, BOARD_DEPTH), (-BOARD_FRONT / 2, BOARD_DEPTH), (-BOARD_REAR / 2, BOARD_END)]


def cam_box():
    """Camera case extents: x0, x1, y0, y1, z0, z1."""
    return (-CAM_W / 2, CAM_W / 2, CAM_FRONT_Y - CAM_D, CAM_FRONT_Y, CAM_BOTTOM_Z, CAM_BOTTOM_Z + CAM_H)


def lens():
    return (0.0, CAM_FRONT_Y, CAM_BOTTOM_Z + CAM_LENS_UP)


def ribbon_path():
    """Ribbon centreline in the Y-Z plane at X = 0, as (y, z) points: down out of the case, R5 bend rearwards over
    the board, S-bend down behind it, through the cable window, R5 down into the Pi's CSI connector."""
    r = BEND_R
    pts = []

    def arc(cy, cz, a0, a1, n=4):
        for i in range(n + 1):
            t = math.radians(a0 + (a1 - a0) * i / n)
            pts.append((cy + r * math.cos(t), cz + r * math.sin(t)))
    z_run = CAM_BOTTOM_Z - r            # 12: run height over the board
    pts.append((RIBBON_EXIT_Y, CAM_BOTTOM_Z + 2))
    arc(RIBBON_EXIT_Y - r, CAM_BOTTOM_Z, 0, -90)               # down then rearwards
    arc(-2.0, z_run - r, 90, 180)                              # S-bend, first half
    arc(-2.0 - 2 * r, z_run - r, 0, -90)                       # second half: now at z_run - 2r, heading rear
    z2 = z_run - 2 * r
    csi_y = -37.8
    arc(csi_y + r, z2 - r, 90, 180)                            # down into the CSI connector
    pts.append((csi_y, -11.0))
    return pts


def path_length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def inner_plan(t, c=CORNER_CHAMFER, x=HEAD_X, y0=HEAD_REAR_Y, y1=None):
    """Head plan outline offset inward by t (negative t = outward), front corners chamfered 45 deg."""
    y1 = HEAD_FRONT_Y if y1 is None else y1
    leg = c - t * (2 - math.sqrt(2))
    xi, yb, yf = x - t, y0 + t, y1 - t
    return [(-xi, yb), (xi, yb), (xi, yf - leg), (xi - leg, yf), (-xi + leg, yf), (-xi, yf - leg)]


def side_profile():
    """Upper shell side profile (Y, Z) without the brow: front face, sloped front roof facet, flat roof, rear facet."""
    slope = (HEAD_TOP_Z - (VISOR_Z + 2.5)) / (HEAD_FRONT_Y + VISOR - ROOF_SLOPE_Y)
    z_front_top = HEAD_TOP_Z - slope * (HEAD_FRONT_Y - ROOF_SLOPE_Y)
    return [(HEAD_REAR_Y, HEAD_SPLIT_Z), (HEAD_FRONT_Y, HEAD_SPLIT_Z), (HEAD_FRONT_Y, z_front_top),
            (ROOF_SLOPE_Y, HEAD_TOP_Z), (HEAD_REAR_Y + REAR_CHAMFER, HEAD_TOP_Z),
            (HEAD_REAR_Y, HEAD_TOP_Z - REAR_CHAMFER)], slope


def ray_exit(x, y, bearing, poly=None):
    """Distance from (x, y) along the bearing to where it leaves the head's outer plan outline."""
    poly = poly or inner_plan(0)
    b = math.radians(bearing)
    dx, dy = math.sin(b), math.cos(b)
    best = 1e9
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((x1 - x) * ey - (y1 - y) * ex) / den
        u = ((x1 - x) * dy - (y1 - y) * dx) / den
        if t > 0 and -1e-9 <= u <= 1 + 1e-9:
            best = min(best, t)
    return best
