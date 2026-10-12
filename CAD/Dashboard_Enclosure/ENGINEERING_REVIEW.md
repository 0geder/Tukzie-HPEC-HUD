# Engineering review: dashboard display enclosure and handlebar mount

Reviewed 12 Oct 2026 on the saved SolidWorks 2025 files in this folder (commit 284e5d9 plus the working tree). No
geometry was changed in this pass. Every result below comes from the audit scripts in `build/audit_*.py`, which
open the saved parts and assembly through the SolidWorks API, or from arithmetic on the build-script parameters
where that is stated. No part has been printed or physically tested.

Acceptance classification: REQUIRES REVISION. The concept (four printed quarters, a rail plate with a dovetail,
a split bar clamp that stays on the vehicle, a Pi 5 cradle on the back) is sound and every part fits the Prusa
Mini bed, but four critical defects mean the parts as saved cannot be assembled into a working mount. All of them
are parameter or one-line script fixes followed by a rebuild (scripts 1, 2, 3 and 5).

## 1. Design overview

| Item | What it is | Saved size (mm) |
|---|---|---|
| Back shell (master, not printed) | Tray for the 272 x 187 x 20 display, 2.5 mm walls, 3 mm back, 1.2 x 1.5 mm snap lips on the long walls, 58 x 16 cable exit in the -X short wall, 16 vent slots, 20 M3 holes | 278.2 x 193.2 x 27 |
| Shell quarters (4) | The master cut at X = 0 and Z = 0 | 139.1 x 96.6 x 27 each |
| Rail plate | 4 mm plate, 8 M3, dovetail rail 30 to 38 mm wide, 6 high, 80 long | 120 x 86 x 10 |
| Joiner plate (2) | 3 mm, 2 M3 at 24 mm pitch | 44 x 20 x 3 |
| Cross joiner | 3 mm, 4 M3 at 24 x 24 | 40 x 40 x 3 |
| Pi 5 cradle | 3 mm base, 4 standoffs 6 OD x 7 high with 2.2 pilots (58 x 49), 4 M3 to the shell | 66 x 95 x 10 |
| Bracket | Dovetail channel (closed end down), upper clamp half, 2 M5 heat-set insert holes, M4 lock screw hole | 56 x 30 x 80 |
| Clamp cap | Lower clamp half, 2 M5 clearance holes | 40 x 12 x 40 |
| Assembly | Master shell, plates, cradle, bracket, cap, dummy bar, dummy display, dummy Pi 5 | 600 (bar) x 73.6 x 195.6 |

Frame used throughout (assembly and parts): X is the driver's right, Y is towards the screen (back face of the
shell at Y = 0, plates and bracket at negative Y), Z is down when fitted. The bar is at Y -34, Z +59.

Estimated mass (solid volume x 1.27 g/cm3 PETG, so an upper bound): shell 263 g, rail plate 73 g, bracket 92 g,
cap 12 g, cradle 25 g, joiners 12 g. With the display (about 1 kg, task brief) and a Pi 5 with cooler (about
60 g), the clamp carries about 1.5 kg.

## 2. Defect register

Severity: critical = the part cannot do its job or cannot be assembled; major = will probably fail in service or
needs a workaround to assemble; moderate = degrades fit, life or printability; minor = tidy-up.

