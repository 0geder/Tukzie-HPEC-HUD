"""SW-7 road-characterisation analysis (run 2 and later).

Modules
  config      every default and threshold, overridable by a session.json
  readers     recorder JSONL and dedup by sequence number, markers, raw IMU stream (RAW v1 or CSV fallback),
              video labels, device-to-host clock map
  segment     runs from start/stop markers, driving/parked labelling and joined driving segments
  dsp         gravity projection, band-pass, ISO 2631-1 Wk weighting, a_w, VDV, per-second features, clipping
  stats       coefficient of variation with bootstrap CI, ICC(2,1) and ICC(3,1) with CI, repeatability table
  delay       front-to-rear delay by cross-correlation, speed = wheelbase / delay
  powertrain  Welch spectra, narrow-band stationary peaks, band energy ratios (RQ4)
  pothole     drop-then-spike detector, calibration with ROC, evaluation against video labels
  report      CSV and LaTeX tables, PDF and PNG figures, summary JSON
  run         the one command: python -m BenchTest.analysis.run --session <folder> --out <folder>
"""
