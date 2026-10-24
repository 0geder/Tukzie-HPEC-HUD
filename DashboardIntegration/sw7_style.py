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

  Type (bundled IBM Plex Sans and IBM Plex Mono, SIL OFL; Atkinson Hyperlegible stays as the fallback; sizes in px)
    S.HERO (150), S.HERO_MIN 120, S.HERO_MAX 180: the page's one hero value
    S.SECONDARY 22 (at most 3 per page), S.BODY 16, S.LABEL 13 (labels, units, caps section labels in ink_2)
    S.ALERT 35 (the hazard banner) and S.DISTANCE 28 (obstacle distances): safety text sized by visual angle at 0.70 m
    S.font(px, weight=QFont.Weight.Normal, caps=False)  -> QFont in Plex Sans (the interface). Bold and Black map to
                           SemiBold (the heaviest weight bundled, never a synthetic bold); caps=True adds a little
                           letter spacing for the few caps section labels.
    S.mono(px, weight=QFont.Weight.Medium)  -> QFont in Plex Mono: only telemetry values, diagnostics, coordinates and
                           timestamps. Both fonts have tabular figures, so digits never shift when a value changes.
    S.value_font(label, px, weight)  sets Mono on a value label when its text is a figure ("12.3 V", "--") and Sans
                           when it is a word ("Unavailable", "Yes"), so an unavailable value never looks like a number.
    S.type_audit(root) -> [(widget, px)] for visible text widgets outside {13, 16, 22, 35, 120..180}

  Surfaces (the refinement of 12 Oct: restrained, Planning/ui-theme-refinement-prompt.md)
    Back plane:   three planes (Planning/three-planes-hero-prompt.md). S.set_plane(page, S.Plane(word, word_box,
                  anchor, subject, subject_box)) gives a page its hero word (Archivo Black, hero_word colour) and its subject
                  (a cut-out TUKZIE render, assets/tukzie_*.png); both are painted once into a cached pixmap behind
                  every widget. S.PLANES holds each page's placement, S.page_plane_geometry(page) the word and subject
                  rects. S.set_back_word / S.attach_back_plane / S.paint_back_plane keep their API.
    Cards:        S.elevate(widget, level=2)   a very light warm shadow (QGraphicsDropShadowEffect). Only for widgets
                  that do not repaint every frame; for those paint a cached shadow:
                  S.paint_card(p, rect, radius=8, level=2, fill="card")   cached shadow + card + hairline border
                  S.paint_shadow(p, rect, radius=8, level=2)              shadow only
                  levels: 1 = chips and small buttons (blur 8, y 1), 2 = cards (blur 12, y 2),
                          3 = sheets (blur 18, y 4). Radii are clamped to RADIUS_MAX (8 px) unless the shape is a circle.
    The nav bar is a flat bar with a hairline on top, NAV_FLOAT_H (72) px, directly under the page stack: it never
    covers content (NAV_OVERLAP is 0). Unselected items are ink; the selected one is signal with a short signal bar.

  Buttons
    S.style_button(btn, kind="outline"|"filled", radius=None, px=16)   signal outline (card fill, signal ink)
                   or filled (signal fill, card ink); THEME.stylesheet() already does "outline" for every
                   QPushButton, ":checked" is filled.
    S.mark_exempt(widget, "reason")    a tappable widget that deliberately has no signal (e.g. the obstacle text)
    S.mark_quiet(widget)               a tappable that is neither selected nor a key control (an unselected nav item,
                                       the status-bar weather item): ink, no signal, and the audit accepts that
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
    "hero_word": "#D5CFC9",          # ink at 14 % over paper: reads at a glance, never over a value
}
NIGHT = {
    "paper": "#1C1A18", "paper_deep": "#24211F", "card": "#26231F", "card_alt": "#2C2925", "hairline": "#3A3531",
    "ink": "#F3ECE6", "ink_2": "#B5ABA3", "ink_3": "#7E756E",
    "charcoal": "#36373C", "on_charcoal": "#F3ECE6", "on_charcoal_2": "#A9A39E",
    "signal": "#D9744A", "signal_pressed": "#B85C35", "signal_tint": "#4A2C20",
    "shadow": "#070504",
    "ok": "#86B08C", "warn": "#E0A63A", "critical": "#E25A4E", "warn_tint": "#4A3B1C",
    "hero_word": "#363331",          # a lifted charcoal: ink at 12 % over the night paper
}
SHADOW_ALPHA = {False: (0.07, 0.09, 0.12), True: (0.30, 0.36, 0.44)}     # day, night; by level 1..3 (very light)
LEVELS = {1: (8, 1), 2: (12, 2), 3: (18, 4)}                             # blur radius, y offset
RADIUS_MAX = 8              # surfaces: small radii (4 to 8 px); circles stay circles
RADIUS_SM = 4               # chips, bars, small controls
BACK_WORDS_SHOWN = True     # the hero word of the three-planes pass (Planning/three-planes-hero-prompt.md)
SPACE = (4, 8, 12, 16, 24, 32)   # the spacing scale

