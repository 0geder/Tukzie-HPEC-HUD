# SW7 Open Day demo (18 November): two-minute live demo

Updated 20 October 2026 for the two-camera layout. What is on the table: the Pi 5 with the touchscreen dashboard, its
own front camera and front time-of-flight board (the front side); the Pi 4 with the rear camera in its printed casing,
the rear time-of-flight board and the ESP32 telemetry unit with its two IMUs (the rear side); the Ethernet cable
between the two Pis; and the poster. Point the front camera towards the visitors and the rear camera the other way,
so the two sides show different scenes.

## Before the first visitor (15 minutes)

1. Power the ESP32 from its own supply or a powered hub, never from a Pi's USB port (that browned out the Pi 4, and it
   happened again in the closed box). Fan on the Pi 4. Pi 5 on its own 5 V 5 A supply, plug pushed fully home (the
   Pi 5's restarts on 19 October were abrupt power losses, most likely a loose plug or the supply).
2. Plug in the Ethernet cable between the Pis and tape it down; the rear side reaches the dashboard only over it.
3. Run `python BenchTest/sw7_check.py` and wait for READY (rear Pi found, camera fps, telemetry fresh, IMUs at
   200 Hz, distance sensors valid, no under-voltage).
4. On the dashboard, check the status chip reads LIVE. Open Surroundings and tap Front, then Rear: both should say
   "Front sensors live" and "Rear sensors live" and show a moving picture.
5. Plan a route on the Map page now, so the simulated drive is one tap away.
6. Put a small "Camera frames are never stored" card next to each camera.

## The two minutes (what to show and say)

| Time | Show | Say |
|---|---|---|
| 0:00 to 0:15 | The whole table | "This is the electronics for TUKZIE, a 72 volt electric cargo trike. It measures how the trike rides and warns the driver about hazards on the dashboard the trike already has. There is a front half and a rear half, joined by this cable." |
| 0:15 to 0:40 | Surroundings, Front. Hold a hand about 20 cm in front of the front ahead sensor. | "These three sensors measure distance left, ahead and right. Watch the reading turn amber, then red, and the warning appear at the top of every page." |
| 0:40 to 1:05 | Step in front of the front camera, then tap Rear. | "The camera finds people and vehicles in about a twentieth of a second at the front, all on this computer, and no picture is ever saved. This is the back of the trike: the picture is mirrored, like a car's reversing camera, and the warning says which side it came from." |
| 1:05 to 1:30 | Banner and hazard list. If a visitor walks steadily towards a camera, point at any "APPROACHING" entry. | "It also works out how soon something will reach you from how fast it grows in the picture, and warns under four seconds. That part has been tested on simulated data; a real approach test is still to do." |
| 1:30 to 2:00 | Tap the ESP32 board or tilt it gently. | "This board reads two motion sensors 200 times a second and sends every record over 4G to a database. We drove the trike with all of this on 19 October; the motion sensors and battery reading held for the whole drive, and we switched the radio off for ten minutes once and lost nothing." |

If someone stays: show the navigation and destination search ("search works like Uber: suggestions as you type;
indoors this drive is simulated, and the yellow strip says so"), the poster's road-session panel, or the enclosure
renders.

## If a part fails

- One side says "Camera offline, retrying" or "sensors offline": the other side keeps working, which is itself the
  point ("a side that drops out shows as offline, never as zero"). Then restart the detector on the Pi that owns that
  camera (`sudo systemctl restart hazard-detector`); it comes back within a few seconds.
- Rear side offline and the front fine: check the Ethernet cable at both ends first (it came loose twice during
  mounting on 19 October), then that the Pi 4 is up.
- No LTE (4G) indoors: the dashboard does not need it; its data comes over the cable. Say "the 4G is down in here, so
  the unit is saving everything and will send it when it reconnects; that is exactly what the outage test checked."
  Spoken directions also need data, so there is no voice; point at the turn banner.
- No GPS indoors: expected. Never say the GPS works on the trike: it had no fix on the road on 19 October, and that is
  being checked. Use the simulated drive and always say "this part is simulated".
- No "APPROACHING" entry appears when someone walks up: do not force it. Say "it needs a steady approach and is tuned
  not to raise false alarms; it is tested on simulated approaches so far."
- Status chip reads NO DATA: the rear Pi is not found. Check the cable, then rerun sw7_check.py. Meanwhile show the
  front side and the poster.
- A distance reading stays empty: one sensor is not answering (the 0.5 s timeout skips it). Use another sensor;
  re-seat the board wiring at the next quiet moment.
- A Pi slows down or restarts: check the ESP32 is not on the Pi 4's USB port, the fan is running, and the Pi 5's plug
  is fully in.
- Everything fails: walk the visitor through the poster and the screenshots on slides 11 and 13 of the deck on the
  laptop.

## Do not say

- "It alerts in half a second" (that was a page-opening time, not alert latency). Say "about a twentieth of a second
  to detect at the front, a tenth at the rear".
- "It has been fully tested on the trike." Say "we drove it once; the motion and battery data held, and a second drive
  will add GPS and the detailed motion data."
- "It predicts crashes" or "it knows a car is coming at you". Say "it estimates how soon something will reach you; that
  is tested on simulated data so far".
- "It detects potholes": the pothole model is built but off by default, because it is too slow beside the main
  detector on a Pi 4.
- "Reverse gear switches to the rear camera" as a vehicle feature: there is no gear signal from the trike yet.
