#!/usr/bin/env bash
# Copy one test day's recordings from both Raspberry Pis into one session folder for the analysis (27 Oct 2026).
#
#   bash BenchTest/collect_session.sh 2026-10-27            # into BenchTest/logs/run2_road_2026-10-27
#   bash BenchTest/collect_session.sh 2026-10-27 <folder>
#
# Files are chosen by modification time (written on that day), not by name: the capture programs can start before
# the clock syncs and then name their files with an old date. Collected:
#   Pi 5: recorder sessions (*_roadtest.jsonl), roadtest_markers.txt, front raw stream (raw_front), phone GPS log,
#         live alerts, power log, dashboard screenshots (screens, as a zip);
#   Pi 4: rear IMU node raw stream (roadtest/raw_rear), telemetry unit raw log (rawlog), live alerts, sync log.
# Then: python -m BenchTest.analysis.run --session <folder> --out <folder>/analysis
set -euo pipefail

DAY=${1:?usage: collect_session.sh YYYY-MM-DD [folder]}
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT=${2:-"$HERE/logs/run2_road_$DAY"}
KEY="$HOME/.ssh/pi4_camera_key"
NEXT=$(date -d "$DAY + 1 day" +%F)
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=8)

pick() {   # first host that answers ssh
    for h in "$@"; do "${SSH[@]}" "$h" true 2>/dev/null && { echo "$h"; return 0; }; done
    return 1
}
PI5=$(pick piadam@Pirate5.local piadam@192.168.137.188) || { echo "Pi 5 not reachable"; exit 1; }
PI4=$(pick ogeder@pi4-camera.local ogeder@192.168.137.85) || PI4=""
echo "Pi 5: $PI5   Pi 4: ${PI4:-not reachable (rear raw not collected)}"
mkdir -p "$OUT"

fetch() {   # host, remote find expression; copies the matching files into $OUT through tar
    local host=$1; shift
    "${SSH[@]}" "$host" "cd ~ && find $* -type f -newermt '$DAY' ! -newermt '$NEXT' -print0 2>/dev/null | tar --null -cf - -T - --transform 's|.*/||'" \
        | tar -xf - -C "$OUT"
}

fetch "$PI5" "roadtest -maxdepth 1 -name '*_roadtest.jsonl'"
"${SSH[@]}" "$PI5" "cat ~/roadtest/roadtest_markers.txt 2>/dev/null" > "$OUT/roadtest_markers.txt" || true
fetch "$PI5" "roadtest/raw_front -name 'front_raw*'"
fetch "$PI5" "roadtest/phone_gps -name 'phone_gps*'"
"${SSH[@]}" "$PI5" "cat ~/alerts_live.jsonl 2>/dev/null" > "$OUT/pi5_alerts_live.jsonl" || true
"${SSH[@]}" "$PI5" "cd ~ && find . -maxdepth 2 -name '*powerwatch*' -newermt '$DAY' -type f | head -5 | xargs -r tar -cf - " | tar -xf - -C "$OUT" 2>/dev/null || true
"${SSH[@]}" "$PI5" "cd ~/roadtest && find . -path '*screens*' -newermt '$DAY' ! -newermt '$NEXT' -type f -print0 2>/dev/null | tar --null -czf - -T -" > "$OUT/pi5_screens.tar.gz" || true

if [ -n "$PI4" ]; then
    fetch "$PI4" "roadtest/raw_rear -name 'rear_raw*'"
    "${SSH[@]}" "$PI4" "cd ~/rawlog 2>/dev/null && find . -name 'rear_raw*' -newermt '$DAY' ! -newermt '$NEXT' -type f -print0 | tar --null -cf - -T -" \
        | (mkdir -p "$OUT/telemetry_unit_rawlog" && tar -xf - -C "$OUT/telemetry_unit_rawlog") || true
    "${SSH[@]}" "$PI4" "cat ~/alerts_live.jsonl 2>/dev/null" > "$OUT/pi4_alerts_live.jsonl" || true
    "${SSH[@]}" "$PI4" "cat ~/sync_log.csv 2>/dev/null" > "$OUT/pi4_sync_log.csv" || true
fi

echo "Collected into $OUT:"
ls -la "$OUT" | tail -n +2
(cd "$OUT" && sha256sum * 2>/dev/null > SHA256SUMS.txt) || true
echo "Next: python -m BenchTest.analysis.run --session \"$OUT\" --out \"$OUT/analysis\""
