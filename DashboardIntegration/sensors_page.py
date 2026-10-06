"""
SensorsPage and HazardBanner: every SW-7 sensor reading on one page, and an
alert over any page when something is close.

SensorsPage (nav bar "Sensors") shows, from the Pi 4 bridge's /telemetry:
  - three ToF gauges (left, ahead, right), amber under 1.0 m, red under 0.5 m;
  - the camera and ToF fusion hazards, nearest first;
  - battery (BMS), GPS, motor and ride/link readings.
A missing reading is shown as "--" (or "no reading"), never a made-up value,
and a Live / ESP32 stale / Offline pill (plus REPLAY while the bridge replays
a file) says how far the readings can be trusted.

HazardBanner sits over the top of DashboardMain on every page:
  - red when the fusion reports an "immediate" hazard (fresh data only);
  - amber when the Pi 4 bridge was reachable and has been lost for 5 s.
Tapping it opens the Sensors page; "Hide 30 s" snoozes it. It is not shown
while the Sensors page itself is on screen.

Feed both from LiveDataProvider.telemetry_updated (raw /telemetry dict, or
None when the bridge is unreachable). QtWidgets only, colours from THEME.
"""
from __future__ import annotations

import time

from PySide6.QtCore import QEvent, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QScroller, QScrollerProperties, QVBoxLayout, QWidget,
)

from ..theme import THEME
from ..widgets.ride_quality_card import _num, format_telemetry, replay_of
from ..widgets.themed_surfaces import ThemedCard, ThemedPageSurface

TOF_MAX_M = 1.2          # VL53L1X range used by the fusion (fusion_config.json)
TOF_WARN_M = 1.0
TOF_CRIT_M = 0.5
LINK_LOST_S = 5.0        # banner warns once a live link has been gone this long
SNOOZE_S = 30.0
WATCHDOG_MS = 3000

BAND_STATUS = {"immediate": "crit", "warning": "warn", "monitoring": "normal"}
BAND_TEXT = {"immediate": "Immediate", "warning": "Warning", "monitoring": "Monitoring"}
LINK_TEXT = {"live": ("Live", "normal"), "stale": ("ESP32 stale", "warn"), "offline": ("Offline", "crit")}


def _dict(value):
    return value if isinstance(value, dict) else {}


def tof_status(metres):
    if metres is None:
        return "inactive"
    return "crit" if metres < TOF_CRIT_M else "warn" if metres < TOF_WARN_M else "normal"


def tof_metres(telemetry):
    """{"left"|"ahead"|"right": metres or None} from one /telemetry reply."""
    tof = _dict(_dict(telemetry).get("tof"))
    age = _num(tof.get("age_ms"))
    fresh = age is None or age <= WATCHDOG_MS
    out = {}
    for side in ("left", "ahead", "right"):
        mm = _num(tof.get(f"{side}_mm"))
        out[side] = mm / 1000.0 if fresh and mm is not None and mm > 0 else None
    return out


def direction_of(hazard):
    sensor = hazard.get("sensor")
    if sensor in ("left", "ahead", "right"):
        return sensor
    b = _num(hazard.get("bearing_deg"))
    if b is None:
        return "ahead"
    return "left" if b < -10 else "right" if b > 10 else "ahead"


def hazards_of(telemetry):
    """Fusion hazards, nearest first (unknown distances last)."""
    hz = [h for h in (_dict(_dict(telemetry).get("fusion")).get("hazards") or []) if isinstance(h, dict)]
    return sorted(hz, key=lambda h: (_num(h.get("distance_m")) is None, _num(h.get("distance_m")) or 0.0))


def hazard_text(h):
    d = _num(h.get("distance_m"))
    dist = f"{d:.1f} m" if d is not None else "distance unknown"
    src = {"tof": "ToF", "camera": "camera", "fused": "camera + ToF"}.get(str(h.get("source")), str(h.get("source") or ""))
    return f"{str(h.get('class') or 'object').capitalize()}  {dist} {direction_of(h)}", src


def _fmt(value, pattern, scale=1.0):
    v = _num(value)
    return "--" if v is None else pattern.format(v * scale)


