"""SW-7 paper and depth style, page agent P2: Surroundings, Diagnostics and Charging.

Planning/paper-depth-theme-prompt.md (sections 3 to 5, 9 and 10) and Planning/data-ownership-and-merge-plan.md.
Installed as app/pages/sw7_style_pages.py; dashboard_main.py calls install(DashboardMain) once at import time, after
sw7_style.install. Nothing happens with TUKZIE_SW7_STYLE=team (or TUKZIE_SW7_LAYOUT=0): the 8-page layout-pass build
stays exactly as it was. The team's files and our sensors_page.py and front_camera_page.py are not edited; this module
wraps their classes and regroups their widgets.

Surroundings (the Front camera and Sensors pages merged, 7 nav items)
  - The page id stays "sensors" (the obstacle pill, the swipe and the tests use it). "camera" and "surroundings" are
    aliases: switch_page_id("camera") or ("surroundings") opens it and selects its nav item. The camera's nav item is
    hidden and it leaves normal_ids, so the arrows and the two-finger swipe follow the new order:
    Drive, Analytics, Diagnostics, Map, Surroundings, Charging, Settings. The reverse camera page is untouched.
  - Middle plane: the camera frame, a raised charcoal slab with a cached shadow. The FrontCameraPage object moves
    inside it (so it still streams only while the page is on screen) and its status chip floats on the frame.
  - Top plane: the tuk-tuk seen from above, on a card overlapping the frame's lower edge by 24 px, with the left,
    ahead and right ToF distances at 22 px (the page's three secondary values), and the hazards card on the right.
  - One hazards list: the fusion's hazards (ToF, camera, camera + ToF) and the camera's own alerts, merged by class
    (a camera alert the fusion already has only adds its confidence), nearest first. The nearest is the hero, 150 px.
  - The Vehicle, Position and Ride and link cards go (their values live on Diagnostics, Charging and the status bar);
    a one-line Ride row (vibration, IMU disagreement) stays. The page's hidden battery row follows the dashboard's
    state, so during a simulated drive it is simulated like every other battery figure.
Diagnostics (one home per value)
  - Drive becomes Controls (throttle, brake, power), Energy becomes Health (motor temp, "Ambient (vehicle)", the
    weather's "Outside (weather)" as a signal glance that opens the weather card, BMS reading, motor rpm), Position
    gains GPS fix, heading and raw GNSS speed, Link gains firmware. Speed, gear, battery, range, battery temp,
    odometer, charging and the data source leave the cards; they stay in the folded details list.
Charging
  - The battery graphic is the middle plane, in front of the hero word CHARGE: the team's composition
    (Planning/reference_team_charging_page.jpg) restyled in paper and ink. A card disc with the ring arc, the tuk-tuk
    outline seen from above filled with rising bubbles to the state of charge, the percentage above it and the
    readings round the ring: power input, voltage and current on the left, charging state, time to full and cell
    health on the right (BatteryAnimation, 30 fps only while shown). Voltage and current come from the BMS when not
    charging (the charger values while charging); anything without a reading is "--", and cell health is the reported
    value or "--", never a made-up 98 %.
  - The "Time to full" and "Charging power" tiles go (the graphic has both). The tiles are Range (its home), Range
    added, Energy.

Tests: tests/test_style_pages.py (screenshots in tests/style/pages/).
"""
from __future__ import annotations

import math

from PySide6.QtCore import QEvent, QObject, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton, QGridLayout, QLabel, QPushButton, QWidget

from ..widgets import sw7_style as S

SURROUNDINGS = "sensors"                       # the page id other code uses
ALIASES = {"camera": SURROUNDINGS, "surroundings": SURROUNDINGS}
TITLE = "Surroundings"
BAND_LIMIT_M = {"immediate": 3.0, "warning": 8.0, "monitoring": 15.0}   # the camera's distance bands
SOURCE_WORD = {"tof": "ToF", "camera": "camera", "fused": "camera + ToF"}
STATUS_TOKEN = {"crit": "critical", "warn": "warn", "normal": "ok", "inactive": "ink_3"}
LINK_CHIP = {"live": ("Sensors live", "ok"), "stale": ("ESP32 stale", "warn"), "offline": ("Sensors offline", "ink_3")}
MAX_ROWS = 5

_installed = False


def _wrap(cls, name, after=None, replace=None):
    """Like sw7_style._swrap, with its own marker, so it can wrap what the layout pass and the core wrapped."""
    orig = getattr(cls, name)
    if getattr(orig, "_sw7_pages", False):
        return
    if replace is not None:
        def method(self, *a, **k):
            return replace(orig, self, *a, **k)
    else:
        def method(self, *a, **k):
            result = orig(self, *a, **k)
            after(self, *a, **k)
            return result
    method._sw7_pages = True
    method.__name__ = name
    setattr(cls, name, method)


def install(main_cls):
    """Called once from dashboard_main.py after sw7_style.install. Nothing with TUKZIE_SW7_STYLE=team."""
    global _installed
    if _installed or not S.enabled() or not getattr(S, "_installed", False):
        return                       # team style, or a build without the core (sw7_style.install not patched in)
    _installed = True
    from . import charging_page, front_camera_page, sensors_page
    _wrap(main_cls, "__init__", after=_main_init)
    _wrap(main_cls, "switch_page_id", replace=_switch_alias)
    # class level, before dashboard_main connects the provider to the bound method
    _wrap(sensors_page.SensorsPage, "set_telemetry", after=_sensors_telemetry)
    _wrap(front_camera_page.FrontCameraPage, "_show_pixmap", after=_camera_frame)
    _wrap(front_camera_page.StatusChip, "setText", after=_camera_chip)
    _install_charging(charging_page)


def _switch_alias(orig, main, pid, *a, **k):
    return orig(main, ALIASES.get(pid, pid), *a, **k)


def _main_init(main, *_a, **_k):
    _merge_surroundings(main)
    _diagnostics(main)
    _charging(main)


# ---- shared helpers ------------------------------------------------------------------------------------------------
def tok(status):
    """THEME status key (crit, warn, normal, inactive) -> palette token."""
    return STATUS_TOKEN.get(status, "ink_3")


def snap_fonts(root, keep=()):
    """Every visible-text label and button under root onto the scale: 13, 16 or 22 px (heroes untouched)."""
    for w in [root] + root.findChildren(QLabel) + root.findChildren(QAbstractButton):
        if w in keep or not hasattr(w, "text"):
            continue
        px = S.text_px(w)
        if px in S.TEXT_SIZES or S.HERO_MIN <= px <= S.HERO_MAX:
            if w.font().family() != S.family():
                w.setFont(S.font(px, w.font().weight()))
            continue
        new = S.LABEL if px <= 14 else S.BODY if px <= 19 else S.SECONDARY
        w.setFont(S.font(new, w.font().weight()))


def chip_style(label, text, dot_key):
    """An ink outline chip with a status dot (as the core's source chip), on a card fill so it reads on a photo."""
    dot = getattr(label, "sw7_dot", None)
    if dot is None:
        dot = label.sw7_dot = QLabel(label)
        dot.setFixedSize(8, 8)
        dot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    f = S.font(S.LABEL, QFont.Weight.Bold, caps=True)
    f.setCapitalization(QFont.Capitalization.AllUppercase)
    label.setFont(f)
    label.setStyleSheet(f"background: {S.hx('card')}; color: {S.hx('ink')}; border: 1px solid {S.hx('ink_3')};"
                        f" border-radius: {S.RADIUS_SM}px; padding: 0px 14px 0px 28px;")
    dot.setStyleSheet(f"background: {S.hx(dot_key)}; border-radius: 4px; border: none;")
    QLabel.setText(label, text)
    label.setFixedHeight(28)
    label.setFixedWidth(QFontMetrics(f).horizontalAdvance(text.upper()) + 60)
    dot.move(14, 10)


class _Bed(QObject):
    """Paints cached shadows (and, with fill, the cards themselves) under chosen children, before the host paints.
    Static cards then cost one cached pixmap each, not a live QGraphicsDropShadowEffect."""

    def __init__(self, host, cards, radius=20, level=2, fill=None, lines=False):
        super().__init__(host)
        self.cards, self.radius, self.level, self.fill, self.lines = list(cards), radius, level, fill, lines
        host.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Paint and S.enabled():
            p = QPainter(obj)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            for c in self.cards:
                if c.isVisibleTo(obj) and c.parentWidget() is obj:
                    r = QRectF(c.geometry())
                    if self.lines:                       # no card: a hairline over the group
                        p.fillRect(QRectF(r.left(), r.top(), r.width(), 1), S.c("hairline"))
                    elif self.fill:
                        S.paint_card(p, r, self.radius, self.level, self.fill)
                    else:
                        S.paint_shadow(p, r, self.radius, self.level)
            p.end()
        return False


