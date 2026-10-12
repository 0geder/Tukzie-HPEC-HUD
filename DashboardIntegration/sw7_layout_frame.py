"""SW-7 layout pass: the shared frame (status bar, nav bar, side arrows), Settings and Charging.

Planning/layout-improvements-prompt.md (agent A) and Planning/google-stitch-dashboard-prompt.md sections 1 and 2.
Only layout, sizes, spacing, hierarchy and touch targets change. Colours come from THEME (the team's palettes) and
the fonts are the team's: THEME.font for text, the Charging page's own monospace for its numbers.

Installed as app/widgets/sw7_layout_frame.py. dashboard_main.py calls install_classes(DashboardMain) once, at import
time, before any page is built. It wraps methods of the team's classes (status bar, nav bar, Settings, Charging and
the dashboard shell), so the team's files keep their code; the only edits inside them are two lines in
charging_page.py (the SOC readout in the ring). TUKZIE_SW7_LAYOUT=0 installs nothing: the team's layout, unchanged.

What changes with the switch on (default):
- Status bar 48 px (was 38), text 16 px (was 11), battery percent 18 px bold in its status colour, clock "14:28",
  weather short ("UCT 19°C"). The source chip (LIVE / REPLAY / NO DATA / SIMULATED) is 120 x 28 px, 14 px bold,
  so the bar does not shift when the text changes. Contents and order are unchanged.
- Nav bar 72 px, every item at least 96 x 64 px with a 32 px icon and a 13 px label under it; the current item has
  a 2 px accent outline, accent icon and accent label.
- Side arrows 64 x 64 px inside the nav bar's end margins, so they never cover page content.
- Settings: title 24 px, two columns of cards (Display, Voice, Driver assistance | Navigation, Colour theme, Save),
  rows 64 px, 64 x 36 px toggles, 44 px slider handles, 64 px drop-downs and buttons, 16 px text.
- Charging: the ring's SOC uses the status bar's rounding (it truncated, so 79.6 % read 79 % beside 80 % in the
  bar), with "5.8 of 7.2 kWh" under it; title "Charging" 24 px and a plain state line 18 px; the charge source is
  one text label ("Source: Solar") instead of three button-like pills; tile values 28 px with 14 px labels; the
  empty power chart says "No charging data".
"""
from __future__ import annotations

import os
import re
import tempfile

LAYOUT_ENV = "TUKZIE_SW7_LAYOUT"

# Sizes at 1280 x 800 (Stitch file, sections 1 and 2)
STATUS_H = 48
STATUS_PX = 16
SOC_PX = 18
CHIP_W, CHIP_H, CHIP_PX = 120, 28, 14
NAV_H = 72
NAV_BTN_W, NAV_BTN_H = 96, 64
NAV_ICON = 32
NAV_LABEL_PX = 13
SAFE_EDGE = 16              # bezel and enclosure lip: no tap targets in the outer 16 px
ARROW = 64
ARROW_ICON = 28
MARGIN = 24                 # outer page margin
GAP = 16                    # between cards
TITLE_PX = 24
SECTION_PX = 13
TEXT_PX = 16
HINT_PX = 14
ROW_H = 64
TOGGLE_W, TOGGLE_H = 64, 36
HANDLE = 44
RING_SOC_PX = 48
RING_ENERGY_PX = 20
STATE_PX = 18
TILE_VALUE_PX = 28
TILE_LABEL_PX = 14
SOURCE_H = 36

NAV_LABELS = {"driving": "Drive", "analytics": "Analytics", "diagnostics": "Diagnostics", "navigation": "Map",
              "camera": "Camera", "sensors": "Sensors", "charging": "Charging", "settings": "Settings",
              "reverse": "Reverse"}
WEATHER_RE = re.compile(r"^(?P<place>.*?):\s*(?P<temp>\S*°C)(?:\s*\(.*\))?$")


def enabled() -> bool:
    return os.environ.get(LAYOUT_ENV, "1").strip() != "0"


