"""SW-7 dual camera: a Front | Rear toggle on Surroundings, one camera and one ToF board per side.

Hardware (15 Oct 2026): the Raspberry Pi 5 at the front (behind the display, runs the dashboard) has its own camera,
hazard detector and ToF board; the Raspberry Pi 4 at the rear (near the battery) keeps its camera, detector, ToF board
and the ESP32 telemetry bridge.

  Front  camera  TUKZIE_FRONT_CAMERA_URL, default http://127.0.0.1:8080 (pi5-hazard-detector.service)
         ToF     TUKZIE_FRONT_TOF_URL, default http://127.0.0.1:8082, GET /telemetry (pi5-tof-bridge.service; the
                 same JSON as the Pi 4 bridge, "esp32" is null there)
  Rear   camera  TUKZIE_REAR_CAMERA_URL, default http://<Pi 4 host>:8080: the host of the bridge the live-data
                 provider uses (its resolver, sw7_endpoints.py, or the host of TUKZIE_TELEMETRY_URL)
         ToF     the Pi 4 bridge on :8081 through the dashboard's own LiveDataProvider (resolver, or
                 TUKZIE_TELEMETRY_URL); this module never points the resolver anywhere else

Installed as app/pages/sw7_dual_camera.py; dashboard_main.py calls install(DashboardMain) once at import time, after
sw7_style_pages (DUAL_CAMERA_PATCHES). It only acts on the paper style's merged Surroundings page; TUKZIE_SW7_DUAL_CAM=0
(or TUKZIE_SW7_STYLE=team) installs nothing, so the single-camera build is unchanged.

What it does
  - Surroundings: a Front | Rear segmented toggle (two 112 x 64 px targets, signal outline, the selected side filled)
    at the top right of the camera frame. Selecting a side switches together the live stream, the camera alerts, the
    three ToF distances round the vehicle and the fused hazards, all from that side's own sources. The frame carries
    the word FRONT or REAR, the ToF card says AROUND THE TUK-TUK · FRONT or · REAR, the link chip names the side.
  - Only the selected side's MJPEG stream is fetched and decoded (FrontCameraPage keeps doing that, it is only told
    which address to use). Both sides' /alerts and ToF /telemetry are polled (small JSON, every 500 ms) so the banner
    can warn about the side that is not shown.
  - A side that cannot be reached shows the usual offline state for that side only: "NO CAMERA IMAGE" with
    "Camera offline, retrying", "--" and "No reading" for the ToF, "No sensor data" and a "--" hero. Never a value
    from the other side, never a simulated value, never 0 for a missing reading.
  - Rear convention (like a car's reversing camera): the rear image is mirrored left to right, so what is on the
    driver's left behind the vehicle is on the left of the screen. The rear ToF board faces backwards, so its own
    left sensor sees the vehicle's right: left_mm and right_mm are swapped, and a fused hazard's bearing is negated,
    before anything is drawn. The figure keeps the vehicle nose up with the rear sensors at its tail, and the straight
    back reading is called "behind". If the rear bridge already reports the vehicle's left and right, set
    TUKZIE_REAR_TOF_SWAP=0 (then only the image is mirrored).
  - Gear R (the dashboard's own gear state: keyboard, controller or the team's gear selector) switches to Rear and
    shows Surroundings in place of the team's reverse page (which has no rear sensor); leaving R returns to the side
    chosen before and the team's code returns to Driving.
  - The last side the driver picked is kept in the dashboard's preferences file (user_prefs.json, global key
    "sw7_camera_side"); the automatic switch in R is not saved.
  - The obstacle banner (HazardBanner) shows alerts from both sides, labelled: approaching objects first ("CAR
    APPROACHING · REAR · 2.1 s", red under 2 s, amber under 4 s), then immediate obstacles ("OBSTACLE 0.4 M FRONT
    RIGHT"), then a side whose sensor link was lost. On Surroundings it shows only the side that is not on screen;
    tapping it opens Surroundings on that side.
  - Approaching fields ("side", "track_id", "approaching", "ttc_s", "closing_mps", fusion also "ttc_source") are used
    when present; without them everything works as before (no TTC, no approaching alerts).
  - Drive's Around tile shows the front ToF (it used to show the Pi 4 board, which is now at the rear). It stays
    front-only: in R the dashboard shows Surroundings (Rear), so the Drive page is not on screen then.

Tests: tests/test_dual_camera.py (screenshots in tests/style/dualcam/).
"""
from __future__ import annotations

import json
import os
import time

from PySide6.QtCore import QObject, QPointF, QRect, QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QPushButton

from ..widgets import sw7_style as S

ENV = "TUKZIE_SW7_DUAL_CAM"
FRONT, REAR = "front", "rear"
SIDES = (FRONT, REAR)
SIDE_WORD = {FRONT: "Front", REAR: "Rear"}
PREF_KEY = "sw7_camera_side"
POLL_MS = 500
REQUEST_TIMEOUT_MS = 2000
STALE_MS = 3000            # no update from a side's ToF for this long: treat it as unreachable
LINK_LOST_S = 5.0          # the banner reports a lost side once it has been gone this long
TTC_CRIT_S, TTC_WARN_S = 2.0, 4.0
LINK_TEXT = {"live": ("sensors live", "ok"), "stale": ("ToF no reading", "warn"), "offline": ("sensors offline", "ink_3")}