# ---- type scale ---------------------------------------------------------------------------------------------------
HERO_MIN, HERO, HERO_MAX = 120, 150, 180
SECONDARY, BODY, LABEL = 22, 16, 13
TEXT_SIZES = (LABEL, BODY, SECONDARY)
# Safety text sized by visual angle (24 Oct 2026; panel 0.170 mm/px, eye 0.70 m, BenchTest/legibility_check.py):
# ISO 15008 recommends 20 arc min (24.0 px capitals) and accepts 16 (19.2 px). Plex capitals are 0.698 of the size.
ALERT = 35                  # the hazard banner: 24.4 px capitals, 20.4 arc min
DISTANCE = 28               # obstacle distances (Drive's Around tile, the Surroundings figure): 19.5 px, 16.3 arc min
SANS, MONO = "IBM Plex Sans", "IBM Plex Mono"
FALLBACK = "Atkinson Hyperlegible"
HERO_FACE = "Archivo Black"  # the back-plane word only: heavy and wide (a full-width word stays short enough to sit
                             # in the open space), bundled (SIL OFL, fonts/OFL-ArchivoBlack.txt)

# ---- frame sizes (1280 x 800, on top of the layout pass) --------------------------------------------------------
NAV_H = 72                  # the nav row: a flat bar, its 64 px targets inside
NAV_FLOAT_H = 72            # the nav widget's height (the same: nothing reaches above the bar)
NAV_OVERLAP = 0             # the page stack ends where the bar starts: the bar never covers content
NAV_BAR_TOP = 0             # the bar inside the nav widget
PILL_TOP, PILL_H = NAV_BAR_TOP, NAV_FLOAT_H    # (names kept for the tests and pages that read them)
INDICATOR_W, INDICATOR_H = 40, 3               # the selected item's signal bar, on the bar's top edge
CIRCLE_D = 0                # the raised circle of the depth pass is gone
NAV_BTN_H = 68              # nav targets: 68 px tall, at least 96 px wide
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
_mono = None


def _register_fonts():
    """Register every bundled TTF once (app/fonts in the dashboard, fonts/ beside this file in DashboardIntegration)."""
    from PySide6.QtGui import QFontDatabase
    import glob
    here = os.path.dirname(os.path.abspath(__file__))
    for folder in (os.path.join(here, "..", "fonts"), os.path.join(here, "fonts")):
        for path in sorted(glob.glob(os.path.join(folder, "*.ttf"))):
            QFontDatabase.addApplicationFont(path)
    return set(QFontDatabase.families())


def family() -> str:
    """The interface font: IBM Plex Sans, else the earlier Atkinson Hyperlegible, else a system sans."""
    global _family, _mono
    if _family is None:
        fams = _register_fonts()
        _family = next((f for f in (SANS, FALLBACK, "B612", "Inter", "DejaVu Sans") if f in fams), "Sans Serif")
        _mono = next((f for f in (MONO, "DejaVu Sans Mono", "Consolas") if f in fams), _family)
    return _family


def mono_family() -> str:
    family()
    return _mono


def _weight(weight):
    """Bold and Black map to SemiBold, the heaviest bundled weight (no synthetic bold), DemiBold stays."""
    from PySide6.QtGui import QFont
    W = QFont.Weight
    if weight is None:
        return W.Normal
    v = int(weight.value) if hasattr(weight, "value") else int(weight)
    if v >= 600:
        return W.DemiBold
    if v >= 500:
        return W.Medium
    return W.Normal


def font(px: int, weight=None, caps: bool = False):
    from PySide6.QtGui import QFont
    f = QFont(family())
    f.setPixelSize(int(px))
    f.setWeight(_weight(weight))
    f.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)
    if caps:
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 104)
    if px >= HERO_MIN:
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 97)
    return f


