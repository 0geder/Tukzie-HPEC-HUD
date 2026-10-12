# SW-7 add-ons for the TUKZIE dashboard

Add-ons for the vehicle dashboard (PySide6, the dashboard team's
`Tukzie-Vac-Work-2026/Dashboard Team/Tukzie-Dashboard/v1.0-validated`):

| File | Goes to | What it does |
|---|---|---|
| `front_camera_page.py` | `app/pages/` | Front camera page: live view and hazard alerts from the Pi 4 detector |
| `live_data_provider.py` | `app/data/` | Polls the Pi 4 telemetry bridge and feeds real values into the dashboard state |
| `ride_quality_card.py` | `app/widgets/` | Compact card with the telemetry the dashboard has no fields for |
| `sw7_endpoints.py` | `app/data/` | Finds the Pi 4 (localhost, override, wired, beacon, mDNS, last good) |
| `sw7_live_only.py` | `app/data/` | Live-only mode: the explicit no-data state, never simulated values |
| `sw7_tile_map.py` | `app/pages/` | Street-tile map for the Navigation page (OpenStreetMap tiles, heading-up follow mode), no QtWebEngine |
| `sw7_layout_frame.py` | `app/widgets/` | Layout pass for the status bar (48 px, 16 px text), nav bar (labels, 64 px targets), side arrows, Settings and Charging; `TUKZIE_SW7_LAYOUT=0` keeps the team's layout (tests/test_layout_frame.py) |
| `sw7_style.py` | `app/widgets/` | Paper and depth style (default; `TUKZIE_SW7_STYLE=team` keeps the layout-pass look): palette, Ink night variant, type scale, shadows, back plane, signal audit, and the restyled frame (tests/test_style_core.py) |
| `sw7_weather.py` | `app/widgets/` | Open-Meteo weather for the status bar and the charcoal weather card; sunrise and sunset switch the night variant |

They are kept here, outside the dashboard repo, so the dashboard team can
review them before anything in their code changes. The telemetry contract is
in `TELEMETRY_LINK.md`. All three use QtNetwork and QtWidgets only, not
QtWebEngine (the Navigation page's WebEngine view has crashed on the Pi 5,
per the dashboard README), and all colours come from the dashboard's `THEME`.

## Front camera page

- Shows the live view from the Pi 4 detector
  (`CameraDetection/hazard_detector.py --preview`), with detections drawn on.
- Lists current alerts (class and distance band) in the dashboard's status
  colours: red immediate, amber warning, green monitoring.
- Shows the detector's frame rate and sensor-to-result latency.
- Emits `alerts_changed(list)`, so other pages can react to alerts.
- Streams video only while the page is on screen, keeps only the newest
  frame, and reconnects every 3 s if the camera drops out.

Endpoints: `GET /stream` (MJPEG) and `GET /alerts` (JSON, `{"active": [...],
"fps": 7.0, "latency_ms": 182}`). Address: `TUKZIE_CAMERA_URL` if set,
otherwise `http://<Pi 4 host>:8080` from the resolver (below); the page
follows the Pi 4 when it is found somewhere else, and shows "Searching for
the Pi 4" meanwhile.

## Live-data provider

`LiveDataProvider(manager)` polls `GET <bridge>/telemetry` every 500 ms
(address `TUKZIE_TELEMETRY_URL` if set, otherwise from the resolver, which it
tells about every poll) and calls
`VehicleStateManager.ingest_live_state(state, source="sw7_telemetry")`.

`ingest_live_state()` replaces the dashboard state as a whole, it does not
merge, so each call gets a complete `VehicleState`:

| Bridge field | VehicleState field | Note |
|---|---|---|
| `esp32.soc` | `soc_pct`, `signal_validity["soc"]` | null keeps the last known value, marked invalid; None if the BMS has never reported (was the default 82 %) |
| `esp32.v * esp32.i / 1000` | `signed_battery_power_kw`; `battery_power_kw = max(0, kW)` | null if either is null; sign not yet checked on the vehicle |
| `esp32.lat`, `esp32.lon` | `latitude`, `longitude`, `gps_timestamp` | only when `fix` is true, otherwise None |
| `esp32.fix` | `signal_validity["gps"]` | |
| `esp32.crs` | `heading`, `signal_validity["heading"]` | GNSS course over ground (firmware 0.7.1+); only with a fix, otherwise None |
| `esp32.alt` | `altitude_m` | GNSS altitude in m (firmware 0.7.1+); only with a fix, otherwise None |
| `bridge.replay`, or `esp32.fw` ending in `-replay` | `data_source` = `sw7_replay` | otherwise `sw7_telemetry`; the map and the ride card show a REPLAY badge |
| `tof.ahead_mm` | `front_obstacle_distance_m`, `signal_validity["front_obstacle"]` | the ahead sensor only, in metres (a side reading must not raise a front warning); None if ToF is null or older than 3 s |
| `esp32.spd_raw` | not mapped | units unconfirmed; `speed_kmh` stays 0 and `signal_validity["speed"]` is False |

Gear, indicator, headlights and parking brake are copied from the manager's
simulation state, so the keyboard and controller still set them. Every other
field keeps the `VehicleState` default and is marked invalid in
`signal_validity` (speed, battery temperature, rear obstacle, weather, road
surface, door, seatbelt, tyres).

Nothing is ingested when the bridge cannot be reached, the reply is not
JSON, `esp32` is null, or `esp32.age_ms` is missing or above 3000. The
dashboard's own 2500 ms watchdog then returns it to simulation and shows its
usual "simulation resumed" toast, or, in live-only mode, to the no-data state
(next section).

Signals: `telemetry_updated(object)` carries the raw `/telemetry` dict on
every poll, or None when the bridge is unreachable; `link_changed(str)` is
"live", "stale" or "offline"; `endpoint_changed(host, how)` says where the
Pi 4 is (`("", "searching")` while searching).

## Live-only mode

Set `TUKZIE_LIVE_ONLY=1` (`deploy/start_sw7_dashboard.sh` does) and the
dashboard never shows a simulated value:

- The simulation timer never runs. The manager starts in mode `no_data` and
  publishes `sw7_live_only.no_data_state()` every 250 ms: every
  sensor-derived field None, every `signal_validity` entry False, not
  charging, `data_source` "no_data". Gear, indicator, headlights and parking
  brake are copied in from the keyboard and controller, so they keep working.
- Live telemetry switches it to `live_controller` as before. The live state is
  built on the same blank state, so fields with no live source (speed,
  pedals, temperatures, odometer, weather, tyres and so on) are None too.
  Range is the dashboard's model estimate from the live state of charge.
- 2.5 s without a fresh live state: back to `no_data` (never to simulation),
  with the toast "Live data lost · showing no data".
- Pages: the status bar shows `--%` and a grey battery; Driving shows `--`
  for speed, brake and accelerator and "Range: -- km"; Diagnostics shows
  "Unavailable"; Analytics shows `--` and leaves gaps out of its charts;
  Charging shows `--` for state of charge, power, voltage, current and
  temperature; the reverse page hides its keyboard-driven radar and shows
  `--` (there is no rear sensor); the ASIS panel says "No live vehicle data"
  instead of "conditions normal" and gives no battery advice from an
  unknown state of charge; route planning refuses with a clear message when
  the state of charge is unknown.

Still not from our sensors in live-only mode: ASIS's recommended speed marker
(a model output from road data, not a measurement), weather from the
internet weather service (live, not simulated), and the location label "UCT".

## Finding the Pi 4

