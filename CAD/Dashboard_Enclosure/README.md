# Dashboard display enclosure and handlebar mount

Status (12 Oct 2026): third model, not printed. Built in SolidWorks 2025 through its API by the scripts in `build/`.
Every key size is a global variable (Tools > Equations) or a named constant at the top of a script, so a new
measurement is one number to change. Every printed part fits the Prusa Mini (180 x 180 x 180 mm).

The display is a Waveshare 10.1" HDMI LCD (B) in its stock case, measured at 272 x 187 mm (see
`../reference_dimensions.md`). `SW7_Dash_Assembly.SLDASM` shows everything fitted to a dummy 22.2 mm handlebar,
with a dummy display and a dummy Pi 5 (`reference_parts/`, not printed). Pictures are in `previews/`.

## How it goes on the tuk-tuk

1. The bar clamp (bracket and cap) is bolted to the middle of the handlebar with two M5 bolts, over a 1 mm rubber
   strip. It stays on the vehicle. Before tightening, turn it around the bar to tilt the screen towards the driver.
2. The display slides down onto the clamp: the dovetail rail on its back goes into the bracket's channel.
3. Turn the M4 thumb screw up from under the bracket until it drops into the rail's detent.
4. To take the display off, loosen the thumb screw and lift the display upwards.

The rail is low on the back of the display, so the screen stands above the handlebar the way a phone mount does.
The bar sits about 37 mm above the display's bottom edge, and about 150 mm of screen is above it.

Why it cannot fall off:
- The channel is closed at its bottom end, so the display's weight sits on a solid stop.
- The thumb screw sits in a detent in the rail, so the display cannot lift out over bumps (a positive lock, not friction).
- The clamp grips the bar with two M5 bolts and a rubber strip. The two halves keep a 1.5 mm squeeze gap, so the bolt load goes into the bar, not into the clamp faces, and it neither slides along the bar nor swings round it.
- The dovetail only lets the display move straight up, against both of these.
- As a backup on the road test, loop a cable tie through the bracket's channel end and round the bar.

## Parts

