# Sensor pod: engineering review

Review date: 12 Oct 2026. Revision reviewed: the first complete model (parts in `print_parts/`, assembly
`SW7_Sensor_Pod_Assembly.SLDASM`). Reviewer: Claude, working through the SolidWorks 2025 API with the audit scripts in
`build/`. Nothing here has been printed or physically tested.

## A. Design overview

The pod mounts at the front of the tuk-tuk. It has two pieces, bolted together:

- **Sensor head.** It holds the camera in its printed case, centred above the ToF sensor board. The three ToF sensors
  look out through flared windows.
  - Upper shell (`SW7_Pod_Head_Upper`).
  - Tray (`SW7_Pod_Head_Tray`).
  - Camera retainer (`SW7_Pod_Camera_Retainer`).
- **Electronics box.** It holds the Raspberry Pi 4 with its fan and the Makerfabs ESP32-S3 A7670. The ESP32 sits under
  a thinned roof for GNSS.
  - Base (`SW7_Pod_Box_Base`).
  - Lid (`SW7_Pod_Box_Lid`).
  - Sunshade (`SW7_Pod_Sunshade`).
  - USB hatch cover (`SW7_Pod_USB_Hatch_Cover`).
- **Mount.** The rail plate (`SW7_Pod_Rail_Plate`) carries the dashboard's dovetail and slides into the dashboard's bar
  clamp (`CAD/Dashboard_Enclosure/SW7_Dash_Bracket` and `SW7_Dash_Clamp_Cap`).

The reference parts in `reference_parts/` are not printed: the sensor board, camera case, Pi 4 with fan, ESP32 with
LiPo and GNSS patch, a 22.2 mm bar and the view cones. The cones are the shapes in the student's screenshot of
12 Oct. They show where each sensor looks (ToF 25 degrees, camera 53.5 degrees horizontal), so that clearance can be
checked. They are not parts.

Key assumptions: the sizes marked estimated in `build/params.py`. The most important are:
- the sensor board's front edge and its mounting holes;
- the side ToF direction (90 degrees as built against 35 degrees in `fusion_config.json`);
- the ToF chip height;
- the ribbon length;
- the LiPo and GNSS patch sizes;
- the 5 V converter;
- the tube diameter.

## B. Checks actually performed

| Check | How | Result |
|---|---|---|
| The interference check itself | `build/audit_1_assembly.py`: a copy of the box base shifted 5 mm was added as a probe | Overlap detected (79 057 mm3), so the check works |
| Hard interference, whole assembly | SolidWorks InterferenceDetectionManager, touching faces not counted | 0 overlaps between any components, including the view cones against the walls, hoods and brow |
| Contact graph | Same, with touching faces counted | Every printed part touches the parts it fastens to. The reference bar touches nothing, because the 1 mm rubber liner gap is not modelled; this is intended |
| Fastener alignment | `build/audit_2_fasteners.py` reads the cylindrical faces of the saved parts and checks that each screw position has a hole of the right size in both parts, coaxial within 0.05 mm | All 30 joints match: flange 4, head seam 2, lid 6, hatch 4, rail plate 4, camera retainer 4, sunshade posts 4. All 12 board pilots are present (sensor board 4, Pi 4, ESP32 4) |
| Print bed | Bounding box of every printed part | All within 180 mm; the largest is the box base at 148.8 x 142.5 x 38.4 |
| Rebuild and save | Every build script saves with error code 0 | Pass |

## C. Defect register

