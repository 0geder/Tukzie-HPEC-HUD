"""Orient every exported part for printing, group them onto Prusa MINI beds and slice with PrusaSlicer 2.9.4.

Uses the student's own MINI profiles (printer, 0.20 mm QUALITY, Prusament PLA) from %APPDATA%\\PrusaSlicer, plus a
small override per bed: structural parts (bracket, clamp cap, rail plates) get 5 perimeters and 50 % infill as the
engineering reviews ask; enclosures get 3 perimeters and 25 %; supports only where a part needs them.
Outputs: oriented/*.stl, gcode/*.gcode, projects/*.3mf and PRINT_LIST.md.
"""
import math
import os
import re
import struct
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
STL = os.path.join(HERE, "stl")
ORI = os.path.join(HERE, "oriented")
GC = os.path.join(HERE, "gcode")
PRJ = os.path.join(HERE, "projects")
CFG = os.path.join(HERE, "config")
for d in (ORI, GC, PRJ, CFG):
    os.makedirs(d, exist_ok=True)
PS = r"C:\Users\0geda\Downloads\PrusaSlicer-2.9.4\PrusaSlicer-2.9.4\prusa-slicer-console.exe"
APP = os.path.join(os.environ["APPDATA"], "PrusaSlicer")
PRINTER = os.path.join(APP, "printer", "Original Prusa MINI & MINI+ - Copy.ini")
PRINT = os.path.join(HERE, "config", "0.20mm QUALITY @MINI (cli).ini")   # the student's profile without
#   "bed_temperature_extruder = 0" and "wipe_tower_extruder = 0", which crash the 2.9.4 command line (multi-
#   extruder settings with no effect on the single-nozzle MINI; found with config/find_bad.py)
FILAMENT = os.path.join(APP, "filament", "Prusament PLA - Copy.ini")

