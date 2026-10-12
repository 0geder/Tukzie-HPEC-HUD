# Data ownership and page merge plan (12 Oct 2026)

## What the student asked for

> some things are better off merged otherwise we have clutter when we have this in a real setup. some data are
> redundant in different pages which should not be the case, check them out

Not a demand for fewer pages, but merges where they make sense. This plan is for a driver glancing at a 10.1 inch
1280 x 800 screen in a moving tuk-tuk, not for a bench engineer. It is a plan only: no code was changed.

Sources read:
- Screenshots: `DashboardIntegration/tests/layout/{drive,frame,map,pages}/after_*.png` (latest layout pass).
- Our code: `DashboardIntegration/*.py` and `tests/dashboard_patches.py`.
- The team's pages (read only): `scratchpad/v11c/Dashboard/app/pages/*.py` and `app/widgets/status_bar.py`.
  Below, "team:" means a path under that `app/` folder.
- Inspiration: `Planning/inspo/inspo_sports_car_tiles.jpg` (speed, rpm and gear pills over a top-down car with the
  four tyre pressures placed at the wheels, map and media tiles beside it), `inspo_honda_e_home.jpg` (home screen of
  tiles: car and battery with km remaining, a big speed tile, a map with the next manoeuvre and ETA, weather; a
  five-icon dock), `inspo_three_column_cluster.jpg` (navigation left, speed dial centre, vehicle status right with
  a ">" on each row that opens its detail).
- The paper and depth theme (`Planning/paper-depth-theme-prompt.md` sections 3 to 5): one subject per page in the
  middle plane, one signal colour that only means "tap this", one hero value per page at 120 to 180 px and
  everything else at 13, 16 or 22 px. All three rules push the same way as this plan: one value, one home.

## 1. Where every data item appears today

Pages in carousel order: Drive, Analytics, Diagnostics, Map, Camera, Sensors, Charging, Settings. "Bar" is the
status bar plus the overlays (SIMULATED strip, obstacle pill). Reverse is the team's page that opens by itself in
gear R.

Key: H = hero or main element, V = value, g = glance (icon, chip, colour, short word), c = chart, d = only inside
the folded "Show advice and details" list on Diagnostics, 2x / 3x = shown that many times on the same page.

