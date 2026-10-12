# Front sensor pod: camera, ToF sensor board, Raspberry Pi 4 and ESP32-S3

Status (12 Oct 2026): first complete model, not printed. Built in SolidWorks 2025 by the scripts in `build/`. Every
size is in `build/params.py`, marked measured, official, estimated or design. Brief:
`Planning/sensor-pod-design-prompt.md`. Research and layout: `Planning/sensor-pod-layout.md`.

The pod is two pieces bolted into one rigid unit, so each part fits the Prusa Mini (180 x 180 x 180 mm):

- **Sensor head** at the front. The camera sits in its yellow case, centred above the sensor board, as in the student's
  layout. The three ToF sensors look out through open, flared windows (25 degree cone plus 5 degrees of margin) with
  drip hoods over them. The faceted top, the brow over the camera and the light-bar groove follow the TUKZIE concept
  renders.
- **Electronics box** behind it:
  - the Raspberry Pi 4 with its fan in the front bay;
  - the Makerfabs ESP32-S3 A7670 in the rear bay, under a thinned plastic roof so the GNSS patch sees the sky;
  - room for a 5 V buck converter or a small powered hub;
  - an SMA bulkhead for the LTE antenna and a cable gland for the vehicle feed;
  - a side hatch to reach the flash drive and the ESP32 cable;
  - a sunshade over the Pi bay.
- **Mount**: a rail plate under the box carries the same dovetail as the dashboard mount, so the pod uses the
  dashboard's bar clamp unchanged. Print a second `CAD/Dashboard_Enclosure/SW7_Dash_Bracket.SLDPRT` and
  `SW7_Dash_Clamp_Cap.SLDPRT`. The pod slides forward onto the clamp. Fit the bracket with its closed end to the
  front, so braking pushes the pod against the stop. The thumb screw stops it sliding back.

`SW7_Sensor_Pod_Assembly.SLDASM` puts everything together on a dummy 22.2 mm bar, with reference bodies for the board,
camera, Pi 4 with fan, ESP32 with LiPo and GNSS patch, and the view cones. SolidWorks' interference check finds no
overlaps, including between the cones and the walls. Pictures are in `previews/`.

## Printed parts

| Part | Size (mm) | Print | Notes |
|---|---|---|---|
| SW7_Pod_Head_Upper | 105 x 68 x 63 | 1 | Roof up, or on its back if the brow needs it; support under the brow only |
| SW7_Pod_Head_Tray | 97 x 60 x 27 | 1 | Floor down. The board sits on its standoffs. The ribbon guide and the jumper channel are in it |
| SW7_Pod_Camera_Retainer | 38 x 16 x 2 | 1 | Flat |
| SW7_Pod_Box_Base | 149 x 143 x 38 | 1 | Floor down. This is the largest part: check the slicer shows it inside the bed |
| SW7_Pod_Box_Lid | 149 x 146 x 5 | 1 | Outer face down |
| SW7_Pod_Sunshade | 100 x 64 x 7 | 1 | Flat |
| SW7_Pod_USB_Hatch_Cover | 52 x 34 x 5 | 1 | Flat |
| SW7_Pod_Rail_Plate | 84 x 60 x 12 | 1 | Plate down, rail up |
| Dashboard bracket and clamp cap | 56 x 80 x 30, 40 x 40 x 12 | 1 each | From `CAD/Dashboard_Enclosure` |

Print in PETG or ASA, not PLA, because the pod sits in the sun. Do not use carbon-filled filament for the lid,
because it would block the GNSS signal.

## Hardware

- M3 heat-set inserts and M3 screws:
  - 4 for the head-to-box flange;
  - 2 for the head seam;
  - 6 for the lid;
  - 4 for the hatch;
  - 4 for the rail plate.
- M2 screws: 4 for the sensor board (self-tapping into 1.6 mm pilots, hole positions estimated), 4 for the camera
  retainer, 4 for the ESP32.
- M2.5 screws: 4 for the Pi 4.
- From the dashboard clamp: 2 M5 x 30 bolts with heat-set inserts, an M4 thumb screw, and a strip of bicycle inner
  tube.
- Others:
  - an SMA bulkhead pigtail (u.FL to SMA) for the LTE antenna;
  - a PG7 gland or rubber grommet;
  - a foam ring between the camera case and the front wall;
  - cable ties.

## Assembly

1. Fit the inserts with a soldering iron.
2. Screw the sensor board into the tray. Plug the Dupont jumpers into J2 from below, run them through the channel
   and tie them to the anchor.
3. Put the camera case in its cradle in the upper shell with the foam ring, and fit the retainer. Lead the ribbon
   down over the board (5 mm minimum bend) and through the cable window into the box.
4. Close the head: seat the upper shell's skirt inside the tray and fit the 2 seam screws.
5. Fit the Pi 4, the ESP32 and the buck converter in the box. Connect the ribbon, the jumpers, power and the antenna
   pigtail.
6. Bolt the head to the box with the 4 flange screws from inside the box. Fit the lid, the sunshade and the hatch
   cover.
7. Bolt the rail plate under the box. Clamp the bracket on the tube with its closed end forward, turn it to set the
   pod's tilt, slide the pod on and tighten the thumb screw.

## Measure before printing

These come from `Planning/sensor-pod-layout.md`. The values in `params.py` are estimates until they are measured.

1. Sensor board:
   - the front edge (the photo suggests 44 to 47 mm against the 41 mm drawn) and the depth;
   - whether it is symmetric;
   - its mounting holes, if it has any.
2. Side ToF directions. A finger test shows which way each side sensor looks. In the photos they look straight out
   sideways (`TOF_SIDE_BEARING = 90`), but `CameraDetection/fusion_config.json` assumes 35 degrees. Make the two
   agree. If the carriers move to 35 degrees, set `TOF_SIDE_BEARING = 35` and rebuild.
3. The ToF chips' height above the PCB (`TOF_Z`, estimated at 9 mm), and the Dupont plug depth under J2.
4. The camera ribbon's length (15 cm assumed; the path needs about 115 mm) and where it leaves the case.
5. ESP32: the LiPo's size, the GNSS patch's size, and the LTE antenna. Also the board revision (the Eagle file is
   V1.2; the photo shows V1.1).
6. The fan's thickness (10 mm assumed). The 5 V buck converter or hub you will use (a 30 x 50 x 20 mm space is
   reserved).
7. The tube at the mounting spot (22.2 mm assumed), and what sits beside the pod on the vehicle.

## Rebuilding

With SolidWorks open, run these in order from `build/`. Each saves its parts and pictures.
1. `1_sensor_head.py`: upper shell and camera retainer.
2. `2_sensor_tray.py`: tray.
3. `3_electronics_box.py`: box base, lid, hatch cover and sunshade.
4. `4_mount_and_refs.py`: rail plate, reference parts and view cones.
5. `5_assembly.py`: assembly, interference check and previews.

The dashboard bracket and cap come from `CAD/Dashboard_Enclosure/build/2_bracket.py`.