| # | Component | Location | Problem | Why it matters | Correction | Severity | Status |
|---|---|---|---|---|---|---|---|
| 1 | Sensor head tray | Board pilots at (X ±11.3, Y 11.8 and 34.9) | The board's mounting-hole positions are estimated from a photo | If they are wrong, the board cannot be screwed down | Measure the holes with calipers, set `BOARD_HOLES`, rebuild | Critical (unverified) | Open, needs the student's measurement |
| 2 | Sensor head, both shells | Side ToF windows | The side sensors face 90 degrees in the model and the photos, but the fusion software assumes 35 degrees | Hazard positions would be wrong on the dashboard | Do the finger test. Either aim the carriers at 35 degrees (set `TOF_SIDE_BEARING = 35` and rebuild) or change `fusion_config.json` to 90 | Major | Open, needs the student's decision |
| 3 | README assembly order | Flange bolts at Z -20 | The two lower flange bolts sit under the Pi 4's PCB (Pi spans X -40 to 45, Z -18 to -0.4). A driver along Y cannot reach them once the Pi is in. The README fits the Pi first | The pod cannot be assembled in the documented order, and removing the head means removing the Pi | Order: head, then flange bolts, then Pi, ESP32 and wiring. Note that servicing the head means removing the Pi (4 screws). The bolts cannot move clear of the Pi, because the head's rear wall spans only X ±48.4 | Major | Fixed in this revision (README) |
| 4 | Assembly | All components except the box base | 15 of 16 components are floating, with no mates and not fixed | They can be dragged out of position, and a reader cannot trust the assembly | Every part is modelled in the pod frame, so fix each pod part in place. The dashboard bracket, cap and bar stay positioned by their transforms and are fixed too | Moderate | Planned (needs SolidWorks, after the dashboard audit) |
| 5 | Assembly | View cones | The cones show by default and look like parts | Confusing; the student asked about them | Hide the reference bodies in the default display state; show them only when checking clearance | Moderate | Planned (needs SolidWorks, after the dashboard audit) |
| 6 | All parts | Sketches | The sketches are drawn by script with no dimensions or relations. The parameters live in `build/params.py`, not in SolidWorks equations | Editing a dimension in SolidWorks does not drive the model. Changes must go through `params.py` and a rebuild | Documented as the editing workflow. Fully dimensioned sketches would mean rebuilding every feature, so this is deferred until the measurements are final | Moderate | Open (documented) |
| 7 | Box base | Flange clearance holes are only 2.4 mm long (the wall) | An M3 screw clamps the head onto a 2.4 mm wall | PETG creep under vibration could loosen the joint | Use M3 x 8 with a washer; check the torque after the first ride. A boss under the screw head would add stiffness if it loosens | Minor | Open (hardware note added) |
| 8 | Whole pod | Mount | The pod hangs on one dovetail and an M4 thumb screw | Vibration loads on a tuk-tuk are unknown | Physical test: shake on the vehicle; check the thumb screw torque and rail wear. Add a safety tie as on the dashboard | Major (unverified) | Open, needs a physical test |
| 9 | Head upper | Brow and hoods | Overhangs over the camera and ToF windows | They need support, or the head must print on its back | Print on its back, with support under the brow only. Check in the slicer | Minor | Open, needs a slicer check |

## D0. How each component is supported, connected, made and assembled

Every joint in this table was confirmed in the saved geometry by `build/audit_2_fasteners.py` (coaxial holes of the
right size in both parts) and by the contact check in `build/audit_1_assembly.py`. "Estimated" marks a dimension that
still needs measuring.

| Component | Supported by | Connected to neighbours by | Made by | Assembled |
|---|---|---|---|---|
| Sensor board (bought) | 4 pillars in the head tray (estimated positions) | 4 M2 x 8 self-tapping into 1.6 mm pilots, 8 mm deep | Bought | Step 2 |
| Camera in its yellow case (printed earlier) | A cradle in the head upper, with 0.3 mm clearance and a foam ring at the front | The retainer plate over it, with 4 M2 x 6 into 1.6 mm pilots | Existing part | Step 3 |
| Camera retainer | The cradle rails in the head upper | 4 M2 x 6 | FDM, flat | Step 3 |
| Head tray | The box front wall, through the flange | 2 M3 x 8 flange screws into inserts in the tray's rear bosses; 2 M3 x 8 seam screws through its side walls into the upper shell | FDM, floor down | Steps 4 and 5 |
| Head upper shell | The tray (its skirt sits inside the tray walls) and the box front wall | 2 M3 x 8 flange screws into its rear bosses; 2 seam screws | FDM, on its back, support under the brow | Steps 4 and 5 |
| Box base | The rail plate, so the whole pod hangs from the clamp | 4 M3 x 8 through the rail plate into inserts in floor bosses | FDM, floor down | Steps 5 and 8 |
| Raspberry Pi 4 (bought) | 4 standoffs, 8 mm, in the box floor | 4 M2.5 x 8 into 2.2 mm pilots | Bought | Step 6, after the flange bolts |
| ESP32-S3 A7670 (bought) | 4 standoffs, 12 mm (LiPo underneath) | 4 M2 x 8 into 1.6 mm pilots | Bought | Step 6 |
| 5 V converter (not chosen) | Box floor, rear bay | 2 cable-tie anchors | Bought | Step 6, size estimated |
| Box lid | The box walls (tongue inside, drip skirt outside) | 6 M3 x 8 into inserts in corner bosses | FDM, outer face down | Step 7 |
| Sunshade | 4 posts on its underside, standing on the lid | 4 M3 x 8 self-tapping up through the lid into the posts | FDM, flat | Step 7, before the lid goes on |
| USB hatch cover | The -X box wall | 4 M3 x 8 into inserts in the wall bosses | FDM, flat | Step 7 |
| Rail plate | The box floor | 4 M3 x 8, counterbored | FDM, plate down | Step 8 |
| Bar clamp (dashboard bracket and cap) | The tube, over a 1 mm rubber liner | Dovetail: 0.3 mm sliding fit, closed end forward, M4 thumb screw. Clamp halves: 2 M5 x 30 into inserts | FDM, from `CAD/Dashboard_Enclosure` | Step 8 |

