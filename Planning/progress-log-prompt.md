# Prompt: build the SW-7 project log

Written 2026-09-28. Used once to create PROJECT_LOG.md from the project's
history. After that, the `progress-scribe` agent (.claude/agents/) keeps
it current.

---

Build PROJECT_LOG.md at the root of the Tukzie-HPEC-HUD repo: the single
record of everything technical done on SW-7 from the start of the project
until now, and every decision made along the way. The student uses it to
know where the project stands, to write the report, and to answer
questions at the presentation, so it must be complete, accurate and easy
to scan.

Sources, in order of authority:
1. The repo itself: `git log --reverse --stat` (47+ commits from
   2026-08-03), the code, BenchTest logs, CameraDetection and
   DashboardIntegration READMEs, Planning/ documents.
2. The report source in Report/*.tex (what was claimed and measured).
3. The GA tracking form in GA Tracking Form/ (what the student reported).
4. The Claude Code session transcript at
   C:\Users\0geda\.claude\projects\c--Users-0geda-OneDrive---University-of-Cape-Town-Documents-PlatformIO-Projects\02999ba8-77fc-45f7-8817-da26b024fcdd.jsonl
   (very large; search it with grep for decisions and results, never read
   it whole).
Where sources disagree, the code and measured logs win; note the conflict.

Structure:
1. Title, one-paragraph summary of the project, "Last updated" line.
2. Where we are: a short paragraph and the status board (Done with
   evidence; In progress; Waiting on someone, naming who; To do), grouped
   by subsystem, with the deadlines (report pre-submission opens 6 Oct,
   final report 27 Oct 23:59, presentations 16 to 17 Nov, Open Day 18 Nov).
3. Decisions register: date, decision, why, who, status (agreed / pending
   supervisor / reversed). Include hardware choices, scope changes,
   method choices, fixes chosen over alternatives, and writing or
   reporting rules the student set.
4. Timeline: dated entries from 2026-08-03 to today, grouped by week,
   each with commit hashes.
5. Technical breakdown per subsystem: ESP32-S3 telemetry unit (boards,
   FreeRTOS tasks, dual IMU acquisition, calibration, ride features,
   fusion, BMS over BLE, GNSS, LTE and MQTT, local logging, sync pulse);
   Raspberry Pi 4 camera (provisioning, capture and sync, hazard detector,
   live view, latency measurement, service); dashboard integration; bench
   tools (live dashboard, logs); mechanical (camera casings); sensors on
   order (VL53L5CX, SEN55, optocouplers); report, GA form and
   presentation. For each: what it does, current state, key measured
   numbers with their source, known limitations.
6. Findings and open issues: every unexpected result, with status.
7. Report sync table: report section, what it currently says, whether it
   matches the latest evidence.
8. Tooling: how to build the report (Tectonic recipe), flash the ESP32,
   reach the Pi, run the detector, where logs live.

Rules: no em dashes, no unnecessary bold, no invented facts (write
"unverified" or "not recorded" instead), never include the student's email
or any password, do not mention the ethics approval in any text meant for
the report (it may appear in the log's decisions register as a fact of
process). Commit and push when done.