_installed = False
_active = None             # the DualCamera of the running dashboard


def enabled() -> bool:
    """TUKZIE_SW7_DUAL_CAM, default on; 0 restores the single-camera Surroundings exactly."""
    return os.environ.get(ENV, "1").strip() != "0"


def _env_url(name, default=None):
    return os.environ.get(name, "").strip().rstrip("/") or default


def front_camera_url():
    return _env_url("TUKZIE_FRONT_CAMERA_URL", "http://127.0.0.1:8080")


def front_tof_url():
    return _env_url("TUKZIE_FRONT_TOF_URL", "http://127.0.0.1:8082")


def rear_tof_swap() -> bool:
    return os.environ.get("TUKZIE_REAR_TOF_SWAP", "1").strip() != "0"


def _num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


# ---- data in the driver's frame ------------------------------------------------------------------------------------
def to_vehicle_frame(telemetry, side):
    """One /telemetry reply with left and right as the driver sees them. Front: unchanged. Rear: the board and the
    camera face backwards, so left_mm and right_mm swap and a hazard's sensor and bearing are mirrored (unless
    TUKZIE_REAR_TOF_SWAP=0). The input is never modified."""
    if side != REAR or not isinstance(telemetry, dict) or not rear_tof_swap():
        return telemetry
    out = dict(telemetry)
    tof = telemetry.get("tof")
    if isinstance(tof, dict):
        tof = dict(tof)
        tof["left_mm"], tof["right_mm"] = telemetry["tof"].get("right_mm"), telemetry["tof"].get("left_mm")
        out["tof"] = tof
    fusion = telemetry.get("fusion")
    if isinstance(fusion, dict) and isinstance(fusion.get("hazards"), list):
        swap = {"left": "right", "right": "left"}
        hz = []
        for h in fusion["hazards"]:
            if isinstance(h, dict):
                h = dict(h)
                if h.get("sensor") in swap:
                    h["sensor"] = swap[h["sensor"]]
                b = _num(h.get("bearing_deg"))
                if b is not None:
                    h["bearing_deg"] = -b
            hz.append(h)
        out["fusion"] = dict(fusion, hazards=hz)
    return out


def where_word(direction, side):
    """left, right, and ahead (front) or behind (rear)."""
    return "behind" if side == REAR and direction == "ahead" else direction


def side_link(telemetry):
    """"live" (fresh ToF), "stale" (the bridge answers, no fresh ToF) or "offline" (no reply)."""
    if not isinstance(telemetry, dict):
        return "offline"
    tof = telemetry.get("tof") if isinstance(telemetry.get("tof"), dict) else None
    if tof is None:
        return "stale"
    age = _num(tof.get("age_ms"))
    if age is not None and age > STALE_MS:
        return "stale"
    return "live" if any(_num(tof.get(k)) is not None for k in ("left_mm", "ahead_mm", "right_mm")) else "stale"


def approach_ttc(entry):
    """The time to collision in s of an approaching camera alert or fused hazard, or None (not approaching, no TTC,
    or the detector does not send the field yet)."""
    if not isinstance(entry, dict) or entry.get("approaching") is not True:
        return None
    ttc = _num(entry.get("ttc_s"))
    return ttc if ttc is not None and ttc >= 0 else None


def side_rows(telemetry, camera_alerts, side):
    """sw7_style_pages.combined_hazards for one side, with the side's words (behind for the rear) and, when the
    detector sends them, the approaching flag and the time to collision. Nearest first."""
    from .sensors_page import direction_of, hazards_of
    from .sw7_style_pages import BAND_LIMIT_M
    rows = []
    for h in hazards_of(telemetry):
        rows.append({"cls": str(h.get("class") or "object").lower(), "dist": _num(h.get("distance_m")),
                     "band": h.get("band"), "where": where_word(direction_of(h), side),
                     "source": str(h.get("source") or ""), "conf": None, "matched": False,
                     "ttc": approach_ttc(h), "track": h.get("track_id")})
    for a in camera_alerts or []:
        if not isinstance(a, dict):
            continue
        cls = str(a.get("class") or "object").lower()
        conf = _num(a.get("confidence"))
        track = a.get("track_id")
        match = next((r for r in rows if r["source"] in ("camera", "fused") and not r["matched"] and r["cls"] == cls
                      and (track is None or r["track"] is None or r["track"] == track)), None)
        if match is not None:
            match["matched"] = True
            if conf is not None:
                match["conf"] = conf
            if match["ttc"] is None:
                match["ttc"] = approach_ttc(a)
            continue
        rows.append({"cls": cls, "dist": None, "band": a.get("distance_band"), "where": where_word("ahead", side),
                     "source": "camera", "conf": conf, "matched": True, "ttc": approach_ttc(a), "track": track})

    def key(r):
        if r["dist"] is not None:
            return (0, r["dist"])
        lim = BAND_LIMIT_M.get(r["band"])
        return (0, lim) if lim is not None else (1, 0.0)
    rows.sort(key=key)
    return rows


