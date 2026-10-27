"""
LiveDataProvider: SW-7 telemetry from the Pi 4 bridge into the TUKZIE dashboard.

Polls GET <bridge_url>/telemetry twice a second (TELEMETRY_LINK.md, section 2),
turns each answer into a VehicleState and hands it to
VehicleStateManager.ingest_live_state(). The bridge address comes from the
TUKZIE_TELEMETRY_URL environment variable if set; otherwise the shared Pi 4
resolver (sw7_endpoints.py, TELEMETRY_LINK.md section 4.3) finds it, and this
provider reports every poll to it so it searches again after 3 failures.
endpoint_changed(host, how) passes on where the Pi 4 was found.

ingest_live_state() replaces the dashboard state as a whole (it does not
merge), so every ingest is a complete VehicleState: the mapped fields below,
the driver inputs (gear, indicator, headlights, parking brake) copied from the
manager's simulation state so the keyboard and controller keep working, and
the dataclass defaults for everything else, with signal_validity marking which
signals are real. In live-only mode (TUKZIE_LIVE_ONLY=1, sw7_live_only.py) the
base is the blank no-data state instead, so every field without a live source
is None rather than a default.

State of charge: the last BMS value is kept (marked invalid) when soc goes
null; if the BMS has never reported, soc_pct is None, never the dataclass
default of 82 %.

Mapping (TELEMETRY_LINK.md, section 3):
  esp32.soc                    -> soc_pct            (validity "soc")
  esp32.v * esp32.i / 1000     -> signed_battery_power_kw, battery_power_kw = max(0, kW)
  esp32.lat, esp32.lon         -> latitude, longitude, gps_timestamp (only when fix)
  esp32.fix                    -> signal_validity["gps"]
  esp32.crs (deg, GNSS course) -> heading, signal_validity["heading"] (only when fix; else None)
  esp32.alt (m)                -> altitude_m (only when fix; else None)
  bridge.replay, or fw ending in "-replay"
                               -> data_source "sw7_replay" instead of "sw7_telemetry", so the
                                  pages (map REPLAY badge, Diagnostics source) can never take
                                  replayed positions for real data
  tof ahead (mm)               -> front_obstacle_distance_m, in m (ahead only: a side reading
                                  must not raise a front-obstacle warning when passing parked cars)
  esp32.spd_raw                -> not mapped (units unconfirmed); speed stays 0, "speed" invalid
  phone GPS (phone_gps_bridge.py on the Pi 5, GET <TUKZIE_PHONE_GPS_URL>/gps, default
  http://127.0.0.1:8084; 23 Oct 2026), used only while its last RMC is under 3000 ms old with a fix:
    speed_kmh                  -> speed_kmh, signal_validity["speed"] (the only live speed source)
    lat, lon, course, alt      -> latitude, longitude, heading, altitude_m, only while the vehicle's
                                  own GNSS has no fix (its own fix always wins); heading only above
                                  3 km/h, where the phone's course is meaningful
  sw7_position_source records which one is shown: "vehicle", "phone" or None.

Phone only (24 Oct 2026): the phone bridge runs on the Pi 5, so it does not depend on the Pi 4.
When the bridge cannot be reached, the reply is not JSON, esp32 is null, or esp32.age_ms is
missing or above 3000, but the phone has a fresh fix, a state is still built from the phone
alone: speed, and position, heading and altitude as above (the vehicle has no fix then). Every
ESP32 field is absent: soc_pct and the battery power None (not the last known value), cell
position None, validity "soc" False; sw7_rear_live is False (True when the ESP32 record is
fresh). A ToF reading is used only if its own age is under 3000 ms, as before; the Pi 5 front
ToF (dual) does not depend on the Pi 4 either. So a Pi 4 restart no longer blanks the
speedometer. link_changed still reports the Pi 4 link ("stale" or "offline").

Nothing is ingested when the ESP32 record is stale (as above) and the phone has no fresh fix
either. The dashboard's own 2500 ms watchdog then returns it to simulation, or in live-only
mode to the explicit no-data state.

Every poll emits telemetry_updated(dict) with the raw bridge JSON, or
telemetry_updated(None) when the bridge is unreachable, for the ride quality
card. link_changed(str) reports "live", "stale" or "offline" when it changes.

Drop this file into app/data/ and wire it up as described in
DashboardIntegration/README.md. It uses QtNetwork only.
"""
from __future__ import annotations