| Item | Bar | Drive | Analytics | Diag | Map | Camera | Sensors | Charging | Settings | Times | Where in the code |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Speed | | H | c | V | | | V (GNSS raw) | | | 4 | sw7_driving.py install_layout; sw7_analytics.py:641 (Graphs); sw7_layout_pages.py:32; sensors_page.py:349 |
| Gear | | V | | V | | | | | | 2 (+Reverse) | team: driving_page.py:110; sw7_layout_pages.py:32; team: reverse_camera_page.py:872 |
| Throttle, brake | | V (pedal bars) | | V | | | | | | 2 | sw7_driving.py:369-372 (no pedal sensors, see its docstring); sw7_layout_pages.py:32 |
| Turn signals, fault icons (lights, park brake, belt, door, tyre, battery temp, motor temp) | | g | | | | | | | | 1 | team: driving_page.py:120-138 |
| State of charge % | V | V | H + c | V | g (arrival %) | | V (BMS raw) | H (ring) | | 7 | team: status_bar.py:28; sw7_driving.py RangeBatteryPair; team: analytics_page.py:187; sw7_layout_pages.py:33; sensors_page.py:347; sw7_layout_frame.py paint_ring_soc |
| Energy "5.7 of 7.2 kWh" | | | V | | | | | V | | 2 | sw7_analytics.py:413-424; sw7_layout_frame.py (ring) |
| Range | | V | g ("about 56 km") | V | | | | V (range added) | | 3 (+1) | sw7_driving.py RangeBatteryPair; sw7_analytics.py:424; sw7_layout_pages.py:33 |
| Battery power | | | V ("Battery output", 0 or more) | V (signed) | | | | 3x (ring "Power input", "Charging power" tile, power chart) | | 5 | team: analytics_page.py:191,267; team: diagnostics_page.py:13; team: charging_page.py:309,568,764 |
| Consumption Wh/km | | | V + c | | | | | | | 1 | team: analytics_page.py:192 |
| Pack voltage, current | | | | | | | V (BMS) | V (ring, charger V and A, "--" unless charging) | | 2 | sensors_page.py:347; team: charging_page.py:310-311,725-744 |
| Battery temperature | | g (icon at 45 / 55 C) | V | V | | | | V (pack temp bar) | | 4 | team: analytics_page.py:188; sw7_layout_pages.py:33; team: charging_page.py:753 |
| Motor temperature | | g (icon) | | V | | | | | | 2 | team: driving_page.py:136; sw7_layout_pages.py:33 |
| Ambient (vehicle sensor) | | | V | V | | | | | | 2 | team: analytics_page.py:189; sw7_layout_pages.py:33 |
| Outside temp (weather service) | V ("UCT 17°C") | | | | | | | | | 1 | team: status_bar.py:25,37 |
| Cell health (SOH) | | | | | | | | V | | 1 | team: charging_page.py:324 |
| Motor rpm | | | | | | | V | | | 1 | sensors_page.py:348 |
| Odometer | | | V (+ trip) + c | V | | | | | | 2 | sw7_analytics.py:434; sw7_layout_pages.py:34 |
| Trip summary | | | V (insights) | | | | | | | 1 | team: analytics_page.py:286 |
| GPS lat, lon | | | | V (+ d coordinates) | marker | | V | | | 2 (+d) | sw7_layout_pages.py:34; sensors_page.py:349 |
| GPS fix, network position | | | | | g (circle) | | V | | | 1 | sensors_page.py:126,349 |
| Altitude | | | | V | g (ALT chip) | | V | | | 3 | sw7_layout_pages.py:34; sw7_tile_map.py:71,516; sensors_page.py:350 |
| Heading | | | | | g (compass, heading-up) | | V | | | 2 | sensors_page.py:349; sw7_tile_map.py:507 |
| Incline | | | | V | | | | | | 1 | sw7_layout_pages.py:34 |
| ToF left, ahead, right | g (pill) | | | (built, hidden) | | | H (top-down) | | | 1 + pill | sensors_page.py tof_metres; ride_quality_card.py (hidden by sw7_layout_pages.py:105-106) |
| Camera detections | g (pill) | | | | | V (alert list) | V (fused hazards list) | | | 2 + pill | front_camera_page.py; sensors_page.py:337,477 |
| Obstacle pill | on every page except Sensors | | | | | | | | | | sensors_page.py HazardBanner; patch at dashboard_patches.py:463 |
| Vibration, IMU disagreement | | | | (built, hidden) | | | V | | | 1 | sensors_page.py:352 |
| IMU rate, IMU drops | | | | V | | | V | | | 2 | sw7_layout_pages.py:37; sensors_page.py:353 |
| Signal (CSQ), MQTT, ESP32 age | | | | V | | | V | | | 2 | sw7_layout_pages.py:37; sensors_page.py:353-354 |
| Firmware, BMS age | | | | | | | V | | | 1 | sensors_page.py:348,354 |
| Link state (Live / stale / offline) | g (amber pill when lost) | | | V | | g (camera chip) | g (Live pill) | | | 3 | sw7_layout_pages.py:43; sensors_page.py:52; front_camera_page.py |
| Pi 4 status, address | | | | V + d | | | | | | 1 | sw7_layout_pages.py:52,216 |
| Data source (LIVE / REPLAY / NO DATA / SIMULATED) | g (chip) + strip | | | V ("Data") + d (raw) | g (SIMULATED in ETA bar) | | g (REPLAY) | | | 4 | sw7_sim_link.py:249; sw7_layout_pages.py:32,183 |
| Charging yes / no | g (battery icon) | | | V | | | | 2x ("Not charging" line, ring "STANDBY") | | 3 | sw7_layout_pages.py:33; team: charging_page.py:766-775 |
| Charging source | | | | d (raw) | | | | V ("Source:") | | 2 | sw7_layout_pages.py:41; sw7_layout_frame.py |
| Time to full | | | | | | | | 2x (ring "Est. ETA", "Time to full" tile) | | 2 | team: charging_page.py:323,768 |
| Next turn | | | | | H (banner) + voice | | | | | 1 | sw7_tile_map.py; sw7_voice_guide.py |
| Route remaining, ETA | | V (route line) | V (insights) | d | 2x (status line, ETA bar) | | | | | 5 | team: driving_page.py:156-158; team: analytics_page.py:276-284; team: navigation_page.py:309 |
| Arrival state of charge | | | V (insights) | | V (status line) | | | | | 2 | team: analytics_page.py:279; team: navigation_page.py:309 |
| ASIS advice, recommended speed | | H (strip, dial tick, "Hold about") | | d | | | | | | 1 (+d) | sw7_driving.py _make_advice_strip; team: diagnostics_page.py:34 |
| Voice status | | | | d | | | | | V (Test voice) | 2 | team: diagnostics_page.py:53 |
| Map follow | | | | d | V (Follow button) | | | | V (toggle) | 3 | team: settings_page.py:121; sw7_tile_map.py |
| Camera fps, latency | | | | | | V | | | | 1 | front_camera_page.py |

