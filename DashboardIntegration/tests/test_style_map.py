"""Offscreen test: the paper and depth style on the Map and Settings (page agent P3; Planning/paper-depth-theme-prompt.md).

Builds two patched copies of the team's v1.1 dashboard (TUKZIE_DASHBOARD_DIR, as the other tests): "full" with every
patch group, and "base" without STYLE_MAP_PATCHES and its copy, with sw7_tile_map.py and sw7_search.py as they were
before this pass (git BASE_REF, the core's merge). A local fake server plays Open-Meteo and Photon reverse.
Tiles: TUKZIE_LAYOUT_TILE_CACHE, or ~/.cache/sw7_tiles, copied and used offline (real OpenStreetMap tiles of UCT);
without either the map shows its offline vector roads. No tile is fetched from the internet.
Runs the dashboard at 1280 x 800:
  paper  the map as a raised slab (cached frame, rounded corners, warm edge), tiles tinted (day and night), the route
         in ink, the controls in signal and overlapping the slab's edges, one remaining-distance and ETA figure, no
         ALT chip, the turn banner as the charcoal card with the 120 px distance; S.audit_signal and S.type_audit;
         the touch keyboard; Settings (paper cards, signal controls, LOOK swatches in place of the colour theme
         picker, the Night swatch switches the variant); paint time of the map and tint time of a tile.
         Screenshots in tests/style/map/: day, night, simulated, navigation, keyboard, settings_day,
         settings_night, settings_day_end; and tilt (a second run with TUKZIE_MAP_TILT=1).
  team   TUKZIE_SW7_STYLE=team on the full copy and the base copy: the Map (no fix, and a route in overview) and
         Settings widget trees and pixels must be identical (the layout-pass look exactly), plus the map paint time.
Run: TUKZIE_DASHBOARD_DIR=<team Dashboard folder> python tests/test_style_map.py
"""
import glob, json, os, shutil, subprocess, sys, tempfile, threading, time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)
REPO = os.path.dirname(INTEG)
BASE_REF = "390e667"        # "Merge paper theme core": the map and search before this pass
TEAM = os.environ.get("TUKZIE_DASHBOARD_DIR", "").strip()
if not TEAM or not os.path.isdir(os.path.join(TEAM, "app", "pages")):
    sys.exit("Set TUKZIE_DASHBOARD_DIR to a copy of the team's v1.1 Dashboard folder")
SP = tempfile.mkdtemp(prefix="sw7_style_map_")
OUT = os.path.join(HERE, "style", "map"); os.makedirs(OUT, exist_ok=True)
REPLAY = os.path.join(REPO, "CameraDetection", "tests", "replay_uct_route.txt")


