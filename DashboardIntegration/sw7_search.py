"""SW-7: destination search on the Navigation page, like a ride-hailing app (Planning/destination-search-prompt.md).

The team's search waited for Nominatim, which finds nothing for partial words and has no location bias. This
replaces it for the destination field only:

- Type-ahead from Photon (photon.komoot.io, OpenStreetMap data built for search-as-you-type), biased to the
  current position and limited to South Africa. Recent destinations and offline place matches (the team's own
  place list, through a fast word-prefix index) show at once; Photon results are merged in when they arrive.
  Requests are debounced (120 ms, the team's timer), cached by query, run on background threads, and stale
  answers are dropped. If Photon fails, the team's coordinator.request_suggestions runs as before.
- Two-line rows (name in bold, address dimmer), the distance from the current position, a clock for recent
  places and a pin for search results, drawn by a delegate on the team's own suggestions list. Items keep the
  team's contract (text = label, UserRole = place dict with lat, lon, label) so _choose_suggestion still works.
- Recent destinations (~/.config/sw7/recent_destinations.json, 8, newest first) when the empty field is tapped.
- A header row saying where the route will start: GPS fix, the modem's network position, the last known fix,
  or UCT. fallback_start() gives the coordinator the same order for the route start.

TUKZIE_SW7_SEARCH=0 keeps the team's search. TUKZIE_PHOTON_URL and TUKZIE_SW7_RECENTS override the endpoint and
the recents file (tests).
"""
from __future__ import annotations

import json
import math
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractItemView, QListWidgetItem, QStyle, QStyledItemDelegate

try:
    from ..theme import THEME
except ImportError:          # imported on its own (coordinator start resolution in tests)
    THEME = None

UCT = (-33.9577, 18.4612)
PHOTON_URL = "https://photon.komoot.io/api/"
USER_AGENT = "TUKZIE-SW7-dashboard/1.0 (UCT student project)"
BBOX = "16.3,-35.0,33.0,-22.0"          # South Africa
MAX_RECENTS = 8
CACHE_SIZE = 96

ROLE_KIND = int(Qt.ItemDataRole.UserRole) + 1        # header | status | recent | result | local
ROLE_TITLE = ROLE_KIND + 1
ROLE_SUBTITLE = ROLE_KIND + 2
ROLE_DISTANCE = ROLE_KIND + 3
ROLE_POSKIND = ROLE_KIND + 4
CHOOSABLE = ("recent", "result", "local")
ROW_H = {"header": 40, "status": 44}
ROW_DEFAULT_H = 58
VISIBLE_ROWS = 5
_STATE_SELECTED = QStyle.StateFlag.State_Selected


def enabled():
    return os.environ.get("TUKZIE_SW7_SEARCH", "1").strip() != "0"