import copy
import json
import math
import os
import time

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from .vehicle_state import VehicleState
from .sw7_live_only import DRIVER_INPUT_FIELDS, live_only_enabled, no_data_state

try:
    from .data_provider import _default_warnings
except ImportError:            # keep working if the dashboard renames it
    _default_warnings = None

# Fixed bridge address; None (the default) means: use the Pi 4 resolver.
TELEMETRY_URL = (os.environ.get("TUKZIE_TELEMETRY_URL", "").strip().rstrip("/") or None)

POLL_MS = 500
REQUEST_TIMEOUT_MS = 2000
ESP32_STALE_MS = 3000          # contract: stop sending above this age
TOF_STALE_MS = 3000
PHONE_GPS_URL = (os.environ.get("TUKZIE_PHONE_GPS_URL", "").strip().rstrip("/") or "http://127.0.0.1:8084")
PHONE_GPS_STALE_MS = 3000
PHONE_HEADING_MIN_KMH = 3.0    # below this a phone's course over ground is noise
SOURCE = "sw7_telemetry"
REPLAY_SOURCE = "sw7_replay"      # data_source while the bridge replays a file

# Driver inputs that the dashboard itself owns (keyboard, controller), in
# DRIVER_INPUT_FIELDS, are carried over from the manager's simulation state
# into each live state.


def _num(value):
    """float(value), or None for null, NaN, infinities, bools and non-numbers."""
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def esp32_is_fresh(telemetry) -> bool:
    """True when the bridge reply carries an ESP32 record no older than 3000 ms."""
    if not isinstance(telemetry, dict):
        return False
    esp = telemetry.get("esp32")
    if not isinstance(esp, dict):
        return False
    age = _num(esp.get("age_ms"))
    return age is not None and age <= ESP32_STALE_MS


def front_tof_m(telemetry):
    """The ahead ToF reading in metres, or None. Side sensors are shown on the ride card only."""
    tof = telemetry.get("tof") if isinstance(telemetry, dict) else None
    if not isinstance(tof, dict):
        return None
    age = _num(tof.get("age_ms"))
    if age is not None and age > TOF_STALE_MS:
        return None
    ahead = _num(tof.get("ahead_mm"))
    return ahead / 1000.0 if ahead is not None and ahead > 0 else None


def phone_gps_fix(phone):
    """The phone bridge's /gps reply when it is fresh and has a fix, else None."""
    if not isinstance(phone, dict) or phone.get("fix") is not True:
        return None
    age = _num(phone.get("age_ms"))
    if age is None or age > PHONE_GPS_STALE_MS:
        return None
    if _num(phone.get("lat")) is None or _num(phone.get("lon")) is None:
        return None
    return phone


def is_replay(telemetry) -> bool:
    """True when the bridge says it is replaying a file (bridge.replay), or the
    ESP32 record is marked as replayed (fw ending in "-replay")."""
    if not isinstance(telemetry, dict):
        return False
    bridge = telemetry.get("bridge")
    if isinstance(bridge, dict) and bridge.get("replay") is True:
        return True
    esp = telemetry.get("esp32")
    return isinstance(esp, dict) and str(esp.get("fw") or "").endswith("-replay")


KNOTS_TO_KMH = 1.852
SPEED_AGREE_KMH = 3.0      # two speeds agree when within 3 km/h or 25 % of the larger
SPEED_AGREE_FRAC = 0.25


