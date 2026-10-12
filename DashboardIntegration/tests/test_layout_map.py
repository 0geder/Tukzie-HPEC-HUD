"""Offscreen test: the layout pass on the Navigation page (Planning/layout-improvements-prompt.md, agent D).

Builds a patched copy of the team's v1.1 dashboard (TUKZIE_DASHBOARD_DIR, as the other tests) and runs the full
dashboard at 1280 x 800 four times: TUKZIE_SW7_LAYOUT=0 and =1, each flat and with TUKZIE_MAP_TILT=1. In each run it
shows a simulated drive along a route with turns (turn banner, arrival-time bar), then a live drive along the same
route, then follow mode with no route, and saves a screenshot of each in tests/layout/map/ (before_*.png with
TUKZIE_SW7_LAYOUT=0, after_*.png with the layout pass).

With the layout pass it checks: every map control (Follow, Overview, 3D, +, -) is at least 64 x 64 and they form
one column on the right edge with the compass on top, 12 px apart and clear of the 16 px safe edge; Simulate drive /
End simulation is 200 x 64; the turn banner is at (24, 24), 520 x 128 with a 40 px Then strip; distance 48 px,
street 24 px, Then 18 px, arrival time 36 px, distance and arrival 24 px, chip and altitude 16 px, labels and
attribution 12 px or more; SIMULATED is a chip inside the arrival-time bar and no SIMULATED DRIVE label floats over
the map; none of banner, search field, column, Simulate drive, arrival-time bar, attribution, status line and
altitude chip overlap, and none covers the road ahead of the arrow; the team's Follow and Overview buttons are
hidden; the Navigate button is at least 120 x 48 and the status line 18 px.
With TUKZIE_SW7_LAYOUT=0 it checks the earlier geometry exactly (44 x 38 zoom buttons, 210 x 44 Simulate drive,
48 px compass at the old place, the team's Follow and Overview buttons, the centred banner and the SIMULATED DRIVE
label).
Tiles: TUKZIE_LAYOUT_TILE_CACHE, if set, is copied and used offline (real OpenStreetMap tiles of UCT make readable
screenshots); otherwise the map shows its offline vector roads. No tile is fetched from the internet.
Run: TUKZIE_DASHBOARD_DIR=<team Dashboard folder> python tests/test_layout_map.py
"""
import glob, os, shutil, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)
REPO = os.path.dirname(INTEG)
TEAM = os.environ.get("TUKZIE_DASHBOARD_DIR", "").strip()
if not TEAM or not os.path.isdir(os.path.join(TEAM, "app", "pages")):
    sys.exit("Set TUKZIE_DASHBOARD_DIR to a copy of the team's v1.1 Dashboard folder")
SP = tempfile.mkdtemp(prefix="sw7_layout_map_")
out = os.path.join(HERE, "layout", "map"); os.makedirs(out, exist_ok=True)
stamp = str(int(time.time()))
build, src = os.path.join(SP, "build_" + stamp), os.path.join(SP, "src_" + stamp)
shutil.copytree(TEAM, build, ignore=shutil.ignore_patterns("__pycache__"))
os.makedirs(src)
for f in glob.glob(os.path.join(INTEG, "*.py")):
    shutil.copy(f, src)
shutil.copy(os.path.join(INTEG, "tests", "dashboard_patches.py"), src)
shutil.copytree(os.path.join(INTEG, "fonts"), os.path.join(src, "fonts"))
r = subprocess.run([sys.executable, os.path.join(INTEG, "deploy", "apply_patches.py"), build, "--source", src,
                    "--native-map", "--team-dir", os.path.join(SP, "nonexistent")], capture_output=True, text=True)
print(r.stdout.strip().splitlines()[-1] if r.returncode == 0 else r.stdout + r.stderr)
if r.returncode:
    sys.exit(1)
cache = os.path.join(SP, "tiles")
given = os.environ.get("TUKZIE_LAYOUT_TILE_CACHE", "").strip()
if given and os.path.isdir(given):
    shutil.copytree(given, cache)
