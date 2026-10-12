# Reference dimensions for the SW-7 enclosures

Compiled 12 Oct 2026 for the two printed enclosures: the dashboard display back shell (Pi 5 behind the 10.1 inch screen) and the front sensor casing (camera, JCP Sense v1.0 ToF board, Pi 4, ESP32-S3 A7670X).

Source labels used below:

- measured: measured by the student (whiteboard, calipers, tape or STL)
- official: from the manufacturer's drawing or page (URL given)
- vac team: from the Tukzie-Vac-Work-2026 folder (path given)
- estimated: inferred, not measured or documented; check before printing

All sizes in mm unless stated. Paths are relative to `PlatformIO/Projects/`.

## 1. Dashboard display (Waveshare 10.1 inch HDMI LCD (B) with case)

Identification. The vac Dashboard Team recorded the screen as "WS HDMI 10.1" 1280x800 IPS (B) capacitive touch" supplied by PiShop with its stock case and bracket (vac team: `Tukzie-Vac-Work-2026/Dashboard Team/README.md` lines 79 and 322; `Dashboard Team/HANDOVER.md` lines 16, 42). That is the Waveshare 10.1inch HDMI LCD (B) (with case). Its official outline, 274.12 x 187.00 mm, agrees with the student's 272 x 187 mm, so this is a likely match, verify. The 2 mm difference on the long side is within a tape or ruler reading, but measure it with calipers before fixing the shell's inner size.

Official drawings: product page dimension image https://www.waveshare.com/img/devkit/LCD/10.1BK/Exterior-Size.jpg and the 2D drawing https://files.waveshare.com/wiki/10.1inch_HDMI_LCD_B_with_case/10.1inch_HDMI_LCD_B_with_case_2D_PDF_20260116.pdf (DXF and STEP are on the same wiki: https://www.waveshare.com/wiki/10.1inch_HDMI_LCD_(B)_(with_case)). The STEP file can be imported straight into SolidWorks as a reference body.