# Up direction in the SolidWorks model frame for each part (the face opposite it goes on the bed), from the reviews.
UP = {
    "SW7_Dash_Bracket": "+Y",          # clamp split face on the bed, channel up
    "SW7_Dash_Clamp_Cap": "+Y",        # outer face on the bed, bore groove up
    "SW7_Dash_Cross_Joiner": "+Y", "SW7_Dash_Joiner_Plate": "+Y",
    "SW7_Dash_Pi5_Cradle": "-Y",       # base on the bed, standoffs up
    "SW7_Dash_Rail_Plate": "+Y",       # bolting face on the bed, rail up
    "SW7_Dash_Shell_Q_Left_Bottom": "+Y", "SW7_Dash_Shell_Q_Left_Top": "+Y",
    "SW7_Dash_Shell_Q_Right_Bottom": "+Y", "SW7_Dash_Shell_Q_Right_Top": "+Y",   # back plate on the bed
    "SW7_Pod_Box_Base": "+Y",          # floor on the bed (model Y = pod up)
    "SW7_Pod_Box_Lid": "-Y",           # outer face on the bed
    "SW7_Pod_Camera_Retainer": "+Y",
    "SW7_Pod_Head_Tray": "+Y",         # floor on the bed
    "SW7_Pod_Head_Upper": "-Z",        # on its back: rear face (pod -Y = model +Z) on the bed
    "SW7_Pod_Rail_Plate": "-Y",        # plate on the bed, rail up
    "SW7_Pod_Sunshade": "-Y",          # top plate on the bed, posts up
    "SW7_Pod_USB_Hatch_Cover": "+X",   # flat
    "SW7_IMU_Pod_Base": "+Y",          # floor on the bed
    "SW7_IMU_Pod_Lid": "-Y",           # engraved top face on the bed, hold-down rib up
}
OVR = {
    "structural": {"perimeters": 5, "fill_density": "50%", "support_material": 0},
    "structural_support": {"perimeters": 5, "fill_density": "50%", "support_material": 1,
                           "support_material_auto": 1, "support_material_buildplate_only": 1},
    "enclosure": {"perimeters": 3, "fill_density": "25%", "support_material": 0},
    "enclosure_bed_support": {"perimeters": 3, "fill_density": "25%", "support_material": 1,
                              "support_material_auto": 1, "support_material_buildplate_only": 1},
    "enclosure_support": {"perimeters": 3, "fill_density": "25%", "support_material": 1,
                          "support_material_auto": 1, "support_material_buildplate_only": 0},
}
# Beds: (name, override, [(part, copies)], times to print, purpose)
BEDS = [
    ("01_Dash_Shell_Left_Top", "enclosure", [("SW7_Dash_Shell_Q_Left_Top", 1)], 1, "Dashboard back shell quarter"),
    ("02_Dash_Shell_Left_Bottom", "enclosure", [("SW7_Dash_Shell_Q_Left_Bottom", 1)], 1, "Dashboard back shell quarter"),
    ("03_Dash_Shell_Right_Top", "enclosure", [("SW7_Dash_Shell_Q_Right_Top", 1)], 1, "Dashboard back shell quarter"),
    ("04_Dash_Shell_Right_Bottom", "enclosure", [("SW7_Dash_Shell_Q_Right_Bottom", 1)], 1, "Dashboard back shell quarter"),
    ("05_Dash_Rail_Plate_and_Joiners", "structural", [("SW7_Dash_Rail_Plate", 1), ("SW7_Dash_Joiner_Plate", 2)], 1,
     "Dashboard rail plate and the 2 joiner plates"),
    ("06_Dash_Pi5_Cradle_and_Cross_Joiner", "enclosure", [("SW7_Dash_Pi5_Cradle", 1), ("SW7_Dash_Cross_Joiner", 1)], 1,
     "Pi 5 cradle and cross joiner"),
    ("07_Bar_Clamp_Bracket_and_Cap", "structural_support", [("SW7_Dash_Bracket", 1), ("SW7_Dash_Clamp_Cap", 1)], 2,
     "Handlebar clamp: print twice (one for the dashboard, one for the sensor pod)"),
    ("08_Pod_Head_Upper", "enclosure_support", [("SW7_Pod_Head_Upper", 1)], 1, "Sensor pod head, upper shell"),
    ("09_Pod_Head_Tray_and_Camera_Retainer", "enclosure_bed_support",
     [("SW7_Pod_Head_Tray", 1), ("SW7_Pod_Camera_Retainer", 1)], 1, "Sensor pod tray and camera retainer"),
    ("10_Pod_Box_Base", "enclosure_bed_support", [("SW7_Pod_Box_Base", 1)], 1, "Sensor pod electronics box"),
    ("11_Pod_Box_Lid", "enclosure", [("SW7_Pod_Box_Lid", 1)], 1, "Sensor pod lid"),
    ("12_Pod_Rail_Plate_Sunshade_Hatch", "structural",
     [("SW7_Pod_Rail_Plate", 1), ("SW7_Pod_Sunshade", 1), ("SW7_Pod_USB_Hatch_Cover", 1)], 1,
     "Sensor pod rail plate, sunshade and USB hatch cover"),
    ("13_IMU_Pods_x2", "enclosure", [("SW7_IMU_Pod_Base", 2), ("SW7_IMU_Pod_Lid", 2)], 1,
     "Two IMU pods (dashboard and rear), base and lid each"),
]


def read_stl(p):
    with open(p, "rb") as f:
        f.read(80)
        n = struct.unpack("<I", f.read(4))[0]
        tris = [struct.unpack("<12f", f.read(50)[:48]) for _ in range(n)]
    return tris


def rot(v, up):
    x, y, z = v
    return {"+Y": (x, -z, y), "-Y": (x, z, -y), "+Z": (x, y, z), "-Z": (x, -y, -z),
            "+X": (-z, y, x), "-X": (z, y, -x)}[up]


