# Dashboard display enclosure and clip-on mount

Status (12 Oct 2026): second model, not printed. Built in SolidWorks 2025 through its API by the scripts in `build/`.
Every key size is a global variable (Tools > Equations), so a new measurement is one number to change.

The display is a Waveshare 10.1" HDMI LCD (B) in its stock case (named in the vac Dashboard Team's README; see
`../reference_dimensions.md`). The parts are sized for the Prusa Mini, whose bed is 180 x 180 x 180 mm.

## Parts

| Part | Size (mm) | Print | What it does |
|---|---|---|---|
| SW7_Dash_Back_Shell.SLDPRT | 278.2 x 193.2 x 27 | Do not print. This is the master that the quarters are cut from. | Tray covering the back of the display. The display presses in from the front past 1.2 mm snap lips on the long walls. 24 mm deep inside. |
| print_parts/SW7_Dash_Shell_Q_Left_Top, Left_Bottom, Right_Top, Right_Bottom | 139.1 x 96.6 x 27 each | 1 of each | The four quarters of the shell |
| print_parts/SW7_Dash_Rail_Plate.SLDPRT | 120 x 120 x 4, rail 6 mm high | 1 | Bolts across the centre with eight M3 (two into each quarter), so it holds the quarters together. Carries the dovetail rail (30 to 38 mm wide, 90 mm long). |
| print_parts/SW7_Dash_Joiner_Plate.SLDPRT | 44 x 20 x 3 | 4 | Bolt across the outer ends of the two split lines, two M3 each |
| SW7_Dash_Bracket.SLDPRT | 56 x 80 x 18 | 1 | Stays on the tuk-tuk. The rail slides down into its dovetail channel, which is closed at the bottom. An M4 thumb screw from the side locks it. A saddle sits on the tube and two slots take hose clamps or 9 mm cable ties. |

Hardware: 16 x M3 x 8 bolts with nuts (the shell's back is 3 mm thick and the plates 3 to 4 mm), and 1 x M4 thumb screw.
Also glue the quarter walls where they butt together (epoxy or CA for PETG).

Layout, seen from the driver (+X is the driver's right, so the connector side is -X):
- Cable exit, 58 x 16 mm, in the left-hand short wall: the connectors span 43 to 45 mm (measured) plus room for the plug bodies. The display's HDMI, USB and power plugs come out on that side
  (photo `Photos/Reference/Enclosures/2026-10-12_display_on_desk_cables_left.jpg`). The opening is centred on the side
  and covers about 64 to 122 mm from the top edge, where the plugs sit in the photo.
- Vent slots in two rows near the left-hand side, behind the display's driver board.
- The rail runs vertically on the back, so the display slides down onto the bracket and lifts off upwards.

## Numbers used

| Value | Source |
|---|---|
| Display outer 272 x 187 mm | Measured tight by the student on 12 Oct. The Waveshare drawing gives 274.12 x 187.00, but the measurement is used. The pocket is 0.6 mm larger each side. |
| Stack depth 20 mm (`DispT`) | Student's estimate. Waveshare gives 18 mm for the case without the Pi, so with a Pi 5 on the back it is probably deeper. Measure the deepest point, including the Pi and plugs, before printing. |
| Meter area about 30.5 cm across | Tape photo, 2 Sep 2026. The 278 mm shell fits with about 1 cm to spare each side, if the plugs are right-angled. |
| Tube diameter 32 mm (`TubeD`, bracket) | Placeholder. Measure what the bracket will strap to. |
| Raspberry Pi 5: 85 x 56 mm, M2.5 holes 58 x 49 mm | Official mechanical drawing |

## Before printing

1. Measure the stack depth and set `DispT` in `build/1_back_shell.py`.
2. Measure the tube at the meter and set `TubeD` in `build/2_bracket.py`.
3. Check the cable exit against the plugs. Measure how far the plugs are from the top edge and from the back of
   the display. The exit starts 2 mm above the floor and is 16 mm tall. Right-angle HDMI and USB plugs keep the
   width beside the vehicle small.
4. Print the bracket and the rail plate first and test the slide. The clearance is `Slide` = 0.3 mm a side.
5. Use PETG or ASA. PLA softens in the sun. Print the quarters open side up; they need no supports.

## Rebuilding

With SolidWorks open, run these in order:
1. `python build/1_back_shell.py` makes the master shell.
2. `python build/2_bracket.py` makes the bracket.
3. `python build/3_split_and_plates.py` makes the quarters and the plates. The bolt-hole layout is read from the shell script, so the two stay matched.
