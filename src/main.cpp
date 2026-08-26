#include <Arduino.h>

namespace {

// Baseline firmware version; keep this independent from future sensor modules.
constexpr char FIRMWARE_VERSION[] = "0.1.0";
constexpr unsigned long HEARTBEAT_INTERVAL_MS = 5000;

unsigned long lastHeartbeatMs = 0;

void printStartupMessage() {
  Serial.println();
  Serial.println("SW-7 ESP32-S3 Firmware");
  Serial.println("======================");
  Serial.println("System booted");
  Serial.print("Firmware version: ");
  Serial.println(FIRMWARE_VERSION);
  Serial.println("MCU: ESP32-S3");
  Serial.println("Status: ONLINE");
  Serial.println();
}

void printHeartbeatIfDue(unsigned long nowMs) {
  if (nowMs - lastHeartbeatMs < HEARTBEAT_INTERVAL_MS) {
    return;
  }

  lastHeartbeatMs = nowMs;
  Serial.println("[HEARTBEAT] System running");
}

}  // namespace

void setup() {
  // This baseline validates the MCU and primary serial interface only.
  Serial.begin(115200);
  printStartupMessage();
}

void loop() {
  // Use elapsed time instead of delay so future real-time tasks can be added.
  printHeartbeatIfDue(millis());
}

