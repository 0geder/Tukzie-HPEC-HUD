"""Front sensor pod (Pi 5): choose print orientations, lay out Prusa MINI beds and slice with PrusaSlicer 2.9.4.

Same pipeline as slice_all.py (the student's MINI profiles: printer, 0.20 mm QUALITY (cli copy), Prusament PLA; beds
laid out here and sliced with --dont-arrange because --merge crashes), plus an orientation search:
  1. every part is scored in the six axis-aligned orientations that fit the 180 mm cube: overhang area (facets facing
     down more than 45 deg from vertical, not on the bed), bed contact area and height;
  2. the best candidates (lowest overhang, and the runner-up when it is within reach) are sliced alone, with supports
     on when they have overhangs, and the one with the least filament wins (time breaks a tie);
  3. the winners are laid out on beds and sliced.
Input: <OUT>/stl/*.STL exported from SolidWorks (model orientation, mm). Output in OUT: oriented/, candidates/,
beds/, gcode/, projects/, orientation_scores.txt, PRINT_LIST.md.
Usage: python slice_front_pod.py <OUT folder>
"""
import math
import os
import re
import struct
import subprocess
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\0geda\Desktop\Fourth Year\EEE4022S\3D Prints\front_pod"
STL = os.path.join(OUT, "stl")
ORI, CAND, COMB = os.path.join(OUT, "oriented"), os.path.join(OUT, "candidates"), os.path.join(OUT, "beds")
GC, PRJ, CFG = os.path.join(OUT, "gcode"), os.path.join(OUT, "projects"), os.path.join(OUT, "config")
for d in (ORI, CAND, COMB, GC, PRJ, CFG):
    os.makedirs(d, exist_ok=True)
PS = r"C:\Users\0geda\Downloads\PrusaSlicer-2.9.4\PrusaSlicer-2.9.4\prusa-slicer-console.exe"
APP = os.path.join(os.environ["APPDATA"], "PrusaSlicer")
PRINTER = os.path.join(APP, "printer", "Original Prusa MINI & MINI+ - Copy.ini")
PRINT = r"C:\Users\0geda\Desktop\Fourth Year\EEE4022S\3D Prints\config\0.20mm QUALITY @MINI (cli).ini"
FILAMENT = os.path.join(APP, "filament", "Prusament PLA - Copy.ini")
OVR = {
    "structural": {"perimeters": 5, "fill_density": "50%", "support_material": 0},
    "structural_support": {"perimeters": 5, "fill_density": "50%", "support_material": 1,
                           "support_material_auto": 1, "support_material_buildplate_only": 0},
    "enclosure": {"perimeters": 3, "fill_density": "25%", "support_material": 0},
    "enclosure_bed_support": {"perimeters": 3, "fill_density": "25%", "support_material": 1,
                              "support_material_auto": 1, "support_material_buildplate_only": 1},
    "enclosure_support": {"perimeters": 3, "fill_density": "25%", "support_material": 1,
                          "support_material_auto": 1, "support_material_buildplate_only": 0},
}
PARTS = {   # part: settings family (the rail plate carries the pod: 5 perimeters, 50 %, as the reviews ask)
    "SW7_FPod_Box_Base": "enclosure", "SW7_FPod_Box_Lid": "enclosure", "SW7_FPod_Sunshade": "enclosure",
    "SW7_FPod_Rear_Port_Cover": "enclosure", "SW7_FPod_Side_Port_Cover": "enclosure",
    "SW7_FPod_Rail_Plate": "structural",
}
# Parts whose remaining overhangs are only 45 deg ledge undersides and short bridges (checked in SolidWorks, audit 3:
# the cable window top 40 mm, the port tops 28 and 30 mm, tie tunnels 3 to 4 mm), sliced without supports. On 16 Oct
# the box base without supports was 130.8 g / 11 h 28 min, against 147.1 g / 13 h 42 min with auto supports and
# 139.7 g / 12 h 30 min with build-plate-only supports (before the 45 deg gussets under the port bosses were added).
NO_SUPPORT = {"SW7_FPod_Box_Base": "+Y"}     # part: the orientation (floor down) this applies to
BED, GAP, MARGIN = 180.0, 6.0, 8.0
OVERHANG_COS = math.cos(math.radians(45))


def read_stl(p):
    with open(p, "rb") as f:
        f.read(80)
        n = struct.unpack("<I", f.read(4))[0]
        return [struct.unpack("<12f", f.read(50)[:48]) for _ in range(n)]


def rot(v, up):
    x, y, z = v
    return {"+Y": (x, -z, y), "-Y": (x, z, -y), "+Z": (x, y, z), "-Z": (x, -y, -z),
            "+X": (-z, y, x), "-X": (z, y, -x)}[up]