| ID | Component | Location | Problem (measured unless stated) | Why it matters | Proposed correction | Severity |
|---|---|---|---|---|---|---|
| D1 | Clamp cap | Bar bore | The cap is two separate solid bodies (audit 3: bodies 2). The bore radius is 12.1 mm centred on the cap's top face, and the cap is only 12 mm thick (CapT), so the bore cuts right through, leaving a 3.1 mm slot at the bottom (bodies at Z 1.55..20 and -20..-1.55). | There is no material under the bar. The cap is two loose wedges, so the clamp cannot hold the bar at all. | CapT = 17 (4.9 mm under the liner). Keep M5 x 30 bolts (bolt tip ends 1 mm above the split face, full 10 mm insert engagement). | Critical |
| D2 | Bracket and cap | M5 holes | Bracket: 0.20 mm of material between each 6.4 mm insert hole and the clamp boss's outer face, over the whole insert depth (Y -12 to 0), and 1.30 mm to the bar bore (audit 4). Cap: 0.65 mm to the outer face, 1.75 mm to the bore. Cause: BoltZ 16.6 with ClampZ 20 (half width). | A heat-set insert needs 2 to 3 mm of wall. A 0.2 mm skin will split while the insert is pressed in, and the clamp preload has nothing to react against. | ClampZ = 26 (boss and cap 52 mm across the bar), BoltZ = 18.5: insert hole wall 3.2 mm to the bore and 4.3 mm to the outside; cap holes 3.65 and 4.75 mm. The channel block (80 mm long) already covers this. | Critical |
| D3 | Back shell and quarters | Rail plate and top joiner holes | The shell's 8 rail-plate holes are at Z -18 to -88 and its 2 top-joiner holes at Z +82, the mirror image of where the rail plate (Z +10 to +96) and joiner (Z -82) sit in the assembly. Audit 2: 10 shell holes with nothing bolted through, 10 plate holes with no shell hole behind them. Cause: `1_back_shell.py` step 6 draws the holes at sketch (x, z) on a Top-plane sketch, where sketch y is model -Z. The cradle script negates z (`zs()`), the shell script does not; the Pi holes are symmetric so they still match. The quarters carry the same error (the rail holes are in the two Top quarters). | As printed, the rail plate could only bolt to the top quarters, so the display would hang below the bar instead of standing above it, and the "top" joiner holes would lie under the rail plate. | In step 6 of `1_back_shell.py` draw `(x * mm, -z * mm)`, then rerun scripts 1, 3 and 5, and rerun audit 2 (expect 0 unmatched). | Critical |
| D4 | Cross joiner and rail plate | Centre of the back, Z +10 to +20 | Hard interference 1146 mm3 between the cross joiner (Z -20 to +20) and the rail plate (Z +10 to +96), both on the shell's back face (audit 1). | Both parts cannot be fitted. Leaving the joiner out loses the only bolt that ties the two top quarters to the bottom ones on the right of centre. | Remove the cross joiner and extend the rail plate up to Z -20 (plate 120 x 116, centre Z +38, still fits the bed), adding the four holes at X +/-12, Z +/-12. It then joins all four quarters at the centre and both bottom quarters. Rail stays where it is. | Major |
| D5 | Bracket | M4 lock screw | The lock hole axis (assembly Y -7) is 3 mm below the rail plate's outer face (Y -4), and the rail plate extends to X +/-60, beyond the bracket's +/-28. Arithmetic: an M4 thumb screw head is 10 to 16 mm across, so its head (radius 5 to 8) hits the rail plate and cannot be fitted or turned. The hole is also only 1.35 mm from the bracket's top face (audit 4), and the screw tip bears on a 30 degree flank, so it is a friction lock only. | The README's "thumb screw stops it lifting out over bumps" is not achievable as modelled. | Move the lock to the bar side: a vertical M4 heat-set insert in the channel block at bracket (X 0, Z -30), from the underside (Y 0) through the channel floor, with a 4.5 mm diameter, 2 mm deep detent in the rail's top face at the matching point. The thumb screw then has the whole underside to turn in and locks positively. Delete the side hole. | Major |
| D6 | Bracket and cap | Clamp split | Bore 24.2 mm = 22.2 bar + 2 x 1 mm liner, with both halves meeting on the split plane (Y -12). No clamping gap. | When the bolts are tightened the halves meet face to face, so bolt preload goes into the split faces, not into the bar. Grip depends only on liner thickness tolerance, so the mount can rotate on the bar. | Take 0.75 mm off each half's split face (1.5 mm gap when clamped on the bar with liner), or keep the faces and make the bore 23.4 mm. | Major |
| D7 | All M3 joints | Bolt stack inside the shell | Free space between the back plate's inside face (Y 3) and the display back (Y 5.5) is 2.5 mm (assembly). Rail plate grip is 4 + 3 = 7 mm; with a 2.4 mm nut an M3 x 8 does not reach through the nut, and an M3 x 10 tip lands at Y 6, 0.5 mm into the display. Joiners and cradle: 6 mm grip, M3 x 8 tip at Y 5, nut top at 5.4. | The README hardware list (20 M3 x 8 with nuts) cannot be fitted with the nuts inside. | Bolt from inside with ISO 7380 button heads (1.65 mm head, fits the 2.5 mm gap), nyloc nuts outside: M3 x 12 for the rail plate, M3 x 10 for joiners and cradle. All rail plate nuts are outside the bracket's footprint (X +/-40 and +/-52 against +/-28), checked from the hole list. Fit these before the display goes in. | Major |
| D8 | Rail plate and bracket | Dovetail | The flanks are not parallel: rail 31.6 degrees from the plate normal, channel 30.5 degrees (measured face normals). Horizontal gap per side: 0.29 mm at the mouth, 0.12 mm at the rail's wide edge (from the measured face extents); normal gaps between the flank planes measured at their root points 0.10 and 0.26 mm (audit 2). Floor gap 0.30 mm. Cause: the rail profile starts 0.5 mm inside the plate (slope 4 over 6.5) while the channel slope is 4 over 6.8. | 0.1 mm at the bearing edge is below what PETG prints hold (elephant's foot and layer ripple are 0.1 to 0.2 mm). The rail will bind or need sanding. | Draw the rail from the plate face: half width 15 at Y 4 to 19 at Y 10 (33.7 degrees). Draw the channel as the rail offset by 0.35 mm normal (0.42 horizontal): half width 15.42 at the mouth and 19.42 at the rail-top level, floor 0.3 below the rail top. Print a 20 mm long coupon of both before the full parts. | Moderate |
| D9 | Assembly | Whole file | (a) The rail plate file (saved 10:35) is newer than the assembly (09:30): its component state is 5 (internal ID mismatch), and on the first open of this audit it came up suppressed with no geometry. (b) No mates; positions are fixed transforms and only the shell is fixed. (c) The dummy Pi 5 is 10 mm away from the cradle's standoffs (board Z -42.5 to 42.5, standoffs at Z -49 and +9, so the board belongs at Z -52.5 to 32.5). (d) The assembly uses the master shell, not the four quarters. | Screenshots and the interference check reflect a stale state; the Pi preview overstates how close the USB end is to the bar. | After D1 to D8, rerun `5_assembly.py` with the Pi translation (0, -10, -10). Optionally build a second assembly from the quarters. | Moderate |
| D10 | Left quarters | Cable exit roof | The 58 mm cable exit straddles the Z = 0 split, so in each left quarter its roof (Y 21, 2.5 x 29 mm, 72.5 mm2 per quarter) is a cantilever overhang supported at one end only when printed back-down (audit 3 downward faces). | Will droop or fail without support. | Either add a support enforcer under it, or extend the exit to the front edge (Y 5 to 27) so it becomes an open notch with no roof, which also makes plugging in easier. | Moderate |
| D11 | Back shell | Display pocket | Pocket 273.2 x 188.2 (272 measured + 2 x 0.6). The Waveshare drawing gives 274.12, which would not fit. Depth: display placed at Y 5.5 to 25.5 against the lips for the estimated 20 mm; the official case is 18 mm, which leaves 2 mm of play. | Either a display that does not go in, or one that rattles against the lips. | Measure the long side with calipers before printing. Add 2 to 3 mm closed-cell foam on the back plate to take up depth and damp vibration. | Moderate |
| D12 | All parts | Sketches and globals | Only the shell's first three sketches are fully defined and linked to equations. The shell's vent, cable exit and bolt sketches are under defined (0 to 1 dimensions). Every sketch in the bracket, cap, rail plate, joiners and cradle is under defined with 0 dimensions (audit 3). The bracket and rail plate carry global variables (TubeD, Slide, RailW ...) that nothing references. | Changing a value in Tools > Equations does nothing for most sizes; the README's "a new measurement is one number to change" holds only when the script is edited and rerun. | State in the README that the scripts are the source of truth (edit and rerun 1 to 5). If the parts will be edited in SolidWorks, add dimensions in the scripts with `AddDimension2` as the shell's first three sketches do. | Moderate |
| D13 | Pi 5 cradle | Base over the vents | The cradle base (Z -57.5 to 37.5) covers about 35 percent of the vent slot length (39 of 112 mm per slot column), from the part boxes and vent positions. | Less airflow past the display electronics; the Pi itself has its own cooler outside. | Cut matching slots in the cradle base, or move the vents 30 mm towards +X. | Minor |
| D14 | Pi 5 cradle | Standoffs | 6 mm OD, 1.9 mm wall round the 2.2 mm pilot (audit 4), 7 mm tall, printed vertical. | Fine for a 50 g board, but a self-tapping screw over-torqued will split it. | M2.5 x 6, hand tight, or 7 mm OD standoffs with M2.5 heat-set inserts. | Minor |
| D15 | Bracket | Docstring | `2_bracket.py` says the cap has counterbored holes; it has plain 5.5 mm holes. | Documentation only. | Correct the text. | Minor |
| D16 | Quarters | Wall joints | The walls are butt joints at X = 0 and Z = 0 relying on glue; the plates only join the back plate. | The long walls flex as the display snaps in, which loads the glued wall joints in peel. | Glue the walls with the display fitted as a jig, or add a 10 x 20 x 2 mm splice tab glued inside each wall joint. | Minor |

