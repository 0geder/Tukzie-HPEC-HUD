"""SW-7: finger-drag scrolling for every scrollable area of the dashboard.

The team's pages use QScrollArea and QListWidget, which on the Pi 5 touchscreen only scroll with a scrollbar or a
mouse wheel; a finger drag did nothing (Diagnostics, Charging, the destination suggestions; reported 11 Oct). This
gives each one kinetic touch scrolling, as was already done for Settings and Sensors, with taps still acting at
once (no press delay). Areas that already have a scroller are left alone.
"""
from PySide6.QtWidgets import QAbstractScrollArea, QScroller, QScrollerProperties


def enable_touch_scroll(area):
    viewport = area.viewport()
    if viewport is None or QScroller.hasScroller(viewport):
        return False
    QScroller.grabGesture(viewport, QScroller.ScrollerGestureType.LeftMouseButtonGesture)
    scroller = QScroller.scroller(viewport)
    props = scroller.scrollerProperties()
    props.setScrollMetric(QScrollerProperties.ScrollMetric.MousePressEventDelay, 0.0)   # taps act at once
    props.setScrollMetric(QScrollerProperties.ScrollMetric.OvershootDragResistanceFactor, 0.3)
    props.setScrollMetric(QScrollerProperties.ScrollMetric.OvershootScrollDistanceFactor, 0.05)
    scroller.setScrollerProperties(props)
    return True


def enable_all(root):
    """Touch scrolling for every scroll area under root; returns how many were enabled."""
    return sum(1 for area in root.findChildren(QAbstractScrollArea) if enable_touch_scroll(area))
