# Front sensor pod: research and layout (12 Oct 2026)

Answers the questions in `Planning/sensor-pod-design-prompt.md` and gives the CAD agent a layout and a parameter table. No CAD was done and no code was changed.

Source labels in the tables:

- measured: the student's measurement (whiteboard, ruler photo, STL)
- official: manufacturer drawing, design file or datasheet (URL given)
- estimated: inferred from a photo or from general knowledge; check before printing

Coordinates used throughout (mm): X to the right when looking forward, Y forward, Z up. The origin O is the centre of the sensor board's long (86 mm, rear) edge, on the top surface of the PCB.

## 1. Makerfabs ESP32-S3 A7670X board

### Which board

The repository names it the Makerfabs "ESP32-S3 4G LTE CAT1 A7670X" (`TelemetryUnit/src/main.cpp` lines 23 and 35, `CHANGELOG.md`, `Report/appendixb.tex` Figure makerfabs-pinout, `References/Hardware/esp32s3-zero-4g-lte-1.jpg`). The modem on the unit reports itself as an A7670SA. The product listing is https://www.tindie.com/products/makerfabs/esp32-4g-lte-cat1-a7670x/ (ESP32-S3-WROOM-1, 16 MB flash, 8 MB PSRAM; no dimensions given there). The Makerfabs wiki pages return 404 (checked again today).

### Official outline from the design file

Makerfabs publish the Eagle board file in the product's GitHub repository: https://github.com/Makerfabs/ESP32-S3-4G-LTE-CAT1-A7670X/tree/main/hardware (`ESP32-S3 4G LTE CAT1 V1.2.brd`, with `.sch` and a schematic PDF). I read the outline layer (layer 20) and the part placements from it. The board photo in the repo pinout image is silkscreened V1.1, while the file is V1.2, so confirm the outline with calipers (it is very likely unchanged). The vac Sensor Team's enclosure sketch already used "71, 48" for the ESP mounting holes (`CAD/reference_dimensions.md` section 8), which matches.