def row_texts(row):
    """(main line, detail line, THEME status key); the detail starts with "Approaching · 2.1 s" when known."""
    from .sw7_style_pages import row_texts as base
    main, detail, status = base(row)
    if row.get("ttc") is not None:
        detail = f"Approaching · {row['ttc']:.1f} s · " + detail
    return main, detail, status


def banner_items(side, telemetry, alerts_data):
    """Banner candidates from one side, in the driver's frame: [(order key, status, text)].
    Approaching objects with a time to collision under 4 s first (red under 2 s), then immediate obstacles."""
    from .sensors_page import direction_of, hazards_of
    word = SIDE_WORD[side].upper()
    items, tracks = [], {}
    live = side_link(telemetry) != "offline"
    hazards = hazards_of(telemetry) if live else []
    active = alerts_data.get("active", []) if isinstance(alerts_data, dict) else []
    for entry in list(hazards) + [a for a in active if isinstance(a, dict)]:
        ttc = approach_ttc(entry)
        if ttc is None or ttc >= TTC_WARN_S:
            continue
        track = entry.get("track_id")
        if track is not None and track in tracks and tracks[track] <= ttc:
            continue
        if track is not None:
            items = [i for i in items if i[3] != track]
            tracks[track] = ttc
        cls = str(entry.get("class") or "object").upper()
        items.append(((0, ttc), "crit" if ttc < TTC_CRIT_S else "warn", f"{cls} APPROACHING · {word} · {ttc:.1f} s", track))
    for h in hazards:
        if h.get("band") != "immediate" or (h.get("track_id") is not None and h.get("track_id") in tracks):
            continue
        d = _num(h.get("distance_m"))
        where = direction_of(h)
        place = word if where == "ahead" else f"{word} {where.upper()}"
        dist = f"{d:.1f} M" if d is not None else "DISTANCE UNKNOWN"
        items.append(((1, d if d is not None else 99.0), "crit", f"{str(h.get('class') or 'object').upper()} {dist} {place}", None))
    return [(k, s, t) for k, s, t, _tr in items]


# ---- polling --------------------------------------------------------------------------------------------------------
class JsonPoller(QObject):
    """GET <url_fn()><path> every 500 ms; updated(dict or None). None when the address is unknown (the resolver is
    still searching), the request fails or the reply is not a JSON object."""
    updated = Signal(object)

    def __init__(self, url_fn, path, parent=None):
        super().__init__(parent)
        self.url_fn, self.path = url_fn, path
        self.last = None
        self.polls = 0
        self._reply = None
        self._net = QNetworkAccessManager(self)
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self.poll)

    def start(self):
        self._timer.start()
        self.poll()

    def stop(self):
        self._timer.stop()
        reply, self._reply = self._reply, None
        if reply is not None:
            reply.finished.disconnect(self._finished)
            reply.abort()
            reply.deleteLater()

    def poll(self):
        if self._reply is not None:
            return
        base = self.url_fn()
        if base is None:
            self._emit(None)
            return
        req = QNetworkRequest(QUrl(base + self.path))
        req.setTransferTimeout(REQUEST_TIMEOUT_MS)
        self._reply = self._net.get(req)
        self._reply.finished.connect(self._finished)

    def _finished(self):
        reply, self._reply = self._reply, None
        if reply is None:
            return
        ok = reply.error() == QNetworkReply.NetworkError.NoError
        payload = bytes(reply.readAll()) if ok else b""
        reply.deleteLater()
        data = None
        if ok:
            try:
                data = json.loads(payload)
            except (ValueError, UnicodeDecodeError):
                data = None
        self._emit(data if isinstance(data, dict) else None)

    def _emit(self, data):
        self.last = data
        self.polls += 1
        self.updated.emit(data)


class Side:
    """What is known about one side: its ToF/fusion reply in the driver's frame, its camera's /alerts reply."""

    def __init__(self, name):
        self.name = name
        self.raw = None             # the /telemetry reply as received
        self.telemetry = None       # the same in the driver's frame
        self.updated_at = 0.0
        self.alerts = None          # the /alerts reply, or None when the camera cannot be reached
        self.alerts_polled = False
        self.was_live = False
        self.lost_since = None

    @property
    def link(self):
        return side_link(self.raw)


