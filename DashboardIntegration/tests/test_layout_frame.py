"""Offscreen test: layout pass for the shared frame, Settings and Charging (agent A, sw7_layout_frame.py).

Builds two patched copies of the team's v1.1 dashboard (TUKZIE_DASHBOARD_DIR, as the other tests): one with every
patch group, one without LAYOUT_FRAME_PATCHES. Runs them offscreen at 1280 x 800 in live-only mode with no bridge:
  on   full copy, TUKZIE_SW7_LAYOUT unset (default on): size checks, screenshots tests/layout/frame/after_*.png
  off  full copy, TUKZIE_SW7_LAYOUT=0: screenshots tests/layout/frame/before_*.png
  base copy without the group: the widget tree of Driving, Charging and Settings (class, name, geometry, font size,
       text) must equal the "off" run exactly, so the switch gives back the team's layout.
Run: TUKZIE_DASHBOARD_DIR=<team Dashboard folder> python tests/test_layout_frame.py
"""
import glob, json, os, shutil, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)
TEAM = os.environ.get("TUKZIE_DASHBOARD_DIR", "").strip()
if not TEAM or not os.path.isdir(os.path.join(TEAM, "app", "pages")):
    sys.exit("Set TUKZIE_DASHBOARD_DIR to a copy of the team's v1.1 Dashboard folder")
SP = tempfile.mkdtemp(prefix="sw7_layout_frame_")
OUT = os.path.join(HERE, "layout", "frame"); os.makedirs(OUT, exist_ok=True)


def build(name, without_group):
    target, src = os.path.join(SP, "build_" + name), os.path.join(SP, "src_" + name)
    shutil.copytree(TEAM, target)
    os.makedirs(src)
    for f in glob.glob(os.path.join(INTEG, "*.py")):
        shutil.copy(f, src)
    shutil.copy(os.path.join(INTEG, "tests", "dashboard_patches.py"), src)
    shutil.copytree(os.path.join(INTEG, "fonts"), os.path.join(src, "fonts"))
    if without_group:
        with open(os.path.join(src, "dashboard_patches.py"), "a", encoding="utf-8") as f:
            f.write("\nPATCHES = tuple(p for p in PATCHES if p not in LAYOUT_FRAME_PATCHES)\n")
    r = subprocess.run([sys.executable, os.path.join(INTEG, "deploy", "apply_patches.py"), target, "--source", src,
                        "--native-map", "--team-dir", os.path.join(SP, "nonexistent")], capture_output=True, text=True)
    print(name + ": " + (r.stdout.strip().splitlines()[-1] if r.returncode == 0 else r.stdout + r.stderr))
    if r.returncode:
        sys.exit(1)
    return target