def mono(px: int, weight=None):
    """Plex Mono for telemetry values, diagnostics, coordinates and timestamps (Regular or Medium)."""
    from PySide6.QtGui import QFont
    f = QFont(mono_family())
    f.setPixelSize(int(px))
    f.setWeight(QFont.Weight.Medium if weight is None or _weight(weight) != QFont.Weight.Normal else QFont.Weight.Normal)
    f.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)
    return f


def is_figure(text) -> bool:
    """A value that is a number (or its placeholder "--"), as opposed to a word such as "Unavailable" or "Yes"."""
    t = str(text or "").strip()
    return any(ch.isdigit() for ch in t) or t.startswith("--")


def value_font(label, px: int = None, weight=None):
    """Mono for a figure, Sans for a word: call after setText on a telemetry value label."""
    px = px or text_px(label) or BODY
    f = mono(px, weight) if is_figure(label.text()) else font(px, weight)
    if label.font().family() != f.family() or label.font().pixelSize() != f.pixelSize():
        label.setFont(f)


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
        if px not in TEXT_SIZES and px != ALERT and not (HERO_MIN <= px <= HERO_MAX):
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


def radius_for(rect, radius: float) -> float:
    """Small radii: a circle stays a circle, everything else is clamped to RADIUS_MAX."""
    w, h = float(rect.width()), float(rect.height())
    if abs(w - h) < 1.0 and radius >= min(w, h) / 2.0 - 0.5:
        return radius
    return min(float(radius), float(RADIUS_MAX))


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


def paint_shadow(p, rect, radius: float = RADIUS_MAX, level: int = 2):
    from PySide6.QtCore import QPointF
    radius = radius_for(rect, radius)
    pix, m = shadow_pixmap(int(rect.width()), int(rect.height()), radius, level)
    p.drawPixmap(QPointF(rect.x() - m, rect.y() - m + LEVELS[max(1, min(3, level))][1]), pix)


def paint_card(p, rect, radius: float = RADIUS_MAX, level: int = 2, fill: str = "card", outline: str | None = "hairline"):
    """A card: a very light cached shadow, the fill and a hairline border (outline=None for none)."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QPen
    rect = QRectF(rect)
    radius = radius_for(rect, radius)
    if level:
        paint_shadow(p, rect, radius, level)
    p.save(); p.setRenderHint(p.RenderHint.Antialiasing)
    p.setBrush(c(fill))
    if outline:
        p.setPen(QPen(c(outline), 1.0))
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
    else:
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, radius, radius)
    p.restore()


# ---- back plane: the three planes ----------------------------------------------------------------------------------
# Planning/three-planes-hero-prompt.md. Back: one huge, heavy word per page (Archivo Black, hero_word colour: ink at
# 14 % over paper by day, a lifted charcoal at night). Middle: the subject, one of the student's TUKZIE renders (assets/tukzie_*.png, cut out by
# tools/cut_tukzie_renders.py), drawn in front of the word so the word reads through behind it. Top: the page's own
# widgets. Word and subject are painted once into one cached pixmap per page size and variant (never per frame).
_PLANE_CACHE = {}
_SUBJECT_CACHE = {}
SUBJECTS = ("three_quarter", "front", "side")


def hero_family() -> str:
    family()                                       # registers the bundled fonts
    from PySide6.QtGui import QFontDatabase
    return HERO_FACE if HERO_FACE in QFontDatabase.families() else family()


def hero_font(px: int):
    from PySide6.QtGui import QFont
    f = QFont(hero_family())
    f.setPixelSize(max(8, int(px)))
    if hero_family() != HERO_FACE:
        f.setWeight(QFont.Weight.Bold)
    f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 97)       # set tight, like a poster
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


def asset_path(name: str):
    here = os.path.dirname(os.path.abspath(__file__))
    for folder in (os.path.join(here, "..", "assets"), os.path.join(here, "assets")):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            return os.path.normpath(path)
    return None


def subject_image(view: str):
    """The cut-out render (QImage with alpha), loaded once; None when the asset is missing."""
    from PySide6.QtGui import QImage
    key = ("img", view)
    if key not in _SUBJECT_CACHE:
        path = asset_path(f"tukzie_{view}.png")
        img = QImage(path) if path else QImage()
        _SUBJECT_CACHE[key] = None if img.isNull() else img
    return _SUBJECT_CACHE[key]


def subject_pixmap(view: str, w: int, h: int):
    """The render scaled once to fit w x h (aspect kept, smooth), cached."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap
    key = ("pix", view, int(w), int(h))
    hit = _SUBJECT_CACHE.get(key)
    if hit is None:
        img = subject_image(view)
        if img is None:
            return None
        hit = QPixmap.fromImage(img.scaled(int(w), int(h), Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))
        _SUBJECT_CACHE[key] = hit
    return hit


