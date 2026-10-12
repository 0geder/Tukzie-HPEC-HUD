# Paper and depth theme for the dashboard (12 Oct 2026)

## What the student asked for

> check out thetheme.jpg in the projects folder and apply that theme to all the pages in the DashboardIntegration.
> Since I feel like the whole pages feel flat so we are designing this in 3 planes sth like type in the back subject
> in the middle and the buttons on top where the overlap makes the screen feel deep. where people or the driver can't
> tell what to tap we need to pick a signal colour one color that only ever means tap this and everything else is
> just ink and paper. and if it still looks default which I feel like some pages are we can skip the middle sizes we
> make one thing huge and everything else tiny and nothing in btwn professionally though. ... I need to check out the
> output there before we deploy. also add a weather api updated in there.

This replaces the "keep the team's look" rule from 7 Oct, at the student's request. The layout pass of 12 Oct
(`layout-improvements-prompt.md`, TUKZIE_SW7_LAYOUT) stays underneath: sizes, positions and the 64 px tap targets are
kept, and this pass changes how things look and how they layer.

Reference image: `thetheme_reference.jpg` (a copy of `Projects/thetheme.jpg`), the "Hello, Explorer" safari app. Read it before starting.

## 1. What the reference does

- Paper: a warm off-white page. Cards are a lighter paper and float on soft, warm, long shadows.
- Ink: near-black titles and mid-grey labels. Apart from photos and the map, there is almost no colour.
- One signal colour, terracotta. It is used only for things you press: the selected nav item, the round centre
  button, the "Explore Map" button, the app icon. Nothing that is only information uses it.
- One inverse card, the dark charcoal weather card. Its "29°" is huge and everything under it is tiny.
- Depth: a 3D scene (the desert diorama) is the middle plane. Cards and buttons sit on top of it and overlap its
  edges. The page behind is the back plane.
- Type scale with no middle: "29°" and "Namibia" are huge, everything else is about 12 to 14 px. Few sizes, far apart.

## 2. Palette (sampled from the image, then tidied)

| Token | Hex | Use |
|---|---|---|
| paper | #F3ECE6 | page background (back plane) |
| paper_deep | #E7DCD3 | back-plane shapes, giant background type, sunken wells |
| card | #FBF8F5 | floating cards and panels (top plane) |
| ink | #1E1A17 | primary text, the one huge value, icons |
| ink_2 | #6B625B | labels, secondary text |
| ink_3 | #A89F98 | tertiary text, hairlines, inactive icons |
| charcoal | #34353A | the single inverse card per page (e.g. weather, the hero value), text on it #FBF8F5 |
| signal | #B9562F | tappable only: buttons, the selected nav item, toggles that are on, links, slider handles |
| signal_pressed | #96421F | pressed state |
| signal_tint | #F1DDD2 | the fill of a selected item behind signal-coloured ink |
| shadow | #6E4A32 at 18 to 28 % alpha | all elevation shadows (warm, never pure black) |

Status colours only describe data. They are never on anything tappable, and appear only as small marks: a dot, a
bar, a ring segment, a word. They are never a large fill.
- ok: #4F7A55 (sage)
- warn: #C98A16 (ochre)
- critical: #B3261E (deep red)

Critical is a deeper red than signal, and it never sits on a button. The obstacle pill becomes a charcoal pill with a
critical dot and white text. Its "Hide" control is the only signal-coloured thing in it.

Night: from the weather service's sunset to its sunrise (or TUKZIE_SW7_NIGHT=1), use the Ink variant. It keeps the same
structure with paper #1C1A18, card #26231F, ink #F3ECE6, ink_2 #B5ABA3, signal #D9744A. A white paper screen at night
would dazzle the driver.

## 3. Three planes

1. Back plane (type and ground): the paper background, with the page's one word set huge and faint behind
   everything. For example "DRIVE" in paper_deep at 220 to 300 px, bleeding off an edge. On Driving and Sensors it
   can be the road or ground shape. It is never tappable and never competes with data.
