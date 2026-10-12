"""SW-7 weather: Open-Meteo forecast for the status bar, the charcoal weather card and the night variant.

Planning/paper-depth-theme-prompt.md section 6. Installed as app/widgets/sw7_weather.py; sw7_style.install wires it
into the dashboard in the paper style (install(main)). The service itself has no UI and can be used on its own.

- Forecast: https://api.open-meteo.com/v1/forecast (no key): current temperature, weather code, wind and is_day,
  13 hours of hourly temperature and code, today's and tomorrow's sunrise and sunset (timezone=auto).
- Place name: Photon reverse geocoding (photon.komoot.io/reverse, the same OSM service as the search), the suburb
  ("Rondebosch"); "UCT" when the position is the UCT fallback and no name could be fetched.
- Position: the GPS fix (or the last one), then the modem's network position (sw7_cell_position), then UCT
  (-33.9577, 18.4612). Simulated-drive positions are never used.
- Refresh every 15 min, at once after moving more than 5 km, 3 min after a failure. Each fetch runs on a worker
  thread with a 6 s timeout; the result comes back to the UI thread through a queued signal.
- Disk cache (~/.cache/sw7_weather/last.json, or TUKZIE_WEATHER_CACHE) with the fetch time, so it works offline and
  shows its age ("updated 12 min ago"). With no network and no cache it shows "--" and never a made-up value.
- Sunrise and sunset drive sw7_style.set_night (the Ink variant at night).
Env: TUKZIE_WEATHER_URL and TUKZIE_REVERSE_URL (the tests point them at a local fake server), TUKZIE_WEATHER_CACHE.
"""
from __future__ import annotations

import calendar
import json
import math
import os
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QPushButton, QWidget

from . import sw7_style as S

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REVERSE_URL = "https://photon.komoot.io/reverse"
USER_AGENT = "TUKZIE-SW7-dashboard/1.0 (UCT student project)"
UCT = (-33.9577, 18.4612)
REFRESH_S = 15 * 60
RETRY_S = 3 * 60
MOVE_KM = 5.0
TIMEOUT_S = 6.0
CACHE_MAX_AGE_S = 24 * 3600          # an older cache is not shown at all
HOUR_STEP = 3                         # the card's columns: now, +3 h, +6 h, +9 h, +12 h

# WMO weather codes -> (word, icon kind)
CODES = [((0,), "Clear", "clear"), ((1,), "Mostly clear", "partly"), ((2,), "Partly cloudy", "partly"),
         ((3,), "Overcast", "cloud"), ((45, 48), "Fog", "fog"), (tuple(range(51, 58)), "Drizzle", "rain"),
         (tuple(range(61, 68)), "Rain", "rain"), (tuple(range(71, 78)), "Snow", "snow"),
         ((80, 81, 82), "Showers", "rain"), ((85, 86), "Snow showers", "snow"), ((95, 96, 99), "Thunderstorm", "storm")]


def describe_code(code):
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "", "none"
    for codes, word, kind in CODES:
        if code in codes:
            return word, kind
    return "", "cloud"


def haversine_km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(min(1.0, h)))


def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _epoch(local_iso, offset_s):
    """'2026-10-12T14:00' in the station's local time -> epoch seconds."""
    dt = datetime.fromisoformat(str(local_iso))
    return calendar.timegm(dt.timetuple()) - int(offset_s or 0)


def cache_path() -> Path:
    override = os.environ.get("TUKZIE_WEATHER_CACHE", "").strip()
    return Path(override) if override else Path.home() / ".cache" / "sw7_weather" / "last.json"


