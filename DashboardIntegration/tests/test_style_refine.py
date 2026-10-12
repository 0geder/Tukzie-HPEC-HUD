"""Offscreen test: the UI theme refinement (Planning/ui-theme-refinement-prompt.md, "change the skin, not the product").

Builds a patched copy of the team's v1.1 dashboard (TUKZIE_DASHBOARD_DIR, as the other tests) with every patch group. A
local fake server plays Open-Meteo and Photon reverse (never the real APIs); telemetry, a live vehicle state and camera
alerts are fed to the dashboard directly (made-up test values). Real OSM tiles are used only from a local cache
(TUKZIE_LAYOUT_TILE_CACHE or ~/.cache/sw7_tiles, copied; nothing is downloaded). Runs:
  paper  the 7 pages, day and night, at 1280 x 800: IBM Plex Sans and Mono registered and used (Mono on telemetry
         values, diagnostics, coordinates and timestamps), the status-bar weather unboxed (no border, no fill) and still
         opening the weather card, with its unavailable state; on every page no clipped labels, nothing tappable under
         the nav bar, 64 px touch targets, the signal audit and the type audit; Charging's battery animation (bubbles
         and the spinning arc) running while the page is shown and stopped when it is not, with its paint time; the
         unavailable states (no data) never shown as zero. Screenshots: tests/style/refine/<prefix>_<day|night>_<page>.png
  team   TUKZIE_SW7_STYLE=team: the widget tree of every page (and the pixels of the static pages) must equal
         tests/style/refine/team_reference.json, recorded from the build before this refinement.
Environment: SW7_REFINE_PREFIX (default "after"; "before" for the baseline shots), SW7_REFINE_SHOTS_ONLY=1 (screenshots
without the checks, for the baseline), SW7_REFINE_WRITE_TEAM=1 (record team_reference.json), SW7_REFINE_ONLY=paper|team.
Run: TUKZIE_DASHBOARD_DIR=<team Dashboard folder> python tests/test_style_refine.py
"""
import glob, json, os, shutil, subprocess, sys, tempfile, threading, time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)
REPO = os.path.dirname(INTEG)
TEAM = os.environ.get("TUKZIE_DASHBOARD_DIR", "").strip()
if not TEAM or not os.path.isdir(os.path.join(TEAM, "app", "pages")):
    sys.exit("Set TUKZIE_DASHBOARD_DIR to a copy of the team's v1.1 Dashboard folder")
SP = tempfile.mkdtemp(prefix="sw7_style_refine_")
OUT = os.path.join(HERE, "style", "refine"); os.makedirs(OUT, exist_ok=True)
REFERENCE = os.path.join(OUT, "team_reference.json")
PREFIX = os.environ.get("SW7_REFINE_PREFIX", "after").strip() or "after"
SHOTS_ONLY = os.environ.get("SW7_REFINE_SHOTS_ONLY", "") == "1"
REPLAY = os.path.join(REPO, "CameraDetection", "tests", "replay_uct_route.txt")


