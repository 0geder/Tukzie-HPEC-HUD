"""SW-7: let the map's simulated drive reach the Driving page and the status bar.

While the map runs a simulated drive (sw7_tile_map.SW7TileMap.start_simulation), the Driving page and
the status bar are given a copy of the live vehicle state with the simulated speed and heading, and a
"SIMULATED DRIVE" badge is shown on the Driving page. Only speed and heading are simulated: battery,
ToF obstacles and camera hazards stay live, so they can still be exercised during a simulated drive.
The other pages (Analytics, Diagnostics, Charging) always get the real state, so a simulated drive never
adds to trip distance or energy figures.
"""
import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

try:
    from ..theme import THEME
except ImportError:          # tests import it outside the app package
    THEME = None

BADGE_TEXT = "SIMULATED DRIVE · not live speed"


def _badge(page):
    badge = getattr(page, "_sw7_sim_badge", None)
    if badge is None:
        badge = QLabel(BADGE_TEXT, page)
        badge.setObjectName("sw7SimBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        warn = THEME.status("warn").name() if THEME is not None else "#FFB224"
        badge.setStyleSheet(f"QLabel#sw7SimBadge {{ background: {warn}; color: #0B0D10; border-radius: 10px;"
                            " padding: 6px 16px; font-weight: 700; font-size: 15px; }")
        badge.adjustSize()
        badge.hide()
        page._sw7_sim_badge = badge
    return badge


def _show_badge(page, on):
    if page is None:
        return
    badge = _badge(page)
    if on:
        badge.adjustSize()
        # between the warning-icon row and the top of the speed dial, clear of the indicator arrows
        badge.move(max(0, (page.width() - badge.width()) // 2), int(page.height() * 0.17))
        badge.raise_()
        badge.show()
    else:
        badge.hide()


def refresh(main):
    """Re-show the Driving page and status bar now (called on each simulated-drive step, since in live-only
    mode no new vehicle state arrives while the Pi 4 link is down)."""
    shown = sim_view(main, getattr(main, "current_state", None))
    if shown is None:
        return
    for fn in (getattr(getattr(main, "status", None), "update_state", None),
               getattr(getattr(main, "driving", None), "set_state", None)):
        if fn is not None:
            try:
                fn(shown)
            except Exception as exc:          # a page error must not stop the simulation
                print(f"[SW-7] simulated drive: page update failed: {exc}")


def connect(main):
    m = getattr(getattr(main, "navigation", None), "map", None)
    if m is not None and hasattr(m, "sim_tick"):      # the team's own map has no simulated drive
        m.sim_tick.connect(lambda: refresh(main))


def sim_view(main, state):
    """The state the Driving page and status bar should show: the live state, or during a simulated
    drive a copy with the simulated speed and heading."""
    nav = getattr(main, "navigation", None)
    m = getattr(nav, "map", None)
    driving = getattr(main, "driving", None)
    simulating = bool(getattr(m, "simulating", False)) and getattr(m, "vehicle", None) is not None
    _show_badge(driving, simulating)
    if not simulating or state is None:
        return state
    s = copy.copy(state)
    from .sw7_tile_map import SIM_KMH
    s.speed_kmh = 0.0 if getattr(m, "sim_arrived", False) else float(SIM_KMH)
    s.heading = getattr(m, "heading", None)
    validity = dict(getattr(state, "signal_validity", None) or {})
    validity["speed"] = True
    validity["heading"] = s.heading is not None
    s.signal_validity = validity
    s.data_source = "sw7_simulated_drive"
    s.sw7_simulated = True
    return s