class WeatherReport:
    """One parsed forecast. source: "live" (just fetched) or "cached" (from disk)."""

    def __init__(self, data, fetched_at, place="", position=None, kind="", source="live"):
        self.raw = data
        self.fetched_at = float(fetched_at)
        self.place = place or ""
        self.position = position
        self.position_kind = kind
        self.source = source
        off = data.get("utc_offset_seconds", 0) or 0
        cur = data.get("current") or {}
        self.temp_c = _num(cur.get("temperature_2m"))
        self.code = cur.get("weather_code")
        self.wind_kmh = _num(cur.get("wind_speed_10m"))
        self.is_day = bool(cur.get("is_day", 1))
        self.condition, self.kind = describe_code(self.code)
        hourly = data.get("hourly") or {}
        times = hourly.get("time") or []
        temps = hourly.get("temperature_2m") or []
        codes = hourly.get("weather_code") or []
        self.hourly = []
        for i, t in enumerate(times):
            try:
                self.hourly.append((_epoch(t, off), str(t)[11:16], _num(temps[i]) if i < len(temps) else None,
                                    codes[i] if i < len(codes) else None))
            except (ValueError, TypeError):
                continue
        daily = data.get("daily") or {}
        self.days = []
        for rise, sset in zip(daily.get("sunrise") or [], daily.get("sunset") or []):
            try:
                self.days.append((_epoch(rise, off), _epoch(sset, off)))
            except (ValueError, TypeError):
                continue
        if self.temp_c is None:
            raise ValueError("forecast without a current temperature")

    def age_s(self, now=None):
        return max(0.0, (now or time.time()) - self.fetched_at)

    def age_text(self, now=None):
        age = self.age_s(now)
        if age < 90:
            return "updated just now"
        if age < 3600:
            return f"updated {int(round(age / 60))} min ago"
        return f"updated {int(age // 3600)} h ago"

    def is_night(self, now=None):
        """Between sunset and the next sunrise. None if the days are not known."""
        now = now or time.time()
        if not self.days:
            return None
        for rise, sset in self.days:
            if rise <= now < sset:
                return False
        return True

    def columns(self, now=None, n=5, step=HOUR_STEP):
        """[(label, temp, code, is_day)]: Now, then every step hours."""
        now = now or time.time()
        out = [("Now", self.temp_c, self.code, self.is_day)]
        future = [h for h in self.hourly if h[0] > now + 1800]
        if not future:
            return out
        for k in range(1, n):
            target = now + k * step * 3600
            best = min(future, key=lambda h: abs(h[0] - target))
            if abs(best[0] - target) > 3600:
                break
            day = self.is_night(best[0])
            out.append((best[1], best[2], best[3], True if day is None else not day))
        return out

    def short(self):
        return f"{self.temp_c:.0f}°"

    def status_text(self):
        """'☀ 24° Rondebosch' (the icon as a character, for logs and the accessible name)."""
        glyph = {"clear": "☀" if self.is_day else "☾", "partly": "⛅", "cloud": "☁", "fog": "≡", "rain": "☂",
                 "snow": "❄", "storm": "ϟ"}.get(self.kind, "·")
        return f"{glyph} {self.short()} {self.place}".strip()


def position_of(state, last_fix=None):
    """(lat, lon, kind): GPS fix, the last fix, the network position, then UCT."""
    if state is not None and not getattr(state, "sw7_simulated", False):
        lat, lon = _num(getattr(state, "latitude", None)), _num(getattr(state, "longitude", None))
        if lat is not None and lon is not None and bool((getattr(state, "signal_validity", None) or {}).get("gps", True)):
            return lat, lon, "gps"
    if last_fix:
        return last_fix[0], last_fix[1], "gps"
    cell = getattr(state, "sw7_cell_position", None) if state is not None else None
    if cell and len(cell) >= 2 and _num(cell[0]) is not None and _num(cell[1]) is not None:
        return float(cell[0]), float(cell[1]), "network"
    return UCT[0], UCT[1], "uct"


