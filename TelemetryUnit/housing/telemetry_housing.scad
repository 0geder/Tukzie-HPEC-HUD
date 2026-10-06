// SW-7 telemetry unit housing (ESP32-S3 A7670X board + two MPU6050 IMUs), parametric.
// Render a part:  openscad -D 'part="base"' -o base.stl telemetry_housing.scad   (or "lid", "assembly")
//
// EVERY DIMENSION MARKED "MEASURE" IS A PLACEHOLDER, NOT A VERIFIED VALUE.
// Measure the real parts with calipers and change them here before printing (TelemetryUnit/housing/README.md).
//
// Design rules:
//  - The IMUs sit in pockets in a thick, stiff floor and the base bolts or clamps straight to the frame,
//    so vibration reaches them undamped (no foam under the IMUs: it would filter the ride signal).
//  - All plastic, no metal over the antennas (RF transparent). Print in PETG or ASA, not PLA: PLA softens
//    around 55 to 60 C, which a closed vehicle in the sun can reach.
//  - The board is held by its edges (pocket plus clamping ribs in the lid), so no hole positions are assumed.
//  - Removable (brief: equipment must come off quickly): two hose-clamp or zip-tie slots per side, plus
//    two M5 holes for a flat mount.

part = "assembly";            // "base", "lid" or "assembly"

// ---------- MEASURE: electronics ----------
board_l = 90;     // MEASURE: board length incl. connectors that overhang the PCB edge (mm)
board_w = 60;     // MEASURE: board width (mm)
board_h = 22;     // MEASURE: height from PCB underside to the tallest part on top (mm)
pcb_t   = 1.6;    // MEASURE: PCB thickness
under_h = 3;      // MEASURE: tallest part or pin on the PCB underside (sets standoff height)
imu_l = 21;       // MEASURE: IMU breakout length (GY-521 style boards are often about 21 x 16 mm)
imu_w = 16;       // MEASURE: IMU breakout width
imu_h = 3.5;      // MEASURE: IMU breakout thickness incl. components, without header pins
usb_z = 6;        // MEASURE: height of the USB socket centre above the PCB underside
usb_y = 30;       // MEASURE: USB socket centre measured from the board's left long edge
gnss_patch = 25;  // MEASURE: GNSS patch antenna side length, if it stays inside the box

// ---------- design values ----------
wall = 2.6; floor_t = 4; lid_t = 2.4;
clear = 0.6;                 // per side around the board and IMUs
imu_gap = 10;                // between the two IMUs and the board
standoff_h = under_h + 1.5;
usb_slot = [14, 9];          // width, height of the cable exit
lead_d = 6.5;                // antenna leads, Hall/sync wire
ear = 16;                    // mounting ear length
xo = 8;                      // room at each short end for the lid-screw posts
clamp_slot = [5, 14];        // hose clamp / zip tie slot

inner_l = board_l + 2 * clear + 2 * xo;
inner_w = board_w + imu_w + imu_gap + 3 * clear;
inner_h = standoff_h + board_h + 2;
outer = [inner_l + 2 * wall, inner_w + 2 * wall, floor_t + inner_h];

module rounded_box(size, r = 3) {
    hull() for (x = [r, size[0] - r], y = [r, size[1] - r])
        translate([x, y, 0]) cylinder(r = r, h = size[2], $fn = 32);
}