# ---- the widgets -----------------------------------------------------------------------------------------------------
class SideToggle(QFrame):
    """Front | Rear: two 112 x 64 px segments on a card, signal outline, the selected one filled in signal (the only
    signal on the camera frame: it is the only thing there to tap)."""
    picked = Signal(str)
    SEG_W, SEG_H, PAD = 112, 64, 4

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("sw7SideToggle")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(self.PAD, self.PAD, self.PAD, self.PAD)
        lay.setSpacing(self.PAD)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = {}
        for side in SIDES:
            b = QPushButton(SIDE_WORD[side], self)
            b.setObjectName("sw7Side" + SIDE_WORD[side])
            b.setCheckable(True)
            b.setFixedSize(self.SEG_W, self.SEG_H)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setAccessibleName(f"{SIDE_WORD[side]} camera and sensors")
            b.clicked.connect(lambda _c=False, s=side: self.picked.emit(s))
            self.group.addButton(b)
            lay.addWidget(b)
            self.buttons[side] = b
        self.setFixedSize(2 * self.SEG_W + 3 * self.PAD, self.SEG_H + 2 * self.PAD)
        self.restyle()

    def set_side(self, side):
        b = self.buttons.get(side)
        if b is not None and not b.isChecked():
            b.setChecked(True)

    def restyle(self, *_):
        qss = (f"QFrame#sw7SideToggle {{ background: {S.hx('card')}; border: 1px solid {S.hx('hairline')};"
               f" border-radius: {S.RADIUS_MAX}px; }}")
        for side in SIDES:
            qss += " " + S.button_qss("outline", 6, S.BODY, f"QPushButton#sw7Side{SIDE_WORD[side]}")
        self.setStyleSheet(qss)
        for b in self.buttons.values():
            b.setFont(S.font(S.BODY, QFont.Weight.DemiBold))


def _slab_class():
    from .sw7_style_pages import FrameSlab

    class DualSlab(FrameSlab):
        """The camera frame for one side: the rear image mirrored (reversing camera), and the side's word on it."""

        def __init__(self, view):
            super().__init__(view)
            self.side = FRONT

        def word_rect(self):
            f = S.font(S.SECONDARY, QFont.Weight.DemiBold, caps=True)
            tw = QFontMetrics(f).horizontalAdvance(SIDE_WORD[self.side].upper())
            extra = QFontMetrics(S.font(S.LABEL, QFont.Weight.DemiBold, caps=True)).horizontalAdvance("MIRRORED") + 12 \
                if self.side == REAR else 0
            return QRectF(16, 52, tw + extra + 28, 36)

        def paintEvent(self, _e):
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            r = QRectF(self.rect())
            clip = QPainterPath(); clip.addRoundedRect(r, self.RADIUS, self.RADIUS)
            p.setClipPath(clip)
            p.fillRect(r, S.c("charcoal"))
            AL = Qt.AlignmentFlag
            if self.image is not None:
                if self.side == REAR:          # mirrored left to right, like a car's reversing camera
                    p.save(); p.translate(self.width(), 0); p.scale(-1, 1)
                    p.drawPixmap(0, 0, self.image)
                    p.restore()
                else:
                    p.drawPixmap(0, 0, self.image)
            else:
                p.setPen(S.c("on_charcoal_2")); p.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True))
                p.drawText(QRectF(0, r.center().y() - 26, r.width(), 20), AL.AlignCenter,
                           f"NO {SIDE_WORD[self.side].upper()} CAMERA IMAGE")
                p.setPen(S.c("on_charcoal")); p.setFont(S.font(S.BODY))
                p.drawText(QRectF(0, r.center().y() - 2, r.width(), 24), AL.AlignCenter,
                           self.view.camera.status_label.text() or "Waiting for the camera")
            # the side's word, so the view is never ambiguous
            wr = self.word_rect()
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(S.c("charcoal", 215))
            p.drawRoundedRect(wr, S.RADIUS_SM, S.RADIUS_SM)
            p.setPen(S.c("on_charcoal")); p.setFont(S.font(S.SECONDARY, QFont.Weight.DemiBold, caps=True))
            p.drawText(wr.adjusted(14, 0, -14, 0), AL.AlignLeft | AL.AlignVCenter, SIDE_WORD[self.side].upper())
            if self.side == REAR:
                p.setPen(S.c("on_charcoal_2")); p.setFont(S.font(S.LABEL, QFont.Weight.DemiBold, caps=True))
                p.drawText(wr.adjusted(14, 0, -14, 0), AL.AlignRight | AL.AlignVCenter, "MIRRORED")
            p.end()
    return DualSlab


