"""Offscreen test: the Front | Rear camera toggle on Surroundings (sw7_dual_camera.py, DUAL_CAMERA_PATCHES).

Builds two patched copies of the team's v1.1 dashboard (TUKZIE_DASHBOARD_DIR, as the other tests): one with every
patch group, one without DUAL_CAMERA_PATCHES and its copy. Inside the dashboard process, four local fake servers play
the two sides (never the real Pis):
  front camera   /stream (MJPEG), /alerts, /detections     (as pi5-hazard-detector on the Pi 5, :8080)
  front ToF      /telemetry, "esp32": null                 (as pi5-tof-bridge on the Pi 5, :8082)
  rear camera    /stream, /alerts, /detections             (as the Pi 4 detector, :8080)
  rear bridge    /telemetry with the ESP32                 (as the Pi 4 bridge, :8081, through TUKZIE_TELEMETRY_URL)
Each test image is drawn, not camera data, with a coloured mark on its left half, so a mirrored image is visible.
Runs:
  dual     the toggle (two 64 px targets, signal only there), each side's stream, alerts, ToF figure and hazards; only
           the selected stream fetched; the rear mirrored with left and right swapped; one side offline (the usual
           offline state for it, the other side live, never 0 or a value from the other side); the banner from both
           sides labelled Front or Rear, approaching objects first, with and without the new approaching fields;
           tapping it switches the side; gear R to Rear and back; the choice kept in user_prefs.json; the Around tile
           on the front ToF; signal and type audits; screenshots (tests/style/dualcam/) day and night; paint time.
  restart  a second start reads the saved side (Rear).
  off      TUKZIE_SW7_DUAL_CAM=0 on the full copy, and the copy without the group: the same deterministic feed; the
           Surroundings and Drive widget trees, their pixels and the banner text identical, and no request to the
           front servers.
Run: TUKZIE_DASHBOARD_DIR=<team Dashboard folder> python tests/test_dual_camera.py
"""
import glob, json, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)
TEAM = os.environ.get("TUKZIE_DASHBOARD_DIR", "").strip()
if not TEAM or not os.path.isdir(os.path.join(TEAM, "app", "pages")):
    sys.exit("Set TUKZIE_DASHBOARD_DIR to a copy of the team's v1.1 Dashboard folder")
SP = tempfile.mkdtemp(prefix="sw7_dualcam_")
OUT = os.path.join(HERE, "style", "dualcam"); os.makedirs(OUT, exist_ok=True)


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
            f.write("\nPATCHES = tuple(p for p in PATCHES if p not in DUAL_CAMERA_PATCHES)\n"
                    "COPIES = tuple(c for c in COPIES if c not in DUAL_CAMERA_COPIES)\n")
        os.remove(os.path.join(src, "sw7_dual_camera.py"))
    r = subprocess.run([sys.executable, os.path.join(INTEG, "deploy", "apply_patches.py"), target, "--source", src,
                        "--native-map", "--team-dir", os.path.join(SP, "nonexistent")], capture_output=True, text=True)
    print(name + ": " + (r.stdout.strip().splitlines()[-1] if r.returncode == 0 else r.stdout + r.stderr))
    if r.returncode:
        sys.exit(1)
    return target