class Plane:
    """One page's back and middle planes, in fractions of the page rect.
    word_box (x, y, w, h): the word is fitted to the box width, its capitals' top at the box top (anchor "top"), or
    its baseline at the box bottom (anchor "bottom"), clipped by the page edges. subject_box: the render, fitted into
    the box (aspect kept) and standing on the box bottom (align centre, left or right)."""

    def __init__(self, word, word_box=(-0.02, 0.0, 1.04, 1.0), anchor="top", subject=None, subject_box=None,
                 align="center", strength=1.0):
        self.word, self.word_box, self.anchor = word, word_box, anchor
        self.subject, self.subject_box, self.align = subject, subject_box, align
        self.strength = strength              # 1.0: the hero_word tone; less: fainter (a page whose controls sit on it)

    def key(self):
        return (self.word, self.word_box, self.anchor, self.subject, self.subject_box, self.align, self.strength)


def _box(rect, frac):
    from PySide6.QtCore import QRectF
    return QRectF(rect.width() * frac[0], rect.height() * frac[1], rect.width() * frac[2], rect.height() * frac[3])


def plane_geometry(plane, w: float, h: float):
    """{"word": QRectF of the word's capitals, "subject": QRectF of the drawn render, "font_px"} in page coordinates."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QFontMetricsF
    page = QRectF(0, 0, w, h)
    out = {"word": QRectF(), "subject": QRectF(), "font_px": 0}
    if plane.word:
        box = _box(page, plane.word_box)
        fm = QFontMetricsF(hero_font(200))
        adv = fm.tightBoundingRect(plane.word).width() or fm.horizontalAdvance(plane.word)
        px = max(40, int(200 * box.width() / max(1.0, adv)))
        cap_k = QFontMetricsF(hero_font(200)).capHeight() / 200.0
        px = min(px, max(40, int(box.height() / cap_k)))          # the capitals stay inside the box's height
        fm = QFontMetricsF(hero_font(px))
        tight = fm.tightBoundingRect(plane.word)
        cap = fm.capHeight()
        base = box.top() + cap if plane.anchor == "top" else box.bottom()
        x = box.left() - tight.left() + max(0.0, (box.width() - tight.width()) / 2)
        out["word"] = QRectF(x + tight.left(), base - cap, tight.width(), cap)
        out["font_px"] = px
        out["_word_origin"] = (x, base)
    if plane.subject and plane.subject_box:
        box = _box(page, plane.subject_box)
        img = subject_image(plane.subject)
        if img is not None:
            k = min(box.width() / img.width(), box.height() / img.height())
            sw, sh = img.width() * k, img.height() * k
            x = box.left() + (box.width() - sw) / 2 if plane.align == "center" else \
                box.left() if plane.align == "left" else box.right() - sw
            out["subject"] = QRectF(x, box.bottom() - sh, sw, sh)
    return out


def paint_back_plane(p, rect, word: str = "", corner: str = "bl", px: int = 260, ground=None, plane=None):
    """Paper ground, the page's hero word (back plane) and its subject (middle plane), cached as one pixmap.
    plane: a Plane (set with set_plane); without one, word is shown with a default placement. ground: optional
    QPainterPath(s) filled with paper_deep. Returns the geometry (plane_geometry) of what was drawn."""
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QPainter, QPixmap
    rect = QRectF(rect)
    if plane is None and word:
        plane = Plane(word, (-0.02, 0.62, 1.04, 0.38), "bottom") if corner in ("bl", "br") else Plane(word)
    pkey = plane.key() if plane is not None else None
    key = (int(rect.width()), int(rect.height()), pkey, is_night(), id(ground) if ground is not None else 0,
           BACK_WORDS_SHOWN)
    hit = _PLANE_CACHE.get(key)
    if hit is None:
        pix = QPixmap(max(1, int(rect.width())), max(1, int(rect.height())))
        pix.fill(c("paper"))
        geo = {}
        q = QPainter(pix)
        q.setRenderHint(QPainter.RenderHint.Antialiasing); q.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        q.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if ground is not None:
            q.setPen(Qt.PenStyle.NoPen); q.setBrush(c("paper_deep"))
            for path in (ground if isinstance(ground, (list, tuple)) else [ground]):
                q.drawPath(path)
        if plane is not None and BACK_WORDS_SHOWN:
            geo = plane_geometry(plane, rect.width(), rect.height())
            if plane.word:
                x, base = geo["_word_origin"]
                tone = hx("hero_word") if plane.strength >= 1.0 else blend(hx("paper"), hx("hero_word"), plane.strength)
                q.setFont(hero_font(geo["font_px"])); q.setPen(QColor(tone))
                q.drawText(QPointF(x, base), plane.word)
            sub = geo.get("subject")
            if sub is not None and not sub.isEmpty():
                pm = subject_pixmap(plane.subject, round(sub.width()), round(sub.height()))
                if pm is not None:
                    if is_night():
                        q.setOpacity(0.9)           # a touch quieter on the dark ground (less glare)
                    q.drawPixmap(QPointF(sub.x(), sub.y()), pm)
                    q.setOpacity(1.0)
        q.end()
        if len(_PLANE_CACHE) > 24:
            _PLANE_CACHE.clear()
        hit = _PLANE_CACHE[key] = (pix, geo)
    p.drawPixmap(int(rect.x()), int(rect.y()), hit[0])
    return hit[1]


def set_back_word(page, word: str, corner: str = "bl", px: int = 260):
    page.setProperty("sw7_word", word); page.setProperty("sw7_word_corner", corner); page.setProperty("sw7_word_px", px)
    page.update()


def set_plane(page, plane):
    """Give a page its hero word and subject (a Plane)."""
    page.sw7_plane = plane
    page.setProperty("sw7_word", plane.word if plane is not None else "")
    stage = getattr(page, "sw7_stage", None)
    if stage is not None and hasattr(stage, "place"):
        stage.place()                       # Drive: the advice strip makes room for the subject
    page.update()


def page_plane_geometry(page):
    """The word and subject rects of a page's plane in page coordinates (for tests and placement checks)."""
    plane = getattr(page, "sw7_plane", None)
    if plane is None:
        return {"word": None, "subject": None}
    g = plane_geometry(plane, page.width(), page.height())
    return {"word": g["word"] if not g["word"].isEmpty() else None,
            "subject": g["subject"] if not g["subject"].isEmpty() else None}


