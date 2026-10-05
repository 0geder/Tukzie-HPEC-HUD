#!/usr/bin/env bash
# SW-7 integrated dashboard (separate copy; the team copy in ~/Dashboard is untouched).
# Started at login by ~/.config/autostart/sw7_dashboard.desktop.
# Wait for the desktop, graphics and audio to be ready, as the team's launcher does.
sleep 5
export DISPLAY=:0
export XAUTHORITY=/home/piadam/.Xauthority
# Vehicle display: never blank or power the screen down while the dashboard runs.
xset s off; xset s noblank; xset -dpms
# Show only real sensor data: no simulator values, "--" when data is missing.
export TUKZIE_LIVE_ONLY=1
# Touch-only vehicle: do not start the Xbox controller poller (about 53% of a core).
export TUKZIE_NO_CONTROLLER=1
# No fixed addresses: sw7_endpoints.py finds the Pi 4 (localhost, wired 10.20.0.1,
# beacon, pi4-camera.local, last good). Set TUKZIE_PI4_HOST only to force one for a test.
unset TUKZIE_CAMERA_URL TUKZIE_TELEMETRY_URL
# Announce this Pi on every network so the laptop's pre-test check finds it (one instance).
pgrep -f "sw7_integration/pi5_beacon.py" >/dev/null || \
    setsid nohup python3 /home/piadam/sw7_integration/pi5_beacon.py >/dev/null 2>&1 < /dev/null &
cd /home/piadam/Dashboard_sw7 || exit 1
exec /home/piadam/tukzie-env/bin/python main.py --fullscreen >> /home/piadam/sw7_dashboard.log 2>&1
