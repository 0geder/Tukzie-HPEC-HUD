// Forward-facing mount for the Raspberry Pi Camera Module v1 (OV5647).
//
// DESIGN CHOICE AND WHY: no verified mechanical drawing giving the exact
// mounting-hole positions could be found (checked raspberrypi-spy, Arducam,
// Geekworm, UCTronics - all confirm the 25x24mm PCB footprint but none gave
// precise hole coordinates). Guessing hole positions risks a print that
// physically cannot be screwed down. Instead, this holds the board with a
// friction-fit pocket sized to the well-corroborated PCB envelope, with a
// retention lip over the edges - no dependence on hole position at all.
//
// VERIFY BEFORE PRINTING: measure your actual physical board and adjust
// board_w/board_h/board_thickness below if it differs even slightly, since
// the pocket clearance is intentionally tight (friction fit).

// ---- Measured/assumed parameters (mm) ----
board_w = 25;           // PCB width (corroborated: raspberrypi-spy, Arducam, Geekworm)
board_h = 24;           // PCB height
board_thickness = 1.2;  // PCB thickness (~1mm typical, +margin)
pocket_clearance = 0.3; // per-side clearance for friction fit - tune after test print

lens_hole_d = 10;       // generous clearance around the lens barrel - VERIFY against
                        // your actual board; the lens module itself is roughly 8mm,
                        // this is not from a verified drawing, treat as a first guess
lens_offset_from_top = 8; // approx lens center distance from PCB top edge - ASSUMED,
                           // verify against physical board before printing

ribbon_slot_w = 18;     // flex ribbon cable exit slot width
ribbon_slot_h = 2.5;    // slot height (ribbon is thin; add margin over ~1mm cable)

wall = 2.2;             // holder wall thickness
lip_overlap = 1.0;      // how far the retention lip reaches over the board edge
lip_thickness = 1.0;    // lip thickness (keep thin so it can flex slightly on insert)

base_w = 40;            // mounting base plate width
base_h = 70;            // mounting base plate depth - elongated so the zip-tie
                         // zone (rear) and the camera pocket (front) don't
                         // overlap; see layout note below
base_thickness = 4;

tilt_deg = 5;           // slight downward tilt, adjust once mounting height/angle is known

// Zip-tie slots: generic, adjustable mount that doesn't assume a specific
// frame-tube diameter - wrap a zip-tie through both slots around whatever
// the actual mounting point turns out to be. Kept entirely within the rear
// third of the base, clear of the camera pocket above, so the tie has an
// unobstructed top-to-bottom path and something to actually wrap around
// between the two slots.
tie_slot_w = 3.5;
tie_slot_l = 10;
tie_zone_depth = 25;      // rear region reserved for the zip-tie wrap
tie_slot_from_rear = 7;   // first slot's distance from the rear edge
tie_slot_gap = 12;        // gap between the two slots - the tube/bar sits here

$fn = 64;

module camera_pocket() {
    pocket_w = board_w + 2 * pocket_clearance;
    pocket_h = board_h + 2 * pocket_clearance;
    pocket_depth = board_thickness + 0.4;

    difference() {
        // Outer holder shell
        translate([-pocket_w/2 - wall, -pocket_h/2 - wall, 0])
            cube([pocket_w + 2*wall, pocket_h + 2*wall, pocket_depth + lip_thickness + wall]);

        // Board pocket (open at the front for the lens, open at bottom for insertion).
        // Height stops exactly at wall + pocket_depth - it must NOT overcut into
        // the lip_thickness region above, or there is no material left to form
        // the retention lip at all (an earlier version added a +1 overcut margin
        // here that did exactly this, consuming the entire 1mm lip and leaving
        // the subsequent lip cut operating on already-void, degenerate geometry -
        // found via inspecting the isolated module's exported volume count).
        translate([-pocket_w/2, -pocket_h/2, wall])
            cube([pocket_w, pocket_h, pocket_depth]);

        // Retention lip cut - leaves a lip of lip_thickness around the top
        translate([-pocket_w/2 + lip_overlap, -pocket_h/2 + lip_overlap, wall + pocket_depth])
            cube([pocket_w - 2*lip_overlap, pocket_h - 2*lip_overlap, lip_thickness + 1]);

        // Lens hole, offset toward the "top" (away from ribbon exit)
        translate([0, pocket_h/2 - lens_offset_from_top, -1])
            cylinder(d = lens_hole_d, h = wall + 2);

        // Ribbon cable exit slot, opposite the lens side
        translate([-ribbon_slot_w/2, -pocket_h/2 - wall - 1, wall])
            cube([ribbon_slot_w, wall + 2, ribbon_slot_h]);
    }
}

module mount_base() {
    rear_edge = -base_h/2;
    slot1_y = rear_edge + tie_slot_from_rear;
    slot2_y = slot1_y + tie_slot_gap;

    difference() {
        translate([-base_w/2, -base_h/2, 0])
            cube([base_w, base_h, base_thickness]);

        // Both zip-tie slots, confined to the rear tie_zone_depth region -
        // clear of the camera pocket, which sits in the front region only.
        for (y = [slot1_y, slot2_y]) {
            translate([-tie_slot_l/2, y - tie_slot_w/2, -1])
                cube([tie_slot_l, tie_slot_w, base_thickness + 2]);
        }
    }
}

module camera_mount_assembly() {
    // Camera pocket sits entirely in the front region, past the rear
    // tie_zone_depth, with a small margin so it cannot overhang the base's
    // front edge either (checked against pocket_h + pocket_clearance).
    pocket_h_total = board_h + 2 * pocket_clearance;
    front_region_center = -base_h/2 + tie_zone_depth + pocket_h_total/2 + 3;

    // Embedded slightly into the base (not sitting exactly flush on top of
    // it) so the tilted pocket's coincident bottom face has genuine
    // overlapping material to fuse with, rather than a knife-edge touch.
    embed_depth = 1.2;
    union() {
        mount_base();
        translate([0, front_region_center, base_thickness - embed_depth])
            rotate([tilt_deg, 0, 0])
            camera_pocket();
    }
}

camera_mount_assembly();
