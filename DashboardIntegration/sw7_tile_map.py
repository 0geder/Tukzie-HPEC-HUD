"""
SW7TileMap: a moving street map for the Navigation page without QtWebEngine.

The dashboard team's Leaflet web map (QtWebEngine) segfaults on the Pi 5's
real display (PI5_MAP_CRASH.md), and their native fallback (NativeRouteMap)
only draws vector roads from the small offline index. This widget is a
drop-in for NativeRouteMap (same methods and attributes that
navigation_page.py uses) that draws OpenStreetMap raster tiles with plain
QPainter, so nothing here touches QtWebEngine or OpenGL.

Tiles
  URL https://tile.openstreetmap.org/{z}/{x}/{y}.png, or TUKZIE_TILE_URL.
  Fetched with QNetworkAccessManager, at most 2 requests at a time, with the
  User-Agent "TUKZIE-SW7-dashboard/1.0 (UCT student project)", only for
  tiles on screen (no bulk prefetching, per the OSM tile usage policy).
  Disk cache ~/.cache/sw7_tiles/{z}/{x}/{y}.png (or TUKZIE_TILE_CACHE): a
  tile on disk is always used first and is not fetched again while it is
  under 30 days old, so areas already driven work offline. While a tile is
  missing, a lower-zoom tile from memory is scaled up; if there is none, the
  team's vector roads (set_context / set_plan) are drawn on a plain
  background, so the map never goes blank.

Follow mode (Uber-like)
  Heading-up: the map turns so the vehicle's heading points up, with the
  vehicle as a navigation arrow at 70 % of the height, at zoom 17. GNSS
  course is noise when stopped, so below 3 km/h (speed from the state, or
  estimated from successive fixes when speed is unknown) the last good
  heading is held for 20 s, then the map eases back to north-up; with no
  heading at all it is north-up and the vehicle is a dot. Position and
  heading arrive at about 1 Hz; the marker and the camera move linearly
  from where they are to each new fix over the measured update interval,
  redrawn at about 30 fps by a QTimer that runs only while the widget is
  visible and something is moving.
  Drag pans and leaves follow mode (as NativeRouteMap does); wheel, the +/-
  buttons and a two-finger pinch zoom (zoom keeps follow mode).
  show_overview() fits the route, north-up.

No position: the map stays at the last known position (or the UCT area) with
a "Waiting for GPS fix" banner. Replayed data (VehicleState.data_source
"sw7_replay", set by live_data_provider.py) shows an amber REPLAY badge.

Simulated drive: with a planned route and no real fix in the last 10 s, a
"Simulate drive" button drives a marker along the route at SIM_KMH, one
position a second like the GNSS, heading-up in follow mode, with the route
behind it drawn as done. It is labelled SIMULATED DRIVE with the distance and
time left the whole time, and it only moves this map: nothing is written to
the vehicle state, so speed, battery and the other pages keep showing real
data or "--". A real fix stops it at once.

Navigation view (Planning/map-navigation-prompt.md): with a route and a position (real or simulated) a
Google-style turn banner shows the next manoeuvre, its distance along the route and the one after it, and a
card at the bottom gives time left, distance left and arrival time. The team's planner returns no turn steps,
so manoeuvres are placed where the road name changes and typed from the change in bearing over about 20 m
either side (under 20 deg continue, 20 to 45 slight, 45 to 135 turn, over 135 U-turn). The map zooms in
within 120 m of a turn and back out after it.

Drop this file into app/pages/ (tests/dashboard_patches.py does, and swaps
the import in navigation_page.py; TUKZIE_TILE_MAP=0 restores NativeRouteMap).
QtWidgets, QtGui and QtNetwork only; colours from THEME.
"""
from __future__ import annotations

import math
import os
import time
from collections import OrderedDict
from types import SimpleNamespace

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QTransform
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QPushButton, QWidget

from ..theme import THEME

DEFAULT_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
USER_AGENT = b"TUKZIE-SW7-dashboard/1.0 (UCT student project)"
ATTRIBUTION = "© OpenStreetMap contributors"
CACHE_MAX_AGE_S = 30 * 24 * 3600     # a cached tile younger than this is never fetched again
MAX_CONCURRENT = 2                   # OSM policy: keep parallel downloads low
REQUEST_TIMEOUT_MS = 10000
NET_RETRY_S = 15.0                   # after a network error, wait this long before trying again
TILE_RETRY_S = 60.0                  # a tile that failed with an HTTP error
BLOCKED_RETRY_S = 300.0              # HTTP 403 / 429: the server asks us to back off
MEM_TILES = 192                      # decoded tiles kept in memory (about 50 MB)
DISK_LOADS_PER_FRAME = 12

MIN_ZOOM, MAX_ZOOM, MAX_TILE_ZOOM = 3.0, 20.0, 19
FOLLOW_ZOOM = 17.0
NO_FIX_ZOOM = 16.0
REF_Z = 20                           # all geometry is kept in world pixels at zoom 20
REF_PX = 256.0 * 2 ** REF_Z
EARTH_M = 40075016.686

FRAME_MS = 33                        # about 30 fps while animating
FOLLOW_Y = 0.70                      # vehicle at 70 % of the height in follow mode
LOW_SPEED_KMH = 3.0
HEADING_HOLD_S = 20.0
SNAP_M = 300.0                       # a jump larger than this is not animated
TWEEN_S = 0.6                        # camera transition between follow / overview
UCT = (-33.9570, 18.4610)
SIM_KMH = 25.0                       # simulated drive speed (a tuk-tuk in town)
SIM_TICK_MS = 1000                   # one simulated position a second, like the GNSS
SIM_REAL_FIX_S = 10.0                # the simulation is offered only without a real fix this recent


def _num(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _metres(a, b):
    """Great-circle distance in metres between two (lat, lon) points."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000.0 * math.asin(min(1.0, math.sqrt(h)))


def _course(a, b):
    """Initial course from a to b, degrees clockwise from true north."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    return math.degrees(math.atan2(y, x)) % 360.0


def to_ref(lat, lon):
    """(lat, lon) in degrees -> Web Mercator world pixels at zoom 20."""
    lat = max(-85.05112878, min(85.05112878, float(lat)))
    s = math.sin(math.radians(lat))
    return ((float(lon) + 180.0) / 360.0 * REF_PX,
            (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * REF_PX)


def from_ref(x, y):
    lon = x / REF_PX * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi - 2 * math.pi * y / REF_PX)))
    return lat, lon


