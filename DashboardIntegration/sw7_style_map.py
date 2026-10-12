"""SW-7 paper and depth style, page agent P3: the Map page's own widgets, the touch keyboard and Settings.

Planning/paper-depth-theme-prompt.md (sections 3 to 5, 9 and 10) and Planning/data-ownership-and-merge-plan.md
(option A). Installed as app/pages/sw7_style_map.py; dashboard_main.py calls install(DashboardMain) right after
sw7_style.install (tests/dashboard_patches.py, STYLE_MAP_PATCHES). With TUKZIE_SW7_STYLE=team it does nothing.

The map itself (the raised slab, tinted tiles, ink route, charcoal turn banner, the one arrival-time figure, the
control column in signal) is drawn by sw7_tile_map.py, which checks sw7_style on its own. This module styles what
the team's NavigationPage puts over the map, and the Settings page:

Map page
  - Search field: a floating card (its shadow is painted, cached, by the map), the field with a signal outline,
    Navigate filled signal. The status line is a paper card in ink_2 at 16 px.
  - One remaining-distance and ETA figure: the status line said "1.6 km . 4 min . arrival 78 % . offline router"
    (the plan as it was when it was made) while the arrival-time bar said "3 min . 1.3 km . arrive 11:21" (live,
    from the vehicle's progress along the route). The bar is kept, because it follows the drive; the status line
    keeps only the route source ("Route by offline router . offline preview") and the arrival battery moves into
    the bar ("arrive 11:21 . 78 % battery").
  - The touch keyboard: paper, keys as card buttons with signal ink and a signal outline at 22 px.
Settings
  - Paper cards on cached shadows, one section-title style (13 px caps, ink_2), the page title at 22 px, every
    other text at 16 px (the hint at 13). Toggles, sliders, combo boxes and buttons in signal.
  - The old colour-theme picker does nothing under paper (sw7_style owns the palette), so it is hidden and its card
    becomes LOOK: three swatches, Auto (Paper by day, Ink from sunset), Day (Paper) and Night (Ink). The choice
    holds until the dashboard restarts (Auto again); TUKZIE_SW7_STYLE=team brings back the team's picker.
  - "Map follows the tuk-tuk" reads "Start the map in follow mode": the Map's Follow button is the live mode.
"""
from __future__ import annotations

import os
import tempfile

_installed = False
MARK = "_sw7_style_map"


def _S():
    from ..widgets import sw7_style
    return sw7_style


def enabled():
    try:
        S = _S()
    except ImportError:
        return False
    return S.enabled() and getattr(S, "_installed", False)


def _wrap(cls, name, after=None, replace=None):
    """Wrap a method once, with this module's own marker (sw7_style._swrap skips methods it has wrapped)."""
    orig = getattr(cls, name)
    if getattr(orig, MARK, False):
        return
    if replace is not None:
        def method(self, *a, **k):
            return replace(orig, self, *a, **k)
    else:
        def method(self, *a, **k):
            result = orig(self, *a, **k)
            after(self, *a, **k)
            return result
    setattr(method, MARK, True)
    method.__name__ = name
    setattr(cls, name, method)


def install(main_cls):
    global _installed
    if _installed or not enabled():
        return
    _installed = True
    from . import navigation_page, settings_page
    from ..widgets import touch_keyboard
    _wrap(navigation_page.NavigationPage, "_apply_theme", after=_nav_theme)
    _wrap(navigation_page.NavigationPage, "_route_summary", replace=_route_summary)
    _wrap(touch_keyboard.TouchKeyboard, "_apply_theme", after=_keyboard_theme)
    _wrap(settings_page.SettingsPage, "__init__", after=_settings_init)
    _wrap(settings_page.SettingsPage, "_theme", after=_settings_theme)


# ---- Map page ------------------------------------------------------------------------------------------------------
def _route_summary(orig, page):
    """The route source only: the distance and time left are in the map's arrival-time bar (one figure)."""
    plan = getattr(page, "_plan", None)
    if plan is None:
        return orig(page)
    source = str(getattr(plan, "source", "") or "route")
    suffix = " · offline preview" if "offline" in source.lower() else ""
    return f"Route by {source}{suffix}"


