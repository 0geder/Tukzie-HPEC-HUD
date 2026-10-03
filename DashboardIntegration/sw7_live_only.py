"""
SW-7 live-only mode for the TUKZIE dashboard.

With the environment variable TUKZIE_LIVE_ONLY=1 the dashboard never shows
simulated values. VehicleStateManager (patched, see tests/dashboard_patches.py)
does not run the simulation; until live telemetry arrives, and whenever it
stops, it publishes the explicit "no data" state built here: every
sensor-derived field is None and every entry of signal_validity is False, so
the pages show "--" or "Unavailable". The driver inputs (gear, indicator,
headlights, parking brake) still come from the keyboard and controller,
through the manager's simulation state object, which is only used as a store
for those inputs.

LiveDataProvider builds its live states on top of the same blank state, so a
field that has no live source is None in live mode too, never a default.

Drop this file into app/data/. Plain Python, no Qt.
"""
from __future__ import annotations

import copy
import os

from .vehicle_state import Severity, VehicleState, Warning

NO_DATA_MODE = "no_data"        # VehicleStateManager.mode while there is no live data
NO_DATA_SOURCE = "no_data"      # VehicleState.data_source of the blank state

# Set by the keyboard and the controller, so kept in live-only mode.
DRIVER_INPUT_FIELDS = ("gear", "indicator", "headlights", "parking_brake")

# Every VehicleState field that a sensor or a model of sensor data would fill.
UNKNOWN_FIELDS = (
    "speed_kmh", "throttle_pct", "brake_pct", "power_pct", "acceleration_mps2",
    "soc_pct", "range_km", "consumption_wh_km", "battery_power_kw", "signed_battery_power_kw",
    "battery_temp_c", "motor_temp_c", "battery_soh_pct",
    "ambient_temp_c", "weather_condition", "rain_pct", "wet_road_estimate", "road_surface",
    "road_grade_pct", "current_road_name", "passenger_count", "cargo_mass_kg",
    "total_estimated_mass_kg",
    "odometer_km", "trip_km", "incline_deg",
    "latitude", "longitude", "heading", "altitude_m", "gps_accuracy_m", "gps_timestamp",
    "route_progress",
    "front_obstacle_distance_m", "rear_obstacle_distance_m", "obstacle_closing_rate_mps",
    "reverse_distance_m", "reverse_angle_deg",
    "charging_source", "charging_voltage_v", "charging_current_a", "charging_power_kw",
    "door_closed", "seatbelt_fastened", "tyre_front_kpa", "tyre_rear_left_kpa", "tyre_rear_right_kpa",
    "source_freshness_s",
)

SIGNALS = ("speed", "soc", "battery_temp", "gps", "front_obstacle", "rear_obstacle",
           "weather", "road_surface", "door", "seatbelt", "tyres")


def live_only_enabled() -> bool:
    """True when TUKZIE_LIVE_ONLY=1 (read at call time)."""
    return os.environ.get("TUKZIE_LIVE_ONLY", "").strip() == "1"


def _blank_warnings():
    # Same keys as data_provider._default_warnings(), without the made-up temperatures.
    return [
        Warning("motor_temp", "MOTOR", Severity.OK, value=""),
        Warning("batt_temp", "BATTERY", Severity.OK, value=""),
        Warning("door", "DOOR", Severity.OK),
        Warning("seatbelt", "BELT", Severity.WARN, active=False),
        Warning("park_brake", "P-BRAKE", Severity.INFO, active=True),
        Warning("tyre", "TYRES", Severity.OK),
    ]


def no_data_state(driver_inputs=None) -> VehicleState:
    """A new VehicleState with no sensor values: all of UNKNOWN_FIELDS None,
    all signals invalid, not charging, not simulated. driver_inputs: a
    VehicleState (normally the manager's sim state) to copy the gear,
    indicator, headlights and parking brake from."""
    s = VehicleState(warnings=_blank_warnings())
    for name in UNKNOWN_FIELDS:
        setattr(s, name, None)
    if driver_inputs is not None:
        for name in DRIVER_INPUT_FIELDS:
            setattr(s, name, copy.copy(getattr(driver_inputs, name)))
    pb = s.warning("park_brake")
    if pb:
        pb.active = bool(s.parking_brake)
    s.charging = False
    s.charging_telemetry_source = "unavailable"
    s.weather_source = "unknown"
    s.controller_connected = False
    s.data_source = NO_DATA_SOURCE
    s.is_simulated = False
    s.telemetry_timestamp = 0.0          # ASIS reads 0 as "no telemetry" (stale)
    s.signal_validity = {name: False for name in SIGNALS}
    return s
