# Running the detector as a service on the Pi 4

The service starts the detector at boot with the live view and the
`/alerts` endpoint on port 8080, and restarts it if it stops unexpectedly.

## Before installing

The detector must already run by hand (see `../README.md`, Deploying):
`~/hazard_detector` holds `hazard_detector.py`, `detect.tflite`,
`labelmap.txt` and the `venv` with `ai-edge-litert`.

If the camera needs the no-infrared-filter tuning, add
`--tuning ov5647_noir.json` to the end of the `ExecStart` line first.

## Install (laptop, then Pi)

Laptop PowerShell, from the `Tukzie-HPEC-HUD` folder:

```
scp -i ~/.ssh/pi4_camera_key CameraDetection/hazard_detector.py CameraDetection/deploy/hazard-detector.service ogeder@<pi-ip>:~/hazard_detector/
```

Pi terminal:

```
sudo cp ~/hazard_detector/hazard-detector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hazard-detector
systemctl status hazard-detector --no-pager
```

`active (running)` means it is up. The live view is then at
`http://<pi-ip>:8080` and the alerts at `http://<pi-ip>:8080/alerts`.

## Everyday use

| Task | Command (Pi) |
|---|---|
| See its output (alerts, 5 s timing lines) | `journalctl -u hazard-detector -f` |
| Stop it (for example to run the detector by hand) | `sudo systemctl stop hazard-detector` |
| Start it again | `sudo systemctl start hazard-detector` |
| Stop it starting at boot | `sudo systemctl disable hazard-detector` |
| After copying a new `hazard_detector.py` | `sudo systemctl restart hazard-detector` |

Only one program can use the camera at a time, so stop the service before
running the detector or `rpicam-hello` by hand.

## Address for the dashboard

The Pi 4's name is `pi4-camera`, so on a normal network the dashboard can
use `http://pi4-camera.local:8080` (mDNS, provided by avahi-daemon on Pi
OS). Check it from the Pi 5 with `ping pi4-camera.local`. On the phone
hotspot `.local` names did not resolve, and the address changes when the
Pi reconnects, so there set `TUKZIE_CAMERA_URL` on the Pi 5 to the
current IP from `hostname -I` on the Pi 4.