## 3. Load path and vibration (assessment, not tested)

Path: display -> snap lips and back plate -> shell quarters -> 8 (after D4, 12) M3 into the rail plate -> dovetail
-> closed channel end (weight) and lock screw (lift) -> bracket channel block -> clamp boss -> 2 M5 and rubber
liner -> bar.

- Static moment about the bar: the display and shell centre of mass is about 50 mm out from the bar axis (Y) and
  59 mm above it (Z), about 77 mm away. With 1.5 kg that is up to 1.1 N m, and about 3.4 N m at 3 g of road
  shock. A rubber-lined split clamp with 2 M5 at a modest 1 kN each (limited by the heat-set inserts and PETG
  creep) gives a friction torque of the order of 20 N m, but only once D6 gives the clamp a gap; as modelled the
  preload does not reach the bar at all.
- Layer orientation: printed clamp-face down, the bracket's layers are parallel to the joint between the clamp boss
  and the channel block, which is the section that carries the bending moment. This is the weakest direction in
  FDM. Use 5 perimeters and 50 percent or more infill for the bracket and cap.
- Creep: PETG under constant clamp load in the sun will relax. ASA has a higher softening point (about 100 C
  against about 80 C) and better UV life; use ASA for the bracket, cap and rail plate if the printer can.
- A 1 kg plate on a single 22 mm bar cantilever has a low natural frequency; a tuk-tuk on rough road will excite
  it. The cable tie backup in the README is a sound idea for the first road test.