def _num(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def haversine_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(min(1.0, math.sqrt(h)))


def format_distance(km):
    if km is None:
        return ""
    if km < 1.0:
        return f"{max(10, int(round(km * 100)) * 10)} m"
    return f"{km:.1f} km" if km < 10 else f"{km:.0f} km"


# ---- where am I --------------------------------------------------------------------------------------------

def current_position(state, last_fix=None):
    """The best position for distances, search bias and the header, in the coordinator's start order."""
    lat, lon = _num(getattr(state, "latitude", None)), _num(getattr(state, "longitude", None))
    if lat is not None and lon is not None:
        simulated = bool(getattr(state, "sw7_simulated", False)) or "simulated" in str(getattr(state, "data_source", "") or "")
        if simulated:
            return {"lat": lat, "lon": lon, "kind": "simulated", "header": "From: Simulated drive position"}
        return {"lat": lat, "lon": lon, "kind": "gps", "header": "From: Current location (GPS)"}
    cell = getattr(state, "sw7_cell_position", None) if state is not None else None
    if cell and len(cell) >= 2 and _num(cell[0]) is not None and _num(cell[1]) is not None:
        acc = _num(cell[2]) if len(cell) > 2 else None
        text = f"mobile network, ±{acc:.0f} m" if acc else "mobile network"
        return {"lat": float(cell[0]), "lon": float(cell[1]), "kind": "network", "accuracy_m": acc,
                "header": f"From: Approximate location ({text})"}
    if last_fix and _num(last_fix[0]) is not None and _num(last_fix[1]) is not None:
        return {"lat": float(last_fix[0]), "lon": float(last_fix[1]), "kind": "last",
                "header": "From: Last known position"}
    return {"lat": UCT[0], "lon": UCT[1], "kind": "uct", "header": "From: UCT (no GPS)"}


def fallback_start(raw, last_fix=None):
    """Route start when there is no GPS fix: the network position, then the last fix; None means use UCT."""
    pos = current_position(None if raw is None else _NoFix(raw), last_fix)
    if pos["kind"] == "network":
        label = "Approximate location (mobile network)"
    elif pos["kind"] == "last":
        label = "Last known position"
    else:
        return None
    return {"name": label, "label": label, "lat": pos["lat"], "lon": pos["lon"], "kind": pos["kind"]}


class _NoFix:
    """raw without latitude/longitude (the coordinator only calls fallback_start after the GPS check)."""
    def __init__(self, raw):
        self.sw7_cell_position = getattr(raw, "sw7_cell_position", None)
    latitude = longitude = None


# ---- recents -----------------------------------------------------------------------------------------------

def recents_path():
    override = os.environ.get("TUKZIE_SW7_RECENTS", "").strip()
    return Path(override) if override else Path.home() / ".config" / "sw7" / "recent_destinations.json"


class Recents:
    def __init__(self, path=None):
        self.path = Path(path) if path else recents_path()
        self.items = []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = [p for p in data if isinstance(p, dict) and _num(p.get("lat")) is not None
                          and _num(p.get("lon")) is not None and str(p.get("label") or "").strip()][:MAX_RECENTS]
        except Exception:
            self.items = []

    def add(self, place):
        if not isinstance(place, dict):
            return
        lat, lon = _num(place.get("lat")), _num(place.get("lon"))
        label = str(place.get("label") or place.get("name") or "").strip()
        if lat is None or lon is None or not label or label.lower().startswith(("current location", "approximate location")):
            return
        keep = {k: place[k] for k in ("name", "label", "display_name", "address", "kind", "_online_provider") if k in place}
        keep.update(label=label, lat=lat, lon=lon, saved_at=time.time())
        keep.setdefault("name", label)
        self.items = [p for p in self.items
                      if not (p["label"].lower() == label.lower() or haversine_km((p["lat"], p["lon"]), (lat, lon)) < 0.03)]
        self.items.insert(0, keep)
        del self.items[MAX_RECENTS:]
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.items, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)
        except Exception:
            pass


# ---- Photon ------------------------------------------------------------------------------------------------

def _norm(text):
    return " ".join(re.sub(r"[^0-9a-z]+", " ", str(text).lower().replace("'", "").replace("’", "")).split())


def photon_places(query, near, limit=8, timeout=4.0):
    """Photon search biased to near=(lat, lon). Raises on network or HTTP errors."""
    params = {"q": query, "limit": limit, "lang": "en", "bbox": BBOX}
    if near:
        params.update(lat=f"{near[0]:.5f}", lon=f"{near[1]:.5f}")
    url = os.environ.get("TUKZIE_PHOTON_URL", PHOTON_URL) + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return parse_photon(data)


