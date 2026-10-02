# Dashboard map crash on the Pi 5: diagnosis (2 Oct 2026)

Done over SSH on the dashboard's Raspberry Pi 5 (`Pirate5`, user `piadam`), read-only: test scripts ran from /tmp in separate processes and were removed afterwards; the running dashboard, its files and its saved settings were not changed.

## System
- Debian 13 (trixie), aarch64, 16 GB RAM, kernel page size 16384 bytes.
- Installed dashboard: `~/Dashboard` is v1.1 (newer than the v1.0-validated copy our integration patches were written against). PySide6 6.11.1 in `~/tukzie-env`. Started by `~/start_dashboard.sh` (X11, DISPLAY=:0), log `~/dashboard_boot.log`.
- The boot log shows the dashboard starting four times on 2 Oct (13:57, 13:59, 15:25, 16:00) with no error lines, consistent with a native crash that kills the process before Python can log.

## Tests
| Test | Result |
|---|---|
| Plain QWebEngineView, offscreen, dashboard's Chromium flags and without --disable-software-rasterizer | loads, exits normally |
| Plain QWebEngineView on the real display (DISPLAY=:0) | loads, exits normally |
| QWebEngineView inside a QStackedWidget under a translucent overlay, AA_ShareOpenGLContexts, real display | survives |
| Second dashboard instance offscreen, switch to navigation | survives (map page ready, tiles stay "loading") |
| Second dashboard instance on the real display, map display "OpenStreetMap" | segmentation fault about 2 s after the dashboard is shown |
| Same, map display "Offline roads" (still the web map) | segmentation fault, same timing |
| Same, map display "Native fallback" | no crash; map page shown and alive after 30 s (harmless JS errors: "Cannot read properties of null (reading 'getCenter')") |

## Conclusions
1. The web engine itself works on this Pi, and neither the 16 KB page size nor the Chromium flags alone cause the crash.
2. The crash comes from the dashboard's Leaflet web map when rendered on the real display, whether its data is online or offline. It can happen as soon as the dashboard is shown, because the web map is created and starts rendering in the background (navigation_page.py line 117 calls _create_web_map at construction).
3. A native crash cannot be caught by the page's Python try/except fallback, so it takes the whole dashboard down.

## Workaround (no code change)
Settings > Navigation > Map display: Native fallback. Applies and saves immediately.

## Proposed fixes for the dashboard team (not applied)
1. Create the web map lazily, only when the map page is first shown and the display mode is not "Native fallback", so the native mode never starts the web engine.
2. Probe the web map in a throwaway subprocess at startup (load the same Leaflet page on the real display for a few seconds); if it crashes, force the native map for the session. The dashboard can then never be taken down by the map.
3. Narrow the root cause further: load the Leaflet HTML alone in a QWebEngineView on the display; then disable the page's JavaScript updates (vehicle marker, status polling) one at a time.
