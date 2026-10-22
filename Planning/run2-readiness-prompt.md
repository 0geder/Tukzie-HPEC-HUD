# Prompt: everything ready for the second road run, with nothing left as a placeholder

Written 22 Oct 2026 from the student's brief: "I want it to be that we have met our stuff to the letter. No dummy things when we do our second run. Anything still outstanding is checked and analysed; if there is a better approach, propose it and we brainstorm; if not, it is tested or placed as future work. Get the project to master's level, aiming at PhD rigour. All sources of our data and tests readily available. Video evidence of the journey on YouTube, linked in the report. The SEN55 is not powering. I need to know road characterisation is achieved."

## Standards for every part

1. Nothing invented. Every number comes from a file in the repository or a measurement on the day. Anything not measured is called untested.
2. Every outstanding item ends in exactly one of three states, written down:
   - TEST ON RUN 2: a procedure with the setup, the number of repetitions, the pass criterion, the analysis script that will compute the result, and what the report will say for each outcome (pass or fail);
   - TEST ON THE BENCH BEFORE RUN 2: the same, on the bench;
   - FUTURE WORK: why it cannot be done in time, and the concrete next step, written as a recommendation.
   No fourth state ("TBD", "to be confirmed", dummy values).
3. Rigour at master's level and above: state the sample size, use repeated measurements, report uncertainty (confidence intervals, coefficient of variation or intraclass correlation for repeatability), separate verification (it works as built) from validation (it measures what it should), and keep ground truth independent of the system under test (tape, video, meter, known obstacle).
4. Better approaches are proposed only where they are clearly better and feasible before the deadline (presentations 16 to 17 Nov 2026), with cost and effort. Otherwise they go to future work.
5. Plain style, no em dashes, no unnecessary bold.

## Workstreams

A. Outstanding register. Every `\outstanding{}` marker, every "not measured", "untested", "partly met" and "outstanding" in the report, every requirement R1 to R13 and RQ1 to RQ4, and the run-2 needs (raw stream, GNSS, speed, markers, baseline, video, pothole definition, front and rear IMU nodes). For each: current evidence, the gap, the better approach if any, and the end state per rule 2 with its procedure. Output `Planning/run2-readiness/outstanding-register.md` and a run-2 test plan with a minute-by-minute run sheet.

B. Data availability. Every data source behind a number, figure or table in the report: path, date, test ID, what it supports (report section, figure, table), size, SHA-256, kept in git or only on OneDrive. A script that builds this index and packs a release archive (small files in git; large files, recordings and video in a dated archive), and a draft data-availability statement for the report pointing to it. Output `DATA_INDEX.md`, `tools/build_data_index.py`, `Planning/run2-readiness/data-availability.md`.

C. Road characterisation analysis, ready before the run. One pipeline that takes the run-2 recordings (recorder file, raw IMU stream from front and rear nodes, markers) and produces, with no hand steps: deduplication, run segmentation from markers, vehicle-axis vertical acceleration (gravity projection), band-pass filtering, ISO 2631-1 Wk weighted a_w and VDV, the per-second features, per-pass statistics, repeatability across passes (coefficient of variation, intraclass correlation with confidence interval), speed normalisation, front-to-rear delay by cross-correlation (and speed from wheelbase over delay), stationary powertrain spectra against road spectra (RQ4), and pothole events against the calibrated definition (Planning/pothole-definition.md). Tested now on the run-1 recordings where they apply and on synthetic signals with known answers. Output `BenchTest/analysis/`.

D. Firmware for run 2 (v0.7.5). Raw 200 Hz stream of each IMU on a non-blocking path to the Pi (drops counted, IMU timing unchanged), I2C read-failure and stuck-sample counters, a front-node build (one IMU, no modem, no BLE, no GNSS) for the second ESP32 at the front, and the position removed from the public-broker payload. Start from the unfinished `raw_stream.h` and host test in worktree agent-ae113d6428f53e516. Host tests and `pio run` for both environments must pass; bench timing verified before flashing; nothing flashed by the agent.

E. Video evidence (lead session). A YouTube upload kit (titles, descriptions, chapters, privacy settings, consent note) for the reel and the clips, and the report mechanism: a video-evidence table in Appendix I with links and QR codes, filled once the student uploads and sends the links. Unlisted, faces of others and number plates blurred or consent obtained.

F. SEN55 (lead session). Decide between repair and future work from the facts: what is broken, what powering it needs, what it would take, and what the report says either way.

## Done means

Every item in the register is in one of the three states; the analysis pipeline runs end to end on the run-1 data and on synthetic data; the firmware builds and passes its host tests; the data index lists every source; the report's video mechanism is in place; the run sheet for run 2 has no gaps.