def _nav_theme(page, *_a, **_k):
    S = _S()
    page.setStyleSheet(page.styleSheet() + f"""
        QLabel#routeStatus {{ background: {S.hx('card')}; color: {S.hx('ink_2')}; border: 1px solid {S.hx('hairline')}; border-radius: 8px;
            padding: 8px 16px; font-size: 16px; }}
        QLabel#altitudeCard {{ background: {S.hx('card')}; color: {S.hx('ink')}; border: 1px solid {S.hx('hairline')}; border-radius: 8px; }}
        QFrame#navSearch QLineEdit {{ background: {S.hx('card')}; color: {S.hx('ink')}; border: 1px solid {S.rgba('signal', 0.55)};
            border-radius: 8px; padding: 4px 16px; font-size: 16px; }}
        QFrame#navSearch QPushButton {{ background: {S.hx('signal')}; color: {S.hx('card')}; border: none; border-radius: 8px;
            padding: 0px 20px; font-size: 16px; font-weight: 600; }}
        QFrame#navSearch QPushButton:pressed {{ background: {S.hx('signal_pressed')}; }}
        QFrame#navSearch QPushButton:disabled {{ background: {S.hx('paper_deep')}; color: {S.hx('ink_3')}; }}
        QPushButton#mapToolButton {{ background: {S.hx('card')}; color: {S.hx('signal')}; border: 1px solid {S.rgba('signal', 0.55)};
            border-radius: 8px; padding: 0px 16px; font-size: 16px; font-weight: 600; }}
        QPushButton#mapToolButton:pressed {{ background: {S.hx('signal_tint')}; }}
        QListWidget {{ background: {S.hx('card')}; color: {S.hx('ink')}; border: 1px solid {S.hx('hairline')};
            border-radius: 8px; }}
        """)
    for name in ("plan_btn", "retry_btn"):
        b = getattr(page, name, None)
        if b is not None:
            b.setFont(S.font(16, b.font().weight()))
    # the search field and Navigate fill the 64 px search bar (64 px touch targets)
    search = getattr(page, "search", None)
    if search is not None and search.layout() is not None:
        m_ = search.layout().contentsMargins()
        search.layout().setContentsMargins(m_.left(), 0, m_.right(), 0)
        for name in ("plan_btn", "destination"):
            w = getattr(page, name, None)
            if w is not None:
                w.setMinimumHeight(64)
    status = getattr(page, "route_status", None)
    if status is not None:
        status.setFont(S.font(S.BODY))
    m = getattr(page, "map", None)
    if m is not None:
        m.update()


def _keyboard_theme(kb, *_a, **_k):
    S = _S()
    kb.setStyleSheet(kb.styleSheet() + f"""
        QFrame#touchKeyboard {{ background: {S.hx('paper_deep')}; border-top: 1px solid {S.hx('hairline')}; }}
        QFrame#touchKeyboard QPushButton {{ background: {S.hx('card')}; color: {S.hx('signal')};
            border: 1px solid {S.rgba('signal', 0.55)}; border-radius: 6px; padding: 4px; font-size: 22px; font-weight: 500; }}
        QFrame#touchKeyboard QPushButton:pressed {{ background: {S.hx('signal')}; color: {S.hx('card')}; }}
        """)


# ---- Settings ------------------------------------------------------------------------------------------------------
LOOKS = (("auto", "Auto", "Sunset to sunrise"), ("day", "Day", "Paper"), ("night", "Night", "Ink, low glare"))


def look_mode():
    forced = _S().forced_night()
    return "auto" if forced is None else ("night" if forced else "day")


def set_look(mode):
    """Auto: the weather service's sunrise and sunset choose (sw7_style). Day / Night: forced until restart."""
    S = _S()
    before = S.is_night()
    if mode == "auto":
        os.environ.pop(S.NIGHT_ENV, None)
    else:
        os.environ[S.NIGHT_ENV] = "1" if mode == "night" else "0"
    if S.is_night() != before:
        S._theme_changed()


