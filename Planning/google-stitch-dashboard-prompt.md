# Google Stitch prompt: TUKZIE in-vehicle dashboard layout pass

Written 12 Oct 2026. Purpose: get better layouts for every dashboard page out of Google Stitch
(stitch.withgoogle.com) without changing the team's look. Nothing in the dashboard code changes from this
file. The mock-ups come back for review first, then any code change is planned separately.

The rule from 7 Oct stands: the Night/Day restyle was rejected, so this keeps the team's colours, fonts,
cards, glow background and icons. Only layout, hierarchy, spacing, text size, touch targets and consistency
are open to change.

Sources used: the team's v1.1 code as patched by SW-7 (theme.py, main_window.py, widgets/status_bar.py,
widgets/nav_bar.py, pages/dashboard_main.py, analytics_page.py, charging_page.py, settings_page.py) and the
SW-7 files in DashboardIntegration (sensors_page.py, front_camera_page.py, sw7_tile_map.py, sw7_sim_link.py,
sw7_page_swipe.py, sw7_search.py, sw7_analytics.py, sw7_voice_guide.py, tests/dashboard_patches.py,
deploy/start_sw7_dashboard.sh). Screenshots: tests/sim_sync/*.png (all pages, live and simulated),
tests/search/*.png, tests/hazard_banner.png, tests/analytics_graphs.png, tests/tile_map_navigation_pi5.png,
the scratchpad pillshot shots (obstacle pill, 11 Oct) and the photo
Photos/Reference/Enclosures/2026-10-12_display_front_dashboard_running.jpg (Front camera page on the
Waveshare panel, showing strong reflections on the glossy glass).

---

## 0. Facts the prompt depends on

| Item | Value | Where it comes from |
|---|---|---|
| Screen | Waveshare 10.1 inch, 1280 x 800, landscape, capacitive touch | main.py `--res` default 1280x800; config.py scales from a 1280x800 baseline |
| Window | Full screen (`--fullscreen` in start_sw7_dashboard.sh) | deploy script |
| Pixel density | about 150 px per inch, so 64 px is about 11 mm on the glass | 1509 px diagonal over 10.1 inch |
| Theme in use | Team original (TUKZIE_SW7_THEME=0 since 7 Oct), palette Electric Blue by default | start_sw7_dashboard.sh, config.py `palette_key` |
| Data mode | Live only (TUKZIE_LIVE_ONLY=1): a missing value shows "--", never a made-up number | start script |
| Page change | Two-finger sideways swipe (three on the map), the bottom nav icons, or the small side arrows | sw7_page_swipe.py, dashboard_main.py |

Carousel order (dashboard_main.py `page_ids`, Reverse excluded from swiping):
1 Driving, 2 Analytics, 3 Diagnostics, 4 Navigation, 5 Front camera, 6 Sensors, 7 Charging, 8 Settings.
Reverse camera opens by itself when the gear is R. Startup and Login come before the carousel (Login is
skipped on the bench).

---

## 1. Page by page: now, what works, what to improve

All sizes are at 1280 x 800. "Content area" means the space between the status bar (38 px, top) and the
nav bar (about 56 px, bottom), so about 1280 x 706, or 1280 x 680 while the yellow SIMULATED DRIVE strip
(26 px) shows.

### Shared frame (every page)

Now
- Status bar, 38 px tall, `card` colour with a 1 px bottom border. Three equal columns: left "UCT: --°C
  (Unavailable)" (weather), centre the source chip (LIVE / REPLAY / NO DATA / SIMULATED) then "80%" and a
  38 x 20 battery icon, right "Sun, 11 Oct 2026  02:22:57". All text 11 px DemiBold in `text_dim`.
- Source chip: rounded 8 px, 12 px bold; LIVE green #00E676, REPLAY and SIMULATED amber #FFD600, NO DATA
  grey #455A64 (sw7_sim_link.py CHIPS).
- Yellow strip under the status bar while a simulated drive runs, 26 px, 14 px bold, "SIMULATED DRIVE · not
  live data · battery, range and speed are simulated, obstacles are live". It pushes the page down rather
  than covering it.
- Obstacle pill, top right inside the status bar, left of the clock: 24 to 32 px tall, 200 to 460 px wide,
  deep red #A3201A with white 13 px text "OBSTACLE 0.9 M LEFT" and a 10 px "Hide" button; amber #FFB224
  with dark text for "Sensor link lost". Tap opens Sensors, Hide snoozes 30 s (sensors_page.py HazardBanner).
- Side arrows, 34 x 44 px, at x = 5 and the right edge, vertically centred. They sit on top of content (on
  Sensors they cover the start of "HAZARDS", on Diagnostics the card edges).
- Bottom nav bar, 54 to 58 px, eight icon-only buttons (30 px icons) with 120 px side margins and 22 px
  gaps, so each button is about 110 x 48 px. Selected item: 1 px accent outline on `card_alt`.
- Background: dark navy with the team's soft teal glow; cards #151C24, radius 16, 1 px border.

What works
- Source chip and yellow strip make simulated data impossible to miss, and the strip does not hide content.
- The pill in the status bar no longer covers the page (the 6 Oct version was a 900 px red banner over the top
  of every page, tests/hazard_banner.png).
- One nav bar and one status bar on every page; consistent card style.

Improve
- Status bar text is 11 px in dim grey, too small to read at a glance in sun. Make the bar 48 px and the
  text 16 px; SOC 18 px bold in its status colour; clock as "14:28" only (date and seconds removed, they are
  on Settings or nowhere); weather short: "Rondebosch 19°C".
- Source chip: 28 px tall, 14 px bold, fixed width 120 px so the bar does not shift when the text changes.
- Obstacle pill: 40 px tall (the bar becomes 48 px), text 16 px bold, the whole pill is the tap target to
  Sensors; Hide becomes a separate 64 x 40 px button inside the pill, not a 10 px label.
- Side arrows: the two-finger swipe and the nav bar already change pages, so either drop them or give them a
  reserved 48 px gutter each side where no content goes, at 48 x 96 px. Never on top of content.
- Nav bar: 72 px tall, each button at least 96 x 64 px, icons 32 px, plus an 11 to 12 px label under each
  icon (gloved drivers and new drivers cannot tell Diagnostics from Charging by icon alone). Selected item
  keeps the accent outline and also gets the accent icon colour.
- Page titles: today 24 px (Camera), 27 px (Sensors, Settings), about 28 px (Diagnostics) and a monospace
  "PIT LANE CHARGING DECK" on Charging, at different x positions (12, 28, 50, 655 px). Use one title style:
  24 px bold, x = 24 px, y = 16 px below the status bar, on every page that has one.
- Outer margin 24 px on all pages, 16 px gap between cards, so pages line up when swiping.

### Page 1: Driving

Now (tests/sim_sync/sim_driving.png, live_driving.png)
- ASIS advice card top left, 220 x 90 px, green border, "ASIS" 11 px then "No live vehicle data" 15 px bold.
- Top centre: left and right indicator arrows with a 46 px gear circle between them (P blue, D green), and a
  row of seven grey tell-tale icons about 22 px (lights, park brake, seat belt, door, tyre, temperature,
  motor).
- Centre: round speed gauge about 460 px across, 0 to 50 km/h, blue progress arc, green tick for the ASIS
  recommended speed (20 km/h), yellow tick for the speed cap (about 42 km/h). Speed "25.0" about 80 px tall,
  "km/h · SPEED" 22 px under it. Live without data shows "--".
- Two tall thin bars (32 x 490 px) left and right for BRAKE and ACCEL, value 13 px and label 9 px below.
- Bottom centre: "Range: 55.9 km" 15 px bold and "Free driving · no destination selected" 11 px.

What works
- Speed is the largest thing on screen and centred. The gauge and the cap tick are clear.
- Gear in a coloured circle is easy to read.

Improve
- Speed as a whole number ("25", not "25.0"): one decimal is noise at a glance. 140 px bold digits, unit
  "km/h" 24 px.
- Range and battery are the second most important numbers on an EV but are 15 px at the bottom. Put a
  "Range 55.9 km" and "Battery 80 %" pair under the gauge at 36 px bold, 20 px labels.
- ASIS advice: 15 px in a small corner card is missed. Make it a full-width advice strip, 64 px tall, under
  the gear row or above the range pair, 22 px text, coloured left edge by severity (green info, amber warn,
  red critical). Hide it when there is nothing to say instead of "Route and vehicle conditions normal".
- Brake and accel bars: 490 px tall for two secondary values. Shorten to 300 px, 24 px wide, beside the gauge,
  value 18 px. That frees the left and right thirds.
- Use the freed right side for "next turn" when a route is active (arrow 64 px, distance 36 px, street 20 px),
  so the driver need not swipe to Navigation; left side for nearest obstacle distance from ToF ("Right
  0.4 m") in the obstacle colours.
- Tell-tales: only show lit ones, at 32 px; grey unlit icons add clutter.
- "Free driving · no destination selected" 11 px: drop it, or 16 px dim when a route is active ("To Main
  Road, Rondebosch").

### Page 2: Analytics (and its Graphs view)

Now (tests/sim_sync/sim_analytics.png, live_analytics.png, tests/analytics_graphs.png)
- Title "Analytics" 24 px top left. A vertical infinite carousel (SW-7, sw7_analytics.py): one large card
  about 900 x 360 px in the middle (for example "BATTERY % (SOC)" with a green gradient and the value "80 %"
  about 40 px), the previous and next cards peeking dimmed above and below, 56 x 56 px up and down buttons on
  the right, and eight 8 px position dots.
- Cards in the loop: Battery % (SOC), Battery temp, Ambient temp, Odometer, Battery output, Consumption,
  Driver insights, Graphs. Tapping Graphs opens a 2 x 2 grid of charts (Speed, Battery %, Distance,
  Consumption vs time, 5 min window) with a Back button.

What works
- One card at a time is calm and the coloured gradients match the team's identity. The student asked for the
  carousel; keep it.
- Up and down buttons are a good size.

Improve
- The value inside each big card is small for the card (about 40 px in a 360 px tall card, lots of empty
  gradient). Value 96 px bold, unit 32 px, one context line 18 px ("7.2 kWh pack · 5.8 kWh left"), and a
  small 5 minute sparkline 120 px tall across the bottom of the card.
- Peeking cards: 60 px visible each, so the centre card can be 480 px tall.
- Dots: 12 px with 12 px gaps, and the current card name as a 14 px label next to the active dot.
- Graphs view: in the test shot the "Analytics" and "Graphs" headings render dark on dark, axis labels are
  about 9 px, and every chart runs 0 to 100 whatever the unit. Use real ranges (speed 0 to 50 km/h, SOC 0 to
  100 %, distance auto, consumption 0 to 120 Wh/km), 12 px minimum axis text, current value 24 px top right
  of each chart, Back button 64 px tall.
- This is a parked page; it does not need glance sizes everywhere, but the main value does.

### Page 3: Diagnostics

Now (tests/sim_sync/sim_diagnostics.png)
- Title "System Diagnostics" about 28 px. Card 1: a two-column key/value table (Speed, Throttle, Signed power,
  Range, Motor temp, Incline, GPS, Source, Charging source | Gear, Brake, Battery SOC, Battery temp, Ambient,
  Odometer, Altitude, Charging), labels 11 px caps dim, values 15 px right-aligned.
- Card 2 "RIDE QUALITY AND LINK": twelve fields in a 4-column grid (Vibration, IMU disagreement, IMU rate, IMU
  drops, Motor, GNSS speed, Signal, MQTT, ToF left/ahead/right, ESP32 age) with "Pi 4: 127.0.0.1
  (TUKZIE_TELEMETRY_URL)" and an "Offline" chip.
- Then "ASIS, ROUTE & VOICE STATUS" as a plain two-column list of about 16 rows, 11 px, running under the nav
  bar (scroll).

What works
- Exact values, right-aligned numbers, "Unavailable" in dim text. Good for an engineer when parked.

Improve
- Too much at one size: group into four cards in a 2 x 2 grid with a status dot in each header: Drive
  (speed, gear, throttle, brake, power), Energy (SOC, battery temp, range, charging), Position (GPS, altitude,
  odometer, incline), Link (Pi 4, ESP32 age, MQTT, signal, IMU rate, drops). Value 18 px, label 13 px.
- Move "ASIS, route and voice status" into a collapsed "Details" card at the bottom (64 px header row,
  tap to open).
- ToF and vibration are already on Sensors; show them once (on Sensors) and keep only link health here.
- Replace raw source strings ("sw7_simulated_drive", "127.0.0.1 (TUKZIE_TELEMETRY_URL)") with plain words
  ("Simulated drive", "Pi 4 on this Pi"), raw text in the Details card.

### Page 4: Navigation (map)

Now (tests/sim_sync/sim_navigation.png, scratchpad pillshot/pill_nav.png, tests/tile_map_navigation_pi5.png)
- Full-bleed OpenStreetMap raster map. Overlays:
  - search bar top centre, about 715 x 64 px card, text field and a 78 x 34 px "Navigate" button;
  - "ALTITUDE N/A" card top right, about 112 x 72 px, and a 50 px compass under it;
  - green turn banner (#17703E) about 560 x 104 px: arrow, "230 m" 30 px bold, "Turn right onto Station
    Road" 19 px; under it a darker green (#0F4F2B) "Then: arrive at destination" strip, 15 px;
  - "SIMULATED DRIVE" yellow label about 255 x 58 px floating over the route under the banner, with "Not live
    data · 0.6 km, 2 min left at 25 km/h" 10 px;
  - ETA card bottom centre about 300 x 58 px: "2 min" 24 px green, "630 m · 02:24" 16 px;
  - "Follow" and "Overview" buttons about 98 x 36 px bottom right, "+" and "-" zoom 44 x 38 px, "End
    simulation" 210 x 44 px with a yellow border;
  - status line bottom left about 550 x 40 px "Offline map ready · enter a destination";
  - "Waiting for GPS fix / Showing the UCT area" card in the centre when there is no fix.
- In the simulated shot the team's old side panels leave dark bands down the left edge (top 0 to 373 px)
  and right edge (top 0 to 373 px) of the map.

What works
- Heading-up follow view with the arrow low on the screen, like a phone. The green turn banner is the
  familiar Google Maps pattern and readable. The SIMULATED label is unmistakable.

Improve
- Controls are too small and scattered for gloves: Navigate 78 x 34, Follow/Overview 98 x 36, zoom 44 x 38.
  Put all map controls in one right-hand column, 64 x 64 px each, 12 px gaps: Follow, Overview, +, -, then
  End simulation (64 px tall, 200 px wide) at the bottom.
- Turn banner: anchor top left at 24 px, 520 x 128 px, distance 48 px bold, street 24 px; "Then" strip
  40 px tall, 18 px. It should not float in the middle of the map.
- Move the SIMULATED DRIVE label off the road: make it part of the ETA bar (a yellow segment at its left
  end) so the route under the arrow stays visible. The yellow strip under the status bar already says it on
  every page.
- ETA bar: bottom centre, 560 x 72 px: "2 min" 36 px, "630 m" 24 px, "arrive 14:28" 24 px.
- Search bar: while a route is active, collapse it to a 64 x 64 px search button top left under the turn
  banner; full bar (64 px tall, Navigate button 120 x 48) only when no route is set.
- Altitude N/A: hide when unknown; when known, a small 16 px chip next to the compass.
- Remove the dark leftover bands so the map is truly full width.
- Status line: 18 px, only when it says something new, and fade after 5 s.

### Overlay: destination search (on Navigation)

Now (tests/search/search_results.png, search_results_list.png)
- Typing opens a results list under the search bar (about 715 px wide): first row "From: Current location
  (GPS)" in accent, then results each 58 px tall with a 22 px pin, distance "2.6 km" 11 px under the pin,
  name 16 px bold, address 13 px dim ("Dreyer Street, Claremont, Cape Town", or "Mall · offline map").
  Online results have a blue pin, offline ones grey.
- The on-screen keyboard fills the lower half: keys about 120 x 86 px, 22 px labels. The list and map are
  squeezed into the top 380 px.

What works
- Keys are large enough for gloves. Distance next to each result. Clear online versus offline pins.

Improve
- Rows 72 px tall, name 20 px, address 16 px, distance 16 px right-aligned instead of 11 px under the pin.
- Show at most four results above the keyboard and no scrollbar; add a "More results" row.
- Recent places (Main Road, Rondebosch; UCT Upper Campus; Cavendish Square) as 64 px chips before typing.
- This is a parked task: say so in the field placeholder ("Where to? (when stopped)").

### Page 5: Front camera

Now (front_camera_page.py; photo 2026-10-12_display_front_dashboard_running.jpg)
- Title "Front camera" 24 px bold left, connection status right in 14 px dim ("Live", "Camera image stale",
  "Camera offline, retrying", "Searching for the Pi 4").
- Video takes three quarters of the width (minimum 320 x 240), with detection boxes drawn by the Pi 4.
- Right card, at least 240 px wide: "Alerts" 18 px, then rows like "Person   Immediate" 16 px bold in the
  band colour (red immediate under 3 m, amber warning under 8 m, green monitoring under 15 m), or "No
  hazards"; metrics at the bottom 12 px dim ("7.0 fps, 180 ms").

What works
- Large video, alerts beside it, colours match the fixed status colours.

Improve
- Status as the same chip style as LIVE/NO DATA (28 px, coloured), not 14 px dim text that disappears in glare
  (the photo shows the top strip washed out).
- Alert rows 64 px tall: a 12 px coloured band bar on the left, class 22 px bold ("Person"), band and
  distance 18 px ("Immediate · under 3 m"), confidence 14 px dim ("63 %"). Nearest first. The top alert
  in a red or amber filled card.
- Video at its true 4:3 aspect (about 860 x 645), centred vertically, alerts panel 340 px wide.
- Metrics 14 px in one footer line.

### Page 6: Sensors

Now (tests/sim_sync/sim_sensors.png, tests/sensors_page.png)
- Title "Sensors" 27 px black weight, link pill top right ("Offline" red, "Live" green, "ESP32 stale" amber)
  about 68 x 32 px, REPLAY chip when replaying.
- "AROUND THE TUK-TUK (ToF)" card: three narrow 52 x 96 px vertical gauges LEFT, AHEAD, RIGHT with "no
  reading" 15 px under each; amber under 1.0 m, red under 0.5 m, range to 1.2 m.
- "HAZARDS (CAMERA + ToF)" card: list nearest first, or "No sensor data".
- Grid cards: VEHICLE (Battery, Voltage, Current, BMS reading, Motor), POSITION (GPS fix, Lat/lon, Heading,
  Altitude, GNSS speed), RIDE AND LINK (Vibration, IMU disagreement, IMU rate, IMU drops, ...). Labels 11 px
  dim, values 18 px bold. The page scrolls; the last card is cut off by the nav bar.

What works
- Honest "no reading" and "--", the link pill, the section titles in accent caps.

Improve
- The three ToF gauges are small and far apart (each 52 px wide in a 1200 px card). Replace with one
  top-down tuk-tuk outline (about 360 x 300 px) with three zones round it (left, front, right), each zone
  filled by its colour and the distance printed in 40 px bold ("0.4 m"), "clear" when beyond 1.2 m.
- Put the hazards list to the right of that (about 760 px wide), rows 64 px like the camera page.
- Everything a driver might glance at (ToF, hazards) above the fold; Vehicle, Position and Ride and link
  below, smaller, and not repeated on Diagnostics.
- Link pill 120 x 36 px, 16 px text, same style as the source chip.

### Page 7: Charging

Now (tests/sim_sync/sim_charging.png)
- Left half: a 580 px cyan ring with a glowing green tuk-tuk outline full of bubbles, "79%" 40 px green on
  top, and four values each side in a monospace font (JetBrains Mono chain): Power input "-- kW", Voltage
  "-- V", Current "-- A" | Charging "STANDBY", Est. ETA "--", Cell health "98%"; labels 15 px, values 20 px.
- Right half: "PIT LANE CHARGING DECK" 16 px, "TELEMETRY UNAVAILABLE // NOT CHARGING" 11 px; a CHARGE SOURCE
  row of three 34 px buttons (Solar, Wired, Unknown, Unknown lit blue); an empty "LIVE POWER INPUT RATE (kW)"
  chart; tiles Time to full, Charging power, Range added "+0.0 km", Energy delivered "0.00 kWh"; Pack core
  temperature bar "32.8 °C".

What works
- The tuk-tuk illustration and ring are the most distinctive part of the team's identity; keep them.
- Tiles are tidy and consistent with Analytics gradients.

Improve
- SOC here reads 79 % while the status bar reads 80 % (different rounding). Show the same number everywhere
  (whole percent, same rounding).
- The monospace font is the only place it appears; keep it for numbers only if the team insists, otherwise
  use the main font with tabular figures.
- Charge source row looks like three buttons but is an indicator. Show it as one 36 px chip ("Source:
  Solar") instead.
- Plain words for the header: "Charging" 24 px title, state "Not charging" 18 px.
- Add the pack size: "80 % · 5.8 of 7.2 kWh".
- Values 28 px, labels 14 px; the empty power chart shows "No charging data" centred, 18 px.

### Page 8: Settings

Now (settings_page.py; redesign shot shows the same structure)
- Title "Settings" 27 px. Sections in cards, titles 11 px caps accent: DISPLAY (Fullscreen and Hide cursor
  toggles 34 x 18 px, Brightness slider with a 26 px handle and "100%"), DRIVER ASSISTANCE (Voice enabled,
  "Repeat last warning"), NAVIGATION (drop-downs for map and route source, auto follow, offline maps, plus a
  long grey hint paragraph), VOICE (voice, provider, Speech speed and Volume sliders, Test voice), COLOUR
  THEME (twelve palette swatches, three columns), SYSTEM (Save button). Long scroll.

What works
- Everything in one place, grouped, changes apply at once.

Improve
- Toggles 34 x 18 px and slider handles 26 px are too small for gloves: rows 64 px tall, toggles 64 x 36 px,
  slider handle 44 px, drop-downs 56 px tall.
- Two columns of cards so the page needs less scrolling: left Display, Voice, Driver assistance; right
  Navigation, Colour theme.
- Remove the Save button or label it "Saved automatically"; the hint text says changes apply immediately.
- Shorten the navigation hint to one 14 px line.
- Keep all twelve palettes; Electric Blue stays the default.

### Reverse camera (automatic, gear R)

Not reviewed in a screenshot for this pass. Keep as the team built it. One rule for the mock-up: full-screen
video, the source chip and obstacle pill still visible, no nav bar needed while in R.

---

## 2. Global rules (put these in every Stitch prompt)

### Palette (team Electric Blue, theme.py; do not invent new colours)

| Token | Hex | Use |
|---|---|---|
| background | #0A0F14 | page background (with the team's soft teal radial glow) |
| panels (card) | #151C24 | cards, status bar, nav bar |
| card_alt | #252B33 | buttons, inputs, selected nav item |
| border | #3D434B | 1 px card and button borders |
| accent | #00B7FF | selection, active nav item, section titles, primary buttons, speed arc |
| highlight | #00E5FF | charging ring, regen |
| text | #F5F7FA | main text (17.9:1 on background) |
| text_dim | #A3A6AA | labels (7:1 on cards) |
| text_faint | #6D7075 | decoration only, never data (3.5:1 on cards) |
| status normal | #00E676 | OK, LIVE chip, good battery, gear D |
| status warn | #FFD600 | warning, SIMULATED and REPLAY chips, yellow strip (dark text #0B0D10, 13.8:1) |
| status crit | #FF1744 | critical lines and icons; white text on it is only 3.8:1, so text pills use #A3201A |
| status inactive | #455A64 | NO DATA chip fill with white text (7.2:1); not for text on cards (2.4:1) |
| obstacle pill critical | #A3201A with #FFFFFF | 7.6:1 |
| obstacle pill warning | #FFB224 with #0B0D10 | link lost |
| turn banner | #17703E, then-strip #0F4F2B, white text | map only |

Analytics and Charging cards use soft vertical gradients of their status colour (green SOC, amber temp,
blue odometer and power) over #151C24. Keep them.

### Fonts

- Team choice (theme.py): Orbitron first, then Rajdhani, Inter, Roboto, DejaVu Sans, Noto Sans, Arial. On
  the machines that made the screenshots it renders as a clean neo-grotesque sans (Inter or Roboto look); on
  the Pi it falls back to DejaVu Sans. For Stitch, say "Inter" so the mock-up matches what people see.
- Charging page numbers use a monospace (JetBrains Mono, Fira Code, Consolas). Only there.
- Numbers use tabular figures so values do not jump.
- Weights: titles Bold or Black, values Bold, labels Regular or DemiBold in caps with 1 px letter spacing
  for section titles.

### Text sizes at 1280 x 800

| Role | Minimum | Target |
|---|---|---|
| Primary driving value (speed) | 96 px | 140 px |
| Secondary glance values (range, battery, next turn distance, nearest obstacle) | 32 px | 36 to 48 px |
| Alert text (pill, banner, turn street) | 16 px | 20 to 24 px |
| Labels on driver-facing pages | 14 px | 16 to 18 px |
| Status bar | 16 px | 16 px, SOC 18 px |
| Parked pages (Diagnostics, Settings, Analytics details) | 13 px | 14 to 16 px |
| Nothing anywhere | below 12 px | |

### Touch and gestures

- Every tap target at least 64 x 64 px (about 11 mm on this panel), 12 px apart, for gloved fingers on a
  moving vehicle. Text buttons at least 64 px tall.
- Two-finger sideways swipe changes page (three fingers on the map, where two fingers zoom). Do not put
  horizontal scrollers or sideways sliders where a swipe would land, other than Settings sliders.
- Analytics swipes up and down inside its carousel; that is fine.
- One-finger drag on the map pans it.

### Layout frame

- Status bar 48 px: left weather and location, centre source chip (LIVE, REPLAY, NO DATA, SIMULATED) plus
  battery percent and icon, right obstacle pill (when active) then clock "14:28".
- Yellow SIMULATED DRIVE strip 26 to 32 px under the status bar while simulated; it pushes content down.
- Bottom nav bar 72 px, eight items in carousel order with icon and short label: Drive, Analytics,
  Diagnostics, Map, Camera, Sensors, Charging, Settings.
- Outer margins 24 px; card gap 16 px; card radius 16 px; button radius 12 px.
- Safe edges: keep the outer 16 px clear of tap targets (the bezel and the enclosure lip sit there) and do
  not place controls behind the left or right side arrows if they stay.

### Sunlight and glare

- The panel is glossy and reflects strongly (photo of 12 Oct). Dark theme stays, so contrast has to come from
  size and weight: data text in #F5F7FA or a status colour, never in text_faint.
- Status colour is never the only signal: pair it with a word (LIVE, WARNING, IMMEDIATE) or an icon.
- Avoid thin 1 px lines carrying meaning; gauges and bars at least 8 px thick.

---

## 3. The Stitch prompts

Paste the overall prompt first, then one page prompt at a time. Each page prompt repeats the key frame
facts because Stitch does not always carry context between screens.

### 3.1 Overall prompt (paste first)

```
Design a set of landscape screens for an in-vehicle dashboard app called TUKZIE, shown on a 10.1 inch
touchscreen at exactly 1280 x 800 px, mounted on the handlebar of a small electric tuk-tuk (three-wheel
taxi) at the University of Cape Town. The driver reads it at a glance while driving, often in bright sun
on a glossy screen, and may wear gloves. This is a layout and hierarchy redesign of an existing app: keep
its visual identity exactly.

Identity to keep (do not change):
- Dark theme. Page background #0A0F14 with a soft teal radial glow. Cards #151C24, 1 px border #3D434B,
  radius 16 px. Buttons #252B33, radius 12 px.
- Accent #00B7FF (selected items, section titles in caps, primary buttons, speed arc), highlight #00E5FF.
- Text #F5F7FA, labels #A3A6AA. Never put data in a darker grey than #A3A6AA.
- Status colours, fixed: OK #00E676, warning #FFD600, critical #FF1744, inactive #455A64. Critical text
  pills use #A3201A with white text.
- Font Inter (sans), tabular figures. Titles bold, values bold, labels regular in small caps style.
- Simple line icons, no photos, no new illustrations, no light theme, no new brand colours.

Frame on every screen:
- Top status bar 48 px, colour #151C24: left "Rondebosch 19°C"; centre a source chip (LIVE green with dark
  text, REPLAY or SIMULATED yellow with dark text, NO DATA grey with white text), then "80%" and a battery
  icon in green; right the clock "14:28". When an obstacle is close, a red pill (#A3201A, white bold
  16 px, 40 px tall) sits at the right of the status bar just left of the clock, reading
  "OBSTACLE 0.4 M RIGHT", with a separate 64 x 40 "Hide" button inside it.
- When data is simulated, a yellow (#FFD600) strip 28 px tall directly under the status bar, dark bold
  text: "SIMULATED DRIVE · not live data · battery, range and speed are simulated, obstacles are live".
  It pushes the page down; it never covers content.
- Bottom navigation bar 72 px, #151C24, eight items with a 32 px icon and a 12 px label: Drive,
  Analytics, Diagnostics, Map, Camera, Sensors, Charging, Settings. The current item has a 1 px #00B7FF
  outline, #252B33 fill and an accent icon.
- 24 px outer margins, 16 px gaps, one page title style (24 px bold at the top left) where a title is
  needed.

Rules: every tap target at least 64 x 64 px; driver-facing values at least 32 px, the speed 140 px;
labels at least 14 px; nothing under 12 px. Missing values show "--", never a made-up number. Live and
simulated data must always be clearly told apart by the chip and the yellow strip.
```

### 3.2 Driving

```
Screen: Driving, 1280 x 800 landscape, same frame and identity as before. Source chip SIMULATED, yellow
simulated strip visible, battery 80%.

Layout:
- Centre: a round speed gauge about 480 px wide, 0 to 50 km/h, thick #00B7FF progress arc on a dark grey
  track, a short green tick at 20 km/h (recommended speed) and a yellow tick at 42 km/h (speed cap).
  In the middle "25" in 140 px bold white and "km/h" 24 px below.
- Above the gauge: left and right indicator arrows and a 56 px gear circle "D" in green between them.
  Only lit warning lights shown, 32 px (for example a yellow park brake symbol when parked).
- Under the gauge a pair of glance values, 36 px bold with 18 px labels: "Range 55.9 km" and
  "Battery 80 %".
- An advice strip 64 px tall across the width under the gear row, left edge amber: "Slow to 20 km/h,
  speed bumps ahead on Main Road" in 22 px.
- Right third: next turn card, 300 x 160 px: right-turn arrow 64 px, "230 m" 40 px bold, "Station Road"
  20 px.
- Left third: nearest obstacle card, 300 x 160 px, red: "RIGHT 0.4 m" 40 px bold, "Time-of-flight" 14 px.
- Brake and accelerator as two short vertical bars 24 x 300 px beside the gauge, "0 %" and "40 %" 18 px.

Do not change the colours, gauge style, font or card style. Do not add maps or photos on this screen.
```

### 3.3 Analytics

```
Screen: Analytics, 1280 x 800 landscape, same frame and identity. Source chip LIVE.

Title "Analytics" top left. A vertical carousel of cards: one large card 900 x 480 px in the centre,
the previous and next cards peeking 60 px above and below, dimmed. Centre card "BATTERY % (SOC)" with
a soft green vertical gradient over #151C24, a green battery icon, value "80 %" in 96 px bold, context
line "5.8 of 7.2 kWh left · about 56 km" 18 px, and a thin 5 minute sparkline across the bottom of the
card (falling slowly from 84 to 80). Right side: 64 x 64 up and down arrow buttons and position dots
12 px with the label "Battery" next to the active dot. Other cards in the loop: Battery temp 32 °C
(amber gradient), Ambient temp 19 °C, Odometer 1,284.6 km, Battery output 1.5 kW, Consumption 45 Wh/km,
Driver insights, Graphs.

Also design the Graphs view: "Back" button 64 px tall top left, 2 x 2 chart cards: Speed vs time
(0 to 50 km/h, now 25 km/h), Battery % vs time (0 to 100, now 80 %), Distance vs time (now 12.3 km),
Consumption vs time (0 to 120 Wh/km, now 45 Wh/km), 5 minute window chip in each, axis text 12 px,
current value 24 px top right of each chart.

Keep the gradient cards and colours exactly; only change sizes and spacing.
```

### 3.4 Diagnostics

```
Screen: Diagnostics, 1280 x 800 landscape, same frame and identity. Parked use, for the engineer.
Source chip SIMULATED and yellow strip visible.

Title "System Diagnostics". Four cards in a 2 x 2 grid, each with a header in 13 px accent caps and a
status dot:
- DRIVE: Speed 25.0 km/h, Gear D, Throttle 40 %, Brake 0 %, Power +1.5 kW.
- ENERGY: Battery SOC 79.9 %, Battery temp 32 °C, Motor temp 48 °C, Range 55.9 km, Charging No.
- POSITION: GPS -33.95856, 18.46000, Altitude Unavailable, Odometer 0.16 km, Incline Unavailable.
- LINK: Pi 4 Offline (grey chip), ESP32 age --, MQTT --, Signal --, IMU rate --, IMU drops --.
Labels 13 px #A3A6AA left, values 18 px bold right aligned; "Unavailable" and "--" in #A3A6AA.
Under the grid a collapsed 64 px row "Details: ASIS, route and voice" with a chevron.

Keep the team's card style; no new colours.
```

### 3.5 Navigation (map)

```
Screen: Navigation, 1280 x 800 landscape, same frame and identity. A full-width OpenStreetMap-style
street map of the University of Cape Town and Rondebosch, Cape Town (Rhodes Drive, Woolsack Drive,
Main Road, Station Road), heading-up, with the vehicle as a blue and white navigation arrow at 70 % of
the height and the route as a thick #00B7FF line ahead of it. Source chip SIMULATED, yellow strip.

Overlays:
- Top left at 24 px: green turn banner #17703E, 520 x 128 px, white right-turn arrow 64 px, "230 m"
  48 px bold, "Turn right onto Station Road" 24 px; under it a #0F4F2B strip 40 px "Then: arrive at
  destination" 18 px.
- Right column of square 64 x 64 buttons, #151C24 with border, 12 px gaps: Follow (selected, accent
  outline), Overview, +, -; a compass 56 px above them.
- Bottom centre ETA bar 560 x 72 px, #151C24: at its left a yellow segment "SIMULATED", then "2 min"
  36 px green, "630 m" 24 px, "arrive 14:28" 24 px.
- Bottom right "End simulation" button 200 x 64 px, #151C24 with a 2 px yellow border.
- A 64 x 64 search button top left under the turn banner (the full search bar only shows when no route is
  set).
- Obstacle pill in the status bar: "OBSTACLE 0.9 M LEFT".
Map attribution "© OpenStreetMap contributors" small, bottom right.

Do not cover the road ahead of the arrow with any overlay. Keep the green banner colours.
```

### 3.6 Destination search (overlay on Navigation)

```
Screen: Navigation with search open, 1280 x 800 landscape, same frame and identity, source chip LIVE.
Top: search field 64 px tall, 760 px wide, text "cav", and a "Navigate" button 120 x 48 #00B7FF.
Below: a results card 760 px wide, four rows 72 px each: first "From: Current location (GPS)" in accent;
then "Cavendish Square" 20 px bold / "Dreyer Street, Claremont, Cape Town" 16 px dim / "2.6 km" 16 px right
aligned, blue pin; "Cavendish Close" / "Cavendish Street, Claremont" / "2.4 km"; "Main Road, Rondebosch" /
"offline map" / "1.1 km", grey pin. A "More results" row.
Bottom half: the team's dark on-screen keyboard, keys about 120 x 86 px, 22 px labels, rows QWERTY,
Shift, Backspace, 123, Clear, Space, Enter, Hide.
Before typing (second variant): 64 px recent place chips "UCT Upper Campus", "Main Road, Rondebosch",
"Cavendish Square".
```

### 3.7 Front camera

```
Screen: Front camera, 1280 x 800 landscape, same frame and identity, source chip LIVE.
Title "Front camera" with a status chip to its right "Live · 7.0 fps" (green, 28 px tall).
Left: the camera video at 4:3, about 860 x 645 px, a street scene on Main Road, Rondebosch with thin
coloured detection boxes labelled "person" and "bicycle".
Right: an Alerts card 340 px wide. Rows 64 px tall, nearest first, each with a 12 px coloured bar on the
left: "Person" 22 px bold, "Immediate · under 3 m" 18 px, "63 %" 14 px dim (red, row filled #A3201A);
"Bicycle", "Warning · under 8 m", "55 %" (amber bar); "Car", "Monitoring · under 15 m", "71 %" (green bar).
Footer line 14 px dim "180 ms sensor to screen".
Empty state variant: "No hazards" 20 px centred in the card.
Keep the colours and card style.
```

### 3.8 Sensors

```
Screen: Sensors, 1280 x 800 landscape, same frame and identity, source chip LIVE.
Title "Sensors" and a link chip top right "Live" (green, 120 x 36).
Top card "AROUND THE TUK-TUK (ToF)": a simple top-down outline of a tuk-tuk (three wheels, front
narrow) about 360 x 300 px, with three zones: left zone amber "0.9 m", front zone clear grey "clear",
right zone red "0.4 m"; distances 40 px bold. Legend 14 px: amber under 1.0 m, red under 0.5 m, sensors
reach 1.2 m.
Right of it, "HAZARDS (CAMERA + ToF)" list 760 px wide, rows 64 px: "Obstacle right 0.4 m · ToF" red;
"Person ahead · Immediate · camera" red; "Bicycle · Warning · camera" amber.
Below the fold, smaller cards: VEHICLE (Battery 80 %, Voltage 74.2 V, Current 20.8 A, Motor 48 °C),
POSITION (GPS fix 3D, -33.95856, 18.46000, heading 92°, altitude 41 m), RIDE AND LINK (Vibration
0.035 m/s², IMU rate 200 Hz, IMU drops 0, ESP32 age 0.4 s). Labels 13 px, values 18 px.
Keep accent caps section titles and the card style.
```

### 3.9 Charging

```
Screen: Charging, 1280 x 800 landscape, same frame and identity, source chip LIVE.
Left half: keep the team's large cyan (#00E5FF) ring with the glowing green outline of the tuk-tuk inside
it, "80 %" 48 px bold green at the top, and "5.8 of 7.2 kWh" 20 px under it. Four values on the ring
sides, 28 px bold with 14 px labels: Power input 1.8 kW, Voltage 74.2 V, Current 24.3 A, Cell health 98 %.
Right half: title "Charging" 24 px, state "Charging · solar" 18 px green; one chip "Source: Solar";
a "Power input (kW)" line chart card (last 10 minutes, around 1.8 kW); tiles 28 px values: Time to full
1 h 35 min, Charging power 1.8 kW, Range added +12.4 km, Energy delivered 1.06 kWh; pack temperature bar
32.8 °C in green.
Not charging variant: state "Not charging", values "--", chart says "No charging data".
Numbers may use a monospace font (JetBrains Mono) as the team does; everything else Inter.
Keep the ring and illustration.
```

### 3.10 Settings

```
Screen: Settings, 1280 x 800 landscape, same frame and identity. Parked use.
Title "Settings". Two columns of cards, section titles 13 px accent caps:
Left: DISPLAY (Fullscreen toggle on, Hide cursor toggle on, Brightness slider 100 %), VOICE (Voice
en-ZA Leah, Provider gTTS, Speech speed 1.00x, Volume 80 %, "Test voice" button), DRIVER ASSISTANCE (Voice
alerts toggle on, "Repeat last warning" button).
Right: NAVIGATION (Map source "Offline tiles", Route source "Offline roads", Auto follow toggle on),
COLOUR THEME (twelve palette swatches in three columns: Electric Blue selected, Solar Orange, Forest Green,
Neon Purple, Arctic White, Crimson Performance, Neon Pink, Rose Gold, Sunset Orange, Purple EV, Matrix
Green, Iron Man).
Rows 64 px tall, toggles 64 x 36, slider handles 44 px, drop-downs 56 px. A small note "Changes save
automatically" instead of a Save button.
```

---

## 4. How to use it in Stitch

1. Go to stitch.withgoogle.com and sign in with a Google account.
2. Start a new project. Choose the web (desktop) option rather than mobile, since the screen is landscape;
   the prompt fixes the size at 1280 x 800. If Stitch offers a model choice, the higher quality
   (experimental) mode accepts a reference image: upload tests/sim_sync/sim_driving.png with the Driving
   prompt so it copies the existing look.
3. Paste the overall prompt (3.1) and let it generate. Check the colours against the table in section 2
   before going further; if it drifts (light theme, purple, new fonts), reply "keep #0A0F14 background,
   #151C24 cards, #00B7FF accent, Inter font".
4. Paste one page prompt at a time (3.2 to 3.10). Ask for the obstacle pill and SIMULATED variants where the
   prompt mentions them. Small fixes work best as short follow-ups ("make the Follow button 64 x 64").
5. Export: download each screen as an image (PNG), and if useful use the copy to Figma option. Save them in
   Presentation/mockups/stitch/ with the page name.
6. Bring the images back for a review against this file before any code change. Stitch output is a picture
   and HTML, not PySide6; changes are then made by hand in the SW-7 patch layer, one page at a time, with the
   student's approval, and the team's own copy stays untouched.
