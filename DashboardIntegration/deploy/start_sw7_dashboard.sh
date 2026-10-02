#!/usr/bin/env bash
# SW-7 integrated dashboard (separate copy; the team copy in ~/Dashboard is untouched).
export DISPLAY=:0
export XAUTHORITY=/home/piadam/.Xauthority
# Vehicle display: never blank or power the screen down while the dashboard runs.
xset s off; xset s noblank; xset -dpms
export TUKZIE_CAMERA_URL=http://192.168.137.82:8080
export TUKZIE_TELEMETRY_URL=http://192.168.137.82:8081
cd /home/piadam/Dashboard_sw7 || exit 1
exec /home/piadam/tukzie-env/bin/python main.py --fullscreen >> /home/piadam/sw7_dashboard.log 2>&1
