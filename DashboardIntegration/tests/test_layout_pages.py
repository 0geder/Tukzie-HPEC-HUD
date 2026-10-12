"""Offscreen test of the layout pass on Diagnostics, Front camera and Sensors (agent C,
Planning/layout-improvements-prompt.md; sources: Planning/google-stitch-dashboard-prompt.md sections 1, 2, 3.4,
3.7 and 3.8).

Builds two patched copies of the team's v1.1 dashboard (TUKZIE_DASHBOARD_DIR):
  ref  the integration as it was before this pass (sensors_page.py and front_camera_page.py from LAYOUT_BASE,
       PATCHES without LAYOUT_PAGES_PATCHES);
  new  the current integration (all PATCHES, sw7_layout_pages.py).
and checks:
  1. the switch: with TUKZIE_SW7_LAYOUT=0 the three pages, fed the same state, telemetry and alerts, render
     pixel for pixel like ref, and none of the new widgets exist;
  2. sizes with the layout on (default): Diagnostics has the four cards (Drive, Energy, Position, Link), values
     18 px, labels at least 13 px, the advice list folded behind a 64 px row that opens it, no ToF or vibration
     (they are on Sensors), the ride card hidden but still feeding the Link card; Front camera alert rows 64 px
     with the class 24 px, the status a 28 px chip, no text under 16 px, nearest band first; Sensors has the
     tuk-tuk outline (no gauges) with the distances in 40 px that fit their boxes and keep clear of the body,
     64 px hazard rows, a 120 x 36 link chip, and the outline and hazards above the fold; no visible label
     clipped on any of the three;
  3. the obstacle pill reads the status bar height (38 or 48 px) rather than assuming it;
  4. touch scrolling is still on Diagnostics and Sensors in the full dashboard;
and saves before (TUKZIE_SW7_LAYOUT=0) and after screenshots of the full 1280 x 800 window in tests/layout/pages/:
Sensors with near and with far readings, Front camera with alerts, Diagnostics (and with the details open).
The readings and alerts are made-up TEST values, not data.

Run: TUKZIE_DASHBOARD_DIR=<copy of v1.1 Dashboard> python DashboardIntegration/tests/test_layout_pages.py
"""
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)
REPO = os.path.dirname(INTEG)
LAYOUT_BASE = "9b2bed3"        # the commit before this pass: the reference for TUKZIE_SW7_LAYOUT=0
TEAM = os.environ.get("TUKZIE_DASHBOARD_DIR", "").strip()
if not TEAM or not os.path.isdir(os.path.join(TEAM, "app", "pages")):
    sys.exit("Set TUKZIE_DASHBOARD_DIR to a copy of the team's v1.1 Dashboard folder")
sys.path.insert(0, HERE)
import dashboard_patches as dp  # noqa: E402

OUT = os.path.join(HERE, "layout", "pages")
os.makedirs(OUT, exist_ok=True)
SP = tempfile.mkdtemp(prefix="sw7_layout_pages_")


def build(name, copies, patches, overrides=None):
    root = os.path.join(SP, name)
    shutil.copytree(os.path.join(TEAM, "app"), os.path.join(root, "app"),
                    ignore=shutil.ignore_patterns("__pycache__", "logs"))
    for src, dst in copies:
        os.makedirs(os.path.dirname(os.path.join(root, dst)), exist_ok=True)
        if overrides and src in overrides:
            with open(os.path.join(root, dst), "w", encoding="utf-8", newline="\n") as f:
                f.write(overrides[src])
        else:
            shutil.copy2(os.path.join(INTEG, src), os.path.join(root, dst))
    for rel, old, new in patches:
        path = os.path.join(root, rel)
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
        if "\r\n" in text:
            old, new = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
        assert text.count(old) == 1, f"anchor not found once in {rel}: {old[:60]!r}"
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text.replace(old, new))
    return root


def git_show(path):
    r = subprocess.run(["git", "-C", REPO, "show", f"{LAYOUT_BASE}:{path}"], capture_output=True, text=True,
                       encoding="utf-8")
    if r.returncode:
        sys.exit(f"cannot read {path} at {LAYOUT_BASE}: {r.stderr.strip()}")
    return r.stdout


ref_patches = tuple(p for p in dp.PATCHES if p not in dp.LAYOUT_PAGES_PATCHES)
ref_copies = tuple(c for c in dp.COPIES if c not in dp.LAYOUT_PAGES_COPIES)
ref = build("ref", ref_copies, ref_patches,
            {"sensors_page.py": git_show("DashboardIntegration/sensors_page.py"),
             "front_camera_page.py": git_show("DashboardIntegration/front_camera_page.py")})
