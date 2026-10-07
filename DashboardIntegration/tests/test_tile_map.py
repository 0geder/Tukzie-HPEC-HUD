"""Offscreen test of sw7_tile_map.py (the street-tile map for the Navigation page),
the crs / alt / replay mapping in live_data_provider.py and the REPLAY badges.

What it does:
  1. Copies v1.0-validated/app into a scratch folder, adds our files and applies
     every patch from dashboard_patches.py (as test_live_data_provider.py does),
     and checks the patched navigation_page.py uses SW7TileMap, or the team's
     NativeRouteMap with TUKZIE_TILE_MAP=0.
  2. Serves fake tiles (checkerboard PNGs) from a local HTTP server, with
     TUKZIE_TILE_URL pointing at it and TUKZIE_TILE_CACHE at a temp folder.
  3. Feeds fixes from CameraDetection/tests/replay_uct_route.txt (real DASH lines,
     1 Hz) through build_live_state(), so crs becomes the heading and alt the
     altitude, and checks: the right zoom-17 tiles are requested (the vehicle's
     tile first, only tiles on screen, never more than 2 at a time, with the
     SW-7 User-Agent); they are cached on disk; the map is heading-up with the
     vehicle at 70 % of the height; the marker moves smoothly between fixes;
     the frame timer runs only while something moves and the widget is shown.
     Saves tests/tile_map_follow.png.
  4. Disk cache: a new map at the same place fetches nothing; a tile older
     than 30 days is fetched again.
  5. No fix: "Waiting for GPS fix" at the last known position (or UCT).
     Saves tests/tile_map_no_fix.png.
  6. Replay: data_source "sw7_replay" (bridge.replay or fw "-replay") shows the
     REPLAY badge on the map and on the ride card. Saves tests/tile_map_replay.png.
  7. Tile server down, empty cache: vector roads on a plain background.
     Saves tests/tile_map_offline.png.
  8. Drag leaves follow mode, zoom keeps it, Overview fits the route north-up.

Run: python DashboardIntegration/tests/test_tile_map.py
"""
from __future__ import annotations

import importlib
import json
import math
import os
import shutil
import stat
import struct
import sys
import tempfile
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
INTEGRATION = HERE.parent
REPO = INTEGRATION.parent
DEFAULT_DASH = (REPO.parent / "Tukzie-Vac-Work-2026" / "Dashboard Team" / "Tukzie-Dashboard" / "v1.0-validated")
DASH = Path(os.environ.get("TUKZIE_DASHBOARD_DIR", DEFAULT_DASH))
REPLAY = REPO / "CameraDetection" / "tests" / "replay_uct_route.txt"
sys.path.insert(0, str(HERE))
from dashboard_patches import COPIES, PATCHES  # noqa: E402
# Since 6 Oct 2026 the settings, login and Sensors patches anchor on the team's v1.1 (the version
# installed on the Pi 5), so run with TUKZIE_DASHBOARD_DIR pointing at a copy of v1.1 (~/Dashboard on the
# Pi 5); v1.0-validated no longer takes every patch.


# ---- fake tile server ---------------------------------------------------------------
def _png(z, x, y):
    """A 256x256 checkerboard tile with a dark border, so rotation shows in screenshots."""
    light = (0xE8, 0xEC, 0xE4) if (x + y) % 2 else (0xCF, 0xDB, 0xCB)
    rows = []
    for py in range(256):
        row = bytearray(b"\x00")
        for px in range(256):
            edge = px < 2 or py < 2
            road = 120 <= px <= 135 or 120 <= py <= 135
            row += bytes((0x80, 0x88, 0x90) if edge else (0xFF, 0xFF, 0xFF) if road else light)
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows), 6)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 256, 256, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


