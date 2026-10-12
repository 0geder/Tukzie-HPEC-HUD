"""SW-7 layout pass for the team's Diagnostics page (Planning/layout-improvements-prompt.md, agent C).

The team's page is one dense list: a two-column table of every vehicle field, the ride and link card, then
"ASIS, ROUTE & VOICE STATUS" as about 27 small rows. install_diagnostics() regroups it, without changing what
the page computes:

  - four cards in a 2 x 2 grid, each with a 14 px accent caps header and a status dot:
    Drive (speed, gear, throttle, brake, power, source), Energy (SOC, battery temp, motor temp, ambient,
    range, charging), Position (GPS, altitude, odometer, incline), Link (Pi 4, link, ESP32 age, MQTT, signal,
    IMU rate, IMU drops); labels 14 px, values 18 px bold;
  - the data source and the Pi 4 address in plain words; the raw strings move to the details;
  - the ASIS, route and voice list folded away behind a 64 px "Show advice and details" row;
  - the ride and link card is hidden: ToF and vibration are on the Sensors page, and its link health is in
    the Link card (it still receives the telemetry, which the Link card reads from it).

The page keeps its scroll area, so sw7_touch.enable_all still gives it finger-drag scrolling. With
TUKZIE_SW7_LAYOUT=0 nothing here runs and the page is the team's (as patched) exactly.
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSpacerItem,
                               QVBoxLayout, QWidget)

from ..theme import THEME
from ..widgets.themed_surfaces import ThemedCard

CARDS = (
    ("DRIVE", ("Speed", "Gear", "Throttle", "Brake", "Signed power", "Source")),
    ("ENERGY", ("Battery SOC", "Battery temp", "Motor temp", "Ambient", "Range", "Charging")),
    ("POSITION", ("GPS", "Altitude", "Odometer", "Incline")),
)
CAPTION = {"Signed power": "Power", "Source": "Data"}
LINK_ROWS = (("pi4", "Pi 4"), ("link", "Link"), ("age", "ESP32 age"), ("mqtt", "MQTT"), ("csq", "Signal"),
             ("imu_hz", "IMU rate"), ("drops", "IMU drops"))
RAW_ROWS = ("Source", "Charging source", "Pi 4 address")
SOURCE_WORDS = {
    "sw7_telemetry": "Live (Pi 4)", "sw7_replay": "Replay (recorded file)", "sw7_simulated_drive": "Simulated drive",
    "no_data": "No data", "simulation": "Simulation", "live_controller": "Live (controller)",
}
LINK_WORDS = {"live": ("Live", "normal"), "stale": ("ESP32 stale", "warn"), "offline": ("Offline", "inactive")}
UNKNOWN = ("Unavailable", "--", "", "None", "unavailable")


def enabled():
    """TUKZIE_SW7_LAYOUT, default on; 0 keeps the earlier layout exactly."""
    return os.environ.get("TUKZIE_SW7_LAYOUT", "1").strip() != "0"


def pi4_words(host, how=""):
    """The Pi 4 address in plain words."""
    if not host:
        return "Searching"
    if host in ("127.0.0.1", "localhost"):
        return "On this Pi"
    if host == "10.20.0.1":
        return "Wired (10.20.0.1)"
    return host


class _Card(ThemedCard):
    """A Diagnostics card: header with a status dot, then caption/value rows."""

    def __init__(self, title, rows):
        super().__init__("accent")
        self.setObjectName("sw7DiagCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 14, 20, 16)
        lay.setSpacing(8)
        head = QHBoxLayout(); head.setSpacing(10)
        self.dot = QLabel(); self.dot.setFixedSize(12, 12)
        head.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self.title = QLabel(title); self.title.setObjectName("sw7DiagHeader")
        self.title.setFont(THEME.font(14, QFont.Weight.Black))
        head.addWidget(self.title); head.addStretch(1)
        lay.addLayout(head)
        grid = QGridLayout(); grid.setHorizontalSpacing(16); grid.setVerticalSpacing(6)
        self.values, self.captions = {}, []
        for i, (key, caption) in enumerate(rows):
            cap = QLabel(caption); cap.setObjectName("sw7DiagCaption"); cap.setFont(THEME.font(14))
            val = QLabel("--"); val.setObjectName("sw7DiagValue"); val.setFont(THEME.font(18, QFont.Weight.Bold))
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(cap, i, 0); grid.addWidget(val, i, 1)
            self.values[key] = val; self.captions.append(cap)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        lay.addStretch(1)
        self.set_dot("inactive")

    def set_dot(self, status):
        self.dot.setStyleSheet(f"background: {THEME.color(status).name()}; border-radius: 6px; border: none;")


def _take(root, widget):
    if widget is not None:
        root.removeWidget(widget)
        widget.hide()


def install_diagnostics(page, root, card, separator, support_title, support):
    """Regroup the team's DiagnosticsPage (called at the end of its __init__)."""
    ride = getattr(page, "ride_card", None)
    for w in (card, ride, separator, support_title, support):
        _take(root, w)
    while root.count() and isinstance(root.itemAt(root.count() - 1), QSpacerItem):
        root.takeAt(root.count() - 1)                      # the team's trailing stretch
    root.setContentsMargins(24, 16, 24, 24)
    root.setSpacing(16)
    for i in range(root.count()):
        title = root.itemAt(i).widget()
        if isinstance(title, QLabel):
            title.setFont(THEME.font(24, QFont.Weight.Bold))   # one title style across pages
            break

    old_values = page._values
    cards = []
    grid = QGridLayout(); grid.setHorizontalSpacing(16); grid.setVerticalSpacing(16)
    new_values = {}
    for n, (title, names) in enumerate(CARDS):
        c = _Card(title, [(name, CAPTION.get(name, name)) for name in names])
        cards.append((c, names))
        new_values.update(c.values)
        grid.addWidget(c, n // 2, n % 2)
    link = _Card("LINK", LINK_ROWS)
    grid.addWidget(link, 1, 1)
    grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)
    root.addLayout(grid)

    # Details: the ASIS, route and voice list, plus the raw strings, folded away.
    toggle = QPushButton("Show advice and details (ASIS, route, voice)")
    toggle.setObjectName("sw7DetailsToggle"); toggle.setCheckable(True)
    toggle.setMinimumHeight(64); toggle.setFont(THEME.font(18, QFont.Weight.Bold))
    toggle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    root.addWidget(toggle)
    details = QFrame(); details.setObjectName("sw7DetailsCard")
    dl = QVBoxLayout(details); dl.setContentsMargins(20, 14, 20, 16); dl.setSpacing(10)
    raw = QWidget(); raw.setObjectName("transparentSupportGrid")
    rg = QGridLayout(raw); rg.setContentsMargins(0, 0, 0, 0); rg.setHorizontalSpacing(26); rg.setVerticalSpacing(7)
    raw_values = {}
    for i, name in enumerate(RAW_ROWS):
        cap = QLabel(name.upper()); cap.setObjectName("supportCaption"); cap.setFont(THEME.font(13, QFont.Weight.Bold))
        val = QLabel("--"); val.setObjectName("supportValue"); val.setFont(THEME.font(14, QFont.Weight.DemiBold))
        val.setAlignment(Qt.AlignmentFlag.AlignRight); val.setWordWrap(True)
        rg.addWidget(cap, i // 2, (i % 2) * 2); rg.addWidget(val, i // 2, (i % 2) * 2 + 1)
        raw_values[name] = val
    support_title.setText("ASIS, ROUTE & VOICE STATUS")
    support_title.setFont(THEME.font(14, QFont.Weight.Bold))
    sg = support.layout()
    for i in range(sg.count()):
        w = sg.itemAt(i).widget()
        if isinstance(w, QLabel):
            w.setFont(THEME.font(13, QFont.Weight.Bold) if w.objectName() == "supportCaption"
                      else THEME.font(14, QFont.Weight.DemiBold))
    for w in (raw, support_title, support):
        dl.addWidget(w); w.show()
    details.hide()
    root.addWidget(details)
    root.addStretch(1)

    def set_open(on):
        details.setVisible(on)
        toggle.setText("Hide advice and details" if on else "Show advice and details (ASIS, route, voice)")
    toggle.toggled.connect(set_open)

    # The team's FIELDS still drive update_state; the visible labels are the cards' (raw ones go to details).
    hidden = {name: lab for name, lab in old_values.items() if name not in new_values}
    old_values.update(new_values)
    team_update = page.update_state

    def update_state(s):
        team_update(s)
        raw_source = str(getattr(s, "data_source", "") or "--")
        new_values["Source"].setText(SOURCE_WORDS.get(raw_source, raw_source))
        raw_values["Source"].setText(raw_source)
        if "Charging source" in hidden:
            raw_values["Charging source"].setText(hidden["Charging source"].text())
        for c, names in cards:
            known = any(new_values[n].text() not in UNKNOWN for n in names if n != "Source")
            c.set_dot("normal" if known else "inactive")
    page.update_state = update_state

    def refresh_link():
        if ride is None:
            return
        word, status = LINK_WORDS.get(ride.link, LINK_WORDS["offline"])
        if getattr(ride, "replay", False):
            word, status = "Replay", "warn"
        link.values["link"].setText(word)
        link.values["link"].setStyleSheet(f"background: transparent; color: {THEME.color(status).name()};")
        for key, _ in LINK_ROWS:
            if key in ("pi4", "link"):
                continue
            text = ride.text_of(key)
            st = ride._status.get(key)
            colour = THEME.hex("text_dim") if text in UNKNOWN or ride.link != "live" else (
                THEME.color(st).name() if st else THEME.hex("text"))
            link.values[key].setText(text)
            link.values[key].setStyleSheet(f"background: transparent; color: {colour};")
        link.set_dot(status)

    if ride is not None:
        # dashboard_main connects the provider to ride_card.set_telemetry and set_endpoint after this runs,
        # and the card's own watchdog calls self.set_telemetry, so wrapping the bound methods covers both.
        ride_set, ride_endpoint = ride.set_telemetry, ride.set_endpoint

        def set_telemetry(telemetry):
            ride_set(telemetry)
            refresh_link()

        def set_endpoint(host, how=""):
            ride_endpoint(host, how)
            link.values["pi4"].setText(pi4_words(host, how))
            raw_values["Pi 4 address"].setText(f"{host} ({how})" if host else "searching")
        ride.set_telemetry, ride.set_endpoint = set_telemetry, set_endpoint
        link.values["pi4"].setText("Searching")
        refresh_link()

    def theme(*_):
        page.setStyleSheet(page.styleSheet() + f"""
        QLabel#sw7DiagHeader {{ color: {THEME.hex('accent')}; letter-spacing: 1px; }}
        QLabel#sw7DiagCaption {{ color: {THEME.hex('text_dim')}; }}
        QFrame#sw7DetailsCard {{ background: {THEME.hex('card')}; border: 1px solid {THEME.hex('border')}; border-radius: 16px; }}
        QPushButton#sw7DetailsToggle {{ background: {THEME.hex('card_alt')}; color: {THEME.hex('text')};
            border: 1px solid {THEME.hex('border')}; border-radius: 12px; text-align: left; padding: 0px 20px; }}
        QPushButton#sw7DetailsToggle:checked {{ border-color: {THEME.hex('accent')}; }}
        """)
    THEME.changed.connect(theme)       # after the team's _theme, which resets the page stylesheet
    theme()
    page._sw7_layout = {"cards": [c for c, _ in cards] + [link], "toggle": toggle, "details": details,
                        "link": link, "raw": raw_values}
    return page._sw7_layout
