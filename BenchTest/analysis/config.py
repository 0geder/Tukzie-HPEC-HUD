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
    stop_word: str = "stop"

    # ---- signal processing ---------------------------------------------------------------------------------------
    gravity_lp_hz: float = 0.2        # gravity direction from a low-pass of each axis
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

    # ---- powertrain (RQ4) ----------------------------------------------------------------------------------------
    welch_seg_s: float = 4.0          # 0.25 Hz resolution
    peak_prominence_db: float = 10.0  # narrow-band peak: this far above the median-filtered background
    peak_background_hz: float = 5.0   # width of that median filter
    peak_halfwidth_hz: float = 1.0    # band around each peak used for the energy ratio

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
