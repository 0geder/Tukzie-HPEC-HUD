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

Tilted 3D view (Planning/map-tilt-prompt.md), off unless TUKZIE_MAP_TILT=1: in follow mode the map is seen by
a camera pitched TILT_DEG from straight down, as Google Maps does on CarPlay, so the road ahead recedes toward the
horizon and the arrow sits at 72 % of the height. The flat transform is followed by the pinhole homography of that
camera (a projective QTransform), so tiles, route and markers share one matrix and line up; drags map back through
its inverse. Ground beyond TILT_FAR_PX ahead is not drawn: a band in the theme's background colour fades in where the
horizon would be. With the flag, a "3D" button above the zoom buttons switches between tilted and flat. Overview is
always flat.

Layout pass (Planning/layout-improvements-prompt.md, agent D; on unless TUKZIE_SW7_LAYOUT=0, which gives back the
earlier look exactly): every map control sits in one column of 64 x 64 buttons on the right edge, 24 px in, 12 px
apart: compass, Follow, Overview, 3D (with TUKZIE_MAP_TILT=1), +, -. Simulate drive / End simulation is a 200 x 64
button at the bottom right, above the attribution. The turn banner is anchored top left (520 x 128, distance 48 px,
street 24 px, a 40 px "Then:" strip at 18 px). The SIMULATED DRIVE label no longer floats over the road: it is a
yellow chip at the left end of the arrival-time bar (bottom centre, 560 x 72: time 36 px, distance and arrival 24 px).
The altitude is a small chip left of the compass, only when known. layout_page() places the Navigation page's own
overlays around these (search field right of the banner, team Follow/Overview hidden, status line bottom left at
18 px); navigation_page.py calls it at the end of _position_overlays (dashboard_patches.LAYOUT_MAP_PATCHES).

Paper and depth style (Planning/paper-depth-theme-prompt.md, page agent P3; only when sw7_style is installed, so
TUKZIE_SW7_STYLE=team and the map on its own look exactly as before): the map is the middle plane, a raised slab
(slab_rect) with rounded corners, a warm edge and a long shadow, all in one cached pixmap with four corner patches
(no live effect: the map repaints every frame). Tiles are tinted once each and cached (tint_tile: warm by day, a
dark warm map at night). The route, the vehicle and the destination are ink (information); only the controls are
signal, and the column, search field, Simulate drive and arrival-time bar overlap the slab's edges by 20 to 24 px on
cached shadows. The turn banner is the charcoal card with the distance as the page's hero (120 px). The arrival-time
bar is the page's one remaining-distance and ETA figure, with the plan's arrival battery; there is no ALT chip.

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

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (QColor, QEventPoint, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF, QTransform)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QAbstractButton, QPushButton, QWidget

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
TILT_DEG = 50.0                      # camera pitch in the 3D view (0 = straight down)
TILT_SCALE = 1.2                     # zoom at the vehicle when tilted, so the near road keeps its size
TILT_FOLLOW_Y = 0.72                 # vehicle low in the view when tilted, clear of the ETA card
TILT_HORIZON_Y = 0.08                # where the horizon would sit at full tilt (fraction of the height)
TILT_FAR_PX = 1400.0                 # ground drawn this far ahead (flat screen pixels); beyond it, the sky band
TILT_FADE_PX = 60.0                  # height of the fade from the sky band into the map
TILT_EASE_S = 0.18                   # time constant of the tilt animation (about 0.5 s to settle)
# layout pass (TUKZIE_SW7_LAYOUT, default on)
EDGE = 24                            # outer margin of every overlay
CTRL = 64                            # map control buttons, square
CTRL_GAP = 12
SIM_W = 200                          # Simulate drive / End simulation button, 200 x 64
BANNER_W, BANNER_H, THEN_H = 520, 128, 40
ETA_W, ETA_H = 560, 72
PX = {"distance": 48, "street": 24, "then": 18, "eta_time": 36, "eta_text": 24, "chip": 16, "altitude": 16,
      "label": 14, "status": 18}
TURN_GREEN, THEN_GREEN, ETA_GREEN = "#17703E", "#0F4F2B", "#2E9E5B"


def layout_enabled():
    """TUKZIE_SW7_LAYOUT: the layout pass is on unless it is "0"."""
    return os.environ.get("TUKZIE_SW7_LAYOUT", "1").strip() != "0"


def paper_style():
    """The sw7_style module when the paper and depth style is installed in this dashboard, else None (team look,
    or the map on its own as in test_tile_map). Planning/paper-depth-theme-prompt.md, page agent P3."""
    try:
        from ..widgets import sw7_style as style
    except ImportError:
        return None
    return style if style.enabled() and getattr(style, "_installed", False) else None


# Paper and depth style: the map is a raised slab (middle plane) with the controls floating over its edges.
SLAB_L, SLAB_T = 40, 64              # slab left and top; the cards at EDGE overhang it by 16 and 24 px
SLAB_OVER = 20                       # the control column and the bottom cards overlap the slab by this much
SLAB_R = 28                          # corner radius
SLAB_EDGE = 10                       # the slab's thickness, a warm edge under its face
PAPER_BOTTOM = 32                    # bottom cards end this far above the page bottom (16 px run under the nav pill)
PAPER_BANNER_H = 184                 # turn banner: the distance as the page's hero (120 px), the street at 22 px
TINTS_PER_FRAME = 6                  # tiles tinted per paint at most (the rest next frame)
DAY_TINT = "#F4E8DC"                 # multiplied into the tiles by day: OSM ground becomes paper_deep, roads paper
# night: tile luminance -> colour (labels light, land near the card colour, roads lighter than the land)
NIGHT_LUT = ((0, "#D2C8BF"), (110, "#8F857C"), (170, "#4A433D"), (205, "#38322D"), (232, "#2A2622"),
             (243, "#26221F"), (250, "#3E3832"), (255, "#6A615A"))


def _night_table():
    from PySide6.QtGui import qRgb
    out = []
    for v in range(256):
        for (a, ca), (b, cb) in zip(NIGHT_LUT, NIGHT_LUT[1:]):
            if a <= v <= b:
                k = 0.0 if b == a else (v - a) / (b - a)
                x, y = QColor(ca), QColor(cb)
                out.append(qRgb(round(x.red() + (y.red() - x.red()) * k), round(x.green() + (y.green() - x.green()) * k),
                                round(x.blue() + (y.blue() - x.blue()) * k)))
                break
    return out


_NIGHT_TABLE = None


def tint_tile(pixmap, night):
    """A street tile tinted to sit on paper: by day a little desaturated and multiplied with a warm paper tone; at
    night mapped through NIGHT_LUT by luminance (a dark warm map, labels light) and multiplied with the original
    so water and parks keep a trace of their colour. Done once per tile (cached by the map)."""
    global _NIGHT_TABLE
    from PySide6.QtGui import QImage
    img = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB32)
    gray = img.convertToFormat(QImage.Format.Format_Grayscale8)
    if not night:
        p = QPainter(img)
        p.setOpacity(0.35)
        p.drawImage(0, 0, gray)
        p.setOpacity(1.0)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
        p.fillRect(img.rect(), QColor(DAY_TINT))
        p.end()
        return QPixmap.fromImage(img)
    if _NIGHT_TABLE is None:
        _NIGHT_TABLE = _night_table()
    data = bytes(gray.constBits())
    ind = QImage(data, gray.width(), gray.height(), gray.bytesPerLine(), QImage.Format.Format_Indexed8)
    ind.setColorTable(_NIGHT_TABLE)
    base = ind.convertToFormat(QImage.Format.Format_RGB32)
    p = QPainter(base)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
    p.setOpacity(0.55)
    p.drawImage(0, 0, img)
    p.end()
    return QPixmap.fromImage(base)


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


