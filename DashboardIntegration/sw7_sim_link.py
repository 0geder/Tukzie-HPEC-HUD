"""SW-7: the map's simulated drive in step across every dashboard page, clearly apart from live data.

While the map runs a simulated drive (sw7_tile_map.SW7TileMap.start_simulation), dashboard_main's dispatcher
(_on_vehicle_state) is given one simulated vehicle state instead of the live one, so every page moves together:
position, heading, speed and route progress from the map; power, battery drain, consumption, range,
temperatures, trip and odometer from an energy model; gear D while moving. ToF obstacles, camera hazards,
weather and the Sensors page stay live. The live state is never modified, so ending the simulation, or a real
GNSS fix (which stops it), returns every page to live data at once; Analytics chart points gathered during the
simulation are removed then. Planning/simulated-drive-sync-prompt.md.

The data source is always visible: a chip in the status bar (LIVE, REPLAY, NO DATA or SIMULATED) and, during a
simulated drive, a yellow strip under the status bar on every page.
"""
import copy
import math
import time
from collections import deque

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QLabel

try:
    from ..theme import THEME
    from ..data.vehicle_state import Gear
    from ..asis.config import DEFAULTS, VEHICLE_SPEC
    from ..asis.physics import estimate_remaining_range_km
except ImportError:          # outside the app package (unit use)
    THEME = Gear = DEFAULTS = VEHICLE_SPEC = estimate_remaining_range_km = None

SIM_SOURCE = "sw7_simulated_drive"
STRIP_TEXT = "SIMULATED DRIVE · not live data · battery, range and speed are simulated, obstacles are live"
# Starting values when the live state has none (BMS never reported); stated, not hidden.
DEFAULT_SOC_PCT, DEFAULT_BATT_C, DEFAULT_MOTOR_C, DEFAULT_ODO_KM = 80.0, 28.0, 35.0, 0.0
RATED_INPUT_KW = 2.5          # motor plate: 72 V x 35 A (Introduction)
CHARTS = ("speed_chart", "soc_chart", "dist_chart", "eff_chart")
CHIPS = {                     # data source -> (text, status colour key)
    "sw7_telemetry": ("LIVE", "normal"),
    "sw7_replay": ("REPLAY", "warn"),
    "no_data": ("NO DATA", "inactive"),
    SIM_SOURCE: ("SIMULATED", "warn"),
}


def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _colour(key, fallback):
    try:
        return THEME.status(key).name()
    except Exception:
        return fallback


class SimDrive:
    """The simulated vehicle while the map simulates. Distance comes from the map, so trip, odometer and
    battery agree with how far the marker has moved."""

    def __init__(self):
        self.active = False
        self._charts = {}

    def begin(self, main, live):
        self.active = True
        valid = dict(getattr(live, "signal_validity", None) or {})
        soc = _num(getattr(live, "soc_pct", None)) if valid.get("soc") else None
        self.soc_seeded = soc is None
        self.soc0 = soc if soc is not None else DEFAULT_SOC_PCT
        btemp = _num(getattr(live, "battery_temp_c", None)) if valid.get("battery_temp") else None
        self.batt_c = btemp if btemp is not None else DEFAULT_BATT_C
        self.motor_c = DEFAULT_MOTOR_C
        self.odo0 = _num(getattr(live, "odometer_km", None)) or DEFAULT_ODO_KM
        self.trip0 = _num(getattr(live, "trip_km", None)) or 0.0
        self.energy_wh = 0.0
        self.last_km = 0.0
        self.last_t = time.monotonic()
        analytics = getattr(main, "analytics", None)
        self._charts = {}
        for name in CHARTS:
            chart = getattr(analytics, name, None)
            data = getattr(chart, "_data", None)
            if data is not None:
                self._charts[name] = list(data)

    def end(self, main):
        """Remove what the simulation added to the Analytics charts."""
        self.active = False
        analytics = getattr(main, "analytics", None)
        for name, saved in self._charts.items():
            chart = getattr(analytics, name, None)
            if chart is not None and getattr(chart, "_data", None) is not None:
                chart._data = deque(saved, maxlen=chart._data.maxlen)
                chart.update()
        self._charts = {}

    def state(self, live, m):
        now = time.monotonic()
        dt = max(0.0, min(2.0, now - self.last_t))
        self.last_t = now
        from .sw7_tile_map import SIM_KMH
        arrived = bool(getattr(m, "sim_arrived", False))
        speed = 0.0 if arrived else float(SIM_KMH)
        km = max(0.0, float(getattr(m, "_sim_m", 0.0) or 0.0) / 1000.0)
        throttle = 0.0 if arrived else 30.0 + speed * 0.4
        consumption = round(40 + speed * .6 + throttle * .15, 1)        # team simulator's model, Wh/km
        self.energy_wh += consumption * max(0.0, km - self.last_km)
        self.last_km = km
        capacity_wh = getattr(VEHICLE_SPEC, "battery_capacity_wh", None) or 7200.0
        soc = max(0.0, self.soc0 - self.energy_wh / capacity_wh * 100.0)
        kw = 0.0 if arrived else consumption * speed / 1000.0
        power_pct = min(100.0, kw / RATED_INPUT_KW * 100.0)
        k = min(1.0, dt * .4)
        self.motor_c += (35 + throttle * .45 - self.motor_c) * k        # team simulator's targets
        self.batt_c += (28 + abs(power_pct) * .12 - self.batt_c) * min(1.0, dt * .2)

        s = copy.copy(live)
        s.speed_kmh = speed
        s.acceleration_mps2 = 0.0
        s.throttle_pct, s.brake_pct = throttle, 0.0
        s.power_pct = power_pct
        s.signed_battery_power_kw = round(kw, 2)
        s.battery_power_kw = round(kw, 2)
        s.soc_pct = soc
        s.consumption_wh_km = consumption
        s.battery_temp_c = round(self.batt_c, 1)
        s.motor_temp_c = round(self.motor_c, 1)
        s.trip_km = self.trip0 + km
        s.odometer_km = self.odo0 + km
        if Gear is not None:
            s.gear = Gear.P if arrived else Gear.D
        s.parking_brake = arrived
        s.charging = False
        pos = getattr(m, "vehicle", None)
        if pos:
            s.latitude, s.longitude = pos
        s.heading = getattr(m, "heading", None)
        s.route_progress = getattr(m, "progress", None)
        s.gps_timestamp = time.time()
        if estimate_remaining_range_km is not None:
            try:
                s.range_km = estimate_remaining_range_km(VEHICLE_SPEC, s, DEFAULTS)
            except Exception:
                pass
        validity = dict(getattr(live, "signal_validity", None) or {})
        validity.update({"speed": True, "soc": True, "battery_temp": True, "gps": True,
                         "heading": s.heading is not None})
        s.signal_validity = validity
        s.data_source = SIM_SOURCE
        s.is_simulated = True
        s.sw7_simulated = True
        s.sw7_soc_seeded = self.soc_seeded
        return s