def build(name):
    target, src = os.path.join(SP, "build_" + name), os.path.join(SP, "src_" + name)
    shutil.copytree(TEAM, target, ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(src)
    for f in glob.glob(os.path.join(INTEG, "*.py")):
        shutil.copy(f, src)
    shutil.copy(os.path.join(INTEG, "tests", "dashboard_patches.py"), src)
    shutil.copytree(os.path.join(INTEG, "fonts"), os.path.join(src, "fonts"))
    r = subprocess.run([sys.executable, os.path.join(INTEG, "deploy", "apply_patches.py"), target, "--source", src,
                        "--native-map", "--team-dir", os.path.join(SP, "nonexistent")], capture_output=True, text=True)
    print(name + ": " + (r.stdout.strip().splitlines()[-1] if r.returncode == 0 else r.stdout + r.stderr))
    if r.returncode:
        sys.exit(1)
    return target


def tile_cache():
    cache = os.path.join(SP, "tiles")
    given = os.environ.get("TUKZIE_LAYOUT_TILE_CACHE", "").strip() or os.path.expanduser(os.path.join("~", ".cache", "sw7_tiles"))
    if given and os.path.isdir(given):
        shutil.copytree(given, cache)
    else:
        os.makedirs(cache)
    return cache


# ---- fake Open-Meteo and Photon (as test_style_core) -------------------------------------------------------------------
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
            "hourly": {"time": [local(h) for h in hours], "temperature_2m": [24, 24, 23, 22, 21, 20, 19, 18, 17, 17, 16, 16, 15],
                       "weather_code": [0, 0, 1, 1, 2, 2, 3, 3, 2, 1, 0, 0, 0]},
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

DASH = r'''
import sys, types, os, time, json, copy, math, hashlib, faulthandler
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
from PySide6.QtCore import QTimer, QRect, QPoint, QEventLoop, Qt, QByteArray, QBuffer, QIODevice, QRectF
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QFontMetricsF, QLinearGradient, QPen, QFontDatabase, QFontInfo
from PySide6.QtTest import QTest
a = QApplication(sys.argv)
OUT, MODE, PREFIX, SHOTS_ONLY = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == "1"
fails = []
def check(cond, msg):
    if SHOTS_ONLY:
        return
    print(("ok   " if cond else "FAIL ") + msg)
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
def rect_in(widget):
    return QRect(widget.mapTo(w, QPoint(0, 0)), widget.size())
def near(c, hexcol, tol=10):
    q = QColor(hexcol); return abs(c.red() - q.red()) + abs(c.green() - q.green()) + abs(c.blue() - q.blue()) <= tol

ESP = {"age_ms": 400, "soc": 80, "v": 74.2, "i": -6.8, "bms_age_s": 2, "fix": True, "lat": -33.95856, "lon": 18.46,
       "crs": 92, "alt": 41, "vib": 0.035, "vib_dis": 0.01, "imu_hz": [200, 199], "drops": [0, 0], "csq": 18,
       "mqtt": True, "rpm": 900, "spd_raw": 12.3, "fw": "0.7.3"}
NEAR = {"esp32": ESP, "tof": {"left_mm": 900, "ahead_mm": 450, "right_mm": 1500, "age_ms": 120},
        "fusion": {"hazards": [
            {"class": "obstacle", "distance_m": 0.45, "sensor": "ahead", "band": "immediate", "source": "tof"},
            {"class": "obstacle", "distance_m": 0.9, "sensor": "left", "band": "warning", "source": "tof"},
            {"class": "person", "distance_m": 2.6, "bearing_deg": 4, "band": "immediate", "source": "fused"},
            {"class": "bicycle", "distance_m": 6.0, "bearing_deg": -22, "band": "warning", "source": "camera"}]}}
ALERTS = {"active": [
    {"class": "person", "distance_band": "immediate", "confidence": 0.63, "timestamp": "t", "alert_status": "active"},
    {"class": "dog", "distance_band": "warning", "confidence": 0.58, "timestamp": "t", "alert_status": "active"}],
    "fps": 14.8, "latency_ms": 96}

def jpeg(wd=960, ht=540):
    """A drawn test image (a road from the driver's seat), not camera data."""
    img = QImage(wd, ht, QImage.Format.Format_RGB888)
    p = QPainter(img); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    g = QLinearGradient(0, 0, 0, ht * 0.55); g.setColorAt(0, QColor("#9DB7C9")); g.setColorAt(1, QColor("#D9D2C3"))
    p.fillRect(0, 0, wd, int(ht * 0.55), g)
    p.fillRect(0, int(ht * 0.55), wd, ht, QColor("#7B7468"))
    road = [QPoint(int(wd * 0.44), int(ht * 0.55)), QPoint(int(wd * 0.56), int(ht * 0.55)), QPoint(int(wd * 0.95), ht), QPoint(int(wd * 0.05), ht)]
    p.setBrush(QColor("#4A4A4C")); p.setPen(Qt.PenStyle.NoPen); p.drawPolygon(road)
    p.setPen(QPen(QColor("#E8E2D0"), 6, Qt.PenStyle.DashLine)); p.drawLine(wd // 2, int(ht * 0.57), wd // 2, ht)
    f = QFont("Arial"); f.setPixelSize(18); p.setFont(f); p.setPen(QColor("white"))
    p.drawText(QRectF(0, 12, wd, 26), Qt.AlignmentFlag.AlignCenter, "TEST IMAGE, not camera data")
    p.end()
    ba = QByteArray(); b = QBuffer(ba); b.open(QIODevice.OpenModeFlag.WriteOnly); img.save(b, "JPG"); return bytes(ba)

# the route: a real UCT drive (replay file), named by stretch so the map finds turns (as test_style_map)
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
PLAN = SimpleNamespace(route=pts, nearby_roads=[], destination=dest, waypoint=None, warnings=[], preview=[],
                       distance_km=dist / 1000, duration_s=dist / 1000 / 25 * 3600, arrival_soc_pct=78.0,
                       source="offline router")

from app.main_window import MainWindow
w = MainWindow(); w.resize(1280, 800); w.show()
times = {}
PAGES = (("driving", "drive"), ("analytics", "analytics"), ("diagnostics", "diagnostics"), ("navigation", "map"),
         ("sensors", "surroundings"), ("charging", "charging"), ("settings", "settings"))

def shoot(name):
    a.processEvents(); w.grab().save(f"{OUT}/{PREFIX}_{name}.png")

def labels(root):
    return [l for l in root.findChildren(QLabel) if l.isVisible() and QLabel.text(l).strip()]

def clipped(root):
    out = []
    for l in labels(root):
        if l.wordWrap() or l.textFormat() == Qt.TextFormat.RichText:
            continue
        need = QFontMetricsF(l.font()).horizontalAdvance(QLabel.text(l))
        if need > l.contentsRect().width() + 1:
            out.append((QLabel.text(l)[:30], round(need), l.contentsRect().width()))
        if QFontMetricsF(l.font()).height() > l.contentsRect().height() + 2:
            out.append((QLabel.text(l)[:30], "height", round(QFontMetricsF(l.font()).height()), l.contentsRect().height()))
    return out

def feed_state(d, **kw):
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

def feed_tel(d, telemetry):
    d.telemetry.telemetry_updated.emit(telemetry)
    d.sensors._watchdog.stop()

def dump(d, page):
    out = []
    for wd in [page] + page.findChildren(QWidget):
        if not wd.isVisible():
            continue
        text = wd.text() if isinstance(wd, (QLabel, QAbstractButton)) else ""
        g = rect_in(wd)
        out.append([type(wd).__name__, wd.objectName(), g.x(), g.y(), g.width(), g.height(), px(wd), wd.font().family(), str(text)])
    return out

def setup(d):
    d.status.timer.stop(); d.status.clock.setText("14:28")
    try:
        d.telemetry.stop()
    except Exception:
        pass
    try:
        d.telemetry.telemetry_updated.disconnect(d.hazard_banner.set_telemetry)
    except Exception:
        pass
    cam = d.front_camera
    cam._alert_timer.stop(); cam._start_stream = lambda: None; cam._stop_stream()
    if cam._alert_reply is not None:
        try:
            cam._alert_reply.finished.disconnect(); cam._alert_reply.abort()
        except Exception:
            pass
        cam._alert_reply = None
    try:      # the live-only manager republishes its no-data state; the test feeds its own live states
        d.vehicle_data.updated.disconnect(d._on_vehicle_state)
    except (RuntimeError, TypeError):
        pass
    spin(300)

def frame_points(chip):
    """Pixels round the inside edge of the weather item and in the gaps between its parts."""
    img = w.grab(rect_in(chip)).toImage()          # the item as it shows on the bar
    W, H = img.width(), img.height()
    pts = [(x, y) for x in range(0, W, 3) for y in (1, 2, H - 2, H - 3)] + [(x, y) for y in range(0, H, 3) for x in (1, 2, W - 2, W - 3)]
    return img, pts

def run():
    d = w.dashboard
    setup(d)
    if MODE != "paper":
        return run_team(d)
    from app.widgets import sw7_style as S
    from app.theme import THEME
    wait(lambda: d.sw7_weather.report is not None, 8000)
    d.status.timer.stop(); d.status.clock.setText("14:28")
    if not SHOTS_ONLY:
        font_checks(d, S, THEME)
    live(d)
    if SHOTS_ONLY:
        chip = d.status.sw7_weather_chip
        QTest.mouseClick(chip, Qt.MouseButton.LeftButton); a.processEvents(); shoot("day_weather_card")
        d.sw7_weather_card.close_card()
        for night in (False, True):
            S.set_night(night); a.processEvents(); spin(200); feed_state(d); feed_tel(d, NEAR)
            for pid, name in PAGES:
                d.switch_page_id(pid); a.processEvents(); spin(500 if pid != "navigation" else 900)
                d.status.clock.setText("14:28"); shoot(f"{'night' if night else 'day'}_{name}")
        print("RESULT PASS"); a.quit(); return
    checks(d, S)

def font_checks(d, S, THEME):
    fams = set(QFontDatabase.families())
    check({"IBM Plex Sans", "IBM Plex Mono", "Atkinson Hyperlegible"} <= fams, "IBM Plex Sans and Mono registered (Atkinson kept as the fallback)")
    check(S.family() == "IBM Plex Sans" and THEME.font(16).family() == "IBM Plex Sans", f"UI font: {S.family()}, THEME {THEME.font(16).family()}")
    mf = S.mono(16)
    check(QFontInfo(mf).family() == "IBM Plex Mono", f"telemetry font: {QFontInfo(mf).family()}")
    check(QFontInfo(S.font(16, QFont.Weight.Bold)).styleName() in ("SemiBold", "Medium"), "no synthetic bold: Bold maps to SemiBold")
    fm = QFontMetricsF(S.mono(22))
    check(len({round(fm.horizontalAdvance(ch), 2) for ch in "0123456789"}) == 1, "tabular figures in the telemetry font")
    fm = QFontMetricsF(S.font(150, QFont.Weight.DemiBold))
    check(len({round(fm.horizontalAdvance(ch), 2) for ch in "0123456789"}) == 1, "tabular figures in the hero font (no layout shift)")
    check(d.status.clock.font().family() == "IBM Plex Mono", f"clock (a timestamp) in Plex Mono: {d.status.clock.font().family()}")

def live(d):
    feed_state(d)
    feed_tel(d, NEAR)
    cam = d.front_camera
    cam._streaming_wanted = False; cam._apply_alerts(ALERTS); cam._streaming_wanted = True
    cam._feed(jpeg()); cam._stale_timer.stop(); a.processEvents()
    m = d.navigation.map
    d.switch_page_id("navigation"); spin(300)
    m.set_plan(PLAN, reset_view=False); spin(200)
    for r in recs[200:232:2]:
        s = copy.copy(d._sw7_live_state); s.data_source = "sw7_telemetry"
        s.latitude, s.longitude, s.heading = r["lat"], r["lon"], r.get("crs")
        s.soc_pct = 79.6; s.speed_kmh = 23.0; s.range_km = 56.2
        s.signal_validity = dict(s.signal_validity or {}, gps=True, heading=True, soc=True, speed=True)
        d._on_vehicle_state(s); QTest.qWait(120)
    spin(800)

def checks(d, S):
    m = d.navigation.map
    # ---- the weather item -----------------------------------------------------------------------------------------------
    chip = d.status.sw7_weather_chip
    img, pts = frame_points(chip)
    bg = S.hx("paper")
    off = [(x, y) for x, y in pts if not near(img.pixelColor(x, y), bg, 6)]
    check(not off, f"weather item: no border and no fill (edge pixels off the bar's paper: {len(off)})")
    check(chip.height() >= 44 and chip.width() >= 64 and S.is_tappable(chip) is not False, f"weather item still a {chip.width()} x {chip.height()} target")
    check("24°" in chip.summary() and "Rondebosch" in chip.summary(), f"weather item text {chip.summary()!r}")
    sb = d.status
    cy_chip = rect_in(chip).center().y(); cy_clock = rect_in(sb.clock).center().y()
    check(abs(cy_chip - cy_clock) <= 2, f"weather item aligned with the other indicators ({cy_chip} vs {cy_clock})")
    QTest.mouseClick(chip, Qt.MouseButton.LeftButton); a.processEvents()
    check(d.sw7_weather_card.isVisible(), "tapping the weather item opens the weather card")
    shoot("day_weather_card")
    d.sw7_weather_card.close_card(); a.processEvents()
    # ---- the pages, day and night -----------------------------------------------------------------------------------
    for night in (False, True):
        S.set_night(night); a.processEvents(); spin(200)
        theme = "night" if night else "day"
        feed_state(d); feed_tel(d, NEAR)
        for pid, name in PAGES:
            d.switch_page_id(pid); a.processEvents(); spin(500 if pid != "navigation" else 900)
            d.status.clock.setText("14:28")
            page = d.page_by_id[pid]
            shoot(f"{theme}_{name}")
            tag = f"{theme} {name}"
            view = getattr(d, "sw7_surroundings", None)
            found = S.audit_signal(w, ignore=(m, view.slab if view is not None else None))
            found = [f for f in found if not (f.kind == "info_in_signal" and f.pixels <= 16)]
            check(not found, f"{tag}: signal audit: {S.ok_audit(found) or 'clean'}")
            bad = [(S.describe(x), p) for x, p in S.type_audit(page)]
            check(not bad, f"{tag}: text on the type scale: {bad}")
            cl = clipped(page) + clipped(d.status)
            check(not cl, f"{tag}: no clipped labels: {cl}")
            nav_top = rect_in(d.nav).top() + S.NAV_BAR_TOP
            low = [S.describe(x) for x in page.findChildren(QAbstractButton) if x.isVisible() and rect_in(x).bottom() >= nav_top]
            check(not low, f"{tag}: nothing tappable under the nav bar: {low}")
            check(rect_in(d.stack).bottom() < nav_top, f"{tag}: the nav bar covers no page content ({rect_in(d.stack).bottom()} < {nav_top})")
            small = [S.describe(x) for x in page.findChildren(QAbstractButton) if x.isVisible() and x.isEnabled()
                     and x.width() > 8 and min(x.width(), x.height()) < 64 and not x.property("sw7_small_ok")]
            check(not small, f"{tag}: touch targets at least 64 px: {small}")
            plex = [l for l in labels(page) if l.font().family() in ("IBM Plex Sans", "IBM Plex Mono")]
            other = [(QLabel.text(l)[:20], l.font().family()) for l in labels(page) if l.font().family() not in ("IBM Plex Sans", "IBM Plex Mono")]
            check(not other, f"{tag}: every label in Plex ({len(plex)} labels): {other[:6]}")
            if pid == "charging":
                vis = page.tuk
                check(vis.anim_timer.isActive(), f"{tag}: the battery animation runs on Charging")
                n0 = getattr(vis, "sw7_frames", 0); spin(400)
                check(getattr(vis, "sw7_frames", 0) > n0 + 4, f"{tag}: bubbles and arc move ({getattr(vis, 'sw7_frames', 0) - n0} frames in 0.4 s)")
                out = []
                for _ in range(40):
                    t0 = time.perf_counter(); vis.repaint(); out.append((time.perf_counter() - t0) * 1000)
                times[f"{theme}_charging_ring_ms"] = sorted(out)[20]
                check(sorted(out)[20] < 12.0, f"{tag}: ring frame paint {sorted(out)[20]:.2f} ms (median of 40)")
        # nav targets
        for pid, b in d.nav.buttons.items():
            if b.isVisible():
                check(b.width() >= 64 and b.height() >= 64, f"{theme}: nav {pid} target {b.width()} x {b.height()}")
        d.switch_page_id("analytics"); a.processEvents(); spin(200)
        check(not d.charging.tuk.anim_timer.isActive(), f"{theme}: the animation stops when Charging is not shown")
    S.set_night(False); a.processEvents(); spin(200)
    # ---- telemetry in Plex Mono ---------------------------------------------------------------------------------------
    diag = d.diagnostics; lay = diag._sw7_layout
    feed_state(d); feed_tel(d, NEAR)
    d.switch_page_id("diagnostics"); a.processEvents(); spin(300)
    vals = [v for c in lay["cards"] for v in c.values.values() if isinstance(v, QLabel) and v.isVisible()]
    figs = [v for v in vals if any(ch.isdigit() for ch in v.text())]
    words = [v for v in vals if v.text() in ("Unavailable", "Yes", "No", "Up", "Live")]
    check(figs and all(v.font().family() == "IBM Plex Mono" for v in figs),
          f"Diagnostics figures in Plex Mono: {[(v.text(), v.font().family()) for v in figs][:4]}")
    check(words and all(v.font().family() == "IBM Plex Sans" for v in words),
          f"Diagnostics words in Plex Sans: {[(v.text(), v.font().family()) for v in words][:4]}")
    caps = [c for card in lay["cards"] for c in card.captions if c.isVisible()]
    check(caps and all(c.font().family() == "IBM Plex Sans" for c in caps), "Diagnostics captions in Plex Sans")
    # ---- unavailable never looks like zero ---------------------------------------------------------------------------
    from app.data import sw7_live_only
    d._on_vehicle_state(sw7_live_only.no_data_state()); a.processEvents()
    feed_tel(d, None)
    d.switch_page_id("charging"); a.processEvents(); spin(400)
    ch = d.charging
    tiles = {c.findChild(QLabel).text(): c.value_label.text() for c in (ch.sw7_card_range_now, ch.card_range, ch.card_energy)}
    check(all(v.startswith("--") for v in tiles.values()), f"no data: Charging tiles show '--', not zero: {tiles}")
    state = ch.status.text()
    check("unknown" in state.lower() or "no data" in state.lower(), f"no data: the charging state says unknown: {state!r}")
    check(not ch.tuk.sw7_bubbles_shown(), "no data: no bubbles (they would suggest a charge level)")
    shoot("day_charging_nodata")
    d.switch_page_id("diagnostics"); a.processEvents(); spin(300)
    unav = [v for v in vals if v.text() == "Unavailable"]
    check(unav and all(v.font().family() == "IBM Plex Sans" for v in unav), "no data: 'Unavailable' is a word in Plex Sans, not a figure")
    shoot("day_diagnostics_nodata")
    chip.set_report(None); a.processEvents()
    check(chip.temp_text() == "--°", f"weather unavailable: {chip.summary()!r}")
    shoot("day_weather_unavailable")
    print("PAINT " + json.dumps(times))
    print("RESULT", "PASS" if not fails else f"FAIL {fails}")
    a.quit()

def run_team(d):
    feed_state(d); feed_tel(d, NEAR)
    trees, pix = {}, {}
    for pid in ("driving", "analytics", "diagnostics", "navigation", "camera", "sensors", "charging", "settings"):
        d.switch_page_id(pid); a.processEvents(); spin(500)
        d.status.clock.setText("14:28")
        trees[pid] = dump(d, d.page_by_id[pid])
        if pid in ("diagnostics", "settings", "camera"):
            img = d.page_by_id[pid].grab().toImage()
            pix[pid] = hashlib.sha1(bytes(img.constBits())).hexdigest()
        if PREFIX == "before" or SHOTS_ONLY:
            shoot(f"team_{pid}")
    trees["nav"] = [[pid, b.isVisible(), b.toolTip()] for pid, b in d.nav.buttons.items()] + [list(d.normal_ids)]
    trees["status"] = dump(d, d.status)
    with open(os.path.join(OUT, "..", "_team_now.json"), "w", encoding="utf-8") as f:
        json.dump({"trees": trees, "pix": pix}, f)
    print("RESULT PASS")
    a.quit()

def wait_ready(n=0):
    if w.stack.currentWidget() is getattr(w, "dashboard", None) or n > 60:
        QTimer.singleShot(2500, run)
    else:
        QTimer.singleShot(500, lambda: wait_ready(n + 1))
wait_ready()
a.exec()
'''


def env_for(extra, cache):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", TUKZIE_LIVE_ONLY="1", TUKZIE_NO_CONTROLLER="1",
               TUKZIE_SKIP_LOGIN="1", TUKZIE_SW7_THEME="0", TUKZIE_TELEMETRY_URL="http://127.0.0.1:9",
               TUKZIE_CAMERA_URL="http://127.0.0.1:9",
               TUKZIE_TILE_URL="http://127.0.0.1:9/{z}/{x}/{y}.png", TUKZIE_TILE_CACHE=cache,
               TUKZIE_WEATHER_URL=BASE + "/v1/forecast", TUKZIE_REVERSE_URL=BASE + "/reverse",
               TUKZIE_WEATHER_CACHE=os.path.join(SP, "weather_" + str(time.monotonic_ns()), "last.json"),
               TUKZIE_REPLAY=REPLAY, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    for k in ("TUKZIE_SW7_STYLE", "TUKZIE_SW7_NIGHT", "TUKZIE_SW7_LAYOUT", "TUKZIE_MAP_TILT", "TUKZIE_TILE_MAP"):
        env.pop(k, None)
    env.update(extra)
    if sys.platform == "win32":
        env.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
    return env


def run(target, mode, extra, label, cache):
    r = subprocess.run([sys.executable, "-c", DASH, OUT, mode, PREFIX, "1" if SHOTS_ONLY else "0"], cwd=target,
                       env=env_for(extra, cache), capture_output=True, text=True, timeout=900, encoding="utf-8", errors="replace")
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


cache = tile_cache()
full = build("full")
ONLY = os.environ.get("SW7_REFINE_ONLY", "").strip()
ok, paint = True, {}
if ONLY != "team":
    ok, paint = run(full, "paper", {}, "paper", cache)
if ONLY != "paper":
    ok2, _ = run(full, "team", {"TUKZIE_SW7_STYLE": "team"}, "team (TUKZIE_SW7_STYLE=team)", cache)
    ok = ok and ok2
    now_path = os.path.join(OUT, "..", "_team_now.json")
    if os.path.exists(now_path):
        with open(now_path, encoding="utf-8") as f:
            now = json.load(f)
        os.remove(now_path)
        if os.environ.get("SW7_REFINE_WRITE_TEAM") == "1":
            with open(REFERENCE, "w", encoding="utf-8") as f:
                json.dump(now, f, indent=0)
            print("team reference written:", REFERENCE)
        elif os.path.exists(REFERENCE):
            with open(REFERENCE, encoding="utf-8") as f:
                ref = json.load(f)
            for pid in ref["trees"]:
                same = now["trees"].get(pid) == ref["trees"][pid]
                diff = [(x, y) for x, y in zip(now["trees"].get(pid, []), ref["trees"][pid]) if x != y][:3]
                print(("ok   " if same else "FAIL ") + f"TUKZIE_SW7_STYLE=team: {pid} widget tree as before the refinement"
                      + ("" if same else f" {diff}"))
                ok = ok and same
            for pid in ref["pix"]:
                same = now["pix"].get(pid) == ref["pix"][pid]
                print(("ok   " if same else "FAIL ") + f"TUKZIE_SW7_STYLE=team: {pid} pixels as before the refinement")
                ok = ok and same
        else:
            print("FAIL no team reference (run once with SW7_REFINE_WRITE_TEAM=1 on the build before the refinement)"); ok = False
    else:
        print("FAIL team run wrote nothing"); ok = False
if paint:
    print("Charging ring paint time per animation frame (repaint, median of 40): "
          + ", ".join(f"{k} {v:.2f} ms" for k, v in sorted(paint.items())))
server.shutdown()
shutil.rmtree(SP, ignore_errors=True)
if not ok:
    sys.exit(1)
print("ALL STYLE REFINE TESTS PASSED")
