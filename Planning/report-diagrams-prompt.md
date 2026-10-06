# Report diagrams (TikZ): brief

Written 6 Oct 2026 at the student's request: "if there's any diagrams to be shown, use the LaTeX library to draw it nicely ... don't hallucinate stuff".

## Goal

Replace text-art and missing diagrams in `Report/` with clean TikZ figures that a reader can take in at a glance, drawn from the code and configuration as they are, not from memory.

## Rules

1. Every box, arrow, number and label must be traceable to a file in the repo (firmware `TelemetryUnit/src/main.cpp`, `CameraDetection/fusion_config.json`, `sensor_fusion.py`, `telemetry_bridge.py`, `DashboardIntegration/*.py`, `TELEMETRY_LINK.md`) or to text already in the report. If a fact is not in the repo, leave it out of the figure.
2. Show the state as built, with the firmware or software version in the caption. Mark planned or untested parts as such (dashed outline, "planned" or "not yet wired").
3. One idea per figure. No decoration: no gradients, shadows or icons that carry no information. A restrained palette that prints in greyscale; colour never the only cue.
4. Text in the report's own font at a fixed 8.5 pt (`\swfont` in `sw7styles.tex`), so a figure looks the same in its preview and in the 11 pt report; check it on the rendered report pages.
5. Each figure in its own file under `Report/figures/tikz/`, included with `\input`, so it can be previewed alone (standalone build) and reused.
6. After adding figures: build the report, check there are no errors or undefined references, render the pages with the figures and look at them, then commit.
7. Plain English captions; no em dashes.

## Figures

| File | Shows | Source of truth | Where in the report |
|---|---|---|---|
| `system_architecture.tex` | Telemetry unit, Raspberry Pi 4 and Raspberry Pi 5: sensors, programs, ports, links and rates | `TELEMETRY_LINK.md`, `telemetry_bridge.py`, `hazard_detector.py`, `tof_reader.py`, `live_data_provider.py`, `main.cpp` | Methodology, section 1 (overview) |
| `firmware_tasks.tex` | FreeRTOS tasks per core with priorities and the queues between them (v0.7.1) | `main.cpp` lines 2376 to 2411 (queues and task creation) | Replaces the v0.4.0 text-art figure |
| `fusion_geometry.tex` | Top view: camera field of view, the three ToF cones, the 5 degree gate, 1.2 m range, overlap regions | `fusion_config.json`, `sensor_fusion.py` | Camera and time-of-flight fusion |
| `pi4_discovery.tex` | The order in which the dashboard looks for the Raspberry Pi 4, acceptance rule, re-search and back-off | `sw7_endpoints.py`, report section "Finding the Raspberry Pi 4" | That section |

## Done (6 Oct 2026)

All four figures drawn, previewed standalone, inserted and checked on the rendered report pages. The v0.4.0 text-art task figure was replaced by the v0.7.1 diagram. The report builds with no errors or undefined references. 16 overfull-line warnings remain in body text (long unbreakable words); they predate the figures and are left for the length pass.
