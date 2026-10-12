"""Offscreen test of the layout pass for the Driving and Analytics pages (agent B, LAYOUT_DRIVE_PATCHES,
Planning/layout-improvements-prompt.md and Planning/google-stitch-dashboard-prompt.md 3.2 and 3.3).

Builds patched copies of the team's v1.1 dashboard (TUKZIE_DASHBOARD_DIR) and runs the whole dashboard at
1280 x 800 offscreen in live-only mode with the team look (TUKZIE_SW7_THEME=0, as deployed), three times:
  base: the integration as it was before this pass (git TUKZIE_LAYOUT_BASE, default 9b2bed3);
  off:  this integration with TUKZIE_SW7_LAYOUT=0;
  on:   this integration with the layout pass (default).
Checks:
  1. sizes with the layout on: speed 140 px whole number, unit 24 px; range and battery 36 px with 18 px
     labels; advice strip 64 px tall across the page with 22 px text; pedal bars 24 x 300 px with 18 px
     values; Analytics values 96 px with 32 px units, 18 px context lines, 64 x 64 px buttons, 64 px Back,
     charts scaled to their data (speed 0 to 50, battery 0 to 100, consumption 0 to 120, distance fitted),
     axis text 12 px; no visible text under 12 px on either page; no overlapping blocks on Driving;
  2. during a simulated drive the Driving page shows the simulated speed, range and battery;
  3. the switch: with TUKZIE_SW7_LAYOUT=0 the pages are pixel for pixel what the base integration draws.
Saves before (layout off) and after (layout on) screenshots at 1280 x 800 in tests/layout/drive/.

Run: TUKZIE_DASHBOARD_DIR=<copy of v1.1 Dashboard> python DashboardIntegration/tests/test_layout_drive.py
"""
import glob, json, os, shutil, subprocess, sys, tempfile

# Paper and depth style (sw7_weather): never the real weather API in a test, and no shared weather cache.
os.environ.setdefault("TUKZIE_WEATHER_URL", "http://127.0.0.1:9/v1/forecast")
os.environ.setdefault("TUKZIE_REVERSE_URL", "http://127.0.0.1:9/reverse")
os.environ.setdefault("TUKZIE_WEATHER_CACHE", os.path.join(__import__("tempfile").mkdtemp(prefix="sw7_wx_"), "last.json"))
# This test checks the layout pass in the team look: the paper style is tested in test_style_core.py.
os.environ["TUKZIE_SW7_STYLE"] = "team"
HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)
TEAM = os.environ.get("TUKZIE_DASHBOARD_DIR", "").strip()
if not TEAM or not os.path.isdir(os.path.join(TEAM, "app", "pages")):
    sys.exit("Set TUKZIE_DASHBOARD_DIR to a copy of the team's v1.1 Dashboard folder")
BASE_REV = os.environ.get("TUKZIE_LAYOUT_BASE", "9b2bed3")
OUT = os.path.join(HERE, "layout", "drive")
os.makedirs(OUT, exist_ok=True)
SP = tempfile.mkdtemp(prefix="sw7_layout_drive_")
CHANGED = ("sw7_driving.py", "sw7_analytics.py", "tests/dashboard_patches.py")


def build(name, overrides=None):
    """Patched copy of the dashboard; overrides maps an integration path to replacement text (the base files)."""
    target, src = os.path.join(SP, "build_" + name), os.path.join(SP, "src_" + name)
    shutil.copytree(TEAM, target, ignore=shutil.ignore_patterns("__pycache__", "logs"))
    os.makedirs(src)
    for f in glob.glob(os.path.join(INTEG, "*.py")):
        shutil.copy(f, src)
    shutil.copy(os.path.join(INTEG, "tests", "dashboard_patches.py"), src)
    shutil.copytree(os.path.join(INTEG, "fonts"), os.path.join(src, "fonts"))
    for rel, text in (overrides or {}).items():
        with open(os.path.join(src, os.path.basename(rel)), "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    r = subprocess.run([sys.executable, os.path.join(INTEG, "deploy", "apply_patches.py"), target, "--source", src,
                        "--native-map", "--team-dir", os.path.join(SP, "nonexistent")], capture_output=True, text=True)
    if r.returncode:
        print(r.stdout + r.stderr)
        sys.exit(1)
    return target