class Tiles(BaseHTTPRequestHandler):
    hits = []
    agents = set()
    active = 0
    max_active = 0
    lock = threading.Lock()

    def do_GET(self):
        parts = self.path.strip("/").split("/")
        if len(parts) != 3 or not parts[2].endswith(".png"):
            self.send_error(404); return
        z, x, y = int(parts[0]), int(parts[1]), int(parts[2][:-4])
        with Tiles.lock:
            Tiles.active += 1
            Tiles.max_active = max(Tiles.max_active, Tiles.active)
            Tiles.hits.append((z, x, y))
            Tiles.agents.add(self.headers.get("User-Agent"))
        try:
            time.sleep(0.03)
            body = _png(z, x, y)
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        finally:
            with Tiles.lock:
                Tiles.active -= 1

    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Tiles)
threading.Thread(target=server.serve_forever, daemon=True).start()
TILE_URL = f"http://127.0.0.1:{server.server_address[1]}/{{z}}/{{x}}/{{y}}.png"

# ---- scratch copy of the dashboard ---------------------------------------------------
scratch = Path(os.environ.get("TUKZIE_TEST_SCRATCH") or tempfile.mkdtemp(prefix="tukzie_tiles_"))


def _force_remove(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


target = scratch / "app"
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

cache = scratch / "tile_cache"
if cache.exists():
    shutil.rmtree(cache, onexc=_force_remove)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
os.environ["TUKZIE_TILE_URL"] = TILE_URL
os.environ["TUKZIE_TILE_CACHE"] = str(cache)
os.environ.pop("TUKZIE_TILE_MAP", None)

from PySide6.QtCore import QEventLoop, QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

qapp = QApplication(sys.argv)

from app.data import live_data_provider as ldp  # noqa: E402
from app.pages import navigation_page_fallback  # noqa: E402
from app.pages.sw7_tile_map import SW7TileMap, tile_of, to_ref  # noqa: E402
from app.theme import THEME  # noqa: E402
from app.widgets.ride_quality_card import RideQualityCard  # noqa: E402

qapp.setStyleSheet(THEME.stylesheet())
errors = []
previous_hook = sys.excepthook
sys.excepthook = lambda *exc: (errors.append(exc), previous_hook(*exc))


def run_for(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        qapp.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 20)
        time.sleep(0.005)


def wait_until(pred, timeout_s, what):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        qapp.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 20)
        if pred():
            return
        time.sleep(0.005)
    raise AssertionError(f"timed out waiting for {what}")


def wrap(deg):
    return (deg + 180.0) % 360.0 - 180.0


# ---- 1. the patch ------------------------------------------------------------------------
import app.pages.navigation_page as nav  # noqa: E402
assert nav.NativeRouteMap is SW7TileMap, nav.NativeRouteMap
os.environ["TUKZIE_TILE_MAP"] = "0"
importlib.reload(nav)
assert nav.NativeRouteMap is navigation_page_fallback.NativeRouteMap, "TUKZIE_TILE_MAP=0 must keep the team's map"
del os.environ["TUKZIE_TILE_MAP"]
importlib.reload(nav)
assert nav.NativeRouteMap is SW7TileMap
for name in ("set_plan", "set_context", "set_progress", "update_vehicle", "set_follow_mode", "show_overview", "_zoom"):
    assert callable(getattr(SW7TileMap, name)), name
print("1 patch: navigation_page uses SW7TileMap; TUKZIE_TILE_MAP=0 restores NativeRouteMap")

# ---- replay track -> live states (crs -> heading, alt -> altitude) ---------------------
records = [json.loads(line[5:]) for line in REPLAY.read_text(encoding="utf-8").splitlines() if line.startswith("DASH ")]
assert len(records) > 600, len(records)
# a straight stretch heading about east (course near 90 deg), so heading-up is clearly not north-up
start = 240
track = records[start:start + 12]


def state_of(rec, source="sw7_telemetry", bridge_replay=False):
    esp = dict(rec, age_ms=300)
    if not bridge_replay:
        esp["fw"] = "0.7.1"              # as from the serial port
    tel = {"esp32": esp, "tof": None, "bridge": {"version": "1.0", "replay": bridge_replay,
                                                   "replay_file": "replay_uct_route.txt" if bridge_replay else None}}
    s = ldp.build_live_state(tel, live_only=True)
    s.data_source = ldp.REPLAY_SOURCE if ldp.is_replay(tel) else source
    return s


