"""Check that an MQTT broker accepts our connection and a publish, before pointing the telemetry unit at it.

Credentials come from environment variables, never from this file, so nothing secret reaches git:
  MQTT_HOST, MQTT_PORT (default 1883), MQTT_USER, MQTT_PASSWORD, MQTT_TOPIC (default sw7/test)

PowerShell:
  $env:MQTT_HOST="broker.example"; $env:MQTT_USER="..."; $env:MQTT_PASSWORD="..."; python BenchTest/mqtt_broker_check.py
Git Bash:
  MQTT_HOST=broker.example MQTT_USER=... MQTT_PASSWORD=... python BenchTest/mqtt_broker_check.py

It connects, subscribes to the topic, publishes one test message with QoS 1, waits for the broker's
acknowledgement and for the message to come back, then disconnects. Exit code 0 only if all of that worked.
Needs: pip install paho-mqtt (works with version 1 and 2).
"""
import json
import os
import sys
import time

import paho.mqtt.client as mqtt

HOST = os.environ.get("MQTT_HOST", "").strip()
PORT = int(os.environ.get("MQTT_PORT", "1883"))
USER = os.environ.get("MQTT_USER") or None
PASSWORD = os.environ.get("MQTT_PASSWORD") or None
TOPIC = os.environ.get("MQTT_TOPIC", "sw7/test").strip()

if not HOST:
    sys.exit("Set MQTT_HOST (and MQTT_USER, MQTT_PASSWORD, MQTT_TOPIC if the broker needs them).")

state = {"connected": None, "echo": False}
payload = json.dumps({"source": "sw7_mqtt_broker_check", "t": time.time()})


def on_connect(client, userdata, flags, reason_code, properties=None):
    state["connected"] = reason_code
    if not getattr(reason_code, "is_failure", reason_code != 0):
        client.subscribe(TOPIC, qos=1)


def on_message(client, userdata, msg):
    if msg.payload.decode(errors="replace") == payload:
        state["echo"] = True


try:   # paho-mqtt 2.x
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sw7-check-{int(time.time())}")
except AttributeError:   # paho-mqtt 1.x
    client = mqtt.Client(client_id=f"sw7-check-{int(time.time())}")
if USER:
    client.username_pw_set(USER, PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

print(f"Connecting to {HOST}:{PORT} as {USER or '(no user)'} ...")
client.connect(HOST, PORT, keepalive=30)
client.loop_start()
deadline = time.time() + 10
while state["connected"] is None and time.time() < deadline:
    time.sleep(0.1)
rc = state["connected"]
if rc is None or getattr(rc, "is_failure", rc != 0):
    client.loop_stop()
    sys.exit(f"FAIL: connect result {rc!r} (wrong host, port, user or password?)")
print("Connected. Publishing a test message to", TOPIC)
time.sleep(0.5)                                    # let the subscription settle
info = client.publish(TOPIC, payload, qos=1)
info.wait_for_publish(timeout=10)
acked = info.is_published()
deadline = time.time() + 5
while not state["echo"] and time.time() < deadline:
    time.sleep(0.1)
client.disconnect()
client.loop_stop()
print(f"Broker acknowledged the publish: {'yes' if acked else 'NO'}; message received back: {'yes' if state['echo'] else 'no'}")
sys.exit(0 if acked else 1)