SCRIPT = r'''
import sys, types, math, json, os
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
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication, QLabel, QAbstractButton
from PySide6.QtCore import QTimer, QRect
a = QApplication(sys.argv)
from app.main_window import MainWindow
w = MainWindow(); w.resize(1280, 800); w.show()
OUT, TAG, MODE = sys.argv[1], sys.argv[2], sys.argv[3]       # MODE: base, off or on
res = {"fails": [], "notes": []}
def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: res["fails"].append(msg)
def shot(name):
    w.grab().save(os.path.join(OUT, f"{TAG}_{name}.png"))
def page_shot(widget, name):
    widget.grab().save(os.path.join(OUT, f"{TAG}_page_{name}.png"))
lat0, lon0 = -33.9600, 18.4600
mlat, mlon = 1 / 111320.0, 1 / (111320.0 * math.cos(math.radians(lat0)))
pts = [SimpleNamespace(lat=lat0 + i * 10 * mlat, lon=lon0, road_name="Main Road") for i in range(41)]
pts += [SimpleNamespace(lat=lat0 + 400 * mlat, lon=lon0 + i * 10 * mlon, road_name="Station Road") for i in range(1, 41)]
plan = SimpleNamespace(route=pts, nearby_roads=[], destination={"lat": pts[-1].lat, "lon": pts[-1].lon}, duration_s=120.0)

def small_text(page):
    bad = []
    for lbl in page.findChildren(QLabel) + page.findChildren(QAbstractButton):
        if lbl.isVisibleTo(page) and (lbl.text() or "").strip():
            px = lbl.font().pixelSize()
            if 0 < px < 12: bad.append(f"{type(lbl).__name__} {lbl.text()[:30]!r} {px}px")
    return bad

def wait_ready(n=0):
    d = getattr(w, "dashboard", None)
    if d is None or not d.isVisible():               # past the startup animation
        return QTimer.singleShot(500, lambda: wait_ready(n + 1)) if n < 120 else (print("FAIL no dashboard"), a.quit())
    QTimer.singleShot(2500, nodata)

def nodata():
    d = w.dashboard
    d.switch_page_id("driving")
    QTimer.singleShot(700, nodata_2)
def nodata_2():
    d = w.dashboard
    shot("driving"); page_shot(d.driving, "driving")
    if MODE == "on":
        dp = d.driving
        check(getattr(dp, "sw7_layout", False), "Driving: layout pass installed")
        f = dp.speed.sw7_fonts
        check(f.get("speed") == 140 and f.get("unit") == 24, f"speed font {f.get('speed')} px, unit {f.get('unit')} px")
        check(f.get("text") == "--", f"no live speed shows -- ({f.get('text')!r})")
        for key in ("range", "battery"):
            check(dp.pair.values[key].font().pixelSize() == 36 and dp.pair.labels[key].font().pixelSize() == 18,
                  f"{key}: value {dp.pair.values[key].font().pixelSize()} px, label {dp.pair.labels[key].font().pixelSize()} px")
        check(dp.pair.values["range"].text() == "--" and dp.pair.values["battery"].text() == "--", "range and battery -- with no data")
        s = dp.asis_panel
        check(s.height() == 64 and s.width() >= 1180, f"advice strip {s.width()} x {s.height()} px across the page")
        check(s.line1.font().pixelSize() == 22, f"advice text {s.line1.font().pixelSize()} px")
        check(s.isVisible() and s.line1.text() == "No live vehicle data", f"strip says {s.line1.text()!r}")
        tw, th = dp.brake.sw7_fonts.get("track", (0, 0))
        check(tw == 24 and 200 <= th <= 300 and dp.brake.sw7_fonts.get("value") == 18, f"pedal track {tw:.0f} x {th:.0f} px, value {dp.brake.sw7_fonts.get('value')} px")
        check(dp.route.font().pixelSize() == 16, f"route line {dp.route.font().pixelSize()} px")
        blocks = [("gear", dp.gear), ("faults", dp.faults), ("strip", s), ("dial", dp.speed), ("pair", dp.pair), ("route", dp.route)]
        rects = [(n, QRect(b.mapTo(dp, b.rect().topLeft()), b.size())) for n, b in blocks]
        over = [f"{n1}/{n2}" for i, (n1, r1) in enumerate(rects) for n2, r2 in rects[i + 1:] if r1.intersects(r2)]
        check(not over, f"no overlapping blocks on Driving {over}")
        outside = [n for n, r in rects if not dp.rect().contains(r)]
        check(not outside, f"every block inside the page {outside} (page {dp.width()} x {dp.height()})")
        r = dp.speed.sw7_fonts.get("radius", 0)
        check(r >= 170, f"dial radius {r:.0f} px (dial about {2 * r:.0f} px across)")
        check(not small_text(dp), f"no visible text under 12 px on Driving {small_text(dp)}")
    elif MODE == "off":
        dp = d.driving
        check(type(dp.speed).__name__ == "Speedometer" and not hasattr(dp, "pair"), "layout off: the team's dial and no pair")
        check(dp.asis_panel.maximumHeight() == 112, "layout off: the team's ASIS card")
    d.switch_page_id("analytics")
    QTimer.singleShot(900, analytics)

def analytics():
    d = w.dashboard; an = d.analytics
    shot("analytics"); page_shot(an, "analytics")
    if MODE == "on":
        cw, ch, pitch = an.sw7_carousel._geometry()
        peek = (an.sw7_carousel.height() - ch) / 2 - (pitch - ch)
        check(ch <= 480 and (abs(peek - 60) <= 1 or (ch == 480 and peek >= 60)), f"centre card {cw:.0f} x {ch:.0f} px, neighbours peek {peek:.0f} px")
        from app.pages import sw7_analytics as sa
        card = an.s_soc
        check(sa.VALUE_PX == 96 and sa.UNIT_PX == 32 and card.sw7_big.isVisible(), "card value 96 px, unit 32 px")
        check(card.sw7_context.font().pixelSize() == 18 and card.sw7_caption.font().pixelSize() == 20, "context line 18 px, caption 20 px")
        check(card.sw7_spark is not None and card.sw7_spark.height() == 120, "battery card has a 120 px sparkline")
        for b in (an.sw7_up, an.sw7_down):
            check(b.width() >= 64 and b.height() >= 64, f"carousel button {b.width()} x {b.height()} px")
        check(not small_text(an), f"no visible text under 12 px on Analytics {small_text(an)}")
    an.sw7_stack.setCurrentWidget(an.sw7_graphs_view)
    QTimer.singleShot(600, graphs)

def graphs():
    d = w.dashboard; an = d.analytics
    shot("analytics_graphs"); page_shot(an, "analytics_graphs")
    if MODE == "on":
        check(an.sw7_back.height() >= 64, f"Back button {an.sw7_back.height()} px tall")
        for name, want in (("speed_chart", (0.0, 50.0)), ("soc_chart", (0.0, 100.0)), ("eff_chart", (0.0, 120.0))):
            check(tuple(getattr(an, name).sw7_range) == want, f"{name} axis {getattr(an, name).sw7_range}")
        check(not small_text(an), f"no visible text under 12 px on Graphs {small_text(an)}")
    an.sw7_stack.setCurrentWidget(an.sw7_carousel_view)
    m = d.navigation.map
    m.set_plan(plan, reset_view=False)
    check(m.start_simulation(), "simulated drive started")
    for _ in range(20): m._sim_step()
    d.switch_page_id("driving")
    QTimer.singleShot(12000, sim)          # let the drive run on its own timer: chart points arrive

def sim():
    d = w.dashboard; dp = d.driving
    s = d.current_state
    check(s.data_source == "sw7_simulated_drive", f"simulated state on every page ({s.data_source})")
    shot("driving_sim")
    if MODE == "on":
        f = dp.speed.sw7_fonts
        check(f.get("text") == f"{s.speed_kmh:.0f}" and "." not in f.get("text", "."), f"speed as a whole number: {f.get('text')!r} for {s.speed_kmh}")
        check(dp.pair.values["battery"].text() == f"{s.soc_pct:.0f} %", f"battery {dp.pair.values['battery'].text()!r}")
        check(dp.pair.values["range"].text() == f"{min(70.0, s.range_km):.1f} km", f"range {dp.pair.values['range'].text()!r}")
    from app.asis.models import Severity
    adv = SimpleNamespace(severity=Severity.WARNING, category="ROUTE", semantic_key="test",
                          line1="Slow to 20 km/h, speed bumps ahead on Main Road", line2="", recommended_speed_kmh=20)
    dp.asis_panel._render(adv, 1, 2)
    QTimer.singleShot(150, sim_2)
def sim_2():
    d = w.dashboard; dp = d.driving
    shot("driving_sim_advice")
    if MODE == "on":
        check(dp.asis_panel.isVisible() and dp.asis_panel.height() == 64, "a warning shows in the 64 px strip")
    d.switch_page_id("analytics")
    QTimer.singleShot(800, sim_3)
def sim_3():
    d = w.dashboard; an = d.analytics
    shot("analytics_sim")
    an.sw7_stack.setCurrentWidget(an.sw7_graphs_view)
    QTimer.singleShot(600, sim_4)
def sim_4():
    d = w.dashboard; an = d.analytics
    shot("analytics_graphs_sim")
    if MODE == "on":
        dist = an.dist_chart
        data = list(dist._data)
        check(len(data) >= 2, f"distance chart has {len(data)} points")
        if data:
            lo, hi = dist.sw7_range
            check(lo <= min(data) and hi >= max(data) and hi - lo < 50, f"distance axis fitted to the data: {lo:.2f} to {hi:.2f} km")
    an.sw7_stack.setCurrentWidget(an.sw7_carousel_view)
    d.navigation.map.stop_simulation()
    print("RESULT", json.dumps(res))
    a.quit()

QTimer.singleShot(1000, wait_ready)
a.exec()
'''