def write_oriented(name):
    tris = read_stl(os.path.join(STL, name + ".stl"))
    out = []
    for t in tris:
        vs = [rot(t[3 + 3 * i: 6 + 3 * i], UP[name]) for i in range(3)]
        out.append(vs)
    lo = [min(v[a] for t in out for v in t) for a in range(3)]
    hi = [max(v[a] for t in out for v in t) for a in range(3)]
    path = os.path.join(ORI, name + ".stl")
    with open(path, "wb") as f:
        f.write(b"SW7 oriented for printing".ljust(80, b" "))
        f.write(struct.pack("<I", len(out)))
        for vs in out:
            p = [(v[0] - lo[0], v[1] - lo[1], v[2] - lo[2]) for v in vs]
            a = [p[1][i] - p[0][i] for i in range(3)]
            b = [p[2][i] - p[0][i] for i in range(3)]
            nrm = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
            ln = math.sqrt(sum(c * c for c in nrm)) or 1.0
            f.write(struct.pack("<12fH", *(c / ln for c in nrm), *p[0], *p[1], *p[2], 0))
    # area of facets lying on the bed (z within 0.01): how well the part sits down
    bed = 0.0
    for vs in out:
        if all(abs(v[2] - lo[2]) < 0.01 for v in vs):
            a = [vs[1][i] - vs[0][i] for i in range(3)]
            b = [vs[2][i] - vs[0][i] for i in range(3)]
            bed += 0.5 * abs(a[0] * b[1] - a[1] * b[0])
    return path, [round(hi[a] - lo[a], 1) for a in range(3)], round(bed)


def write_override(key):
    path = os.path.join(CFG, key + ".ini")
    with open(path, "w") as f:
        for k, v in OVR[key].items():
            f.write(f"{k} = {v}\n")
    return path


BED, GAP, MARGIN = 180.0, 6.0, 8.0
COMB = os.path.join(HERE, "beds")
os.makedirs(COMB, exist_ok=True)


def bounds(tris):
    return [min(v[a] for t in tris for v in t) for a in range(3)], [max(v[a] for t in tris for v in t) for a in range(3)]


def combine(name, parts):
    """Shelf-pack the oriented parts on the 180 x 180 bed (6 mm gaps, 8 mm margin) into one STL. PrusaSlicer 2.9.4's
    --merge crashes on this machine (also with default settings), so the layout is done here; every part stays a
    separate shell, so the printed result is the same."""
    items = []
    for part, n in parts:
        tris = [[t[3:6], t[6:9], t[9:12]] for t in read_stl(ORI_PATH[part])]
        lo, hi = bounds(tris)
        for _ in range(n):
            items.append((part, tris, lo, hi))
    items.sort(key=lambda it: -(it[3][1] - it[2][1]))
    placed, x, y, row_h = [], MARGIN, MARGIN, 0.0
    for part, tris, lo, hi in items:
        w, d = hi[0] - lo[0], hi[1] - lo[1]
        if x + w > BED - MARGIN + 1e-6:
            x, y, row_h = MARGIN, y + row_h + GAP, 0.0
        if x + w > BED - MARGIN + 1e-6 or y + d > BED - MARGIN + 1e-6:
            raise SystemExit(f"{name}: {part} does not fit on the bed")
        placed.append((tris, lo, x, y))
        x += w + GAP
        row_h = max(row_h, d)
    # centre the whole layout on the bed
    used_w = max(px + (max(v[0] for t in tr for v in t) - lo[0]) for tr, lo, px, py in placed)
    used_d = max(py + (max(v[1] for t in tr for v in t) - lo[1]) for tr, lo, px, py in placed)
    ox, oy = (BED - used_w) / 2 - MARGIN, (BED - used_d) / 2 - MARGIN
    out = []
    for tris, lo, px, py in placed:
        for t in tris:
            out.append([(v[0] - lo[0] + px + ox, v[1] - lo[1] + py + oy, v[2] - lo[2]) for v in t])
    path = os.path.join(COMB, name + ".stl")
    with open(path, "wb") as f:
        f.write(name.encode()[:80].ljust(80, b" "))
        f.write(struct.pack("<I", len(out)))
        for p in out:
            a = [p[1][i] - p[0][i] for i in range(3)]
            b = [p[2][i] - p[0][i] for i in range(3)]
            nrm = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
            ln = math.sqrt(sum(c * c for c in nrm)) or 1.0
            f.write(struct.pack("<12fH", *(c / ln for c in nrm), *p[0], *p[1], *p[2], 0))
    return path, len(items)


