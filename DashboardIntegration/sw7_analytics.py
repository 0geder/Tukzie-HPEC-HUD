"""
SW-7: an infinite vertical carousel for the Analytics page (Planning/analytics-carousel-prompt.md).

install_carousel() takes the page's own widgets (the six value cards, the four chart cards and the
Driver insights card) out of their grids and shows them in an InfiniteCarousel, plus one Graphs card
that opens the four charts. The widgets are moved, not copied or redrawn, so the team's look and the
page's own update_state() (with SW-7's live-only "--" handling) are unchanged.

Carousel behaviour:
  - the current card is large in the middle, the previous and next cards peek above and below, dimmed;
  - the list wraps both ways (infinite);
  - swipe up, the down arrow or the mouse wheel brings the next card up from below; a short swipe
    snaps back; moves are animated (250 ms);
  - tapping the middle card activates it (Graphs opens the charts); tapping a peeking card scrolls to it;
  - dots on the right show the position.
No automatic scrolling: moving content on a driver display draws the eye.
Turned off with TUKZIE_ANALYTICS_CAROUSEL=0 (the original grid comes back).

Layout pass (12 Oct 2026, Planning/google-stitch-dashboard-prompt.md 3.3), behind TUKZIE_SW7_LAYOUT (default
on; 0 gives the carousel exactly as before). Same cards, gradients and colours; only sizes and spacing:
  - the centre card up to 480 px tall with the neighbours peeking 60 px;
  - each value card: value 96 px bold with its unit at 32 px, one 18 px context line, and a 120 px
    sparkline of the page's own chart history where there is one (battery %, odometer, consumption);
  - 64 x 64 px up and down buttons, 12 px dots with the current card's name at 14 px;
  - Graphs: 64 px Back button, charts scaled to their data (speed 0 to 50 km/h, battery 0 to 100 %,
    consumption 0 to 120 Wh/km, distance fitted), axis text at least 12 px, current value 24 px;
  - headings in the theme's text colour (they were dark on dark where no app stylesheet applies).
"""
from __future__ import annotations

import math
import os

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QStackedWidget, QVBoxLayout, QWidget)

from ..theme import THEME

ANIM_MS = 250
TAP_SLOP_PX = 10

# layout pass sizes (px at 1280 x 800)
VALUE_PX = 96
UNIT_PX = 32
CONTEXT_PX = 18
CAPTION_PX = 20
SPARK_H = 120
PEEK_PX = 60
CARD_GAP = 18
CARD_MAX_H = 480
BUTTON_PX = 64
AXIS_PX = 12
CHART_VALUE_PX = 24
CHART_TITLE_PX = 14
CHART_RANGES = {"speed_chart": (0.0, 50.0), "soc_chart": (0.0, 100.0), "dist_chart": None, "eff_chart": (0.0, 120.0)}
PAPER_RADIUS = 8


def layout_enabled():
    return os.environ.get("TUKZIE_SW7_LAYOUT", "1").strip() != "0"


class InfiniteCarousel(QWidget):
    current_changed = Signal(int)
    item_activated = Signal(int)          # tap on the middle card

    def __init__(self, items, parent=None):
        super().__init__(parent)
        self._items = list(items)
        self._effects = []
        for w in self._items:
            w.setParent(self)
            eff = QGraphicsOpacityEffect(w)
            w.setGraphicsEffect(eff)
            self._effects.append(eff)
        self._pos = 0.0                    # fractional index of the card in the middle
        self._last_current = 0
        self._press_y = None
        self._press_pos = 0.0
        self._moved = False
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(ANIM_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._set_pos)
        self._anim.finished.connect(self._settle)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._layout_pass = layout_enabled()

    # ---- state ---------------------------------------------------------------------------
    @property
    def count(self):
        return len(self._items)

    def current(self):
        return int(round(self._pos)) % self.count if self.count else 0

    def item(self, index):
        return self._items[index % self.count]

    # ---- navigation ----------------------------------------------------------------------
    def step(self, delta):
        self._animate_to(round(self._pos) + int(delta))

    def go_to(self, index):
        cur = self.current()
        d = (index - cur) % self.count
        if d > self.count // 2:
            d -= self.count
        self.step(d)

    def _animate_to(self, target):
        self._anim.stop()
        self._anim.setStartValue(float(self._pos))
        self._anim.setEndValue(float(target))
        self._anim.start()

    def _set_pos(self, value):
        self._pos = float(value)
        self._layout()
        cur = self.current()
        if cur != self._last_current:
            self._last_current = cur
            self.current_changed.emit(cur)

    def _settle(self):
        self._pos = float(round(self._pos) % self.count)   # keep the number small; same card
        self._layout()

    # ---- geometry ------------------------------------------------------------------------
    def _geometry(self):
        if self._layout_pass:                       # neighbours peek PEEK_PX each, centre card up to 480 px
            card_h = max(170.0, min(float(CARD_MAX_H), self.height() - 2.0 * (PEEK_PX + CARD_GAP)))
            card_w = max(300.0, min(self.width() - 40.0, 900.0))
            return card_w, card_h, card_h + CARD_GAP
        card_h = max(170.0, min(360.0, self.height() * 0.56))
        card_w = max(300.0, min(self.width() - 40.0, 900.0))
        return card_w, card_h, card_h + 18.0

    def _layout(self):
        if not self.count:
            return
        card_w, card_h, pitch = self._geometry()
        cy = self.height() / 2.0
        base = math.floor(self._pos)
        frac = self._pos - base
        shown = set()
        for k in range(-2, 3):
            idx = (base + k) % self.count
            if idx in shown:
                continue
            off = k - frac
            top = cy + off * pitch - card_h / 2.0
            if top + card_h < 0 or top > self.height():
                continue
            shown.add(idx)
            w = self._items[idx]
            w.setGeometry(int((self.width() - card_w) / 2), int(top), int(card_w), int(card_h))
            self._effects[idx].setOpacity(1.0 - 0.6 * min(1.0, abs(off)))
            w.show()
        for i, w in enumerate(self._items):
            if i not in shown:
                w.hide()
        self._layout_shadow_update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout()

    def paintEvent(self, event):
        S = getattr(self, "sw7_paper", None)
        if S is None:
            return super().paintEvent(event)
        p = QPainter(self)                         # paper: each shown card floats on a cached shadow
        for w, eff in zip(self._items, self._effects):
            if w.isVisible():
                p.setOpacity(max(0.0, min(1.0, eff.opacity())))
                S.paint_shadow(p, QRectF(w.geometry()), PAPER_RADIUS, 2)
        p.end()

    def _layout_shadow_update(self):
        if getattr(self, "sw7_paper", None) is not None:
            self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self._layout()

    # ---- touch, mouse and wheel ------------------------------------------------------------
    def mousePressEvent(self, event):
        self._anim.stop()
        self._press_y = event.position().y()
        self._press_pos = self._pos
        self._moved = False
        event.accept()

    def mouseMoveEvent(self, event):
        if self._press_y is None:
            return
        dy = event.position().y() - self._press_y
        if abs(dy) > TAP_SLOP_PX:
            self._moved = True
        if self._moved:
            self._set_pos(self._press_pos - dy / self._geometry()[2])

    def mouseReleaseEvent(self, event):
        if self._press_y is None:
            return
        dy = event.position().y() - self._press_y
        self._press_y = None
        pitch = self._geometry()[2]
        if not self._moved:                        # a tap
            k = round((event.position().y() - self.height() / 2.0) / pitch)
            if k == 0:
                self.item_activated.emit(self.current())
            else:
                self.step(max(-1, min(1, k)))
            return
        moved = -dy / pitch                        # swipe up = positive = next card
        if abs(moved) < 0.2:
            target = round(self._press_pos)        # too short: snap back
        elif abs(moved) < 1.0:
            target = round(self._press_pos) + (1 if moved > 0 else -1)
        else:
            target = round(self._press_pos + moved)
        self._animate_to(target)

    def wheelEvent(self, event):
        self.step(-1 if event.angleDelta().y() > 0 else 1)
        event.accept()