# ==== Surroundings ===================================================================================================
def combined_hazards(telemetry, camera_alerts):
    """One list from the fusion's hazards and the camera's alerts, nearest first.

    A camera alert whose class the fusion already reports from the camera (source camera or fused) only adds its
    confidence to that row; any other alert is a camera-only row placed at its band's limit (under 3, 8 or 15 m).
    Rows: {cls, dist (m or None), band, where, source, conf}."""
    from .sensors_page import direction_of, hazards_of
    from ..widgets.ride_quality_card import _num
    rows = []
    for h in hazards_of(telemetry):
        rows.append({"cls": str(h.get("class") or "object").lower(), "dist": _num(h.get("distance_m")),
                     "band": h.get("band"), "where": direction_of(h), "source": str(h.get("source") or ""),
                     "conf": None, "matched": False})
    for a in camera_alerts or []:
        if not isinstance(a, dict):
            continue
        cls = str(a.get("class") or "object").lower()
        conf = a.get("confidence")
        conf = float(conf) if isinstance(conf, (int, float)) and not isinstance(conf, bool) else None
        match = next((r for r in rows if r["cls"] == cls and r["source"] in ("camera", "fused") and not r["matched"]),
                     None)
        if match is not None:
            match["matched"] = True
            if conf is not None:
                match["conf"] = conf
            continue
        rows.append({"cls": cls, "dist": None, "band": a.get("distance_band"), "where": "ahead", "source": "camera",
                     "conf": conf, "matched": True})

    def key(r):
        if r["dist"] is not None:
            return (0, r["dist"])
        lim = BAND_LIMIT_M.get(r["band"])
        return (0, lim) if lim is not None else (1, 0.0)
    rows.sort(key=key)
    return rows


def distance_text(row):
    from .sensors_page import TOF_MAX_M
    d = row["dist"]
    if d is not None:
        return f"{d:.2f} m" if d < TOF_MAX_M else f"{d:.1f} m"
    lim = BAND_LIMIT_M.get(row["band"])
    return f"under {lim:.0f} m" if lim else "distance unknown"


def row_texts(row):
    """(main line, detail line, THEME status key) for one hazard row."""
    from .sensors_page import BAND_STATUS, BAND_TEXT
    main = f"{row['cls'].capitalize()} {distance_text(row)} {row['where']}"
    src = SOURCE_WORD.get(row["source"], row["source"])
    if row["conf"] is not None:
        src += f" {row['conf'] * 100:.0f} %"
    detail = " · ".join(t for t in (BAND_TEXT.get(row["band"], row["band"] or ""), src) if t)
    return main, detail, BAND_STATUS.get(row["band"], "inactive")


def mark(p, rect, token, round_=True, ring=None):
    """A status mark (a dot or a bar) drawn without antialiasing, so its edges are the status colour itself and not
    a blend with the paper that the signal audit would read as near the signal hue."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    if ring:
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(S.c(ring))
        p.drawEllipse(rect.adjusted(-2, -2, 2, 2)) if round_ else p.drawRect(rect.adjusted(-2, -2, 2, 2))
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(S.c(token))
    p.drawEllipse(rect) if round_ else p.drawRect(rect)
    p.restore()


class HazardRow(QWidget):
    """One hazard, 52 px: a 4 px status bar (a small mark), the hazard in 16 px bold, the band and source in 13 px."""
    H = 52

    def __init__(self, parent):
        super().__init__(parent)
        self.main_text, self.detail_text, self.status, self.first = "", "", "inactive", False
        self.setFixedHeight(self.H)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_row(self, main, detail, status, first):
        self.main_text, self.detail_text, self.status, self.first = main, detail, status, first
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w = self.width()
        if not self.first:
            p.setPen(QPen(S.c("hairline"), 1)); p.drawLine(QPointF(0, 0.5), QPointF(w, 0.5))
        mark(p, QRect(0, 12, 4, 28), tok(self.status), round_=False)
        p.setPen(S.c("ink")); p.setFont(S.font(S.BODY, QFont.Weight.Bold))
        p.drawText(QRectF(18, 6, w - 18, 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.main_text)
        p.setPen(S.c("ink_2")); p.setFont(S.font(S.LABEL))
        p.drawText(QRectF(18, 28, w - 18, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.detail_text)
        p.end()


class TukFigure(QWidget):
    """The tuk-tuk from above (front up), with the left, ahead and right ToF distances placed round it like the tyre
    pressures in inspo_sports_car_tiles.jpg. Ink and paper: the zone arcs are ink (dashed ink_3 with no reading),
    the band shows only as a small dot at each sensor, the three distances are the page's 22 px values."""
    SIDES = ("left", "ahead", "right")
    PAD = (40, 24, 40, 48)          # room round the card for its own shadow (it overlaps the camera slab)
    RADIUS = 8

    def __init__(self, parent):
        super().__init__(parent)
        self.metres = {s: None for s in self.SIDES}
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_metres(self, metres):
        if metres != self.metres:
            self.metres = dict(metres)
            self.update()

    def values(self):
        from .sensors_page import zone_text
        return {s: zone_text(self.metres.get(s)) for s in self.SIDES}

    def card_rect(self):
        l, t, r, b = self.PAD
        return QRectF(self.rect()).adjusted(l, t, -r, -b)

    def geometry_of(self):
        """Body and sensor points in card coordinates."""
        w = self.card_rect().width()
        cx, nose = w / 2, 116.0
        bw, bl = 60.0, 100.0
        body = QRectF(cx - bw / 2, nose, bw, bl)
        sensors = {"ahead": QPointF(cx, nose), "left": QPointF(cx - bw / 2, nose + 44), "right": QPointF(cx + bw / 2, nose + 44)}
        return body, sensors

    def paintEvent(self, _e):
        from .sensors_page import TOF_MAX_M, tof_status
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        card = self.card_rect()
        S.paint_card(p, card, self.RADIUS, 1)            # a card with a hairline, a very light shadow
        p.translate(card.topLeft())
        w = card.width()
        AL = Qt.AlignmentFlag
        p.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True)); p.setPen(S.c("ink_2"))
        p.drawText(QRectF(24, 18, 260, 18), AL.AlignLeft | AL.AlignVCenter, "AROUND THE TUK-TUK")
        body, sensors = self.geometry_of()
        heading = {"ahead": 90.0, "left": 180.0, "right": 0.0}
        r_min, r_max = 18.0, 58.0
        radius = {}
        for side in self.SIDES:
            m = self.metres.get(side)
            frac = 1.0 if m is None else max(0.0, min(1.0, m / TOF_MAX_M))
            r = r_min + (r_max - r_min) * frac
            radius[side] = r
            c = sensors[side]
            box = QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r)
            wedge = QPainterPath(c); wedge.arcTo(box, heading[side] - 25, 50); wedge.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(S.c("paper_deep")); p.drawPath(wedge)
            if m is None:
                pen = QPen(S.c("ink_3"), 2, Qt.PenStyle.DashLine)
            elif m >= TOF_MAX_M:
                pen = QPen(S.c("ink_3"), 3)
            else:
                pen = QPen(S.c("ink"), 4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(box, int((heading[side] - 25) * 16), int(50 * 16))
        # body: narrow front, wide back, three wheels (as sensors_page.TukTukView, smaller)
        bw, x0, y0 = body.width(), body.left(), body.top()
        shell = QPainterPath()
        shell.moveTo(x0 + bw * 0.28, y0); shell.lineTo(x0 + bw * 0.72, y0)
        shell.quadTo(x0 + bw * 0.92, y0 + 6, x0 + bw, y0 + 40)
        shell.lineTo(x0 + bw, body.bottom() - 8); shell.quadTo(x0 + bw, body.bottom(), x0 + bw - 8, body.bottom())
        shell.lineTo(x0 + 8, body.bottom()); shell.quadTo(x0, body.bottom(), x0, body.bottom() - 8)
        shell.lineTo(x0, y0 + 40); shell.quadTo(x0 + bw * 0.08, y0 + 6, x0 + bw * 0.28, y0)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(S.c("ink_2"))
        for wx in (x0 - 7, body.right() - 5):
            p.drawRoundedRect(QRectF(wx, body.bottom() - 38, 12, 26), 4, 4)
        p.setPen(QPen(S.c("ink_2"), 2)); p.setBrush(S.c("card_alt")); p.drawPath(shell)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(S.c("ink_2"))
        p.drawRoundedRect(QRectF(body.center().x() - 5, y0 + 8, 10, 22), 4, 4)
        p.setPen(QPen(S.c("hairline"), 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(x0 + 9, y0 + 46, bw - 18, body.height() - 54), 6, 6)
        p.drawLine(QPointF(x0 + bw * 0.22, y0 + 36), QPointF(x0 + bw * 0.78, y0 + 36))
        # a small status dot at each sensor (the only colour on the figure)
        for side in self.SIDES:
            c = sensors[side]
            mark(p, QRect(int(c.x()) - 6, int(c.y()) - 6, 12, 12), tok(tof_status(self.metres.get(side))), ring="card")
        # the three distances, by their sensors
        vals = self.values()
        blocks = {"ahead": QRectF(w / 2 - 130, 40, 260, 30),
                  "left": QRectF(24, sensors["left"].y() - 6, sensors["left"].x() - radius["left"] - 40, 30),
                  "right": QRectF(sensors["right"].x() + radius["right"] + 16, sensors["right"].y() - 6,
                                  w - 24 - (sensors["right"].x() + radius["right"] + 16), 30)}
        align = {"ahead": AL.AlignHCenter, "left": AL.AlignRight, "right": AL.AlignLeft}
        for side in self.SIDES:
            value, word = vals[side]
            b = blocks[side]
            p.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True)); p.setPen(S.c("ink_2"))
            p.drawText(QRectF(b.left(), b.top() - 20, b.width(), 18), align[side] | AL.AlignVCenter,
                       f"{side.upper()} · {word.upper()}")
            p.setFont(S.mono(S.SECONDARY, QFont.Weight.Medium) if value[:1].isdigit() else S.font(S.SECONDARY, QFont.Weight.Medium))
            p.setPen(S.c("ink_3" if value.startswith("--") else "ink"))
            p.drawText(b, align[side] | AL.AlignVCenter, value)
        p.end()