2. Middle plane (the subject): the one thing the page is about, drawn large with a little depth, a soft ground
   shadow or slight perspective:
   - Driving: the speed and its dial.
   - Map: the map, as a raised slab with rounded corners and a thick edge shadow, like the diorama.
   - Sensors: the tuk-tuk seen from above.
   - Charging: the battery ring.
   - Camera: the video frame.
   - Analytics: the current card.
   - Diagnostics: the four cards, as a group.
3. Top plane (controls): buttons, chips, the nav bar, the turn banner, the obstacle pill and small cards float on
   shadows (blur 24 to 40 px, y offset 8 to 16 px). They overlap the subject's edge by 12 to 24 px wherever the
   layout allows, so the overlap shows the depth. The nav bar becomes a floating rounded pill, like the reference,
   with the selected item as a raised signal-coloured circle.

Paint shadows with QGraphicsDropShadowEffect or pre-rendered shadow pixmaps. The Pi 5 must keep a smooth frame rate,
so measure paint time and avoid live effects on anything that animates every frame (the map, the speed). Use a cached
shadow under a static frame for those.

## 4. Signal colour rules (the test checks these)

- Anything that responds to a tap uses signal: buttons, nav items, links, toggles, sliders, map controls,
  "Simulate drive", "Navigate", "Show advice and details", "Hide". Either it is filled signal with card-coloured
  ink, or it is a card with signal ink and a signal outline.
- Nothing else may use signal or a colour close to it (hue within 15 degrees and saturation over 35 %). Status
  colours are only allowed as small marks.
- The data-source chip (LIVE / REPLAY / NO DATA / SIMULATED) is information. It becomes an ink outline chip with a
  status dot (ok, warn, ink_3). SIMULATED keeps a warn-coloured strip under the status bar, written in ink on a warn
  tint, so it can still never be mistaken for live data.

## 5. Type scale: huge or tiny, nothing in between

Each page has one hero value at 120 to 180 px, in ink or on the charcoal card. Everything else uses only these
sizes:
- 13 px: labels and units, ink_2, letter-spaced caps for section labels.
- 16 px: body.
- 22 px: secondary values, at most 3 per page.

No sizes from 28 to 100 px, except the 64 px tap targets, which are a box size, not a text size. Use a bundled font:
Atkinson Hyperlegible is already in `DashboardIntegration/fonts`. Do not depend on system fonts the Pi may lack.

## 6. Weather