Board frame below: origin at the corner with the two side USB-C ports nearest (the "left, bottom" corner of the pinout photo's left view), x along the 75 mm edge, y along the 52 mm edge, top side is the side with the A7670 module.

| Item | Value (mm) | Source |
|---|---|---|
| Outline | 75.0 x 52.0, R2 corners | official (.brd layer 20) |
| Mounting holes | 4, at (2, 2), (73, 2), (2, 50), (73, 50): a 71 x 48 pattern, 2 from each edge | official (.brd) |
| Hole size | outline circle radius 1.143, so about 2.3 diameter: M2 clearance | official (.brd); confirm the drilled size |
| A7670 module (top side) | 24 x 24, centre (44.8, 31.5) | official (.brd) |
| USB-C, ESP32-S3 native | centre y 13.7, on the x = 0 edge, overhangs about 0.9 | official (.brd footprint) |
| USB-C, ESP32-S3 USB-TTL (CH340K) | centre y 35.2, on the x = 0 edge, overhangs about 0.9 | official (.brd) |
| USB-C, A7670X modem USB | centre x 13.6, on the y = 52 edge, overhangs about 1.0 | official (.brd) |
| 3.5 mm audio jack | about x 0 to 13, y 22 to 28, on the x = 0 edge (14.5 x 6.1 x 4.0 part, overhangs about 1.2) | official (.brd footprint name) |
| 5 V IN connector (PH2.0, right angle) | (6.2, 44.4) | official (.brd) |
| Battery connector BAT (PH2.0, right angle) | (9.0, 6.3) | official (.brd) |
| Power slide switch | (17.0, 2.7), on the y = 0 edge | official (.brd) |
| LTE antenna socket (u.FL) | (52.6, 10.5) | official (.brd) |
| GPS antenna socket (u.FL) | (65.1, 41.5) | official (.brd) |
| PWRKEY and BOOT buttons | (72.8, 9.9) and (72.9, 19.1), on the x = 75 edge | official (.brd) |
| 13-pin headers J5 and J2 (2.54 pitch) | along y = 2 and y = 50, x 37.5 to 70.5 | official (.brd) |
| ESP32-S3-WROOM-1 module | bottom side, centre (62.2, 35.1); module 18 x 25.5 x 3.1 | position official (.brd); size official (Espressif WROOM-1 datasheet, https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf) |
| micro SD socket | bottom side, near (60, 15.6) | official (.brd) |
| SIM socket (micro SIM) | bottom side, near (20.3, 35.5) | official (.brd) |
| PCB thickness | 1.6 | estimated |
| Tallest top part without antennas | about 4 (audio jack 4.0; USB-C about 3.2) | estimated from footprint names; pin headers add 8.5 if fitted |
| Tallest bottom part | about 3.1 (WROOM-1) before the LiPo | estimated |
| LiPo pack taped underneath | not known | measure |
| GNSS patch antenna (taped on top) | not known; ceramic patches are usually 25 x 25 x 4 (passive) or 25 x 25 x 8 (active) with a 10 cm lead | estimated, measure |
| LTE antenna | type not known (FPC sticker or whip on a u.FL to SMA lead) | measure |

What the student still has to measure on this board: outline with calipers (75 x 52 expected), hole diameter, LiPo size and thickness, total height from the bottom of the LiPo to the top of the GNSS patch, the GNSS patch size and lead length, the LTE antenna type, size and lead length, and whether pin headers are fitted on J2 and J5.

## 2. Sensor board (JCP 2025 Sense v1.0) orientation

### Evidence

- `Report/figures/sensor_board_top.jpg` (top view, the board on a table) and `Photos/Reference/Enclosures/2026-10-12_sensor_board_and_camera_pod_with_ribbon.jpg`.
- `CameraDetection/tof_reader.py`: three sensors named left, ahead, right (XSHUT GPIO22, 23, 24). The module calls it the UCT 2025 micromouse sensor board.
- `BenchTest/TEST_PROCEDURES.md` C7: the fingertip cover test confirmed that the labels left, ahead and right match the physical sensors.
- `CameraDetection/fusion_config.json`: bearings -35, 0, +35 degrees, half-angle 12.5, all marked as defaults until the C9 calibration (`"calibrated": false`). They were never measured.
- `Report/appendixd.tex`: the carriers sit on J4, J5 and J6. The 2 x 16 header J2 runs along the long edge.

### Result

- Forward edge: the short, 41 mm edge. The ahead carrier (J5) stands on edge along that edge with its face pointing outward, so the board points forward like a boat bow. The long 86 mm edge, where J2 is, is the rear edge.
- The ahead sensor looks straight ahead (0 degrees).
- The left (J4) and right (J6) carriers also stand on edge, but their planes run front to back (parallel to the Y axis) in both photos. In the angled photo their planes make about 93 degrees with the long edge. So as built, the side sensors look straight out sideways, at about -90 and +90 degrees, not at -35 and +35 as `fusion_config.json` assumes. This needs a 30-second check by the student: put a finger 5 cm to the side of the board, then 5 cm diagonally in front, and see which one the left reading responds to.
- If the side sensors do look at plus and minus 90 degrees, their cones (plus or minus 12.5 degrees) never overlap the camera's view (plus or minus 26.75 degrees), so the fusion can only report them as ToF-only obstacles. The carriers appear to sit in female sockets on J4 and J6 (black socket strips beside the carrier pins in the crop). If so, they can be moved onto 6-way female-to-male leads and held at any angle by the housing. Two options for the CAD, as one parameter `tof_side_bearing`:
  - 90 (as built, default): side windows in the side walls.
  - 35 (remote-mounted carriers): windows in the angled front facets, so the cones (22.5 to 47.5 degrees) slightly overlap the camera's edge; this is the geometry the fusion config already assumes.
  Either way, C9 step 3 then measures the real bearings and the config gets updated (not done here, no code edits).
- J2 (2 x 16, 2.54 mm pitch) is along the rear edge, rows about 2 and 5 mm in from it, centred on X = 0, pins spanning X -19 to +19. The top view shows only solder joints on top, so the header body and its pins are underneath and the Dupont plugs go on from below. This sets the space needed under the board (see the side view). The brief's "6 mm below" probably counts only the pin tails; ask the student.
- Four plated holes, about 2 mm (M2), sit around the U1 square, at about X -11.6 / +11.0 and Y 11.8 / 34.9 (a pattern of about 22.6 x 23.1). They are the best way to fix the board (M2 standoffs), better than edge rails. Estimated from the photo; measure.
- The legend at J2's left end names 3V3, DA, CL, SH1 to SH3, 5V.

### Outline

| Item | From the student's figures | From the top photo (scaled to the 86 mm edge, 17.7 px/mm) |
|---|---|---|
| Rear edge | 86 (measured) | 86 (scale reference) |
| Front edge | 41 (measured) | about 44 to 47 |
| End edges | 22 (measured) | about 22.5 |
| Angled edges | 30 (measured, one side) | about 28 to 29 |
| Angle of the angled edges to the rear edge | 41.4 degrees (derived: cos = 22.5/30) | about 45 degrees (right side clean; the left side is blurred by glare) |
| Depth, rear to front edge | 41.8 (derived: 22 + 19.8) | about 43 |
| Ahead carrier (J5) | | centred, its face about 1 mm proud of the front edge, carrier about 18 wide |
| Left carrier J4 outer face | | X about -26, centre Y about 31, about 17 long in Y |
| Right carrier J6 outer face | | X about +23, centre Y about 33 |
| Board edge outboard of the side carriers | | about 8 to 9 mm |

The two sets disagree by 3 to 6 mm on the front edge and by about 4 degrees on the angle. The student's four numbers are not quite consistent with a 45 degree chamfer, and the photo has some perspective error, so neither is certain. For the CAD: build the outline from the student's numbers as parameters, but leave a 3 mm gap at the angled walls and the front wall (instead of 1.5) until the student measures the front edge and the depth directly. The carrier positions look 3 mm asymmetric; measure them.

Heights: 14 above the PCB (carrier tops), PCB 1.6 (assumed), and the underside to be confirmed. The ToF chip centre height above the PCB is not known; 9 is used below (estimated).

### VL53L0X field of view and windows

- Field of view 25 degrees ("VL53L0X system FOV is 25 degrees", ST datasheet DS11555, section 5.1: https://www.st.com/resource/en/datasheet/vl53l0x.pdf). Use a 12.5 degree half-angle plus a 5 degree margin, so 17.5 degrees for the window flare.
- The datasheet's range table (Table 11, 33 ms budget) gives 80 cm typical and 60 cm minimum for a white target outdoors (overcast), and 50 / 40 cm for a grey target, against 2 m and 1.2 m indoors. Outdoors in sun the 1.2 m `max_range_m` in the fusion config is optimistic; expect well under 1 m. Worth noting in the report.
- Cover glass: the datasheet says the cross-talk (the cover's own reflection) depends on the glass type and the air gap, and must be calibrated with the cover fitted (sections 2.3.2 and 2.3.3). ST's cover window note is AN4907, "VL53L0X ranging module cover window guidelines": https://www.st.com/resource/en/application_note/an4907-vl53l0x-ranging-module-cover-window-guidelines-stmicroelectronics.pdf. Its full text could not be downloaded today (st.com timed out), so its numbers are not quoted here. ST's general advice (AN5231 for single-zone sensors, https://www.st.com/resource/en/application_note/an5231-cover-glass-guidelines-for-the-singlezone-timeofflight-sensor-stmicroelectronics.pdf, and the ST community) is: a thin window that passes 940 nm well, the smallest possible air gap (under about 1 mm), and the larger the gap the more cross-talk.
- These carriers stand 3 to 13 mm behind any wall, so a cover window would have a large air gap. Printed PETG or ASA scatters infrared. Recommendation: open apertures, no cover, each flared at 17.5 degrees from the chip outward, with a hood above and a sill sloping down and out below. If a cover is ever needed, glue a 1 mm 940 nm-transmissive window straight onto the carrier face, not into the housing wall, and redo the cross-talk calibration.
- Aperture size at a wall face a distance d from the chip: width = 4.4 + 2 d tan(17.5) = 4.4 + 0.63 d (4.4 x 2.4 is the VL53L0X package; ST datasheet outline). Height = 2.4 + 0.63 d.

## 3. Camera

- Module: Raspberry Pi Camera Module v1 type, OV5647, without an infrared-cut filter (NoIR), on a 15 cm ribbon to the Pi 4 (`Report/Methodology.tex` line 41, `Report/appendixd.tex` line 130).
- Field of view (official, Raspberry Pi camera documentation, https://www.raspberrypi.com/documentation/accessories/camera.html, hardware specification table): 53.50 +/- 0.13 degrees horizontal, 41.41 +/- 0.11 degrees vertical; focal length 3.60 mm. The 53.5 matches `camera_hfov_deg` in the fusion config.
- Ribbon: 15-way, 1.0 mm pitch FFC, 16 mm wide, about 0.3 mm thick with stiffened ends (estimated by the standard FFC rule; `CAD/reference_dimensions.md` section 4). Contacts face the HDMI ports at the Pi end. Standard lengths sold: 15 cm (in the camera box), and 30, 50, 100 and 200 cm from third parties (estimated from retail listings). Minimum bend radius about 5 mm, no creases.
- From the case STLs (`CameraMount/casing`, measured by loading the files): the case is 29.2 x 28.2, bottom shell 7.6 and top cover 4.75 deep (12.35 total). The lens opening in the top cover is 9.6 x 9.6, centred across the 29.2 width and 11.6 from the 28.2 side's lower edge, not centred. The ribbon slot is on that same lower edge, in the bottom (rear) shell. The camera board holes are on a 21 x 12.5 pattern, matching the v2 drawing. So with the lens forward and the ribbon edge down, the lens centre is 11.6 mm above the case's bottom face, and the ribbon leaves the bottom face about 1.2 to 7.6 mm in front of the case's rear face.

## 4. One housing or two

| Point | One printed housing (camera, board, Pi 4, ESP32) | Sensor head plus electronics box, bolted into one unit |
|---|---|---|
| Prusa Mini 180 mm limit | The layout below is about 145 x 202 x 77 overall; one piece would be over 180 in depth, so it would need splitting anyway | Head about 94 x 59 x 77, box about 145 x 143 x 41; each fits, no splitting |
| Heat | Pi 4 fan, sun and the camera share one air space | A double wall between the Pi and the camera; the Pi bay has its own vent path |
| LiPo on the ESP32 | Sits next to the Pi's heat | Own bay behind a divider. LiPo cells are usually rated to charge only up to about 45 C (estimated, check the pack label), and the board's TP4056 charges whenever 5 V is present, so keep this bay away from the Pi and shaded |
| GNSS sky view | Fine on the roof | Fine on the box roof over the ESP32 bay; the head only hides the sky low ahead |
| Ribbon (15 cm) | Short | Short: path about 115 mm (computed below), as long as the Pi is directly behind the head |
| Serviceability | One lid opens everything, but the camera and board are reached past the Pi | The head comes off with 4 screws; the box lid gives access to the Pi and ESP32 |
| Vibration | One stiff body | One stiff body too, because the two are bolted on a flange and share one clamp |
| Later VL53L5CX (the report's intended sensor, `Report/Methodology.tex` line 190) | Reprint everything | Reprint only the head |

Recommendation: a sensor head plus an electronics box, bolted together through a flange into one rigid pod on one clamp, with an internal cable window between them. Not two units at different places on the vehicle: the 15 cm ribbon and the Dupont wires rule that out, and a longer ribbon is the only way to separate them (the report notes noise risk with longer ribbons; a 30 cm ribbon is the fallback if the measured path is too tight).

## 5. Layout

All values in mm, frame as above (O = centre of the board's rear edge, PCB top surface).

### Front view (looking back at the pod from in front)

```
            X=-72.4                                                         X=+72.4
              |<----------------- box, behind, 144.8 wide ----------------->|
                         |<------ head 93.8 wide ------->|
 Z=+48.6 ..............  +-------------------------------+   head roof, drip edge all round
                         |        _______________        |
                         |       |  camera window |      |   16 W x 15 H, flared, centre Z 27.6
 Z=+27.6  lens axis -----|-------|      ( o )     |------|   optional 1.5 clear acrylic disc
                         |       |_______________|       |
 Z=+16   camera case btm |  ===== hood (drip lip) =====  |   web between windows about 7
 Z=+12.4 ...box roof.....|...............................|.......................
                  <--[ ]  |            [ T ]             |  [ ]-->   side ToF windows (if bearing 90)
 Z=+9    ToF chip centres |  side eye   ahead window      | side eye  ahead window 9 W x 8 H
 Z=0     PCB top          |================================|           side windows 13 (Y) x 11 (Z)
                          |   (board, carriers to Z=+14)  |
 Z=-18   Dupont plugs end |       |||||||||||||||        |   under the rear strip only
 Z=-26   head floor (in)  |                               |   vents only in the box floor
 Z=-28.4 ................ +-------------------------------+ ......................
                                    | clamp |  (under the box, see side view)
```

### Side view (from the right, forward is to the left)

```
  forward <---                                                                 ---> rear
  Y=+47.4 +45 +43     +30.65     0  -9.5 -11.9 -14.3   -26.3                -82.3 -88       -152 -154.4
     |     |   |         |       |    |    |    |        |                    |    |            |    |
     +---------------------------------+  +------------------------------------------------------+   Z=+48.6 head roof
     |win| camera case  |                |  |
     |[o]| 12.35 deep   |                |  |
     |   |  lens Z 27.6 |                |  |
     |   |______________| Z=16           |  |
     |      ribbon exits case bottom     |  |  box roof / lid, Z +10 inner, +12.4 outer, sunshade over Pi bay
     |      at Y~34, R5 bend rearwards   |  +--+---------------------------------------+---------------------+  Z=+12.4
     |           \___________________    |     |   ribbon S-bend through the window,   |  GNSS patch under   |
     |  hood      Z~11 over the board   \|     |   runs back at Z~+3 to the CSI         |  the roof (plastic  |
     |[T] ahead ToF Z 9   carriers to 14 )R5   |   v CSI at Y~-38, X 0                  |  only above it)     |
     |=================================== |     |  [fan]   Pi 4, PCB top Z -16.6       |  ESP32 75x52 on 12  |
     |  board PCB, Z 0                    |    window|  ==========================  GPIO|  standoffs, LiPo    |
     |  M2 pillars    J2 + Dupont plugs   |   40x32  |  USB-C (right angle) at front    |D |  below; buck 5 V    |
     |  to the floor  |||  bend back R5 --+--------> |  8 mm standoffs                  |I |  beside it          |  LTE antenna
     |                                    |          |                                  |V |                     |  on the rear wall
     +---------------------------------+  +------------------------------------------------------+   Z=-28.4
          vents: none in the head           floor slots, intake +X end, exhaust -X end, 3 mm upstands
                                  |<- flange, 4 x M3 -->|            clamp + strap slots under Y ~ -83
```

### Plan view of the box (from above, forward at the top)

```
  Y=-14.3  +----------------------------------------------------------------+  front wall (flange to head)
           |            cable window X -20..+20 (ribbon top, Dupont bottom) |
           |  USB plug zone   | Pi 4, ports edge forward, X -40..+45 |power |
           |  X -70..-43      | USB-C at X +33.8 on the front edge   |chan. |
           |  flash drive,    | CSI at X 0, Y about -38              |X +45 |
           |  right-angle USB | fan over the SoC                     |..+70 |
           |  to the ESP32    | GPIO on the rear edge, centre X 12.5 |      |
  Y=-86    +==================+======== divider, 2 thick =============+======+
           |  USB-C plug zone | ESP32 X -46..+29, Y -149..-97        | buck |
           |  X -70..-46      | GNSS patch above, on the roof        | 5 V  |
           |                  | LTE u.FL at X 6.6, Y -138.5          | X +32|
           |                  |                                      | ..+67|
  Y=-152   +----------------------------------------------------------------+  rear wall: LTE antenna,
                                                                                power gland at X +55
```

### Routing

- Ribbon: leaves the case bottom at about Y 34, Z 16; R5 bend rearwards; runs back at Z about 11 (clears the jumpers J1/J3 and the socket at U1, about 9, estimated) to Y -5 behind the board's rear edge; S-bend (two R5 bends) down to Z about +3; through the top of the cable window; back over the Pi's front strip to the CSI connector at about X 0, Y -38; R5 bend down into the connector. Path about 8 + 34 + 16 + 33 + 8 + 12 + 4 = 115 mm, leaving about 35 mm slack on the 15 cm ribbon. The slack loops in the head behind the board (Y 0 to -9.5). Two cable-tie anchors: on the head roof behind the camera and on the box front wall above the window. Keep the ribbon at least 30 mm from the LTE antenna and its lead (it is about 100 mm away in this layout).
- Dupont bundle (8 to 10 wires): plugs on J2 from below, about 14 long (to Z about -18), wires bend back with R5 at Z about -20, then through the bottom of the cable window, along the floor of the Pi bay on the -X side of the Pi, and up to the GPIO header on the Pi's rear edge (plugs on top, to Z about +6, under the roof at +10). Path about 150 mm; 20 cm Dupont leads fit. One cable-tie anchor on the head floor behind the board and one on the Pi bay floor.
- Pi power: 5 V from the buck in the ESP32 bay, through the divider along the +X power channel, to the Pi's USB-C on its front edge with a right-angle plug (or to GPIO 5 V and GND if the plug does not fit; that bypasses the Pi's input fuse).
- ESP32 power: from the same buck, not from the Pi's USB (6 Oct under-voltage). The data cable from a Pi USB-A port to the ESP32 runs along the -X side: Pi USB end and the ESP32's USB-C edge both face -X, so it is a short right-angle USB-A to USB-C lead through a notch in the divider.
- External cables (vehicle 5 V or 12 V feed): one cable gland or grommet in the rear wall at the bottom, with a drip loop below it outside. Nothing enters through the roof.

### Rain, dust and heat

- Drip edges: the head roof overhangs the front face by 8 and has a drip groove underneath. A hood (drip lip) runs across above the ahead ToF window, and a smaller one above each side window. Rule to keep the hoods out of the beams: a hood that sticks out L in front of a window, with its lower edge h above the beam axis, is clear of the ToF cone if L < h / tan(17.5) = 3.2 h, and clear of the camera's vertical view if L < h / tan(23.7) = 2.3 h (half of 41.4 degrees plus 3 margin, plus the pod tilt).
- Window sills slope down and outward by at least 15 degrees, so water drains out.
- Camera window: either open behind a hood, or a 1.5 mm clear acrylic or polycarbonate disc glued in a recess on the outside (the camera tolerates a cover, the ToF sensors do not). A foam ring between the case front and the wall stops reflections from inside and keeps dust off the lens.
- Vents only in the box floor, with 3 mm internal upstands: intake at the +X end, exhaust at the -X end of the Pi bay. The fan pulls air from the box and blows it onto the Pi.
- Lid seam: a tongue (2 wide, 2.5 tall) into a groove with a 1.5 mm cord gasket or a printed TPU gasket; the same on the head-to-box flange around the cable window.
- Sun: a second roof skin (sunshade, 5 mm air gap) over the Pi bay; light colour. PETG or ASA, never PLA. No metal, no carbon-filled filament and no metallic paint over the GNSS patch.

### Mounting

One clamp under the box near Y -83, X 0 (close to the centre of mass), on the 22.2 mm handlebar assumption until measured, plus two strap slots as on the dashboard bracket. The pitch is set at the clamp (parameter `pod_tilt_deg`). Tilting the pod also tilts the ToF beams; at a 0.9 m mounting height and 5 degrees down, the lower edge of the ahead cone meets the road about 2.9 m ahead, beyond its range, so a small down tilt is safe.

## 6. Parameter table for the CAD agent

| Parameter | Value (mm or degrees) | Source |
|---|---|---|
| Sensor board rear edge | 86 | measured |
| Front edge | 41 (photo suggests 44 to 47) | measured, check |
| End edges | 22 | measured |
| Angled edges | 30 | measured (one side) |
| Angled edge angle to the rear edge | 41.4 (photo about 45) | derived from measured |
| Board depth | 41.8 (photo about 43) | derived, check |
| Gap board to wall | 3 until rechecked, then 1.5 | design choice |
| PCB thickness | 1.6 | estimated |
| Tallest part above the PCB (carriers) | 14 | measured |
| Under-board clearance for J2 Dupont plugs | 24.4 (floor at Z -26) | estimated; 8 if J2 points up |
| Board mounting holes | 4 x about M2, about (+/-11.3, 11.8) and (+/-11.3, 34.9) | estimated from photo |
| J2 header | 2 x 16, 2.54 pitch, rows at Y 2.1 and 5.0, X -19 to +19, body underneath | estimated from photo |
| Ahead ToF chip centre | X 0, Y 44, Z 9 | estimated |
| Side ToF chip centres | X -26 and +23 (likely +/-24.5), Y 32, Z 9 | estimated from photo |
| `tof_side_bearing` | 90 as built (35 if the carriers are remote-mounted) | estimated, check |
| ToF field of view | 25 full cone; window flare 17.5 half-angle | official (ST DS11555) plus margin |
| ToF package | 4.4 x 2.4 | official (ST DS11555) |
| Ahead ToF window, outer face | 9 W x 8 H, flared 17.5 | design (from the rule in section 2) |
| Side ToF windows, outer face | 13 (Y) x 11 (Z), on flat "eye" plates normal to the beam at abs(X) 35 inner, 37.4 outer | design |
| Camera case | 29.2 W x 28.2 H x 12.35 D | measured (STL) |
| Camera lens opening in case | 9.6 x 9.6, centred in X, 11.6 above the case bottom | measured (STL) |
| Camera case position | X -14.6 to +14.6, Y 30.65 to 43.0, Z 16 to 44.2 | design |
| Lens centre | X 0, Y 43, Z 27.6 | design |
| Ribbon exit | case bottom, Y about 34 (1.2 to 7.6 in front of the case rear face) | measured (STL), check |
| Camera horizontal / vertical FOV | 53.5 / 41.4 | official (Raspberry Pi docs) |
| Camera window, outer face | 16 W x 15 H, flared (26.75 + 3 sideways, 20.7 + 3 up and down, plus tilt) | design |
| Ribbon | 16 wide, 0.3 thick, 150 long, R5 minimum | width estimated, length measured (report), check |
| Ribbon slot where needed | 18 x 2.5 | estimated |
| Head wall / roof / floor | 2.4 | design |
| Head outer | X +/-46.9 at the rear, Y -11.9 to +47.4, Z -28.4 to +48.6 | design |
| Box outer | X +/-72.4, Y -11.9 to -154.4, Z -28.4 to +12.4 (sunshade +5) | design |
| Flange | 4 x M3 heat-set inserts, foam gasket | design |
| Cable window | X -20 to +20, Z -24 to +8 | design |
| Pi 4 board | 85 x 56, R3, PCB about 1.4 | official (Pi 4 mechanical drawing, https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-mechanical-drawing.pdf) |
| Pi 4 holes | M2.5, 58 x 49, 3.5 from edges; in box frame X -16.5 and +41.5, Y -29.8 and -78.8 | official pattern, design position |
| Pi 4 position | X -40 to +45, Y -26.3 to -82.3, PCB bottom Z -18 (8 mm standoffs) | design |
| Pi 4 USB/Ethernet stack | 16 above the PCB, about 3 overhang | official |
| Pi 4 GPIO header | 8.5 above the PCB, centre 29 from the USB-C-end hole along the hole line | official |
| Pi 4 CSI connector | 5.5 above the PCB, about 45 from the USB-C end, about 11.5 in from the port edge | height official, position estimated |
| Pi front clearance for USB-C plug | 12 with a right-angle plug (30 with a straight one) | estimated |
| Fan | 30 x 30, thickness about 10 | 30 measured (student), thickness estimated |
| ESP32 board | 75 x 52, R2, holes 71 x 48 at 2 from edges, about M2 | official (.brd) |
| ESP32 position | X -46 to +29, Y -149 to -97, on 12 mm standoffs | design |
| ESP32 USB-C edge clearance | 24 | estimated |
| ESP32 total height incl. LiPo and patch | not known (placeholder 22 in the old scad) | measure |
| GNSS patch | 25 x 25 x 8 placeholder, under the roof above the ESP32 | estimated |
| LTE antenna | on the rear wall, X +6 to +40 | design; type to measure |
| 5 V buck converter | 60 x 35 x 20 placeholder, X +32 to +67 in the ESP32 bay | estimated |
| Drip edge overhang | 8 roof, hoods per the rule in section 5 | design |
| Vent upstands | 3 | design |
| Lid tongue and groove | 2 wide, 2.5 tall, 1.5 cord | design |
| Handlebar tube | 22.2 | estimated (brief) |
| `pod_tilt_deg`, camera height | parameters | to set on the vehicle |
| Print limit | every part within 180 x 180 x 180 | Prusa Mini |

## 7. Measurements still needed from the student

1. Sensor board: front edge length, depth from the rear edge to the front edge, the second angled edge (symmetry), and a top-view photo square to the camera next to a ruler.
2. Which way the side sensors look (finger test, section 2), and whether the J4 and J6 carriers unplug from sockets.
3. J2: which side its plastic body and pins are on, and how far the Dupont plugs reach below the board when plugged in.
4. Mounting holes in the sensor board: positions and diameter.
5. Each ToF chip's centre height above the PCB, and the side carriers' outer-face X positions.
6. Height of the tallest part in the middle of the board (jumpers J1/J3, socket at U1), for the ribbon run.
7. Camera ribbon: length (15 cm assumed) and where it exits the yellow case.
8. ESP32 board: outline check (75 x 52), hole diameter, LiPo size, total height, the GNSS patch size and lead length, the LTE antenna type and lead length, and whether pin headers are fitted.
9. Fan thickness, and whether it sits on a heatsink.
10. The 5 V supply: buck converter or powered hub, its size, and what it is fed from on the vehicle.
11. On the vehicle: the mounting tube diameter, where the pod sits, its height above the road, and what is beside it within 1.2 m to the left and right (it would sit in the side sensors' beams if they look sideways).
