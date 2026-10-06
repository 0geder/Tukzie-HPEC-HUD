# Telemetry unit housing

Files: `telemetry_housing.scad` (source, parametric), `base_concept.stl` and `lid_concept.stl`
(exported from the placeholder sizes, do not print yet), `concept_assembly.png`, `concept_top.png`.

Status (6 Oct 2026): concept only. Every size marked MEASURE in the .scad is a placeholder, not a
measurement. Measure the parts, change the numbers, re-export, test-print the base at low infill, then
print the real one.

## What it holds and why it is shaped this way

- The Makerfabs ESP32-S3 A7670X board, held by its long edges on two rails and clamped by ribs in the lid,
  so no mounting-hole positions are assumed (same approach as `CameraMount/`).
- The two MPU6050 IMUs in pockets in a 4 mm floor. The base is bolted or clamped directly to the frame,
  so road and motor vibration reach the IMUs undamped. Do not put foam or rubber under the IMUs or the
  base: it would filter the very signal the ride analysis measures.
- One USB cable exit (to the Pi), three 6.5 mm exits for the antenna leads and the Hall and sync wires,
  and a 1.5 mm drain hole for condensation.
- A recess under the lid for the GNSS patch antenna, so it faces the sky under 1.2 mm of plastic if it
  stays inside the box.
- Ears with two hose-clamp or zip-tie slots and one M5 hole at each end, so the unit comes off quickly
  (the brief asks for project equipment to be easily removable).
- Print in PETG or ASA. PLA softens at about 55 to 60 C, which a vehicle parked in the sun can reach.
  No metal parts over the antennas.

## Measurements needed (calipers, in mm)

Electronics:
1. Board length and width, including any connector that sticks out past the PCB edge.
2. Board height: PCB underside to the tallest part on top (the modem shield or the antenna sockets).
3. Tallest part or pin on the PCB underside.
4. USB socket used for the Pi cable: which edge, distance of its centre from a corner, height above the PCB underside.
5. Each antenna: type (small patch, flexible strip or stub), size, and how it connects (a small snap-on
   IPEX/u.FL socket on the board, or soldered). A photo of each antenna and where its cable meets the board.
6. IMU breakout length, width and thickness (without header pins), and how its wires leave it.

On the trike (photos with a tape measure in view):
7. Two or three candidate spots on the frame, rigid metal, inside the cabin and out of the rain.
8. Tube diameter or flat-plate size at each spot.
9. Distance from each spot to where the Pi will sit (USB cable length), and to the roof (antenna lead length).

## Where to put it

- The box goes on rigid frame metal inside the cabin, close to the vehicle's centre and low down, so the
  IMUs measure the chassis and not a panel that flaps. Under or behind the seat, or on a frame member
  near the floor, are likely spots.
- The GPS antenna should not stay in the box if the box is under a metal roof or seat: it needs sky. If
  the antennas plug in with IPEX/u.FL sockets, an IPEX-to-SMA pigtail and an external active GNSS antenna
  on the roof (magnetic or adhesive base) is the robust fix; the 4G antenna also works better outside the
  box. If an antenna is soldered on, the box has to go where that antenna can see the sky, for example
  under the windscreen, and the IMUs then move to a small separate rigid mount on the frame.
- Keep the box away from the motor controller and the high-current battery cables (electrical noise and heat).

## Other housings still to do

- Raspberry Pi 4 with the three ToF sensors: the ToF sensors must face forward with a clear view, and
  the camera already has its own casing (`CameraMount/casing`). If the camera and ToF move to the Pi 5
  (AI HAT), this box is no longer needed.
- Raspberry Pi 5 and the dashboard screen: the team's mount, to be checked.