Add `sw7_weather.py`, using Open-Meteo (https://api.open-meteo.com/v1/forecast, no key). It asks for current
temperature, weather code, wind, is_day, hourly temperature and weather code for the next 12 h, and daily sunrise
and sunset.
- Position comes from the GPS fix, then the modem's network position, then UCT (-33.9577, 18.4612).
- Refresh every 15 min, or immediately after moving more than 5 km.
- It runs off the UI thread, with a 6 s timeout and a cached last result (with its age) on disk, so it works offline.
- The status bar shows a weather icon, temperature and place, for example "☀ 24° Rondebosch", in place of the fixed "UCT 17°C".
- Tapping it opens a weather card in the style of the reference: charcoal, hero temperature, five hourly columns.
  The card is a sheet over the current page, or sits on Diagnostics or Settings.
- Show "updated 12 min ago", and "--" with no network and no cache. Never invent a value.
- Sunrise and sunset drive the Ink night variant.
- Tests use a local fake server, never the real API.

## 7. Rules (as in the layout pass)

- Change the dashboard only through `DashboardIntegration/`: COPIES for our modules, patch entries in
  `tests/dashboard_patches.py` for the team's files, in new groups appended to the end of the PATCHES line.
- The switch is `TUKZIE_SW7_STYLE`: `paper` is the default in this build, and `team` gives exactly the current
  (layout-pass) look. A test checks the `team` path renders as before.
- Test against `scratchpad/v11c/Dashboard`, a fresh extract of `dash_v11.tgz`. Never point TUKZIE_TEST_SCRATCH at it.
  Run with QT_QPA_PLATFORM=offscreen. All existing tests must pass:
  - test_live_data_provider
  - test_tile_map
  - test_sim_sync
  - test_search
  - test_analytics_carousel
  - test_layout_frame
  - test_layout_drive
  - test_layout_pages
  - test_layout_map
- Screenshots at 1280 x 800 go in `tests/style/<area>/`: day, night and simulated drive. Look at them and fix
  overlaps, clipping and anything that still looks default.
- Keep: live versus simulated, the obstacle pill's position, two- and three-finger swipe, touch scrolling, voice
  guidance, simulated-drive sync, the tilt map, search.
- Commit on your worktree branch only. No push, no deploy, no co-author line. No em dashes in docs or comments.

## 8. Split

1. Core (one agent, first): `sw7_style.py`, holding the palette, night variant, type scale, elevation and shadow
   helpers, the back-plane painter and a signal-colour audit used by the tests. This agent also does the frame
   (status bar, floating nav pill, side arrows, the obstacle pill restyle, the SIMULATED strip and chip), the weather
   service and card, and `tests/test_style_core.py`.
2. Then three page agents, in parallel, using the core's API:
   - Driving and Analytics.
   - Diagnostics, Camera, Sensors and Charging.
   - Map (warm tile tint, the slab with edge shadow, controls and banner on top) and Settings.

## 9. Core API (for the page agents)

Done by the core agent (12 Oct): `DashboardIntegration/sw7_style.py` and `sw7_weather.py` (copied to `app/widgets/`,
groups `STYLE_CORE_COPIES` and `STYLE_CORE_PATCHES`), the paper pill in `sensors_page.HazardBanner.sw7_paper`, and
`tests/test_style_core.py` (screenshots in `tests/style/core/`). The full API is in the docstring at the top of
`sw7_style.py`; the short version:

```python
from ..widgets import sw7_style as S          # in app/pages ("from . import sw7_style" in app/widgets)
if S.enabled(): ...                           # paper; with TUKZIE_SW7_STYLE=team change nothing at all
S.hx("signal"), S.c("ink"), S.c("shadow", 60), S.rgba("ink", .5)   # read at paint or restyle time
S.is_night()                                  # Ink variant; THEME.changed fires on every day/night switch
S.font(px, weight, caps=False)                # bundled Atkinson Hyperlegible; px only 13, 16, 22 or 120..180
S.HERO (150), S.SECONDARY 22, S.BODY 16, S.LABEL 13
S.set_back_word(page, "DRIVE", corner="bl")   # ThemedPageSurface pages; others: S.attach_back_plane(w, "CHARGE")
S.elevate(widget, level)                      # static widgets only (QGraphicsDropShadowEffect, warm)
S.paint_card(p, rect, radius, level, fill="card")   # cached shadow + card, for anything that animates
S.paint_shadow(p, rect, radius, level)        # levels: 1 chip or button, 2 card, 3 slab or sheet
S.button_qss(kind="outline" or "filled", radius, px, selector);  S.style_button(btn, kind)
S.mark_tappable(w);  S.mark_exempt(w, "reason")
S.audit_signal(root, ignore=(map,)) -> [Finding(widget, kind, pixels, note)];  S.ok_audit(findings)
S.type_audit(root) -> [(widget, px)] outside the scale
```

- Tokens: paper, paper_deep, card, card_alt, hairline, ink, ink_2, ink_3, charcoal, on_charcoal, on_charcoal_2,
  signal, signal_pressed, signal_tint, shadow, ok, warn, critical, warn_tint (day values as in section 2).
- THEME follows in paper mode: bg = paper, card, card_alt, accent = signal, highlight = ink, text = ink,
  text_dim = ink_2, text_faint = ink_3, border = hairline, track = paper_deep; status normal, warn, crit, inactive =
  ok, warn, critical, ink_3; info = ink_2; regen = ok. THEME.stylesheet() makes every QPushButton a signal outline
  button (checked: filled), line edits and combo boxes signal-outlined, toggles and sliders signal. Team code that
  reads THEME is mostly right already; anything with hard-coded colours (the turn banner green, the speed dial,
  the touch keyboard keys, the map) still needs its page agent.
- Audit rule: signal-like = hue within 15 degrees of signal and saturation over 35 %. Critical red is within that
  rule too, so a non-tappable widget may hold up to `S.MARK_PX` (420) such pixels when they are nearer a status
  colour than signal (a dot, a bar). Pure signal on a non-tappable widget always fails.
- Default back-plane words (set by the core, change them freely): Drive DRIVE, Analytics TRIPS, Diagnostics
  HEALTH, Camera ROAD, Sensors AROUND, Charging CHARGE, Settings SETUP; Map none. Bottom corners show about 60 % of
  the capitals above the nav pill.
- Frame geometry at 1280 x 800: status bar y 0..48 (paper, no border), the SIMULATED strip 26 px under it while it
  shows, page stack y 48..744 (696 px, 16 px more than the layout pass: it runs NAV_OVERLAP = 16 px under the
  pill). Nav overlay y 712..800, pill x 88..1192, y 728..792; the selected circle (52 px) reaches y 720. Arrows are
  64 x 64 round signal-outline buttons at (16, 728) and (1200, 728). Keep tap targets out of the page's bottom
  16 px; Driving's "Free driving" line currently sits under the pill.
- The obstacle pill is charcoal with a critical (or warn) dot, its text button marked exempt, Hide filled signal.
  The source chip is 132 x 28, an ink outline with a status dot. The weather chip is `main.status.sw7_weather_chip`,
  the card `main.sw7_weather_card`, the service `main.sw7_weather`.
- Tests: copy the build and run pattern of `test_style_core.py`. Always set `TUKZIE_WEATHER_URL` and
  `TUKZIE_REVERSE_URL` (a fake server, or a dead port such as http://127.0.0.1:9) and `TUKZIE_WEATHER_CACHE` (a temp
  file); the existing tests now do. The layout tests run with `TUKZIE_SW7_STYLE=team`.
- Paint time: `QWidget.grab()` of the window, median of 25, compared with `TUKZIE_SW7_STYLE=team`.
## 10. Page merge decision (student, 12 Oct): option A plus Surroundings

See `data-ownership-and-merge-plan.md`, which has the table of where each value appears and the one home page for each.

- Remove every duplicate. Each value has one home page with the full detail. Anywhere else it appears only as a small
  glance value that opens its home page when tapped (in signal colour, since it is tappable).
- Drive is the glance page. Following the inspiration images in `inspo/`, it gets tiles beside the speed hero:
  - Next turn: a mini map with the turn, opening Map.
  - Around: the tuk-tuk from above with the left, ahead and right ToF distances placed around it, like the tyre
    pressures in `inspo_sports_car_tiles.jpg`, opening Surroundings.
  - Range and battery, opening Charging.
  The pedal bars have no sensor behind them, so remove them.
- Front camera and Sensors merge into one page, Surroundings: the camera frame, the tuk-tuk with its ToF distances,
  and one combined hazards list (not two). That gives 7 pages: Drive, Analytics, Diagnostics, Map, Surroundings,
  Charging, Settings. The nav bar and the swipe order follow. The obstacle pill opens Surroundings.
- Fix these along the way:
  - The Map shows two different remaining-distance and ETA figures. Keep one.
  - Two outside temperatures: label the vehicle's as "Ambient (vehicle)" and the weather service's as "Outside (weather)".
  - During a simulated drive, the Sensors battery stays live while every other battery figure is simulated. It must
    follow the simulation like the rest.
- The team's pages keep their structure; trim their duplicates with patches. Everything sits behind TUKZIE_SW7_STYLE,
  and `team` gives back the 8-page layout-pass build exactly.

Page agents, after the core:
- P1: Drive (glance tiles) and Analytics.
- P2: Surroundings (the camera and Sensors merge, the nav and swipe order change, and the pill target), plus
  Diagnostics and Charging de-duplication.
- P3: Map (slab, warm tiles, a single ETA) and Settings.
