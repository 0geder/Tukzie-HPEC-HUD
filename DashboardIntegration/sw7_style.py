"""SW-7 paper and depth style: palette, type scale, elevation, back plane, signal audit and the restyled frame.

Planning/paper-depth-theme-prompt.md (from thetheme_reference.jpg). Installed as app/widgets/sw7_style.py;
dashboard_main.py calls install(DashboardMain) once at import time, after the layout pass (sw7_layout_frame).

API for the page agents (everything else in this file is the frame and can be ignored)
-------------------------------------------------------------------------------------------
    from ..widgets import sw7_style as S        # from app/pages; "from . import sw7_style" in app/widgets

    S.enabled()            True for the paper style (TUKZIE_SW7_STYLE unset or "paper", and the layout pass on).
                           False for "team": then do nothing, the page must look exactly as before.
    S.is_night()           True while the Ink (night) variant is shown.

  Colours (always read them at paint or restyle time; they change at sunset)
    S.hx("signal")         "#B9562F" (hex string, for QSS)      S.c("ink") QColor     S.c("shadow", 60) QColor, alpha 60
    S.rgba("ink", 0.5)     "rgba(30,26,23,0.5)" for QSS
    tokens: paper, paper_deep, card, card_alt, hairline, ink, ink_2, ink_3, charcoal, on_charcoal, on_charcoal_2,
            signal, signal_pressed, signal_tint, shadow, ok, warn, critical, warn_tint
    THEME follows the palette in paper mode: THEME.hex("bg")=paper, "card"=card, "accent"=signal, "text"=ink,
    "text_dim"=ink_2, "text_faint"=ink_3, "border"=hairline, status normal/warn/crit = ok/warn/critical,
    "info"=ink_2. So team code that reads THEME follows automatically. THEME.changed fires on day/night switches:
    connect it and restyle.
    Rule: signal only on things you can tap. Status colours only as small marks (dot, bar, ring segment, word).

  Type (bundled Atkinson Hyperlegible; sizes in px)
    S.HERO (150), S.HERO_MIN 120, S.HERO_MAX 180: the page's one hero value
    S.SECONDARY 22 (at most 3 per page), S.BODY 16, S.LABEL 13 (labels, units, caps section labels in ink_2)
    S.font(px, weight=QFont.Weight.Normal, caps=False)  -> QFont; caps=True adds letter spacing for caps labels
    S.type_audit(root) -> [(widget, px)] for visible text widgets outside {13, 16, 22, 120..180}

  Depth (three planes)
    Back plane:   S.set_back_word(page, "DRIVE", corner="bl")  giant faint word behind a ThemedPageSurface page
                  S.attach_back_plane(widget, "CHARGE")         same for any other QWidget page (paints under it)
                  S.paint_back_plane(p, rect, word, corner="bl", px=260)  if you paint the page yourself
    Middle/top:   S.elevate(widget, level=2)   QGraphicsDropShadowEffect, warm. Only for widgets that do not
                  repaint every frame (not the map, not the live speed): for those paint a cached shadow:
                  S.paint_card(p, rect, radius=24, level=2, fill="card")   shadow pixmap (cached) + card
                  S.paint_shadow(p, rect, radius=24, level=2)              shadow only
                  levels: 1 = chips and small buttons (blur 24, y 8), 2 = cards (blur 32, y 12),
                          3 = floating slabs and sheets (blur 40, y 16)
    The nav bar is a floating pill. The page stack runs NAV_OVERLAP (16) px under it, so keep tap targets out
    of the bottom 16 px of a page, and the selected item's circle reaches 24 px into the page in the middle.

  Buttons
    S.style_button(btn, kind="outline"|"filled", radius=None, px=16)   signal outline (card fill, signal ink)
                   or filled (signal fill, card ink); THEME.stylesheet() already does "outline" for every
                   QPushButton, ":checked" is filled.
    S.mark_exempt(widget, "reason")    a tappable widget that deliberately has no signal (e.g. the obstacle text)
    S.mark_tappable(widget)            a custom widget that reacts to taps (not a QAbstractButton)

  Tests
    S.audit_signal(root, ignore=(map_widget,)) -> list of Finding(widget, kind, pixels, note)
        kind "info_in_signal": a non-tappable widget painted more than S.MARK_PX px in or near the signal hue
        (hue within 15 degrees, saturation over 35 %; small status marks up to MARK_PX are allowed)
        kind "tap_without_signal": a visible, enabled tappable widget with no signal pixels
    S.ok_audit(findings) -> "" or a readable list

  Weather: sw7_weather.py (WeatherService, the status-bar chip and the charcoal WeatherCard).

TUKZIE_SW7_STYLE=team installs nothing (the layout-pass look exactly). TUKZIE_SW7_NIGHT=1 / 0 forces the Ink / Paper
variant; unset, the weather service's sunrise and sunset choose (Paper when unknown).
"""
from __future__ import annotations

import os
from collections import namedtuple

STYLE_ENV = "TUKZIE_SW7_STYLE"
NIGHT_ENV = "TUKZIE_SW7_NIGHT"