def tile_of(lat, lon, z):
    """The (x, y) of the tile at zoom z that contains (lat, lon)."""
    x, y = to_ref(lat, lon)
    span = 256.0 * 2 ** (REF_Z - z)
    return int(x // span), int(y // span)


def _ref_per_m(y):
    lat = from_ref(0.0, y)[0]
    return REF_PX / (EARTH_M * max(0.05, math.cos(math.radians(lat))))


def _wrap(deg):
    return (deg + 180.0) % 360.0 - 180.0


class _Cam:
    __slots__ = ("x", "y", "zoom", "bearing", "ax", "ay")

    def __init__(self, x, y, zoom, bearing, ax, ay):
        self.x, self.y, self.zoom, self.bearing, self.ax, self.ay = x, y, zoom, bearing, ax, ay

    def blend(self, other, k):
        l = lambda a, b: a + (b - a) * k  # noqa: E731
        return _Cam(l(self.x, other.x), l(self.y, other.y), l(self.zoom, other.zoom),
                    (self.bearing + _wrap(other.bearing - self.bearing) * k) % 360.0,
                    l(self.ax, other.ax), l(self.ay, other.ay))


class SW7TileMap(QWidget):
    """Street-tile map, drop-in for NativeRouteMap (see the module docstring)."""

    follow_changed = Signal(bool)     # auto_follow changed (drag, Follow, Overview)

    def __init__(self, parent=None):
        super().__init__(parent)
        # NativeRouteMap's public attributes
        self.route = []
        self.roads = []
        self.context_roads = []
        self.places = []
        self.vehicle = None
        self.destination = None
        self.progress = 0.0
        self.context_centre = UCT
        self.context_span = 0.035
        self.auto_follow = True
        self.heading = 0.0
        # SW-7 status, for the tests and Diagnostics
        self.tile_url = os.environ.get("TUKZIE_TILE_URL", "").strip() or DEFAULT_TILE_URL
        self.cache_dir = os.path.expanduser(os.environ.get("TUKZIE_TILE_CACHE", "").strip()
                                             or os.path.join("~", ".cache", "sw7_tiles"))
        self.requested_tiles = []         # every (z, x, y) asked of the server, in order
        self.max_in_flight = 0
        self.tile_status = "starting"     # online / offline / starting
        self.vector_fallback_active = False
        self.heading_up = False
        self.replay = False
        self.last_fix = None              # (lat, lon) of the last real position
        self.simulating = False           # simulated drive running (or arrived, until ended)
        self.sim_arrived = False
        self._sim_path = []               # [(lat, lon, metres from the start)] of the route
        self._sim_m = 0.0                 # metres driven in the simulation
        self._real_fix_time = None
        self._maneuvers = []              # [{"at_m", "kind", "road"}] along the route, last one "arrive"
        self._route_total_m = 0.0
        self._along_m = None              # vehicle's distance along the route (m), None without a position
        self._plan_duration_s = 0.0
        self._auto_zoom_near = None       # last auto-zoom state, so a manual zoom is not fought every fix

        self._mode = "follow"             # follow / explore / overview
        self._zoom_now = self._zoom_target = NO_FIX_ZOOM
        self._bearing_now = 0.0
        self._explore = None              # _Cam while exploring
        self._overview = None             # _Cam target of the overview
        self._tween_from = None
        self._tween_start = 0.0
        self._last_cam = None
        # vehicle animation
        self._fix_from = self._fix_to = None
        self._seg_start = 0.0
        self._seg_dur = 0.0
        self._interval = 1.0
        self._last_fix_time = None
        self._last_move_time = None
        self._est_kmh = None
        self._good_heading = None
        self._good_heading_time = 0.0
        self._marker_heading = None
        # geometry in reference pixels
        self._route_poly = QPolygonF()
        self._route_cum = []
        self._road_polys = []
        # tiles
        self._mem = OrderedDict()
        self._disk_missing = set()
        self._stale = set()
        self._in_flight = {}
        self._failed = {}
        self._net_down_until = 0.0
        self._disk_loads = 0
        self._net = QNetworkAccessManager(self)
        # interaction
        self._press = None
        self._dragging = False
        self._pinch = None
        self._last_tick = time.monotonic()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self._tick)
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._kick)

        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.zoom_in = QPushButton("+", self)
        self.zoom_out = QPushButton("−", self)
        for button in (self.zoom_in, self.zoom_out):
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.zoom_in.clicked.connect(lambda: self._zoom(.7))
        self.zoom_out.clicked.connect(lambda: self._zoom(1.4))
        self.sim_button = QPushButton("Simulate drive", self)
        self.sim_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sim_button.clicked.connect(self.toggle_simulation)
        self.sim_button.hide()
        self._sim_timer = QTimer(self)
        self._sim_timer.setInterval(SIM_TICK_MS)
        self._sim_timer.timeout.connect(self._sim_step)
        THEME.changed.connect(self._apply_theme)
        self._apply_theme()

    # ---- NativeRouteMap API ------------------------------------------------------
    def set_plan(self, plan, reset_view=True):
        self.route = list(getattr(plan, "route", []) or []) if plan else []
        self.roads = list(getattr(plan, "nearby_roads", []) or []) if plan else []
        self.destination = getattr(plan, "destination", None) if plan else None
        self._route_poly, self._route_cum = QPolygonF(), []
        total = 0.0
        prev = None
        for q in self.route:
            try:
                x, y = to_ref(float(q.lat), float(q.lon))
            except (AttributeError, TypeError, ValueError):
                continue
            if prev is not None:
                total += math.hypot(x - prev[0], y - prev[1])
            self._route_poly.append(QPointF(x, y))
            self._route_cum.append(total)
            prev = (x, y)
        self._rebuild_roads()
        path = self._route_metres()
        self._build_maneuvers(plan)
        if path != self._sim_path:
            self.stop_simulation()
            self._sim_path = path
        self._update_sim_button()
        if plan and reset_view and not self.simulating:
            self.show_overview()
        self._kick()

    def set_context(self, payload):
        payload = payload or {}
        self.context_roads = list(payload.get("roads") or [])
        self.places = list(payload.get("places") or [])
        centre = payload.get("centre") or {}
        if centre.get("lat") is not None and centre.get("lon") is not None:
            self.context_centre = (float(centre["lat"]), float(centre["lon"]))
        try:
            self.context_span = max(0.008, min(0.08, float(payload.get("span", self.context_span))))
        except (TypeError, ValueError):
            pass
        self._rebuild_roads()
        self._kick()

    def set_progress(self, value):
        if self.simulating:               # the simulation sets its own progress
            return
        try:
            self.progress = max(0.0, min(1.0, float(value or 0.0)))
        except (TypeError, ValueError):
            self.progress = 0.0
        self.update()

    def update_vehicle(self, state):
        now = time.monotonic()
        simulated = bool(getattr(state, "sw7_simulated", False))
        if not simulated and _num(getattr(state, "latitude", None)) is not None \
                and _num(getattr(state, "longitude", None)) is not None:
            self._real_fix_time = now
            if self.simulating:
                self.stop_simulation()    # a real position always wins
        elif not simulated and self.simulating:
            return                        # live data without a position: keep the simulated drive
        self.replay = "replay" in str(getattr(state, "data_source", "") or "")
        validity = getattr(state, "signal_validity", None) or {}
        heading = _num(getattr(state, "heading", None))
        if validity.get("heading") is False:
            heading = None
        self.heading = heading if heading is not None else 0.0
        lat, lon = _num(getattr(state, "latitude", None)), _num(getattr(state, "longitude", None))
        if lat is None or lon is None:
            self.vehicle = None
            self._kick()
            return
        self.vehicle = (lat, lon)
        if not simulated:
            self.last_fix = (lat, lon)
        p = to_ref(lat, lon)
        speed = _num(getattr(state, "speed_kmh", None))
        moved = False
        if self._fix_to is None:
            if self._mode == "follow":                 # first fix: glide from the UCT view to the vehicle
                self._start_tween()
                if self._zoom_target == NO_FIX_ZOOM:
                    self._zoom_target = FOLLOW_ZOOM
            self._fix_from = self._fix_to = p
            self._seg_dur = 0.0
            self._last_fix_time = self._last_move_time = now
        elif p != self._fix_to:
            gap = now - (self._last_fix_time or now)
            dist_m = math.hypot(p[0] - self._fix_to[0], p[1] - self._fix_to[1]) / _ref_per_m(p[1])
            if 0.05 < gap < 5.0:
                self._interval = 0.7 * self._interval + 0.3 * gap
            move_gap = now - (self._last_move_time or now)
            if move_gap > 0.05:
                self._est_kmh = dist_m / move_gap * 3.6
            if dist_m > SNAP_M:
                self._fix_from = self._fix_to = p
                self._seg_dur = 0.0
            else:
                self._fix_from = self._vehicle_ref(now)
                self._fix_to = p
                self._seg_start = now
                self._seg_dur = max(0.1, min(1.5, self._interval))
            self._last_fix_time = self._last_move_time = now
            moved = True
        else:
            self._last_fix_time = now
            if now - (self._last_move_time or now) > 2.5:
                self._est_kmh = 0.0
        # Trust the course only while moving: from the state's speed when it is known,
        # otherwise only on a new position that implies at least 3 km/h (live mode has no
        # speed yet, and the bridge repeats each 1 Hz record on its 2 Hz polls).
        if speed is not None:
            moving = speed >= LOW_SPEED_KMH
        else:
            moving = moved and self._est_kmh is not None and self._est_kmh >= LOW_SPEED_KMH
        if heading is not None and moving:
            self._good_heading = heading % 360.0
            self._good_heading_time = now
            if self._marker_heading is None:
                self._marker_heading = self._good_heading
        self._update_navigation(lat, lon)
        self._update_sim_button()
        self._kick()

    # ---- navigation (turn banner, ETA, auto-zoom) --------------------------------------
    def _build_maneuvers(self, plan):
        self._maneuvers, self._along_m, self._auto_zoom_near = [], None, None
        self._plan_duration_s = float(getattr(plan, "duration_s", 0) or 0) if plan else 0.0
        pts, total, prev = [], 0.0, None
        for q in self.route:
            try:
                lat, lon = float(q.lat), float(q.lon)
            except (AttributeError, TypeError, ValueError):
                continue
            if prev is not None:
                total += _metres(prev, (lat, lon))
            pts.append((lat, lon, total, str(getattr(q, "road_name", "") or "").strip()))
            prev = (lat, lon)
        self._route_pts, self._route_total_m = pts, total
        if len(pts) < 2:
            return
        name = pts[0][3]
        for i in range(1, len(pts) - 1):
            if not pts[i][3] or pts[i][3] == name:
                continue
            name_change = i
            # the turn itself: the point near the name change where the route bends most
            def bend(c):
                if c <= 0 or c >= len(pts) - 1:
                    return 0.0
                return abs(_wrap(_course(pts[c][:2], pts[c + 1][:2]) - _course(pts[c - 1][:2], pts[c][:2])))
            i = max(range(max(1, name_change - 2), min(len(pts) - 1, name_change + 2)), key=bend)
            j = i
            while j > 0 and pts[i][2] - pts[j][2] < 20.0:
                j -= 1
            k = i
            while k < len(pts) - 1 and pts[k][2] - pts[i][2] < 20.0:
                k += 1
            if j == i or k == i:
                continue
            turn = _wrap(_course(pts[i][:2], pts[k][:2]) - _course(pts[j][:2], pts[i][:2]))
            a = abs(turn)
            side = "right" if turn > 0 else "left"
            kind = ("straight" if a < 20 else f"slight_{side}" if a < 45 else side if a < 135 else "uturn")
            self._maneuvers.append({"at_m": pts[i][2], "kind": kind, "road": pts[name_change][3]})
            name = pts[name_change][3]
        self._maneuvers.append({"at_m": total, "kind": "arrive", "road": ""})

    def _update_navigation(self, lat, lon):
        if not self._maneuvers or len(getattr(self, "_route_pts", [])) < 2:
            self._along_m = None
            return
        if self.simulating:
            self._along_m = self._sim_m
        else:
            best, along = None, 0.0
            for (a_lat, a_lon, a_m, _), (b_lat, b_lon, b_m, _) in zip(self._route_pts, self._route_pts[1:]):
                ax, ay = to_ref(a_lat, a_lon); bx, by = to_ref(b_lat, b_lon); px, py = to_ref(lat, lon)
                dx, dy = bx - ax, by - ay
                t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
                d = math.hypot(ax + t * dx - px, ay + t * dy - py)
                if best is None or d < best:
                    best, along = d, a_m + t * (b_m - a_m)
            self._along_m = along
        nxt = self.next_maneuvers(1)
        near = bool(nxt) and nxt[0][1] < 120.0 and nxt[0][0]["kind"] != "arrive"
        if self._mode == "follow" and near != self._auto_zoom_near:
            self._zoom_target = FOLLOW_ZOOM + (0.8 if near else 0.0)
        self._auto_zoom_near = near

    def next_maneuvers(self, n=2):
        """[(manoeuvre, metres to it)] ahead of the vehicle, nearest first."""
        if self._along_m is None:
            return []
        ahead = [(m, m["at_m"] - self._along_m) for m in self._maneuvers if m["at_m"] - self._along_m > -5.0]
        return ahead[:n]

    @property
    def navigating(self):
        return self._along_m is not None and bool(self._maneuvers)

    # ---- simulated drive -------------------------------------------------------------------
    def _route_metres(self):
        pts, total, prev = [], 0.0, None
        for q in self.route:
            try:
                lat, lon = float(q.lat), float(q.lon)
            except (AttributeError, TypeError, ValueError):
                continue
            if prev is not None:
                total += _metres(prev, (lat, lon))
            pts.append((lat, lon, total))
            prev = (lat, lon)
        return pts if len(pts) >= 2 and total > 1.0 else []

    @property
    def sim_available(self):
        recent = self._real_fix_time is not None and time.monotonic() - self._real_fix_time < SIM_REAL_FIX_S
        return bool(self._sim_path) and not recent

    def toggle_simulation(self):
        if self.simulating:
            self.stop_simulation()
        else:
            self.start_simulation()

    def start_simulation(self):
        if not self.sim_available:
            return False
        self.simulating, self.sim_arrived, self._sim_m = True, False, 0.0
        self.vehicle = None
        self._fix_from = self._fix_to = None
        self._good_heading = self._marker_heading = None
        if self._mode != "follow":
            self._start_tween()
            self._mode = "follow"
        self._set_auto_follow(True)
        self._zoom_target = FOLLOW_ZOOM
        self._sim_step()
        self._sim_timer.start()
        self._update_sim_button()
        return True

    def stop_simulation(self):
        if not self.simulating:
            return
        self._sim_timer.stop()
        self.simulating = self.sim_arrived = False
        self.vehicle = None
        self._fix_from = self._fix_to = None
        self._good_heading = self._marker_heading = None
        self.progress = 0.0
        self._zoom_target = NO_FIX_ZOOM
        self._update_sim_button()
        self._kick()

    def _sim_point(self, m):
        path = self._sim_path
        for (la0, lo0, c0), (la1, lo1, c1) in zip(path, path[1:]):
            if m <= c1 or (la1, lo1, c1) == path[-1]:
                k = 0.0 if c1 <= c0 else max(0.0, min(1.0, (m - c0) / (c1 - c0)))
                return la0 + (la1 - la0) * k, lo0 + (lo1 - lo0) * k, _course((la0, lo0), (la1, lo1))
        la, lo, _ = path[-1]
        return la, lo, None

    def _sim_step(self):
        if not self.simulating or not self._sim_path:
            return
        total = self._sim_path[-1][2]
        if self._sim_m > 0 or self._fix_to is not None:
            self._sim_m = min(total, self._sim_m + SIM_KMH / 3.6 * SIM_TICK_MS / 1000.0)
        arrived = self._sim_m >= total - 0.01
        lat, lon, course = self._sim_point(self._sim_m)
        self.update_vehicle(SimpleNamespace(
            latitude=lat, longitude=lon, heading=course, speed_kmh=0.0 if arrived else SIM_KMH,
            data_source="sw7_simulated_drive", signal_validity={}, sw7_simulated=True))
        self.progress = self._sim_m / total if total > 0 else 1.0
        if arrived:
            self._sim_timer.stop()
            self.sim_arrived = True
            self._update_sim_button()
        self.update()

    def sim_remaining(self):
        """(metres, minutes) left in the simulated drive."""
        if not self._sim_path:
            return 0.0, 0.0
        left = max(0.0, self._sim_path[-1][2] - self._sim_m)
        return left, left / (SIM_KMH / 3.6) / 60.0

    def _update_sim_button(self):
        if self.simulating:
            self.sim_button.setText("End simulation")
            self.sim_button.show()
        elif self.sim_available:
            self.sim_button.setText("Simulate drive")
            self.sim_button.show()
        else:
            self.sim_button.hide()

    def set_follow_mode(self, enabled):
        enabled = bool(enabled)
        if enabled and self._mode != "follow":
            self._start_tween()
            self._mode = "follow"
            self._zoom_target = FOLLOW_ZOOM if self._fix_to is not None else NO_FIX_ZOOM
        elif not enabled and self._mode == "follow":
            self._freeze()
        self._set_auto_follow(enabled)
        self._kick()

    def show_overview(self):
        self._start_tween()
        self._overview = self._fit_camera()
        self._zoom_target = self._overview.zoom
        self._mode = "overview"
        self._set_auto_follow(False)
        self._kick()

    def _zoom(self, factor):
        """factor < 1 zooms in (NativeRouteMap convention). Follow mode stays on."""
        if self._mode == "overview":
            self._freeze()
        self._zoom_target = max(MIN_ZOOM, min(MAX_ZOOM, self._zoom_target - math.log2(max(1e-3, factor))))
        self._kick()

    # ---- public helpers (tests, Diagnostics) ---------------------------------------
    @property
    def waiting_for_fix(self):
        return self.vehicle is None

    @property
    def bearing(self):
        return self._last_cam.bearing if self._last_cam else self._bearing_now

    def camera(self):
        return self._camera(time.monotonic())

    def screen_point(self, lat, lon):
        """Where (lat, lon) is drawn with the current camera."""
        return self._transform(self._camera(time.monotonic())).map(QPointF(*to_ref(lat, lon)))

    def vehicle_screen_point(self):
        pos = self._vehicle_ref(time.monotonic())
        return None if pos is None else self._transform(self._camera(time.monotonic())).map(QPointF(*pos))

    def tile_path(self, z, x, y):
        return os.path.join(self.cache_dir, str(z), str(x), f"{y}.png")

    # ---- animation -------------------------------------------------------------------
    def _set_auto_follow(self, value):
        if self.auto_follow != value:
            self.auto_follow = value
            self.follow_changed.emit(value)

    def _kick(self):
        if self.isVisible() and not self._timer.isActive():
            self._last_tick = time.monotonic()
            self._timer.start()
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self._kick()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self):
        now = time.monotonic()
        dt = max(0.0, min(0.2, now - self._last_tick))
        self._last_tick = now
        busy = self._advance(now, dt)
        self.update()
        if not busy:
            self._timer.stop()

    def _heading_valid(self, now):
        return self._good_heading is not None and now - self._good_heading_time <= HEADING_HOLD_S

    def _desired_bearing(self, now):
        if self._mode == "follow":
            return self._good_heading if self._heading_valid(now) else 0.0
        if self._mode == "explore" and self._explore is not None:
            return self._explore.bearing
        return 0.0

    def _advance(self, now, dt):
        busy = False
        dz = self._zoom_target - self._zoom_now
        if abs(dz) > 0.002:
            self._zoom_now += dz * (1 - math.exp(-dt / 0.12))
            busy = True
        else:
            self._zoom_now = self._zoom_target
        desired = self._desired_bearing(now)
        db = _wrap(desired - self._bearing_now)
        if abs(db) > 0.05:
            self._bearing_now = (self._bearing_now + db * (1 - math.exp(-dt / 0.45))) % 360.0
            busy = True
        else:
            self._bearing_now = desired
        self.heading_up = self._mode == "follow" and self._heading_valid(now)
        if self._good_heading is not None:
            if self._marker_heading is None:
                self._marker_heading = self._good_heading
            dm = _wrap(self._good_heading - self._marker_heading)
            if abs(dm) > 0.05:
                self._marker_heading = (self._marker_heading + dm * (1 - math.exp(-dt / 0.25))) % 360.0
                busy = True
        if self._seg_dur > 0 and now < self._seg_start + self._seg_dur:
            busy = True
        if self._tween_from is not None:
            if now - self._tween_start < TWEEN_S:
                busy = True
            else:
                self._tween_from = None
        if self._mode == "follow" and self._heading_valid(now):
            # wake up again when the held heading expires
            remaining = HEADING_HOLD_S - (now - self._good_heading_time)
            if not busy and not self._retry_timer.isActive():
                self._retry_timer.start(int(remaining * 1000) + 50)
        return busy

    def _vehicle_ref(self, now):
        if self._fix_to is None:
            return None
        if self._seg_dur <= 0:
            return self._fix_to
        k = (now - self._seg_start) / self._seg_dur
        if k >= 1.0:
            return self._fix_to
        k = max(0.0, k)
        return (self._fix_from[0] + (self._fix_to[0] - self._fix_from[0]) * k,
                self._fix_from[1] + (self._fix_to[1] - self._fix_from[1]) * k)

    # ---- camera ----------------------------------------------------------------------
    def _insets(self):
        w = self.width()
        return max(26.0, min(390.0, w * .28)), 130.0, 90.0, 65.0   # left, right, top, bottom

    def _usable_centre(self):
        left, right, top, bottom = self._insets()
        w, h = max(1, self.width()), max(1, self.height())
        return left + max(1.0, w - left - right) / 2, top + max(1.0, h - top - bottom) / 2

    def _target_camera(self, now):
        ucx, ucy = self._usable_centre()
        if self._mode == "overview" and self._overview is not None:
            o = self._overview
            return _Cam(o.x, o.y, self._zoom_now, self._bearing_now, ucx, ucy)
        if self._mode == "explore" and self._explore is not None:
            e = self._explore
            return _Cam(e.x, e.y, self._zoom_now, self._bearing_now, e.ax, e.ay)
        pos = self._vehicle_ref(now)
        if pos is None:
            pos = to_ref(*self.context_centre)
            return _Cam(pos[0], pos[1], self._zoom_now, self._bearing_now, ucx, ucy)
        return _Cam(pos[0], pos[1], self._zoom_now, self._bearing_now, ucx, max(1, self.height()) * FOLLOW_Y)

    def _camera(self, now):
        cam = self._target_camera(now)
        if self._tween_from is not None:
            k = (now - self._tween_start) / TWEEN_S
            if k < 1.0:
                k = max(0.0, k)
                cam = self._tween_from.blend(cam, k * k * (3 - 2 * k))
        return cam

    def _start_tween(self):
        self._tween_from = self._last_cam or self._camera(time.monotonic())
        self._tween_start = time.monotonic()

    def _freeze(self):
        """Leave follow / overview, keeping the camera exactly where it is."""
        cam = self._camera(time.monotonic())
        self._explore = cam
        self._tween_from = None
        self._zoom_now = self._zoom_target = cam.zoom
        self._bearing_now = cam.bearing
        self._mode = "explore"
        self._set_auto_follow(False)

    def _transform(self, cam):
        s = 2 ** (cam.zoom - REF_Z)
        t = QTransform()
        t.translate(cam.ax, cam.ay)
        t.rotate(-cam.bearing)
        t.scale(s, s)
        t.translate(-cam.x, -cam.y)
        return t

    def _fit_camera(self):
        pts = [(self._route_poly[i].x(), self._route_poly[i].y()) for i in range(self._route_poly.size())]
        if self.destination:
            try:
                pts.append(to_ref(float(self.destination["lat"]), float(self.destination["lon"])))
            except (KeyError, TypeError, ValueError):
                pass
        pos = self._vehicle_ref(time.monotonic())
        if pos is not None:
            pts.append(pos)
        if len(pts) < 2:
            lat, lon = self.vehicle or self.context_centre
            span = self.context_span if not pts else 0.006
            pts = [to_ref(lat - span, lon - span), to_ref(lat + span, lon + span)]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        left, right, top, bottom = self._insets()
        uw = max(50.0, self.width() - left - right)
        uh = max(50.0, self.height() - top - bottom)
        dx, dy = max(1.0, max(xs) - min(xs)), max(1.0, max(ys) - min(ys))
        zoom = REF_Z + math.log2(min(uw / dx, uh / dy)) - 0.1
        zoom = max(MIN_ZOOM, min(18.0, zoom))
        ucx, ucy = self._usable_centre()
        return _Cam((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, zoom, 0.0, ucx, ucy)

    # ---- tiles -----------------------------------------------------------------------
    def _remember(self, key, pixmap):
        self._mem[key] = pixmap
        self._mem.move_to_end(key)
        while len(self._mem) > MEM_TILES:
            self._mem.popitem(last=False)

    def _tile_pixmap(self, key):
        pm = self._mem.get(key)
        if pm is not None:
            self._mem.move_to_end(key)
            return pm
        if key in self._disk_missing or self._disk_loads >= DISK_LOADS_PER_FRAME:
            return None
        path = self.tile_path(*key)
        try:
            age = time.time() - os.path.getmtime(path)
        except OSError:
            self._disk_missing.add(key)
            return None
        self._disk_loads += 1
        pm = QPixmap(path)
        if pm.isNull():
            self._disk_missing.add(key)
            return None
        if age > CACHE_MAX_AGE_S:
            self._stale.add(key)        # shown now, refreshed when the server answers
        self._remember(key, pm)
        return pm

    def _ancestor(self, key):
        z, x, y = key
        for up in range(1, 6):
            if z - up < 0:
                break
            pkey = (z - up, x >> up, y >> up)
            pm = self._mem.get(pkey)
            if pm is not None:
                n = 1 << up
                size = 256.0 / n
                return pm, QRectF((x - (pkey[1] << up)) * size, (y - (pkey[2] << up)) * size, size, size)
        return None, None

    def _visible_tiles(self, t, z):
        inv, ok = t.inverted()
        if not ok:
            return []
        w, h = self.width(), self.height()
        corners = [inv.map(QPointF(px, py)) for px, py in ((0, 0), (w, 0), (0, h), (w, h))]
        span = 256.0 * 2 ** (REF_Z - z)
        n = 1 << z
        xs, ys = [c.x() for c in corners], [c.y() for c in corners]
        tx0, tx1 = max(0, int(min(xs) // span)), min(n - 1, int(max(xs) // span))
        ty0, ty1 = max(0, int(min(ys) // span)), min(n - 1, int(max(ys) // span))
        screen = QPolygonF(QRectF(self.rect()))
        cam = self._last_cam
        out = []
        if (tx1 - tx0 + 1) * (ty1 - ty0 + 1) > 400:
            return out
        for tx in range(tx0, tx1 + 1):
            for ty in range(ty0, ty1 + 1):
                rect = QRectF(tx * span, ty * span, span, span)
                poly = t.map(QPolygonF(rect))
                if not poly.intersects(screen):
                    continue
                c = t.map(rect.center())
                d = math.hypot(c.x() - cam.ax, c.y() - cam.ay) if cam else 0.0
                out.append((d, (z, tx, ty), rect))
        out.sort(key=lambda item: item[0])
        return [(key, rect) for _d, key, rect in out]

    def _pump(self, wanted):
        now = time.monotonic()
        if now < self._net_down_until:
            if self.isVisible() and not self._retry_timer.isActive():
                self._retry_timer.start(int((self._net_down_until - now) * 1000) + 50)
            return
        for key in wanted:
            if len(self._in_flight) >= MAX_CONCURRENT:
                break
            if key in self._in_flight or self._failed.get(key, 0.0) > now:
                continue
            z, x, y = key
            url = self.tile_url.replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y))
            req = QNetworkRequest(QUrl(url))
            req.setRawHeader(b"User-Agent", USER_AGENT)
            req.setTransferTimeout(REQUEST_TIMEOUT_MS)
            reply = self._net.get(req)
            self._in_flight[key] = reply
            self.requested_tiles.append(key)
            self.max_in_flight = max(self.max_in_flight, len(self._in_flight))
            reply.finished.connect(lambda key=key, reply=reply: self._on_tile(key, reply))

    def _on_tile(self, key, reply):
        self._in_flight.pop(key, None)
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        ok = reply.error() == QNetworkReply.NetworkError.NoError
        data = bytes(reply.readAll()) if ok else b""
        reply.deleteLater()
        now = time.monotonic()
        pm = QPixmap()
        if ok and data and pm.loadFromData(data):
            self.tile_status = "online"
            self._remember(key, pm)
            self._disk_missing.discard(key)
            self._stale.discard(key)
            self._failed.pop(key, None)
            path = self.tile_path(*key)
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                tmp = path + ".part"
                with open(tmp, "wb") as f:
                    f.write(data)
                os.replace(tmp, path)
            except OSError:
                pass                     # cache full or read-only: the tile is still shown
        elif status is None:             # no HTTP answer: offline, DNS, timeout, refused
            self.tile_status = "offline"
            self._net_down_until = now + NET_RETRY_S
            self._failed[key] = now + NET_RETRY_S
        elif int(status) in (403, 429):
            self.tile_status = "offline"
            self._net_down_until = now + BLOCKED_RETRY_S
            self._failed[key] = now + BLOCKED_RETRY_S
        else:
            self._failed[key] = now + TILE_RETRY_S
            self._stale.discard(key)
        self.update()

    # ---- vector roads (fallback) -----------------------------------------------------
    @staticmethod
    def _road_rank(road):
        return {
            "motorway": 0, "trunk": 1, "primary": 2, "secondary": 3,
            "tertiary": 4, "unclassified": 5, "residential": 6,
            "living_street": 7, "service": 8, "track": 9,
        }.get(str(road.get("hw", "")), 10)

    def _rebuild_roads(self):
        seen, out = set(), []
        for road in [*self.context_roads, *self.roads]:
            try:
                pts = [(float(q[0]), float(q[1])) for q in road.get("pts", []) if len(q) >= 2]
            except (TypeError, ValueError, AttributeError):
                continue
            if len(pts) < 2:
                continue
            key = (road.get("name", ""), round(pts[0][0], 5), round(pts[0][1], 5), len(pts))
            if key in seen:
                continue
            seen.add(key)
            poly = QPolygonF([QPointF(*to_ref(lat, lon)) for lat, lon in pts])
            out.append((self._road_rank(road), poly, str(road.get("name") or "").strip()))
        out.sort(key=lambda r: r[0], reverse=True)       # minor first, major on top
        self._road_polys = out

    def _draw_vector_roads(self, p, t):
        p.setTransform(t)
        p.setBrush(Qt.BrushStyle.NoBrush)
        labels = []
        for rank, poly, name in self._road_polys:
            major = rank <= 4
            colour = QColor(THEME.hex("text_dim"))
            colour.setAlpha(210 if major else 120)
            pen = QPen(colour, 3.0 if major else 1.4, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.drawPolyline(poly)
            if name and major and poly.size() > 2:
                labels.append((name, poly[poly.size() // 2]))
        p.resetTransform()
        p.setFont(THEME.font(9, QFont.Weight.Medium))
        p.setPen(QColor(THEME.hex("text_dim")))
        occupied = []
        for name, point in labels[:120]:
            q = t.map(point)
            rect = QRectF(q.x() - 58, q.y() - 9, 116, 18)
            if not rect.intersects(QRectF(self.rect())) or any(rect.intersects(o) for o in occupied):
                continue
            occupied.append(rect)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, name[:28])
        dot = QColor(THEME.hex("highlight"))
        for place in self.places[:120]:
            try:
                q = t.map(QPointF(*to_ref(float(place["lat"]), float(place["lon"]))))
            except (KeyError, TypeError, ValueError):
                continue
            if not (8 <= q.x() <= self.width() - 8 and 8 <= q.y() <= self.height() - 8):
                continue
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(dot)
            p.drawEllipse(q, 2.6, 2.6)

    # ---- painting --------------------------------------------------------------------
    def paintEvent(self, _event):
        now = time.monotonic()
        cam = self._camera(now)
        self._last_cam = cam
        t = self._transform(cam)
        z = int(max(0, min(MAX_TILE_ZOOM, round(cam.zoom))))
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r = QRectF(self.rect())
        p.fillRect(r, QColor(THEME.hex("bg_alt")))

        self._disk_loads = 0
        tiles = self._visible_tiles(t, z)
        drawn, wanted, bare = [], [], []
        for key, rect in tiles:
            pm = self._tile_pixmap(key)
            if pm is None:
                wanted.append(key)
                parent, src = self._ancestor(key)
                if parent is not None:
                    drawn.append((rect, parent, src))
                else:
                    bare.append(rect)
            else:
                drawn.append((rect, pm, QRectF(0, 0, pm.width(), pm.height())))
                if key in self._stale:
                    wanted.append(key)
        self.vector_fallback_active = bool(bare) or not tiles
        if self.vector_fallback_active:
            self._draw_vector_roads(p, t)
        p.setTransform(t)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        bleed = 0.6 / max(1e-9, 2 ** (cam.zoom - REF_Z))     # hide hairline seams between rotated tiles
        for rect, pm, src in drawn:
            p.drawPixmap(rect.adjusted(-bleed, -bleed, bleed, bleed), pm, src)
        p.resetTransform()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if drawn and not THEME.is_light:
            veil = QColor(THEME.hex("bg"))
            veil.setAlpha(50)                                 # soften bright tiles on dark palettes
            p.fillRect(r, veil)

        self._draw_route(p, t)
        self._draw_vehicle(p, t, cam, now)
        self._draw_overlays(p, cam)
        p.end()
        if self._disk_loads >= DISK_LOADS_PER_FRAME:
            QTimer.singleShot(0, self.update)               # more tiles waiting on disk
        # Fetch only once the zoom has settled, so a zoom animation does not download
        # tiles for the levels it passes through (parents are scaled up meanwhile).
        if abs(cam.zoom - self._zoom_target) < 0.05 and self._tween_from is None:
            self._pump(wanted)

    def _draw_route(self, p, t):
        n = self._route_poly.size()
        if n > 1:
            total = self._route_cum[-1] if self._route_cum else 0.0
            done_len = self.progress * total
            i = 0
            while i < n - 2 and self._route_cum[i + 1] <= done_len:
                i += 1
            a, b = self._route_poly[i], self._route_poly[i + 1]
            seg = self._route_cum[i + 1] - self._route_cum[i]
            k = 0.0 if seg <= 0 else max(0.0, min(1.0, (done_len - self._route_cum[i]) / seg))
            split = QPointF(a.x() + (b.x() - a.x()) * k, a.y() + (b.y() - a.y()) * k)
            done = QPolygonF([self._route_poly[j] for j in range(i + 1)] + [split])
            ahead = QPolygonF([split] + [self._route_poly[j] for j in range(i + 1, n)])
            p.setTransform(t)
            p.setBrush(Qt.BrushStyle.NoBrush)

            def stroke(poly, colour, width):
                pen = QPen(colour, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                pen.setCosmetic(True)
                p.setPen(pen)
                p.drawPolyline(poly)

            casing = QColor(THEME.hex("bg"))
            casing.setAlpha(200)
            stroke(self._route_poly, casing, 10.0)
            dim = QColor(THEME.hex("text_faint"))
            dim.setAlpha(170)
            if self.progress > 0:
                stroke(done, dim, 6.0)                           # travelled part, dimmed
            stroke(ahead, QColor(THEME.hex("accent")), 6.0)
            p.resetTransform()
        if self.destination:
            try:
                q = t.map(QPointF(*to_ref(float(self.destination["lat"]), float(self.destination["lon"]))))
            except (KeyError, TypeError, ValueError):
                return
            p.setBrush(THEME.status("crit"))
            p.setPen(QPen(QColor(THEME.hex("text")), 2))
            p.drawEllipse(q, 8, 8)

    def _draw_vehicle(self, p, t, cam, now):
        pos = self._vehicle_ref(now)
        if pos is None:
            return
        q = t.map(QPointF(*pos))
        live = self.vehicle is not None
        fill = QColor(THEME.hex("accent")) if live else THEME.status("inactive")
        ring = QColor("#FFFFFF")
        halo = QColor(fill)
        halo.setAlpha(55)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo)
        p.drawEllipse(q, 24, 24)
        if self._marker_heading is None:
            p.setBrush(fill)
            p.setPen(QPen(ring, 3))
            p.drawEllipse(q, 9, 9)
            return
        p.save()
        p.translate(q)
        p.rotate(self._marker_heading - cam.bearing)
        arrow = QPainterPath(QPointF(0, -18))
        arrow.lineTo(13, 14)
        arrow.lineTo(0, 7)
        arrow.lineTo(-13, 14)
        arrow.closeSubpath()
        p.setBrush(fill)
        p.setPen(QPen(ring, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(arrow)
        p.restore()

    def compass_rect(self):
        return QRectF(self.width() - 84, 104, 48, 48)

    def _draw_overlays(self, p, cam):
        w, h = self.width(), self.height()
        # compass: the needle points to north on screen
        c = self.compass_rect()
        p.setPen(QPen(QColor(THEME.hex("border")), 1.5))
        p.setBrush(QColor(THEME.hex("card")))
        p.drawEllipse(c)
        p.save()
        p.translate(c.center())
        p.rotate(-cam.bearing)
        north = QPainterPath(QPointF(0, -12))
        north.lineTo(5, 0)
        north.lineTo(-5, 0)
        north.closeSubpath()
        south = QPainterPath(QPointF(0, 12))
        south.lineTo(5, 0)
        south.lineTo(-5, 0)
        south.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(THEME.status("crit"))
        p.drawPath(north)
        p.setBrush(QColor(THEME.hex("text_faint")))
        p.drawPath(south)
        p.restore()
        # "N" upright, just outside the north tip
        a = math.radians(-cam.bearing)
        n_at = c.center() + QPointF(16 * math.sin(a), -16 * math.cos(a))
        p.setPen(QColor(THEME.hex("text")))
        p.setFont(THEME.font(9, QFont.Weight.Bold))
        p.drawText(QRectF(n_at.x() - 7, n_at.y() - 7, 14, 14), Qt.AlignmentFlag.AlignCenter, "N")

        # attribution (required by the OSM licence), left of the zoom buttons
        text = ATTRIBUTION
        if self.vector_fallback_active and self.tile_status == "offline":
            text = "Street tiles offline, showing offline roads · " + ATTRIBUTION
        p.setFont(THEME.font(9))
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text) + 14
        box = QRectF(w - 72 - tw, h - 24, tw, 18)
        bg = QColor(THEME.hex("card"))
        bg.setAlpha(200)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(box, 5, 5)
        p.setPen(QColor(THEME.hex("text_dim")))
        p.drawText(box, Qt.AlignmentFlag.AlignCenter, text)

        ucx, ucy = self._usable_centre()
        pill_y = 126.0
        if self.navigating:
            pill_y = self._draw_navigation(p, w, h) + 36.0
        self._pill_y = pill_y               # where the REPLAY / SIMULATED badge goes (tests read it)
        if self.replay:
            self._pill(p, QPointF(ucx, pill_y), "REPLAY", "Replayed data, not live", THEME.status("warn"), filled=True)
        if self.simulating:
            left_m, left_min = self.sim_remaining()
            if self.sim_arrived:
                title, sub = "ARRIVED (SIMULATED)", "Not live data. Tap End simulation to finish"
            else:
                title = "SIMULATED DRIVE"
                sub = f"Not live data · {left_m / 1000:.1f} km, {max(1, round(left_min))} min left at {SIM_KMH:.0f} km/h"
            self._pill(p, QPointF(ucx, pill_y), title, sub, THEME.status("warn"), filled=True)
        if self.vehicle is None:
            sub = "Showing the last known position" if self.last_fix else "Showing the UCT area"
            self._pill(p, QPointF(ucx, max(150.0, h * 0.42)), "Waiting for GPS fix", sub, THEME.status("warn"))

    @staticmethod
    def _distance_text(m):
        m = max(0.0, m)
        if m >= 1000:
            return f"{m / 1000:.1f} km"
        return f"{int(round(m / 10.0) * 10)} m" if m >= 20 else "now"

    @staticmethod
    def _instruction(man):
        road = man["road"] or "the road"
        return {"straight": f"Continue onto {road}", "left": f"Turn left onto {road}",
                "right": f"Turn right onto {road}", "slight_left": f"Slight left onto {road}",
                "slight_right": f"Slight right onto {road}", "uturn": f"Make a U-turn onto {road}",
                "arrive": "Arrive at destination"}[man["kind"]]

    def _turn_arrow(self, p, r, kind, colour):
        """White manoeuvre arrow inside rect r."""
        pen = QPen(colour, max(3.0, r.width() * 0.11), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        cx, bottom, top = r.center().x(), r.bottom() - r.height() * 0.08, r.top() + r.height() * 0.18
        path = QPainterPath(QPointF(cx, bottom))
        if kind == "arrive":
            p.drawEllipse(QPointF(cx, r.center().y() - r.height() * 0.08), r.width() * 0.22, r.width() * 0.22)
            p.drawLine(QPointF(cx, r.center().y() + r.height() * 0.14), QPointF(cx, bottom))
            return
        if kind == "uturn":
            mid = r.center().y()
            path.lineTo(cx - r.width() * 0.18, mid)
            path.arcTo(QRectF(cx - r.width() * 0.18, top, r.width() * 0.36, r.width() * 0.36), 180, -180)
            path.lineTo(cx + r.width() * 0.18, mid + r.height() * 0.12)
            tip, ang = QPointF(cx + r.width() * 0.18, mid + r.height() * 0.12), 90.0
        else:
            bend = r.center().y() + r.height() * 0.05
            path.lineTo(cx, bend)
            dx = {"straight": 0.0, "left": -1.0, "right": 1.0, "slight_left": -0.6, "slight_right": 0.6}[kind]
            if dx == 0:
                tip, ang = QPointF(cx, top), -90.0
            else:
                tip = QPointF(cx + dx * r.width() * 0.34, top if abs(dx) < 1 else bend - r.height() * 0.05)
                ang = math.degrees(math.atan2(tip.y() - bend, tip.x() - cx))
            path.lineTo(tip)
        p.drawPath(path)
        head = r.width() * 0.2
        a = math.radians(ang)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(colour)
        p.drawPolygon(QPolygonF([QPointF(tip.x() + math.cos(a) * head * 0.6, tip.y() + math.sin(a) * head * 0.6),
                                 QPointF(tip.x() + math.cos(a + 2.4) * head, tip.y() + math.sin(a + 2.4) * head),
                                 QPointF(tip.x() + math.cos(a - 2.4) * head, tip.y() + math.sin(a - 2.4) * head)]))

    def _draw_navigation(self, p, w, h):
        """Turn banner at the top of the usable area and an ETA card at the bottom. Returns the banner's bottom y."""
        left, right, top, bottom = self._insets()
        ahead = self.next_maneuvers(2)
        if not ahead:
            return top
        man, dist = ahead[0]
        bw = min(560.0, w - left - right - 20)
        bx = left + (w - left - right - bw) / 2
        by = top + 40
        bh = 104.0
        green, white = QColor("#17703E"), QColor("#FFFFFF")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(green)
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 14, 14)
        self._turn_arrow(p, QRectF(bx + 16, by + 14, 76, 76), man["kind"], white)
        p.setPen(white)
        p.setFont(THEME.font(30, QFont.Weight.Bold))
        p.drawText(QRectF(bx + 108, by + 10, bw - 120, 44), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   "" if man["kind"] == "arrive" else self._distance_text(dist))
        p.setFont(THEME.font(19, QFont.Weight.DemiBold))
        p.drawText(QRectF(bx + 108, by + 54, bw - 120, 40), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   p.fontMetrics().elidedText(self._instruction(man), Qt.TextElideMode.ElideRight, int(bw - 124)))
        end = by + bh
        if len(ahead) > 1:
            then = QRectF(bx + 14, end - 4, min(bw - 28, 360.0), 40)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#0F4F2B"))
            p.drawRoundedRect(then, 10, 10)
            p.setPen(white)
            p.setFont(THEME.font(15, QFont.Weight.DemiBold))
            p.drawText(then.adjusted(14, 4, -10, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       p.fontMetrics().elidedText("Then: " + (lambda t: t[:1].lower() + t[1:])(self._instruction(ahead[1][0])),
                                                  Qt.TextElideMode.ElideRight, int(then.width() - 26)))
            end = then.bottom()
        # ETA card: time left, distance left, arrival time
        left_m = max(0.0, self._route_total_m - (self._along_m or 0.0))
        if self.simulating:
            eta_s = left_m / (SIM_KMH / 3.6)
        elif self._plan_duration_s > 0 and self._route_total_m > 0:
            eta_s = self._plan_duration_s * left_m / self._route_total_m
        else:
            eta_s = None
        if eta_s is not None:
            arrive = time.strftime("%H:%M", time.localtime(time.time() + eta_s))
            minutes = max(1, int(round(eta_s / 60.0)))
            cw, ch = 300.0, 58.0
            ex = min(max(600.0, (w - cw) / 2), w - 320.0 - cw)
            ey = h - 70.0 - ch
            card = QRectF(ex, ey, cw, ch)
            bg = QColor(THEME.hex("card"))
            bg.setAlpha(235)
            p.setPen(QPen(QColor(THEME.hex("border")), 1))
            p.setBrush(bg)
            p.drawRoundedRect(card, 14, 14)
            p.setPen(QColor("#2E9E5B"))
            p.setFont(THEME.font(24, QFont.Weight.Bold))
            p.drawText(card.adjusted(16, 0, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{minutes} min")
            p.setPen(QColor(THEME.hex("text")))
            p.setFont(THEME.font(16, QFont.Weight.DemiBold))
            p.drawText(card.adjusted(0, 0, -16, 0), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       f"{self._distance_text(left_m) if left_m >= 20 else '0 m'}  \u00b7  {arrive}")
        return end

    def _pill(self, p, centre, title, sub, colour, filled=False):
        p.setFont(THEME.font(17, QFont.Weight.Bold))
        tw = p.fontMetrics().horizontalAdvance(title)
        p.setFont(THEME.font(10))
        sw = p.fontMetrics().horizontalAdvance(sub)
        bw, bh = max(tw, sw) + 44, 58
        box = QRectF(centre.x() - bw / 2, centre.y() - bh / 2, bw, bh)
        bg = QColor(colour) if filled else QColor(THEME.hex("card"))
        bg.setAlpha(240)
        p.setBrush(bg)
        p.setPen(QPen(colour, 2))
        p.drawRoundedRect(box, 14, 14)
        fg = QColor("#101418") if filled else QColor(THEME.hex("text"))
        p.setPen(fg if filled else colour)
        p.setFont(THEME.font(17, QFont.Weight.Bold))
        p.drawText(QRectF(box.left(), box.top() + 6, bw, 26), Qt.AlignmentFlag.AlignCenter, title)
        p.setPen(fg)
        p.setFont(THEME.font(10))
        p.drawText(QRectF(box.left(), box.top() + 32, bw, 18), Qt.AlignmentFlag.AlignCenter, sub)

    # ---- interaction -----------------------------------------------------------------
    def resizeEvent(self, event):
        self.zoom_in.setGeometry(max(0, self.width() - 62), max(0, self.height() - 94), 44, 38)
        self.zoom_out.setGeometry(max(0, self.width() - 62), max(0, self.height() - 52), 44, 38)
        self.sim_button.setGeometry(max(0, self.width() - 290), max(0, self.height() - 100), 210, 44)
        if self._mode == "overview":
            self._overview = self._fit_camera()
            self._zoom_target = self._zoom_now = self._overview.zoom
        super().resizeEvent(event)

    def _apply_theme(self, *_):
        style = (f"font-size:24px;background:{THEME.hex('card')};color:{THEME.hex('text')};"
                 f"border:1px solid {THEME.hex('border')};border-radius:6px;")
        for button in (self.zoom_in, self.zoom_out):
            button.setStyleSheet(style)
        self.sim_button.setStyleSheet(
            f"font-size:16px;font-weight:700;background:{THEME.hex('card')};color:{THEME.hex('text')};"
            f"border:2px solid {THEME.status('warn').name()};border-radius:8px;")
        self.update()

    def wheelEvent(self, event):
        self._zoom(.8 if event.angleDelta().y() > 0 else 1.25)
        event.accept()

    def _drag_to(self, pos):
        if self._press is None:
            return
        if not self._dragging:
            if (pos - self._press).manhattanLength() < 8:
                return
            self._dragging = True
            if self._mode != "explore":
                self._freeze()
            self._drag_last = self._press
        cam = self._explore
        inv, ok = self._transform(cam).inverted()
        if ok:
            a, b = inv.map(self._drag_last), inv.map(pos)
            cam.x -= b.x() - a.x()
            cam.y -= b.y() - a.y()
        self._drag_last = pos
        self._kick()

    def _release(self, pos):
        if not self._dragging and self._press is not None and self.compass_rect().contains(pos):
            if self._mode == "explore" and self._explore is not None:
                self._explore.bearing = 0.0           # tap the compass: north up
                self._kick()
        self._press = None
        self._dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.position()
            self._dragging = False
            event.accept()

    def mouseMoveEvent(self, event):
        self._drag_to(event.position())

    def mouseReleaseEvent(self, event):
        self._release(event.position())

    def event(self, event):
        kind = event.type()
        if kind in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd,
                    QEvent.Type.TouchCancel):
            points = event.points()
            if kind == QEvent.Type.TouchBegin and points:
                start = points[0].position().toPoint()
                if any(b.isVisible() and b.geometry().contains(start) for b in (self.zoom_in, self.zoom_out)):
                    event.ignore()                    # let the buttons get their synthesized clicks
                    return False
            if kind in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
                if points:
                    self._release(points[0].position())
                self._pinch = None
                event.accept()
                return True
            if len(points) >= 2:
                a, b = points[0].position(), points[1].position()
                d = max(1.0, math.hypot(a.x() - b.x(), a.y() - b.y()))
                if self._pinch is None:
                    self._pinch = (d, self._zoom_target)
                    self._press = None
                    self._dragging = False
                else:
                    d0, z0 = self._pinch
                    if self._mode == "overview":
                        self._freeze()
                    self._zoom_target = self._zoom_now = max(MIN_ZOOM, min(MAX_ZOOM, z0 + math.log2(d / d0)))
                    self._kick()
            elif points and self._pinch is None:
                pos = points[0].position()
                if kind == QEvent.Type.TouchBegin:
                    self._press = pos
                    self._dragging = False
                else:
                    self._drag_to(pos)
            event.accept()
            return True
        return super().event(event)
