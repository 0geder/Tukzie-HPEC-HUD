# Engineering review: IMU pod (GY-521 / MPU-6050)

Reviewed 12 Oct 2026 on the saved SolidWorks 2025 parts `SW7_IMU_Pod_Base.SLDPRT` and `SW7_IMU_Pod_Lid.SLDPRT`
(commit 8534cb5). No geometry was changed in this pass. Results come from `build/audit_imu.py` and from
`../Dashboard_Enclosure/build/audit_4_walls.py` run on these two files, or from arithmetic on the build-script
parameters where stated. Nothing has been printed or tested.

Acceptance classification: PROTOTYPE-READY, on two conditions: measure the GY-521 hole spacing and offset before
printing (they are unverified, and changing them needs a script rerun, see I2), and use M2.5 x 6 lid screws (I1).
No critical or major defect was found. The part is small and cheap, so a first print is the quickest way to check
the board fit.

## 1. Design overview

| Item | What it is | Saved size (mm) |
|---|---|---|
| Base | 44 x 30 x 12 block. Board pocket 21.2 x 18.2 x 5 deep (measured 20 x 17 board + 0.6 a side), floor at Y 7. Two board pilot holes 2.2 mm, 15.2 apart, 5.6 off centre, 4 mm deep below the floor. Four lid pilot holes 2.2 mm at X +/-18, Z +/-11, 8 mm deep. Cable exit 8 wide x 3.5 deep in the +X end. Two strap tunnels 6 x 3.5 through the width at X +/-13, 1.5 mm above the bottom. | 44 x 12 x 30 |
| Lid | 2 mm plate, four 2.9 mm clearance holes, forward arrow engraved 0.6 deep pointing +X | 44 x 2 x 30 |

Frame: X is vehicle forward (arrow), Y up (base bottom at Y 0, top at Y 12), Z across.

## 2. Defect register

| ID | Component | Location | Problem (measured unless stated) | Why it matters | Proposed correction | Severity |
|---|---|---|---|---|---|---|
| I1 | Base | Lid pilot holes next to the strap tunnels | The lid pilot holes run from Y 12 down to Y 4; the strap tunnels reach up to Y 5. Between Y 4 and 5 the wall from each hole to the tunnel side is 0.90 mm (audit 4). | A self-tapping M2.5 that reaches the bottom of the hole (M2.5 x 8 or longer through the 2 mm lid) will burst into the tunnel. | Shorten the lid pilot holes to 6 mm (bottom at Y 6, 1 mm above the tunnel roof) and specify M2.5 x 6 lid screws (4 mm engagement). | Moderate |
| I2 | Base | Board pilot holes | Spacing 15.2 and offset 5.6 are unverified. The hole sketch is under defined with one dimension and is not linked to the `HoleSpacing` or `HoleOffset` globals (no equation references them), so editing the globals in SolidWorks does not move the holes. | If the real spacing differs, the board cannot be screwed down and the fix is not a one-number change. | Measure: outer edge to outer edge of the two holes minus one hole diameter. Then either edit `2_base_features.py` and rebuild, or add two dimensions in the sketch linked to `HoleSpacing` and `HoleOffset`. Because the holes are only on one edge (Z -5.6), the board can only be screwed down one way round, which keys the IMU axes to the arrow, provided the positions are right. | Moderate |
| I3 | Base and lid | Parametric links | `PodH` drives only the "Pod Top" plane, not the body extrusion (no equation on the boss depth). `StrapX`, `StrapW`, `StrapT`, `StrapZ0`, `CableW`, `LidInset`, `PilotD`, `FloorHoleD` (for the lid holes) are globals that nothing references. The strap slot sketch has 0 dimensions, although the docstring of `3_strap_slots_and_save.py` says it is dimensioned and linked. The lid's `LidInset` and `ClearD` are not linked either, and base and lid keep separate copies of `PodL` and `PodW`. | Changing a global in Tools > Equations either does nothing or, for `PodH`, breaks the part (the top plane moves away from the top face). | Treat the scripts as the source of truth, or link the dimensions in the scripts as was done for the pocket. Correct the docstring. | Moderate |
| I4 | Base | Board retention | The board is held by two screws along one edge; the opposite edge is free. Space between the board top (Y 8.6) and the lid underside (Y 12) is 3.4 mm (arithmetic). | The free edge can flap at road-vibration frequencies and add noise to the IMU signal; the MPU-6050 measures its own board's motion. | A 3 mm foam pad (or a 2.5 mm rib on the lid underside plus 1 mm foam) pressing on the free edge, clear of the MPU-6050 chip. | Moderate |
| I5 | Base | Header pins | 3.4 mm above the board and 0.6 mm clearance at the sides (arithmetic). A straight 2.54 mm header (about 8.5 mm tall) or a right-angle header (about 6 mm out from the edge) does not fit. | The board as usually sold (header loose or soldered) will not go in. | State in the README: no header, wires soldered straight to the pads and routed over the board to the +X cable exit (exit floor at Y 8.5, board top at 8.6, so the wires lie flat). | Moderate |
| I6 | Base | Board pilot holes next to the strap tunnels | 1.30 mm wall between each board pilot hole and the inner side of the tunnel, between Y 3 and 5 (audit 4). | Acceptable for a 1.6 mm board screw that only reaches Y 3.4 (see I9) with light torque; less margin if a longer screw is used. | Keep the board screws short (I9), or move the tunnels to X +/-14 (needs I1 first). | Minor |
| I7 | Base | Mounting | Cable ties through the 6 x 3.5 tunnels alone; 1.5 mm floor under each tunnel (audit 4); square tunnel edges. | Ties allow the pod to rock on a curved or rough surface, which shows up as false vibration in the data; sharp edges can cut ties. | Add VHB double-sided foam tape under the base as well as the ties; 0.5 mm chamfer on the tunnel edges. | Minor |
| I8 | Base and lid | Sealing | Open cable exit, flat lid with no lip or gasket. | Dust and rain on an open vehicle. | A 1 mm foam gasket under the lid, a dab of silicone at the cable exit, and a cable tie anchor for strain relief. | Minor |
| I9 | Base | Board screw length | Pilots go 4 mm below the floor: board 1.6 + 4 = 5.6 mm available. | An M2.5 x 6 bottoms out. | Specify M2.5 x 5 for the board. | Minor |
| I10 | Build scripts | Rebuild path | Steps 2 and 3 work on whatever document is active; step 3 deletes a feature by its default name (`Cut-Extrude5`) made by step 2; step 1 does not save. | A rebuild out of order, or with another document active, gives a wrong part silently. | Merge steps 1 to 3 into one script that creates, builds and saves the base, as the lid script does. | Minor |

