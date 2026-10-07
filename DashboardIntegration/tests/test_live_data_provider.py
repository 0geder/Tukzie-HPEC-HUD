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
  6. Live-only mode (TUKZIE_LIVE_ONLY=1): the patched dashboard shows the
     no-data state with the bridge down (no simulated values, the simulation
     not running, every page renders), goes live when a bridge appears and
     returns to no-data, not simulation, when it stops.
  7. The Pi 4 resolver (sw7_endpoints.py): localhost first, the override,
     a UDP beacon to 127.0.0.1:50808, and a new search after 3 failures,
     with the live-data provider and the camera page following it.

Run: python DashboardIntegration/tests/test_live_data_provider.py
Needs PySide6 (6.11.2 used). Set TUKZIE_DASHBOARD_DIR to use another copy of
the dashboard, TUKZIE_TEST_SCRATCH to choose the scratch folder.
"""
from __future__ import annotations

import json
import os
# Keep the resolver tests off the real beacon port: a live Pi 4 on the same network
# broadcasts to 50808 and would be picked up instead of the test's fake sources.
os.environ.setdefault("TUKZIE_BEACON_PORT", "50919")
import shutil
import socket
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
# Since 6 Oct 2026 the settings, login and Sensors patches anchor on the team's v1.1 (the version
# installed on the Pi 5), so run with TUKZIE_DASHBOARD_DIR pointing at a copy of v1.1 (~/Dashboard on the
# Pi 5); v1.0-validated no longer takes every patch.

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
    (scratch / dst).parent.mkdir(parents=True, exist_ok=True)   # e.g. app/fonts
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
# The Navigation page's street-tile map (sw7_tile_map.py): never fetch real OSM tiles in this test,
# and keep its cache in the scratch folder. tests/test_tile_map.py tests the tiles themselves.
os.environ["TUKZIE_TILE_URL"] = "http://127.0.0.1:9/{z}/{x}/{y}.png"
os.environ["TUKZIE_TILE_CACHE"] = str(scratch / "tile_cache")
os.environ.pop("TUKZIE_TILE_MAP", None)

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
assert provider.resolver is None, "TUKZIE_TELEMETRY_URL must bypass the resolver"
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
assert s.heading is None and s.altitude_m is None, "no crs / alt in the record: heading and altitude unknown"
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
from app.pages.sw7_tile_map import SW7TileMap  # noqa: E402
assert isinstance(dm.navigation.map, SW7TileMap), type(dm.navigation.map)
dm.switch_page_id("navigation"); run_for(0.5)
assert dm.navigation.map.vehicle is not None and dm.navigation.map.isVisible(), "tile map not fed or not shown"
dm.grab().save(str(scratch / "dashboard_navigation.png"))
dm.switch_page_id("navigation"); dm.navigate_pages(1)
assert dm.stack.currentWidget() is dm.front_camera, "camera page not next after navigation"
assert dm.nav.buttons["camera"].isChecked()
dm.switch_page_id("diagnostics"); run_for(0.3)
dm.grab().save(str(scratch / "dashboard_diagnostics.png"))
dm.close()
server2.shutdown(); server2.server_close()
print("2 patched DashboardMain: live from the bridge, ride card fed, camera page in nav order")


def free_port(host="127.0.0.1"):
    with socket.socket() as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def bridge_on(host, port):
    srv = ThreadingHTTPServer((host, port), Bridge)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ---- 3. live-only mode --------------------------------------------------------
from app.data.sw7_live_only import UNKNOWN_FIELDS  # noqa: E402
from app.data.vehicle_state import Indicator  # noqa: E402
from PySide6.QtCore import QObject, Signal  # noqa: E402

os.environ["TUKZIE_LIVE_ONLY"] = "1"
errors = []
previous_hook = sys.excepthook


def _record_and_print(*exc):   # exceptions in Qt slots and paint events land here
    errors.append(exc)
    previous_hook(*exc)


class _Probe(QObject):
    fire = Signal()


_probe = _Probe()
_probe.fire.connect(lambda: 1 / 0)
sys.excepthook = lambda *exc: errors.append(exc)   # silent for this deliberate error
_probe.fire.emit()
assert errors and errors[0][0] is ZeroDivisionError, "slot exceptions are not reaching sys.excepthook"
errors.clear()
sys.excepthook = _record_and_print

port3 = free_port()
ldp.TELEMETRY_URL = f"http://127.0.0.1:{port3}"     # nothing listens there yet: bridge down
dm3 = DashboardMain()
dm3.resize(1280, 800)
dm3.show()
vd = dm3.vehicle_data
modes = []
vd.mode_changed.connect(modes.append)
assert vd.live_only and vd.mode == "no_data", vd.mode
run_for(1.5)


def assert_no_data(state, where):
    assert state.data_source == "no_data" and state.is_simulated is False, (where, state.data_source)
    # route_progress is written onto the shown state by the navigation page from ASIS (0 with no route)
    bad = [name for name in UNKNOWN_FIELDS if getattr(state, name) is not None and name != "route_progress"]
    assert not bad, f"{where}: fields not None: {bad}"
    assert not any(state.signal_validity.values()), (where, state.signal_validity)


def assert_no_sim(where):
    assert not vd.sim._timer.isActive(), f"{where}: simulation timer running"
    assert dm3.current_state is vd.state and vd.state is not vd.sim.state, f"{where}: sim state displayed"


assert_no_data(dm3.current_state, "bridge down at start")
assert_no_sim("bridge down at start")
assert dm3.status.soc.text() == "--%", dm3.status.soc.text()
assert dm3.driving.range.text() == "Range: -- km", dm3.driving.range.text()
assert dm3.driving.speed.speed_known is False and dm3.driving.brake.known is False and dm3.driving.accel.known is False
for name in ("Speed", "Throttle", "Brake", "Signed power", "Battery SOC", "Range", "Battery temp", "Motor temp",
             "Ambient", "Incline", "Odometer", "GPS", "Altitude"):
    assert dm3.diagnostics._values[name].text() == "Unavailable", (name, dm3.diagnostics._values[name].text())
assert dm3.diagnostics._values["Source"].text() == "no_data"
for stat_name in ("s_soc", "s_btemp", "s_atemp", "s_odo", "s_power", "s_eff"):
    assert getattr(dm3.analytics, stat_name).value.text() == "--", stat_name
assert all(dm3.charging.tuk.unknown.values()), dm3.charging.tuk.unknown
assert dm3.charging.thermal_value.text() == "--"
assert dm3.reverse.distance_card.value_label.text() == "--" and not dm3.reverse.radar.isVisible()
assert dm3.diagnostics.ride_card.endpoint_label.text() == "Pi 4: 127.0.0.1 (TUKZIE_TELEMETRY_URL)"
wait_until(lambda: dm3.driving.asis_panel.line1.text() == "No live vehicle data", 3, "ASIS panel: no live data")
for pid in dm3.page_ids:                       # paint every page in the no-data state
    dm3.stack.setCurrentWidget(dm3.page_by_id[pid])
    run_for(0.15)
    dm3.grab()
dm3.switch_page_id("driving")
dm3.grab().save(str(scratch / "live_only_no_data.png"))
dm3._on_vehicle_state(vd.state)               # a direct call raises if the status bar or driving page fails
assert not dm3._last_page_error, dm3._last_page_error
assert not errors, errors
# driver inputs still work without data
vd.set_indicator(Indicator.LEFT)
vd.toggle_headlights()
wait_until(lambda: dm3.current_state.indicator == Indicator.LEFT and dm3.current_state.headlights, 2,
           "driver inputs shown in the no-data state")
assert_no_data(dm3.current_state, "after driver inputs")
print("3a live-only, bridge down: no-data state, no simulation, every page renders, driver inputs work")

serve(LIVE)
server3 = bridge_on("127.0.0.1", port3)
wait_until(lambda: vd.mode == "live_controller", 6, "live-only dashboard live from the bridge")
s = dm3.current_state
assert close(s.soc_pct, 76.5) and close(s.front_obstacle_distance_m, 0.812) and close(s.latitude, -33.95791)
assert s.speed_kmh is None and s.battery_temp_c is None and s.odometer_km is None and s.throttle_pct is None
assert s.indicator == Indicator.LEFT and s.headlights, "driver inputs not carried into the live state"
assert dm3.status.soc.text() == f"{76.5:.0f}%", dm3.status.soc.text()
assert dm3.diagnostics._values["Speed"].text() == "Unavailable"
assert dm3.diagnostics._values["Battery SOC"].text() == "76.5 %"
assert_no_sim("live")
dm3.grab().save(str(scratch / "live_only_live.png"))
print("3b live-only: live from the bridge, unmapped fields stay None")

server3.shutdown(); server3.server_close()
wait_until(lambda: vd.mode == "no_data", 6, "back to no-data when the bridge stops")
run_for(0.6)
assert_no_data(dm3.current_state, "after the bridge stopped")
assert_no_sim("after the bridge stopped")
assert dm3.toast.text().startswith("Live data lost"), dm3.toast.text()
assert "simulation" not in modes, modes
assert dm3.status.soc.text() == "--%"
assert not dm3._last_page_error and not errors, (dm3._last_page_error, errors)
dm3.close()
print("3c live-only: bridge stopped -> no-data state and 'Live data lost' toast; modes:", modes)

# soc never reported: None, not the dataclass default of 82 %
NO_BMS = json.loads(json.dumps(LIVE)); NO_BMS["esp32"]["soc"] = None
assert ldp.build_live_state(NO_BMS, live_only=False).soc_pct is None
assert ldp.build_live_state(NO_BMS, live_only=True).soc_pct is None
print("3d soc_pct is None when the BMS has never reported")

# ---- 4. Pi 4 resolver -------------------------------------------------------------
import app.data.sw7_endpoints as ep  # noqa: E402
import app.pages.front_camera_page as fcp  # noqa: E402
from app.data.sw7_endpoints import Pi4Resolver  # noqa: E402

cfg = scratch / "sw7_config"
if cfg.exists():
    shutil.rmtree(cfg, onexc=_force_remove)
os.environ.pop("TUKZIE_PI4_HOST", None)
serve(LIVE)


def watch(resolver):
    seen = []
    resolver.host_changed.connect(lambda host, how: seen.append((host, how)))
    return seen


# 4a localhost first
pA = free_port()
srvA = bridge_on("127.0.0.1", pA)
r1 = Pi4Resolver(telemetry_port=pA, config_dir=cfg)
seen1 = watch(r1)
r1.start()
wait_until(lambda: r1.host is not None, 5, "resolver on localhost")
assert (r1.host, r1.how) == ("127.0.0.1", "localhost") and seen1[-1] == ("127.0.0.1", "localhost"), seen1
assert r1.telemetry_url() == f"http://127.0.0.1:{pA}" and r1.camera_url() == "http://127.0.0.1:8080"
assert (cfg / "last_pi4_host").read_text().strip() == "127.0.0.1"
assert not r1.beacon_error, r1.beacon_error
r1.stop(); srvA.shutdown(); srvA.server_close()
print("4a resolver: localhost first; saved as last good")

# 4b nothing on localhost: falls through to the override (environment, then endpoints.conf)
pB = free_port("127.0.0.2")
srvB = bridge_on("127.0.0.2", pB)
os.environ["TUKZIE_PI4_HOST"] = "127.0.0.2"
r2 = Pi4Resolver(telemetry_port=pB, config_dir=cfg, listen_for_beacons=False)
r2.start()
wait_until(lambda: r2.host is not None, 5, "resolver on the override host")
assert (r2.host, r2.how) == ("127.0.0.2", "override"), (r2.host, r2.how)
r2.stop()
del os.environ["TUKZIE_PI4_HOST"]
(cfg / "endpoints.conf").write_text("# test\npi4_host = 127.0.0.2\n", encoding="utf-8")
r2b = Pi4Resolver(telemetry_port=pB, config_dir=cfg, listen_for_beacons=False)
r2b.start()
wait_until(lambda: r2b.host is not None, 5, "resolver on the endpoints.conf host")
assert (r2b.host, r2b.how) == ("127.0.0.2", "override"), (r2b.host, r2b.how)
r2b.stop(); srvB.shutdown(); srvB.server_close()
(cfg / "endpoints.conf").unlink()
print("4b resolver: falls through to the override (TUKZIE_PI4_HOST and endpoints.conf)")

# 4c beacon: learn the host from the source address of a UDP beacon to 127.0.0.1:50808
pC = free_port("127.0.0.3")
srvC = bridge_on("127.0.0.3", pC)
r3 = Pi4Resolver(telemetry_port=pC, config_dir=cfg)
seen3 = watch(r3)
r3.start()
assert not r3.beacon_error, r3.beacon_error
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as other:
    other.bind(("127.0.0.4", 0))
    other.sendto(b'{"sw7": "other"}', ("127.0.0.1", ep.BEACON_PORT))
run_for(0.3)
assert r3.beacon_host is None, "a packet that is not a SW-7 beacon was accepted"
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as pi4:
    pi4.bind(("127.0.0.3", 0))
    pi4.sendto(json.dumps({"sw7": "pi4", "v": 1, "host": "pi4-camera", "camera_port": 8080,
                           "telemetry_port": 8081, "seq": 1}).encode(), ("127.0.0.1", ep.BEACON_PORT))
wait_until(lambda: r3.host is not None, 10, "resolver on the beacon source")
assert (r3.host, r3.how) == ("127.0.0.3", "beacon"), (r3.host, r3.how, seen3)
r3.beacon_time -= ep.BEACON_MAX_AGE_S + 1          # an old beacon is ignored
assert ("127.0.0.3", "beacon") not in r3.candidates()
r3.stop(); srvC.shutdown(); srvC.server_close()
print("4c resolver: learned 127.0.0.3 from a UDP beacon; old beacons ignored; candidates seen:", seen3)

# 4d a new search after 3 failures, followed by the provider and the camera page
pD = free_port()
srvD1 = bridge_on("127.0.0.1", pD)
r4 = Pi4Resolver(telemetry_port=pD, config_dir=cfg, listen_for_beacons=False)
manager4 = VehicleStateManager(50, 41.9, 2500)
manager4.start()
provider4 = LiveDataProvider(manager4, resolver=r4)
endpoints4 = []
provider4.endpoint_changed.connect(lambda host, how: endpoints4.append((host, how)))
card4 = RideQualityCard()
provider4.endpoint_changed.connect(card4.set_endpoint)
fcp.CAMERA_URL = None
ep._shared = r4                                     # the camera page uses the shared resolver
cam = fcp.FrontCameraPage()
provider4.start()
wait_until(lambda: provider4.link == "live", 5, "provider live through the resolver")
assert endpoints4[0] == ("", "searching") and ("127.0.0.1", "localhost") in endpoints4, endpoints4
assert card4.endpoint_label.text() == "Pi 4: 127.0.0.1 (localhost)", card4.endpoint_label.text()
assert cam.camera_url() == "http://127.0.0.1:8080"
srvD1.shutdown(); srvD1.server_close()
os.environ["TUKZIE_PI4_HOST"] = "127.0.0.2"
srvD2 = bridge_on("127.0.0.2", pD)
wait_until(lambda: r4.host == "127.0.0.2", 20, "a new search after the bridge stopped")   # probes now wait up to 3 s each
assert r4.how == "override" and ("", "searching") in endpoints4[1:], endpoints4
wait_until(lambda: provider4.link == "live", 5, "provider live on the new host")
assert card4.endpoint_label.text() == "Pi 4: 127.0.0.2 (override)"
assert cam.camera_url() == "http://127.0.0.2:8080"
# exactly 3 failures in a row start a new search
r4.report_failure(); r4.report_failure()
assert r4.host == "127.0.0.2", "searched again before 3 failures"
r4.report_success(); r4.report_failure(); r4.report_failure()
assert r4.host == "127.0.0.2", "a success must reset the failure count"
r4.report_failure()
assert r4.host is None and r4.how == "searching"
wait_until(lambda: r4.host == "127.0.0.2", 5, "found again after the forced search")
provider4.stop(); manager4.stop(); r4.stop(); srvD2.shutdown(); srvD2.server_close()
del os.environ["TUKZIE_PI4_HOST"]
assert not errors, errors
sys.excepthook = previous_hook
print("4d resolver: new search after 3 failures; provider, ride card and camera page follow; endpoints:", endpoints4)
print("ALL TESTS PASSED")