def oriented(tris, up, rotz=False):
    out = []
    for t in tris:
        vs = [rot(t[3 + 3 * i: 6 + 3 * i], up) for i in range(3)]
        if rotz:
            vs = [(-v[1], v[0], v[2]) for v in vs]
        out.append(vs)
    lo = [min(v[a] for t in out for v in t) for a in range(3)]
    return [[(v[0] - lo[0], v[1] - lo[1], v[2] - lo[2]) for v in t] for t in out]


def score(tris):
    """overhang mm2, bed contact mm2, size."""
    hi = [max(v[a] for t in tris for v in t) for a in range(3)]
    over = bed = 0.0
    for vs in tris:
        a = [vs[1][i] - vs[0][i] for i in range(3)]
        b = [vs[2][i] - vs[0][i] for i in range(3)]
        n = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
        ln = math.sqrt(sum(c * c for c in n))
        if ln < 1e-12:
            continue
        area = ln / 2
        nz = n[2] / ln
        if all(v[2] < 0.01 for v in vs):
            bed += area
        elif nz < -OVERHANG_COS:
            over += area * (-nz)            # projected area that needs support or a bridge
    return round(over), round(bed), [round(h, 1) for h in hi]


def write_stl(path, tris, name="SW7"):
    with open(path, "wb") as f:
        f.write(name.encode()[:80].ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for p in tris:
            a = [p[1][i] - p[0][i] for i in range(3)]
            b = [p[2][i] - p[0][i] for i in range(3)]
            n = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
            ln = math.sqrt(sum(c * c for c in n)) or 1.0
            f.write(struct.pack("<12fH", *(c / ln for c in n), *p[0], *p[1], *p[2], 0))


def write_override(key):
    path = os.path.join(CFG, key + ".ini")
    with open(path, "w") as f:
        for k, v in OVR[key].items():
            f.write(f"{k} = {v}\n")
    return path


def slice_files(name, key, files, outdir, project=True):
    common = ["--load", PRINTER, "--load", PRINT, "--load", FILAMENT, "--load", write_override(key)]
    g = os.path.join(outdir, name + ".gcode")
    r = subprocess.run([PS, "--export-gcode", *common, "--dont-arrange", "-o", g, *files], capture_output=True,
                       text=True)
    if r.returncode or not os.path.exists(g):
        return None, (r.stdout + r.stderr)[-800:]
    if project:
        subprocess.run([PS, "--export-3mf", *common, "--dont-arrange", "-o", os.path.join(PRJ, name + ".3mf"), *files],
                       capture_output=True, text=True)
    txt = open(g, encoding="utf-8", errors="ignore").read()
    t = re.search(r"estimated printing time \(normal mode\) = (.+)", txt)
    grams = re.search(r"filament used \[g\] = ([\d.]+)", txt)
    metres = re.search(r"filament used \[mm\] = ([\d.]+)", txt)
    return {"time": t.group(1).strip() if t else "?", "g": float(grams.group(1)) if grams else 0.0,
            "m": float(metres.group(1)) / 1000 if metres else 0.0}, None


def minutes(s):
    d = re.search(r"(\d+)d", s); h = re.search(r"(\d+)h", s); m = re.search(r"(\d+)m", s)
    return (int(d.group(1)) * 1440 if d else 0) + (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)


def centred(tris):
    """Place one part in the middle of the bed (for candidate slicing)."""
    hi = [max(v[a] for t in tris for v in t) for a in range(2)]
    ox, oy = (BED - hi[0]) / 2, (BED - hi[1]) / 2
    return [[(v[0] + ox, v[1] + oy, v[2]) for v in t] for t in tris]


# ---------- 1 and 2: orientation search ----------
log = open(os.path.join(OUT, "orientation_scores.txt"), "w", encoding="utf-8")


def out(s):
    print(s)
    log.write(s + "\n")


CHOSEN = {}
for part, family in PARTS.items():
    raw = read_stl(os.path.join(STL, part + ".STL"))
    rows = []
    for up in ("+X", "-X", "+Y", "-Y", "+Z", "-Z"):
        tris = oriented(raw, up)
        over, bed, size = score(tris)
        fits = size[2] <= BED and min(size[0], size[1]) <= BED - 2 * MARGIN and max(size[0], size[1]) <= BED - 2 * MARGIN
        rows.append((over, -bed, size[2], up, tris, size, fits))
    rows.sort(key=lambda r: (not r[6], r[0], r[1]))
    out(f"\n{part}  (model axis up / overhang mm2 projected / bed contact mm2 / size mm / fits)")
    for over, nb, h, up, _, size, fits in rows:
        out(f"  up {up}: overhang {over:6d}  bed {-nb:6d}  size {size}  {'fits' if fits else 'DOES NOT FIT'}")
    cands = [r for r in rows if r[6]][:2]
    best = None
    for over, nb, h, up, tris, size, fits in cands:
        key = family if over < 50 or NO_SUPPORT.get(part) == up else family + "_support"
        path = os.path.join(CAND, f"{part}_up{up[0] == '+' and 'p' or 'm'}{up[1]}.stl")
        write_stl(path, centred(tris), part)
        res, err = slice_files(os.path.basename(path)[:-4], key, [path], CAND, project=False)
        if res is None:
            out(f"  candidate up {up}: slicing FAILED {err}")
            continue
        out(f"  candidate up {up} ({key}): {res['time']}, {res['g']:.1f} g")
        if best is None or (res["g"], minutes(res["time"])) < (best[2]["g"], minutes(best[2]["time"])):
            best = (up, key, res)
    out(f"  CHOSEN: up {best[0]} ({best[1]})")
    CHOSEN[part] = best

# ---------- 3: beds ----------
BEDS = [  # name, settings, [(part, copies, rotate 90 deg on the bed)], purpose
    ("F1_FPod_Box_Base", None, [("SW7_FPod_Box_Base", 1, False)], "Front pod electronics box (Pi 5)"),
    ("F2_FPod_Box_Lid", None, [("SW7_FPod_Box_Lid", 1, False)], "Front pod lid"),
    ("F3_FPod_Rail_Plate_Sunshade_Covers", "structural",
     [("SW7_FPod_Rail_Plate", 1, False), ("SW7_FPod_Sunshade", 1, True), ("SW7_FPod_Rear_Port_Cover", 1, False),
      ("SW7_FPod_Side_Port_Cover", 1, False)], "Front pod rail plate, sunshade and the two cable port covers"),
]


def combine(name, items):
    placed, x, y, row_h = [], MARGIN, MARGIN, 0.0
    objs = []
    for part, n, rz in items:
        tris = oriented(read_stl(os.path.join(STL, part + ".STL")), CHOSEN[part][0], rz)
        write_stl(os.path.join(ORI, part + ".stl"), oriented(read_stl(os.path.join(STL, part + ".STL")),
                                                              CHOSEN[part][0]), part)
        hi = [max(v[a] for t in tris for v in t) for a in range(3)]
        for _ in range(n):
            objs.append((part, tris, hi))
    objs.sort(key=lambda o: -o[2][1])
    for part, tris, hi in objs:
        w, d = hi[0], hi[1]
        if x + w > BED - MARGIN + 1e-6:
            x, y, row_h = MARGIN, y + row_h + GAP, 0.0
        if x + w > BED - MARGIN + 1e-6 or y + d > BED - MARGIN + 1e-6:
            raise SystemExit(f"{name}: {part} does not fit on the bed")
        placed.append((tris, x, y, hi))
        x += w + GAP
        row_h = max(row_h, d)
    used_w = max(px + hi[0] for _, px, _, hi in placed)
    used_d = max(py + hi[1] for _, _, py, hi in placed)
    ox, oy = (BED - used_w) / 2 - MARGIN, (BED - used_d) / 2 - MARGIN
    allt = [[(v[0] + px + ox, v[1] + py + oy, v[2]) for v in t] for tris, px, py, _ in placed for t in tris]
    path = os.path.join(COMB, name + ".stl")
    write_stl(path, allt, name)
    return path, len(objs), [(round(px + ox, 1), round(py + oy, 1), hi) for _, px, py, hi in placed]


rows, total_min, total_g = [], 0, 0.0
out("\nbeds:")
for name, key, items, purpose in BEDS:
    if key is None:
        key = CHOSEN[items[0][0]][1]
    path, n, lay = combine(name, items)
    res, err = slice_files(name, key, [path], GC)
    if res is None:
        out(f"  {name} FAILED {err}")
        continue
    total_min += minutes(res["time"])
    total_g += res["g"]
    out(f"  {name:40s} {n} parts  {key:22s} {res['time']:>14s}  {res['g']:6.1f} g  layout {lay}")
    rows.append((name, purpose, key, res["time"], res["g"], res["m"]))
out(f"TOTAL {total_min // 60} h {total_min % 60} min, {total_g:.0f} g")
log.close()

with open(os.path.join(OUT, "PRINT_LIST.md"), "w", encoding="utf-8") as f:
    f.write("# Front sensor pod (Pi 5): Prusa MINI, Prusament PLA, 0.20 mm QUALITY\n\n")
    f.write("Sliced with PrusaSlicer 2.9.4 from the student's MINI profiles (`slice_front_pod.py`).\n\n")
    f.write("| Bed | What | Settings | Time | PLA |\n|---|---|---|---|---|\n")
    for name, purpose, key, tm, g, m in rows:
        f.write(f"| {name} | {purpose} | {key.replace('_', ' ')} | {tm} | {g:.0f} g ({m:.1f} m) |\n")
    f.write(f"\nTotal for the new parts: about {total_min // 60} h {total_min % 60} min and {total_g:.0f} g of PLA.\n")
