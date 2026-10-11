"""SW-7: swipe between dashboard pages with two fingers (three on the map).

Two fingers moved together sideways go to the next page (swipe left) or the previous one (swipe right), in the
order of the dashboard's own arrows (dashboard_main.navigate_pages). On the map two fingers zoom, so there three
fingers are needed; the rest of the Navigation page takes two. One finger is never used here, so scrolling, taps,
the Analytics carousel and the map's drag are unchanged. Touch events are read at the window, before the widgets,
and never consumed. A short slide of the old page shows the change. Planning/page-swipe-prompt.md.
"""
import time

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPointF, QPropertyAnimation, Qt
from PySide6.QtGui import QEventPoint, QWindow
from PySide6.QtWidgets import QApplication, QLabel

SWIPE_PX = 140         # sideways travel of the fingers' centre
SWIPE_RATIO = 1.8      # at least this much more sideways than up or down
SWIPE_S = 1.0          # within this time of the required fingers landing
SLIDE_MS = 220
TOUCH = (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd, QEvent.Type.TouchCancel)


class PageSwipe(QObject):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.changes = 0                    # page changes made by swipes (tests, log)
        self._reset()
        QApplication.instance().installEventFilter(self)

    def _reset(self):
        self._first = None                  # global position of the first finger of this gesture
        self._start = None                  # (centre, time, fingers needed) once enough fingers are down
        self._fired = False

    # ---- where the gesture began ----------------------------------------------------------------
    def _map_under(self, gpos):
        m = getattr(getattr(self.main, "navigation", None), "map", None)
        if m is None or not m.isVisible():
            return False
        return m.rect().contains(m.mapFromGlobal(gpos.toPoint()))

    # ---- touch ----------------------------------------------------------------------------------
    def eventFilter(self, obj, event):
        if isinstance(obj, QWindow) and event.type() in TOUCH:
            try:
                self._touch(event)
            except Exception as exc:          # a gesture bug must never block the touchscreen
                print(f"[SW-7] page swipe: {exc}")
        return False

    def _touch(self, event):
        kind = event.type()
        down = [p for p in event.points() if p.state() != QEventPoint.State.Released]
        if kind == QEvent.Type.TouchBegin:
            self._reset()
            if event.points():
                self._first = event.points()[0].globalPosition()
        if kind in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel) or not down:
            self._reset()
            return
        if self._fired or self._first is None or not self.main.isVisible():
            return
        need = 3 if self._map_under(self._first) else 2
        n = len(down)
        centre = sum((p.globalPosition() for p in down), QPointF()) / n
        if n >= need and (self._start is None or n != self._start[3]):
            self._start = (centre, time.monotonic(), need, n)      # (re)start once the fingers are all down
            return
        if self._start is None or n < self._start[2]:
            return
        c0, t0, _, _ = self._start
        dx, dy = centre.x() - c0.x(), centre.y() - c0.y()
        if time.monotonic() - t0 > SWIPE_S:
            self._start = (centre, time.monotonic(), need, n)      # too slow: measure afresh from here
            return
        if abs(dx) >= SWIPE_PX and abs(dx) >= SWIPE_RATIO * abs(dy):
            self._fired = True
            self.go(+1 if dx < 0 else -1)

    # ---- page change with a short slide ----------------------------------------------------------
    def go(self, direction):
        stack = getattr(self.main, "stack", None)
        old = stack.currentWidget() if stack is not None else None
        shot = old.grab() if old is not None and old.isVisible() else None
        self.main.navigate_pages(direction)
        self.changes += 1
        if shot is None or stack is None or stack.currentWidget() is old:
            return
        overlay = QLabel(stack)
        overlay.setPixmap(shot)
        overlay.setGeometry(0, 0, stack.width(), stack.height())
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        overlay.show()
        overlay.raise_()
        anim = QPropertyAnimation(overlay, b"pos", overlay)
        anim.setDuration(SLIDE_MS)
        anim.setStartValue(QPoint(0, 0))
        anim.setEndValue(QPoint(-stack.width() if direction > 0 else stack.width(), 0))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(overlay.deleteLater)
        anim.start()


def install(main):
    if getattr(main, "_sw7_page_swipe", None) is None:
        main._sw7_page_swipe = PageSwipe(main)
    return main._sw7_page_swipe
