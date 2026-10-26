#!/usr/bin/env bash
# SW-7: speech and Bluetooth speaker on the Pi 5, as set up on 26 Oct 2026. Safe to run again.
#
#   1. espeak-ng (offline speech, the dashboard's last fallback) and libportaudio2 (apt);
#   2. edge-tts upgraded in tukzie-env (7.2.8 was refused by Microsoft with 403; 7.3.1 works), vosk and
#      sounddevice for the voice commands, and the Vosk small English model in ~/vosk-model-small-en-us-0.15;
#   3. the dashboard's online voice set to "auto" (edge-tts, Leah en-ZA neural, then gTTS); it was "gTTS";
#   4. the telemetry ingest pointed at broker.hivemq.com (test.mosquitto.org was down on 25 Oct);
#   5. the speaker paired, trusted and set as the default output in A2DP (music quality). The hands-free
#      profile also gives its microphone, but playback drops to call quality, so it is not used for now.
#
# Run on the Pi 5 as piadam:  bash pi5_audio_setup.sh [speaker MAC]   (speaker in pairing mode)
set -euo pipefail

MAC=${1:-F4:CE:50:3B:59:F4}        # Volkano Mamba 2.0
ENV=$HOME/tukzie-env
PREFS=$HOME/Dashboard_sw7/app/asis/data/user_prefs.json

sudo apt-get install -y -q espeak-ng libportaudio2
"$ENV/bin/pip" install -q -U edge-tts vosk sounddevice
if [ ! -d "$HOME/vosk-model-small-en-us-0.15" ]; then
    (cd "$HOME" && wget -q https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip \
        && unzip -q vosk-model-small-en-us-0.15.zip && rm vosk-model-small-en-us-0.15.zip)
fi

if [ -f "$PREFS" ]; then
    cp -n "$PREFS" "$PREFS.bak_audio_setup" || true
    "$ENV/bin/python" - "$PREFS" <<'EOF'
import json, sys
p = sys.argv[1]; d = json.load(open(p)); g = d.setdefault("global", {})
g["online_voice_provider"] = "auto"; g["edge_tts_voice"] = "en-ZA-LeahNeural"
json.dump(d, open(p, "w"), indent=2)
EOF
fi

cat > "$HOME/sw7_server/sw7_ingest.env" <<'EOF'
SW7_MQTT_HOST=broker.hivemq.com
SW7_MQTT_PORT=1883
SW7_MQTT_TOPIC=sw7/telemetry
EOF

{ echo "agent NoInputNoOutput"; echo "default-agent"; echo "pairable on"; echo "scan on"; sleep 12
  echo "pair $MAC"; sleep 10; echo "trust $MAC"; sleep 1; echo "connect $MAC"; sleep 8
  echo "scan off"; echo quit; } | bluetoothctl >/dev/null 2>&1 || true
CARD=bluez_card.${MAC//:/_}
SINK=bluez_sink.${MAC//:/_}.a2dp_sink
pactl set-card-profile "$CARD" a2dp_sink 2>/dev/null || true
pactl set-default-sink "$SINK" && pactl set-sink-volume "$SINK" 80%

systemctl --user restart sw7-ingest
sudo systemctl restart sw7-dashboard
echo "done: $(bluetoothctl info "$MAC" | grep -E 'Connected')"