def fuse_speed(phone_kmh, vehicle_kmh):
    """Dashboard speed from the phone and the vehicle GNSS (27 Oct 2026). Both: their mean when they agree (within
    3 km/h or 25 %), else the phone's, the one checked against video; one: that one; none: None.
    Returns (km/h or None, source: "fused", "phone (sources disagree)", "phone", "vehicle" or None)."""
    p = max(0.0, phone_kmh) if phone_kmh is not None else None
    v = max(0.0, vehicle_kmh) if vehicle_kmh is not None else None
    if p is not None and v is not None:
        if abs(p - v) <= max(SPEED_AGREE_KMH, SPEED_AGREE_FRAC * max(p, v)):
            return (p + v) / 2.0, "fused"
        return p, "phone (sources disagree)"
    if p is not None:
        return p, "phone"
    if v is not None:
        return v, "vehicle"
    return None, None


def build_live_state(telemetry, driver_inputs=None, previous=None, live_only=None, dual=False, front_telemetry=None,
                     phone_gps=None):
    """Map one /telemetry reply onto a new VehicleState.

    driver_inputs: a VehicleState (normally the manager's sim state) to copy
    DRIVER_INPUT_FIELDS from. previous: the last state this provider built,
    used to keep the last known state of charge when soc goes null.
    live_only: build on the blank no-data state (default: TUKZIE_LIVE_ONLY).
    dual: two-camera layout (sw7_dual_camera, 15 Oct 2026). The Pi 4 bridge is then at the rear, so its
    straight-on ToF reading is the rear obstacle, and the front obstacle comes from front_telemetry (the
    Pi 5's own ToF bridge reply, or None when it has not answered).
    phone_gps: the phone bridge's /gps reply (or None); gives speed, and position when the vehicle has no fix.
    telemetry may be None (the Pi 4 bridge unreachable).
    Returns None when the ESP32 part is missing or stale and the phone has no fresh fix either. With a
    stale ESP32 and a fresh phone fix the state comes from the phone alone, every ESP32 field absent."""
    rear_live = esp32_is_fresh(telemetry)
    phone = phone_gps_fix(phone_gps)
    if not rear_live and phone is None:
        return None
    if live_only is None:
        live_only = live_only_enabled()
    esp = telemetry["esp32"] if rear_live else {}     # phone only: no ESP32 field is trusted
    if live_only:
        s = no_data_state(driver_inputs)
    else:
        warnings = _default_warnings() if _default_warnings else []
        s = VehicleState(warnings=warnings)
        if driver_inputs is not None:
            for name in DRIVER_INPUT_FIELDS:
                setattr(s, name, copy.copy(getattr(driver_inputs, name)))

    soc = _num(esp.get("soc"))
    if soc is not None:
        s.soc_pct = soc
    elif rear_live and previous is not None and previous.soc_pct is not None:
        s.soc_pct = previous.soc_pct      # last BMS value, marked invalid below
    else:
        s.soc_pct = None                  # BMS has never reported, or the Pi 4 is gone: unknown, not 82 %

    volts, amps = _num(esp.get("v")), _num(esp.get("i"))
    if volts is not None and amps is not None:
        kw = volts * amps / 1000.0
        s.signed_battery_power_kw = kw
        s.battery_power_kw = max(0.0, kw)
    else:
        s.signed_battery_power_kw = None
        s.battery_power_kw = None if live_only else 0.0

    lat, lon = _num(esp.get("lat")), _num(esp.get("lon"))
    gps_ok = esp.get("fix") is True and lat is not None and lon is not None
    if gps_ok:
        s.latitude, s.longitude, s.gps_timestamp = lat, lon, time.time()
    else:
        s.latitude = s.longitude = None
        s.gps_timestamp = None
    # GNSS course over ground and altitude (firmware 0.7.1+), only with a fix. Without them
    # heading is None, not the dataclass default of 0 (north), so the map stays north-up.
    # Cell-tower position (firmware 0.7.3+): the modem's estimate from the towers it hears,
    # sent only without a GNSS fix. Approximate (about 550 m indoors), so it is never put in
    # latitude/longitude: the map draws it as a circle, the way a phone does indoors.
    crs = _num(esp.get("crs")) if gps_ok else None
    alt = _num(esp.get("alt")) if gps_ok else None
    s.sw7_position_source = "vehicle" if gps_ok else None
    s.sw7_rear_live = rear_live
    phone_kmh = _num(phone.get("speed_kmh")) if phone else None
    # 27 Oct 2026: the vehicle's own GNSS speed, in knots per the A76XX manual (not yet confirmed on the road), used
    # only with a vehicle fix in a fresh record. fuse_speed() combines it with the phone's.
    spd_raw = _num(esp.get("spd_raw")) if gps_ok else None
    vehicle_kmh = spd_raw * KNOTS_TO_KMH if spd_raw is not None and spd_raw >= 0 else None
    if phone and not gps_ok:
        s.latitude, s.longitude, s.gps_timestamp = _num(phone["lat"]), _num(phone["lon"]), time.time()
        gps_ok = True
        s.sw7_position_source = "phone"
        crs = _num(phone.get("course_deg")) if (phone_kmh or 0.0) >= PHONE_HEADING_MIN_KMH else None
        alt = _num(phone.get("alt_m"))
    clat, clon, cacc = _num(esp.get("cell_lat")), _num(esp.get("cell_lon")), _num(esp.get("cell_acc_m"))
    s.sw7_cell_position = (clat, clon, cacc) if not gps_ok and clat is not None and clon is not None else None
    s.heading = crs % 360.0 if crs is not None else None
    s.altitude_m = alt
    speed, s.sw7_speed_source = fuse_speed(phone_kmh, vehicle_kmh)
    s.sw7_speed_phone_kmh, s.sw7_speed_vehicle_kmh = phone_kmh, vehicle_kmh
    if speed is not None:
        s.speed_kmh = speed

    if dual:
        front = front_tof_m(front_telemetry) if isinstance(front_telemetry, dict) else None
        rear = front_tof_m(telemetry)        # the rear board's "ahead" sensor looks straight back
    else:
        front, rear = front_tof_m(telemetry), None
    s.front_obstacle_distance_m = front
    if dual:
        s.rear_obstacle_distance_m = rear

    # Without a speed from either source speed_kmh keeps its default of 0 (None in live-only mode).
    s.signal_validity = {
        "speed": speed is not None, "soc": soc is not None, "battery_temp": False,
        "gps": gps_ok, "heading": s.heading is not None, "front_obstacle": front is not None,
        "rear_obstacle": rear is not None, "weather": False, "road_surface": False,
        "door": False, "seatbelt": False, "tyres": False,
    }
    return s


