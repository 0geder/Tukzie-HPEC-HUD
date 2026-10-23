# Run 2: what is done (23 Oct) and what remains (road part, Monday 26 Oct)

Deadlines: presubmission closes Monday 26 Oct (fall-back copy, not marked); final report Tuesday 27 Oct 23:59, no extension.
Word budget: the body is 14,610 words (long-report range 10,000 to 15,000), so Monday's results must replace the
placeholder text, not add to it.

## Done on 23 October (lab part, vehicle on stands)

- Both nodes on the vehicle, v0.7.8, 200 Hz, 0 drops; raw 200 Hz streams logged on both Pis; recorder and screenshots running.
- Two stand runs, throttle settings not recorded: 15:53:11 to 15:55:50 and 16:08:12 to 16:10:20; mean 3.2 and 4.5 A
  (peaks 4.4 and 6.2 A). Spectra done: rear 5 to 7 times rest, 40 to 70 Hz; the front shows the same lines (42.75, 49.0,
  64.0 Hz) at a smaller level. In the report (Results, R3 section, Figure res-stands).
- IMU calibration in the mounted position: front 0.9919 (firmware), rear 1.0094 (from the raw stream). R2 now met.
- Phone GNSS as speed and fallback position (Share GPS over the hotspot, sw7-phone-gps on the Pi 5): 13 satellites,
  0 checksum errors; dashboard speed checked with a simulated 20 km/h. In the report (Results R4, Appendix J).
- Pi 4: two restarts (14:17, 16:22:48), repeated under-voltage; the second restart 40 s after the rear unit restarted.
- Vehicle GNSS: antenna fitted, no fix in the lab in over 45 min.

## Before Monday

| # | Item | Who |
|---|---|---|
| 1 | Copy today's data off both Pis; add to the data index: done 23 Oct (BenchTest/logs/run2_lab_2026-10-23) | Claude |
| 2 | Spectra of the two stand runs from the raw streams (Welch), rest against turning, front against rear: done 23 Oct | Claude |
| 3 | Dashboard: take the phone's speed even when the rear unit's data is stale (a Pi 4 restart blanked the speedometer); redeploy, screenshot | Claude |
| 4 | Recorders and raw capture wait for the clock sync at boot (files were named with the 22 Oct date) | Claude |
| 5 | Rear ESP32 on its own supply, never the Pi 4's USB; Pi 4 on a stronger supply (EcoFlow if Dr Amayo agrees, or 5 V 3 A with a short thick cable) | Student |
| 6 | Vehicle GNSS: antenna outside, flat, open sky; reseat the connector; else the spare | Student |
| 7 | Front ToF wires (Pi 5 pins 1, 3, 5, 6) and the rear left ToF | Student |
| 8 | Upload the presubmission (Sunday's PDF) before Monday ends | Student |

## Monday, road part (minimum that answers RQ1 and RQ4)

1. Pre-checks: sw7_check.py READY; phone hotspot on, Share GPS connected (Pi 5 /gps fix true); markers ready.
2. On stands, if the hoist is free (20 min): BMS key-off against the multimeter (3 readings); stand runs L M H H M L,
   60 s each, with the meter volts and clamp amps at 30 s and the setting in each marker; 10 mallet strikes and a tap slate.
3. Measure: wheelbase (3 readings), drive-wheel circumference (3 readings), IMU positions from the axles.
4. Closed area: still 60 s (S0); 50 m taped section with the side video; passes at 10, 15 and 20 km/h, 5 each,
   counterbalanced order, each pass marked start and end; 3 coasting passes; 5 speed-bump passes at 10 km/h; still 60 s.
5. Removal timed (R13).
6. Same evening: copy the data, run python -m BenchTest.analysis.run, fill the placeholders (12 in the body),
   rewrite the abstract and conclusions, recount words, rebuild, run tools/compare_report_versions.py.
7. Tuesday: read-through, deck and poster results slide, final PDF named
   "EEE4022S 2026 FINAL REPORT OKTSAM001 OKUTHE S - WINBERG.pdf", submit well before 23:59.
