#!/usr/bin/env bash
# SW-7 integrated dashboard (separate copy; the team copy in ~/Dashboard is untouched).
export DISPLAY=:0
export XAUTHORITY=/home/piadam/.Xauthority
# Vehicle display: never blank or power the screen down while the dashboard runs.
xset s off; xset s noblank; xset -dpms
# Show only real sensor data: no simulator values, "--" when data is missing.
export TUKZIE_LIVE_ONLY=1
# No fixed addresses: sw7_endpoints.py finds the Pi 4 (localhost, wired 10.20.0.1,
# beacon, pi4-camera.local, last good). Set TUKZIE_PI4_HOST only to force one for a test.
unset TUKZIE_CAMERA_URL TUKZIE_TELEMETRY_URL
cd /home/piadam/Dashboard_sw7 || exit 1
exec /home/piadam/tukzie-env/bin/python main.py --fullscreen >> /home/piadam/sw7_dashboard.log 2>&1