def parse_photon(data):
    out = []
    for feat in (data or {}).get("features", []):
        coords = (feat.get("geometry") or {}).get("coordinates") or []
        props = feat.get("properties") or {}
        if len(coords) < 2:
            continue
        lon, lat = _num(coords[0]), _num(coords[1])
        if lat is None or lon is None:
            continue
        street = " ".join(x for x in (props.get("housenumber"), props.get("street")) if x)
        title = props.get("name") or street or props.get("district") or props.get("city") or props.get("state")
        if not title:
            continue
        parts = []
        for part in (street if props.get("name") else None, props.get("district") or props.get("locality"),
                     props.get("city") or props.get("county"), props.get("state")):
            if part and re.search(r"(^|\s)Ward \d+$", part):   # municipal wards ("Cape Town Ward 59") mean nothing to a rider
                continue
            if part and part != title and part not in parts:
                parts.append(part)
        address = ", ".join(parts[:3])
        label = ", ".join([title] + parts[:2])
        kind = str(props.get("osm_value") or props.get("type") or "place").replace("_", " ")
        if any(_norm(p["name"]) == _norm(title) and haversine_km((p["lat"], p["lon"]), (lat, lon)) < 0.15 for p in out):
            continue
        out.append({"name": title, "label": label, "display_name": ", ".join([title] + parts), "address": address,
                    "kind": kind, "lat": lat, "lon": lon, "search": f"{label} {kind} Photon",
                    "_online_provider": "Photon"})
    return out


# ---- offline places ----------------------------------------------------------------------------------------

class LocalIndex:
    """Word-prefix index over the team's offline place list (82k places): a few milliseconds per query, no
    fuzzy matching (Photon covers typos), so local matches can be shown before the network answers."""

    def __init__(self, places):
        self.rows, self.keys = [], {}
        for place in places:
            lat, lon = _num(place.get("lat")), _num(place.get("lon"))
            label = str(place.get("label") or place.get("name") or "").strip()
            if lat is None or lon is None or not label:
                continue
            norm = _norm(label)
            words = norm.split()
            i = len(self.rows)
            self.rows.append((norm, words, label, place, lat, lon))
            for key in {w[:2] for w in words if len(w) >= 2}:
                self.keys.setdefault(key, []).append(i)

    def search(self, query, near=None, limit=5):
        q = _norm(query)
        tokens = [t for t in q.split() if t]
        if not tokens or len(q) < 2:
            return []
        lead = max(tokens, key=len)
        if len(lead) < 2:
            return []
        found = []
        for i in self.keys.get(lead[:2], ()):
            norm, words, label, place, lat, lon = self.rows[i]
            if norm.startswith(q):
                rank = 0
            elif all(any(w.startswith(t) for w in words) for t in tokens):
                rank = 1
            else:
                continue
            dist = haversine_km(near, (lat, lon)) if near else 0.0
            found.append((rank, dist, len(label), label, place))
        found.sort(key=lambda r: r[:3])
        out, seen = [], set()
        for _rank, _dist, _n, label, place in found:
            if label.lower() in seen:
                continue
            seen.add(label.lower())
            title, _, rest = label.partition(",")
            kind = str(place.get("kind") or "place").replace("_", " ")
            if kind in ("yes", "address", "house", "residential"):
                kind = "address"
            item = dict(place)
            item.update(name=label, label=label, address=(rest.strip() + " · " if rest.strip() else "") + kind.capitalize()
                        + " · offline map", _title=title.strip())
            out.append(item)
            if len(out) >= limit:
                break
        return out


# ---- the rows ----------------------------------------------------------------------------------------------

def _theme(key, fallback):
    try:
        return THEME.color(key)
    except Exception:
        return QColor(fallback)


def _font(size, weight=QFont.Weight.Normal):
    try:
        return THEME.font(size, weight)
    except Exception:
        f = QFont()
        f.setPixelSize(size)
        f.setWeight(weight)
        return f