DASH = r'''
import sys, types, os, time, json, threading, hashlib, faulthandler
faulthandler.enable()
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
OUT, MODE = sys.argv[1], sys.argv[2]
fails = []
def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg, flush=True)
    if not cond: fails.append(msg)

# ---- fixtures ------------------------------------------------------------------------------------------------------
ESP = {"age_ms": 400, "soc": 80, "v": 74.2, "i": -6.8, "bms_age_s": 2, "fix": True, "lat": -33.95856, "lon": 18.46,
       "crs": 92, "alt": 41, "vib": 0.035, "vib_dis": 0.01, "imu_hz": [200, 199], "drops": [0, 0], "csq": 18,
       "mqtt": True, "rpm": 900, "spd_raw": 12.3, "fw": "0.7.3"}
def front_tel(approach):
    hz = [{"class": "obstacle", "distance_m": 0.3, "sensor": "right", "band": "immediate", "source": "tof"},
          {"class": "person", "distance_m": 2.6, "bearing_deg": -14, "band": "immediate", "source": "fused"}]
    if approach:
        hz[1].update({"side": "front", "track_id": 7, "approaching": False, "ttc_s": None, "closing_mps": None, "ttc_source": None})
    return {"esp32": None, "tof": {"left_mm": 900, "ahead_mm": 2000, "right_mm": 300, "age_ms": 90},
            "fusion": {"hazards": hz}}
def rear_tel(approach):
    hz = [{"class": "obstacle", "distance_m": 0.4, "sensor": "left", "band": "immediate", "source": "tof"},
          {"class": "car", "distance_m": 5.5, "bearing_deg": 20, "band": "warning", "source": "fused"}]
    if approach:
        hz[1].update({"side": "rear", "track_id": 3, "approaching": True, "ttc_s": 1.6, "closing_mps": 3.4, "ttc_source": "fused"})
    return {"esp32": ESP, "tof": {"left_mm": 400, "ahead_mm": 700, "right_mm": 1500, "age_ms": 110},
            "fusion": {"hazards": hz}}
def front_alerts(approach):
    act = [{"class": "person", "distance_band": "immediate", "confidence": 0.81, "timestamp": "t", "alert_status": "active"},
           {"class": "bicycle", "distance_band": "warning", "confidence": 0.55, "timestamp": "t", "alert_status": "active"}]
    if approach:
        act[0].update({"side": "front", "track_id": 7, "approaching": False, "ttc_s": None, "closing_mps": None})
        act[1].update({"side": "front", "track_id": 9, "approaching": True, "ttc_s": 3.1, "closing_mps": 1.2})
    return {"active": act, "fps": 19.2, "latency_ms": 53}
def rear_alerts(approach):
    act = [{"class": "car", "distance_band": "warning", "confidence": 0.74, "timestamp": "t", "alert_status": "active"},
           {"class": "dog", "distance_band": "monitoring", "confidence": 0.52, "timestamp": "t", "alert_status": "active"}]
    if approach:
        act[0].update({"side": "rear", "track_id": 3, "approaching": True, "ttc_s": 2.1, "closing_mps": 2.6})
        act[1].update({"side": "rear", "track_id": 4, "approaching": False, "ttc_s": None, "closing_mps": None})
    return {"active": act, "fps": 14.6, "latency_ms": 88}

STATE = {"front_cam": {"down": False, "alerts": front_alerts(False), "streams": 0, "active": 0, "hits": 0},
         "front_tof": {"down": False, "telemetry": front_tel(False), "hits": 0},
         "rear_cam": {"down": False, "alerts": rear_alerts(False), "streams": 0, "active": 0, "hits": 0},
         "rear_bridge": {"down": False, "telemetry": rear_tel(False), "hits": 0}}
JPEG = {}

def make_handler(name):
    st = STATE[name]
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _json(self, obj):
            body = json.dumps(obj).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            st["hits"] += 1
            try:
                if st["down"]:
                    self.send_response(503); self.send_header("Content-Length", "0"); self.end_headers(); return
                if self.path == "/telemetry" and "telemetry" in st:
                    return self._json(st["telemetry"])
                if self.path == "/alerts" and "alerts" in st:
                    return self._json(st["alerts"])
                if self.path == "/detections" and "alerts" in st:
                    return self._json({"detections": []})
                if self.path == "/stream" and name in JPEG:
                    st["streams"] += 1; st["active"] += 1
                    try:
                        self.send_response(200)
                        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame"); self.end_headers()
                        t0 = time.monotonic()
                        while not st["down"] and time.monotonic() - t0 < 300:
                            j = JPEG[name]
                            self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(j) + j + b"\r\n")
                            self.wfile.flush(); time.sleep(0.15)
                    finally:
                        st["active"] -= 1
                    return
                self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers()
            except OSError:
                pass
    return H

SERVERS = {}
for name in STATE:
    s = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(name)); s.daemon_threads = True
    threading.Thread(target=s.serve_forever, daemon=True).start()
    SERVERS[name] = f"http://127.0.0.1:{s.server_address[1]}"
os.environ["TUKZIE_FRONT_CAMERA_URL"] = SERVERS["front_cam"]
os.environ["TUKZIE_FRONT_TOF_URL"] = SERVERS["front_tof"]
os.environ["TUKZIE_REAR_CAMERA_URL"] = SERVERS["rear_cam"]
os.environ["TUKZIE_TELEMETRY_URL"] = SERVERS["rear_bridge"] if MODE != "off" else "http://127.0.0.1:9"   # off: fed by hand

from PySide6.QtWidgets import QApplication, QWidget, QLabel, QAbstractButton
from PySide6.QtCore import QTimer, QRect, QPoint, QEventLoop, Qt, QByteArray, QBuffer, QIODevice, QRectF
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QFontMetricsF, QPen
from PySide6.QtTest import QTest
a = QApplication(sys.argv)

def wait(cond, ms):
    t = time.monotonic()
    while not cond() and (time.monotonic() - t) * 1000 < ms:
        a.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50); time.sleep(0.01)
    return cond()
def spin(ms):
    wait(lambda: False, ms)
def px(widget):
    f = widget.font(); return f.pixelSize() if f.pixelSize() > 0 else round(f.pointSizeF() * 96 / 72)

def jpeg(label, mark, wd=960, ht=540):
    """A drawn test image: sky, road, and a coloured block on the LEFT half (so mirroring shows), not camera data."""
    img = QImage(wd, ht, QImage.Format.Format_RGB888)
    p = QPainter(img)
    p.fillRect(0, 0, wd, int(ht * 0.55), QColor("#9DB7C9")); p.fillRect(0, int(ht * 0.55), wd, ht, QColor("#7B7468"))
    p.fillRect(int(wd * 0.06), int(ht * 0.30), int(wd * 0.22), int(ht * 0.40), QColor(mark))
    f = QFont("Arial"); f.setPixelSize(30); p.setFont(f); p.setPen(QColor("white"))
    p.drawText(QRectF(0, ht * 0.80, wd, 40), Qt.AlignmentFlag.AlignCenter, label + " TEST IMAGE, not camera data")
    p.end()
    ba = QByteArray(); b = QBuffer(ba); b.open(QIODevice.OpenModeFlag.WriteOnly); img.save(b, "JPG", 85); return bytes(ba)
JPEG["front_cam"] = jpeg("FRONT", "#1E8E3E")      # green block on the left
JPEG["rear_cam"] = jpeg("REAR", "#1A56DB")        # blue block on the left (on screen: right, mirrored)

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
    found = S.audit_signal(w, ignore=(view.slab if view is not None else None,))
    check(not found, f"{tag}: signal audit: {S.ok_audit(found) or 'clean'}")
    bad = [(S.describe(x), p) for x, p in S.type_audit(page)]
    check(not bad, f"{tag}: text only in 13, 16, 22 or 120 to 180 px: {bad}")
    cl = clipped(page)
    check(not cl, f"{tag}: no clipped labels: {cl}")

def colour_share(img, rect, test):
    n = hit = 0
    for x in range(rect.left(), rect.right(), 6):
        for y in range(rect.top(), rect.bottom(), 6):
            c = img.pixelColor(x, y); n += 1
            hit += 1 if test(c) else 0
    return hit / max(1, n)
GREEN = lambda c: c.green() > 110 and c.red() < 90 and c.blue() < 110
BLUE = lambda c: c.blue() > 160 and c.red() < 80 and c.green() < 130

def row_mains(view):
    return [r.main_text for r in view.rows_w if r.isVisible()]

def no_zero(view):
    vals = [v for v, _w in view.figure.values().values()]
    return not any(v.startswith("0 ") or v == "0" or v == "0.00 m" for v in vals) and view.hero.text() not in ("0", "0.00")

def run():
    d = w.dashboard
    d.status.timer.stop(); d.status.clock.setText("14:28")
    if MODE == "off":
        return run_off(d)
    dual = getattr(d, "sw7_dual", None)
    check(dual is not None, "the dual camera controller is installed (default on)")
    if dual is None:
        return finish()
    from app.widgets import sw7_style as S
    from app.pages import sw7_dual_camera as DC
    from app.data.vehicle_state import Gear
    view, cam, hb = d.sw7_surroundings, d.front_camera, d.hazard_banner
    if MODE == "restart":
        check(dual.selected == "rear" and dual.toggle.buttons["rear"].isChecked(), f"after a restart the saved side is shown: {dual.selected}")
        d.switch_page_id("sensors")
        check(wait(lambda: view.slab.image is not None and STATE["rear_cam"]["active"] > 0, 8000) and STATE["front_cam"]["streams"] == 0,
              "and it streams the rear camera, not the front")
        return finish()
    check(dual.selected == "front", "a fresh dashboard starts on Front")
    # ---- the toggle ---------------------------------------------------------------------------------------------
    d.switch_page_id("sensors"); a.processEvents()
    tg = dual.toggle
    bf, br = tg.buttons["front"], tg.buttons["rear"]
    check(bf.isVisible() and br.isVisible() and bf.height() >= 64 and br.height() >= 64 and bf.width() >= 64,
          f"Front | Rear: two visible targets at least 64 px tall ({bf.width()} x {bf.height()}, {br.width()} x {br.height()})")
    check(bf.text() == "Front" and br.text() == "Rear" and bf.isChecked() and not br.isChecked(), "Front selected")
    slab_r = QRect(view.slab.mapTo(w, QPoint(0, 0)), view.slab.size()); tg_r = QRect(tg.mapTo(w, QPoint(0, 0)), tg.size())
    check(slab_r.contains(tg_r) and not tg_r.intersects(QRect(view.chip.mapTo(w, QPoint(0, 0)), view.chip.size())),
          "the toggle sits on the camera frame, clear of the status chip")
    # ---- front -------------------------------------------------------------------------------------------------
    check(wait(lambda: view.slab.image is not None, 8000), "front: the front stream shows")
    check(wait(lambda: len(row_mains(view)) >= 3 and view.figure.values()["right"][0] == "0.30 m", 5000), "front: hazards and ToF arrive")
    check(STATE["front_cam"]["streams"] >= 1 and STATE["rear_cam"]["streams"] == 0, f"front: only the front stream is fetched (front {STATE['front_cam']['streams']}, rear {STATE['rear_cam']['streams']})")
    check(STATE["rear_cam"]["hits"] > 0 and STATE["front_tof"]["hits"] > 0, "both sides' alerts and the front ToF are polled (for the banner)")
    vals = view.figure.values()
    check(vals["left"][0] == "0.90 m" and vals["ahead"][0] == "Clear" and vals["right"][0] == "0.30 m", f"front ToF figure from the Pi 5 board: {vals}")
    check(view.figure.side == "front" and view.slab.side == "front", "front: the figure and the frame say FRONT")
    mains = row_mains(view)
    check(mains[:2] == ["Obstacle 0.30 m right", "Person 2.6 m left"] and "Bicycle under 8 m ahead" in mains,
          f"front: the Pi 5 fusion and the front camera's alerts, nearest first: {mains}")
    check(view.link_chip.text() == "Front sensors live", f"front: link chip {view.link_chip.text()!r}")
    check(view.ride.text().startswith("Vibration 0.04"), f"the ride row stays on the Pi 4's ESP32: {view.ride.text()!r}")
    img = w.grab().toImage(); sl = view.slab.geometry().translated(view.mapTo(w, QPoint(0, 0)))
    left_half = QRect(sl.left() + 20, sl.top() + 120, sl.width() // 2 - 40, sl.height() - 200)
    right_half = QRect(sl.center().x() + 20, sl.top() + 120, sl.width() // 2 - 40, sl.height() - 200)
    check(colour_share(img, left_half, GREEN) > 0.08 and colour_share(img, right_half, GREEN) < 0.02, "front: not mirrored (the mark stays on the left)")
    check(no_zero(view), "front: no 0 shown for a reading")
    audits(d, d.sensors, "day front")
    shoot("day_surroundings_front")
    times["surroundings_front"] = paint_ms()
    # ---- rear -------------------------------------------------------------------------------------------------
    QTest.mouseClick(br, Qt.MouseButton.LeftButton); a.processEvents()
    check(dual.selected == "rear" and br.isChecked() and not bf.isChecked(), "tapping Rear selects Rear")
    check(view.slab.image is None, "the front picture goes at once (nothing stale from the other side)")
    check(wait(lambda: view.slab.image is not None, 8000), "rear: the rear stream shows")
    check(wait(lambda: STATE["front_cam"]["active"] == 0, 6000) and STATE["rear_cam"]["active"] >= 1, "rear: the front stream is closed, only the rear one open")
    check(wait(lambda: view.figure.values()["right"][0] == "0.40 m", 4000), "rear: rear ToF arrives")
    vals = view.figure.values()
    check(vals["left"][0] == "Clear" and vals["right"][0] == "0.40 m" and vals["ahead"][0] == "0.70 m",
          f"rear: the board's left (0.40 m) is the driver's right, its right (1.5 m) the driver's left: {vals}")
    mains = row_mains(view)
    check(mains[:2] == ["Obstacle 0.40 m right", "Car 5.5 m left"] and "Dog under 15 m behind" in mains,
          f"rear: hazards in the driver's frame, the straight back reading behind: {mains}")
    check(view.link_chip.text() == "Rear sensors live" and view.figure.side == "rear" and view.slab.side == "rear", f"rear: chip {view.link_chip.text()!r}, REAR on the figure and frame")
    img = w.grab().toImage()
    check(colour_share(img, right_half, BLUE) > 0.08 and colour_share(img, left_half, BLUE) < 0.02, "rear: mirrored (the mark on the image's left shows on the right)")
    check(not hb.isVisible() or "REAR" not in hb.text.text(), "on Surroundings Rear the banner does not repeat the rear")
    audits(d, d.sensors, "day rear")
    shoot("day_surroundings_rear")
    times["surroundings_rear"] = paint_ms()
    check(json.load(open(os.path.join("app", "asis", "data", "user_prefs.json"), encoding="utf-8"))["global"].get("sw7_camera_side") == "rear",
          "the driver's choice is saved in user_prefs.json")
    # ---- the banner, without and with the approaching fields --------------------------------------------------------
    d.switch_page_id("driving"); a.processEvents()
    check(wait(lambda: hb.isVisible() and "FRONT" in hb.text.text(), 3000), f"Drive: the banner shows: {hb.text.text()!r}")
    t = hb.text.text()
    check(t.startswith("OBSTACLE 0.3 M FRONT RIGHT") and "(+" in t, f"without approaching fields: the nearest immediate obstacle, labelled Front: {t!r}")
    check(dual.banner_message()[2] == "front", "its side is Front")
    shoot("day_drive_banner_obstacle")
    STATE["front_cam"]["alerts"] = front_alerts(True); STATE["rear_cam"]["alerts"] = rear_alerts(True)
    STATE["front_tof"]["telemetry"] = front_tel(True); STATE["rear_bridge"]["telemetry"] = rear_tel(True)
    check(wait(lambda: hb.text.text().startswith("CAR APPROACHING · REAR · 1.6 s") and dual.sides["front"].alerts.get("active", [{}])[-1].get("approaching")
               and dual.sides["rear"].alerts.get("active", [{}])[0].get("approaching"), 4000),
          f"with the fields: approaching first, labelled Rear, the fused TTC (smaller than the camera's for track 3): {hb.text.text()!r}")
    msg = dual.banner_message()
    check(msg[0] == "crit", "TTC under 2 s: red")
    items = DC.banner_items("front", dual.sides["front"].telemetry, dual.sides["front"].alerts)
    check(items[0][2] == "BICYCLE APPROACHING · FRONT · 3.1 s" and items[0][1] == "warn", f"TTC 3.1 s: amber, before the obstacles: {items[:2]}")
    shoot("day_drive_banner")
    times["drive"] = paint_ms()
    QTest.mouseClick(hb.text, Qt.MouseButton.LeftButton); a.processEvents()
    check(d.stack.currentWidget() is d.sensors and dual.selected == "rear", "tapping the banner opens Surroundings on that side (Rear)")
    dual.set_side("front", user=True); a.processEvents()
    check(wait(lambda: hb.isVisible() and "REAR" in hb.text.text(), 3000), f"on Surroundings Front, the rear's approaching car still shows: {hb.text.text()!r}")
    check(wait(lambda: any("Approaching · 3.1 s" in r.detail_text for r in view.rows_w if r.isVisible()), 3000),
          f"the alert list shows the TTC of an approaching object: {[r.detail_text for r in view.rows_w if r.isVisible()]}")
    QTest.mouseClick(hb.text, Qt.MouseButton.LeftButton); a.processEvents()
    check(dual.selected == "rear", "tapping it switches Surroundings to Rear")
    check(any(r.detail_text.startswith("Approaching · 1.6 s") for r in view.rows_w if r.isVisible()), "rear list: the approaching car with its TTC")
    shoot("day_surroundings_rear_approaching")
    # ---- one side offline -------------------------------------------------------------------------------------------
    dual.set_side("front", user=True)
    STATE["front_cam"]["down"] = True; STATE["front_tof"]["down"] = True
    check(wait(lambda: view.slab.image is None and view.figure.values()["left"][0] == "--", 9000), "front offline: no picture, ToF --")
    check(wait(lambda: "offline" in cam.status_label.text().lower(), 5000), f"front offline: the camera status says so: {cam.status_label.text()!r}")
    vals = view.figure.values()
    check(all(v == "--" and wd == "No reading" for v, wd in vals.values()), f"front offline: every ToF zone -- and No reading: {vals}")
    check(view.hero.text() == "--" and view.link_chip.text() == "Front sensors offline" and view.empty.text() == "No sensor data" and not row_mains(view),
          f"front offline: hero {view.hero.text()!r}, chip {view.link_chip.text()!r}, {view.empty.text()!r}")
    check(no_zero(view), "front offline: never 0")
    audits(d, d.sensors, "day front offline")
    shoot("day_surroundings_front_offline")
    QTest.mouseClick(br, Qt.MouseButton.LeftButton); a.processEvents()
    check(wait(lambda: view.slab.image is not None and view.figure.values()["right"][0] == "0.40 m", 8000), "the rear side keeps working")
    dual.set_side("front", user=True)
    STATE["front_cam"]["down"] = False; STATE["front_tof"]["down"] = False
    check(wait(lambda: view.slab.image is not None and view.figure.values()["right"][0] == "0.30 m", 9000), "front back: picture and ToF again")
    # ---- the Around tile ----------------------------------------------------------------------------------------------
    tile = d.driving.sw7_tiles["around"]
    check(tile.metres.get("right") == 0.3 and tile.metres.get("left") == 0.9 and tile.label == "AROUND · FRONT",
          f"Drive's Around tile is on the front ToF: {tile.metres} {tile.label!r}")
    # ---- gear R ---------------------------------------------------------------------------------------------------
    d.switch_page_id("driving")
    d.vehicle_data.set_gear(Gear.R)
    check(wait(lambda: dual.selected == "rear" and d.stack.currentWidget() is d.sensors, 3000), "gear R: Surroundings on Rear (in place of the reverse page)")
    d.vehicle_data.set_gear(Gear.D)
    check(wait(lambda: dual.selected == "front" and d.stack.currentWidget() is d.driving, 3000), "leaving R: back to Front and Driving")
    check(json.load(open(os.path.join("app", "asis", "data", "user_prefs.json"), encoding="utf-8"))["global"].get("sw7_camera_side") == "front",
          "the automatic switch in R is not saved as the driver's choice")
    # ---- night ------------------------------------------------------------------------------------------------------
    S.set_night(True); a.processEvents(); spin(300)
    d.switch_page_id("sensors"); dual.set_side("front"); spin(1500)
    audits(d, d.sensors, "night front"); shoot("night_surroundings_front")
    dual.set_side("rear"); wait(lambda: view.slab.image is not None, 6000); spin(600)
    audits(d, d.sensors, "night rear"); shoot("night_surroundings_rear")
    STATE["front_cam"]["down"] = True; STATE["front_tof"]["down"] = True
    dual.set_side("front"); wait(lambda: view.figure.values()["left"][0] == "--", 9000); spin(300)
    shoot("night_surroundings_front_offline")
    STATE["front_cam"]["down"] = False; STATE["front_tof"]["down"] = False
    d.switch_page_id("driving"); wait(lambda: hb.isVisible(), 4000); spin(800)
    shoot("night_drive_banner")
    S.set_night(False)
    # paint with both streams configured, the selected one streaming
    d.switch_page_id("sensors"); dual.set_side("rear", user=True); wait(lambda: view.slab.image is not None, 6000); spin(500)
    times["surroundings_rear_streaming"] = paint_ms()
    dual.set_side("front", user=False); wait(lambda: view.slab.image is not None, 6000); spin(500)
    times["surroundings_front_streaming"] = paint_ms()
    finish()

def dump(page):
    out = []
    for wd in [page] + page.findChildren(QWidget):
        if not wd.isVisible():
            continue
        text = wd.text() if isinstance(wd, (QLabel, QAbstractButton)) else ""
        g = QRect(wd.mapTo(w, QPoint(0, 0)), wd.size())
        out.append([type(wd).__name__, wd.objectName(), g.x(), g.y(), g.width(), g.height(), px(wd), text])
    return out

def run_off(d):
    """The deterministic single-camera feed (as test_style_pages): telemetry through the provider's signal, alerts and
    a frame straight into the camera page."""
    check(getattr(d, "sw7_dual", None) is None, "TUKZIE_SW7_DUAL_CAM=0 (or no group): no dual camera controller")
    try:
        d.telemetry.stop()
    except Exception:
        pass
    cam = d.front_camera
    cam._alert_timer.stop(); cam._start_stream = lambda: None; cam._stop_stream()
    if cam._alert_reply is not None:
        cam._alert_reply.finished.disconnect(); cam._alert_reply.abort(); cam._alert_reply = None
    spin(300)
    tel = rear_tel(False); tel["fusion"]["hazards"][0]["band"] = "immediate"
    d.switch_page_id("sensors"); a.processEvents()
    d.telemetry.telemetry_updated.emit(tel); d.sensors._watchdog.stop()
    cam._streaming_wanted = False; cam._apply_alerts(rear_alerts(False)); cam._streaming_wanted = True
    cam._feed(JPEG["rear_cam"]); cam._stale_timer.stop(); a.processEvents(); spin(300)
    trees, pix = {}, {}
    trees["sensors"] = dump(d.sensors)
    img = d.sensors.grab().toImage(); pix["sensors"] = hashlib.sha1(bytes(img.constBits())).hexdigest()
    d.switch_page_id("driving"); a.processEvents(); spin(1500)
    d.telemetry.telemetry_updated.emit(tel); a.processEvents(); spin(300)
    trees["driving"] = dump(d.driving)
    img = d.driving.grab().toImage(); pix["driving"] = hashlib.sha1(bytes(img.constBits())).hexdigest()
    trees["banner"] = [d.hazard_banner.isVisible(), d.hazard_banner.text.text()]
    check(d.hazard_banner.isVisible() and " ".join(d.hazard_banner.text.text().split()).startswith("OBSTACLE 0.4 M LEFT"),
          f"single camera: the banner as before: {d.hazard_banner.text.text()!r}")
    spin(1500)
    check(STATE["front_cam"]["hits"] == 0 and STATE["front_tof"]["hits"] == 0, "no request to the front camera or the front ToF")
    with open(f"{OUT}/../tree_dualcam_{sys.argv[3]}.json", "w", encoding="utf-8") as f:
        json.dump({"trees": trees, "pix": pix}, f)
    finish()

def finish():
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
               TUKZIE_SKIP_LOGIN="1", TUKZIE_SW7_THEME="0", TUKZIE_CAMERA_URL="http://127.0.0.1:9",
               TUKZIE_TILE_URL="http://127.0.0.1:9/{z}/{x}/{y}.png", TUKZIE_TILE_CACHE=os.path.join(SP, "tiles"),
               TUKZIE_WEATHER_URL="http://127.0.0.1:9/v1/forecast", TUKZIE_REVERSE_URL="http://127.0.0.1:9/reverse",
               TUKZIE_WEATHER_CACHE=os.path.join(SP, "weather", "last.json"),
               PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    for k in ("TUKZIE_SW7_STYLE", "TUKZIE_SW7_LAYOUT", "TUKZIE_SW7_NIGHT", "TUKZIE_SW7_DUAL_CAM", "TUKZIE_TELEMETRY_URL", "TUKZIE_REAR_TOF_SWAP",
              "TUKZIE_FRONT_CAMERA_URL", "TUKZIE_FRONT_TOF_URL", "TUKZIE_REAR_CAMERA_URL"):
        env.pop(k, None)
    env.update(extra)
    if sys.platform == "win32":
        env.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
    return env


def run(target, args, extra, label):
    r = subprocess.run([sys.executable, "-c", DASH] + args, cwd=target, env=env_for(extra), capture_output=True,
                       text=True, timeout=900, encoding="utf-8", errors="replace")
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
ok, paint = run(full, [OUT, "dual"], {}, "dual (default)")
ok2, _ = run(full, [OUT, "restart"], {}, "restart (the saved side)")
base = build("base", True)
ok3, _ = run(full, [OUT, "off", "off"], {"TUKZIE_SW7_DUAL_CAM": "0"}, "off (TUKZIE_SW7_DUAL_CAM=0)")
ok4, _ = run(base, [OUT, "off", "base"], {}, "base (without the dual camera group)")
ok = ok and ok2 and ok3 and ok4
trees = {}
for m in ("off", "base"):
    path = os.path.join(OUT, "..", f"tree_dualcam_{m}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            trees[m] = json.load(f)
        os.remove(path)
if len(trees) == 2:
    for key in trees["base"]["trees"]:
        same = trees["off"]["trees"][key] == trees["base"]["trees"][key]
        diff = [(x, y) for x, y in zip(trees["off"]["trees"][key], trees["base"]["trees"][key]) if x != y][:3]
        print(("ok   " if same else "FAIL ") + f"TUKZIE_SW7_DUAL_CAM=0: {key} identical to the build without the group"
              + ("" if same else f" {diff}"))
        ok = ok and same
    for key in trees["base"]["pix"]:
        same = trees["off"]["pix"][key] == trees["base"]["pix"][key]
        print(("ok   " if same else "FAIL ") + f"TUKZIE_SW7_DUAL_CAM=0: {key} pixels identical to the build without the group")
        ok = ok and same
else:
    print("FAIL the off-switch comparison did not run"); ok = False
print("Paint time of a full 1280 x 800 frame (QWidget.grab, median of 15): "
      + ", ".join(f"{k} {v:.1f} ms" for k, v in sorted(paint.items())))
shutil.rmtree(SP, ignore_errors=True)
if not ok:
    sys.exit(1)
print("ALL DUAL CAMERA TESTS PASSED")