`sw7_endpoints.Pi4Resolver` (TELEMETRY_LINK.md section 4.3) tries, in order:
127.0.0.1 (localhost, for a single Pi 5 running everything), the override
(`TUKZIE_PI4_HOST` or `pi4_host=` in `~/.config/sw7/endpoints.conf`), wired
10.20.0.1, the source of the latest UDP beacon on port 50808 (not older than
10 s), `pi4-camera.local`, and the last good host from
`~/.config/sw7/last_pi4_host`. A host is accepted when `/telemetry` on port
8081 answers within 3 s with valid JSON; 3 failed polls in a row start a new
search. One resolver is shared by the provider and the camera page
(`shared_resolver()`). The ride card shows "Pi 4: <host> (<how>)" or
"Pi 4: searching". `TUKZIE_TELEMETRY_URL` and `TUKZIE_CAMERA_URL` bypass it.

## Ride quality card

Shows vibration (`vib`, m/s2), IMU disagreement, IMU1/IMU2 sample rates and
drops, motor rpm, raw GNSS speed (units unconfirmed), modem signal quality
(`csq` of 31, amber below 10), MQTT up or down, ToF left, ahead and right in
metres (amber under 1 m), and the ESP32 record age, with a pill that reads
Live, ESP32 stale or Offline. Values turn grey when not live, and the card goes
Offline by itself if nothing arrives for 3 s. While the bridge replays a file
(`bridge.replay`, or `fw` ending in `-replay`) an amber REPLAY badge sits next
to the pill.

It is a card, not a page, placed on the Diagnostics page under the main
diagnostics card. Reasons: the bottom bar is icon-only with one icon per page,
and these figures are engineering health data like the rest of Diagnostics,
not something the driver needs on a separate screen; the Diagnostics page
already scrolls, so it costs two lines there and no new icon or page id. The
card is self-contained, so it can move to the Driving page or a page of its
own later. See `tests/ride_card.png`.

## Street-tile map (Navigation page)

The team's Leaflet web map segfaults on the Pi 5's display
(`PI5_MAP_CRASH.md`), and their "Native fallback" only draws vector roads
from the small offline index around UCT. `sw7_tile_map.SW7TileMap` replaces
that native map (same methods and attributes, so only the import in
`navigation_page.py` changes; `TUKZIE_TILE_MAP=0` brings the team's map back).
It draws OpenStreetMap raster tiles with QPainter, so no QtWebEngine.

- Tiles: `https://tile.openstreetmap.org/{z}/{x}/{y}.png` (or
  `TUKZIE_TILE_URL`), at most 2 requests at a time, User-Agent
  `TUKZIE-SW7-dashboard/1.0 (UCT student project)`, only tiles on screen and
  only once the zoom has settled (no bulk prefetching, per the OSM tile
  policy). Disk cache `~/.cache/sw7_tiles/{z}/{x}/{y}.png` (or
  `TUKZIE_TILE_CACHE`): read first, and a tile under 30 days old is never
  fetched again, so areas already driven work offline. After a network
  error it waits 15 s before trying again (5 min after HTTP 403 or 429).
- Missing tile: a lower-zoom tile from memory is scaled up; if there is
  none, the team's vector roads (`set_context`, `set_plan`) are drawn on a
  plain background, and the attribution line says the street tiles are
  offline. The map is never blank.
- Follow mode: heading-up (the map turns so the GNSS course points up),
  the vehicle as an arrow at 70 % of the height, zoom 17. The course is only
  trusted while moving: from `speed_kmh` when known, otherwise when a new fix
  implies at least 3 km/h (live mode has no speed yet). Stopped, the last
  good heading is held for 20 s, then the map eases to north-up; with no
  course at all it is north-up with a dot instead of an arrow.
- Smooth: each 1 Hz fix starts a linear move from where the marker is to the
  new fix over the measured update interval; camera rotation and zoom ease
  exponentially. A 30 fps QTimer runs only while the map is visible and
  something moves. Jumps over 300 m are not animated.
- Touch: drag pans and leaves follow mode; pinch, wheel and +/- zoom and keep
  follow mode; Overview fits the route north-up; tapping the compass turns an
  explored map north-up.
- Route from `set_plan` in the accent colour on a dark casing, the travelled
  part (`set_progress`, by distance along the route) dimmed.
- No position: the map stays at the last known position, or the UCT area,
  with a "Waiting for GPS fix" banner. Replayed data: amber REPLAY badge.
- Compass and "© OpenStreetMap contributors" always shown.
- Layout pass (on unless `TUKZIE_SW7_LAYOUT=0`, which gives back the earlier
  look pixel for pixel): one column of 64 x 64 controls on the right edge
  (compass, Follow, Overview, 3D with `TUKZIE_MAP_TILT=1`, +, -), Simulate
  drive / End simulation 200 x 64 at the bottom right above the attribution;
  the turn banner anchored top left (520 x 128, distance 48 px, street 24 px,
  "Then:" strip 40 px at 18 px); the SIMULATED label as a yellow chip at the
  left end of the arrival-time bar (bottom centre, 560 x 72); the altitude as
  a small chip by the compass, only when known. `layout_page()` moves the
  page's own overlays to fit (search field right of the banner, the team's
  Follow, Overview and altitude card hidden, status line at 18 px), called
  from `_position_overlays` (`LAYOUT_MAP_PATCHES`). Screenshots before and
  after in `tests/layout/map/`.

