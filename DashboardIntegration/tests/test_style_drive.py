"""Offscreen test: the paper and depth style on Driving and Analytics (agent P1; Planning/paper-depth-theme-prompt.md
sections 3 to 5 and 10, Planning/data-ownership-and-merge-plan.md option A).

Builds a patched copy of the team's v1.1 dashboard (TUKZIE_DASHBOARD_DIR, as the other tests) with every patch group.
A local fake server plays Open-Meteo and Photon reverse (never the real APIs). Runs the dashboard at 1280 x 800:
  paper  Drive: the speed disc as the one hero (120 to 180 px), the Next turn, Around and Range tiles overlapping the
         disc's edge and opening Map, Sensors (or Surroundings) and Charging, no pedal bars, no route line under the
         nav pill, the battery percent only in the status bar, the ASIS strip in ink; Analytics: five cards (no
         battery %, battery temp or ambient temp), one hero value per card, ink charts. On both pages S.audit_signal
         (signal only on tappable things) and S.type_audit (13, 16, 22 or 120 to 180 px). Day, simulated drive and
         night screenshots in tests/style/drive/, and the paint time of the Driving page.
  team   TUKZIE_SW7_STYLE=team: the layout-pass pages (pedal bars, range and battery pair, eight cards), nothing paper.
Run: TUKZIE_DASHBOARD_DIR=<team Dashboard folder> python tests/test_style_drive.py
"""
import glob, json, os, shutil, subprocess, sys, tempfile, threading, time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)
TEAM = os.environ.get("TUKZIE_DASHBOARD_DIR", "").strip()
if not TEAM or not os.path.isdir(os.path.join(TEAM, "app", "pages")):
    sys.exit("Set TUKZIE_DASHBOARD_DIR to a copy of the team's v1.1 Dashboard folder")
SP = tempfile.mkdtemp(prefix="sw7_style_drive_")
OUT = os.path.join(HERE, "style", "drive"); os.makedirs(OUT, exist_ok=True)


