"""Offscreen test of live_data_provider.py and ride_quality_card.py against a
copy of the v1.0-validated dashboard and a local fake telemetry bridge.

What it does:
  1. Copies v1.0-validated/app into a scratch folder (the original is never
     touched), copies our three files into it and applies the README patches
     from dashboard_patches.py to the copy.
  2. Starts a tiny HTTP server on 127.0.0.1 that serves /telemetry like the
     Pi 4 bridge (TELEMETRY_LINK.md, section 2).
  3. Runs a VehicleStateManager plus LiveDataProvider against it and checks
     what reaches ingest_live_state(): normal values, nulls, a stale ESP32,
     esp32 null, bad JSON, and the server going down.
  4. Checks the ride card's values and its Live / stale / Offline states,
     and saves tests/ride_card.png.
  5. Starts the patched DashboardMain and checks it goes live from the
     bridge, feeds the ride card, and has the camera page in its page order.

Run: python DashboardIntegration/tests/test_live_data_provider.py
Needs PySide6 (6.11.2 used). Set TUKZIE_DASHBOARD_DIR to use another copy of
the dashboard, TUKZIE_TEST_SCRATCH to choose the scratch folder.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
INTEGRATION = HERE.parent
DEFAULT_DASH = (INTEGRATION.parent.parent / "Tukzie-Vac-Work-2026" / "Dashboard Team"
                / "Tukzie-Dashboard" / "v1.0-validated")
DASH = Path(os.environ.get("TUKZIE_DASHBOARD_DIR", DEFAULT_DASH))
sys.path.insert(0, str(HERE))
from dashboard_patches import COPIES, PATCHES  # noqa: E402

# ---- fake bridge -----------------------------------------------------------
LIVE = {
    "esp32": {"seq": 812, "up_ms": 812345, "fw": "0.7.0", "soc": 76.5, "v": 51.2, "i": 18.4,
              "bms_age_s": 0.6, "fix": True, "lat": -33.95791, "lon": 18.46102, "spd_raw": 7.9,
              "vib": 0.42, "vib_dis": 0.07, "imu_hz": [400.0, 398.6], "drops": [0, 3],
              "rpm": 1450, "csq": 18, "mqtt": True, "age_ms": 420},
    "tof": {"left_mm": 1620, "ahead_mm": 812, "right_mm": None, "age_ms": 35},
    "bridge": {"version": "1.0", "serial_port": "/dev/ttyACM0", "lines": 1234, "bad_lines": 2},
}
NULLS = {
    "esp32": {"seq": 813, "up_ms": 813345, "fw": "0.7.0", "soc": None, "v": None, "i": 18.0,
              "bms_age_s": None, "fix": False, "lat": None, "lon": None, "spd_raw": None,
              "vib": None, "vib_dis": None, "imu_hz": [400.0, 0.0], "drops": [0, 3],
              "rpm": None, "csq": None, "mqtt": False, "age_ms": 900},
    "tof": None,
    "bridge": {"version": "1.0", "serial_port": "/dev/ttyACM0", "lines": 1235, "bad_lines": 2},
}
STALE = json.loads(json.dumps(LIVE)); STALE["esp32"]["age_ms"] = 4500
NO_ESP = {"esp32": None, "tof": {"left_mm": 900, "ahead_mm": 1400, "right_mm": 700, "age_ms": 30},
          "bridge": {"version": "1.0", "serial_port": "/dev/ttyACM0", "lines": 0, "bad_lines": 0}}


class Bridge(BaseHTTPRequestHandler):
    body = b""
    hits = 0

    def do_GET(self):
        if self.path != "/telemetry":
            self.send_error(404); return
        Bridge.hits += 1
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(Bridge.body)))
        self.end_headers()
        self.wfile.write(Bridge.body)

    def log_message(self, *args):
        pass


def serve(payload):
    Bridge.body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()


server = ThreadingHTTPServer(("127.0.0.1", 0), Bridge)
threading.Thread(target=server.serve_forever, daemon=True).start()
BRIDGE_URL = f"http://127.0.0.1:{server.server_address[1]}"
serve(LIVE)

# ---- scratch copy of the dashboard, with our files and the README patches ---
scratch = Path(os.environ.get("TUKZIE_TEST_SCRATCH") or tempfile.mkdtemp(prefix="tukzie_dash_"))
target = scratch / "app"
def _force_remove(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)   # copies of OneDrive files can be read-only
    func(path)


if target.exists():
    shutil.rmtree(target, onexc=_force_remove)
shutil.copytree(DASH / "app", target, ignore=shutil.ignore_patterns("__pycache__", "logs"))
for src, dst in COPIES:
    shutil.copy2(INTEGRATION / src, scratch / dst)
for rel, old, new in PATCHES:
    path = scratch / rel
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"patch anchor not found exactly once in {rel}: {old!r}"
    path.write_text(text.replace(old, new), encoding="utf-8")
print(f"dashboard copied to {scratch} and patched ({len(PATCHES)} edits)")
sys.path.insert(0, str(scratch))

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
os.environ["TUKZIE_TELEMETRY_URL"] = BRIDGE_URL
os.environ["TUKZIE_CAMERA_URL"] = "http://192.0.2.1:9"   # TEST-NET: never answers

from PySide6.QtCore import QEventLoop  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

qapp = QApplication(sys.argv)

from app.data.data_provider import VehicleStateManager  # noqa: E402
from app.data.live_data_provider import LiveDataProvider  # noqa: E402
from app.theme import THEME  # noqa: E402
from app.widgets.ride_quality_card import RideQualityCard  # noqa: E402

qapp.setStyleSheet(THEME.stylesheet())


def wait_until(pred, timeout_s, what):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        qapp.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
        if pred():
            return
        time.sleep(0.01)
    raise AssertionError(f"timed out waiting for {what}")


def run_for(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        qapp.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
        time.sleep(0.01)


def close(a, b, tol=1e-6):
    return a is not None and b is not None and abs(a - b) <= tol


# ---- 1. provider + manager --------------------------------------------------
manager = VehicleStateManager(50, 41.9, 2500)
ingested = []
original_ingest = manager.ingest_live_state
def recording_ingest(state, source="live_controller"):
    ingested.append((state, source))
    original_ingest(state, source)
manager.ingest_live_state = recording_ingest
manager.start()

provider = LiveDataProvider(manager)
assert provider.url == BRIDGE_URL, provider.url
card = RideQualityCard()
card.resize(980, card.sizeHint().height())
card.show()
provider.telemetry_updated.connect(card.set_telemetry)
raw_seen = []
provider.telemetry_updated.connect(raw_seen.append)
links = []
provider.link_changed.connect(links.append)
provider.start()

# 1a. normal values
wait_until(lambda: len(ingested) >= 2, 4, "two live ingests")
s, source = ingested[-1]
assert source == "sw7_telemetry", source
assert close(s.soc_pct, 76.5), s.soc_pct
assert close(s.signed_battery_power_kw, 51.2 * 18.4 / 1000), s.signed_battery_power_kw
assert close(s.battery_power_kw, 51.2 * 18.4 / 1000)
assert close(s.latitude, -33.95791) and close(s.longitude, 18.46102)
assert s.gps_timestamp is not None and time.time() - s.gps_timestamp < 5
assert close(s.front_obstacle_distance_m, 0.812), s.front_obstacle_distance_m
assert s.speed_kmh == 0.0, "spd_raw must not be mapped to speed_kmh"
v = s.signal_validity
assert v["gps"] and v["soc"] and v["front_obstacle"] and not v["speed"], v
assert s.is_simulated is False and s.data_source == "sw7_telemetry"
assert manager.mode == "live_controller" and manager.state is s
assert raw_seen[-1] == LIVE, "telemetry_updated must carry the raw bridge dict"
assert provider.link == "live" and card.link == "live"
assert card.text_of("vib") == "0.42 m/s\u00b2", card.text_of("vib")
assert card.text_of("vib_dis") == "0.07"
assert card.text_of("imu_hz") == "400 / 399 Hz", card.text_of("imu_hz")
assert card.text_of("drops") == "0 / 3"
assert card.text_of("rpm") == "1450 rpm"
assert card.text_of("csq") == "18 / 31"
assert card.text_of("mqtt") == "Up"
assert card.text_of("tof_left") == "1.62 m" and card.text_of("tof_ahead") == "0.81 m"
assert card.text_of("tof_right") == "--"
assert card.pill.text() == "Live"
qapp.processEvents()
card.grab().save(str(HERE / "ride_card.png"))
print("1a live values: ingest and ride card correct; saved ride_card.png")

# 1b. nulls: soc kept from the last good value, no power, no GPS, no front distance
serve(NULLS)
n = len(ingested)
wait_until(lambda: len(ingested) >= n + 2, 4, "ingests with null fields")
s = ingested[-1][0]
assert close(s.soc_pct, 76.5) and s.signal_validity["soc"] is False, (s.soc_pct, s.signal_validity)
assert s.signed_battery_power_kw is None and s.battery_power_kw == 0.0
assert s.latitude is None and s.longitude is None and s.signal_validity["gps"] is False
assert s.front_obstacle_distance_m is None and s.signal_validity["front_obstacle"] is False
assert card.link == "live" and card.text_of("vib") == "--" and card.text_of("mqtt") == "Down"
assert card.text_of("imu_hz") == "400 / 0 Hz" and card.text_of("tof_ahead") == "--"
print("1b nulls: mapped to None or kept, card shows blanks")

# 1c. stale ESP32 record: polling continues, nothing is ingested, dashboard falls back
serve(STALE)
wait_until(lambda: provider.link == "stale", 3, "stale link")
n, hits = len(ingested), Bridge.hits
run_for(1.6)
assert Bridge.hits >= hits + 2, "provider stopped polling"
assert len(ingested) == n, "ingested while esp32.age_ms > 3000"
assert card.link == "stale" and card.pill.text() == "ESP32 stale"
wait_until(lambda: manager.mode == "simulation", 4, "dashboard's own fallback to simulation")
print("1c stale: no ingest, card says ESP32 stale, dashboard back on simulation")

# 1d. esp32 null (ToF only): still nothing ingested
serve(NO_ESP)
run_for(1.2)
assert len(ingested) == n and provider.link == "stale"
assert card.text_of("age") == "No data" and card.text_of("tof_right") == "0.70 m"
print("1d esp32 null: no ingest")

# 1e. bad JSON counts as offline
serve(b"{not json")
wait_until(lambda: provider.link == "offline", 3, "offline on bad JSON")
assert len(ingested) == n and card.link == "offline"

# 1f. back to live, then the server goes down
serve(LIVE)
wait_until(lambda: provider.link == "live" and manager.mode == "live_controller", 4, "live again")
server.shutdown(); server.server_close()
wait_until(lambda: provider.link == "offline", 5, "offline when the bridge is down")
n = len(ingested)
run_for(1.5)
assert len(ingested) == n, "ingested while the bridge was down"
assert card.link == "offline" and card.pill.text() == "Offline" and card.text_of("vib") == "--"
assert raw_seen[-1] is None
qapp.processEvents()
card.grab().save(str(scratch / "ride_card_offline.png"))
wait_until(lambda: manager.mode == "simulation", 4, "fallback after the bridge went down")
print("1e/1f bad JSON and server down: offline, no ingest, fallback to simulation")
print("link changes:", links)
provider.stop(); manager.stop()

# 1g. card watchdog: no updates at all for 3 s turns it Offline
card2 = RideQualityCard()
card2.set_telemetry(LIVE)
assert card2.link == "live"
wait_until(lambda: card2.link == "offline", 5, "card watchdog")
print("1g card watchdog: Offline after 3 s without updates")

# ---- 2. patched DashboardMain ----------------------------------------------
server2 = ThreadingHTTPServer(("127.0.0.1", 0), Bridge)
threading.Thread(target=server2.serve_forever, daemon=True).start()
import app.data.live_data_provider as ldp  # noqa: E402
ldp.TELEMETRY_URL = f"http://127.0.0.1:{server2.server_address[1]}"
serve(LIVE)
try:
    import PySide6.QtMultimedia  # noqa: F401  (in PySide6-Addons; the reverse page's chime needs it)
except ImportError:
    # PySide6-Essentials only: give the reverse camera page a silent QSoundEffect.
    import types
    from PySide6.QtCore import QObject

    class _SilentSoundEffect(QObject):
        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    _stub = types.ModuleType("PySide6.QtMultimedia")
    _stub.QSoundEffect = _SilentSoundEffect
    sys.modules["PySide6.QtMultimedia"] = _stub
    print("PySide6.QtMultimedia missing: using a silent QSoundEffect stub for the reverse page")
from app.pages.dashboard_main import DashboardMain  # noqa: E402

dm = DashboardMain()
dm.resize(1280, 800)
dm.show()
wait_until(lambda: dm.vehicle_data.mode == "live_controller" and dm.diagnostics.ride_card.link == "live",
           6, "patched dashboard live from the bridge")
assert close(dm.current_state.soc_pct, 76.5)
assert dm.current_state.front_obstacle_distance_m is not None
assert "camera" in dm.page_ids and "camera" in dm.normal_ids and "camera" in dm.nav.buttons
dm.switch_page_id("navigation"); dm.navigate_pages(1)
assert dm.stack.currentWidget() is dm.front_camera, "camera page not next after navigation"
assert dm.nav.buttons["camera"].isChecked()
dm.switch_page_id("diagnostics"); run_for(0.3)
dm.grab().save(str(scratch / "dashboard_diagnostics.png"))
dm.close()
server2.shutdown(); server2.server_close()
print("2 patched DashboardMain: live from the bridge, ride card fed, camera page in nav order")
print("ALL TESTS PASSED")