Screenshots (fake test tiles): `tests/tile_map_follow.png`,
`tests/tile_map_no_fix.png`, `tests/tile_map_replay.png`,
`tests/tile_map_offline.png`.

## Wiring it in (edits for the dashboard team)

Each edit below is exact: find the existing line, add or change as shown.
The same edits are in `tests/dashboard_patches.py`, and the test applies them
to a copy of v1.0-validated and starts the patched dashboard, so they are
checked against the current files.

1. Copy the six files: `front_camera_page.py` and `sw7_tile_map.py` to
   `app/pages/`, `live_data_provider.py`, `sw7_endpoints.py` and
   `sw7_live_only.py` to `app/data/`, `ride_quality_card.py` to
   `app/widgets/`.

2. `app/pages/dashboard_main.py`

   a. Imports. After `from ..data.data_provider import VehicleStateManager` (line 18) add:
   ```python
   from ..data.live_data_provider import LiveDataProvider
   ```
   After `from .driving_page import DrivingPage` (line 27) add:
   ```python
   from .front_camera_page import FrontCameraPage
   ```

   b. After `self.settings = SettingsPage(self.saved_settings)` (line 74) add:
   ```python
           self.front_camera = FrontCameraPage()
   ```

   c. In `self.page_by_id`, change `"settings": self.settings,` (line 79) to:
   ```python
               "settings": self.settings, "camera": self.front_camera,
   ```

   d. Line 81, add `"camera"` after `"navigation"` in `page_ids`:
   ```python
           self.page_ids = ["driving", "analytics", "diagnostics", "navigation", "camera", "reverse", "charging", "settings"]
   ```

   e. Line 85, add `"camera"` after `"navigation"` in `normal_ids` too. The
   older steps missed this list; without it the side arrows skip the camera
   page and its nav button never shows as selected (lines 147 and 156).
   ```python
           self.normal_ids = ["driving", "analytics", "diagnostics", "navigation", "camera", "charging", "settings"]
   ```

   f. After `self._apply_theme(); self.switch_page_id("driving"); self.vehicle_data.start()` (line 120) add:
   ```python
           self.telemetry = LiveDataProvider(self.vehicle_data, parent=self)
           self.telemetry.telemetry_updated.connect(self.diagnostics.ride_card.set_telemetry)
           self.telemetry.endpoint_changed.connect(self.diagnostics.ride_card.set_endpoint)
           self.telemetry.start()
   ```

   g. In `closeEvent` (line 282), change
   `for fn, name in ((self.vehicle_data.stop, "vehicle data"),` to:
   ```python
           for fn, name in ((self.telemetry.stop, "telemetry"), (self.vehicle_data.stop, "vehicle data"),
   ```
   (the rest of that line stays as it is).