def format_readings(telemetry):
    """{key: (text, status or None)} for the vehicle and position cards."""
    esp = _dict(_dict(telemetry).get("esp32"))
    soc = _num(esp.get("soc"))
    fix = esp.get("fix")
    out = {
        "soc": ("--" if soc is None else f"{soc:.0f} %", None if soc is None else "crit" if soc < 15 else "warn" if soc < 30 else "normal"),
        "v": (_fmt(esp.get("v"), "{:.1f} V"), None),
        "i": (_fmt(esp.get("i"), "{:.1f} A"), None),
        "bms_age": (_fmt(esp.get("bms_age_s"), "{:.0f} s ago"), None),
        "fix": ("--" if fix is None else "Yes" if fix else "No fix", None if fix is None else "normal" if fix else "warn"),
        "pos": ("--" if _num(esp.get("lat")) is None or _num(esp.get("lon")) is None
                else f"{_num(esp.get('lat')):.5f}, {_num(esp.get('lon')):.5f}", None),
        "crs": (_fmt(esp.get("crs"), "{:.0f}°"), None),
        "alt": (_fmt(esp.get("alt"), "{:.0f} m"), None),
        "fw": (str(esp.get("fw") or "--"), None),
    }
    return out


class TofGauge(QWidget):
    """One ToF direction: a bar that fills as an object gets closer, and the distance."""

    def __init__(self, caption, parent=None):
        super().__init__(parent)
        self.caption = caption
        self.metres = None
        self.setMinimumSize(150, 170)
        THEME.changed.connect(self.update)

    def set_metres(self, metres):
        if metres != self.metres:
            self.metres = metres
            self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        status = tof_status(self.metres)
        colour = THEME.color(status)
        p.setPen(QColor(THEME.hex("text_dim")))
        p.setFont(THEME.font(12, QFont.Weight.Bold))
        p.drawText(QRectF(0, 0, w, 22), Qt.AlignmentFlag.AlignCenter, self.caption.upper())
        track = QRectF(w / 2 - 26, 28, 52, h - 74)
        p.setPen(QPen(QColor(THEME.hex("border")), 1.5))
        p.setBrush(QColor(THEME.hex("card_alt")))
        p.drawRoundedRect(track, 10, 10)
        if self.metres is not None:
            close = max(0.0, min(1.0, 1.0 - self.metres / TOF_MAX_M))
            fill = QRectF(track.left() + 4, track.bottom() - 4 - (track.height() - 8) * max(close, 0.04),
                          track.width() - 8, (track.height() - 8) * max(close, 0.04))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(colour)
            p.drawRoundedRect(fill, 7, 7)
        p.setPen(colour if self.metres is not None else QColor(THEME.hex("text_dim")))
        p.setFont(THEME.font(20 if self.metres is not None else 13, QFont.Weight.Black))
        text = "no reading" if self.metres is None else ("> 1.2 m" if self.metres >= TOF_MAX_M else f"{self.metres:.2f} m")
        p.drawText(QRectF(0, h - 42, w, 40), Qt.AlignmentFlag.AlignCenter, text)
        p.end()


