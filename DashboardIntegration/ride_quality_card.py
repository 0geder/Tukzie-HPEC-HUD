"""
RideQualityCard: a compact card with the SW-7 telemetry the dashboard has no
fields for (TELEMETRY_LINK.md, section 3).

Shows vibration level, IMU disagreement, IMU sample rates and drops, motor
rpm, raw GNSS speed (units unconfirmed), modem signal quality, MQTT up or
down, and the three ToF distances in metres, with a Live / ESP32 stale /
Offline pill.

Feed it from LiveDataProvider.telemetry_updated: set_telemetry(dict) with the
raw /telemetry JSON, or set_telemetry(None) when the bridge is unreachable.
It turns itself to Offline if nothing arrives for 3 s.

Drop this file into app/widgets/ and wire it up as described in
DashboardIntegration/README.md. QtWidgets only, colours from THEME.
"""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

from ..theme import THEME

STALE_MS = 3000          # same threshold as the live-data provider
WATCHDOG_MS = 3000       # no update at all for this long: show Offline
TOF_NEAR_M = 1.0         # ToF readings under this are shown in the warning colour
CSQ_WEAK = 10            # modem signal quality under this is shown as weak

# (key, caption) in display order, four per row
FIELDS = (
    ("vib", "Vibration"), ("vib_dis", "IMU disagreement"), ("imu_hz", "IMU rate"), ("drops", "IMU drops"),
    ("rpm", "Motor"), ("spd_raw", "GNSS speed (raw)"), ("csq", "Signal"), ("mqtt", "MQTT"),
    ("tof_left", "ToF left"), ("tof_ahead", "ToF ahead"), ("tof_right", "ToF right"), ("age", "ESP32 age"),
)