def _paint_page_plane(page, p):
    page.sw7_plane_geo = paint_back_plane(p, page.rect(), page.property("sw7_word") or "",
                                          page.property("sw7_word_corner") or "bl",
                                          int(page.property("sw7_word_px") or 260),
                                          plane=getattr(page, "sw7_plane", None))


def attach_back_plane(widget, word: str = "", corner: str = "bl", px: int = 260):
    """Paint the back plane under any QWidget page (an event filter paints before the widget's own paintEvent)."""
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtGui import QPainter

    class F(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.Type.Paint and enabled():
                p = QPainter(obj)
                _paint_page_plane(obj, p)
                p.end()
            return False

    set_back_word(widget, word, corner, px)
    f = F(widget); widget.installEventFilter(f); widget._sw7_plane = f
    return f


# ---- buttons ------------------------------------------------------------------------------------------------------
def button_qss(kind: str = "outline", radius: int = RADIUS_MAX, px: int = BODY, selector: str = "QPushButton") -> str:
    """filled: a key control (signal fill, card ink). outline: a secondary control (card, a fine signal border at
    reduced strength, signal ink). Radii are small (at most RADIUS_MAX); weight SemiBold."""
    radius = min(int(radius), RADIUS_MAX)
    fam = family()
    if kind == "filled":
        return (f"{selector}{{background:{hx('signal')};color:{hx('card')};border:none;border-radius:{radius}px;"
                f"font-family:'{fam}';font-size:{px}px;font-weight:600;padding:0px 16px;}}"
                f" {selector}:pressed{{background:{hx('signal_pressed')};}}"
                f" {selector}:disabled{{background:{hx('paper_deep')};color:{hx('ink_3')};}}")
    return (f"{selector}{{background:{hx('card')};color:{hx('signal')};border:1px solid {rgba('signal', 0.55)};"
            f"border-radius:{radius}px;font-family:'{fam}';font-size:{px}px;font-weight:600;padding:0px 16px;}}"
            f" {selector}:pressed{{background:{hx('signal_tint')};}}"
            f" {selector}:checked{{background:{hx('signal')};color:{hx('card')};border:1px solid {hx('signal')};}}"
            f" {selector}:disabled{{color:{hx('ink_3')};border-color:{hx('hairline')};}}")


def style_button(btn, kind: str = "outline", radius: int | None = None, px: int = BODY):
    r = radius if radius is not None else RADIUS_MAX
    btn.setStyleSheet(button_qss(kind, r, px))


def mark_exempt(widget, reason: str):
    widget.setProperty("sw7_signal_exempt", reason)


def mark_quiet(widget, on: bool = True):
    """A tappable that is neither selected nor a key control: drawn in ink, and the audit does not ask for signal."""
    widget.setProperty("sw7_quiet", bool(on))


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

    photos = _photo_rects(root)
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
            if tap is None and photos and any(q.contains(x, y) for q in photos):
                continue                     # the render itself (a control over it still counts)
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
        if not wd.isVisible() or not is_tappable(wd) or under_ignored(wd) or wd.property("sw7_signal_exempt") \
                or wd.property("sw7_quiet"):
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


def _photo_rects(root):
    """Where a TUKZIE render (a photograph in the middle plane) shows, in root coordinates: its red light bar is the
    vehicle's, not interface colour, so the audit skips it (as it skips the map and the camera frame)."""
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QWidget
    out = []
    for wd in [root] + root.findChildren(QWidget):
        plane = getattr(wd, "sw7_plane", None)
        if plane is None or not plane.subject or not wd.isVisible():
            continue
        r = page_plane_geometry(wd).get("subject")
        if r is not None:
            o = wd.mapTo(root, QPoint(0, 0))
            out.append(QRect(int(r.x()) + o.x(), int(r.y()) + o.y(), int(r.width()) + 1, int(r.height()) + 1))
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
        QFrame#card {{ background-color: {p['card']}; border: 1px solid {p['hairline']}; border-radius: {RADIUS_MAX}px; }}
        QFrame#cardAlt {{ background-color: {p['card_alt']}; border: 1px solid {p['hairline']}; border-radius: {RADIUS_MAX}px; }}
        QLabel#dim {{ color: {p['ink_2']}; background: transparent; }}
        QLabel#faint {{ color: {p['ink_3']}; background: transparent; }}
        QPushButton {{ background-color: {p['card']}; color: {p['signal']}; border: 1px solid {rgba('signal', 0.55)};
            border-radius: {RADIUS_MAX}px; padding: 8px 16px; font-weight: 600; }}
        QPushButton:pressed {{ background-color: {p['signal_tint']}; }}
        QPushButton:checked {{ background-color: {p['signal']}; color: {p['card']}; border: 1px solid {p['signal']}; }}
        QPushButton:disabled {{ color: {p['ink_3']}; border-color: {p['hairline']}; background-color: {p['card_alt']}; }}
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background-color: {p['card']}; color: {p['ink']};
            border: 1px solid {rgba('signal', 0.55)}; border-radius: {RADIUS_MAX - 2}px; padding: 7px 12px; }}
        QLineEdit:focus, QComboBox:focus {{ border: 1px solid {p['signal']}; }}
        QComboBox QAbstractItemView, QMenu {{ background-color: {p['card']}; color: {p['ink']};
            border: 1px solid {p['hairline']}; selection-background-color: {p['signal_tint']}; selection-color: {p['ink']}; }}
        QCheckBox {{ background: transparent; spacing: 12px; }}
        QCheckBox::indicator {{ width: 44px; height: 24px; border-radius: 12px; background: {p['paper_deep']};
            border: 1px solid {p['ink_3']}; }}
        QCheckBox::indicator:checked {{ background: {p['signal']}; border-color: {p['signal']}; }}
        QSlider::groove:horizontal {{ height: 4px; border-radius: 2px; background: {p['paper_deep']}; }}
        QSlider::handle:horizontal {{ width: 24px; margin: -10px 0; border-radius: 12px; background: {p['signal']}; }}
        QSlider::sub-page:horizontal {{ background: {p['signal']}; border-radius: 2px; }}
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
    _paint_page_plane(page, p)
    p.end()
    QWidget.paintEvent(page, event)


