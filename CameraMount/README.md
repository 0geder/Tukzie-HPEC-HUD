# Forward-facing camera mount

Files: `camera_mount.scad` (source, parametric), `camera_mount.stl` (print-ready),
`camera_mount_final.png` (reference render).

## What this holds

The Raspberry Pi Camera Module v1 (OV5647) already in use on this project.
No verified mechanical drawing giving exact mounting-hole positions could be
found for this board (checked raspberrypi-spy, Arducam, Geekworm, UCTronics
- all confirm the 25x24mm PCB footprint, none gave hole coordinates), so
rather than guess and risk a print that can't be screwed down, this holds
the board with a friction-fit pocket sized to the well-corroborated PCB
envelope, retained by a printed lip over the edges. No dependence on hole
position at all.

## Before printing

**Measure your actual physical board** and adjust `board_w`/`board_h`/
`board_thickness` at the top of `camera_mount.scad` if it differs even
slightly - the pocket clearance is intentionally tight (0.3mm/side) for a
friction fit. Also treat `lens_hole_d` and `lens_offset_from_top` as first
guesses, not verified measurements - check them against the real board
before committing to a full-size print.

Recommend a quick test print of just the pocket at low infill first to
check board fit before printing the full assembly.

## Mounting

The base plate has two zip-tie slot pairs at the rear, separated from the
camera pocket (front) so a zip-tie has a genuinely clear path both through
the slots and across the top of the base - no specific frame-tube diameter
is assumed; wrap a zip-tie around whatever the actual mounting point turns
out to be. `tilt_deg` (currently 5°) sets a slight forward-down camera
angle - adjust once the actual mounting height/angle on the vehicle is
known.

## A note on the design process

While building this, an early version's STL export reported "Volumes: 2",
which was initially (incorrectly) read as evidence the two halves weren't
fused into one printable piece. Testing that assumption against a plain
single cube showed OpenSCAD's CGAL report normally reads "Volumes: 2" for
any single valid solid - a false alarm, corrected here rather than left
unstated. The investigation did surface a real, separate bug in the
process: the pocket cavity cut was sized to reach the very top of the
holder, which meant the retention lip never actually existed in the first
version - fixed by stopping the cavity cut exactly at the lip's boundary.
Final geometry was confirmed with a full CGAL render (`--render`, not the
faster preview mode, which had its own separate visual-only artifact that
briefly looked like a missing lens hole) - "Simple: yes" reported, no
errors, lip and lens hole both confirmed present in the accurate render.
