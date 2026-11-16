# Poster v5 prompt (16 Nov 2026)

Rework the A1 portrait poster (Presentation/source/build_poster.js -> Presentation/SW7_Poster_A1.pptx) so that a visitor who
looks at it for a minute sees the whole project: what the trike is, what was missing, what was built, how the parts connect,
how the work was planned and tested, and what the road test showed.

## Model: the EcoBot E-poster (Downloads/Main Assignment - E-poster for UCT Open Day Project.pdf, 2024)

What it does well, and what to carry over:

- Every section is a picture, not a paragraph: Background is three circle photos each with a short callout; the scope is three
  labelled chevrons (description, requirements, business needs); the WBS is a flow of circles with arrows; the schedule is a
  Gantt chart; risks are hexagon pairs. Text is short and sits inside shapes.
- The planning is visible: phases, schedule and how risk was handled are shown, not only results.
- One hero picture of the product with a three-line summary.
- References at the foot.

What not to copy: the dark busy background, many fonts and colours, small text (body under 24 pt at A1 fails the 2 m rule).

## Content, by section (every fact from the report or the tuksense.site stage dates)

1. Background: three circle photos with callouts: the TUKZIE trike and its dashboard; nothing measured the ride or warned
   the driver; the brief, and the HUD replaced by dashboard alerts (agreed 1 to 2 Oct).
2. Scope statement as chevrons: Aim (measure vibration front and rear with IMUs; warn the driver with front and rear cameras on
   the trike's own dashboard; keep every record when the network drops), Requirements (13, pass marks set before testing,
   grouped by subsystem), Constraints (removable, no drilling; no test participants; low speed on campus).
3. System on the trike: a block diagram with four subsystems in four colours, equal weight so no part outshines another:
   ride sensing (two IMU nodes, 200 Hz), hazard detection (two cameras, ToF), telemetry (BMS over BLE, GNSS, LTE store and
   forward), driver display (Pi 5 dashboard). Front Pi 5 and rear Pi 4 joined by Ethernet. Small photos tagged in the same colours.
4. Method and plan: phase flow (requirements, bench, enclosures, road test 1 on 19 Oct, road test 2 on 27 Oct, analysis) and a
   Gantt from late July to 27 October using the site's stage dates.
5. Road test results: the IMU trace and the result tiles, each tile coloured by its subsystem.
6. Requirements scorecard: R1 to R13 as chips grouped by subsystem, coloured met / partly met / not tested (5 / 7 / 1).
7. Limits and next steps as pairs (what limited it, what comes next).
8. Conclusion with the QR code to tuksense.site.
9. References strip: ISO 2631-1, ISO 15008, NHTSA 2013.

## Rules

- Check the .pptx for manual edits before rebuilding; back up v4.
- Body text 26 to 28 pt, nothing under 24 pt. No em dashes, no unnecessary bold.
- Keep the UCT crest, supervisors and the faint TUKZIE render background.
- Render to PNG and check every panel for overflow before handing over; then PDF, commit and push.