Physical tests needed (none done): dovetail coupon slide fit (D8); clamp slip torque: hang 1.5 kg at 150 mm from
the bar (2.2 N m) for 10 minutes, then check for rotation; insert pull-out by hand torque on an M5 in a test boss;
snap-lip retention: shake test with the display fitted; a 10 minute ride with the cable tie backup, checking bolt
torque afterwards.

## 4. Checks performed and results

| Check | How | Result |
|---|---|---|
| Probe proof for interference | audit 1: a second cross joiner added 2 mm into the back plate | DETECTED, 1563.7 mm3 with the back shell. The check reports real overlaps. Probe deleted, assembly not saved. |
| Interference, touching not counted | audit 1 on `SW7_Dash_Assembly.SLDASM`, all 11 components resolved | 1 overlap: cross joiner / rail plate 1145.5 mm3 (D4). |
| Contact graph (TreatCoincidenceAsInterference) | audit 1 | Every printed part touches something. Bracket touches the rail plate and cap; cap touches the bracket; the dummy bar touches nothing (the 1 mm liner is not modelled, expected). Only the shell is fixed; no mates exist. |
| Component state | audit 1, `GetSuppression2` | Rail plate state 5 (ID mismatch); first open showed it suppressed (D9). |
| Fastener holes, coaxial in both parts | audit 2: cylinder faces read from the saved parts, mapped by each component's transform, matched within 0.05 mm | Cradle 4/4, right joiner 2/2, cross joiner 4/4, M5 clamp 2/2 matched. Rail plate 0/8 and top joiner 0/2 matched (D3). |
| Quarters against the master | audit 3 | Every quarter hole is in the master and every master hole is in a quarter, so the quarters are current with the master (and share D3). |
| Pi standoff pattern | audit 2 | Pilots at 49.0 x 58.0 mm, matching the Pi 5 drawing. Dummy Pi 10 mm off (D9). |
| Dovetail fit | audit 2 and a face-normal query | See D8. |
| Body count and validity | audit 3, `GetBodies2` and `IBody2.Check3` | One body in every part except the clamp cap (2 bodies, D1). Check3 reports 0 faults on every body. |
| Bed fit | audit 3, part boxes | Every printed part fits 180 x 180 x 180 (largest: quarters 139.1 x 96.6 x 27, rail plate 120 x 86 x 10). The master shell (278.2) does not, as intended. |
| Thin walls | audit 4: `ClosestDistance` between every pair of non-adjacent faces, counted as a wall only when the line between them runs into the material; checked first on the bracket, where the 0.2 mm wall from the script arithmetic was found | Under 2 mm: bracket insert holes 0.20 (D2), insert to bore 1.30, lock hole to top face 1.35; cap 0.65 and 1.75; cradle standoff wall 1.90; quarters only the 1.5 mm snap lips. Plates: none. |
| Overhangs | audit 3: planar faces facing down more than 45 degrees, above the bed, for the stated print orientation | Quarters: lips (1.2 mm, prints fine) and the cable exit roof in the left quarters (D10). Bracket channel-down: the channel floor is a 38.6 mm bridge (2792 mm2). Rail plate, joiners, cradle, cap: none. Curved faces (the bar bore) were judged by inspection, not by the script. |
| Sketch definition | audit 3, `ISketch.GetConstrainedStatus` and display dimensions per sketch | D12. |

