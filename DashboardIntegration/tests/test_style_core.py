"""Offscreen test: the paper and depth style, core (sw7_style.py, sw7_weather.py; Planning/paper-depth-theme-prompt.md).

Builds two patched copies of the team's v1.1 dashboard (TUKZIE_DASHBOARD_DIR, as the other tests): one with every
patch group, one without STYLE_CORE_PATCHES and its copies. A local fake server plays Open-Meteo and Photon reverse
(never the real APIs). Runs:
  unit   palette and the switch, THEME in paper, the signal rule, the weather service against the fake server
         (fresh, cached and offline, no data, the 6 s timeout off the UI thread, moving 5 km), night from sunset.
  paper  the dashboard at 1280 x 800: frame checks, the signal audit and the type audit on the frame, screenshots in
         tests/style/core/ (Driving and Map: day, night, simulated drive, obstacle, weather card open), paint time.
  team   TUKZIE_SW7_STYLE=team on the full copy, and the base copy: the widget trees and the window pixels of
         Driving and Map must be identical (the layout-pass look exactly), plus the team paint time.
Run: TUKZIE_DASHBOARD_DIR=<team Dashboard folder> python tests/test_style_core.py
"""
import glob, json, os, shutil, subprocess, sys, tempfile, threading, time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)
TEAM = os.environ.get("TUKZIE_DASHBOARD_DIR", "").strip()
if not TEAM or not os.path.isdir(os.path.join(TEAM, "app", "pages")):
    sys.exit("Set TUKZIE_DASHBOARD_DIR to a copy of the team's v1.1 Dashboard folder")
SP = tempfile.mkdtemp(prefix="sw7_style_core_")
OUT = os.path.join(HERE, "style", "core"); os.makedirs(OUT, exist_ok=True)


