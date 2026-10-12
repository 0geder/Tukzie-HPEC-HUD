# 3D prints for 13 Oct 2026: Prusa MINI, PLA

All three SW-7 designs are sliced and ready: the dashboard mount, the front sensor pod and the IMU pods. The parts are
from revision 2 of the CAD (after the engineering reviews). Details per bed are in `PRINT_LIST.md`, and a top view of
every bed is in `bed_layouts.png`.

## What is in this folder

| Folder or file | Use |
|---|---|
| `gcode/` | The 13 files to print. Copy them to the MINI's USB stick |
| `projects/` | The same beds as PrusaSlicer projects (.3mf). Open one to look at it or change a setting, then re-export |
| `stl/` | Every part as exported from SolidWorks (model orientation) |
| `oriented/` | Every part turned to its print orientation |
| `beds/` | The parts laid out on each 180 x 180 bed, one STL per bed |
| `slice_all.py` | Rebuilds everything above from `stl/` |

## Settings

- Your own profiles: Original Prusa MINI, 0.20 mm QUALITY @MINI, Prusament PLA (215 C nozzle, 60 C bed).
- Two lines are left out of the print profile: `bed_temperature_extruder` and `wipe_tower_extruder`. They are
  multi-extruder settings that crash the PrusaSlicer 2.9.4 command line, and they do nothing on a MINI.
- The clamp brackets, clamp caps and rail plates take the load, so they get 5 perimeters and 50 % infill, as the
  reviews ask. The enclosure parts get 3 perimeters and 25 %.
- Supports:
  - the clamp bracket's half bore: build plate only;
  - the pod head upper's brow: auto;
  - the pod tray and box: build plate only.
  - everything else prints without supports.

## Order for tomorrow (about 75 h in total, 0.9 kg of PLA)

1. `07_Bar_Clamp_Bracket_and_Cap` (9 h) and `05_Dash_Rail_Plate_and_Joiners` (4 h 20 min) first. Check that the
   rail slides into the bracket (0.35 mm a side) and that the thumb screw drops into the detent. Do this before
   printing the rest, because everything hangs on this fit. Print bed 07 a second time later, for the sensor pod.
2. `13_IMU_Pods_x2` (2 h 30 min) and `06_Dash_Pi5_Cradle_and_Cross_Joiner` (2 h): quick, and they check the hole
   sizes (inserts, M3 and M2.5).
3. The four dashboard shell quarters (01 to 04, about 3 h 50 min each). Run them on parallel MINIs if you can.
4. The sensor pod: 09, 11 and 12, then the two long ones overnight: `08_Pod_Head_Upper` (10 h 20 min) and
   `10_Pod_Box_Base` (11 h 20 min).
   - The pod still has unmeasured sizes: the sensor board's holes and the side ToF angle (see
     `CAD/Sensor_Pod/ENGINEERING_REVIEW.md`).
   - Print it as a fit check, or wait for the measurements.

## Notes

- PLA softens at about 55 C, so these prints are for fit and function checks. Reprint the parts that live on the
  vehicle in PETG or ASA: the clamp, rail plates, shell and pod.
- Heat-set inserts in PLA: use a lower iron temperature (about 190 to 200 C) and press slowly.
- Glue the shell quarters' walls with the display fitted as a jig. Bolt the plates with M3 button heads inside and
  nyloc nuts outside.
