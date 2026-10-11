# Bench observations, 10 to 11 October 2026

Measurements taken during the bench session of 10 to 11 October that the presentation and report quote. Each line
says how it was measured. Raw files are next to this one where they exist.

## Time-of-flight sensors after the reader fix

- After the 0.5 s I/O timeout fix (commit d155665) and rewiring, the telemetry bridge on the Pi 4 opened all three
  sensors ("ToF sensors open: left, ahead, right" in its journal).
- Hand test: /telemetry polled twice a second for 3 minutes while a hand was held about 20 cm in front of the ahead
  and right sensors in turn. Raw file: 2026-10-10_tof_hand_test.txt (columns: time, left_mm, ahead_mm, right_mm).
  Left read 0.97 to 1.05 m throughout (a wall); ahead read 80 to 264 mm with the hand (and 744 mm once); right read
  157 to 199 mm with the hand and 1.13 to 1.25 m otherwise. Nulls are "no target in range".

## Raspberry Pi 4 temperature and power

- Without cooling: 80.8 to 81.3 C with the detector running, power flags 0xd0000 (under-voltage, throttling and
  soft temperature limit since boot), BenchTest/sw7_check.py and vcgencmd, 10 Oct.
- After a fan was fitted: 47.7 to 48.7 C a few minutes after boot (vcgencmd measure_temp three times), 57.4 C in a
  later sw7_check.py run the same evening, and 66.2 C on 11 Oct with the detector and the bridge running for about
  5 hours. Power flags 0x0 once the ESP32 was no longer drawing from the Pi's USB.
- Reboots: three restarts in about 20 minutes on 10 Oct while the ESP32 (LTE modem) was plugged straight into a Pi 4
  USB port (uptime reset seen over SSH); none in the following 4 hours after it was moved off the Pi.

## Camera detector on a healthy Pi 4

- 11 Oct, from the hazard-detector service's own [timing] log lines (journalctl), Pi 4 at 1.8 GHz, flags 0x0, 66 C,
  4 threads, preview on, NoIR tuning, saturation 1.8: 14.6 to 14.7 fps; total latency (camera readout to detection)
  median 118 to 122 ms, 95th percentile 146 to 148 ms; inference median 51 to 52 ms; queue wait median 55 to 58 ms.
- This is lower than the 19.5 fps and 102 ms median in the report's earlier benchmark (C4), which ran without the
  telemetry bridge, sensor fusion polling and the live preview being viewed; the cause of the difference has not
  been isolated.

## Voice on the Raspberry Pi 5

- The Pi 5 has no analogue audio and the touchscreen's EDID declares no audio, so the output was a null sink until
  Bluetooth earphones (soundcore R50i NC) were paired on 11 Oct (pulseaudio-module-bluetooth installed).
- The dashboard's Microsoft Edge voice (edge-tts 7.2.8, en-ZA-LeahNeural) was refused by the service with HTTP 403
  although the Pi's clock was synchronised; gTTS (Google) was installed and a test phrase played through the
  earphones (8.6 s, heard by the student). The dashboard's voice provider was already set to gTTS.
