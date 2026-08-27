# Tukzie-HPEC-HUD
Embedded telemetry and windshield HUD system for the TUKZIE Rev 0 platform. UCT EEE4022S Final Year Project (2026).

## A7670X UART verification

The [`a7670x_uart_verification.ino`](a7670x_uart_verification.ino) sketch verifies
the Makerfabs ESP32-S3 4G LTE CAT1 UART link without opening a data connection.
It uses the documented mapping:

- ESP32-S3 GPIO47: modem TX
- ESP32-S3 GPIO48: modem RX
- UART: 115200 baud, 8 data bits, no parity, 1 stop bit

Upload it with the modem powered and open the main serial monitor at 115200 baud.
The sketch sends `AT`; when the modem responds with `OK`, it sends `AT+CPIN?`,
`AT+CSQ`, and `AT+CREG?` in sequence.
