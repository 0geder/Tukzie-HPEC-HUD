# SW7 Open Day demo (18 November): two-minute live demo

What is on the table: the Pi 5 with the team's touchscreen dashboard, the Pi 4 with the camera in its printed casing
and the three distance sensors, the ESP32 telemetry unit with its two IMUs, and the poster.

## Before the first visitor (15 minutes)

1. Power the ESP32 from its own supply or the laptop, never from a Pi's USB port (that browned out the Pi 4). Fan on
   the Pi 4.
2. Run `python BenchTest/sw7_check.py` and wait for READY (Pi 4 found, camera fps, telemetry fresh, IMUs at 200 Hz,
   three distance sensors valid, no under-voltage).
3. On the dashboard, check the status chip reads LIVE. Open the Camera page once to see the video is live.
4. Plan a route on the Navigation page now, so the simulated drive is one tap away.
5. Put a small "Camera frames are never stored" card next to the camera.

## The two minutes (what to show and say)

| Time | Show | Say |
|---|---|---|
| 0:00 to 0:15 | The whole table | "This is the electronics for TUKZIE, a 72 volt electric cargo trike. It measures how the trike rides and warns the driver about hazards on the dashboard the trike already has." |
| 0:15 to 0:40 | Sensors page. Hold a hand about 20 cm in front of the ahead sensor. | "These three sensors measure distance left, ahead and right. Watch the gauge turn amber, then red, and the red warning appear in the status bar on every page." |
| 0:40 to 1:05 | Swipe with two fingers to the Camera page. Step in front of the camera. | "The camera finds people and vehicles in about a tenth of a second, all on the Pi, and no picture is ever saved. That is me in the alert list." |
| 1:05 to 1:35 | Navigation page. Type "cav" in the search, pick a place, Navigate, then Simulate drive. | "Search works like Uber: suggestions as you type, nearest first. Indoors there is no GPS, so this drive is simulated, and the yellow strip says so on every page. The obstacle warnings stay live." |
| 1:35 to 2:00 | Tap the ESP32 board or tilt it gently. | "This board reads two motion sensors 200 times a second and sends every record over 4G to a database. We switched its radio off for ten minutes and not one record was lost." |

If someone stays: show a two-finger swipe through the pages (three fingers on the map), or the poster's fault
investigations.

## If a part fails

- No LTE (4G) indoors: the dashboard does not need it; its data comes from the Pi 4 over the local link. Say "the 4G
  is down in here, so the unit is saving everything and will send it when it reconnects; that is exactly what the
  outage test checked." Spoken directions also need data, so there is no voice; point at the turn banner.
- No GPS indoors: expected. The map shows "Waiting for GPS fix" or a network-position circle. Use the simulated drive
  and always say "this part is simulated". Never let simulated numbers pass as real ones.
- Search suggestions do not come (no internet on the Pi 5): offline matches and recent places still appear; pick
  one of those. (The no-internet path is tested offscreen only.)
- Status chip reads NO DATA: the Pi 4 is not found. Check both Pis are on the same network, then rerun sw7_check.py.
  Meanwhile show the camera casing and the poster.
- Camera page says "Camera offline, retrying": on the Pi 4, `sudo systemctl restart hazard-detector`; it comes back
  within a few seconds. Talk through the alert rules (three frames to raise, five to clear) while it restarts.
- A distance gauge stays empty: one sensor is not answering (the 0.5 s timeout skips it). Use another sensor; re-seat
  the sensor board wiring at the next quiet moment.
- Pi 4 slows down or restarts: check the ESP32 is not on its USB port, and that the fan is running.
- Everything fails: walk the visitor through the poster (results panel and fault investigations) and the
  screenshots on slide 11 of the deck on the laptop.

## Do not say

- "It alerts in half a second" (that was a page-opening time, not alert latency). Say "about a tenth of a second
  to detect".
- "It has been tested on the trike" unless the road test has happened by then.
- "It detects potholes": the pothole model is built but off by default, because it is too slow beside the main
  detector on a Pi 4.
