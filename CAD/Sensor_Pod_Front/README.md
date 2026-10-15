# Front sensor pod: camera, ToF board and a Raspberry Pi 5 with the AI HAT+

Status (16 Oct 2026): complete model, audited, sliced, not printed. It is a variant of `CAD/Sensor_Pod` for the new
layout (15 Oct): the Pi 5 sits at the front with its own camera and ToF board, and the Pi 4 and the ESP32 stay in the
original pod at the rear. Built in SolidWorks 2025 by the scripts in `build/`. Every size is in `build/params.py`. It
imports the original pod's params and overrides only the box, and marks each value official, estimated (MEASURE) or
design, with its source. The engineering review with all audit results is `ENGINEERING_REVIEW.md`.

## What it is

- **Sensor head.** The same three parts as the original pod: upper shell, tray and camera retainer. Audit 6 compared
  the saved files and found them identical to the original parts (volume, area, centre of mass, box, face count). The
  sliced bed 08 and bed 09 G-code from 13 Oct can be printed again unchanged.
- **Electronics box** for the Raspberry Pi 5 stack only. The stack, bottom to top:
  - the Pi 5;
  - the official Active Cooler;
  - the 16 mm kit spacers and stacking header;
  - the AI HAT+, with the Hailo and a heatsink allowance.

  Removed compared with the original: the ESP32 bay, divider, LiPo space, GNSS window, LTE SMA hole, gland, 5 V
  buck anchors and middle lid screws. The box is 112.5 mm long (was 142.5) and 18 mm taller (top at Z 28) for the HAT.
- **Mount.** The rail plate is the original pod's plate, unchanged: the same dovetail and the same bolt pattern
  (X ±22, Y -91 and -49). Audit 2 checked the original plate file's holes against this box's inserts. It slides into
  the shared bar clamp (`CAD/Dashboard_Enclosure` bracket and cap). This pod needs its own clamp: print bed 07 once
  more (three in total: dashboard, rear pod, front pod).

## Layout in the box

- The Pi's 40-pin header faces the head. The ToF board's seven Dupont jumpers come through the cable window and plug
  onto the stacking header's pins above the HAT: pins 1, 3, 5, 6, 15, 16 and 18. They make an R5 hairpin over the HAT
  edge.
- The micro-HDMI and USB-C edge faces the rear wall. The USB-A and Ethernet end faces the +X wall.
- The camera ribbon runs from the window over the HAT at Z 12. It makes one 45 degree crease fold, then an R5 bend
  down through the HAT's slot into the CAM/DISP connector nearer the micro-HDMI ports. Use the 200 mm Raspberry Pi 5
  camera cable (22 to 15 way). The path is about 164 mm.
- **Cable ports.** Each cable leaves through a U-notch in a flat cover over a wall opening:
  - rear wall: USB-C power and micro-HDMI 0 to the display. Use a one-piece micro-HDMI to HDMI cable, or a short
    micro-HDMI to HDMI pigtail;
  - +X wall: Ethernet to the rear Pi 4, and USB-A for the display's touch (the lower port of the stack nearer the
    Ethernet jack).

  Each cable is tied down to a tie block inside, and there is a drip ledge over the rear cover.
- **Air.**
  - The Active Cooler blows towards -X between the Pi and the HAT, out through the lower slots in the -X wall.
  - Upper slot rows in both side walls let air cross over the HAT and the Hailo.
  - The intake is through floor slots behind 3 mm upstands at the +X end.
  - Every side opening is under a 45 degree drip ledge.
- A 22 mm gap between the front wall and the Pi leaves room for a 2.5 mm hex key on the lower flange bolts, with the
  Pi and the HAT in place. Audit 5 checked this with a key stand-in.

## Printed parts

