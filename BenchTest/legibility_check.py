"""Legibility and touch-target check of the deployed dashboard, with no participant (RQ2, R11; ISO 15008 character height).

Runs a patched copy of the dashboard offscreen at the panel's native 1280 x 800 with the deployed settings
(start_sw7_dashboard.sh: live-only, team layout, two cameras, no login, no controller, paper style), shows every page
in turn and records, for every visible text label and button: the font's pixel size and its capital height from
QFontMetricsF.capHeight() (the rendered height of capitals in that font, not an estimate), and every visible button's
width and height. Screenshots of each page are saved beside the JSON.

Criteria (Section 2.6 of the report): ISO 15008 character height by visual angle, 20 arc minutes recommended and 16
acceptable [reimer2014typeface, you2021charsize]; touch keys improved performance up to about 17.5 mm [kim2014touchkey].
Panel: 10.1 inch diagonal, 1280 x 800, so 149.4 px per inch, 0.170 mm per pixel. Eye-to-screen distance: 0.70 m
assumed (to be measured on the vehicle), with 0.60 and 0.80 m given as sensitivity.

Run: python BenchTest/legibility_check.py <patched dashboard folder> <out folder>
"""
import json, math, os, subprocess, sys

PX_MM = 10.1 * 25.4 / math.hypot(1280, 800)          # mm per pixel


def need_px(arcmin, dist_m):
    return 2 * dist_m * 1000 * math.tan(math.radians(arcmin / 60) / 2) / PX_MM


CHILD = r'''
import sys, os, json, types
class _Meta(type):
    def __getattr__(cls, name): return _Dummy
class _Dummy(metaclass=_Meta):
    def __init__(self, *a, **k): pass
    def __getattr__(self, name): return _Dummy()
    def __call__(self, *a, **k): return _Dummy()
    def __bool__(self): return False
    def __int__(self): return 0
_m = types.ModuleType("PySide6.QtMultimedia")
for _n in ("QSoundEffect", "QMediaPlayer", "QAudioOutput", "QMediaDevices", "QAudioDevice"):
    setattr(_m, _n, _Dummy)
sys.modules["PySide6.QtMultimedia"] = _m
from PySide6.QtWidgets import QApplication, QLabel, QAbstractButton, QStackedWidget
from PySide6.QtGui import QFontMetricsF
from PySide6.QtCore import QTimer
a = QApplication(sys.argv)
from app.main_window import MainWindow
w = MainWindow(); w.resize(1280, 800); w.show()
OUT = sys.argv[1]
rows = {"pages": []}

def widgets_on_screen():
    out = []
    for wd in w.findChildren(QLabel) + w.findChildren(QAbstractButton):
        if not wd.isVisible() or wd.window() is not w:
            continue
        g = wd.mapTo(w, wd.rect().topLeft())
        if g.x() >= 1280 or g.y() >= 800 or g.x() + wd.width() <= 0 or g.y() + wd.height() <= 0:
            continue
        txt = (wd.text() if hasattr(wd, "text") else "") or ""
        fm = QFontMetricsF(wd.font())
        out.append({"kind": type(wd).__name__, "text": txt.strip()[:40], "font_px": wd.font().pixelSize(),
                    "font_pt": wd.font().pointSizeF(), "cap_px": round(fm.capHeight(), 2),
                    "w": wd.width(), "h": wd.height(), "x": g.x(), "y": g.y(),
                    "button": isinstance(wd, QAbstractButton), "enabled": wd.isEnabled()})
    return out

def run(stack, i=0):
    if i >= stack.count():
        json.dump(rows, open(os.path.join(OUT, "legibility.json"), "w"), indent=1)
        a.quit(); return
    stack.setCurrentIndex(i)
    def take():
        name = type(stack.widget(i)).__name__
        w.grab().save(os.path.join(OUT, f"page_{i:02d}_{name}.png"))
        rows["pages"].append({"index": i, "page": name, "items": widgets_on_screen()})
        run(stack, i + 1)
    QTimer.singleShot(900, take)

def ready(n=0):
    d = getattr(w, "dashboard", None)
    if d is None or not d.isVisible():
        return QTimer.singleShot(500, lambda: ready(n + 1)) if n < 120 else (print("no dashboard"), a.quit())
    stacks = sorted(d.findChildren(QStackedWidget), key=lambda s: -s.count())
    print("stack pages:", stacks[0].count())
    QTimer.singleShot(2500, lambda: run(stacks[0]))
QTimer.singleShot(500, ready)
a.exec()
'''


