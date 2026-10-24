"""SW-7 road-characterisation analysis (run 2 and later).

Modules
  config      every default and threshold, overridable by a session.json
  readers     recorder JSONL and dedup by sequence number, markers, raw IMU stream (RAW v1 or CSV fallback),
              video labels, device-to-host clock map
  segment     runs from start/stop(end) markers incl. the R2 run-sheet grammar, driving/parked labelling, video
              crossings of the section lines, fixed-length bins along a section
  dsp         gravity projection, ride band-pass, ISO 2631-1 Wk weighting, a_w, VDV, per-second and per-bin
              features, clipping
  stats       CV with bootstrap CI, ICC(2,1) and ICC(3,1) with CI (bins as rows; refused when n is too small),
              Wilson and Poisson bounds for counts
  delay       front-to-rear delay by cross-correlation, speed = wheelbase / delay
  powertrain  Welch spectra, stand peaks, order-tracked or fixed lines, energies in the 0.5 to 80 Hz RQ4 band,
              coasting against powered
  pothole     drop-then-spike detector, working threshold, descriptive counts per pass and threshold sweep
  report      CSV and LaTeX tables, PDF and PNG figures, summary JSON
  run         the one command: python -m BenchTest.analysis.run --session <folder> --out <folder>
"""