| Part | Size (mm) | Notes |
|---|---|---|
| SW7_FPod_Head_Upper | 104.8 x 67.9 x 63.1 | Identical to SW7_Pod_Head_Upper (bed 08) |
| SW7_FPod_Head_Tray | 96.8 x 60.1 x 26.8 | Identical to SW7_Pod_Head_Tray (bed 09) |
| SW7_FPod_Camera_Retainer | 37.8 x 16.2 x 2.0 | Identical to SW7_Pod_Camera_Retainer (bed 09) |
| SW7_FPod_Box_Base | 152.8 x 116.5 x 56.4 | New |
| SW7_FPod_Box_Lid | 148.6 x 116.3 x 5.4 | New (no GNSS window) |
| SW7_FPod_Rear_Port_Cover | 52.0 x 30.5 x 3.0 | New |
| SW7_FPod_Side_Port_Cover | 53.0 x 33.3 x 3.0 | New |
| SW7_FPod_Sunshade | 100.0 x 82.0 x 7.0 | New: 82 long (original 64), over the whole Pi bay |
| SW7_FPod_Rail_Plate | 60.0 x 84.0 x 12.0 | Identical to SW7_Pod_Rail_Plate (bed 12) |

The G-code, 3MF projects, STLs and the print list are in
`C:\Users\0geda\Desktop\Fourth Year\EEE4022S\3D Prints\front_pod\` (made by `CAD/Print/slice_front_pod.py`).

## Hardware

- M3 heat-set inserts and M3 x 8 screws:
  - 4 for the flange (with washers);
  - 2 for the head seam;
  - 4 for the lid;
  - 4 for each port cover;
  - 4 for the rail plate.
- Self-tapping screws: 4 x M3 x 8 into the sunshade posts, 4 x M2 x 6 for the camera retainer, 4 x M2 x 8 for the
  sensor board.
- 4 x M2.5 x 18 pan head (DIN 7985) from under the floor, through the standoffs and the Pi into the AI HAT+ kit's
  spacers. The kit's own top screws hold the HAT. Two of the four sit under the rail plate, so fit the Pi before the
  plate.
- Others:
  - closed-cell foam strip round each cable in its notch, and along the lid's front edge against the head;
  - cable ties (2.5 mm);
  - the 200 mm Pi 5 camera cable.

## Assembly

1. Fit all the heat-set inserts.
2. Build the head as for the original pod: board in the tray, camera in the cradle with the retainer, close the seam.
3. Bolt the head to the empty box with the 4 flange screws, from inside, with a 2.5 mm hex key.
4. Fit the Active Cooler to the Pi 5. Screw the Pi down with the four M2.5 x 18 from under the floor into the kit
   spacers. Connect the PCIe flat cable, fit the stacking header, then fit the HAT with the kit's top screws.
5. Connect the camera ribbon. Lay it over the HAT, fold it once at 45 degrees and feed it down through the HAT slot
   into the connector. Push the jumpers onto the stacking pins.
6. Lay each cable in its notch with foam, tie it to its block, and fit the port covers.
7. Fit the sunshade to the lid (M3 x 8 self-tapping from under the lid), then fit the lid.
8. Bolt on the rail plate and slide the pod onto the clamp.

To take the head off later: remove the lid, unplug the ribbon and the jumpers, and undo the 4 flange screws with the
hex key. The Pi and the HAT stay in place.

## Measure before printing

The values marked MEASURE in `build/params.py`. The ones that set the box:

1. The AI HAT+ kit spacer height (16 mm from the product brief) and how far the stacking pins stand above the HAT
   (6 mm assumed).
2. The Hailo heatsink height, if one is fitted (10 mm allowed including the package).
3. The Dupont housing length (14 mm assumed).
4. The real plug lengths: USB-C and micro-HDMI 23 mm, Ethernet 30 mm, USB-A 35 mm. Also the cable diameters, which
   set the notch widths: 5, 7, 7 and 5 mm.
5. Which CAM/DISP connector is 0 and which is 1 on the board, and the ribbon width at the 22-pin end (11.5 mm assumed).
6. The Active Cooler's height over the SoC (15 mm assumed above the PCB).
7. The board items carried over from the original pod: the sensor board's holes and the side ToF angle.

## Rebuilding

With SolidWorks open and no documents open, run these in `build/`:
1. `1_sensor_head.py`, then `2_sensor_tray.py`.
2. `3_electronics_box.py`.
3. `4_mount_and_refs.py`.
4. `5_assembly.py`. The assembly, interference check and renders take about 40 min.

Then run `audit_1` to `audit_6` and `export_stl.py`, then `CAD/Print/slice_front_pod.py`. Close all SolidWorks
documents between steps: a part left open makes the next save fail with error 1.