class _Dots(QWidget):
    """Vertical position dots; the current one is filled in the accent colour."""

    def __init__(self, count, parent=None, names=None):
        super().__init__(parent)
        self.count, self.current = count, 0
        self.names = list(names) if names else None   # layout pass: the current card's name beside its dot
        self.setFixedWidth(150 if self.names else 28)
        THEME.changed.connect(self.update)

    def set_current(self, i):
        self.current = i
        self.update()

    def paintEvent(self, _event):
        if self.names:
            return self._paint_named()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        gap = 22.0
        top = self.height() / 2.0 - gap * (self.count - 1) / 2.0
        for i in range(self.count):
            on = i == self.current
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(THEME.color("accent") if on else QColor(THEME.hex("border")))
            r = 6.0 if on else 4.5
            p.drawEllipse(QRectF(self.width() / 2.0 - r, top + i * gap - r, 2 * r, 2 * r))
        p.end()

    def _paint_named(self):
        """12 px dots, 12 px apart, at the right edge; the current card's name at 14 px to the left of its dot."""
        S = getattr(self, "sw7_paper", None)
        if S is not None:
            return self._paint_paper(S)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        gap, r = 24.0, 6.0
        x = self.width() - BUTTON_PX / 2.0               # under the centre of the up and down buttons
        top = self.height() / 2.0 - gap * (self.count - 1) / 2.0
        for i in range(self.count):
            on = i == self.current
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(THEME.color("accent") if on else QColor(THEME.hex("border")))
            p.drawEllipse(QRectF(x - r, top + i * gap - r, 2 * r, 2 * r))
        name = self.names[self.current % len(self.names)] if self.names else ""
        p.setPen(QColor(THEME.hex("text")))
        p.setFont(THEME.font(14, QFont.Weight.DemiBold))
        y = top + self.current * gap
        p.drawText(QRectF(0, y - 12, x - r - 8, 24), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, name)
        p.end()


    def _paint_paper(self, S):
        """Paper: the dots are information, so ink (current) and hairline, never signal; the name at 13 px."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        gap, r = 24.0, 6.0
        x = self.width() - BUTTON_PX / 2.0
        top = self.height() / 2.0 - gap * (self.count - 1) / 2.0
        for i in range(self.count):
            on = i == self.current
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(S.c("ink") if on else S.c("ink_3"))
            rr = r if on else 4.0
            p.drawEllipse(QRectF(x - rr, top + i * gap - rr, 2 * rr, 2 * rr))
        name = self.names[self.current % len(self.names)] if self.names else ""
        p.setPen(S.c("ink"))
        p.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True))
        y = top + self.current * gap
        p.drawText(QRectF(0, y - 12, x - r - 10, 24), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   name.upper())
        p.end()


def _enlarge_value_card(card):
    """Bigger caption and value for a value card shown alone in the carousel."""
    card.setMaximumWidth(16777215)
    card.setMaximumHeight(16777215)
    card.content_layout().insertStretch(1, 1)          # centre the value vertically in the taller card
    for label in card.findChildren(QLabel):
        if label is getattr(card, "value", None):
            label.setFont(THEME.font(64, QFont.Weight.Bold))
        else:
            label.setFont(THEME.font(20, QFont.Weight.ExtraBold))


# ---- layout pass widgets ---------------------------------------------------------------------------------------
def _split_value(text):
    """'80 %' -> ('80', '%'); '12.3 km' -> ('12.3', 'km'); '--' -> ('--', '')."""
    text = (text or "").strip()
    if " " in text:
        num, unit = text.split(" ", 1)
        return num, unit
    return text, ""


class _BigValue(QWidget):
    """The card's value: number at VALUE_PX bold, unit at UNIT_PX, on one baseline, centred.

    It mirrors the team's value label (still set by update_state, kept hidden), so the label's text stays the
    reference for tests and for the TUKZIE_SW7_LAYOUT=0 look."""

    def __init__(self, label, color_key, parent=None):
        super().__init__(parent)
        self.label, self.color_key = label, color_key
        self.setFixedHeight(int(VALUE_PX * 1.2))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        THEME.changed.connect(self.update)

    def paintEvent(self, _event):
        num, unit = _split_value(self.label.text())
        S = getattr(self, "sw7_paper", None)
        if S is not None:
            return self._paint_paper(S, num, unit)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fn, fu = THEME.font(VALUE_PX, QFont.Weight.Bold), THEME.font(UNIT_PX, QFont.Weight.DemiBold)
        mn, mu = QFontMetricsF(fn), QFontMetricsF(fu)
        gap = 12.0 if unit else 0.0
        total = mn.horizontalAdvance(num) + gap + (mu.horizontalAdvance(unit) if unit else 0.0)
        x = (self.width() - total) / 2.0
        base = (self.height() + mn.capHeight()) / 2.0
        p.setPen(QColor(THEME.hex("text")))
        p.setFont(fn)
        p.drawText(QPointF(x, base), num)
        if unit:
            p.setPen(QColor(THEME.hex("text_dim")))
            p.setFont(fu)
            p.drawText(QPointF(x + mn.horizontalAdvance(num) + gap, base), unit)
        p.end()


    def _paint_paper(self, S, num, unit):
        """Paper: the card's one huge value (S.HERO) in ink, its unit at 22 px in ink_2."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fn, fu = S.font(S.HERO, QFont.Weight.DemiBold), S.font(S.SECONDARY, QFont.Weight.Medium)
        mn, mu = QFontMetricsF(fn), QFontMetricsF(fu)
        gap = 14.0 if unit else 0.0
        total = mn.horizontalAdvance(num) + gap + (mu.horizontalAdvance(unit) if unit else 0.0)
        x = (self.width() - total) / 2.0
        base = (self.height() + mn.capHeight()) / 2.0
        p.setPen(S.c("ink") if num != "--" else S.c("ink_3"))
        p.setFont(fn)
        p.drawText(QPointF(x, base), num)
        if unit:
            p.setPen(S.c("ink_2"))
            p.setFont(fu)
            p.drawText(QPointF(x + mn.horizontalAdvance(num) + gap, base), unit)
        p.end()