s0 = state_of(track[0])
assert abs(s0.heading - track[0]["crs"] % 360) < 1e-9 and s0.signal_validity["heading"] is True
assert abs(s0.altitude_m - track[0]["alt"]) < 1e-9
no_crs = dict(track[0], crs=None, alt=None)
s1 = state_of(no_crs)
assert s1.heading is None and s1.altitude_m is None and s1.signal_validity["heading"] is False
no_fix = dict(track[0], fix=False)
s2 = state_of(no_fix)
assert s2.heading is None and s2.altitude_m is None and s2.latitude is None
assert ldp.build_live_state({"esp32": dict(no_crs, age_ms=1)}, live_only=False).heading is None
print("2 provider: crs -> heading and alt -> altitude_m only with a fix; otherwise None")

# ---- 3. follow mode -------------------------------------------------------------------------
W, H = 1100, 700
plan_pts = [SimpleNamespace(lat=r["lat"], lon=r["lon"]) for r in records[start - 30:start + 60:3]]
plan = SimpleNamespace(route=plan_pts, nearby_roads=[], destination={"lat": plan_pts[-1].lat, "lon": plan_pts[-1].lon})
m = SW7TileMap()
m.resize(W, H)
follow_events = []
m.follow_changed.connect(follow_events.append)
m.set_plan(plan, reset_view=False)
m.set_progress(0.35)
m.update_vehicle(state_of(track[0]))
m.show()
assert m.auto_follow
for rec in track[1:6]:
    m.update_vehicle(state_of(rec))
    run_for(1.0)
z17 = tile_of(track[5]["lat"], track[5]["lon"], 17)
wait_until(lambda: not m._in_flight and not m.vector_fallback_active, 15, "all visible tiles loaded")
run_for(0.6)
req = list(m.requested_tiles)
assert req, "no tiles requested"
assert all(k[0] == 17 for k in req), {k[0] for k in req}
assert len(set(req)) == len(req), "a tile was requested twice"
first_vehicle_tile = tile_of(track[0]["lat"], track[0]["lon"], 17)
assert req[0] == (17, *first_vehicle_tile), (req[0], first_vehicle_tile)
assert (17, *z17) in req
radius = math.hypot(W, H) / 256 + 2
assert all(math.hypot(k[1] - z17[0], k[2] - z17[1]) <= radius for k in req), "a tile far off screen was requested"
assert set(Tiles.hits) == set(req), "server hits and requested tiles differ"
assert m.max_in_flight <= 2 and Tiles.max_active <= 2, (m.max_in_flight, Tiles.max_active)
assert Tiles.agents == {"TUKZIE-SW7-dashboard/1.0 (UCT student project)"}, Tiles.agents
for z, x, y in req:
    assert (cache / str(z) / str(x) / f"{y}.png").is_file(), f"tile {z}/{x}/{y} not cached"
assert m.tile_status == "online"
print(f"3a tiles: {len(req)} zoom-17 tiles requested (vehicle tile first, max 2 at a time, SW-7 User-Agent), all cached")

heading = track[5]["crs"] % 360
assert m.heading_up, "follow mode should be heading-up while moving"
assert abs(wrap(m.bearing - heading)) < 3, (m.bearing, heading)
v = m.vehicle_screen_point()
assert abs(v.y() - 0.70 * H) < 2, v
lat, lon = track[5]["lat"], track[5]["lon"]
ahead = m.screen_point(lat + 0.0005 * math.cos(math.radians(heading)),
                       lon + 0.0005 * math.sin(math.radians(heading)) / math.cos(math.radians(lat)))
assert ahead.y() < v.y() - 40 and abs(ahead.x() - v.x()) < 4, (v, ahead)
north = m.screen_point(lat + 0.0005, lon)
assert abs(wrap(math.degrees(math.atan2(north.x() - v.x(), v.y() - north.y())) + heading)) < 3, "north not at -heading"
m.grab().save(str(HERE / "tile_map_follow.png"))
print(f"3b heading-up: bearing {m.bearing:.1f} deg for course {heading:.1f} deg, vehicle at 70 % height; "
      "saved tile_map_follow.png")

