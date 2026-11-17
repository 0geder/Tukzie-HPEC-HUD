"""Alert spot check, 27 Oct road session (run 17 Nov 2026, after the report was submitted).

Picks dashboard screen captures (screens/HHMMSS.jpg, one every 2 s) taken during the laps (11:30 to 12:40)
while the Surroundings page was open, works out which camera side was showing from the Front/Rear toggle,
and takes an evenly spaced sample. Labels were made by eye from the frames; see alert_spot_check_labels.csv.

Run from BenchTest/logs/run2_road_2026-10-27:  python analysis/alert_spot_check_sample.py
"""
import json, os
from PIL import Image


def orange(p):
    return p[0] > 150 and p[1] < 120 and p[2] < 90


def sec(t):
    return int(t[:2]) * 3600 + int(t[2:4]) * 60 + int(t[4:6])


def tsec(ts):
    h, m, s = map(int, ts[11:19].split(":"))
    return h * 3600 + m * 60 + s


frames = sorted(f for f in os.listdir("screens") if "113000" <= f[:6] <= "124000")
surr = []
for f in frames:
    im = Image.open("screens/" + f).convert("RGB")
    if orange(im.getpixel((797, 732))):  # Surroundings tab underline
        side = "rear" if orange(im.getpixel((640, 110))) else ("front" if orange(im.getpixel((530, 110))) else None)
        if side:
            surr.append((f[:6], side))

# Stratify by the alert log's state (approximate: it did not always match the screen, so the
# labels use the hazard list visible on the screen, not this state).
logs = {}
for side, fn in (("front", "pi5_alerts_live.jsonl"), ("rear", "pi4_alerts_live.jsonl")):
    logs[side] = [(tsec(a["timestamp"]), a) for a in map(json.loads, (l for l in open(fn) if '"2026-10-27' in l))]


def active(side, t):
    st = {}
    for ts, a in logs[side]:
        if ts > t:
            break
        st[a["class"]] = a if a["alert_status"] == "active" else None
    return sorted(k for k, v in st.items() if v)


rows = [(h, side, active(side, sec(h))) for h, side in surr]


def even(lst, n):
    return [lst[int(i * len(lst) / n)] for i in range(n)] if len(lst) > n else lst


withA = [r for r in rows if r[2]]
noA = [r for r in rows if not r[2]]
sample = ([("A",) + r for r in even([r for r in withA if r[1] == "front"], 24) + even([r for r in withA if r[1] == "rear"], 16)]
          + [("N",) + r for r in even([r for r in noA if r[1] == "front"], 12) + even([r for r in noA if r[1] == "rear"], 8)])
print(len(frames), "frames in the laps;", len(surr), "on Surroundings;", len(sample), "sampled")
for i, s in enumerate(sample, 1):
    print(i, *s)