class SuggestionDelegate(QStyledItemDelegate):
    """Uber-style rows: icon and distance on the left, name in bold over a dimmer address."""

    def sizeHint(self, option, index):
        return QSize(max(100, option.rect.width()), ROW_H.get(index.data(ROLE_KIND), ROW_DEFAULT_H))

    def paint(self, p, option, index):
        kind = index.data(ROLE_KIND) or "result"
        r = option.rect
        text, dim, accent, border = (_theme("text", "#ffffff"), _theme("text_dim", "#aaaaaa"),
                                     _theme("accent", "#80c0ff"), _theme("border", "#444444"))
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pressed = bool(option.state & _STATE_SELECTED) and kind in CHOOSABLE
        if pressed:
            fill = QColor(accent)
            fill.setAlpha(40)
            p.fillRect(r, fill)
        if kind == "header":
            self._paint_header(p, r, index, accent, dim, border)
        elif kind == "status":
            p.setPen(dim)
            p.setFont(_font(14))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, index.data(ROLE_TITLE) or "")
        else:
            left = QRect(r.left(), r.top(), 64, r.height())
            icon_c = QPointF(left.center().x(), r.top() + r.height() * 0.38)
            if kind == "recent":
                self._clock(p, icon_c, dim)
            else:
                self._pin(p, icon_c, accent if kind == "result" else dim)
            p.setPen(dim)
            p.setFont(_font(11))
            p.drawText(QRect(left.left(), int(r.top() + r.height() * 0.62), left.width(), int(r.height() * 0.34)),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, index.data(ROLE_DISTANCE) or "")
            body = QRect(left.right() + 4, r.top(), r.width() - left.width() - 14, r.height())
            title_f, sub_f = _font(16, QFont.Weight.Bold), _font(13)
            p.setFont(title_f)
            p.setPen(text)
            fm = QFontMetrics(title_f)
            p.drawText(QRect(body.left(), r.top() + 7, body.width(), fm.height() + 2),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       fm.elidedText(index.data(ROLE_TITLE) or "", Qt.TextElideMode.ElideRight, body.width()))
            p.setFont(sub_f)
            p.setPen(dim)
            fs = QFontMetrics(sub_f)
            p.drawText(QRect(body.left(), r.top() + 9 + fm.height(), body.width(), fs.height() + 2),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       fs.elidedText(index.data(ROLE_SUBTITLE) or "", Qt.TextElideMode.ElideRight, body.width()))
        p.setPen(QPen(border, 1))
        p.drawLine(r.left() + (0 if kind == "header" else 64), r.bottom(), r.right(), r.bottom())
        p.restore()

    @staticmethod
    def _paint_header(p, r, index, accent, dim, border):
        pos = index.data(ROLE_POSKIND) or "uct"
        c = QPointF(r.left() + 32, r.center().y() + 0.5)
        if pos in ("gps", "simulated"):
            p.setPen(Qt.PenStyle.NoPen)
            halo = QColor(accent)
            halo.setAlpha(60)
            p.setBrush(halo)
            p.drawEllipse(c, 10, 10)
            p.setBrush(accent)
            p.drawEllipse(c, 5.5, 5.5)
        elif pos == "network":
            halo = QColor(accent)
            halo.setAlpha(45)
            p.setBrush(halo)
            p.setPen(QPen(accent, 1.5, Qt.PenStyle.DashLine))
            p.drawEllipse(c, 9, 9)
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(dim, 2))
            p.drawEllipse(c, 6, 6)
        p.setPen(accent if pos in ("gps", "simulated", "network") else dim)
        p.setFont(_font(14, QFont.Weight.DemiBold))
        p.drawText(QRect(r.left() + 64, r.top(), r.width() - 74, r.height()),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, index.data(ROLE_TITLE) or "")

    @staticmethod
    def _clock(p, c, color):
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(color, 2))
        p.drawEllipse(c, 9, 9)
        p.drawLine(c, QPointF(c.x(), c.y() - 5.5))
        p.drawLine(c, QPointF(c.x() + 4.5, c.y() + 2))

    @staticmethod
    def _pin(p, c, color):
        path = QPainterPath()
        top = QPointF(c.x(), c.y() - 4)
        path.addEllipse(top, 7, 7)
        tip = QPainterPath()
        tip.moveTo(c.x() - 6, c.y() - 0.5)
        tip.lineTo(c.x(), c.y() + 10)
        tip.lineTo(c.x() + 6, c.y() - 0.5)
        tip.closeSubpath()
        path = path.united(tip)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(path)
        p.setBrush(_theme("card_alt", "#222222"))
        p.drawEllipse(top, 2.8, 2.8)