def _card_paint(orig, card, event):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QPainter
    from PySide6.QtWidgets import QFrame
    from PySide6.QtGui import QPen
    p = QPainter(card); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if card.property("sw7_open") and BACK_WORDS_SHOWN:
        p.fillRect(QRectF(0, 0, card.width(), 1), c("hairline"))     # an open group: a hairline, no card
    else:
        p.setPen(QPen(c("hairline"), 1.0)); p.setBrush(c("card"))
        p.drawRoundedRect(QRectF(card.rect()).adjusted(0.5, 0.5, -0.5, -0.5), RADIUS_MAX, RADIUS_MAX)
    p.end()
    QFrame.paintEvent(card, event)


# ---- the frame ----------------------------------------------------------------------------------------------------
BACK_WORDS = {"driving": "DRIVE", "analytics": "STATS", "diagnostics": "SYSTEM", "camera": "ROAD",
              "navigation": "MAP", "sensors": "AROUND", "charging": "CHARGE", "settings": "SETUP"}
# Each page's word and subject (fractions of the 1280 x 680 page). Values and tiles are top-plane widgets drawn over
# this; the subjects sit where no value is (tests/test_style_planes.py checks the boxes against every driving value).
PLANES = {
    # Drive: the whole word in the open band between the advice row (with the gear and lamps) and the tiles, which sit
    # low; the vehicle cuts into the end of the "E"; its wheels stand just above the Around tile's readings (the tile's
    # label row passes in front of them)
    "driving": Plane("DRIVE", (0.03, 0.12, 0.76, 0.30), "top", "three_quarter", (0.735, 0.12, 0.265, 0.395), "right"),
    "analytics": Plane("STATS", (0.015, 0.0, 0.97, 0.985), "bottom"),
    "diagnostics": Plane("SYSTEM", (0.015, 0.0, 0.97, 0.985), "bottom"),      # the band above the nav bar
    "camera": Plane("ROAD", (-0.03, 0.0, 1.06, 0.98), "bottom"),
    "navigation": Plane("MAP", (-0.03, 0.0, 1.06, 0.98), "bottom"),
    "sensors": Plane("AROUND", (0.015, 0.42, 0.97, 0.565), "bottom"),     # under the nearest-distance hero
    # Charging: CHARGE across the band above the nav bar, read through the ring (no disc); the front view stands in the
    # lower right under the compact column, cutting into "GE"
    "charging": Plane("CHARGE", (0.015, 0.0, 0.97, 0.985), "bottom", "front", (0.70, 0.56, 0.28, 0.425)),
    # Settings: fainter (its buttons and sliders sit on the letters), the side view standing in it
    "settings": Plane("SETUP", (0.015, 0.0, 0.97, 0.985), "bottom", "side", (0.52, 0.745, 0.46, 0.25), strength=0.45),
}

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
        col = c("signal") if button.isChecked() else c("ink_2")      # only the selected item is in signal
        size = 26
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
                          f"border-bottom:1px solid {hx('hairline')};min-height:47px;max-height:47px;}}"
                          f" QLabel{{color:{hx('ink')};background:transparent;}}")
        bar.clock.setFont(mono(BODY, QFont.Weight.Medium))          # a timestamp: Plex Mono
        bar.soc.setFont(mono(BODY, QFont.Weight.Medium))            # a telemetry value: Plex Mono
        if getattr(bar, "_state", None) is not None:
            bar.update_state(bar._state)
        if hasattr(bar, "sw7_weather_chip"):
            bar.sw7_weather_chip.update()

    _swrap(cls, "_apply_theme", after=theme_after)
    _swrap(cls, "__init__", after=theme_after)      # after the layout pass's own __init__ sizes