Things the screenshots show that the table alone does not:
- Two outside temperatures disagree on one screen: `pages/after_diagnostics.png` has "UCT 17°C" in the bar and
  "Ambient 23 °C" in the Energy card. One is the weather service, the other the vehicle sensor, and neither says so.
- The Map shows two different route summaries at once: `map/after_navigation.png` has "1.6 km · 4 min · arrival 78 %"
  bottom left (the plan when it was made) and "3 min · 1.3 km · arrive 11:21" in the ETA bar (live).
- On Drive, Analytics and Charging the battery percent is on screen twice at once (bar plus page), and on Charging it
  is the same "5.7 of 7.2 kWh" line that Analytics also prints.
- Charging prints the charger voltage and current, which are "--" unless charging, while Sensors prints the pack
  voltage and current from the BMS ("74.2 V"). A driver sees "-- V" on the battery page while the BMS knows the value.
- During a simulated drive the Sensors "Battery" value stays live (it reads raw telemetry) while every other battery
  figure is simulated, so the same label shows two different numbers.
- The layout brief said Diagnostics would drop "duplicates of Sensors"; it moved link health into a Link card, but
  Sensors still has its own Ride and link card with the same five values.

## 2. One home per item

Rule: every item has one home page where it is shown in full. Anywhere else it may only be a glance (one word, an
icon, a colour, or one value) that taps through to its home, and never on the same screen as its home value. Two
exceptions: critical alerts may repeat (the obstacle pill is an alert, not a reading), and the folded raw list on
Diagnostics may hold every field for bench work, because it is hidden until asked for.

Home names below use option B's pages; the option A home is in brackets where it differs.

