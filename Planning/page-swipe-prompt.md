# Multi-finger swipe between dashboard pages (brief)

Written 11 Oct 2026 from the student's request: "move through the pages by using two fingers to swipe through the
pages like a carousel from left to right ... in the map area two fingers zoom, so moving to another page from the
map page one should use three fingers".

## Behaviour

Revised the same day after the first version flipped a page when two fingers merely rested on the screen
("it has to be smooth ... some decorum please"): the change now follows the fingers and is decided on release.

- Nothing happens until the fingers move sideways together: every finger the same way, mostly horizontal, past
  about 30 px. Holding, resting a hand, a pinch or a vertical move never moves a page.
- While dragging, the current page follows the fingers and the neighbouring page slides in beside it.
- On lifting, the page changes only if the drag passed a third of the width or ended in a quick flick the same
  way; otherwise it springs back. Both settle in about 0.2 s.
- Swipe left for the next page and right for the previous one, in the same order and wrap-around as the
  dashboard's own left and right arrows (dashboard_main normal_ids).
- On the map itself, two fingers keep zooming and panning the map; three fingers swipe pages. Elsewhere on the
  Navigation page (search bar, buttons) two fingers swipe as on any page.
- The map ignores three-finger touches (no zoom or pan jump while swiping).
- One-finger gestures are untouched: scrolling, the Analytics carousel's vertical swipe, taps, the map's drag.
- One page change per gesture; nothing happens on the start-up and PIN screens.
- A short slide (about 0.22 s) shows the old page leaving in the swipe direction, like a carousel.

## How

- One event filter on the application that reads touch events at the window, before the widgets, and never
  consumes them, so every widget behaves exactly as before.
- New module DashboardIntegration/sw7_page_swipe.py, installed with the other SW-7 modules after the dashboard is
  built; a small change in sw7_tile_map's touch handler for three or more fingers.

## Tests and rules

- Offscreen tests with synthetic touch: two-finger swipe left and right on a normal page changes page both ways;
  two fingers on the map zoom and do not change page; three fingers on the map change page and do not zoom; one
  finger changes nothing; existing suites pass.
- No restyle, no layout change. Committed, pushed and deployed after the tests pass.