3. `app/pages/diagnostics_page.py`

   After `from ..widgets.themed_surfaces import ThemedPageSurface, ThemedCard` (line 8) add:
   ```python
   from ..widgets.ride_quality_card import RideQualityCard
   ```
   After `        root.addWidget(card)` (line 21) add:
   ```python
           self.ride_card=RideQualityCard();root.addWidget(self.ride_card)
   ```

4. `app/widgets/nav_bar.py`, in `NAV_ITEMS` after `('navigation','navigation','Navigation'),` add:
   ```python
       ('camera','camera','Front camera'),
   ```

5. `app/widgets/icon_registry.py`, just before `DRAWERS: dict[str, DrawFn] = {` add:
   ```python
   def camera(p,r,c):
       _setup(p,c,max(1.6,r.width()*.065))
       body=QRectF(r.left()+r.width()*.14,r.top()+r.height()*.30,r.width()*.72,r.height()*.48)
       p.drawRoundedRect(body,r.width()*.08,r.width()*.08)
       p.drawRect(QRectF(r.left()+r.width()*.36,r.top()+r.height()*.20,r.width()*.22,r.height()*.10))
       p.drawEllipse(body.center(),r.width()*.14,r.width()*.14)
   ```
   and in `DRAWERS` change `'speaker': speaker,` to:
   ```python
       'speaker': speaker, 'camera': camera,
   ```

6. Live-only mode: the `LIVE_ONLY_PATCHES` in `tests/dashboard_patches.py`
   (in `data_provider.py`, `dashboard_main.py`, `status_bar.py`,
   `driving_page.py`, `diagnostics_page.py`, `analytics_page.py`,
   `charging_page.py`, `login_page.py`, `reverse_camera_page.py`,
   `asis_advisory_panel.py`, `asis/advice_engine.py`, `asis/coordinator.py`).
   They are listed there with a comment each rather than repeated here; the
   manager only changes behaviour with `TUKZIE_LIVE_ONLY=1`, and the page
   guards only act on values that are None. Their anchors are checked against
   v1.0-validated; the deploy step must check them on the Pi's v1.1 (each
   must occur exactly once).

7. Street-tile map: in `app/pages/navigation_page.py`, after
   `from .navigation_page_fallback import NativeRouteMap` add:
   ```python
   if __import__("os").environ.get("TUKZIE_TILE_MAP", "1").strip() != "0":   # SW-7 street-tile map
       from .sw7_tile_map import SW7TileMap as NativeRouteMap  # noqa: F811
   ```
   (`TILE_MAP_PATCHES`; the anchor occurs once in both v1.0-validated and
   v1.1.)

The Pi 4 is found automatically (above). To pin it, set `TUKZIE_PI4_HOST`
(or `pi4_host=` in `~/.config/sw7/endpoints.conf`); to bypass the resolver
altogether, set `TUKZIE_TELEMETRY_URL` and `TUKZIE_CAMERA_URL`.

## Layout pass: Diagnostics, Front camera, Sensors (12 Oct)

From Planning/google-stitch-dashboard-prompt.md (sections 1, 2, 3.4, 3.7, 3.8), behind `TUKZIE_SW7_LAYOUT`
(default on; `=0` gives the earlier pages exactly, checked pixel for pixel by `tests/test_layout_pages.py`).
Layout, sizes and grouping only; the team's colours and fonts stay.

- Diagnostics (`sw7_layout_pages.py`, `LAYOUT_PAGES_PATCHES`): four cards, Drive, Energy, Position and Link,
  values 18 px, labels 14 px, a status dot in each header; the data source and the Pi 4 address in plain words
  ("Simulated drive", "On this Pi"), the raw strings in the details; the ASIS, route and voice list folded behind
  a 64 px "Show advice and details" row. The ride card is hidden (ToF and vibration are on Sensors); it still
  receives the telemetry and feeds the Link card. The page still scrolls by finger.
- Front camera (`front_camera_page.py`): the status is a 28 px chip like the source chip ("Live · 7.0 fps"),
  alerts are 64 px rows with a 12 px band colour bar, the class in 24 px and "Immediate · under 3 m" under it,
  nearest band first, the top immediate or warning alert filled in the obstacle pill colours; alerts card 340 px;
  nothing under 16 px.
