"""Every default the road-characterisation pipeline uses, in one place.

A session folder may hold a `session.json` whose keys override these (same names, lower case); `run.py --config`
does the same from another path. Values marked UNVERIFIED are assumptions that must be checked on the vehicle or
against a datasheet before a result that depends on them is reported.
"""
from dataclasses import dataclass, field, asdict, fields
import json
import os

G0 = 9.80665                      # standard gravity, m/s^2


@dataclass
class Config:
    # ---- acquisition -------------------------------------------------------------------------------------------
    fs: float = 200.0                 # IMU sample rate, Hz (firmware ImuTask period 5 ms)
    accel_range_g: float = 8.0        # MPU-6050 configured range (raw_stream.h: +-8 g, 4096 counts/g)
    clip_fraction: float = 0.98       # a sample counts as clipped at or beyond this fraction of the range
    max_gap_s: float = 0.05           # gaps longer than this split a stream into separate chunks (no interpolation)

    # ---- driving / parked labelling (report, Method: "Road session") ---------------------------------------------
    drive_current_a: float = 1.0      # |i| above this, A
    drive_vib: float = 0.3            # or vib above this, m/s^2
    drive_join_s: float = 10.0        # driving segments less than this apart are joined
    readable_fields: tuple = ("vib", "i", "v", "imu_hz", "drops")

    # ---- run segmentation from markers ---------------------------------------------------------------------------
    start_word: str = "start"
    stop_word: tuple = ("stop", "end")   # any of these closes a run (run sheet of 26 Oct writes "end")
    # Run-2 grammar "R2 <block> <condition> <repeat> <start|end>": the block letter is the road section and sets the
    # kind of pass; blocks not listed here (S0, TAP, RECAL, DISPLAY, V5, R13, session, TEST ...) are events, not
    # passes. "STANDS" is the stationary powertrain block (condition = motor setting L, M, H or idle).
    road_blocks: dict = field(default_factory=lambda: {"A": "smooth", "R": "rough", "B": "bump", "P": "obstacle"})
    stands_block: str = "STANDS"
    coast_words: tuple = ("coast",)

    # ---- signal processing ---------------------------------------------------------------------------------------
    gravity_lp_hz: float = 0.2        # gravity direction from a low-pass of each axis
    # Ride band: sigma, crest, peak-to-peak, the pothole detector and the front-to-rear delay use the vertical
    # acceleration band-passed here (dsp.Chunk.bp). a_w and VDV use Wk on the unfiltered vertical (0.4 to 100 Hz
    # analogue weighting, evaluated up to fs/2). RQ4 uses its own, wider band (pt_band_*), because the powertrain
    # lines seen on the stands on 23 Oct lie at 40 to 70 Hz, above this band's upper edge.
    band_lo_hz: float = 2.0
    band_hi_hz: float = 40.0
    band_order: int = 4               # Butterworth order of each edge (zero phase: applied forward and back)
    jerk_lp_hz: float = 20.0
    window_s: float = 1.0             # per-second features

    # ---- speed ---------------------------------------------------------------------------------------------------
    # GNSS spd_raw is assumed to be knots (receiver manual); UNVERIFIED against a known speed (report, R4).
    spd_raw_to_mps: float = 0.514444
    v_min_mps: float = 1.0            # speed gate for sigma^2 / v
    wheelbase_m: float = None         # front axle to rear axle; must be measured with a tape (no default on purpose)
    delay_min_s: float = 0.03         # front to rear delay search range
    delay_max_s: float = 1.5
    delay_window_s: float = 5.0       # windows for the delay confidence interval

    # ---- repeatability -------------------------------------------------------------------------------------------
    n_boot: int = 2000
    seed: int = 1
    # ICC rows are fixed-length bins along a section (the passes are the repeated measurements), not whole sections:
    # one 50 m section has no between-section variance to measure. Bins come from the video crossing times of the
    # section lines (crossings_csv) when present, else from the pass markers; by distance (speed integrated) when a
    # speed is known, else equal time fractions (constant-speed assumption, stated in the output).
    icc_bin_m: float = 5.0
    section_length_m: float = 50.0    # default measured length between the section lines (tape)
    section_lengths_m: dict = field(default_factory=dict)   # per section, {"A": 50.0, "R": 40.0}
    icc_min_rows: int = 5             # fewer rows (bins or sections) than this: no ICC, CV only, and the output says so
    icc_min_passes: int = 3
    icc_metrics: tuple = ("a_w", "sigma")

    # ---- powertrain (RQ4) ----------------------------------------------------------------------------------------
    welch_seg_s: float = 4.0          # 0.25 Hz resolution
    peak_prominence_db: float = 10.0  # narrow-band peak: this far above the median-filtered background
    peak_background_hz: float = 5.0   # width of that median filter
    peak_halfwidth_hz: float = 1.0    # half-width of the band around each line used for the line energy
    # RQ4 band: below Nyquist (100 Hz) and below the MPU-6050 DLPF corner (94 Hz, attenuating above about 80 Hz);
    # it holds the 40 to 70 Hz stand lines. Line energy is reported as a share of the energy in this band.
    pt_band_lo_hz: float = 0.5
    pt_band_hi_hz: float = 80.0
    pt_sub_bands: tuple = ((0.5, 4.0), (4.0, 8.0), (8.0, 16.0), (16.0, 40.0), (40.0, 80.0))   # register B3
    # Lines from the stand runs of 23 Oct (rear and front, BenchTest/logs/run2_lab_2026-10-23/stand_spectra_1023.json),
    # used as fixed lines when this session has no stand run, or when no speed is available to track orders.
    pt_stand_lines_hz: tuple = (42.75, 49.0, 64.0)
    # Order tracking: a line at order o of the wheel rotation lies at o * v / C. Orders come from pt_orders, else
    # from the session's stand peaks divided by the wheel rate on the stands (stand_wheel_hz, from the 240 frames/s
    # video of the wheel mark). Needs the measured drive-wheel circumference; without it, or without a speed, the
    # fixed lines are used with +-peak_halfwidth_hz.
    wheel_circumference_m: float = None
    stand_wheel_hz: dict = field(default_factory=dict)       # {"L": 3.1, "M": 4.4, "H": 5.6}, wheel rev/s
    pt_orders: tuple = ()
    coast_match_mps: float = 1.0 / 3.6   # coasting and powered passes compared within this mean-speed difference

    # ---- pothole detector (Planning/pothole-definition.md) -------------------------------------------------------
    ph_window_s: float = 0.3          # drop then spike within this window
    ph_min_dur_s: float = 0.02        # drop-to-spike time limits
    ph_max_dur_s: float = 0.3
    ph_drop_fraction: float = 0.25    # the drop must be at least this fraction of the peak-to-peak
    ph_refractory_s: float = 0.5      # one event per this interval (the largest)
    ph_fa_per_km: float = 1.0         # false-alarm target on smooth road (decision 3 in the definition, proposed)
    ph_label_tol_s: float = 0.5       # detection matches a video label within this time
    ph_threshold_a: float = None      # calibrated: threshold(v) = a + b v  (m/s^2, m/s^2 per m/s)
    ph_threshold_b: float = 0.0

    # ---- pass classification from marker text (case-insensitive substrings) ---------------------------------------
    smooth_words: tuple = ("smooth",)
    obstacle_words: tuple = ("plank", "obstacle", "pothole")
    stationary_words: tuple = ("stationary", "static", "parked")
    motor_words: tuple = ("low", "med", "high")

    # ---- files ---------------------------------------------------------------------------------------------------
    raw_files: dict = field(default_factory=dict)   # {"front": "front_raw.txt", "rear": "rear_raw.txt"}
    sync_edges: dict = field(default_factory=dict)  # {"rear": [Pi GPIO epoch s of each RAWS edge, in order]}
    labels_csv: str = None            # video labels: time, type
    crossings_csv: str = None         # video crossing times of the section lines: run, t_in, t_out (epoch s or ISO)

    def update(self, d):
        names = {f.name for f in fields(self)}
        for k, v in d.items():
            k = k.lower()
            if k not in names:
                raise KeyError(f"unknown config key {k!r}")
            if isinstance(getattr(self, k), tuple) and isinstance(v, list):
                v = tuple(v)
            setattr(self, k, v)
        return self

    def to_dict(self):
        return asdict(self)


def load_config(session_dir=None, path=None, overrides=None):
    cfg = Config()
    for p in ([os.path.join(session_dir, "session.json")] if session_dir else []) + ([path] if path else []):
        if p and os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                cfg.update(json.load(f))
    if overrides:
        cfg.update({k: v for k, v in overrides.items() if v is not None})
    return cfg
