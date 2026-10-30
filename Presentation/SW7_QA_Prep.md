# Question preparation: the 20 hardest questions

For the 5 minutes of examiner questions after the 10-minute talk (16 or 17 November 2026). Rewritten on 30 October 2026 from the submitted report (Embedded Telemetry with Road-Surface Characterisation and Camera-Based Hazard Detection for the TUKZIE Electric Trike) and BenchTest/logs/run2_road_2026-10-27/analysis/run2_summary_numbers.txt. The version of 20 October, written before the second road session, is in backup_2026-10-30/; many of its answers ("RQ4 waits for the road run", "no GNSS fix", "power not measured") are now wrong.

How to answer: the number, where it was measured, then its limit. One to three sentences, then stop. "Not measured, and this is how I would measure it" is a strong answer; a guessed number is not.

Section numbers are the report's (Table 5.3 is the summary of R1 to R13).

---

## Part 1: the 20 hardest

1. Your place-by-place ICC is 0.16 against a criterion of 0.75. Why did it fail, and what would fix it?
In 8 m cells a pass spends only 1 to 3 s, and over that time a_w varied about 30 % between passes but only about 18 % between cells, so pass-to-pass noise swamps the differences between places; with the phone's 1 Hz positions and laps that did not follow the same line, I cannot separate the two (5.3, 6.2). Cell sizes of 6 to 16 m and GNSS lags of up to 2 s gave at most 0.32. The fix is marked straight sections with side video, three passes per speed, so each pass covers the same strip and the windows come from section lines, not GNSS speed (Recommendation 4, 8.1).

2. RQ1 asks how accurately. With no reference accelerometer, how can you claim accuracy?
I don't claim road accuracy. In RQ1, accuracy means the instrument's: rate, sample loss, calibration and the feature computation, which are verified on the bench; for the ride itself there was no reference accelerometer or measured road profile, so only repeatability can be assessed (1.3, 7.4). Repeatability is 5.0 % and 5.3 % CV over whole passes, but not place by place.

3. Why is R2, calibration, not met on the vehicle?
A single magnitude factor holds only in the orientation it was measured in. Mounted on 23 October the front needed a factor 1.2 % different from its bench value, and on 27 October the parked vehicle read 9.845 (rear, a new board not recalibrated) and 9.941 m/s2 (front) against 9.81, outside 9.80 to 9.82 (5.2, Table 5.3). The fix is a six-position, per-axis calibration in the final mounting before every campaign and after any board change (Recommendation 9).

4. Why did the Raspberry Pi 4 keep browning out, and is it fixed?
The telemetry unit's LTE modem drew its transmit bursts through the Pi 4's USB port: a 2 s flag logger showed under-voltage 14 s after the modem came up, three restarts in 20 minutes, none in 4 hours once the unit was moved (E.3.7, 6.6). It is not fixed on the vehicle: on 27 October, with the unit again on that port, the Pi 4 flagged under-voltage and restarted once at 11:21; the fix is a regulated vehicle converter for the unit, never a Pi's USB port (5.9, Recommendation 1).

5. The brief asked for a windshield HUD. Why did it become dashboard integration?
The trike already has a Raspberry Pi 5 touchscreen dashboard, and a second display would compete for the same attention (1.2, 2.7); my supervisor agreed and the title changed to match. The dashboard's real problem was data validity: it showed simulated values with no sign when its link was down, which live-only mode removes (6.5). The optical HUD part of the brief is not met; it was replaced, by agreement.

6. Air quality was in the brief. Why is there no air-quality data?
The SEN55 arrived without its cable; to avoid waiting I soldered wires to its test pads, the supply pad lifted and the sensor never powered up again (J.9, Figure in Appendix I). A replacement with its JST cable needs no other hardware change on the Pi 4's I2C bus; the lesson is to wait for the connector (Recommendation 10).

7. Why only two passes at 15 km/h and one at 20?
The car park was too small to hold the higher speeds for long, and the light trike without its body became unstable in the corners; the phone recorded up to 28.3 km/h (5.3). So repeatability is shown only at 10 km/h, and I_v rose with speed (1.14, 1.59, 2.44 at about 10, 13 and 18 km/h), so it is not speed-invariant over this range.