def fetch_forecast(lat, lon, timeout=TIMEOUT_S):
    params = {"latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}",
              "current": "temperature_2m,weather_code,wind_speed_10m,is_day",
              "hourly": "temperature_2m,weather_code", "forecast_hours": 13,
              "daily": "sunrise,sunset", "forecast_days": 2, "timezone": "auto"}
    url = os.environ.get("TUKZIE_WEATHER_URL", FORECAST_URL) + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_place(lat, lon, timeout=TIMEOUT_S):
    url = os.environ.get("TUKZIE_REVERSE_URL", REVERSE_URL) + "?" + urllib.parse.urlencode(
        {"lat": f"{lat:.5f}", "lon": f"{lon:.5f}", "limit": 1})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    for feat in data.get("features") or []:
        pr = feat.get("properties") or {}
        for key in ("district", "locality", "suburb", "city", "name"):
            if str(pr.get(key) or "").strip():
                return str(pr[key]).strip()
    return ""


class WeatherService(QObject):
    """updated(report or None). report is the latest WeatherReport (live or cached), None if there is none."""
    updated = Signal(object)
    _done = Signal(object)

    def __init__(self, parent=None, autostart=True, drive_night=True):
        super().__init__(parent)
        self.report = None
        self.state = None
        self.last_fix = None
        self.fetch_pos = None          # where the last attempt asked for
        self.last_attempt = 0.0
        self.busy = False
        self.failures = 0
        self.requests = 0
        self.drive_night = drive_night
        self._done.connect(self._on_done, Qt.ConnectionType.QueuedConnection)
        self.timer = QTimer(self); self.timer.setSingleShot(True); self.timer.timeout.connect(self.refresh)
        self.night_timer = QTimer(self); self.night_timer.setInterval(60_000); self.night_timer.timeout.connect(self._apply_night)
        self._load_cache()
        if autostart:
            QTimer.singleShot(0, self.refresh)
            self.night_timer.start()

    # position --------------------------------------------------------------------------------------------------------
    def update_state(self, state):
        if state is None or getattr(state, "sw7_simulated", False):
            return
        self.state = state
        lat, lon, kind = position_of(state)
        if kind == "gps":
            self.last_fix = (lat, lon)
        if self.fetch_pos is not None and not self.busy and haversine_km(self.fetch_pos[:2], (lat, lon)) > MOVE_KM \
                and time.time() - self.last_attempt > 60:
            self.refresh()

    def position(self):
        return position_of(self.state, self.last_fix)

    # fetching ----------------------------------------------------------------------------------------------------------
    def refresh(self):
        if self.busy:
            return
        lat, lon, kind = self.position()
        place = None
        if self.report is not None and self.report.position and self.report.place \
                and haversine_km(self.report.position[:2], (lat, lon)) < 2.0:
            place = self.report.place
        self.busy = True
        self.last_attempt = time.time()
        self.fetch_pos = (lat, lon, kind)
        self.requests += 1
        threading.Thread(target=self._work, args=(lat, lon, kind, place), daemon=True, name="sw7-weather").start()

    def _work(self, lat, lon, kind, place):
        try:
            data = fetch_forecast(lat, lon)
            if place is None:
                try:
                    place = fetch_place(lat, lon)
                except Exception:
                    place = ""
            if not place and kind == "uct":
                place = "UCT"
            self._done.emit({"ok": True, "data": data, "place": place, "pos": (lat, lon), "kind": kind,
                             "at": time.time()})
        except Exception as exc:
            self._done.emit({"ok": False, "error": str(exc)})

    def _on_done(self, res):
        self.busy = False
        if res.get("ok"):
            try:
                rep = WeatherReport(res["data"], res["at"], res["place"], res["pos"], res["kind"], "live")
            except Exception as exc:
                res = {"ok": False, "error": f"bad forecast: {exc}"}
            else:
                self.report = rep
                self.failures = 0
                self._save_cache(res)
                self.timer.start(REFRESH_S * 1000)
                self._apply_night()
                self.updated.emit(rep)
                return
        self.failures += 1
        self.last_error = res.get("error")
        if self.report is not None and self.report.source == "live":
            self.report.source = "cached"       # what is shown is now older than the last try
        self.timer.start(RETRY_S * 1000)
        self.updated.emit(self.report)

    # cache --------------------------------------------------------------------------------------------------------------
    def _save_cache(self, res):
        path = cache_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"fetched_at": res["at"], "place": res["place"], "pos": list(res["pos"]),
                                       "kind": res["kind"], "data": res["data"]}), encoding="utf-8")
            os.replace(tmp, path)
        except Exception:
            pass

    def _load_cache(self):
        try:
            c = json.loads(cache_path().read_text(encoding="utf-8"))
            if time.time() - float(c["fetched_at"]) > CACHE_MAX_AGE_S:
                return
            self.report = WeatherReport(c["data"], c["fetched_at"], c.get("place", ""), tuple(c.get("pos") or ()) or None,
                                        c.get("kind", ""), "cached")
        except Exception:
            self.report = None
            return
        self._apply_night()

    # night ----------------------------------------------------------------------------------------------------------------
    def _apply_night(self):
        if not self.drive_night or self.report is None:
            return
        night = self.report.is_night()
        if night is not None:
            S.set_night(night)


