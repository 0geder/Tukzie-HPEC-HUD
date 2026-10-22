#!/usr/bin/env bash
# SW-7 common time base for the two Pis over the wired link (sw7-link, set up by
# setup_sw7_link.sh). The Pi 5 (dashboard, road recorder) is the time server and
# keeps serving from its own clock when there is no internet ("local stratum"),
# so the two Pis stay aligned on the road. The Pi 4 follows it over 10.20.0.2.
# Needed so that front (Pi 5) and rear (Pi 4) samples can be put on one time
# base for the front-to-rear analysis (run-2 test plan, bench gate G5).
#
#   sudo bash setup_sw7_chrony.sh pi5     # server, run first
#   sudo bash setup_sw7_chrony.sh pi4     # client
#
# Install chrony while the Pi still has internet (apt). Safe to run again.
# Check afterwards on the Pi 4:  chronyc sources -v   and   chronyc tracking
# (the 10.20.0.2 line should be marked "*" and the offset well under 1 ms).
set -u

usage() { echo "usage: sudo $0 pi4|pi5" >&2; exit 2; }
[ "$#" -eq 1 ] || usage
ROLE=$1
case "$ROLE" in pi4|pi5) ;; *) usage ;; esac
if [ "$(id -u)" -ne 0 ]; then echo "Run with sudo: sudo $0 $ROLE" >&2; exit 1; fi

if ! command -v chronyd >/dev/null 2>&1; then
    echo "Installing chrony (needs internet once)..."
    apt-get update -qq && apt-get install -y -qq chrony || { echo "apt failed: connect to the internet and run again." >&2; exit 1; }
fi

CONF=/etc/chrony/conf.d/sw7-link.conf
if [ "$ROLE" = pi5 ]; then
    cat > "$CONF" <<'EOF'
# SW-7: serve time to the Pi 4 on the wired link, also without internet.
allow 10.20.0.0/24
local stratum 8 orphan
EOF
else
    cat > "$CONF" <<'EOF'
# SW-7: follow the Pi 5 on the wired link, polling every 1 to 16 s.
server 10.20.0.2 iburst minpoll 0 maxpoll 4 prefer
# Step the clock if it is more than 0.1 s out (first 3 updates), then slew.
makestep 0.1 3
EOF
fi

# chrony replaces systemd-timesyncd; make sure only one is running.
systemctl disable --now systemd-timesyncd 2>/dev/null || true
systemctl enable chrony >/dev/null 2>&1 || systemctl enable chronyd >/dev/null 2>&1 || true
systemctl restart chrony 2>/dev/null || systemctl restart chronyd
sleep 3
echo "--- chronyc sources ---"; chronyc sources -v 2>/dev/null | tail -6
echo "--- chronyc tracking ---"; chronyc tracking 2>/dev/null | head -8
echo "Written $CONF ($ROLE)."
