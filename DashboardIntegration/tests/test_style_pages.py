"""Offscreen test: the paper and depth style, page agent P2 (sw7_style_pages.py; Planning/paper-depth-theme-prompt.md
sections 9 and 10, Planning/data-ownership-and-merge-plan.md).

Builds two patched copies of the team's v1.1 dashboard (TUKZIE_DASHBOARD_DIR, as the other tests): one with every
patch group, one without STYLE_PAGES_PATCHES and its copy. A local fake server plays Open-Meteo and Photon reverse
(never the real APIs); telemetry and camera alerts are fed to the dashboard directly. Runs:
  paper  the dashboard at 1280 x 800: Surroundings (Front camera and Sensors merged: 7 nav items, the swipe and arrow
         order, the "camera" and "surroundings" aliases, the obstacle pill, one combined hazards list nearest first,
         the ToF figure, the camera frame streaming only on this page, the battery following the simulated drive),
         Diagnostics (one home per value, "Ambient (vehicle)" and "Outside (weather)", the weather glance) and
         Charging (one power, one time to full, one state, BMS voltage and current), the signal audit and the type
         audit on each page, screenshots in tests/style/pages/ (day, night, simulated drive), paint time.
  team   TUKZIE_SW7_STYLE=team on the full copy, and the base copy: the 8-page nav, and the widget trees of
         Surroundings, Camera, Diagnostics and Charging (and the pixels of Sensors and Diagnostics) identical.
Run: TUKZIE_DASHBOARD_DIR=<team Dashboard folder> python tests/test_style_pages.py
"""
import glob, json, os, shutil, subprocess, sys, tempfile, threading, time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)
TEAM = os.environ.get("TUKZIE_DASHBOARD_DIR", "").strip()
if not TEAM or not os.path.isdir(os.path.join(TEAM, "app", "pages")):
    sys.exit("Set TUKZIE_DASHBOARD_DIR to a copy of the team's v1.1 Dashboard folder")
SP = tempfile.mkdtemp(prefix="sw7_style_pages_")
OUT = os.path.join(HERE, "style", "pages"); os.makedirs(OUT, exist_ok=True)


