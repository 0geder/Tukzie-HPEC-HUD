# SW-7 project notes for Claude

SW-7 (UCT EEE4022S 2026, Samson Okuthe): "Embedded Telemetry, Road-Surface Characterisation and Camera-Based Hazard Detection for the TUKZIE Electric Tricycle"
(title since 23 Oct 2026; from 2 Oct it was "Development of an Embedded HPEC Telemetry Unit and Dashboard Integration for the TUKZIE Rev 0 Platform", and the
windshield HUD of the original brief was replaced by dashboard integration). ESP32-S3 firmware in TelemetryUnit/
(v0.7.0); Pi 4 camera detector and telemetry bridge in CameraDetection/;
add-ons for the vehicle's PySide6 dashboard on the Pi 5 (Pirate5) in
DashboardIntegration/; tests and logs in BenchTest/. README.md has the
architecture and folder map. The repository name predates the title change.

- After finishing any piece of work in this repo (a fix, a test, a
  decision, a report edit), run the `progress-scribe` agent with a short
  description of what was done, so PROJECT_LOG.md, CHANGELOG.md and the report stay
  current. PROJECT_LOG.md is the student's record of everything done and
  decided.
- Commit with plain messages, never a Co-Authored-By line, and push to
  origin main after each completed piece of work. Never push other teams'
  repos.
- Writing everywhere: no em dashes, no unnecessary bold.
- Ethics: D20 lifted by the student on 21 Oct 2026. The approval letter (EBE/03305/2026) is Appendix H and the report has an ethics and safety section (Methodology, sec:ethics).
- Verify every claim against a source or a measurement; say when
  something is unverified. No invented results, numbers or references.
- The student runs commands on the Raspberry Pi 4 (`pi4-camera`) and the
  ESP32 board themselves. Give copy-paste blocks with laptop and Pi
  clearly separated, and keep the Camera Test Runbook page current.
