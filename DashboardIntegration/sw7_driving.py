"""
SW7DrivePanel: the centre of the Driving page in the SW-7 theme (TUKZIE_SW7_THEME, on by default).

Replaces the team's 0 to 50 dial and the brake and accelerator bars (the vehicle has no pedal
sensors, so those bars could only ever show "--") with three values a driver can read in one
glance, sized from Research/DashboardDesign for a 10.1-inch 1280 x 800 panel at about 70 cm:

  - speed as a large number, capital height about 120 px (about 100 arc minutes);
  - battery state of charge and range as two tiles, values about 48 px high, labels about 24 px
    (ISO 15008's 20 arc minutes recommended is about 24 px at that distance).

A value with no live source is shown as "--", never as 0 (live-only mode). Battery colour follows
the theme's status colours: red under 15 %, amber under 30 %, otherwise green, and the value is
always printed, so colour is never the only cue.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..theme import THEME

SPEED_PX = 170      # font pixel size; capital height about 120 px in Atkinson Hyperlegible
VALUE_PX = 72       # about 48 px capitals
LABEL_PX = 34       # about 24 px capitals


def _num(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


class SW7DrivePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.speed = None
        self.soc = None
        self.range_km = None
        self.setMinimumSize(560, 420)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        THEME.changed.connect(self.update)

    def set_state(self, s):
        valid = getattr(s, "signal_validity", None) or {}
        self.speed = None if valid.get("speed") is False else _num(getattr(s, "speed_kmh", None))
        self.soc = None if valid.get("soc") is False else _num(getattr(s, "soc_pct", None))
        self.range_km = _num(getattr(s, "range_km", None)) if self.soc is not None else None
        self.update()

    def _font(self, px, weight=QFont.Weight.Bold):
        f = THEME.font(px, weight)
        f.setPixelSize(px)
        return f

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        text, dim = QColor(THEME.hex("text")), QColor(THEME.hex("text_dim"))

        # speed
        speed_h = min(h * 0.52, SPEED_PX * 1.15)
        p.setPen(text)
        p.setFont(self._font(SPEED_PX, QFont.Weight.Bold))
        speed = "--" if self.speed is None else f"{self.speed:.0f}"
        p.drawText(QRectF(0, 0, w, speed_h), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, speed)
        p.setPen(dim)
        p.setFont(self._font(LABEL_PX, QFont.Weight.Normal))
        unit_y = speed_h - p.fontMetrics().descent() * 0 - SPEED_PX * 0.16   # tuck the unit under the digits
        p.drawText(QRectF(0, unit_y, w, LABEL_PX * 1.4), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "km/h")

        # battery and range tiles
        top = speed_h - SPEED_PX * 0.16 + LABEL_PX * 1.9
        tile_h = max(150.0, min(190.0, h - top - 8))
        gap = 24
        tile_w = min(360.0, (w - gap) / 2)
        x0 = (w - (2 * tile_w + gap)) / 2
        soc_status = None if self.soc is None else ("crit" if self.soc < 15 else "warn" if self.soc < 30 else "normal")
        tiles = (
            ("BATTERY", "--" if self.soc is None else f"{self.soc:.0f} %", soc_status, self.soc),
            ("RANGE", "--" if self.range_km is None else f"{self.range_km:.0f} km", None, None),
        )
        for i, (label, value, status, fill) in enumerate(tiles):
            r = QRectF(x0 + i * (tile_w + gap), top, tile_w, tile_h)
            p.setPen(QPen(QColor(THEME.hex("border")), 1.2))
            p.setBrush(QColor(THEME.hex("card")))
            p.drawRoundedRect(r, 12, 12)
            p.setPen(dim)
            p.setFont(self._font(LABEL_PX, QFont.Weight.Bold))
            p.drawText(r.adjusted(22, 14, -22, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, label)
            p.setPen(THEME.status(status) if status else text)
            p.setFont(self._font(VALUE_PX, QFont.Weight.Bold))
            p.drawText(r.adjusted(22, LABEL_PX * 1.5, -22, -30), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, value)
            if fill is not None:                      # battery bar along the bottom of the tile
                bar = QRectF(r.left() + 22, r.bottom() - 26, r.width() - 44, 10)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(THEME.hex("track")))
                p.drawRoundedRect(bar, 5, 5)
                p.setBrush(THEME.status(status))
                p.drawRoundedRect(QRectF(bar.left(), bar.top(), bar.width() * max(0.0, min(1.0, fill / 100.0)), bar.height()), 5, 5)
        p.end()


# ---- layout pass (12 Oct 2026, Planning/google-stitch-dashboard-prompt.md 3.2) --------------------------------
# For the team look (TUKZIE_SW7_THEME=0, the deployed setting). Behind TUKZIE_SW7_LAYOUT (default on);
# TUKZIE_SW7_LAYOUT=0 leaves the team's Driving page exactly as it was. Only sizes, order and spacing change:
# the same widgets, colours, dial style and fonts.
#   - advice strip: the ASIS card becomes a 64 px strip across the page, 22 px text, coloured left edge;
#   - speed: a whole number at 140 px with "km/h" at 24 px, inside the same 0 to 50 dial (drawn larger);
#   - range and battery: a pair under the dial, values 36 px bold, labels 18 px;
#   - brake and accelerator: short bars (24 x 300 px track) beside the dial, value 18 px;
#   - the route line 16 px instead of 11 px, the interlock warning 16 px instead of 10 px.
import os

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from ..asis.config import VEHICLE_SPEC

LAYOUT_SPEED_PX = 140
LAYOUT_UNIT_PX = 24
LAYOUT_VALUE_PX = 36
LAYOUT_LABEL_PX = 18
LAYOUT_STRIP_H = 64
LAYOUT_STRIP_PX = 22
LAYOUT_PEDAL_TRACK = (24, 300)
LAYOUT_PEDAL_VALUE_PX = 18
LAYOUT_ROUTE_PX = 16
LAYOUT_MARGIN = 24
NORMAL_TEXT = "Route and vehicle conditions normal"


def layout_enabled():
    return os.environ.get("TUKZIE_SW7_LAYOUT", "1").strip() != "0"


def _layout_speedometer_class(base):
    """The team's Speedometer, drawn as large as the space allows, with a 140 px whole-number speed."""

    class LayoutSpeedometer(base):
        SPEED_PX = LAYOUT_SPEED_PX
        UNIT_PX = LAYOUT_UNIT_PX

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setMinimumSize(300, 260)
            self.setMaximumWidth(560)
            self.sw7_fonts = {}

        def paintEvent(self, _):
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            pad = 10.0
            # the dial is a 270 degree arc open at the bottom: it needs 2r across and about 1.72r down
            r = max(60.0, min((self.width() - 2 * pad) / 2.0, (self.height() - 2 * pad) / 1.72, 250.0))
            side = r / 0.41                                   # the team's proportions (r = 0.41 x side)
            cx = self.width() / 2.0
            cy = pad + r + max(0.0, (self.height() - 2 * pad - 1.72 * r) / 2.0)
            start, span = 135.0, 270.0
            arc = QRectF(cx - r, cy - r, 2 * r, 2 * r)
            p.setPen(QPen(THEME.color('track'), max(7, side * .028), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(arc, int(-start * 16), int(-span * 16))
            p.setPen(QPen(THEME.color('accent'), max(5, side * .021), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(arc, int(-start * 16), int(-span * (self.speed / 50.0) * 16))
            tick_px = max(12, int(side * .032))
            for v in range(51):
                a = start + span * v / 50.0
                major = v % 5 == 0
                q1 = self._point(cx, cy, r * (.86 if major else .91), a)
                q2 = self._point(cx, cy, r * .98, a)
                p.setPen(QPen(THEME.color('text_dim') if major else THEME.color('text_faint'), 2.2 if major else .75))
                p.drawLine(q1, q2)
                if major and v % 10 == 0:                  # numbers every 10 km/h, clear of the big speed
                    t = self._point(cx, cy, r * .75, a)
                    p.setFont(THEME.font(tick_px, QFont.Weight.Medium))
                    p.setPen(THEME.color('text_dim'))
                    p.drawText(QRectF(t.x() - 22, t.y() - 11, 44, 22), Qt.AlignmentFlag.AlignCenter, str(v))
            cap = float(VEHICLE_SPEC.max_speed_kmh)
            a = start + span * cap / 50.0
            p.setPen(QPen(THEME.status('warn'), max(3, side * .009)))
            p.drawLine(self._point(cx, cy, r * .82, a), self._point(cx, cy, r * 1.02, a))
            if self.recommended is not None:
                rec = max(0.0, min(50.0, float(self.recommended)))
                a = start + span * rec / 50.0
                p.setPen(QPen(THEME.status('normal'), max(3, side * .009)))
                p.drawLine(self._point(cx, cy, r * .80, a), self._point(cx, cy, r * 1.01, a))
            speed_px = int(min(self.SPEED_PX, r * 0.80))
            known = getattr(self, 'speed_known', True)
            p.setPen(THEME.color('text'))
            p.setFont(THEME.font(speed_px, QFont.Weight.Black))
            num = QRectF(cx - r, cy - speed_px * 0.62, 2 * r, speed_px * 1.05)
            shown = f'{self.speed:.0f}' if known else '--'
            p.drawText(num, Qt.AlignmentFlag.AlignCenter, shown)
            p.setPen(THEME.color('text_dim'))
            p.setFont(THEME.font(self.UNIT_PX, QFont.Weight.Medium))
            p.drawText(QRectF(cx - r, num.bottom(), 2 * r, self.UNIT_PX * 1.4), Qt.AlignmentFlag.AlignCenter, 'km/h')
            self.sw7_fonts = {"speed": speed_px, "unit": self.UNIT_PX, "ticks": tick_px, "radius": r, "text": shown}
            p.end()

    return LayoutSpeedometer


def _layout_pedal_class(base):
    """The team's PedalBar with a short 24 x 300 px track and an 18 px value."""

    class LayoutPedalBar(base):
        def __init__(self, title, status, parent=None):
            super().__init__(title, status, parent)
            self.setMinimumSize(76, 180)
            self.setMaximumSize(76, LAYOUT_PEDAL_TRACK[1] + 60)
            self.sw7_fonts = {}

        def sizeHint(self):
            return QSize(76, LAYOUT_PEDAL_TRACK[1] + 60)

        def paintEvent(self, _):
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            tw = float(LAYOUT_PEDAL_TRACK[0])
            th = max(60.0, min(float(LAYOUT_PEDAL_TRACK[1]), h - 56.0))
            x, top = (w - tw) / 2.0, max(4.0, (h - 56.0 - th) / 2.0)
            p.setPen(QPen(THEME.color('border'), 2))
            p.setBrush(THEME.color('card_alt'))
            p.drawRoundedRect(QRectF(x, top, tw, th), 8, 8)
            fill = th * self.value
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(THEME.status(self.status))
            p.drawRoundedRect(QRectF(x, top + th - fill, tw, fill), 7, 7)
            p.setPen(THEME.color('text'))
            p.setFont(THEME.font(LAYOUT_PEDAL_VALUE_PX, QFont.Weight.Black))
            p.drawText(QRectF(0, top + th + 4, w, 26), Qt.AlignmentFlag.AlignCenter,
                       f'{self.value * 100:.0f}%' if getattr(self, 'known', True) else '--')
            p.setPen(THEME.color('text_dim'))
            p.setFont(THEME.font(14, QFont.Weight.Bold))
            p.drawText(QRectF(0, top + th + 30, w, 20), Qt.AlignmentFlag.AlignCenter, self.title)
            self.sw7_fonts = {"value": LAYOUT_PEDAL_VALUE_PX, "label": 14, "track": (tw, th)}
            p.end()

    return LayoutPedalBar


class RangeBatteryPair(QWidget):
    """Range and battery under the dial: values 36 px bold, labels 18 px under them. "--" when unknown."""

    def __init__(self, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(96)
        row.addStretch(1)
        self.values, self.labels = {}, {}
        for key, label in (("range", "RANGE"), ("battery", "BATTERY")):
            col = QVBoxLayout()
            col.setSpacing(0)
            v, l = QLabel("--"), QLabel(label)
            v.setFont(THEME.font(LAYOUT_VALUE_PX, QFont.Weight.Bold))
            l.setFont(THEME.font(LAYOUT_LABEL_PX, QFont.Weight.DemiBold))
            for w in (v, l):
                w.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                col.addWidget(w)
            self.values[key], self.labels[key] = v, l
            row.addLayout(col)
        row.addStretch(1)
        self._soc_status = None
        THEME.changed.connect(self._colours)
        self._colours()

    def set_state(self, s):
        valid = getattr(s, "signal_validity", None) or {}
        soc = None if valid.get("soc") is False else _num(getattr(s, "soc_pct", None))
        rng = _num(getattr(s, "range_km", None))
        if rng is not None:
            rng = min(float(VEHICLE_SPEC.rated_max_range_km), rng)
        self.values["range"].setText("--" if rng is None else f"{rng:.1f} km")
        self.values["battery"].setText("--" if soc is None else f"{soc:.0f} %")
        self._soc_status = None if soc is None else ("crit" if soc < 15 else "warn" if soc < 30 else "normal")
        self._colours()

    def _colours(self):
        text, dim = THEME.hex("text"), THEME.hex("text_dim")
        bat = THEME.status(self._soc_status).name() if self._soc_status else text
        self.values["range"].setStyleSheet(f"background: transparent; color: {text};")
        self.values["battery"].setStyleSheet(f"background: transparent; color: {bat};")
        for l in self.labels.values():
            l.setStyleSheet(f"background: transparent; color: {dim};")


def _make_advice_strip(panel):
    """Turn the team's ASIS card into a full-width strip: one 64 px row, 22 px text, coloured left edge."""
    root = panel.layout()
    head = None
    while root.count():
        item = root.takeAt(0)
        if item.layout() is not None:
            head = item.layout()
    if head is not None:                                  # free the heading and count from their old row
        while head.count():
            head.takeAt(0)
        head.setParent(None)
    root.setContentsMargins(20, 4, 16, 4)
    row = QHBoxLayout()
    row.setSpacing(16)
    panel.heading.setFont(THEME.font(16, QFont.Weight.Black))
    panel.line1.setFont(THEME.font(LAYOUT_STRIP_PX, QFont.Weight.Bold))
    panel.line2.setFont(THEME.font(16, QFont.Weight.Medium))
    panel.count.setFont(THEME.font(14, QFont.Weight.Bold))
    panel.line1.setWordWrap(True)
    panel.line2.setWordWrap(True)
    panel.line2.setMaximumWidth(380)
    for w in (panel.heading, panel.line1, panel.line2, panel.count):
        w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    row.addWidget(panel.heading, 0)
    row.addWidget(panel.line1, 1)
    row.addWidget(panel.line2, 0)
    row.addWidget(panel.count, 0)
    root.addLayout(row)
    panel.setMinimumWidth(0)
    panel.setMaximumWidth(16777215)
    panel.setFixedHeight(LAYOUT_STRIP_H)
    policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    policy.setRetainSizeWhenHidden(True)                 # the dial does not jump when the strip hides
    panel.setSizePolicy(policy)
    team_theme = panel._apply_theme

    def apply_theme():
        team_theme()
        sev = panel.property("severity") or "normal"
        key = {"critical": "crit", "warning": "warn", "advice": "accent", "info": "info"}.get(sev, "normal")
        edge = THEME.color("accent") if key == "accent" else THEME.status(key)
        panel.setStyleSheet(f"""
            QFrame#asisAdvisoryPanel {{
                background: {THEME.hex('card')};
                border: 1px solid {THEME.hex('border')};
                border-left: 8px solid {edge.name()};
                border-radius: 12px;
            }}
            QFrame#asisAdvisoryPanel QLabel {{ background: transparent; color: {THEME.hex('text')}; border: none; }}
        """)
        # nothing to say: hide the strip (its space is kept, so nothing moves)
        panel.setVisible(not (sev == "normal" and panel.line1.text() == NORMAL_TEXT))

    panel._apply_theme = apply_theme
    THEME.changed.connect(apply_theme)
    apply_theme()


def install_layout(page):
    """Rearrange the team's Driving page (team look only). Returns True when the layout pass is applied."""
    if not layout_enabled() or getattr(page, "sw7", None) is not None:
        return False
    grid = page.layout()
    while grid.count():                                   # take every widget and row out of the team's grid
        grid.takeAt(0)
    for i in range(4):
        grid.setColumnStretch(i, 0)
        grid.setRowStretch(i, 0)
    grid.setContentsMargins(LAYOUT_MARGIN, 8, LAYOUT_MARGIN, 8)
    grid.setSpacing(0)

    old = (page.speed, page.brake, page.accel)
    page.speed = _layout_speedometer_class(type(old[0]))()
    page.brake = _layout_pedal_class(type(old[1]))('BRAKE', 'crit')
    page.accel = _layout_pedal_class(type(old[2]))('ACCEL', 'normal')
    for w in old:
        w.hide()
        w.deleteLater()

    _make_advice_strip(page.asis_panel)
    page.pair = RangeBatteryPair()
    page.range.hide()
    page.route.setFont(THEME.font(LAYOUT_ROUTE_PX, QFont.Weight.DemiBold))
    page.interlock.setFont(THEME.font(LAYOUT_ROUTE_PX, QFont.Weight.Black))

    col = QVBoxLayout()
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(6)
    col.addWidget(page.gear, 0, Qt.AlignmentFlag.AlignHCenter)
    col.addWidget(page.faults, 0, Qt.AlignmentFlag.AlignHCenter)
    col.addSpacing(4)
    col.addWidget(page.asis_panel)
    centre = QHBoxLayout()
    centre.setSpacing(24)
    centre.addStretch(1)
    centre.addWidget(page.brake, 0, Qt.AlignmentFlag.AlignVCenter)
    centre.addWidget(page.speed, 4)
    centre.addWidget(page.accel, 0, Qt.AlignmentFlag.AlignVCenter)
    centre.addStretch(1)
    col.addLayout(centre, 1)
    col.addWidget(page.pair)
    col.addWidget(page.route)
    col.addWidget(page.interlock)
    grid.addLayout(col, 0, 0)

    team_set_state = page.set_state

    def set_state(s):
        team_set_state(s)
        page.pair.set_state(s)
        page.interlock.setVisible(bool(page.interlock.text()))

    page.set_state = set_state
    page.interlock.hide()
    page.sw7_layout = True
    return True
