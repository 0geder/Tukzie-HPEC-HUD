"""SW-7: carousel-style swipe between dashboard pages with two fingers (three on the map).

Behaves like a phone's page carousel rather than a trigger:
  - nothing happens until the fingers move sideways together (every finger the same way, mostly horizontal, past
    START_PX); holding the screen, resting a hand on it, or a pinch never moves a page;
  - while dragging, the current page follows the fingers and the neighbouring page slides in beside it;
  - on lifting, the change completes only if the drag passed COMMIT_FRACTION of the width or ended in a quick
    flick in the same direction; otherwise the page springs back. Both are animated.
Two fingers anywhere; three on the map itself, where two fingers zoom (the map ignores three-finger touches).
One-finger gestures are never used here. Touch events are read at the window and never consumed, so every widget
behaves as before. Page order is the dashboard's own arrows (dashboard_main.navigate_pages).
Planning/page-swipe-prompt.md.
"""
import time

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, Qt
from PySide6.QtGui import QEventPoint, QWindow
from PySide6.QtWidgets import QApplication, QLabel, QWidget

START_PX = 30            # sideways travel before a drag is recognised
DIRECTION_RATIO = 1.6    # sideways must exceed up/down by this factor to start
TOGETHER = 0.5           # each finger must have moved at least this share of the average, the same way
COMMIT_FRACTION = 0.33   # of the page width, to complete on release
FLICK_PX_PER_S = 900     # or a flick at least this fast (with at least FLICK_MIN_PX of travel)
FLICK_MIN_PX = 80
SETTLE_MS = 200
TOUCH = (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd, QEvent.Type.TouchCancel)


class PageSwipe(QObject):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.changes = 0                    # completed page changes (tests, log)
        self.springbacks = 0                # drags released short and returned
        self._strip = None                  # overlay holding the current and the neighbouring page pictures
        self._anim = None
        self._reset()
        QApplication.instance().installEventFilter(self)

    def _reset(self):
        self._first = None                  # global position of the first finger of this touch sequence
        self._starts = None                 # {finger id: start position} once enough fingers are down
        self._need = 2
        self._dragging = False
        self._done = False                  # this touch sequence has finished its gesture
        self._dx = 0.0
        self._samples = []                  # (time, dx) for the release velocity

    # ---- input ---------------------------------------------------------------------------------
    def eventFilter(self, obj, event):
        if isinstance(obj, QWindow) and event.type() in TOUCH:
            try:
                self._touch(event)
            except Exception as exc:          # a gesture bug must never block the touchscreen
                print(f"[SW-7] page swipe: {exc}")
        return False

    def _map_under(self, gpos):
        m = getattr(getattr(self.main, "navigation", None), "map", None)
        return m is not None and m.isVisible() and m.rect().contains(m.mapFromGlobal(gpos.toPoint()))

    def _touch(self, event):
        kind = event.type()
        pts = event.points()
        if kind == QEvent.Type.TouchBegin:
            self._reset()
            if pts:
                self._first = pts[0].globalPosition()
                self._need = 3 if self._map_under(self._first) else 2
        down = {p.id(): p.globalPosition() for p in pts if p.state() != QEventPoint.State.Released}
        ending = kind in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel)
        if self._dragging and (ending or len(down) < self._need):
            self._release(cancelled=kind == QEvent.Type.TouchCancel)
            return
        if ending:
            self._reset()
            return
        if self._done or self._first is None or self._anim is not None or not self.main.isVisible():
            return
        if len(down) != self._need:          # too few, or extra fingers (a hand, a pinch-and-swipe): start over
            self._starts = None
            return
        if self._starts is None or set(self._starts) != set(down):
            self._starts = dict(down)
            return
        moves = [(down[i].x() - self._starts[i].x(), down[i].y() - self._starts[i].y()) for i in down]
        dx = sum(m[0] for m in moves) / len(moves)
        dy = sum(m[1] for m in moves) / len(moves)
        if not self._dragging:
            together = all(m[0] * dx > 0 and abs(m[0]) >= TOGETHER * abs(dx) for m in moves)
            if abs(dx) >= START_PX and abs(dx) >= DIRECTION_RATIO * abs(dy) and together:
                if not self._begin_drag(dx):
                    self._done = True
                    return
            else:
                if abs(dy) >= START_PX and abs(dy) > abs(dx):
                    self._done = True        # a vertical two-finger move: not a page swipe this time
                return
        self._drag_to(dx)

    # ---- dragging --------------------------------------------------------------------------------
    def _neighbour(self, direction):
        ids = list(getattr(self.main, "normal_ids", []))
        stack = self.main.stack
        current = self.main.page_ids[stack.currentIndex()]
        if not ids:
            return None
        pos = ids.index(current) if current in ids else 0
        return self.main.page_by_id.get(ids[(pos + direction) % len(ids)])

    def _picture(self, page, size):
        if page is None:
            return None
        if not page.isVisible():
            page.resize(size)                # a hidden page lays out at the stack's size before its picture
        return page.grab()

    def _begin_drag(self, dx):
        stack = getattr(self.main, "stack", None)
        if stack is None or stack.width() < 50:
            return False
        size = stack.size()
        current = stack.currentWidget()
        self._targets = {+1: self._neighbour(+1), -1: self._neighbour(-1)}
        pics = {d: self._picture(p, size) for d, p in self._targets.items()}
        here = self._picture(current, size)
        if here is None:
            return False
        w, h = size.width(), size.height()
        strip = QWidget(stack)
        strip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        strip.setGeometry(-w, 0, 3 * w, h)   # [previous | current | next]
        for slot, pic in ((0, pics.get(-1)), (1, here), (2, pics.get(+1))):
            lab = QLabel(strip)
            lab.setGeometry(slot * w, 0, w, h)
            if pic is not None:
                lab.setPixmap(pic)
        strip.show()
        strip.raise_()
        self._strip, self._w = strip, w
        self._dragging = True
        self._samples = []
        return True

    def _drag_to(self, dx):
        self._dx = dx
        now = time.monotonic()
        self._samples = [(t, x) for t, x in self._samples if now - t < 0.12] + [(now, dx)]
        if self._strip is not None:
            self._strip.move(int(-self._w + dx), 0)

    def _release(self, cancelled=False):
        dx, w = self._dx, self._w
        speed = 0.0
        if len(self._samples) >= 2:
            (t0, x0), (t1, x1) = self._samples[0], self._samples[-1]
            if t1 > t0:
                speed = (x1 - x0) / (t1 - t0)
        flick = abs(speed) >= FLICK_PX_PER_S and abs(dx) >= FLICK_MIN_PX and speed * dx > 0
        commit = not cancelled and (abs(dx) >= COMMIT_FRACTION * w or flick)
        direction = +1 if dx < 0 else -1      # fingers moving left bring in the next page
        end_x = (-w - w * direction) if commit else -w
        self._dragging, self._done = False, True
        strip = self._strip
        anim = QPropertyAnimation(strip, b"pos", self)
        anim.setDuration(SETTLE_MS)
        anim.setStartValue(strip.pos())
        anim.setEndValue(QPoint(int(end_x), 0))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def finish():
            if commit:
                self.main.navigate_pages(direction)
                self.changes += 1
            else:
                self.springbacks += 1
            strip.deleteLater()
            self._strip, self._anim = None, None

        anim.finished.connect(finish)
        self._anim = anim
        anim.start()


def install(main):
    if getattr(main, "_sw7_page_swipe", None) is None:
        main._sw7_page_swipe = PageSwipe(main)
    return main._sw7_page_swipe