def soc_text(soc) -> str:
    """Whole-percent state of charge, rounded the way the status bar rounds it ("--" when unknown)."""
    if soc is None:
        return "--"
    return f"{max(0.0, min(100.0, float(soc))):.0f}"


def short_weather(text: str) -> str:
    """'Rondebosch: 19°C (Clear Sky)' -> 'Rondebosch 19°C'; anything else unchanged."""
    m = WEATHER_RE.match(str(text or ""))
    return f"{m.group('place')} {m.group('temp')}" if m else str(text or "")


def _wrap(cls, name, after=None, replace=None):
    """Replace cls.name with a function that runs the original and then after(self, *a), or replace(orig, self, *a)."""
    orig = getattr(cls, name)
    if getattr(orig, "_sw7_layout", False):
        return
    if replace is not None:
        def method(self, *a, **k):
            return replace(orig, self, *a, **k)
    else:
        def method(self, *a, **k):
            result = orig(self, *a, **k)
            after(self, *a, **k)
            return result
    method._sw7_layout = True
    method.__name__ = name
    setattr(cls, name, method)


_installed = False


def install_classes(main_cls):
    """Wrap the team's classes. Called once from dashboard_main.py; does nothing with TUKZIE_SW7_LAYOUT=0."""
    global _installed
    if _installed or not enabled():
        return
    _installed = True
    from . import status_bar, nav_bar
    _install_status_bar(status_bar.DashboardStatusBar)
    _install_nav(nav_bar.BottomNavigation)
    _wrap(main_cls, "_position_arrows", replace=_position_arrows)
    try:
        from ..pages import sw7_sim_link
        _install_chip(sw7_sim_link)
    except ImportError:
        pass
    from ..pages import settings_page, charging_page
    _wrap(settings_page.SettingsPage, "__init__", after=_settings_init)
    _wrap(settings_page.SettingsPage, "_theme", after=_settings_theme)
    _install_charging(charging_page)


# ---- status bar --------------------------------------------------------------------------------------------------
def _install_status_bar(cls):
    from datetime import datetime

    def init_after(bar, *_a, **_k):
        from PySide6.QtGui import QFont
        from ..theme import THEME
        bar.setFixedHeight(STATUS_H)
        for w in (bar.weather, bar.clock):
            w.setFont(THEME.font(STATUS_PX, QFont.Weight.DemiBold))
        bar.soc.setFont(THEME.font(SOC_PX, QFont.Weight.Bold))
        bar.centre.layout().setSpacing(8)
        bar._tick()
        bar._refresh_weather()

    def tick(orig, bar):
        bar.clock.setText(datetime.now().astimezone().strftime("%H:%M"))

    def weather_after(bar, *_a, **_k):
        bar.weather.setText(short_weather(bar.weather.text()))

    def theme_after(bar, *_a, **_k):
        from ..theme import THEME
        bar.setStyleSheet(bar.styleSheet().replace("min-height:38px;max-height:38px;",
                                                   f"min-height:{STATUS_H - 1}px;max-height:{STATUS_H - 1}px;")   # plus the 1 px border
                          + f" QLabel{{color:{THEME.hex('text')};background:transparent;}}")
        if bar._state is not None:
            bar.update_state(bar._state)   # the battery percent keeps its status colour

    _wrap(cls, "__init__", after=init_after)
    _wrap(cls, "_tick", replace=tick)
    _wrap(cls, "_refresh_weather", after=weather_after)
    _wrap(cls, "_apply_theme", after=theme_after)


def _install_chip(sim_link):
    """The source chip: fixed 120 x 28 px, 14 px bold, same colours and words."""
    cls = sim_link._Indicators

    def show_after(marks, source, *_a, **_k):
        text, key = sim_link.CHIPS.get(source, ("", None))
        if not text:
            return
        bg = sim_link._colour(key, "#5A6270")
        fg = "#0B0D10" if key in ("normal", "warn") else "#FFFFFF"
        marks.chip.setFixedSize(CHIP_W, CHIP_H)
        marks.chip.setStyleSheet(f"QLabel#sw7SourceChip {{ background: {bg}; color: {fg}; border-radius: 8px;"
                                 f" padding: 0px; font-weight: 700; font-size: {CHIP_PX}px; }}")
        marks.place()

    _wrap(cls, "show_source", after=show_after)