def _figure_class():
    from .sw7_style_pages import TukFigure, mark, tok

    class DualFigure(TukFigure):
        """The tuk-tuk from above, nose up, with one side's three ToF distances. Front: as TukFigure (the sensors at
        the nose). Rear: the sensors at the tail, the straight back reading called "behind"; left and right are the
        driver's (to_vehicle_frame swapped the rear board's)."""

        def __init__(self, parent):
            super().__init__(parent)
            self.side = FRONT

        def set_side(self, side):
            if side != self.side:
                self.side = side
                self.update()

        def layout_of(self, w, h):
            cx, bw, bl = w / 2, 60.0, 100.0
            if self.side == REAR:
                nose = 48.0
                tail = nose + bl
                sensors = {"ahead": QPointF(cx, tail), "left": QPointF(cx - bw / 2, tail - 44),
                           "right": QPointF(cx + bw / 2, tail - 44)}
                heading = {"ahead": 270.0, "left": 180.0, "right": 0.0}
                r_max = {"ahead": max(24.0, min(58.0, h - tail - 56)), "left": 58.0, "right": 58.0}
            else:
                nose = 116.0
                sensors = {"ahead": QPointF(cx, nose), "left": QPointF(cx - bw / 2, nose + 44),
                           "right": QPointF(cx + bw / 2, nose + 44)}
                heading = {"ahead": 90.0, "left": 180.0, "right": 0.0}
                r_max = {s: 58.0 for s in self.SIDES}
            return QRectF(cx - bw / 2, nose, bw, bl), sensors, heading, r_max

        def geometry_of(self):
            c = self.card_rect()
            body, sensors, _h, _r = self.layout_of(c.width(), c.height())
            return body, sensors

        def paintEvent(self, _e):
            from .sensors_page import TOF_MAX_M, tof_status
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            card = self.card_rect()
            S.paint_card(p, card, self.RADIUS, 1)
            p.translate(card.topLeft())
            w, h = card.width(), card.height()
            AL = Qt.AlignmentFlag
            p.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True)); p.setPen(S.c("ink_2"))
            p.drawText(QRectF(24, 18, 360, 18), AL.AlignLeft | AL.AlignVCenter,
                       f"AROUND THE TUK-TUK · {SIDE_WORD[self.side].upper()}")
            body, sensors, heading, r_max = self.layout_of(w, h)
            r_min = 18.0
            radius = {}
            for side in self.SIDES:
                m = self.metres.get(side)
                frac = 1.0 if m is None else max(0.0, min(1.0, m / TOF_MAX_M))
                r = r_min + (r_max[side] - r_min) * frac
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
            for side in self.SIDES:
                c = sensors[side]
                mark(p, QRect(int(c.x()) - 6, int(c.y()) - 6, 12, 12), tok(tof_status(self.metres.get(side))), ring="card")
            vals = self.values()
            ahead_top = 40 if self.side == FRONT else sensors["ahead"].y() + radius["ahead"] + 22
            blocks = {"ahead": QRectF(w / 2 - 130, ahead_top, 260, 30),
                      "left": QRectF(24, sensors["left"].y() - 6, sensors["left"].x() - radius["left"] - 40, 30),
                      "right": QRectF(sensors["right"].x() + radius["right"] + 16, sensors["right"].y() - 6,
                                      w - 24 - (sensors["right"].x() + radius["right"] + 16), 30)}
            align = {"ahead": AL.AlignHCenter, "left": AL.AlignRight, "right": AL.AlignLeft}
            for side in self.SIDES:
                value, word = vals[side]
                b = blocks[side]
                name = where_word(side, self.side).upper()
                p.setFont(S.font(S.LABEL, QFont.Weight.Bold, caps=True)); p.setPen(S.c("ink_2"))
                p.drawText(QRectF(b.left(), b.top() - 20, b.width(), 18), align[side] | AL.AlignVCenter,
                           f"{name} · {word.upper()}")
                p.setFont(S.mono(S.SECONDARY, QFont.Weight.Medium) if value[:1].isdigit()
                          else S.font(S.SECONDARY, QFont.Weight.Medium))
                p.setPen(S.c("ink_3" if value.startswith("--") else "ink"))
                p.drawText(b, align[side] | AL.AlignVCenter, value)
            p.end()
    return DualFigure