# smoothing: between two 1 Hz fixes the marker moves part of the way, steadily
before = m._vehicle_ref(time.monotonic())
m.update_vehicle(state_of(track[6]))
target6 = to_ref(track[6]["lat"], track[6]["lon"])
fractions = []
for _ in range(6):
    run_for(0.12)
    pos = m._vehicle_ref(time.monotonic())
    dx, dy = target6[0] - before[0], target6[1] - before[1]
    fractions.append(((pos[0] - before[0]) * dx + (pos[1] - before[1]) * dy) / max(1e-9, dx * dx + dy * dy))
assert m._timer.isActive(), "frame timer not running during the animation"
assert all(0.0 < f < 1.0 for f in fractions), fractions
assert all(b > a for a, b in zip(fractions, fractions[1:])), fractions
run_for(1.6)
assert m._vehicle_ref(time.monotonic()) == target6
wait_until(lambda: not m._timer.isActive(), 3, "frame timer stopping when nothing moves")
m.hide()
m.update_vehicle(state_of(track[7]))
run_for(0.3)
assert not m._timer.isActive(), "frame timer running while hidden"
m.show()
run_for(1.5)
print("3c smoothing: marker part-way between fixes (" + ", ".join(f"{f:.2f}" for f in fractions)
      + "); timer stops when idle and while hidden")

# heading held when stopped, north-up with no heading at all
stopped = dict(track[7], crs=123.0)                       # same position: stopped, course is noise
m.update_vehicle(state_of(stopped))
run_for(1.2)
m.update_vehicle(state_of(stopped))
run_for(1.6)
m.update_vehicle(state_of(stopped))
run_for(0.5)
assert abs(wrap(m.bearing - track[7]["crs"])) < 5, ("course noise while stopped must be ignored", m.bearing)
m2 = SW7TileMap()
m2.resize(W, H)
m2.show()
m2.update_vehicle(state_of(dict(track[0], crs=None)))
run_for(0.8)
assert not m2.heading_up and abs(wrap(m2.bearing)) < 0.5 and m2._marker_heading is None
m2.close()
print("3d stopped: course noise ignored (heading held); no course: north-up with a dot marker")

# ---- 4. disk cache ----------------------------------------------------------------------------
hits_before = len(Tiles.hits)
m3 = SW7TileMap()
m3.resize(W, H)
m3.show()
for rec in track[5:8]:
    m3.update_vehicle(state_of(rec))
    run_for(0.4)
run_for(1.5)
from_disk_only = [k for k in m3.requested_tiles if (cache / str(k[0]) / str(k[1]) / f"{k[2]}.png").is_file()
                  and k in req]
assert not from_disk_only, f"cached tiles fetched again: {from_disk_only}"
assert not m3.vector_fallback_active
m3.close()
old_key = req[0]
old_path = cache / str(old_key[0]) / str(old_key[1]) / f"{old_key[2]}.png"
old_time = time.time() - 31 * 24 * 3600
os.utime(old_path, (old_time, old_time))
m4 = SW7TileMap()
m4.resize(W, H)
m4.show()
m4.update_vehicle(state_of(track[0]))
wait_until(lambda: old_key in m4.requested_tiles and not m4._in_flight, 8, "refresh of a 31-day-old tile")
assert time.time() - old_path.stat().st_mtime < 60, "refreshed tile not rewritten"
fresh = [k for k in m4.requested_tiles if k != old_key and k in req]
assert not fresh, f"tiles under 30 days old fetched again: {fresh}"
m4.close()
print(f"4 cache: new map fetched none of the cached tiles ({len(Tiles.hits) - hits_before} other hits); "
      "a 31-day-old tile was fetched again")