## 3. Load path and vibration (assessment, not tested)

The pod carries only a 2 to 3 g board, so strength is not the issue; stiffness of the mounting is. The board's
two screws, the pod's own rigidity (a 44 x 30 x 12 PETG block) and above all the strap or tape joint to the vehicle
decide whether the sensor sees the vehicle's motion or the pod's. Cable ties alone leave the pod free to rock (I7).
A physical check is needed: log the IMU with the pod strapped, then with ties plus VHB tape, on the same stretch,
and compare the high-frequency content.

## 4. Checks performed and results

| Check | How | Result |
|---|---|---|
| Probe proof for interference | `audit_imu.py`: temporary assembly (not saved), a second lid pushed 1 mm into the base | DETECTED: 816.5 mm3 with the base (and 1245.9 mm3 with the first lid). The check reports real overlaps. |
| Interference, lid on base | Same temporary assembly, lid at Y 12 | No hard interference. With touching counted, the lid and base touch (contact on the top face), as intended. |
| Lid screws coaxial | `audit_imu.py`: lid clearance holes (r 1.45) against base pilots (r 1.1), read from the saved parts | 4 of 4 coaxial within 0.05 mm. |
| Body count and validity | `GetBodies2`, `IBody2.Check3` | One body each, 0 faults. |
| Bed fit | Part boxes | Base 44 x 12 x 30, lid 44 x 2 x 30: fit the 180 mm cube. |
| Pocket size | Upward planar faces | Pocket floor 21.2 x 18.2 at Y 7 (5 deep), matching 20 x 17 + 0.6 a side. |
| Thin walls | `audit_4_walls.py` (non-adjacent face pairs, material only) | 0.90 mm lid pilot to tunnel (I1), 1.30 mm board pilot to tunnel (I6), 1.50 mm tunnel floor, 2.0 mm pocket floor over the tunnels, 1.40 mm lid under the engraved arrow. |
| Sketch definition | `ISketch.GetConstrainedStatus` and dimensions per sketch | Base: Sketch1 (outline) and Sketch2 (pocket) fully defined; pilot holes, lid holes and cable exit under defined with 1 dimension each; strap slots under defined with 0. Lid: outline fully defined; holes and arrow under defined with 1 dimension each. |
| Equations | Read from both parts | See I2 and I3. |
| Overhangs | By inspection of the face list (the dashboard overhang script was not run on these parts) | Base printed bottom down: the only overhangs are the strap tunnel roofs, 6 mm bridges, which print without support. Lid flat: none. |

## 5. Checks not performed

- The GY-521 hole spacing and offset against a real board (no measurement available, I2).
- A physical fit of the board, wires and lid; the vibration comparison in section 3.
- FEA (not useful for a 3 g load).
- Sealing or temperature behaviour.
- The scripted overhang check (`audit_3_parts.py`) was not run on these two parts; the overhang row above is by
  inspection.

## 6. Print plan

| Part | Qty per pod | Material | Orientation | Supports | Notes |
|---|---|---|---|---|---|
| Base | 1 | PETG (ASA if mounted in sun) | Bottom on the bed, pocket up | None (6 mm tunnel bridges) | 4 perimeters so the pilot holes are solid wall |
| Lid | 1 | PETG or ASA | Flat, arrow up | None | |

## 7. Assembly sequence

1. Solder the four wires (VCC, GND, SCL, SDA, plus INT if used) straight to the GY-521 pads, no header (I5).
2. Lay the board in the pocket with its holes over the two pilots (only one way round fits the screws), wires
   over the board to the +X exit. Two M2.5 x 5 self-tapping screws, hand tight.
3. Foam pad on the board's free edge (I4), lid on with the arrow pointing forward, four M2.5 x 6 (I1).
4. On the vehicle: VHB tape under the base, cable ties through both tunnels, arrow pointing forward.