8. How good is the detector on the road? Precision, false alerts?
Not measured. No forward video was kept on either session, so no road alert has been checked; the system stores no frames by design under the ethics approval, and a dataset with frames needs a revised application (5.6, 6.3, 8.2). The plan is to label a random sample of at least 200 road alerts against forward video with faces and plates blurred before storage, and report precision and false alerts per kilometre (Recommendation 6).

9. Your report body is 18,079 words. The guide is 10,000 to 15,000. Why?
It is above the guide, and I stated the count under the declaration rather than hide it. The second road session was driven on the submission day (27 October) and its results went into the body. [Student: give your own reason in one sentence; do not argue the guide.] (Guide from the GA template, as recorded in Planning/brief-compliance.md; count from the report's declaration page.)

10. Every part here is off the shelf. What is genuinely new?
No reviewed system combines fixed-rate inertial acquisition with measured timing and loss, on-board ride features, camera and range fusion, cellular telemetry with local logging and replay, and display on the vehicle's own dashboard on a light electric cargo trike (2.12, Table 2.1). The contribution is that integration and its measurement: the 33 to 44 ms flash-write gap, detection latency on each computer, replay after a 10-minute outage, 99.9 % of records on the road, and road evidence that the ride measure repeats over whole passes but not place by place (7.3).

11. What would you do with two more weeks?
Fit a regulated supply for the telemetry unit with inline current meters; fix the LTE reconnection lost from 11:51 and re-measure latency on the road; enlarge the banner to about 24 px capitals; then drive marked straight sections with side video, three passes per speed, after recalibrating both nodes mounted (8.1, Recommendations 1, 3, 4, 5, 9). That would give a place-by-place ICC and a road latency on more than nine records.

12. "Zero dropped samples", yet you report gaps. Isn't R1 misleading?
They are different measures, and the report gives both. The queue loses nothing, but each flash write pauses reading for 33 to 44 ms, and the catch-up reads are new readings, not the missed instants (5.1, 7.1). The inertial nodes, which keep no flash log, removed the pause: 200.00 Hz with no interval over 5.2 ms on the vehicle.

13. Is R10, the dashboard link, met on the vehicle?
Partly. The wired serial link delivered 4,196 of 4,201 per-second records on 27 October (99.9 %), against 62 % over USB on 19 October, but 5 records were missed against a criterion of no missing sequence numbers (5.7, Table 5.3). It is met on the bench: 0 bad lines in 2,489 and in 3,720 over 62 minutes.

14. How do you know the vibration you measure is the road and not the motor?
The stand runs found the powertrain lines at 42.75, 49.0 and 64.0 Hz; on the road they held only 0.9 to 3.1 % of the 0.5 to 80 Hz energy in powered passes (0.4 % coasting), while 65 to 84 % lay at 4 to 8 Hz, and a coasting pass read a_w 1.80 against 1.78 powered (5.3). That holds at these low speeds; at higher power the 40 to 70 Hz energy would weigh more (6.2).

15. Why did you use a phone for speed instead of your own GNSS?
On the smooth loop the vehicle receiver's pass-mean speed, read as knots, was 0.9 to 1.4 times the phone's and its position 8 to 25 m away; it updated about every 4 s, near the 3 s poll, and from 12:13 held a stale position and zero speed while still flagged as fixed (5.4). The phone gave 14,181 fixes until 12:29, so R4 stays partly met.

16. Your road latency rests on nine records, and the link died at 11:51. What happened?
Over LTE 153 records reached the database, 37 live and 116 replayed from the backlog, and the nine live records with GNSS time arrived a median of 0.44 s after stamping (95th percentile 0.55 s) (5.7). From 11:51 the cellular link did not reconnect; the cause was not established, and the remaining records stayed in the unit's log. Fixing the reconnection is Recommendation 3.

17. Is your dashboard safe to glance at while driving?
I don't know: glance time (R12) needs a participant and an ethics amendment, so it was not tested (5.8). The legibility check that needs no participant found the hierarchy inverted: at 0.62 m the speed digits subtend 94 arc minutes against ISO 15008's recommended 20, but the alert banner only 10, below the minimum of 12, and 4 of 110 labels reach the acceptable 16 (5.8, 6.5).

18. Is the 0.26 s alert onset what the driver experiences?
No. It is computed at the detector from the three-frame onset and the Pi 4's latency with the whole system (about 2.2 m at 30 km/h); the delay from an object's appearance to the screen was not measured (5.6, 7.1, test C8). The 0.5 s on the camera page was the time after opening the page with a person already in view, not alert latency.

19. Five passes is a small sample. How confident is the 5 % CV?
The rear's 95 % interval is 1.9 to 6.2 % and the front's 1.4 to 7.2 %, both inside the 10 % criterion (run2_summary_numbers.txt). The bigger limit is that the pass windows come from GNSS speed, so they include each lap's turns and run-up, and there is one loop at one speed on one day (5.3, 6.2).

20. How far is this from use on a real vehicle in service?
A prototype run on the vehicle, short of the demonstration in a relevant environment (TRL 6) that was the target (7.3). The evidence is one vehicle, one hardware set, two short low-speed sessions, an advisory-only detector at automation level 0, and no measured effect on the driver (1.5, 7.4).

---

## Part 2: other likely questions, short answers

Why 200 Hz? ISO 2631-1 weights to 80 Hz, so the Nyquist rate is 160 Hz; 200 Hz gives margin. Both nodes held 200.005 and 200.006 Hz on the road (1.4, 5.1).

What does HPEC mean on an ESP32? Predictable completion of time-critical work in a small power budget: a fixed 5 ms period with measured jitter and loss, features on board; the vision runs on the Pis (1.1, 4.3).

What does the whole system draw? 27 W at the portable power station's display with everything running, between the 17 W typical and 31 W peak estimates; the display's accuracy is unknown and it does not split by load (K.9). About 0.28 % of a 7.2 kWh pack an hour, but enough to empty it in about 15 days if left on, so it must switch off with the vehicle (5.9).

Battery (R5)? Held under load on the vehicle: up to 82.9 A on the 20 km/h pass, 74.0 to 71.2 V on 27 October; never checked against a meter, so partly met (5.5).

Fusion and range (R8)? At about 0.5 m the fused distance was 0.47 m (median of 43 records), but only 6 of 43 records were fused and a person is a poor target; the flat-target check C9 is still needed (5.6).

Time to contact? Box width over its rate of growth, so no focal length or object size is needed; warning under 4 s, immediate under 2 s; accuracy on a real approach is untested (C11) (4.6.5, 6.3).

Front-to-rear delay as a speed estimate? Not estimated: the correlation peaked at 0.37 to 0.53 at 0.09 to 0.10 s in every pass, the same at all speeds, so it reflects the body's common motion or a clock offset, not the wheelbase (5.3).

Store-and-forward on the public broker? The broker acknowledges with no subscriber present and does not queue, so completeness rests on comparing the database with the unit's log; an authenticated, encrypted broker that queues for a persistent subscriber is Recommendation 3 (5.7, 6.4).

Privacy and ethics? Approved with conditions on 6 October 2026 (EBE/03305/2026), no human subjects; frames exist only in memory, each alert keeps a few fields, no identification (3.7). Road videos shown are held off the repository with faces and the number plate blurred (A.1).

R13, removable installation? Mounted with no drilling or permanent change, but removal was not timed, so partly met (5.9, Table 5.3).

Pothole detector? Not scored: no bump or pothole passes were marked. Training on South African footage raised the validation score to 0.714 mAP@50, not claimed without a held-out or on-vehicle score (6.2, 6.3).

How did you use AI? Claude Code as a coding and writing assistant, at my direction; I made the decisions, ran the tests and am responsible for every claim; prompt examples are in A.3.

Requirements tally? 5 met on the bench (R1 to R3, R9, R10), 7 partly (R4 to R8, R11, R13), R12 not tested; on the road R1 met at the front, R10 for 99.9 %, R4 and R9 in part, R2 not (7.2).