# ---- palette ------------------------------------------------------------------------------------------------------
DAY = {
    "paper": "#F3ECE6", "paper_deep": "#E7DCD3", "card": "#FBF8F5", "card_alt": "#F6F0EA", "hairline": "#E3D9D0",
    "ink": "#1E1A17", "ink_2": "#6B625B", "ink_3": "#A89F98",
    "charcoal": "#34353A", "on_charcoal": "#FBF8F5", "on_charcoal_2": "#B4AFAA",
    "signal": "#B9562F", "signal_pressed": "#96421F", "signal_tint": "#F1DDD2",
    "shadow": "#6E4A32",
    "ok": "#4F7A55", "warn": "#C98A16", "critical": "#B3261E", "warn_tint": "#F2E0B8",
}
NIGHT = {
    "paper": "#1C1A18", "paper_deep": "#24211F", "card": "#26231F", "card_alt": "#2C2925", "hairline": "#3A3531",
    "ink": "#F3ECE6", "ink_2": "#B5ABA3", "ink_3": "#7E756E",
    "charcoal": "#36373C", "on_charcoal": "#F3ECE6", "on_charcoal_2": "#A9A39E",
    "signal": "#D9744A", "signal_pressed": "#B85C35", "signal_tint": "#4A2C20",
    "shadow": "#070504",
    "ok": "#86B08C", "warn": "#E0A63A", "critical": "#E25A4E", "warn_tint": "#4A3B1C",
}
SHADOW_ALPHA = {False: (0.18, 0.22, 0.28), True: (0.45, 0.55, 0.65)}     # day, night; by level 1..3
LEVELS = {1: (24, 8), 2: (32, 12), 3: (40, 16)}                         # blur radius, y offset

# ---- type scale ---------------------------------------------------------------------------------------------------
HERO_MIN, HERO, HERO_MAX = 120, 150, 180
SECONDARY, BODY, LABEL = 22, 16, 13
TEXT_SIZES = (LABEL, BODY, SECONDARY)

# ---- frame sizes (1280 x 800, on top of the layout pass) --------------------------------------------------------
NAV_H = 72                  # the layout pass's nav row: the pill and its 64 px targets
NAV_FLOAT_H = 88            # the floating nav overlay: 16 px more for the raised circle
NAV_OVERLAP = 16            # the page stack runs this far under the pill
PILL_TOP, PILL_H = 16, 64   # the pill inside the overlay
CIRCLE_D = 52               # the selected item's raised circle
NAV_BTN_H = 80              # nav targets: 80 px tall (the circle and the label), at least 96 px wide
CHIP_W, CHIP_H = 132, 28
MARK_PX = 420               # audit: signal-like pixels allowed in one non-tappable widget (a status dot, a bar)

_night = None               # None: not decided yet (day)


def enabled() -> bool:
    if os.environ.get(STYLE_ENV, "paper").strip().lower() == "team":
        return False
    return os.environ.get("TUKZIE_SW7_LAYOUT", "1").strip() != "0"


def forced_night():
    v = os.environ.get(NIGHT_ENV, "").strip()
    return None if v == "" else v not in ("0", "false", "no")


def is_night() -> bool:
    forced = forced_night()
    if forced is not None:
        return forced
    return bool(_night)


def palette() -> dict:
    return NIGHT if is_night() else DAY


def hx(key: str) -> str:
    return palette()[key]


def c(key: str, alpha: int | None = None):
    from PySide6.QtGui import QColor
    col = QColor(palette()[key])
    if alpha is not None:
        col.setAlpha(int(alpha))
    return col


def rgba(key: str, a: float) -> str:
    col = c(key)
    return f"rgba({col.red()},{col.green()},{col.blue()},{a:.3f})"


def blend(a: str, b: str, t: float) -> str:
    from PySide6.QtGui import QColor
    ca, cb = QColor(a), QColor(b)
    return QColor(round(ca.red() * (1 - t) + cb.red() * t), round(ca.green() * (1 - t) + cb.green() * t),
                  round(ca.blue() * (1 - t) + cb.blue() * t)).name()


def set_night(on: bool):
    """Switch the variant (the weather service calls this at sunrise and sunset). Emits THEME.changed."""
    global _night
    on = bool(on)
    if _night is on:
        return
    before = is_night()
    _night = on
    if is_night() != before:
        _theme_changed()


def _theme_changed():
    _SHADOW_CACHE.clear(); _PLANE_CACHE.clear()
    try:
        from ..theme import THEME
        THEME.changed.emit()
    except Exception:
        pass


# ---- fonts --------------------------------------------------------------------------------------------------------
_family = None


def family() -> str:
    global _family
    if _family is None:
        from PySide6.QtGui import QFontDatabase
        import glob
        here = os.path.dirname(os.path.abspath(__file__))
        for folder in (os.path.join(here, "..", "fonts"), os.path.join(here, "fonts")):
            for path in glob.glob(os.path.join(folder, "*.ttf")):
                QFontDatabase.addApplicationFont(path)
        fams = set(QFontDatabase.families())
        _family = next((f for f in ("Atkinson Hyperlegible", "B612", "Inter", "DejaVu Sans") if f in fams), "Sans Serif")
    return _family


def font(px: int, weight=None, caps: bool = False):
    from PySide6.QtGui import QFont
    f = QFont(family())
    f.setPixelSize(int(px))
    f.setWeight(QFont.Weight.Normal if weight is None else weight)
    if caps:
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 108)
    if px >= HERO_MIN:
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 96)
    return f


