#!/usr/bin/env python3
r"""Build DATA_INDEX.md: every data source behind the SW-7 report, with checksums.

Usage (from anywhere):
    python tools/build_data_index.py            # write DATA_INDEX.md at the repo root
    python tools/build_data_index.py --pack     # also write a dated release zip
                                                # into ../SW7_data_release/

What it does
  1. Inventories the data locations: BenchTest/logs/**, Report/evidence/**,
     Report/figures/results/**, Report/figures/road1/**, the two bench figures,
     CameraDetection logs, training runs and test data, TelemetryUnit/test_host,
     Planning/lab-notebook.md, Server databases (if present) and the road-test
     media folder ../Roadtest1 (outside the repository).
  2. Extracts every file reference from Report/*.tex (\texttt{...} and
     \includegraphics{...}, plus plain mentions of file names), resolves it
     to files on disk and records where it is cited (figure, table or section
     label; for the evidence table, the row).
  3. Assigns a test ID (T1..T15, C1..C11, B1..B5) from the Evidence lines of
     BenchTest/TEST_PROCEDURES.md, with a short hand map (SUPPLEMENT) for files
     the procedures do not name.
  4. Records size, SHA-256, date (from the name, else the file time) and
     whether git tracks the file.
  5. Flags references that resolve to nothing, and data on disk that no part
     of the report cites.

--pack writes ../SW7_data_release/SW7_data_release_<date>.zip containing every
file the report depends on that git does not track, plus DATA_INDEX.md,
SHA256SUMS.txt and WITHHELD.txt. Video, the road-test media folder and photos
that show people are never packed (privacy); they are listed in WITHHELD.txt
as held by the author and available on request.

Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import os
import re
import subprocess
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "Report"
EXTERNAL = {"Roadtest1": ROOT.parent / "Roadtest1"}  # name -> folder outside the repo

# Folders inventoried in full (relative to ROOT).
SCAN_DIRS = [
    "BenchTest/logs",
    "Report/evidence",
    "Report/figures/results",
    "Report/figures/road1",
    "CameraDetection/training/runs",
    "CameraDetection/tests/data",
    "TelemetryUnit/test_host",
]
# Single files or globs inventoried (relative to ROOT).
SCAN_GLOBS = [
    "Report/figures/recorded_session.png",
    "Report/figures/live_dashboard.png",
    "CameraDetection/*.jsonl",
    "CameraDetection/*.csv",
    "CameraDetection/fusion_config*.json",
    "Planning/lab-notebook.md",
    "Server/*.db",
    "Server/*.db-wal",
    "Server/reports/**/*",
]
SKIP_PARTS = {"__pycache__", ".git"}
SKIP_SUFFIXES = {".pyc"}

# Folder references too broad to count as citing every file inside them.
GENERIC_FOLDERS = {
    "BenchTest", "BenchTest/logs", "Report", "Report/evidence", "Planning",
    "CameraDetection", "CameraDetection/tests", "CameraDetection/deploy",
    "DashboardIntegration", "DashboardIntegration/tests", "DashboardIntegration/deploy",
    "TelemetryUnit", "Server", "Report/archive_full_2026-10-11",
}
# Tex files whose references are evidence in their own right: every file they
# resolve to gets a row, even code.
EVIDENCE_TEX = {"appendixc.tex", "Results.tex", "appendixi.tex"}
DATA_EXT = {".log", ".csv", ".jsonl", ".json", ".db", ".txt", ".mp4", ".jpg", ".jpeg", ".png", ".pdf"}

# Test IDs for files the Evidence lines of TEST_PROCEDURES.md do not name.
# (glob relative to ROOT, test ID, reason)
SUPPLEMENT = [
    ("Report/evidence/2026-09-25_bench_console_replay.png", "B1", "bench console replay of the T1 log"),
    ("Report/figures/recorded_session.png", "T1", "Figure fig:recorded-session, the 150 s bench session"),
    ("Report/figures/live_dashboard.png", "T1", "bench dashboard on the T1 setup"),
    ("BenchTest/logs/2026-10-15_pi5_detector*", "C4", "detector latency on the Pi 5, plotted with the C4 runs"),
    ("BenchTest/logs/calibration/*", "C5", "distance calibration stills (focal_cal.py)"),
    ("BenchTest/logs/calibration/rejected/*", "C5", "rejected calibration still"),
    ("BenchTest/logs/focal_cal.csv", "C5", "focal length calibration"),
    ("BenchTest/logs/2026-10-10_tof_hand_test.txt", "C7", "ToF hand test, cited in Methodology"),
    ("BenchTest/logs/2026-10-11_t15_device_log.clean.jsonl", "T15", "clean copy of the T15 device log"),
    ("BenchTest/logs/2026-10-06_pi4_power_watch.log", "Power", "Pi 4 power watcher"),
    ("BenchTest/logs/2026-10-10_bench_observations.md", "Power", "Pi 4 reboots and timing, whole system"),
    ("BenchTest/logs/roadtest_2026-10-19/*", "Road run 1", "first road session, 19 Oct"),
    ("Report/figures/road1/*", "Road run 1", "stills from the road-test media"),
    ("../Roadtest1/*", "Road run 1", "road-test media originals"),
    ("../Roadtest1/edit/*", "Road run 1", "road-test reel"),
    ("Report/figures/results/road_session_1019.*", "Road run 1", "Figure fig:res-road"),
    ("Report/figures/results/imu_write_gaps.*", "T2, T9", "Figure fig:res-imu-gaps"),
    ("Report/figures/results/detector_latency.*", "C4", "Figure fig:res-latency"),
    ("Report/figures/results/t15_outage_backlog.*", "T15", "Figure fig:res-t15"),
    ("TelemetryUnit/test_host/*", "T15", "host test of the store-and-forward ledger"),
    ("CameraDetection/training/runs/*", "Pothole model", "YOLO11n pothole training runs"),
    ("CameraDetection/training/runs/*/*", "Pothole model", "YOLO11n pothole training runs"),
    ("CameraDetection/training/runs/*/*/*", "Pothole model", "YOLO11n pothole training runs"),
    ("CameraDetection/ncnn_bench.py", "C8a", "NCNN trial"),
    ("CameraDetection/tof_probe.py", "C7", "stand-in ToF probe"),
    ("CameraDetection/tof_reader.py", "C7", "stand-in ToF reader"),
    ("BenchTest/log_dump.py", "T10", "stored log read-back tool"),
    ("CameraDetection/tests/test_sensor_fusion.py", "C9", "fusion offline tests"),
    ("DashboardIntegration/tests/test_front_camera_page_live.py", "B2", ""),
    ("DashboardIntegration/tests/test_live_data_provider.py", "B3", ""),
    ("DashboardIntegration/tests/tile_map_*", "B4", ""),
    ("DashboardIntegration/PI5_MAP_CRASH.md", "B5", ""),
    ("Planning/lab-notebook.md", "Lab notebook", "daily lab record"),
]

GROUP_ORDER = (
    [f"T{i}" for i in range(1, 16)] + ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C8a", "C9", "C10", "C11"]
    + [f"B{i}" for i in range(1, 6)] + ["Power", "Pothole model", "Road run 1", "Lab notebook"]
)

# Privacy: never packed, listed as held by the author.
PRIVATE_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".heic"}


def is_private(rel: str) -> bool:
    p = rel.lower()
    if p.startswith("../roadtest1/"):
        return True
    if Path(p).suffix in PRIVATE_SUFFIXES:
        return True
    if Path(p).suffix in {".jpg", ".jpeg", ".png"} and "person" in Path(p).name:
        return True
    return False


# ---------------------------------------------------------------- helpers

def run_git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                              encoding="utf-8", check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return ""


def git_state() -> tuple[set[str], set[str], set[str]]:
    """(tracked, modified, all files on disk known to git incl. untracked)."""
    tracked = {l.strip() for l in run_git("-c", "core.quotepath=off", "ls-files").splitlines() if l.strip()}
    others = {l.strip() for l in run_git("-c", "core.quotepath=off", "ls-files", "-o", "--exclude-standard").splitlines() if l.strip()}
    modified = {l.strip() for l in run_git("-c", "core.quotepath=off", "ls-files", "-m").splitlines() if l.strip()}
    return tracked, modified, tracked | others


def rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return "../" + p.resolve().relative_to(ROOT.parent).as_posix()


def abs_path(r: str) -> Path:
    return (ROOT / r).resolve()


def walk(base: Path):
    if not base.exists():
        return
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_PARTS and not d.startswith(".")]
        for f in filenames:
            if Path(f).suffix in SKIP_SUFFIXES or f.startswith("~$"):
                continue
            yield Path(dirpath) / f


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


DATE_RE = [
    (re.compile(r"(20\d\d)-(\d\d)-(\d\d)"), "{0}-{1}-{2}"),
    (re.compile(r"(?<!\d)(20\d\d)(\d\d)(\d\d)(?!\d)"), "{0}-{1}-{2}"),
]


def file_date(r: str, p: Path) -> tuple[str, str]:
    for rx, fmt in DATE_RE:
        m = rx.search(r)
        if m:
            return fmt.format(*m.groups()), "name"
    return dt.date.fromtimestamp(p.stat().st_mtime).isoformat(), "mtime"


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


# ---------------------------------------------------------------- tex parsing

def norm_tex(s: str) -> str:
    s = re.sub(r"\\allowbreak\s*", "", s)
    s = s.replace("\\_", "_").replace("\\textasciitilde", "~").replace("\\,", " ")
    s = s.replace("{}", "").replace("\\-", "")
    s = re.sub(r"_\s+", "_", s)  # "bench\_ observations" is a line-break hint, not a space
    s = re.sub(r"/\s+", "/", s)
    s = re.sub(r"[ \t]+", " ", s)
    return s


def braced(text: str, start: int) -> tuple[str, int]:
    """Return the content of the {...} group opening at text[start]."""
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
    return text[start + 1:], len(text)


SECTION_LABEL = re.compile(r"\\(?:chapter|section|subsection|subsubsection)\*?\{[^\n]*?\}\s*\\label\{([^}]+)\}|\\label\{((?:chap|sec|app|subsec):[^}]+)\}")
ENV_BEGIN = re.compile(r"\\begin\{(figure|table|longtable)\*?\}")


def context(text: str, pos: int, texname: str) -> str:
    """Label of the float holding pos, else the enclosing section label."""
    last = None
    for m in ENV_BEGIN.finditer(text, 0, pos):
        last = m
    if last:
        env = last.group(1)
        end = text.find(f"\\end{{{env}}}", last.end())
        if end != -1 and end > pos:
            body = text[last.end():end]
            lab = re.search(r"\\label\{([^}]+)\}", body)
            label = lab.group(1) if lab else f"unlabelled {env}"
            if env == "longtable":
                row_start = text.rfind("\\hline", last.end(), pos)
                row = norm_tex(text[row_start + 6:pos]) if row_start != -1 else ""
                row = row.split("\\endhead")[-1].replace("\n", " ").strip()
                cells = [c.strip() for c in row.split("&")]
                if len(cells) >= 2:
                    test = re.sub(r"\\[a-zA-Z]+|[{}~]", " ", cells[1])
                    test = re.sub(r"\s+", " ", test).strip()
                    label += f" (row: {cells[0]}, {test[:60]})"
            return label
    sec = None
    for m in SECTION_LABEL.finditer(text, 0, pos):
        sec = m.group(1) or m.group(2)
    return sec or texname


def tex_files() -> list[Path]:
    return sorted(p for p in REPORT.glob("*.tex"))


# ---------------------------------------------------------------- resolution

class Resolver:
    def __init__(self, disk: set[str]):
        self.disk = set(disk)
        for name, folder in EXTERNAL.items():
            for p in walk(folder):
                self.disk.add(rel(p))
        self.by_name: dict[str, list[str]] = defaultdict(list)
        for r in self.disk:
            self.by_name[Path(r).name].append(r)

    def under(self, folder: str) -> list[str]:
        folder = folder.rstrip("/") + "/"
        return sorted(r for r in self.disk if r.startswith(folder) and abs_path(r).exists())

    def exists(self, r: str) -> bool:
        return abs_path(r).is_file()

    def resolve(self, token: str, prev: str | None, base: str = "") -> tuple[list[str], bool, str]:
        """Return (files, is_folder, normalised token). Empty list = unresolved."""
        t = token.strip().strip("`'\"()").rstrip(".,;:")
        t = t.replace("\\", "/") if "\\" in t and "/" not in t else t
        if not t:
            return [], False, t
        if t in EXTERNAL:
            return self.under(rel(EXTERNAL[t])), True, rel(EXTERNAL[t]) + "/"
        # "..._run2.csv", "..clean.jsonl", ".clean.jsonl": suffix of the previous file
        if t.startswith(".") and prev and not t.startswith("../"):
            suffix = t.lstrip(".")
            d = str(Path(prev).parent.as_posix())
            cands = [r for r in self.disk if Path(r).parent.as_posix() == d and Path(r).name.endswith(suffix)
                     and r != prev]
            if cands:
                pn = Path(prev).name
                best = max(cands, key=lambda c: len(os.path.commonprefix([pn, Path(c).name])))
                return [best], False, best
            return [], False, t
        is_folder = t.endswith("/")
        if "*" in t:
            if t.endswith("/"):
                t = t + "*"
            pats = [t] if "/" in t else ([f"{Path(prev).parent.as_posix()}/{t}"] if prev else []) + [f"*/{t}"]
            for pat in pats:
                hits = sorted(r for r in self.disk if fnmatch.fnmatch(r, pat))
                if hits:
                    return hits, False, pat
            return [], False, t
        if is_folder:
            cands = [t]
            if base:
                cands.append(f"{base}/{t}")
            if prev:
                cands.append(f"{Path(prev).parent.as_posix()}/{t}")
            for c in cands:
                c = c.lstrip("./") if not c.startswith("../") else c
                hits = self.under(c)
                if hits:
                    return hits, True, c
            name = t.rstrip("/")
            dirs = sorted({Path(r).parent.as_posix() for r in self.disk
                           if Path(r).parent.as_posix().endswith("/" + name)})
            if len(dirs) == 1:
                return self.under(dirs[0]), True, dirs[0] + "/"
            return [], True, t
        cands = []
        if base:
            cands.append(f"{base}/{t}")
        cands.append(t)
        if prev and "/" not in t:
            cands.append(f"{Path(prev).parent.as_posix()}/{t}")
        for c in cands:
            if self.exists(c):
                return [c], False, c
            if abs_path(c).is_dir():
                return self.under(c), True, c + "/"
        if "/" in t:
            hits = [r for r in self.disk if r.endswith("/" + t)]
        else:
            hits = self.by_name.get(t, [])
        hits = [h for h in hits if abs_path(h).exists()]
        if hits:
            return sorted(hits), False, t
        return [], False, t


def looks_like_path(t: str) -> bool:
    t = t.strip()
    if not t or t.startswith(("/", "~")) or "<" in t or "@" in t:
        return False
    if t in EXTERNAL:
        return True
    if re.search(r"\.(org|com|net|io|local|za)$", t):  # host names, not files
        return False
    if re.search(r"\.[A-Za-z0-9]{1,6}$", t):
        return True
    if t.endswith("/"):
        return True
    return False


def collect_refs(res: Resolver):
    """Yield (texfile, context, token, files, is_folder) for every file reference."""
    out = []
    for tf in tex_files():
        raw = tf.read_text(encoding="utf-8", errors="replace")
        prev = None
        for m in re.finditer(r"\\(texttt|includegraphics)(\[[^\]]*\])?\{", raw):
            kind = m.group(1)
            content, _ = braced(raw, m.end() - 1)
            content = norm_tex(content)
            # an evidence-table cell may hold several paths separated by commas
            parts = [content] if kind == "includegraphics" else [c for c in re.split(r",\s*", content)]
            for part in parts:
                if kind == "texttt" and not looks_like_path(part):
                    continue
                base = "Report" if kind == "includegraphics" else ""
                files, folder, token = res.resolve(part, prev, base)
                if kind == "includegraphics" and not files:
                    for ext in (".pdf", ".png", ".jpg"):
                        files, folder, token = res.resolve(part + ext, prev, base)
                        if files:
                            break
                ctx = context(raw, m.start(), tf.name)
                out.append((tf.name, ctx, part, files, folder))
                if files and not folder:
                    prev = files[0]
                elif files and folder:
                    prev = files[0]
    return out


def procedure_ids(res: Resolver) -> dict[str, set[str]]:
    ids: dict[str, set[str]] = defaultdict(set)
    proc = ROOT / "BenchTest" / "TEST_PROCEDURES.md"
    if not proc.exists():
        return ids
    text = proc.read_text(encoding="utf-8", errors="replace")
    sections = re.split(r"^### ", text, flags=re.M)[1:]
    tok_re = re.compile(r"(?:\.{1,3}_?)?[A-Za-z0-9_./*-]+(?:\.(?:log|csv|jsonl|json|txt|png|jpg|md|py)|/)")
    for sec in sections:
        m = re.match(r"([TCB]\d+a?)\.", sec)
        if not m:
            continue
        tid = m.group(1)
        prev = None
        for line in sec.splitlines():
            if "Evidence" not in line:
                continue
            for tok in tok_re.findall(line.split("Evidence", 1)[1]):
                if tok.rstrip("/") in GENERIC_FOLDERS:
                    continue
                files, folder, _ = res.resolve(tok, prev)
                for f in files:
                    ids[f].add(tid)
                if files:
                    prev = files[0]
    return ids


def plot_inputs() -> dict[str, list[str]]:
    """Files read by Report/figures/results/make_results_plots.py -> figure names."""
    script = ROOT / "Report" / "figures" / "results" / "make_results_plots.py"
    out: dict[str, list[str]] = defaultdict(list)
    if not script.exists():
        return out
    text = script.read_text(encoding="utf-8")
    for block in re.split(r"\ndef ", text):
        saves = re.findall(r'save\(fig,\s*"([^"]+)"\)', block)
        for m in re.finditer(r'LOGS\s*/\s*"([^"]+)"(?:\s*/\s*"([^"]+)")?', block):
            r = "BenchTest/logs/" + "/".join(g for g in m.groups() if g)
            out[r].extend(saves or ["(console check)"])
    return out


# ---------------------------------------------------------------- main build

def build(args):
    tracked, modified, disk = git_state()
    if not tracked:
        print("warning: git not available; 'in git' column will read 'no'", file=sys.stderr)
        disk = {rel(p) for p in walk(ROOT)}
    res = Resolver(disk)

    inventory: set[str] = set()
    for d in SCAN_DIRS:
        for p in walk(ROOT / d):
            inventory.add(rel(p))
    for g in SCAN_GLOBS:
        for p in ROOT.glob(g):
            if p.is_file() and not (SKIP_PARTS & set(p.parts)) and p.suffix not in SKIP_SUFFIXES:
                inventory.add(rel(p))
    for name, folder in EXTERNAL.items():
        for p in walk(folder):
            inventory.add(rel(p))

    refs = collect_refs(res)
    cites: dict[str, set[str]] = defaultdict(set)      # file -> citations
    generic: dict[str, set[str]] = defaultdict(set)    # file -> generic folder citations
    missing = []
    for texname, ctx, token, files, folder in refs:
        if not files:
            missing.append((texname, ctx, token))
            continue
        tok_norm = token.strip().rstrip("/")
        is_generic = folder and tok_norm in GENERIC_FOLDERS
        for f in files:
            label = f"{texname.replace('.tex', '')}: {ctx}"
            if is_generic:
                generic[f].add(label)
                continue
            cites[f].add(label)
            if texname in EVIDENCE_TEX or Path(f).suffix in DATA_EXT and Path(f).suffix not in {".png", ".pdf", ".jpg"}:
                inventory.add(f)

    # plain mentions of a file name (e.g. the videos named in Table tab:road1-videos)
    for tf in tex_files():
        raw = tf.read_text(encoding="utf-8", errors="replace")
        text = norm_tex(raw)
        for f in inventory:
            name = Path(f).name
            stem = Path(f).stem
            keys = [name] if (len(name) >= 14 or re.search(r"\d", name)) else []
            if len(stem) >= 20:
                keys.append(stem)
            for k in keys:
                i = text.find(k)
                if i != -1:
                    j = raw.replace("\\_", "_").find(k)
                    if j != -1:  # else the name only spans a line-break hint and is cited explicitly
                        cites[f].add(f"{tf.stem}: {context(raw, j, tf.name)}")
                    break

    plots = plot_inputs()
    for f, figs in plots.items():
        for fig in sorted(set(figs)):
            cites[f].add(f"plot input -> figures/results/{fig}")
        if res.exists(f):
            inventory.add(f)
        else:
            missing.append(("make_results_plots.py", "plot input", f))

    # PNG twins of the cited PDF plots, and the script that draws them
    script = "Report/figures/results/make_results_plots.py"
    for f in list(inventory):
        if f.startswith("Report/figures/results/") and not cites.get(f):
            twin = [g for g in inventory if g != f and Path(g).parent == Path(f).parent
                    and Path(g).stem == Path(f).stem and cites.get(g)]
            if twin:
                cites[f] |= {c + " (PNG copy)" for c in cites[twin[0]] if not c.startswith("plot input")}
    drawn = sorted({c for g in inventory if g.startswith("Report/figures/results/") and g.endswith(".pdf")
                    for c in cites.get(g, [])})
    if script in inventory and drawn and not cites.get(script):
        cites[script] |= {"draws " + d for d in drawn}

    tids = procedure_ids(res)
    for pat, tid, _why in SUPPLEMENT:
        for f in inventory:
            if fnmatch.fnmatch(f, pat) and not tids.get(f):
                tids[f].add(tid)

    rows = []
    for f in sorted(inventory):
        p = abs_path(f)
        if not p.exists() or not p.is_file():
            continue
        st = p.stat()
        date, how = file_date(f, p)
        if f.startswith("../"):
            git = "outside repo"
        elif f in modified:
            git = "yes (modified)"
        elif f in tracked:
            git = "yes"
        else:
            git = "no"
        tid = ", ".join(sorted(tids.get(f, []), key=lambda x: GROUP_ORDER.index(x) if x in GROUP_ORDER else 99)) or "-"
        rows.append(dict(path=f, date=date, date_src=how, tid=tid, size=st.st_size, sha=sha256(p), git=git,
                         cites=sorted(cites.get(f, [])), generic=sorted(generic.get(f, [])), private=is_private(f)))

    # dependencies: specifically cited or plot input
    for r in rows:
        r["depends"] = bool(r["cites"])

    return rows, missing, refs


def group_key(tid: str) -> tuple[int, str]:
    first = tid.split(",")[0].strip()
    return (GROUP_ORDER.index(first) if first in GROUP_ORDER else len(GROUP_ORDER), first)


def write_index(rows, missing, out: Path, pack_name: str | None = None):
    today = dt.date.today().isoformat()
    origin = run_git("remote", "get-url", "origin").strip() or "(no git remote)"
    head = run_git("rev-parse", "--short", "HEAD").strip() or "?"
    n = len(rows)
    not_git = [r for r in rows if r["git"] in ("no", "outside repo")]
    size_not_git = sum(r["size"] for r in not_git)
    dep_not_git = [r for r in not_git if r["depends"]]
    unref = [r for r in rows if not r["cites"]]
    missing_u = sorted(set(missing))

    L = []
    L.append("# SW-7 data index\n")
    L.append(f"Generated {today} by `tools/build_data_index.py` from commit {head} of {origin}. "
             "Do not edit by hand; run `python tools/build_data_index.py` again after adding data.\n")
    L.append("Each row is one file. Supports lists where the report cites the file (tex file: figure, table "
             "or section label; for the evidence table, the row), and plot inputs of "
             "`Report/figures/results/make_results_plots.py`. Test IDs follow `BenchTest/TEST_PROCEDURES.md`. "
             "To verify a copy, compare its SHA-256 (`sha256sum <file>` or "
             "`Get-FileHash -Algorithm SHA256 <file>`) with the value here. Checksums are of the files on "
             "disk when the index was built; a tracked file marked modified differs from the committed copy.\n")
    L.append("In git: yes = in the GitHub repository; no = on the author's OneDrive copy only (packed in the "
             "dated release archive if the report depends on it); outside repo = in the project folder next "
             "to the repository. Files marked private (video and pictures showing people) are held by the "
             "author and available on request; they are never packed.\n")
    L.append("## Summary\n")
    L.append(f"- Sources indexed: {n} files, {human(sum(r['size'] for r in rows))}.")
    L.append(f"- Not in git: {len(not_git)} files, {human(size_not_git)}; of these the report depends on "
             f"{len(dep_not_git)} ({human(sum(r['size'] for r in dep_not_git))}), "
             f"{sum(1 for r in dep_not_git if r['private'])} of them private.")
    L.append(f"- References in the report that resolve to no file: {len(missing_u)} (listed below).")
    L.append(f"- Files indexed but cited by nothing in the report: {len(unref)} (listed below).")
    if pack_name:
        L.append(f"- Release archive: `{pack_name}` (see SHA256SUMS.txt inside).")
    L.append("")

    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        groups[r["tid"].split(",")[0].strip()].append(r)
    L.append("## Sources by test\n")
    for g in sorted(groups, key=lambda x: group_key(x)):
        title = "Not assigned to a test" if g == "-" else g
        L.append(f"### {title}\n")
        L.append("| Path | Date | Test | Supports | Size | SHA-256 | In git |")
        L.append("|---|---|---|---|---|---|---|")
        for r in groups[g]:
            sup = "; ".join(r["cites"]) or "not cited"
            if r["private"]:
                sup += " (private: held by the author)"
            date = r["date"] + ("" if r["date_src"] == "name" else " (mtime)")
            L.append(f"| `{r['path']}` | {date} | {r['tid']} | {sup} | {human(r['size'])} | `{r['sha']}` | {r['git']} |")
        L.append("")

    L.append("## References in the report that resolve to no file\n")
    repo_missing = [m for m in missing_u if "/" in m[2]]
    bare_missing = [m for m in missing_u if "/" not in m[2]]
    if repo_missing:
        L.append("Paths that should exist in the repository:\n")
        L.append("| Tex file | Where | Reference as written |")
        L.append("|---|---|---|")
        for texname, ctx, tok in repo_missing:
            L.append(f"| {texname} | {ctx} | `{tok}` |")
    else:
        L.append("Paths that should exist in the repository: none missing.")
    L.append("")
    if bare_missing:
        L.append("Bare file names not found in the repository (files on a device, in the toolchain, or kept "
                 "out of git on purpose; not data, listed for completeness):\n")
        for texname, ctx, tok in bare_missing:
            L.append(f"- `{tok}` ({texname}, {ctx})")
        L.append("")
    L.append("## Data on disk cited by nothing in the report\n")
    L.append("These files sit in the data folders but no figure, table or section names them (a mention of a "
             "whole broad folder such as `BenchTest/logs/` does not count). Either cite them, or note them as "
             "supporting material only.\n")
    cited_paths = {r["path"] for r in rows if r["cites"]}
    for r in unref:
        notes = []
        sib = sorted(c for c in cited_paths if Path(c).parent == Path(r["path"]).parent
                     and not Path(r["path"]).parent.as_posix().rstrip("/") in GENERIC_FOLDERS)
        if sib:
            notes.append(f"same dataset folder as cited `{Path(sib[0]).name}`")
        if r["generic"]:
            notes.append("folder mentioned only in general")
        extra = f" ({'; '.join(notes)})" if notes else ""
        L.append(f"- `{r['path']}` ({human(r['size'])}, in git: {r['git']}){extra}")
    L.append("")
    L.append("## Held by the author, available on request\n")
    L.append("Video and pictures that show people, kept off GitHub and out of the release archive.\n")
    priv = [r for r in rows if r["private"] and r["git"] != "yes" and r["git"] != "yes (modified)"]
    for r in priv:
        L.append(f"- `{r['path']}` ({human(r['size'])}, SHA-256 `{r['sha']}`)")
    pub_priv = [r for r in rows if r["private"] and r["git"].startswith("yes")]
    if pub_priv:
        L.append("\nPictures named as showing a person that are already in the public repository (confirm each "
                 "shows only the author or a team member who agreed, or remove from git):\n")
        for r in pub_priv:
            L.append(f"- `{r['path']}`")
    L.append("\nServer database: the central store (`sw7_telemetry.db`, SQLite) lives on the Raspberry Pi 5 "
             "(`~/sw7_server/`) and is not copied to the laptop; the T15 results were exported from it as the "
             "CSV files in `BenchTest/logs/2026-10-11_t15/` with `Server/sync_report.py`.\n")
    out.write_text("\n".join(L), encoding="utf-8")
    return dict(n=n, not_git=len(not_git), size_not_git=size_not_git, dep_not_git=dep_not_git,
                missing=missing_u, unref=unref, priv=priv)


def pack(rows, index_path: Path, include_uncited: bool = False) -> Path:
    today = dt.date.today().isoformat()
    dest = ROOT.parent / "SW7_data_release"
    dest.mkdir(exist_ok=True)
    zpath = dest / f"SW7_data_release_{today}.zip"
    packed = [r for r in rows if r["git"] in ("no", "outside repo") and not r["private"]
              and (r["depends"] or include_uncited)]
    withheld = [r for r in rows if r["private"] and not r["git"].startswith("yes")]
    sums = "".join(f"{r['sha']}  {r['path']}\n" for r in packed)
    held = ["Held by the author, available on request.",
            "Withheld from this archive because they show people (privacy, ethics approval EBE-03305-2026).", ""]
    held += [f"{r['sha']}  {r['path']}  ({human(r['size'])})" for r in withheld]
    readme = (f"SW-7 data release {today}\n\n"
              "Files the report depends on that are not in the GitHub repository, at their repository paths.\n"
              "DATA_INDEX.md lists every source with its SHA-256; SHA256SUMS.txt covers the files in this archive\n"
              "(check with: sha256sum -c SHA256SUMS.txt). WITHHELD.txt lists video and pictures of people that\n"
              "are held by the author and available on request.\n")
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for r in packed:
            z.write(abs_path(r["path"]), r["path"])
        z.write(index_path, "DATA_INDEX.md")
        z.writestr("SHA256SUMS.txt", sums)
        z.writestr("WITHHELD.txt", "\n".join(held) + "\n")
        z.writestr("README.txt", readme)
    (dest / f"SW7_data_release_{today}.zip.sha256").write_text(f"{sha256(zpath)}  {zpath.name}\n", encoding="utf-8")
    print(f"packed {len(packed)} files ({human(sum(r['size'] for r in packed))}) -> {zpath} "
          f"({human(zpath.stat().st_size)}); {len(withheld)} withheld")
    return zpath


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pack", action="store_true", help="write a dated release zip into ../SW7_data_release/")
    ap.add_argument("--include-uncited", action="store_true",
                    help="with --pack, also pack untracked data the report does not cite (e.g. the 17 Oct trial)")
    ap.add_argument("--out", default=str(ROOT / "DATA_INDEX.md"), help="index output path")
    args = ap.parse_args()
    rows, missing, _ = build(args)
    out = Path(args.out)
    pack_name = f"SW7_data_release_{dt.date.today().isoformat()}.zip" if args.pack else None
    s = write_index(rows, missing, out, pack_name)
    print(f"{s['n']} sources; {s['not_git']} not in git ({human(s['size_not_git'])}); "
          f"{len(s['dep_not_git'])} of those cited by the report; {len(s['missing'])} unresolved references; "
          f"{len(s['unref'])} uncited files -> {out}")
    if args.pack:
        pack(rows, out, args.include_uncited)


if __name__ == "__main__":
    main()
