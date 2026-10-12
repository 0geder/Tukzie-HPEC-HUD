"""Sensor pod step 4: the rail plate under the electronics box, and the reference parts for the assembly.

The rail plate carries the same dovetail as the dashboard (30 to 38 mm, 6 mm high, 80 mm long), so the pod uses the
dashboard's bar clamp unchanged: CAD/Dashboard_Enclosure/SW7_Dash_Bracket.SLDPRT and SW7_Dash_Clamp_Cap.SLDPRT.
One clamp design for both, and either can go on any 22.2 mm bar.
Here the rail runs fore and aft, so the pod slides forward onto the clamp. The bracket is fitted with its closed end
at the front, so braking pushes the pod against the stop and the thumb screw stops it sliding back.

Reference parts (not printed): sensor board with its three ToF carriers, the camera case, the Pi 4 with its fan, the
ESP32 board with its GNSS patch, and the view cones (ToF 25 deg full cone, camera horizontal FOV) as thin bodies so
the assembly shows what each sensor sees.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import *          # noqa: F401,F403
from swlib import Part, PRINT, REF

ZB = BOX_BOT_Z
PLATE_Y = 84.0                 # long enough for the 80 mm rail
PLATE_T = RAIL_PLATE[2]
RAIL_L = 80.0

# ---------- Rail plate ----------
print("rail plate")
G = {"PlateX": RAIL_PLATE[0], "PlateY": PLATE_Y, "PlateT": PLATE_T, "RailW": RAIL_W, "RailW2": RAIL_W2,
     "RailH": RAIL_H, "RailL": RAIL_L}
p = Part(G)
hx, y0, y1 = RAIL_PLATE[0] / 2, MOUNT_Y - PLATE_Y / 2, MOUNT_Y + PLATE_Y / 2
zt, zb = ZB, ZB - PLATE_T
p.prism("Z", [("rect", -hx, y0, hx, y1)], zb, zt, "Rail Plate")
a, b = RAIL_W / 2, RAIL_W2 / 2
p.prism("Y", [("poly", [(-a, zb + 0.5), (a, zb + 0.5), (b, zb - RAIL_H), (-b, zb - RAIL_H)])],
        MOUNT_Y - RAIL_L / 2, MOUNT_Y + RAIL_L / 2, "Dovetail Rail")
p.cut("Z", [("circle", x, y, M3_CLEAR / 2) for x, y in RAIL_BOLTS], zb - 0.5, zt + 0.5, "M3 Holes")
p.cut("Z", [("circle", x, y, 3.0) for x, y in RAIL_BOLTS], zb - 0.5, zb + 3.5, "Counterbores")
p.save(os.path.join(PRINT, "SW7_Pod_Rail_Plate.SLDPRT"), "rail_plate_iso.png")
p.close_doc()

# ---------- Sensor board with carriers ----------
print("reference: sensor board")
r = Part()
r.prism("Z", [("poly", board_outline())], -PCB_T, 0.0, "PCB")
r.prism("Z", [("rect", -J2_X, J2_Y[0], J2_X, J2_Y[1])], -BELOW_PCB - DUPONT_DROP, 0.0, "J2 Header And Dupont Plugs")
for name, x, y, z, bearing in tof_chips():
    import math
    bb = math.radians(bearing)
    dx, dy = math.sin(bb), math.cos(bb)
    tx, ty = math.cos(bb), -math.sin(bb)
    w, d = 8.0, 2.0                     # carrier board 8 wide, 2 deep (with chip), standing on its header
    pts = [(x - tx * w / 2 - dx * d, y - ty * w / 2 - dy * d), (x + tx * w / 2 - dx * d, y + ty * w / 2 - dy * d),
           (x + tx * w / 2, y + ty * w / 2), (x - tx * w / 2, y - ty * w / 2)]
    r.prism("Z", [("poly", pts)], 0.0, ABOVE_PCB, f"ToF Carrier {name}")
r.save(os.path.join(REF, "REF_Sensor_Board.SLDPRT"))
r.close_doc()

# ---------- Camera case ----------
print("reference: camera")
c = Part()
x0, x1, cy0, cy1, cz0, cz1 = cam_box()
c.prism("Z", [("rect", x0, cy0, x1, cy1)], cz0, cz1, "Camera Case")
c.save(os.path.join(REF, "REF_Camera_Case.SLDPRT"))
c.close_doc()

# ---------- Pi 4 with fan ----------
print("reference: Pi 4")
q = Part()
pz0 = ZB + WALL + PI_STANDOFF
q.prism("Z", [("rect", PI_X0, PI_Y0, PI_X1, PI_Y1)], pz0, pz0 + 1.6, "Pi 4 PCB")
q.prism("Z", [("rect", PI_X0 - 2, PI_Y0 + 2, PI_X0 + 21, PI_Y1 - 2)], pz0 + 1.6, pz0 + 1.6 + 16.0, "USB And Ethernet")
fx, fy, fs, ft = PI_FAN
q.prism("Z", [("rect", fx - fs / 2, fy - fs / 2, fx + fs / 2, fy + fs / 2)], pz0 + 1.6 + 6, pz0 + 1.6 + 6 + ft, "Fan")
q.save(os.path.join(REF, "REF_Pi4_with_Fan.SLDPRT"))
q.close_doc()

# ---------- ESP32 board with GNSS patch ----------
print("reference: ESP32")
e = Part()
ez0 = ZB + WALL + ESP_STANDOFF
e.prism("Z", [("rect", ESP_X0, ESP_Y0, ESP_X0 + ESP_L, ESP_Y0 + ESP_W)], ez0, ez0 + 1.6, "ESP32 PCB")
gx = ESP_X0 + ESP_L / 2
gy = ESP_Y0 + ESP_W / 2
gw, gl, gh = GNSS_PATCH
e.prism("Z", [("rect", gx - gw / 2, gy - gl / 2, gx + gw / 2, gy + gl / 2)], ez0 + 1.6, ez0 + 1.6 + gh, "GNSS Patch")
e.prism("Z", [("rect", ESP_X0 + 5, ESP_Y0 + 5, ESP_X0 + ESP_L - 5, ESP_Y0 + ESP_W - 5)], ez0 - 8.0, ez0, "LiPo")
e.save(os.path.join(REF, "REF_ESP32_A7670.SLDPRT"))
e.close_doc()

# ---------- View cones ----------
print("reference: view cones")
v = Part()
for name, x, y, z, bearing in tof_chips():
    v.beam_feature((x, y, z), bearing, ("circle", 1.2), 0.0, TOF_CONE_LEN, TOF_FOV / 2, f"ToF Cone {name}",
                   cut=False, merge=False)
lx, ly, lz = lens()
v.beam_feature((lx, ly, lz), 0.0, ("circle", 1.5), 0.0, 60.0, CAM_HFOV / 2, "Camera FOV (horizontal)",
               cut=False, merge=False)
v.save(os.path.join(REF, "REF_View_Cones.SLDPRT"))
v.close_doc()
print("done")
