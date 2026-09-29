# Stitch prompt: SW-7 bench console redesign

Written 2026-09-29. Paste "Shared description" plus ONE variant into Stitch.
Export the result as HTML (and a screenshot) and give it back, and Claude
merges the design into BenchTest/sw7_console.html, keeping all the live
serial, camera and command functions.

---

## Shared description (paste first)

Design a single-page desktop web app called "SW-7 Bench Console". It is an
engineering monitoring tool for an electric cargo trike's telemetry
system, used by one engineering student on a laptop (1280 to 1440 px wide)
at a lab bench and beside the vehicle during tests. It must be readable at
a glance from about a metre away, and every value must be exact (these are
test measurements, not marketing numbers).

The page shows, in one screen with light scrolling:

1. Top bar: app name; an "ESP32" connection control (Connect and
   Disconnect buttons, a status chip such as "connected, 115200"); a
   "Camera" address field (example "10.84.114.244:8080") with a Show camera
   button and a status chip ("live", "off", "no stream"); a firmware chip
   ("firmware v0.5.0"); buttons "Save session log" and "Clear".
2. Front camera panel: a 4:3 live video area (the video already has
   detection boxes drawn on it) and, beside it, a hazard alert list. Each
   alert has a class and a distance band with confidence, for example
   "Person, immediate, 63%" and "Bicycle, warning, 55%". Bands have fixed
   meanings: immediate (under 3 m), warning (under 8 m), monitoring (under
   15 m). Also a small metrics chip: "7.0 fps, 180 ms sensor to result".
   Empty state: "No alerts".
3. Telemetry unit panel with six status cards, each with a status dot
   (good, warning, fault, off):
   - Ride vibration: big value "0.035 m/s² std"; fused RMS 10.141;
     disagreement 0.02; sources "both IMUs".
   - IMU acquisition: IMU1 rate 200.0 Hz; IMU2 rate 200.0 Hz; max gap 5.3 ms;
     dropped 0; scale factors 1.0390 / 1.0245.
   - Battery (BMS): link "no link"; pack voltage, current, state of charge
     (empty until linked, shown as a dash).
   - Position (GNSS): fix "no fix"; latitude, longitude, speed.
   - Cellular (MQTT): session "connected"; last event "Connected.".
   - Logging and system: flash log "on"; free heap 156 KB; self-tests
     "2 passed"; sync pulses "300 edges".
4. A wide line chart: "Vibration level (standard deviation of acceleration
   magnitude)", three series IMU1, IMU2 and Fused, over the last 2 minutes
   (values from 0 to about 17 m/s², mostly near 0 with bursts).
5. Two half-width panels: "Sensor disagreement" line chart (0 to 2), and a
   table "Latest window per sensor" with rows IMU1, IMU2, Fused and columns
   RMS, std, p2p, crest, jerk, crossings.
6. Two half-width panels for sensors not yet connected, shown in a clear
   "awaiting sensor" state that still looks designed:
   - "Time-of-flight (VL53L5CX)": an 8 by 8 grid of distance cells in
     metres, coloured red under 1 m and amber under 2 m.
   - "Air quality and microclimate (SEN55)": PM1.0, PM2.5, PM4.0, PM10 in
     µg/m³, temperature °C, humidity %, VOC index, NOx index.
7. Commands and serial output: buttons "!status", "!log off", "!log on",
   "!mqtt", and a danger-styled "!recal" that needs an inline confirmation
   ("Board flat and completely still?" Yes / Cancel); a text box "AT
   command, or ! command, then Enter"; a filter dropdown (All lines, Ride
   features, IMU and calibration, Battery, GNSS, MQTT, Commands, Problems);
   and a monospace scrolling log.

Design rules for both variants:
- Provide a dark theme and a light theme.
- Status colours must be distinct from the brand accent and colour-blind
  safe, and every status also has a text label or icon, never colour alone.
- Numbers use tabular figures and always show units.
- Charts have labelled axes, a faint grid and a legend.
- Clear hierarchy: the camera alerts and the six status dots are what the
  user checks first.
- No stock photos, no marketing hero, no fake brand logos.
- Output one desktop screen at 1440 px wide and a 1280 px variant.

## Variant A: lively (paste after the shared description)

Make it feel like a modern vehicle mission-control screen: confident
colour, depth and motion cues. Use a dark-first palette with one vivid
accent, soft glows on live elements (the camera frame, active alerts,
connected chips), animated-looking pulse indicators on status dots, rounded
cards with subtle gradients, and larger display numerals for the key
values. Alerts should be bold, colour-filled pills that stand out from
across the bench. Keep it technical, not playful.

## Variant B: minimal (paste after the shared description)

Make it calm and minimal, like a precise lab instrument: mostly neutral
greys with a single accent, generous whitespace, thin hairline dividers
instead of heavy cards, one clear type scale, and no decoration. Status is
shown by small dots and short labels, and colour appears only where
something needs attention (an alert, a fault, a disconnected link). The
charts are thin-line and quiet. Everything should still fit on one screen
with light scrolling.
