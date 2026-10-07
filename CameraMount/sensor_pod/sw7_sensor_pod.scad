// SW-7 sensor pod: camera + ToF sensor board at the front, Raspberry Pi 4 and the ESP32 telemetry board
// behind, in one printed housing, so the camera and the three distance sensors keep a fixed geometry.
//   openscad -D 'part="base"' -o base.stl sw7_sensor_pod.scad      (parts: "base", "lid", "assembly")
//
// Values marked MEASURE are placeholders, NOT measurements. Do not print until they are replaced
// (CameraMount/sensor_pod/README.md lists what to measure). Values marked KNOWN come from a source:
//   - Raspberry Pi 4: 85 x 56 mm board, M2.5 holes on a 58 x 49 mm pattern, 3.5 mm from the edges
//     (Raspberry Pi 4 Model B mechanical drawing).
//   - Camera: the case already printed for this project, CameraMount/casing/RPi_cam_case_*.stl,
//     measured from the STL files as 29.2 x 28.2 mm, 12.35 mm deep with top and bottom together.
// Coordinates: X left to right, Y front (0) to back, Z up. Print the base upright, the lid upside down,
// in PETG or ASA (not PLA: it softens around 55 to 60 C).

part = "assembly";

// ---------- KNOWN ----------
pi_l = 85; pi_w = 56; pi_hole_dx = 58; pi_hole_dy = 49; pi_hole_in = 3.5; pi_hole_d = 2.7;
cam_case_w = 29.2; cam_case_h = 28.2; cam_case_d = 12.35;

// ---------- MEASURE: sensor board (JCP 2025 Sense v1.0) ----------
sb_w = 70;            // MEASURE: width, left to right, with the side sensors fitted
sb_d = 45;            // MEASURE: depth, front to back
sb_t = 1.6;           // MEASURE: PCB thickness
sb_top = 10;          // MEASURE: tallest part above the PCB (ToF breakouts, header)
sb_under = 3;         // MEASURE: tallest part or pin under the PCB
sb_side_angle = 35;   // MEASURE: angle of the side sensors from straight ahead (degrees)
sb_sensor_z = 5;      // MEASURE: height of the ToF lens centre above the PCB top
sb_ahead_y = 4;       // MEASURE: ahead sensor's lens, distance behind the board's front edge
sb_side_x = 28;       // MEASURE: side sensors' lenses, distance left/right of the centre line
sb_side_y = 12;       // MEASURE: side sensors' lenses, distance behind the board's front edge
imu_l = 21; imu_w = 16;   // MEASURE: IMU breakout size (two pockets in the ESP32 bay floor)

// ---------- MEASURE: ESP32 telemetry board ----------
esp_l = 90; esp_w = 60; esp_h = 22;   // MEASURE: length, width, height incl. tallest part

// ---------- design ----------
wall = 2.4; floor_t = 3; lid_t = 2.4; clear = 0.6;
standoff_h = max(sb_under + 1.5, 5);
gap = 6;                                   // between parts inside
rear_w = pi_w + esp_w + 3 * gap;           // Pi and ESP32 side by side, long sides front to back
rear_d = max(pi_l, esp_l) + 2 * gap;
front_d = sb_d + 2 * gap;
inner_w = max(rear_w, sb_w + 2 * gap);
inner_d = front_d + rear_d;
cam_shelf_z = floor_t + standoff_h + sb_t + sb_top + 3;      // camera case sits above the sensor board
inner_h = max(cam_shelf_z - floor_t + cam_case_h + 4, esp_h + standoff_h + 6, 34);
// Angled front corners: the flat centre face ends 6 mm inside the side sensors, so each side sensor
// looks out through its own angled face (set by sb_side_x and sb_side_angle once measured).
chamfer = (inner_w + 2 * wall) / 2 - max(10, sb_side_x - 6);
outer = [inner_w + 2 * wall, inner_d + 2 * wall, floor_t + inner_h];
cx = outer[0] / 2;                         // centre line: camera and the ahead sensor sit on it
sensor_z = floor_t + standoff_h + sb_t + sb_sensor_z;