# ---- icons ---------------------------------------------------------------------------------------------------------------
def paint_icon(p, rect, kind, is_day=True, main=None, second=None):
    """A weather icon in rect, line style. main: the sun or main colour; second: cloud and rain colour."""
    from PySide6.QtGui import QColor
    main = QColor(main or S.c("warn")); second = QColor(second or S.c("ink_2"))
    r = QRectF(rect); s = min(r.width(), r.height())
    cx, cy = r.center().x(), r.center().y()
    p.save(); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    lw = max(1.6, s * 0.075)

    def sun(x, y, rad, col):
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(col); p.drawEllipse(QPointF(x, y), rad, rad)
        p.setPen(QPen(col, lw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for k in range(8):
            a = k * math.pi / 4
            p.drawLine(QPointF(x + math.cos(a) * rad * 1.45, y + math.sin(a) * rad * 1.45),
                       QPointF(x + math.cos(a) * rad * 1.9, y + math.sin(a) * rad * 1.9))

    def moon(x, y, rad, col):
        path = QPainterPath(); path.addEllipse(QPointF(x, y), rad, rad)
        cut = QPainterPath(); cut.addEllipse(QPointF(x + rad * 0.55, y - rad * 0.35), rad * 0.9, rad * 0.9)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(col); p.drawPath(path.subtracted(cut))

    def cloud(x, y, w, col, fill=True):
        path = QPainterPath()
        h = w * 0.42
        path.addRoundedRect(QRectF(x - w / 2, y - h * 0.15, w, h * 0.65), h * 0.32, h * 0.32)
        path.addEllipse(QPointF(x - w * 0.16, y - h * 0.12), w * 0.22, w * 0.22)
        path.addEllipse(QPointF(x + w * 0.14, y - h * 0.28), w * 0.27, w * 0.27)
        path = path.simplified()
        if fill:
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(col)
        else:
            p.setPen(QPen(col, lw)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

    if kind == "clear":
        (sun if is_day else moon)(cx, cy, s * 0.22 if is_day else s * 0.32, main)
    elif kind == "partly":
        (sun if is_day else moon)(cx - s * 0.12, cy - s * 0.12, s * 0.17 if is_day else s * 0.24, main)
        cloud(cx + s * 0.06, cy + s * 0.12, s * 0.66, second)
    elif kind in ("cloud", "fog", "rain", "snow", "storm"):
        cloud(cx, cy - (s * 0.08 if kind != "cloud" else 0), s * 0.78, second)
        p.setPen(QPen(second, lw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        base = cy + s * 0.22
        if kind == "fog":
            for k in range(2):
                p.drawLine(QPointF(cx - s * 0.32, base + k * s * 0.12), QPointF(cx + s * 0.32, base + k * s * 0.12))
        elif kind == "rain":
            for k in (-1, 0, 1):
                p.drawLine(QPointF(cx + k * s * 0.18, base), QPointF(cx + k * s * 0.18 - s * 0.06, base + s * 0.18))
        elif kind == "snow":
            for k in (-1, 0, 1):
                p.drawPoint(QPointF(cx + k * s * 0.18, base + s * 0.08))
        elif kind == "storm":
            p.setPen(QPen(main, lw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawPolyline([QPointF(cx + s * 0.04, base - s * 0.04), QPointF(cx - s * 0.08, base + s * 0.12),
                            QPointF(cx + s * 0.06, base + s * 0.12), QPointF(cx - s * 0.06, base + s * 0.28)])
    else:
        p.setPen(QPen(second, lw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(cx - s * 0.2, cy), QPointF(cx + s * 0.2, cy))
    p.restore()


# ---- status-bar chip -------------------------------------------------------------------------------------------------------
class WeatherChip(QPushButton):
    """The status-bar weather item, unboxed (Planning/ui-theme-refinement-prompt.md, item 5): a small icon, then
    "24° · Rondebosch" inline with the other indicators. No box, pill, border or fill; the whole item (44 px tall,
    with padding) is still the tap target that opens the weather card. Unavailable: "--°" and the fallback place."""
    H = 36
    ICON = 20
    GAP = 8
    PAD = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sw7WeatherChip")
        self.setCheckable(False); self.setFlat(True); self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)
        self.report = None
        self.place_fallback = "UCT"
        self.setStyleSheet("QPushButton#sw7WeatherChip{background:transparent;border:none;padding:0px;}")
        S.mark_quiet(self)                 # an indicator that opens a detail: ink, not signal
        self.set_report(None)

    def temp_text(self):
        return self.report.short() if self.report is not None else "--°"

    def place_text(self):
        if self.report is not None:
            return self.report.place
        return self.place_fallback

    def summary(self):
        return self.report.status_text() if self.report is not None else f"-- {self.place_fallback}".strip()

    def _fonts(self):
        return S.font(S.BODY, QFont.Weight.Medium), S.font(S.BODY)

    def parts(self):
        """(temperature, separator, place) as painted."""
        place = self.place_text()
        return self.temp_text(), (" · " if place else ""), place

    def set_report(self, report):
        self.report = report
        self.setText("")                   # painted; the words are in the accessible name
        self.setAccessibleName(self.summary()); self.setToolTip(self.summary())
        f1, f2 = self._fonts()
        t, sep, place = self.parts()
        w = self.PAD + self.ICON + self.GAP + QFontMetrics(f1).horizontalAdvance(t)
        if place:
            w += QFontMetrics(f2).horizontalAdvance(sep + place)
        self.setFixedWidth(w + self.PAD)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        if self.isDown():                  # touch feedback only while pressed
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(S.c("signal_tint"))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(2, 4, -2, -4), S.RADIUS_SM, S.RADIUS_SM)
        kind = self.report.kind if self.report is not None else "none"
        day = self.report.is_day if self.report is not None else True
        cy = self.height() / 2
        paint_icon(p, QRectF(self.PAD, cy - self.ICON / 2, self.ICON, self.ICON), kind, day, S.c("warn"), S.c("ink_2"))
        x = self.PAD + self.ICON + self.GAP
        f1, f2 = self._fonts()
        t, sep, place = self.parts()
        AL = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        p.setFont(f1); p.setPen(S.c("ink") if self.report is not None else S.c("ink_3"))
        p.drawText(QRectF(x, 0, 200, self.height()), AL, t)
        x += QFontMetrics(f1).horizontalAdvance(t)
        if place:
            p.setFont(f2); p.setPen(S.c("ink_2"))
            p.drawText(QRectF(x, 0, 400, self.height()), AL, sep + place)
        p.end()


# ---- the charcoal weather card ------------------------------------------------------------------------------------------------
class _Scrim(QWidget):
    """Dims the page under the card and paints the card's shadow (so the card itself is exactly the card); a tap
    anywhere outside the card closes it."""

    def __init__(self, parent, on_tap):
        super().__init__(parent)
        self.on_tap = on_tap
        self.card_rect = None
        self.setObjectName("sw7WeatherScrim")
        S.mark_tappable(self, False)

    def paintEvent(self, _e):
        p = QPainter(self); p.fillRect(self.rect(), S.c("paper", 110 if not S.is_night() else 150))
        if self.card_rect is not None:
            S.paint_shadow(p, QRectF(self.card_rect), WeatherCard.RADIUS, 3)
        p.end()

    def mousePressEvent(self, e):
        e.accept(); self.on_tap()


class WeatherCard(QWidget):
    """The inverse card of the reference: charcoal, hero temperature, five columns, 'updated N min ago'."""
    W, H = 620, 432
    RADIUS = 8
    PAD = 36
    CLOSE_W, CLOSE_H = 132, 64
    HERO_PX = 132

    def __init__(self, main):
        host = main.centralWidget()
        self.scrim = _Scrim(host, self.close_card)
        super().__init__(host)
        self.main = main
        self.setObjectName("sw7WeatherCard")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.report = None
        self.setFixedSize(self.W, self.H)
        self.close_btn = QPushButton("Close", self)
        self.close_btn.setObjectName("sw7WeatherClose")
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # closing must not hand focus to a text field
        self.close_btn.setFixedSize(self.CLOSE_W, self.CLOSE_H)
        self.close_btn.move(self.W - 24 - self.CLOSE_W, self.H - 24 - self.CLOSE_H)
        self.close_btn.clicked.connect(self.close_card)
        self.age_timer = QTimer(self); self.age_timer.setInterval(30_000); self.age_timer.timeout.connect(self.update)
        self._theme()
        self.scrim.hide(); self.hide()

    def _theme(self):
        self.close_btn.setFont(S.font(S.BODY, QFont.Weight.Bold))
        self.close_btn.setStyleSheet(S.button_qss("filled", self.CLOSE_H // 2, S.BODY, "QPushButton#sw7WeatherClose"))
        self.update(); self.scrim.update()

    def set_report(self, report):
        self.report = report
        self.update()

    def place(self):
        host = self.parentWidget()
        status = getattr(self.main, "status", None)
        top = status.height() if status is not None else 48
        self.scrim.setGeometry(0, top, host.width(), host.height() - top)
        self.move(16, top + 12)
        self.scrim.card_rect = self.geometry().translated(0, -top)

    def open_card(self):
        self.place()
        self.scrim.show(); self.scrim.raise_()
        self.show(); self.raise_()
        self.age_timer.start()

    def close_card(self):
        self.age_timer.stop()
        self.hide(); self.scrim.hide()

    def paintEvent(self, _e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        card = QRectF(self.rect())
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(S.c("charcoal")); p.drawRoundedRect(card, self.RADIUS, self.RADIUS)
        fg, fg2 = S.c("on_charcoal"), S.c("on_charcoal_2")
        rep = self.report
        L, R = self.PAD, card.width() - self.PAD
        top = 28
        AL = Qt.AlignmentFlag
        # label row: the place, in small caps
        p.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True)); p.setPen(fg2)
        place = (rep.place if rep is not None and rep.place else "") or "Weather"
        p.drawText(QRectF(L, top, 400, 20), AL.AlignLeft | AL.AlignVCenter, place.upper())
        # the hero temperature
        hero = S.font(self.HERO_PX, QFont.Weight.Bold)
        p.setFont(hero); p.setPen(fg)
        hero_text = f"{rep.temp_c:.0f}°" if rep is not None else "--"
        fm = QFontMetrics(hero)
        p.drawText(QPointF(L - 6, top + fm.ascent()), hero_text)
        hero_w = fm.horizontalAdvance(hero_text)
        # icon and words beside it
        ix = L + hero_w + 24
        kind = rep.kind if rep is not None else "none"
        paint_icon(p, QRectF(ix, top + 36, 80, 80), kind, rep.is_day if rep is not None else True, S.c("warn"), fg2)
        p.setFont(S.font(S.SECONDARY, QFont.Weight.Bold)); p.setPen(fg)
        word = (rep.condition if rep is not None else "No weather data") or ""
        p.drawText(QRectF(ix, top + 124, R - ix, 30), AL.AlignLeft | AL.AlignVCenter, word)
        p.setFont(S.font(S.BODY)); p.setPen(fg2)
        if rep is None:
            sub = "No network and no saved forecast"
        else:
            sub = f"Wind {rep.wind_kmh:.0f} km/h" if rep.wind_kmh is not None else ""
        p.drawText(QRectF(ix, top + 154, R - ix, 24), AL.AlignLeft | AL.AlignVCenter, sub)
        # hairline and five columns
        y0 = top + 200
        p.setPen(QPen(S.c("on_charcoal_2", 70), 1)); p.drawLine(QPointF(L, y0), QPointF(R, y0))
        cols = rep.columns() if rep is not None else []
        cw = (R - L) / 5
        for i in range(5):
            x = L + i * cw
            label, temp, code, day = cols[i] if i < len(cols) else ("", None, None, True)
            if rep is None or not label:
                continue
            p.setFont(S.mono(S.LABEL)); p.setPen(fg2)                  # a time: Plex Mono
            p.drawText(QRectF(x, y0 + 16, cw, 18), AL.AlignHCenter, label)
            _w, k = describe_code(code)
            paint_icon(p, QRectF(x + cw / 2 - 17, y0 + 42, 34, 34), k, day, S.c("warn"), fg2)
            p.setFont(S.font(S.SECONDARY, QFont.Weight.Medium)); p.setPen(fg)
            p.drawText(QRectF(x, y0 + 82, cw, 30), AL.AlignHCenter, f"{temp:.0f}°" if temp is not None else "--")
        # footer: the age of what is shown, beside Close
        p.setFont(S.font(S.LABEL)); p.setPen(fg2)
        foot = self.footer_text()
        p.drawText(QRectF(L, card.height() - 24 - self.CLOSE_H, R - L - self.CLOSE_W, self.CLOSE_H),
                   AL.AlignLeft | AL.AlignVCenter, foot)
        p.end()

    def footer_text(self):
        rep = self.report
        if rep is None:
            return "--"
        return rep.age_text() + (" · offline" if rep.source == "cached" else "") + " · Open-Meteo"

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.close_card()
        else:
            super().keyPressEvent(e)


# ---- wiring -----------------------------------------------------------------------------------------------------------------
def install(main):
    """The chip in place of the status bar's weather text, the card, and the service fed from the live state."""
    from ..theme import THEME
    bar = main.status
    bar.weather.hide()
    chip = WeatherChip(bar)
    grid = bar.layout()
    grid.addWidget(chip, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    bar.sw7_weather_chip = chip
    card = WeatherCard(main)
    main.sw7_weather_card = card
    service = WeatherService(main)
    main.sw7_weather = service

    def on_report(rep):
        chip.set_report(rep); card.set_report(rep)
    service.updated.connect(on_report)
    on_report(service.report)
    chip.clicked.connect(lambda: card.close_card() if card.isVisible() else card.open_card())
    THEME.changed.connect(lambda: (card._theme(), chip.update()))

    def on_state(state):
        live = getattr(main, "_sw7_live_state", None) or state
        service.update_state(live)
        if service.report is None:
            fallback = "UCT" if service.position()[2] == "uct" else ""
            if fallback != chip.place_fallback:
                chip.place_fallback = fallback
                chip.set_report(None)
    if hasattr(main, "state_updated"):
        main.state_updated.connect(on_state)
    return service
