# Front sensor pod (Pi 5 + AI HAT+): engineering review

Review date: 16 Oct 2026. Revision reviewed: the saved parts in `print_parts/` and
`SW7_Front_Sensor_Pod_Assembly.SLDASM` after the fixes in section C. Reviewer: Claude, through the SolidWorks 2025
API with the audit scripts in `build/`. Their outputs are kept in `audit_logs/`. Nothing has been printed or
physically tested. Every number below was measured on the saved model by those scripts unless it says it was
worked out from parameters.

## A. Design overview

The front pod is a variant of `CAD/Sensor_Pod` for the layout of 15 Oct. The Raspberry Pi 5 sits at the front with
its own camera (OV5647 in the yellow case) and its own ToF board (JCP board, three VL53L0X). The Pi 4 and the ESP32
stay in the original pod at the rear. The student's Pi 5 carries the official Active Cooler and the AI HAT+ (Hailo).

| Group | Parts | Change against the original pod |
|---|---|---|
| Sensor head | SW7_FPod_Head_Upper, SW7_FPod_Head_Tray, SW7_FPod_Camera_Retainer | None. Identical to the original saved parts (audit 6) |
| Electronics box | SW7_FPod_Box_Base, SW7_FPod_Box_Lid, SW7_FPod_Rear_Port_Cover, SW7_FPod_Side_Port_Cover, SW7_FPod_Sunshade | New. See below |
| Mount | SW7_FPod_Rail_Plate and the dashboard's bar clamp | Rail plate identical to the original (audit 6). A third clamp is needed |

What changed in the box:
- **Removed:** the ESP32 bay and standoffs, the divider and its notches, the LiPo space, the GNSS thin window, the
  LTE SMA hole, the gland, the 5 V buck anchors, the -X USB hatch and the middle lid screws.
- **Size:**
  - Shell: 144.8 x 112.5 mm in plan (was 144.8 x 142.5), walls from Z -28.4 to 28.0 (was to 10.0). With the drip
    ledges, the base part measures 152.8 x 116.5 x 56.4 (was 148.8 x 142.5 x 38.4).
  - Lid: 148.6 x 116.3 x 5.4.
  - The box is 30 mm shorter. It is 18 mm taller for the AI HAT+ stack.
- **Pi 5 stack**, bottom to top:
  - Pi 5 on four 10 mm standoffs;
  - Active Cooler;
  - 16 mm kit spacers and stacking header;
  - AI HAT+, with the Hailo and an estimated 8 mm heatsink.

  The Pi is fixed by M2.5 x 18 pan heads from under the floor (counterbored) into the kit spacers. Its 40-pin
  header faces the head, the micro-HDMI / USB-C edge faces the rear and the USB / Ethernet end faces +X.
- **Cable ports.** Each port is a wall opening with a flat cover. The cables sit in U-notches open at the cover's
  bottom edge, are tied to a block inside, and have foam in the notch:
  - rear: USB-C power and micro-HDMI 0;
  - +X: Ethernet and USB-A (touch).

  45 degree gussets under the upper cover bosses, and a drip ledge over the rear cover.
- **Air.**
  - Cooler exhaust (towards -X, under the HAT): slots low in the -X wall.
  - Cross-flow over the HAT and the Hailo: upper slot rows in both side walls.
  - Intake: floor slots with 3 mm upstands at +X, plus a small floor exhaust and drain at -X.
  - All side slots sit under drip ledges with 45 degree undersides.
- **Kept:**
  - the faceted rear corners and rear bottom facet;
  - the lid with its drip skirt and front skirts;
  - M3 heat-set lid screws;
  - the head flange bolting and the cable window;
  - a cable tie anchor;
  - the vent upstands;
  - the sunshade on posts.

Sources for the Pi 5 stack are listed in `build/params.py`: the Pi 5 mechanical drawing, the Active Cooler product
brief and the AI HAT+ product brief. Positions read off those drawings, rather than dimensioned on them, are marked
as scaled. Estimates are marked MEASURE.

## B. Checks performed (final revision)

