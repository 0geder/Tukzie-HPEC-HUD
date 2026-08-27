#include <Arduino.h>

// Makerfabs ESP32-S3 4G LTE CAT1 A7670X mapping:
// ESP32-S3 GPIO47 <- modem TX
// ESP32-S3 GPIO48 -> modem RX
constexpr int A7670X_RX_PIN = 47;
constexpr int A7670X_TX_PIN = 48;
constexpr unsigned long MODEM_BAUD = 115200;
constexpr unsigned long COMMAND_TIMEOUT_MS = 2000;

bool sendCommand(const char *command) {
  while (Serial1.available() > 0) {
    Serial1.read();
  }

  Serial.print(">> ");
  Serial.println(command);
  Serial1.println(command);

  String response;
  const unsigned long deadline = millis() + COMMAND_TIMEOUT_MS;
  while (millis() < deadline) {
    while (Serial1.available() > 0) {
      const char character = static_cast<char>(Serial1.read());
      response += character;
      Serial.write(character);
    }

    if (response.indexOf("\nOK") >= 0 || response.endsWith("OK\r")) {
      return true;
    }
    if (response.indexOf("\nERROR") >= 0 || response.endsWith("ERROR\r")) {
      return false;
    }
    delay(1);
  }

  return response.indexOf("OK") >= 0;
}

void setup() {
  Serial.begin(115200);
  Serial1.begin(MODEM_BAUD, SERIAL_8N1, A7670X_RX_PIN, A7670X_TX_PIN);

  Serial.println("\nA7670X UART verification");
  Serial.println("UART: modem TX GPIO47, modem RX GPIO48");

  if (!sendCommand("AT")) {
    Serial.println("\nAT failed: no OK response.");
    return;
  }

  Serial.println("\nAT succeeded. Testing modem status commands.");
  sendCommand("AT+CPIN?");
  sendCommand("AT+CSQ");
  sendCommand("AT+CREG?");
}

void loop() {
}