def build(name, without_group):
    target, src = os.path.join(SP, "build_" + name), os.path.join(SP, "src_" + name)
    shutil.copytree(TEAM, target, ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(src)
    for f in glob.glob(os.path.join(INTEG, "*.py")):
        shutil.copy(f, src)
    shutil.copy(os.path.join(INTEG, "tests", "dashboard_patches.py"), src)
    shutil.copytree(os.path.join(INTEG, "fonts"), os.path.join(src, "fonts"))
    shutil.copytree(os.path.join(INTEG, "assets"), os.path.join(src, "assets"))
    if without_group:
        with open(os.path.join(src, "dashboard_patches.py"), "a", encoding="utf-8") as f:
            f.write("\nPATCHES = tuple(p for p in PATCHES if p not in STYLE_PAGES_PATCHES)\n"
                    "COPIES = tuple(c for c in COPIES if c not in STYLE_PAGES_COPIES)\n")
        os.remove(os.path.join(src, "sw7_style_pages.py"))
    r = subprocess.run([sys.executable, os.path.join(INTEG, "deploy", "apply_patches.py"), target, "--source", src,
                        "--native-map", "--team-dir", os.path.join(SP, "nonexistent")], capture_output=True, text=True)
    print(name + ": " + (r.stdout.strip().splitlines()[-1] if r.returncode == 0 else r.stdout + r.stderr))
    if r.returncode:
        sys.exit(1)
    return target


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
            "current": {"time": local(now), "temperature_2m": 17.4, "weather_code": 2, "wind_speed_10m": 12.4, "is_day": 1},
            "hourly": {"time": [local(h) for h in hours], "temperature_2m": [17, 18, 18, 19, 19, 18, 17, 16, 15, 15, 14, 14, 13],
                       "weather_code": [2, 2, 1, 1, 0, 0, 1, 2, 3, 3, 2, 1, 0]},
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
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QFontMetricsF, QLinearGradient, QPen
from PySide6.QtTest import QTest
a = QApplication(sys.argv)
OUT, MODE = sys.argv[1], sys.argv[2]
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
def px(widget):
    f = widget.font(); return f.pixelSize() if f.pixelSize() > 0 else round(f.pointSizeF() * 96 / 72)
def rect_in(widget):
    return QRect(widget.mapTo(w, QPoint(0, 0)), widget.size())

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
    {"class": "car", "distance_band": "monitoring", "confidence": 0.71, "timestamp": "t", "alert_status": "active"},
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
    p.setPen(QPen(QColor("#FF1744"), 3)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawRect(520, 250, 70, 170)
    p.setPen(QPen(QColor("#FFD600"), 3)); p.drawRect(300, 300, 90, 70)
    f = QFont("Arial"); f.setPixelSize(18); p.setFont(f); p.setPen(QColor("white"))
    p.drawText(520, 244, "person 0.63"); p.drawText(300, 294, "dog 0.58")
    p.drawText(QRectF(0, 12, wd, 26), Qt.AlignmentFlag.AlignCenter, "TEST IMAGE, not camera data")
    p.end()
    ba = QByteArray(); b = QBuffer(ba); b.open(QIODevice.OpenModeFlag.WriteOnly); img.save(b, "JPG"); return bytes(ba)

def plan():
    lat0, lon0 = -33.9600, 18.4600
    mlat, mlon = 1 / 111320.0, 1 / (111320.0 * math.cos(math.radians(lat0)))
    pts = [SimpleNamespace(lat=lat0 + i * 10 * mlat, lon=lon0, road_name="Main Road", dist_km=i * 0.01, elevation_m=0.0) for i in range(41)]
    pts += [SimpleNamespace(lat=lat0 + 400 * mlat, lon=lon0 + i * 10 * mlon, road_name="Station Road", dist_km=0.4 + i * 0.01, elevation_m=0.0) for i in range(1, 41)]
    dest = {"name": "Station Road", "label": "Station Road, Rondebosch", "lat": pts[-1].lat, "lon": pts[-1].lon}
    return SimpleNamespace(route=pts, nearby_roads=[], destination=dest, waypoint=None, warnings=[], preview=[],
                           distance_km=0.8, duration_s=120.0, arrival_soc_pct=78.0, source="offline router")

from app.main_window import MainWindow
w = MainWindow(); w.resize(1280, 800); w.show()
times = {}

def paint_ms(n=15):
    a.processEvents(); w.grab(); out = []
    for _ in range(n):
        t = time.perf_counter(); w.grab(); out.append((time.perf_counter() - t) * 1000)
    return sorted(out)[n // 2]

def shoot(name):
    a.processEvents(); w.grab().save(f"{OUT}/{name}.png")

def labels(root):
    return [l for l in root.findChildren(QLabel) if l.isVisible() and QLabel.text(l).strip()]

def clipped(root):
    out = []
    for l in labels(root):
        if l.wordWrap():
            continue
        need = QFontMetricsF(l.font()).horizontalAdvance(QLabel.text(l))
        if need > l.contentsRect().width() + 1:
            out.append((QLabel.text(l), round(need), l.contentsRect().width()))
    return out

def audits(d, page, tag):
    from app.widgets import sw7_style as S
    view = getattr(d, "sw7_surroundings", None)
    found = S.audit_signal(w, ignore=(view.slab if view is not None else None,))   # the camera image is a photo, like the map
    check(not found, f"{tag}: signal audit: {S.ok_audit(found) or 'clean'}")
    bad = [(S.describe(x), p) for x, p in S.type_audit(page)]
    check(not bad, f"{tag}: page text only in 13, 16, 22 or 120 to 180 px: {bad}")
    cl = clipped(page)
    check(not cl, f"{tag}: no clipped labels: {cl}")
    top = d.stack.mapTo(w, QPoint(0, 0)).y()
    low = [S.describe(x) for x in page.findChildren(QAbstractButton)
           if x.isVisible() and rect_in(x).bottom() > top + d.stack.height() - 16]
    check(not low, f"{tag}: no tap targets in the page's bottom 16 px (under the nav pill): {low}")

def feed(d, telemetry):
    d.telemetry.telemetry_updated.emit(telemetry)
    d.sensors._watchdog.stop()

def dump(d, page):
    out = []
    for wd in [page] + page.findChildren(QWidget):
        if not wd.isVisible():
            continue
        text = wd.text() if isinstance(wd, (QLabel, QAbstractButton)) else ""
        g = rect_in(wd)
        out.append([type(wd).__name__, wd.objectName(), g.x(), g.y(), g.width(), g.height(), px(wd), text])
    return out

def run():
    d = w.dashboard
    d.status.timer.stop(); d.status.clock.setText("14:28")
    try:
        d.telemetry.stop()
    except Exception:
        pass
    d.telemetry.telemetry_updated.disconnect(d.hazard_banner.set_telemetry)
    cam = d.front_camera
    cam._alert_timer.stop(); cam._start_stream = lambda: None; cam._stop_stream()
    if cam._alert_reply is not None:          # a poll still in flight would clear the fed alerts when it fails
        cam._alert_reply.finished.disconnect(); cam._alert_reply.abort(); cam._alert_reply = None
    cam._alert_reply = None   # a poll still in flight is ignored when it finishes
    spin(300)
    if MODE != "paper":
        return run_team(d)
    from app.widgets import sw7_style as S
    from app.pages import sw7_style_pages as P
    check(wait(lambda: d.sw7_weather.report is not None, 8000), "the weather service fetched (fake Open-Meteo)")
    d.status.timer.stop(); d.status.clock.setText("14:28")
    nav = d.nav
    # ---- the merge: 7 pages, the order, the aliases --------------------------------------------------------------
    shown = [pid for pid, b in nav.buttons.items() if b.isVisible()]
    want = ["driving", "analytics", "diagnostics", "navigation", "sensors", "charging", "settings"]
    check(shown == want, f"7 nav items: {shown}")
    check(nav.buttons["sensors"].sw7_label.text() == "Surroundings" and not nav.buttons["camera"].isVisible(),
          "the Camera item is gone and Sensors is Surroundings")
    check(d.normal_ids == want, f"swipe and arrow order: {d.normal_ids}")
    d.switch_page_id("navigation"); d.navigate_pages(1); a.processEvents()
    check(d.stack.currentWidget() is d.sensors and nav.buttons["sensors"].isChecked(), "Map -> Surroundings with the arrow")
    d.navigate_pages(1); check(d.stack.currentWidget() is d.charging, "Surroundings -> Charging")
    d.navigate_pages(-1); d.navigate_pages(-1); check(d.stack.currentWidget() is d.navigation, "back to Map")
    for alias in ("camera", "surroundings", "sensors"):
        d.switch_page_id("driving"); d.switch_page_id(alias); a.processEvents()
        check(d.stack.currentWidget() is d.sensors and nav.buttons["sensors"].isChecked(), f"switch_page_id({alias!r}) opens Surroundings")
    sw = d._sw7_page_swipe
    d.switch_page_id("navigation")
    check(sw._neighbour(1) is d.sensors and sw._neighbour(-1) is d.diagnostics, "the two-finger swipe's neighbours follow")
    # the obstacle pill opens Surroundings
    d.switch_page_id("driving"); hb = d.hazard_banner
    hb._message = ("crit", "OBSTACLE 0.45 M AHEAD"); hb._refresh(); a.processEvents()
    QTest.mouseClick(hb.text, Qt.MouseButton.LeftButton); a.processEvents()
    check(d.stack.currentWidget() is d.sensors and not hb.isVisible(), "tapping the obstacle pill opens Surroundings (and hides it there)")
    hb._message = None; hb._refresh()
    # ---- Surroundings with near hazards ------------------------------------------------------------------------------
    view = d.sw7_surroundings
    check(cam.parentWidget() is view and cam.isVisible() and cam._streaming_wanted, "the camera streams inside Surroundings")
    d.switch_page_id("analytics"); a.processEvents()
    check(not cam._streaming_wanted, "and stops when another page is shown")
    d.switch_page_id("sensors"); a.processEvents()
    feed(d, NEAR)
    cam._streaming_wanted = False; cam._apply_alerts(ALERTS); cam._streaming_wanted = True
    cam._feed(jpeg()); cam._stale_timer.stop(); a.processEvents()
    rows = [P.row_texts(r)[0] for r in view.rows]
    check(rows == ["Obstacle 0.45 m ahead", "Obstacle 0.90 m left", "Person 2.6 m ahead", "Bicycle 6.0 m left",
                   "Dog under 8 m ahead", "Car under 15 m ahead"], f"one hazards list, nearest first: {rows}")
    check(P.row_texts(view.rows[2])[1] == "Immediate · camera + ToF 63 %", f"a camera alert the fusion has adds its confidence: {P.row_texts(view.rows[2])[1]!r}")
    vis_rows = [r.main_text for r in view.rows_w if r.isVisible()]
    check(len(vis_rows) == 4 and view.more.text() == "+2 more, farther away", f"4 rows and '+2 more': {vis_rows} {view.more.text()!r}")
    lists = [x for x in d.sensors.findChildren(QWidget) if x.isVisible() and x.objectName() in ("sw7AlertRow",)]
    check(not lists and not cam.metrics_label.parentWidget().isVisible() and not d.sensors.scroll.isVisible(),
          "the camera's own alert list and the old Sensors cards are not shown (one list)")
    check(view.hero.text() == "0.45" and view.unit.text() == "m" and px(view.hero) == 150, f"hero: nearest {view.hero.text()} {view.unit.text()} at 150 px")
    vals = view.figure.values()
    check(vals["left"][0] == "0.90 m" and vals["ahead"][0] == "0.45 m" and vals["right"][0] == "Clear", f"ToF figure: {vals}")
    check(view.slab.image is not None and QLabel.text(view.chip).upper().startswith("CAMERA LIVE · 14.8"), f"camera frame and chip {QLabel.text(view.chip)!r}")
    check(view.link_chip.text() == "Sensors live" and view.ride.text() == "Vibration 0.04 m/s² · IMU disagreement 0.01",
          f"link chip and ride row: {view.link_chip.text()!r} {view.ride.text()!r}")
    fr, tk, hz, _x = view.rects()
    check(tk.top() < fr.bottom() and tk.left() > fr.left() and fr.bottom() - tk.top() >= 12, "the tuk-tuk card overlaps the frame's edge (depth)")
    audits(d, d.sensors, "day surroundings")
    shoot("day_surroundings")
    times["paper_surroundings"] = paint_ms()
    # offline: no invented values
    feed(d, None); cam._apply_alerts({"active": [], "fps": None}); a.processEvents()
    check(view.hero.text() == "--" and view.link_chip.text() == "Sensors offline", f"offline: hero {view.hero.text()!r}, chip {view.link_chip.text()!r}")
    feed(d, NEAR); cam._streaming_wanted = False; cam._apply_alerts(ALERTS); cam._streaming_wanted = True; cam._stale_timer.stop()
    # ---- Diagnostics ---------------------------------------------------------------------------------------------
    d.switch_page_id("diagnostics"); a.processEvents(); spin(300)
    diag = d.diagnostics; lay = diag._sw7_layout
    cards = [c.title.text() for c in lay["cards"]]
    check(cards == ["CONTROLS", "HEALTH", "POSITION", "LINK"], f"cards: {cards}")
    seen = [l.text() for c in lay["cards"] for l in c.captions if l.isVisible()]
    for gone in ("Speed", "Gear", "Battery SOC", "Range", "Battery temp", "Odometer", "Charging", "Data"):
        check(gone not in seen, f"{gone!r} left the Diagnostics cards (its home is elsewhere)")
    check("Ambient (vehicle)" in seen and "Outside (weather)" in seen, f"two labelled temperatures: {seen}")
    check(all(k in lay["details_values"] for k in ("Speed", "Gear", "Battery SOC", "Range", "Odometer")), "they stay in the folded details")
    g = lay["glance"]
    check(g.text().startswith("17°") and S.is_tappable(g), f"weather glance {g.text()!r} in signal, tappable")
    rv = lay["telemetry_rows"]
    check(rv["fix"].text() == "Yes" and rv["fw"].text() == "0.7.3" and rv["rpm"].text() == "900 rpm", "GPS fix, firmware and motor rpm from the telemetry")
    audits(d, diag, "day diagnostics")
    shoot("day_diagnostics")
    times["paper_diagnostics"] = paint_ms()
    QTest.mouseClick(g, Qt.MouseButton.LeftButton); a.processEvents()
    check(d.sw7_weather_card.isVisible(), "the glance opens the weather card"); d.sw7_weather_card.close_card()
    lay["toggle"].setChecked(True); a.processEvents(); spin(200)
    check(lay["details"].isVisible() and lay["details_values"]["Gear"].text() not in ("", "--"), "details open with the raw values")
    bad = [(S.describe(x), p) for x, p in S.type_audit(diag)]
    check(not bad, f"details: text on the scale: {bad}")
    shoot("day_diagnostics_details"); lay["toggle"].setChecked(False)
    # ---- Charging --------------------------------------------------------------------------------------------------
    d.switch_page_id("charging"); a.processEvents(); spin(400)
    ch = d.charging
    check(not ch.card_eta.isVisible() and not ch.card_rate.isVisible(), "the Time to full and Charging power tiles are gone")
    t = ch.tuk._sw7_texts
    check(t["voltage"] == "74.2 V" and t["current"] == "-6.8 A", f"not charging: pack voltage and current from the BMS: {t['voltage']} {t['current']}")
    check(t["soh"] == "--", f"cell health only when reported: {t['soh']!r}")
    states = [l.text() for l in labels(ch) if l is not ch.sw7_title and (l.text().startswith(("Not charging", "Charging")) or "STANDBY" in l.text())]
    want_state = "Charging state unknown · no live data" if str(getattr(d.current_state, "data_source", "")) == "no_data" else "Not charging"
    check(states == [want_state], f"one charging state (unknown with no live data, refinement): {states}")
    power = [l.text() for l in labels(ch) if l.text().endswith(" kW")]
    check(not power, f"one power figure (on the ring): {power}")
    check(ch.sw7_card_range_now.value_label.text() not in ("",), f"Range tile {ch.sw7_card_range_now.value_label.text()!r}")
    check(ch.tuk.anim_timer.isActive() == (not ch.tuk.sw7_no_data) and ch.tuk.anim_timer.interval() >= 33,
          "the battery animation (restored by the refinement) runs at 30 fps on Charging, and not with no live data")
    audits(d, ch, "day charging")
    shoot("day_charging")
    times["paper_charging"] = paint_ms()
    # ---- simulated drive: every battery figure follows -------------------------------------------------------------
    m = d.navigation.map
    d.switch_page_id("navigation"); spin(300); m.set_plan(plan(), reset_view=False); spin(200)
    check(m.start_simulation(), "simulated drive started")
    for _ in range(20): m._sim_step()
    spin(400)
    feed(d, NEAR)
    s = d.current_state
    d.switch_page_id("sensors"); a.processEvents(); spin(200)
    soc_txt = d.sensors.values["soc"].text()
    check(s.data_source == "sw7_simulated_drive" and soc_txt == f"{s.soc_pct:.0f} %" and d.status.soc.text() == f"{s.soc_pct:.0f}%",
          f"Surroundings battery follows the simulation: {soc_txt} (status bar {d.status.soc.text()}, telemetry says 80)")
    check(not [l.text() for l in labels(d.sensors) if l.text().endswith("%")], "no second battery figure on Surroundings")
    audits(d, d.sensors, "simulated surroundings"); shoot("simulated_surroundings")
    d.switch_page_id("diagnostics"); spin(300); audits(d, d.diagnostics, "simulated diagnostics"); shoot("simulated_diagnostics")
    d.switch_page_id("charging"); spin(300)
    t = ch.tuk._sw7_texts
    check(t["soc"] == f"{s.soc_pct:.0f}" or t["soc"] == f"{d.current_state.soc_pct:.0f}", f"Charging ring follows: {t['soc']}")
    check(t["voltage"] == "--", "simulated: no live BMS voltage mixed in")
    audits(d, ch, "simulated charging"); shoot("simulated_charging")
    m.stop_simulation(); spin(300)
    # ---- night ------------------------------------------------------------------------------------------------------
    S.set_night(True); a.processEvents(); spin(200)
    feed(d, NEAR)
    for pid, page, name in (("sensors", d.sensors, "surroundings"), ("diagnostics", d.diagnostics, "diagnostics"), ("charging", ch, "charging")):
        d.switch_page_id(pid); a.processEvents(); spin(250)
        img = w.grab().toImage()
        check(abs(img.pixelColor(640, 60).red() - QColor(S.NIGHT["paper"]).red()) < 20 or pid == "sensors", f"night {name}: Ink paper")
        audits(d, page, f"night {name}")
        shoot(f"night_{name}")
    times["paper_surroundings_night"] = (d.switch_page_id("sensors"), paint_ms())[1]
    S.set_night(False)
    print("PAINT " + json.dumps(times))
    print("RESULT", "PASS" if not fails else f"FAIL {fails}")
    a.quit()

def run_team(d):
    check(not hasattr(d, "sw7_surroundings") and d.nav.buttons["camera"].isVisible() and "camera" in d.normal_ids
          and len([b for b in d.nav.buttons.values() if b.isVisible()]) == 8, f"{MODE}: 8 pages, Camera and Sensors apart")
    trees, pix = {}, {}
    d.sensors.set_telemetry(NEAR); d.sensors._watchdog.stop()
    for pid in ("sensors", "camera", "diagnostics", "charging"):
        d.switch_page_id(pid); a.processEvents(); spin(400)
        trees[pid] = dump(d, d.page_by_id[pid])
        if pid in ("sensors", "diagnostics"):
            img = d.page_by_id[pid].grab().toImage()
            pix[pid] = hashlib.sha1(bytes(img.constBits())).hexdigest()
    trees["nav"] = [[pid, b.isVisible(), b.toolTip()] for pid, b in d.nav.buttons.items()] + [list(d.normal_ids)]
    for pid in ("sensors", "diagnostics", "charging"):
        d.switch_page_id(pid); times[f"team_{pid}"] = paint_ms()
    with open(f"{OUT}/../tree_pages_{MODE}.json", "w", encoding="utf-8") as f:
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
               TUKZIE_CAMERA_URL="http://127.0.0.1:9",
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
    r = subprocess.run([sys.executable, "-c", DASH] + args, cwd=target, env=env_for(extra), capture_output=True,
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
ONLY = os.environ.get("SW7_PAGES_ONLY", "")          # "paper" or "team" while debugging
ok, paint = True, {}
if ONLY != "team":
    ok, paint = run(full, [OUT, "paper"], {}, "paper")
if ONLY != "paper":
    base = build("base", True)
    ok3, paint_team = run(full, [OUT, "team"], {"TUKZIE_SW7_STYLE": "team"}, "team (TUKZIE_SW7_STYLE=team)")
    ok4, _ = run(base, [OUT, "base"], {"TUKZIE_SW7_STYLE": "team"}, "base (without the page group)")
    ok = ok and ok3 and ok4
    trees = {}
    for m in ("team", "base"):
        path = os.path.join(OUT, "..", f"tree_pages_{m}.json")
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
            ok = ok and same
        for pid in trees["base"]["pix"]:
            px_same = trees["team"]["pix"][pid] == trees["base"]["pix"][pid]
            print(("ok   " if px_same else "FAIL ") + f"TUKZIE_SW7_STYLE=team: {pid} pixels identical to the base")
            ok = ok and px_same
    else:
        print("FAIL team comparison did not run"); ok = False
    paint.update(paint_team)
print("Paint time of a full 1280 x 800 frame (QWidget.grab, median of 15): "
      + ", ".join(f"{k} {v:.1f} ms" for k, v in sorted(paint.items())))
server.shutdown()
shutil.rmtree(SP, ignore_errors=True)
if not ok:
    sys.exit(1)
print("ALL STYLE PAGES TESTS PASSED")