new = build("new", dp.COPIES, dp.PATCHES)
print(f"built ref ({len(ref_patches)} edits) and new ({len(dp.PATCHES)} edits) in {SP}")

WORKER = r'''
import os, sys, time, types
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
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QScrollArea, QScroller
a = QApplication(sys.argv)
OUT, MODE, SHOTS = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
LAYOUT = MODE == "on"
fails = []
def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)

ESP = {"age_ms": 400, "soc": 80, "v": 74.2, "i": 20.8, "bms_age_s": 2, "fix": True, "lat": -33.95856, "lon": 18.46,
       "crs": 92, "alt": 41, "vib": 0.035, "vib_dis": 0.01, "imu_hz": [200, 199], "drops": [0, 0], "csq": 18,
       "mqtt": True, "rpm": 900, "spd_raw": 12.3, "fw": "0.7.3"}
NEAR = {"esp32": ESP, "tof": {"left_mm": 900, "ahead_mm": 450, "right_mm": 1500, "age_ms": 120},
        "fusion": {"hazards": [
            {"class": "obstacle", "distance_m": 0.45, "sensor": "ahead", "band": "immediate", "source": "tof"},
            {"class": "obstacle", "distance_m": 0.9, "sensor": "left", "band": "warning", "source": "tof"},
            {"class": "person", "distance_m": 2.6, "bearing_deg": 4, "band": "immediate", "source": "fused"},
            {"class": "bicycle", "distance_m": 6.0, "bearing_deg": -22, "band": "warning", "source": "camera"}]}}
FAR = {"esp32": ESP, "tof": {"left_mm": 1350, "ahead_mm": 1100, "right_mm": 1800, "age_ms": 120},
       "fusion": {"hazards": []}}
ALERTS = {"active": [
    {"class": "car", "distance_band": "monitoring", "confidence": 0.71, "timestamp": "t", "alert_status": "active"},
    {"class": "person", "distance_band": "immediate", "confidence": 0.63, "timestamp": "t", "alert_status": "active"},
    {"class": "bicycle", "distance_band": "warning", "confidence": 0.55, "timestamp": "t", "alert_status": "active"}],
    "fps": 7.0, "latency_ms": 182}

def jpeg(w=640, h=480):
    img = QImage(w, h, QImage.Format.Format_RGB888); img.fill(QColor("#3A4654"))
    p = QPainter(img); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(0, int(h * 0.62), w, h, QColor("#2B2F33"))
    p.setPen(QColor("#FF1744")); p.drawRect(250, 170, 90, 220)
    p.setPen(QColor("#FFD600")); p.drawRect(430, 230, 120, 120)
    p.setPen(QColor("white")); f = QFont("Arial"); f.setPixelSize(20); p.setFont(f)
    p.drawText(250, 162, "person 0.63"); p.drawText(430, 222, "bicycle 0.55")
    p.drawText(QRectF(0, 20, w, 30), Qt.AlignmentFlag.AlignCenter, "TEST IMAGE, not camera data")
    p.end()
    ba = QByteArray(); b = QBuffer(ba); b.open(QIODevice.OpenModeFlag.WriteOnly); img.save(b, "JPG"); return bytes(ba)
FRAME = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg() + b"\r\n"

def labels(root):
    return [l for l in root.findChildren(QLabel) if l.isVisibleTo(root) and QLabel.text(l)]

def clipped(root):
    out = []
    for l in labels(root):
        if l.wordWrap() or l.textFormat() == Qt.TextFormat.RichText:
            continue
        need = QFontMetricsF(l.font()).horizontalAdvance(QLabel.text(l))
        if need > l.contentsRect().width() + 1:
            out.append((QLabel.text(l), round(need), l.contentsRect().width()))
    return out

from app.theme import THEME
from app.data.vehicle_state import VehicleState, Gear
from app.pages.diagnostics_page import DiagnosticsPage
from app.pages.sensors_page import SensorsPage
from app.pages.front_camera_page import FrontCameraPage
STATE = VehicleState(speed_kmh=25.0, gear=Gear.D, throttle_pct=40.0, brake_pct=0.0, signed_battery_power_kw=1.5,
                     soc_pct=79.9, range_km=55.9, battery_temp_c=32.0, motor_temp_c=48.0, ambient_temp_c=19.0,
                     odometer_km=0.16, incline_deg=1.2, latitude=-33.95856, longitude=18.46, altitude_m=None)
STATE.data_source = "sw7_simulated_drive"
W, H = 1280, 648         # content area at 1280 x 800: 48 px status bar, 72 px nav bar, 32 px simulated strip

def standalone(cls):
    page = cls(); page.setStyleSheet(THEME.stylesheet()); page.resize(W, H)
    t = getattr(page, "_alert_timer", None)
    if t is not None: t.stop()          # no network poll between the reference and the switch run
    page.show(); a.processEvents()
    return page

# ---- 1. standalone pages, the same input in every mode -------------------------------------------------
diag = standalone(DiagnosticsPage)
diag.ride_card.set_endpoint("127.0.0.1", "TUKZIE_TELEMETRY_URL")
diag.ride_card.set_telemetry(NEAR)
diag.update_state(STATE); a.processEvents()
diag.grab().save(f"{OUT}/page_diagnostics.png")
sens = standalone(SensorsPage)
sens.set_telemetry(NEAR); a.processEvents(); sens.grab().save(f"{OUT}/page_sensors_near.png")
sens.set_telemetry(FAR); a.processEvents(); sens.grab().save(f"{OUT}/page_sensors_far.png")
cam = standalone(FrontCameraPage)
cam._stop_stream(); cam._streaming_wanted = False
cam._feed(FRAME); cam._stale_timer.stop()
cam._apply_alerts(ALERTS); a.processEvents(); cam.grab().save(f"{OUT}/page_camera.png")

if MODE == "off":
    from app.pages.front_camera_page import AlertRow
    from app.pages.sensors_page import TukTukView
    check(not hasattr(diag, "_sw7_layout") and diag.ride_card.isVisibleTo(diag), "switch off: Diagnostics is the team's page with the ride card")
    check(not sens.findChildren(TukTukView) and hasattr(sens, "gauges"), "switch off: Sensors has the three gauges, no outline")
    check(not cam.findChildren(AlertRow), "switch off: Front camera has the earlier alert labels")
elif LAYOUT:
    from app.pages.front_camera_page import AlertRow, StatusChip
    from app.pages.sensors_page import TukTukView, zone_text
    # Diagnostics
    L = diag._sw7_layout
    titles = [c.title.text() for c in L["cards"]]
    check(titles == ["DRIVE", "ENERGY", "POSITION", "LINK"], f"Diagnostics cards: {titles}")
    vals = [v for c in L["cards"] for v in c.values.values()]
    caps = [c_ for c in L["cards"] for c_ in c.captions]
    check(all(v.font().pixelSize() >= 18 for v in vals), "Diagnostics values 18 px")
    check(all(c.font().pixelSize() >= 13 for c in caps) and all(c.title.font().pixelSize() >= 13 for c in L["cards"]),
          "Diagnostics labels and card headers at least 13 px")
    check(L["toggle"].height() >= 64 and not L["details"].isVisible(), f"advice folded behind a {L['toggle'].height()} px row")
    seen = " | ".join(QLabel.text(l) for l in labels(diag))
    check("ToF" not in seen and "Vibration" not in seen.title() and not diag.ride_card.isVisibleTo(diag),
          "no ToF or vibration on Diagnostics (they are on Sensors); ride card hidden")
    link = L["link"].values
    check(link["link"].text() == "Live" and link["pi4"].text() == "On this Pi" and link["csq"].text() == "18 / 31"
          and link["imu_hz"].text() == "200 / 199 Hz", f"Link card from the ride card: {link['link'].text()}, {link['pi4'].text()}, {link['csq'].text()}")
    check(diag._values["Source"].text() == "Simulated drive" and L["raw"]["Source"].text() == "sw7_simulated_drive",
          "source in plain words, the raw string in the details")
    check(diag._values["Speed"].text() == "25.0 km/h" and diag._values["Battery SOC"].text() == "79.9 %", "update_state fills the cards")
    check(not clipped(diag), f"Diagnostics: no clipped labels {clipped(diag)}")
    L["toggle"].click(); a.processEvents()
    small = [(QLabel.text(l), l.font().pixelSize()) for l in labels(diag) if l.font().pixelSize() < 13]
    check(L["details"].isVisible() and not small, f"the row opens the advice list; nothing under 13 px {small[:3]}")
    diag.grab().save(f"{OUT}/page_diagnostics_details.png")
    L["toggle"].click(); a.processEvents()
    check(not L["details"].isVisible(), "and folds it again")
    # Front camera
    rows = cam.findChildren(AlertRow)
    check(len(rows) == 3 and all(r.height() == 64 for r in rows), f"camera alert rows 64 px: {[r.height() for r in rows]}")
    check([r.main.text() for r in rows] == ["Person", "Bicycle", "Car"], "nearest band first")
    check(all(r.main.font().pixelSize() >= 24 for r in rows) and rows[0].detail.text() == "Immediate \u00b7 under 3 m",
          "class 24 px, band and distance under it")
    chip = cam.status_label
    check(isinstance(chip, StatusChip) and chip.height() == 28 and chip.font().pixelSize() >= 16, "status chip 28 px, 16 px text")
    small = [(QLabel.text(l), l.font().pixelSize()) for l in labels(cam) if l.font().pixelSize() < 16]
    check(not small, f"no camera text under 16 px {small}")
    check(not clipped(cam), f"camera: no clipped labels {clipped(cam)}")
    cam.status_label.setText("Live"); cam._apply_alerts(ALERTS)
    check(QLabel.text(chip) == "Live \u00b7 7.0 fps" and chip.text() == "Live", f"chip shows {QLabel.text(chip)!r}, text() stays 'Live'")
    # Sensors
    sens.set_telemetry(NEAR); a.processEvents()
    tuk = sens.findChildren(TukTukView)
    check(len(tuk) == 1 and not hasattr(sens, "gauges"), "Sensors: the tuk-tuk outline, no gauges")
    tuk = tuk[0]
    body, sensors, boxes = tuk.geometry_of()
    fm = QFontMetricsF(THEME.font(40, QFont.Weight.Black))
    widest = max(fm.horizontalAdvance(t) for t in ("0.45 m", "1.15 m", "Clear", "--"))
    inside = QRectF(0, 0, tuk.width(), tuk.height())
    check(all(inside.contains(b) for b in boxes.values()) and all(b.width() >= widest for b in boxes.values()),
          f"40 px distances fit their boxes (widest {widest:.0f} px, boxes {[round(b.width()) for b in boxes.values()]})")
    check(not any(b.intersects(body) for b in boxes.values()) and not boxes["left"].intersects(boxes["right"]),
          "distances keep clear of the body and of each other")
    check(boxes["left"].center().x() < body.left() < body.right() < boxes["right"].center().x()
          and boxes["ahead"].bottom() + 88 <= sensors["ahead"].y(), "each distance by its sensor, clear of its zone")
    check(zone_text(0.45) == ("0.45 m", "Very close") and zone_text(0.9) == ("0.90 m", "Close")
          and zone_text(1.5) == ("Clear", "over 1.2 m") and zone_text(None) == ("--", "No reading"), "zone words")
    check(tuk.metres == {"left": 0.9, "ahead": 0.45, "right": 1.5}, f"readings reach the outline: {tuk.metres}")
    hz = sens.findChildren(AlertRow)
    check(len(hz) == 4 and all(r.height() == 64 for r in hz) and hz[0].main.text() == "Obstacle 0.45 m ahead",
          f"hazard rows 64 px, nearest first: {[r.main.text() for r in hz]}")
    check(sens.pill.size().width() == 120 and sens.pill.size().height() == 36 and sens.pill.font().pixelSize() >= 16,
          "link chip 120 x 36, 16 px")
    vp = sens.scroll.viewport()
    hz_card = hz[0].parentWidget()
    bottom = max(tuk.mapTo(vp, QPoint(0, tuk.height())).y(), hz_card.mapTo(vp, QPoint(0, hz_card.height())).y())
    check(bottom <= vp.height(), f"outline and hazards above the fold ({bottom} of {vp.height()} px)")
    small = [(QLabel.text(l), l.font().pixelSize()) for l in labels(sens) if l.font().pixelSize() < 14]
    check(not small, f"Sensors text at least 14 px {small[:3]}")
    check(not clipped(sens), f"Sensors: no clipped labels {clipped(sens)}")

# ---- 2. the full dashboard: pill placement, touch scrolling, screenshots -------------------------------
if SHOTS:
    from app.main_window import MainWindow
    w = MainWindow(); w.resize(1280, 800); w.show()
    t0 = time.monotonic()
    while w.stack.currentWidget() is not w.dashboard and time.monotonic() - t0 < 40:
        QTest.qWait(200)
    d = w.dashboard
    check(w.stack.currentWidget() is d, "dashboard shown")
    d.telemetry.stop()                   # our test telemetry only, no dead-bridge polls in between
    QTest.qWait(600)
    hb = d.hazard_banner
    for bar_h in (38, 48):
        d.status.setFixedHeight(bar_h); QTest.qWait(150)
        hb._message = ("crit", "OBSTACLE 0.5 M AHEAD"); hb._refresh(); QTest.qWait(50)
        g = hb.geometry(); h = max(24, min(40, d.status.height() - 8))   # layout on: 40 px in the 48 px bar
        check(g.height() == h and g.y() == (d.status.height() - h) // 2,
              f"pill follows a {d.status.height()} px status bar: y {g.y()}, height {g.height()}")
    d.status.setMinimumHeight(0); d.status.setMaximumHeight(16777215); QTest.qWait(150)
    for pid in ("diagnostics", "sensors"):
        d.switch_page_id(pid); QTest.qWait(150)
        area = getattr(d, pid).findChild(QScrollArea)
        check(area is not None and QScroller.hasScroller(area.viewport()), f"touch scrolling on {pid}")
    tag = "after" if LAYOUT else "before"
    def shot(name):
        QTest.qWait(400); w.grab().save(f"{OUT}/{tag}_{name}.png")
    d.diagnostics.ride_card.set_endpoint("127.0.0.1", "TUKZIE_TELEMETRY_URL")
    d.diagnostics.ride_card.set_telemetry(NEAR)
    d.switch_page_id("diagnostics"); shot("diagnostics")
    if LAYOUT:
        d.diagnostics._sw7_layout["toggle"].click(); shot("diagnostics_details")
        d.diagnostics._sw7_layout["toggle"].click()
    d.sensors.set_telemetry(NEAR); hb.set_telemetry(NEAR)
    d.switch_page_id("sensors"); shot("sensors_near")
    d.sensors.set_telemetry(FAR); shot("sensors_far")
    d.switch_page_id("camera"); QTest.qWait(100)
    c = d.front_camera; c._stop_stream(); c._streaming_wanted = False
    c._feed(FRAME); c._apply_alerts(ALERTS); c.status_label.setText("Live"); c._apply_alerts(dict(ALERTS))
    hb.set_telemetry(NEAR); shot("camera_alerts")
print("RESULT", "PASS" if not fails else f"FAIL {fails}")
'''

