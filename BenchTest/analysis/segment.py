"""Segmentation: runs (passes) from markers, and driving / parked labelling of the 1 Hz records.

Marker convention for run 2 (typed into the recorder or appended to roadtest_markers.txt):
    "<name> start ..."   opens a run, "<name> stop ..." closes it; the start and stop words are parameters.
The run's name is the start marker's text with the start word removed, for example
    "S1 smooth pass3 20kmh start"  ->  name "S1 smooth pass3 20kmh".
A start without a stop closes at the next start (flagged "unclosed"); a stop without a start is ignored.
Section, class and speed setting are read from the name (classify_run).
"""
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
    kind: str = ""            # smooth, obstacle, stationary or other
    setting: str = ""         # motor setting for stationary runs (low, med, high) or speed text for passes
    pass_no: int = None

    @property
    def duration(self):
        return self.t1 - self.t0


def _has_word(text, word):
    return re.search(r"(^|[^a-z0-9])" + re.escape(word.lower()) + r"($|[^a-z0-9])", text.lower()) is not None


def runs_from_markers(markers, start_word="start", stop_word="stop", t_end=None):
    """Pair start and stop markers into Run objects. markers: time-sorted list of (t, text)."""
    runs, open_run = [], None
    for t, text in markers:
        if text.strip().lower() in RECORDER_MARKERS:
            continue
        if _has_word(text, start_word):
            if open_run is not None:
                open_run.t1, open_run.closed = t, False
                runs.append(open_run)
            name = re.sub(r"\s+", " ", re.sub(r"(?i)(^|\s)" + re.escape(start_word) + r"(\s|$)", " ", text)).strip()
            open_run = Run(name=name, t0=t, t1=float("nan"), start_text=text)
        elif _has_word(text, stop_word) and open_run is not None:
            open_run.t1, open_run.stop_text = t, text
            runs.append(open_run)
            open_run = None
    if open_run is not None:
        open_run.t1 = t_end if t_end is not None else open_run.t0
        open_run.closed = False
        runs.append(open_run)
    return runs


def classify_run(run, cfg):
    """Fill section, kind, setting and pass number from the run name (case-insensitive substrings)."""
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