def run(build_dir, tag, mode, layout):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", TUKZIE_LIVE_ONLY="1", TUKZIE_NO_CONTROLLER="1",
               TUKZIE_SKIP_LOGIN="1", TUKZIE_SW7_THEME="0", TUKZIE_TELEMETRY_URL="http://127.0.0.1:9",
               TUKZIE_SW7_LAYOUT=layout)
    if sys.platform == "win32":
        env.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
    shots = os.path.join(SP, "shots")
    os.makedirs(shots, exist_ok=True)
    r = subprocess.run([sys.executable, "-c", SCRIPT, shots, tag, mode], cwd=build_dir, env=env,
                       capture_output=True, text=True, timeout=300)
    print(f"--- {tag} (TUKZIE_SW7_LAYOUT={layout})")
    print("\n".join(l for l in r.stdout.splitlines() if l.lstrip().startswith(("ok", "FAIL"))))
    line = [l for l in r.stdout.splitlines() if l.startswith("RESULT ")]
    if not line:
        print(r.stdout[-3000:], r.stderr[-3000:])
        return ["no result from the dashboard run"], shots
    return json.loads(line[0][7:])["fails"], shots


def same_image(p1, p2):
    from PySide6.QtGui import QImage
    a, b = QImage(p1), QImage(p2)
    if a.isNull() or b.isNull() or a.size() != b.size():
        return False, "size differs"
    a = a.convertToFormat(QImage.Format.Format_RGB32)
    b = b.convertToFormat(QImage.Format.Format_RGB32)
    diff = sum(1 for y in range(0, a.height(), 2) for x in range(0, a.width(), 2) if a.pixel(x, y) != b.pixel(x, y))
    return diff == 0, f"{diff} sampled pixels differ"