# ---- the controller --------------------------------------------------------------------------------------------------
class DualCamera(QObject):
    side_changed = Signal(str)

    def __init__(self, main):
        super().__init__(main)
        from .sw7_style_pages import SurroundingsView
        self.main, self.view, self.camera = main, main.sw7_surroundings, main.front_camera
        self.sides = {s: Side(s) for s in SIDES}
        self.gear = None
        self.before_reverse = None
        self.banner_side = None
        self.resolver = None
        self._rear_override = _env_url("TUKZIE_REAR_CAMERA_URL")
        if self._rear_override is None:
            # the rear camera is on the Pi 4, the host of the bridge the live-data provider uses: its resolver, or the
            # host of TUKZIE_TELEMETRY_URL when that fixes the bridge (no second resolver, no second beacon listener)
            tel = getattr(main, "telemetry", None)
            self.resolver = getattr(tel, "resolver", None)
            if self.resolver is not None:
                self.resolver.host_changed.connect(self._on_pi4_changed)
            elif getattr(tel, "_fixed_url", None):
                host = QUrl(tel._fixed_url).host()
                self._rear_override = f"http://{host}:8080" if host else None
        self.selected = self._load_pref()

        # ---- the camera page: told which address to stream, fed the selected side's alerts
        cam = self.camera
        cam._alert_timer.stop()
        if cam.resolver is not None:
            try:
                cam.resolver.host_changed.disconnect(cam._on_pi4_changed)
            except (RuntimeError, TypeError):
                pass
        cam.camera_url = lambda: self.camera_url(self.selected)
        # a side whose stream drops or stalls shows no picture (the page used to keep the last frame on screen)
        cam._on_stream_finished = self._stream_finished
        cam._stale_timer.timeout.connect(self._drop_picture)

        # ---- the page: the side's slab, figure and toggle in place of the single-camera ones
        v = self.view
        old_slab, old_fig = v.slab, v.figure
        v.slab = _slab_class()(v)
        v.figure = _figure_class()(v)
        for w in (old_slab, old_fig):
            w.hide(); w.setParent(None); w.deleteLater()
        self.toggle = SideToggle(v)
        self.toggle.picked.connect(lambda s: self.set_side(s, user=True))
        S.elevate(self.toggle, 1)
        v.slab.lower()
        v.figure.raise_(); v.chip.raise_(); self.toggle.raise_()
        v.set_telemetry = lambda *_a, **_k: None          # the controller feeds the view, per side
        v.refresh = self._refresh_view
        v._place = self._place_view
        from ..theme import THEME
        THEME.changed.connect(self.toggle.restyle)
        self._view_set_telemetry = SurroundingsView.set_telemetry

        # ---- sources
        self.front_tof = JsonPoller(front_tof_url, "/telemetry", self)
        self.front_tof.updated.connect(lambda t: self._on_telemetry(FRONT, t))
        self.alert_pollers = {FRONT: JsonPoller(front_camera_url, "/alerts", self),
                              REAR: JsonPoller(lambda: self.camera_url(REAR), "/alerts", self)}
        for side, poller in self.alert_pollers.items():
            poller.updated.connect(lambda data, s=side: self._on_alerts(s, data))
        tel = getattr(main, "telemetry", None)
        if tel is not None:
            tel.telemetry_updated.connect(lambda t: self._on_telemetry(REAR, t))
            # The Pi 4 bridge is now the rear one: its straight-on ToF becomes the rear obstacle and the
            # front obstacle comes from the Pi 5's own ToF (live_data_provider.build_live_state, dual=True).
            tel.dual = True
            self.front_tof.updated.connect(lambda t: setattr(tel, "front_telemetry", t))
        self._watchdog = QTimer(self)
        self._watchdog.setInterval(1000)
        self._watchdog.timeout.connect(self._check_stale)

        # ---- banner, Around tile, gear
        hb = getattr(main, "hazard_banner", None)
        if hb is not None:
            hb.sw7_dual = self                            # its own per-telemetry update is skipped (see install)
            hb._shown_check = lambda: False               # what it shows is chosen here (the side not on screen)
            self._tap_side = None
            hb.text.pressed.connect(lambda: setattr(self, "_tap_side", self.banner_side))   # before the page changes
            hb.open_sensors.connect(self._banner_opened)
        main.stack.currentChanged.connect(lambda *_: self.update_banner())
        main.state_updated.connect(self._on_state)

        self._apply_side(initial=True)
        self.front_tof.start()
        for poller in self.alert_pollers.values():
            poller.start()
        self._watchdog.start()

    # ---- addresses and preferences ---------------------------------------------------------------------------------
    def camera_url(self, side):
        if side == FRONT:
            return front_camera_url()
        if self._rear_override is not None:
            return self._rear_override
        return self.resolver.camera_url() if self.resolver is not None else None

    def _load_pref(self):
        prefs = getattr(self.main, "preferences", None)
        try:
            side = prefs.data.get("global", {}).get(PREF_KEY)
        except AttributeError:
            side = None
        return side if side in SIDES else FRONT

    def _save_pref(self, side):
        prefs = getattr(self.main, "preferences", None)
        if prefs is None:
            return
        try:
            prefs.data.setdefault("global", {})[PREF_KEY] = side
            prefs.save()
        except (AttributeError, OSError, TypeError):
            pass

    # ---- switching -------------------------------------------------------------------------------------------------
    def set_side(self, side, user=False):
        if side not in SIDES:
            return
        if user:
            self._save_pref(side)
            if self.gear == "R":
                self.before_reverse = side       # a choice made in R is the one to return to
        if side == self.selected:
            self.toggle.set_side(side)
            return
        self.selected = side
        self._apply_side()

    def _apply_side(self, initial=False):
        side, v, cam = self.selected, self.view, self.camera
        self.toggle.set_side(side)
        v.slab.side = side
        v.figure.set_side(side)
        v.hz_title.setText(f"{SIDE_WORD[side].upper()} HAZARDS · CAMERA AND TOF · NEAREST FIRST")
        # the other side's picture, alerts and readings go at once: nothing stale is ever shown for this side
        cam._stop_stream()
        cam._buf = b""
        cam._pixmap = None
        cam._stale_timer.stop()
        v.slab.image = None
        v.slab.update()
        cam.status_label.set_fps(None)
        cam.status_label.setText("Connecting")
        if cam._last_alerts:
            cam._last_alerts = []
            cam._render_alerts([])
            cam.alerts_changed.emit([])
        v.alerts = []
        cam._start_stream()
        s = self.sides[side]
        if s.alerts_polled:
            self._apply_camera(s.alerts)
        self._feed_view()
        self.update_banner()
        if not initial:
            self.side_changed.emit(side)

    def _stream_finished(self):
        from .front_camera_page import FrontCameraPage
        FrontCameraPage._on_stream_finished(self.camera)
        self._drop_picture()

    def _drop_picture(self):
        self.camera._pixmap = None
        self.view.slab.image = None
        self.view.slab.update()

    def _on_pi4_changed(self, host, how):
        if self.selected == REAR and self._rear_override is None:
            cam = self.camera
            cam._stop_stream()
            if not host:
                cam.status_label.setText("Searching for the Pi 4")
            cam._start_stream()

    # ---- data ------------------------------------------------------------------------------------------------------
    def _on_alerts(self, side, data):
        s = self.sides[side]
        s.alerts, s.alerts_polled = data, True
        if side == self.selected:
            self._apply_camera(data)
        self.update_banner()

    def _apply_camera(self, data):
        cam = self.camera
        if self.camera_url(self.selected) is None:
            cam.status_label.setText("Searching for the Pi 4")
            cam._apply_alerts(None)
        elif data is None:
            cam.status_label.setText("Camera offline, retrying")
            cam._apply_alerts(None)
        else:
            cam._apply_alerts(data)

    def _on_telemetry(self, side, raw):
        s = self.sides[side]
        s.raw = raw if isinstance(raw, dict) else None
        s.telemetry = to_vehicle_frame(s.raw, side)
        s.updated_at = time.monotonic()
        if s.link != "offline":
            s.was_live, s.lost_since = True, None
        elif s.was_live and s.lost_since is None:
            s.lost_since = time.monotonic()
        if side == self.selected or (side == REAR and self.selected == FRONT):
            self._feed_view()            # the rear reply also carries the ride row (the ESP32 is on the Pi 4)
        if side == FRONT:
            self._feed_around(s.telemetry)
        self.update_banner()

    def _check_stale(self):
        now = time.monotonic()
        for side, s in self.sides.items():
            if s.raw is not None and (now - s.updated_at) * 1000 > STALE_MS:
                self._on_telemetry(side, None)

    def _feed_view(self):
        self._view_set_telemetry(self.view, self.sides[self.selected].telemetry)

    def _feed_around(self, telemetry):
        tile = getattr(getattr(self.main, "driving", None), "sw7_tiles", {}).get("around")
        if tile is not None:
            tile.label = "AROUND · FRONT"
            tile.set_telemetry(telemetry, sw7_dual=True)

    # ---- the page --------------------------------------------------------------------------------------------------
    def _place_view(self):
        from .sw7_style_pages import SurroundingsView
        v = self.view
        SurroundingsView._place(v)
        frame = v.rects()[0]
        self.toggle.move(int(frame.right()) - 16 - self.toggle.width(), int(frame.top()) + 16)

    def _refresh_view(self):
        """SurroundingsView.refresh for the selected side: its hazards (with the TTC of approaching objects), its link,
        its words; the ride row from the Pi 4's ESP32 whichever side is shown."""
        from .sw7_style_pages import BAND_LIMIT_M, MAX_ROWS, SOURCE_WORD, chip_style
        from ..widgets.ride_quality_card import format_telemetry, replay_of
        v, side = self.view, self.selected
        s = self.sides[side]
        v.rows = side_rows(s.telemetry, v.alerts, side)
        link = s.link
        v.link = link
        replay = replay_of(s.raw)[0]
        text, key = ((f"{SIDE_WORD[side]} replay", "warn") if replay and link != "offline"
                     else (f"{SIDE_WORD[side]} {LINK_TEXT[link][0]}", LINK_TEXT[link][1]))
        chip_style(v.link_chip, text, key)
        for i, w in enumerate(v.rows_w):
            if i < len(v.rows) and (i < MAX_ROWS - 1 or len(v.rows) <= MAX_ROWS):
                main, detail, status = row_texts(v.rows[i])
                w.set_row(main, detail, status, i == 0)
                w.show()
            else:
                w.hide()
        extra = len(v.rows) - (MAX_ROWS - 1) if len(v.rows) > MAX_ROWS else 0
        v.more.setText(f"+{extra} more, farther away" if extra else "")
        no_data = link == "offline" and not v.alerts
        v.empty.setText("" if v.rows else ("No sensor data" if no_data else "No hazards"))
        if v.rows:
            r = v.rows[0]
            _main, _detail, status = row_texts(r)
            if r["dist"] is not None:
                d = r["dist"]
                hero = f"{d:.2f}" if d < 1.2 else f"{d:.1f}"
            else:
                lim = BAND_LIMIT_M.get(r["band"])
                hero = f"<{lim:.0f}" if lim else "--"
            unit = "m" if hero != "--" else ""
            src = SOURCE_WORD.get(r["source"], r["source"])
            sub = f"{r['cls'].capitalize()} {r['where']} · {src}"
            if r.get("ttc") is not None:
                sub += f" · {r['ttc']:.1f} s"
        else:
            hero, unit, status = ("--", "", "inactive") if no_data else ("Clear", "", "normal")
            sub = "No sensor data" if no_data else f"Nothing detected {'behind' if side == REAR else 'in front of'} the tuk-tuk"
        v.hero.setText(hero); v.unit.setText(unit); v.sub.setText(sub)
        v.sub_status = status
        ride = format_telemetry(self.sides[REAR].raw)[1]
        vib, dis = ride.get("vib", ("--", None))[0], ride.get("vib_dis", ("--", None))[0]
        v.ride.setText(f"Vibration {vib} · IMU disagreement {dis}")
        v.figure.set_metres(_tof_metres(s.telemetry))
        v.replay = replay
        self._place_view()
        v.update()

    # ---- banner ----------------------------------------------------------------------------------------------------
    def banner_message(self):
        """(status, text, side) for the banner, or None. On Surroundings the side on screen is left out."""
        on_page = self.main.stack.currentWidget() is getattr(self.main, "sensors", None)
        items = []
        for side in SIDES:
            if on_page and side == self.selected:
                continue
            s = self.sides[side]
            for key, status, text in banner_items(side, s.telemetry, s.alerts):
                items.append((key, status, text, side))
            if s.lost_since is not None and time.monotonic() - s.lost_since >= LINK_LOST_S:
                items.append(((2, 0.0), "warn", f"{SIDE_WORD[side]} sensor link lost", side))
        if not items:
            return None
        items.sort(key=lambda i: i[0])
        top = items[0]
        more = f"  (+{len(items) - 1} more)" if len(items) > 1 else ""
        return top[1], top[2] + more, top[3]

    def update_banner(self):
        hb = getattr(self.main, "hazard_banner", None)
        if hb is None:
            return
        msg = self.banner_message()
        if msg is None:
            hb._message, self.banner_side = None, None
        else:
            hb._message, self.banner_side = (msg[0], msg[1]), msg[2]
        hb.sw7_side = self.banner_side
        hb._refresh()

    def _banner_opened(self):
        side, self._tap_side = self._tap_side or self.banner_side, None
        if side in SIDES:
            self.set_side(side, user=True)

    # ---- gear --------------------------------------------------------------------------------------------------------
    def _on_state(self, state):
        g = getattr(state, "gear", None)
        g = g.value if hasattr(g, "value") else (str(g) if g is not None else None)
        if g == self.gear:
            return
        was, self.gear = self.gear, g
        if g == "R":
            self.before_reverse = self.selected
            self.set_side(REAR)
            # the team's reverse page has no rear sensor; the rear camera and ToF are on Surroundings
            if self.main.stack.currentWidget() is getattr(self.main, "reverse", None):
                self.main.switch_page_id("sensors")
        elif was == "R" and self.before_reverse is not None:
            self.set_side(self.before_reverse)
            self.before_reverse = None


