# Analytics page: infinite vertical carousel (brief)

Written 7 Oct 2026 from the student's request: "focus on the analytics page, don't touch anything or break anything, just the analytics page. An upward-scrolling carousel, infinite, for the tabs: battery SOC, battery temp, ambient temp, odometer, battery output, consumption and all those. The comparison graphs (speed, battery %, distance and consumption against time) placed under one tab in the carousel; tapping it shows the graphs."

## Scope and rules

1. Only the Analytics page changes. One patch to `app/pages/analytics_page.py` plus a new module `sw7_analytics.py`; no other page, widget, theme or service is edited.
2. Keep the team's visual style: the carousel reuses the page's own gradient cards and charts, re-parented, in the team's palette. The student rejected the separate redesign (memory: dashboard look), so no new palette or font.
3. Nothing about the data changes. The six value cards and four charts are the team's existing widgets, still updated by the page's own `update_state` (with SW-7's live-only patch, so missing data shows "--"). The carousel only moves them.
4. Reversible: `TUKZIE_ANALYTICS_CAROUSEL=0` gives the original grid.
5. No made-up data in screenshots or tests presented as real.

## Behaviour

- Items, in order: Battery % (SOC), Battery temp, Ambient temp, Odometer, Battery output, Consumption, Graphs, Driver insights. The list wraps both ways (infinite).
- The current item is shown large in the middle; the previous and next items peek above and below, dimmed, so it is obvious the list continues.
- Upward scrolling: swiping up (or the down arrow, or the wheel) brings the next item up from below; swiping down goes back. A short swipe snaps back; the move is animated (about 0.25 s).
- Tapping the Graphs item opens the graphs view: the four time graphs in a 2 by 2 grid, larger than before, with a Back button that returns to the carousel at the same item. Tapping a peeking item scrolls to it.
- A column of dots on the right shows the position; up and down buttons for people who tap rather than swipe.
- No automatic scrolling (moving content on a driver display draws the eye); can be added later if wanted.

## Checks before deploying

- Offscreen test on a copy of the team's v1.1 with every patch: wrap-around both ways, swipe and tap, Graphs opens and Back returns, values still update through `update_state`, `TUKZIE_ANALYTICS_CAROUSEL=0` restores the grid.
- Both existing dashboard test suites still pass.
- Screenshots of the carousel and the graphs view, then deploy and look at the real screen.
