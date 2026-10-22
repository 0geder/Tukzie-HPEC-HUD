// Copy this file to mqtt_secrets.h (same folder) and fill in the broker you have been given.
// mqtt_secrets.h is git-ignored: it stays on this laptop, is never committed, and must not be
// pasted into an AI assistant. Delete mqtt_secrets.h to go back to the public test broker.
#pragma once
#define MQTT_BROKER_HOST "broker.example.org"
#define MQTT_BROKER_PORT 1883
#define MQTT_USERNAME "your-username"
#define MQTT_PASSWORD "your-password"
#define MQTT_TOPIC "your/topic"
// Firmware v0.7.5: the published record leaves out lat, lon and the cell
// position unless this is 1. Set it to 1 only if this broker is private.
// #define MQTT_INCLUDE_POSITION 1