| Part | Size (mm) | Print | What it does |
|---|---|---|---|
| print_parts/SW7_Dash_Shell_Q_Left_Top, Left_Bottom, Right_Top, Right_Bottom | 139.1 x 96.6 x 27 each | 1 of each | The four quarters of the back shell. The display presses in from the front past 1.2 mm snap lips on the long walls. 24 mm deep inside. |
| print_parts/SW7_Dash_Rail_Plate.SLDPRT | 120 x 74 x 4, rail 6 high | 1 | Low on the back (Z 22 to 96, clear of the cross joiner), eight M3. Carries the dovetail rail (30 to 38 mm wide, 72 mm long, two lock detents) and joins the two bottom quarters. |
| print_parts/SW7_Dash_Cross_Joiner.SLDPRT | 40 x 40 x 3 | 1 | At the centre, one M3 into each quarter |
| print_parts/SW7_Dash_Joiner_Plate.SLDPRT | 44 x 20 x 3 | 2 | Across the top of the vertical joint and the right of the horizontal joint, two M3 each |
| print_parts/SW7_Dash_Pi5_Cradle.SLDPRT | 66 x 95 x 10 | 1 | Holds the Raspberry Pi 5 on the back, on the left (the display's connector side). Four M3 through the shell, two either side of the joint, so it also joins the two left quarters. The Pi screws to four 7 mm standoffs (M2.5 x 6), components out, USB and Ethernet end down. A notch marks the USB end. |
| SW7_Dash_Bracket.SLDPRT | 56 x 80 x 29 | 1 | Dovetail channel on top (closed at the bottom end, 0.35 mm parallel clearance), M4 lock insert underneath, and the upper half of the bar clamp (52 mm across the bar) with two M5 heat-set inserts, 10 mm blind |
| SW7_Dash_Clamp_Cap.SLDPRT | 40 x 52 x 16 | 1 | Lower half of the bar clamp, 4.9 mm under the bore, two M5 clearance holes |
| SW7_Dash_Back_Shell.SLDPRT | 278.2 x 193.2 x 27 | Do not print | Master the quarters are cut from |

Hardware (revision 2, from the engineering review):
- 20 M3 ISO 7380 button-head bolts with nyloc nuts. Put the heads inside the shell, which leaves 2.5 mm behind the
  display, and the nuts outside. M3 x 12 for the 8 rail plate bolts; M3 x 10 for the joiners, the cross joiner and the
  cradle. Fit them before the display goes in.
- 4 M2.5 x 6 screws for the Pi, hand tight.
- 2 M5 x 30 socket head bolts with washers, and 2 M5 heat-set inserts.
- 1 M4 heat-set insert and 1 M4 thumb screw for the lock.
- A strip of bicycle inner tube for the bar.
- 2 to 3 mm closed-cell foam on the back plate, to take up the display's depth and damp vibration.
- Epoxy or CA glue for the quarter walls where they butt together.

Layout, seen from the driver (+X is the driver's right, so the connector side is -X):
- The cable exit, 58 x 16 mm, is in the left-hand short wall. The connectors span 43 to 45 mm (measured), plus room for
  the plug bodies. The display's HDMI, USB and power plugs come out on that side (photo
  `Photos/Reference/Enclosures/2026-10-12_display_on_desk_cables_left.jpg`).
- Vent slots are in two rows near the left-hand side.
- The Pi 5 sits on the left of the back, 10 mm above centre. Its USB end is 13 mm clear of the handlebar. Screws hold the
  Pi rather than clips, because the vehicle shakes and clips on a 1.6 mm board work loose.

## Numbers used

| Value | Source |
|---|---|
| Display outer 272 x 187 mm | Measured tight by the student on 12 Oct. The Waveshare drawing gives 274.12 x 187.00. The pocket is 0.6 mm larger each side. |
| Display depth 20 mm (`DispT`) | Student's estimate. Waveshare gives 18 mm for the display in its case, without the Pi. The Pi is now outside the shell. |
| Connector span 43 to 45 mm | Measured by the student |
| Handlebar 22.2 mm (`TubeD`, bracket) | Standard 7/8 in motorcycle bar. Not yet measured on the tuk-tuk; some bars are 25.4 mm. |
| Meter area about 30.5 cm across | Tape photo, 2 Sep 2026. The 278 mm shell fits if the plugs are right-angled (straight plugs add 4 to 5 cm on the left). |
| Raspberry Pi 5: 85 x 56 mm, M2.5 holes 58 x 49 mm, 3.5 mm from the edges | Official mechanical drawing |

## Before printing

1. Measure the handlebar where the clamp will go: its diameter, and at least 45 mm of straight bar, clear of the
   switch housings and cables. Set `TubeD` in `build/2_bracket.py`.
2. Check the display depth and set `DispT` in `build/1_back_shell.py`.
3. Use right-angle HDMI and USB adapters on the display's left side.
4. Print the bracket and rail plate first and test the slide. The clearance is `Slide` = 0.3 mm a side.
5. Use PETG or ASA. PLA softens in the sun. Print the quarters open side up, the bracket with the clamp face on the bed,
   and the cap flat.

## Reviews

`ENGINEERING_REVIEW.md` has the full audit: the defect register, the checks run with their evidence, and the
revision 2 corrections. Audit scripts are in `build/audit_*.py`. The build scripts are the source of truth: most sketches
are not dimensioned in SolidWorks.

## Rebuilding

With SolidWorks open, run these in order. The bolt layout lives in `1_back_shell.py` and the other scripts read it from there.
1. `python build/1_back_shell.py`: master shell
2. `python build/2_bracket.py`: bracket and clamp cap
3. `python build/3_split_and_plates.py`: quarters, rail plate and joiners
4. `python build/4_pi5_cradle.py`: Pi 5 cradle
5. `python build/5_assembly.py`: reference parts and the assembly
