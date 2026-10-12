"""
FrontCameraPage: the SW-7 forward camera inside the TUKZIE dashboard.

Shows the live view from the Raspberry Pi 4 hazard detector
(CameraDetection/hazard_detector.py, run with --preview) and its current
alerts. It talks to the detector over two plain HTTP endpoints:

  GET <camera_url>/stream   MJPEG, the camera image with detections drawn on
  GET <camera_url>/alerts   JSON, {"active": [...], "fps": n, "latency_ms": n}
                            each active alert has class, distance_band,
                            confidence, timestamp, alert_status

The camera address comes from the TUKZIE_CAMERA_URL environment variable if
set; otherwise from the shared Pi 4 resolver (sw7_endpoints.py,
TELEMETRY_LINK.md section 4.3) as http://<Pi 4 host>:8080, following it when
the Pi 4 is found somewhere else.

Drop this file into app/pages/ and wire it up as described in
DashboardIntegration/README.md. It uses only QtNetwork and QtWidgets (no
QtWebEngine), streams video only while the page is on screen, and keeps
only the newest frame, so a slow link drops frames rather than lagging.

Layout (TUKZIE_SW7_LAYOUT, default on; Planning/layout-improvements-prompt.md): the connection status is a
coloured chip like the LIVE / NO DATA source chip, alerts are 64 px rows with a 12 px band colour bar
(nearest band first, the top immediate or warning alert filled), and no text is under 16 px, since glare
washes small text out on the glossy panel. TUKZIE_SW7_LAYOUT=0 gives the earlier page exactly.
"""
from __future__ import annotations

import json
import os

from PySide6.QtCore import QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

from ..theme import THEME
from .base_page import BasePage

# Fixed camera address; None (the default) means: ask the Pi 4 resolver.
CAMERA_URL = (os.environ.get("TUKZIE_CAMERA_URL", "").strip().rstrip("/") or None)

# Band -> dashboard status colour key (fixed across every palette).
BAND_STATUS = {"immediate": "crit", "warning": "warn", "monitoring": "normal"}
BAND_TEXT = {"immediate": "Immediate", "warning": "Warning", "monitoring": "Monitoring"}
BAND_RANGE = {"immediate": "under 3 m", "warning": "under 8 m", "monitoring": "under 15 m"}
BAND_ORDER = {"immediate": 0, "warning": 1, "monitoring": 2}
# Filled top-alert colours, the same as the obstacle pill (Planning/google-stitch-dashboard-prompt.md section 2).
FILLED = {"crit": ("#A3201A", "#FFFFFF"), "warn": ("#FFB224", "#0B0D10")}

MAX_BUFFER_BYTES = 2_000_000   # drop the buffer if no complete frame turns up in this much data
ALERT_POLL_MS = 500
RECONNECT_MS = 3000
STALE_MS = 2500                # no new frame for this long: show the image as stale
STREAM_SILENCE_MS = 5000       # no stream bytes for this long: drop the connection and retry


def layout_on():
    """SW-7 layout pass (TUKZIE_SW7_LAYOUT, default on); 0 keeps the earlier layout exactly."""
    return os.environ.get("TUKZIE_SW7_LAYOUT", "1").strip() != "0"


class AlertRow(QFrame):
    """One alert, 64 px tall: a 12 px band colour bar, the main text 24 px bold, a detail line 18 px and an
    optional right-hand note 16 px. filled=True paints the whole row in the obstacle pill colours."""

    def __init__(self, status, main, detail="", note="", filled=False, parent=None):
        super().__init__(parent)
        self.setObjectName("sw7AlertRow")
        self.setFixedHeight(64)
        colour = THEME.color(status).name()
        bg, fg = FILLED.get(status, (None, None)) if filled else (None, None)
        bg = bg or THEME.hex("card_alt")
        fg = fg or THEME.hex("text")
        dim = fg if filled else THEME.hex("text_dim")
        self.setStyleSheet(f"QFrame#sw7AlertRow {{ background: {bg}; border: 1px solid {THEME.hex('border')};"
                           f" border-radius: 10px; }} QLabel {{ background: transparent; border: none; color: {fg}; }}"
                           f" QLabel#sw7AlertDim {{ color: {dim}; }}"
                           f" QFrame#sw7AlertBar {{ background: {colour}; border: none; border-radius: 4px; }}")
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 4, 12, 4)
        row.setSpacing(12)
        bar = QFrame(); bar.setObjectName("sw7AlertBar"); bar.setFixedWidth(12)
        row.addWidget(bar)
        text = QVBoxLayout(); text.setContentsMargins(0, 0, 0, 0); text.setSpacing(0)
        self.main = QLabel(main); self.main.setFont(THEME.font(24 if detail else 22, QFont.Weight.Bold))
        text.addWidget(self.main)
        self.detail = QLabel(detail); self.detail.setFont(THEME.font(18))
        if detail:
            text.addWidget(self.detail)
        row.addLayout(text, 1)
        self.note = QLabel(note); self.note.setObjectName("sw7AlertDim"); self.note.setFont(THEME.font(16))
        if note:
            row.addWidget(self.note, 0, Qt.AlignmentFlag.AlignVCenter)


