# Component placement and enclosures on the TUKZIE Rev 0

Status: proposal, 30 Sep 2026. Nothing here has been fitted yet. Positions
depend on the vehicle, so each one is to be confirmed on the trike (with
Yusuf, and with SW-6 and JBM11, who are building onto the same vehicle).

## What has to go on the vehicle

| Part | Needs |
|---|---|
| ESP32-S3 A7670X board, LiPo | Dry, cool, rigid, USB-C reachable for flashing and `!recal` |
| LTE antenna | Away from metal and from the GNSS antenna |
| GNSS patch antenna | Clear sky view, ceramic face up, not under metal |
| IMU1, IMU2 | Hard-mounted to the frame at two points, known orientation |
| Raspberry Pi 4 | Within ribbon-cable reach of the camera, ventilated |
| Camera (existing printed casing and 30 degree mount) | Front, centred, level, clear view ahead |
| Sync wire and ground | Short, latched, strain-relieved (came loose twice on the bench) |
| Power | 5 V for the Pi and the ESP32 from the 72 V pack: fused converter, not yet chosen (power budget still open) |
| Optocoupler Hall tap (later) | Near the motor connector, after the supervisor agrees (D31) |

## Proposed placement

1. One front electronics box behind the dashboard or windshield frame,
   holding the Pi 4 and the ESP32 board. Reasons: the camera ribbon is
   short (standard 15 cm; long CSI ribbons pick up noise), and putting both
   boards in one box makes the sync wire a few centimetres long and
   protected, which removes the loose-jumper problem.
2. Camera on the windshield frame or handlebar crossbar, centred, in the
   existing casing. Level it with the phone's spirit level; check framing
   with the live view.
3. GNSS patch on top of the dashboard under the windshield (glass and
   plastic are fine, metal is not), face up. If there is a metal roof,
   the patch must not be under it; put it on the roof or at the front edge.
4. LTE antenna on the side or top of the front box, vertical if possible,
   at least 10 cm from the GNSS patch.
5. IMUs, two different points on rigid frame members (not plastic panels,
   which resonate). Suggested: IMU1 on the frame under the driver's seat
   (the ISO 2631-1 seat-base point, what the driver feels); IMU2 on the
   frame near the front wheel or the rear axle (closer to the road input).
   This is a decision for the student and supervisor; the fusion reports
   the disagreement between the two points either way.
6. Cables: IMU cables along frame members, cable-tied every 15 to 20 cm,
   with drip loops before each box entry, away from the motor phase wires
   and the motor controller.

## Enclosure design rules

- Material: PETG or ASA, not PLA (PLA softens at about 55 to 60 C, which
  a parked vehicle in the sun can reach).
- Water and dust: lid with an overlapping lip or a gasket; no openings on
  top; cables enter from the bottom through glands or tight grommets.
  Aim for rain-splash protection, roughly IP54.
- Boards on standoffs with heat-set inserts, screws with threadlocker or
  nylon lock nuts. Pi 4 holes: 58 by 49 mm, M2.5. ESP32 board holes: to be
  measured.
- The main box may sit on rubber grommets. The IMUs must not: they are
  there to measure the frame's vibration, and any isolation filters it.
  Screw each IMU pod to the frame or a steel bracket (double-sided tape is
  acceptable only as a temporary fix, since it damps high frequencies).
- IMU pods: small stiff printed box, two screws to the frame, the MPU6050
  screwed inside, an axis arrow (X forward, Z up) printed on the lid. Both
  IMUs in the same orientation.
- Heat: side vents with a baffle, or a heatsink case, for the Pi; keep the
  LiPo away from the Pi and out of direct sun.
- Access: slot for the ESP32 USB-C, the Pi's SD card reachable, a window
  or light pipe for the board LEDs.
- Connectors: latched JST-XH/PH or screw terminals instead of jumpers,
  with strain relief at every box entry. Sync and ground in the same
  cable as IMU2's I2C (the pins share connector J5 by design).
- I2C runs: keep each IMU cable under about 1 m, with SDA, SCL and ground
  twisted together. Check SDA/SCL again at the vehicle (T8) and watch for
  I2C errors in `!status`.
- Label every box and cable end.

## For today's mounting session

The printed enclosures cannot be ready today. Temporary fit, in order:
1. Measure and photograph (list below).
2. IMUs screwed or clamped to the chosen frame points, orientation noted
   and photographed; then `!recal` with the trike still.
3. Front box: a spare plastic project box or the boards on a plate,
   cable-tied behind the dashboard, out of the rain.
4. Camera casing on the windshield frame, levelled.
5. Sync wire and ground taped or glued at both ends.

## Measurements needed to design the enclosures

- ESP32 A7670X board outline, hole positions, height with the LiPo, and
  where the USB-C, antenna connectors and headers are.
- Antenna cable lengths (LTE and GNSS) from the board.
- Space available behind the dashboard (width, height, depth) and what
  it can be fixed to.
- Frame tube or plate sizes at the two IMU points (for clamps or screws).
- Cable run lengths: front box to each IMU point, to the camera, to the
  power source.
- Whether the roof (if any) is metal.
- Photos of each location, with a tape measure in view.

With these, parametric OpenSCAD models (like `CameraMount/`) can be made
for the front box, the two IMU pods and a GNSS antenna holder.