class FrameSlab(QWidget):
    """The middle plane: the camera frame as a raised charcoal slab (its shadow is painted by the view). It shows
    the newest camera image, cropped to fill, or the camera's status when there is none. The signal audit treats it
    like the map (a photo, not ink and paper)."""
    RADIUS = 8

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.setObjectName("sw7CameraSlab")
        self.image = None

    def set_image(self, pixmap):
        if pixmap is None or pixmap.isNull() or self.width() < 4:
            return
        size = self.size()
        scaled = pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        x, y = (scaled.width() - size.width()) // 2, (scaled.height() - size.height()) // 2
        self.image = scaled.copy(QRect(x, y, size.width(), size.height()))
        self.update()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.image is not None:
            self.set_image(self.view.camera._pixmap)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        r = QRectF(self.rect())
        clip = QPainterPath(); clip.addRoundedRect(r, self.RADIUS, self.RADIUS)
        p.setClipPath(clip)
        p.fillRect(r, S.c("charcoal"))
        if self.image is not None:
            p.drawPixmap(0, 0, self.image)
        else:
            AL = Qt.AlignmentFlag
            p.setPen(S.c("on_charcoal_2")); p.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True))
            p.drawText(QRectF(0, r.center().y() - 26, r.width(), 20), AL.AlignCenter, "NO CAMERA IMAGE")
            p.setPen(S.c("on_charcoal")); p.setFont(S.font(S.BODY))
            p.drawText(QRectF(0, r.center().y() - 2, r.width(), 24), AL.AlignCenter,
                       self.view.camera.status_label.text() or "Waiting for the camera")
        p.end()