def _look_swatch_class():
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QFont, QPainter, QPainterPath, QPen, QColor
    from PySide6.QtWidgets import QPushButton

    class LookSwatch(QPushButton):
        """A swatch button: a small page of the look (paper, a card, a line of ink), its name in signal and a
        13 px note. Checked: signal tint with a 3 px signal outline."""

        def __init__(self, mode, name, note, parent=None):
            super().__init__(name, parent)
            self.mode, self.name, self.note = mode, name, note
            self.setCheckable(True)
            self.setAutoExclusive(True)
            self.setMinimumHeight(132)
            self.setFont(_S().font(16, QFont.Weight.Bold))
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        def _page(self, p, r, pal):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(pal["paper"]))
            p.drawRoundedRect(r, 4, 4)
            card = QRectF(r.left() + 10, r.top() + 10, r.width() * 0.62, r.height() - 20)
            p.setBrush(QColor(pal["card"]))
            p.drawRoundedRect(card, 3, 3)
            p.setBrush(QColor(pal["ink"]))
            p.drawRoundedRect(QRectF(card.left() + 8, card.top() + 8, card.width() * 0.55, 6), 3, 3)
            p.setBrush(QColor(pal["ink_3"]))
            p.drawRoundedRect(QRectF(card.left() + 8, card.top() + 20, card.width() * 0.75, 4), 2, 2)
            p.setBrush(QColor(pal["signal"]))
            p.drawEllipse(QRectF(r.right() - 26, r.bottom() - 26, 16, 16))

        def paintEvent(self, _event):
            S = _S()
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            on = self.isChecked()
            r = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
            p.setBrush(S.c("signal_tint") if on or self.isDown() else S.c("card"))
            p.setPen(QPen(S.c("signal") if on else S.c("hairline"), 2.0 if on else 1.0))
            p.drawRoundedRect(r, 8, 8)
            prev = QRectF(r.left() + 12, r.top() + 12, r.width() - 24, 56)
            if self.mode == "auto":       # half Paper, half Ink
                p.save()
                left = QPainterPath(); left.addRect(QRectF(prev.left(), prev.top(), prev.width() / 2, prev.height()))
                p.setClipPath(left); self._page(p, prev, S.DAY); p.restore()
                p.save()
                right = QPainterPath(); right.addRect(QRectF(prev.center().x(), prev.top(), prev.width() / 2, prev.height()))
                p.setClipPath(right); self._page(p, prev, S.NIGHT); p.restore()
            else:
                self._page(p, prev, S.NIGHT if self.mode == "night" else S.DAY)
            p.setPen(QPen(S.c("hairline"), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(prev, 4, 4)
            p.setPen(S.c("signal"))
            p.setFont(S.font(16, QFont.Weight.Bold))
            p.drawText(QRectF(r.left() + 14, prev.bottom() + 6, r.width() - 28, 24),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.name)
            p.setPen(S.c("ink_2"))
            p.setFont(S.font(13))
            p.drawText(QRectF(r.left() + 14, prev.bottom() + 30, r.width() - 28, 20),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       p.fontMetrics().elidedText(self.note, Qt.TextElideMode.ElideRight, int(r.width() - 28)))
            p.end()

    return LookSwatch


def _icons():
    """Knob and chevron images in the current palette (QSS needs files): off knob signal, on knob card, chevron
    signal. Cached in the temp folder by colour."""
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter, QPen
    S = _S()
    folder = os.path.join(tempfile.gettempdir(), "sw7_style_map")
    os.makedirs(folder, exist_ok=True)
    out = {}
    for name, colour in (("off", S.hx("ink_2")), ("on", S.hx("card"))):
        path = os.path.join(folder, f"knob_{name}_{colour.strip('#')}.png").replace("\\", "/")
        if not os.path.isfile(path):
            img = QImage(60, 32, QImage.Format.Format_ARGB32_Premultiplied); img.fill(Qt.GlobalColor.transparent)
            p = QPainter(img); p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(colour))
            d = 24
            p.drawEllipse(QRectF(60 - d - 4 if name == "on" else 4, 4, d, d)); p.end()
            img.save(path)
        out[name] = path
    path = os.path.join(folder, f"chevron_{S.hx('signal').strip('#')}.png").replace("\\", "/")
    if not os.path.isfile(path):
        img = QImage(20, 12, QImage.Format.Format_ARGB32_Premultiplied); img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(S.hx("signal")), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPolyline([QPointF(3, 3), QPointF(10, 9), QPointF(17, 3)]); p.end()
        img.save(path)
    out["chevron"] = path
    return out


def _cards(page):
    return [c for c in getattr(page, "sw7_columns", {}).values()]


def _settings_init(page, *_a, **_k):
    from PySide6.QtCore import QEvent, QObject, QRectF
    from PySide6.QtGui import QFont, QPainter
    from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QWidget
    S = _S()
    content = page.scroll.widget()
    # one title style, one section style, everything else body (the hint at label size)
    for w in content.findChildren(QLabel):
        if w.objectName() == "sectionTitle":
            w.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True))
        elif w.text() == "Settings":
            w.setFont(S.font(S.SECONDARY, QFont.Weight.Bold))
        elif w.text().startswith("Changes apply and save immediately"):
            w.setFont(S.font(S.LABEL)); w.setObjectName("dim")
        else:
            w.setFont(S.font(S.BODY, w.font().weight()))
    for w in content.findChildren(QCheckBox):
        w.setFont(S.font(S.BODY, QFont.Weight.Medium))
        S.mark_quiet(w)                   # an off toggle is ink; an on toggle is signal (selected)
    follow = getattr(page, "auto_follow", None)
    if follow is not None:
        follow.setText("Start the map in follow mode")
    # LOOK in place of the colour theme picker
    cols = getattr(page, "sw7_columns", {})
    card = cols.get("SYSTEM COLOUR PALETTE")
    if card is not None and not hasattr(page, "sw7_looks"):
        for sw in getattr(page, "sw7_swatches", []):
            card.layout().removeWidget(sw)
            sw.hide()
        for t in card.findChildren(QLabel):
            if t.objectName() == "sectionTitle":
                t.setText("LOOK")
        LookSwatch = _look_swatch_class()
        row = QWidget(card); row.setObjectName("sw7LookRow")
        lay = QHBoxLayout(row); lay.setContentsMargins(0, 4, 0, 0); lay.setSpacing(12)
        page.sw7_looks = {}
        for mode, name, note in LOOKS:
            b = LookSwatch(mode, name, note, row)
            b.clicked.connect(lambda _c=False, m=mode: (set_look(m), _sync_looks(page)))
            lay.addWidget(b, 1)
            page.sw7_looks[mode] = b
        card.layout().addWidget(row, 1, 0, 1, 2)
        _sync_looks(page)
    # cards float on cached shadows, painted under them by the content widget
    class Shadows(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.Type.Paint and enabled():
                p = QPainter(obj)
                for c in _cards(page):
                    if c.isVisible() and not S.BACK_WORDS_SHOWN:      # three planes: no cards, no shadows
                        S.paint_shadow(p, QRectF(c.geometry()), 8, 1)
                p.end()
            return False
    if not hasattr(page, "_sw7_shadows"):
        page._sw7_shadows = Shadows(content)
        content.installEventFilter(page._sw7_shadows)
    page._sw7_paper = True
    _settings_theme(page)


def _sync_looks(page):
    mode = look_mode()
    for m, b in getattr(page, "sw7_looks", {}).items():
        b.setChecked(m == mode)


def _settings_theme(page, *_a, **_k):
    if not getattr(page, "_sw7_paper", False):
        return
    S = _S()
    ic = _icons()
    p = S.palette()
    page.setStyleSheet(page.styleSheet() + f"""
        QLabel {{ color: {p['ink']}; background: transparent; }}
        QLabel#dim {{ color: {p['ink_2']}; }}
        QLabel#sectionTitle {{ color: {p['ink_2']}; letter-spacing: 1px; }}
        QCheckBox {{ color: {p['ink']}; background: transparent; spacing: 14px; }}
        QCheckBox::indicator {{ width: 60px; height: 32px; border-radius: 16px; border: 1px solid {p['ink_3']};
            background: {p['paper_deep']}; image: url({ic['off']}); }}
        QCheckBox::indicator:checked {{ background: {p['signal']}; border-color: {p['signal']}; image: url({ic['on']}); }}
        QSlider::groove:horizontal {{ height: 4px; border-radius: 2px; background: {p['paper_deep']}; }}
        QSlider::sub-page:horizontal {{ background: {p['signal']}; border-radius: 2px; }}
        QSlider::handle:horizontal {{ width: 32px; height: 32px; margin: -14px 0; border-radius: 16px;
            background: {p['signal']}; border: 3px solid {p['card']}; }}
        QComboBox, QLineEdit {{ background: {p['card']}; color: {p['ink']}; border: 1px solid {S.rgba('signal', 0.55)};
            border-radius: 8px; padding: 4px 16px; }}
        QComboBox::drop-down {{ border: none; width: 40px; }}
        QComboBox::down-arrow {{ image: url({ic['chevron']}); width: 20px; height: 12px; }}
        QComboBox:disabled {{ border-color: {p['hairline']}; color: {p['ink_3']}; }}
        QPushButton {{ background: {p['card']}; color: {p['signal']}; border: 1px solid {S.rgba('signal', 0.55)};
            border-radius: 8px; padding: 4px 20px; font-weight: 600; }}
        QPushButton:pressed {{ background: {p['signal_tint']}; }}
        QScrollArea, QWidget#settingsContent {{ background: transparent; border: none; }}
        """)
    if S.BACK_WORDS_SHOWN:
        # three planes: the groups sit on the paper under a hairline (no cards), so SETUP and the vehicle show
        # between them; the controls keep their own fills
        for c in _cards(page):
            name = c.objectName() or "sw7SettingsGroup"
            c.setObjectName(name)
            c.setProperty("sw7_open", True)          # a ThemedCard paints only a hairline (sw7_style._card_paint)
            c.update()
            c.setStyleSheet(f"QFrame#{name} {{ background: transparent; border: none; border-top: 1px solid {p['hairline']};"
                            " border-radius: 0px; }")
    save = getattr(page, "save_button", None)
    if save is not None:                  # the page's one primary action: filled
        save.setStyleSheet(S.button_qss("filled", 16, 16))
    for b in getattr(page, "sw7_looks", {}).values():
        b.update()
    page.scroll.widget().update()
