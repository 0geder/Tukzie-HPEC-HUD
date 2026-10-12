# Dashboard display enclosure and clip-on mount

Status (12 Oct 2026): first model, not printed. Built in SolidWorks 2025 through its API by the scripts in `build/`;
every key size is a global variable (Tools > Equations), so a new measurement is one number to change.

## Parts

| Part | Outside size (mm) | What it does |
|---|---|---|
| SW7_Dash_Back_Shell.SLDPRT | 278.2 x 193.2 x 27, plus a 6 mm rail | Tray that covers the back of the display. The 272 x 187 mm stack presses in from the front past 1.2 mm snap lips on the long walls. 24 mm deep inside (20 mm stack + 4 mm for plugs). Cable exit 60 x 12 mm in one long wall (the bottom when fitted), eight vent slots over the Pi 5, and a dovetail rail (30 to 38 mm wide, 6 mm high, 90 mm long) on the back. |
| SW7_Dash_Bracket.SLDPRT | 56 x 80 x 18 | Stays on the tuk-tuk. The shell's rail slides down into its dovetail channel, which is closed at the bottom so the shell cannot fall through. An M4 thumb screw from the side locks it. A saddle sits on the tube and two 9 x 3.5 mm slots take hose clamps or cable ties. |

To fit: strap the bracket at the meter, slide the display down onto it, tighten the thumb screw. To remove it, loosen the screw and lift the display off. The bracket stays on the vehicle.

## Numbers used

| Value | Source |
|---|---|
| Display outer 272 x 187 mm | Measured by the student (whiteboard photo, `Photos/Reference/Enclosures/`) |
| Stack thickness 20 mm | Student's estimate. Measure the deepest point, including the Pi 5 and any plugs. |
| Meter area about 30.5 cm across | Tape photo, 2 Sep 2026. The 278 mm shell fits with about 1.5 cm to spare. |
| Tube diameter 32 mm (`TubeD`) | Placeholder. Measure what the bracket will strap to at the meter. |
| Raspberry Pi 5: 85 x 56 mm, M2.5 holes 58 x 49 mm | Official mechanical drawing |

## Before printing

1. Measure the stack depth and the tube or plate at the meter. Set `DispT` in the shell and `TubeD` in the bracket.
2. Check where the Pi 5 sits behind the display and move the vent slots over it. Their position is set in `1_back_shell.py`.
3. Print size: the shell (278 x 193 mm) does not fit a 256 x 256 mm bed, even placed diagonally. Print it on a 300 mm
   class printer, or split it into two halves joined with screw plates. The bracket prints on anything.
4. Use PETG or ASA. PLA softens in the sun.
5. Print the bracket first and test the rail fit. Its sliding clearance is `Slide` = 0.3 mm a side.

## Rebuilding

With SolidWorks open, run `python build/1_back_shell.py`, then `python build/2_bracket.py`. Each creates a new part and saves it here.