class SurroundingsView(QWidget):
    """The merged page, laid over SensorsPage (which keeps its id, its data methods and its hidden widgets)."""
    M = 24
    COL_W = 488
    FRAME_R, CARD_R = 8, 8
    OVERLAP = 16

    def __init__(self, page, camera, main):
        super().__init__(page)
        self.setObjectName("sw7Surroundings")
        self.page, self.camera, self.main = page, camera, main
        self.telemetry, self.alerts, self.rows, self.link, self.replay = None, [], [], "offline", False
        self.slab = FrameSlab(self)
        # the camera page moves inside the frame; it streams while this page is on screen, as before
        plane = getattr(camera, "_sw7_plane", None)       # the core gave the Camera page its own back plane
        if plane is not None:
            camera.removeEventFilter(plane)
        camera.setProperty("sw7_word", "")
        camera.setParent(self)
        camera.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        for w in camera.findChildren(QWidget):
            if isinstance(w, QLabel) and w.text() == getattr(camera, "title", ""):
                w.hide()
        side = camera.metrics_label.parentWidget()
        if side is not None and side is not camera:
            side.hide()                              # its alerts list: merged into the one list here
        camera.video.hide(); camera.video.setFixedSize(2, 2)   # the frame is painted here, cropped to the slab
        chip = camera.status_label
        chip.setParent(self)
        chip.sw7_paper = True
        chip.setText(chip.text())
        S.elevate(chip, 1)
        self.chip = chip
        camera.show()

        def label(text="", px=S.BODY, weight=QFont.Weight.Normal, dim=False, caps=False):
            lab = QLabel(text, self)
            lab.setFont(S.font(px, weight, caps=caps))
            lab.setObjectName("sw7Dim" if dim else "sw7Ink")
            lab.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            return lab
        self.title = label(TITLE, S.SECONDARY, QFont.Weight.Bold)
        self.link_chip = label()
        self.near = label("NEAREST", S.LABEL, QFont.Weight.Bold, dim=True, caps=True)
        self.hero = label("--", S.HERO, QFont.Weight.Bold)
        self.unit = label("m", S.SECONDARY, QFont.Weight.Bold, dim=True)
        self.sub_status = "inactive"
        self.sub = label("", S.BODY, dim=True)
        self.hz_title = label("HAZARDS · CAMERA AND TOF · NEAREST FIRST", S.LABEL, QFont.Weight.Bold, dim=True, caps=True)
        self.rows_w = [HazardRow(self) for _ in range(MAX_ROWS)]
        self.empty = label("", S.BODY, dim=True)
        self.more = label("", S.LABEL, QFont.Weight.Bold, dim=True, caps=True)
        self.ride_title = label("RIDE", S.LABEL, QFont.Weight.Bold, dim=True, caps=True)
        self.ride = label("--", S.BODY, dim=True)
        self.figure = TukFigure(self)
        self.figure.raise_(); chip.raise_()
        from ..theme import THEME
        THEME.changed.connect(self.restyle)
        self.restyle()
        self.refresh()

    # geometry ------------------------------------------------------------------------------------------------------
    def rects(self):
        W, H, M = self.width(), self.height(), self.M
        col_x = W - M - self.COL_W
        fw = col_x - 2 * M
        frame = QRectF(M, M, fw, round(fw * 9 / 16))
        bottom = H - 24                                         # the flat nav bar sits below the page
        tuk = QRectF(M + self.OVERLAP, frame.bottom() - self.OVERLAP, fw - 2 * self.OVERLAP,
                     bottom - (frame.bottom() - self.OVERLAP))
        hz = QRectF(col_x, 280, self.COL_W, bottom - 280)
        return frame, tuk, hz, col_x

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._place()

    def _place(self):
        frame, tuk, hz, col_x = self.rects()
        self.slab.setGeometry(frame.toRect())
        self.camera.setGeometry(0, 0, 4, 4)          # streaming follows its visibility; it paints nothing
        self.chip.move(int(frame.left()) + 16, int(frame.top()) + 16)
        l, t, r, b = TukFigure.PAD
        self.figure.setGeometry(tuk.toRect().adjusted(-l, -t, r, b))
        self.title.setGeometry(col_x, self.M - 4, 300, 32)
        self.link_chip.move(self.width() - self.M - self.link_chip.width(), self.M)
        self.near.setGeometry(col_x, 62, 300, 18)
        fm = QFontMetrics(self.hero.font())
        self.hero.setGeometry(col_x - 6, 66, self.COL_W, fm.height())
        tw = fm.horizontalAdvance(self.hero.text())
        ufm = QFontMetrics(self.unit.font())
        base = 66 + fm.ascent()
        self.unit.setGeometry(col_x - 6 + tw + 10, int(base - ufm.ascent()), 80, ufm.height())
        self.sub_dot = QRect(col_x, int(base + 24), 10, 10)
        self.sub.setGeometry(col_x + 18, int(base + 14), self.COL_W - 18, 30)
        x, y, w = int(hz.left()) + 24, int(hz.top()), int(hz.width()) - 48
        self.hz_title.setGeometry(x, y + 20, w, 18)
        for i, r in enumerate(self.rows_w):
            r.setGeometry(x, y + 48 + i * HazardRow.H, w, HazardRow.H)
        self.empty.setGeometry(x, y + 52, w, 44)
        shown = sum(1 for r in self.rows_w if not r.isHidden())
        self.more.setGeometry(x + 18, y + 48 + shown * HazardRow.H + 6, w - 18, 18)
        self.ride_title.setGeometry(x, int(hz.bottom()) - 40, 52, 24)
        self.ride.setGeometry(x + 56, int(hz.bottom()) - 43, w - 56, 30)

    # paint ---------------------------------------------------------------------------------------------------------
    def paintEvent(self, _e):
        frame, tuk, hz, _x = self.rects()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        # middle plane: the camera slab's shadow (the slab paints itself); top plane: the hazards card (the tuk-tuk
        # card paints itself, over the slab's edge)
        S.paint_shadow(p, frame, self.FRAME_R, 1)
        if S.BACK_WORDS_SHOWN:              # three planes: the hazards list sits on the paper under a hairline
            p.fillRect(QRectF(hz.left(), hz.top(), hz.width(), 1), S.c("hairline"))
        else:
            S.paint_card(p, hz, self.CARD_R, 1)
        if getattr(self, "sub_dot", None) is not None:
            mark(p, self.sub_dot, tok(self.sub_status))
        # the Ride row at the foot of the hazards card, under a hairline
        p.setPen(QPen(S.c("hairline"), 1))
        y = hz.bottom() - 56.5
        p.drawLine(QPointF(hz.left() + 24, y), QPointF(hz.right() - 24, y))
        p.end()

    def set_frame(self, pixmap):
        self.slab.set_image(pixmap)

    # data ----------------------------------------------------------------------------------------------------------
    def set_telemetry(self, telemetry):
        from .sensors_page import tof_metres
        from ..widgets.ride_quality_card import format_telemetry, replay_of
        self.telemetry = telemetry
        self.link, ride = format_telemetry(telemetry)
        self.replay = replay_of(telemetry)[0]
        self.figure.set_metres(tof_metres(telemetry))
        vib, dis = ride.get("vib", ("--", None))[0], ride.get("vib_dis", ("--", None))[0]
        self.ride.setText(f"Vibration {vib} · IMU disagreement {dis}")
        self.refresh()

    def set_camera_alerts(self, alerts):
        self.alerts = list(alerts or [])
        self.refresh()

    def refresh(self):
        self.rows = combined_hazards(self.telemetry, self.alerts)
        text, key = ("Replay", "warn") if self.replay and self.link != "offline" else LINK_CHIP.get(self.link, LINK_CHIP["offline"])
        chip_style(self.link_chip, text, key)
        for i, w in enumerate(self.rows_w):
            if i < len(self.rows) and (i < MAX_ROWS - 1 or len(self.rows) <= MAX_ROWS):
                main, detail, status = row_texts(self.rows[i])
                w.set_row(main, detail, status, i == 0)
                w.show()
            else:
                w.hide()
        extra = len(self.rows) - (MAX_ROWS - 1) if len(self.rows) > MAX_ROWS else 0
        self.more.setText(f"+{extra} more, farther away" if extra else "")
        no_data = self.link == "offline" and not self.alerts
        self.empty.setText("" if self.rows else ("No sensor data" if no_data else "No hazards"))
        if self.rows:
            r = self.rows[0]
            main, _detail, status = row_texts(r)
            if r["dist"] is not None:
                d = r["dist"]
                hero = f"{d:.2f}" if d < 1.2 else f"{d:.1f}"
            else:
                lim = BAND_LIMIT_M.get(r["band"])
                hero = f"<{lim:.0f}" if lim else "--"
            unit = "m" if hero != "--" else ""
            src = SOURCE_WORD.get(r["source"], r["source"])
            sub = f"{r['cls'].capitalize()} {r['where']} · {src}"
        else:
            hero, unit, status = ("--", "", "inactive") if no_data else ("Clear", "", "normal")
            sub = "No sensor data" if no_data else "Nothing detected around the tuk-tuk"
        self.hero.setText(hero); self.unit.setText(unit); self.sub.setText(sub)
        self.sub_status = status
        self._place()

    def restyle(self):
        self.setStyleSheet(f"QLabel#sw7Ink {{ background: transparent; color: {S.hx('ink')}; }}"
                           f" QLabel#sw7Dim {{ background: transparent; color: {S.hx('ink_2')}; }}")
        self.chip.setText(self.chip.text())
        self.refresh()
        self.update()


def _camera_chip(chip, *_a, **_k):
    """The camera status chip (front_camera_page.StatusChip) on Surroundings: an outline chip with a status dot."""
    if not getattr(chip, "sw7_paper", False):
        return
    status = chip._status
    shown = f"{status} · {chip._fps:.1f} fps" if status == "Live" and chip._fps is not None else status
    key = {"Live": "ok", "Camera image stale": "warn"}.get(status, "ink_3")
    chip_style(chip, f"Camera {shown}" if status == "Live" else shown, key)
    view = chip.parentWidget()
    if isinstance(view, SurroundingsView) and view.slab.image is None:
        view.slab.update()


def _camera_frame(camera, *_a, **_k):
    view = camera.parentWidget()
    if isinstance(view, SurroundingsView):
        view.set_frame(camera._pixmap)


def _sensors_telemetry(page, telemetry, *_a, **_k):
    view = getattr(page, "sw7_view", None)
    if view is not None:
        view.set_telemetry(telemetry)
        _sensors_battery(page)


def _sensors_battery(page):
    """The page's battery row (hidden with the Vehicle card) follows the dashboard's state, like every other page:
    simulated during a simulated drive, live otherwise. It used to read the raw BMS telemetry."""
    lab = getattr(page, "values", {}).get("soc")
    if lab is None or not hasattr(page, "_sw7_soc"):
        return
    soc = page._sw7_soc
    lab.setText("--" if soc is None else f"{soc:.0f} %")


def _merge_surroundings(main):
    cam, sens = getattr(main, "front_camera", None), getattr(main, "sensors", None)
    if cam is None or sens is None:
        return
    stack = main.stack
    idx = stack.indexOf(cam)
    if idx >= 0:                       # keep the stack indexes in step with page_ids: an empty slot for "camera"
        slot = QWidget(); slot.setObjectName("sw7CameraSlot")
        stack.insertWidget(idx, slot)
        stack.removeWidget(cam)
    main.page_by_id["camera"] = sens
    main.page_by_id["surroundings"] = sens
    if "camera" in main.normal_ids:
        main.normal_ids.remove("camera")
    btn = main.nav.buttons.get("camera")
    if btn is not None:
        btn.hide()
    sb = main.nav.buttons.get(SURROUNDINGS)
    if sb is not None:
        sb.setToolTip(TITLE)
        if getattr(sb, "sw7_label", None) is not None:
            sb.sw7_label.setText(TITLE)
    # the page: the old scroll area (Vehicle, Position, Ride and link cards) goes, the merged view takes its place
    if hasattr(sens, "scroll"):
        sens.scroll.hide()
    view = SurroundingsView(sens, cam, main)
    sens.layout().addWidget(view)
    sens.sw7_view = view
    main.sw7_surroundings = view
    cam.alerts_changed.connect(view.set_camera_alerts)
    view.set_camera_alerts(cam._last_alerts)
    view.set_telemetry(None)

    def on_state(state):
        sens._sw7_soc = getattr(state, "soc_pct", None)
        _sensors_battery(sens)
    main.state_updated.connect(on_state)
    on_state(main.current_state)


# ==== Diagnostics ===================================================================================================
CONTROLS = ("Throttle", "Brake", "Signed power")
HEALTH = ("Motor temp", "Ambient")
POSITION = ("GPS", "Altitude", "Incline")
TO_DETAILS = ("Speed", "Gear", "Battery SOC", "Battery temp", "Range", "Charging", "Odometer")
AMBIENT = "Ambient (vehicle)"
OUTSIDE = "Outside (weather)"


def _card_rows(card):
    return list(zip(list(card.values.keys()), card.captions))