env = dict(os.environ, QT_QPA_PLATFORM="offscreen", TUKZIE_NO_CONTROLLER="1", TUKZIE_SKIP_LOGIN="1",
           TUKZIE_SW7_THEME="0", PYTHONIOENCODING="utf-8", TUKZIE_TELEMETRY_URL="http://127.0.0.1:9", TUKZIE_CAMERA_URL="http://127.0.0.1:9")
env.pop("TUKZIE_LIVE_ONLY", None)
if sys.platform == "win32":
    env.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")


def run(name, root, layout, shots):
    out = os.path.join(SP, "out_" + name); os.makedirs(out, exist_ok=True)
    e = dict(env, TUKZIE_SW7_LAYOUT=layout)
    r = subprocess.run([sys.executable, "-c", WORKER, out, name, "1" if shots else "0"], cwd=root, env=e,
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    print(f"-- {name} (TUKZIE_SW7_LAYOUT={layout})")
    print("\n".join(l for l in r.stdout.splitlines() if l.startswith(("ok", "FAIL", "RESULT"))))
    if "RESULT" not in r.stdout:
        print(r.stdout[-2000:], r.stderr[-3000:])
    return out, "RESULT PASS" in r.stdout


ok = True
ref_out, good = run("ref", ref, "0", False); ok &= good
off_out, good = run("off", new, "0", True); ok &= good
on_out, good = run("on", new, "1", True); ok &= good

same = []
for name in ("page_diagnostics.png", "page_sensors_near.png", "page_sensors_far.png", "page_camera.png"):
    eq = filecmp.cmp(os.path.join(ref_out, name), os.path.join(off_out, name), shallow=False)
    print(("ok   " if eq else "FAIL ") + f"switch: TUKZIE_SW7_LAYOUT=0 renders {name[5:-4]} exactly as before this pass")
    same.append(eq)
ok &= all(same)

for src_dir in (off_out, on_out):
    for f in sorted(os.listdir(src_dir)):
        if f.startswith(("before_", "after_")):
            shutil.copy(os.path.join(src_dir, f), os.path.join(OUT, f))
print("screenshots:", ", ".join(sorted(f for f in os.listdir(OUT) if f.endswith(".png"))), "in", OUT)
shutil.rmtree(SP, ignore_errors=True)
if not ok:
    sys.exit("LAYOUT PAGES TESTS FAILED")
print("ALL LAYOUT PAGES TESTS PASSED")
