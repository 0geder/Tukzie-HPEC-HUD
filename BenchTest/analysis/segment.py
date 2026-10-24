"""Segmentation: runs (passes) from markers, and driving / parked labelling of the 1 Hz records.

Marker convention for run 2 (typed into the recorder or appended to roadtest_markers.txt):
    "<name> start ..."   opens a run, "<name> stop ..." closes it; the start and stop words are parameters.
The run's name is the start marker's text with the start word removed, for example
    "S1 smooth pass3 20kmh start"  ->  name "S1 smooth pass3 20kmh".
A start without a stop closes at the next start (flagged "unclosed"); a stop without a start is ignored.
Section, class and speed setting are read from the name (classify_run).

Run-2 grammar (run sheet of 26 Oct): "R2 <block> <condition> <repeat> start|end", for example "R2 A v10 p1 start".
The block letter is the section (cfg.road_blocks gives its kind: smooth, rough, bump, obstacle), "coast" in the
condition makes a coasting pass, "v10" is the target speed (10 km/h), "p1" or "r1" the repeat; "R2 STANDS M r2" is a
stationary run at motor setting M. Any other block (S0, TAP, RECAL, DISPLAY, V5, R13, session, TEST) is an event.

Bins (section_bins): each pass over a section is cut into fixed-length bins along the road, so that the ICC rows are
places on the section and the passes are the repeated measurements.
"""
import csv
from dataclasses import dataclass
import re

import numpy as np


RECORDER_MARKERS = ("session start", "session end")   # written by road_logger.py itself, never a run boundary


@dataclass
class Run:
    name: str
    t0: float
    t1: float
    start_text: str
    stop_text: str = ""
    closed: bool = True
    section: str = ""
    kind: str = ""            # smooth, rough, bump, obstacle, coast, stationary, event or other
    setting: str = ""         # motor setting for stationary runs (low, med, high) or speed text for passes
    pass_no: int = None

    @property
    def duration(self):
        return self.t1 - self.t0


def _has_word(text, word):
    return re.search(r"(^|[^a-z0-9])" + re.escape(word.lower()) + r"($|[^a-z0-9])", text.lower()) is not None


def runs_from_markers(markers, start_word="start", stop_word=("stop", "end"), t_end=None):
    """Pair start and stop markers into Run objects. markers: time-sorted list of (t, text).

    stop_word: one word or several (any closes). Session markers ("R2 session start lab") never open a run.
    """
    stops = (stop_word,) if isinstance(stop_word, str) else tuple(stop_word)
    runs, open_run = [], None
    for t, text in markers:
        if text.strip().lower() in RECORDER_MARKERS or _has_word(text, "session"):
            continue
        if _has_word(text, start_word):
            if open_run is not None:
                open_run.t1, open_run.closed = t, False
                runs.append(open_run)
            name = re.sub(r"\s+", " ", re.sub(r"(?i)(^|\s)" + re.escape(start_word) + r"(\s|$)", " ", text)).strip()
            open_run = Run(name=name, t0=t, t1=float("nan"), start_text=text)
        elif any(_has_word(text, w) for w in stops) and open_run is not None:
            open_run.t1, open_run.stop_text = t, text
            runs.append(open_run)
            open_run = None
    if open_run is not None:
        open_run.t1 = t_end if t_end is not None else open_run.t0
        open_run.closed = False
        runs.append(open_run)
    return runs


def _classify_r2(run, cfg):
    """Run-2 grammar "R2 <block> <condition> <repeat>"; returns False if the name is not in it."""
    m = re.match(r"\s*R2\s+(\S+)\s*(.*)$", run.name, re.I)
    if not m:
        return False
    block, rest = m.group(1), m.group(2).lower()
    blocks = {k.upper(): v for k, v in cfg.road_blocks.items()}
    rp = re.search(r"(?:^|\s)(?:p|r|pass|run)\s*(\d+)(?:\s|$)", rest)
    run.pass_no = int(rp.group(1)) if rp else None
    if block.upper() == cfg.stands_block.upper():
        run.kind, run.section = "stationary", ""
        run.setting = rest.split()[0].upper() if rest.split() else ""
        return True
    if block.upper() not in blocks:
        run.kind, run.section, run.setting = "event", block.upper(), ""
        return True
    run.section = block.upper()
    run.kind = "coast" if any(w in rest for w in cfg.coast_words) else blocks[block.upper()]
    sp = re.search(r"(?:^|\s)v\s*(\d+(?:\.\d+)?)", rest) or re.search(r"(\d+(?:\.\d+)?)\s*km/?h", rest)
    run.setting = (sp.group(1) + "kmh") if sp else ("coast" if run.kind == "coast" else "")
    return True