def _add_row(card, key, caption, widget=None):
    grid = card.layout().itemAt(1).layout()
    r = grid.rowCount()
    cap = QLabel(caption); cap.setObjectName("sw7DiagCaption"); cap.setFont(S.font(S.BODY))
    val = widget if widget is not None else QLabel("--")
    if widget is None:
        val.setObjectName("sw7DiagValue"); val.setFont(S.font(S.BODY, QFont.Weight.Bold))
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(cap, r, 0); grid.addWidget(val, r, 1)
    else:
        grid.addWidget(cap, r, 0, Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(val, r, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    card.values[key] = val; card.captions.append(cap)
    return val


def _diagnostics(main):
    page = getattr(main, "diagnostics", None)
    lay = getattr(page, "_sw7_layout", None)
    if not lay:
        return
    from .sw7_layout_pages import UNKNOWN
    from .sensors_page import format_readings
    from ..widgets.ride_quality_card import format_telemetry
    drive, energy, position, link = lay["cards"]
    drive.title.setText("CONTROLS")
    energy.title.setText("HEALTH")
    keep = {drive: CONTROLS, energy: HEALTH, position: POSITION}
    for card, names in keep.items():
        for key, cap in _card_rows(card):
            if key not in names:
                cap.hide(); card.values[key].hide()
            elif key == "Ambient":
                cap.setText(AMBIENT)
    # Health: the weather's outside temperature as a glance that opens the weather card, then the BMS and motor
    glance = QPushButton("--°")
    glance.setObjectName("sw7WeatherGlance")
    glance.setFixedSize(132, 64)
    glance.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    _add_row(energy, "outside", OUTSIDE, glance)
    tel_rows = {}
    for card, rows in ((energy, (("bms_age", "BMS reading"), ("rpm", "Motor rpm"))),
                       (position, (("fix", "GPS fix"), ("crs", "Heading"), ("spd_raw", "GNSS speed (raw)"))),
                       (link, (("fw", "Firmware"),))):
        for key, caption in rows:
            tel_rows[key] = _add_row(card, key, caption)
    # the details list: what left the cards, under the raw source and the Pi 4 address
    raw = lay["raw"]
    rg = raw["Source"].parentWidget().layout()
    n0 = len(raw)
    extra = {}
    for i, name in enumerate(TO_DETAILS, start=n0):
        cap = QLabel(name.upper()); cap.setObjectName("supportCaption"); cap.setFont(S.font(S.LABEL, QFont.Weight.Bold))
        val = QLabel("--"); val.setObjectName("supportValue"); val.setFont(S.font(S.LABEL, QFont.Weight.DemiBold))
        val.setAlignment(Qt.AlignmentFlag.AlignRight); val.setWordWrap(True)
        rg.addWidget(cap, i // 2, (i % 2) * 2); rg.addWidget(val, i // 2, (i % 2) * 2 + 1)
        extra[name] = val
    lay["details_values"] = extra
    lay["glance"] = glance
    lay["telemetry_rows"] = tel_rows

    def open_weather():
        card = getattr(main, "sw7_weather_card", None)
        if card is not None:
            card.open_card()
    glance.clicked.connect(open_weather)

    def weather(rep=None):
        rep = rep if rep is not None else getattr(getattr(main, "sw7_weather", None), "report", None)
        glance.setText(f"{rep.temp_c:.0f}°  ›" if rep is not None and rep.temp_c is not None else "--°  ›")
    svc = getattr(main, "sw7_weather", None)
    if svc is not None:
        svc.updated.connect(weather)
    weather()

    visible = {drive: CONTROLS, energy: HEALTH, position: POSITION}
    lay_update = page.update_state

    def value_fonts():
        """Figures in Plex Mono, words ("Unavailable", "Yes", "Live") in Plex Sans; unavailable values in ink_3, so an
        unavailable value never reads like a zero."""
        for card in lay["cards"]:
            for lab in card.values.values():
                if not isinstance(lab, QLabel):
                    continue
                S.value_font(lab, S.BODY, QFont.Weight.Medium)
                if lab.text() in UNKNOWN:
                    lab.setStyleSheet(f"background: transparent; color: {S.hx('ink_3')};")
                    lab.setProperty("sw7_unknown", True)
                elif lab.property("sw7_unknown"):
                    lab.setStyleSheet(f"background: transparent; color: {S.hx('ink')};")
                    lab.setProperty("sw7_unknown", False)

    def update_state(s):
        lay_update(s)
        for name, lab in extra.items():
            lab.setText(page._values[name].text())
        for card, names in visible.items():
            known = any(card.values[n].text() not in UNKNOWN for n in names)
            card.set_dot("normal" if known else "inactive")
        value_fonts()
    page.update_state = update_state
    lay["value_fonts"] = value_fonts

    last = {"t": None}

    def on_telemetry(telemetry):
        last["t"] = telemetry
        readings = format_readings(telemetry)
        ride = format_telemetry(telemetry)[1]
        for key, lab in tel_rows.items():
            text, status = readings.get(key) or ride.get(key) or ("--", None)
            lab.setText(text)
            col = S.hx("ink_3") if text in UNKNOWN else S.hx(tok(status)) if status else S.hx("ink")
            lab.setStyleSheet(f"background: transparent; color: {col};")
        if "value_fonts" in lay:
            lay["value_fonts"]()
    tel = getattr(main, "telemetry", None)
    if tel is not None:
        tel.telemetry_updated.connect(on_telemetry)
    on_telemetry(None)

    # the look: four cards on cached shadows, ink and paper, one signal toggle and one signal glance
    cards = list(lay["cards"])
    host = cards[0].parentWidget()
    if S.BACK_WORDS_SHOWN:
        # three planes: the four groups sit on the paper under a hairline (no cards), SYSTEM shows between them
        for c in cards:
            c.setProperty("sw7_open", True)
        page._sw7_bed = None
    else:
        page._sw7_bed = _Bed(host, cards, 8, 1)
    page._sw7_bed_details = _Bed(host, [lay["details"]], 8, 1, fill="card")   # the details frame paints no fill
    root = host.layout()
    root.setContentsMargins(24, 16, 24, 40)
    # the details toggle moves up beside the title, so the four cards fit above the nav pill (with the SIMULATED
    # strip too); opening it scrolls to the details under the cards, closing it scrolls back
    toggle, details = lay["toggle"], lay["details"]
    title = next((root.itemAt(i).widget() for i in range(root.count())
                  if isinstance(root.itemAt(i).widget(), QLabel)), None)
    if title is not None:
        from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QSizePolicy
        root.removeWidget(title); root.removeWidget(toggle)
        head = QHBoxLayout(); head.setSpacing(16)
        head.addWidget(title, 0, Qt.AlignmentFlag.AlignVCenter); head.addStretch(1); head.addWidget(toggle)
        root.insertLayout(0, head)
        toggle.setText("Show advice and details")
        toggle.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        toggle.setFixedSize(300, 64)
        area = page.findChild(QScrollArea)

        def follow(on):
            toggle.setText("Hide advice and details" if on else "Show advice and details")
            if area is not None:
                bar = area.verticalScrollBar()
                QTimer.singleShot(0, lambda: bar.setValue(max(0, details.y() - 16) if on else 0))
        toggle.toggled.connect(follow)
    for c in lay["cards"]:
        c.title.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True))
        c.layout().setContentsMargins(24, 18, 24, 18)
    for lab in host.findChildren(QLabel):
        if lab.text() == "System Diagnostics":
            lab.setText("Diagnostics"); lab.setFont(S.font(S.SECONDARY, QFont.Weight.Bold))
        elif lab.objectName() == "sw7DiagCaption":
            lab.setFont(S.font(S.BODY))
        elif lab.objectName() == "sw7DiagValue":
            lab.setFont(S.font(S.BODY, QFont.Weight.Bold))
    lay["toggle"].setFont(S.font(S.BODY, QFont.Weight.Bold))
    snap_fonts(host)
    from ..theme import THEME

    def theme(*_):
        page.setStyleSheet(page.styleSheet() + f"""
        QLabel#sw7DiagHeader {{ color: {S.hx('ink_2')}; }}
        QLabel#sw7DiagCaption {{ color: {S.hx('ink_2')}; }}
        QLabel#supportCaption {{ color: {S.hx('ink_2')}; }}
        QLabel#supportTitle {{ color: {S.hx('ink_2')}; }}
        QFrame#sw7DetailsCard {{ background: {S.hx('card')}; border: 1px solid {S.hx('hairline')}; border-radius: {S.RADIUS_MAX}px; }}
        {S.button_qss('outline', 8, S.BODY, 'QPushButton#sw7DetailsToggle')}
        {S.button_qss('outline', 8, S.BODY, 'QPushButton#sw7WeatherGlance')}
        """)
        on_telemetry(last["t"])
    THEME.changed.connect(theme)
    theme()


# ==== Charging ======================================================================================================
def _install_charging(mod):
    _wrap(mod.ChargingPage, "paintEvent", replace=lambda orig, page, e: None)        # the back plane shows through
    _wrap(mod._GradientCard, "paintEvent", replace=lambda orig, card, e: None)       # painted by the page's _Bed
    _wrap(mod._TuktukTelemetryVisual, "paintEvent", replace=_ring_paint)
    _wrap(mod._TuktukTelemetryVisual, "set_telemetry", after=lambda vis, *a, **k: vis.update())
    _wrap(mod._LivePowerGraph, "paintEvent", replace=_graph_paint)
    _wrap(mod._ThermalBar, "paintEvent", replace=_thermal_paint)
    _wrap(mod.ChargingPage, "update_state", after=_charging_update)


def _charging(main):
    page = getattr(main, "charging", None)
    if page is None or not hasattr(page, "card_eta"):
        return
    vis = page.tuk
    # The team's battery animation (bubbles in the fluid, the spinning arc) stays, restyled in ink and paper
    # (BatteryAnimation): it runs at 30 fps only while Charging is on screen and the state of charge is known.
    vis.sw7_bms, vis.sw7_soh, vis.sw7_sim, vis.sw7_no_data = None, None, False, False
    BatteryAnimation(vis)
    container = page.card_eta.parentWidget()
    right = container.layout()
    right.setContentsMargins(16, 8, 16, 32)
    grid = next(right.itemAt(i).layout() for i in range(right.count())
                if isinstance(right.itemAt(i).layout(), QGridLayout))
    # one time to full and one power figure (both on the ring): those two tiles go; Range (its home) comes in
    for card in (page.card_eta, page.card_rate, page.card_range, page.card_energy):
        grid.removeWidget(card)
    page.card_eta.hide(); page.card_rate.hide()
    page.sw7_card_range_now = page._create_metric_card("Range", "--", "normal")
    for col, card in enumerate((page.sw7_card_range_now, page.card_range, page.card_energy)):
        grid.addWidget(card, 0, col)
        grid.setColumnStretch(col, 1)
    tiles = (page.sw7_card_range_now, page.card_range, page.card_energy)
    for card in tiles:
        card.setMinimumHeight(88)
        card.layout().setContentsMargins(20, 12, 20, 12)
        card.value_label.setFont(S.font(S.SECONDARY, QFont.Weight.Bold))
    page.sw7_card_range_now.findChild(QLabel).setObjectName("dim")
    from . import charging_page as cp
    cards = [w for w in container.findChildren(cp._GradientCard) if w.parentWidget() is container]
    if S.BACK_WORDS_SHOWN:
        # three planes: no cards; each group sits on the paper under a hairline, so CHARGE and the vehicle show
        # between the groups, and the column is compact enough to leave the lower right to the vehicle
        page._sw7_bed = _Bed(container, cards, 8, 1, lines=True)
        for card in cards:
            card.setStyleSheet("QFrame { background: transparent; border: none; }")
            if card.layout() is not None:
                card.layout().setContentsMargins(0, 10, 0, 4)
        for card in tiles:
            card.setMinimumHeight(64)
            card.layout().setContentsMargins(0, 10, 12, 4)
        page.power_graph.setMinimumHeight(64)
        right.setContentsMargins(16, 8, 24, 8)
        right.setSpacing(0)
        for i in range(right.count()):
            item = right.itemAt(i)
            if item.spacerItem() is not None and item.spacerItem().sizeHint().height() in (12, 16):
                item.spacerItem().changeSize(0, 6)
        right.invalidate()
    else:
        page._sw7_bed = _Bed(container, cards, 8, 1, fill="card")
        for card in cards:
            if card.layout() is not None:
                m = card.layout().contentsMargins()
                card.layout().setContentsMargins(max(20, m.left()), max(12, m.top()), max(20, m.right()), max(12, m.bottom()))
    for lab in page.findChildren(QLabel):
        if lab in [c.value_label for c in tiles]:
            continue
        if lab is getattr(page, "sw7_title", None):
            lab.setFont(S.font(S.SECONDARY, QFont.Weight.Bold))
        elif lab.text() in ("Power input (kW)", "Pack temperature", "Range added", "Energy delivered", "Range"):
            lab.setFont(S.font(S.LABEL, QFont.Weight.Bold))
    snap_fonts(page, keep=[c.value_label for c in tiles])
    page.thermal_bar.setFixedHeight(10)

    def on_telemetry(telemetry):
        from ..widgets.ride_quality_card import _num, format_telemetry
        link, _ride = format_telemetry(telemetry)
        esp = telemetry.get("esp32") if isinstance(telemetry, dict) and isinstance(telemetry.get("esp32"), dict) else {}
        v, i = _num(esp.get("v")), _num(esp.get("i"))
        vis.sw7_bms = (v, i) if link == "live" and (v is not None or i is not None) else None
        vis.update()
    tel = getattr(main, "telemetry", None)
    if tel is not None:
        tel.telemetry_updated.connect(on_telemetry)


def _charging_update(page, s, *_a, **_k):
    vis = page.tuk
    vis.sw7_soh = getattr(s, "battery_soh_pct", None)
    source = str(getattr(s, "data_source", ""))
    vis.sw7_sim = source == "sw7_simulated_drive"
    no_data = source == "no_data"
    vis.sw7_no_data = no_data
    card = getattr(page, "sw7_card_range_now", None)
    if card is not None:
        from ..asis.config import VEHICLE_SPEC
        rng = getattr(s, "range_km", None)
        card.value_label.setText("--" if rng is None else f"{min(VEHICLE_SPEC.rated_max_range_km, float(rng)):.0f} km")
    # Five states, each in words: charging, not charging, zero (a real 0, shown as 0), unknown and unavailable ("--")
    if no_data:
        for c in (page.card_range, page.card_energy):          # session figures with no live data: unavailable
            c.value_label.setText("--")
        page.status.setText("Charging state unknown · no live data")
        page.status.setStyleSheet(f"color:{S.hx('ink_2')};background:transparent;")
    elif bool(getattr(s, "charging", False)):
        page.status.setStyleSheet(f"color:{S.hx('ink')};background:transparent;")
    src = page.findChild(QLabel, "sw7ChargeSource")        # the layout pass coloured it once, in the day palette
    if src is not None:
        src.setStyleSheet(f"color:{S.hx('ink')};background:transparent;")
    for c in tiles_of(page):
        S.value_font(c.value_label, S.SECONDARY, QFont.Weight.Medium)
        c.value_label.setStyleSheet(f"color:{S.hx('ink_3' if c.value_label.text().startswith('--') else 'ink')};"
                                    "background:transparent;")
    anim = getattr(vis, "sw7_anim", None)
    if anim is not None:
        anim.sync()
    vis.update()


def tiles_of(page):
    return [c for c in (getattr(page, "sw7_card_range_now", None), page.card_range, page.card_energy) if c is not None]


def ring_values(vis):
    """The figures the graphic shows: {soc, energy, power, voltage, current, state, ttf, soh} (also kept for the tests).
    Anything without a reading is "--"; cell health is only ever the reported value (never a made-up 98 %)."""
    from ..charging_model import format_duration
    from ..widgets.sw7_layout_frame import ring_texts
    unknown = getattr(vis, "unknown", {}) or {}
    soc_t, energy_t = ring_texts(vis)
    no_data = bool(getattr(vis, "sw7_no_data", False))
    charging = vis.current_kw > 0 and not no_data
    power = "--" if unknown.get("kw") or no_data else f"{vis.current_kw:.1f} kW"
    if charging:
        volt = "--" if unknown.get("v") else f"{vis.current_v:.1f} V"
        amp = "--" if unknown.get("a") else f"{vis.current_a:.1f} A"
    else:                                   # not charging: the pack's own voltage and current from the BMS
        bms = None if getattr(vis, "sw7_sim", False) else getattr(vis, "sw7_bms", None)   # (live telemetry)
        volt = f"{bms[0]:.1f} V" if bms and bms[0] is not None else "--"
        amp = f"{bms[1]:.1f} A" if bms and bms[1] is not None else "--"
    soh = None if no_data else getattr(vis, "sw7_soh", None)
    state = "--" if no_data else "Charging" if charging else "Not charging"
    return {"soc": soc_t.rstrip("%"), "energy": energy_t, "power": power, "voltage": volt, "current": amp,
            "state": state, "ttf": format_duration(vis.current_eta_s) if charging and vis.current_eta_s else "--",
            "soh": "--" if soh is None else f"{float(soh):.0f} %"}


READINGS = (("Power input", "power"), ("Voltage", "voltage"), ("Current", "current"),
            ("Charging", "state"), ("Time to full", "ttf"), ("Cell health", "soh"))


def _ring_geometry(vis):
    """(cx, cy, R, rr, ri): the graphic's centre, the disc radius, the ring arc radius and the hull's half height."""
    w, h = vis.width(), vis.height()
    R = max(150.0, min(w / 2 - 8, h / 2 - 12))
    cx, cy = w / 2, h / 2
    rr = R - 14                       # the ring arc (the team's spinning state-of-charge arc)
    ri = R * 0.43                     # the hull's half height
    return cx, cy, R, rr, ri


def hull_paths(vis):
    """The team's tuk-tuk seen from above (charging_page._TuktukTelemetryVisual), scaled into the ring:
    (hull, details, centre, k). Design units: x within +-72, y from -157 to +95 round the team's centre."""
    cx, cy, R, _rr, ri = _ring_geometry(vis)
    k = 2 * ri / 252.0
    hc = QPointF(cx, cy + R * 0.20)                  # the hull's centre: below the percentage
    ox, oy = hc.x(), hc.y() + 31 * k                 # the team's (cx, cy): the hull spans oy-157k .. oy+95k

    def P(x, y):
        return QPointF(ox + x * k, oy + y * k)
    hull = QPainterPath(P(-68, 80))
    hull.quadTo(P(0, 95), P(68, 80)); hull.lineTo(P(70, 15)); hull.quadTo(P(72, -27), P(62, -55))
    hull.lineTo(P(46, -120)); hull.quadTo(P(32, -150), P(16, -153)); hull.quadTo(P(0, -157), P(-16, -153))
    hull.quadTo(P(-32, -150), P(-46, -120)); hull.lineTo(P(-62, -55)); hull.lineTo(P(-70, 15)); hull.closeSubpath()
    det = QPainterPath()
    det.moveTo(P(-44, -115)); det.quadTo(P(0, -123), P(44, -115))
    det.moveTo(P(-59, -51)); det.quadTo(P(0, -60), P(59, -51))
    det.addRoundedRect(QRectF(P(-18, -69), P(18, -55)), 2 * k, 2 * k)
    det.moveTo(P(-33, -40)); det.quadTo(P(0, -36), P(33, -40)); det.lineTo(P(40, -31))
    det.moveTo(P(-33, -40)); det.lineTo(P(-40, -31))
    det.addRoundedRect(QRectF(P(-46, -21), P(-5, 12)), 6 * k, 6 * k)
    det.addRoundedRect(QRectF(P(5, -21), P(46, 12)), 6 * k, 6 * k)
    det.addRoundedRect(QRectF(P(-60, 39), P(60, 71)), 4 * k, 4 * k)
    return hull, det, hc, k


def _reading_slots(vis):
    """Where the six readings sit round the ring: three on the left, three on the right (the team's columns)."""
    cx, cy, R, _rr, _ri = _ring_geometry(vis)
    _hull, _det, hc, k = hull_paths(vis)
    half = 74 * k                                    # the hull's half width
    colw = max(120.0, R * 0.92 - half - 20)
    ys = [hc.y() - R * 0.36, hc.y() - R * 0.06, hc.y() + R * 0.24]
    out = []
    for i, y in enumerate(ys):
        out.append(QRectF(cx - half - 20 - colw, y, colw, 50))
    for i, y in enumerate(ys):
        out.append(QRectF(cx + half + 20, y, colw, 50))
    return out


def _ring_back(vis, vals):
    """The static back layer: the disc (card, hairline, very light shadow) and the ring track."""
    from PySide6.QtGui import QPixmap
    cx, cy, R, rr, _ri = _ring_geometry(vis)
    dpr = vis.devicePixelRatioF()
    pix = QPixmap(int(vis.width() * dpr), int(vis.height() * dpr)); pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if not S.BACK_WORDS_SHOWN:
        S.paint_card(p, QRectF(cx - R, cy - R, 2 * R, 2 * R), R, 2)
    else:
        # three planes: no disc, as in the team's page; the ring and the outline stand on the paper and CHARGE reads
        # through them. The hull keeps a paper fill so the bubbles and the level stay clear.
        hull = hull_paths(vis)[0]
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(S.c("card")); p.drawPath(hull)
    pen = QPen(S.c("paper_deep"), 4); pen.setCapStyle(Qt.PenCapStyle.FlatCap)
    p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush); p.drawEllipse(QPointF(cx, cy), rr, rr)
    p.end()
    return pix