| Item | Home | Glance allowed (taps to home) | Remove (pure duplicate) |
|---|---|---|---|
| Speed | Home (Drive) | none | Diagnostics Drive card row. Keep GNSS raw speed in System only, labelled raw |
| Gear, turn signals, fault icons | Home (Drive) | Reverse page gear box (team) | Diagnostics Gear row |
| Throttle, brake | System raw list | none | Drive pedal bars (no pedal sensors on the vehicle, so they only show "--" live) |
| State of charge % | status bar (one number, every page) | Home battery tile as a bar only; Map arrival % stays as a different value | Drive "BATTERY 80 %", Analytics Battery % hero card, Diagnostics SOC row, Sensors Battery row. The Energy ring keeps its big figure as the page hero |
| Energy kWh left | Energy (Charging) | none | Analytics context line |
| Range | Energy (Charging) | Home battery tile (Drive range value) | Analytics "about 56 km", Diagnostics Range row |
| Battery power (signed) | Energy (Analytics card "Battery output") | Home battery tile, small "-1.7 kW" | Diagnostics Power row; on Charging the "Charging power" tile (ring plus chart are enough) |
| Consumption | Energy (Analytics) | none | none |
| Pack voltage, current | Energy (Charging ring, fed from the BMS always, charger values while charging) | none | Sensors Vehicle card voltage and current |
| Battery temperature | Energy (Charging pack temp bar) | Home fault icon at 45 / 55 C | Analytics Battery temp card, Diagnostics row |
| Motor temperature | System (Diagnostics) | Home fault icon | none |
| Ambient sensor | System, labelled "Ambient sensor" | none | Analytics Ambient temp card |
| Outside weather | status bar, tap opens the weather sheet (paper theme section 6) | Home weather tile shows the forecast only, not the current temperature | none |
| Cell health, BMS age, rpm, firmware | System (Hardware card) | none | none (they move from Sensors) |
| Odometer, trip | Energy (Analytics, "Energy and trip") | none | Diagnostics Odometer row |
| GPS, fix, altitude, heading, incline | System (Position card, one card) | Map marker and compass only | Sensors Position card; Map ALT chip; Diagnostics coordinates in the raw list stay (d) |
| ToF left, ahead, right | Surroundings (Sensors) | Home "Around" tile with the three numbers; obstacle pill when immediate | Diagnostics ride card (already hidden, keep it as the telemetry sink, see risks) |
| Camera and fused hazards | Surroundings, one list | Home Around tile shows the nearest; obstacle pill | The second list: Camera alert list and Sensors hazards list become one |
| Vibration, IMU disagreement | Surroundings (Ride row) in A; System in B | none | none |
| IMU rate and drops, signal, MQTT, ESP32 age | System (Link card) | none | Sensors Ride and link card copies |
| Link state | System (Link card) | status bar chip and the amber pill; a "Sensors live" word on Surroundings | Diagnostics "Data" row (raw value stays in d) |
| Pi 4 status | System (Link card) | none | none |
| Data source | status bar chip and SIMULATED strip | Map ETA bar "SIMULATED" | Diagnostics Drive card "Data" row |
| Charging yes / no, source, time to full | Energy (Charging) | battery icon in the status bar | Diagnostics Charging row; the ring "STANDBY" word or the state line (keep one); the "Time to full" tile (the ring has Est. ETA) |
| Next turn | Map | Home next-turn tile; voice | none |
| Route remaining, ETA, arrival % | Map ETA bar | Home next-turn tile, one line | Map status-line km and min (keep only "offline router"), Drive route line, Analytics insights live route text (keep the latest-trip summary) |
| ASIS advice | Home (Drive) strip | voice | none (raw stays in d) |
| Voice, map follow | System Settings | Map Follow button (it is the live mode; the setting is the start-up default, rename it "Start the map in follow mode") | none |

## 3. Top redundancies, ranked by what a driver notices

1. Battery percent in 7 places, and twice on one screen on Drive, Analytics and Charging.
2. Link health (IMU rate, drops, signal, MQTT, ESP32 age) as two full cards, on Diagnostics and on Sensors.
3. Route remaining and ETA in 5 places, twice on the Map with different numbers.
4. Two outside temperatures (weather 17 °C, sensor 23 °C) with nothing to say which is which.
5. Charging page repeats itself: power three times, time to full twice, charging state twice.
6. Position (lat, lon, altitude) on Diagnostics, Sensors and the Map chip; Sensors adds heading and fix.
7. Hazards as two lists (Camera alerts and Sensors hazards), plus the pill.
8. Diagnostics Drive and Energy cards repeat what Drive and Charging already show (speed, gear, SOC, range, power,
   battery temp, odometer).

Also worth fixing: the pedal bars on Drive have no sensor behind them, and the Sensors battery stays live during a
simulated drive while everything else is simulated.

## 4. Option A: light merge (keep 8 pages)

Pages and swipe order unchanged: Drive, Analytics, Diagnostics, Map, Camera, Sensors, Charging, Settings.

What changes:
- Drive: the pedal bars go. In their place two tiles beside the dial: Next turn (left, taps to Map) and Around
  (right, the three ToF numbers round a small tuk-tuk, taps to Sensors). Under the dial only Range, which taps to
  Charging. "BATTERY 80 %" and the route line go (the bar has the percent, the next-turn tile has the route).
- Analytics: from 8 cards to 5. Battery %, Battery temp and Ambient temp go. The context line under the cards loses
  "5.7 of 7.2 kWh". Insights keep only the latest-trip summary.
