"""
FrontCameraPage: the SW-7 forward camera inside the TUKZIE dashboard.

Shows the live view from the Raspberry Pi 4 hazard detector
(CameraDetection/hazard_detector.py, run with --preview) and its current
alerts. It talks to the detector over two plain HTTP endpoints:

  GET <camera_url>/stream   MJPEG, the camera image with detections drawn on
  GET <camera_url>/alerts   JSON, {"active": [...], "fps": n, "latency_ms": n}
                            each active alert has class, distance_band,
                            confidence, timestamp, alert_status

The camera address comes from the TUKZIE_CAMERA_URL environment variable,
default http://pi4-camera.local:8080 (the Pi 4's mDNS name).

Drop this file into app/pages/ and wire it up as described in
DashboardIntegration/README.md. It uses only QtNetwork and QtWidgets (no
QtWebEngine), streams video only while the page is on screen, and keeps
only the newest frame, so a slow link drops frames rather than lagging.
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

CAMERA_URL = os.environ.get("TUKZIE_CAMERA_URL", "http://pi4-camera.local:8080").rstrip("/")

# Band -> dashboard status colour key (fixed across every palette).
BAND_STATUS = {"immediate": "crit", "warning": "warn", "monitoring": "normal"}
BAND_TEXT = {"immediate": "Immediate", "warning": "Warning", "monitoring": "Monitoring"}

MAX_BUFFER_BYTES = 2_000_000   # drop the buffer if no complete frame turns up in this much data
ALERT_POLL_MS = 500
RECONNECT_MS = 3000
STALE_MS = 2500                # no new frame for this long: show the image as stale
STREAM_SILENCE_MS = 5000       # no stream bytes for this long: drop the connection and retry


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
        self._render_alerts([])

        self._alert_timer = QTimer(self)
        self._alert_timer.timeout.connect(self._poll_alerts)
        self._alert_timer.start(ALERT_POLL_MS)

        self._stale_timer = QTimer(self)
        self._stale_timer.setSingleShot(True)
        self._stale_timer.timeout.connect(self._mark_stale)

        THEME.changed.connect(lambda *_: self._render_alerts(self._last_alerts))

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
        self._buf = b""
        req = QNetworkRequest(QUrl(CAMERA_URL + "/stream"))
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
        req = QNetworkRequest(QUrl(CAMERA_URL + "/alerts"))
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

    def update_state(self, state):
        """Vehicle telemetry is not needed here; the camera feeds this page."""
        pass