# nav bar -------------------------------------------------------------------------------------------------------------
def _install_nav(cls):
    def init_after(nav, *_a, **_k):
        from PySide6.QtCore import Qt
        nav.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        for b in nav.buttons.values():
            b.sw7_nav = True
            mark_quiet(b)                      # unselected items are ink; the selected one is signal
            b.setFixedHeight(NAV_BTN_H)
            lab = getattr(b, "sw7_label", None)
            if lab is not None and b.layout() is not None:
                b.layout().setContentsMargins(2, 0, 2, 8)
            b.toggled.connect(lambda on, btn=b, n=nav: _nav_label_weight(btn, on, n))
            b.refresh()
        _nav_theme(nav)

    def paint(orig, nav, event):
        """A flat bar: card fill, a hairline on top, and a short signal bar over the selected item."""
        from PySide6.QtCore import QRectF, Qt
        from PySide6.QtGui import QPainter
        p = QPainter(nav)
        bar = _pill_rect(nav)
        p.fillRect(bar, c("card"))
        p.fillRect(QRectF(bar.left(), bar.top(), bar.width(), 1), c("hairline"))
        sel = next((b for b in nav.buttons.values() if b.isChecked() and b.isVisible()), None)
        if sel is not None:                    # on the selected item's own top edge (it is part of the target)
            g = sel.geometry()
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(c("signal"))
            p.drawRect(QRectF(g.center().x() - INDICATOR_W / 2 + 1, g.top(), INDICATOR_W, INDICATOR_H))
        p.end()

    _swrap(cls, "__init__", after=init_after)
    _swrap(cls, "_theme", after=lambda nav, *a, **k: _nav_theme(nav))
    _swrap(cls, "paintEvent", replace=paint)
    _swrap(cls, "select", after=lambda nav, *a, **k: nav.update())


