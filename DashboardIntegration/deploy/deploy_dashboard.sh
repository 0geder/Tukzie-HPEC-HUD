#!/usr/bin/env bash
# Deploy the SW-7 dashboard build to the Pi 5. Run on the laptop in Git Bash,
# from anywhere inside the SW-7 repository:
#
#   bash DashboardIntegration/deploy/deploy_dashboard.sh [--pi5 HOST] [--key FILE] [--user NAME] [--no-restart]
#
# What it does, in order:
#   1. copies every DashboardIntegration/*.py (camera page, live provider, ride card,
#      sw7_endpoints.py, sw7_live_only.py), tests/dashboard_patches.py,
#      apply_patches.py and start_sw7_dashboard.sh to ~/sw7_integration on the Pi 5;
#   2. stops OUR dashboard only: python processes whose working directory is
#      ~/Dashboard_sw7. The team's dashboard in ~/Dashboard is never touched;
#   3. moves the old ~/Dashboard_sw7 to ~/Dashboard_sw7.prev and makes a fresh copy of
#      ~/Dashboard (cp -r, chmod -R u+w, __pycache__ removed);
#   4. applies the patches (apply_patches.py refuses to touch ~/Dashboard; every
#      anchor must match exactly once) and sets map_display_provider to
#      "Native fallback" in the copy's user_prefs.json;
#   5. writes the deployed git commit to ~/Dashboard_sw7/DEPLOYED_COMMIT, installs
#      ~/start_sw7_dashboard.sh and starts the dashboard again (unless --no-restart).
#
# No sudo needed. Uses the ssh key ~/.ssh/pi4_camera_key by default (the same key
# is installed for piadam on the Pi 5).
set -euo pipefail

PI5=Pirate5.local
KEY="$HOME/.ssh/pi4_camera_key"
USER_NAME=piadam
RESTART=1

usage() {
    sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --pi5) [ "$#" -ge 2 ] || usage; PI5=$2; shift 2 ;;
        --key) [ "$#" -ge 2 ] || usage; KEY=$2; shift 2 ;;
        --user) [ "$#" -ge 2 ] || usage; USER_NAME=$2; shift 2 ;;
        --no-restart) RESTART=0; shift ;;
        -h|--help) usage ;;
        *) echo "unknown argument: $1" >&2; usage ;;
    esac
done

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
INTEG=$(dirname "$HERE")
REPO=$(git -C "$INTEG" rev-parse --show-toplevel)
COMMIT=$(git -C "$REPO" rev-parse HEAD)
if [ -n "$(git -C "$REPO" status --porcelain -- DashboardIntegration)" ]; then
    echo "WARNING: DashboardIntegration has uncommitted changes; recording the commit as $COMMIT-dirty"
    COMMIT="$COMMIT-dirty"
fi