# ---- 5. no fix ----------------------------------------------------------------------------------
last = m.vehicle
m.update_vehicle(state_of(no_fix))
run_for(0.8)
assert m.waiting_for_fix and m.last_fix == last
cam = m.camera()
lx, ly = to_ref(*last)
assert math.hypot(cam.x - lx, cam.y - ly) < 1.0, "camera left the last known position"
m.grab().save(str(HERE / "tile_map_no_fix.png"))
m5 = SW7TileMap()
m5.resize(W, H)
m5.show()
st = state_of(no_fix)
m5.update_vehicle(st)
run_for(0.5)
c5 = m5.camera()
ux, uy = to_ref(-33.9570, 18.4610)
assert m5.waiting_for_fix and math.hypot(c5.x - ux, c5.y - uy) < 1.0, "no position ever: should show UCT"
assert m5.requested_tiles, "the UCT area should still load tiles"
m5.close()
print("5 no fix: 'Waiting for GPS fix' over the last known position (or UCT); saved tile_map_no_fix.png")

# ---- 6. replay badge ------------------------------------------------------------------------------
m.update_vehicle(state_of(track[8], bridge_replay=True))
run_for(1.2)
assert m.replay, "map should know the data is replayed"
img = m.grab().toImage()
ucx = m._usable_centre()[0]
px = img.pixelColor(int(ucx) - 30, int(m._pill_y))   # below the turn banner when navigating
amber = THEME.status("warn")
assert abs(px.red() - amber.red()) < 40 and abs(px.green() - amber.green()) < 40 and px.blue() < 120, px.name()
img.save(str(HERE / "tile_map_replay.png"))
rec_fw = dict(track[8], age_ms=300)                     # fw "0.7.1-replay" alone also counts
assert ldp.is_replay({"esp32": rec_fw, "bridge": {"replay": False}})
m.update_vehicle(state_of(track[9]))
run_for(0.3)
assert not m.replay
card = RideQualityCard()
card.show()
card.set_telemetry({"esp32": rec_fw, "tof": None, "bridge": {"version": "1.0", "replay": True,
                                                            "replay_file": "replay_uct_route.txt"}})
assert card.replay and card.replay_badge.isVisible() and card.replay_badge.text() == "REPLAY"
card.set_telemetry({"esp32": dict(rec_fw, fw="0.7.1"), "tof": None, "bridge": {"replay": False, "replay_file": None}})
assert not card.replay and not card.replay_badge.isVisible()
card.close()
# the provider marks replayed states with data_source "sw7_replay"
got = []
fake_manager = SimpleNamespace(sim=None, ingest_live_state=lambda s, source: got.append(source))
prov = ldp.LiveDataProvider(fake_manager, url="http://127.0.0.1:9")
prov.apply({"esp32": rec_fw, "tof": None, "bridge": {"replay": True, "replay_file": "x.txt"}})
prov.apply({"esp32": dict(rec_fw, fw="0.7.1"), "tof": None, "bridge": {"replay": False, "replay_file": None}})
assert got == ["sw7_replay", "sw7_telemetry"], got
print("6 replay: amber REPLAY badge on the map and the ride card; provider source sw7_replay; "
      "saved tile_map_replay.png")

# ---- 7. tile server down, empty cache: vector roads -------------------------------------------------
os.environ["TUKZIE_TILE_URL"] = "http://127.0.0.1:9/{z}/{x}/{y}.png"     # nothing listens on port 9
os.environ["TUKZIE_TILE_CACHE"] = str(scratch / "empty_cache")
lat0, lon0 = track[0]["lat"], track[0]["lon"]
roads = []
for i in range(-6, 7):
    roads.append({"name": f"Test Road {i}", "hw": "secondary" if i % 3 == 0 else "residential",
                  "pts": [[lat0 + i * 0.0006, lon0 - 0.01], [lat0 + i * 0.0006, lon0 + 0.01]]})
    roads.append({"name": "", "hw": "residential",
                  "pts": [[lat0 - 0.01, lon0 + i * 0.0007], [lat0 + 0.01, lon0 + i * 0.0007]]})