module shell(sz, r = 3) {                  // box with the two front corners cut at the sensor angle
    c = max(4, chamfer - (outer[0] - sz[0]) / 2);   // inner shells follow the outer face, a wall thickness in
    linear_extrude(sz[2]) offset(r = r) offset(delta = -r)
        polygon([[c, 0], [sz[0] - c, 0], [sz[0], c * tan(sb_side_angle)], [sz[0], sz[1]], [0, sz[1]], [0, c * tan(sb_side_angle)]]);
}

// Line-of-sight cut: a cone from point p pointing at bearing b (degrees from straight ahead, + = right),
// opening at half-angle h plus a margin, long enough to pass through any wall in front of it. The window
// in the wall is therefore exactly where, and as wide as, the sensor or camera actually looks.
module sight(p, b, h, start_r = 2.5, len = 70) {
    translate(p) rotate([0, 0, b]) rotate([90, 0, 0])      // +b turns the forward (-Y) axis to the right
        cylinder(r1 = start_r, r2 = start_r + len * tan(h + 3), h = len, $fn = 48);
}

module windows() {
    board_front = wall + gap;                        // y of the sensor board's front edge
    // the three ToF sensors (VL53L0X field of view about 25 degrees, half-angle 12.5)
    sight([cx, board_front + sb_ahead_y, sensor_z], 0, 12.5);
    for (s = [-1, 1])
        sight([cx + s * sb_side_x, board_front + sb_side_y, sensor_z], s * sb_side_angle, 12.5);
    // camera: horizontal half field of view 26.75 degrees (53.5, as in fusion_config.json), from the lens
    sight([cx, wall + 3, cam_shelf_z + cam_case_h / 2], 0, 26.75, 6, 40);
}

module base() {
    difference() {
        union() {
            shell(outer);
            // mounting ears at the back corners (hose clamp or zip tie slots, M5 hole)
            for (x = [-18, outer[0]]) translate([x, outer[1] - 40, 0]) cube([18, 40, floor_t]);
        }
        translate([wall, wall, floor_t]) shell([inner_w, inner_d, inner_h + 1], 2);
        windows();
        // Pi 4 ports: USB-A and Ethernet end through the back wall, USB-C power side through the right wall
        pi_x = wall + gap; pi_y = wall + front_d;
        translate([pi_x - 1, outer[1] - wall - 1, floor_t + 4]) cube([pi_w + 2, wall + 2, 18]);
        translate([outer[0] - wall - 1, pi_y + 2, floor_t + 4]) cube([wall + 2, pi_l - 4, 12]);
        // ESP32: three cable holes (USB, antenna leads) in the back wall
        for (k = [0, 1, 2]) translate([wall + 2 * gap + pi_w + 12 + k * 16, outer[1] - wall - 1, floor_t + 12])
            rotate([-90, 0, 0]) cylinder(d = 7, h = wall + 2, $fn = 24);
        // two IMU pockets in the floor of the ESP32 bay (IMUs sit on the stiff floor, no foam)
        for (k = [0, 1]) translate([wall + 2 * gap + pi_w + 6 + k * (imu_l + 8), wall + front_d + esp_l + gap - imu_w - 4, floor_t - 1.5])
            cube([imu_l + 1, imu_w + 1, 2]);
        // mounting ear slots and holes
        for (x = [-9, outer[0] + 9]) {
            for (y = [outer[1] - 32, outer[1] - 14]) translate([x - 2.5, y - 6, -1]) cube([5, 12, floor_t + 2]);
            translate([x, outer[1] - 23, -1]) cylinder(d = 5.4, h = floor_t + 2, $fn = 24);
        }
    }
    // Pi 4 standoffs on its hole pattern (M2.5 heat-set insert or self-tapping, 2.2 mm pilot)
    pi_x = wall + gap; pi_y = wall + front_d;
    for (dx = [0, pi_hole_dy], dy = [0, pi_hole_dx])
        translate([pi_x + pi_hole_in + dx, pi_y + pi_hole_in + dy, floor_t]) difference() {
            cylinder(d = 6, h = standoff_h, $fn = 24);
            cylinder(d = 2.2, h = standoff_h + 1, $fn = 16);
        }
    // sensor board rails along its left and right edges (edge-held: no hole positions assumed)
    intersection() {                                   // keep the rails inside the cavity
        translate([wall, wall, 0]) shell([inner_w, inner_d, outer[2]], 2);
        for (x = [cx - sb_w / 2 - clear - 2, cx + sb_w / 2 + clear])
            translate([x, wall + gap, floor_t]) difference() {
                cube([2, sb_d, standoff_h + sb_t + 2]);
                translate([x < cx ? 1 : -1, -1, standoff_h]) cube([2, sb_d + 2, sb_t + 0.3]);  // slot the PCB slides into
            }
    }
    // ESP32 bay: corner guides
    ex = wall + 2 * gap + pi_w; ey = wall + front_d;
    for (p = [[0, 0], [esp_w, 0], [0, esp_l], [esp_w, esp_l]])
        translate([ex + p[0] - (p[0] ? 0 : 3), ey + p[1] - (p[1] ? 0 : 3), floor_t]) cube([3, 3, 8]);
    // camera shelf with a pocket for the printed camera case, lens facing the front window
    translate([cx - cam_case_w / 2 - 3, wall, cam_shelf_z - 3]) difference() {
        cube([cam_case_w + 6, cam_case_d + 6, 3 + 6]);
        translate([3 - clear / 2, -1, 3]) cube([cam_case_w + clear, cam_case_d + 1 + clear, 7]);
    }
    // shelf supports down to the floor, clear of the sensor board's front edge
    for (x = [cx - cam_case_w / 2 - 3, cx + cam_case_w / 2 + 1])
        translate([x, wall, floor_t]) cube([2, 4, cam_shelf_z - floor_t - 3]);
}

