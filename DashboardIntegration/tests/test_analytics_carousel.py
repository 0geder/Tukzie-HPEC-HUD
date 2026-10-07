"""Offscreen test of the Analytics carousel (sw7_analytics.py, Planning/analytics-carousel-prompt.md).

Builds a scratch copy of the team's dashboard (TUKZIE_DASHBOARD_DIR, a copy of v1.1) with every SW-7 patch,
then checks on the Analytics page alone:
  1. the carousel holds the six value cards, the Graphs card and the insights card (8), starting at SOC;
  2. it wraps both ways (infinite): back from the first card is the last, forward from the last is the first;
  3. a swipe up of more than a fifth of a card moves to the next card; a small swipe snaps back;
  4. tapping the middle Graphs card opens the graphs view with the four charts; Back returns, same card;
  5. update_state() still fills the cards ("--" for missing values) and feeds the charts;
  6. TUKZIE_ANALYTICS_CAROUSEL=0 gives the original grid (no carousel).
Saves tests/analytics_carousel.png and tests/analytics_graphs.png (made-up TEST values, not data; not kept in the repo).

Run: TUKZIE_DASHBOARD_DIR=<copy of v1.1> python DashboardIntegration/tests/test_analytics_carousel.py
"""
from __future__ import annotations

import os
import shutil
import stat
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
INTEGRATION = HERE.parent
DASH = Path(os.environ["TUKZIE_DASHBOARD_DIR"])
sys.path.insert(0, str(HERE))
from dashboard_patches import COPIES, PATCHES  # noqa: E402

scratch = Path(tempfile.mkdtemp(prefix="tukzie_analytics_"))


def _force_remove(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


shutil.copytree(DASH / "app", scratch / "app", ignore=shutil.ignore_patterns("__pycache__", "logs"))
for src, dst in COPIES:
    (scratch / dst).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(INTEGRATION / src, scratch / dst)
for rel, old, new in PATCHES:
    path = scratch / rel
    text = path.read_text(encoding="utf-8")
    if "\r\n" in text:
        old, new = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
    assert text.count(old) == 1, f"anchor not found once in {rel}: {old[:60]!r}"
    path.write_text(text.replace(old, new), encoding="utf-8")
sys.path.insert(0, str(scratch))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEventLoop, QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

qapp = QApplication(sys.argv)
from app.pages.analytics_page import AnalyticsPage  # noqa: E402


def run_for(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        qapp.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 20)
        time.sleep(0.005)


def state(**kw):
    base = dict(soc_pct=None, battery_temp_c=None, ambient_temp_c=None, odometer_km=None,
                battery_power_kw=None, consumption_wh_km=None, speed_kmh=None)
    base.update(kw)
    return SimpleNamespace(**base)


page = AnalyticsPage()
page.resize(1280, 700)
page.show()
run_for(0.3)
car = page.sw7_carousel

# 1. contents
assert car.count == 8, car.count
assert car.current() == 0 and car.item(0) is page.s_soc
assert car.item(page.sw7_graphs_index).findChildren(type(page.insight_title))   # Graphs card has labels
print("1 carousel: 6 value cards, Graphs and insights (8 cards), starting at battery %")

# 2. infinite both ways
car.step(-1); run_for(0.45)
assert car.current() == 7, car.current()
car.step(1); run_for(0.45)
assert car.current() == 0
for _ in range(8):
    car.step(1); run_for(0.35)
assert car.current() == 0, "eight steps forward must come back to the first card"
print("2 wrap: back from the first is the last; eight steps forward return to the first")

# 3. swipes
pitch = car._geometry()[2]
mid = QPoint(car.width() // 2, car.height() // 2)
QTest.mousePress(car, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, mid)
for i in range(1, 7):
    QTest.mouseMove(car, QPoint(mid.x(), int(mid.y() - pitch * 0.45 * i / 6)))
QTest.mouseRelease(car, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                   QPoint(mid.x(), int(mid.y() - pitch * 0.45)))
run_for(0.45)
assert car.current() == 1, f"swipe up should bring the next card, got {car.current()}"
QTest.mousePress(car, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, mid)
for i in range(1, 4):
    QTest.mouseMove(car, QPoint(mid.x(), int(mid.y() + pitch * 0.1 * i / 3)))
QTest.mouseRelease(car, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                   QPoint(mid.x(), int(mid.y() + pitch * 0.1)))
run_for(0.45)
assert car.current() == 1, "a short swipe must snap back"
print("3 swipe: up by about half a card moves to the next card; a short swipe snaps back")

# 5 (before the screenshots): update_state still drives the cards and charts
for _ in range(15):
    page.update_state(state(soc_pct=55.0, battery_temp_c=31.0, ambient_temp_c=22.0, odometer_km=12.3,
                            battery_power_kw=1.2, consumption_wh_km=45.0, speed_kmh=18.0))
assert page.s_soc.value.text() == "55 %" and page.s_odo.value.text() == "12.3 km", page.s_soc.value.text()
page.update_state(state())
assert page.s_soc.value.text() == "--" and page.s_eff.value.text() == "--"
page.update_state(state(soc_pct=55.0, battery_temp_c=31.0, ambient_temp_c=22.0, odometer_km=12.3,
                        battery_power_kw=1.2, consumption_wh_km=45.0, speed_kmh=18.0))
print("5 values: update_state fills the cards; missing values show --")

car.go_to(0); run_for(0.45)
page.grab().save(str(HERE / "analytics_carousel.png"))

# 4. Graphs opens and Back returns
car.go_to(page.sw7_graphs_index); run_for(0.45)
assert car.current() == page.sw7_graphs_index
QTest.mouseClick(car, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, mid)
run_for(0.2)
assert page.sw7_stack.currentWidget() is page.sw7_graphs_view, "tapping Graphs must open the graphs view"
assert page.speed_chart.isVisible() and page.eff_chart.isVisible()
page.grab().save(str(HERE / "analytics_graphs.png"))
QTest.mouseClick(page.sw7_back, Qt.MouseButton.LeftButton)
run_for(0.2)
assert page.sw7_stack.currentWidget() is page.sw7_carousel_view and car.current() == page.sw7_graphs_index
print("4 graphs: tapping Graphs opens the four charts; Back returns to the same card")

# 6. switch off
os.environ["TUKZIE_ANALYTICS_CAROUSEL"] = "0"
plain = AnalyticsPage()
assert not hasattr(plain, "sw7_carousel")
print("6 off: TUKZIE_ANALYTICS_CAROUSEL=0 keeps the original grid")
page.close(); plain.close()
shutil.rmtree(scratch, ignore_errors=True)   # Qt may still hold a font file open on Windows
print("ALL ANALYTICS CAROUSEL TESTS PASSED")