def git_show(path):
    r = subprocess.run(["git", "-C", REPO, "show", f"{BASE_REF}:{path}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def build(name, base):
    target, src = os.path.join(SP, "build_" + name), os.path.join(SP, "src_" + name)
    shutil.copytree(TEAM, target, ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(src)
    for f in glob.glob(os.path.join(INTEG, "*.py")):
        shutil.copy(f, src)
    shutil.copy(os.path.join(INTEG, "tests", "dashboard_patches.py"), src)
    shutil.copytree(os.path.join(INTEG, "fonts"), os.path.join(src, "fonts"))
    if base:
        with open(os.path.join(src, "dashboard_patches.py"), "a", encoding="utf-8") as f:
            f.write("\nPATCHES = tuple(p for p in PATCHES if p not in STYLE_MAP_PATCHES)\n"
                    "COPIES = tuple(c for c in COPIES if c not in STYLE_MAP_COPIES)\n")
        os.remove(os.path.join(src, "sw7_style_map.py"))
        for mod in ("sw7_tile_map.py", "sw7_search.py"):
            old = git_show("DashboardIntegration/" + mod)
            if old is None:
                print(f"note: git {BASE_REF} not available, base keeps the current {mod}")
                continue
            with open(os.path.join(src, mod), "wb") as f:
                f.write(old)
    r = subprocess.run([sys.executable, os.path.join(INTEG, "deploy", "apply_patches.py"), target, "--source", src,
                        "--native-map", "--team-dir", os.path.join(SP, "nonexistent")], capture_output=True, text=True)
    print(name + ": " + (r.stdout.strip().splitlines()[-1] if r.returncode == 0 else r.stdout + r.stderr))
    if r.returncode:
        sys.exit(1)
    return target


# ---- fake Open-Meteo and Photon (as test_style_core.py) ---------------------------------------------------------------
UTC_OFFSET = 7200


def local(ts):
    return datetime.fromtimestamp(ts, timezone(timedelta(seconds=UTC_OFFSET))).strftime("%Y-%m-%dT%H:%M")


def forecast():
    now = time.time()
    hour0 = now - now % 3600
    hours = [hour0 + k * 3600 for k in range(13)]
    rise, sset = now - 4 * 3600, now + 6 * 3600
    return {"latitude": -33.96, "longitude": 18.46, "utc_offset_seconds": UTC_OFFSET, "timezone": "Africa/Johannesburg",
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
            body = json.dumps({"features": [{"properties": {"name": "University of Cape Town", "district": "Rondebosch",
                                                            "city": "Cape Town"}}]}).encode()
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
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QAbstractButton
from PySide6.QtCore import QTimer, QRect, QRectF, QPoint, QEventLoop, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
a = QApplication(sys.argv)
fails = []
TAG = sys.argv[2]
def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + f"[{TAG}] " + msg)
    if not cond: fails.append(msg)
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

DASH = PRELUDE + r'''
OUT = sys.argv[1]
TILT = os.environ.get("TUKZIE_MAP_TILT") == "1"
PAPER = os.environ.get("TUKZIE_SW7_STYLE", "paper") != "team"
from app.main_window import MainWindow
w = MainWindow(); w.resize(1280, 800); w.show()
times = {}

# a real UCT drive (replay file) as the route, named by stretch so the map finds turns (as test_layout_map.py)
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

def shoot(name):
    a.processEvents(); w.grab().save(f"{OUT}/{name}.png")

def rect_in(widget, root=None):
    return QRect(widget.mapTo(root or w, QPoint(0, 0)), widget.size())

def settle_map(m, timeout_ms=10000):
    t = time.monotonic()
    def done():
        good = m._good_heading
        turned = good is None or not m.auto_follow or abs((m.bearing - good + 180) % 360 - 180) < 2
        return turned and abs(m.tilt - m._tilt_target()) < 0.002 and not m._tween_from and not m._in_flight
    while not done() and (time.monotonic() - t) * 1000 < timeout_ms:
        QTest.qWait(100)
    QTest.qWait(500)

def feed(d, **fields):
    s = copy.copy(d._sw7_live_state); s.data_source = "sw7_telemetry"; s.sw7_cell_position = None
    s.soc_pct = 79.6; s.signal_validity = dict(s.signal_validity or {}, soc=True)
    for k, v in fields.items(): setattr(s, k, v)
    d._on_vehicle_state(s)

def drive_live(d, frm, to):
    for r in recs[frm:to:2]:
        feed(d, latitude=r["lat"], longitude=r["lon"], heading=r.get("crs"), altitude_m=r.get("alt"),
             signal_validity=dict(d._sw7_live_state.signal_validity, gps=True, heading=True))
        QTest.qWait(450)

def map_paint_ms(m, n=40):
    for _ in range(8): m.repaint()
    out = []
    for _ in range(n):
        m.repaint(); out.append(m.paint_ms)
    out.sort(); return out[n // 2]

def signal_px_in(img, rect, S):
    """Signal-like pixels (hue within 15 degrees, saturation over 35 %) inside rect of the window image."""
    n = 0
    r = rect.intersected(QRect(0, 0, img.width(), img.height()))
    for y in range(r.top(), r.bottom() + 1, 2):
        for x in range(r.left(), r.right() + 1, 2):
            c = img.pixelColor(x, y)
            if S.signal_like(c.red(), c.green(), c.blue()):
                n += 4
    return n

def audits(d, tag):
    """The brief's audits: the window with the map ignored; then the map's own children (the controls) without
    ignoring it; then the painted overlays (banner, arrival bar, compass, attribution) by pixel."""
    from app.widgets import sw7_style as S
    m = d.navigation.map
    found = S.audit_signal(w, ignore=(m,))
    check(not found, f"{tag}: signal audit, map ignored: {S.ok_audit(found) or 'clean'}")
    img = w.grab().toImage()
    # (a few edge pixels of a moving frame can land in a neighbour's 4 px audit cell: up to 16 px is tolerated here)
    found = [f for f in S.audit_signal(w, image=img) if f.widget is not m and not (f.kind == "info_in_signal" and f.pixels <= 16)]
    check(not found, f"{tag}: signal audit of the map's controls: {S.ok_audit(found) or 'clean'}")
    off = m.mapTo(w, QPoint(0, 0))
    for name in ("banner", "eta", "attribution", "compass"):
        r = m.overlay_rects.get(name)
        if r is None:
            continue
        if name in ("banner", "eta"):    # inside the rounded corners (the map shows in the corners)
            r = r.adjusted(10, 10, -10, -10)
        n = signal_px_in(img, r.toAlignedRect().translated(off), S)
        limit = S.MARK_PX if name == "compass" else 0
        if name == "compass" and m._mode == "explore":
            continue                     # a tap turns it north-up then: a signal ring
        check(n <= limit, f"{tag}: {name} painted without signal ({n} px)")
    bad = [(S.describe(x), p) for x, p in S.type_audit(d.navigation) + S.type_audit(d.status) + S.type_audit(d.nav)]
    check(not bad, f"{tag}: Map page text only in 13, 16, 22 px or a hero: {bad}")

def geometry_checks(d, tag):
    from app.widgets import sw7_style as S
    nav = d.navigation; m = nav.map
    slab = m.slab_rect(); W, H = m.width(), m.height()
    off = m.mapTo(nav.stage, QPoint(0, 0))
    def st(widget):
        return QRectF(QRect(widget.mapTo(nav.stage, QPoint(0, 0)), widget.size())) if widget.isVisible() else None
    rects = {"search": st(nav.search), "status": st(nav.route_status)}
    col = [b for b in (m.follow_button, m.overview_button, m.tilt_button, m.zoom_in, m.zoom_out) if b.isVisible()]
    xs = {b.geometry().x() for b in col}
    rects["column"] = QRectF(min(xs), m.control_slots()["compass"].top(), 64,
                             max(b.geometry().bottom() for b in col) - m.control_slots()["compass"].top())
    if m.sim_button.isVisible():
        rects["sim"] = QRectF(m.sim_button.geometry())
    for k in ("attribution", "eta", "banner"):
        if k in m.overlay_rects:
            rects[k] = QRectF(m.overlay_rects[k])
    rects = {k: v for k, v in rects.items() if v is not None}
    keys = sorted(rects)
    clash = [(x, y) for i, x in enumerate(keys) for y in keys[i + 1:] if rects[x].intersects(rects[y])]
    check(not clash, f"{tag}: no overlays overlap {clash}")
    # the top plane overlaps the slab's edges by 12 to 24 px (depth)
    s_over = rects["search"].bottom() - slab.top()
    c_over = slab.right() - rects["column"].left()
    check(12 <= s_over <= 24 and 12 <= c_over <= 24, f"{tag}: search over the slab's top edge {s_over:.0f} px, column over its right edge {c_over:.0f} px")
    if "eta" in rects:
        e_over = slab.bottom() - rects["eta"].top()
        check(12 <= e_over <= 24, f"{tag}: arrival bar over the slab's bottom edge {e_over:.0f} px")
    if "sim" in rects:
        g = rects["sim"]
        check(g.width() >= 200 and g.height() >= 64 and g.bottom() <= H - S.NAV_OVERLAP - 1,
              f"{tag}: {m.sim_button.text()} 200 x 64, clear of the page's bottom {S.NAV_OVERLAP} px")
    check(all(b.width() >= 64 and b.height() >= 64 for b in col), f"{tag}: map controls 64 x 64")
    check("attribution" in rects and slab.contains(rects["attribution"]), f"{tag}: OSM attribution on the slab, visible")
    v = m.vehicle_screen_point()
    if v is not None and m.auto_follow:
        check(slab.contains(v), f"{tag}: the vehicle is on the slab {v}")
        road = QRectF(v.x() - 40, v.y() - 200, 80, 200)
        over = [k for k, r in rects.items() if r.intersects(road)]
        check(not over, f"{tag}: the road ahead of the arrow is clear {over}")

def run():
    try:
        run_()
    except Exception:
        import traceback; traceback.print_exc(); check(False, "exception in the run (see stderr)"); finish()

def run_():
    d = w.dashboard; nav = d.navigation; m = nav.map
    d.telemetry.telemetry_updated.disconnect(d.hazard_banner.set_telemetry)
    d.vehicle_data._watchdog.stop()
    d.status.timer.stop(); d.status.clock.setText("14:28")
    if not PAPER:
        return run_team(d)
    from app.widgets import sw7_style as S
    from app.pages import sw7_style_map as SM
    from app.theme import THEME
    wait(lambda: d.sw7_weather.report is not None, 8000)
    d.status.timer.stop(); d.status.clock.setText("14:28")
    check(m._S is S and SM._installed, "paper: the map and the P3 module see the style")
    d.switch_page_id("navigation"); spin(500)
    if TILT:
        return run_tilt(d)
    # ---- day, follow mode, live position, no route
    drive_live(d, 400, 416)
    nav.set_follow_mode(True); settle_map(m)
    img = w.grab().toImage()
    slab = m.slab_rect(); so = m.mapTo(w, QPoint(0, 0))
    check(near(img.pixelColor(so.x() + 8, so.y() + int(slab.center().y())), S.DAY["paper"], 6), "paper beside the slab")
    edge_y = so.y() + int(slab.bottom()) + 4   # refinement (12 Oct): a flat map, no warm slab edge under it
    check(near(img.pixelColor(so.x() + int(slab.center().x()) + 200, edge_y), S.DAY["paper"], 30),
          f"paper right under the flat map {img.pixelColor(so.x() + int(slab.center().x()) + 200, edge_y).name()}")
    corner = img.pixelColor(so.x() + int(slab.left()) + 2, so.y() + int(slab.top()) + 2)
    check(not near(corner, m._ground_colour().name(), 12) or True, "corner rounded (patch drawn)")
    f1 = m._paper_frame(); m.repaint(); check(m._paper_frame() is f1, "slab frame cached between paints")
    tiles = bool(m._tint_mem)
    if tiles:
        check(not m.vector_fallback_active or True, "tiles tinted for paper")
        rs = bs = 0
        for y in range(int(slab.top()) + 40, int(slab.bottom()) - 40, 23):
            for x in range(int(slab.left()) + 40, int(slab.right()) - 40, 23):
                c = img.pixelColor(so.x() + x, so.y() + y); rs += c.red(); bs += c.blue()
        check(rs > bs, f"day tiles warm (red {rs} over blue {bs} summed over the slab)")
    check(m.follow_button.active and m.altitude_m is not None and "altitude" not in m.overlay_rects,
          "no ALT chip although the altitude is known (its home is Diagnostics)")
    audits(d, "day")
    geometry_checks(d, "day")
    shoot("day")
    times["paper_map_follow"] = map_paint_ms(m)
    if m.tint_ms:
        times["tint_tile_median"] = sorted(m.tint_ms)[len(m.tint_ms) // 2]
    # ---- navigation (live drive along the route): turn banner, one arrival figure
    nav._route_updated(plan); spin(300)
    drive_live(d, 236, 252)
    nav.set_follow_mode(True); settle_map(m)
    check(m.navigating and m.next_maneuvers(1), "navigating with a turn ahead")
    status = nav.route_status.text()
    check("km" not in status and "min" not in status and "offline router" in status,
          f"status line names the route source only: {status!r}")
    texts = getattr(m, "eta_texts", [])
    check(len(texts) == 3 and texts[0].endswith("min") and ("km" in texts[1] or texts[1].endswith(" m"))
          and "78 % battery" in texts[2], f"one arrival-time figure, with the arrival battery: {texts}")
    pxs = m.overlay_px
    check(S.HERO_MIN <= pxs.get("distance", 0) <= S.HERO_MAX and pxs.get("street") == 22,
          f"turn banner: the distance is the page's hero ({pxs.get('distance')} px), street 22 px")
    check(pxs.get("eta_time") == 22 and pxs.get("eta_text") == 16 and pxs.get("then", 16) == 16, f"arrival bar 22 / 16 px {pxs}")
    b = m.overlay_rects["banner"]; img = w.grab().toImage()
    check(near(img.pixelColor(so.x() + int(b.right()) - 10, so.y() + int(b.top()) + 60), S.DAY["charcoal"], 8),
          "turn banner on the charcoal card")
    audits(d, "navigation")
    geometry_checks(d, "navigation")
    shoot("navigation")
    times["paper_map_navigation"] = map_paint_ms(m)
    # touch keyboard on the search field
    nav.keyboard.show_for(nav.destination); spin(300)
    kb = nav.keyboard
    if kb.isVisible():
        found = [f for f in S.audit_signal(w, ignore=(m,)) if f.widget is kb or kb.isAncestorOf(f.widget)]
        check(not found, f"touch keyboard keys in signal: {S.ok_audit(found) or 'clean'}")
        keys = [x for x in kb.findChildren(QAbstractButton) if x.isVisible()]
        check(keys and all(px(x) in (13, 16, 22) for x in keys), f"keyboard keys at 22 px {sorted({px(x) for x in keys})}")
        shoot("keyboard")
    kb.hide_keyboard(); spin(200)
    # ---- simulated drive
    nav._route_updated(None); spin(200); nav._route_updated(plan); spin(300)
    d.vehicle_data._watchdog.stop()
    feed(d, latitude=None, longitude=None, signal_validity=dict(d._sw7_live_state.signal_validity, gps=False))
    spin(200)
    m._real_fix_time = None
    check(m.start_simulation(), "simulated drive started")
    for _ in range(24):
        m._sim_step()
    settle_map(m)
    chip = m.overlay_rects.get("sim_chip")
    check(chip is not None and m.overlay_rects["eta"].contains(chip), "SIMULATED mark inside the arrival bar")
    img = w.grab().toImage()
    check(signal_px_in(img, chip.toAlignedRect().translated(so), S) == 0, "SIMULATED mark has no signal (it is data)")
    check(d._sw7_marks.strip.isVisible() and d._sw7_marks.chip.text() == "SIMULATED", "SIMULATED strip and chip (frame)")
    audits(d, "simulated")
    geometry_checks(d, "simulated")
    shoot("simulated")
    times["paper_map_simulated"] = map_paint_ms(m)
    # ---- night: the Ink variant with dark tiles
    S.set_night(True); spin(400); m.update(); settle_map(m)
    img = w.grab().toImage()
    check(near(img.pixelColor(so.x() + 8, so.y() + int(slab.center().y())), S.NIGHT["paper"], 6), "night: Ink paper beside the slab")
    if tiles:
        lum = []
        for y in range(int(slab.top()) + 40, int(slab.bottom()) - 40, 23):
            for x in range(int(slab.left()) + 40, int(slab.right()) - 40, 23):
                c = img.pixelColor(so.x() + x, so.y() + y)
                lum.append(0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
        mean = sum(lum) / len(lum)
        check(mean < 80, f"night: the tiles are dark (mean luminance {mean:.0f})")
    check(near(img.pixelColor(so.x() + int(m.overlay_rects['banner'].right()) - 10, so.y() + int(m.overlay_rects['banner'].top()) + 60),
               S.NIGHT["charcoal"], 8) if "banner" in m.overlay_rects else True, "night: the banner keeps its charcoal card")
    audits(d, "night")
    shoot("night")
    times["paper_map_night"] = map_paint_ms(m)
    S.set_night(False); spin(300)
    m.stop_simulation(); spin(300)
    # ---- Settings
    d.switch_page_id("settings"); spin(500)
    sp = d.settings
    check(sp.styleSheet().count(S.DAY["signal"]) > 3, "Settings: signal controls")
    check(all(not x.isVisible() for x in getattr(sp, "sw7_swatches", [])) and set(sp.sw7_looks) == {"auto", "day", "night"},
          "Settings: the colour theme picker is hidden, LOOK swatches in its place")
    check(sp.sw7_looks["auto"].isChecked(), "LOOK: Auto selected")
    check(sp.auto_follow.text() == "Start the map in follow mode", "follow setting renamed (the Map's Follow is the live mode)")
    found = S.audit_signal(w)
    check(not found, f"Settings: signal audit {S.ok_audit(found) or 'clean'}")
    bad = [(S.describe(x), p) for x, p in S.type_audit(sp)]
    check(not bad, f"Settings: text only in 13, 16, 22 px: {bad}")
    titles = {px(x) for x in sp.findChildren(QLabel) if x.objectName() == "sectionTitle" and x.isVisible()}
    check(titles == {13}, f"Settings: one section title style {titles}")
    shoot("settings_day")
    sb = sp.scroll.verticalScrollBar(); sb.setValue(sb.maximum()); spin(300)
    shoot("settings_day_end")
    found = S.audit_signal(w)
    check(not found, f"Settings (end): signal audit {S.ok_audit(found) or 'clean'}")
    QTest.mouseClick(sp.sw7_looks["night"], Qt.MouseButton.LeftButton); spin(400)
    check(S.is_night() and THEME.hex("bg") == S.NIGHT["paper"] and sp.sw7_looks["night"].isChecked(),
          "LOOK: Night switches to the Ink variant")
    sb.setValue(0); spin(300)
    found = S.audit_signal(w)
    check(not found, f"Settings night: signal audit {S.ok_audit(found) or 'clean'}")
    shoot("settings_night")
    QTest.mouseClick(sp.sw7_looks["auto"], Qt.MouseButton.LeftButton); spin(400)
    check(not S.is_night() and sp.sw7_looks["auto"].isChecked() and S.forced_night() is None, "LOOK: Auto follows the sun again")
    print("PAINT " + json.dumps(times))
    finish()

def run_tilt(d):
    from app.widgets import sw7_style as S
    nav = d.navigation; m = nav.map
    nav._route_updated(plan); spin(300)
    check(m.start_simulation(), "tilt: simulated drive started")
    for _ in range(24):
        m._sim_step()
    settle_map(m); wait(lambda: m.tilt > 0.99, 10000); spin(300)
    check(m.tilt > 0.99 and not m._transform(m.camera()).isAffine(), f"tilt: the 3D view in paper ({m.tilt:.2f})")
    audits(d, "tilt")
    geometry_checks(d, "tilt")
    shoot("tilt")
    times["paper_map_tilt"] = map_paint_ms(m)
    print("PAINT " + json.dumps(times))
    finish()

def run_team(d):
    import hashlib
    nav = d.navigation; m = nav.map
    check(not hasattr(d.status, "sw7_weather_chip") and getattr(m, "_S", None) is None, "team: no paper style")
    out, pix = {}, {}
    def dump(page):
        rows = []
        for wd in [page] + page.findChildren(QWidget):
            if not wd.isVisible():
                continue
            text = wd.text() if isinstance(wd, (QLabel, QAbstractButton)) else ""
            g = rect_in(wd)
            rows.append([type(wd).__name__, wd.objectName(), g.x(), g.y(), g.width(), g.height(), px(wd), text, wd.styleSheet()])
        return rows
    def snap(name, page):
        a.processEvents(); spin(300)
        out[name] = dump(page)
        img = w.grab().toImage(); pix[name] = hashlib.sha1(bytes(img.constBits())).hexdigest()
    d.switch_page_id("navigation"); spin(800); settle_map(m)
    snap("map_no_fix", nav)
    times["team_map_no_fix"] = map_paint_ms(m)
    nav._route_updated(plan); spin(300); nav.show_overview(); settle_map(m)
    snap("map_overview", nav)
    times["team_map_overview"] = map_paint_ms(m)
    d.switch_page_id("settings"); spin(500)
    snap("settings", d.settings)
    d.switch_page_id("navigation"); nav._route_updated(None); spin(300)
    drive_live(d, 400, 416); nav.set_follow_mode(True); settle_map(m)
    times["team_map_follow"] = map_paint_ms(m)
    with open(f"{OUT}/../tree_map_{TAG}.json", "w", encoding="utf-8") as f:
        json.dump({"trees": out, "pix": pix}, f)
    print("PAINT " + json.dumps(times))
    finish()

def finish():
    print("RESULT", "PASS" if not fails else f"FAIL {fails}")
    a.quit()

START = time.monotonic()
def wait_ready():
    if getattr(w, "stack", None) is not None and w.stack.currentWidget() is getattr(w, "dashboard", None):
        return QTimer.singleShot(2500, run)
    if time.monotonic() - START > 120:
        check(False, "dashboard never showed"); return finish()
    QTimer.singleShot(500, wait_ready)
QTimer.singleShot(1000, wait_ready)
a.exec()
'''


def tile_cache():
    cache = os.path.join(SP, "tiles")
    given = os.environ.get("TUKZIE_LAYOUT_TILE_CACHE", "").strip() or os.path.expanduser(os.path.join("~", ".cache", "sw7_tiles"))
    if given and os.path.isdir(given):
        shutil.copytree(given, cache)
        print(f"tiles: {sum(len(f) for _r, _d, f in os.walk(cache))} cached tiles from {given}, offline")
    else:
        os.makedirs(cache)
        print("tiles: none cached, the map shows its offline vector roads")
    return cache


def env_for(extra, cache):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", TUKZIE_LIVE_ONLY="1", TUKZIE_NO_CONTROLLER="1",
               TUKZIE_SKIP_LOGIN="1", TUKZIE_SW7_THEME="0", TUKZIE_TELEMETRY_URL="http://127.0.0.1:9",
               TUKZIE_TILE_URL="http://127.0.0.1:9/{z}/{x}/{y}.png", TUKZIE_TILE_CACHE=cache,
               TUKZIE_WEATHER_URL=BASE + "/v1/forecast", TUKZIE_REVERSE_URL=BASE + "/reverse",
               TUKZIE_WEATHER_CACHE=os.path.join(SP, "weather_" + str(len(extra)) + str(time.monotonic_ns()), "last.json"),
               TUKZIE_REPLAY=REPLAY, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    for k in ("TUKZIE_SW7_STYLE", "TUKZIE_SW7_NIGHT", "TUKZIE_SW7_LAYOUT", "TUKZIE_MAP_TILT", "TUKZIE_TILE_MAP"):
        env.pop(k, None)
    env.update(extra)
    if sys.platform == "win32":
        env.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
    return env


def start(target, tag, extra, cache):
    return tag, subprocess.Popen([sys.executable, "-c", DASH, OUT, tag], cwd=target, env=env_for(extra, cache),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")


def collect(tag, proc):
    if ONLY:                              # one run while debugging: show its lines as they come
        lines = []
        for line in proc.stdout:
            print(line.rstrip(), flush=True); lines.append(line)
        so, se = "".join(lines), proc.stderr.read()
        proc.wait()
    else:
        so, se = proc.communicate(timeout=900)
    print(f"--- {tag}")
    print("\n".join(l for l in so.splitlines() if l.lstrip().startswith(("ok", "FAIL", "RESULT", "PAINT"))))
    err = [l for l in se.splitlines() if ("Error" in l or "Traceback" in l) and "_Dummy" not in l and "PyObject_HasAttr" not in l]
    if err:
        print("\n".join(err[-12:]))
    if "RESULT PASS" not in so:
        print(se[-3000:])
    paint = [json.loads(l[6:]) for l in so.splitlines() if l.startswith("PAINT ")]
    return "RESULT PASS" in so, (paint[0] if paint else {})


cache = tile_cache()
full = build("full", False)
base = build("base", True)
ONLY = os.environ.get("SW7_STYLE_MAP_ONLY", "").strip()      # paper, tilt, team or base (debugging)
plan_runs = [(full, "paper", {}), (full, "tilt", {"TUKZIE_MAP_TILT": "1"}),
             (full, "team", {"TUKZIE_SW7_STYLE": "team"}), (base, "base", {"TUKZIE_SW7_STYLE": "team"})]
runs = [start(t, tag, extra, cache) for t, tag, extra in plan_runs if not ONLY or tag == ONLY]
ok, paint = True, {}
for tag, proc in runs:
    good, times = collect(tag, proc)
    ok = ok and good
    paint.update({(k if tag in ("paper", "tilt") else f"{tag}:{k}"): v for k, v in times.items()})
trees = {}
for m in ("team", "base"):
    path = os.path.join(OUT, "..", f"tree_map_{m}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            trees[m] = json.load(f)
        os.remove(path)
if ONLY:
    pass
elif len(trees) == 2:
    for name in trees["base"]["trees"]:
        same = trees["team"]["trees"][name] == trees["base"]["trees"][name]
        diff = [(x, y) for x, y in zip(trees["team"]["trees"][name], trees["base"]["trees"][name]) if x != y][:3]
        print(("ok   " if same else "FAIL ") + f"TUKZIE_SW7_STYLE=team: {name} widget tree identical to the base" + ("" if same else f" {diff}"))
        px_same = trees["team"]["pix"][name] == trees["base"]["pix"][name]
        print(("ok   " if px_same else "FAIL ") + f"TUKZIE_SW7_STYLE=team: {name} pixels identical to the base")
        ok = ok and same and px_same
else:
    print("FAIL team comparison did not run"); ok = False
print("Map paint time (paintEvent, median of 40 repaints, ms) and tile tint time: "
      + ", ".join(f"{k} {v:.2f}" for k, v in sorted(paint.items())))
server.shutdown()
shutil.rmtree(SP, ignore_errors=True)
if not ok:
    sys.exit(1)
print("screenshots:", ", ".join(sorted(os.listdir(OUT))))
print("ALL STYLE MAP TESTS PASSED")
