# Virtual Tukzie: bench-test harness + placement visualiser

Status: vision / core piece in progress. Written 2026-09-18, revised same day
after clarifying the intended architecture.

## The idea, restated plainly

Right now the only way to test SW-7's sensing and signal-processing pipeline
against something resembling a real ride is to mount it on the actual Tukzie
and drive it. That is slow, needs the vehicle to be physically available and
assembled, and can't be repeated on demand.

The real sensors (IMU1, IMU2, and later the camera/BMS/GNSS) already talk to
the laptop over the COM port when the ESP32-S3 is on the bench. The proposal
is **not** to fake the sensor data - it's to keep the real sensors in the
loop, physically move/tap them by hand on the desk, and let PC-side software
read the genuine data coming back and interpret it: classify it against
known road-event signatures, visualise it, and flag whether the detection
logic behaves the way it should. This lets bench-testing substitute for a
chunk of vehicle-mounted testing (proving the sensing and classification
logic works on real physical motion), without needing the trike present or
assembled. It does not replace a real field test - a hand-tap on a desk and
an actual pothole at actual speed are not the same signal - but it validates
the pipeline end-to-end on genuine hardware in the meantime.

Separately, there's a wish to visualise where each subsystem physically
mounts on the chassis (shared with SW-6/Sharaav and JBM11/Melo, since all
three theses are building onto one vehicle that's still under development).

## My honest read on this

**Real-sensor bench-test harness - strong idea, cheap, build it now.** The
IMUs are already wired, already streaming validated `RIDE1`/`RIDE2` feature
lines over COM15 in exactly the format needed
(`[RIDE1] n=200 rms=... std=... p2p=... crest=... jerk=... crossings=...`).
A PC-side script can listen to that live, classify each window against
threshold-based event signatures, and give you a real-time readout - turning
"stare at scrolling numbers in a serial monitor" into a proper test tool.
This needs no firmware changes to get a first working version, since the
debug output already carries everything required.

**3D placement visualisation - useful, but scope the ambition down.** A
simple 3D scene (chassis outline + labelled markers for where IMU1, IMU2,
camera, HUD, BMS tap, and the other two theses' components sit) gets almost
all of the practical value - coordination between three students who can't
all be elbow-deep in the same vehicle at once. Buildable with an off-the-
shelf 3D web viewer (Three.js) and a rough mesh or even just a labelled
schematic.

Actual Gaussian splatting - a photorealistic neural reconstruction of the
real trike - is a materially bigger undertaking: multi-angle video capture
of a physically stable, well-lit vehicle, a training pipeline
(Nerfstudio/Polycam-style), non-trivial compute. It's also a computer-
graphics/ML technique, not an embedded-systems one - worth asking whether an
EEE HPEC telemetry thesis's markers will value it, or whether it reads as
scope creep. Given the list of still-open, higher-priority items (per-sensor
IMU calibration, the real vehicle field test, GNSS/BMS/MQTT/camera live
validation, motor Hall tap, camera mount fabrication), treat splatting as
optional late-stage polish, not a commitment.

**Bottom line:** build the real-sensor bench-test/classification tool now -
it's cheap, uses hardware already wired and working, and is genuinely useful
today. Build the simple marker-based 3D viewer next. Leave Gaussian
splatting as a stretch goal.

## Proposed architecture

### 1. PC-side live reader and classifier (build first)

A Python script that opens COM15, parses `[RIDE1]`/`[RIDE2]` lines as they
stream in real time, and classifies each window against threshold-based
signatures derived from the ride-characterisation features already computed
on-device (RMS, std, peak-to-peak, crest factor, mean jerk, threshold-
crossing count). Output: a live readout (console table, optionally a live
plot) showing, per IMU, the current feature values and a classified event
label ("quiescent" / "moderate vibration" / "sharp jerk event" / etc). This
is the "software version of the Tukzie" in the sense that means something
concrete: it's the piece of software that turns real, hand-generated bench
motion on the connected sensors into an interpretation of what that would
represent as a ride event, without the vehicle being present.

Initial thresholds are necessarily provisional (no real ride data exists yet
to calibrate them against). That's fine for now - the point of this tool at
this stage is validating that the classification logic behaves sensibly on
genuine physical motion (a hard tap reads as a sharp event, resting reads as
quiescent, a sustained shake reads as sustained vibration), not producing
final calibrated thresholds. Once real field-test data exists, feed it back
in to tighten the thresholds.

### 2. Firmware protocol hardening (later, optional)

The current `[RIDE1]`/`[RIDE2]` lines are debug prints interleaved with BMS
scan logs and sync-pulse messages, which is fine for a first version parsed
with a regex, but fragile long-term. If this tool proves useful, a dedicated
compact line (or binary frame) emitted only for structured telemetry, kept
separate from human-readable debug logging, would be more robust and is a
natural extension of the same idea already used for the sync pulse and BMS
sample globals.

### 3. Placement viewer (v1, scoped down)

A single-page Three.js scene: a rough chassis outline with labelled,
clickable markers for each mounted or planned component, colour-coded by
which thesis owns it. Goal is communication between the three of you, not
visual fidelity. Not built yet.

### 4. Stretch: real Gaussian splat overlay

Only after everything above is working and there's spare time: capture a
short multi-angle video of the physical Tukzie once it's stable and well-
lit, run it through an existing splatting tool, and use the resulting splat
as a photorealistic backdrop under the same marker coordinate system from
step 3. Not required for anything else here to function.

## Why this is defensible in the report, not just a fun side project

- Turns "I connected the IMUs and the numbers look plausible" into "I built
  a classification harness and validated it against known physical stimuli
  on real hardware" - a genuine methodology step, not a demo trick.
- Directly addresses the coordination problem already identified in the
  "Three Projects, One Trike" analysis.
- Cleanly separated from the real vehicle field test rather than replacing
  it - a marker can see this as evidence of rigorous bench-test practice
  ahead of the real drive, not a workaround for skipping it.

## Current status (updated 2026-09-18, later same day)

- `BenchTest/live_classifier.py` - working. Validated live against the real,
  wired IMUs: correctly reads quiescent baseline off COM15.
- A real walk-around video of the physical Tukzie (`TukzieVideo.mp4`, 44s,
  60fps, ~2641 frames, multiple real angles, static subject, even lighting)
  has been captured and uploaded to Polycam for Gaussian splat processing -
  no local GPU on this machine, so cloud processing is the right call rather
  than a from-scratch local COLMAP/3DGS pipeline.
- `VirtualTukzie/dashboard.html` - working first version. A local page (must
  be opened directly in Chrome/Edge, not hosted, since Web Serial needs a
  top-level browsing context) that connects to the real ESP32 over Web
  Serial, parses the genuine `[RIDE1]`/`[RIDE2]` lines live, and renders a
  sci-fi styled HUD with per-IMU classification, plus a vehicle viewer
  currently showing real extracted frames from the walk-around video. Has a
  clearly marked slot (`POLYCAM_EMBED_URL` constant) to drop in the real
  splat embed once Polycam finishes processing.
- Note: only one process can hold the COM port at a time - close
  `pio device monitor` / the Python classifier before opening the dashboard,
  or vice versa.

Still not built: the marker-based multi-subsystem placement viewer (showing
where SW-6/Sharaav and JBM11/Melo's components sit alongside SW-7's) -
lower priority than the outstanding real-hardware validation items
(per-sensor IMU calibration, real vehicle field test, GNSS/BMS/MQTT/camera
live validation).

## Evolution: from dashboard to walkthrough (2026-09-19)

The dashboard works but reads as a flat app - a splat in a box next to a
telemetry panel. The next step is to make it feel like actually walking
around the real vehicle, with live component data surfaced in the space
where that component actually is, not off to the side in a fixed panel.

### Execution prompt

> Evolve `VirtualTukzie/dashboard.html` from a two-panel app layout into an
> immersive walkthrough built around the real Gaussian splat already
> integrated - this is a presentation and interaction upgrade around
> already-working real data (Web Serial live telemetry, the real splat,
> the real captured-frame fallback), not a replacement of any of it.
>
> 1. Make the splat full-screen, the primary view rather than a small
>    panel, with the HUD styling (dark theme, scanline/corner accents)
>    surviving as an overlay rather than a separate boxed section.
> 2. Add a guided walkthrough camera mode: a scripted, smooth
>    transition between a small set of preset viewpoints (front, side,
>    rear/chassis), each with a brief on-screen label, alongside free
>    orbit/zoom for manual exploration. This does not need real component
>    coordinates to build - it is camera framing, not component placement.
> 3. Move the live telemetry off the fixed side panel and into floating,
>    HUD-style overlays anchored to screen corners/edges, so it reads as
>    part of the scene rather than a bolted-on dashboard.
> 4. For per-component hotspots tied to where IMU1/IMU2/the camera
>    actually sit on the real splat: do not fabricate 3D coordinates for
>    these, since there's no way to verify them against the real model
>    from outside the browser. Instead build a simple placement mode -
>    click on the model once per component to drop a marker, store the
>    resulting coordinates (e.g. in the page, exportable as a small JSON
>    block) - so the real positions get set once, by looking at the real
>    splat, rather than guessed.
> 5. Keep it a single local HTML file served the same way (local HTTP
>    server, Chrome/Edge, Web Serial) - no new dependencies beyond what's
>    already loaded (Three.js, GaussianSplats3D).

### Status

Being implemented now - see chat history / git history for what actually
landed versus what remains from this prompt.
