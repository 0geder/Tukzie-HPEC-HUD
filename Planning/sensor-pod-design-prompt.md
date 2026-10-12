# Front sensor pod: camera, ToF sensor board, Raspberry Pi 4 and ESP32-S3 (12 Oct 2026)

## What the student asked for

> check the layout that I want the sensor board to be with the camera given that those are the dimensions I have
> measured for the boards and its with to give room to the TOFs and the pins it has. you see theres also the
> esp32-s3 makerfab that you gotta account for and check for the wires as well. lets go design the stuff.

Printer: Prusa Mini, a 180 x 180 x 180 mm bed. Parts larger than that are split and joined with bolted plates, as for
the dashboard (`CAD/Dashboard_Enclosure`). Material: PETG or ASA, since the parts sit outdoors in sun and rain.

## Measurements (student, 12 Oct, whiteboard and photos)

Sensor board (JCP 2025 Sense v1.0), seen from above, is a six-sided "boat" outline:
- One long straight edge, 86 mm.
- The opposite edge, 41 mm, parallel to it and centred.
- Two short end edges, 22 mm each, square to the long edge.
- Two angled edges, 30 mm each, joining the end edges to the 41 mm edge. Only one of each was labelled. The board
  looks symmetric in the photos; check that.
- From these, each angled edge covers (86 - 41) / 2 = 22.5 mm along the board and about 19.8 mm across it, so the
  board is about 22 + 19.8 = 41.8 mm deep. The angled edges sit about 41 degrees off the long edge. These are
  derived figures: confirm them against the photos and the fusion config (`CameraDetection`,
  `fusion_config.json` or similar).
- Heights from the side sketch: 14 mm above the PCB (ToF breakouts on their headers, header bodies) and 6 mm below
  it (pin tails). PCB 1.6 mm assumed.
- Which edge faces forward? The photos show the ToF breakouts standing on headers near the angled corners, looking
  out ahead and to the sides. Work out the forward edge and the three sensors' lines of sight from the photos, the
  code (`CameraDetection/tof_reader.py`, fusion config), and `CameraMount/sensor_pod/README.md`. If the result
  cannot be told for certain, state the assumption and make it one parameter.
- Pins: a long header row along one edge, and Dupont jumper wires to the Pi 4 GPIO (power, ground, I2C and the
  XSHUT lines, about 8 to 10 wires). Each Dupont housing needs about 15 mm straight plus a bend radius. Leave a
  cable channel for the bundle.

Camera:
- It sits in the printed yellow case, 29.2 x 28.2 x 12.35 mm (from its STL in `CameraMount/casing`), lens facing
  forward.
- The student's layout puts the camera directly above the sensor board, centred, with its bottom a few mm above
  the board's top components (ruler photo: case from about 0 to 2.6 cm, board at about 3 to 4.5 cm).
- The camera's flat ribbon cable (15-pin, about 16 mm wide) runs down behind the board to the Pi 4's CSI connector.
  Do not crease it. The minimum bend radius is about 5 mm, and its length (measure: 15 or 30 cm) limits how far the
  Pi 4 can be.

Raspberry Pi 4: 85 x 56 mm, M2.5 holes on a 58 x 49 mm pattern, 3.5 mm from the edges. It has a 30 mm fan on top (the
student fitted one; the Pi reached its temperature limit on the bench). USB and Ethernet stack 16 mm tall. Its USB
ports hold a flash drive and the ESP32's cable.

ESP32-S3 telemetry board, Makerfabs, with the A7670 LTE modem:
- A red board with a GNSS patch antenna on top, three USB-C ports, an LTE antenna (u.FL), a SIM slot and a LiPo pack
  taped underneath.
- Find its official outline, hole positions and connector positions (Makerfabs wiki or GitHub, the product page,
  the KiCad or Gerber files). If they are not published, estimate from the photos against the Pi 4 (85 x 56 mm) and
  list the measurements the student must take.
- The GNSS patch must see the sky through plastic only, never under metal or carbon-loaded plastic. Keep the LTE
  antenna away from the Pi and the ribbon.
- Power: the modem must not be powered from the Pi's USB (it caused under-voltage resets on 6 Oct). Leave room for
  a powered USB hub or a separate 5 V buck converter and its wiring.

## Where it goes on the vehicle

- Today's vehicle is the green TUKZIE test tuk-tuk. See `MeasurementsOfTuktuk`, `Photos/Reference/Vehicle_Measurements`
  and the meter-area photo: about 30.5 cm across at the meter.
- The pod mounts at the front, looking ahead, with the camera at a known height and tilt (a parameter). Attach it to
  a tube or plate with a clamp and strap slots, as the dashboard bracket does, so it comes off quickly. The
  handlebar is assumed 22.2 mm until measured.
- Style: match the TUKZIE concept renders in `Projects/new_tukzie_*.png`: faceted, angular panels, black lower part
  and a light-bar line. A plain box is not enough, but function comes first.

## Design questions to answer, with a recommendation

1. One housing (camera, board, Pi 4 and ESP32) against two (a front sensor head with the camera and board, plus an
   electronics box with the Pi 4 and ESP32, linked by the ribbon and the Dupont bundle). Weigh the Prusa Mini size
   limit, heat (Pi 4 fan, sun), GNSS sky view, the ribbon length, serviceability and vibration.
2. ToF windows: an open aperture shaped to each sensor's 25 degree cone plus margin, or a cover. VL53L0X ranging
   degrades behind most plastics. Recommend apertures with a drip lip, and keep the camera window clear of the ToF
   cones.
3. Wire routing: the Dupont bundle and ribbon paths, strain relief (cable-tie anchors), grommets, a drip loop, and
   room to unplug everything.
4. Rain and dust: a drip edge over the windows, vents on the underside only, and a sealed lid seam (a lip or a
   gasket groove).

## Deliverables

1. `CAD/Sensor_Pod/` with SolidWorks parts built by scripts in `build/`, following `CAD/Dashboard_Enclosure/build`:
   - global variables for every measured size;
   - `sm.AddToDB = True` while sketching (no grid snapping);
   - `SetUserPreferenceToggle(10, False)`;
   - transforms set through `_oleobj_.Invoke` by dispatch id;
   - check every cut by volume;
   - extrusion direction is the third argument of FeatureExtrusion2.

   Also produce:
   - an assembly with reference parts for the board, camera, Pi 4 (with fan) and ESP32, plus the ToF cones as thin
     reference bodies, so the window clearance can be seen;
   - previews in `previews/`;
   - a README with the parts table, hardware list, print orientation and a "measure before printing" list.
2. Every printed part must fit 180 x 180 x 180 mm.
3. Check interference in the assembly (SolidWorks' interference detection, or a script check of bounding boxes and
   the cones against the walls), and report clearances to the ToF cones, the camera's field of view (53.5 degrees
   horizontal), the Dupont plugs and the ribbon.
4. Only one agent drives SolidWorks at a time. Close every document you open. If a part is open in the student's
   SolidWorks window, say so instead of fighting the file lock.
5. Commit on your branch. No push, no co-author line, no em dashes in docs.