else:
    os.makedirs(cache)
base_env = dict(os.environ, QT_QPA_PLATFORM="offscreen", TUKZIE_LIVE_ONLY="1",
                TUKZIE_NO_CONTROLLER="1", TUKZIE_SKIP_LOGIN="1", TUKZIE_SW7_THEME="0",
                TUKZIE_TELEMETRY_URL="http://127.0.0.1:9", TUKZIE_TILE_URL="http://127.0.0.1:9/{z}/{x}/{y}.png",
                TUKZIE_TILE_CACHE=cache, TUKZIE_REPLAY=os.path.join(REPO, "CameraDetection", "tests", "replay_uct_route.txt"))
for k in ("TUKZIE_SW7_LAYOUT", "TUKZIE_MAP_TILT", "TUKZIE_TILE_MAP"):
    base_env.pop(k, None)
if sys.platform == "win32":
    base_env.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")   # offscreen Qt finds no fonts otherwise

script = r'''
import sys, types, json, math, copy, os, time
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
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QRect, QRectF, QPoint
from PySide6.QtTest import QTest
a = QApplication(sys.argv)
from app.main_window import MainWindow
w = MainWindow(); w.resize(1280, 800); w.show()
OUT, TAG = sys.argv[1], sys.argv[2]
LAYOUT = os.environ.get("TUKZIE_SW7_LAYOUT", "1") != "0"
TILT = os.environ.get("TUKZIE_MAP_TILT") == "1"
fails = []
def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + f"[{TAG}] " + msg)
    if not cond: fails.append(msg)

# a real UCT drive (replay file) as the route, named by stretch so the map finds turns
recs = [json.loads(l[5:]) for l in open(os.environ["TUKZIE_REPLAY"], encoding="utf-8") if l.startswith("DASH ")]
recs = [r for r in recs if r.get("fix") and r.get("lat") is not None]
names = ["Woolsack Drive", "University Avenue", "Rhodes Drive", "Main Road", "Station Road", "Belmont Road", "Lovers Walk"]
def course(p, q):
    la1, lo1, la2, lo2 = map(math.radians, (p[0], p[1], q[0], q[1]))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    return math.degrees(math.atan2(y, x)) % 360
raw = [(r["lat"], r["lon"]) for r in recs[200:520:4]]
pts, name_i, ref, dist = [], 0, None, 0.0
for i, (la, lo) in enumerate(raw):
    if i:
        dist += math.hypot((la - raw[i-1][0]) * 111320, (lo - raw[i-1][1]) * 111320 * math.cos(math.radians(la)))
    if i + 1 < len(raw):
        c = course((la, lo), raw[i + 1])
        if ref is None: ref = c
        if abs((c - ref + 180) % 360 - 180) > 50 and name_i + 1 < len(names):
            name_i += 1; ref = c
    pts.append(SimpleNamespace(lat=la, lon=lo, road_name=names[name_i], dist_km=dist / 1000, elevation_m=0.0))
dest = {"name": "Lovers Walk", "label": "Lovers Walk, Rondebosch", "lat": pts[-1].lat, "lon": pts[-1].lon}
plan = SimpleNamespace(route=pts, nearby_roads=[], destination=dest, waypoint=None, warnings=[], preview=[],
                       distance_km=dist / 1000, duration_s=dist / 1000 / 25 * 3600, arrival_soc_pct=78.0,
                       source="offline router")

def stage_rect(widget, nav):
    if widget is None or not widget.isVisible(): return None
    tl = widget.mapTo(nav.stage, QPoint(0, 0))
    return QRectF(tl.x(), tl.y(), widget.width(), widget.height())

def map_rect(m, nav, r):
    if r is None: return None
    off = m.mapTo(nav.stage, QPoint(0, 0))
    return QRectF(r).translated(off.x(), off.y())

def layout_checks(scene):
    d = w.dashboard; nav = d.navigation; m = nav.map
    W, H = m.width(), m.height()
    if not LAYOUT:
        check(m.zoom_in.geometry() == QRect(W - 62, H - 94, 44, 38) and m.zoom_out.geometry() == QRect(W - 62, H - 52, 44, 38),
              f"{scene}: zoom buttons 44 x 38 where they were")
        check(m.compass_rect() == QRectF(W - 84, 104, 48, 48), f"{scene}: 48 px compass where it was")
        check(not m.follow_button.isVisible() and not m.overview_button.isVisible(), f"{scene}: no map Follow/Overview")
        check(nav.follow_btn.isVisible() and nav.follow_btn.size().width() == 100 and nav.follow_btn.size().height() == 36,
              f"{scene}: the team's Follow button 100 x 36 {nav.follow_btn.size()}")
        if m.sim_button.isVisible():
            check(m.sim_button.geometry() == QRect(W - 290, H - 100, 210, 44), f"{scene}: Simulate drive 210 x 44 where it was")
        if m.simulating:
            check("SIMULATED DRIVE" in m.drawn_pills, f"{scene}: the SIMULATED DRIVE label as before")
        if "banner" not in m.overlay_rects and m.navigating:
            check(True, f"{scene}: no layout banner rect with the layout off")
        if TILT:
            check(m.tilt_button.geometry() == QRect(W - 62, H - 136, 44, 38), f"{scene}: 3D button 44 x 38 where it was")
        return
    slots = m.control_slots()
    buttons = [("Follow", m.follow_button), ("Overview", m.overview_button), ("+", m.zoom_in), ("-", m.zoom_out)]
    if TILT:
        buttons.insert(2, ("3D", m.tilt_button))
    xs = set()
    for name, b in buttons:
        g = b.geometry()
        check(b.isVisible() and g.width() >= 64 and g.height() >= 64, f"{scene}: {name} button {g.width()} x {g.height()}")
        xs.add(g.x())
    check(len(xs) == 1 and min(xs) + 64 <= W - 16 and min(xs) + 64 == W - 24, f"{scene}: one column 24 px from the right edge {xs}")
    tops = sorted([m.compass_rect().adjusted(-4, -4, 4, 4).top()] + [b.geometry().y() for _n, b in buttons])
    check(all(b - a >= 64 + 12 for a, b in zip(tops, tops[1:])), f"{scene}: column slots 12 px apart {tops}")
    check(m.compass_rect().width() >= 56 and m.compass_rect().left() >= min(xs), f"{scene}: compass {m.compass_rect().width():.0f} px on top of the column")
    check(not nav.follow_btn.isVisible() and not nav.overview_btn.isVisible(), f"{scene}: the team's small Follow/Overview hidden")
    check(not nav.altitude.isVisible(), f"{scene}: the ALTITUDE N/A card hidden")
    check(nav.plan_btn.width() >= 120 and nav.plan_btn.height() >= 48, f"{scene}: Navigate {nav.plan_btn.width()} x {nav.plan_btn.height()}")
    check(nav.search.height() >= 64, f"{scene}: search field {nav.search.height()} px tall")
    check(nav.route_status.font().pixelSize() == 18 or "18px" in nav.route_status.styleSheet().replace(" ", ""),
          f"{scene}: status line 18 px")
    if m.sim_button.isVisible():
        g = m.sim_button.geometry()
        check(g.width() >= 200 and g.height() >= 64 and g.right() <= W - 16 and g.bottom() <= H - 16,
              f"{scene}: {m.sim_button.text()} {g.width()} x {g.height()} inside the safe edge")
    px = m.overlay_px
    rects = {"search": stage_rect(nav.search, nav), "status": stage_rect(nav.route_status, nav),
             "column": map_rect(m, nav, QRectF(min(xs), slots["compass"].top(), 64, max(b.geometry().bottom() for _n, b in buttons) - slots["compass"].top())),
             "sim": map_rect(m, nav, QRectF(m.sim_button.geometry())) if m.sim_button.isVisible() else None,
             "attribution": map_rect(m, nav, m.overlay_rects.get("attribution")),
             "eta": map_rect(m, nav, m.overlay_rects.get("eta")),
             "banner": map_rect(m, nav, m.overlay_rects.get("banner")),
             "altitude": map_rect(m, nav, m.overlay_rects.get("altitude"))}
    rects = {k: v for k, v in rects.items() if v is not None}
    names_ = sorted(rects)
    clash = [(a_, b_) for i, a_ in enumerate(names_) for b_ in names_[i + 1:] if rects[a_].intersects(rects[b_])]
    check(not clash, f"{scene}: no overlays overlap {clash}")
    v = m.vehicle_screen_point()
    if v is not None:
        road = map_rect(m, nav, QRectF(v.x() - 40, v.y() - 200, 80, 200))
        over = [k for k, r in rects.items() if r.intersects(road)]
        check(not over, f"{scene}: the road ahead of the arrow is clear {over}")
    if m.navigating and "banner" in m.overlay_rects:
        b = m.overlay_rects["banner"]
        check(b.left() == 24 and b.top() == 24 and b.width() == 520, f"{scene}: banner top left at 24 px, 520 wide {b}")
        check(px.get("distance") == 48 or px.get("street") == 24, f"{scene}: distance 48 px, street 24 px {px}")
        if "then" in m.overlay_rects:
            t = m.overlay_rects["then"]
            check(abs(b.height() - (128 + 40)) < 0.5 and t.height() == 40 and px.get("then") == 18, f"{scene}: Then strip 40 px, 18 px text")
        check(rects["search"].left() >= rects["banner"].right() + 12, f"{scene}: search field right of the banner")
    if "eta" in m.overlay_rects:
        e = m.overlay_rects["eta"]
        check(e.width() == 560 and e.height() == 72 and abs(e.center().x() - W / 2) < 1, f"{scene}: arrival bar 560 x 72 bottom centre")
        check(px.get("eta_time") == 36 and px.get("eta_text") == 24, f"{scene}: arrival 36 / 24 px")
        check(m.overlay_rects["eta_text_right"].left() <= e.right() - 8, f"{scene}: arrival text fits in the bar")
    if m.simulating:
        chip = m.overlay_rects.get("sim_chip")
        check(chip is not None and m.overlay_rects["eta"].contains(chip) and px.get("chip", 0) >= 16,
              f"{scene}: SIMULATED chip inside the arrival bar")
        check(not any("SIMULATED" in t for t in m.drawn_pills), f"{scene}: no SIMULATED label over the map {m.drawn_pills}")
    check(all(b.label_px() >= 12 for _n, b in buttons if b.label), f"{scene}: button labels 12 px or more")

def settle(ms=1200):
    QTest.qWait(ms)

def settle_map(m, timeout_ms=10000):
    # four dashboards run at once, so animations can be slow: wait until heading-up and tilt have settled
    t = time.monotonic()
    def done():
        good = m._good_heading
        turned = good is None or not m.auto_follow or abs((m.bearing - good + 180) % 360 - 180) < 2
        return turned and abs(m.tilt - m._tilt_target()) < 0.002 and not m._tween_from
    while not done() and (time.monotonic() - t) * 1000 < timeout_ms:
        QTest.qWait(100)
    QTest.qWait(400)

def feed(d, **fields):
    s = copy.copy(d._sw7_live_state); s.data_source = "sw7_telemetry"
    s.sw7_cell_position = None
    for k, v in fields.items(): setattr(s, k, v)
    d._on_vehicle_state(s)

def run():
    d = w.dashboard; nav = d.navigation; m = nav.map
    d.vehicle_data._watchdog.stop()
    d.switch_page_id("navigation"); settle(500)
    # 1. simulated drive with turn banner and arrival-time bar
    nav._route_updated(plan); settle(300)
    check(m.start_simulation(), "simulation started")
    for _ in range(24):
        m._sim_step()
    settle(1000); settle_map(m)
    w.grab().save(f"{OUT}/{TAG}.png" if TILT else f"{OUT}/{TAG}_simulated.png")
    layout_checks("simulated drive")
    if TILT:
        check(m.tilt > 0.99, f"tilted view {m.tilt:.2f}")
        m.stop_simulation(); settle(300)
        return finish()
    m.stop_simulation(); settle(300)
    # 2. live drive along the route: turn banner, arrival bar, altitude known
    for i, r in enumerate(recs[236:252:2]):
        feed(d, latitude=r["lat"], longitude=r["lon"], heading=r.get("crs"), altitude_m=r.get("alt"),
             signal_validity=dict(d._sw7_live_state.signal_validity, gps=True, heading=True))
        QTest.qWait(450)
    settle(800); settle_map(m)
    w.grab().save(f"{OUT}/{TAG}_navigation.png")
    check(m.navigating and m.next_maneuvers(1), "navigating with a turn ahead")
    layout_checks("navigation")
    # 3. follow mode, no route
    nav._route_updated(None); settle(300)
    for r in recs[400:416:2]:
        feed(d, latitude=r["lat"], longitude=r["lon"], heading=r.get("crs"), altitude_m=r.get("alt"),
             signal_validity=dict(d._sw7_live_state.signal_validity, gps=True, heading=True))
        QTest.qWait(450)
    nav.set_follow_mode(True); settle(800); settle_map(m)
    w.grab().save(f"{OUT}/{TAG}_follow.png")
    check(m.auto_follow and m.heading_up, "follow mode, heading-up")
    if LAYOUT:
        check(m.follow_button.active and not m.overview_button.active, "Follow shows as selected")
        m.overview_button.click(); settle(200)
        check(not m.auto_follow and m.overview_button.active and not nav._map_status.get("auto_follow"),
              "Overview button goes through the page (map status updated)")
        m.follow_button.click(); settle(200)
        check(m.auto_follow and nav._map_status.get("auto_follow") and nav.follow_btn.text() == "Following",
              "Follow button goes through the page's set_follow_mode")
    layout_checks("follow")
    finish()

def finish():
    QTimer.singleShot(200, lambda: (print("RESULT", "PASS" if not fails else f"FAIL {fails}"), a.quit()))
START = time.monotonic()
def wait_for_dashboard():
    # the startup animation takes longer when four runs share the machine: wait until the dashboard shows
    if getattr(w, "stack", None) is not None and w.stack.currentWidget() is w.dashboard and w.dashboard.isVisible():
        return QTimer.singleShot(2500, run)
    if time.monotonic() - START > 120:
        check(False, "dashboard never showed"); return finish()
    QTimer.singleShot(500, wait_for_dashboard)
QTimer.singleShot(3000, wait_for_dashboard)
a.exec()
'''

runs = [("before", "0", "0"), ("after", "1", "0"), ("before_tilt", "0", "1"), ("after_tilt", "1", "1")]
procs = []
for tag, layout, tilt in runs:
    env = dict(base_env, TUKZIE_SW7_LAYOUT=layout)
    if tilt == "1":
        env["TUKZIE_MAP_TILT"] = "1"
    procs.append((tag, subprocess.Popen([sys.executable, "-c", script, out, tag], cwd=build, env=env,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)))
ok = True
for tag, proc in procs:
    so, se = proc.communicate(timeout=300)
    print("\n".join(l for l in so.splitlines() if l.lstrip().startswith(("ok", "FAIL", "RESULT"))))
    err = [l for l in se.splitlines() if ("Error" in l or "Traceback" in l) and "_Dummy" not in l and "PyObject_HasAttr" not in l]
    if err:
        print("\n".join(err[-8:]))
    if "RESULT PASS" not in so:
        ok = False
        print(se[-3000:])
shutil.rmtree(SP, ignore_errors=True)
if not ok:
    sys.exit(1)
print("screenshots:", ", ".join(sorted(os.listdir(out))))
print("ALL LAYOUT MAP TESTS PASSED")