m6 = SW7TileMap()
m6.resize(W, H)
m6.show()
m6.set_context({"roads": roads, "places": [], "centre": {"lat": lat0, "lon": lon0}, "span": 0.02})
m6.update_vehicle(state_of(track[0]))
wait_until(lambda: m6.tile_status == "offline", 8, "tile requests failing")
run_for(0.8)
assert m6.vector_fallback_active, "missing tiles must fall back to the vector roads"
img = m6.grab().toImage()
bg = THEME.color("bg_alt") if hasattr(THEME, "color") else None
road_px = 0
for yy in range(0, H, 6):
    for xx in range(0, W, 6):
        c = img.pixelColor(xx, yy)
        if bg is not None and abs(c.red() - bg.red()) + abs(c.green() - bg.green()) + abs(c.blue() - bg.blue()) > 60:
            road_px += 1
assert road_px > 200, f"offline map looks blank ({road_px} non-background samples)"
img.save(str(HERE / "tile_map_offline.png"))
n_req = len(m6.requested_tiles)
run_for(2.0)
assert len(m6.requested_tiles) == n_req, "kept hammering a dead tile server"
m6.close()
print(f"7 server down: vector roads drawn ({road_px} road samples), retries paused; saved tile_map_offline.png")
os.environ["TUKZIE_TILE_URL"] = TILE_URL
os.environ["TUKZIE_TILE_CACHE"] = str(cache)

# ---- 8. interaction ---------------------------------------------------------------------------------
m.update_vehicle(state_of(track[9]))
run_for(1.2)
z_before = m._zoom_target
m._zoom(.7)
assert m.auto_follow and m._zoom_target > z_before, "zoom must keep follow mode"
QTest.mousePress(m, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(500, 300))
for i in range(1, 6):
    QTest.mouseMove(m, QPoint(500 + i * 30, 300 + i * 10))
QTest.mouseRelease(m, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(650, 350))
assert not m.auto_follow and follow_events and follow_events[-1] is False, "drag must leave follow mode"
m.set_follow_mode(True)
assert m.auto_follow and follow_events[-1] is True
m.show_overview()
try:
    wait_until(lambda: abs(wrap(m.bearing)) < 0.5, 5, "overview turning north-up")
except AssertionError:
    print("overview state:", m._mode, m.bearing, m._bearing_now, m._timer.isActive(), m.isVisible(), m._tween_from, m._zoom_now, m._zoom_target); raise
assert not m.auto_follow
for q in plan_pts:
    sp = m.screen_point(q.lat, q.lon)
    assert 0 <= sp.x() <= W and 0 <= sp.y() <= H, f"route point off screen in overview: {sp}"
m.set_follow_mode(True)
run_for(1.0)
m.close()
assert not errors, errors
print("8 interaction: zoom keeps follow, drag leaves it, Overview fits the route north-up")

# ---- 9. simulated drive -----------------------------------------------------------------------------
m9 = SW7TileMap()
m9.resize(W, H)
m9.set_plan(plan, reset_view=True)
m9.show()
run_for(0.3)
nofix = SimpleNamespace(latitude=None, longitude=None, heading=None, speed_kmh=None,
                        data_source="sw7_telemetry", signal_validity={})
m9.update_vehicle(nofix)
assert m9.sim_available and m9.sim_button.isVisible() and m9.sim_button.text() == "Simulate drive"
assert m9.start_simulation()
assert m9.simulating and not m9.waiting_for_fix and m9.auto_follow and m9.sim_button.text() == "End simulation"
start_pt = m9.vehicle
for _ in range(5):
    m9._sim_step()
assert m9.vehicle != start_pt and 0 < m9.progress < 1
assert abs(m9._sim_m - 5 * 25 / 3.6) < 0.5, m9._sim_m
m9.update_vehicle(nofix)
assert m9.simulating and m9.vehicle is not None, "live data without a position must not stop the simulation"
m9.set_progress(0.0)
assert m9.progress > 0, "the page's progress must not overwrite the simulation's"
assert m9.last_fix is None, "a simulated position must never be recorded as a real fix"
run_for(2.0)
_, _, course = m9._sim_point(m9._sim_m)
assert abs(wrap(m9.bearing - course)) < 25, (m9.bearing, course)
m9.grab().save(str(HERE / "tile_map_simulated_drive.png"))
steps = 0
while not m9.sim_arrived and steps < 2000:
    m9._sim_step(); steps += 1
