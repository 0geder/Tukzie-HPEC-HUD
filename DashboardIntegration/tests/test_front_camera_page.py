"""Offscreen test of DashboardIntegration/front_camera_page.py.
Setup: copy the dashboard app package (Tukzie-Vac-Work-2026/Dashboard Team/Dashboard+ASIS/Dashboard+ASIS/app)
into a scratch folder, copy front_camera_page.py into its app/pages/, install PySide6-Essentials,
then run this file from that scratch folder."""
import os, sys, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = "C:/Windows/Fonts"
os.environ["TUKZIE_CAMERA_URL"] = "http://192.0.2.1:9"   # TEST-NET address: never answers
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QTimer, Qt
from PySide6.QtGui import QImage, QPainter, QColor, QFont
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from app.pages.front_camera_page import FrontCameraPage, extract_latest_jpeg

# 1. parser unit checks
def jpeg(colour, w=640, h=480, text=""):
    img = QImage(w, h, QImage.Format.Format_RGB888); img.fill(QColor(colour))
    if text:
        p = QPainter(img); p.setPen(QColor("white")); p.setFont(QFont("Arial", 28)); p.drawText(img.rect(), Qt.AlignmentFlag.AlignCenter, text); p.end()
    ba = QByteArray(); b = QBuffer(ba); b.open(QIODevice.OpenModeFlag.WriteOnly); img.save(b, "JPG"); return bytes(ba)
a, b = jpeg("#224466", text="frame A"), jpeg("#446622", text="frame B")
part = lambda j: b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(j) + j + b"\r\n"
stream = part(a) + part(b)
got, rest = extract_latest_jpeg(stream); assert got == b and rest == b"", "newest frame not chosen"
got, rest = extract_latest_jpeg(stream[: len(part(a)) + 200]); assert got == a and rest.startswith(b"\xff\xd8"), "partial second frame not kept"
got, rest = extract_latest_jpeg(b"junk"); assert got is None and rest == b""
print("parser checks passed")

# 2. page: feed a stream in odd-sized chunks, then apply alerts
from app.theme import THEME
page = FrontCameraPage(); page.setStyleSheet(THEME.stylesheet()); page.resize(1280, 640); page.show()
data = part(a) + part(b)
for i in range(0, len(data), 1777):
    page._feed(data[i:i+1777])
assert page._pixmap is not None and page._pixmap.width() == 640
page._apply_alerts({"active": [
    {"class": "person", "distance_band": "immediate", "confidence": 0.63, "timestamp": "2026-09-28T16:20:00+0200", "alert_status": "active"},
    {"class": "bicycle", "distance_band": "warning", "confidence": 0.55, "timestamp": "2026-09-28T16:20:01+0200", "alert_status": "active"}],
    "fps": 7.0, "latency_ms": 182})
seen = []
page.alerts_changed.connect(seen.append)
page._apply_alerts({"active": [], "fps": 7.1, "latency_ms": 175})
assert seen == [[]], seen
page._apply_alerts({"active": [
    {"class": "person", "distance_band": "immediate", "confidence": 0.63, "timestamp": "x", "alert_status": "active"},
    {"class": "bicycle", "distance_band": "warning", "confidence": 0.55, "timestamp": "y", "alert_status": "active"}],
    "fps": 7.0, "latency_ms": 182})
app.processEvents()
page.grab().save("page_live.png")
page._apply_alerts(None); app.processEvents(); page.grab().save("page_offline.png")
print("page checks passed; status:", page.status_label.text())
# 3. real network path: unreachable camera must not crash or block the UI
QTimer.singleShot(7000, app.quit); app.exec()
print("after 7 s against an unreachable camera, status:", page.status_label.text())
