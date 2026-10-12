# UI theme refinement (student brief, 12 Oct 2026)

The student's master prompt, pasted on 12 Oct, is summarised here; the reference is the current paper build
(`Presentation/mockups/paper_theme_all_pages.jpg`). Change the skin, not the product.

## Requirements
1. Keep everything: every page, every control, live data, maps and routing, the camera and hazards, settings,
   simulated drive, swipes, voice, the offline and no-data states. Only the styling changes.
2. Colour: warm ivory and paper, sand and stone for secondary surfaces, terracotta and copper only for active and
   selected states and key controls, deep charcoal text and dark surfaces, grey-brown secondary text, a restrained
   green for healthy, amber for warning, red for critical. Status must never be shown by colour alone.
3. Surfaces: open layouts, fine borders, hairline separators, small radii (4 to 8 px), very restrained shadows. No
   floating pills, no stack of rounded cards, no decorative gradients, no glass. Use a surface only where it groups
   information.
4. Typography:
   - IBM Plex Sans for the interface. IBM Plex Mono only for telemetry values, diagnostics, coordinates and
     timestamps. Both are bundled under the SIL Open Font Licence.
   - Prominent speed and range figures use a weight and spacing that read at a glance.
   - Clear hierarchy, tabular figures, no layout shift when digit counts change, little bold, no caps and wide
     tracking everywhere, no tiny low-contrast metadata.
5. Weather: no box, pill or border. A small icon, then the temperature and the place ("24° · Rondebosch") inline in
   the status bar, aligned with the other indicators. Dynamic data and the unavailable state are kept, and tapping
   it still opens the weather card.
6. Every page, light and dark:
   - Drive: the speedometer is the anchor. Refine the ticks, needle, labels, battery and range, next turn and the
     proximity figure.
   - Analytics: restrained charts with readable axes and units. No invented data.
   - Diagnostics: logical groups, and unavailable must never look like zero.
   - Map: the map dominates, overlays do not collide, and every control is kept.
   - Surroundings: warnings stay prominent, and overlays must read on both bright and dark frames.
   - Charging: explicit units; unavailable, zero, charging, not charging and unknown all shown distinctly.
     **Keep the team's battery animation (the bubbles and the spinning arc) and restyle it in the paper colours.**
     The paper pass had stopped it.
   - Settings: every control and its persistence kept; clear states.
   - Dark mode: designed as its own theme, not an inversion.
7. Navigation: the same destinations; the active page clear without heavy decoration; touch targets of at least
   64 px; the bottom bar must never cover content.
8. Validation:
   - All existing tests.
   - A new test covering the pages, the fonts loading, the unboxed weather, both themes and no clipping.
   - Before and after screenshots of every page in light and dark.
   - `TUKZIE_SW7_STYLE=team` must stay exactly as it is.

## Inventory (12 Oct, before the refinement)

Taken from the paper build (all 15 tests passing, screenshots `DashboardIntegration/tests/style/refine/before_*.png`,
day and night, and `before_team_*.png` for `TUKZIE_SW7_STYLE=team`).

Pages (nav order, ids in brackets):
1. Drive (`driving`): ASIS advice strip, gear and turn indicators, warning lamps, the speed dial (ticks, arc, the
   speed-limit and recommended-speed marks), the Next turn tile (mini map, opens Map), the Around tile (ToF left,
   ahead and right, opens Surroundings), the Range and battery tile (opens Charging), the interlock line.
2. Analytics (`analytics`): the infinite vertical carousel (odometer and the other value cards, Graphs card, insights),
   the graphs view with its four charts and Back, the dots and the up and down buttons.
3. Diagnostics (`diagnostics`): Controls, Health (with the "Outside (weather)" glance that opens the weather card),
   Position and Link cards, "Show advice and details" with the folded advice, route, voice and raw values list.
4. Map (`navigation`): the street-tile map (follow, overview, compass, zoom, optional 3D tilt), the turn banner,
   destination search with type-ahead and the touch keyboard, Navigate, the arrival bar (one ETA), Simulate drive and
   End simulation, the offline and "Waiting for GPS fix" states, the attribution.
5. Surroundings (`sensors`, aliases `camera` and `surroundings`): the camera frame and its status chip, the tuk-tuk
   with ToF distances, one combined hazards list nearest first, the nearest hazard as the hero, the sensors link chip,
   the Ride row.
6. Charging (`charging`): the battery ring (state of charge, stored energy, power, voltage, current, time to full,
   cell health), the team's battery animation (bubbles in the fluid and the spinning arc, stopped by the paper pass),
   the charge source line, the power-input chart, the Range, Range added and Energy delivered tiles, pack temperature.
7. Settings (`settings`): brightness, voice, voice speed, volume, Test voice, voice alerts, Repeat last warning,
   start-in-follow-mode, the LOOK swatches (Auto, Day, Night), Save, "Show advanced settings" and every advanced
   control, each persisted in the saved settings.

Shared components: the status bar (weather item, source chip LIVE / REPLAY / NO DATA / SIMULATED, battery percent and
icon, clock), the SIMULATED strip, the obstacle pill (opens Surroundings, Hide), the weather card, the nav bar
(7 items, labels), the side arrows, the two- and three-finger page swipe, touch scrolling, the back plane.

Features that must survive the refinement: live versus simulated versus no data on every page; simulated-drive sync;
voice guidance and voice alerts; destination search and recents; follow, overview and tilt on the map; the camera
streaming only while Surroundings is shown; the weather service, its cache, its unavailable state and the day and
night switch at sunrise and sunset; every setting and its persistence; `TUKZIE_SW7_STYLE=team` exactly as it is
(recorded in `tests/style/refine/team_reference.json`).
