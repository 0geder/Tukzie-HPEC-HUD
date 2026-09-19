# Virtual Tukzie dashboard

A local, browser-based dashboard combining a real Gaussian splat of the
physical Tukzie with live telemetry read directly off the real, connected
ESP32-S3 over the COM port. Nothing here is simulated or fabricated - the
3D model is a real reconstruction from a real walk-around video, and the
sensor readings are the genuine, calibrated output of the wired-up IMUs.

## Running it

This must be served over a local HTTP server, not opened directly as a
`file://` page - Chromium browsers block loading local sibling files (needed
for the 113MB splat) from a bare file:// page, and Web Serial also expects
a proper page origin.

From this folder:

```
python -m http.server 8000
```

Then open **http://localhost:8000/dashboard.html** in **Chrome or Edge**
(Web Serial is not supported in Firefox or Safari).

## Using it

- **Live 3D splat** tab: the real Gaussian splat reconstruction
  (`splat/Tukzie.ply`, 451,937 points) of the physical vehicle. Drag to
  orbit, scroll to zoom. First load takes a few seconds (113MB).
- **Captured frames** tab: still images extracted directly from the
  walk-around video, as a lightweight fallback if the splat fails to load.
- **Connect to Tukzie** button: opens a Web Serial connection to the ESP32.
  Close any other program holding the port first (PlatformIO's serial
  monitor, the Python bench-test classifier, etc.) - only one process can
  hold a COM port at a time.
- **Live telemetry panel**: real RMS/P2P/crest/jerk per IMU, classified
  against provisional event-detection thresholds (see
  `Planning/virtual-tukzie-digital-twin.md` for the reasoning and the
  thresholds' current status).

## Files

- `dashboard.html` - the page itself
- `assets/` - real frames extracted from the walk-around video
- `splat/Tukzie.ply` - the real Gaussian splat (gitignored - see below)

## Note on the splat file

`splat/Tukzie.ply` is 113MB, which exceeds GitHub's 100MB hard file-size
limit, so it is excluded via `.gitignore` and kept local only. If this
repository is cloned fresh, the dashboard's splat view will show a load
error until `Tukzie.ply` is placed back in this folder.
