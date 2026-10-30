# Numbers cheat sheet: 15 to know by heart

One page for the panel on 16 or 17 November 2026 (10-minute talk, 5 minutes of questions). Written 30 October 2026 from the submitted report and BenchTest/logs/run2_road_2026-10-27/analysis/run2_summary_numbers.txt. Section numbers are the report's. Kept separate from SW7_Talking_Points.md because source/build_deck.js regenerates that file from the deck's speaker notes. The word-for-word talk is SW7_Speaker_Script.md; hard questions are in SW7_QA_Prep.md.

Project title: Embedded Telemetry with Road-Surface Characterisation and Camera-Based Hazard Detection for the TUKZIE Electric Trike. Say the title or "the system", not the old project code.

| # | Number | What it means | Source |
|---|---|---|---|
| 1 | 200.005 and 200.006 Hz | Front and rear inertial nodes on the road, 27 Oct. Front 1,791,190 samples, no gap; rear 1,184,780 with 910 lost in transport (0.08 %). R1 met at the front. | 5.1, Table 5.3 |
| 2 | 33 to 44 ms | Flash-write gap on the telemetry unit, not filled by later reads. Buffering made it rarer, not shorter. Inertial nodes with no flash log: 200.00 Hz, no interval over 5.2 ms. | 5.1, 6.1, 7.1 |
| 3 | 5.0 % and 5.3 % | CV of whole-pass a_w, 5 passes at 10 km/h on the smooth loop, rear and front (rear a_w 1.78, front 1.16 m/s2). Criterion 10 %. | 5.3 |
| 4 | About 2 times | Rough strip against smooth loop at the same speed: rear 3.61 against 1.78, front 2.26 against 1.16 m/s2 (CV near 20 %, laps covered different stretches). | 5.3 |
| 5 | ICC 0.16 | Place by place (8 m cells), rear smooth loop, 95 % interval -0.09 to 0.75; rough 0.01; front 0.00 to 0.02; at most 0.32 in sensitivity checks. Criterion 0.75. Not met. | 5.3, 6.2 |
| 6 | 0.9 to 3.1 % | Share of 0.5 to 80 Hz energy in the powertrain lines in powered passes (0.4 % coasting); 65 to 84 % lies at 4 to 8 Hz. Coasting a_w 1.80 against 1.78 powered. | 5.3, 6.2 |
| 7 | 42.75, 49.0, 64.0 Hz | Powertrain lines from the 23 Oct stand runs; rear vibration rose 5 to 7 times, energy 40 to 70 Hz, same lines at the front. | 5.3 |
| 8 | 4,196 of 4,201 | Per-second records over the wired serial link on 27 Oct (99.9 %); 62 % over USB on 19 Oct. R10 partly met on the vehicle (5 missed). | 5.7, Table 5.3 |
| 9 | 112 of 112 | Records stored after a 10-minute radio outage (T15); reconnect 5.2 s; 24 only after a backfill from the unit's log; 0 duplicates. | 5.7, Table 5.2 |
| 10 | 153 records, 0.44 s | LTE on the road: 37 live, 116 replayed; live latency median 0.44 s (95th 0.55 s, n = 9); no reconnection after 11:51. | 5.7 |
| 11 | 51 to 54 ms against 118 to 122 ms | Detector median, readout to result: Pi 5 beside the dashboard against Pi 4 with the whole system (bench). Road: front 23.3 fps, 68 ms; rear 12.1 fps, 103 ms. Onset at the detector about 0.26 s. | 5.6, Table 5.3 |
| 12 | 94 and 10 arc minutes | At the measured 0.62 m eye distance: speed digits 94, alert banner 10. ISO 15008: 20 recommended, 16 acceptable, 12 minimum. Warnings not legible at a glance. | 5.8, 6.5 |
| 13 | 9.845 and 9.941 m/s2 | Rear and front at rest on the vehicle, 27 Oct, against 9.81. R2 not met on the vehicle (criterion 9.80 to 9.82). | 5.2 |
| 14 | About every 4 s; 8 to 25 m | Vehicle GNSS position updated about every 4 s (near the 3 s poll), 8 to 25 m from the phone on the smooth loop; stale from 12:13 while still flagged fixed. Phone was the speed source. | 5.4 |
| 15 | 27 W | Whole system on the vehicle, read at the portable power station (EcoFlow); between the 17 W typical and 31 W peak estimates. Pi 4 under-voltage began 14 s after the modem came up on its USB port. | K.9, E.3.7 |

Also know: 13 requirements; 5 met on the bench (R1 to R3, R9, R10), 7 partly (R4 to R8, R11, R13), R12 glance time not tested (7.2). Passes at 15 and 20 km/h: 2 and 1 only (5.3). Report body 18,079 words. Videos: tuksense.site.
