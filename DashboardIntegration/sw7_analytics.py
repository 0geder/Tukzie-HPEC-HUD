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
"""
from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QStackedWidget, QVBoxLayout, QWidget)

from ..theme import THEME

ANIM_MS = 250
TAP_SLOP_PX = 10


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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout()

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

    def __init__(self, count, parent=None):
        super().__init__(parent)
        self.count, self.current = count, 0
        self.setFixedWidth(28)
        THEME.changed.connect(self.update)

    def set_current(self, i):
        self.current = i
        self.update()

    def paintEvent(self, _event):
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


def install_carousel(page, root, grid, chart_grid):
    from .analytics_page import _GradientCard          # the team's card, so the look matches

    stats = [page.s_soc, page.s_btemp, page.s_atemp, page.s_odo, page.s_power, page.s_eff]
    chart_cards = [chart_grid.itemAt(i).widget() for i in range(chart_grid.count())]
    for w in stats:
        grid.removeWidget(w)
    for w in chart_cards:
        chart_grid.removeWidget(w)
    root.removeItem(grid)
    root.removeItem(chart_grid)
    root.removeWidget(page.insights)
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
    dots = _Dots(len(items))
    for b in (up, down):
        b.setFixedSize(56, 56)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.setFont(THEME.font(18, QFont.Weight.Bold))
    side.addWidget(up)
    side.addWidget(dots, 1)
    side.addWidget(down)
    row.addLayout(side)
    up.clicked.connect(lambda: carousel.step(-1))
    down.clicked.connect(lambda: carousel.step(1))
    carousel.current_changed.connect(dots.set_current)

    # graphs view: the four charts, larger, with a back button
    graphs_view = QWidget()
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
    return carousel
