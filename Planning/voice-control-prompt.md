# Voice control for the dashboard (prompt, 25 Oct 2026)

## Student's request (paraphrased from chat, 25 Oct)

Control the dashboard by voice, like a car assistant:
- "home" goes to the home (driving) page with the speed, and "map" goes to the map;
- "map, destination Rondebosch" looks the place up and offers the options; the driver says "first one" or "second one" and that becomes the destination on the map;
- the vehicle has no gear signal, so "reverse" or "rear camera" shows the rear camera and "front camera" goes back to the front camera;
- by default, once reversing is done, the dashboard returns to the home page with the speed.

## Constraints

1. Off by default (`TUKZIE_SW7_VOICE=1` turns it on), so it cannot break the deployed dashboard. Nothing is deployed without the student's approval of screenshots (memory: dashboard look).
2. Offline speech recognition on the Pi 5 (Vosk, a small English model), with no cloud service, so it works without coverage. Audio is processed in memory and never stored. This is the same data minimisation as the camera frames; nobody is a research subject.
3. Voice changes only what the display shows. It never controls the vehicle.
4. Reuse the dashboard's own hooks:
   - `main.switch_page_id("driving" | "navigation" | "sensors")`;
   - `main.sw7_dual.set_side("front" | "rear")`;
   - the Navigation page's destination field and suggestion list (sw7_search: setting the text runs the search; `_choose(item)` picks a row);
   - `asis.voice.speak()` for spoken confirmations, so the team's voice choice, volume and mute apply.
5. The intent parser is pure Python and host-tested. GUI behaviour is tested offscreen by feeding recognised text. Recognition is tested on scripted spoken commands generated as WAV files (no person recorded), giving accuracy and latency as a bench result.

## Behaviour

| Said | Action |
|---|---|
| "home", "go home", "speed", "driving", "dashboard" | Driving page |
| "map", "navigation" | Map page |
| "reverse", "rear camera", "back camera", "rear view" | Surroundings page, rear side; reverse mode on |
| "front camera", "front view" | Surroundings page, front side; reverse mode off |
| "done", "forward", "finished reversing" while in reverse mode | Driving page |
| "map destination X", "destination X", "go to X", "navigate to X", "take me to X" | Map page; X typed into the destination field; when suggestions arrive, the first three are read out ("Option one, ...") and the dashboard waits 20 s for a choice |
| "first", "one", "option one", "number one" (up to three) | Choose that suggestion: the destination is set and the route planned |
| "cancel", "stop" | End the choice or reverse mode |

**Reverse mode ends by itself** (back to the driving page), since there is no gear signal:
- after 45 s on the rear view with no command; or
- when the phone speed has been at or above 8 km/h for 3 s, because the vehicle is clearly driving forward.

**Listening:** always on when enabled, with short commands matched exactly. A spoken confirmation follows each action. An optional wake word is planned (`TUKZIE_SW7_VOICE_WAKE`, for example "dash"); without it, a phrase must parse as a command to have any effect.

## Deliverables

- `DashboardIntegration/sw7_voice_control.py` (parser, controller, Vosk listener), patched in with the other SW-7 modules.
- `DashboardIntegration/tests/test_voice_control.py`: parser cases, GUI actions offscreen with screenshots, reverse auto-return, and the destination choice flow with a fake search.
- `BenchTest/voice_recognition_check.py`: scripted commands spoken to WAV (Windows SAPI), recognised by Vosk; reports the share understood and the latency.
- Report: a short entry in Appendix G and one line in Recommendations. It is a bench feature, not a road result.