def build():
    target, src = os.path.join(SP, "build"), os.path.join(SP, "src")
    shutil.copytree(TEAM, target, ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(src)
    for f in glob.glob(os.path.join(INTEG, "*.py")):
        shutil.copy(f, src)
    shutil.copy(os.path.join(INTEG, "tests", "dashboard_patches.py"), src)
    shutil.copytree(os.path.join(INTEG, "fonts"), os.path.join(src, "fonts"))
    r = subprocess.run([sys.executable, os.path.join(INTEG, "deploy", "apply_patches.py"), target, "--source", src,
                        "--native-map", "--team-dir", os.path.join(SP, "nonexistent")], capture_output=True, text=True)
    print("build: " + (r.stdout.strip().splitlines()[-1] if r.returncode == 0 else r.stdout + r.stderr))
    if r.returncode:
        sys.exit(1)
    return target


# ---- fake Open-Meteo and Photon (day) --------------------------------------------------------------------------------
UTC_OFFSET = 7200


def local(ts):
    return datetime.fromtimestamp(ts, timezone(timedelta(seconds=UTC_OFFSET))).strftime("%Y-%m-%dT%H:%M")


def forecast():
    now = time.time()
    hour0 = now - now % 3600
    hours = [hour0 + k * 3600 for k in range(13)]
    rise, sset = now - 4 * 3600, now + 6 * 3600
    return {"latitude": -33.96, "longitude": 18.46, "utc_offset_seconds": UTC_OFFSET,
            "current": {"time": local(now), "temperature_2m": 24.3, "weather_code": 0, "wind_speed_10m": 12.4, "is_day": 1},
            "hourly": {"time": [local(h) for h in hours], "temperature_2m": [24, 25, 26, 26, 25, 24, 23, 21, 20, 19, 18, 17, 17],
                       "weather_code": [0, 0, 1, 2, 2, 3, 3, 61, 61, 3, 2, 1, 0]},
            "daily": {"time": [local(now)[:10], local(now + 86400)[:10]], "sunrise": [local(rise), local(rise + 86400)],
                      "sunset": [local(sset), local(sset + 86400)]}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/v1/forecast"):
            body = json.dumps(forecast()).encode()
        elif self.path.startswith("/reverse"):
            body = json.dumps({"features": [{"properties": {"name": "University of Cape Town", "district": "Rondebosch"}}]}).encode()
        else:
            self.send_response(404); self.end_headers(); return
        try:
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        except OSError:
            pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
server.daemon_threads = True
threading.Thread(target=server.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{server.server_address[1]}"

SCRIPT = r'''
import sys, types, os, time, json, copy, math, faulthandler
faulthandler.enable()
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
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QAbstractButton
from PySide6.QtCore import QTimer, QRect, QRectF, QPoint, QEventLoop, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
a = QApplication(sys.argv)
OUT, MODE = sys.argv[1], sys.argv[2]
from app.main_window import MainWindow
w = MainWindow(); w.resize(1280, 800); w.show()
fails = []
def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)
def wait(cond, ms):
    t = time.monotonic()
    while not cond() and (time.monotonic() - t) * 1000 < ms:
        a.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50); time.sleep(0.01)
    return cond()
def spin(ms):
    wait(lambda: False, ms)
def rect_in(widget):
    return QRect(widget.mapTo(w, QPoint(0, 0)), widget.size())
def shoot(name):
    a.processEvents(); w.grab().save(f"{OUT}/{name}.png")
def paint_ms(n=25):
    a.processEvents(); w.grab(); out = []
    for _ in range(n):
        t = time.perf_counter(); w.grab(); out.append((time.perf_counter() - t) * 1000)
    return sorted(out)[n // 2]

TELEMETRY = {"tof": {"left_mm": 900, "ahead_mm": 450, "right_mm": 1150, "age_ms": 120},
             "fusion": {"hazards": [{"class": "person", "distance_m": 2.6, "bearing_deg": 2, "band": "monitoring",
                                     "source": "camera"}]}}

def feed(d, **kw):
    s = copy.copy(d._sw7_live_state); s.data_source = "sw7_telemetry"
    vals = dict(soc_pct=79.6, speed_kmh=23.0, range_km=56.2, battery_power_kw=1.7, odometer_km=1284.6,
                consumption_wh_km=46.0, trip_km=3.4)
    vals.update(kw)
    for k, v in vals.items():
        setattr(s, k, v)
    s.signal_validity = dict(s.signal_validity or {}, soc=True, speed=True)
    try:
        from app.data.vehicle_state import Gear
        s.gear = Gear.D
    except Exception:
        pass
    d._on_vehicle_state(s)
    a.processEvents()

def plan():
    lat0, lon0 = -33.9600, 18.4600
    mlat, mlon = 1 / 111320.0, 1 / (111320.0 * math.cos(math.radians(lat0)))
    pts = [SimpleNamespace(lat=lat0 + i * 10 * mlat, lon=lon0, road_name="Main Road", dist_km=i * 0.01, elevation_m=0.0) for i in range(41)]
    pts += [SimpleNamespace(lat=lat0 + 400 * mlat, lon=lon0 + i * 10 * mlon, road_name="Station Road", dist_km=0.4 + i * 0.01, elevation_m=0.0) for i in range(1, 41)]
    dest = {"name": "Station Road", "label": "Station Road, Rondebosch", "lat": pts[-1].lat, "lon": pts[-1].lon}
    return SimpleNamespace(route=pts, nearby_roads=[], destination=dest, waypoint=None, warnings=[], preview=[],
                           distance_km=0.8, duration_s=120.0, arrival_soc_pct=78.0, source="offline router")

def audits(d, page, tag):
    from app.widgets import sw7_style as S
    found = S.audit_signal(w)
    check(not found, f"{tag}: signal audit on the window: {S.ok_audit(found) or 'clean'}")
    bad = [(S.describe(x), p) for x, p in S.type_audit(page)]
    check(not bad, f"{tag}: text only in 13, 16, 22 or 120 to 180 px: {bad}")

def visible_texts(page):
    return [x.text() for x in page.findChildren(QLabel) if x.isVisible() and x.text()]

def drive_checks(d, tag):
    from app.widgets import sw7_style as S
    dr = d.driving
    st = dr.sw7_stage
    nt, ar, rg = st.next_turn, st.around, st.range
    page_h = d.stack.height()
    sp = dr.speed
    cx, cy, R = sp.disc()
    disc = QRectF(rect_in(sp).x() + cx - R, rect_in(sp).y() + cy - R, 2 * R, 2 * R)
    check(S.HERO_MIN <= sp.sw7_fonts.get("speed", 0) <= S.HERO_MAX, f"{tag}: speed hero {sp.sw7_fonts.get('speed')} px")
    for t in (nt, ar):
        g = QRectF(rect_in(t))
        over = (g.right() - disc.left()) if t is nt else (disc.right() - g.left())
        check(12 <= over <= 24, f"{tag}: {t.label} tile overlaps the disc's edge by {over:.0f} px (12 to 24)")
    g = QRectF(rect_in(rg))
    check(g.top() < disc.bottom() and g.bottom() <= rect_in(d.stack).bottom() - 16 + 1,
          f"{tag}: Range tile over the disc's open bottom and above the nav pill ({g.top():.0f} to {g.bottom():.0f})")
    for t in (nt, ar, rg):
        check(t.isVisible() and t.height() >= 64 and t.width() >= 64, f"{tag}: {t.label} is a {t.width()} x {t.height()} target")
        check(rect_in(t).bottom() <= rect_in(d.stack).bottom() - 16, f"{tag}: {t.label} clear of the bottom 16 px")
    check(not dr.brake.isVisible() and not dr.accel.isVisible() and not dr.pair.isVisible(), f"{tag}: no pedal bars, no pair")
    check(not dr.route.isVisible(), f"{tag}: no route line under the nav pill")
    texts = visible_texts(dr)
    check(not any("%" in x for x in texts), f"{tag}: no battery percent on the page (status bar only): {texts}")
    check(d.status.soc.isVisible() and "%" in d.status.soc.text(), f"{tag}: the status bar keeps the percent")

def run():
    from app.widgets import sw7_style as S
    d = w.dashboard
    d.telemetry.telemetry_updated.disconnect(d.hazard_banner.set_telemetry)
    d.status.timer.stop(); d.status.clock.setText("14:28")
    if MODE == "team":
        return run_team(d)
    svc = d.sw7_weather
    wait(lambda: svc.report is not None, 8000)
    d.status.timer.stop(); d.status.clock.setText("14:28")
    times = {}
    dr = d.driving
    check(getattr(dr, "sw7_paper", False), "Driving page in paper")
    try:      # the live-only manager republishes its no-data state; the test feeds its own live states
        d.vehicle_data.updated.disconnect(d._on_vehicle_state)
    except (RuntimeError, TypeError):
        pass
    try:      # and the advice the test sets is not replaced by the ASIS service's own updates
        d.asis.support_state_updated.disconnect(d._on_support)
    except (RuntimeError, TypeError, AttributeError):
        pass
    d.switch_page_id("driving"); feed(d)
    st = dr.sw7_stage
    st.refresh()
    st.around.set_telemetry(TELEMETRY); a.processEvents()
    check(st.range.value_text() == "56 km", f"Range tile: {st.range.value_text()!r}")
    check(st.around.metres == {"left": 0.9, "ahead": 0.45, "right": 1.15}, f"Around tile: {st.around.metres}")
    check(st.around.nearest and "2.6 m" in st.around.nearest, f"Around: nearest hazard {st.around.nearest!r}")
    check(dr.speed.sw7_fonts.get("text") == "23", f"speed shown {dr.speed.sw7_fonts.get('text')!r}")
    # the Around tile reads the dashboard's own telemetry signal
    d.telemetry.telemetry_updated.emit({"tof": {"left_mm": 700, "ahead_mm": 1300, "right_mm": 800, "age_ms": 50}})
    a.processEvents()
    check(st.around.metres["left"] == 0.7, "Around tile follows telemetry_updated")
    st.around.set_telemetry(TELEMETRY)
    shoot("day_drive")
    drive_checks(d, "day")
    nt = st.next_turn
    check(nt.summary.get("kind") == "none" and "Free driving" in nt.summary.get("status", ""),
          f"Next turn without a route: {nt.summary}")
    audits(d, dr, "day drive")
    times["paper_drive"] = paint_ms()
    # taps open the home pages
    for tile, want in ((st.next_turn, "navigation"), (st.around, "sensors"), (st.range, "charging")):
        d.switch_page_id("driving"); a.processEvents()
        QTest.mouseClick(tile, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(60, 60)); a.processEvents()
        want = "surroundings" if want == "sensors" and "surroundings" in d.page_by_id else want
        check(d.stack.currentWidget() is d.page_by_id[want], f"tapping {tile.label} opens {want}")
    d.switch_page_id("driving"); a.processEvents()
    # touch: a one-finger tap opens the page; a drag or a two-finger gesture that starts on a tile does not
    dev = QTest.createTouchDevice()
    c = st.next_turn.mapTo(w, QPoint(180, 180))
    def touch(points, moves=None, wait_ms=60):
        t = QTest.touchEvent(w, dev)
        for i, p0 in enumerate(points): t.press(i, p0)
        t.commit(); QTest.qWait(wait_ms)
        if moves:
            t = QTest.touchEvent(w, dev)
            for i, p1 in enumerate(moves): t.move(i, p1)
            t.commit(); QTest.qWait(wait_ms)
        t = QTest.touchEvent(w, dev)
        for i, p1 in enumerate(moves or points): t.release(i, p1)
        t.commit(); QTest.qWait(450)
    touch([c, c + QPoint(45, 12)])
    check(d.stack.currentWidget() is dr, "two fingers on a tile do not open its page")
    touch([c], [c + QPoint(-200, 0)])
    check(d.stack.currentWidget() is dr, "a one-finger drag from a tile does not open its page")
    touch([c])
    check(d.stack.currentWidget() is d.navigation, "a one-finger tap on Next turn opens the Map")
    d.switch_page_id("driving"); QTest.qWait(450)
    # advice strip
    p = dr.asis_panel
    from app.asis.models import Severity
    adv = SimpleNamespace(severity=Severity.WARNING, category="Road", line1="Speed bumps ahead on Main Road",
                          line2="", recommended_speed_kmh=20.0, semantic_key="bumps")
    p.set_support_state(SimpleNamespace(advisories=[adv], quality=None)); a.processEvents()
    check(p.isVisible() and p.line1.text().startswith("Speed bumps"), "ASIS strip shows the advice")
    check(S.text_px(p.line1) == 22 and S.text_px(p.heading) == 13, "ASIS strip: 22 px advice, 13 px heading")
    img = w.grab().toImage(); dg = rect_in(p.sw7_dot).center()
    q = img.pixelColor(dg.x(), dg.y()); wq = QColor(S.hx("warn"))
    check(abs(q.red() - wq.red()) + abs(q.green() - wq.green()) + abs(q.blue() - wq.blue()) < 40, "ASIS warning: a warn dot")
    shoot("day_drive_advice")
    audits(d, dr, "day drive advice")
    # Analytics
    an = d.analytics
    d.switch_page_id("analytics")
    for k in range(32):
        feed(d, odometer_km=1284.6 + k * 0.05, consumption_wh_km=44.0 + (k % 7), speed_kmh=12 + (k * 3) % 20)
    car = an.sw7_carousel
    check(car.count == 5 and car.item(0) is an.s_odo, f"Analytics: five cards from Odometer ({car.count})")
    check(not an.s_soc.isVisible() and not an.s_btemp.isVisible() and not an.s_atemp.isVisible(),
          "no battery %, battery temp or ambient temp cards")
    car.go_to(0); spin(400)
    check(an.s_odo.value.text() == f"{1284.6 + 31 * 0.05:.1f} km", f"odometer value {an.s_odo.value.text()!r}")
    shoot("day_analytics")
    audits(d, an, "day analytics")
    car.go_to(1); spin(400); shoot("day_analytics_power")
    car.go_to(an.sw7_graphs_index); spin(400)
    shoot("day_analytics_graphs_card")
    audits(d, an, "graphs card")
    QTest.mouseClick(car, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(car.width() // 2, car.height() // 2))
    spin(200)
    check(an.sw7_stack.currentWidget() is an.sw7_graphs_view, "tapping Graphs opens the charts")
    shoot("day_analytics_graphs")
    audits(d, an, "graphs")
    QTest.mouseClick(an.sw7_back, Qt.MouseButton.LeftButton); spin(200)
    car.go_to(0); spin(400)
    # simulated drive
    m = d.navigation.map
    d.switch_page_id("navigation"); spin(300)
    m.set_plan(plan(), reset_view=False); spin(200)
    check(m.start_simulation(), "simulated drive started")
    for _ in range(20): m._sim_step()
    d.switch_page_id("driving"); spin(600)
    s = d.current_state
    check(s.data_source == "sw7_simulated_drive", "Driving gets the simulated state")
    check(dr.speed.sw7_fonts.get("text") == "25", f"simulated speed on the disc {dr.speed.sw7_fonts.get('text')!r}")
    check(st.range.range_km is not None and abs(st.range.range_km - min(s.range_km, 999)) < 1e-6, "Range tile follows the simulation")
    nt.update(); a.processEvents(); w.grab()
    man, dist = m.next_maneuvers(1)[0]
    check(nt.summary.get("kind") == "turn" and nt.summary.get("distance") == m._distance_text(dist)
          and "Station Road" in nt.summary.get("instruction", ""), f"Next turn follows the map: {nt.summary}")
    shoot("simulated_drive")
    drive_checks(d, "simulated")
    audits(d, dr, "simulated drive")
    d.switch_page_id("analytics"); spin(400); shoot("simulated_analytics")
    for _ in range(300):
        if m.sim_arrived: break
        m._sim_step()
    d.switch_page_id("driving"); spin(400); nt.update(); a.processEvents(); w.grab()
    check(nt.summary.get("kind") == "arrived", f"Next turn at the end: {nt.summary.get('kind')}")
    m.stop_simulation(); spin(300)
    nt.update(); a.processEvents(); w.grab()
    # night
    feed(d)
    p.set_support_state(SimpleNamespace(advisories=[], quality=None))
    S.set_night(True); a.processEvents(); spin(300)
    shoot("night_drive")
    audits(d, dr, "night drive")
    times["paper_drive_night"] = paint_ms()
    d.switch_page_id("analytics"); spin(400); shoot("night_analytics")
    audits(d, an, "night analytics")
    car.go_to(an.sw7_graphs_index); spin(400)
    QTest.mouseClick(car, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(car.width() // 2, car.height() // 2))
    spin(200); shoot("night_analytics_graphs")
    audits(d, an, "night graphs")
    QTest.mouseClick(an.sw7_back, Qt.MouseButton.LeftButton); spin(100)
    S.set_night(False)
    print("PAINT " + json.dumps(times))
    print("RESULT", "PASS" if not fails else f"FAIL {fails}")
    a.quit()

def run_team(d):
    dr, an = d.driving, d.analytics
    check(not hasattr(d.status, "sw7_weather_chip"), "team: no paper frame")
    check(not getattr(dr, "sw7_paper", False) and not hasattr(dr, "sw7_stage"), "team: Driving is the layout pass")
    d.switch_page_id("driving"); spin(300)
    check(dr.brake.isVisible() and dr.accel.isVisible() and dr.pair.isVisible(), "team: pedal bars and the pair as before")
    check(an.sw7_carousel.count == 8 and not getattr(an, "sw7_paper", False), "team: eight Analytics cards")
    times = {"team_drive": paint_ms()}
    print("PAINT " + json.dumps(times))
    print("RESULT", "PASS" if not fails else f"FAIL {fails}")
    a.quit()

def wait_ready(n=0):
    if w.stack.currentWidget() is getattr(w, "dashboard", None) or n > 60:
        QTimer.singleShot(2500, run)
    else:
        QTimer.singleShot(500, lambda: wait_ready(n + 1))
wait_ready()
a.exec()
'''


def env_for(extra):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", TUKZIE_LIVE_ONLY="1", TUKZIE_NO_CONTROLLER="1",
               TUKZIE_SKIP_LOGIN="1", TUKZIE_SW7_THEME="0", TUKZIE_TELEMETRY_URL="http://127.0.0.1:9",
               TUKZIE_TILE_URL="http://127.0.0.1:9/{z}/{x}/{y}.png", TUKZIE_TILE_CACHE=os.path.join(SP, "tiles"),
               TUKZIE_WEATHER_URL=BASE + "/v1/forecast", TUKZIE_REVERSE_URL=BASE + "/reverse",
               TUKZIE_WEATHER_CACHE=os.path.join(SP, "weather", "last.json"),
               PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    for k in ("TUKZIE_SW7_STYLE", "TUKZIE_SW7_NIGHT", "TUKZIE_SW7_LAYOUT"):
        env.pop(k, None)
    env.update(extra)
    if sys.platform == "win32":
        env.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
    return env


def run(target, args, extra, label):
    r = subprocess.run([sys.executable, "-c", SCRIPT] + args, cwd=target, env=env_for(extra), capture_output=True,
                       text=True, timeout=600, encoding="utf-8", errors="replace")
    print(f"--- {label}")
    print("\n".join(l for l in r.stdout.splitlines() if l.lstrip().startswith(("ok", "FAIL", "RESULT", "PAINT"))))
    err = [l for l in r.stderr.splitlines() if ("Error" in l or "Traceback" in l or "line " in l) and "_Dummy" not in l
           and "PyObject_HasAttr" not in l]
    if err:
        print("\n".join(err[-12:]))
    if "RESULT PASS" not in r.stdout:
        print("\n".join(r.stderr.splitlines()[-30:]))
    paint = [json.loads(l[6:]) for l in r.stdout.splitlines() if l.startswith("PAINT ")]
    return "RESULT PASS" in r.stdout, (paint[0] if paint else {})


os.makedirs(os.path.join(SP, "tiles"), exist_ok=True)
full = build()
ok1, paint = run(full, [OUT, "paper"], {}, "paper")
ok2, paint_team = run(full, [OUT, "team"], {"TUKZIE_SW7_STYLE": "team"}, "team (TUKZIE_SW7_STYLE=team)")
paint.update(paint_team)
print("Paint time of a full 1280 x 800 frame on Driving (QWidget.grab, median of 25): "
      + ", ".join(f"{k} {v:.1f} ms" for k, v in sorted(paint.items())))
server.shutdown()
shutil.rmtree(SP, ignore_errors=True)
if not (ok1 and ok2):
    sys.exit(1)
print("ALL STYLE DRIVE TESTS PASSED")
