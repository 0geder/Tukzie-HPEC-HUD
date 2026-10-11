# Simulated drive in sync across the dashboard, clearly apart from live data (brief)

Written 11 Oct 2026 from the student's request: "when the simulation is running the battery page should also go
hand in hand ... go through all the pages of the dashboard and have all the things that can be simulated in sync
when simulating a drive; when having the real data there should be a clear difference, and the dashboard should
be able to pick up the real data as well ... don't break a thing".

## Today

The map's Simulate drive moves the vehicle along the planned route at 25 km/h. Since 11 Oct the Driving page and
status bar also show the simulated speed with a badge; every other page still shows live (or no) data, so the
battery, range, power, consumption, temperatures and trip do not move during a simulated drive.

## What to build

1. One simulated vehicle state, produced while the map simulates and sent to every page through the team's own
   dispatcher (dashboard_main._on_vehicle_state), so all pages stay in step:
   - From the map: position, heading, speed (25 km/h moving, 0 on arrival), route progress.
   - From the team's simulator formulas (data_provider.SimDataProvider._tick), integrated over real elapsed
     time: throttle for a steady cruise, power and signed battery power, state of charge drain, consumption,
     range (asis.physics.estimate_remaining_range_km), motor and battery temperature, trip and odometer.
   - Gear D and parking brake off while moving; P at arrival.
   - Starting values from the live state: the real state of charge, odometer and temperatures if the BMS has
     reported, otherwise stated defaults; the simulation never writes into the live state.
2. Live where the simulation has nothing to say: ToF obstacle distances and camera hazards (the hazard banner
   and Sensors page), weather, charging (not charging during a drive), the network-position circle stops
   showing while simulating.
3. A clear difference between the modes, on every page:
   - Simulated: a yellow strip under the status bar, "SIMULATED DRIVE · not live data", on all pages, plus the
     Driving page badge; the data-source chip reads SIMULATED.
   - Live: a green LIVE chip in the status bar. Replay: amber REPLAY. No data: grey NO DATA.
4. Back to live cleanly: ending the simulation, or a real GNSS fix (already stops it), returns every page to the
   live state at once. Points the Analytics charts gathered during the simulation are removed, so its history
   and the odometer never contain simulated distance.
5. The Sensors page keeps showing the raw live telemetry throughout, as the always-real reference.

## Rules

- Team look kept: chips and strip use the existing status colours; no page layouts change.
- Live-only mode unchanged when no simulation runs; TUKZIE_LIVE_ONLY stays on.
- Tests: the existing suites pass; new checks that a simulated drive changes speed, battery, range and power on
  every page, marks every page as simulated, and that ending it restores live values and the Analytics charts.
- Offscreen screenshots of each page during a simulated drive and in live mode before deploying.