def _num(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _pair(value, fmt):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    a, b = _num(value[0]), _num(value[1])
    if a is None and b is None:
        return None
    return " / ".join("--" if x is None else fmt.format(x) for x in (a, b))


def format_telemetry(telemetry):
    """Return (link, {key: (text, status_key or None)}) for one /telemetry reply.

    link is "live", "stale" or "offline". status_key is a THEME status key
    (normal, warn, crit) for values worth colouring; None keeps the text colour."""
    blank = {key: ("--", None) for key, _ in FIELDS}
    if not isinstance(telemetry, dict):
        return "offline", blank
    out = dict(blank)
    esp = telemetry.get("esp32") if isinstance(telemetry.get("esp32"), dict) else None
    age = _num(esp.get("age_ms")) if esp else None
    link = "live" if age is not None and age <= STALE_MS else "stale"

    if esp:
        vib = _num(esp.get("vib"))
        if vib is not None:
            out["vib"] = (f"{vib:.2f} m/s²", None)
        dis = _num(esp.get("vib_dis"))
        if dis is not None:
            out["vib_dis"] = (f"{dis:.2f}", None)
        hz = _pair(esp.get("imu_hz"), "{:.0f}")
        if hz:
            out["imu_hz"] = (hz + " Hz", None)
        drops = _pair(esp.get("drops"), "{:.0f}")
        if drops:
            out["drops"] = (drops, None)
        rpm = _num(esp.get("rpm"))
        if rpm is not None:
            out["rpm"] = (f"{rpm:.0f} rpm", None)
        spd = _num(esp.get("spd_raw"))
        if spd is not None:
            out["spd_raw"] = (f"{spd:.1f}", None)
        csq = _num(esp.get("csq"))
        if csq is not None and 0 <= csq <= 31:
            out["csq"] = (f"{csq:.0f} / 31", "warn" if csq < CSQ_WEAK else "normal")
        mqtt = esp.get("mqtt")
        if isinstance(mqtt, bool):
            out["mqtt"] = ("Up", "normal") if mqtt else ("Down", "warn")
        if age is not None:
            out["age"] = (f"{age / 1000:.1f} s", "warn" if link == "stale" else None)
    else:
        out["age"] = ("No data", "warn")

    tof = telemetry.get("tof") if isinstance(telemetry.get("tof"), dict) else None
    if tof:
        tof_age = _num(tof.get("age_ms"))
        tof_fresh = tof_age is None or tof_age <= STALE_MS
        for side in ("left", "ahead", "right"):
            mm = _num(tof.get(f"{side}_mm"))
            if mm is not None and tof_fresh:
                m = mm / 1000.0
                out[f"tof_{side}"] = (f"{m:.2f} m", "warn" if m < TOF_NEAR_M else None)
    return link, out


class RideQualityCard(QFrame):
    LINK_TEXT = {"live": "Live", "stale": "ESP32 stale", "offline": "Offline"}
    LINK_STATUS = {"live": "normal", "stale": "warn", "offline": "inactive"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rideQualityCard")
        self.link = "offline"
        self._values = {}
        self._status = {}
        self._captions = []

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 12, 18, 14)
        root.setSpacing(8)
        header = QHBoxLayout()
        self.title = QLabel("RIDE QUALITY AND LINK")
        self.title.setFont(THEME.font(12, QFont.Weight.Bold))
        header.addWidget(self.title)
        header.addStretch(1)
        self.pill = QLabel()
        self.pill.setFont(THEME.font(11, QFont.Weight.Bold))
        self.pill.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        header.addWidget(self.pill)
        root.addLayout(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(2)
        for i, (key, caption) in enumerate(FIELDS):
            row, col = (i // 4) * 2, i % 4
            cap = QLabel(caption.upper())
            cap.setFont(THEME.font(9, QFont.Weight.Bold))
            if row:
                cap.setContentsMargins(0, 6, 0, 0)
            val = QLabel("--")
            val.setFont(THEME.font(17, QFont.Weight.Bold))
            grid.addWidget(cap, row, col)
            grid.addWidget(val, row + 1, col)
            self._captions.append(cap)
            self._values[key] = val
            self._status[key] = None
        for col in range(4):
            grid.setColumnStretch(col, 1)
        root.addLayout(grid)
        root.addStretch(1)

        self._watchdog = QTimer(self)
        self._watchdog.setSingleShot(True)
        self._watchdog.setInterval(WATCHDOG_MS)
        self._watchdog.timeout.connect(lambda: self.set_telemetry(None))

        THEME.changed.connect(self._theme)
        self._theme()
        self.set_telemetry(None)

    def set_telemetry(self, telemetry):
        """telemetry: raw /telemetry dict, or None when the bridge is unreachable."""
        self.link, values = format_telemetry(telemetry)
        for key, (text, status) in values.items():
            self._values[key].setText(text)
            self._status[key] = status
        if telemetry is not None:
            self._watchdog.start()
        self._paint_values()

    def text_of(self, key):
        return self._values[key].text()

    def _paint_values(self):
        dim = self.link != "live"
        for key, label in self._values.items():
            status = self._status[key]
            if dim:
                colour = THEME.hex("text_faint")
            elif status:
                colour = THEME.status(status).name()
            else:
                colour = THEME.hex("text")
            label.setStyleSheet(f"background: transparent; border: none; color: {colour};")
        colour = THEME.status(self.LINK_STATUS[self.link]).name()
        self.pill.setText(self.LINK_TEXT[self.link])
        self.pill.setStyleSheet(f"color: {colour}; background: transparent; border: 1px solid {colour};"
                                " border-radius: 9px; padding: 2px 10px;")

    def _theme(self, *_):
        self.setStyleSheet(f"QFrame#rideQualityCard {{ background: {THEME.hex('card')};"
                           f" border: 1px solid {THEME.hex('border')}; border-radius: 15px; }}")
        self.title.setStyleSheet(f"background: transparent; border: none; color: {THEME.hex('text')};")
        for cap in self._captions:
            cap.setStyleSheet(f"background: transparent; border: none; color: {THEME.hex('text_dim')};")
        self._paint_values()