module base() {
    difference() {
        union() {
            rounded_box(outer);
            // mounting ears along both short ends
            for (x = [-ear, outer[0]]) translate([x, 0, 0]) cube([ear, outer[1], floor_t]);
        }
        // cavity
        translate([wall, wall, floor_t]) cube([inner_l, inner_w, inner_h + 1]);
        // IMU pockets in the floor, side by side, beside the board
        for (i = [0, 1])
            translate([wall + xo + clear + i * (imu_l + imu_gap), wall + board_w + 2 * clear + imu_gap, floor_t - 1.5])
                cube([imu_l + 2 * clear, imu_w + 2 * clear, 10]);
        // USB cable exit in the left short wall, at board height
        translate([-1, wall + clear + usb_y - usb_slot[0] / 2, floor_t + standoff_h + usb_z - usb_slot[1] / 2])
            cube([wall + 2, usb_slot[0], usb_slot[1]]);
        // two antenna leads and one wire exit in the right short wall
        for (k = [0, 1, 2])
            translate([outer[0] - wall - 1, wall + 12 + k * 14, floor_t + inner_h - 8])
                rotate([0, 90, 0]) cylinder(d = lead_d, h = wall + 2, $fn = 24);
        // condensation drain in a corner of the floor
        translate([wall + 3, wall + 3, -1]) cylinder(d = 1.5, h = floor_t + 2, $fn = 16);
        // clamp slots and M5 holes in the ears
        for (x = [-ear / 2, outer[0] + ear / 2]) {
            for (y = [outer[1] * 0.25, outer[1] * 0.75])
                translate([x - clamp_slot[0] / 2, y - clamp_slot[1] / 2, -1]) cube([clamp_slot[0], clamp_slot[1], floor_t + 2]);
            translate([x, outer[1] / 2, -1]) cylinder(d = 5.4, h = floor_t + 2, $fn = 24);
        }
    }
    // board standoff rails (support the PCB edges only, clear of underside parts)
    for (y = [wall + clear, wall + clear + board_w - 3])
        translate([wall + xo + clear, y, floor_t]) cube([board_l, 3, standoff_h]);
}

module lid() {
    difference() {
        union() {
            rounded_box([outer[0], outer[1], lid_t]);
            // locating lip inside the walls
            translate([wall + 0.3, wall + 0.3, -3]) cube([inner_l - 0.6, inner_w - 0.6, 3]);
            // ribs that press the board onto its rails
            for (y = [wall + clear + 1, wall + clear + board_w - 4])
                translate([wall + xo + clear + 5, y, -(inner_h - standoff_h - pcb_t)]) cube([board_l - 10, 3, inner_h - standoff_h - pcb_t]);
        }
        // hollow the lip so the board components clear it
        translate([wall + 2.3, wall + 2.3, -4]) cube([inner_l - 4.6, inner_w - 4.6, 4]);
        // GNSS patch recess on the underside: the patch faces the sky under 1.2 mm of plastic
        translate([outer[0] - wall - gnss_patch - 6, outer[1] / 2 - gnss_patch / 2, -1]) cube([gnss_patch + 1, gnss_patch + 1, lid_t - 1.2 + 1]);
        // four M3 lid screws into the corners
        for (x = [wall + 3, outer[0] - wall - 3], y = [wall + 3, outer[1] - wall - 3])
            translate([x, y, -10]) cylinder(d = 3.4, h = 20, $fn = 20);
    }
}

module corner_bosses() {
    for (x = [wall + 3, outer[0] - wall - 3], y = [wall + 3, outer[1] - wall - 3])
        translate([x, y, floor_t]) difference() {
            cylinder(d = 8, h = inner_h - 3, $fn = 24);
            cylinder(d = 2.6, h = inner_h, $fn = 20);   // M3 self-tapping pilot
        }
}

if (part == "base") { base(); corner_bosses(); }
else if (part == "lid") translate([0, 0, lid_t]) rotate([180, 0, 0]) translate([0, 0, 0]) lid();
else {
    color("SteelBlue") { base(); corner_bosses(); }
    color("LightGray", 0.55) translate([0, 0, outer[2] + 12]) lid();
    // stand-ins for the electronics, for checking fit only
    color("DarkGreen") translate([wall + xo + clear, wall + clear, floor_t + standoff_h]) cube([board_l, board_w, pcb_t]);
    color("Orange") for (i = [0, 1])
        translate([wall + xo + clear * 2 + i * (imu_l + imu_gap), wall + board_w + 3 * clear + imu_gap, floor_t - 1.5])
            cube([imu_l, imu_w, imu_h]);
}

echo(str("Outer size (mm): ", outer[0], " x ", outer[1], " x ", outer[2] + lid_t, " plus ears ", ear, " mm each end"));