| Item | Value | Source |
|---|---|---|
| Outer frame, long x short | 272 x 187 | measured (whiteboard photo `Tukzie-HPEC-HUD/Photos/Reference/2026-10-12_whiteboard_dashboard_272x187_pi5_imu_sizes.jpg`) |
| Outer frame, long x short | 274.12 x 187.00 (product image rounds to 274.11) | official (2D PDF above) |
| Frame corner radius | R6 front frame, R5 back plate | official (2D PDF) |
| Cover glass (lens) outline | 253.96 +/- 0.10 x 168.60 | official (2D PDF, "LENS OD") |
| Glass inset from frame edge | 10.14 (long sides), 9.20 (short sides) | official (2D PDF) |
| Visible area of the glass | 217.96 +/- 0.20 x 136.60 | official (2D PDF, "LENS VA") |
| Active (display) area | 216.96 x 135.60 | official (product dimension image) |
| Visible area offset in glass | 18.00 from one short edge, 16.00 from one long edge | official (2D PDF) |
| Back plate width (short direction) | 173.4 | official (2D PDF back view) |
| Overall thickness, front frame to back plate, no Pi | 18.00 | official (2D PDF side view) |
| Front layers (frame + glass) | 8.10, of which the top layer is 1.90 | official (2D PDF side view) |
| Whole stack with Pi 5 behind | about 20 | measured (student's estimate, photos `2026-10-12_display_stack_side_view_1.jpg`, `_2.jpg`) |
| Resolution | 1280 x 800 IPS, capacitive touch | official (wiki); vac team README |
| Pi mounting on the back plate | hole set "2" = Pi A+/B+/2B/3B pattern, which is the same 58 x 49 pattern as Pi 4 and Pi 5 | official (2D PDF back view legend) |
| Connectors on the driver board | HDMI (full size), micro USB power, micro USB touch, power switch, all on one short edge | official (product image, 2D PDF) |
| Frame screws | 12 around the front frame (3 per long side plus corners and mid short side, from the image) | official image, count estimated |
| VESA pattern | none; the stock case only has a 45 degree back stand | official (product image) |

Gap to check. Waveshare's official stack is 18 mm before the Pi, but the student's estimate for the whole stack with the Pi 5 is about 20 mm. A Pi 5 behind the back plate on standoffs would add roughly 20 to 25 mm more (board, USB and Ethernet stack about 16 mm, plus standoffs). Either the Pi sits within the stack (between the plates) on this unit, or the 20 mm excludes the Pi. Measure the depth from the front glass to the tallest point of the Pi (the USB/Ethernet stack or the cooler) before setting `DispT` in `Tukzie-HPEC-HUD/CAD/Dashboard_Enclosure/build/1_back_shell.py` (currently 20).

## 2. Raspberry Pi 5 (dashboard, behind the display)

Official drawing: https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-mechanical-drawing.pdf (redirects to https://pip.raspberrypi.com/documents/RP-008347-DS-raspberry-pi-5-mechanical-drawing.pdf). Edges below: "left" is the short edge away from the USB/Ethernet end, "bottom" is the long edge with USB-C and micro HDMI, as drawn.

| Item | Value | Source |
|---|---|---|
| Board outline | 85 x 56 | official |
| Mounting holes | 4 x ø2.7 (for M2.5), 58 x 49 pattern, centres 3.5 from the left and top/bottom edges | official |
| Hole pad keep-out | 6 diameter around each hole | official |
| Extra holes for the Active Cooler push pins | 2 smaller holes (one labelled ø3), positions on the drawing | official |
| USB-C power, centre from left edge | 11.2 | official |
| micro HDMI 0 and 1, centres from left edge | 25.8 and 39.2 | official |
| USB-A ports and Ethernet on the right short edge, centres from bottom edge | Ethernet 10.2; USB stacks 29.1 and 47 | official |
| Port overhang past the 85 mm edge | 3 | official (side view) |
| Small side-view steps | 0.45, 4.1, 3.2, 3.4, 4.4, 4.1 (connector heights at the left end) | official (side view, unlabelled) |
| Tallest part (USB/Ethernet stack) above the PCB | about 16 | estimated (same connectors as the Pi 4, Z = 16.0) |
| PCB thickness | about 1.4 to 1.6 | estimated, not on the drawing; measure |
| Active Cooler footprint | 63.50 x 42.50, fan 30 x 30 | official https://datasheets.raspberrypi.com/cooling/raspberry-pi-active-cooler-mechanical-drawing.pdf |
| Active Cooler height | 13.70 overall in the side view (includes the push-pin heads under the board line) | official (same drawing) |
| Pi 5 as drawn on the whiteboard | 90 x 60 (with clearance) | measured (whiteboard photo) |

## 3. Raspberry Pi 4 Model B (front sensor casing)

Official drawing: https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-mechanical-drawing.pdf. Z values are component heights above the PCB top.

| Item | Value | Source |
|---|---|---|
| Board outline, corner radius | 85 x 56, R3.0 | official |
| Mounting holes | ø2.7 (M2.5), 58 x 49 pattern, centres 3.5 from edges | official |
| USB-A stacks | Z = 16.0, centres 9 and 27 from the bottom edge | official |
| Ethernet | Z = 13.5, centre 45.75 from the bottom edge | official |
| GPIO header | Z = 8.5, 2 x 20, centred 29 from the left hole (on the hole line) | official |
| USB-C | Z = 3.2, centre 3.5 + 7.7 = 11.2 from the left edge | official |
| micro HDMI 0 and 1 | Z = 3.0, centres 26.0 and 39.5 from the left edge (11.2 + 14.8, then + 13.5) | official |
| Audio jack | Z = 6.0 | official |
| CSI (camera) and DSI connectors | Z = 5.5 | official |
| PoE header | 6.14 below the top edge near the top-right hole | official |
| Port overhang past the right edge | about 2 to 3 (USB and Ethernet) | estimated from the drawing |
| PCB thickness | about 1.4 | estimated, measure |

## 4. Camera (OV5647 v1 module in the student's printed case)

The project camera is the OV5647 (Camera Module v1 type, NoIR) on a 15 cm ribbon to the Pi 4 (`Tukzie-HPEC-HUD/Report/Methodology.tex` line 41; `Report/appendixd.tex` line 130).

| Item | Value | Source |
|---|---|---|
| Printed case, assembled | 29.2 x 28.2 x 12.35 | measured (from the STLs, `Tukzie-HPEC-HUD/CameraMount/casing/RPi_cam_case_*.stl`) |
| Case bottom shell | 29.2 x 28.2 x 7.6 | measured (`Report/appendixb.tex` line 4) |
| Case top cover | 4.8 thick | measured (same) |
| 30 degree corner mount | 32.3 tall | measured (same) |
| Camera Module v2 PCB | 25 x 23.862, R2.0 corners | official https://datasheets.raspberrypi.com/camera/camera-module-2-mechanical-drawing.pdf |
| v2 mounting holes | 4 x ø2.2, centres 2 from the edges; pattern 21 x 12.5 (holes at 2 and 23 across, 2 and 14.5 up) | official (same) |
| v2 lens centre | 12.5 from the hole-row edge (on the axis between the 14.5 holes), 9.462 from the connector-side edge | official (same) |
| v2 connector | 15-way FPC at one 25 mm edge, 20.8 long, about 5.5 deep | official (same) |
| Camera Module 3 PCB, thickness | 25 x 23.862; PCB 1.12; 11.3 from the PCB back to the lens front | official https://datasheets.raspberrypi.com/camera/camera-module-3-standard-mechanical-drawing.pdf |
| Camera Module 3 holes, lens | ø2.2 holes, same 21 x 12.5 pattern; lens body 8.9 square, 66 degree horizontal field | official (same) |
| v1 (OV5647) board | 25 x 24, hole pattern as v2 | estimated (the v1 and v2 share the footprint by common report; `CameraMount/README.md` notes no official v1 drawing was found); measure |
| Ribbon, 15-way 1.0 mm pitch (Pi 4, camera side) | 16 wide, about 0.3 thick with stiffener | estimated (standard FFC width = (pins + 1) x pitch); measure |
| Ribbon, 22-way 0.5 mm pitch (Pi 5 end) | 11.5 wide | estimated (same rule); pitch is official per the Pi 5 camera cable listings, e.g. https://thepihut.com/collections/raspberry-pi/products/camera-adapter-cable-for-raspberry-pi-5 and https://www.pishop.us/product/camera-cable-for-raspberry-pi-5/ |
| Suggested casing slot for the ribbon | 18 x 2.5 for 15-way (as in `CameraMount/camera_mount.scad`), 13.5 x 2.5 for 22-way | estimated (2 mm clearance each side) |

## 5. JCP 2025 Sense v1.0 ToF sensor board

No dimensions are recorded anywhere in either repository. Everything in `Tukzie-HPEC-HUD/CameraMount/sensor_pod/sw7_sensor_pod.scad` lines 20 to 31 is marked MEASURE (placeholders 70 x 45, 1.6 PCB, 10 tall, 35 degree side angle).

| Item | Value | Source |
|---|---|---|
| Sensors | 3 x VL53L0X (centre plus two angled side wings), about 25 degree field each | measured on the bench (chip confirmed, `BenchTest/TEST_PROCEDURES.md` line 169); field of view from the scad comments |
| Header | 2 x 16 header J2 along one edge, pins 1/2 and 31/32 marked; ribbon cable to the Pi | measured (`Report/appendixd.tex` line 18) |
| Board length | about 120 | estimated from a photo (`Photos/Reference/README.md`, sensor board photo); measure |
| Width, depth, PCB thickness, side-wing angle, lens positions, holes | not recorded | gap: measure with calipers (list in `CameraMount/sensor_pod/README.md`) |

## 6. ESP32-S3 A7670X board (Makerfabs) and IMUs

| Item | Value | Source |
|---|---|---|
| Makerfabs ESP32-S3 4G LTE CAT1 A7670X outline, holes, height | not found online (Makerfabs pages returned 404); not recorded locally | gap: measure. Do not use the Waveshare ESP32-S3-A7670E figure (30.44 x 110), which is a different board |
| ESP32 placeholder in the pod model | 90 x 60 x 22 | estimated (`sw7_sensor_pod.scad` line 34, marked MEASURE) |
| IMU breakout (GY-521, MPU-6050) | 20 x 17 | measured (whiteboard photo) |
| IMU placeholder in the IMU pod | 21.5 x 16.5 | estimated (`CAD/IMU_Pod/build/1_base_body.py`, marked MEASURE) |

## 7. Vehicle measurements already on file

From `Tukzie-HPEC-HUD/Photos/Reference/README.md` (photos of 2 Sep 2026, readings from the tape, approximate):

| Item | Value | Source |
|---|---|---|
| Handlebar height at the left grip | about 690 | measured |
| Meter and headlamp area width to the steering stem | about 305 | measured |
| Handlebar above the rear seat | about 640 | measured |
| Mirror span region | about 900 | measured |
| Driver seat width | about 720 | measured |

Not recorded anywhere: handlebar tube diameter, steering stem diameter, frame tube sizes at the IMU points, space behind the dashboard. The vac team recorded no vehicle mounting points or tube sizes either.

## 8. Vac Sensor Team enclosure (Tukzie-Vac-Work-2026/Sensor Team/enclosure)

This is the vac team's box for a Raspberry Pi 5 and the ESP32 (not a display mount). The SolidWorks files were read without SolidWorks: the 2018+ format stores zlib-compressed sections, and the `swXmlContents/KeyWords` section lists every feature with its driving dimensions, and `PreviewPNG` holds the thumbnail. Dimension names (D1, D2, ...) cannot be tied to specific edges without opening the sketch, so the interpretations below are estimated; confirm in SolidWorks.

Files: `Assem1.SLDASM` (components housing_v.2-1, secure_pi-1, lidv.2-1; no mates recorded), `housing_v.2.SLDPRT`, `lidv.2.SLDPRT`, `bracket.SLDPRT` (saved internally as "secure_pi"). All from vac team, path `Tukzie-Vac-Work-2026/Sensor Team/enclosure/`.

housing_v.2.SLDPRT

| Feature (sketch or extrusion) | Dimensions | Likely meaning (estimated) |
|---|---|---|
| base sketch, Boss-Extrude1 | 176 x 157.5, R5 corners; 4 thick | outer footprint and floor |
| exterior walls, Boss-Extrude2 | 4 thick walls on 176 x 157.5; 60 tall | walls; total height 64 |
| TXD1/TXD2/TXD3 | 181.5, 200, 64 | overall size including the mounting tabs (157.5 + 2 x 12 = 181.5, 176 + 2 x 12 = 200) |
| Sketch20, Boss-Extrude5 | tabs 12 out, R10 and R5, 4 x ø4 holes, 50 spacing, 6 and 8 offsets; 4 thick | four mounting tabs at the base with M4 holes |
| Pi support, Boss-Extrude3 | 90, 92, 56, 12, 13, 10, 7, 2; 10 tall | locating ribs or posts around the Pi 5 (85 x 56 board) |
| ESP mounting hole, Cut-Extrude1 | 71, 48, 4.25, 15.25, 2 x ø2.8; 4 deep | ESP32 board holes (positions, verify) |
| interior wall, Boss-Extrude4 | 10, 4 thick; 55.5 tall | divider wall between the Pi and ESP32 bays |
| interior wall holes | 10, 15, 5, R3 | cable passes through the divider |
| lid groove, Cut-Extrude4 | 2 wide, R5; 2.5 deep | groove for the lid lip |
| Sketch14 with LPattern2/3 | ø2 holes, 8.5 offset, pattern 62 spacing x 2 | M2 holes for the Pi hold-down bracket (vac notes say too small) |
| Sketch10, Sketch13 | 40 x 43, R3; 52 x 17 | rectangular port opening in one wall (visible in the preview) |
| Sketch17, Sketch19 | ø15 holes | cable or gland entries |
| ventilation, Sketch21 to 26, LPattern4 to 9 | ø5 holes on 17 and 14.25 pitch, 166, 15, 11.75, 10.25 | vent holes along the walls |
| Sketch27, Cut-Extrude18 | 129.5 x 3.5, R1, 15, 10; 10 deep | long slot in the base for the buck converters (vac notes) |
| Sketch29 | 5 x 5, R3 | small cut-out |

lidv.2.SLDPRT: plate 173.5 x 152.5, R5, 2 thick; lip 2.25 wide and 2.5 tall (sketch values 9, 3.65, 2). The lid sits inside the 176 x 157.5 walls on the groove.

bracket.SLDPRT ("secure_pi"): a hat-shaped strap over the Pi. Sketch3: 52 span, 20 legs, 2 thick, 8 feet; extruded 10 wide; ø2 hole in each foot (5 and 3 offsets); LPattern 62 spacing.

Vac team notes on this enclosure (`Tukzie-Vac-Work-2026/Sensor Team/Raspberry Pi setup.pdf`, Housing section): add a slot on the left wall for the CAN wiring; the bracket holes were modelled for M2 and are too small; the long base slot was a stand-in because the buck converter hole positions were unknown; add holes in the back wall for the converter supply. The vac team found no recorded tuk-tuk mounting points, tube sizes or display dimensions.

Previews of the three parts and assembly were extracted to a temporary folder only; nothing was saved in the repository.

## 9. Gaps to measure before printing

1. Display: long side with calipers (272 or 274.1), and the true depth from the glass to the tallest point of the Pi 5 or its cooler.
2. Which cooler is on the Pi 5 (Active Cooler 13.7, a heatsink, or none).
3. JCP Sense v1.0 board: width, depth, thickness, side-wing angle, lens positions, header position, any holes.
4. Makerfabs ESP32-S3 A7670X: outline, holes, height with the LiPo, USB-C and antenna socket positions.
5. Camera v1 board: confirm 25 x 24 and the 21 x 12.5 hole pattern on the actual board; ribbon width with calipers.
6. Vehicle: handlebar and stem tube diameters, frame tube sizes at the IMU points, the space behind the dashboard.
