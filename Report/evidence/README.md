# Test evidence

Raw evidence behind the results in the report: screenshots, terminal
output and logs, one file per test, named so they sort by date. Appendix C
of the report ("Test Evidence") indexes them and shows the key ones.

## Naming

`YYYY-MM-DD_subsystem_what.ext`, for example
`2026-09-28_camera_run2_after_fixes.txt` or
`2026-10-02_esp32_flash_stall_log_off.log`. Subsystems: `esp32`, `imu`,
`bms`, `gnss`, `mqtt`, `camera`, `sync`, `tof`, `sen55`, `dashboard`,
`vehicle`. Put a two-line `#` comment at the top of every text file saying
what the test was and what it shows.

## How to capture

| What | How |
|---|---|
| ESP32 output | In `BenchTest/sw7_console.html`, press "Save session log" (every line with a timestamp). Or `pio device monitor -b 115200 -f log2file`, which writes a log file in the project folder. |
| Pi terminal output | Add `2>&1 \| tee ~/evidence/<name>.txt` to the command, for example `python3 hazard_detector.py --duration 60 2>&1 \| tee ~/evidence/2026-10-01_camera_parkinglot.txt`, then copy it back with `scp -i ~/.ssh/pi4_camera_key ogeder@<pi-ip>:~/evidence/* Report/evidence/` from the laptop. |
| Laptop screen | Windows: Win+Shift+S, then save the snip here. |
| Pi screen | `grim ~/evidence/<name>.png` on the Pi desktop (Wayland), then scp it back. |
| Timing | `hazard_detector.py --timing-log <name>.csv`, keep the CSV and the `[timing]` lines. |
| Runbook pastes | Anything sent through the Camera Test Runbook's Send box can be exported from there on request. |

## Rules

- Evidence must be real output from the test it names. Never edit numbers
  in an evidence file; if a file needs explaining, add a `#` comment.
- No identifiable people other than the student, and no number plates,
  in any stored image. For camera results keep the terminal output and
  the alert log, which hold only class, band, confidence, timestamp and
  status, or use screenshots with no people in view.
- Replays of recorded logs are fine as figures, but must use only the
  recorded data (no sample or test lines).
