# Dashboard layout improvements (12 Oct 2026)

The student asked to act on `Planning/google-stitch-dashboard-prompt.md` now. The source for every change is section 1
(page by page) and section 2 (global rules) of that file. This brief splits the work between four agents. Each agent
works in its own git worktree and owns its own files, so their work can be merged without conflicts.

## Rules for every agent

1. Keep the team's look: the Electric Blue palette and fonts from theme.py, with the hex codes listed in section 2 of the Stitch file. The student rejected a restyle on 7 Oct. This work changes layout, hierarchy, sizes, spacing and touch targets only. Do not add new colours, a new font or a light theme.
2. Every change sits behind `TUKZIE_SW7_LAYOUT` (default on). `TUKZIE_SW7_LAYOUT=0` must give back exactly the current look, and a test must check this.
3. Change the dashboard only through our files in `DashboardIntegration/`:
   - SW-7 modules are installed by COPIES.
   - Edits to the team's files are patch entries in `tests/dashboard_patches.py`. The format is (file, exact anchor, replacement), and every anchor must occur exactly once in the patched source.
   - Add your entries as a new group named in your brief, and append that group to the end of the `PATCHES` line.
   - Never edit the team source in the scratchpad.
4. The team source to test against is `C:\Users\0geda\AppData\Local\Temp\claude\c--Users-0geda-OneDrive---University-of-Cape-Town-Documents-PlatformIO-Projects\02999ba8-77fc-45f7-8817-da26b024fcdd\scratchpad\v11c\Dashboard`. Set `TUKZIE_DASHBOARD_DIR` to it and `QT_QPA_PLATFORM=offscreen`.
5. Screen size is 1280 x 800, full screen, landscape.
6. Every existing test must still pass, and you report the output:
   - test_live_data_provider
   - test_tile_map
   - test_sim_sync
   - test_search
   - test_analytics_carousel
   - test_front_camera_page
7. Add a test for your pages. It must check sizes (tap targets at least 64 px; text and value sizes as given in the Stitch file), check the layout switch, and save before and after screenshots at 1280 x 800 into `tests/layout/<your area>/`. Look at the screenshots yourself and fix overlaps, clipping and text that does not fit.
8. Keep these as they are: the LIVE / REPLAY / NO DATA / SIMULATED distinction, the SIMULATED DRIVE strip, the obstacle pill top-right in the status bar, two-finger page swipe (three on the map), touch scrolling, voice guidance and the simulated-drive sync.
9. Commit on your worktree branch. Do not push, do not deploy, and add no co-author line.
10. Docs and comments: no em dashes, no unnecessary bold.

## Split

| Agent | Area | Owns | Patch group |
|---|---|---|---|
| A | Shared frame: status bar 48 px with 16 px text, nav bar with labels and 64 px targets, side arrows off the content; Settings (64 x 36 toggles, 64 px rows, two columns); Charging (one SOC figure, "5.8 of 7.2 kWh", the source row as a label) | the team's dashboard_main.py and its status/nav widgets, settings_page.py, charging page; new module `sw7_layout_frame.py` | `LAYOUT_FRAME_PATCHES` |
| B | Driving (speed 140 px whole number, range and battery 36 px under it, advice strip 64 px); Analytics (values 96 px, graph scales fitted to the data, readable axis labels and headings) | `sw7_driving.py`, `sw7_analytics.py`, the team's driving and analytics pages | `LAYOUT_DRIVE_PATCHES` |
| C | Diagnostics (four cards: Drive, Energy, Position, Link; the advice list folded away; duplicates of Sensors removed); Front camera (64 px alert rows with a band colour bar, status as a chip); Sensors (tuk-tuk outline with three 40 px distances, hazards beside it) | the team's diagnostics page, `front_camera_page.py`, `sensors_page.py` (except the HazardBanner placement) | `LAYOUT_PAGES_PATCHES` |
| D | Map: one column of 64 x 64 controls, turn banner anchored top-left, the SIMULATED label moved into the arrival-time bar | `sw7_tile_map.py` (keep the tilt view, the network circle, the touch fixes and the sim echo guard), navigation_page.py overlays | `LAYOUT_MAP_PATCHES` |

To avoid clashes:
- Only agent A changes the status bar and nav bar.
- Only agent C touches sensors_page.py.
- Agent D does not touch sw7_sim_link.py.
- If you need something from a file another agent owns, write it down in your final report instead of editing that file.