## D. Mechanical notes

- **Load path.** Pod weight (about 0.5 to 0.7 kg estimated: printed parts about 315 cm3 of PETG at 1.27 g/cm3 is about
  0.4 kg, plus the boards and LiPo) goes:
  1. into the box floor;
  2. through 4 M3 inserts into the rail plate;
  3. through the dovetail into the bracket;
  4. through 2 M5 bolts and the rubber liner into the bar.

  The head hangs off the box on 4 M3 flange bolts, about 60 mm ahead of the box. No load case is defined, so no
  safety factor is claimed. A road test with the pod strapped by a safety tie is the validation route.
- **Fits** (design values; a test print should confirm them):
  - Dovetail: 0.3 mm a side, sliding.
  - Camera case in its cradle: 0.3 mm.
  - Lid tongue: 0.3 mm.
  - Board-to-wall gap: 3 mm until the board is measured.
  - M3 inserts: 4.0 mm holes for standard 4.0 to 4.2 mm inserts.
  - M3 clearance: 3.4 mm.
  - Self-tapping pilots: M2 1.6 mm, M2.5 2.2 mm.
- **Screw lengths:**
  - M3 x 8 for the flange, seam, lid, hatch and rail plate (2.4 to 3 mm part plus a 6 mm insert).
  - M3 x 8 self-tapping for the sunshade posts.
  - M2 x 6 for the camera retainer.
  - M2 x 8 for the sensor board and ESP32.
  - M2.5 x 8 for the Pi.
- **Heat.** The Pi 4 fan draws air through the drip-hooded side vents, and the sunshade keeps direct sun off the lid
  over the Pi. Running temperature in the sun is untested.

## E. Print plan

| Part | Material | Orientation | Supports |
|---|---|---|---|
| Head upper | PETG or ASA | On its back (rear face down) | Under the brow only |
| Head tray | PETG or ASA | Floor down | None expected |
| Camera retainer, sunshade, hatch cover | PETG | Flat | None |
| Box base | PETG or ASA | Floor down | None expected (vent hoods are 45 degrees) |
| Box lid | PETG, not carbon-filled (GNSS) | Outer face down | None |
| Rail plate | PETG | Plate down, rail up | None |

Print a calibration coupon first: an M3 insert hole, an M3 clearance hole, an M2 pilot and a 20 mm piece of dovetail
with the bracket profile.

## F. Checks not performed

- Slicer preview and STL watertightness. These are not run yet.
- Drawings (PDF) and STEP export. These are not produced yet.
- Any load calculation or FEA. There is no load case.
- Physical fit with the real boards: blocked on the measurements in the README.

## G. Files

All are in this folder of the repo:
`C:\Users\0geda\OneDrive - University of Cape Town\Documents\PlatformIO\Projects\Tukzie-HPEC-HUD\CAD\Sensor_Pod`.

| Location | Contents |
|---|---|
| `SW7_Sensor_Pod_Assembly.SLDASM` | The assembly |
| `print_parts/` | The 8 printed parts (.SLDPRT) |
| `reference_parts/` | Reference bodies (.SLDPRT) |
| `build/` | Build and audit scripts, and `params.py` |
| `previews/` | Pictures |

## H. Acceptance

REQUIRES REVISION. The model passes interference and fastener checks. Defect 3 is fixed in this revision; 4 and 5 are planned.
It cannot be PROTOTYPE-READY until:
- the board hole positions are measured (defect 1);
- the side ToF direction is decided (defect 2);
- a slicer check is done.