class LiveDataProvider(QObject):
    telemetry_updated = Signal(object)   # raw /telemetry dict, or None when offline
    link_changed = Signal(str)           # "live", "stale" or "offline"
    endpoint_changed = Signal(str, str)  # (Pi 4 host or "", how it was found or "searching")

    def __init__(self, manager, url: str | None = None, parent=None, resolver=None):
        """url: fixed bridge address. Otherwise resolver, else TUKZIE_TELEMETRY_URL,
        else the shared Pi 4 resolver (sw7_endpoints.shared_resolver())."""
        super().__init__(parent)
        self.manager = manager
        fixed = url or (None if resolver is not None else TELEMETRY_URL)
        self._fixed_url = fixed.rstrip("/") if fixed else None
        self.resolver = None
        if self._fixed_url is None:
            if resolver is None:
                from .sw7_endpoints import shared_resolver
                resolver = shared_resolver()
            self.resolver = resolver
            resolver.host_changed.connect(self.endpoint_changed)
        self.link = "offline"
        self.dual = False                # set by sw7_dual_camera: this bridge is then the rear one
        self.front_telemetry = None      # the Pi 5 front ToF reply, fed by sw7_dual_camera
        self.last_telemetry = None
        self.phone_gps = None            # last /gps reply from the phone bridge, or None
        self._phone_gps_at = 0.0         # time.monotonic() when it arrived
        self._gps_reply = None
        self._last_state = None
        self._reply = None
        self._reply_url = None
        self._net = QNetworkAccessManager(self)
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._poll)

    @property
    def url(self):
        """The bridge address in use, or None while the resolver is searching."""
        if self._fixed_url is not None:
            return self._fixed_url
        return self.resolver.telemetry_url()

    def endpoint(self):
        """(host, how) of the bridge in use; how is "TUKZIE_TELEMETRY_URL" for a fixed address."""
        if self._fixed_url is not None:
            return QUrl(self._fixed_url).host(), "TUKZIE_TELEMETRY_URL"
        return (self.resolver.host or "", self.resolver.how)

    def start(self):
        if not self._timer.isActive():
            if self.resolver is not None:
                self.resolver.start()
            self.endpoint_changed.emit(*self.endpoint())
            self._timer.start()
            self._poll()

    def stop(self):
        self._timer.stop()
        reply, self._reply = self._reply, None
        if reply is not None:
            reply.finished.disconnect(self._on_finished)
            reply.abort()
            reply.deleteLater()
        gps, self._gps_reply = self._gps_reply, None
        if gps is not None:
            gps.finished.disconnect(self._on_gps_finished)
            gps.abort()
            gps.deleteLater()

    def _poll_phone_gps(self):
        if self._gps_reply is not None:
            return
        req = QNetworkRequest(QUrl(PHONE_GPS_URL + "/gps"))
        req.setTransferTimeout(REQUEST_TIMEOUT_MS)
        self._gps_reply = self._net.get(req)
        self._gps_reply.finished.connect(self._on_gps_finished)

    def _on_gps_finished(self):
        reply, self._gps_reply = self._gps_reply, None
        if reply is None:
            return
        data = None
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                data = json.loads(bytes(reply.readAll()))
            except (ValueError, UnicodeDecodeError):
                data = None
        reply.deleteLater()
        self.phone_gps = data if isinstance(data, dict) else None
        self._phone_gps_at = time.monotonic()

    def current_phone_gps(self):
        """The last /gps reply with its age_ms grown by the time since it arrived, so a reply that is not
        renewed (the phone bridge hanging) turns stale on its own; None if there is none."""
        gps = self.phone_gps
        if not isinstance(gps, dict):
            return None
        age = _num(gps.get("age_ms"))
        if age is None:
            return gps
        return dict(gps, age_ms=age + (time.monotonic() - self._phone_gps_at) * 1000.0)

    def _poll(self):
        self._poll_phone_gps()
        if self._reply is not None:
            return  # previous poll still in flight
        url = self.url
        if url is None:            # resolver still searching for the Pi 4
            self.apply(None)
            return
        req = QNetworkRequest(QUrl(url + "/telemetry"))
        req.setTransferTimeout(REQUEST_TIMEOUT_MS)
        self._reply_url = url
        self._reply = self._net.get(req)
        self._reply.finished.connect(self._on_finished)

    def _on_finished(self):
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
        data = data if isinstance(data, dict) else None
        # Tell the resolver, unless it has moved to another host meanwhile.
        if self.resolver is not None and self._reply_url == self.resolver.telemetry_url():
            if data is None:
                self.resolver.report_failure()
            else:
                self.resolver.report_success()
        self.apply(data)

    def apply(self, telemetry):
        """Handle one parsed /telemetry reply (None: bridge unreachable). With the Pi 4 stale or unreachable,
        a fresh phone fix still gives a phone-only state (build_live_state); the link reports the Pi 4."""
        self.last_telemetry = telemetry
        sim = getattr(self.manager, "sim", None)
        state = build_live_state(telemetry, sim.state if sim is not None else None, self._last_state,
                                 dual=self.dual, front_telemetry=self.front_telemetry,
                                 phone_gps=self.current_phone_gps())
        if state is not None:
            if state.sw7_rear_live:
                self._last_state = state     # keeps the last BMS value across a Pi 4 outage, as before
            self.manager.ingest_live_state(state, source=REPLAY_SOURCE if is_replay(telemetry) else SOURCE)
        if telemetry is None:
            self._set_link("offline")
        else:
            self._set_link("live" if esp32_is_fresh(telemetry) else "stale")
        self.telemetry_updated.emit(telemetry)

    def _set_link(self, link):
        if link != self.link:
            self.link = link
            self.link_changed.emit(link)