def text_px(widget) -> int:
    f = widget.font()
    return f.pixelSize() if f.pixelSize() > 0 else round(f.pointSizeF() * 96 / 72)


def type_audit(root):
    """Visible QLabel / QAbstractButton with text whose font size is outside the scale."""
    from PySide6.QtWidgets import QAbstractButton, QLabel
    out = []
    for w in [root] + root.findChildren(QLabel) + root.findChildren(QAbstractButton):
        if not hasattr(w, "text") or not w.isVisibleTo(root.window()) or not w.isVisible() or not str(w.text()).strip():
            continue
        px = text_px(w)
        if px not in TEXT_SIZES and not (HERO_MIN <= px <= HERO_MAX):
            out.append((w, px))
    return out


# ---- elevation ----------------------------------------------------------------------------------------------------
_SHADOW_CACHE = {}


def _shadow_colour(level):
    col = c("shadow")
    col.setAlphaF(SHADOW_ALPHA[is_night()][max(1, min(3, level)) - 1])
    return col


def elevate(widget, level: int = 2):
    """A warm drop shadow on a widget that does not animate. Returns the effect (or None if not paper)."""
    from PySide6.QtWidgets import QGraphicsDropShadowEffect
    blur, dy = LEVELS[max(1, min(3, level))]
    eff = widget.graphicsEffect()
    if not isinstance(eff, QGraphicsDropShadowEffect):
        eff = QGraphicsDropShadowEffect(widget)
        widget.setGraphicsEffect(eff)
    eff.setBlurRadius(blur); eff.setOffset(0, dy); eff.setColor(_shadow_colour(level))
    widget.setProperty("sw7_level", level)
    if not widget.property("sw7_elev_hooked"):
        widget.setProperty("sw7_elev_hooked", True)
        try:
            from ..theme import THEME
            THEME.changed.connect(lambda w=widget: _re_elevate(w))
        except Exception:
            pass
    return eff


def _re_elevate(widget):
    try:
        eff = widget.graphicsEffect()
        if eff is not None and hasattr(eff, "setColor"):
            eff.setColor(_shadow_colour(int(widget.property("sw7_level") or 2)))
    except RuntimeError:
        pass


def shadow_pixmap(w: int, h: int, radius: float, level: int = 2):
    """(pixmap, margin): the blurred shadow of a w x h rounded rect, cached. Draw it at (x - margin, y - margin + dy)."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QImage, QPainter, QPixmap
    from PySide6.QtWidgets import QGraphicsBlurEffect, QGraphicsPixmapItem, QGraphicsScene
    level = max(1, min(3, level))
    key = (int(w), int(h), round(radius, 1), level, is_night())
    hit = _SHADOW_CACHE.get(key)
    if hit is not None:
        return hit
    blur, _dy = LEVELS[level]
    m = blur
    src = QImage(int(w) + 2 * m, int(h) + 2 * m, QImage.Format.Format_ARGB32_Premultiplied)
    src.fill(Qt.GlobalColor.transparent)
    p = QPainter(src); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(_shadow_colour(level))
    p.drawRoundedRect(QRectF(m, m, w, h), radius, radius); p.end()
    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(QPixmap.fromImage(src))
    eff = QGraphicsBlurEffect(); eff.setBlurRadius(blur * 0.9)
    eff.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(eff); scene.addItem(item)
    out = QImage(src.size(), QImage.Format.Format_ARGB32_Premultiplied); out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out); scene.render(p, QRectF(out.rect()), QRectF(0, 0, out.width(), out.height())); p.end()
    res = (QPixmap.fromImage(out), m)
    if len(_SHADOW_CACHE) > 64:
        _SHADOW_CACHE.clear()
    _SHADOW_CACHE[key] = res
    return res


def paint_shadow(p, rect, radius: float = 24, level: int = 2):
    from PySide6.QtCore import QPointF
    pix, m = shadow_pixmap(int(rect.width()), int(rect.height()), radius, level)
    p.drawPixmap(QPointF(rect.x() - m, rect.y() - m + LEVELS[max(1, min(3, level))][1]), pix)


def paint_card(p, rect, radius: float = 24, level: int = 2, fill: str = "card", outline: str | None = None):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QPen
    rect = QRectF(rect)
    if level:
        paint_shadow(p, rect, radius, level)
    p.save(); p.setRenderHint(p.RenderHint.Antialiasing)
    p.setPen(QPen(c(outline), 1.5) if outline else Qt.PenStyle.NoPen); p.setBrush(c(fill))
    p.drawRoundedRect(rect, radius, radius); p.restore()


# ---- back plane ---------------------------------------------------------------------------------------------------
_PLANE_CACHE = {}


def paint_back_plane(p, rect, word: str = "", corner: str = "bl", px: int = 260, ground=None):
    """Paper ground with the page's word huge and faint (paper_deep), bleeding off the given corner (bl, br, tl, tr).
    ground: optional QPainterPath(s) filled with paper_deep (a road or ground shape). Cached as a pixmap."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QFont, QFontMetrics, QPainter, QPixmap
    rect = QRectF(rect)
    key = (int(rect.width()), int(rect.height()), word, corner, px, is_night(), id(ground) if ground is not None else 0)
    pix = _PLANE_CACHE.get(key)
    if pix is None:
        pix = QPixmap(max(1, int(rect.width())), max(1, int(rect.height())))
        pix.fill(c("paper"))
        q = QPainter(pix); q.setRenderHint(QPainter.RenderHint.Antialiasing); q.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        if ground is not None:
            q.setPen(Qt.PenStyle.NoPen); q.setBrush(c("paper_deep"))
            for path in (ground if isinstance(ground, (list, tuple)) else [ground]):
                q.drawPath(path)
        if word:
            f = font(px, QFont.Weight.Bold); f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 92)
            q.setFont(f); q.setPen(c("paper_deep"))
            fm = QFontMetrics(f)
            tw = fm.horizontalAdvance(word)
            x = -px * 0.06 if corner in ("bl", "tl") else pix.width() - tw + px * 0.06
            # bottom corners: about 60 % of the capitals show above the floating nav pill
            y = pix.height() - NAV_OVERLAP + px * 0.22 if corner in ("bl", "br") else fm.ascent() - px * 0.22
            q.drawText(int(x), int(y), word)
        q.end()
        if len(_PLANE_CACHE) > 24:
            _PLANE_CACHE.clear()
        _PLANE_CACHE[key] = pix
    p.drawPixmap(int(rect.x()), int(rect.y()), pix)


