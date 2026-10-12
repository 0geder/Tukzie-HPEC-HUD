# Three planes with hero type and the TUKZIE vehicle (student brief, 12 Oct 2026, evening)

The student's words: "I want us to go in three planes, big type in the back, subjects in the middle, like what the guy
is saying and that theme, and have the battery thingy like the one in the screenshot. Also have the tuk-tuk in the
picture like the new_tukzie pictures in the folder Projects."

The reference is a product poster (AURA headphones):
- Back plane: a huge, heavy word filling the width, set tight and dark on a light ground.
- Middle plane: the product photo in front of the word, overlapping the middle of the letters, so the word reads
  through behind it.
- Top plane: small UI on top of both, in the corners and along the bottom.

The depth comes from the overlap.

This builds on the refined paper theme deployed today (`Planning/ui-theme-refinement-prompt.md`, commit 5baa5f2).
Keep:
- IBM Plex type for the interface and for readings;
- the unboxed weather;
- the flat navigation bar;
- status shown in words as well as colour;
- one tap colour;
- every feature and the test suite.

The refinement removed the back-plane words. The student now wants them back, bigger and bolder, in a disciplined way.

## What to build

1. Back plane: huge type.
   - One word per page, set very heavy and condensed:
     - DRIVE
     - STATS (Analytics)
     - SYSTEM (Diagnostics)
     - MAP
     - AROUND (Surroundings)
     - CHARGE
     - SETUP (Settings)

     A wordmark such as TUKZIE may be used where it reads better.
   - Bundle an OFL display face for it, such as IBM Plex Sans Condensed Bold, Archivo Black, Anton or Bebas Neue.
     Check its licence and add it to COPIES.
   - The word spans roughly the page width, sits behind the subject, and is clipped by the screen edges where needed.
   - Colour: paper_deep by day, a lifted charcoal at night. It must never compete with data: driving values stay
     ink on top.
   - Draw it from a cached pixmap; it must not repaint every frame.
2. Middle plane: the subject.
   - Use the student's TUKZIE concept renders: `Projects/new_tukzie_three_quarter_front.png`,
     `new_tukzie_front.png` and `new_tukzie_side.png`.
   - Cut each one out of its white background with a clean alpha edge and a soft contact shadow. Save the results as
     `DashboardIntegration/assets/tukzie_*.png` (added to COPIES).
   - Place them so they overlap the hero word:
     - Drive: the three-quarter render beside or under the speed, with the tiles still readable.
     - Charging: the battery graphic below.
     - Diagnostics or Surroundings: the side or front view where it helps.
     - Map: the map is its own subject; no vehicle picture there.
   - Never cover a value the driver needs. Keep it cheap to paint on the Pi 5: cached and scaled once.
3. Top plane: the controls.
   - The existing tiles, values and buttons stay on top, with their hairlines and light shadows.
   - Where a tile overlaps the vehicle or the word, it stays legible: a paper card with a light shadow.
4. Charging: the team's battery graphic (`Planning/reference_team_charging_page.jpg`).
   - Bring back the composition of the team's original Charging page:
     - the vehicle outline seen from above, filled with rising bubbles to the state-of-charge level;
     - the ring arc around it;
     - the big percentage above it;
     - the readings placed around the ring (power input, voltage, current, charging state, estimated time to full,
       cell health).
   - Restyle it in the paper and ink palette, with no neon. The fill and bubbles are ink or ok-green by state of
     charge, and the arc is ink with the tap colour only if it is interactive.
   - Keep the animation running at 30 fps only while the page is visible.
   - Unavailable values show "--". Cell health shows "--" until real data exists: no made-up 98 %.
5. Keep the live, replay, no-data and simulated states, and the obstacle pill. Night mode must get the same three
   planes.

## Checks

- All 14 dashboard tests, plus test_style_refine, must pass. Extend it, or add tests/test_style_planes.py, to check:
  - the hero word is present and behind the subject on each page;
  - the subject images load, with alpha;
  - no driving value is covered: test the bounding boxes of the values against the vehicle image and the word;
  - the Charging animation runs.
- Screenshots of every page, day and night, at 1280 x 800, in `tests/style/planes/`. Look at them and fix crowding.
- Paint time on the laptop must stay under 15 ms per frame.
- `TUKZIE_SW7_STYLE=team` must be unchanged.
- No deploy. The student approves the screenshots first.