class _Indicators(QObject):
    """The status-bar chip and the simulated-drive strip, kept in place on resize."""

    def __init__(self, main):
        super().__init__(main)
        self.main = main
        status = getattr(main, "status", None)
        self.chip = QLabel("", status if status is not None else main)
        self.chip.setObjectName("sw7SourceChip")
        self.chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.chip.hide()
        self.strip = QLabel(STRIP_TEXT, main)
        self.strip.setObjectName("sw7SimStrip")
        self.strip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.strip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.strip.setStyleSheet(f"QLabel#sw7SimStrip {{ background: {_colour('warn', '#FFB224')}; color: #0B0D10;"
                                 " font-weight: 700; font-size: 14px; padding: 3px 10px; }")
        self.strip.setFixedHeight(26)
        self.strip.hide()
        # In the dashboard's own layout, under the status bar, so the pages move down while it shows instead of
        # being covered; it takes no space when hidden. Overlay only if the layout is not the expected one.
        self.in_layout = False
        holder = status.parentWidget() if status is not None else None
        layout = holder.layout() if holder is not None else None
        if layout is not None and layout.indexOf(status) >= 0:
            layout.insertWidget(layout.indexOf(status) + 1, self.strip)
            self.in_layout = True
        main.installEventFilter(self)
        if status is not None:
            status.installEventFilter(self)
        self.source = None

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.place()
        return False

    def place(self):
        status = getattr(self.main, "status", None)
        if status is not None:
            self.chip.adjustSize()
            self.chip.move(max(0, status.width() // 2 - 70 - self.chip.width()), max(0, (status.height() - self.chip.height()) // 2))
            top = status.geometry().bottom() + 1
        else:
            top = 0
        if not self.in_layout:
            self.strip.setGeometry(0, top, self.main.width(), 26)
            self.strip.raise_()

    def show_source(self, source):
        text, key = CHIPS.get(source, ("", None))
        if source != self.source:
            self.source = source
            if not text:
                self.chip.hide()
            else:
                self.chip.setText(text)
                bg = _colour(key, "#5A6270")
                fg = "#0B0D10" if key in ("normal", "warn") else "#FFFFFF"
                self.chip.setStyleSheet(f"QLabel#sw7SourceChip {{ background: {bg}; color: {fg}; border-radius: 8px;"
                                        " padding: 2px 10px; font-weight: 700; font-size: 12px; }")
                self.chip.show()
        self.strip.setVisible(source == SIM_SOURCE)
        self.place()


def sim_view(main, live):
    """The state every page should show: the live state, or a simulated one during a simulated drive."""
    if live is None:
        return live
    sim = getattr(main, "_sw7_sim", None)
    if sim is None:
        sim = main._sw7_sim = SimDrive()
    marks = getattr(main, "_sw7_marks", None)
    if marks is None:
        marks = main._sw7_marks = _Indicators(main)
    m = getattr(getattr(main, "navigation", None), "map", None)
    simulating = bool(getattr(m, "simulating", False)) and getattr(m, "vehicle", None) is not None
    if simulating and not sim.active:
        sim.begin(main, live)
    elif not simulating and sim.active:
        sim.end(main)
    shown = sim.state(live, m) if simulating else live
    marks.show_source(getattr(shown, "data_source", None))
    return shown


def refresh(main):
    """Re-dispatch now (each simulated-drive step, and when it ends): in live-only mode no new vehicle state
    arrives while the Pi 4 link is down, so the pages would otherwise not move."""
    live = getattr(main, "_sw7_live_state", None)
    if live is None:
        live = getattr(getattr(main, "vehicle_data", None), "state", None)
    handler = getattr(main, "_on_vehicle_state", None)
    if live is not None and handler is not None:
        try:
            handler(live)
        except Exception as exc:          # a page error must not stop the simulation
            print(f"[SW-7] simulated drive: page update failed: {exc}")


def connect(main):
    m = getattr(getattr(main, "navigation", None), "map", None)
    if m is not None and hasattr(m, "sim_tick"):      # the team's own map has no simulated drive
        m.sim_tick.connect(lambda: refresh(main))
