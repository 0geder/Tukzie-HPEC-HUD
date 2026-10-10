# Map: whole-region offline map, offline routing and voice guidance (brief)

Written 11 Oct 2026 from the student's request and a pasted outline ("work like Google Maps navigation, fully
offline-capable, with natural voice guidance"). The outline assumed a windshield HUD and possibly an STM32; this brief
is corrected to the real system.

## Real system

- Raspberry Pi 5 Model B, 16 GB RAM, 4 cores, 48 GB free on the SD card; Raspberry Pi OS (Debian trixie).
- The team's PySide6 dashboard (v1.1) with our patches; our map widget `DashboardIntegration/sw7_tile_map.py`
  (QPainter, heading-up, auto-zoom, turn banner, simulated drive, network-position circle). 1280x800 touchscreen.
- Position from the ESP32-S3 telemetry unit (A7670 modem GNSS, assisted GNSS and mobile-network position since
  firmware 0.7.3), through the Pi 4 bridge. IMUs are MPU6050 (not an ICM-42688).
- Audio: none fitted. The Pi 5 has only HDMI audio outputs; a USB speaker (or a display with HDMI audio) is needed.
- Rules carried over: keep the team's look (no restyle without a mock-up), live data only, nothing invented,
  OSM attribution on screen, no Google tiles, APIs or voice.

## Diagnosis (step 1, done 11 Oct)

The map draws raster tiles fetched live from tile.openstreetmap.org and cached in `~/.cache/sw7_tiles` (23 MB on the
Pi 5, prefetched by `tools/prefetch_tiles.py` for -34.00..-33.90, 18.40..18.52 at zoom 11 to 16). With internet it
works anywhere; offline, everything outside that box is blank except the small offline road index. A bigger prefetch
box is not a fix: Cape Town at street zooms is gigabytes, and OSM's tile policy forbids bulk downloading. Routing is
also online only: the team's route service uses OpenRouteService, the public OSRM demo and Nominatim, with
turn-by-turn steps switched off (our turn banner derives turns from road-name changes).

## Stage 1: whole-region offline vector map

- Data: Geofabrik `africa/south-africa-latest.osm.pbf`, cut to the Western Cape with osmium (one bounding-box line to
  change for all of South Africa).
- Tiles: Planetiler (OpenMapTiles schema) to a PMTiles file, maxzoom 14 (overzoomed beyond), roads, names, water,
  landuse, buildings from zoom 14. Built on the laptop or the Pi; record the build time and file size.
- Rendering: keep our widget. Add a local vector source beside the online raster source: read tiles from the PMTiles
  file, decode the vector tiles, draw each tile once into a QPixmap with a style matched to the team's colours, and
  reuse the existing tile cache, rotation and zoom pipeline. Labels drawn upright after rotation.
  Chosen over MapLibre Native because it needs no new Qt plugin on the Pi and keeps every existing feature and test.
- Offline is the default; online raster stays as an option. A refresh script re-downloads and rebuilds monthly.
- Tests: offline (no network) the map draws streets in Stellenbosch, Paarl and Hermanus, at the region's edges and in
  the UCT box; frame time on the Pi 5 at 1280x800 while panning and rotating.

## Stage 2: offline turn-by-turn routing

- Engine: Valhalla (rich manoeuvre text, costing options), from the same extract. On the Pi 5 through pyvalhalla
  (Python package with the tile builder and router) if its aarch64 wheel works, else a native build.
- Profile: motor_scooter costing, top speed 42 km/h (the vehicle plate's rated speed), motorways avoided, primary
  roads allowed. Assumption to confirm with the team: the trike may use ordinary roads but not freeways.
- Integration: offline route first, the team's online services as fallback, through our patch to their route
  service; manoeuvres from Valhalla replace the road-name heuristic when present. Off-route detection (more than
  about 40 m from the route for 3 s) triggers a reroute.
- Geocoding offline: a search over named places and streets from the same extract.
- Tests: known routes (UCT to Stellenbosch, UCT to Muizenberg) give sensible steps; a recorded trace that leaves the
  route reroutes within 3 s; query time on the Pi 5.

## Stage 3: voice guidance

- Piper TTS on the Pi 5, an English voice (en_GB or en_US; South African English if one exists and sounds right),
  common phrases pre-generated, street names synthesised on demand, eSpeak-NG as fallback.
- Timing scaled to speed: an early prompt (about 30 s ahead), a near prompt (about 100 to 150 m at trike speed) and
  "now" at the turn; close turns merged ("turn left, then turn right"); a queue where the newest instruction wins;
  mute and volume on the map.
- A pronunciation-override file for local names (Afrikaans and isiXhosa).
- Needs a speaker fitted to the Pi 5.

## Order and rules

Stage 1, then 2, then 3. Each stage tested offscreen and on the Pi 5, screenshots shown before deploying,
committed and pushed. Report, deck and Q&A updated with what was measured, marked tested or untested.
