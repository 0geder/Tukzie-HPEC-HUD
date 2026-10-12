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

Layout (TUKZIE_SW7_LAYOUT, default on; Planning/layout-improvements-prompt.md): in place of the three
52 px gauges, a tuk-tuk outline seen from above with the left, ahead and right distances in 40 px by
their sensors, each zone in its band colour with a word under it; the hazards list beside it in 64 px
rows; the vehicle, position and ride cards below, smaller. TUKZIE_SW7_LAYOUT=0 gives the earlier page
exactly. The HazardBanner (obstacle pill) is the same in both.
"""
from __future__ import annotations

import os
import time

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
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


def _position_text(esp):
    """GNSS position, else the mobile-network estimate marked as approximate (firmware 0.7.3+)."""
    lat, lon = _num(esp.get("lat")), _num(esp.get("lon"))
    if lat is not None and lon is not None:
        return f"{lat:.5f}, {lon:.5f}", None
    clat, clon, acc = _num(esp.get("cell_lat")), _num(esp.get("cell_lon")), _num(esp.get("cell_acc_m"))
    if clat is not None and clon is not None:
        return f"{clat:.4f}, {clon:.4f} (network, ±{acc:.0f} m)" if acc else f"{clat:.4f}, {clon:.4f} (network)", "warn"
    return "--", None


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
        "pos": _position_text(esp),
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


def layout_on():
    """SW-7 layout pass (TUKZIE_SW7_LAYOUT, default on); 0 keeps the earlier layout exactly."""
    return os.environ.get("TUKZIE_SW7_LAYOUT", "1").strip() != "0"


ZONE_WORD = {"crit": "Very close", "warn": "Close", "normal": "Clear", "inactive": "No reading"}


def zone_text(metres):
    """(distance text, word under it) for one ToF zone."""
    if metres is None:
        return "--", ZONE_WORD["inactive"]
    if metres >= TOF_MAX_M:
        return "Clear", f"over {TOF_MAX_M:.1f} m"
    return f"{metres:.2f} m", ZONE_WORD[tof_status(metres)]


class TukTukView(QWidget):
    """A tuk-tuk outline seen from above (front up: one front wheel, two at the back) with the three ToF
    zones round it. Each zone is a wedge from its sensor, as long as the free space (full length when
    clear), filled in its band colour; its distance is printed in 40 px bold next to it, with the side
    above and a word under it, so the colour is never the only signal."""
    BASE_W, BASE_H = 520, 414
    SIDES = ("left", "ahead", "right")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.metres = {side: None for side in self.SIDES}
        self.setMinimumSize(self.BASE_W, self.BASE_H)
        THEME.changed.connect(self.update)

    def set_metres(self, side, metres):
        if self.metres.get(side) != metres:
            self.metres[side] = metres
            self.update()

    def geometry_of(self):
        """Body rectangle, the three sensor points and the three text boxes, in widget coordinates."""
        w, h = self.width(), self.height()
        cx, oy = w / 2, max(0.0, (h - self.BASE_H) / 2)
        bw, bl = 112, 196
        nose_y = oy + 182
        body = QRectF(cx - bw / 2, nose_y, bw, bl)
        sensors = {"ahead": QPointF(cx, nose_y), "left": QPointF(cx - bw / 2, nose_y + 88),
                   "right": QPointF(cx + bw / 2, nose_y + 88)}
        side_w = cx - bw / 2 - 24
        text = {"ahead": QRectF(cx - 130, oy, 260, 88),
                "left": QRectF(0, nose_y + 138, side_w, 88),
                "right": QRectF(w - side_w, nose_y + 138, side_w, 88)}
        return body, sensors, text

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body, sensors, text = self.geometry_of()
        r_min, r_max = 26.0, 84.0
        heading = {"ahead": 90.0, "left": 180.0, "right": 0.0}       # degrees, Qt angles (anticlockwise from east)
        for side in self.SIDES:
            m = self.metres[side]
            status = tof_status(m)
            colour = THEME.color(status)
            centre = sensors[side]
            frac = 1.0 if m is None else max(0.0, min(1.0, m / TOF_MAX_M))
            r = r_min + (r_max - r_min) * frac
            box = QRectF(centre.x() - r, centre.y() - r, 2 * r, 2 * r)
            fill = QColor(colour); fill.setAlpha(70 if m is not None else 30)
            path = QPainterPath(centre); path.arcTo(box, heading[side] - 28, 56); path.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(fill); p.drawPath(path)
            pen = QPen(colour, 8 if m is not None else 3, Qt.PenStyle.SolidLine if m is not None else Qt.PenStyle.DashLine)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(box, int((heading[side] - 28) * 16), int(56 * 16))
        # body: narrow front, wide back, roof panel, three wheels
        bw, x0, y0 = body.width(), body.left(), body.top()
        shell = QPainterPath()
        shell.moveTo(x0 + bw * 0.28, y0)
        shell.lineTo(x0 + bw * 0.72, y0)
        shell.quadTo(x0 + bw * 0.92, y0 + 10, x0 + bw, y0 + 76)
        shell.lineTo(x0 + bw, body.bottom() - 14)
        shell.quadTo(x0 + bw, body.bottom(), x0 + bw - 14, body.bottom())
        shell.lineTo(x0 + 14, body.bottom())
        shell.quadTo(x0, body.bottom(), x0, body.bottom() - 14)
        shell.lineTo(x0, y0 + 76)
        shell.quadTo(x0 + bw * 0.08, y0 + 10, x0 + bw * 0.28, y0)
        wheel = QColor(THEME.hex("text_dim"))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(wheel)
        for wx in (x0 - 12, body.right() - 8):
            p.drawRoundedRect(QRectF(wx, body.bottom() - 70, 20, 46), 6, 6)
        p.setPen(QPen(QColor(THEME.hex("text_dim")), 3)); p.setBrush(QColor(THEME.hex("card_alt")))
        p.drawPath(shell)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(wheel)                 # the front wheel, under the nose
        p.drawRoundedRect(QRectF(body.center().x() - 9, y0 + 14, 18, 40), 6, 6)
        p.setPen(QPen(QColor(THEME.hex("border")), 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(x0 + 16, y0 + 84, bw - 32, body.height() - 100), 10, 10)
        p.drawLine(QPointF(x0 + bw * 0.22, y0 + 64), QPointF(x0 + bw * 0.78, y0 + 64))   # windscreen
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(THEME.hex("accent")))
        for side in self.SIDES:
            p.drawEllipse(sensors[side], 6, 6)
        # distances
        for side in self.SIDES:
            m = self.metres[side]
            value, word = zone_text(m)
            colour = THEME.color(tof_status(m)) if m is not None else QColor(THEME.hex("text_dim"))
            box = text[side]
            p.setPen(QColor(THEME.hex("text_dim"))); p.setFont(THEME.font(16, QFont.Weight.Bold))
            p.drawText(QRectF(box.left(), box.top(), box.width(), 20), Qt.AlignmentFlag.AlignCenter, side.upper())
            p.setPen(colour); p.setFont(THEME.font(40, QFont.Weight.Black))
            p.drawText(QRectF(box.left(), box.top() + 18, box.width(), 50), Qt.AlignmentFlag.AlignCenter, value)
            p.setPen(colour if m is not None else QColor(THEME.hex("text_dim"))); p.setFont(THEME.font(16, QFont.Weight.Bold))
            p.drawText(QRectF(box.left(), box.top() + 68, box.width(), 20), Qt.AlignmentFlag.AlignCenter, word)
        p.end()


class SensorsPage(ThemedPageSurface):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SensorsPage")
        self._layout = layout_on()
        if self._layout:
            self._build_layout()
        else:
            self._build_classic()
        self._last_hz = None
        self._watchdog = QTimer(self); self._watchdog.setSingleShot(True)
        self._watchdog.timeout.connect(lambda: self.set_telemetry(None))
        THEME.changed.connect(self._theme); self._theme()
        self.set_telemetry(None)

    def _build_layout(self):
        """Tuk-tuk outline and hazards above the fold; vehicle, position and ride cards below, smaller."""
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(self.scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        sc = QScroller.scroller(self.scroll.viewport()); props = sc.scrollerProperties()
        props.setScrollMetric(QScrollerProperties.ScrollMetric.MousePressEventDelay, 0.0)   # taps act at once
        sc.setScrollerProperties(props)
        content = QWidget(); content.setObjectName("sensorsContent")
        root = QVBoxLayout(content); root.setContentsMargins(24, 16, 24, 24); root.setSpacing(16)
        self.scroll.setWidget(content); outer.addWidget(self.scroll)

        head = QHBoxLayout(); head.setSpacing(12)
        title = QLabel("Sensors"); title.setFont(THEME.font(24, QFont.Weight.Bold)); head.addWidget(title)
        head.addStretch(1)
        self.replay = QLabel("REPLAY"); self.replay.setFont(THEME.font(16, QFont.Weight.Bold)); self.replay.hide()
        self.pill = QLabel(); self.pill.setFont(THEME.font(16, QFont.Weight.Bold))
        for chip in (self.replay, self.pill):
            chip.setFixedSize(120, 36); chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        head.addWidget(self.replay); head.addWidget(self.pill)
        root.addLayout(head)

        top = QHBoxLayout(); top.setSpacing(16)
        around = ThemedCard("accent"); al = QVBoxLayout(around); al.setContentsMargins(16, 14, 16, 14); al.setSpacing(8)
        al.addWidget(self._title("AROUND THE TUK-TUK (ToF)"))
        self.tuk = TukTukView(); al.addWidget(self.tuk, 1)
        legend = QLabel(f"Amber under {TOF_WARN_M:.1f} m · red under {TOF_CRIT_M:.1f} m · sensors reach {TOF_MAX_M:.1f} m")
        legend.setObjectName("dim"); legend.setFont(THEME.font(16)); legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        al.addWidget(legend)
        top.addWidget(around, 0)

        hz = ThemedCard("accent"); self.hz_layout = QVBoxLayout(hz); self.hz_layout.setContentsMargins(16, 14, 16, 14)
        self.hz_layout.setSpacing(8)
        self.hz_layout.addWidget(self._title("HAZARDS (CAMERA + ToF)"))
        self.hz_box = QVBoxLayout(); self.hz_box.setSpacing(8); self.hz_layout.addLayout(self.hz_box)
        self.hz_layout.addStretch(1)
        top.addWidget(hz, 1)
        root.addLayout(top)

        self.values = {}
        lower = QHBoxLayout(); lower.setSpacing(16)
        lower.addWidget(self._grid_card("VEHICLE", (("soc", "Battery"), ("v", "Voltage"), ("i", "Current"),
                                                    ("bms_age", "BMS reading"), ("rpm", "Motor")), cols=2), 1)
        lower.addWidget(self._grid_card("POSITION", (("fix", "GPS fix"), ("crs", "Heading"), ("pos", "Lat, lon"),
                                                     ("alt", "Altitude"), ("spd_raw", "GNSS speed (raw)")), cols=2,
                                        wide=("pos",)), 1)
        lower.addWidget(self._grid_card("RIDE AND LINK", (("vib", "Vibration"), ("vib_dis", "IMU disagreement"),
                                                          ("imu_hz", "IMU rate"), ("drops", "IMU drops"), ("csq", "Signal"),
                                                          ("mqtt", "MQTT"), ("age", "ESP32 age"), ("fw", "Firmware")),
                                        cols=2), 1)
        root.addLayout(lower)
        root.addStretch(1)

    def _build_classic(self):
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

    def _title(self, text):
        label = QLabel(text); label.setObjectName("sectionTitle")
        label.setFont(THEME.font(14 if self._layout else 11, QFont.Weight.Black))
        return label

    def _grid_card(self, title, fields, cols=4, wide=()):
        """A card of caption/value pairs, cols per row; keys in wide take a whole row (layout mode only)."""
        card = ThemedCard("accent"); g = QGridLayout(card); g.setContentsMargins(18, 14, 18, 14)
        g.setHorizontalSpacing(18); g.setVerticalSpacing(4)
        g.addWidget(self._title(title), 0, 0, 1, cols)
        if not self._layout:
            for n, (key, caption) in enumerate(fields):
                r, c = 1 + (n // 4) * 2, n % 4
                cap = QLabel(caption); cap.setObjectName("dim"); cap.setFont(THEME.font(11))
                val = QLabel("--"); val.setFont(THEME.font(18, QFont.Weight.Bold))
                g.addWidget(cap, r, c); g.addWidget(val, r + 1, c)
                self.values[key] = val
            return card
        r, c = 1, 0
        for key, caption in fields:
            span = cols if key in wide else 1
            if c + span > cols:
                r, c = r + 2, 0
            cap = QLabel(caption); cap.setObjectName("dim"); cap.setFont(THEME.font(14))
            val = QLabel("--"); val.setFont(THEME.font(18, QFont.Weight.Bold))
            g.addWidget(cap, r, c, 1, span); g.addWidget(val, r + 1, c, 1, span)
            self.values[key] = val
            c += span
            if c >= cols:
                r, c = r + 2, 0
        for col in range(cols):
            g.setColumnStretch(col, 1)
        g.setRowStretch(r + 2, 1)
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
        if self._layout:                          # the same style as the source chip, fixed 120 x 36
            self.pill.setStyleSheet(f"color: #0B0D10; background: {THEME.color(status).name()}; border-radius: 8px;")
        else:
            self.pill.setStyleSheet(f"color: #000; background: {THEME.color(status).name()}; border-radius: 10px; padding: 4px 12px;")
        replaying, _ = replay_of(telemetry)
        self.replay.setVisible(replaying)
        tof = tof_metres(telemetry)
        if self._layout:
            for side in TukTukView.SIDES:
                self.tuk.set_metres(side, tof.get(side))
        else:
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
        if self._layout:
            self._render_hazard_rows(hazards, link)
            return
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

    def _render_hazard_rows(self, hazards, link):
        """64 px rows like the camera page, nearest first; the top one filled when immediate or warning."""
        from .front_camera_page import FILLED, AlertRow
        if not hazards:
            none = QLabel("No sensor data" if link == "offline" else "No hazards")
            none.setObjectName("dim"); none.setFont(THEME.font(20))
            none.setAlignment(Qt.AlignmentFlag.AlignCenter); none.setMinimumHeight(64)
            self.hz_box.addWidget(none)
            return
        for n, h in enumerate(hazards[:5]):
            _text, src = hazard_text(h)
            d = _num(h.get("distance_m"))
            # two decimals inside the ToF range, as on the outline (0.45 m, not 0.5 m next to a red zone)
            dist = "distance unknown" if d is None else f"{d:.2f} m" if d < TOF_MAX_M else f"{d:.1f} m"
            band = h.get("band")
            status = BAND_STATUS.get(band, "inactive")
            detail = " · ".join(t for t in (BAND_TEXT.get(band, band or ""), src) if t)
            main = f"{str(h.get('class') or 'object').capitalize()} {dist} {direction_of(h)}"
            self.hz_box.addWidget(AlertRow(status, main, detail,
                                           filled=(n == 0 and status in FILLED)))
        if len(hazards) > 5:
            more = QLabel(f"+{len(hazards) - 5} more, nearest shown first")
            more.setObjectName("dim"); more.setFont(THEME.font(16))
            self.hz_box.addWidget(more)

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
        if self._layout:
            self.replay.setStyleSheet(f"color: #0B0D10; background: {THEME.color('warn').name()}; border-radius: 8px;")
        else:
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
        # A compact pill tucked into the right of the status bar, left of the clock (student, 11 Oct): the earlier
        # centred 900 px banner covered the status bar and the top of every page.
        row = QHBoxLayout(self); row.setContentsMargins(12, 0, 4, 0); row.setSpacing(6)
        self.text = QPushButton(); self.text.setFlat(True); self.text.setFont(THEME.font(13, QFont.Weight.Black))
        self.text.setCursor(Qt.CursorShape.PointingHandCursor)
        self.text.clicked.connect(self._open)
        self.hide_btn = QPushButton("Hide"); self.hide_btn.setFont(THEME.font(12 if __import__("os").environ.get("TUKZIE_SW7_LAYOUT", "1").strip() != "0" else 10, QFont.Weight.Bold))
        self.hide_btn.clicked.connect(self._snooze)
        row.addWidget(self.text, 1); row.addWidget(self.hide_btn)
        parent.installEventFilter(self)
        bar = getattr(parent, "status", None)
        if bar is not None:
            bar.installEventFilter(self)   # _place reads the bar's height, so follow it when it changes (38 or 48 px)
        self._recheck = QTimer(self); self._recheck.timeout.connect(self._refresh); self._recheck.start(500)
        self.hide()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize and (obj is self.parent() or obj is getattr(self.parent(), "status", None)):
            self._place()
        return False

    def _place(self):
        """Right-hand side of the status bar, left of the date and clock, so no page content is covered."""
        parent = self.parent()
        pw = parent.width()
        bar = getattr(parent, "status", None)
        bar_h = bar.height() if bar is not None and bar.height() > 0 else 38
        from os import environ
        layout = environ.get("TUKZIE_SW7_LAYOUT", "1").strip() != "0"
        h = max(24, min(40, bar_h - 8)) if layout else max(24, min(32, bar_h - 6))   # 40 px in the 48 px bar
        w = min(460, max(200, self.sizeHint().width()))
        clock_w = 110 if layout else 190   # the layout pass shows the clock alone, the earlier bar date and clock
        self.setGeometry(int(max(8, pw - clock_w - w)), int((bar_h - h) / 2), int(w), int(h))

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
                message = ("crit", f"{text.upper()}{more}")   # no symbol: the bundled font has no warning glyph; tap opens Sensors
        elif self._was_live:
            self._lost_since = self._lost_since or now
            if now - self._lost_since >= LINK_LOST_S:
                message = ("warn", "Sensor link lost")
        self._message = message
        self._refresh()

    def sw7_paper(self):
        """Paper and depth style (sw7_style, called by the frame): a charcoal pill with a status dot and white text;
        Hide is the only signal-coloured thing in it. Position and size stay as in the layout pass."""
        from PySide6.QtWidgets import QLabel
        from ..widgets import sw7_style as S
        self._paper = S
        self.dot = QLabel(self); self.dot.setFixedSize(12, 12)
        self.dot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.layout().insertWidget(0, self.dot)
        self.layout().setContentsMargins(16, 0, 6, 0); self.layout().setSpacing(10)
        self.text.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True))
        self.hide_btn.setFont(S.font(S.LABEL, QFont.Weight.Bold))
        self.hide_btn.setFixedHeight(28); self.hide_btn.setObjectName("hide")
        S.mark_exempt(self.text, "the alert text opens Sensors; the brief keeps the pill charcoal with Hide as its control")
        S.elevate(self, 1)
        THEME.changed.connect(self._refresh)
        self._refresh()

    def _refresh(self):
        show = self._message is not None and time.monotonic() >= self._snooze_until and not self._shown_check()
        if show and getattr(self, "_paper", None) is not None:
            S = self._paper
            status, text = self._message
            h = 40
            self.setStyleSheet(f"HazardBanner {{ background: {S.hx('charcoal')}; border-radius: {h // 2}px; }}"
                               f" QPushButton {{ color: {S.hx('on_charcoal')}; background: transparent; border: none;"
                               f" text-align: left; padding: 0px; }}"
                               f" QPushButton#hide {{ background: {S.hx('signal')}; color: {S.hx('card')};"
                               f" border-radius: 14px; padding: 0px 14px; }}"
                               f" QPushButton#hide:pressed {{ background: {S.hx('signal_pressed')}; }}")
            self.dot.setStyleSheet(f"background: {S.hx('critical' if status == 'crit' else 'warn')}; border-radius: 6px;")
            self.hide_btn.setObjectName("hide")
            self.text.setText(text)
            self._place(); self.show(); self.raise_()
            return
        if show:
            status, text = self._message
            # Fixed banner colours from Research/DashboardDesign, the same in both themes:
            # white on deep red (7.6:1) for critical, near-black on amber (10.8:1) for warning.
            colour, fg = {"crit": ("#A3201A", "#FFFFFF"), "warn": ("#FFB224", "#0B0D10")}[status]
            self.setStyleSheet(f"HazardBanner {{ background: {colour}; border-radius: 9px; }}"
                               f" QPushButton {{ color: {fg}; background: transparent; border: none; text-align: left; }}"
                               f" QPushButton#hide {{ border: 1px solid {fg}; border-radius: 6px; padding: 1px 6px; }}")
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
