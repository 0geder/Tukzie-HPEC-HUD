# Front camera page for the TUKZIE dashboard

An add-on page for the vac-work dashboard (PySide6,
`Tukzie-Vac-Work-2026/Dashboard Team/Dashboard+ASIS`) that shows the SW-7
forward camera and its hazard alerts. It is kept here, outside the
dashboard repo, so the dashboard team can review it before anything in
their code changes.

## What it does

- Shows the live view from the Raspberry Pi 4 detector
  (`CameraDetection/hazard_detector.py --preview`), with the detections
  the model makes drawn on the image.
- Lists the current alerts (class and distance band) in the dashboard's
  own status colours: red immediate, amber warning, green monitoring.
- Shows the detector's frame rate and sensor-to-result latency.
- Emits `alerts_changed(list)`, so other pages (for example a toast on the
  driving page) can react to alerts without showing the video.

It uses QtNetwork and QtWidgets only, not QtWebEngine (the Navigation
page's WebEngine view has crashed on the Pi 5, per the dashboard README).
Video streams only while the page is on screen, only the newest frame is
decoded, and the page reconnects every 3 s if the camera drops out.

## Endpoints it reads (served by the detector)

| Endpoint | Content |
|---|---|
| `GET /stream` | MJPEG: the camera image with detections drawn on it |
| `GET /alerts` | JSON: `{"active": [...], "fps": 7.0, "latency_ms": 182}`; each active alert has `class`, `distance_band`, `confidence`, `timestamp`, `alert_status` |

The camera address is taken from the `TUKZIE_CAMERA_URL` environment
variable, default `http://pi4-camera.local:8080`.

## Wiring it in (four small edits for the dashboard team)

1. Copy `front_camera_page.py` into `app/pages/`.

2. `app/pages/dashboard_main.py`, with the other page imports:
   ```python
   from .front_camera_page import FrontCameraPage
   ```
   and where the pages are created:
   ```python
   self.front_camera = FrontCameraPage()
   ```
   then add `"camera": self.front_camera` to `self.page_by_id`, and
   `"camera"` to `self.page_ids` (for example after `"navigation"`).

3. `app/widgets/nav_bar.py`, add a button to `NAV_ITEMS`:
   ```python
   ('camera','camera','Front camera'),
   ```

4. `app/widgets/icon_registry.py`, add a drawer and register it in
   `DRAWERS` as `'camera': camera`:
   ```python
   def camera(p,r,c):
       _setup(p,c,max(1.6,r.width()*.065))
       body=QRectF(r.left()+r.width()*.14,r.top()+r.height()*.30,r.width()*.72,r.height()*.48)
       p.drawRoundedRect(body,r.width()*.08,r.width()*.08)
       p.drawRect(QRectF(r.left()+r.width()*.36,r.top()+r.height()*.20,r.width()*.22,r.height()*.10))
       p.drawEllipse(body.center(),r.width()*.14,r.width()*.14)
   ```

On the Pi 5, if `pi4-camera.local` does not resolve on the vehicle
network, set the address before starting the dashboard, for example
`export TUKZIE_CAMERA_URL=http://192.168.1.50:8080`.

## Tested

Offscreen on a laptop with PySide6 6.11.2, inside a copy of the
dashboard's `app` package, with the dashboard's own stylesheet:

- The frame parser picks the newest complete JPEG from a multipart
  stream, keeps a partial frame for the next chunk, and ignores junk.
- The page decodes a stream fed in uneven 1777-byte chunks, lists two
  alerts, clears them, and emits `alerts_changed` only when the list
  changes.
- Pointed at an address that never answers, the UI stays responsive and
  reports "Camera offline, retrying" within 7 s.
- The camera icon drawer in step 4 renders correctly at 96 px.

Not yet tested: on the Pi 5 itself, against the live detector, and the
four wiring edits above (they touch the dashboard team's files).