| Check | How | Result |
|---|---|---|
| Interference check is trustworthy | audit 1: a copy of the box base shifted 5 mm is added as a probe | See section B1 |
| Hard interference, whole assembly | `5_assembly.py` and audit 1, InterferenceDetectionManager, touching not counted. 17 components: 9 printed parts, Pi 5 stack, cables, sensor board, camera case, view cones, bracket, cap, bar | See section B1 |
| Fastener coaxiality | audit 2: cylindrical faces read from the saved parts, a hole of the right size in both parts within 0.05 mm | See section B2 |
| Head and rail plate unchanged | audit 6: volume, area, centre of mass, box and face count against `CAD/Sensor_Pod/print_parts` | See section B3 |
| Body validity and bed fit | audit 3: body count, IBody2.Check3, bounding box | See section B4 |
| Minimum wall and insert wall | audit 4: ClosestDistance between every pair of faces whose line runs through material, and the thinnest wall round every M3 insert hole (r 2.0) | See section B5 |
| Clearances to the Pi 5 stack and cables | audit 5: ClosestDistance per stand-in feature, gaps in the stack, hex key access with interference, bend radii | See section B6 |
| Overhangs and print | Slicer: every part scored in six orientations, the best two sliced, beds sliced (PrusaSlicer 2.9.4, the student's MINI profile) | See section E |

(Sections B1 to B6 are filled from the final audit logs.)

## C. Defect register (found by the audits on this design, all fixed and re-audited)

| # | Part | Problem (measured) | Correction | Status |
|---|---|---|---|---|
| 1 | Box base | Rear boss at X -56 exactly tangent to the rear lid boss: the feature failed to build | Boss at X -57, merged into the lid boss | Fixed |
| 2 | Box base | Lower rear-port insert holes 0.10 mm from the rear bottom facet (audit 4) | Lower rear bosses raised to Z -19.5, with a root block to the floor. Insert wall now 2.00 mm | Fixed |
| 3 | Box base | Pi screw counterbores left a 0.32 mm skin round a 6 mm standoff (audit 4) | 8.5 mm bases round the standoffs. Counterbore wall now 1.51 mm | Fixed |
| 4 | Box base | Side tie blocks overran the opening by 0.3 and 0.6 mm, leaving slivers (audit 4) | Blocks clipped to the opening | Fixed |
| 5 | Box base | Rail insert cap 1.40 mm after shortening the bosses to clear the Pi; the boss under the Ethernet jack had 3 mm to the PCB (audit 4, then parameters) | Pi standoffs 10 mm (box top Z 28), bosses back to 6 mm: cap 2.00 mm in audit 4 | Fixed |
| 6 | Box base | Drip ledge tips 1.0 mm (audit 4) | 1.5 mm tips | Fixed |
| 7 | Box base | Upper horizontal port bosses printed in the air without supports (slicer comparison) | 45 degree gussets under them; the base now prints with no supports | Fixed |
| 8 | Box base | The new side gusset at Y -52 was 0.28 mm from the USB-A plug stand-in (audit 5) | Side bosses at Y -50 | Fixed |
| 9 | Head upper (front copy) | The original script adds a rear drip lip that the original saved part and bed 08 do not have (+841.6 mm3, audit 6) | Left out of the front copy so the head is the printed one; noted in `CAD/Sensor_Pod/ENGINEERING_REVIEW.md` | Fixed (copy) |
| 10 | Rear plug stand-ins | 13.6 and 12.8 mm3 overlap with the ports (the ports stand 0.5 mm past the board edge) | Stand-ins start at the port face | Fixed |
| 11 | Audit 1 script (from the original) | The probe copy was never deleted (`asm.EditDelete` without the call under late binding), so it showed in the contact list | `call0(asm, "EditDelete")` | Fixed |

## C2. Findings carried over from the original head (not changed, so that the printed head can be reused)

Audit 4 also ran on the head parts. They are identical to the original pod's, and these findings apply to both pods:

| Part | Finding | Severity | Suggestion if the head is ever revised |
|---|---|---|---|
| Head upper | The two seam insert holes are blind 6.1 mm into a 6.2 mm block: 0.20 mm of skin at their far end (the side walls are 2 mm) | Minor: the insert grips on its sides; the skin may break through when the insert is pressed | Seam blocks 1 mm deeper, or a 5 mm insert hole |
| Head upper | Pairs of faces 0.01 mm apart at the seam (the +0.01 mm overlaps in the script) | Cosmetic: below slicer resolution | Remove the 0.01 offsets |
| Head upper | Flange insert holes 1.90 mm from the boss end | Minor | None needed |
| Head tray | 0.5 mm gap between the bundle tie anchor and the rear wall | Cosmetic | None needed |
| Camera retainer | M2 clearance holes 0.8 mm from the plate edge | Minor (already printed) | 1 mm wider plate |

## D. Mechanical notes

- **Load path:** box floor, then 4 M3 inserts into the rail plate (bosses back to the original 6 mm, insert cap
  2.0 mm), then the dovetail into a third dashboard bracket, then 2 M5 into the bar. The box is lighter than the
  original's (no ESP32, no LiPo, 30 mm shorter). The Pi 5 with the cooler and HAT is heavier than the Pi 4 with its
  fan. No load case is defined and no safety factor is claimed.
- **Fits** (design values; they are not measured on prints):
  - M3 inserts in 4.0 mm holes;
  - M3 clearance 3.4 mm;
  - M2.5 clearance 2.7 mm, with a 5.5 x 2.2 mm counterbore;
  - lid 0.3 mm;
  - cable notches 0.3 mm round the cable stand-ins.
- **Heat** (not measured; the brief's operating range is 0 to 50 C ambient):
  - The Active Cooler draws from the sides of the 1.0 mm gap under the HAT. That gap is set by the official kit.
  - It blows out through the -X wall's lower slots.
  - The Hailo has 14.8 mm of air above it and cross-flow through the upper slots.
  - A sun-soak test with the lid and sunshade on is needed.
- **Assembly order:** the head bolts on to the empty box. The Pi stack goes in later, from below with the four
  M2.5 x 18, before the rail plate. Two of the screws are under the plate. To take the head off later, unplug the
  ribbon and the jumpers and undo the flange bolts with a 2.5 mm hex key; the Pi and the HAT stay in (audit 5,
  section B6). This removes the original pod's defect 3 (Pi out to reach the lower flange bolts) for this variant.

## E. Print plan and slicing

See `C:\Users\0geda\Desktop\Fourth Year\EEE4022S\3D Prints\front_pod\README.md`.

## F. Estimated and unverified

| Item | Value used | Source | Measure |
|---|---|---|---|
| AI HAT+ spacer height | 16 mm | AI HAT+ brief ("16mm stacking header, spacers") | The kit spacers |
| Stacking pins above the HAT | 6 mm | Estimate | The pins |
| Hailo heatsink | 10 mm with the package | Estimate | The heatsink if fitted (2 mm without) |
| Active Cooler top above the PCB | 15 mm | Brief 13.70 plus 1.3 estimated | On the board |
| CAM/DISP connector positions | bx 47.0 to 49.8 and 53.2 to 56.0, by 0.7 to 16.2 | Scaled from the Pi 5 drawing | On the board; which one is CAM/DISP 0 |
| Hailo position | bx 22.6 to 39.6, by 18.3 to 35.5 | Scaled from the AI HAT+ drawing | |
| Ethernet / USB heights, port centre heights | 13.5 and 16 mm | Estimate | |
| Plug lengths | USB-C 23, micro-HDMI 23, Ethernet 30, USB-A 35 mm | Estimate | The actual cables |
| Cable diameters (notch widths) | 5, 7, 7, 5 mm | Estimate | The actual cables |
| Ribbon width at the 22-pin end | 11.5 mm | Estimate | The cable |
| Dupont housing length | 14 mm | Estimate | |
| Pi 5 underside parts | 1.5 mm | Estimate | |
| PCIe flat cable loop | 6 mm past the board end | Estimate | |
| Carried over from the original | sensor board holes, side ToF angle, ToF chip height, tube diameter | Original review | As in `CAD/Sensor_Pod/README.md` |

The ribbon's 45 degree crease fold is the standard way to turn an FFC; it is not a bend and has no radius to check.
A twisted ribbon was considered and rejected: a 90 degree twist of an 11.5 mm ribbon over the 14 mm drop would
strain the edge conductors by about 19 percent (arithmetic).

## G. Files

| Location | Contents |
|---|---|
| `SW7_Front_Sensor_Pod_Assembly.SLDASM` | The assembly |
| `SW7_Front_Sensor_Pod_Exploded.SLDASM` | Exploded copy for the pictures |
| `print_parts/` | The 9 printed parts |
| `reference_parts/` | Pi 5 stack, cables, sensor board, camera case, view cones (not printed) |
| `reference_tools/` | Hex key stand-ins for audit 5 |
| `build/` | Build and audit scripts, `params.py` |
| `audit_logs/` | The output of every build and audit run quoted here |
| `renders/` | The pictures |

## H. Acceptance

(Filled from the final audit logs.)