fails = []
on_dir = build("on")
off_fails, shots = run(on_dir, "off", "off", "0")
on_fails, _ = run(on_dir, "on", "on", "1")
fails += [f"off: {f}" for f in off_fails] + [f"on: {f}" for f in on_fails]

base = {}
for rel in CHANGED:
    g = subprocess.run(["git", "-C", INTEG, "show", f"{BASE_REV}:DashboardIntegration/{rel}"], capture_output=True)
    if g.returncode:
        base = None
        break
    base[rel] = g.stdout.decode("utf-8")
print("--- switch: TUKZIE_SW7_LAYOUT=0 against the base integration", BASE_REV)
if base is None:
    print(f"SKIP pixel comparison: git revision {BASE_REV} not found")
else:
    base_fails, _ = run(build("base", base), "base", "base", "1")
    fails += [f"base: {f}" for f in base_fails]
    for name in ("driving", "analytics", "analytics_graphs"):
        ok, why = same_image(os.path.join(shots, f"base_page_{name}.png"), os.path.join(shots, f"off_page_{name}.png"))
        print(("ok   " if ok else "FAIL ") + f"{name} page with the layout off is the base look ({why})")
        if not ok:
            fails.append(f"switch: {name} differs from the base look ({why})")

for name in ("driving", "driving_sim", "driving_sim_advice", "analytics", "analytics_sim", "analytics_graphs",
             "analytics_graphs_sim"):
    for tag, label in (("off", "before"), ("on", "after")):
        src = os.path.join(shots, f"{tag}_{name}.png")
        if os.path.exists(src):
            shutil.copy(src, os.path.join(OUT, f"{label}_{name}.png"))
print("screenshots:", OUT)
shutil.rmtree(SP, ignore_errors=True)
if fails:
    print("FAILED:", fails)
    sys.exit(1)
print("ALL LAYOUT DRIVE TESTS PASSED")
