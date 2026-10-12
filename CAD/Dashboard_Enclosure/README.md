# Dashboard display enclosure and clip-on mount

Status (12 Oct 2026): second model, not printed. Built in SolidWorks 2025 through its API by the scripts in `build/`.
Every key size is a global variable (Tools > Equations), so a new measurement is one number to change.

The display is a Waveshare 10.1" HDMI LCD (B) in its stock case (named in the vac Dashboard Team's README; see
`../reference_dimensions.md`). The parts are sized for the Prusa Mini, whose bed is 180 x 180 x 180 mm.

## Parts

| Part | Size (mm) | Print | What it does |
|---|---|---|---|
| SW7_Dash_Back_Shell.SLDPRT | 280.4 x 193.2 x 27 | Do not print. This is the master that the quarters are cut from. | Tray covering the back of the display. The display presses in from the front past 1.2 mm snap lips on the long walls. 24 mm deep inside. |
| print_parts/SW7_Dash_Shell_Q_Left_Top, Left_Bottom, Right_Top, Right_Bottom | 140.2 x 96.6 x 27 each | 1 of each | The four quarters of the shell |
| print_parts/SW7_Dash_Rail_Plate.SLDPRT | 120 x 120 x 4, rail 6 mm high | 1 | Bolts across the centre with eight M3 (two into each quarter), so it holds the quarters together. Carries the dovetail rail (30 to 38 mm wide, 90 mm long). |
| print_parts/SW7_Dash_Joiner_Plate.SLDPRT | 44 x 20 x 3 | 4 | Bolt across the outer ends of the two split lines, two M3 each |
| SW7_Dash_Bracket.SLDPRT | 56 x 80 x 18 | 1 | Stays on the tuk-tuk. The rail slides down into its dovetail channel, which is closed at the bottom. An M4 thumb screw from the side locks it. A saddle sits on the tube and two slots take hose clamps or 9 mm cable ties. |

Hardware: 16 x M3 x 8 bolts with nuts (the shell's back is 3 mm thick and the plates 3 to 4 mm), and 1 x M4 thumb screw.
Also glue the quarter walls where they butt together (epoxy or CA for PETG).

Layout, seen from the driver (+X is the driver's right):
- Cable exit, 70 x 16 mm, in the right-hand short wall. This is the side where the display's and the Pi's connectors are.
- Vent slots in two rows near the right-hand side, over the Pi 5.
- The rail runs vertically on the back, so the display slides down onto the bracket and lifts off upwards.

## Numbers used

| Value | Source |
|---|---|
| Display outer 274.2 x 187 mm | Waveshare drawing gives 274.12 x 187.00. The student measured 272 x 187; the larger value is used so it cannot be too tight. |
| Stack depth 20 mm (`DispT`) | Student's estimate. Waveshare gives 18 mm for the case without the Pi, so with a Pi 5 on the back it is probably deeper. Measure the deepest point, including the Pi and plugs, before printing. |
| Meter area about 30.5 cm across | Tape photo, 2 Sep 2026. The 280 mm shell fits with about 1 cm to spare each side. |
| Tube diameter 32 mm (`TubeD`, bracket) | Placeholder. Measure what the bracket will strap to. |
| Raspberry Pi 5: 85 x 56 mm, M2.5 holes 58 x 49 mm | Official mechanical drawing |

## Before printing

1. Measure the stack depth and set `DispT` in `build/1_back_shell.py`.
2. Measure the tube at the meter and set `TubeD` in `build/2_bracket.py`.
3. Check that the connectors really come out on the right-hand short side, and that the cable exit's height
   (it starts 2 mm above the floor) lines up with them.
4. Print the bracket and the rail plate first and test the slide. The clearance is `Slide` = 0.3 mm a side.
5. Use PETG or ASA. PLA softens in the sun. Print the quarters open side up; they need no supports.

## Rebuilding

With SolidWorks open, run these in order:
1. `python build/1_back_shell.py` makes the master shell.
2. `python build/2_bracket.py` makes the bracket.
3. `python build/3_split_and_plates.py` makes the quarters and the plates. The bolt-hole layout is read from the shell script, so the two stay matched.
