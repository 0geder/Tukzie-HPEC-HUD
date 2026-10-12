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