# ---- the controller ----------------------------------------------------------------------------------------

class DestinationSearch(QObject):
    _result = Signal(int, str, object)       # token, source, payload (emitted from worker threads)

    def __init__(self, page, fetch=None, recents=None):
        super().__init__(page)
        self.page, self.coordinator = page, page.coordinator
        self.edit, self.list = page.destination, page.suggestions
        self.fetch = fetch or photon_places
        self.recents = recents or Recents()
        self.cache = OrderedDict()
        self.token = 0
        self.query = ""
        self.local, self.online, self.recent_hits = [], None, []
        self.online_failed = False
        self.stale_dropped = 0
        self.timings = []                    # (query, source, seconds) for the tests and the log
        self._sent = {}
        self._index, self._index_md, self._index_lock = None, None, threading.Lock()
        self._net = ThreadPoolExecutor(max_workers=2, thread_name_prefix="sw7-photon")
        self._loc = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sw7-local")
        self._result.connect(self._on_result, Qt.ConnectionType.QueuedConnection)

        self.edit.setPlaceholderText("Where to?")
        lst = self.list
        lst.setItemDelegate(SuggestionDelegate(lst))
        lst.setMaximumHeight(16777215)
        lst.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        lst.setFocusPolicy(Qt.FocusPolicy.NoFocus)      # a tap or drag on the list keeps the field and keyboard
        lst.setStyleSheet("QListWidget { padding: 0px; }")
        lst.setWordWrap(False)
        # Our handlers in front of the team's: destination results and choices come here first.
        try:
            self.coordinator.suggestions_ready.disconnect(page._suggestions_ready)
        except (RuntimeError, TypeError):
            pass
        self.coordinator.suggestions_ready.connect(self._team_suggestions)
        try:
            lst.itemClicked.disconnect(page._choose_suggestion)
        except (RuntimeError, TypeError):
            pass
        lst.itemClicked.connect(self._choose)
        self.coordinator.route_updated.connect(self._route_planned)
        self.edit.textChanged.connect(self._text_changed)
        self.edit.installEventFilter(self)
        page.keyboard.installEventFilter(self)
        self._index_timer = QTimer(self)               # build the offline index as soon as the map has loaded
        self._index_timer.setInterval(1500)
        self._index_timer.timeout.connect(self._prepare_index)
        self._index_timer.start()
        self._prepare_index()

    # -- position ---------------------------------------------------------------------------------------------
    def position(self):
        return current_position(getattr(self.page, "_last_state", None), getattr(self.coordinator, "last_asis_fix", None))

    # -- events -----------------------------------------------------------------------------------------------
    def eventFilter(self, obj, event):
        et = event.type()
        if obj is self.edit:
            if et in (QEvent.Type.FocusIn, QEvent.Type.MouseButtonPress) and not self.edit.text().strip():
                QTimer.singleShot(0, self.show_recents)      # after the keyboard has opened
            elif et == QEvent.Type.FocusOut:
                QTimer.singleShot(150, self._maybe_hide)
        elif obj is self.page.keyboard and et in (QEvent.Type.Show, QEvent.Type.Hide):
            if self.list.isVisible():
                QTimer.singleShot(0, self.page._position_overlays)
        return False

    def _maybe_hide(self):
        if not self.edit.hasFocus():
            self.list.hide()

    def _text_changed(self, text):
        if not text.strip() and self.edit.hasFocus():
            self.show_recents()

    # -- requests ---------------------------------------------------------------------------------------------
    def show_recents(self):
        if self.edit.text().strip():
            return
        self.token += 1
        self.query = ""
        self.local, self.online, self.recent_hits = [], None, list(self.recents.items)
        self._render()

    def request(self, text):
        """Called by the team's debounce timer (120 ms) for the destination field."""
        q = text.strip()
        if not q:
            self.show_recents()
            return
        self.token += 1
        token, self.query = self.token, text
        pos = self.position()
        near = (pos["lat"], pos["lon"])
        nq = _norm(q)
        self.recent_hits = [r for r in self.recents.items if nq and nq in _norm(r["label"])][:3]
        self.local, self.online, self.online_failed = [], None, False
        self._sent[token] = time.monotonic()
        for old in [t for t in self._sent if t < token - 20]:
            del self._sent[old]
        key = (nq, round(near[0], 2), round(near[1], 2))
        if key in self.cache:
            self.cache.move_to_end(key)
            self.online = self.cache[key]
        elif len(nq) < 2:                              # one letter: recents and offline matches only
            self.online = []
        self._render()
        self._loc.submit(self._local_job, token, q, near)
        if self.online is None:
            self._net.submit(self._photon_job, token, q, near, key)

    def _prepare_index(self):
        md = getattr(self.coordinator, "mapdata", None)
        if md is None or not getattr(md, "ok", False) or md is self._index_md:
            return
        self._index_md = md
        self._index_timer.stop()
        self._loc.submit(self._build_index, md)

    def _build_index(self, md):
        with self._index_lock:
            try:
                self._index = LocalIndex(list(getattr(md, "places", None) or []))
            except Exception:
                self._index = None

    def _local_job(self, token, q, near):
        try:
            if self._index is None:
                md = getattr(self.coordinator, "mapdata", None)
                if md is not None and getattr(md, "ok", False):
                    self._index_md = md
                    self._build_index(md)
            places = self._index.search(q, near, 5) if self._index is not None else []
            self._result.emit(token, "local", places)
        except Exception:
            self._result.emit(token, "local", [])

    def _photon_job(self, token, q, near, key):
        if token != self.token:
            return                               # already superseded before it started: do not send it
        try:
            places = self.fetch(q, near)
            self._result.emit(token, "photon", (key, places))
        except Exception as exc:
            self._result.emit(token, "photon_error", str(exc))

    def _on_result(self, token, source, payload):
        if token in self._sent:
            self.timings.append((self.query if token == self.token else "", source, time.monotonic() - self._sent[token]))
        if source == "photon" and payload[1] is not None:
            self.cache[payload[0]] = payload[1]
            while len(self.cache) > CACHE_SIZE:
                self.cache.popitem(last=False)
        if token != self.token:
            self.stale_dropped += 1
            return
        if source == "local":
            self.local = payload
        elif source == "photon":
            self.online = payload[1]
            if not self.online and not self.local:
                self._team_fallback()
        else:
            self.online, self.online_failed = [], True
            self._team_fallback()
        self._render()

    def _team_fallback(self):
        self.coordinator.request_suggestions("destination", self.query)

    def _team_suggestions(self, field, items):
        if field != "destination":
            self.page._suggestions_ready(field, items)
            return
        places = [dict(v) for v in items or [] if isinstance(v, dict) and v.get("_query", self.query) == self.query]
        if not self.query or not places:
            return
        for p in places:
            p.setdefault("address", (p.get("display_name") if p.get("display_name") != p.get("label") else "")
                         or str(p.get("kind") or "place").capitalize())
        self.online = places
        self._render()

    # -- choosing ---------------------------------------------------------------------------------------------
    def _choose(self, item):
        if item is None or item.data(ROLE_KIND) not in CHOOSABLE:
            return
        place = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(place, dict):
            self.recents.add(place)
        self.token += 1                                # answers still on their way must not reopen the list
        self.page._choose_suggestion(item)

    def _route_planned(self, plan):
        dest = getattr(plan, "destination", None) if plan is not None else None
        if isinstance(dest, dict):
            self.recents.add(dest)

    # -- the list ---------------------------------------------------------------------------------------------
    def rows(self):
        """(kind, place) rows to show, header excluded."""
        if not self.query.strip():
            return [("recent", p) for p in self.recent_hits]
        out, taken = [], []

        def fresh(p):
            name = _norm(p.get("_title") or p.get("name") or p.get("label"))
            return not any(name == n and haversine_km((p["lat"], p["lon"]), ll) < 0.3 for n, ll in taken)

        for kind, group in (("recent", self.recent_hits), ("result", self.online or []), ("local", self.local)):
            for p in group:
                if _num(p.get("lat")) is None or _num(p.get("lon")) is None or not fresh(p):
                    continue
                taken.append((_norm(p.get("_title") or p.get("name") or p.get("label")), (p["lat"], p["lon"])))
                out.append((kind, p))
        return out[:12]

    def _render(self):
        self._prepare_index()
        if not self.edit.hasFocus():
            return
        pos = self.position()
        here = (pos["lat"], pos["lon"])
        lst = self.list
        lst.clear()
        header = QListWidgetItem(pos["header"])
        header.setFlags(Qt.ItemFlag.NoItemFlags)
        header.setData(ROLE_KIND, "header")
        header.setData(ROLE_TITLE, pos["header"])
        header.setData(ROLE_POSKIND, pos["kind"])
        lst.addItem(header)
        rows = self.rows()
        for kind, place in rows:
            label = str(place.get("label") or place.get("name"))
            title = place.get("_title") or place.get("name") or label
            if kind == "recent" or title == label:
                title, _, rest = label.partition(",")
                address = place.get("address") or rest.strip()
            else:
                address = place.get("address") or ""
            item = QListWidgetItem(label)
            data = dict(place)
            data["label"] = label
            data["_query"] = self.edit.text()
            data.pop("_title", None)
            item.setData(Qt.ItemDataRole.UserRole, data)
            item.setData(ROLE_KIND, kind)
            item.setData(ROLE_TITLE, title.strip())
            item.setData(ROLE_SUBTITLE, address)
            item.setData(ROLE_DISTANCE, format_distance(haversine_km(here, (float(place["lat"]), float(place["lon"])))))
            lst.addItem(item)
        if not rows:
            if self.query.strip():
                busy = self.online is None
                msg = "Searching…" if busy else "No places found"
            else:
                msg = "Type a place, shop or street"
            status = QListWidgetItem(msg)
            status.setFlags(Qt.ItemFlag.NoItemFlags)
            status.setData(ROLE_KIND, "status")
            status.setData(ROLE_TITLE, msg)
            lst.addItem(status)
        lst.setVisible(True)
        self.page._position_overlays()

    def list_geometry(self):
        """Under the search panel, as wide as it; up to five rows, never under the touch keyboard."""
        page, lst = self.page, self.list
        panel = page.search.geometry()
        top = panel.bottom() + 6
        content = sum(ROW_H.get(lst.item(i).data(ROLE_KIND), ROW_DEFAULT_H)
                      for i in range(min(lst.count(), VISIBLE_ROWS + 1))) + 2
        height = content
        kb = page.keyboard
        if kb.isVisible():
            kb_top = page.stage.mapFromGlobal(kb.mapToGlobal(QPoint(0, 0))).y()
            height = min(height, max(ROW_H["header"] + ROW_DEFAULT_H * 2, kb_top - top - 8))
        height = min(height, max(120, page.stage.height() - top - 12))
        return QRect(panel.left(), top, panel.width(), height)

    def shutdown(self):
        self._net.shutdown(wait=False, cancel_futures=True)
        self._loc.shutdown(wait=False, cancel_futures=True)


def install(page):
    """Called at the end of NavigationPage.__init__ (dashboard_patches.SEARCH_PATCHES)."""
    if not enabled():
        return None
    page._sw7_search = DestinationSearch(page)
    return page._sw7_search