def slice_bed(name, key, parts):
    comb, n_items = combine(name, parts)
    files = [comb]
    common = ["--load", PRINTER, "--load", PRINT, "--load", FILAMENT, "--load", write_override(key)]
    g = os.path.join(GC, name + ".gcode")
    r = subprocess.run([PS, "--export-gcode", *common, "--dont-arrange", "-o", g, *files],   # laid out by combine()
                       capture_output=True, text=True)
    if r.returncode or not os.path.exists(g):
        return None, (r.stdout + r.stderr)[-800:]
    subprocess.run([PS, "--export-3mf", *common, "--dont-arrange", "-o", os.path.join(PRJ, name + ".3mf"), *files],
                   capture_output=True, text=True)
    txt = open(g, encoding="utf-8", errors="ignore").read()
    objs = list(range(n_items))
    t = re.search(r"estimated printing time \(normal mode\) = (.+)", txt)
    grams = re.search(r"filament used \[g\] = ([\d.]+)", txt)
    metres = re.search(r"filament used \[mm\] = ([\d.]+)", txt)
    return {"objects": len(objs), "time": t.group(1).strip() if t else "?", "g": float(grams.group(1)) if grams else 0.0,
            "m": float(metres.group(1)) / 1000 if metres else 0.0}, None


def minutes(s):
    d = re.search(r"(\d+)d", s); h = re.search(r"(\d+)h", s); m = re.search(r"(\d+)m", s)
    return (int(d.group(1)) * 1440 if d else 0) + (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)


ORI_PATH = {}
print("orientation:")
for name in UP:
    p, size, bed = write_oriented(name)
    ORI_PATH[name] = p
    print(f"  {name:32s} up {UP[name]}  size {size}  on bed {bed} mm2")

rows, total_min, total_g = [], 0, 0.0
for name, key, parts, times, purpose in BEDS:
    res, err = slice_bed(name, key, parts)
    if res is None:
        print("FAILED", name, err)
        rows.append((name, purpose, key, times, "FAILED", 0, 0))
        continue
    total_min += minutes(res["time"]) * times
    total_g += res["g"] * times
    print(f"  {name:40s} {res['objects']} parts {res['time']:>14s}  {res['g']:6.1f} g  x{times}")
    rows.append((name, purpose, key, times, res["time"], res["g"], res["m"]))

with open(os.path.join(HERE, "PRINT_LIST.md"), "w", encoding="utf-8") as f:
    f.write("# SW-7 print list: Prusa MINI, Prusament PLA, 0.20 mm QUALITY\n\n")
    f.write("Sliced with PrusaSlicer 2.9.4 from the student's own MINI profiles (`slice_all.py`). PLA is for fit checks; "
            "reprint the parts that live on the vehicle (bracket, cap, rail plates, shell, pod) in PETG or ASA, "
            "because PLA softens in the sun.\n\n")
    f.write("| Bed | What | Settings | Print | Time each | PLA each |\n|---|---|---|---|---|---|\n")
    for name, purpose, key, times, tm, g, m in rows:
        f.write(f"| {name} | {purpose} | {key.replace('_', ' ')} | x{times} | {tm} | {g:.0f} g ({m:.1f} m) |\n")
    f.write(f"\nTotal: about {total_min // 60} h {total_min % 60} min of printing and {total_g:.0f} g of PLA "
            f"(about {total_g / 1000:.2f} kg), counting the clamp twice.\n")
print(f"TOTAL {total_min // 60} h {total_min % 60} min, {total_g:.0f} g")