module lid() {
    difference() {
        shell([outer[0], outer[1], lid_t]);
        // 30 mm fan over the Pi's processor area, with its four M3 holes (24 mm pattern)
        fx = wall + gap + pi_w / 2; fy = wall + front_d + pi_l * 0.45;
        translate([fx, fy, -1]) cylinder(d = 28, h = lid_t + 2, $fn = 60);
        for (sx = [-12, 12], sy = [-12, 12]) translate([fx + sx, fy + sy, -1]) cylinder(d = 3.3, h = lid_t + 2, $fn = 16);
        // vent slots over the ESP32 bay
        for (k = [0:5]) translate([wall + 2 * gap + pi_w + 8, wall + front_d + 12 + k * 12, -1]) cube([esp_w - 16, 3, lid_t + 2]);
    }
    translate([wall + 0.3, wall + 0.3, -3]) difference() {   // locating lip
        shell([inner_w - 0.6, inner_d - 0.6, 3], 2);
        translate([2, 2, -1]) shell([inner_w - 4.6, inner_d - 4.6, 5], 1);
    }
}

if (part == "base") base();
else if (part == "lid") translate([0, 0, lid_t]) rotate([180, 0, 0]) lid();
else {
    color("SteelBlue") base();
    color("LightGray", 0.4) translate([0, 0, outer[2] + 15]) lid();
    // stand-ins for checking fit only
    color("DarkGreen") translate([wall + gap, wall + front_d, floor_t + standoff_h]) cube([pi_w, pi_l, 1.4]);
    color("Teal") translate([wall + 2 * gap + pi_w, wall + front_d, floor_t]) cube([esp_w, esp_l, 1.6]);
    color("Orange") translate([cx - sb_w / 2, wall + gap, floor_t + standoff_h]) cube([sb_w, sb_d, sb_t]);
    color("Gold") translate([cx - cam_case_w / 2, wall + 3, cam_shelf_z]) cube([cam_case_w, cam_case_d, cam_case_h]);
}
echo(str("Pod outer size (mm): ", outer[0], " x ", outer[1], " x ", outer[2] + lid_t, "; camera lens centre ",
         cam_shelf_z + cam_case_h / 2, " mm and ToF ", sensor_z, " mm above the floor"));