- Sensors (`sensors_page.py`): the three gauges are replaced by a tuk-tuk outline seen from above with a wedge
  per ToF sensor (as long as the free space, in its band colour) and the distance in 40 px by each sensor, with a
  word under it (Very close, Close, Clear, No reading); the hazards list beside it in 64 px rows; Vehicle,
  Position and Ride and link below in three columns; the link chip 120 x 36. The obstacle pill is unchanged; it
  now also re-places itself when the status bar changes height.

Screenshots (made-up test readings): `tests/layout/pages/before_*.png` and `after_*.png`.

## Paper and depth style, core (12 Oct)

From Planning/paper-depth-theme-prompt.md (the student's thetheme.jpg), behind `TUKZIE_SW7_STYLE` (default `paper`;
`team` installs nothing, checked widget for widget and pixel for pixel by `tests/test_style_core.py`). One patch line
in `dashboard_main.py` (`STYLE_CORE_PATCHES`) calls `sw7_style.install` after the layout pass.

- THEME gives the Paper palette (warm off-white, ink text, one terracotta signal colour that only marks things you
  can tap) and the bundled Atkinson Hyperlegible font, so every page that reads THEME follows. From sunset to
  sunrise (from the weather service, or `TUKZIE_SW7_NIGHT=1`) it switches to the darker Ink variant.
- Frame: status bar on paper; the source chip an ink outline with a status dot; the SIMULATED strip ink on a warn
  tint; the obstacle pill charcoal with a red dot and a signal Hide; the nav bar a floating rounded pill whose
  selected item is a raised signal circle, the page running 16 px under it; the side arrows round signal-outline
  buttons on shadows.
- Weather (`sw7_weather.py`): Open-Meteo (no key) and Photon reverse geocoding for the suburb, from the GPS fix,
  then the modem's network position, then UCT; every 15 min or after moving 5 km, on a worker thread with a 6 s
  timeout, cached on disk with its age (`~/.cache/sw7_weather/last.json`). The status bar shows "☀ 24° Rondebosch"
  in place of the fixed "UCT 17°C"; tapping it opens a charcoal card with the temperature, five 3-hourly columns and
  "updated N min ago". No network and no cache: "--", never a made-up value.
- The pages themselves are restyled by the page agents, using the API at the top of `sw7_style.py`.

Screenshots (fake weather server): `tests/style/core/`. Not yet tested on the Pi 5 or against the real API.

## UI theme refinement (12 Oct)

From Planning/ui-theme-refinement-prompt.md ("change the skin, not the product"), on top of the paper style; nothing
changes with `TUKZIE_SW7_STYLE=team` (checked widget for widget, and pixel for pixel on the static pages, against
`tests/style/refine/team_reference.json`, recorded before the refinement).

- Type: IBM Plex Sans (Regular, Medium, SemiBold) for the interface and IBM Plex Mono (Regular, Medium) for telemetry
  values, diagnostics, coordinates and timestamps, bundled in `fonts/` from the official IBM/plex releases under the
  SIL Open Font Licence (`fonts/OFL-IBMPlex.txt`, group `STYLE_REFINE_COPIES`). Bold maps to SemiBold (no synthetic
  bold); both fonts have tabular figures. Atkinson Hyperlegible stays as the fallback. `S.mono()` and
  `S.value_font()` (Mono for a figure, Sans for a word such as "Unavailable").
- Surfaces: radii 4 to 8 px (circles stay circles), hairline borders, very light shadows, no back-plane words. The nav
  bar is a flat 72 px bar with a hairline on top, directly under the page stack (it covers nothing); only the
  selected item is signal, with a short signal bar. Side arrows flat with a hairline.
- Weather: unboxed in the status bar (icon, "24° · Rondebosch"), still the tap target for the weather card, "--°"
  when unavailable.