class SensorsPage(ThemedPageSurface):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SensorsPage")
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(self.scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        sc = QScroller.scroller(self.scroll.viewport()); props = sc.scrollerProperties()
        props.setScrollMetric(QScrollerProperties.ScrollMetric.MousePressEventDelay, 0.0)   # taps act at once
        sc.setScrollerProperties(props)
        content = QWidget(); content.setObjectName("sensorsContent")
        root = QVBoxLayout(content); root.setContentsMargins(28, 18, 28, 28); root.setSpacing(12)
        self.scroll.setWidget(content); outer.addWidget(self.scroll)

        head = QHBoxLayout()
        title = QLabel("Sensors"); title.setFont(THEME.font(27, QFont.Weight.Black)); head.addWidget(title)
        head.addStretch(1)
        self.replay = QLabel("REPLAY"); self.replay.setFont(THEME.font(12, QFont.Weight.Black)); self.replay.hide()
        self.pill = QLabel(); self.pill.setFont(THEME.font(12, QFont.Weight.Black))
        head.addWidget(self.replay); head.addWidget(self.pill)
        root.addLayout(head)

        around = ThemedCard("accent"); al = QVBoxLayout(around); al.setContentsMargins(18, 14, 18, 14)
        al.addWidget(self._title("AROUND THE TUK-TUK (ToF)"))
        gauges = QHBoxLayout()
        self.gauges = {side: TofGauge(side) for side in ("left", "ahead", "right")}
        for side in ("left", "ahead", "right"):
            gauges.addWidget(self.gauges[side])
        al.addLayout(gauges)
        root.addWidget(around)

        hz = ThemedCard("accent"); self.hz_layout = QVBoxLayout(hz); self.hz_layout.setContentsMargins(18, 14, 18, 14)
        self.hz_layout.addWidget(self._title("HAZARDS (CAMERA + ToF)"))
        self.hz_box = QVBoxLayout(); self.hz_layout.addLayout(self.hz_box)
        root.addWidget(hz)

        self.values = {}
        root.addWidget(self._grid_card("VEHICLE", (("soc", "Battery"), ("v", "Voltage"), ("i", "Current"),
                                                   ("bms_age", "BMS reading"), ("rpm", "Motor"))))
        root.addWidget(self._grid_card("POSITION", (("fix", "GPS fix"), ("pos", "Lat, lon"), ("crs", "Heading"),
                                                    ("alt", "Altitude"), ("spd_raw", "GNSS speed (raw)"))))
        root.addWidget(self._grid_card("RIDE AND LINK", (("vib", "Vibration"), ("vib_dis", "IMU disagreement"),
                                                         ("imu_hz", "IMU rate"), ("drops", "IMU drops"), ("csq", "Signal"),
                                                         ("mqtt", "MQTT"), ("age", "ESP32 age"), ("fw", "Firmware"))))
        root.addStretch(1)

        self._last_hz = None
        self._watchdog = QTimer(self); self._watchdog.setSingleShot(True)
        self._watchdog.timeout.connect(lambda: self.set_telemetry(None))
        THEME.changed.connect(self._theme); self._theme()
        self.set_telemetry(None)

    @staticmethod
    def _title(text):
        label = QLabel(text); label.setObjectName("sectionTitle"); label.setFont(THEME.font(11, QFont.Weight.Black))
        return label

    def _grid_card(self, title, fields):
        card = ThemedCard("accent"); g = QGridLayout(card); g.setContentsMargins(18, 14, 18, 14)
        g.setHorizontalSpacing(18); g.setVerticalSpacing(4)
        g.addWidget(self._title(title), 0, 0, 1, 4)
        for n, (key, caption) in enumerate(fields):
            r, c = 1 + (n // 4) * 2, n % 4
            cap = QLabel(caption); cap.setObjectName("dim"); cap.setFont(THEME.font(11))
            val = QLabel("--"); val.setFont(THEME.font(18, QFont.Weight.Bold))
            g.addWidget(cap, r, c); g.addWidget(val, r + 1, c)
            self.values[key] = val
        return card

    def set_telemetry(self, telemetry):
        link, ride = format_telemetry(telemetry)
        readings = dict(ride); readings.update(format_readings(telemetry))
        for key, label in self.values.items():
            text, status = readings.get(key, ("--", None))
            label.setText(text)
            label.setStyleSheet(f"color: {THEME.color(status).name() if status else THEME.hex('text')}; background: transparent;")
        text, status = LINK_TEXT.get(link, LINK_TEXT["offline"])
        self.pill.setText(text)
        self.pill.setStyleSheet(f"color: #000; background: {THEME.color(status).name()}; border-radius: 10px; padding: 4px 12px;")
        replaying, _ = replay_of(telemetry)
        self.replay.setVisible(replaying)
        tof = tof_metres(telemetry)
        for side, gauge in self.gauges.items():
            gauge.set_metres(tof.get(side))
        self._render_hazards(hazards_of(telemetry), link)
        if telemetry is not None:
            self._watchdog.start(WATCHDOG_MS)

    def _render_hazards(self, hazards, link):
        key = (link, tuple((hazard_text(h), h.get("band")) for h in hazards))
        if key == self._last_hz:
            return
        self._last_hz = key
        while self.hz_box.count():
            w = self.hz_box.takeAt(0).widget()
            if w is not None:
                w.hide(); w.setParent(None); w.deleteLater()
        if not hazards:
            none = QLabel("No sensor data" if link == "offline" else "No hazards")
            none.setObjectName("dim"); none.setFont(THEME.font(15))
            self.hz_box.addWidget(none)
            return
        for h in hazards[:8]:
            text, src = hazard_text(h)
            band = h.get("band")
            row = QLabel(f"{text}    {BAND_TEXT.get(band, band or '')}    ({src})")
            row.setFont(THEME.font(16, QFont.Weight.Bold))
            row.setStyleSheet(f"color: #000; background: {THEME.color(BAND_STATUS.get(band, 'inactive')).name()};"
                              " border-radius: 8px; padding: 8px 10px;")
            self.hz_box.addWidget(row)

    def update_state(self, state):
        """The bridge feeds this page directly (set_telemetry)."""

    def _theme(self):
        self.setStyleSheet(f"""
        SensorsPage, QWidget#sensorsContent {{ background: transparent; }}
        QLabel {{ background: transparent; color: {THEME.hex('text')}; }}
        QLabel#dim {{ color: {THEME.hex('text_dim')}; }}
        QLabel#sectionTitle {{ color: {THEME.hex('accent')}; letter-spacing: 1px; }}
        QScrollArea {{ background: transparent; border: none; }}
        """)
        self.replay.setStyleSheet(f"color: #000; background: {THEME.color('warn').name()}; border-radius: 10px; padding: 4px 12px;")


class HazardBanner(QFrame):
    """Alert strip over the top of its parent. open_sensors is emitted on tap."""
    open_sensors = Signal()

    def __init__(self, parent, is_sensors_page_shown=lambda: False):
        super().__init__(parent)
        self._shown_check = is_sensors_page_shown
        self._snooze_until = 0.0
        self._was_live = False
        self._lost_since = None
        self._message = None
        row = QHBoxLayout(self); row.setContentsMargins(16, 6, 8, 6); row.setSpacing(10)
        self.text = QPushButton(); self.text.setFlat(True); self.text.setFont(THEME.font(17, QFont.Weight.Black))
        self.text.setCursor(Qt.CursorShape.PointingHandCursor)
        self.text.clicked.connect(self._open)
        self.hide_btn = QPushButton("Hide 30 s"); self.hide_btn.setFont(THEME.font(12, QFont.Weight.Bold))
        self.hide_btn.clicked.connect(self._snooze)
        row.addWidget(self.text, 1); row.addWidget(self.hide_btn)
        parent.installEventFilter(self)
        self._recheck = QTimer(self); self._recheck.timeout.connect(self._refresh); self._recheck.start(500)
        self.hide()

    def eventFilter(self, obj, event):
        if obj is self.parent() and event.type() == QEvent.Type.Resize:
            self._place()
        return False

    def _place(self):
        pw = self.parent().width()
        w = min(900, pw - 120)
        self.setGeometry(int((pw - w) / 2), 10, int(w), 58)

    def set_telemetry(self, telemetry):
        link, _ = format_telemetry(telemetry)
        now = time.monotonic()
        message = None
        if link != "offline":
            self._was_live, self._lost_since = True, None
            urgent = [h for h in hazards_of(telemetry) if h.get("band") == "immediate"]
            if urgent:
                text, _src = hazard_text(urgent[0])
                more = f"  (+{len(urgent) - 1} more)" if len(urgent) > 1 else ""
                message = ("crit", f"⚠  {text.upper()}{more}   ·   tap for sensors")
        elif self._was_live:
            self._lost_since = self._lost_since or now
            if now - self._lost_since >= LINK_LOST_S:
                message = ("warn", "Sensor link lost: readings not updating   ·   tap for sensors")
        self._message = message
        self._refresh()

    def _refresh(self):
        show = self._message is not None and time.monotonic() >= self._snooze_until and not self._shown_check()
        if show:
            status, text = self._message
            colour = THEME.color(status).name()
            fg = "#fff" if status == "crit" else "#000"
            self.setStyleSheet(f"HazardBanner {{ background: {colour}; border-radius: 12px; }}"
                               f" QPushButton {{ color: {fg}; background: transparent; border: none; text-align: left; }}"
                               f" QPushButton#hide {{ border: 1px solid {fg}; border-radius: 8px; padding: 6px 10px; }}")
            self.hide_btn.setObjectName("hide")
            self.text.setText(text)
            self._place(); self.show(); self.raise_()
        else:
            self.hide()

    def _open(self):
        self.hide()
        self.open_sensors.emit()

    def _snooze(self):
        self._snooze_until = time.monotonic() + SNOOZE_S
        self.hide()