def set_back_word(page, word: str, corner: str = "bl", px: int = 260):
    page.setProperty("sw7_word", word); page.setProperty("sw7_word_corner", corner); page.setProperty("sw7_word_px", px)
    page.update()


def attach_back_plane(widget, word: str = "", corner: str = "bl", px: int = 260):
    """Paint the back plane under any QWidget page (an event filter paints before the widget's own paintEvent)."""
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtGui import QPainter

    class F(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.Type.Paint and enabled():
                p = QPainter(obj)
                paint_back_plane(p, obj.rect(), obj.property("sw7_word") or "", obj.property("sw7_word_corner") or "bl",
                                 int(obj.property("sw7_word_px") or 260))
                p.end()
            return False

    set_back_word(widget, word, corner, px)
    f = F(widget); widget.installEventFilter(f); widget._sw7_plane = f
    return f


# ---- buttons ------------------------------------------------------------------------------------------------------
def button_qss(kind: str = "outline", radius: int = 16, px: int = BODY, selector: str = "QPushButton") -> str:
    if kind == "filled":
        return (f"{selector}{{background:{hx('signal')};color:{hx('card')};border:none;border-radius:{radius}px;"
                f"font-size:{px}px;font-weight:700;padding:0px 16px;}}"
                f" {selector}:pressed{{background:{hx('signal_pressed')};}}")
    return (f"{selector}{{background:{hx('card')};color:{hx('signal')};border:2px solid {hx('signal')};"
            f"border-radius:{radius}px;font-size:{px}px;font-weight:700;padding:0px 16px;}}"
            f" {selector}:pressed{{background:{hx('signal_tint')};}}"
            f" {selector}:checked{{background:{hx('signal')};color:{hx('card')};}}")


def style_button(btn, kind: str = "outline", radius: int | None = None, px: int = BODY):
    r = radius if radius is not None else min(32, max(12, btn.height() // 2 if btn.height() > 0 else 16))
    btn.setStyleSheet(button_qss(kind, r, px))


def mark_exempt(widget, reason: str):
    widget.setProperty("sw7_signal_exempt", reason)


def mark_tappable(widget, on: bool = True):
    widget.setProperty("sw7_tap", bool(on))


# ---- signal audit -------------------------------------------------------------------------------------------------
Finding = namedtuple("Finding", "widget kind pixels note")


def _hue_sat(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == 0 or mx == mn:
        return None, 0.0
    d = mx - mn
    if mx == r:
        h = 60.0 * (((g - b) / d) % 6)
    elif mx == g:
        h = 60.0 * ((b - r) / d + 2)
    else:
        h = 60.0 * ((r - g) / d + 4)
    return h, d / mx


def signal_like(r, g, b, signal=None) -> bool:
    """Hue within 15 degrees of the signal hue and saturation over 35 % (section 4 of the brief)."""
    from PySide6.QtGui import QColor
    sig = QColor(signal or hx("signal"))
    sh, _ = _hue_sat(sig.red(), sig.green(), sig.blue())
    h, s = _hue_sat(r, g, b)
    if h is None or s <= 0.35:
        return False
    d = abs(h - sh) % 360
    return min(d, 360 - d) <= 15


def is_tappable(w) -> bool:
    from PySide6.QtWidgets import QAbstractButton, QAbstractSlider, QComboBox, QLineEdit, QScrollBar
    tap = w.property("sw7_tap")
    if tap is not None:
        return bool(tap)
    if not w.isEnabled():
        return False
    if isinstance(w, QScrollBar):
        return False            # a position indicator: lists scroll by finger (sw7_touch)
    return isinstance(w, (QAbstractButton, QAbstractSlider, QComboBox, QLineEdit))


def _tap_owner(w, root):
    while w is not None:
        if is_tappable(w):
            return w
        if w is root:
            return None
        w = w.parentWidget()
    return None


def audit_signal(root, ignore=(), mark_px: int = MARK_PX, step: int = 2, image=None):
    """Grab root, find every pixel in or near the signal hue and give it to the widget under it (childAt, the
    widget that would get the tap). Returns Findings (see the module API)."""
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtWidgets import QWidget
    img = (image or root.grab().toImage()).convertToFormat(QImage.Format.Format_RGB32)
    w, h = img.width(), img.height()
    sig = QColor(hx("signal"))
    sh, _ = _hue_sat(sig.red(), sig.green(), sig.blue())
    ignored = [x for x in ignore if x is not None]

    def under_ignored(x):
        while x is not None:
            if any(x is i for i in ignored):
                return True
            x = x.parentWidget()
        return False

    buf = bytes(img.constBits())
    bpl = img.bytesPerLine()
    tap_hits, info_hits, info_status = {}, {}, {}
    status_cols = [QColor(hx(k)) for k in ("critical", "warn", "ok")]
    cache = {}
    for y in range(0, h, step):
        row = y * bpl
        for x in range(0, w, step):
            i = row + 4 * x
            b, g, r = buf[i], buf[i + 1], buf[i + 2]
            mx = r if r > g else g
            if b > mx:
                mx = b
            mn = r if r < g else g
            if b < mn:
                mn = b
            if mx == 0 or (mx - mn) <= 0.35 * mx:
                continue
            hh, _s = _hue_sat(r, g, b)
            d = abs(hh - sh) % 360
            if min(d, 360 - d) > 15:
                continue
            cell = (x // 4, y // 4)
            owner = cache.get(cell)
            if owner is None:
                cw = root.childAt(QPoint(x, y)) or root
                owner = cache[cell] = cw
            if under_ignored(owner):
                continue
            tap = _tap_owner(owner, root)
            if tap is not None:
                tap_hits[id(tap)] = (tap, tap_hits.get(id(tap), (tap, 0))[1] + step * step)
            else:
                near_status = min(abs(r - q.red()) + abs(g - q.green()) + abs(b - q.blue()) for q in status_cols) < \
                    abs(r - sig.red()) + abs(g - sig.green()) + abs(b - sig.blue())
                book = info_status if near_status else info_hits
                book[id(owner)] = (owner, book.get(id(owner), (owner, 0))[1] + step * step)
    out = []
    for key, (wd, n) in info_hits.items():
        out.append(Finding(wd, "info_in_signal", n, "signal-coloured but not tappable"))
    for key, (wd, n) in info_status.items():
        if n > mark_px:
            out.append(Finding(wd, "info_in_signal", n, f"status colour near the signal hue over {mark_px} px"))
    for wd in [root] + root.findChildren(QWidget):
        if not wd.isVisible() or not is_tappable(wd) or under_ignored(wd) or wd.property("sw7_signal_exempt"):
            continue
        g = wd.geometry()
        if wd.width() < 8 or wd.height() < 8:
            continue
        top = wd.mapTo(root, QPoint(0, 0))
        if top.x() >= w or top.y() >= h or top.x() + wd.width() <= 0 or top.y() + wd.height() <= 0:
            continue
        if not _really_visible(wd, root, top):
            continue
        if tap_hits.get(id(wd), (wd, 0))[1] < 12:
            out.append(Finding(wd, "tap_without_signal", 0, "tappable but no signal colour"))
    return out


def _really_visible(wd, root, top):
    """The widget's centre is not covered by another widget (it is what a tap there would reach)."""
    from PySide6.QtCore import QPoint
    centre = QPoint(top.x() + wd.width() // 2, top.y() + wd.height() // 2)
    hit = root.childAt(centre)
    while hit is not None:
        if hit is wd:
            return True
        hit = hit.parentWidget()
    # a widget transparent for mouse events over it, or a child covering the centre: check a few more points
    for fx, fy in ((0.25, 0.5), (0.75, 0.5), (0.5, 0.25), (0.5, 0.75)):
        hit = root.childAt(QPoint(top.x() + int(wd.width() * fx), top.y() + int(wd.height() * fy)))
        while hit is not None:
            if hit is wd:
                return True
            hit = hit.parentWidget()
    return False


def describe(w) -> str:
    from PySide6.QtWidgets import QAbstractButton, QLabel
    text = ""
    if isinstance(w, (QLabel, QAbstractButton)):
        text = str(w.text())[:30]
    return f"{type(w).__name__}#{w.objectName() or '-'} {text!r}"


def ok_audit(findings) -> str:
    return "; ".join(f"{f.kind}: {describe(f.widget)} ({f.pixels} px)" for f in findings)


# ---- THEME in paper mode --------------------------------------------------------------------------------------------
def _theme_token(key):
    p = palette()
    return {"bg": p["paper"], "bg_alt": p["paper"], "card": p["card"], "card_alt": p["card_alt"],
            "accent": p["signal"], "highlight": p["ink"], "text": p["ink"], "text_dim": p["ink_2"],
            "text_faint": p["ink_3"], "border": p["hairline"], "track": p["paper_deep"]}.get(key, p["ink"])


def _theme_status(key):
    p = palette()
    return {"normal": p["ok"], "warn": p["warn"], "crit": p["critical"], "inactive": p["ink_3"],
            "info": p["ink_2"], "regen": p["ok"]}.get(key, p["ink_3"])


def paper_stylesheet() -> str:
    p = palette()
    return f"""
        QWidget {{ color: {p['ink']}; selection-background-color: {p['signal_tint']}; selection-color: {p['ink']}; }}
        QLabel, QAbstractButton#iconButton, QWidget#transparentContainer {{ background: transparent; }}
        QFrame#card {{ background-color: {p['card']}; border: none; border-radius: 24px; }}
        QFrame#cardAlt {{ background-color: {p['card_alt']}; border: none; border-radius: 20px; }}
        QLabel#dim {{ color: {p['ink_2']}; background: transparent; }}
        QLabel#faint {{ color: {p['ink_3']}; background: transparent; }}
        QPushButton {{ background-color: {p['card']}; color: {p['signal']}; border: 2px solid {p['signal']};
            border-radius: 16px; padding: 8px 16px; font-weight: 700; }}
        QPushButton:pressed {{ background-color: {p['signal_tint']}; }}
        QPushButton:checked {{ background-color: {p['signal']}; color: {p['card']}; border: 2px solid {p['signal']}; }}
        QPushButton:disabled {{ color: {p['ink_3']}; border-color: {p['hairline']}; background-color: {p['card_alt']}; }}
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background-color: {p['card']}; color: {p['ink']};
            border: 2px solid {p['signal']}; border-radius: 14px; padding: 7px 12px; }}
        QComboBox QAbstractItemView, QMenu {{ background-color: {p['card']}; color: {p['ink']};
            border: 1px solid {p['hairline']}; selection-background-color: {p['signal_tint']}; selection-color: {p['ink']}; }}
        QCheckBox {{ background: transparent; spacing: 12px; }}
        QCheckBox::indicator {{ width: 44px; height: 24px; border-radius: 12px; background: {p['paper_deep']};
            border: 2px solid {p['signal']}; }}
        QCheckBox::indicator:checked {{ background: {p['signal']}; border-color: {p['signal']}; }}
        QSlider::groove:horizontal {{ height: 8px; border-radius: 4px; background: {p['paper_deep']}; }}
        QSlider::handle:horizontal {{ width: 28px; margin: -10px 0; border-radius: 14px; background: {p['signal']}; }}
        QSlider::sub-page:horizontal {{ background: {p['signal']}; border-radius: 4px; }}
        QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
        QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
        QScrollBar::handle:vertical {{ background: {p['hairline']}; min-height: 28px; border-radius: 4px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """


def _swrap(cls, name, after=None, replace=None):
    """Like sw7_layout_frame._wrap, with its own marker, so it can wrap a method the layout pass wrapped."""
    orig = getattr(cls, name)
    if getattr(orig, "_sw7_style", False):
        return
    if replace is not None:
        def method(self, *a, **k):
            return replace(orig, self, *a, **k)
    else:
        def method(self, *a, **k):
            result = orig(self, *a, **k)
            after(self, *a, **k)
            return result
    method._sw7_style = True
    method.__name__ = name
    setattr(cls, name, method)


def install_theme():
    """THEME produces the Paper (or Ink) palette, the paper stylesheet and the bundled font."""
    from .. import theme as theme_mod
    T = theme_mod.Theme
    _swrap(T, "_token", replace=lambda orig, self, key: _theme_token(key))
    _swrap(T, "status", replace=_status_colour)
    _swrap(T, "stylesheet", replace=lambda orig, self: paper_stylesheet())
    _swrap(T, "_pick_font_family", replace=lambda orig, self: family())
    if not getattr(T, "_sw7_is_light", False):
        T.is_light = property(lambda self: not is_night())
        T._sw7_is_light = True
    theme_mod.THEME._family = None
    from ..widgets import themed_surfaces as ts
    _swrap(ts.ThemedPageSurface, "paintEvent", replace=_surface_paint)
    _swrap(ts.ThemedCard, "paintEvent", replace=_card_paint)


def _status_colour(orig, theme, key):
    from PySide6.QtGui import QColor
    return QColor(_theme_status(key))


def _surface_paint(orig, page, event):
    from PySide6.QtGui import QPainter
    from PySide6.QtWidgets import QWidget
    p = QPainter(page)
    paint_back_plane(p, page.rect(), page.property("sw7_word") or "", page.property("sw7_word_corner") or "bl",
                     int(page.property("sw7_word_px") or 260))
    p.end()
    QWidget.paintEvent(page, event)


def _card_paint(orig, card, event):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QPainter
    from PySide6.QtWidgets import QFrame
    p = QPainter(card); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(c("card"))
    p.drawRoundedRect(QRectF(card.rect()), 20, 20); p.end()
    QFrame.paintEvent(card, event)


# ---- the frame ----------------------------------------------------------------------------------------------------
BACK_WORDS = {"driving": "DRIVE", "analytics": "TRIPS", "diagnostics": "HEALTH", "camera": "ROAD",
              "sensors": "AROUND", "charging": "CHARGE", "settings": "SETUP"}

_installed = False


def install(main_cls):
    """Called once from dashboard_main.py, after sw7_layout_frame.install_classes. Nothing with TUKZIE_SW7_STYLE=team."""
    global _installed
    if _installed or not enabled():
        return
    _installed = True
    install_theme()
    from . import status_bar, nav_bar, icon_registry
    _install_status_bar(status_bar.DashboardStatusBar, status_bar.BatteryLevelIcon)
    _install_nav(nav_bar.BottomNavigation)
    _swrap(icon_registry.IconButton, "refresh", after=_icon_refresh)
    _swrap(main_cls, "__init__", after=_main_init)
    _swrap(main_cls, "_apply_theme", after=_main_theme)
    _swrap(main_cls, "_position_arrows", replace=_position_frame)
    _swrap(main_cls, "switch_page_id", after=lambda m, *a, **k: m.nav.update() if hasattr(m, "nav") else None)
    try:
        from ..pages import sw7_sim_link
        _install_chip(sw7_sim_link)
    except ImportError:
        pass


def _icon_refresh(button, *_a, **_k):
    from PySide6.QtCore import QSize
    from .icon_registry import icon
    if button.objectName() == "sideArrow":
        col = c("signal")
    elif getattr(button, "sw7_nav", False):
        col = c("card") if button.isChecked() else c("signal")
        size = 26 if button.isChecked() else 28
        button.setIcon(icon(button.name, size, col)); button.setIconSize(QSize(size, size))
        return
    else:
        col = c("card") if button.isChecked() else c("signal")
    button.setIcon(icon(button.name, button.icon_size, col)); button.setIconSize(QSize(button.icon_size, button.icon_size))


# status bar ----------------------------------------------------------------------------------------------------------
def _install_status_bar(cls, battery_cls):
    def theme_after(bar, *_a, **_k):
        from PySide6.QtGui import QFont
        bar.setStyleSheet(f"QFrame#dashboardStatusBar{{background:{hx('paper')};border:none;"
                          f"min-height:48px;max-height:48px;}} QLabel{{color:{hx('ink')};background:transparent;}}")
        bar.clock.setFont(font(BODY, QFont.Weight.Bold))
        bar.soc.setFont(font(BODY, QFont.Weight.Bold))
        if getattr(bar, "_state", None) is not None:
            bar.update_state(bar._state)
        if hasattr(bar, "sw7_weather_chip"):
            bar.sw7_weather_chip.update()

    _swrap(cls, "_apply_theme", after=theme_after)
    _swrap(cls, "__init__", after=theme_after)      # after the layout pass's own __init__ sizes


# nav pill ------------------------------------------------------------------------------------------------------------
def _install_nav(cls):
    def init_after(nav, *_a, **_k):
        from PySide6.QtCore import Qt
        nav.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        for b in nav.buttons.values():
            b.sw7_nav = True
            b.setFixedHeight(NAV_BTN_H)
            lab = getattr(b, "sw7_label", None)
            if lab is not None and b.layout() is not None:
                b.layout().setContentsMargins(2, 0, 2, 5)
            b.refresh()
        _nav_theme(nav)

    def paint(orig, nav, event):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter
        p = QPainter(nav); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pill = _pill_rect(nav)
        paint_card(p, pill, PILL_H / 2, 2)
        sel = next((b for b in nav.buttons.values() if b.isChecked() and b.isVisible()), None)
        if sel is not None:
            cx = sel.geometry().center().x() + 0.5
            circle = QRectF(cx - CIRCLE_D / 2, PILL_TOP - 8, CIRCLE_D, CIRCLE_D)
            paint_shadow(p, circle, CIRCLE_D / 2, 1)
            from PySide6.QtCore import Qt
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(c("signal")); p.drawEllipse(circle)
        p.end()

    _swrap(cls, "__init__", after=init_after)
    _swrap(cls, "_theme", after=lambda nav, *a, **k: _nav_theme(nav))
    _swrap(cls, "paintEvent", replace=paint)
    _swrap(cls, "select", after=lambda nav, *a, **k: nav.update())


def _pill_rect(nav):
    from PySide6.QtCore import QRectF
    left = getattr(nav, "sw7_pill_x", (88, nav.width() - 88))
    return QRectF(left[0], PILL_TOP, left[1] - left[0], PILL_H)


def _nav_theme(nav):
    """Transparent buttons over the painted pill; the icon sits higher in the selected item (its circle).
    Label colours come from the layout pass (accent = signal when checked, text_dim = ink_2)."""
    if not any(hasattr(b, "sw7_label") for b in nav.buttons.values()):
        return
    from PySide6.QtGui import QFont
    nav.setStyleSheet(
        f"QFrame#bottomNavigation{{background:transparent;border:none;min-height:{NAV_FLOAT_H}px;max-height:{NAV_FLOAT_H}px;}}"
        " QFrame#bottomNavigation QPushButton{background:transparent;border:none;border-radius:0px;"
        "padding:12px 0px 10px 0px;}"
        " QFrame#bottomNavigation QPushButton:checked{background:transparent;border:none;padding:0px 0px 16px 0px;}"
        " QFrame#bottomNavigation QPushButton:pressed{background:transparent;}")
    for b in nav.buttons.values():
        lab = getattr(b, "sw7_label", None)
        if lab is not None:
            lab.setFont(font(LABEL, QFont.Weight.Bold))
    nav.update()


# shell: nav overlay, arrows, back words, weather --------------------------------------------------------------------
def _main_init(main, *_a, **_k):
    from PySide6.QtWidgets import QWidget
    host = main.centralWidget()
    root = host.layout()
    # The nav bar floats: it leaves the layout (a spacer keeps the pages NAV_OVERLAP px under it) and is placed
    # over the bottom of the page stack by _position_frame.
    idx = root.indexOf(main.nav)
    if idx >= 0:
        root.removeWidget(main.nav)
        spacer = QWidget(); spacer.setObjectName("sw7NavSpacer"); spacer.setFixedHeight(NAV_H - NAV_OVERLAP)
        spacer.setStyleSheet("background:transparent;")
        root.insertWidget(idx, spacer)
        main.sw7_nav_spacer = spacer
    main.nav.setParent(host); main.nav.show()
    main.nav.setFixedHeight(NAV_FLOAT_H)
    lay = main.nav.layout()
    m = lay.contentsMargins()
    lay.setContentsMargins(m.left(), 2, m.right(), NAV_FLOAT_H - 2 - NAV_BTN_H)
    for b in (main.left, main.right):
        b.setFixedSize(64, 64)
        elevate(b, 1)
        b.refresh()
    for pid, word in BACK_WORDS.items():
        page = main.page_by_id.get(pid) if hasattr(main, "page_by_id") else None
        if page is None:
            continue
        from .themed_surfaces import ThemedPageSurface
        if isinstance(page, ThemedPageSurface):
            set_back_word(page, word)
        else:
            attach_back_plane(page, word)
    # hazard pill (sensors_page.HazardBanner) and the weather chip and card
    banner = getattr(main, "hazard_banner", None)
    if banner is not None and hasattr(banner, "sw7_paper"):
        banner.sw7_paper()
    from . import sw7_weather
    sw7_weather.install(main)
    _position_frame(None, main)


def _main_theme(main, *_a, **_k):
    if not hasattr(main, "nav"):
        return
    main.setStyleSheet(main.styleSheet() + f"""
        QPushButton#sideArrow {{ background: {hx('card')}; border: 2px solid {hx('signal')}; border-radius: 32px; padding: 0px; }}
        QPushButton#sideArrow:pressed {{ background: {hx('signal_tint')}; }}
        """)
    for b in (getattr(main, "left", None), getattr(main, "right", None)):
        if b is not None:
            b.refresh()


def _position_frame(orig, main):
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QRegion
    nav, left, right = getattr(main, "nav", None), getattr(main, "left", None), getattr(main, "right", None)
    if nav is None or left is None or right is None or nav.height() != NAV_FLOAT_H:
        return orig(main) if orig is not None else None
    host = main.centralWidget()
    W, H = host.width(), host.height()
    nav.setGeometry(0, H - NAV_FLOAT_H, W, NAV_FLOAT_H)
    edge = 16
    nav.sw7_pill_x = (edge + 64 + 8, W - edge - 64 - 8)
    pill = _pill_rect(nav).toRect()
    nav.setMask(QRegion(QRect(pill.x() - 28, 4, pill.width() + 56, NAV_FLOAT_H - 4)))
    nav.raise_()
    y = H - NAV_FLOAT_H + PILL_TOP + (PILL_H - 64) // 2
    from PySide6.QtCore import QSize
    for b in (left, right):
        if b.icon_size != 28:
            b.icon_size = 28; b.refresh(); b.setIconSize(QSize(28, 28))
    left.setGeometry(edge, y, 64, 64)
    right.setGeometry(W - edge - 64, y, 64, 64)
    left.raise_(); right.raise_()
    banner = getattr(main, "hazard_banner", None)
    if banner is not None and banner.isVisible():
        banner.raise_()
    card = getattr(main, "sw7_weather_card", None)
    if card is not None and card.isVisible():
        card.place(); card.raise_()


# source chip and the SIMULATED strip ----------------------------------------------------------------------------------
def _install_chip(sim_link):
    cls = sim_link._Indicators

    def restyle(marks):
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QLabel
        text, key = sim_link.CHIPS.get(marks.source, ("", None))
        chip = marks.chip
        dot = getattr(chip, "sw7_dot", None)
        if dot is None:
            dot = chip.sw7_dot = QLabel(chip); dot.setFixedSize(8, 8)
        dot_col = {"normal": hx("ok"), "warn": hx("warn")}.get(key, hx("ink_3"))
        dot.setStyleSheet(f"background:{dot_col};border-radius:4px;")
        dot.move(14, (CHIP_H - 8) // 2)
        chip.setFixedSize(CHIP_W, CHIP_H)
        chip.setFont(font(LABEL, QFont.Weight.Bold, caps=True))
        chip.setStyleSheet(f"QLabel#sw7SourceChip {{ background: transparent; color: {hx('ink')};"
                           f" border: 1.5px solid {hx('ink_3')}; border-radius: {CHIP_H // 2}px;"
                           f" padding: 0px 0px 0px 14px; font-size: {LABEL}px; font-weight: 700; }}")
        strip = marks.strip
        strip.setFont(font(LABEL, QFont.Weight.Bold, caps=True))
        strip.setStyleSheet(f"QLabel#sw7SimStrip {{ background: {hx('warn_tint')}; color: {hx('ink')};"
                            f" border-top: 1px solid {hx('warn')}; border-bottom: 1px solid {hx('warn')};"
                            f" font-weight: 700; font-size: {LABEL}px; padding: 3px 10px; }}")
        marks.place()

    def init_after(marks, *_a, **_k):
        from ..theme import THEME
        restyle(marks)
        THEME.changed.connect(lambda m=marks: restyle(m))

    def show_after(marks, *_a, **_k):
        if marks.chip.isVisible():
            restyle(marks)

    _swrap(cls, "__init__", after=init_after)
    _swrap(cls, "show_source", after=show_after)