def _nav_label_weight(button, on, nav):
    from PySide6.QtGui import QFont
    lab = getattr(button, "sw7_label", None)
    if lab is not None:
        lab.setFont(font(LABEL, QFont.Weight.DemiBold if on else QFont.Weight.Medium))
    nav.update()


def _pill_rect(nav):
    """The bar: the nav widget's full width, NAV_BAR_TOP down to the bottom."""
    from PySide6.QtCore import QRectF
    return QRectF(0, NAV_BAR_TOP, nav.width(), nav.height() - NAV_BAR_TOP)


def _nav_theme(nav):
    """Transparent buttons on the painted bar, icon above a 13 px label. Label colours come from the layout pass
    (accent = signal when checked, text_dim = ink_2); the selected label is SemiBold, the others Medium."""
    if not any(hasattr(b, "sw7_label") for b in nav.buttons.values()):
        return
    from PySide6.QtGui import QFont
    nav.setStyleSheet(
        f"QFrame#bottomNavigation{{background:transparent;border:none;min-height:{NAV_FLOAT_H}px;max-height:{NAV_FLOAT_H}px;}}"
        " QFrame#bottomNavigation QPushButton{background:transparent;border:none;border-radius:0px;"
        "padding:0px 0px 22px 0px;}"
        " QFrame#bottomNavigation QPushButton:checked{background:transparent;border:none;padding:0px 0px 22px 0px;}"
        f" QFrame#bottomNavigation QPushButton:pressed{{background:{hx('signal_tint')};}}")
    for b in nav.buttons.values():
        lab = getattr(b, "sw7_label", None)
        if lab is not None:
            lab.setFont(font(LABEL, QFont.Weight.DemiBold if b.isChecked() else QFont.Weight.Medium))
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
    top = NAV_BAR_TOP + (NAV_FLOAT_H - NAV_BAR_TOP - NAV_BTN_H) // 2
    lay.setContentsMargins(m.left(), top, m.right(), NAV_FLOAT_H - top - NAV_BTN_H)
    for b in (main.left, main.right):
        b.setFixedSize(64, 64)            # flat: a hairline circle on the bar, no shadow
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
        set_plane(page, PLANES.get(pid) or Plane(word))
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
        QPushButton#sideArrow {{ background: transparent; border: 1px solid {hx('hairline')}; border-radius: 32px; padding: 0px; }}
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
    nav.sw7_pill_x = (0, W)
    nav.clearMask()
    nav.raise_()
    y = H - NAV_FLOAT_H + NAV_BAR_TOP + (NAV_FLOAT_H - NAV_BAR_TOP - 64) // 2
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
        chip.setFont(font(LABEL, QFont.Weight.DemiBold, caps=True))
        chip.setStyleSheet(f"QLabel#sw7SourceChip {{ background: transparent; color: {hx('ink')};"
                           f" border: 1px solid {hx('ink_3')}; border-radius: {RADIUS_SM}px;"
                           f" padding: 0px 0px 0px 14px; font-size: {LABEL}px; font-weight: 600; }}")
        strip = marks.strip
        strip.setFont(font(LABEL, QFont.Weight.DemiBold, caps=True))
        strip.setStyleSheet(f"QLabel#sw7SimStrip {{ background: {hx('warn_tint')}; color: {hx('ink')};"
                            f" border-top: 1px solid {hx('warn')}; border-bottom: 1px solid {hx('warn')};"
                            f" font-weight: 600; font-size: {LABEL}px; padding: 3px 10px; }}")
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
