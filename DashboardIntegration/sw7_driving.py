"""
SW7DrivePanel: the centre of the Driving page in the SW-7 theme (TUKZIE_SW7_THEME, on by default).

Replaces the team's 0 to 50 dial and the brake and accelerator bars (the vehicle has no pedal
sensors, so those bars could only ever show "--") with three values a driver can read in one
glance, sized from Research/DashboardDesign for a 10.1-inch 1280 x 800 panel at about 70 cm:

  - speed as a large number, capital height about 120 px (about 100 arc minutes);
  - battery state of charge and range as two tiles, values about 48 px high, labels about 24 px
    (ISO 15008's 20 arc minutes recommended is about 24 px at that distance).

A value with no live source is shown as "--", never as 0 (live-only mode). Battery colour follows
the theme's status colours: red under 15 %, amber under 30 %, otherwise green, and the value is
always printed, so colour is never the only cue.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..theme import THEME

SPEED_PX = 170      # font pixel size; capital height about 120 px in Atkinson Hyperlegible
VALUE_PX = 72       # about 48 px capitals
LABEL_PX = 34       # about 24 px capitals


def _num(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


class SW7DrivePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.speed = None
        self.soc = None
        self.range_km = None
        self.setMinimumSize(560, 420)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        THEME.changed.connect(self.update)

    def set_state(self, s):
        valid = getattr(s, "signal_validity", None) or {}
        self.speed = None if valid.get("speed") is False else _num(getattr(s, "speed_kmh", None))
        self.soc = None if valid.get("soc") is False else _num(getattr(s, "soc_pct", None))
        self.range_km = _num(getattr(s, "range_km", None)) if self.soc is not None else None
        self.update()

    def _font(self, px, weight=QFont.Weight.Bold):
        f = THEME.font(px, weight)
        f.setPixelSize(px)
        return f

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        text, dim = QColor(THEME.hex("text")), QColor(THEME.hex("text_dim"))

        # speed
        speed_h = min(h * 0.52, SPEED_PX * 1.15)
        p.setPen(text)
        p.setFont(self._font(SPEED_PX, QFont.Weight.Bold))
        speed = "--" if self.speed is None else f"{self.speed:.0f}"
        p.drawText(QRectF(0, 0, w, speed_h), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, speed)
        p.setPen(dim)
        p.setFont(self._font(LABEL_PX, QFont.Weight.Normal))
        unit_y = speed_h - p.fontMetrics().descent() * 0 - SPEED_PX * 0.16   # tuck the unit under the digits
        p.drawText(QRectF(0, unit_y, w, LABEL_PX * 1.4), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "km/h")

        # battery and range tiles
        top = speed_h - SPEED_PX * 0.16 + LABEL_PX * 1.9
        tile_h = max(150.0, min(190.0, h - top - 8))
        gap = 24
        tile_w = min(360.0, (w - gap) / 2)
        x0 = (w - (2 * tile_w + gap)) / 2
        soc_status = None if self.soc is None else ("crit" if self.soc < 15 else "warn" if self.soc < 30 else "normal")
        tiles = (
            ("BATTERY", "--" if self.soc is None else f"{self.soc:.0f} %", soc_status, self.soc),
            ("RANGE", "--" if self.range_km is None else f"{self.range_km:.0f} km", None, None),
        )
        for i, (label, value, status, fill) in enumerate(tiles):
            r = QRectF(x0 + i * (tile_w + gap), top, tile_w, tile_h)
            p.setPen(QPen(QColor(THEME.hex("border")), 1.2))
            p.setBrush(QColor(THEME.hex("card")))
            p.drawRoundedRect(r, 12, 12)
            p.setPen(dim)
            p.setFont(self._font(LABEL_PX, QFont.Weight.Bold))
            p.drawText(r.adjusted(22, 14, -22, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, label)
            p.setPen(THEME.status(status) if status else text)
            p.setFont(self._font(VALUE_PX, QFont.Weight.Bold))
            p.drawText(r.adjusted(22, LABEL_PX * 1.5, -22, -30), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, value)
            if fill is not None:                      # battery bar along the bottom of the tile
                bar = QRectF(r.left() + 22, r.bottom() - 26, r.width() - 44, 10)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(THEME.hex("track")))
                p.drawRoundedRect(bar, 5, 5)
                p.setBrush(THEME.status(status))
                p.drawRoundedRect(QRectF(bar.left(), bar.top(), bar.width() * max(0.0, min(1.0, fill / 100.0)), bar.height()), 5, 5)
        p.end()
