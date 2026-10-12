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
    S = _style()
    if S is not None:                                     # paper and depth style (TUKZIE_SW7_STYLE, default paper)
        install_paper(page, S)
    return True


# ---- paper and depth style (12 Oct 2026, Planning/paper-depth-theme-prompt.md sections 3 to 5 and 10) ------------
# Drive becomes the glance page. Behind TUKZIE_SW7_STYLE: "team" (or no sw7_style module) leaves the layout pass
# above exactly as it is. In paper:
#   - back plane: the word DRIVE (set by sw7_style);
#   - middle plane: the speed dial as a raised disc (a slab with a thick edge on a cached shadow), the speed at
#     168 px in ink, the only hero on the page;
#   - top plane: three glance tiles that overlap the disc's edge and open the page that owns the value
#     (Planning/data-ownership-and-merge-plan.md, option A): Next turn (Map), Around (Sensors, later Surroundings)
#     and Range (Charging). Each tile carries one signal-coloured chevron, the only signal on the page apart from
#     the frame. The battery percent is in the status bar only; the tile shows it as a bar;
#   - the pedal bars (no pedal sensors on the vehicle) and the route line are gone: the route line's text is in
#     the Next turn tile, so "Free driving" no longer sits under the nav pill;
#   - the ASIS strip on a paper card, ink text, the severity as a small status dot.
# Type: 168 px speed; 22 px only for the advice line, the turn distance and the range; the rest 13 or 16 px.
import time
import types

from PySide6.QtCore import QPointF, QTimer
from PySide6.QtGui import QFontMetricsF, QPainterPath, QPolygonF
from PySide6.QtWidgets import QAbstractButton

PAPER_SPEED_PX = 168
SLAB_EDGE = 0               # the disc is flat now (a hairline edge, no slab)
TILE_W, TILE_H = 360, 372   # Next turn and Around
RANGE_W, RANGE_H = 380, 104
TILE_OVERLAP = 12           # how far the side tiles reach over the disc's edge (kept small: little stacking)
TILE_RADIUS = 8
CHEVRON_D = 36


def _style():
    """sw7_style when the paper style is on, else None (TUKZIE_SW7_STYLE=team, or a build without the module)."""
    try:
        from . import sw7_style as S
    except ImportError:
        return None
    return S if S.enabled() else None


def _main_of(widget):
    """The DashboardMain above a page (it has switch_page_id and page_by_id), or None."""
    w = widget
    while w is not None:
        if hasattr(w, "switch_page_id") and hasattr(w, "page_by_id"):
            return w
        w = w.parentWidget()
    return None