SCRIPT = r'''
import sys, types, json, copy, re
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
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QAbstractButton, QCheckBox, QComboBox, QPushButton,
                               QSlider, QStyle, QStyleOptionButton, QStyleOptionSlider)
from PySide6.QtCore import QTimer, QRect, QPoint
from PySide6.QtGui import QFont
a = QApplication(sys.argv)
from app.main_window import MainWindow
w = MainWindow(); w.resize(1280, 800); w.show()
OUT, MODE = sys.argv[1], sys.argv[2]
fails = []
def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)
def px(widget):
    f = widget.font(); return f.pixelSize() if f.pixelSize() > 0 else round(f.pointSizeF() * 96 / 72)
def rect_in(widget, ref):
    return QRect(widget.mapTo(ref, QPoint(0, 0)), widget.size())

def dump(d, pid):
    page = d.page_by_id[pid]
    out = []
    for wd in [d.status, d.nav, d.left, d.right] + [page] + page.findChildren(QWidget):
        if not wd.isVisible() or wd is d.status.clock:
            continue
        text = wd.text() if isinstance(wd, (QLabel, QAbstractButton)) else ""
        g = rect_in(wd, w)
        out.append([type(wd).__name__, wd.objectName(), g.x(), g.y(), g.width(), g.height(), px(wd), text])
    return out

def feed(d, soc):
    s = copy.copy(d._sw7_live_state); s.data_source = "sw7_telemetry"; s.soc_pct = soc
    s.signal_validity = dict(s.signal_validity or {}, soc=True)
    d._on_vehicle_state(s)

def wait_ready(n=0):
    if w.stack.currentWidget() is getattr(w, "dashboard", None) or n > 60:
        QTimer.singleShot(2500, run)
    else:
        QTimer.singleShot(500, lambda: wait_ready(n + 1))

def shoot(name):
    if MODE == "base":
        return
    w.grab().save(f"{OUT}/{'after' if MODE == 'on' else 'before'}_{name}.png")

def run():
    d = w.dashboard
    d.telemetry.telemetry_updated.disconnect(d.hazard_banner.set_telemetry)   # the test sets the pill itself
    tree = {}
    for pid in ("driving", "charging", "settings"):
        d.switch_page_id(pid); QApplication.processEvents()
        if MODE != "on":
            tree[pid] = dump(d, pid)
    if MODE != "on":
        with open(f"{OUT}/../tree_{MODE}.json", "w", encoding="utf-8") as f:
            json.dump(tree, f)
    # screenshots: a live state at 79.6 % shows the rounding difference (before: 80 % in the bar, 79 % in the ring)
    d.switch_page_id("driving"); QApplication.processEvents()
    feed(d, 79.6); shoot("driving")
    hb = d.hazard_banner
    hb._message = ("crit", "OBSTACLE 0.9 M LEFT"); hb._refresh(); QApplication.processEvents()
    feed(d, 79.6); shoot("driving_obstacle")
    if MODE == "on":
        st = d.status
        bar = rect_in(st, w)
        g = rect_in(hb, w)
        check(hb.isVisible() and g.top() >= bar.top() and g.bottom() <= bar.bottom(),
              f"obstacle pill inside the 48 px status bar: {g.getRect()} in {bar.getRect()}")
        for name, other in (("clock", st.clock), ("battery percent", st.soc), ("battery icon", st.battery), ("chip", d._sw7_marks.chip)):
            o = rect_in(other, w)
            text_w = other.fontMetrics().horizontalAdvance(other.text()) if isinstance(other, QLabel) and other is not d._sw7_marks.chip else o.width()
            if other is st.clock:
                o = QRect(o.right() - text_w, o.y(), text_w, o.height())
            check(not g.intersects(o), f"obstacle pill clear of the {name}")
    hb._message = None; hb._refresh()
    d.switch_page_id("charging"); QApplication.processEvents(); QApplication.processEvents(); feed(d, 79.6)
    shoot("charging")
    d.switch_page_id("settings"); QApplication.processEvents(); shoot("settings")
    sa = d.settings.scroll.verticalScrollBar(); sa.setValue(sa.maximum()); QApplication.processEvents(); shoot("settings_end"); sa.setValue(0)
    if MODE != "on":
        check(d.status.height() <= 39 and d.status.clock.font().pixelSize() == 11,
              f"switch off: status bar {d.status.height()} px, {d.status.clock.font().pixelSize()} px text")
        check(d.left.width() == 44 and d.left.height() == 44 and d.left.x() == 5, f"switch off: side arrows at x = 5, {d.left.width()} x {d.left.height()}")
        check(re.search(r"\d\d:\d\d:\d\d", d.status.clock.text()) is not None, "switch off: clock with date and seconds")
    else:
        checks_on(d)
    print("RESULT", "PASS" if not fails else f"FAIL {fails}")
    a.quit()

def checks_on(d):
    from app.widgets import sw7_layout_frame as L
    from app.pages.sw7_sim_link import CHIPS
    st, nav = d.status, d.nav
    # ---- status bar
    check(st.height() == 48, f"status bar 48 px: {st.height()}")
    check(px(st.weather) == 16 and px(st.clock) == 16, f"status text 16 px: weather {px(st.weather)}, clock {px(st.clock)}")
    check(px(st.soc) == 18 and st.soc.font().weight() >= QFont.Weight.Bold, f"battery percent 18 px bold: {px(st.soc)}")
    check(re.fullmatch(r"\d\d:\d\d", st.clock.text()) is not None, f"clock 'HH:MM': {st.clock.text()!r}")
    check("(" not in st.weather.text() and ":" not in st.weather.text(), f"short weather: {st.weather.text()!r}")
    chip = d._sw7_marks.chip
    for source in CHIPS:
        d._sw7_marks.show_source(source)
        g = rect_in(chip, st)
        check(chip.width() == 120 and chip.height() == 28 and "font-size: 14px" in chip.styleSheet()
              and g.top() >= 0 and g.bottom() < st.height(),
              f"chip {chip.text()!r} 120 x 28, 14 px, inside the bar: {g.getRect()}")
    c, s = rect_in(chip, w), rect_in(st.centre, w)
    soc_left = s.center().x() - (st.soc.width() + 8 + st.battery.width()) // 2
    check(c.right() < soc_left and rect_in(st.weather, w).left() < c.left(), "order: weather, chip, battery percent, clock")
    feed(d, 79.6)
    check(st.soc.text() == "80%", f"status bar SOC 79.6 -> {st.soc.text()!r}")
    # ---- nav bar and arrows
    check(nav.height() == 72, f"nav bar 72 px: {nav.height()}")
    labels = []
    for pid, b in nav.buttons.items():
        lab = getattr(b, "sw7_label", None)
        labels.append(lab.text() if lab else None)
        check(b.width() >= 96 and b.height() >= 64 and b.icon_size == 32,
              f"nav {pid}: {b.width()} x {b.height()}, icon {b.icon_size}")
        if lab:
            check(px(lab) == 13 and lab.isVisible() and lab.width() >= lab.fontMetrics().horizontalAdvance(lab.text()),
                  f"nav label {lab.text()!r} 13 px, fits")
    check(labels == ["Drive", "Analytics", "Diagnostics", "Map", "Camera", "Sensors", "Charging", "Settings"],
          f"nav labels in carousel order: {labels}")
    d.switch_page_id("charging"); QApplication.processEvents()
    from app.theme import THEME
    sel = nav.buttons["charging"]
    check(sel.isChecked() and THEME.hex("accent").lower() in sel.sw7_label.styleSheet().lower()
          and f"border:2px solid {THEME.hex('accent')}" in nav.styleSheet(), "current item: 2 px accent outline, accent label")
    navg, content = rect_in(nav, w), rect_in(d.stack, w)
    for arrow in (d.left, d.right):
        g = rect_in(arrow, w)
        check(g.width() == 64 and g.height() == 64, f"side arrow 64 x 64: {g.width()} x {g.height()}")
        check(navg.contains(g) and not g.intersects(content), f"side arrow inside the nav bar, off the page content: {g.getRect()}")
        check(g.left() >= 16 and g.right() <= w.width() - 17, "side arrow clear of the 16 px safe edge")
        check(all(not g.intersects(rect_in(b, w)) for b in nav.buttons.values()), "side arrow clear of every nav button")
    # ---- Settings
    page = d.settings
    d.switch_page_id("settings"); QApplication.processEvents()
    cards = page.sw7_columns
    left = [rect_in(cards[n], w) for n in L.LEFT_CARDS if n in cards]
    right = [rect_in(cards[n], w) for n in L.RIGHT_CARDS if n in cards]
    check(len(left) == 3 and len(right) == 3 and max(r.right() for r in left) < min(r.left() for r in right)
          and left[0].top() == right[0].top(), "Settings in two columns: Display, Voice, Driver | Navigation, Colour, Save")
    title = [l for l in page.findChildren(QLabel) if l.text() == "Settings"][0]
    tg = rect_in(title, d.stack)
    check(px(title) == 24 and tg.x() == 24 and tg.y() == 16, f"Settings title 24 px at (24, 16): {px(title)} at {tg.x()}, {tg.y()}")
    for box in [b for b in page.findChildren(QCheckBox) if b.isVisible()]:
        opt = QStyleOptionButton(); box.initStyleOption(opt)
        ind = box.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, opt, box)
        check(ind.width() == 64 and ind.height() == 36 and box.height() >= 64 and px(box) >= 16,
              f"toggle {box.text()!r}: {ind.width()} x {ind.height()}, row {box.height()} px")
    for kind in (QComboBox, QPushButton):
        for wd in [x for x in page.findChildren(kind) if x.isVisible()]:
            check(wd.height() >= 64, f"{kind.__name__} {getattr(wd, 'text', lambda: '')()!r} {wd.height()} px tall")
    for sl in [x for x in page.findChildren(QSlider) if x.isVisible()]:
        opt = QStyleOptionSlider(); sl.initStyleOption(opt)
        h = sl.style().subControlRect(QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, sl)
        check(h.width() == 44 and sl.height() >= 64, f"slider handle {h.width()} px, row {sl.height()} px")
    sws = page.sw7_swatches
    xs = sorted({rect_in(s, w).x() for s in sws})
    from app.theme import THEME as _T
    fm = __import__("PySide6.QtGui", fromlist=["QFontMetrics"]).QFontMetrics(_T.font(14, QFont.Weight.Bold))
    clipped = [s.p.name for s in sws if fm.horizontalAdvance(s.p.name) > s.width() - 84]
    check(len(sws) == 12 and len(xs) == 2 and not clipped and min(s.height() for s in sws) >= 64,
          f"twelve palettes in two columns, every name fits: columns at {xs}, clipped {clipped}")
    small = [(l.text()[:30], px(l)) for l in page.findChildren(QLabel) if l.isVisible() and px(l) < 13]
    check(not small, f"no Settings text below 13 px: {small}")
    # ---- Charging
    ch = d.charging
    d.switch_page_id("charging"); QApplication.processEvents(); feed(d, 79.6)
    ring = L.ring_texts(ch.tuk)
    check(ring == ("80%", "5.7 of 7.2 kWh") and ring[0] == st.soc.text(),
          f"ring SOC matches the status bar ({st.soc.text()!r}): {ring}")
    check(L.soc_text(79.4) == "79" and L.soc_text(None) == "--", "one rounding: 79.4 -> 79, unknown -> --")
    badge = ch.charge_badge
    check(badge.sw7_label.text() == "Source: Unknown" and badge.sw7_label.height() == 36
          and not any(p.isVisible() for p in (badge._solar_pill, badge._wired_pill, badge._unknown_pill)),
          f"charge source as one label: {badge.sw7_label.text()!r}")
    check(not isinstance(badge.sw7_label, QAbstractButton), "the source label is not a button")
    badge.set_source("solar")
    check(badge.sw7_label.text() == "Source: Solar", "source label follows the telemetry")
    check(ch.sw7_title.text() == "Charging" and px(ch.sw7_title) == 24, "Charging title 24 px")
    check(px(ch.status) == 18 and ch.status.text() == "Not charging", f"state line 18 px: {ch.status.text()!r}")
    for card in (ch.card_eta, ch.card_rate, ch.card_range, ch.card_energy):
        check(px(card.value_label) == 28, f"tile value 28 px: {card.value_label.text()!r}")

wait_ready()
a.exec()
'''