def main():
    dash, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", TUKZIE_LIVE_ONLY="1", TUKZIE_NO_CONTROLLER="1", TUKZIE_SKIP_LOGIN="1",
               TUKZIE_SW7_THEME="0", TUKZIE_SW7_DUAL_CAM="1", QT_QPA_FONTDIR="C:/Windows/Fonts",
               TUKZIE_WEATHER_URL="http://127.0.0.1:9/v1/forecast", TUKZIE_REVERSE_URL="http://127.0.0.1:9/reverse",
               TUKZIE_TELEMETRY_URL="http://127.0.0.1:9", TUKZIE_PHONE_GPS_URL="http://127.0.0.1:9", PYTHONPATH=dash)
    child = os.path.join(out, "_child.py")
    open(child, "w", encoding="utf-8").write(CHILD)
    r = subprocess.run([sys.executable, child, out], cwd=dash, env=env, capture_output=True, text=True, timeout=600)
    print(r.stdout[-1500:], r.stderr[-1500:])
    data = json.load(open(os.path.join(out, "legibility.json")))
    need = {(a, d): need_px(a, d) for a in (16, 20) for d in (0.6, 0.7, 0.8)}
    texts, buttons = [], []
    for pg in data["pages"]:
        for it in pg["items"]:
            if it["text"]:
                texts.append((pg["page"], it))
            if it["button"] and it["enabled"]:
                buttons.append((pg["page"], it))
    seen = {}
    for page, it in texts:
        seen.setdefault((it["text"], it["cap_px"]), (page, it))
    caps = sorted(v[1]["cap_px"] for v in seen.values())
    summary = {"mm_per_px": PX_MM, "need_cap_px": {f"{a}arcmin@{d}m": round(v, 1) for (a, d), v in need.items()},
               "distinct_text_items": len(caps)}
    for key, req in (("ge20_at_0.7", need[(20, 0.7)]), ("ge16_at_0.7", need[(16, 0.7)])):
        summary[key] = sum(c >= req for c in caps)
    summary["cap_px_quantiles"] = {q: round(caps[int(q * (len(caps) - 1))], 1) for q in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0)} if caps else {}
    summary["below_16_at_0.7"] = sorted({(v[0], v[1]["text"], v[1]["cap_px"]) for v in seen.values() if v[1]["cap_px"] < need[(16, 0.7)]},
                                        key=lambda t: t[2])
    bt = {}
    for page, it in buttons:
        bt.setdefault((it["text"], it["w"], it["h"]), (page, it))
    mins = sorted(min(v[1]["w"], v[1]["h"]) * PX_MM for v in bt.values())
    summary["buttons"] = len(mins)
    summary["button_min_side_mm_quantiles"] = {q: round(mins[int(q * (len(mins) - 1))], 1) for q in (0.0, 0.25, 0.5, 0.75, 1.0)} if mins else {}
    summary["buttons_ge_17.5mm"] = sum(m >= 17.5 for m in mins)
    summary["buttons_ge_10mm"] = sum(m >= 10.0 for m in mins)
    json.dump(summary, open(os.path.join(out, "legibility_summary.json"), "w"), indent=1, default=list)
    print(json.dumps({k: v for k, v in summary.items() if k != "below_16_at_0.7"}, indent=1))
    print("below 16 arcmin at 0.7 m:", len(summary["below_16_at_0.7"]))
    for t in summary["below_16_at_0.7"][:25]:
        print("  ", t)


if __name__ == "__main__":
    main()