- Diagnostics: the Drive card becomes Controls (throttle, brake, signed power); the Energy card becomes Health
  (motor temp, ambient sensor, cell health, BMS age, rpm); Position gains fix, heading and raw GNSS speed; Link gains
  firmware. Speed, gear, SOC, range, battery temp, odometer, charging and data source leave the cards and stay only
  in the folded raw list.
- Map: the bottom-left status line keeps only the route source and offline words; arrival percent moves into the
  ETA bar ("arrive 11:21 · 78 %"). The ALT chip goes.
- Camera: unchanged (its list labels what the boxes in the video are).
- Sensors: the Vehicle, Position and Ride and link cards go, apart from a one-line Ride row (vibration, IMU
  disagreement). The page becomes the tuk-tuk, the hazards list and that row.
- Charging: one power figure and one time-to-full figure. The ring's voltage and current read the BMS when not
  charging. The "Charging power" and "Time to full" tiles go; their slots show Range and Power now.
- Status bar: the weather text says what it is ("Outside 17°"), and the sensor value is "Ambient sensor" on
  Diagnostics.
- Tap-through: every glance tile shows a small signal-coloured ">" (as in the three-column cluster). Under the paper
  theme only the chevron is signal coloured, so the tile stays ink and paper and the signal rule holds.

Home (Drive) at 1280 x 800, option A:

```
0    +------------------------------------------------------------------------------------------+
     | Outside 17°   [ LIVE ]   82 % [###]                     [ OBSTACLE 0.5 m AHEAD  Hide ]  14:28 |
48   +------------------------------------------------------------------------------------------+
     | ADVICE   Slow to 20 km/h, speed bumps ahead on Main Road               Hold about 20  1/2   |
112  +------------------------------------------------------------------------------------------+
     |                        <=   ( D )   =>        fault icons                                |
     |                                                                                          |
     |  +---------------------+          .---------------.           +---------------------+   |
     |  | NEXT TURN         > |        /                   \         | AROUND            > |   |
     |  |                     |       |                     |        |       0.45 m        |   |
     |  |  ->  400 m          |       |         25          |        |       +-----+       |   |
     |  |  University Avenue  |       |        km/h         |        | 0.90  | tuk | Clear |   |
     |  |  3 min . arr 11:21  |        \    20 limit       /         |       +-----+       |   |
     |  +---------------------+          '---------------'           +---------------------+   |
     |                                                                                          |
     |                                 56 km   RANGE  >                                         |
728  +------------------------------------------------------------------------------------------+
     | <  Drive  Analytics  Diagnostics  Map  Camera  Sensors  Charging  Settings  >            |
800  +------------------------------------------------------------------------------------------+
```

Tiles are about 300 x 260 px, the dial about 420 px across, so the speed stays the one hero. With no route, the
next-turn tile says "No route" and taps to the Map search.

Deleted in A: pedal bars, Drive battery figure and route line, three Analytics cards, the Sensors Vehicle and
Position cards and most of Ride and link, the Diagnostics duplicate rows, the Map ALT chip and duplicate status-line
numbers, two Charging tiles.

Risks in A:
- Simulated-drive sync: `test_sim_sync.py` checks that speed, battery, range and power change on every page
  (`PAGES` at line 62). With fewer copies it must check each item on its home and glance only. The Sensors battery
  live versus simulated clash disappears because that row goes.
- Swipe order: unchanged.
- Tests to update: test_layout_drive (pedal bars, range and battery pair), test_analytics_carousel (`car.count == 8`
  at line 83 becomes 5, and the card names), test_layout_pages (Diagnostics card rows, Sensors cards),
  test_layout_map (status line text, ALT chip), test_layout_frame (Charging tiles), test_live_data_provider (it
  reads `diagnostics._values` by name at line 408 and the raw Source; keep the names in the hidden list),
  test_sim_sync.
