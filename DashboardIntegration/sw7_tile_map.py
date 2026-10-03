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

Drop this file into app/pages/ (tests/dashboard_patches.py does, and swaps
the import in navigation_page.py; TUKZIE_TILE_MAP=0 restores NativeRouteMap).
QtWidgets, QtGui and QtNetwork only; colours from THEME.
"""
from __future__ import annotations

import math
import os
import time
from collections import OrderedDict

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


def _num(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


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
        if plan and reset_view:
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
        try:
            self.progress = max(0.0, min(1.0, float(value or 0.0)))
        except (TypeError, ValueError):
            self.progress = 0.0
        self.update()

    def update_vehicle(self, state):
        now = time.monotonic()
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
        self.vehicle = self.last_fix = (lat, lon)
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
        self._kick()

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
        if self.replay:
            self._pill(p, QPointF(ucx, 126), "REPLAY", "Replayed data, not live", THEME.status("warn"), filled=True)
        if self.vehicle is None:
            sub = "Showing the last known position" if self.last_fix else "Showing the UCT area"
            self._pill(p, QPointF(ucx, max(150.0, h * 0.42)), "Waiting for GPS fix", sub, THEME.status("warn"))

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
        if self._mode == "overview":
            self._overview = self._fit_camera()
            self._zoom_target = self._zoom_now = self._overview.zoom
        super().resizeEvent(event)

    def _apply_theme(self, *_):
        style = (f"font-size:24px;background:{THEME.hex('card')};color:{THEME.hex('text')};"
                 f"border:1px solid {THEME.hex('border')};border-radius:6px;")
        for button in (self.zoom_in, self.zoom_out):
            button.setStyleSheet(style)
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
