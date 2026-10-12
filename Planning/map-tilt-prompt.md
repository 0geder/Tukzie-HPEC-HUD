# Map: tilted 3D driving view like Google Maps on CarPlay (brief)

Written 12 Oct 2026 from the student's question: can our map move like Google Maps on Apple CarPlay while driving,
heading-up, tilted so the road ahead recedes toward the horizon, the arrow in the lower third, smooth rotation and
panning.

## Scope and rules

1. Only our map widget changes (`DashboardIntegration/sw7_tile_map.py`). No dashboard_patches.py edits are needed:
   the file is already copied into app/pages/.
2. The student rejected the earlier restyle, so this is a behaviour feature that is off by default. Nothing changes
   unless `TUKZIE_MAP_TILT=1` is set. With the flag, a small "3D" button sits above the existing +/- zoom buttons,
   styled like them, and toggles between the tilted and the flat view (the map starts tilted).
3. Screenshots (flat vs tilted, during the simulated drive) are shown to the student before anything is deployed.
   No deploy to the Pi and no commit from this task.

## Approach

- The flat heading-up world transform (translate, rotate, scale) is followed by a perspective transform: the exact
  pinhole homography of a camera pitched TILT_DEG (50 deg) from straight down, looking at the vehicle. It is a
  projective QTransform (the same matrix QTransform.quadToQuad would give for the rectangle-to-trapezoid mapping),
  so tiles, the route polyline and every marker position go through one matrix and line up exactly.
- Tiles are drawn straight through that transform (one pass over the screen pixels, no extra offscreen copy). Only
  tiles inside the ground area seen by the camera are requested, as before (no prefetching), and the ground is cut
  off TILT_FAR_PX ahead; above that a band in the theme's background colour fades into the map, where the horizon
  would be. This keeps the tile count and paint time bounded.
- The vehicle arrow is drawn upright after the transform, at 72 % of the height (low in the view; 78 % was
  tried first but put the arrow under the ETA card at 1024 px wide). The destination pin
  and labels are drawn only where they are on the visible ground.
- The tilt eases in and out (about 0.5 s), so switching, or leaving follow mode for the overview, is smooth.
  Overview is flat and north-up. Dragging keeps the tilt it had; drags and taps are converted back to the map through
  the inverse transform, with points above the horizon clamped to the ground.
- Speed-based zoom: not done in this pass (it would fight the manual zoom and the near-turn zoom).

## Acceptance tests (test_tile_map.py, section 12)

1. Without the flag: no 3D button, tilt off, transform affine; all earlier tests unchanged.
2. With the flag: button visible and checked, transform projective, vehicle at 72 % height, a point ahead appears
   above the vehicle and nearer the centre line than in the flat view (foreshortening), the route vertices map to the
   same screen points as the painted route (same matrix), and screen to map round trips within 0.5 px.
3. A tap or drag point is mapped back through the inverse transform to the same map point.
4. The 3D button toggles flat and tilted; overview goes flat; follow again goes tilted.
5. Paint time at 1024x600 offscreen with tiles in memory, tilted, measured over 40 frames: target under 15 ms on the
   laptop; the number is printed.
6. Screenshots saved: tests/tile_map_flat_drive.png and tests/tile_map_tilt_drive.png (simulated drive), and copies
   in Presentation/mockups/.
7. test_sim_sync.py, test_search.py and test_live_data_provider.py still pass.

## Result (12 Oct 2026, offscreen, not yet on the Pi)

All of the above pass. Paint at 1024x600 with tiles in memory: tilted median 8.0 ms (p90 11.8 ms), flat 5.6 ms.
Up to 65 tiles are visible when tilted (about 20 flat). Mock-ups with real OSM tiles in Presentation/mockups/
(map_tilt_3d_drive_1/2.png, map_flat_2d_drive_1/2.png) for the student to approve before any deployment.