class _Sparkline(QWidget):
    """The last points of one of the page's own charts (the same history the Graphs view shows)."""

    def __init__(self, chart, color_key, parent=None):
        super().__init__(parent)
        self.chart, self.color_key = chart, color_key
        self.setFixedHeight(SPARK_H)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        THEME.changed.connect(self.update)

    def paintEvent(self, _event):
        data = list(getattr(self.chart, "_data", []) or [])
        S = getattr(self, "sw7_paper", None)
        if S is not None:
            return _paint_spark_paper(self, S, data)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dim = QColor(THEME.hex("text_dim"))
        p.setPen(dim)
        p.setFont(THEME.font(AXIS_PX, QFont.Weight.DemiBold))
        p.drawText(QRectF(0, 0, self.width(), 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, "RECENT")
        plot = QRectF(0, 22, self.width(), self.height() - 26)
        if len(data) < 2:
            p.setFont(THEME.font(14, QFont.Weight.Medium))
            p.drawText(plot, Qt.AlignmentFlag.AlignCenter, "No history yet")
            p.end()
            return
        lo, hi = min(data), max(data)
        if hi - lo < 1e-9:
            lo, hi = lo - 1.0, hi + 1.0
        p.drawText(QRectF(0, 0, self.width(), 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
                   f"{lo:.1f} to {hi:.1f}" if hi - lo < 10 else f"{lo:.0f} to {hi:.0f}")
        n = len(data)
        pts = [QPointF(plot.left() + plot.width() * i / (n - 1), plot.bottom() - (v - lo) / (hi - lo) * plot.height())
               for i, v in enumerate(data)]
        col = THEME.color(self.color_key)
        top_c, bot_c = QColor(col), QColor(col)
        top_c.setAlpha(60)
        bot_c.setAlpha(0)
        grad = QLinearGradient(QPointF(0, plot.top()), QPointF(0, plot.bottom()))
        grad.setColorAt(0.0, top_c)
        grad.setColorAt(1.0, bot_c)
        area = QPainterPath()
        area.moveTo(pts[0].x(), plot.bottom())
        for pt in pts:
            area.lineTo(pt)
        area.lineTo(pts[-1].x(), plot.bottom())
        area.closeSubpath()
        p.fillPath(area, grad)
        pen = QPen(col, 3.0)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        for i in range(1, n):
            p.drawLine(pts[i - 1], pts[i])
        p.end()


def _label_style(label, key="text"):
    label.setStyleSheet(f"background: transparent; color: {THEME.hex(key)};")


def _layout_value_card(card, color_key, chart=None):
    """Value card for the layout pass: caption, 96 px value with 32 px unit, 18 px context line, sparkline."""
    card.setMaximumWidth(16777215)
    card.setMaximumHeight(16777215)
    lay = card.content_layout()
    lay.setContentsMargins(28, 22, 28, 18)
    caption = None
    for label in card.findChildren(QLabel):
        if label is not getattr(card, "value", None):
            caption = label
            label.setFont(THEME.font(CAPTION_PX, QFont.Weight.ExtraBold))
    card.value.hide()                                   # still holds the text; _BigValue draws it
    card.sw7_big = _BigValue(card.value, color_key)
    card.sw7_context = QLabel("")
    card.sw7_context.setFont(THEME.font(CONTEXT_PX, QFont.Weight.Medium))
    card.sw7_context.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    card.sw7_spark = _Sparkline(chart, color_key) if chart is not None else None
    lay.insertStretch(1, 1)
    lay.insertWidget(2, card.sw7_big)
    lay.insertWidget(3, card.sw7_context)
    if card.sw7_spark is not None:
        lay.addWidget(card.sw7_spark)

    def colours():
        if caption is not None:
            _label_style(caption)
        _label_style(card.sw7_context, "text_dim")

    THEME.changed.connect(colours)
    colours()
    card.sw7_caption = caption


def _context_lines(page, s):
    """One short line per value card (18 px), from the same state update_state() shows."""
    def num(name):
        v = getattr(s, name, None)
        return None if v is None or isinstance(v, bool) else float(v)
    soc, rng = num("soc_pct"), num("range_km")
    try:
        from ..asis.config import VEHICLE_SPEC
        cap_wh = float(getattr(VEHICLE_SPEC, "battery_capacity_wh", None) or 7200.0)
    except Exception:  # noqa: BLE001
        cap_wh = 7200.0
    if soc is None:
        soc_line = "No battery data"
    else:
        soc_line = f"{soc / 100.0 * cap_wh / 1000.0:.1f} of {cap_wh / 1000.0:.1f} kWh left"
        if rng is not None:
            soc_line += f" · about {rng:.0f} km"
    trip = num("trip_km")
    return {
        "s_soc": soc_line,
        "s_btemp": "Battery pack",
        "s_atemp": "Outside air",
        "s_odo": "Total distance" + (f" · this trip {trip:.1f} km" if trip else ""),
        "s_power": "Drawn from the battery now",
        "s_eff": "Energy used per km",
    }


def _paint_chart(chart, name, _event):
    """The team's MiniChart drawn with real ranges, 12 px axis text and a 24 px current value."""
    S = getattr(chart, "sw7_paper", None)
    if S is not None:
        return _paint_chart_paper(chart, name, S)
    p = QPainter(chart)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    w, h = chart.width(), chart.height()
    dim, text = QColor(THEME.hex("text_dim")), QColor(THEME.hex("text"))
    data = list(chart._data)
    p.setPen(text)
    p.setFont(THEME.font(CHART_TITLE_PX, QFont.Weight.DemiBold))
    p.drawText(QRectF(96, 4, w - 96 - 150, 26), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, chart._title)
    p.setPen(THEME.color(chart._color_key))
    p.setFont(THEME.font(CHART_VALUE_PX, QFont.Weight.Bold))
    digits = 2 if name == "dist_chart" and data and abs(data[-1]) < 10 else 1   # short trips: metres matter
    current = f"{data[-1]:.{digits}f} {chart._unit}" if data else f"-- {chart._unit}"
    p.drawText(QRectF(8, 0, w - 16, 34), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, current)

    left = 60.0
    plot = QRectF(left, 44, w - left - 18, h - 44 - 46)
    fixed = CHART_RANGES.get(name)
    if fixed is not None:
        lo, hi = fixed
        if data:
            lo = min(lo, min(data))
            top = max(data)
            if top > hi:                                  # never clip: widen to the next round step
                step = 10.0 ** math.floor(math.log10(max(1.0, top)))
                hi = math.ceil(top / step) * step
    elif len(data) >= 1:                                  # distance: fitted to the data
        lo, hi = min(data), max(data)
        pad = max(0.05, (hi - lo) * 0.1)
        lo, hi = lo - pad, hi + pad
    else:
        lo, hi = 0.0, 1.0
    rng = (hi - lo) or 1.0

    axis = QColor(THEME.hex("border"))
    axis.setAlpha(160)
    p.setPen(QPen(axis, 1.5))
    p.drawLine(QPointF(plot.left(), plot.top()), QPointF(plot.left(), plot.bottom()))
    p.drawLine(QPointF(plot.left(), plot.bottom()), QPointF(plot.right(), plot.bottom()))
    grid = QColor(THEME.hex("border"))
    grid.setAlpha(70)
    p.setPen(QPen(grid, 1, Qt.PenStyle.DashLine))
    for i in range(1, 4):
        y = plot.top() + plot.height() * i / 4
        p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))

    p.setPen(dim)
    p.setFont(THEME.font(AXIS_PX, QFont.Weight.Medium))
    fmt = "{:.0f}" if rng >= 10 else "{:.1f}" if rng >= 1 else "{:.2f}"
    for frac in (0.0, 0.5, 1.0):
        val, y = lo + rng * frac, plot.bottom() - plot.height() * frac
        p.drawText(QRectF(18, y - 9, left - 24, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, fmt.format(val))
    p.save()
    p.translate(10, plot.center().y())
    p.rotate(-90)
    p.drawText(QRectF(-50, -9, 100, 18), Qt.AlignmentFlag.AlignCenter, chart._unit)
    p.restore()
    _, _, label_full, label_half = chart.TIMELINES[chart._combo.currentIndex()]
    for label, x, align in ((label_full, plot.left(), Qt.AlignmentFlag.AlignLeft),
                            (label_half, plot.center().x() - 30, Qt.AlignmentFlag.AlignHCenter),
                            ("now", plot.right() - 60, Qt.AlignmentFlag.AlignRight)):
        p.drawText(QRectF(x, plot.bottom() + 4, 60, 18), align | Qt.AlignmentFlag.AlignVCenter, label)
    p.drawText(QRectF(plot.left(), plot.bottom() + 22, plot.width(), 18), Qt.AlignmentFlag.AlignHCenter, "Time")

    if len(data) < 2:
        p.setFont(THEME.font(14, QFont.Weight.Medium))
        p.drawText(plot, Qt.AlignmentFlag.AlignCenter, "No data yet" if not data else "One point so far")
        p.end()
        return
    n = len(data)
    pts = [QPointF(plot.left() + plot.width() * i / (n - 1), plot.bottom() - (v - lo) / rng * plot.height())
           for i, v in enumerate(data)]
    col = THEME.color(chart._color_key)
    top_c, bot_c = QColor(col), QColor(col)
    top_c.setAlpha(50)
    bot_c.setAlpha(0)
    grad = QLinearGradient(QPointF(0, plot.top()), QPointF(0, plot.bottom()))
    grad.setColorAt(0.0, top_c)
    grad.setColorAt(1.0, bot_c)
    area = QPainterPath()
    area.moveTo(pts[0].x(), plot.bottom())
    for pt in pts:
        area.lineTo(pt)
    area.lineTo(pts[-1].x(), plot.bottom())
    area.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.fillPath(area, grad)
    pen = QPen(col, 2.5)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    for i in range(1, n):
        p.drawLine(pts[i - 1], pts[i])
    chart.sw7_range = (lo, hi)
    p.end()


def _layout_chart(chart, name):
    """Instance overrides on the team's MiniChart (its class and the TUKZIE_SW7_LAYOUT=0 look stay as they are)."""
    import types
    chart.sw7_range = CHART_RANGES.get(name)
    chart.paintEvent = types.MethodType(lambda self, e: _paint_chart(self, name, e), chart)
    chart.setMinimumHeight(200)

    def restyle():
        bg = THEME.hex('bg_alt') if not THEME.is_light else "rgba(255, 255, 255, 0.7)"
        chart._combo.setStyleSheet(f"""
            QComboBox {{ background: {bg}; color: {THEME.hex('text')}; border: 1px solid {THEME.hex('border')};
                         border-radius: 6px; padding: 2px 8px; font-weight: bold; font-size: {AXIS_PX + 2}px; }}
            QComboBox::drop-down {{ border: none; width: 18px; }}
            QComboBox QAbstractItemView {{ background: {THEME.hex('card')}; color: {THEME.hex('text')};
                selection-background-color: {THEME.hex('accent')}; border: 1px solid {THEME.hex('border')};
                font-size: {AXIS_PX + 4}px; }}
        """)
        chart._combo.setGeometry(8, 2, 84, 32)

    def resize(self, event):
        type(self).resizeEvent(self, event)
        self._combo.setGeometry(8, 2, 84, 32)

    chart.resizeEvent = types.MethodType(resize, chart)
    THEME.changed.connect(restyle)
    restyle()


def install_carousel(page, root, grid, chart_grid):
    from .analytics_page import _GradientCard          # the team's card, so the look matches

    stats = [page.s_soc, page.s_btemp, page.s_atemp, page.s_odo, page.s_power, page.s_eff]
    chart_cards = [chart_grid.itemAt(i).widget() for i in range(chart_grid.count())]
    for w in stats:
        grid.removeWidget(w)
    S = _style() if layout_enabled() else None
    if S is not None:   # paper: battery %, battery temp and ambient temp have their homes elsewhere (merge plan, A)
        for w in (page.s_soc, page.s_btemp, page.s_atemp):
            w.hide()
        stats = [page.s_odo, page.s_power, page.s_eff]
    for w in chart_cards:
        chart_grid.removeWidget(w)
    root.removeItem(grid)
    root.removeItem(chart_grid)
    root.removeWidget(page.insights)
    layout_pass = layout_enabled()
    if layout_pass:
        sparks = {"s_soc": (page.soc_chart, "normal"), "s_odo": (page.dist_chart, "accent"),
                  "s_eff": (page.eff_chart, "info")}
        keys = {"s_soc": "normal", "s_btemp": "warn", "s_atemp": "info", "s_odo": "accent",
                "s_power": "accent", "s_eff": "info"}
        for name, key in keys.items():
            chart, _ = sparks.get(name, (None, None))
            _layout_value_card(getattr(page, name), key, chart)
        for name in CHART_RANGES:
            _layout_chart(getattr(page, name), name)
        root.setContentsMargins(24, 12, 24, 12)
        title_label = root.itemAt(0).widget() if root.count() else None   # the team's "Analytics" title
        team_update = page.update_state

        def update_state(s):
            team_update(s)
            lines = _context_lines(page, s)
            for name in keys:
                card = getattr(page, name)
                card.sw7_context.setText(lines[name])
                card.sw7_big.update()
                if card.sw7_spark is not None:
                    card.sw7_spark.update()

        page.update_state = update_state
        page.open_log.setMinimumHeight(BUTTON_PX)
        page.open_log.setFont(THEME.font(16, QFont.Weight.Bold))
    else:
        for w in stats:
            _enlarge_value_card(w)
    page.insight_title.setFont(THEME.font(20, QFont.Weight.Bold))
    page.insight_body.setFont(THEME.font(18, QFont.Weight.Medium))

    # the Graphs card
    graphs_card = _GradientCard("accent")
    lay = graphs_card.content_layout()
    lay.setContentsMargins(24, 20, 24, 20)
    title = QLabel("GRAPHS")
    title.setFont(THEME.font(20, QFont.Weight.ExtraBold))
    body = QLabel("Speed, battery %, distance and consumption over time")
    body.setFont(THEME.font(26, QFont.Weight.Bold))
    body.setWordWrap(True)
    hint = QLabel("Tap to open  ›")
    hint.setFont(THEME.font(18, QFont.Weight.DemiBold))
    lay.addStretch(1)                                  # text centred vertically in the card
    for lbl in (title, body, hint):
        lbl.setStyleSheet("background: transparent;")
        lay.addWidget(lbl)
    lay.addStretch(1)
    hint.setStyleSheet(f"background: transparent; color: {THEME.hex('accent')};")

    items = stats + [graphs_card, page.insights]
    graphs_index = len(stats)

    # carousel view: carousel, plus arrows and dots on the right
    carousel_view = QWidget()
    row = QHBoxLayout(carousel_view)
    row.setContentsMargins(0, 0, 0, 0)
    carousel = InfiniteCarousel(items)
    row.addWidget(carousel, 1)
    side = QVBoxLayout()
    up, down = QPushButton("▲"), QPushButton("▼")
    names = ["Battery %", "Battery temp", "Ambient temp", "Odometer", "Battery output", "Consumption",
             "Graphs", "Driver insights"]
    if S is not None:
        names = ["Odometer", "Battery output", "Consumption", "Graphs", "Driver insights"]
    dots = _Dots(len(items), names=names if layout_pass else None)
    for b in (up, down):
        b.setFixedSize(*((BUTTON_PX, BUTTON_PX) if layout_pass else (56, 56)))
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.setFont(THEME.font(18, QFont.Weight.Bold))
    right = Qt.AlignmentFlag.AlignRight if layout_pass else Qt.AlignmentFlag(0)
    side.addWidget(up, 0, right)
    side.addWidget(dots, 1)
    side.addWidget(down, 0, right)
    row.addLayout(side)
    up.clicked.connect(lambda: carousel.step(-1))
    down.clicked.connect(lambda: carousel.step(1))
    carousel.current_changed.connect(dots.set_current)

    # graphs view: the four charts, larger, with a back button
    graphs_view = _ShadowHost(S) if S is not None else QWidget()
    gv = QVBoxLayout(graphs_view)
    gv.setContentsMargins(0, 0, 0, 0)
    top = QHBoxLayout()
    back = QPushButton("‹  Back")
    back.setFixedHeight(48)
    back.setFont(THEME.font(16, QFont.Weight.Bold))
    back.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    heading = QLabel("Graphs")
    heading.setFont(THEME.font(20, QFont.Weight.Bold))
    heading.setStyleSheet("background: transparent;")
    top.addWidget(back)
    top.addSpacing(12)
    top.addWidget(heading)
    top.addStretch(1)
    gv.addLayout(top)
    cg = QGridLayout()
    cg.setSpacing(10)
    for i, card in enumerate(chart_cards):
        for chart in (page.speed_chart, page.soc_chart, page.dist_chart, page.eff_chart):
            chart.setMaximumHeight(16777215)
        cg.addWidget(card, i // 2, i % 2)
    gv.addLayout(cg, 1)
    if layout_pass:
        back.setFixedHeight(BUTTON_PX)
        back.setMinimumWidth(140)
        back.setFont(THEME.font(18, QFont.Weight.Bold))
        heading.setFont(THEME.font(24, QFont.Weight.Bold))
        gv.setSpacing(12)
        cg.setSpacing(16)

        def colours():                                  # explicit colours: never dark on dark
            for lbl in (heading, title, body) + ((title_label,) if isinstance(title_label, QLabel) else ()):
                _label_style(lbl)
            hint.setStyleSheet(f"background: transparent; color: {THEME.hex('accent')};")
            _label_style(page.insight_title)
            _label_style(page.insight_body)

        THEME.changed.connect(colours)
        colours()

    stack = QStackedWidget()
    stack.addWidget(carousel_view)
    stack.addWidget(graphs_view)
    root.addWidget(stack, 1)

    def activated(i):
        if i == graphs_index:
            stack.setCurrentWidget(graphs_view)

    carousel.item_activated.connect(activated)
    back.clicked.connect(lambda: stack.setCurrentWidget(carousel_view))
    page.sw7_carousel, page.sw7_stack = carousel, stack
    page.sw7_graphs_view, page.sw7_carousel_view, page.sw7_graphs_index = graphs_view, carousel_view, graphs_index
    page.sw7_back, page.sw7_up, page.sw7_down = back, up, down
    if S is not None:
        _install_paper(page, S, carousel, dots, graphs_card, (title, body, hint), heading, title_label, chart_cards)
    return carousel


# ---- paper and depth style (12 Oct 2026, Planning/paper-depth-theme-prompt.md sections 3 to 5 and 10) ------------
# Behind TUKZIE_SW7_STYLE (paper by default; "team", or a build without sw7_style, keeps everything above exactly).
#   - five cards instead of eight: Odometer, Battery output, Consumption, Graphs, Driver insights (battery %, battery
#     temp and ambient temp have their homes in the status bar, Charging and Diagnostics);
#   - each value card: one huge value (S.HERO) in ink, the unit at 22 px, a 13 px caps label, a 16 px context line;
#   - flat paper cards on cached warm shadows (the carousel and the graphs view paint them, so the cards keep their
#     opacity effect and nothing that repaints often carries a live effect);
#   - charts in ink: ink_3 axes, 13 px text, one status-colour line (ok) over a faint ink wash;
#   - signal only on what reacts to a tap: the up and down buttons, Back, the chart period boxes, "Tap to open" on
#     the Graphs card; the position dots are information, so ink;
#   - Driver insights keep only the latest-trip summary (the live route text is on the Map).
def _style():
    try:
        from ..widgets import sw7_style as S
    except ImportError:
        return None
    return S if S.enabled() else None


class _ShadowHost(QWidget):
    """A plain container that paints cached card shadows under the children listed in .shadowed."""

    def __init__(self, S, parent=None):
        super().__init__(parent)
        self.S, self.shadowed = S, []

    def paintEvent(self, _event):
        p = QPainter(self)
        for w in self.shadowed:
            if w.isVisible():
                self.S.paint_shadow(p, QRectF(w.geometry()), PAPER_RADIUS, 1)
        p.end()


class _GraphsPreview(QWidget):
    """Paper Graphs card: the four histories as small ink sparklines (13 px caps names, one ok line each)."""

    def __init__(self, S, charts, parent=None):
        super().__init__(parent)
        self.S, self.charts = S, charts
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)   # taps go to the carousel
        self.setMinimumHeight(180)
        THEME.changed.connect(self.update)

    def paintEvent(self, _event):
        S = self.S
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        gap = 24.0
        cw = (self.width() - gap) / 2.0
        ch = (self.height() - gap) / 2.0
        for i, chart in enumerate(self.charts):
            r = QRectF((i % 2) * (cw + gap), (i // 2) * (ch + gap), cw, ch)
            p.setPen(S.c("ink_2"))
            p.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True))
            p.drawText(QRectF(r.left(), r.top(), r.width(), 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       chart._title.replace(" vs Time", "").upper())
            plot = QRectF(r.left(), r.top() + 24, r.width(), r.height() - 28)
            p.setPen(QPen(S.c("hairline"), 1))
            p.drawLine(plot.bottomLeft(), plot.bottomRight())
            data = list(chart._data)
            if len(data) >= 2:
                lo, hi = min(data), max(data)
                if hi - lo < 1e-9:
                    lo, hi = lo - 1.0, hi + 1.0
                _paper_line(p, S, plot, data, lo, hi)
        p.end()


def _paper_card_paint(card, S):
    p = QPainter(card)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(S.c("hairline"), 1.0))
    p.setBrush(S.c("card"))
    p.drawRoundedRect(QRectF(card.rect()).adjusted(0.5, 0.5, -0.5, -0.5), PAPER_RADIUS, PAPER_RADIUS)
    p.end()


def _paint_spark_paper(spark, S, data):
    p = QPainter(spark)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(S.c("ink_2"))
    p.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True))
    p.drawText(QRectF(0, 0, spark.width(), 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, "RECENT")
    plot = QRectF(0, 24, spark.width(), spark.height() - 28)
    p.setPen(QPen(S.c("hairline"), 1))
    p.drawLine(plot.bottomLeft(), plot.bottomRight())
    if len(data) < 2:
        p.setPen(S.c("ink_3"))
        p.setFont(S.font(S.BODY))
        p.drawText(plot, Qt.AlignmentFlag.AlignCenter, "No history yet")
        p.end()
        return
    lo, hi = min(data), max(data)
    if hi - lo < 1e-9:
        lo, hi = lo - 1.0, hi + 1.0
    p.setPen(S.c("ink_2"))
    p.drawText(QRectF(0, 0, spark.width(), 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
               f"{lo:.1f} to {hi:.1f}" if hi - lo < 10 else f"{lo:.0f} to {hi:.0f}")
    _paper_line(p, S, plot, data, lo, hi)
    p.end()


def _paper_line(p, S, plot, data, lo, hi):
    """One ink line over a faint ink wash (a chart line is data, not a status)."""
    n = len(data)
    rng = (hi - lo) or 1.0
    pts = [QPointF(plot.left() + plot.width() * i / (n - 1), plot.bottom() - (v - lo) / rng * plot.height())
           for i, v in enumerate(data)]
    grad = QLinearGradient(QPointF(0, plot.top()), QPointF(0, plot.bottom()))
    grad.setColorAt(0.0, S.c("ink", 12))
    grad.setColorAt(1.0, S.c("ink", 0))
    area = QPainterPath()
    area.moveTo(pts[0].x(), plot.bottom())
    for pt in pts:
        area.lineTo(pt)
    area.lineTo(pts[-1].x(), plot.bottom())
    area.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.fillPath(area, grad)
    pen = QPen(S.c("ink"), 2.0)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    line = QPainterPath(pts[0])
    for pt in pts[1:]:
        line.lineTo(pt)
    p.drawPath(line)


def _paint_chart_paper(chart, name, S):
    """A MiniChart in paper: 13 px caps title, the current value at 16 px bold, ink_3 axes, one ok line."""
    p = QPainter(chart)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    w, h = chart.width(), chart.height()
    data = list(chart._data)
    p.setPen(S.c("ink_2"))
    p.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True))
    p.drawText(QRectF(112, 2, w - 112 - 150, 34), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
               chart._title.upper())
    p.setPen(S.c("ink"))
    p.setFont(S.mono(S.BODY, QFont.Weight.Medium))
    digits = 2 if name == "dist_chart" and data and abs(data[-1]) < 10 else 1
    current = f"{data[-1]:.{digits}f} {chart._unit}" if data else f"-- {chart._unit}"
    p.drawText(QRectF(8, 2, w - 22, 34), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, current)
    fixed = CHART_RANGES.get(name)
    if fixed is not None:
        lo, hi = fixed
        if data:
            lo = min(lo, min(data))
            top = max(data)
            if top > hi:
                step = 10.0 ** math.floor(math.log10(max(1.0, top)))
                hi = math.ceil(top / step) * step
    elif data:
        lo, hi = min(data), max(data)
        pad = max(0.05, (hi - lo) * 0.1)
        lo, hi = lo - pad, hi + pad
    else:
        lo, hi = 0.0, 1.0
    rng = (hi - lo) or 1.0
    fmt = "{:.0f}" if rng >= 10 else "{:.1f}" if rng >= 1 else "{:.2f}"
    fm = QFontMetricsF(S.mono(S.LABEL, QFont.Weight.Normal))
    left = max(60.0, 34.0 + max(fm.horizontalAdvance(fmt.format(lo + rng * k)) for k in (0.0, 0.5, 1.0)))
    plot = QRectF(left, 48, w - left - 18, h - 48 - 46)
    p.setPen(QPen(S.c("hairline"), 1))
    for i in range(1, 4):
        y = plot.top() + plot.height() * i / 4
        p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
    p.setPen(QPen(S.c("ink_3"), 1.5))
    p.drawLine(QPointF(plot.left(), plot.top()), QPointF(plot.left(), plot.bottom()))
    p.drawLine(QPointF(plot.left(), plot.bottom()), QPointF(plot.right(), plot.bottom()))
    p.setPen(S.c("ink_2"))
    p.setFont(S.mono(S.LABEL, QFont.Weight.Normal))
    for frac in (0.0, 0.5, 1.0):
        val, y = lo + rng * frac, plot.bottom() - plot.height() * frac
        p.drawText(QRectF(22, y - 9, left - 30, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   fmt.format(val))
    p.save()
    p.translate(10, plot.center().y())
    p.rotate(-90)
    p.drawText(QRectF(-50, -9, 100, 18), Qt.AlignmentFlag.AlignCenter, chart._unit)
    p.restore()
    _, _, label_full, label_half = chart.TIMELINES[chart._combo.currentIndex()]
    for label, x, align in ((label_full, plot.left(), Qt.AlignmentFlag.AlignLeft),
                            (label_half, plot.center().x() - 30, Qt.AlignmentFlag.AlignHCenter),
                            ("now", plot.right() - 60, Qt.AlignmentFlag.AlignRight)):
        p.drawText(QRectF(x, plot.bottom() + 4, 60, 18), align | Qt.AlignmentFlag.AlignVCenter, label)
    p.drawText(QRectF(plot.left(), plot.bottom() + 22, plot.width(), 18), Qt.AlignmentFlag.AlignHCenter, "Time")
    chart.sw7_range = (lo, hi)
    if len(data) < 2:
        p.setPen(S.c("ink_3"))
        p.setFont(S.font(S.BODY))
        p.drawText(plot, Qt.AlignmentFlag.AlignCenter, "No data yet" if not data else "One point so far")
        p.end()
        return
    _paper_line(p, S, plot, data, lo, hi)
    p.end()


def _paper_label(label, S, px, colour="ink", weight=QFont.Weight.Normal, caps=False):
    label.setFont(S.font(px, weight, caps=caps))
    if caps:
        label.setText(label.text().upper())
    label.setStyleSheet(f"background: transparent; color: {S.hx(colour)};")


def _install_paper(page, S, carousel, dots, graphs_card, graphs_texts, heading, title_label, chart_cards):
    import types
    page.paintEvent = types.MethodType(lambda self, e: None, page)   # the back plane (sw7_style) shows through
    page.layout().setContentsMargins(24, 8, 24, 16)   # the nav bar no longer covers the page (sw7_style)
    carousel.sw7_paper = dots.sw7_paper = S
    cards = [page.s_odo, page.s_power, page.s_eff, graphs_card, page.insights] + list(chart_cards)
    for card in cards:
        card.paintEvent = types.MethodType(lambda self, e: _paper_card_paint(self, S), card)
    page.sw7_graphs_view.shadowed = list(chart_cards)
    for card in (page.s_odo, page.s_power, page.s_eff):
        card.sw7_big.sw7_paper = S
        card.sw7_big.setFixedHeight(int(S.HERO * 1.15))
        card.content_layout().setContentsMargins(32, 26, 32, 22)
        if card.sw7_spark is not None:
            card.sw7_spark.sw7_paper = S
    for name in CHART_RANGES:
        getattr(page, name).sw7_paper = S
    title, body, hint = graphs_texts
    S.mark_tappable(graphs_card)                      # the carousel opens it on a tap
    lay = graphs_card.content_layout()
    lay.setContentsMargins(32, 26, 32, 28)
    while lay.count() and lay.itemAt(0).spacerItem() is not None:     # text at the top, the previews under it
        lay.takeAt(0)
    if lay.count() and lay.itemAt(lay.count() - 1).spacerItem() is not None:
        lay.takeAt(lay.count() - 1)
    lay.setSpacing(8)
    preview = _GraphsPreview(S, [page.speed_chart, page.soc_chart, page.dist_chart, page.eff_chart])
    lay.addSpacing(16)
    lay.addWidget(preview, 1)
    page.sw7_graphs_preview = preview
    layout_update = page.update_state

    def update_state(s):
        layout_update(s)
        preview.update()

    page.update_state = update_state
    page.update_support = lambda support: None        # insights keep the latest trip only; the route is on the Map

    def restyle():
        for card in (page.s_odo, page.s_power, page.s_eff):
            for box in card.findChildren(QWidget):
                if hasattr(box, "_draw") and hasattr(box, "_key"):   # the team's icon: off, the caption is enough
                    box.hide()
            if card.sw7_caption is not None:
                _paper_label(card.sw7_caption, S, S.LABEL, "ink_2", QFont.Weight.Bold, caps=True)
            _paper_label(card.sw7_context, S, S.BODY, "ink_2")
        _paper_label(title, S, S.LABEL, "ink_2", QFont.Weight.Bold, caps=True)
        _paper_label(body, S, S.SECONDARY, "ink", QFont.Weight.Bold)
        _paper_label(hint, S, S.BODY, "signal", QFont.Weight.Bold)
        _paper_label(page.insight_title, S, S.LABEL, "ink_2", QFont.Weight.Bold, caps=True)
        _paper_label(page.insight_body, S, S.BODY, "ink")
        _paper_label(heading, S, S.SECONDARY, "ink", QFont.Weight.Bold)
        if isinstance(title_label, QLabel):
            _paper_label(title_label, S, S.LABEL, "ink_2", QFont.Weight.Bold, caps=True)
        for b, r in ((page.sw7_up, BUTTON_PX // 2), (page.sw7_down, BUTTON_PX // 2), (page.sw7_back, BUTTON_PX // 2),
                     (page.open_log, 24)):
            b.setFont(S.font(S.BODY, QFont.Weight.Bold))
            b.setStyleSheet(S.button_qss("outline", r, S.BODY) +
                            f" QPushButton:disabled{{background:{S.hx('card_alt')};color:{S.hx('ink_3')};"
                            f"border:1px solid {S.hx('hairline')};}}")
        for name in CHART_RANGES:
            combo = getattr(page, name)._combo
            combo.setStyleSheet(f"""
                QComboBox {{ background: {S.hx('card')}; color: {S.hx('signal')}; border: 1px solid {S.rgba('signal', 0.55)};
                             border-radius: 6px; padding: 2px 10px; font-weight: 600; font-size: {S.LABEL}px; }}
                QComboBox::drop-down {{ border: none; width: 16px; }}
                QComboBox QAbstractItemView {{ background: {S.hx('card')}; color: {S.hx('ink')};
                    selection-background-color: {S.hx('signal_tint')}; selection-color: {S.hx('ink')};
                    border: 1px solid {S.hx('hairline')}; font-size: {S.BODY}px; }}
            """)
            combo.setGeometry(8, 2, 84, 32)
        page.update()

    THEME.changed.connect(restyle)
    restyle()
    page.sw7_paper = True