class _MapButton(QPushButton):
    """A map control. Without a glyph it is a plain QPushButton (the look before the layout pass); with one it
    paints itself as a 64 x 64 card button with an icon and, for Follow and Overview, a label under it."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.glyph = None                 # None, or "plus" / "minus" / "follow" / "overview" / "3d"
        self.label = ""
        self.active = False               # selected look (Follow while following, Overview in the overview)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_glyph(self, glyph, label=""):
        self.glyph, self.label = glyph, label
        self.setStyleSheet("")
        self.update()

    def set_active(self, value):
        if self.active != bool(value):
            self.active = bool(value)
            self.update()

    def label_px(self):
        """Label size: 14 px, or smaller (never under 12) if the word would not fit the button. Paper: 13 px."""
        if paper_style() is not None:
            return 13
        for px in (PX["label"], 13, 12):
            if QFontMetricsF(THEME.font(px, QFont.Weight.DemiBold)).horizontalAdvance(self.label) <= self.width() - 6:
                return px
        return 12

    def paintEvent(self, event):
        if self.glyph is None:
            return super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        on = self.active or (self.isCheckable() and self.isChecked())
        S = paper_style()
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if S is not None:                 # paper: a signal outline card, filled signal while selected
            # (its shadow is painted by the map under it, cached: the map repaints every frame)
            p.setBrush(S.c("signal") if on else S.c("signal_tint" if self.isDown() else "card"))
            p.setPen(QPen(S.c("signal"), 2.0))
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 20, 20)
            ink = S.c("card") if on else S.c("signal")
        else:
            accent, text = QColor(THEME.hex("accent")), QColor(THEME.hex("text"))
            bg = QColor(THEME.hex("card_alt" if self.isDown() else "card"))
            bg.setAlpha(240)
            p.setBrush(bg)
            p.setPen(QPen(accent if on else QColor(THEME.hex("border")), 2.0 if on else 1.0))
            p.drawRoundedRect(r, 12, 12)
            ink = accent if on else text
        c = r.center()
        icon_c = QPointF(c.x(), c.y() - 9) if self.label else c
        pen = QPen(ink, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        if self.glyph in ("plus", "minus"):
            p.setPen(pen)
            p.drawLine(QPointF(c.x() - 13, c.y()), QPointF(c.x() + 13, c.y()))
            if self.glyph == "plus":
                p.drawLine(QPointF(c.x(), c.y() - 13), QPointF(c.x(), c.y() + 13))
        elif self.glyph == "3d":
            p.setPen(ink)
            p.setFont(THEME.font(22, QFont.Weight.Bold))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, "3D")
        elif self.glyph == "follow":            # the navigation arrow, as on the map
            arrow = QPainterPath(QPointF(icon_c.x(), icon_c.y() - 13))
            arrow.lineTo(icon_c.x() + 10, icon_c.y() + 11)
            arrow.lineTo(icon_c.x(), icon_c.y() + 5)
            arrow.lineTo(icon_c.x() - 10, icon_c.y() + 11)
            arrow.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ink)
            p.drawPath(arrow)
        elif self.glyph == "overview":          # a route between two corners of a frame
            p.setPen(QPen(ink, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            x0, y0, s = icon_c.x() - 13, icon_c.y() - 12, 26.0
            for (ax, ay), (dx, dy) in (((x0, y0), (1, 1)), ((x0 + s, y0), (-1, 1)),
                                       ((x0, y0 + s - 2), (1, -1)), ((x0 + s, y0 + s - 2), (-1, -1))):
                p.drawLine(QPointF(ax, ay), QPointF(ax + 7 * dx, ay))
                p.drawLine(QPointF(ax, ay), QPointF(ax, ay + 7 * dy))
            route = QPainterPath(QPointF(x0 + 6, y0 + s - 7))
            route.cubicTo(QPointF(x0 + 14, y0 + s - 6), QPointF(x0 + 10, y0 + 6), QPointF(x0 + s - 6, y0 + 6))
            p.drawPath(route)
        if self.label:
            p.setPen(ink)
            p.setFont(THEME.font(self.label_px(), QFont.Weight.DemiBold))
            p.drawText(QRectF(r.left(), r.bottom() - 24, r.width(), 20), Qt.AlignmentFlag.AlignCenter, self.label)
        p.end()


class SW7TileMap(QWidget):
    """Street-tile map, drop-in for NativeRouteMap (see the module docstring)."""

    follow_changed = Signal(bool)     # auto_follow changed (drag, Follow, Overview)
    sim_tick = Signal()               # each simulated-drive step, and when it ends (sw7_sim_link.py)
    overlays_changed = Signal()       # the turn banner appeared or went (layout_page moves the search field)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sw7_layout = layout_enabled()   # read once: the layout pass (TUKZIE_SW7_LAYOUT=0 is the earlier look)
        self.overlay_rects = {}           # where the last paint put the banner, ETA bar, chips (tests, layout_page)
        self.overlay_px = {}              # text sizes used in the last paint, in px (tests)
        self.drawn_pills = []             # titles of the pills drawn in the last paint (tests)
        self.altitude_m = None            # from the live state, for the altitude chip (layout pass)
        self.follow_handler = None        # set by layout_page: the page's own set_follow_mode / show_overview
        self.overview_handler = None
        self._banner_shown = (False, False)   # (turn banner, altitude chip) last told to the page
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
        self.approx = None                # (lat, lon, accuracy m) from the mobile network, no GNSS fix
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
        # 3D tilt (off unless TUKZIE_MAP_TILT=1)
        self.tilt_available = os.environ.get("TUKZIE_MAP_TILT", "0").strip() == "1"
        self.tilt_enabled = self.tilt_available
        self._tilt_now = 0.0              # 0 flat .. 1 fully tilted, eased toward _tilt_target()
        self._explore_tilt = 0.0          # tilt kept while exploring (a drag from the tilted view stays tilted)
        self.paint_ms = None              # duration of the last paintEvent (tests, Diagnostics)
        self._ground_y = 0.0              # screen y where the drawn ground starts (sky band above it when tilted)
        # paper and depth style (None in the team look): the slab, tinted tiles, cached frame and shadows
        self._S = paper_style() if self.sw7_layout else None
        self._tint_mem = OrderedDict()    # (z, x, y, night) -> tinted pixmap
        self._tints_left = TINTS_PER_FRAME
        self.tint_ms = []                 # time to tint each tile, ms (tests)
        self._frame_key = None
        self._frame = None                # (pixmap of paper, slab shadow, edge and face; [(QPointF, corner pixmap)])
        self.floating = []                # the page's widgets over the map, given a cached shadow (layout_page)
        self.arrival_soc = None           # the plan's arrival state of charge, shown in the arrival-time bar

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
        self._multi = False               # a three-finger page swipe is in progress (sw7_page_swipe)
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
        self.zoom_in = _MapButton("+", self)
        self.zoom_out = _MapButton("−", self)
        self.zoom_in.clicked.connect(lambda: self._zoom(.7))
        self.zoom_out.clicked.connect(lambda: self._zoom(1.4))
        self.sim_button = QPushButton("Simulate drive", self)
        self.sim_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sim_button.clicked.connect(self.toggle_simulation)
        self.sim_button.hide()
        self.tilt_button = _MapButton("3D", self)
        self.tilt_button.setCheckable(True)
        self.tilt_button.setChecked(self.tilt_enabled)
        self.tilt_button.toggled.connect(self.set_tilt)
        self.tilt_button.setVisible(self.tilt_available)
        # Follow and Overview in the map's own control column (layout pass); the page's buttons are hidden then
        self.follow_button = _MapButton("Follow", self)
        self.follow_button.clicked.connect(self._follow_clicked)
        self.overview_button = _MapButton("Overview", self)
        self.overview_button.clicked.connect(self._overview_clicked)
        if self.sw7_layout:
            self.zoom_in.set_glyph("plus")
            self.zoom_out.set_glyph("minus")
            self.tilt_button.set_glyph("3d")
            self.follow_button.set_glyph("follow", "Follow")
            self.overview_button.set_glyph("overview", "Overview")
        else:
            self.follow_button.hide()
            self.overview_button.hide()
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
        self.arrival_soc = _num(getattr(plan, "arrival_soc_pct", None)) if plan else None
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
        self._check_overlays()
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
        # The dashboard's simulated state (sw7_sim_link) carries this map's own simulated position back to it on
        # every dispatch. Taking it would count each echo as a new fix and shorten the glide between steps to the
        # live polling rate, so the marker moved in jerks (seen 11 Oct). The map is the source: ignore the echo.
        if getattr(state, "sw7_from_dashboard", False):
            return
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
        cell = None if simulated else getattr(state, "sw7_cell_position", None)
        self.approx = (cell if cell and _num(cell[0]) is not None and _num(cell[1]) is not None
                       and (lat is None or lon is None) else None)
        if not simulated:
            self.altitude_m = _num(getattr(state, "altitude_m", None)) if lat is not None and lon is not None else None
        if lat is None or lon is None:
            self.vehicle = None
            self._check_overlays()
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
        self._check_overlays()
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
        self._check_overlays()
        self._kick()
        self.sim_tick.emit()

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
        self.sim_tick.emit()

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

    def set_tilt(self, enabled):
        """3D button: tilted (CarPlay-style) or flat view. Only does anything with TUKZIE_MAP_TILT=1."""
        enabled = bool(enabled) and self.tilt_available
        if enabled != self.tilt_enabled:
            self.tilt_enabled = enabled
            if self._mode == "explore":
                self._explore_tilt = 1.0 if enabled else 0.0
        if self.tilt_button.isChecked() != enabled:
            self.tilt_button.setChecked(enabled)
        self._kick()

    @property
    def tilt(self):
        """Current tilt, 0 flat to 1 fully tilted (eases after a change)."""
        return self._tilt_now

    def _tilt_target(self):
        if not self.tilt_enabled:
            return 0.0
        if self._mode == "follow":
            return 1.0
        if self._mode == "explore":
            return self._explore_tilt
        return 0.0                        # overview: flat, north-up

    def _follow_clicked(self):
        (self.follow_handler or (lambda: self.set_follow_mode(True)))()

    def _overview_clicked(self):
        (self.overview_handler or self.show_overview)()

    def _sync_buttons(self):
        self.follow_button.set_active(self._mode == "follow")
        self.overview_button.set_active(self._mode == "overview")

    def _check_overlays(self):
        """Tell the page when the turn banner comes or goes, so it can move the search field (layout pass)."""
        shown = (self.sw7_layout and self.navigating and bool(self.next_maneuvers(1)),
                 self.altitude_chip_rect() is not None)
        if shown != self._banner_shown:
            self._banner_shown = shown
            self.overlays_changed.emit()

    # ---- layout pass: where things go ---------------------------------------------------
    def control_slots(self):
        """The right-hand column, top to bottom: {name: QRect} in widget coordinates (layout pass only)."""
        x = self.width() - EDGE - CTRL
        names = ["compass", "follow", "overview"] + (["tilt"] if self.tilt_available else []) + ["zoom_in", "zoom_out"]
        return {name: QRect(x, EDGE + i * (CTRL + CTRL_GAP), CTRL, CTRL) for i, name in enumerate(names)}

    def sim_button_rect(self):
        if self._S is not None:           # paper: on the slab's bottom right corner, beside the arrival-time bar
            return QRect(self.width() - EDGE - SIM_W, self.height() - PAPER_BOTTOM - CTRL, SIM_W, CTRL)
        return QRect(self.width() - EDGE - SIM_W, self.height() - EDGE - 14 - CTRL, SIM_W, CTRL)

    def slab_rect(self):
        """Paper style: the map's face, a raised slab inside the page. The search field, the turn banner, the
        control column and the bottom cards overlap its edges (the depth of the three planes)."""
        w, h = self.width(), self.height()
        right = w - EDGE - CTRL + SLAB_OVER
        bottom = h - PAPER_BOTTOM - ETA_H + SLAB_OVER
        return QRectF(SLAB_L, SLAB_T, max(10, right - SLAB_L), max(10, bottom - SLAB_T))

    def turn_banner_rect(self):
        """Where the turn banner is (with its Then strip), or None when no banner shows (layout pass only)."""
        if not self.sw7_layout or not self.navigating:
            return None
        ahead = self.next_maneuvers(2)
        if not ahead:
            return None
        bw = min(float(BANNER_W), self.width() - 2 * EDGE - CTRL - 2 * CTRL_GAP)
        bh = PAPER_BANNER_H if self._S is not None else BANNER_H
        return QRectF(EDGE, EDGE, bw, bh + (THEN_H if len(ahead) > 1 else 0))

    def _altitude_text(self):
        return f"ALT {self.altitude_m:.0f} m"

    def altitude_chip_rect(self):
        if not self.sw7_layout or self.altitude_m is None or self._S is not None:
            return None                   # paper: no ALT chip (the altitude's home is Diagnostics, merge plan A)
        aw = QFontMetricsF(THEME.font(PX["altitude"], QFont.Weight.DemiBold)).horizontalAdvance(self._altitude_text()) + 24
        slot = self.control_slots()["compass"]
        return QRectF(slot.left() - CTRL_GAP - aw, slot.center().y() - 15, aw, 32)

    def eta_rect(self):
        w, h = self.width(), self.height()
        cw = min(float(ETA_W), w - 2 * (EDGE + SIM_W + CTRL_GAP))
        return QRectF((w - cw) / 2, h - (PAPER_BOTTOM if self._S is not None else EDGE) - ETA_H, cw, ETA_H)

    def layout_page(self, page):
        """Place the Navigation page's own overlays around the map's (layout pass). Called by the page at the end
        of _position_overlays (dashboard_patches.LAYOUT_MAP_PATCHES); does nothing with TUKZIE_SW7_LAYOUT=0."""
        if not self.sw7_layout:
            return
        stage = getattr(page, "stage", None)
        if stage is None or not hasattr(page, "search"):
            return
        if not getattr(page, "_sw7_layout_hooked", False):
            page._sw7_layout_hooked = True
            self.overlays_changed.connect(page._position_overlays)
            self.follow_handler = lambda: page.set_follow_mode(True)
            self.overview_handler = page.show_overview
            page.plan_btn.setMinimumSize(120, 48)
            page.destination.setMinimumHeight(48)
            page.route_status.setStyleSheet(f"font-size: {16 if self._S is not None else PX['status']}px;")
            self.floating = [page.search, page.route_status, page.retry_btn]   # cached shadows (paper)
        off = self.mapTo(stage, QPoint(0, 0))
        w, h = stage.width(), stage.height()
        col_left = off.x() + self.width() - EDGE - CTRL
        # Follow and Overview live in the map's column; the page's small buttons and the altitude card go
        for widget in (page.follow_btn, page.overview_btn, page.altitude):
            widget.hide()
        # search field: top centre, or right of the turn banner while one shows; never over the column
        banner = self.turn_banner_rect()
        top = off.y() + EDGE
        limit = col_left - 2 * CTRL_GAP                  # right end of the search field
        chip = self.altitude_chip_rect()
        if chip is not None:
            limit = min(limit, off.x() + int(chip.left()) - CTRL_GAP)
        if banner is not None:
            left = off.x() + int(banner.right()) + 2 * CTRL_GAP
            width = limit - left
        else:
            width = min(760, limit - (off.x() + EDGE))
            left = max(off.x() + EDGE, min(off.x() + (self.width() - width) // 2, limit - width))
        page.search.setGeometry(left, top, max(240, width), 64)
        # status line bottom left, beside the arrival-time bar when one shows
        eta = self.eta_rect() if self.navigating else None
        right = off.x() + int(eta.left()) - CTRL_GAP if eta is not None else off.x() + self.width() - EDGE - SIM_W - CTRL_GAP
        sw = max(200, min(560, right - (off.x() + EDGE)))
        sh = max(48, min(76, page.route_status.heightForWidth(sw) if page.route_status.wordWrap() else 48))
        bottom = off.y() + self.height() - (PAPER_BOTTOM if self._S is not None else EDGE)
        page.route_status.setGeometry(off.x() + EDGE, bottom - sh, sw, sh)
        page.retry_btn.setGeometry(off.x() + EDGE, bottom - sh - CTRL_GAP - CTRL, 160, CTRL)
        lst = getattr(page, "suggestions", None)
        if lst is not None and lst.isVisible():
            search = getattr(page, "_sw7_search", None)
            if search is not None:
                lst.setGeometry(search.list_geometry())
            else:
                p = page.destination.mapTo(stage, page.destination.rect().bottomLeft())
                lst.setGeometry(p.x(), p.y() + 4, page.destination.width(), min(160, 32 * max(1, lst.count())))
        for widget in (page.search, page.route_status, page.retry_btn, lst):
            if widget is not None:
                widget.raise_()

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

    def map_point(self, pos):
        """(lat, lon) under the screen point pos, through the inverse of the current (possibly tilted) transform.
        Points above the visible ground (the sky band) are taken at its top edge."""
        cam = self._camera(time.monotonic())
        inv, ok = self._transform(cam).inverted()
        if not ok:
            return None
        q = inv.map(self._on_ground(QPointF(pos)))
        return from_ref(q.x(), q.y())

    def vehicle_screen_point(self):
        pos = self._vehicle_ref(time.monotonic())
        return None if pos is None else self._transform(self._camera(time.monotonic())).map(QPointF(*pos))

    def tile_path(self, z, x, y):
        return os.path.join(self.cache_dir, str(z), str(x), f"{y}.png")

    # ---- animation -------------------------------------------------------------------
    def _set_auto_follow(self, value):
        self._sync_buttons()
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
        dt_tilt = self._tilt_target() - self._tilt_now
        if abs(dt_tilt) > 0.002:
            self._tilt_now += dt_tilt * (1 - math.exp(-dt / TILT_EASE_S))
            busy = True
        else:
            self._tilt_now = self._tilt_target()
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
        """Screen margins kept clear of the navigation page's overlays. The left margin made room for the
        team's Route Guidance panel; that panel is hidden by default since 11 Oct (our turn banner replaces it),
        so the map then uses the full width."""
        w = self.width()
        guidance = os.environ.get("TUKZIE_ROUTE_GUIDANCE", "0").strip() == "1"
        left = max(26.0, min(390.0, w * .28)) if guidance else 26.0
        if self._S is not None:           # paper: inside the slab, clear of the cards on its edges
            return (max(left, SLAB_L + 16.0), float(EDGE + CTRL - SLAB_OVER + 16), float(EDGE + 64 + CTRL_GAP),
                    float(PAPER_BOTTOM + ETA_H + CTRL_GAP))
        if self.sw7_layout:               # control column on the right, search on top, arrival-time bar at the bottom
            return left, float(EDGE + CTRL + CTRL_GAP + 4), float(EDGE + 64 + CTRL_GAP), float(EDGE + ETA_H + CTRL_GAP)
        return left, 130.0, 90.0, 65.0   # left, right, top, bottom

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
            centre = (self.approx[0], self.approx[1]) if self.approx else self.context_centre
            pos = to_ref(*centre)
            return _Cam(pos[0], pos[1], self._zoom_now, self._bearing_now, ucx, ucy)
        follow_y = FOLLOW_Y + (TILT_FOLLOW_Y - FOLLOW_Y) * self._tilt_now
        return _Cam(pos[0], pos[1], self._zoom_now, self._bearing_now, ucx, max(1, self.height()) * follow_y)

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
        self._explore_tilt = self._tilt_now
        self._mode = "explore"
        self._set_auto_follow(False)

    def _transform(self, cam):
        s = 2 ** (cam.zoom - REF_Z)
        t = QTransform()
        t.translate(cam.ax, cam.ay)
        t.rotate(-cam.bearing)
        t.scale(s, s)
        t.translate(-cam.x, -cam.y)
        persp = self._perspective(cam)
        return t if persp is None else t * persp

    def _perspective(self, cam, tilt=None):
        """Screen-space homography of a camera pitched TILT_DEG * tilt from straight down, looking at the anchor
        (cam.ax, cam.ay), or None when flat. A flat point d = (dx, dy) from the anchor (dy < 0 ahead) goes to
        anchor + s * (dx, dy cos(a)) / (1 - dy sin(a) / D): the anchor stays put, the road ahead shrinks toward
        the horizon at ay - s D / tan(a). D (the camera distance) is fixed so that at full tilt the horizon is at
        TILT_HORIZON_Y; it does not change with the tilt, so easing the tilt from 0 moves the horizon down from
        far above the screen. Same matrix as QTransform.quadToQuad for the matching trapezoid."""
        tilt = self._tilt_now if tilt is None else tilt
        if tilt < 1e-3:
            return None
        h = max(1, self.height())
        a = math.radians(TILT_DEG * tilt)
        s = 1.0 + (TILT_SCALE - 1.0) * tilt
        d = (TILT_FOLLOW_Y - TILT_HORIZON_Y) * h * math.tan(math.radians(TILT_DEG)) / TILT_SCALE
        k = math.sin(a) / d
        q = QTransform(s, 0.0, 0.0,
                       -cam.ax * k, s * math.cos(a) - cam.ay * k, -k,
                       cam.ax, cam.ay, 1.0)
        return QTransform.fromTranslate(-cam.ax, -cam.ay) * q

    def _ground_top(self, cam):
        """Screen y of the far edge of the drawn ground (TILT_FAR_PX ahead of the anchor); 0 when flat."""
        persp = self._perspective(cam)
        if persp is None:
            return 0.0
        far = persp.map(QPointF(cam.ax, cam.ay - TILT_FAR_PX))
        return max(0.0, min(self.height() * 0.6, far.y()))

    def _on_ground(self, pos):
        """pos with y clamped below the sky band, so the inverse transform stays on the ground plane."""
        top = self._ground_top(self._last_cam or self._camera(time.monotonic()))
        return QPointF(pos.x(), max(pos.y(), top + 4.0)) if top > 0 else QPointF(pos)

    def _visible(self, t, ref_point):
        """Screen point of ref_point, or None if it is beyond the drawn ground or behind the camera."""
        if t.isAffine():
            return t.map(ref_point)
        x, y = ref_point.x(), ref_point.y()
        w = t.m13() * x + t.m23() * y + t.m33()
        if w <= 1e-6:
            return None
        q = t.map(ref_point)
        return q if q.y() >= self._ground_y - 1.0 else None

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
    def _tinted(self, key, pm, night):
        """The tinted copy of tile key (paper style), made at most TINTS_PER_FRAME times a paint; None if over."""
        k = key + (night,)
        hit = self._tint_mem.get(k)
        if hit is not None:
            self._tint_mem.move_to_end(k)
            return hit
        if self._tints_left <= 0:
            return None
        self._tints_left -= 1
        t0 = time.perf_counter()
        hit = tint_tile(pm, night)
        self.tint_ms.append((time.perf_counter() - t0) * 1000.0)
        del self.tint_ms[:-200]
        self._tint_mem[k] = hit
        while len(self._tint_mem) > MEM_TILES:
            self._tint_mem.popitem(last=False)
        return hit

    def _remember(self, key, pixmap):
        self._tint_mem.pop(key + (False,), None)
        self._tint_mem.pop(key + (True,), None)
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

    def _ancestor(self, key, night=None):
        """A lower-zoom tile in memory and the part of it that covers key. night (paper style): from the tinted
        tiles of that variant instead."""
        z, x, y = key
        for up in range(1, 6):
            if z - up < 0:
                break
            pkey = (z - up, x >> up, y >> up)
            pm = self._mem.get(pkey) if night is None else self._tint_mem.get(pkey + (night,))
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
        top = self._ground_y              # 0 when flat; below the sky band when tilted
        x0 = 0.0
        if self._S is not None:           # paper: only the slab shows the map
            slab = self.slab_rect()
            x0, w, top, h = slab.left(), slab.right(), max(top, slab.top()), slab.bottom()
        # The visible ground in map coordinates: the screen (below the sky band) through the inverse transform.
        # A homography maps the four corners to a quadrilateral, so the test stays exact when tilted.
        corners = [inv.map(QPointF(px, py)) for px, py in ((x0, top), (w, top), (w, h), (x0, h))]
        ground = QPolygonF(corners)
        span = 256.0 * 2 ** (REF_Z - z)
        n = 1 << z
        xs, ys = [c.x() for c in corners], [c.y() for c in corners]
        tx0, tx1 = max(0, int(min(xs) // span)), min(n - 1, int(max(xs) // span))
        ty0, ty1 = max(0, int(min(ys) // span)), min(n - 1, int(max(ys) // span))
        cam = self._last_cam
        out = []
        if (tx1 - tx0 + 1) * (ty1 - ty0 + 1) > 400:
            return out
        for tx in range(tx0, tx1 + 1):
            for ty in range(ty0, ty1 + 1):
                rect = QRectF(tx * span, ty * span, span, span)
                if not QPolygonF(rect).intersects(ground):
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
            q = self._visible(t, point)
            if q is None:
                continue
            rect = QRectF(q.x() - 58, q.y() - 9, 116, 18)
            if not rect.intersects(QRectF(self.rect())) or any(rect.intersects(o) for o in occupied):
                continue
            occupied.append(rect)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, name[:28])
        dot = QColor(THEME.hex("highlight"))
        for place in self.places[:120]:
            try:
                q = self._visible(t, QPointF(*to_ref(float(place["lat"]), float(place["lon"]))))
            except (KeyError, TypeError, ValueError):
                continue
            if q is None or not (8 <= q.x() <= self.width() - 8 and 8 <= q.y() <= self.height() - 8):
                continue
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(dot)
            p.drawEllipse(q, 2.6, 2.6)

    # ---- painting --------------------------------------------------------------------
    def paintEvent(self, _event):
        started = time.perf_counter()
        now = time.monotonic()
        cam = self._camera(now)
        self._last_cam = cam
        t = self._transform(cam)
        self._ground_y = self._ground_top(cam)
        tilted = self._ground_y > 0.0
        z = int(max(0, min(MAX_TILE_ZOOM, round(cam.zoom))))
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r = QRectF(self.rect())
        S = self._S
        night = S.is_night() if S is not None else None
        if S is not None:                 # paper: page, slab shadow, edge and face from one cached pixmap
            frame, corners = self._paper_frame()
            p.drawPixmap(0, 0, frame)
            slab = self.slab_rect()
            p.setClipRect(slab.intersected(QRectF(0, self._ground_y, r.width(), r.height())) if tilted else slab)
        else:
            p.fillRect(r, QColor(THEME.hex("bg_alt")))
            if tilted:                    # tiles and route only on the ground, below the sky band
                p.setClipRect(QRectF(0, self._ground_y, r.width(), r.height() - self._ground_y))

        self._disk_loads = 0
        self._tints_left = TINTS_PER_FRAME
        tiles = self._visible_tiles(t, z)
        drawn, wanted, bare = [], [], []
        deferred = False
        for key, rect in tiles:
            pm = self._tile_pixmap(key)
            if pm is not None and S is not None:
                tinted = self._tinted(key, pm, night)
                if tinted is None:        # over this paint's tint budget: a tinted parent, or the slab face
                    deferred = True
                    parent, src = self._ancestor(key, night)
                    if parent is not None:
                        drawn.append((rect, parent, src))
                    continue
                pm = tinted
            if pm is None:
                wanted.append(key)
                parent, src = self._ancestor(key, night)
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
        if drawn and not THEME.is_light and S is None:
            veil = QColor(THEME.hex("bg"))
            veil.setAlpha(50)                                 # soften bright tiles on dark palettes
            p.fillRect(r, veil)

        self._draw_route(p, t)
        if tilted:
            if S is None:
                p.setClipping(False)
            else:
                p.setClipRect(slab)       # the haze stays on the slab
            self._draw_sky(p, r)
        if S is not None:
            p.setClipping(False)
            self._draw_vehicle(p, t, cam, now)
            for at, corner in corners:   # round the slab's corners over whatever was drawn there
                p.drawPixmap(at, corner)
            self._paint_floating_shadows(p)
        else:
            self._draw_vehicle(p, t, cam, now)
        self._draw_overlays(p, cam)
        p.end()
        self.paint_ms = (time.perf_counter() - started) * 1000.0
        if deferred:
            QTimer.singleShot(0, self.update)               # more tiles to tint
        if self._disk_loads >= DISK_LOADS_PER_FRAME:
            QTimer.singleShot(0, self.update)               # more tiles waiting on disk
        # Fetch only once the zoom has settled, so a zoom animation does not download
        # tiles for the levels it passes through (parents are scaled up meanwhile).
        if abs(cam.zoom - self._zoom_target) < 0.05 and self._tween_from is None:
            self._pump(wanted)

    # ---- paper and depth style -------------------------------------------------------
    def _ground_colour(self):
        """The slab's face where no tile is drawn yet (and the haze of the tilted view): the tinted OSM ground."""
        return QColor("#E2D5C9") if not self._S.is_night() else QColor("#292522")

    def _edge_colour(self):
        S = self._S
        return QColor(S.blend(S.hx("paper_deep"), S.hx("shadow"), 0.28)) if not S.is_night() else QColor("#121110")

    def _paper_frame(self):
        """(pixmap, corners): the page in paper, the slab's long warm shadow, its edge (the thickness, like the
        side of the diorama in the reference) and its face; and four corner patches with the slab's rounded
        corner cut out, drawn over the map to round it. Cached by size and day or night: the map repaints every
        frame, so no live effect is used."""
        S = self._S
        key = (self.width(), self.height(), S.is_night())
        if self._frame_key == key and self._frame is not None:
            return self._frame
        from PySide6.QtGui import QImage
        w, h = max(1, self.width()), max(1, self.height())
        slab = self.slab_rect()
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(S.c("paper"))
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = slab.adjusted(0, 0, 0, SLAB_EDGE)
        S.paint_shadow(p, body, SLAB_R, 3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._edge_colour())
        p.drawRoundedRect(body, SLAB_R, SLAB_R)
        p.setBrush(self._ground_colour())
        p.drawRoundedRect(slab, SLAB_R, SLAB_R)
        p.end()
        corners = []
        n = SLAB_R + 2
        for cx, cy in ((slab.left(), slab.top()), (slab.right() - n, slab.top()),
                       (slab.left(), slab.bottom() - n), (slab.right() - n, slab.bottom() - n)):
            at = QPoint(int(math.floor(cx)), int(math.floor(cy)))
            patch = img.copy(QRect(at.x(), at.y(), n + 1, n + 1))
            q = QPainter(patch)
            q.setRenderHint(QPainter.RenderHint.Antialiasing)
            q.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
            q.setPen(Qt.PenStyle.NoPen)
            q.setBrush(QColor(0, 0, 0, 255))
            q.drawRoundedRect(slab.translated(-at.x(), -at.y()), SLAB_R, SLAB_R)
            q.end()
            corners.append((at, QPixmap.fromImage(patch)))
        self._frame_key, self._frame = key, (QPixmap.fromImage(img), corners)
        return self._frame

    def _paint_floating_shadows(self, p):
        """Cached shadows under the top-plane widgets over the map: the control column, Simulate drive and the
        page's search field and status line (their own drop-shadow effects would re-blur every map frame)."""
        S = self._S
        for b in (self.follow_button, self.overview_button, self.tilt_button, self.zoom_in, self.zoom_out):
            if b.isVisible():
                S.paint_shadow(p, QRectF(b.geometry()).adjusted(2, 2, -2, -2), 20, 1)
        if self.sim_button.isVisible():
            S.paint_shadow(p, QRectF(self.sim_button.geometry()).adjusted(2, 2, -2, -2), 20, 1)
        for widget in self.floating:
            try:
                if widget is not None and widget.isVisible():
                    win = self.window()     # a sibling over the map: map through the window
                    tl = widget.mapTo(win, QPoint(0, 0)) - self.mapTo(win, QPoint(0, 0))
                    S.paint_shadow(p, QRectF(tl.x(), tl.y(), widget.width(), widget.height()), 24, 1)
            except RuntimeError:
                pass

    def _draw_sky(self, p, r):
        """Band above the drawn ground in the theme's background colour, fading into the map (tilted view)."""
        sky = QColor(THEME.hex("bg")) if self._S is None else self._ground_colour()
        y = self._ground_y
        p.fillRect(QRectF(0, 0, r.width(), y + 1), sky)
        fade = QLinearGradient(0, y, 0, y + TILT_FADE_PX)
        clear = QColor(sky)
        clear.setAlpha(0)
        fade.setColorAt(0.0, sky)
        fade.setColorAt(1.0, clear)
        p.fillRect(QRectF(0, y, r.width(), TILT_FADE_PX), fade)

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

            S = self._S
            if S is not None:             # paper: the route is information, so ink on a paper casing (no signal)
                casing = S.c("paper", 235)
                stroke(self._route_poly, casing, 12.0)
                if self.progress > 0:
                    stroke(done, S.c("ink_3", 220), 6.0)
                stroke(ahead, S.c("ink"), 7.0)
                p.resetTransform()
            else:
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
                q = self._visible(t, QPointF(*to_ref(float(self.destination["lat"]), float(self.destination["lon"]))))
            except (KeyError, TypeError, ValueError):
                return
            if q is None:                 # beyond the drawn ground in the tilted view
                return
            if self._S is not None:       # paper: an ink target on a paper ring
                p.setBrush(self._S.c("paper"))
                p.setPen(QPen(self._S.c("ink"), 4))
                p.drawEllipse(q, 10, 10)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(self._S.c("ink"))
                p.drawEllipse(q, 4, 4)
                return
            p.setBrush(THEME.status("crit"))
            p.setPen(QPen(QColor(THEME.hex("text")), 2))
            p.drawEllipse(q, 8, 8)

    def _draw_approx(self, p, t):
        """Cell-tower position: a dot inside a translucent circle of the reported accuracy."""
        lat, lon, acc = self.approx
        ref = to_ref(lat, lon)
        q = self._visible(t, QPointF(*ref))
        if q is None:
            return
        acc_m = _num(acc) or 500.0
        edge = t.map(QPointF(ref[0] + acc_m * _ref_per_m(ref[1]), ref[1]))
        radius = max(14.0, math.hypot(edge.x() - q.x(), edge.y() - q.y()))
        fill = QColor(THEME.hex("accent")) if self._S is None else self._S.c("ink_2")
        area = QColor(fill)
        area.setAlpha(38)
        rim = QColor(fill)
        rim.setAlpha(120)
        p.setBrush(area)
        p.setPen(QPen(rim, 1.5))
        p.drawEllipse(q, radius, radius)
        p.setBrush(fill)
        p.setPen(QPen(QColor("#FFFFFF") if self._S is None else self._S.c("card"), 3))
        p.drawEllipse(q, 8, 8)

    def _draw_vehicle(self, p, t, cam, now):
        pos = self._vehicle_ref(now)
        if pos is None:
            if self.approx and not self.simulating:
                self._draw_approx(p, t)
            return
        q = t.map(QPointF(*pos))
        live = self.vehicle is not None
        fill = QColor(THEME.hex("accent")) if live else THEME.status("inactive")
        ring = QColor("#FFFFFF")
        if self._S is not None:           # paper: the tuk-tuk in ink on a card ring (information, not signal)
            fill, ring = self._S.c("ink" if live else "ink_2"), self._S.c("card")
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
        if self.sw7_layout:               # a 56 px compass in the top slot of the control column
            return QRectF(self.control_slots()["compass"]).adjusted(4, 4, -4, -4)
        return QRectF(self.width() - 84, 104, 48, 48)

    def _draw_overlays(self, p, cam):
        w, h = self.width(), self.height()
        # compass: the needle points to north on screen
        c = self.compass_rect()
        S = self._S
        if S is not None:                 # paper: a floating card; a signal ring while a tap turns it north-up
            S.paint_shadow(p, c, c.width() / 2, 1)
            tappable = self._mode == "explore"
            p.setPen(QPen(S.c("signal"), 2.0) if tappable else QPen(S.c("hairline"), 1.0))
            p.setBrush(S.c("card"))
        else:
            p.setPen(QPen(QColor(THEME.hex("border")), 1.5))
            p.setBrush(QColor(THEME.hex("card")))
        p.drawEllipse(c)
        k = c.width() / 48.0              # needle scaled with the compass (1 before the layout pass)
        p.save()
        p.translate(c.center())
        p.rotate(-cam.bearing)
        north = QPainterPath(QPointF(0, -12 * k))
        north.lineTo(5 * k, 0)
        north.lineTo(-5 * k, 0)
        north.closeSubpath()
        south = QPainterPath(QPointF(0, 12 * k))
        south.lineTo(5 * k, 0)
        south.lineTo(-5 * k, 0)
        south.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(THEME.status("crit"))
        p.drawPath(north)
        p.setBrush(QColor(THEME.hex("text_faint")))
        p.drawPath(south)
        p.restore()
        # "N" upright, just outside the north tip
        a = math.radians(-cam.bearing)
        n_at = c.center() + QPointF(16 * k * math.sin(a), -16 * k * math.cos(a))
        p.setPen(QColor(THEME.hex("text")))
        p.setFont(THEME.font(13 if S is not None else 12 if self.sw7_layout else 9, QFont.Weight.Bold))
        nh = 7 * k
        p.drawText(QRectF(n_at.x() - nh, n_at.y() - nh, 2 * nh, 2 * nh), Qt.AlignmentFlag.AlignCenter, "N")
        self.overlay_rects = {"compass": QRectF(c)}
        self.overlay_px = {}
        self.drawn_pills = []
        chip = self.altitude_chip_rect()
        if chip is not None:              # altitude chip left of the compass, only when known (layout pass)
            p.setFont(THEME.font(PX["altitude"], QFont.Weight.DemiBold))
            text = self._altitude_text()
            bg = QColor(THEME.hex("card"))
            bg.setAlpha(235)
            p.setPen(QPen(QColor(THEME.hex("border")), 1))
            p.setBrush(bg)
            p.drawRoundedRect(chip, 12, 12)
            p.setPen(QColor(THEME.hex("text")))
            p.drawText(chip, Qt.AlignmentFlag.AlignCenter, text)
            self.overlay_rects["altitude"] = chip
            self.overlay_px["altitude"] = PX["altitude"]

        # attribution (required by the OSM licence), left of the zoom buttons
        text = ATTRIBUTION
        if self.vector_fallback_active and self.tile_status == "offline":
            text = ("Tiles offline · " if self.sw7_layout else "Street tiles offline, showing offline roads · ") + ATTRIBUTION
        p.setFont(THEME.font(13 if S is not None else 12 if self.sw7_layout else 9))
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text) + 14
        if S is not None:                 # paper: on the slab, above Simulate drive, clear of the column
            slab = self.slab_rect()
            box = QRectF(slab.right() - 12 - tw, self.sim_button_rect().top() - 8 - 22, tw, 22)
        elif self.sw7_layout:             # bottom right, under the Simulate drive button, clear of the column
            box = QRectF(w - EDGE - tw, h - 30, tw, 20)
        else:
            box = QRectF(w - 72 - tw, h - 24, tw, 18)
        self.overlay_rects["attribution"] = box
        bg = QColor(THEME.hex("card"))
        bg.setAlpha(200)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(box, 5, 5)
        p.setPen(QColor(THEME.hex("text_dim")))
        p.drawText(box, Qt.AlignmentFlag.AlignCenter, text)

        ucx, ucy = self._usable_centre()
        if S is not None:                 # paper: badges in the middle of the slab's free width
            ucx = (SLAB_L + self.width() - EDGE - CTRL) / 2
        pill_y = 126.0
        if self.sw7_layout:
            # badges go under the search field, between the turn banner (if any) and the control column
            banner = self.turn_banner_rect() if self.navigating else None
            if self.navigating:
                self._draw_navigation_layout(p, w, h)
            pill_y = float(EDGE + 64 + CTRL_GAP + 29)
            if banner is not None:
                ucx = (banner.right() + w - EDGE - CTRL) / 2
        elif self.navigating:
            pill_y = self._draw_navigation(p, w, h) + 36.0
        self._pill_y = pill_y               # where the REPLAY / SIMULATED badge goes (tests read it)
        self._pill_x = ucx
        if self.replay:
            self._pill(p, QPointF(ucx, pill_y), "REPLAY", "Replayed data, not live", THEME.status("warn"), filled=True)
        if self.simulating and not self.sw7_layout:   # layout pass: a SIMULATED chip in the arrival-time bar instead
            left_m, left_min = self.sim_remaining()
            if self.sim_arrived:
                title, sub = "ARRIVED (SIMULATED)", "Not live data. Tap End simulation to finish"
            else:
                title = "SIMULATED DRIVE"
                sub = f"Not live data · {left_m / 1000:.1f} km, {max(1, round(left_min))} min left at {SIM_KMH:.0f} km/h"
            self._pill(p, QPointF(ucx, pill_y), title, sub, THEME.status("warn"), filled=True)
        if self.vehicle is None and self.approx and not self.simulating:
            acc = _num(self.approx[2])
            sub = ("From the mobile network" + (f", about ±{acc:.0f} m" if acc else "")
                   + ". Waiting for GPS fix")
            self._pill(p, QPointF(ucx, pill_y), "Approximate position", sub, THEME.status("warn"))
        elif self.vehicle is None and not self.simulating:
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

    def _eta_seconds(self, left_m):
        if self.simulating:
            return left_m / (SIM_KMH / 3.6)
        if self._plan_duration_s > 0 and self._route_total_m > 0:
            return self._plan_duration_s * left_m / self._route_total_m
        return None

    def _draw_navigation_layout(self, p, w, h):
        """Layout pass: turn banner anchored top left, arrival-time bar at the bottom centre with the SIMULATED chip
        at its left end. Sizes from PX (Planning/google-stitch-dashboard-prompt.md, Navigation)."""
        if self._S is not None:
            return self._draw_navigation_paper(p, w, h)
        green, white = QColor(TURN_GREEN), QColor("#FFFFFF")
        ahead = self.next_maneuvers(2)
        banner = self.turn_banner_rect()
        if ahead and banner is not None:
            man, dist = ahead[0]
            bx, by, bw = banner.left(), banner.top(), banner.width()
            text_w = bw - 112 - 16
            p.setPen(Qt.PenStyle.NoPen)
            if len(ahead) > 1:            # the Then strip under the banner, one card with it
                p.setBrush(QColor(THEN_GREEN))
                p.drawRoundedRect(banner, 16, 16)
                p.setBrush(green)
                p.drawRoundedRect(QRectF(bx, by, bw, BANNER_H), 16, 16)
                p.drawRect(QRectF(bx, by + BANNER_H - 16, bw, 16))
                p.setPen(white)
                p.setFont(THEME.font(PX["then"], QFont.Weight.DemiBold))
                then = QRectF(bx + 20, by + BANNER_H, bw - 40, THEN_H)
                nxt = self._instruction(ahead[1][0])
                p.drawText(then, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           p.fontMetrics().elidedText("Then: " + nxt[:1].lower() + nxt[1:], Qt.TextElideMode.ElideRight,
                                                      int(then.width())))
                self.overlay_rects["then"] = then
                self.overlay_px["then"] = PX["then"]
            else:
                p.setBrush(green)
                p.drawRoundedRect(QRectF(bx, by, bw, BANNER_H), 16, 16)
            self._turn_arrow(p, QRectF(bx + 20, by + (BANNER_H - 72) / 2, 72, 72), man["kind"], white)
            tx = bx + 112
            p.setPen(white)
            if man["kind"] == "arrive":
                p.setFont(THEME.font(PX["street"] + 4, QFont.Weight.Bold))
                p.drawText(QRectF(tx, by, text_w, BANNER_H), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           p.fontMetrics().elidedText(self._instruction(man), Qt.TextElideMode.ElideRight, int(text_w)))
            else:
                p.setFont(THEME.font(PX["distance"], QFont.Weight.Bold))
                p.drawText(QRectF(tx, by + 8, text_w, 64), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           self._distance_text(dist))
                p.setFont(THEME.font(PX["street"], QFont.Weight.DemiBold))
                p.drawText(QRectF(tx, by + 72, text_w, 44), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           p.fontMetrics().elidedText(self._instruction(man), Qt.TextElideMode.ElideRight, int(text_w)))
                self.overlay_px["distance"] = PX["distance"]
            self.overlay_px["street"] = PX["street"]
            self.overlay_rects["banner"] = QRectF(banner)
        # arrival-time bar: [SIMULATED]  2 min   630 m   arrive 14:28
        left_m = max(0.0, self._route_total_m - (self._along_m or 0.0))
        eta_s = self._eta_seconds(left_m)
        if eta_s is None and not self.simulating:
            return
        bar = self.eta_rect()
        bg = QColor(THEME.hex("card"))
        bg.setAlpha(240)
        p.setPen(QPen(QColor(THEME.hex("border")), 1))
        p.setBrush(bg)
        p.drawRoundedRect(bar, 16, 16)
        self.overlay_rects["eta"] = QRectF(bar)
        x = bar.left() + 10
        if self.simulating:
            p.setFont(THEME.font(PX["chip"], QFont.Weight.Bold))
            label = "SIMULATED"
            chip = QRectF(x, bar.top() + 10, p.fontMetrics().horizontalAdvance(label) + 28, bar.height() - 20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(THEME.status("warn"))
            p.drawRoundedRect(chip, 12, 12)
            p.setPen(QColor("#0B0D10"))
            p.drawText(chip, Qt.AlignmentFlag.AlignCenter, label)
            self.overlay_rects["sim_chip"] = chip
            self.overlay_px["chip"] = PX["chip"]
            x = chip.right()
        arrived = self.sim_arrived
        minutes = max(1, int(round((eta_s or 0) / 60.0)))
        parts = [("Arrived" if arrived else f"{minutes} min", PX["eta_time"], QColor(ETA_GREEN), QFont.Weight.Bold),
                 (self._distance_text(left_m) if left_m >= 20 else "0 m", PX["eta_text"], QColor(THEME.hex("text")),
                  QFont.Weight.DemiBold)]
        if eta_s is not None and not arrived:
            parts.append(("arrive " + time.strftime("%H:%M", time.localtime(time.time() + eta_s)), PX["eta_text"],
                          QColor(THEME.hex("text_dim")), QFont.Weight.DemiBold))
        widths = [QFontMetricsF(THEME.font(px, wt)).horizontalAdvance(t) for t, px, _c, wt in parts]
        room = bar.right() - 10 - x
        if len(parts) == 3 and sum(widths) + 16 * (len(parts) + 1) > room:   # narrow: drop the word "arrive"
            parts[2] = (parts[2][0].replace("arrive ", ""),) + parts[2][1:]
            widths[2] = QFontMetricsF(THEME.font(parts[2][1], parts[2][3])).horizontalAdvance(parts[2][0])
        gap = max(12.0, (room - sum(widths)) / (len(parts) + 1))
        x += gap
        for (text, px, colour, weight), tw in zip(parts, widths):
            p.setPen(colour)
            p.setFont(THEME.font(px, weight))
            p.drawText(QRectF(x, bar.top(), tw + 2, bar.height()), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            x += tw + gap
        self.overlay_rects["eta_text_right"] = QRectF(x - gap, bar.top(), 0, bar.height())
        self.overlay_px["eta_time"], self.overlay_px["eta_text"] = PX["eta_time"], PX["eta_text"]

    def _draw_navigation_paper(self, p, w, h):
        """Paper style: the turn banner is the page's inverse (charcoal) card with the distance to the turn as the
        page's one hero value (120 px) and the street at 22 px; the arrival-time bar is a paper card with time and
        distance left at 22 px and the arrival time and the plan's arrival battery at 16 px. This bar is the one
        remaining-distance and ETA figure on the page: it follows the vehicle along the route, while the status
        line only names the route source (Planning/data-ownership-and-merge-plan.md, option A)."""
        S = self._S
        on, on2 = S.c("on_charcoal"), S.c("on_charcoal_2")
        ahead = self.next_maneuvers(2)
        banner = self.turn_banner_rect()
        if ahead and banner is not None:
            man, dist = ahead[0]
            bx, by, bw = banner.left(), banner.top(), banner.width()
            S.paint_shadow(p, banner, 24, 2)
            p.setPen(Qt.PenStyle.NoPen)
            top = QRectF(bx, by, bw, PAPER_BANNER_H)
            if len(ahead) > 1:            # the Then strip: the bottom of the same card, a shade lighter
                p.setBrush(QColor(S.blend(S.hx("charcoal"), S.hx("on_charcoal"), 0.07)))
                p.drawRoundedRect(banner, 24, 24)
                p.setBrush(S.c("charcoal"))
                p.drawRoundedRect(top, 24, 24)
                p.drawRect(QRectF(bx, by + PAPER_BANNER_H - 24, bw, 24))
                p.setPen(on2)
                p.setFont(S.font(16, QFont.Weight.DemiBold))
                then = QRectF(bx + 24, by + PAPER_BANNER_H, bw - 48, THEN_H)
                nxt = self._instruction(ahead[1][0])
                p.drawText(then, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           p.fontMetrics().elidedText("Then: " + nxt[:1].lower() + nxt[1:], Qt.TextElideMode.ElideRight,
                                                      int(then.width())))
                self.overlay_rects["then"] = then
                self.overlay_px["then"] = 16
            else:
                p.setBrush(S.c("charcoal"))
                p.drawRoundedRect(top, 24, 24)
            self._turn_arrow(p, QRectF(bx + 22, by + 30, 76, 76), man["kind"], on)
            tx, text_w = bx + 116, bw - 116 - 20
            if man["kind"] == "arrive":
                p.setPen(on)
                p.setFont(S.font(22, QFont.Weight.Bold))
                p.drawText(QRectF(tx, by + 20, text_w, 96), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           p.fontMetrics().elidedText(self._instruction(man), Qt.TextElideMode.ElideRight, int(text_w)))
            else:
                p.setPen(on)
                f = S.font(S.HERO_MIN, QFont.Weight.Bold)
                p.setFont(f)
                text = self._distance_text(dist)
                if QFontMetricsF(f).horizontalAdvance(text) > text_w:   # "1.2 km": the unit goes small
                    number, unit = text.rsplit(" ", 1)
                    nw = QFontMetricsF(f).horizontalAdvance(number + " ")
                    p.drawText(QRectF(tx, by - 4, text_w, 140), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, number)
                    p.setFont(S.font(22, QFont.Weight.Bold))
                    p.drawText(QRectF(tx + nw - 18, by + 74, text_w - nw + 18, 30),
                               Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, unit)
                else:
                    p.drawText(QRectF(tx, by - 4, text_w, 140), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
                self.overlay_px["distance"] = S.HERO_MIN
                p.setPen(on)
                p.setFont(S.font(22, QFont.Weight.DemiBold))
                street = QRectF(bx + 24, by + 128, bw - 48, 40)
                p.drawText(street, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           p.fontMetrics().elidedText(self._instruction(man), Qt.TextElideMode.ElideRight, int(street.width())))
            self.overlay_px["street"] = 22
            self.overlay_rects["banner"] = QRectF(banner)
        left_m = max(0.0, self._route_total_m - (self._along_m or 0.0))
        eta_s = self._eta_seconds(left_m)
        if eta_s is None and not self.simulating:
            return
        bar = self.eta_rect()
        S.paint_card(p, bar, 24, 2)
        self.overlay_rects["eta"] = QRectF(bar)
        x = bar.left() + 12
        if self.simulating:               # data-source mark: ink on a warn tint with a warn dot, never signal
            p.setFont(S.font(13, QFont.Weight.Bold, caps=True))
            label = "SIMULATED"
            chip = QRectF(x, bar.top() + 20, p.fontMetrics().horizontalAdvance(label) + 40, bar.height() - 40)
            p.setPen(QPen(S.c("warn"), 1))
            p.setBrush(S.c("warn_tint"))
            p.drawRoundedRect(chip, chip.height() / 2, chip.height() / 2)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(S.c("warn"))
            p.drawEllipse(QPointF(chip.left() + 14, chip.center().y()), 4, 4)
            p.setPen(S.c("ink"))
            p.drawText(chip.adjusted(22, 0, -6, 0), Qt.AlignmentFlag.AlignCenter, label)
            self.overlay_rects["sim_chip"] = chip
            self.overlay_px["chip"] = 13
            x = chip.right()
        arrived = self.sim_arrived
        minutes = max(1, int(round((eta_s or 0) / 60.0)))
        ink, ink2 = S.c("ink"), S.c("ink_2")
        parts = [("Arrived" if arrived else f"{minutes} min", 22, ink, QFont.Weight.Bold),
                 (self._distance_text(left_m) if left_m >= 20 else "0 m", 22, ink, QFont.Weight.Normal)]
        if eta_s is not None and not arrived:
            tail = "arrive " + time.strftime("%H:%M", time.localtime(time.time() + eta_s))
            if self.arrival_soc is not None:
                tail += f" · {self.arrival_soc:.0f} % battery"
            parts.append((tail, 16, ink2, QFont.Weight.Normal))
        fonts = [S.font(px, wt) for _t, px, _c, wt in parts]
        widths = [QFontMetricsF(f).horizontalAdvance(t) for f, (t, *_r) in zip(fonts, parts)]
        room = bar.right() - 12 - x
        if len(parts) == 3 and sum(widths) + 16 * (len(parts) + 1) > room:   # narrow: shorter tail
            parts[2] = (parts[2][0].replace("arrive ", "").replace(" battery", ""),) + parts[2][1:]
            widths[2] = QFontMetricsF(fonts[2]).horizontalAdvance(parts[2][0])
        gap = max(12.0, (room - sum(widths)) / (len(parts) + 1))
        x += gap
        for (text, px, colour, weight), f, tw in zip(parts, fonts, widths):
            p.setPen(colour)
            p.setFont(f)
            p.drawText(QRectF(x, bar.top(), tw + 2, bar.height()), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            x += tw + gap
        self.overlay_rects["eta_text_right"] = QRectF(x - gap, bar.top(), 0, bar.height())
        self.overlay_px["eta_time"], self.overlay_px["eta_text"] = 22, 16
        self.eta_texts = [t for t, *_r in parts]

    def _pill(self, p, centre, title, sub, colour, filled=False):
        if self._S is not None:           # paper: a floating card with a status dot; ink text
            return self._pill_paper(p, centre, title, sub, colour)
        self.drawn_pills.append(title)
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

    def _pill_paper(self, p, centre, title, sub, colour):
        S = self._S
        self.drawn_pills.append(title)
        tf, sf = S.font(16, QFont.Weight.Bold), S.font(13)
        tw = QFontMetricsF(tf).horizontalAdvance(title) + 22
        sw = QFontMetricsF(sf).horizontalAdvance(sub)
        bw, bh = max(tw, sw) + 48, 64
        box = QRectF(centre.x() - bw / 2, centre.y() - bh / 2, bw, bh)
        S.paint_card(p, box, 20, 2)
        title_r = QRectF(box.left(), box.top() + 9, bw, 24)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(colour))
        p.drawEllipse(QPointF(box.center().x() - tw / 2 + 5, title_r.center().y()), 5, 5)
        p.setPen(S.c("ink"))
        p.setFont(tf)
        p.drawText(title_r.adjusted(22, 0, 0, 0), Qt.AlignmentFlag.AlignCenter, title)
        p.setPen(S.c("ink_2"))
        p.setFont(sf)
        p.drawText(QRectF(box.left(), box.top() + 35, bw, 20), Qt.AlignmentFlag.AlignCenter, sub)

    # ---- interaction -----------------------------------------------------------------
    def resizeEvent(self, event):
        if self.sw7_layout:
            slots = self.control_slots()
            for name, button in (("follow", self.follow_button), ("overview", self.overview_button),
                                 ("tilt", self.tilt_button), ("zoom_in", self.zoom_in), ("zoom_out", self.zoom_out)):
                if name in slots:
                    button.setGeometry(slots[name])
            self.sim_button.setGeometry(self.sim_button_rect())
        else:
            self.zoom_in.setGeometry(max(0, self.width() - 62), max(0, self.height() - 94), 44, 38)
            self.zoom_out.setGeometry(max(0, self.width() - 62), max(0, self.height() - 52), 44, 38)
            self.tilt_button.setGeometry(max(0, self.width() - 62), max(0, self.height() - 136), 44, 38)
            self.sim_button.setGeometry(max(0, self.width() - 290), max(0, self.height() - 100), 210, 44)
        if self._mode == "overview":
            self._overview = self._fit_camera()
            self._zoom_target = self._zoom_now = self._overview.zoom
        super().resizeEvent(event)

    def _apply_theme(self, *_):
        S = self._S
        if S is not None:                 # paper: Simulate drive a signal outline button; caches follow the variant
            self.sim_button.setStyleSheet(S.button_qss("outline", 20, 16))
            for b in (self.follow_button, self.overview_button, self.tilt_button, self.zoom_in, self.zoom_out):
                b.setFont(S.font(13, QFont.Weight.Bold))   # the labels are painted at 13 px
            self._frame_key = None
            night = S.is_night()
            for k in [k for k in self._tint_mem if k[3] != night]:
                del self._tint_mem[k]
            self.update()
            return
        if self.sw7_layout:               # the column buttons paint themselves from THEME
            self.sim_button.setStyleSheet(
                f"font-size:{PX['status']}px;font-weight:700;padding:0px 12px;background:{THEME.hex('card')};"
                f"color:{THEME.hex('text')};border:2px solid {THEME.status('warn').name()};border-radius:12px;")
            self.update()
            return
        style = (f"font-size:24px;background:{THEME.hex('card')};color:{THEME.hex('text')};"
                 f"border:1px solid {THEME.hex('border')};border-radius:6px;")
        for button in (self.zoom_in, self.zoom_out):
            button.setStyleSheet(style)
        self.tilt_button.setStyleSheet(
            f"QPushButton{{font-size:15px;font-weight:700;padding:0px;background:{THEME.hex('card')};color:{THEME.hex('text')};"
            f"border:1px solid {THEME.hex('border')};border-radius:6px;}}"
            f"QPushButton:checked{{border:2px solid {THEME.hex('accent')};color:{THEME.hex('accent')};}}")
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
        if ok:                            # tilted: points in the sky band are taken on the ground's far edge
            a, b = inv.map(self._on_ground(self._drag_last)), inv.map(self._on_ground(pos))
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
                # Any visible button under the finger (zoom, Simulate drive) gets the touch as a
                # synthesized click. Up to 11 Oct only the zoom buttons were listed here, so a tap on
                # Simulate drive was taken by the map as a drag and never clicked on the touchscreen.
                if any(b.isVisible() and b.geometry().contains(start)
                       for b in self.findChildren(QAbstractButton)):
                    event.ignore()
                    return False
            if kind in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
                if points and not self._multi:
                    self._release(points[0].position())
                self._pinch = None
                self._multi = False
                event.accept()
                return True
            # Three or more fingers swipe between dashboard pages (sw7_page_swipe): the map neither zooms nor
            # pans for them, and does not treat the lift as a tap or drag end.
            if len([q for q in points if q.state() != QEventPoint.State.Released]) >= 3 or self._multi:
                self._multi = True
                self._pinch = None
                self._press = None
                self._dragging = False
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
