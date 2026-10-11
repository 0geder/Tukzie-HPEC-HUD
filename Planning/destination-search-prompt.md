# Destination search like a ride-hailing app (brief)

Written 11 Oct 2026 from the student's request, with Uber screenshots: "the current location should be picked
out from the GPS when one wants to enter a destination and just have the destination entering kind of similar
to theirs ... the area suggestions when typing are quite slow, I need it to act like a proper search engine and
give relevant Google-Maps type location suggestions".

## Today (team v1.1)

- The Navigation page has one field, "Enter destination", and a Navigate button. Typing starts a 280 ms timer
  that calls coordinator.request_suggestions, which waits for the online geocoder (OpenRouteService with a key,
  otherwise Nominatim) and then merges the offline place matches. Nothing shows until the network answers.
- Nominatim is not made for type-ahead: no results for partial words ("food lo"), no bias to where the vehicle
  is, and a policy of about one request per second. So suggestions are slow and often missing.
- The start of every route is the GPS fix, or silently "Default UCT start (GPS unavailable)". The network
  position from the modem (about 550 m indoors) and the last known fix are not used.
- Suggestion rows are single plain-text lines, 32 px high, at most 160 px of list.

## What to build (sw7_search.py, installed on the Navigation page)

1. Fast, relevant type-ahead.
   - Photon (photon.komoot.io, OpenStreetMap data, built for search-as-you-type), biased to the current
     position, limited to South Africa (bbox 16.3,-35.0,33.0,-22.0), English labels, 8 results.
   - Debounce 120 ms. Recent destinations and the team's offline place matches appear at once (no network);
     Photon results are merged in when they arrive.
   - Stale answers are dropped (each request has a token; only the newest is shown). Answers are cached by
     query. All network and matching work runs on background threads; the UI thread never waits.
   - If Photon fails or there is no connection, the team's coordinator.request_suggestions runs as before
     (ORS or Nominatim plus offline matches), so nothing is lost.
2. Rows like Uber's: two lines (place name in bold, address dimmer), the distance from the current position
   on the left ("3.2 km"), a clock icon for a recent place and a pin icon for a search result. A
   QStyledItemDelegate on the team's own suggestions list, rows about 58 px, up to five rows (four when the
   touch keyboard is up, so the list never goes under it). Each item keeps the team's contract: text is the
   label, UserRole is the place dict with lat, lon and label, so the team's _choose_suggestion still works.
3. Recent destinations: when the empty field is tapped, the last destinations show with distances
   (~/.config/sw7/recent_destinations.json, at most 8, newest first). A destination is saved when a row is
   chosen and when a route is planned.
4. Current location as the start, shown honestly in a header row at the top of the dropdown:
   - "From: Current location (GPS)" with a GNSS fix;
   - "From: Approximate location (mobile network, ±550 m)" with only the modem's network estimate;
   - "From: Last known position" with only an older fix;
   - "From: UCT (no GPS)" otherwise.
   The header cannot be selected. coordinator._resolve_start uses the same order (GPS fix, network position,
   last fix, UCT) and labels the start accordingly. The placeholder becomes "Where to?".
5. Team look kept: colours from THEME, the team's fonts; only the dropdown changes. The touch keyboard and
   finger scrolling of the list (sw7_touch) keep working. TUKZIE_SW7_SEARCH=0 restores the team's search.

## Why Photon

Measured from Cape Town on 11 Oct: "food lo" gives Food Lover's Market branches, "cavend" gives Cavendish
Square (Claremont), "two4one" gives Two4One (Lower Main Road, Observatory), in 0.7 to 2 s. Nominatim gave no
results for the same partial words. Photon is free, needs no key and is meant for this use; we send a
descriptive User-Agent and at most one request per 120 ms pause in typing, with a cache.

## Tests (tests/test_search.py, offscreen, patched copy, no internet)

Photon is replaced by a stub. Checks: recents on focus with distances; local matches before the network
result; stale responses dropped; rows render (screenshot in tests/search/); choosing a row sets the
destination hint with lat and lon and saves a recent; start resolution order GPS, network, last fix, UCT.
Plus one live timing check against real Photon from the laptop, then the existing suites and a Pi 5 deploy.

## Status (11 Oct 2026)

Built: DashboardIntegration/sw7_search.py (copied to app/pages/), SEARCH_PATCHES in tests/dashboard_patches.py
(navigation_page.py: debounce and handler for the destination field, list geometry, install; coordinator.py:
start order), tests/test_search.py.

Tested offscreen (full patched dashboard, fake Photon server): all 33 checks pass. Offline matches 2 to 20 ms
after the debounce, before the network answer; stale answers dropped; repeat queries from the cache; team
fallback when Photon fails; header for GPS, network, last fix and UCT; a tap sets the hint with lat/lon and
saves a recent; coordinator start order GPS, network, last fix, UCT; list stays above the keyboard and keeps
finger scrolling. Screenshots in DashboardIntegration/tests/search/. Existing suites (sim sync, tile map, live
data provider, analytics carousel) still pass.

Live Photon from the laptop: 0.72 to 1.26 s per query, relevant first results ("food lo", "cavend",
"two4one", "groote sch", "kirstenb", "uct"). On the Pi 5: Photon 1.1 to 1.4 s, offline index built in 0.5 s,
offline matches 1 to 9 ms. Deployed to the Pi 5 and the dashboard restarted.

Not yet tested: on the real touchscreen by hand (typing, finger scrolling of the new rows, tapping a row), a
route planned from the network-position start on the vehicle, behaviour with no internet on the Pi (fallback
path is tested offscreen only).