- Team ownership: Drive, Analytics, Diagnostics, Charging and Map overlays are the team's pages. Everything stays
  as patches and SW-7 wrappers behind a switch (for example `TUKZIE_SW7_DEDUP=0` gives today's pages), as with
  the layout pass. Removing a card means hiding it, not deleting the team's code.

## 5. Option B: real merge (5 pages)

Pages in swipe order: Home, Map, Surroundings, Energy, System. Home and Map sit next to each other because they are
what a driver uses while moving; System is last.

| New page | Built from | Middle-plane subject (paper theme) | Hero value |
|---|---|---|---|
| Home | Drive | speed | speed |
| Map | Map (unchanged apart from section 4's Map fixes) | the map slab | next-turn distance |
| Surroundings | Camera + Sensors | tuk-tuk from above beside the video | nearest distance |
| Energy | Charging + the battery half of Analytics | battery ring | state of charge |
| System | Diagnostics + Settings (two tabs: Status, Settings) | the cards as a group | none (a status page) |

What moves where:
- Home: speed, gear, turn signals and fault icons, the advice strip, and four tiles: Next turn (Map), Battery
  (range, a bar for the percent, power now; taps to Energy), Around (three ToF numbers placed round a top-down tuk-tuk
  like the tyre pressures in inspo_sports_car_tiles, the nearest hazard under it, taps to Surroundings), Weather (the
  next hours, not the current temperature, taps to the weather sheet).
- Surroundings: the camera video left, the tuk-tuk with the three ToF arcs right, and one hazard list underneath
  (camera, ToF and fused, nearest first; the camera list's confidence moves into each row). A one-line Ride row
  (vibration, IMU disagreement) at the bottom. The camera fps and "Sensors live" chips sit in the header.
- Energy: the Charging ring on the left as the hero (SOC, kWh, pack voltage and current from the BMS, cell health).
  The right column changes with the state: while charging it is the team's charging column (source, power chart,
  time to full, range added, energy delivered); while driving it is the Analytics carousel with Power now,
  Consumption, Odometer and trip, Graphs and Driver insights. A two-item switch at the top ("Charging", "Driving")
  lets the driver pick by hand. Battery temperature is the pack temp bar under the ring.
- System, Status tab: Health (motor temp, ambient sensor, cell health, BMS age, rpm), Position (GPS and fix, heading,
  altitude, incline, raw GNSS speed), Link (Pi 4, link, ESP32 age, MQTT, signal, IMU rate and drops, firmware),
  Controls (throttle, brake, signed power), then the folded raw list and ASIS details as today. Settings tab: the
  team's Settings page as it is.
- Reverse: still opens by itself in R and closes on leaving R; not in the swipe order.
- Obstacle pill: still on every page, still top right; tapping opens Surroundings; hidden only on Surroundings.

Deleted in B: everything deleted in A, plus the Analytics page as its own page (its battery cards go, the rest
moves to Energy), the Camera alert list as a separate list, the Sensors Vehicle and Position cards, the Diagnostics
Drive and Energy cards as they are now, and three nav items.

Home at 1280 x 800, option B (three columns, after inspo_three_column_cluster and inspo_honda_e_home):

```
0    +------------------------------------------------------------------------------------------+
     | 14:28    Outside 17°  Rondebosch      [ LIVE ]   82 % [###]      [ OBSTACLE 0.5 m  Hide ]  |
48   +------------------------------------------------------------------------------------------+
     | ADVICE   Slow to 20 km/h, speed bumps ahead on Main Road                  Hold about 20   |
112  +-----------------------------+  +------------------------------+  +------------------------+
     | NEXT TURN                 > |  |     <=     ( D )     =>      |  | BATTERY              > |
     |  +-----------------------+  |  |                              |  |  56 km                 |
     |  |  mini map, route line |  |  |                              |  |  [##########-----]     |
     |  |          ^            |  |  |            25                |  |  -1.7 kW now           |
     |  +-----------------------+  |  |           km/h               |  +------------------------+
     |  ->  400 m                  |  |                              |  | AROUND               > |
     |  University Avenue          |  |         20 limit             |  |         0.45           |
     |  3 min . 1.3 km . 11:21     |  |                              |  |       +-----+          |
     +-----------------------------+  |   fault icons (only lit      |  |  0.90 | tuk | Clear    |
     | WEATHER                   > |  |   ones shown)                |  |       +-----+          |
     |  Rain from 15:00, wind 20   |  |                              |  |  Person 2.6 m ahead    |
     +-----------------------------+  +------------------------------+  +------------------------+
728  +------------------------------------------------------------------------------------------+
     |        ( Home )        Map        Surroundings        Energy        System                 |
800  +------------------------------------------------------------------------------------------+
```

Columns about 400, 432 and 400 px with 16 px gaps and 24 px margins. Speed at 160 px is the only hero; tile values at
22 px, labels at 13 px (paper theme section 5). In the Around tile the tuk-tuk is drawn from above with each distance
at its sensor, coloured by band, and the whole tile turns to the critical mark when a hazard is immediate. The nav
bar has five items, so each one is about 230 px wide, far above the 64 px minimum.

Risks in B:
- Simulated-drive sync: the dispatcher (`dashboard_main._on_vehicle_state`, patched by SIM_LINK_PATCHES) calls
  `self.driving`, `self.analytics`, `self.charging` and the rest by name. The merged pages must host the team's page
  objects (re-parented inside a container), not replace them, so those calls and `sim_view` keep working and the
  Analytics charts still lose their simulated points on End simulation.
- Swipe order: `sw7_page_swipe.py:104` reads `normal_ids`, so the swipe follows a new list on its own, but every
  `switch_page_id("sensors")`, `("diagnostics")` and `("navigation")` call (hazard pill, search, tests) needs a map
  from old ids to new pages. Three-finger swipe on the Map is unaffected.
- Telemetry wiring: `diagnostics.ride_card` is the sink the Link card reads (`sw7_layout_pages.py:207`) and
  test_live_data_provider waits on it (line 317). It must stay, hidden, inside System.
- Tests to update: all of option A's, plus test_layout_frame (nav items and their widths), test_sim_sync (`PAGES`
  and the swipe checks), test_search (switching to the map), test_front_camera_page and test_front_camera_page_live
  (the camera now inside Surroundings), and new tests for Home and the old-id mapping. Screenshots in a new
  `tests/merge/` folder.
- Team ownership: this changes how the team's product is organised, not only how it looks. Their Driving, Analytics,
  Diagnostics, Charging and Settings pages survive as objects but stop being nav items. It needs the team's
  agreement before the presentations on 16 and 17 Nov, and a switch (for example `TUKZIE_SW7_PAGES=classic`) that
  gives back the 8-page dashboard exactly, so the team can still demo their pages.
- Report and slides: the report's screenshots and page descriptions, and the deck, poster and Q&A notes, all name
  the 8 pages and would need updating.
- Effort: Home and the Surroundings and Energy containers are new widgets, on top of the paper theme work that is
  being built now. Doing both at once means two agents in the same pages.

## 6. Recommendation

Do option A now, and build option B's Home as the Drive page's next step rather than as a 5-page rebuild.

Reasons:
- A removes every pure duplicate in section 3 and fixes the two wrong-looking screens (two route summaries on the
  Map, two outside temperatures) with hide-and-relabel patches the team can switch off. It keeps the swipe order, the
  team's pages and most tests.
- A's Drive tiles (Next turn, Around, Range) are the same widgets B's Home needs, so A is a step toward B, not a
  detour.
- B's biggest win is Surroundings (camera and sensors are one question: what is around me), and that can be done
  inside A as a second step: put the Camera video into the Sensors page and drop the Camera nav item, giving 7 pages,
  without touching any team page.
- Energy and System merges touch four team pages and the report; leave them as a proposal to the team, with
  the classic switch, after the presentations.

Order of work, so it fits with the paper theme pass:
1. Agree the homes in section 2 with the student (and the team for their pages).
2. Option A dedup as one patch group behind `TUKZIE_SW7_DEDUP`, written against the paper theme's type scale so the
   tiles are 22 px values and 13 px labels from the start.
3. Surroundings (Camera into Sensors), 7 pages.
4. If wanted after the demo: Home as in option B, Energy and System merges behind `TUKZIE_SW7_PAGES`.

When any of this lands, the deck, poster, talking points and Q&A prep need the new page list and screenshots too.