def _ring_front(vis, vals):
    """The static front layer: the hull outline and its details over the fluid, the percentage above it, the stored
    energy, and the six readings round the ring (labels 13 px Plex Sans, values 22 px Plex Mono, "--" in ink_3)."""
    from PySide6.QtGui import QPixmap
    cx, cy, R, _rr, _ri = _ring_geometry(vis)
    hull, det, hc, k = hull_paths(vis)
    dpr = vis.devicePixelRatioF()
    pix = QPixmap(int(vis.width() * dpr), int(vis.height() * dpr)); pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    AL = Qt.AlignmentFlag
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(S.c("ink_3"), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawPath(det)
    p.setPen(QPen(S.c("ink"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawPath(hull)
    known = vals["soc"] not in ("--", "")
    hero = S.font(S.HERO_MIN, QFont.Weight.DemiBold); fm = QFontMetrics(hero)
    pct = S.font(S.SECONDARY, QFont.Weight.Medium); pfm = QFontMetrics(pct)
    tw, pw = fm.horizontalAdvance(vals["soc"]), pfm.horizontalAdvance("%")
    top_hull = hc.y() - 126 * k
    base = top_hull - 42
    x = cx - (tw + 6 + pw) / 2 if known else cx - tw / 2
    p.setFont(hero); p.setPen(S.c("ink") if known else S.c("ink_3")); p.drawText(QPointF(x, base), vals["soc"])
    if known:
        p.setFont(pct); p.setPen(S.c("ink_2")); p.drawText(QPointF(x + tw + 6, base - fm.capHeight() + pfm.capHeight()), "%")
    p.setFont(S.font(S.LABEL, QFont.Weight.Medium)); p.setPen(S.c("ink_2"))
    p.drawText(QRectF(cx - 140, base - fm.capHeight() - 40, 280, 18), AL.AlignCenter,
               "Battery" if known else "Battery · no reading")
    p.setFont(S.mono(S.LABEL, QFont.Weight.Normal)); p.setPen(S.c("ink_2"))
    p.drawText(QRectF(cx - 150, base + 8, 300, 20), AL.AlignCenter, vals["energy"])
    slots = _reading_slots(vis)
    drawn = []
    for i, ((label, key), r) in enumerate(zip(READINGS, slots)):
        align = (AL.AlignRight if i < 3 else AL.AlignLeft) | AL.AlignVCenter
        p.setFont(S.font(S.LABEL, QFont.Weight.Medium)); p.setPen(S.c("ink_2"))
        p.drawText(QRectF(r.x(), r.y(), r.width(), 18), align, label)
        value = vals[key]
        f = S.mono(S.SECONDARY) if S.is_figure(value) else S.font(S.SECONDARY, QFont.Weight.Medium)
        p.setFont(f); p.setPen(S.c("ink_3") if value.startswith("--") else S.c("ink"))
        p.drawText(QRectF(r.x(), r.y() + 18, r.width(), 30), align,
                   QFontMetrics(f).elidedText(value, Qt.TextElideMode.ElideRight, int(r.width())))
        drawn.append(label)
    vis.sw7_readings = drawn
    vis.sw7_outline = hull
    p.end()
    return pix


class BatteryAnimation(QObject):
    """The team's battery animation (Charging page), restyled in paper and ink: bubbles rise through the fluid inside
    the tuk-tuk outline (filled to the state of charge) and the state-of-charge arc turns round the ring, as in the
    team's page (Planning/reference_team_charging_page.jpg). Fluid and bubbles are ok-green while charging or above
    30 %, ink below; the arc is ink (it is not tappable). Nothing moves, and no fluid is drawn, when the state of
    charge is unknown. It reuses the team's anim_timer at 30 fps, running only while the page is on screen. The disc
    and the text are two cached layers, so a frame paints two pixmaps, the fluid, about 24 circles and one arc."""
    BUBBLES = 24
    FPS_MS = 33

    def __init__(self, vis):
        super().__init__(vis)
        import random
        self.vis = vis
        self.rng = random.Random(7)               # the same bubble pattern on every start (and in the screenshots)
        self.angle = 0.0
        self.bubbles = [self._new(initial=True) for _ in range(self.BUBBLES)]
        self.cache = {}
        vis.sw7_anim = self
        vis.sw7_frames = 0
        vis.sw7_bubbles_shown = lambda: self.visible_bubbles() > 0
        t = vis.anim_timer
        t.stop()
        try:
            t.timeout.disconnect(vis._animate_step)
        except (RuntimeError, TypeError):
            pass
        t.setInterval(self.FPS_MS)
        t.timeout.connect(self.step)
        vis.installEventFilter(self)
        from ..theme import THEME
        THEME.changed.connect(self.invalidate)

    def _new(self, initial=False):
        r = self.rng
        return {"x": r.uniform(-0.62, 0.62), "y": r.uniform(-1.0, 1.0) if initial else 1.0 + r.uniform(0.02, 0.2),
                "r": r.uniform(2.0, 4.0), "v": r.uniform(0.006, 0.014), "ph": r.uniform(0, 6.28),
                "wv": r.uniform(0.04, 0.10), "a": r.uniform(0.35, 0.75)}

    # state ---------------------------------------------------------------------------------------------------------
    def soc(self):
        vals = getattr(self.vis, "_sw7_texts", None) or ring_values(self.vis)
        try:
            return max(0.0, min(100.0, float(vals["soc"])))
        except (TypeError, ValueError):
            return None

    def charging(self):
        return float(getattr(self.vis, "current_kw", 0.0) or 0.0) > 0.0

    def wanted(self):
        return self.vis.isVisible() and self.soc() is not None and not getattr(self.vis, "sw7_no_data", False)

    def sync(self):
        t = self.vis.anim_timer
        if self.wanted():
            if not t.isActive():
                t.start()
        elif t.isActive():
            t.stop()

    def visible_bubbles(self):
        soc = self.soc()
        if soc is None or getattr(self.vis, "sw7_no_data", False):
            return 0
        level = 1.0 - 2.0 * soc / 100.0
        return sum(1 for b in self.bubbles if b["y"] > level)

    def invalidate(self, *_):
        self.cache.clear()
        self.vis.update()

    def eventFilter(self, obj, e):
        if e.type() in (QEvent.Type.Show, QEvent.Type.Hide):
            QTimer.singleShot(0, self.sync)
        elif e.type() == QEvent.Type.Resize:
            self.cache.clear()
        return False

    def step(self):
        if not self.wanted():
            self.sync()
            return
        kw = max(0.0, min(22.0, float(getattr(self.vis, "current_kw", 0.0) or 0.0)))
        charging = kw > 0
        self.angle = (self.angle + (0.7 * 2 if charging else 0.35)) % 360     # the team's 0.7 deg per 16 ms frame
        level = 1.0 - 2.0 * (self.soc() or 0.0) / 100.0            # fluid surface, -1 (top) to 1 (bottom)
        speed = (1.0 + kw * 0.15) if charging else 0.45
        for i, b in enumerate(self.bubbles):
            b["y"] -= b["v"] * speed
            b["ph"] += b["wv"]
            if b["y"] < level + 0.08:
                b["a"] -= 0.05
            if b["y"] <= level or b["a"] <= 0:
                self.bubbles[i] = self._new()
        self.vis.sw7_frames = getattr(self.vis, "sw7_frames", 0) + 1
        self.vis.update()

    # paint ---------------------------------------------------------------------------------------------------------
    def layers(self, vals):
        key = (self.vis.width(), self.vis.height(), S.is_night(), tuple(sorted(vals.items())))
        hit = self.cache.get(key)
        if hit is None:
            self.cache.clear()
            hit = self.cache[key] = (_ring_back(self.vis, vals), _ring_front(self.vis, vals), hull_paths(self.vis))
        return hit

    def paint(self, p, vals):
        cx, cy, _R, rr, _ri = _ring_geometry(self.vis)
        back, front, (hull, _det, hc, k) = self.layers(vals)
        p.drawPixmap(0, 0, back)
        soc = self.soc()
        live = soc is not None and not getattr(self.vis, "sw7_no_data", False)
        charging = self.charging()
        tone = "ok" if (charging or (soc or 0) >= 30) else "ink"
        if live and soc > 0:
            # the fluid inside the outline, up to the state of charge, with a hairline surface, and the bubbles
            top_y, bot_y = hc.y() - 126 * k, hc.y() + 95 * k + 31 * k
            p.save(); p.setClipPath(hull)
            top = bot_y - (bot_y - top_y) * soc / 100.0
            tint = S.blend(S.hx("card"), S.hx(tone), 0.16 if not S.is_night() else 0.24)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(tint))
            p.drawRect(QRectF(cx - 80 * k, top, 160 * k, bot_y - top))
            p.setPen(QPen(S.c(tone), 1.2)); p.drawLine(QPointF(cx - 80 * k, top), QPointF(cx + 80 * k, top))
            col = QColor(S.hx(tone))
            p.setPen(Qt.PenStyle.NoPen)
            level = 1.0 - 2.0 * soc / 100.0
            half_h = (bot_y - top_y) / 2.0
            mid = (bot_y + top_y) / 2.0
            for b in self.bubbles:
                if b["y"] <= level:
                    continue
                col.setAlphaF(max(0.0, min(1.0, b["a"])) * (0.9 if charging else 0.55))
                p.setBrush(col)
                wob = math.sin(b["ph"]) * 2.5 if charging else 0.0
                p.drawEllipse(QPointF(cx + b["x"] * 70 * k + wob, mid + b["y"] * half_h), b["r"], b["r"])
            p.restore()
        if live:
            # the team's ring arc: its length is the state of charge, and it turns (ink: it is not tappable)
            pen = QPen(S.c("ink"), 4.0); pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(cx - rr, cy - rr, 2 * rr, 2 * rr), int((90 - self.angle) * 16), -int(soc / 100.0 * 360 * 16))
        p.drawPixmap(0, 0, front)


def _ring_paint(orig, vis, _e):
    p = QPainter(vis)
    p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    vals = ring_values(vis)
    if getattr(vis, "sw7_no_data", False):
        vals["soc"], vals["energy"] = "--", "-- of " + vals["energy"].split(" of ")[-1]
    vis._sw7_texts = vals
    anim = getattr(vis, "sw7_anim", None)
    if anim is not None:
        anim.paint(p, vals)
    else:
        p.drawPixmap(0, 0, _ring_back(vis, vals)); p.drawPixmap(0, 0, _ring_front(vis, vals))
    p.end()


def _graph_paint(orig, graph, _e):
    p = QPainter(graph)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    w, h = graph.width(), graph.height()
    hist = list(graph.history)
    if not hist or max(hist) <= 0.0:
        # no grid without data: the words sit in their own row, on the baseline hairline (never struck through)
        p.setPen(QPen(S.c("hairline"), 1))
        p.drawLine(0, h - 1, w, h - 1)
        p.setPen(S.c("ink_2")); p.setFont(S.font(S.BODY))
        p.drawText(QRectF(0, 0, w, h - 2), Qt.AlignmentFlag.AlignCenter, "No charging data")
        p.end()
        return
    p.setPen(QPen(S.c("hairline"), 1))
    for i in range(1, 4):
        p.drawLine(0, int(h * i / 4), w, int(h * i / 4))
    top = max(max(hist), 7.0)
    path = QPainterPath()
    for i, v in enumerate(hist):
        x = i / max(1, len(hist) - 1) * w
        y = h - (v / top * (h - 10)) - 3
        path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
    p.setPen(QPen(S.c("ink"), 2)); p.drawPath(path)
    p.end()


def _thermal_paint(orig, bar, _e):
    p = QPainter(bar)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    w, h = bar.width(), bar.height()
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(S.c("paper_deep"))
    p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
    t = bar._temp
    if t > 0:
        p.setBrush(S.c("critical" if t > 45 else "warn" if t > 35 else "ok"))
        p.drawRoundedRect(QRectF(0, 0, max(h, w * min(t, 60.0) / 60.0), h), h / 2, h / 2)
    p.end()