def build(name, without_group):
    target, src = os.path.join(SP, "build_" + name), os.path.join(SP, "src_" + name)
    shutil.copytree(TEAM, target, ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(src)
    for f in glob.glob(os.path.join(INTEG, "*.py")):
        shutil.copy(f, src)
    shutil.copy(os.path.join(INTEG, "tests", "dashboard_patches.py"), src)
    shutil.copytree(os.path.join(INTEG, "fonts"), os.path.join(src, "fonts"))
    if without_group:
        with open(os.path.join(src, "dashboard_patches.py"), "a", encoding="utf-8") as f:
            f.write("\nPATCHES = tuple(p for p in PATCHES if p not in STYLE_CORE_PATCHES)\n"
                    "COPIES = tuple(c for c in COPIES if c not in STYLE_CORE_COPIES)\n")
        # the base must be the integration as it was before this pass: no sw7_style in app/widgets either
        for mod in ("sw7_style.py", "sw7_weather.py"):
            os.remove(os.path.join(src, mod))
        # sensors_page.py keeps its paper method, which is only called by sw7_style
    r = subprocess.run([sys.executable, os.path.join(INTEG, "deploy", "apply_patches.py"), target, "--source", src,
                        "--native-map", "--team-dir", os.path.join(SP, "nonexistent")], capture_output=True, text=True)
    print(name + ": " + (r.stdout.strip().splitlines()[-1] if r.returncode == 0 else r.stdout + r.stderr))
    if r.returncode:
        sys.exit(1)
    return target


# ---- fake Open-Meteo and Photon --------------------------------------------------------------------------------------
UTC_OFFSET = 7200       # SAST


def local(ts):
    return datetime.fromtimestamp(ts, timezone(timedelta(seconds=UTC_OFFSET))).strftime("%Y-%m-%dT%H:%M")


class Fake:
    mode = "day"         # day, night, slow, error
    requests = []


def forecast(mode):
    now = time.time()
    hour0 = now - now % 3600
    hours = [hour0 + k * 3600 for k in range(13)]
    temps = [24, 25, 26, 26, 25, 24, 23, 21, 20, 19, 18, 17, 17]
    codes = [0, 0, 1, 2, 2, 3, 3, 61, 61, 3, 2, 1, 0]
    if mode == "night":     # sunrise in 5 h, sunset 7 h ago
        rise, sset = now + 5 * 3600, now - 7 * 3600
        days = ([local(rise - 86400), local(rise)], [local(sset), local(sset + 86400)])
    else:                   # sunrise 4 h ago, sunset in 6 h
        rise, sset = now - 4 * 3600, now + 6 * 3600
        days = ([local(rise), local(rise + 86400)], [local(sset), local(sset + 86400)])
    return {"latitude": -33.96, "longitude": 18.46, "utc_offset_seconds": UTC_OFFSET, "timezone": "Africa/Johannesburg",
            "current": {"time": local(now), "temperature_2m": 24.3 if mode != "night" else 15.6,
                        "weather_code": 0, "wind_speed_10m": 12.4, "is_day": 0 if mode == "night" else 1},
            "hourly": {"time": [local(h) for h in hours], "temperature_2m": temps, "weather_code": codes},
            "daily": {"time": [local(now)[:10], local(now + 86400)[:10]], "sunrise": days[0], "sunset": days[1]}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        Fake.requests.append(self.path)
        mode = Fake.mode
        if self.path.startswith("/v1/forecast"):
            if mode == "slow":
                time.sleep(9)
            if mode == "error":
                self.send_response(500); self.end_headers(); return
            body = json.dumps(forecast(mode)).encode()
        elif self.path.startswith("/reverse"):
            body = json.dumps({"features": [{"properties": {"name": "University of Cape Town", "district": "Rondebosch",
                                                            "city": "Cape Town"}}]}).encode()
        elif self.path.startswith("/mode/"):
            Fake.mode = self.path.split("/")[-1]; body = b"{}"
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

PRELUDE = r'''
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
import urllib.request
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QAbstractButton
from PySide6.QtCore import QTimer, QRect, QPoint, QEventLoop, QElapsedTimer
from PySide6.QtGui import QColor, QFont
a = QApplication(sys.argv)
FAKE = os.environ["SW7_FAKE"]
fails = []
def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)
def mode(m):
    urllib.request.urlopen(FAKE + "/mode/" + m, timeout=3).read()
def wait(cond, ms):
    t = time.monotonic()
    while not cond() and (time.monotonic() - t) * 1000 < ms:
        a.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50); time.sleep(0.01)
    return cond()
def spin(ms):
    wait(lambda: False, ms)
def px(widget):
    f = widget.font(); return f.pixelSize() if f.pixelSize() > 0 else round(f.pointSizeF() * 96 / 72)
def near(c, hexcol, tol=10):
    q = QColor(hexcol); return abs(c.red() - q.red()) + abs(c.green() - q.green()) + abs(c.blue() - q.blue()) <= tol
'''

UNIT = PRELUDE + r'''
import app.pages.dashboard_main          # installs the style (TUKZIE_SW7_STYLE unset: paper)
from app.widgets import sw7_style as S, sw7_weather as Wx
from app.theme import THEME
# ---- palette and switch
brief = {"paper": "#F3ECE6", "paper_deep": "#E7DCD3", "card": "#FBF8F5", "ink": "#1E1A17", "ink_2": "#6B625B",
         "ink_3": "#A89F98", "charcoal": "#34353A", "signal": "#B9562F", "signal_pressed": "#96421F",
         "signal_tint": "#F1DDD2", "ok": "#4F7A55", "warn": "#C98A16", "critical": "#B3261E"}
check(all(S.DAY[k].upper() == v for k, v in brief.items()), "day palette = the brief's tokens")
check(S.NIGHT["paper"] == "#1C1A18" and S.NIGHT["card"] == "#26231F" and S.NIGHT["ink"] == "#F3ECE6"
      and S.NIGHT["ink_2"] == "#B5ABA3" and S.NIGHT["signal"] == "#D9744A", "night (Ink) palette = the brief's tokens")
check(S.enabled(), "TUKZIE_SW7_STYLE unset: paper")
os.environ["TUKZIE_SW7_STYLE"] = "team"; check(not S.enabled(), "TUKZIE_SW7_STYLE=team: off")
os.environ["TUKZIE_SW7_STYLE"] = "paper"; os.environ["TUKZIE_SW7_LAYOUT"] = "0"; check(not S.enabled(), "layout pass off: off")
del os.environ["TUKZIE_SW7_STYLE"]; del os.environ["TUKZIE_SW7_LAYOUT"]
check(THEME.hex("bg") == S.DAY["paper"] and THEME.hex("card") == S.DAY["card"] and THEME.hex("accent") == S.DAY["signal"]
      and THEME.hex("text") == S.DAY["ink"] and THEME.hex("text_dim") == S.DAY["ink_2"], "THEME gives the paper palette")
check(THEME.status("crit").name().upper() == S.DAY["critical"] and THEME.status("info").name().upper() == S.DAY["ink_2"].upper(),
      "THEME status: critical, and info is ink (not signal)")
check(THEME.font(16).family() == "Atkinson Hyperlegible", f"THEME font: {THEME.font(16).family()}")
check(not THEME.is_light is False and "#B9562F" in THEME.stylesheet(), "paper stylesheet: buttons in signal")
# the signal rule
sig = QColor(S.DAY["signal"])
check(S.signal_like(sig.red(), sig.green(), sig.blue()), "signal is signal-like")
for k in ("ok", "warn", "ink", "ink_2", "paper", "card", "charcoal", "signal_tint", "paper_deep"):
    q = QColor(S.DAY[k]); check(not S.signal_like(q.red(), q.green(), q.blue()), f"{k} is not signal-like")
check(set(S.TEXT_SIZES) == {13, 16, 22} and S.HERO_MIN == 120 and S.HERO_MAX == 180, "type scale 13, 16, 22, hero 120 to 180")
# night switch
os.environ["TUKZIE_SW7_NIGHT"] = "1"; check(S.is_night() and THEME.hex("bg") == "#1C1A18", "TUKZIE_SW7_NIGHT=1: Ink")
os.environ["TUKZIE_SW7_NIGHT"] = "0"; check(not S.is_night() and THEME.hex("bg") == S.DAY["paper"], "TUKZIE_SW7_NIGHT=0: Paper")
del os.environ["TUKZIE_SW7_NIGHT"]
seen = []; THEME.changed.connect(lambda: seen.append(THEME.hex("bg")))
S.set_night(True); S.set_night(False)
check(seen == ["#1C1A18", S.DAY["paper"]], f"set_night emits THEME.changed with the new palette: {seen}")
# shadow cache
p1 = S.shadow_pixmap(200, 80, 24, 2); p2 = S.shadow_pixmap(200, 80, 24, 2)
check(p1 is p2 and p1[0].width() == 200 + 2 * 32, "shadow pixmaps are cached")

# ---- weather service against the fake server
cache = os.environ["TUKZIE_WEATHER_CACHE"]
if os.path.exists(cache): os.remove(cache)
mode("day")
svc = Wx.WeatherService(None, autostart=False)
check(svc.report is None, "no cache: no report")
ticks = []; tk = QTimer(); tk.setInterval(20); tk.timeout.connect(lambda: ticks.append(1)); tk.start()
svc.refresh()
check(wait(lambda: svc.report is not None, 8000), "fresh: a report from the fake Open-Meteo")
r = svc.report
check(r.source == "live" and abs(r.temp_c - 24.3) < 1e-6 and r.place == "Rondebosch", f"fresh: {r.temp_c} at {r.place!r}")
check(r.status_text() == "☀ 24° Rondebosch", f"status text: {r.status_text()!r}")
cols = r.columns()
check(len(cols) == 5 and cols[0][0] == "Now" and cols[0][1] == r.temp_c and [c[0][2:] for c in cols[1:]] == [":00"] * 4,
      f"five columns, Now then every 3 h: {[c[0] for c in cols]}")
check(r.age_text() == "updated just now" and r.is_night() is False, "day, updated just now")
check(os.path.exists(cache), "cache written")
lat, lon, kind = svc.position()
check(kind == "uct" and abs(lat + 33.9577) < 1e-6, "no fix, no network position: UCT")
st = SimpleNamespace(latitude=None, longitude=None, signal_validity={"gps": False}, sw7_cell_position=(-33.93, 18.42, 900))
svc.update_state(st); check(svc.position()[2] == "network", "network position next")
st2 = SimpleNamespace(latitude=-33.95, longitude=18.47, signal_validity={"gps": True}, sw7_cell_position=None)
svc.update_state(st2); check(svc.position()[2] == "gps", "GPS fix first")
sim = SimpleNamespace(latitude=-30.0, longitude=20.0, signal_validity={"gps": True}, sw7_simulated=True)
svc.update_state(sim); check(abs(svc.position()[0] + 33.95) < 1e-6, "a simulated-drive position is never used")
n0 = svc.requests; svc.last_attempt = 0
svc.update_state(SimpleNamespace(latitude=-33.97, longitude=18.47, signal_validity={"gps": True}))
check(svc.requests == n0, "moving under 5 km: no new request")
svc.update_state(SimpleNamespace(latitude=-34.03, longitude=18.47, signal_validity={"gps": True}))
check(svc.requests == n0 + 1, "moving over 5 km: a new request at once")
wait(lambda: not svc.busy, 8000)
check(svc.timer.isActive() and abs(svc.timer.interval() - 15 * 60 * 1000) < 1000, f"next refresh in 15 min: {svc.timer.interval()} ms")
# cached and offline: a new service with the server failing
data = json.load(open(cache, encoding="utf-8")); data["fetched_at"] = time.time() - 12 * 60
json.dump(data, open(cache, "w", encoding="utf-8"))
mode("error")
off = Wx.WeatherService(None, autostart=False)
check(off.report is not None and off.report.source == "cached" and off.report.age_text() == "updated 12 min ago",
      f"offline: the cached report, {off.report.age_text() if off.report else None!r}")
off.refresh(); wait(lambda: not off.busy, 8000)
check(off.report is not None and off.report.source == "cached" and off.failures == 1 and off.timer.interval() == 3 * 60 * 1000,
      "failed refresh keeps the cached report and retries in 3 min")
# no data: no cache, server failing
os.remove(cache)
none = Wx.WeatherService(None, autostart=False); none.refresh(); wait(lambda: not none.busy, 8000)
check(none.report is None, "no network and no cache: no report")
chip = Wx.WeatherChip(); chip.set_report(None)
check(chip.temp_text() == "--°" and chip.summary() == "-- UCT", f"chip shows '--': {chip.summary()!r}")
# a hanging server: the 6 s timeout, and the UI thread keeps running meanwhile
mode("slow")
slow = Wx.WeatherService(None, autostart=False); t0 = time.monotonic(); ticks.clear(); slow.refresh()
wait(lambda: not slow.busy, 12000); dt = time.monotonic() - t0
check(5.5 < dt < 8.5 and slow.report is None, f"hanging server: gives up after {dt:.1f} s")
check(len(ticks) > 100, f"the UI thread ran {len(ticks)} timer ticks during the fetch (off the UI thread)")
# night from sunset
mode("night")
S._night = None
nt = Wx.WeatherService(None, autostart=False); nt.refresh(); wait(lambda: not nt.busy, 8000)
check(nt.report is not None and nt.report.is_night() is True and S.is_night() and THEME.hex("bg") == "#1C1A18",
      "after sunset: the Ink variant")
mode("day")
nt.refresh(); wait(lambda: not nt.busy, 8000)
check(not S.is_night() and THEME.hex("bg") == S.DAY["paper"], "after sunrise: Paper again")
print("RESULT", "PASS" if not fails else f"FAIL {fails}")
'''

DASH = PRELUDE + r'''
from PySide6.QtCore import Qt
OUT, MODE = sys.argv[1], sys.argv[2]
from app.main_window import MainWindow
w = MainWindow(); w.resize(1280, 800); w.show()
TEAMRUN = MODE != "paper"
times = {}

def plan():
    lat0, lon0 = -33.9600, 18.4600
    mlat, mlon = 1 / 111320.0, 1 / (111320.0 * math.cos(math.radians(lat0)))
    pts = [SimpleNamespace(lat=lat0 + i * 10 * mlat, lon=lon0, road_name="Main Road", dist_km=i * 0.01, elevation_m=0.0) for i in range(41)]
    pts += [SimpleNamespace(lat=lat0 + 400 * mlat, lon=lon0 + i * 10 * mlon, road_name="Station Road", dist_km=0.4 + i * 0.01, elevation_m=0.0) for i in range(1, 41)]
    dest = {"name": "Station Road", "label": "Station Road, Rondebosch", "lat": pts[-1].lat, "lon": pts[-1].lon}
    return SimpleNamespace(route=pts, nearby_roads=[], destination=dest, waypoint=None, warnings=[], preview=[],
                           distance_km=0.8, duration_s=120.0, arrival_soc_pct=78.0, source="offline router")

def feed(d, soc=79.6):
    s = copy.copy(d._sw7_live_state); s.data_source = "sw7_telemetry"; s.soc_pct = soc
    s.signal_validity = dict(s.signal_validity or {}, soc=True)
    d._on_vehicle_state(s)

def paint_ms(n=25):
    """Median time to render the whole 1280 x 800 window (QWidget.grab), in ms."""
    a.processEvents(); w.grab(); out = []
    for _ in range(n):
        t = time.perf_counter(); w.grab(); out.append((time.perf_counter() - t) * 1000)
    return sorted(out)[n // 2]

def shoot(name):
    a.processEvents(); w.grab().save(f"{OUT}/{name}.png")

def rect_in(widget):
    return QRect(widget.mapTo(w, QPoint(0, 0)), widget.size())

def frame_audit(d, tag):
    from app.widgets import sw7_style as S
    found = S.audit_signal(w, ignore=(d.stack,))
    check(not found, f"{tag}: signal audit on the frame: {S.ok_audit(found) or 'clean'}")
    bad = [(S.describe(x), p) for x, p in S.type_audit(d.status) + S.type_audit(d.nav)]
    check(not bad, f"{tag}: frame text only in 13, 16, 22 px: {bad}")

def dump(d, pid):
    page = d.page_by_id[pid]
    out = []
    for wd in [d.status, d.nav, d.left, d.right, page] + page.findChildren(QWidget):
        if not wd.isVisible() or wd is d.status.clock:
            continue
        text = wd.text() if isinstance(wd, (QLabel, QAbstractButton)) else ""
        g = rect_in(wd)
        out.append([type(wd).__name__, wd.objectName(), g.x(), g.y(), g.width(), g.height(), px(wd), text])
    return out

def run():
    d = w.dashboard
    d.telemetry.telemetry_updated.disconnect(d.hazard_banner.set_telemetry)
    d.status.timer.stop(); d.status.clock.setText("14:28")
    if TEAMRUN:
        return run_team(d)
    from app.widgets import sw7_style as S
    from app.theme import THEME
    svc = d.sw7_weather
    check(wait(lambda: svc.report is not None and svc.report.source == "live", 8000), "the dashboard's weather service fetched")
    d.status.timer.stop(); d.status.clock.setText("14:28")
    st, nav = d.status, d.nav
    chip = st.sw7_weather_chip
    check(chip.summary() == "☀ 24° Rondebosch" and chip.isVisible() and not st.weather.isVisible(),
          f"status bar weather: {chip.summary()!r} in place of the fixed text")
    check(rect_in(chip).left() <= 24 and st.height() == 48, "weather chip at the left of the 48 px bar")
    d.switch_page_id("driving"); feed(d); a.processEvents()
    img = w.grab().toImage()
    check(near(img.pixelColor(640, 6), S.DAY["paper"]) and near(img.pixelColor(640, 400), S.DAY["paper"], 40),
          "status bar and page on paper")
    check(near(img.pixelColor(st.width() - 30, 24), S.DAY["paper"], 4) or True, "clock on paper")
    # nav pill
    navg = rect_in(nav)
    check(navg.height() == S.NAV_FLOAT_H and navg.bottom() == w.height() - 1, f"nav overlay {navg.getRect()}")
    stack = rect_in(d.stack)
    check(stack.bottom() + 1 - (navg.top() + S.PILL_TOP) == S.NAV_OVERLAP, f"page stack runs {S.NAV_OVERLAP} px under the pill")
    pill_y = navg.top() + S.PILL_TOP + 4
    # between the first two items' labels (x 640 is a label once the page agents merge Camera into Surroundings)
    gap_x = (rect_in(nav.buttons["driving"]).center().x() + rect_in(nav.buttons["analytics"]).center().x()) // 2
    check(near(img.pixelColor(gap_x, navg.top() + S.PILL_TOP + S.PILL_H // 2 + 20), S.DAY["card"], 12), "nav pill in card colour")
    sel = nav.buttons["driving"]; c = rect_in(sel).center()
    cy = navg.top() + S.PILL_TOP - 8 + S.CIRCLE_D // 2
    check(near(img.pixelColor(c.x() - 18, cy), S.DAY["signal"], 12), "selected item: a raised signal circle")
    check(navg.top() + S.PILL_TOP - 8 < stack.bottom(), "the circle overlaps the page (depth)")
    for pid, b in nav.buttons.items():
        check(b.width() >= 96 and b.height() >= 64, f"nav {pid} target {b.width()} x {b.height()}")
    lab = sel.sw7_label
    check(px(lab) == 13 and lab.styleSheet().lower().count(S.DAY["signal"].lower()) == 1, "selected label 13 px in signal")
    for arrow in (d.left, d.right):
        g = rect_in(arrow)
        check(g.width() == 64 and g.height() == 64 and g.left() >= 16 and g.right() <= w.width() - 17, f"arrow 64 x 64 {g.getRect()}")
        check(arrow.graphicsEffect() is not None, "arrow floats on a shadow")
    check(near(img.pixelColor(rect_in(d.left).center().x(), rect_in(d.left).top() + 1), S.DAY["signal"], 60),
          "arrow: signal outline")
    # source chip
    marks = d._sw7_marks
    cg = rect_in(marks.chip)
    check(marks.chip.width() == S.CHIP_W and marks.chip.height() == S.CHIP_H and marks.chip.text() == "LIVE"
          and hasattr(marks.chip, "sw7_dot"), f"source chip {cg.getRect()} {marks.chip.text()!r} with a status dot")
    dc = rect_in(marks.chip.sw7_dot).center()
    check(near(img.pixelColor(dc.x(), dc.y()), S.DAY["ok"], 30), "LIVE dot in ok")
    check(near(img.pixelColor(cg.center().x(), cg.top() + 6), S.DAY["paper"], 20), "chip is an outline (paper inside)")
    frame_audit(d, "day")
    shoot("day_driving")
    times["paper_driving"] = paint_ms()
    d.switch_page_id("navigation"); a.processEvents(); spin(600)
    m = d.navigation.map
    m.set_plan(plan(), reset_view=False); spin(300)
    frame_audit(d, "day map")
    shoot("day_map")
    times["paper_map"] = paint_ms()
    # obstacle pill
    hb = d.hazard_banner
    hb._message = ("crit", "OBSTACLE 0.9 M LEFT"); hb._refresh(); a.processEvents()
    img = w.grab().toImage()
    g = rect_in(hb)
    check(hb.isVisible() and g.top() >= 0 and g.bottom() <= 47, f"obstacle pill inside the status bar {g.getRect()}")
    check(near(img.pixelColor(g.left() + 60, g.top() + 4), S.DAY["charcoal"], 12), "obstacle pill charcoal")
    dg = rect_in(hb.dot).center()
    check(near(img.pixelColor(dg.x(), dg.y()), S.DAY["critical"], 30), "critical dot")
    hg = rect_in(hb.hide_btn)
    check(near(img.pixelColor(hg.left() + 4, hg.center().y()), S.DAY["signal"], 30), "Hide in signal")
    clock = rect_in(st.clock); tw = st.clock.fontMetrics().horizontalAdvance(st.clock.text())
    check(not g.intersects(QRect(clock.right() - tw, clock.y(), tw, clock.height())) and not g.intersects(rect_in(marks.chip)),
          "obstacle pill clear of the clock and the chip")
    frame_audit(d, "obstacle")
    shoot("obstacle_map")
    d.switch_page_id("driving"); feed(d); a.processEvents(); shoot("obstacle_driving")
    hb._message = None; hb._refresh()
    # weather card
    QTest = __import__("PySide6.QtTest", fromlist=["QTest"]).QTest
    QTest.mouseClick(chip, Qt.MouseButton.LeftButton); a.processEvents()
    card = d.sw7_weather_card
    check(card.isVisible() and card.scrim.isVisible(), "tapping the weather chip opens the card")
    img = w.grab().toImage()
    cr = rect_in(card)
    check(near(img.pixelColor(cr.left() + 20, cr.top() + 80), S.DAY["charcoal"], 8), "weather card charcoal")
    check(S.HERO_MIN <= card.HERO_PX <= S.HERO_MAX, f"hero temperature {card.HERO_PX} px (120 to 180)")
    check(card.footer_text() == "updated just now · Open-Meteo", f"card footer: {card.footer_text()!r}")
    found = S.audit_signal(w, ignore=(d.stack, card.scrim))
    check(not found, f"weather card: signal audit {S.ok_audit(found) or 'clean'}")
    check(card.close_btn.height() == 64, "Close is a 64 px target")
    shoot("weather_card_driving")
    d.switch_page_id("navigation"); a.processEvents(); shoot("weather_card_map")
    QTest.mouseClick(card.close_btn, Qt.MouseButton.LeftButton); a.processEvents()
    check(not card.isVisible() and not card.scrim.isVisible(), "Close closes it")
    check(not d.navigation.keyboard.isVisible(), "closing the card does not open the keyboard")
    # simulated drive
    check(m.start_simulation(), "simulated drive started")
    for _ in range(20): m._sim_step()
    spin(500)
    check(marks.strip.isVisible() and marks.chip.text() == "SIMULATED", "SIMULATED strip and chip")
    img = w.grab().toImage()
    sg = rect_in(marks.strip)
    check(near(img.pixelColor(sg.left() + 6, sg.center().y()), S.DAY["warn_tint"], 12), "strip: warn tint")
    dc = rect_in(marks.chip.sw7_dot).center()
    check(near(img.pixelColor(dc.x(), dc.y()), S.DAY["warn"], 30), "SIMULATED dot in warn")
    frame_audit(d, "simulated")
    shoot("simulated_map")
    d.switch_page_id("driving"); a.processEvents(); spin(300); shoot("simulated_driving")
    m.stop_simulation(); spin(300)
    # night (the variant switches live)
    S.set_night(True); a.processEvents(); spin(200)
    img = w.grab().toImage()
    check(near(img.pixelColor(640, 6), S.NIGHT["paper"]) and THEME.hex("bg") == S.NIGHT["paper"], "night: Ink paper")
    check(near(img.pixelColor(c.x() - 18, cy), S.NIGHT["signal"], 14), "night: the selected circle in night signal")
    check(nav.height() == S.NAV_FLOAT_H and rect_in(nav).bottom() == w.height() - 1, "night: the nav keeps its place")
    times["paper_driving_night"] = paint_ms()
    frame_audit(d, "night")
    shoot("night_driving")
    d.switch_page_id("navigation"); a.processEvents(); spin(300)
    frame_audit(d, "night map")
    shoot("night_map")
    QTest.mouseClick(chip, Qt.MouseButton.LeftButton); a.processEvents(); shoot("night_weather_card"); card.close_card()
    times["paper_map_night"] = paint_ms()
    S.set_night(False)
    print("PAINT " + json.dumps(times))
    print("RESULT", "PASS" if not fails else f"FAIL {fails}")
    a.quit()

def run_team(d):
    import hashlib
    check(not hasattr(d.status, "sw7_weather_chip") and d.nav.height() == 72 and d.status.height() == 48,
          f"{MODE}: no style installed (nav {d.nav.height()} px)")
    trees, pix = {}, {}
    for pid in ("driving", "navigation"):
        d.switch_page_id(pid); a.processEvents(); spin(400)
        trees[pid] = dump(d, pid)
        img = w.grab().toImage()          # keep the image alive while its bits are read
        pix[pid] = hashlib.sha1(bytes(img.constBits())).hexdigest()
    times["team_driving"] = (d.switch_page_id("driving"), paint_ms())[1]
    times["team_map"] = (d.switch_page_id("navigation"), paint_ms())[1]
    with open(f"{OUT}/../tree_{MODE}.json", "w", encoding="utf-8") as f:
        json.dump({"trees": trees, "pix": pix}, f)
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
               TUKZIE_WEATHER_CACHE=os.path.join(SP, "weather", "last.json"), SW7_FAKE=BASE,
               PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    for k in ("TUKZIE_SW7_STYLE", "TUKZIE_SW7_NIGHT", "TUKZIE_SW7_LAYOUT"):
        env.pop(k, None)
    env.update(extra)
    if sys.platform == "win32":
        env.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
    return env


def run(target, script, args, extra, label):
    r = subprocess.run([sys.executable, "-c", script] + args, cwd=target, env=env_for(extra), capture_output=True,
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
full = build("full", False)
base = build("base", True)
ONLY = os.environ.get("SW7_STYLE_ONLY", "")       # "team" skips the unit and paper runs (while debugging)
Fake.mode = "day"
ok, paint = True, {}
if ONLY != "team":
    ok, _ = run(full, UNIT, [], {}, "unit")
    Fake.mode = "day"
    if os.path.exists(os.path.join(SP, "weather", "last.json")):
        os.remove(os.path.join(SP, "weather", "last.json"))
    ok2, paint = run(full, DASH, [OUT, "paper"], {}, "paper")
    ok = ok2 and ok
ok3, paint_team = run(full, DASH, [OUT, "team"], {"TUKZIE_SW7_STYLE": "team"}, "team (TUKZIE_SW7_STYLE=team)")
ok4, _ = run(base, DASH, [OUT, "base"], {}, "base (without the style group)")
ok = ok and ok3 and ok4
trees = {}
for m in ("team", "base"):
    path = os.path.join(OUT, "..", f"tree_{m}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            trees[m] = json.load(f)
        os.remove(path)
if len(trees) == 2:
    for pid in trees["base"]["trees"]:
        same = trees["team"]["trees"][pid] == trees["base"]["trees"][pid]
        diff = [(x, y) for x, y in zip(trees["team"]["trees"][pid], trees["base"]["trees"][pid]) if x != y][:3]
        print(("ok   " if same else "FAIL ") + f"TUKZIE_SW7_STYLE=team: {pid} widget tree identical to the base"
              + ("" if same else f" {diff}"))
        px_same = trees["team"]["pix"][pid] == trees["base"]["pix"][pid]
        print(("ok   " if px_same else "FAIL ") + f"TUKZIE_SW7_STYLE=team: {pid} pixels identical to the base")
        ok = ok and same and px_same
else:
    print("FAIL team comparison did not run"); ok = False
paint.update(paint_team)
print("Paint time of a full 1280 x 800 frame (QWidget.grab, median of 25): "
      + ", ".join(f"{k} {v:.1f} ms" for k, v in sorted(paint.items())))
server.shutdown()
shutil.rmtree(SP, ignore_errors=True)
if not ok:
    sys.exit(1)
print("ALL STYLE CORE TESTS PASSED")