Audit scripts: `build/audit_1_assembly.py`, `build/audit_2_fasteners.py`, `build/audit_3_parts.py`,
`build/audit_4_walls.py`. None of them saves anything; each closes the documents it opens.

## 5. Checks not performed

- FEA of the bracket, clamp or rail plate: no material model for printed PETG/ASA with layer anisotropy is set up;
  the physical tests in section 3 are more useful at this stage.
- Slicing: no G-code was produced, so print times and actual support volumes are estimates.
- The SolidWorks Thickness Analysis and Draft tools were not used; audit 4 replaces the first for planar and
  cylindrical faces only (other surface types are skipped; there are none in these parts).
- Mass with assigned materials: the parts have no material set; masses above are volume x density.
- Tolerance stack of the printed quarters when glued (flatness of the back after gluing).
- The cable routing, connector clearances beyond the 58 x 16 exit, and heat in the closed shell.
- Re-running the audits after the corrections: they must be rerun after D1 to D8 are fixed.

## 6. Print plan

| Part | Qty | Material | Orientation | Supports | Notes |
|---|---|---|---|---|---|
| Shell quarters | 4 | PETG (ASA if in direct sun) | Back plate on the bed, open side up | Left quarters: under the cable exit roof (D10). Lips print without | 3 perimeters, 25 percent infill |
| Rail plate | 1 | ASA or PETG | Bolting face on the bed, rail up | None (rail flanks 31.6 degrees from vertical) | 5 perimeters, 50 percent infill; check the rail edge for elephant's foot |
| Joiner plate | 2 | PETG | Flat | None | (cross joiner dropped if D4 fix is taken) |
| Pi 5 cradle | 1 | PETG | Base on the bed, standoffs up | None | |
| Bracket | 1 | ASA or PETG | Clamp (split) face on the bed, channel up | Build-plate-only support inside the half bore (24 mm arch) | 5 perimeters, 50 percent or more infill; inserts vertical |
| Clamp cap | 1 | ASA or PETG | Outer (bottom) face on the bed, bore groove up | None | Only after D1 and D2 |

## 7. Assembly sequence (after the corrections)

1. Press the two M5 heat-set inserts into the bracket from the split face, and the M4 insert from the underside
   (D5 fix). Let them cool before loading.
2. Lay the four quarters face down on a flat surface. Glue the wall butt joints (or use the display as a jig, D16).
3. From inside the shell, push M3 button-head bolts through the back plate; on the outside fit the rail plate
   (12 bolts after D4), the joiner plate(s) and the Pi 5 cradle, with nyloc nuts. Every nut is reachable with a
   5.5 mm nut driver from outside; the cradle nuts sit between the standoffs (closest standoff 12.9 mm from a
   bolt centre), so do these before the Pi goes on.
4. Screw the Pi 5 to the cradle standoffs with four M2.5 x 6, USB end towards the notch (down).
5. Lay the foam pad on the back plate, connect the display cables through the cable exit, and press the display in
   past the lips.
6. On the vehicle: wrap the bar with 1 mm inner tube, fit the bracket above and cap below, M5 x 30 with washers
   from below with a 4 mm hex key, set the tilt, tighten evenly.
7. Slide the display's rail down into the channel until it stops, then tighten the M4 thumb screw from below into
   the rail's detent. Add the cable tie backup for the first road test.