- Pages: Drive (flat dial, finer ticks, a needle, Mono tick numbers and distances, the Around and battery bands in
  words as well as colour), Analytics (hairline cards, ink chart lines, Mono axes), Diagnostics (figures in Mono,
  "Unavailable" in Sans ink_3), Map (flat map with 8 px corners, hairline controls, 64 px search bar and Navigate),
  Surroundings, Settings (ink off toggles, finer sliders), Charging (below).
- Charging: the team's battery animation is back, restyled: bubbles rise through a light fluid filled to the state
  of charge and a short arc circles the track (ok colour while charging, ink_3 otherwise). It runs at 30 fps only
  while the page is shown and the state of charge is known; the disc and figures are cached layers, so a frame costs
  about 1.1 to 1.3 ms on a laptop (not yet measured on the Pi 5). With no live data the state reads "Charging state
  unknown · no live data" and the session tiles show "--", never zero.

Test: `tests/test_style_refine.py` (screenshots `tests/style/refine/before_*.png` and `after_*.png`, day and night).

## Three planes: hero type and the TUKZIE renders (12 Oct)

From Planning/three-planes-hero-prompt.md, on top of the refinement; nothing changes with `TUKZIE_SW7_STYLE=team`.

- Back plane: one huge word per page in Archivo Black (Omnibus-Type, google/fonts, SIL Open Font Licence 1.1,
  `fonts/OFL-ArchivoBlack.txt`), heavy and wide so a word across the page stays short enough to sit in the open
  space: DRIVE, STATS, SYSTEM, MAP, AROUND, CHARGE, SETUP. It is ink at 14 % over paper by day (#D5CFC9) and a
  lifted charcoal (#363331) at night, clipped by the page edges, and never over a value: the gear row and warning lamps on
  Drive sit on a paper card, and the Surroundings word stays under the nearest-distance hero.
- Middle plane: the student's TUKZIE renders, cut out of their white backgrounds by `tools/cut_tukzie_renders.py`
  (Pillow, numpy, scipy; development only) into `assets/tukzie_three_quarter.png`, `tukzie_front.png` and
  `tukzie_side.png`, with a feathered edge and the render's own ground shadow kept as a soft shadow. Drive has the
  three-quarter view above the Around tile (the advice strip stops short of it), Charging the front view under the
  tiles, Settings the side view under the Save card. Map has none; Diagnostics and Surroundings have no free space
  for one. Word and render are painted once into a cached pixmap per page size and variant (`S.Plane`, `S.PLANES`,
  `S.set_plane`, `S.page_plane_geometry`).
- Top plane: the widgets. After the student's review (AURA pass) Drive's tiles and dial sit low so DRIVE and the
  vehicle fill the open upper area (the render is about 1.7 times larger), the advice strip, the Charging column,
  the Settings and Diagnostics groups and the hazards list have no cards (groups under a hairline), and the Charging
  ring has no disc. Cards stay where they group data or keep text legible (the Drive tiles, the gear row, the
  Range tile, the camera frame, the tuk-tuk card).
- Charging: the team's composition (Planning/reference_team_charging_page.jpg) in paper and ink: a card disc with the
  ring arc (its length the state of charge, turning slowly, ink), the tuk-tuk outline from above filled with rising
  bubbles to the state of charge (ok-green while charging or above 30 %, ink below), the percentage above it, and
  the readings round the ring: power input, voltage, current, charging state, time to full, cell health. 30 fps only
  while shown; "--" for anything without a reading, and cell health is "--" until it is reported.
- COPIES: group `STYLE_PLANES_COPIES` (the font, its licence, the three renders to `app/assets`).

Test: `tests/test_style_planes.py` (screenshots `tests/style/planes/`, day and night).

## Tests

`tests/test_live_data_provider.py` (run with `python
DashboardIntegration/tests/test_live_data_provider.py`): copies
v1.0-validated's `app` into a scratch folder, adds the five files, applies
the edits above to the copy, and starts a local HTTP server that serves
`/telemetry` like the bridge. Offscreen, with PySide6 6.11.2 (Essentials) on a
laptop, it checks:

- Normal values reach `ingest_live_state()` mapped as in the table above,
  with `speed_kmh` left at 0, and the dashboard switches to live mode.
- Null fields map to None or keep the last state of charge, marked invalid.
- With `esp32.age_ms` 4500, with `esp32` null, with bad JSON and with the
  server stopped, polling continues, nothing is ingested, and the dashboard
  falls back to simulation by itself.
- The ride card shows the values, ESP32 stale, Offline, and goes Offline
  after 3 s without updates. `tests/ride_card.png` is its live state.
- The patched `DashboardMain` starts, goes live from the bridge, fills the
  ride card on the Diagnostics page, and puts the camera page after
  Navigation in the page order and arrows.
- Live-only mode: with the bridge down the patched dashboard shows the
  no-data state (every sensor field None, the simulation timer not running,
  the shown state not the simulator's), the status bar, Driving,
  Diagnostics, Analytics, Charging and reverse pages show `--` or
  Unavailable, every page paints without an exception, and the indicator and
  headlights still work. It goes live when a fake bridge appears (unmapped
  fields still None) and returns to no-data, with the "Live data lost" toast
  and never the simulation, when it stops. `soc_pct` is None when the BMS has
  never reported, in both modes.
- The patched Navigation page uses `SW7TileMap`, which is fed the live
  position (tiles pointed at a dead local port, so no real OSM traffic).
- Resolver: picks localhost when a fake bridge is on 127.0.0.1; falls through
  to the override (`TUKZIE_PI4_HOST`, then `endpoints.conf`) on 127.0.0.2;
  learns 127.0.0.3 from a fake UDP beacon sent to 127.0.0.1:50808 (and ignores
  a packet that is not a SW-7 beacon, and a beacon older than 10 s); after the
  bridge stops, searches again and finds the new host, with the provider, the
  ride card label and the camera page following; exactly 3 failures in a row
  start a new search.

With PySide6-Essentials only, the test gives the reverse camera page a silent
`QSoundEffect` stub, because `QtMultimedia` is in PySide6-Addons.

`tests/test_tile_map.py` tests the street-tile map against a local fake
tile server (`TUKZIE_TILE_URL`, temp `TUKZIE_TILE_CACHE`), fed with fixes
from `CameraDetection/tests/replay_uct_route.txt` through
`build_live_state()` (so `crs` and `alt` mapping are checked too): the
right zoom-17 tiles are requested (vehicle tile first, never more than 2 at
a time, the SW-7 User-Agent) and cached; a new map at the same place fetches
nothing, a 31-day-old tile is fetched again; heading-up with the vehicle at
70 % height; the marker moves steadily between fixes and the frame timer
stops when idle or hidden; course noise while stopped is ignored; "Waiting
for GPS fix" at the last position or UCT; the REPLAY badge on the map and
the ride card, and `sw7_replay` from the provider; vector roads with the
tile server down and no endless retries; drag, zoom and Overview; and that
`TUKZIE_TILE_MAP=0` restores the team's map. Both tests also pass against
the v1.1 copy (`TUKZIE_DASHBOARD_DIR`).

`tests/test_layout_map.py` runs the patched dashboard at 1280 x 800 with
`TUKZIE_SW7_LAYOUT=0` and `=1`, flat and tilted, through a simulated drive, a
live drive with a turn banner and follow mode. It checks the 64 px column, the
banner, text and bar sizes, that no overlays overlap or cover the road ahead
of the arrow, and with the layout off the earlier geometry, and saves the
screenshots in `tests/layout/map/` (`TUKZIE_LAYOUT_TILE_CACHE` may point at a
folder of cached OSM tiles for readable screenshots; nothing is downloaded).

`tests/test_front_camera_page.py` and `tests/test_front_camera_page_live.py`
are the earlier camera page tests (run from a scratch copy of the app).

Not yet tested: on the Pi 5 itself, against the real bridge and ESP32, and
the edits above in the dashboard team's own repo.