def classify_run(run, cfg):
    """Fill section, kind, setting and pass number from the run name (case-insensitive substrings)."""
    if _classify_r2(run, cfg):
        return run
    low = run.name.lower()
    m = re.match(r"\s*(S\d+)\b", run.name, re.I)
    run.section = m.group(1).upper() if m else ""
    if any(w in low for w in cfg.stationary_words):
        run.kind = "stationary"
        run.setting = next((w for w in cfg.motor_words if w in low), "")
    elif any(w in low for w in cfg.obstacle_words):
        run.kind = "obstacle"
    elif any(w in low for w in cfg.smooth_words):
        run.kind = "smooth"
    else:
        run.kind = "other"
    if run.kind != "stationary":
        sp = re.search(r"(\d+(?:\.\d+)?)\s*km/?h", low)
        run.setting = sp.group(0).replace(" ", "") if sp else ""
    p = re.search(r"(?:pass|run|p)\s*(\d+)", low)
    run.pass_no = int(p.group(1)) if p else None
    return run


def label_driving(current_a, vib, current_thr=1.0, vib_thr=0.3):
    """Per-record driving flag: |current| > current_thr or vib > vib_thr (NaN compares false)."""
    with np.errstate(invalid="ignore"):
        return (np.abs(np.asarray(current_a, float)) > current_thr) | (np.asarray(vib, float) > vib_thr)


def driving_segments(t, driving, join_s=10.0):
    """Driving segments as a list of (t_start, t_end) of the flagged records, joining records at most join_s apart.

    t is the record time (s), sorted; each flagged record stands for itself, so a single record gives a segment of
    zero length (count one record period when summing durations). Records missing from the file are not filled: a
    gap longer than join_s ends a segment. "At most" reproduces the lab notebook of 21 Oct (26 segments after 18:15,
    965 s counted inclusively on the sequence-number clock); "strictly less than" gives 28 and 947 s.
    """
    t = np.asarray(t, float)
    idx = np.flatnonzero(np.asarray(driving, bool))
    segs = []
    for k in idx:
        if segs and t[k] - segs[-1][1] <= join_s:
            segs[-1][1] = t[k]
        else:
            segs.append([t[k], t[k]])
    return [tuple(s) for s in segs]


def in_segments(t, segs):
    t = np.asarray(t, float)
    m = np.zeros(t.shape, bool)
    for a, b in segs:
        m |= (t >= a) & (t <= b)
    return m


def read_crossings(path, tz_default=None):
    """Video crossing times of the section lines: CSV with header run,t_in,t_out (epoch s or ISO 8601).

    run is the run name as built from the markers (for example "R2 A v10 p1"). Returns {run: (t_in, t_out)}.
    """
    from .readers import parse_time
    out = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
            if row.get("run") and row.get("t_in") and row.get("t_out"):
                out[row["run"]] = (parse_time(row["t_in"], tz_default), parse_time(row["t_out"], tz_default))
    return out


def section_bins(t0, t1, length_m=None, bin_m=5.0, speed_fn=None, window_from_lines=False, n_time_bins=10):
    """Bin edges (times) along one pass over a section.

    window_from_lines: [t0, t1) is the crossing of the section's start and end lines (video), so the distance in the
    window is length_m; the speed profile (if any) only shapes where the bin edges fall (distance scaled to length_m),
    so the bins are the same places on every pass. Otherwise [t0, t1) is the marker interval: with a speed the edges
    are every bin_m metres of integrated distance (partial last bin dropped); without a speed, equal time fractions
    (length_m / bin_m of them, or n_time_bins), which assumes constant speed.
    Returns (edges, method text).
    """
    n_len = int(round(length_m / bin_m)) if length_m else n_time_bins
    v = None
    if speed_fn is not None:
        tg = np.linspace(t0, t1, max(int((t1 - t0) * 10), 2) + 1)
        v = np.array([speed_fn(x) for x in tg], float)
        if np.isfinite(v).mean() < 0.8:
            v = None
        else:
            v = np.interp(tg, tg[np.isfinite(v)], v[np.isfinite(v)])
    if v is None:
        return np.linspace(t0, t1, n_len + 1), f"{n_len} equal time fractions (no speed: constant speed assumed)"
    d = np.r_[0.0, np.cumsum(0.5 * (v[1:] + v[:-1]) * np.diff(tg))]
    if d[-1] <= 0:
        return np.linspace(t0, t1, n_len + 1), f"{n_len} equal time fractions (speed zero)"
    if window_from_lines and length_m:
        d = d * length_m / d[-1]
        targets = np.linspace(0, length_m, n_len + 1)
        how = f"{n_len} bins of {bin_m:g} m by distance (speed integrated, scaled to the {length_m:g} m section)"
    else:
        targets = np.arange(0, d[-1] + 1e-9, bin_m)
        how = f"{len(targets) - 1} bins of {bin_m:g} m by integrated speed from the start marker"
    return np.interp(targets, d, tg), how
