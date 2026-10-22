# Pothole definition and IMU calibration (proposal, 22 Oct 2026, awaiting the student's decisions)

Principle (Literature review): a trike needs its own baseline, not a threshold carried over from a car, so the detector is calibrated on the TUKZIE against a physical definition.

## Physical definition (ground truth)

A pothole is a local depression in the road surface at least 25 mm deep and at least 150 mm across, crossed by a wheel. Project choice, not a standard. Shallower damage is rough surface (Sharaav's code 3); raised obstacles (speed bumps, kerbs, planks) are a separate class. To agree with Sharaav's definition for his code 4.

## Signature in the IMU

Vertical acceleration (projected onto gravity, frame axes) band-passed about 2 to 40 Hz: a drop as the wheel falls in, a sharp positive spike at the far edge, then ringing; duration about (hole length + contact patch) / speed, 0.05 to 0.3 s. A speed bump rises first and lasts longer. The trike has one front wheel and two rear wheels, so front and rear events need not pair; each node detects on its own; pairs give speed from wheelbase / delay.

Features in a 0.3 s sliding window: drop-then-spike order, peak-to-peak, duration, speed at the time.

## Calibration

0. IMU six-position per-axis calibration and mounted orientation.
1. Stationary powertrain baseline at low, medium, high motor speed: noise floor.
2. Smooth road, 2 to 3 speeds, 5 passes each: false-alarm distribution.
3. Known obstacle (25 mm plank drop) and one measured real pothole, 5 passes per speed: event amplitude against speed.
4. Speed-dependent threshold between 2 and 3; report detection rate and false alarms per km (ROC).
5. Route with phone video, every pothole labelled: field detection and false-alarm rates.
Severity classes only after 4, from measured depths. Check clipping at plus or minus 8 g in step 3.

## Decisions needed

1. 25 mm deep and 150 mm across, or an existing team definition.
2. Plank drop as the controlled obstacle, or real potholes only.
3. False-alarm target, for example at most 1 per km on smooth road.