def run(target, mode, layout):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", TUKZIE_LIVE_ONLY="1", TUKZIE_NO_CONTROLLER="1",
               TUKZIE_SKIP_LOGIN="1", TUKZIE_SW7_THEME="0", TUKZIE_TELEMETRY_URL="http://127.0.0.1:9")
    env.pop("TUKZIE_SW7_LAYOUT", None)
    if layout is not None:
        env["TUKZIE_SW7_LAYOUT"] = layout
    if sys.platform == "win32":
        env.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
    r = subprocess.run([sys.executable, "-c", SCRIPT, OUT, mode], cwd=target, env=env, capture_output=True,
                       text=True, timeout=300)
    print(f"--- {mode}")
    print("\n".join(l for l in r.stdout.splitlines() if l.lstrip().startswith(("ok", "FAIL", "RESULT"))))
    err = [l for l in r.stderr.splitlines() if ("Error" in l or "Traceback" in l) and "_Dummy" not in l
           and "PyObject_HasAttr" not in l]
    if err:
        print("\n".join(err[-8:]))
    return "RESULT PASS" in r.stdout


full = build("full", False)
base = build("base", True)
ok = run(full, "on", None)
ok = run(full, "off", "0") and ok
ok = run(base, "base", None) and ok
trees = {}
for mode in ("off", "base"):
    path = os.path.join(OUT, "..", f"tree_{mode}.json")
    with open(path, encoding="utf-8") as f:
        trees[mode] = json.load(f)
    os.remove(path)
for pid in trees["base"]:
    same = trees["off"][pid] == trees["base"][pid]
    if not same:
        diff = [(x, y) for x, y in zip(trees["off"][pid], trees["base"][pid]) if x != y][:4]
        print(f"FAIL TUKZIE_SW7_LAYOUT=0 differs from the team layout on {pid}: {diff}"
              f" ({len(trees['off'][pid])} vs {len(trees['base'][pid])} widgets)")
        ok = False
    else:
        print(f"ok   TUKZIE_SW7_LAYOUT=0 gives the team's layout on {pid} ({len(trees['base'][pid])} widgets identical)")
shutil.rmtree(SP, ignore_errors=True)
if not ok:
    sys.exit(1)
print("ALL LAYOUT FRAME TESTS PASSED")
