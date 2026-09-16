# Tukzie HPEC Telemetry Unit and Windshield HUD

An embedded telemetry system and windshield head up display for the TUKZIE Rev 0 platform, a 72V electric cargo tricycle built at the University of Cape Town for affordable, locally serviceable electric mobility in African contexts.

This is a final year Electrical and Computer Engineering project (EEE4022S, 2026) at UCT.

## What this project does

The system reads sensor data from the vehicle, processes it on an embedded microcontroller, and gives the driver useful information through a windshield display. It also sends telemetry data to a central server so the vehicle's performance can be tracked over time.

Specifically, the project covers:

* **Vehicle dynamic response sensing.** Two IMUs (inertial measurement units) measure vibration and motion, used to tell the difference between road induced disturbance (potholes, bumps) and vibration that just comes from the motor and drivetrain.
* **GPS positioning.** The onboard 4G modem also provides satellite positioning, so vehicle location and speed can be logged.
* **Battery monitoring.** The vehicle's battery pack is read over Bluetooth Low Energy, giving voltage, current, state of charge, temperature, and fault status.
* **Camera based hazard awareness.** A Raspberry Pi camera runs a lightweight object detection model to flag pedestrians, cyclists, and other vehicles nearby, with a rough distance estimate. This is a hazard awareness aid, not a self driving system.
* **Time synchronisation.** A dedicated signal line keeps the microcontroller and the Raspberry Pi's clocks aligned, so sensor data and camera footage can be lined up afterwards.
* **Cellular connectivity.** A 4G modem on the main board lets the vehicle send data back to a central server even away from WiFi.
* **Windshield HUD.** A head up display for the driver, still in early planning, intended to show speed, battery level, and safety alerts without requiring the driver to look down.

## Repository layout

| Folder | Contents |
|---|---|
| `HUDTelemetryUnit/` | The main ESP32-S3 firmware (PlatformIO project). This is the code that runs on the vehicle. |
| `CameraDetection/` | The Raspberry Pi camera hazard detection script and its pretrained model. |
| `Report/` | Drafts of the final written report and the report template. |
| `Planning/` | Vehicle integration and test plans. |
| `Vehicle Documentation/` | The manufacturer's manual for the TUKZIE vehicle itself. |
| `GA Tracking Form/` | The graduate attributes tracking form required by the department. |
| `References/Papers/` | Academic papers used in the literature review, sorted by topic. |
| `References/Datasheets/` | Component datasheets. |

## Hardware

* Makerfabs ESP32-S3 board with a built in A7670X 4G LTE Cat 1 modem, running the main firmware
* Two MPU6050 accelerometer and gyroscope modules for vibration sensing
* A JBD/Xiaoxiang smart battery management system, read over Bluetooth
* A Raspberry Pi 4 with a camera module, for hazard detection and video recording
* The TUKZIE Rev 0 vehicle itself, a Jinpeng electric cargo tricycle

## Building the firmware

The firmware is a PlatformIO project.

```
cd HUDTelemetryUnit
pio run              # build
pio run -t upload    # flash to the board
pio device monitor    # view serial output
```

## Project status

Actively in development. The sensor acquisition, GNSS parsing, battery monitoring, and time sync systems are built and have been tested against real hardware. The camera hazard detection script is written but not yet tested against a live camera. The windshield HUD has not been built yet. See the report drafts in `Report/` for full detail on what has been validated so far and what is still outstanding.

## Course context

This project is submitted as part of EEE4022S, the final year project course in the Department of Electrical Engineering at the University of Cape Town.