Removal is the reverse of 7. Tool access above was worked out from the measured hole positions and part outlines
(arithmetic, not a tool model in SolidWorks). The one access problem found is the M4 lock, which needs the D5
change: as modelled, its head collides with the rail plate. The new D4 holes at Z +/-12 are clear of the bracket
(which starts at Z +19), so their nuts do not sit under it.


## 8. Revision 2: corrections applied and re-checked (12 Oct 2026)

These corrections were made in the build scripts and the parts were rebuilt in SolidWorks. Every audit was then run again
on the saved files.

| ID | What was changed | Evidence after the rebuild |
|---|---|---|
| D1 | Cap thickness 17 mm (`CapT`) | Cap box Y -29.0 to -12.75, so 4.9 mm of material is left under the 24.2 mm bore. Audit 3: 1 body, 0 Check3 faults |
| D2 | `ClampZ` 26, `BoltZ` 18.5. The insert holes are now blind 10 mm from the split face, not cut through to the channel | Audit 4: bracket 0 walls under 2 mm, cap 0 walls under 2 mm. Insert cut removed 724 mm3 = 2 x pi x 3.2^2 x 11.25 |
| D3 | `1_back_shell.py` step 6 draws holes at (x, -z) | Audit 2: all 8 rail-plate holes, both joiner plates, the cross joiner and the cradle match the shell. Audit 3: quarters against the master, none missing |
| D4 | Rail plate moved to Z 22 to 96 (74 mm tall, centre Z 59, symmetric). The cross joiner stays at Z -20 to 20, which keeps a bolt into every quarter | Audit 1: 0 hard interferences (was 1146 mm3). Probe still detected (1563.7 mm3) |
| D5 | Side lock replaced: a vertical M4 heat-set insert under the channel at bracket Z -30, a 4.5 mm clearance hole into the channel, and two 4.5 x 2 mm detents in the rail face at plate centre +/-28. The rail is 72 mm (was 80), so each detent has 5.75 mm of wall to the rail end | Lock insert cut 69.8 mm3 (expected 69.8); detents 63.6 mm3 (expected 63.6). Lock axis at assembly Z 31 = plate centre 59 - 28 |
| D6 | 0.75 mm taken off each split face: a 1.5 mm squeeze gap | Bracket boss bottom Y -11.25, cap top Y -12.75. Audit 1 now shows the cap not touching the bracket, as intended: it is held by the 2 M5 bolts (holes coaxial, audit 2) and grips the bar through the liner |
| D7 | Hardware changed: ISO 7380 M3 button heads from inside with nyloc nuts outside. M3 x 12 for the rail plate, M3 x 10 for the joiners and cradle | README updated |
| D8 | Rail drawn from the plate face (no slope change at the 0.5 mm embed). Channel = rail offset 0.35 mm normal to the flanks, floor 0.35 below | Audit 2: normal gap 0.350 mm on both flanks; flank normals parallel (was 0.10 and 0.26) |
| D9 | Pi reference placed at (0, -10, -10) on the standoffs. Every component fixed (`FixComponent()` needs the call parentheses under late binding, which is why the first attempt fixed nothing) | Audit 1: 11 of 11 fixed, 0 interferences, the Pi reference touches the cradle |
| D10 | The cable exit is an open notch to the front edge | No roof left to print over the plugs |
| D13 | Vent slots cut through the cradle base, keeping 3 mm from the standoffs, edges and the USB-end notch | Audit 4: the cradle's only walls under 2 mm are the standoff walls of 1.9 mm (D14, minor). My first slot layout left 1.0 mm walls; audit 4 caught that, and the slots were moved |
| D15 | Docstring corrected | |
| D11, D12, D16, D14 | Not geometry. Foam pad, scripts as the source of truth, splice tabs, hand-tight M2.5 x 6 | Documented, not changed |

The bracket now sits at Z 21 to 101, so it reaches 4.4 mm below the shell's bottom edge. That is behind the display
and clear of the bar. The bar is at Z 61.

Acceptance after revision 2: PROTOTYPE-READY for a first print of the bracket, cap and rail plate, together with the
dovetail coupon. Before the full shell is printed, still needed:
- the long side of the display measured;
- the clamp slip test;
- the shake test.

Not done: slicing, FEA and any physical test.
