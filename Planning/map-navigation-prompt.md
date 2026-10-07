# Map: navigation that looks and moves like Google Maps (brief)

Written 7 Oct 2026 from the student's request: "can we have the map pick up similar to Google Maps when doing
navigation and have it move like that".

## Scope and rules

1. Only our map widget changes (`DashboardIntegration/sw7_tile_map.py`, the street-tile map that replaces the
   team's map). The team's Navigation page layout, route list and search bar are not edited.
2. The student rejected the separate redesign, so new elements follow navigation-app conventions without restyling
   the dashboard, and screenshots are shown before anything is deployed (memory: dashboard look).
3. No invented data. Turn instructions are derived from the route the team's planner returns; distances and times
   come from the route and the real or clearly labelled simulated position.
4. Tested offscreen with the existing map tests before deploying.

## What "like Google Maps" means here

- Turn banner at the top of the map: a turn arrow, the distance to the turn ("150 m"), and the instruction
  ("Turn left onto Baxter Avenue"), with the following instruction underneath ("Then: slight right onto Main Road").
  At the end: "Arrive at destination".
- Bottom strip: time left, distance left, and arrival clock time.
- Camera: heading-up, the vehicle low in the view so more road ahead is visible (already 70 % of the height), zooming
  in as a turn approaches and back out after it.
- The route ahead drawn bold, the driven part greyed (already in place).

## How the turns are found

The team's planner gives route points with the road name and distance along the route; its online request has
turn-by-turn steps switched off. A manoeuvre is placed where the road name changes. The turn type comes from the
change in bearing, measured over about 20 m before and after that point:
under 20 degrees "Continue onto", 20 to 45 "Slight left/right", 45 to 135 "Turn left/right", over 135 "U-turn".
The distance to the next manoeuvre is measured along the route from the vehicle's position projected onto the route
(real fix, or the simulated drive).

## Later, if wanted

- A tilted, three-dimensional view (QPainter perspective transform); to be tried only if the Raspberry Pi 5 keeps
  its frame rate.
- Spoken turn instructions through the dashboard's voice engine (needs the speaker).