def _tof_metres(telemetry):
    from .sensors_page import tof_metres
    return tof_metres(telemetry)


# ---- install ---------------------------------------------------------------------------------------------------------
def _wrap(cls, name, after=None, replace=None):
    orig = getattr(cls, name)
    if getattr(orig, "_sw7_dual", False):
        return
    if replace is not None:
        def method(self, *a, **k):
            return replace(orig, self, *a, **k)
    else:
        def method(self, *a, **k):
            result = orig(self, *a, **k)
            after(self, *a, **k)
            return result
    method._sw7_dual = True
    method.__name__ = name
    setattr(cls, name, method)


def _banner_telemetry(orig, banner, *a, **k):
    if getattr(banner, "sw7_dual", None) is not None:
        return None                      # the controller chooses the message from both sides
    return orig(banner, *a, **k)


def _around_telemetry(orig, tile, telemetry, *a, sw7_dual=False, **k):
    if _active is not None and not sw7_dual:
        return None                      # the Pi 4 board is at the rear now; the controller feeds the front one
    return orig(tile, telemetry, *a, **k)


def install(main_cls):
    """Called once from dashboard_main.py after sw7_style_pages.install. Nothing with TUKZIE_SW7_DUAL_CAM=0 or the team
    style (there is no Surroundings page then)."""
    global _installed
    if _installed or not enabled() or not S.enabled():
        return
    from . import sw7_style_pages
    if not getattr(sw7_style_pages, "_installed", False):
        return
    _installed = True
    from . import sensors_page
    _wrap(sensors_page.HazardBanner, "set_telemetry", replace=_banner_telemetry)
    try:
        from ..widgets import sw7_driving
        _wrap(sw7_driving.AroundTile, "set_telemetry", replace=_around_telemetry)
    except (ImportError, AttributeError):
        pass
    _wrap(main_cls, "__init__", after=_main_init)


def _main_init(main, *_a, **_k):
    main.sw7_dual = None
    if getattr(main, "sw7_surroundings", None) is None or getattr(main, "front_camera", None) is None:
        return
    global _active
    main.sw7_dual = _active = DualCamera(main)
