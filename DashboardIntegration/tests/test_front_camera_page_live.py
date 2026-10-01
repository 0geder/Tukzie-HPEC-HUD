"""Front camera page against the live detector on the Pi (offscreen).
The detector runs for about 45 s; the page runs 60 s, so the last part
also checks the page's behaviour when the camera goes away."""
import os, sys, time
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = "C:/Windows/Fonts"
os.environ["TUKZIE_CAMERA_URL"] = sys.argv[1] if len(sys.argv) > 1 else "http://10.74.67.244:8080"
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from app.pages.front_camera_page import FrontCameraPage
from app.theme import THEME

page = FrontCameraPage(); page.setStyleSheet(THEME.stylesheet()); page.resize(1280, 640); page.show()
t0 = time.monotonic()
frames, alerts_seen, status_log = [], [], []
orig_feed = page._feed
def feed(data):
    before = page._pixmap
    orig_feed(data)
    if page._pixmap is not before:
        frames.append(time.monotonic() - t0)
page._feed = feed
page.alerts_changed.connect(lambda a: alerts_seen.append((round(time.monotonic() - t0, 1), [(x.get("class"), x.get("distance_band")) for x in a])))
last = [None]
def poll_status():
    s = page.status_label.text()
    if s != last[0]:
        status_log.append((round(time.monotonic() - t0, 1), s)); last[0] = s
st = QTimer(); st.timeout.connect(poll_status); st.start(200)
QTimer.singleShot(20000, lambda: page.grab().save("page_live_real.png"))
QTimer.singleShot(58000, lambda: page.grab().save("page_after_camera_stops.png"))
QTimer.singleShot(60000, app.quit)
app.exec()

live = [t for t in frames if t < 45]
print("frames decoded: %d in total; %d in the first 45 s (%.1f per second)" % (len(frames), len(live), len(live) / 45))
gaps = [b - a for a, b in zip(frames, frames[1:])]
if gaps:
    print("longest gap between decoded frames while live: %.2f s" % max(g for a, g in zip(frames, gaps) if a < 40))
print("status changes:", status_log)
print("alert changes:", alerts_seen[:12])
print("metrics text at the end:", page.metrics_label.text().replace("\n", " | "))
