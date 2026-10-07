# SW-7 sensor pod: camera, ToF sensor board, Raspberry Pi 4 and ESP32 in one housing

Files: `sw7_sensor_pod.scad` (source, parametric), `base_CONCEPT.stl` and `lid_CONCEPT.stl` (exported from the
placeholder sizes: do not print), `concept_assembly.png`, `concept_front.png`, `concept_top.png`.

Status (7 Oct 2026): concept. The Raspberry Pi 4 and camera dimensions are known; the sensor board and ESP32
sizes are placeholders, marked MEASURE in the .scad. Measure, change the numbers, re-export, test-print, then print.

## Why one housing

The camera and the three ToF sensors share one rigid front, so their directions are fixed by the print instead of
by how parts are taped down. The camera's lens sits on the centre line above the ahead sensor, and the left and
right faces are angled to the side sensors. That makes the fusion calibration (test C9) a measurement of the
printed geometry, done once, and `fusion_config.json` can then hold the measured angles.

## What is in it

- Front: the sensor board lies flat on two edge rails (no hole positions assumed), with its three ToF sensors
  looking out through windows cut along each sensor's line of sight (25 degree cone plus margin), so each window is
  exactly where that sensor looks. The camera sits in the case already printed for it
  (`CameraMount/casing`, 29.2 x 28.2 x 12.35 mm, measured from the STL) on a shelf above the board, behind a window
  cut to its 53.5 degree field of view.
- Back: the Raspberry Pi 4 on four standoffs on its 58 x 49 mm M2.5 hole pattern (2.2 mm pilot for self-tapping
  screws or heat-set inserts), with the USB and Ethernet end open at the back and a slot for the USB-C power side;
  an ESP32 bay with corner guides, three cable holes (USB, antenna leads) and two IMU pockets in the stiff floor.
- Lid: a 30 mm fan opening over the Pi's processor with its M3 holes (the Pi 4 reached its temperature limit on
  the bench), vent slots over the ESP32 bay, and a locating lip.
- Two mounting ears with hose-clamp or zip-tie slots and an M5 hole, so the pod comes off the vehicle quickly.
- Placeholder outside size: about 139 x 164 x 57 mm. Print in PETG or ASA, not PLA.

## Measurements needed (calipers, mm), with a photo of each board next to a ruler

Sensor board (JCP 2025 Sense v1.0):
1. Width (left to right, with the side sensors on) and depth (front to back); a top-view photo with a ruler.
2. PCB thickness; tallest part above it (the ToF breakouts, the 2x16 header); tallest part or pin underneath.
3. Each ToF sensor's lens position: the ahead one's distance behind the front edge; the side ones' distance from
   the centre line and behind the front edge; and their height above the PCB.
4. The angle of the side sensors from straight ahead (the angled board edges).
5. Where the 2x16 header is and which way its cable leaves.
6. Any mounting holes (positions and diameter), if it has them.

ESP32 board: length, width, height to the tallest part, where its USB and antenna sockets are.
IMU breakouts: length, width, thickness.
On the vehicle: where the pod will sit (photo with a tape), what it will be fixed to (tube diameter or flat plate),
and its height above the road (sets the camera tilt).

## SolidWorks

The model is written in OpenSCAD so every size is a named parameter that can be changed and re-exported in seconds.
The exported STL files open in SolidWorks (File > Open, type Mesh, "Import as Solid Body" for STL files under 20 000
facets, or as a graphics body to view and measure), and they go straight to a slicer for printing. Changes are best
made in the .scad parameters and re-exported, rather than by editing the mesh in SolidWorks.

## Power note

The telemetry unit must not be powered from the Pi's USB port (its LTE modem caused the under-voltage seen on 6 Oct).
Leave room for a powered USB hub or a separate 5 V supply in the vehicle wiring.
