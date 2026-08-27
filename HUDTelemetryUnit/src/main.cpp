#include <Arduino.h>

// Makerfabs ESP32-S3 to A7670X UART Pins
#define A7670X_RX_PIN 47
#define A7670X_TX_PIN 48
#define MODEM_BAUD 115200

unsigned long lastHeartbeat = 0;
const unsigned long heartbeatInterval = 1000;

void setup() {
  Serial.begin(115200);

  const unsigned long serialWaitStart = millis();
  while (!Serial && millis() - serialWaitStart < 3000) {
    delay(100);
  }
  delay(1000);

  Serial.println("\nSW-7 ESP32-S3 Firmware v0.2.0");
  Serial.println("==============================");
  Serial.println("System booted: ESP32-S3");
  Serial.println("Status: ONLINE\n");

  Serial.println("Starting Serial1 (RX: 47, TX: 48)...");
  Serial1.begin(MODEM_BAUD, SERIAL_8N1, A7670X_RX_PIN, A7670X_TX_PIN);
  delay(2000);

  const char* testCommands[] = {"AT", "AT+CPIN?", "AT+CSQ", "AT+CREG?"};

  for (int i = 0; i < 4; i++) {
    Serial.print("---> Sending: ");
    Serial.println(testCommands[i]);
    Serial1.println(testCommands[i]);

    unsigned long startWait = millis();
    while (millis() - startWait < 2000) {
      while (Serial1.available()) {
        Serial.write(Serial1.read());
      }
    }
    Serial.println("\n-----------------");
  }

  Serial.println("==============================");
  Serial.println("Sequence complete. Entering pass-through mode.");
  Serial.println("Type AT commands below freely:");
}

void loop() {
  if (millis() - lastHeartbeat >= heartbeatInterval) {
    lastHeartbeat = millis();
  }

  if (Serial.available()) {
    Serial1.write(Serial.read());
  }

  if (Serial1.available()) {
    Serial.write(Serial1.read());
  }
}