def _paper_speedometer_class(base, S):
    """The layout pass's dial drawn as a raised paper disc: ink arc and ticks, 13 px numbers, the speed at 168 px."""

    class PaperSpeedometer(base):
        SPEED_PX = PAPER_SPEED_PX

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setMaximumWidth(16777215)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        def disc(self):
            """(cx, cy, R): the disc in widget coordinates."""
            R = max(60.0, min(self.width() / 2.0, (self.height() - SLAB_EDGE) / 2.0))
            return self.width() / 2.0, R, R

        def paintEvent(self, _):
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            cx, cy, R = self.disc()
            # the face: card with a hairline edge (its very light shadow is painted by the stage)
            p.setPen(QPen(S.c("hairline"), 1.0))
            p.setBrush(S.c("card"))
            p.drawEllipse(QPointF(cx, cy), R - 0.5, R - 0.5)
            r = R - 30
            start, span = 135.0, 270.0
            arc = QRectF(cx - r, cy - r, 2 * r, 2 * r)
            p.setPen(QPen(S.c("paper_deep"), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawArc(arc, int(-start * 16), int(-span * 16))
            known = getattr(self, "speed_known", True)
            if known and self.speed > 0.05:
                p.setPen(QPen(S.c("ink"), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                p.drawArc(arc, int(-start * 16), int(-span * (min(50.0, self.speed) / 50.0) * 16))
            # ticks: every 1 km/h a hairline, every 5 a short tick, every 10 a long tick with its number (Plex Mono)
            p.setFont(S.mono(S.LABEL, QFont.Weight.Normal))
            for v in range(51):
                a = start + span * v / 50.0
                if v % 10 == 0:
                    p.setPen(QPen(S.c("ink_2"), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                    p.drawLine(self._point(cx, cy, r * .86, a), self._point(cx, cy, r * .955, a))
                    t = self._point(cx, cy, r * .75, a)
                    p.setPen(S.c("ink_2"))
                    p.drawText(QRectF(t.x() - 22, t.y() - 10, 44, 20), Qt.AlignmentFlag.AlignCenter, str(v))
                elif v % 5 == 0:
                    p.setPen(QPen(S.c("ink_3"), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                    p.drawLine(self._point(cx, cy, r * .895, a), self._point(cx, cy, r * .955, a))
                else:
                    p.setPen(QPen(S.c("hairline"), 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                    p.drawLine(self._point(cx, cy, r * .925, a), self._point(cx, cy, r * .955, a))
            cap = float(VEHICLE_SPEC.max_speed_kmh)
            a = start + span * min(50.0, cap) / 50.0
            p.setPen(QPen(S.c("warn"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawLine(self._point(cx, cy, r * .86, a), self._point(cx, cy, r * 1.06, a))
            if self.recommended is not None:
                rec = max(0.0, min(50.0, float(self.recommended)))
                a = start + span * rec / 50.0
                p.setPen(QPen(S.c("ok"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                p.drawLine(self._point(cx, cy, r * .86, a), self._point(cx, cy, r * 1.06, a))
            if known:
                # the needle: a slim ink pointer across the track at the speed, with a small hub dot on the track
                a = start + span * max(0.0, min(50.0, self.speed)) / 50.0
                p.setPen(QPen(S.c("ink"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawLine(self._point(cx, cy, r * .80, a), self._point(cx, cy, r * 1.07, a))
                p.setPen(QPen(S.c("card"), 2.0)); p.setBrush(S.c("ink"))
                p.drawEllipse(self._point(cx, cy, r, a), 5.0, 5.0)
            speed_px = int(max(S.HERO_MIN, min(self.SPEED_PX, r * 0.9)))
            shown = f"{self.speed:.0f}" if known else "--"
            f = S.font(speed_px, QFont.Weight.DemiBold)
            fm = QFontMetricsF(f)
            base_y = cy + fm.capHeight() / 2.0 - 6
            p.setPen(S.c("ink") if known else S.c("ink_3"))
            p.setFont(f)
            p.drawText(QPointF(cx - fm.horizontalAdvance(shown) / 2.0, base_y), shown)
            p.setPen(S.c("ink_2"))
            p.setFont(S.font(S.LABEL, QFont.Weight.Medium))
            p.drawText(QRectF(cx - 80, base_y + 14, 160, 20), Qt.AlignmentFlag.AlignCenter,
                       "km/h" if known else "km/h · no speed reading")
            self.sw7_fonts = {"speed": speed_px, "unit": S.LABEL, "ticks": S.LABEL, "radius": r, "text": shown}
            p.end()

    return PaperSpeedometer


def _paint_chevron(p, S, rect, pressed=False):
    """The tap mark of a glance tile: a signal-outline circle with a ">" in it (filled while pressed)."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(S.c("signal", 140), 1.0))
    p.setBrush(S.c("signal") if pressed else S.c("card"))
    p.drawEllipse(rect.adjusted(1, 1, -1, -1))
    c = rect.center()
    k = rect.width() * 0.12
    pen = QPen(S.c("card") if pressed else S.c("signal"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
               Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath(QPointF(c.x() - k * 0.6, c.y() - k * 1.25))
    path.lineTo(QPointF(c.x() + k * 0.75, c.y()))
    path.lineTo(QPointF(c.x() - k * 0.6, c.y() + k * 1.25))
    p.drawPath(path)
    p.restore()


class GlanceTile(QAbstractButton):
    """A top-plane card that shows one glance value and opens the page that owns it. The page's stage paints its
    shadow (cached), the tile paints the card, its caps label, the chevron and its own content (draw_content)."""

    def __init__(self, S, label, target, parent=None):
        super().__init__(parent)
        self.S, self.label, self.target = S, label, target
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(label.title())
        self.clicked.connect(self.open_target)
        THEME.changed.connect(self.update)
        self.opened = []                  # page ids this tile opened (tests)
        # Touch: only a one-finger tap that stays put opens the page. Two- and three-finger page swipes
        # (sw7_page_swipe) and one-finger drags that start on a tile must never open it.
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self._touch = None                # (start positions, most fingers, moved, start time)

    def event(self, e):
        from PySide6.QtCore import QEvent
        kind = e.type()
        if kind in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
            pts = e.points()
            if kind == QEvent.Type.TouchBegin:
                self._touch = [{p.id(): p.position() for p in pts}, len(pts), False, time.monotonic()]
                self.setDown(True)
            elif self._touch is not None:
                t = self._touch
                t[1] = max(t[1], len(pts))
                for p in pts:
                    s = t[0].get(p.id())
                    if s is None:
                        t[0][p.id()] = p.position()
                    elif abs(p.position().x() - s.x()) > 12 or abs(p.position().y() - s.y()) > 12:
                        t[2] = True
                if t[1] > 1 or t[2]:
                    self.setDown(False)
                if kind in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
                    self.setDown(False)
                    tap = kind == QEvent.Type.TouchEnd and t[1] == 1 and not t[2] and time.monotonic() - t[3] < 1.0
                    self._touch = None
                    if tap:
                        self.click()
            e.accept()
            return True
        return super().event(e)

    def target_id(self):
        main = _main_of(self)
        targets = self.target if isinstance(self.target, (tuple, list)) else (self.target,)
        if main is None:
            return targets[0]
        return next((t for t in targets if t in getattr(main, "page_by_id", {})), targets[0])

    def open_target(self):
        main = _main_of(self)
        pid = self.target_id()
        self.opened.append(pid)
        if main is not None and pid in getattr(main, "page_by_id", {}):
            main.switch_page_id(pid)

    def chevron_rect(self):
        return QRectF(self.width() - 20 - CHEVRON_D, 16, CHEVRON_D, CHEVRON_D)

    def paintEvent(self, _):
        S = self.S
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        r = QRectF(self.rect())
        p.setPen(QPen(S.c("hairline"), 1.0))
        p.setBrush(S.c("signal_tint") if self.isDown() else S.c("card"))
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), TILE_RADIUS, TILE_RADIUS)
        p.setPen(S.c("ink_2"))
        p.setFont(S.font(S.LABEL, QFont.Weight.DemiBold, caps=True))
        p.drawText(QRectF(24, 20, self.width() - 100, 32), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   self.label)
        _paint_chevron(p, S, self.chevron_rect(), self.isDown())
        self.draw_content(p)
        p.end()

    def draw_content(self, p):
        pass

    def _text(self, p, rect, text, px, colour="ink", weight=QFont.Weight.Normal, align=None, caps=False, elide=True):
        S = self.S
        p.setPen(S.c(colour))
        f = S.font(px, weight, caps=caps)
        p.setFont(f)
        if elide:
            text = QFontMetricsF(f).elidedText(text, Qt.TextElideMode.ElideRight, rect.width())
        p.drawText(rect, align or (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text)


def _to_xy(lat, lon, lat0, lon0):
    return ((lon - lon0) * 111320.0 * math.cos(math.radians(lat0)), (lat - lat0) * 111320.0)


class NextTurnTile(GlanceTile):
    """Next turn: a mini map of the route around the vehicle (heading up), the turn arrow, its distance and road,
    and one line with the time, distance and arrival. With no route it says so and opens the Map to plan one."""

    def __init__(self, S, page, parent=None):
        super().__init__(S, "NEXT TURN", "navigation", parent)
        self.page = page
        self.summary = {}                 # what the tile shows (tests)

    def map(self):
        main = _main_of(self)
        nav = getattr(main, "navigation", None) if main is not None else None
        m = getattr(nav, "map", None)
        return m if m is not None and hasattr(m, "next_maneuvers") else None

    def _state(self):
        m = self.map()
        if m is None or not getattr(m, "route", None):
            status = self.page.route.text().strip() if hasattr(self.page, "route") else ""
            return {"kind": "none", "status": status or "Free driving · no destination selected"}
        ahead = m.next_maneuvers(1)
        if not ahead or (getattr(m, "vehicle", None) is None and not getattr(m, "simulating", False)):
            return {"kind": "ready", "status": "Waiting for a position on the route"}
        man, dist = ahead[0]
        left_m = max(0.0, float(getattr(m, "_route_total_m", 0.0)) - float(getattr(m, "_along_m", 0.0) or 0.0))
        eta = m._eta_seconds(left_m) if hasattr(m, "_eta_seconds") else None
        parts = [f"{max(1, round(eta / 60.0))} min" if eta is not None else None, m._distance_text(left_m)
                 if left_m >= 20 else "0 m",
                 time.strftime("arrive %H:%M", time.localtime(time.time() + eta)) if eta is not None else None]
        arrived = bool(getattr(m, "sim_arrived", False)) or (man["kind"] == "arrive" and dist < 15)
        return {"kind": "arrived" if arrived else "turn", "man": man, "dist": dist,
                "distance": "" if man["kind"] == "arrive" else m._distance_text(dist),
                "instruction": "Arrived" if arrived else m._instruction(man),
                "line": "At the destination" if arrived else " · ".join(x for x in parts if x)}

    def draw_content(self, p):
        S = self.S
        st = self._state()
        self.summary = {k: v for k, v in st.items() if k != "man"}
        well = QRectF(20, 68, self.width() - 40, 156)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(S.c("paper" if S.is_night() else "paper_deep"))
        p.drawRoundedRect(well, 6, 6)
        x0 = 24.0
        if st["kind"] in ("none", "ready"):
            self._placeholder_roads(p, well)
            self._text(p, QRectF(x0, 240, self.width() - 48, 32), "No route" if st["kind"] == "none" else "Route ready",
                       S.SECONDARY, "ink", QFont.Weight.Bold)
            p.setPen(S.c("ink_2"))
            p.setFont(S.font(S.BODY))
            p.drawText(QRectF(x0, 276, self.width() - 48, 48), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                       | Qt.TextFlag.TextWordWrap, st["status"])
            self._text(p, QRectF(x0, self.height() - 44, self.width() - 48, 22),
                       "Tap to plan a trip" if st["kind"] == "none" else "Tap to open the map", S.LABEL, "ink_2")
            return
        self._mini_map(p, well)
        m = self.map()
        arrow = QRectF(x0, 238, 48, 48)
        if hasattr(m, "_turn_arrow"):
            m._turn_arrow(p, arrow, "arrive" if st["kind"] == "arrived" else st["man"]["kind"], S.c("ink"))
        tx = x0 + 64
        if st["distance"]:
            self._text(p, QRectF(tx, 236, self.width() - tx - 24, 30), st["distance"], S.SECONDARY, "ink", QFont.Weight.Bold)
            self._text(p, QRectF(tx, 266, self.width() - tx - 24, 24), st["instruction"], S.BODY, "ink")
        else:
            self._text(p, QRectF(tx, 248, self.width() - tx - 24, 30), st["instruction"], S.BODY, "ink", QFont.Weight.Bold)
        p.setPen(QPen(S.c("hairline"), 1))
        p.drawLine(QPointF(x0, 308), QPointF(self.width() - 24, 308))
        p.setPen(S.c("ink_2")); p.setFont(S.mono(S.LABEL, QFont.Weight.Normal))   # times and distances: Plex Mono
        p.drawText(QRectF(x0, 318, self.width() - 48, 32), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, st["line"])

    def _placeholder_roads(self, p, well):
        S = self.S
        p.save()
        p.setClipRect(well)
        pen = QPen(S.c("hairline" if S.is_night() else "card"), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(well.left() + well.width() * 0.3, well.top() - 10),
                   QPointF(well.left() + well.width() * 0.42, well.bottom() + 10))
        p.drawLine(QPointF(well.left() - 10, well.top() + well.height() * 0.62),
                   QPointF(well.right() + 10, well.top() + well.height() * 0.48))
        p.setPen(QPen(S.c("hairline" if S.is_night() else "card"), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(well.left() + well.width() * 0.72, well.top() - 10),
                   QPointF(well.left() + well.width() * 0.8, well.bottom() + 10))
        c = QPointF(well.left() + well.width() * 0.37, well.top() + well.height() * 0.56)
        p.setPen(QPen(S.c("ink_3"), 2))
        p.setBrush(S.c("card"))
        p.drawEllipse(c, 8, 8)
        p.restore()

    def _mini_map(self, p, well):
        """The route from 120 m behind to 120 m past the next turn, heading up, in ink on the paper well."""
        S = self.S
        m = self.map()
        pts = list(getattr(m, "_route_pts", []) or [])
        along = float(getattr(m, "_along_m", 0.0) or 0.0)
        if len(pts) < 2:
            return
        ahead = m.next_maneuvers(1)
        turn_m = ahead[0][0]["at_m"] if ahead else pts[-1][2]
        lo, hi = along - 120.0, max(along + 160.0, turn_m + 120.0)

        def at(dist):
            dist = max(pts[0][2], min(pts[-1][2], dist))
            for a, b in zip(pts, pts[1:]):
                if dist <= b[2] or b is pts[-1]:
                    k = 0.0 if b[2] <= a[2] else (dist - a[2]) / (b[2] - a[2])
                    return a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k
            return pts[-1][0], pts[-1][1]

        lat0, lon0 = at(along)
        fx, fy = _to_xy(*at(along + 25.0), lat0, lon0)
        ang = math.atan2(fx, fy) if (fx or fy) else 0.0          # course, clockwise from north
        ca, sa = math.cos(ang), math.sin(ang)

        def local(lat, lon):
            x, y = _to_xy(lat, lon, lat0, lon0)
            return x * ca - y * sa, x * sa + y * ca              # rotated: travel direction is +y

        seq = [(along, local(lat0, lon0))]
        for la, lo_, d, _ in pts:
            if lo < d < hi:
                seq.append((d, local(la, lo_)))
        seq.append((lo, local(*at(lo))))
        seq.append((hi, local(*at(hi))))
        seq.sort(key=lambda q: q[0])
        xs = [q[1][0] for q in seq]
        ys = [q[1][1] for q in seq]
        span = max(80.0, max(abs(v) for v in xs) * 2.0, (max(ys) - min(0.0, min(ys))))
        scale = min((well.width() - 48) / max(80.0, max(abs(v) for v in xs) * 2.0 + 1e-6),
                    (well.height() - 36) / max(80.0, max(ys) - min(ys) + 1e-6))
        scale = min(scale, (well.height() - 36) / 80.0)
        _ = span
        ox = well.center().x()
        oy = well.bottom() - 18 - (0.0 - min(ys)) * scale

        def screen(xy):
            return QPointF(ox + xy[0] * scale, oy - xy[1] * scale)

        p.save()
        p.setClipRect(well.adjusted(2, 2, -2, -2))
        done = QPainterPath()
        todo = QPainterPath()
        first_done = first_todo = True
        for d, xy in seq:
            q = screen(xy)
            if d <= along:
                if first_done:
                    done.moveTo(q); first_done = False
                else:
                    done.lineTo(q)
            if d >= along:
                if first_todo:
                    todo.moveTo(q); first_todo = False
                else:
                    todo.lineTo(q)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(S.c("hairline" if S.is_night() else "card"), 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(done)
        p.drawPath(todo)
        p.setPen(QPen(S.c("ink_3"), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(done)
        p.setPen(QPen(S.c("ink"), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(todo)
        if ahead:
            tq = screen(local(*at(turn_m)))
            p.setPen(QPen(S.c("ink"), 3))
            p.setBrush(S.c("card"))
            p.drawEllipse(tq, 7, 7)
        v = screen((0.0, 0.0))
        tri = QPolygonF([QPointF(v.x(), v.y() - 12), QPointF(v.x() + 9, v.y() + 9), QPointF(v.x(), v.y() + 4),
                         QPointF(v.x() - 9, v.y() + 9)])
        p.setPen(QPen(S.c("card"), 2.5))
        p.setBrush(S.c("ink"))
        p.drawPolygon(tri)
        p.restore()


class AroundTile(GlanceTile):
    """Around: the tuk-tuk from above with the left, ahead and right ToF distances placed at their sensors (like the
    tyre pressures in inspo_sports_car_tiles.jpg), each with a small status dot, and the nearest hazard."""

    SIDES = ("left", "ahead", "right")

    def __init__(self, S, parent=None):
        super().__init__(S, "AROUND", ("surroundings", "sensors"), parent)
        self.metres = {s: None for s in self.SIDES}
        self.nearest = None
        self.has_data = False

    def set_telemetry(self, telemetry):
        try:
            from ..pages.sensors_page import hazard_text, hazards_of, tof_metres
        except ImportError:
            return
        self.has_data = telemetry is not None
        self.metres = tof_metres(telemetry)
        hz = hazards_of(telemetry)
        self.nearest = " ".join(hazard_text(hz[0])[0].split()) if hz else None
        self.update()

    def _status(self, metres):
        if metres is None:
            return None
        return "critical" if metres < 0.5 else "warn" if metres < 1.0 else "ok"

    def _tuk(self, p, cx, cy):
        """Top-down tuk-tuk, nose up: one front wheel, two rear wheels, canopy over the cabin."""
        S = self.S
        w, h = 74.0, 138.0
        top, bot = cy - h / 2, cy + h / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(S.c("ink_2"))
        p.drawRoundedRect(QRectF(cx - 7, top - 6, 14, 26), 5, 5)                       # front wheel
        for sx in (-1, 1):                                                              # rear wheels
            p.drawRoundedRect(QRectF(cx + sx * (w / 2 + 3) - 8, bot - 46, 16, 32), 5, 5)
        body = QPainterPath(QPointF(cx, top))
        body.cubicTo(QPointF(cx + 24, top), QPointF(cx + 26, top + 18), QPointF(cx + 28, top + 34))
        body.lineTo(QPointF(cx + w / 2, top + 56))
        body.lineTo(QPointF(cx + w / 2, bot - 10))
        body.quadTo(QPointF(cx + w / 2, bot), QPointF(cx + w / 2 - 10, bot))
        body.lineTo(QPointF(cx - w / 2 + 10, bot))
        body.quadTo(QPointF(cx - w / 2, bot), QPointF(cx - w / 2, bot - 10))
        body.lineTo(QPointF(cx - w / 2, top + 56))
        body.lineTo(QPointF(cx - 28, top + 34))
        body.cubicTo(QPointF(cx - 26, top + 18), QPointF(cx - 24, top), QPointF(cx, top))
        p.setPen(QPen(S.c("ink"), 2.2))
        p.setBrush(S.c("card"))
        p.drawPath(body)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(S.c("charcoal"))
        p.drawRoundedRect(QRectF(cx - w / 2 + 6, top + 50, w - 12, h - 60), 10, 10)  # canopy
        p.setBrush(S.c("ink_3"))
        p.drawRoundedRect(QRectF(cx - 18, top + 30, 36, 12), 5, 5)                     # windscreen

    def draw_content(self, p):
        S = self.S
        W = float(self.width())
        cx, cy = W / 2.0, 214.0
        self._tuk(p, cx, cy)
        pos = {"ahead": (QRectF(cx - 70, 70, 140, 44), QPointF(cx, cy - 82), QPointF(cx, 116)),
               "left": (QRectF(20, cy - 34, 118, 44), QPointF(cx - 44, cy - 22), QPointF(112, cy - 12)),
               "right": (QRectF(W - 138, cy - 34, 118, 44), QPointF(cx + 44, cy - 22), QPointF(W - 112, cy - 12))}
        for side in self.SIDES:
            box, at_car, at_text = pos[side]
            m = self.metres.get(side)
            status = self._status(m)
            if side == "ahead":                            # (the side readings sit level with their sensors)
                p.setPen(QPen(S.c("hairline"), 1.0))
                p.drawLine(at_text, at_car)
            if status is not None:                         # a short arc at the sensor: a small status mark
                p.setPen(QPen(S.c(status), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                rr = QRectF(cx - 60, cy - 100, 120, 120) if side == "ahead" else QRectF(cx - 70, cy - 70, 140, 140)
                start = {"ahead": 70, "left": 160, "right": -20}[side]
                p.drawArc(rr, start * 16, 40 * 16)
            text = "--" if m is None else f"{m:.2f} m"
            align = {"ahead": Qt.AlignmentFlag.AlignHCenter, "left": Qt.AlignmentFlag.AlignLeft,
                     "right": Qt.AlignmentFlag.AlignRight}[side]
            f = S.mono(S.BODY, QFont.Weight.Medium)
            tw = QFontMetricsF(f).horizontalAdvance(text)
            p.setPen(S.c("ink" if m is not None else "ink_3")); p.setFont(f)
            p.drawText(QRectF(box.left(), box.top(), box.width(), 22), align | Qt.AlignmentFlag.AlignVCenter, text)
            # the side and, with a reading, its band in words (never by colour alone)
            word = {None: "no reading", "critical": "very close", "warn": "close", "ok": "clear"}[status]
            self._text(p, QRectF(box.left() - (20 if side == "ahead" else 0), box.top() + 22,
                                 box.width() + (40 if side == "ahead" else 0), 18),
                       f"{side.capitalize()} · {word}", S.LABEL, "ink_2", QFont.Weight.Medium,
                       align | Qt.AlignmentFlag.AlignVCenter)
            if status is not None:                         # status dot beside the number
                x = {"ahead": box.center().x() + tw / 2 + 10, "left": box.left() + tw + 10,
                     "right": box.right() - tw - 10}[side]
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(S.c(status))
                p.drawEllipse(QPointF(x, box.top() + 11), 4.5, 4.5)
        p.setPen(QPen(S.c("hairline"), 1))
        p.drawLine(QPointF(24, 308), QPointF(W - 24, 308))
        if not self.has_data:
            line = "No sensor data"
        else:
            line = self.nearest or "Clear around the vehicle"
        self._text(p, QRectF(24, 318, W - 48, 32), line, S.LABEL, "ink_2", QFont.Weight.Medium)


class RangeTile(GlanceTile):
    """Range and battery: range at 22 px, the state of charge as a bar only (the percent is in the status bar), and
    the battery power now at 13 px. Opens Charging."""

    def __init__(self, S, parent=None):
        super().__init__(S, "RANGE", "charging", parent)
        self.range_km = self.soc = self.power_kw = None

    def chevron_rect(self):
        return QRectF(self.width() - 20 - CHEVRON_D, (self.height() - CHEVRON_D) / 2.0, CHEVRON_D, CHEVRON_D)

    def set_state(self, s):
        valid = getattr(s, "signal_validity", None) or {}
        self.soc = None if valid.get("soc") is False else _num(getattr(s, "soc_pct", None))
        rng = _num(getattr(s, "range_km", None))
        self.range_km = None if rng is None else min(float(VEHICLE_SPEC.rated_max_range_km), rng)
        self.power_kw = _num(getattr(s, "battery_power_kw", None))
        self.update()

    def value_text(self):
        return "--" if self.range_km is None else f"{self.range_km:.0f} km"

    def draw_content(self, p):
        S = self.S
        self._text(p, QRectF(24, 50, 130, 34), self.value_text(), S.SECONDARY, "ink" if self.range_km is not None
                   else "ink_3", QFont.Weight.DemiBold)
        x = 152.0
        # the battery: a bar, and its band in words too (never by colour alone)
        band = None if self.soc is None else "very low" if self.soc < 15 else "low" if self.soc < 30 else None
        title = "BATTERY" + ("" if self.soc is not None and band is None else f" · {band or 'NO READING'}".upper())
        self._text(p, QRectF(x, 20, self.width() - x - 70, 32), title, S.LABEL, "ink_2", QFont.Weight.DemiBold, caps=True)
        bar = QRectF(x, 60, self.width() - x - 84, 6)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(S.c("paper_deep"))
        p.drawRoundedRect(bar, 3, 3)
        if self.soc is not None:
            k = "critical" if self.soc < 15 else "warn" if self.soc < 30 else "ok"
            p.setBrush(S.c(k))
            p.drawRoundedRect(QRectF(bar.left(), bar.top(), max(6.0, bar.width() * max(0.0, min(1.0, self.soc / 100.0))),
                                     bar.height()), 3, 3)
        power = "-- kW" if self.power_kw is None else f"{self.power_kw:.1f} kW now"
        p.setPen(S.c("ink_2")); p.setFont(S.mono(S.LABEL, QFont.Weight.Normal))
        p.drawText(QRectF(x, 74, bar.width(), 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, power)


class DriveStage(QWidget):
    """The paper Driving page: every part placed by hand on a transparent stage over the back plane, which paints
    the cached shadows of the disc, the tiles and the advice strip (so nothing animated carries a live effect)."""

    def __init__(self, page, S, parent=None):
        super().__init__(parent)
        self.page, self.S = page, S
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.next_turn = NextTurnTile(S, page, self)
        self.around = AroundTile(S, self)
        self.range = RangeTile(S, self)
        self._telemetry_main = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        THEME.changed.connect(self.update)

    def tiles(self):
        return (self.next_turn, self.around, self.range)

    def refresh(self):
        """Once a second: connect the Around tile to the telemetry once the dashboard exists, redraw Next turn."""
        main = _main_of(self)
        if main is not None and self._telemetry_main is None and hasattr(main, "telemetry"):
            try:
                main.telemetry.telemetry_updated.connect(self.around.set_telemetry)
                self._telemetry_main = main
            except (AttributeError, RuntimeError, TypeError):
                pass
            m = self.next_turn.map()
            if m is not None and hasattr(m, "sim_tick"):
                m.sim_tick.connect(self.next_turn.update)
        if self.isVisible():
            self.next_turn.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.place()

    def place(self):
        pg = self.page
        W, H = self.width(), self.height()
        # the advice strip stops short of the subject (the TUKZIE render, middle plane) so it never hides it
        right = W - 32
        sub = self.S.page_plane_geometry(pg).get("subject") if hasattr(self.S, "page_plane_geometry") else None
        if sub is not None and sub.top() < 12 + LAYOUT_STRIP_H:
            right = int(sub.left()) - 16
        pg.asis_panel.setGeometry(32, 12, right - 32, LAYOUT_STRIP_H)
        gw = pg.gear.width()
        pg.gear.setGeometry(int((W - gw) / 2), 84, gw, pg.gear.height())
        fw = max(pg.faults.sizeHint().width(), 300)
        pg.faults.setGeometry(int((W - fw) / 2), 140, fw, 37)
        top = 184
        R = int(max(150, min(232, (H - top - 24 - 40) / 2)))
        pg.speed.setGeometry(int(W / 2 - R), top, 2 * R, 2 * R + SLAB_EDGE)
        cy = top + R
        ty = int(cy - TILE_H / 2 + 2)
        self.next_turn.setGeometry(int(W / 2 - R - TILE_W + TILE_OVERLAP), ty, TILE_W, TILE_H)
        self.around.setGeometry(int(W / 2 + R - TILE_OVERLAP), ty, TILE_W, TILE_H)
        r = R - 30
        ry = int(min(H - 16 - 8 - RANGE_H, cy + r * 0.707 + 4))
        self.range.setGeometry(int((W - RANGE_W) / 2), ry, RANGE_W, RANGE_H)
        pg.interlock.setGeometry(int(W / 2 - 300), ry - 30, 600, 24)
        for t in self.tiles():
            t.raise_()
        self.update()

    def cluster_rect(self):
        """The card under the gear row and the warning lamps (None when the hero word is off)."""
        S, pg = self.S, self.page
        if not getattr(S, "BACK_WORDS_SHOWN", False):
            return None
        g, f = pg.gear.geometry(), pg.faults.geometry()
        left, right = min(g.left(), f.left()) - 16, max(g.right(), f.right()) + 16
        return QRectF(left, g.top() - 6, right - left, f.bottom() - g.top() + 12)

    def paintEvent(self, _):
        S = self.S
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # the gear, turn indicators and warning lamps sit on one paper card (they lie over the hero word)
        r = self.cluster_rect()
        if r is not None:
            S.paint_card(p, r, 8, 1)
        sp = self.page.speed
        if hasattr(sp, "disc"):
            cx, cy, R = sp.disc()
            g = sp.geometry()
            S.paint_shadow(p, QRectF(g.x() + cx - R, g.y() + cy - R + SLAB_EDGE, 2 * R, 2 * R), R, 1)
        for t in self.tiles():
            if t.isVisible():
                S.paint_shadow(p, QRectF(t.geometry()), TILE_RADIUS, 1)
        p.end()


def _paper_gear_paint(badge, event, S):
    """GearBadge in paper: the team's turn arrows, then the gear in ink in a card circle (R in warn)."""
    from ..widgets.indicators import IndicatorCluster
    IndicatorCluster.paintEvent(badge, event)
    p = QPainter(badge)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    col = S.c("warn") if badge.gear == "R" else S.c("ink")
    c = QPointF(badge.rect().center().x() + 0.5, badge.rect().center().y() + 0.5)
    p.setPen(QPen(S.c("hairline"), 1.5))
    p.setBrush(S.c("card"))
    p.drawEllipse(c, 23, 23)
    p.setPen(col)
    p.setFont(S.font(S.BODY, QFont.Weight.Bold))
    p.drawText(QRectF(c.x() - 23, c.y() - 23, 46, 46), Qt.AlignmentFlag.AlignCenter, badge.gear)
    p.end()


def _paper_strip(panel, S):
    """The ASIS strip on a paper card: ink text, the severity as a small status dot before the heading."""
    row = panel.layout().itemAt(0).layout() if panel.layout() and panel.layout().count() else None
    dot = QLabel(panel)
    dot.setFixedSize(10, 10)
    if row is not None:
        row.insertWidget(0, dot, 0, Qt.AlignmentFlag.AlignVCenter)
        row.setSpacing(14)
    panel.layout().setContentsMargins(22, 4, 22, 4)
    panel.heading.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True))
    panel.line1.setFont(S.font(S.SECONDARY, QFont.Weight.Bold))
    panel.line2.setFont(S.font(S.BODY, QFont.Weight.Bold))
    panel.count.setFont(S.font(S.LABEL, QFont.Weight.Bold))
    panel.line1.setWordWrap(False)
    panel.line2.setWordWrap(False)
    panel.line2.setMaximumWidth(16777215)
    panel.sw7_dot = dot

    def apply_theme():
        sev = panel.property("severity") or "normal"
        no_data = panel.line1.text().strip().lower().startswith("no live")
        key = {"critical": "critical", "warning": "warn"}.get(sev, "ink_3" if no_data else "ok")
        panel.setStyleSheet(f"""
            QFrame#asisAdvisoryPanel {{ background: {S.hx('card')}; border: 1px solid {S.hx('hairline')}; border-radius: {S.RADIUS_MAX}px; }}
            QFrame#asisAdvisoryPanel QLabel {{ background: transparent; color: {S.hx('ink')}; border: none; }}
        """)
        panel.heading.setText(panel.heading.text().upper())
        panel.heading.setStyleSheet(f"color: {S.hx('ink_2')}; background: transparent; border: none;")
        panel.count.setStyleSheet(f"color: {S.hx('ink_2')}; background: transparent; border: none;")
        panel.line2.setStyleSheet(f"color: {S.hx('ink_2')}; background: transparent; border: none;")
        dot.setStyleSheet(f"background: {S.hx(key)}; border-radius: 5px;")
        panel.setVisible(not (sev == "normal" and panel.line1.text() == NORMAL_TEXT))
        stage = getattr(panel, "sw7_stage", None)
        if stage is not None:
            stage.update()

    panel._apply_theme = apply_theme
    THEME.changed.connect(apply_theme)
    apply_theme()


def _empty_layout(lay):
    while lay.count():
        item = lay.takeAt(0)
        if item.layout() is not None:
            _empty_layout(item.layout())


def install_paper(page, S):
    """Rebuild the laid-out Driving page as the paper glance page (see the comment above GlanceTile)."""
    grid = page.layout()
    _empty_layout(grid)
    grid.setContentsMargins(0, 0, 0, 0)
    stage = DriveStage(page, S)
    grid.addWidget(stage, 0, 0)
    old = page.speed
    page.speed = _paper_speedometer_class(type(old), S)()
    page.speed.speed, page.speed.recommended = old.speed, old.recommended
    page.speed.speed_known = getattr(old, "speed_known", True)
    old.hide()
    old.deleteLater()
    for w in (page.asis_panel, page.gear, page.faults, page.speed, page.interlock):
        w.setParent(stage)
        w.show()
    page.interlock.setFont(S.font(S.BODY, QFont.Weight.Bold))
    page.interlock.setAlignment(Qt.AlignmentFlag.AlignCenter)
    page.interlock.hide()
    for w in (page.brake, page.accel, page.pair, page.route, page.range):   # no pedal sensors; the rest moved
        w.hide()
    page.gear.paintEvent = types.MethodType(lambda self, e: _paper_gear_paint(self, e, S), page.gear)
    _paper_strip(page.asis_panel, S)
    page.asis_panel.sw7_stage = stage
    page.sw7_stage = stage
    page.sw7_tiles = {"next_turn": stage.next_turn, "around": stage.around, "range": stage.range}

    layout_set_state = page.set_state

    def set_state(s):
        layout_set_state(s)
        stage.range.set_state(s)
        page.interlock.setVisible(bool(page.interlock.text()))
        stage.next_turn.update()

    page.set_state = set_state
    team_support = page.set_support

    def set_support(support):
        team_support(support)
        stage.next_turn.update()

    page.set_support = set_support
    team_route = page.show_route_status

    def show_route_status(message):
        team_route(message)
        stage.next_turn.update()

    page.show_route_status = show_route_status
    stage.place()
    page.sw7_paper = True