class StatusChip(QLabel):
    """The camera status as a chip like the LIVE / NO DATA source chip: 28 px tall, 16 px bold, filled.
    text() returns the plain status ("Live", "Camera image stale", ...), so callers see what they set;
    the chip shows the frame rate after "Live"."""
    STATUS = {"Live": "normal", "Camera image stale": "warn"}

    def __init__(self, text=""):
        super().__init__()
        self._status = ""
        self._fps = None
        self.setObjectName("sw7CameraChip")
        self.setFixedHeight(28)
        self.setFont(THEME.font(16, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText(text)

    def text(self):
        return self._status

    def set_fps(self, fps):
        self._fps = fps
        self.setText(self._status)

    def setText(self, text):
        self._status = text
        shown = f"{text} · {self._fps:.1f} fps" if text == "Live" and self._fps is not None else text
        super().setText(shown)
        key = self.STATUS.get(text, "inactive")
        fg = "#0B0D10" if key in ("normal", "warn") else "#FFFFFF"
        self.setStyleSheet(f"QLabel#sw7CameraChip {{ background: {THEME.color(key).name()}; color: {fg};"
                           " border-radius: 8px; padding: 0px 14px; }")


def extract_latest_jpeg(buf: bytes) -> tuple[bytes | None, bytes]:
    """Return (newest complete JPEG in buf or None, bytes left to keep).

    JPEG data never contains FF D9 except as the end-of-image marker (the
    encoder byte-stuffs FF in entropy-coded data), so frames are found from
    their start (FF D8) and end (FF D9) markers without parsing multipart
    headers. Older complete frames are skipped on purpose."""
    latest = None
    pos = 0
    while True:
        start = buf.find(b"\xff\xd8", pos)
        if start < 0:
            return latest, b""
        end = buf.find(b"\xff\xd9", start + 2)
        if end < 0:
            return latest, buf[start:]
        latest = buf[start:end + 2]
        pos = end + 2


class FrontCameraPage(BasePage):
    title = "Front camera"
    alerts_changed = Signal(list)   # list of active alert dicts, nearest band first

    def build(self):
        self._net = QNetworkAccessManager(self)
        self._stream_reply = None
        self._alert_reply = None
        self._buf = b""
        self._pixmap = None
        self._streaming_wanted = False
        self._last_alerts = []
        self.resolver = None
        if CAMERA_URL is None:
            from ..data.sw7_endpoints import shared_resolver
            self.resolver = shared_resolver()
            self.resolver.host_changed.connect(self._on_pi4_changed)

        self._layout = layout_on()
        if self._layout:
            self._build_layout()
        else:
            self._build_classic()
        self._render_alerts([])

        self._alert_timer = QTimer(self)
        self._alert_timer.timeout.connect(self._poll_alerts)
        self._alert_timer.start(ALERT_POLL_MS)

        self._stale_timer = QTimer(self)
        self._stale_timer.setSingleShot(True)
        self._stale_timer.timeout.connect(self._mark_stale)

        THEME.changed.connect(lambda *_: self._render_alerts(self._last_alerts))

    def _build_layout(self):
        """Title and status chip on one line; the video beside a 340 px alerts card."""
        self._root.setContentsMargins(24, 16, 24, 16)
        self._root.setSpacing(16)
        header = QHBoxLayout()
        header.setSpacing(16)
        title = QLabel(self.title)
        title.setFont(THEME.font(24, QFont.Weight.Bold))
        header.addWidget(title)
        self.status_label = StatusChip("Connecting")
        header.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignVCenter)
        header.addStretch(1)
        self._root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(16)
        self.video = QLabel("Waiting for the camera")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setMinimumSize(320, 240)
        self.video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video.setObjectName("dim")
        self.video.setFont(THEME.font(20))
        body.addWidget(self.video, 1)

        side = QFrame()
        side.setObjectName("card")
        side.setFixedWidth(340)
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(16, 16, 16, 16)
        side_lay.setSpacing(12)
        heading = QLabel("Alerts")
        heading.setFont(THEME.font(20, QFont.Weight.Bold))
        side_lay.addWidget(heading)
        self.alert_box = QVBoxLayout()
        self.alert_box.setSpacing(8)
        side_lay.addLayout(self.alert_box)
        side_lay.addStretch(1)
        self.metrics_label = QLabel("")
        self.metrics_label.setObjectName("dim")
        self.metrics_label.setFont(THEME.font(16))
        self.metrics_label.setWordWrap(True)
        side_lay.addWidget(self.metrics_label)
        body.addWidget(side, 0)
        self._root.addLayout(body, 1)

    def _build_classic(self):
        header = QHBoxLayout()
        title = QLabel(self.title)
        title.setFont(THEME.font(24, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch(1)
        self.status_label = QLabel("Connecting")
        self.status_label.setObjectName("dim")
        self.status_label.setFont(THEME.font(14))
        header.addWidget(self.status_label)
        self._root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(10)

        self.video = QLabel("Waiting for the camera")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setMinimumSize(320, 240)
        self.video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video.setObjectName("dim")
        self.video.setFont(THEME.font(18))
        body.addWidget(self.video, 3)

        side = QFrame()
        side.setObjectName("card")
        side.setMinimumWidth(240)
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(12, 12, 12, 12)
        side_lay.setSpacing(8)
        heading = QLabel("Alerts")
        heading.setFont(THEME.font(18, QFont.Weight.Bold))
        side_lay.addWidget(heading)
        self.alert_box = QVBoxLayout()
        self.alert_box.setSpacing(6)
        side_lay.addLayout(self.alert_box)
        side_lay.addStretch(1)
        self.metrics_label = QLabel("")
        self.metrics_label.setObjectName("dim")
        self.metrics_label.setFont(THEME.font(12))
        self.metrics_label.setWordWrap(True)
        side_lay.addWidget(self.metrics_label)
        body.addWidget(side, 1)

        self._root.addLayout(body, 1)

    def camera_url(self):
        """The camera address in use, or None while the Pi 4 is being searched for."""
        if CAMERA_URL is not None:
            return CAMERA_URL
        return self.resolver.camera_url() if self.resolver is not None else None

    def _on_pi4_changed(self, host, how):
        # Follow the Pi 4 to its new address: drop the old stream, open a new one.
        self._stop_stream()
        if not host:
            self.status_label.setText("Searching for the Pi 4")
        self._start_stream()

    # ---- video stream: only while the page is visible -------------------
    def showEvent(self, event):
        super().showEvent(event)
        self._streaming_wanted = True
        self._start_stream()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._streaming_wanted = False
        self._stop_stream()

    def _start_stream(self):
        if not self._streaming_wanted or self._stream_reply is not None:
            return
        url = self.camera_url()
        if url is None:
            return              # _on_pi4_changed starts it once the Pi 4 is found
        self._buf = b""
        req = QNetworkRequest(QUrl(url + "/stream"))
        # Qt aborts the transfer if no bytes arrive for this long, which
        # triggers the reconnect below when the camera goes silent.
        req.setTransferTimeout(STREAM_SILENCE_MS)
        self._stream_reply = self._net.get(req)
        self._stream_reply.readyRead.connect(self._on_stream_data)
        self._stream_reply.finished.connect(self._on_stream_finished)

    def _stop_stream(self):
        reply, self._stream_reply = self._stream_reply, None
        if reply is not None:
            reply.readyRead.disconnect(self._on_stream_data)
            reply.finished.disconnect(self._on_stream_finished)
            reply.abort()
            reply.deleteLater()

    def _on_stream_data(self):
        if self._stream_reply is None:
            return
        self._feed(bytes(self._stream_reply.readAll()))

    def _feed(self, data: bytes):
        """Add received bytes; show the newest complete frame, if any."""
        self._buf += data
        jpeg, self._buf = extract_latest_jpeg(self._buf)
        if len(self._buf) > MAX_BUFFER_BYTES:
            self._buf = b""
        if jpeg is None:
            return
        image = QImage.fromData(jpeg, "JPG")
        if image.isNull():
            return
        self._pixmap = QPixmap.fromImage(image)
        self._show_pixmap()
        self._stale_timer.start(STALE_MS)

    def _show_pixmap(self):
        if self._pixmap is None:
            return
        self.video.setPixmap(self._pixmap.scaled(
            self.video.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._show_pixmap()

    def _mark_stale(self):
        if self.status_label.text() == "Live":
            self.status_label.setText("Camera image stale")

    def _on_stream_finished(self):
        reply, self._stream_reply = self._stream_reply, None
        if reply is not None:
            reply.deleteLater()
        self.status_label.setText("Camera offline, retrying")
        if self._streaming_wanted:
            QTimer.singleShot(RECONNECT_MS, self._start_stream)

    # ---- alerts: polled all the time, so other pages can react ----------
    def _poll_alerts(self):
        if self._alert_reply is not None:
            return  # previous poll still in flight
        url = self.camera_url()
        if url is None:
            self.status_label.setText("Searching for the Pi 4")
            self._apply_alerts(None)
            return
        req = QNetworkRequest(QUrl(url + "/alerts"))
        req.setTransferTimeout(ALERT_POLL_MS * 4)
        self._alert_reply = self._net.get(req)
        self._alert_reply.finished.connect(self._on_alerts_finished)

    def _on_alerts_finished(self):
        reply, self._alert_reply = self._alert_reply, None
        if reply is None:
            return
        ok = reply.error() == QNetworkReply.NetworkError.NoError
        payload = bytes(reply.readAll()) if ok else b""
        reply.deleteLater()
        if not ok:
            self.status_label.setText("Camera offline, retrying")
            self._apply_alerts(None)
            return
        try:
            self._apply_alerts(json.loads(payload))
        except (ValueError, TypeError):
            self._apply_alerts(None)

    def _apply_alerts(self, data):
        """data: parsed /alerts JSON, or None when the camera can't be reached."""
        if data is None:
            active, fps, latency = [], None, None
            self.metrics_label.setText("No data from the camera")
        else:
            active = [a for a in data.get("active", []) if isinstance(a, dict)]
            fps, latency = data.get("fps"), data.get("latency_ms")
            parts = []
            if fps is not None:
                parts.append(f"{fps:.1f} frames per second")
            if latency is not None:
                parts.append(f"{latency:.0f} ms sensor to result")
            if self._layout:                        # one footer line; the frame rate is on the chip
                self.status_label.set_fps(fps if isinstance(fps, (int, float)) else None)
                self.metrics_label.setText(f"{latency:.0f} ms sensor to result" if latency is not None else "")
            else:
                self.metrics_label.setText("\n".join(parts))
            if self._stream_reply is not None or not self._streaming_wanted:
                self.status_label.setText("Live")
        if active != self._last_alerts:
            self._last_alerts = active
            self._render_alerts(active)
            self.alerts_changed.emit(active)

    def _render_alerts(self, active):
        while self.alert_box.count():
            item = self.alert_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()          # off screen now, not at the next event loop pass
                w.setParent(None)
                w.deleteLater()
        if self._layout:
            self._render_alert_rows(active)
            return
        if not active:
            none = QLabel("No hazards")
            none.setObjectName("dim")
            none.setFont(THEME.font(15))
            self.alert_box.addWidget(none)
            return
        for a in active:
            band = a.get("distance_band")
            colour = THEME.color(BAND_STATUS.get(band, "inactive")).name()
            row = QLabel(f"{str(a.get('class', '?')).capitalize()}   {BAND_TEXT.get(band, band or '')}")
            row.setFont(THEME.font(16, QFont.Weight.Bold))
            row.setStyleSheet(f"color: #000; background: {colour}; border-radius: 8px; padding: 8px 10px;")
            self.alert_box.addWidget(row)

    def _render_alert_rows(self, active):
        """64 px rows, nearest band first; the top one filled red or amber when immediate or warning."""
        if not active:
            none = QLabel("No hazards")
            none.setObjectName("dim")
            none.setFont(THEME.font(20))
            none.setAlignment(Qt.AlignmentFlag.AlignCenter)
            none.setMinimumHeight(64)
            self.alert_box.addWidget(none)
            return
        ordered = sorted(active, key=lambda a: BAND_ORDER.get(a.get("distance_band"), 3))
        for n, a in enumerate(ordered[:6]):
            band = a.get("distance_band")
            status = BAND_STATUS.get(band, "inactive")
            detail = " · ".join(t for t in (BAND_TEXT.get(band, band or ""), BAND_RANGE.get(band, "")) if t)
            conf = a.get("confidence")
            note = f"{conf * 100:.0f} %" if isinstance(conf, (int, float)) and not isinstance(conf, bool) else ""
            self.alert_box.addWidget(AlertRow(status, str(a.get("class", "?")).capitalize(), detail, note,
                                              filled=(n == 0 and status in FILLED)))
        if len(ordered) > 6:
            more = QLabel(f"+{len(ordered) - 6} more")
            more.setObjectName("dim")
            more.setFont(THEME.font(16))
            self.alert_box.addWidget(more)

    def update_state(self, state):
        """Vehicle telemetry is not needed here; the camera feeds this page."""
        pass