assert m9.sim_arrived and m9.progress == 1.0 and m9.simulating and not m9._sim_timer.isActive()
m9.toggle_simulation()
assert not m9.simulating and m9.waiting_for_fix and m9.sim_button.text() == "Simulate drive"
assert m9.start_simulation()
m9.update_vehicle(state_of(track[0]))
assert not m9.simulating and m9.last_fix is not None, "a real fix must stop the simulation"
assert not m9.sim_available and not m9.sim_button.isVisible(), "no simulation while a real fix is recent"
m9.close()

# ---- 10. navigation view: turns from road names, banner, ETA, auto-zoom ------------------------------
# A known route: 300 m north on A Road, right (east) 200 m on B Street, left (north) 150 m on C Avenue.
lat0, lon0 = -33.9600, 18.4600
m_lat, m_lon = 1 / 111320.0, 1 / (111320.0 * math.cos(math.radians(lat0)))
nav_pts = [SimpleNamespace(lat=lat0 + i * 10 * m_lat, lon=lon0, road_name="A Road") for i in range(31)]
nav_pts += [SimpleNamespace(lat=lat0 + 300 * m_lat, lon=lon0 + i * 10 * m_lon, road_name="B Street") for i in range(1, 21)]
nav_pts += [SimpleNamespace(lat=lat0 + (300 + i * 10) * m_lat, lon=lon0 + 200 * m_lon, road_name="C Avenue") for i in range(1, 16)]
nav_plan = SimpleNamespace(route=nav_pts, nearby_roads=[], destination={"lat": nav_pts[-1].lat, "lon": nav_pts[-1].lon},
                           duration_s=130.0)
m10 = SW7TileMap()
m10.resize(W, H)
m10.set_plan(nav_plan, reset_view=False)
m10.show()
kinds = [(mn["kind"], round(mn["at_m"]), mn["road"]) for mn in m10._maneuvers]
assert [k[0] for k in kinds] == ["right", "left", "arrive"], kinds
assert abs(kinds[0][1] - 300) <= 3 and abs(kinds[1][1] - 500) <= 3 and abs(kinds[2][1] - 650) <= 3, kinds
assert m10._instruction(m10._maneuvers[0]) == "Turn right onto B Street"
m10.update_vehicle(nofix)
assert m10.start_simulation()
for _ in range(30):                      # 30 s at 25 km/h is about 208 m
    m10._sim_step()
nxt = m10.next_maneuvers(2)
assert nxt[0][0]["kind"] == "right" and 80 < nxt[0][1] < 100, nxt
assert nxt[1][0]["kind"] == "left"
assert m10._zoom_target > 17.5, "the map should zoom in within 120 m of a turn"
run_for(1.5)
m10.grab().save(str(HERE / "tile_map_navigation.png"))
for _ in range(20):
    m10._sim_step()
assert m10.next_maneuvers(1)[0][0]["kind"] == "left", "after the right turn the next manoeuvre is the left turn"
# a real fix 50 m up A Road: the simulation stops and the position is projected onto the route
real = SimpleNamespace(latitude=lat0 + 50 * m_lat, longitude=lon0 + 3 * m_lon, heading=0.0, speed_kmh=12.0,
                       data_source="sw7_telemetry", signal_validity={})
m10.update_vehicle(real)
assert not m10.simulating and abs(m10._along_m - 50) < 3, m10._along_m
assert m10.next_maneuvers(1)[0][0]["kind"] == "right" and abs(m10.next_maneuvers(1)[0][1] - 250) < 4
m10.close()
assert not errors, errors
server.shutdown()
print("10 navigation: right then left found from road names, distance to the turn counts down, zoom in near a "
      "turn, a real fix is projected onto the route; saved tile_map_navigation.png")
print(f"9 simulated drive: starts without a fix, 25 km/h along the route, heading-up, ignores position-less "
      f"live data, arrives after {steps + 5} steps, ends on request, a real fix stops it; saved tile_map_simulated_drive.png")
print("ALL TILE MAP TESTS PASSED")