# ---- nav bar and side arrows -------------------------------------------------------------------------------------
def _install_nav(cls):
    def init_after(nav, *_a, **_k):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QLabel, QVBoxLayout
        from PySide6.QtGui import QFont
        from ..theme import THEME
        side = SAFE_EDGE + ARROW + GAP
        nav.layout().setContentsMargins(side, (NAV_H - NAV_BTN_H) // 2, side, (NAV_H - NAV_BTN_H) // 2)
        nav.layout().setSpacing(12)
        nav.setFixedHeight(NAV_H)
        for pid, button in nav.buttons.items():
            button.icon_size = NAV_ICON
            button.setMinimumSize(NAV_BTN_W, NAV_BTN_H)
            button.setMaximumHeight(NAV_BTN_H)
            label = QLabel(NAV_LABELS.get(pid, button.toolTip()), button)
            label.setObjectName("sw7NavLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
            label.setFont(THEME.font(NAV_LABEL_PX, QFont.Weight.DemiBold))
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            lay = QVBoxLayout(button); lay.setContentsMargins(2, 0, 2, 5); lay.addStretch(1); lay.addWidget(label)
            button.sw7_label = label
            button.toggled.connect(lambda _on, b=button: _nav_label_colour(b))
            button.refresh()
        _nav_theme(nav)

    _wrap(cls, "__init__", after=init_after)
    _wrap(cls, "_theme", after=lambda nav, *a, **k: _nav_theme(nav))


def _nav_label_colour(button):
    from ..theme import THEME
    label = getattr(button, "sw7_label", None)
    if label is not None:
        col = THEME.hex("accent") if button.isChecked() else THEME.hex("text_dim")
        label.setStyleSheet(f"color:{col};background:transparent;")


def _nav_theme(nav):
    from ..theme import THEME
    if not any(hasattr(b, "sw7_label") for b in nav.buttons.values()):
        return    # still inside the team's __init__; init_after styles it
    nav.setStyleSheet(
        f"QFrame#bottomNavigation{{background:{THEME.hex('card')};border-top:1px solid {THEME.hex('border')};"
        f"min-height:{NAV_H - 1}px;max-height:{NAV_H - 1}px;}}"   # plus the 1 px border
        f" QFrame#bottomNavigation QPushButton{{background:transparent;border:2px solid transparent;border-radius:12px;"
        f"padding:0px 0px 18px 0px;}}"
        f" QFrame#bottomNavigation QPushButton:checked{{border:2px solid {THEME.hex('accent')};"
        f"background:{THEME.hex('card_alt')};}}"
        f" QFrame#bottomNavigation QPushButton:hover{{background:{THEME.hex('card_alt')};}}")
    for b in nav.buttons.values():
        _nav_label_colour(b)


def _position_arrows(orig, main):
    """The side arrows sit in the nav bar's end margins, 64 x 64 px, clear of every page."""
    left, right, nav = getattr(main, "left", None), getattr(main, "right", None), getattr(main, "nav", None)
    if left is None or right is None or nav is None:
        return orig(main)
    from PySide6.QtCore import QSize
    host = main.centralWidget()
    g = nav.geometry()
    y = g.y() + (g.height() - ARROW) // 2
    for button in (left, right):
        if button.icon_size != ARROW_ICON:
            button.icon_size = ARROW_ICON; button.refresh(); button.setIconSize(QSize(ARROW_ICON, ARROW_ICON))
    left.setGeometry(SAFE_EDGE, y, ARROW, ARROW)
    right.setGeometry(max(SAFE_EDGE, host.width() - ARROW - SAFE_EDGE), y, ARROW, ARROW)
    left.raise_(); right.raise_()


# ---- Settings ----------------------------------------------------------------------------------------------------
LEFT_CARDS = ("DISPLAY", "VOICE", "DRIVER ASSISTANCE")
RIGHT_CARDS = ("NAVIGATION", "SYSTEM COLOUR PALETTE", "SYSTEM")


def _settings_init(page, *_a, **_k):
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                                   QSlider, QVBoxLayout)
    from ..theme import THEME
    content = page.scroll.widget()
    root = content.layout()
    root.setContentsMargins(MARGIN, 16, MARGIN, MARGIN)
    root.setSpacing(GAP)
    cards = {}
    for card in content.findChildren(QFrame):
        title = card.property("sectionTitle")
        if title and card.parentWidget() is content:
            cards[str(title)] = card
    # Title: one style on every page
    for i in range(root.count()):
        w = root.itemAt(i).widget()
        if isinstance(w, QLabel) and w.text() == "Settings":
            w.setFont(THEME.font(TITLE_PX, QFont.Weight.Bold))
            break
    # Two columns: Display, Voice, Driver assistance | Navigation, Colour theme, Save
    for card in cards.values():
        root.removeWidget(card)
    for i in reversed(range(root.count())):
        item = root.itemAt(i)
        if item.spacerItem() is not None:
            root.takeAt(i)
    cols = QHBoxLayout(); cols.setSpacing(GAP)
    for names in (LEFT_CARDS, RIGHT_CARDS):
        col = QVBoxLayout(); col.setSpacing(GAP)
        for name in names:
            if name in cards:
                col.addWidget(cards[name])
        col.addStretch(1)
        cols.addLayout(col, 1)
    root.addLayout(cols, 1)
    page.sw7_columns = {name: cards[name] for name in cards}
    # Colour theme: two columns of swatches in the half-width card, so the palette names are not cut off
    grid = cards.get("SYSTEM COLOUR PALETTE").layout() if "SYSTEM COLOUR PALETTE" in cards else None
    if grid is not None and hasattr(grid, "itemAtPosition"):
        title_item = grid.itemAtPosition(0, 0)
        swatches = []
        for r in range(1, grid.rowCount()):
            for c in range(grid.columnCount()):
                item = grid.itemAtPosition(r, c)
                if item is not None and item.widget() is not None and item.widget() not in swatches:
                    swatches.append(item.widget())
        for sw in swatches:
            grid.removeWidget(sw)
        if title_item is not None and title_item.widget() is not None:
            title = title_item.widget(); grid.removeWidget(title); grid.addWidget(title, 0, 0, 1, 2)
        for i, sw in enumerate(swatches):
            grid.addWidget(sw, 1 + i // 2, i % 2)
        grid.setContentsMargins(20, 16, 20, 16); grid.setSpacing(12)
        page.sw7_swatches = swatches
    # Sizes: 16 px text, 64 px rows, 13 px section titles
    for w in content.findChildren(QLabel):
        if w.objectName() == "sectionTitle":
            w.setFont(THEME.font(SECTION_PX, QFont.Weight.Black))
        elif w.text() != "Settings":
            w.setFont(THEME.font(TEXT_PX, w.font().weight()))
        if w.text().startswith("Changes apply and save immediately"):
            w.setText("Changes apply and save immediately.")
            w.setFont(THEME.font(HINT_PX)); w.setWordWrap(False)
    for kind in (QCheckBox, QComboBox, QLineEdit, QPushButton, QSlider):
        for w in content.findChildren(kind):
            w.setFont(THEME.font(TEXT_PX, QFont.Weight.DemiBold))
            w.setMinimumHeight(ROW_H)
    for grid_owner in cards.values():
        lay = grid_owner.layout()
        if lay is not None:
            lay.setContentsMargins(20, 16, 20, 16)
            if hasattr(lay, "setVerticalSpacing"):
                lay.setVerticalSpacing(8)
    _settings_theme(page)


def _toggle_knobs():
    """Two 64 x 36 knob images (off: knob left in text_dim; on: knob right in text), drawn with the theme colours."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter
    from ..theme import THEME
    folder = os.path.join(tempfile.gettempdir(), "sw7_layout")
    os.makedirs(folder, exist_ok=True)
    out = []
    for checked, colour in ((False, THEME.hex("text_dim")), (True, THEME.hex("text"))):
        path = os.path.join(folder, f"knob{TOGGLE_W}_{'on' if checked else 'off'}_{colour.strip('#')}.png").replace("\\", "/")
        if not os.path.isfile(path):
            w, h = TOGGLE_W - 4, TOGGLE_H - 4          # inside the 2 px border
            img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)
            p = QPainter(img); p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(colour))
            d = h - 6
            x = w - d - 3 if checked else 3
            p.drawEllipse(QRectF(x, 3, d, d)); p.end()
            img.save(path)
        out.append(path)
    return out


def _settings_theme(page, *_a, **_k):
    if not hasattr(page, "sw7_columns"):
        return    # still inside the team's __init__; _settings_init styles it
    from ..theme import THEME
    off, on = _toggle_knobs()
    track = THEME.hex("card_alt")
    page.setStyleSheet(page.styleSheet() + f"""
        QCheckBox {{ spacing: 14px; }}
        QCheckBox::indicator {{ width: {TOGGLE_W - 4}px; height: {TOGGLE_H - 4}px; border-radius: {TOGGLE_H // 2}px;
            border: 2px solid {THEME.hex('border')}; background: {track}; image: url({off}); }}
        QCheckBox::indicator:checked {{ background: {THEME.hex('accent')}; border-color: {THEME.hex('accent')};
            image: url({on}); }}
        QSlider::groove:horizontal {{ height: 8px; border-radius: 4px; background: {track}; }}
        QSlider::sub-page:horizontal {{ background: {THEME.hex('accent')}; border-radius: 4px; }}
        QSlider::handle:horizontal {{ width: {HANDLE}px; height: {HANDLE}px; margin: -{(HANDLE - 8) // 2}px 0;
            border-radius: {HANDLE // 2}px; background: {THEME.hex('accent')}; }}
        QComboBox, QLineEdit {{ border-radius: 12px; padding: 4px 12px; }}
        QPushButton {{ border-radius: 12px; padding: 4px 18px; }}
        """)


# ---- Charging ----------------------------------------------------------------------------------------------------
def ring_texts(vis):
    """('80%', '5.8 of 7.2 kWh') for the Charging ring: the status bar's rounding, pack size from VEHICLE_SPEC."""
    from ..asis.config import VEHICLE_SPEC
    unknown = getattr(vis, "unknown", {}).get("soc")
    soc = None if unknown else float(vis.current_soc)
    pack = VEHICLE_SPEC.battery_capacity_wh / 1000.0
    energy = "--" if soc is None else f"{max(0.0, min(100.0, soc)) / 100.0 * pack:.1f}"
    return f"{soc_text(soc)}%", f"{energy} of {pack:.1f} kWh"


def paint_ring_soc(vis, p, cx, cy):
    """The SOC in the ring (48 px on screen) and the stored energy under it (20 px), above the tuk-tuk's roof."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QPen
    from ..pages.charging_page import get_mono_font
    from ..theme import THEME
    scale = p.transform().m11() or 1.0       # the ring is drawn in a 500 x 560 design space, scaled to fit
    soc, energy = ring_texts(vis)
    font = get_mono_font(10, QFont.Weight.Black); font.setPixelSize(max(8, round(RING_SOC_PX / scale)))
    p.setFont(font); p.setPen(QPen(QColor("#52E560")))
    p.drawText(QRectF(cx - 130, cy - 232, 260, 50), Qt.AlignmentFlag.AlignCenter, soc)
    font = get_mono_font(10, QFont.Weight.Bold); font.setPixelSize(max(8, round(RING_ENERGY_PX / scale)))
    p.setFont(font); p.setPen(QPen(THEME.color("text")))
    p.drawText(QRectF(cx - 130, cy - 184, 260, 24), Qt.AlignmentFlag.AlignCenter, energy)


def _install_charging(mod):
    def badge_refresh(badge, *_a, **_k):
        label = getattr(badge, "sw7_label", None)
        if label is not None:
            label.setText(f"Source: {badge.charge_type.capitalize()}")

    def badge_init(badge, *_a, **_k):
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QLabel
        from ..theme import THEME
        for pill in (badge._solar_pill, badge._wired_pill, badge._unknown_pill):
            pill.hide()
        badge.sw7_label = QLabel()
        badge.sw7_label.setObjectName("sw7ChargeSource")
        badge.sw7_label.setFont(THEME.font(STATE_PX, QFont.Weight.DemiBold))
        badge.sw7_label.setFixedHeight(SOURCE_H)
        badge.sw7_label.setStyleSheet(f"color:{THEME.hex('text')};background:transparent;")
        badge.layout().addWidget(badge.sw7_label)
        badge.layout().addStretch(1)
        badge_refresh(badge)

    def page_init(page, *_a, **_k):
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QLabel
        from ..theme import THEME
        page.layout().setContentsMargins(MARGIN, 16, MARGIN, 16)
        for w in page.findChildren(QLabel):
            t = w.text()
            if t == "PIT LANE CHARGING DECK":
                w.setText("Charging"); w.setFont(THEME.font(TITLE_PX, QFont.Weight.Bold)); page.sw7_title = w
            elif t == "CHARGE SOURCE":
                w.hide()
            elif t in ("LIVE POWER INPUT RATE (kW)", "PACK CORE TEMPERATURE", "TIME TO FULL", "CHARGING POWER",
                       "RANGE ADDED", "ENERGY DELIVERED"):
                w.setText({"LIVE POWER INPUT RATE (kW)": "Power input (kW)", "PACK CORE TEMPERATURE": "Pack temperature",
                           "TIME TO FULL": "Time to full", "CHARGING POWER": "Charging power",
                           "RANGE ADDED": "Range added", "ENERGY DELIVERED": "Energy delivered"}[t])
                w.setFont(THEME.font(TILE_LABEL_PX, QFont.Weight.DemiBold)); w.setObjectName("dim")
        page.status.setFont(THEME.font(STATE_PX, QFont.Weight.DemiBold)); page.status.setObjectName("dim")
        page.status.setText("Not charging")
        for card in (page.card_eta, page.card_rate, page.card_range, page.card_energy):
            f = card.value_label.font(); f.setPixelSize(TILE_VALUE_PX); card.value_label.setFont(f)
            card.setMinimumHeight(84)
        f = page.thermal_value.font(); f.setPixelSize(TEXT_PX + 2); page.thermal_value.setFont(f)
        page.power_graph.setMinimumHeight(110)
        page.thermal_bar.setMinimumHeight(12)

    def page_update(page, s, *_a, **_k):
        charging = bool(getattr(s, "charging", False))
        source = str(getattr(s, "charging_source", None) or "unknown").lower()
        from ..theme import THEME
        if charging:
            page.status.setText("Charging" + (f" · {source}" if source in ("solar", "wired") else ""))
            page.status.setStyleSheet(f"color:{THEME.status('normal').name()};background:transparent;")
        else:
            page.status.setText("Not charging")
            page.status.setStyleSheet(f"color:{THEME.hex('text_dim')};background:transparent;")

    def graph_paint(graph, *_a, **_k):
        if graph.history and max(graph.history) > 0.0:
            return
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPainter
        from ..theme import THEME
        p = QPainter(graph)
        p.setPen(THEME.color("text_dim")); p.setFont(THEME.font(STATE_PX))
        p.drawText(graph.rect(), Qt.AlignmentFlag.AlignCenter, "No charging data")
        p.end()

    _wrap(mod._ChargeTypeBadge, "__init__", after=badge_init)
    _wrap(mod._ChargeTypeBadge, "_refresh", after=badge_refresh)
    _wrap(mod.ChargingPage, "__init__", after=page_init)
    _wrap(mod.ChargingPage, "update_state", after=page_update)
    _wrap(mod._LivePowerGraph, "paintEvent", after=graph_paint)