FILES=("$INTEG"/*.py "$INTEG/tests/dashboard_patches.py" "$HERE/apply_patches.py" "$HERE/start_sw7_dashboard.sh" "$HERE/pi5_beacon.py")
for f in "${FILES[@]}"; do
    [ -f "$f" ] || { echo "missing: $f" >&2; exit 1; }
done

SSH_OPTS=(-i "$KEY" -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new)
TARGET="$USER_NAME@$PI5"

echo "Deploying commit $COMMIT to $TARGET"
ssh "${SSH_OPTS[@]}" "$TARGET" 'mkdir -p ~/sw7_integration'
scp -q "${SSH_OPTS[@]}" "${FILES[@]}" "$TARGET:sw7_integration/"
echo "Copied ${#FILES[@]} files to ~/sw7_integration"

# The remote part. CR characters are stripped in case this file was checked out
# with Windows line endings.
tr -d '\r' <<'REMOTE' | ssh "${SSH_OPTS[@]}" "$TARGET" bash -s -- "$COMMIT" "$RESTART"
set -euo pipefail
COMMIT=$1
RESTART=$2
TEAM="$HOME/Dashboard"
OURS="$HOME/Dashboard_sw7"
INT="$HOME/sw7_integration"
PY="$HOME/tukzie-env/bin/python"
[ -x "$PY" ] || PY=python3

[ -d "$TEAM" ] || { echo "ERROR: $TEAM not found" >&2; exit 1; }
[ "$OURS" != "$TEAM" ] || { echo "ERROR: build dir equals team dir" >&2; exit 1; }
sed -i 's/\r$//' "$INT"/*.py "$INT"/*.sh

our_pids() {
    # python processes of this user whose working directory is ~/Dashboard_sw7
    # (also matches the "(deleted)" form after the folder was moved away).
    local p cwd
    for p in $(pgrep -u "$(id -u)" -f python || true); do
        cwd=$(readlink "/proc/$p/cwd" 2>/dev/null || true)
        case "$cwd" in
            "$OURS"|"$OURS (deleted)") echo "$p" ;;
        esac
    done
}

pids=$(our_pids)
if [ -n "$pids" ]; then
    echo "Stopping our dashboard: pid $(echo $pids)"
    kill $pids 2>/dev/null || true
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        [ -z "$(our_pids)" ] && break
        sleep 0.5
    done
    left=$(our_pids)
    if [ -n "$left" ]; then
        echo "Still running after 5 s, sending SIGKILL: $(echo $left)"
        kill -9 $left 2>/dev/null || true
    fi
else
    echo "Our dashboard was not running"
fi

if [ -d "$OURS" ]; then
    rm -rf "$OURS.prev"
    mv "$OURS" "$OURS.prev"
    echo "Previous build kept as $OURS.prev"
fi
cp -r "$TEAM" "$OURS"
chmod -R u+w "$OURS"
find "$OURS" -name __pycache__ -type d -prune -exec rm -rf {} +
echo "Fresh copy of $TEAM made at $OURS"

"$PY" "$INT/apply_patches.py" "$OURS" --source "$INT" --native-map --team-dir "$TEAM"

echo "$COMMIT" > "$OURS/DEPLOYED_COMMIT"
cp "$INT/start_sw7_dashboard.sh" "$HOME/start_sw7_dashboard.sh"
chmod +x "$HOME/start_sw7_dashboard.sh"
echo "Installed ~/start_sw7_dashboard.sh"

# Boot: the Pi 5 desktop is labwc (Wayland), which ignores ~/.config/autostart/*.desktop and
# runs ~/.config/labwc/autostart, where the team's launcher is. Keep their file once as
# autostart.team-backup (restore by copying it back), then point the line at our launcher.
LABWC="$HOME/.config/labwc/autostart"
if [ -f "$LABWC" ] && ! grep -q start_sw7_dashboard "$LABWC"; then
    [ -f "$LABWC.team-backup" ] || cp "$LABWC" "$LABWC.team-backup"
    sed -i 's#/home/piadam/start_dashboard.sh#/home/piadam/start_sw7_dashboard.sh#' "$LABWC"
    grep -q start_sw7_dashboard "$LABWC" || echo "/home/piadam/start_sw7_dashboard.sh &" >> "$LABWC"
    echo "labwc autostart now starts the SW-7 dashboard (team file kept as $LABWC.team-backup)"
fi
# Stop the team's dashboard if it is running, so only ours is on screen (their files are untouched).
for p in $(pgrep -f "tukzie-env/bin/python main.py"); do
    [ "$(readlink "/proc/$p/cwd")" = "$TEAM" ] && kill "$p" && echo "Stopped the team dashboard (pid $p) for this session"
done

if [ "$RESTART" = "1" ]; then
    setsid nohup "$HOME/start_sw7_dashboard.sh" >/dev/null 2>&1 < /dev/null &
    started=""
    for _ in $(seq 1 16); do
        sleep 0.5
        started=$(our_pids)
        [ -n "$started" ] && break
    done
    if [ -n "$started" ]; then
        sleep 3
        if [ -n "$(our_pids)" ]; then
            echo "Dashboard running: pid $(echo $(our_pids))"
        else
            echo "ERROR: dashboard started and then exited. Last log lines:" >&2
            tail -n 20 "$HOME/sw7_dashboard.log" >&2 || true
            exit 1
        fi
    else
        echo "ERROR: dashboard did not start. Last log lines:" >&2
        tail -n 20 "$HOME/sw7_dashboard.log" >&2 || true
        exit 1
    fi
else
    echo "Not restarted (--no-restart). Start with: ~/start_sw7_dashboard.sh &"
fi
echo "DEPLOYED_COMMIT=$(cat "$OURS/DEPLOYED_COMMIT")"
REMOTE

echo "Deployed commit: $COMMIT"
