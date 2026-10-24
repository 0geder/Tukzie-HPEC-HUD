"""Test of phone_gps_bridge.py and the phone GPS path in live_data_provider.py (23 Oct 2026).

1. NMEA: checksums, RMC and GGA parsing (any talker ID), knots to km/h, S and W signs, a void RMC.
2. The bridge end to end: sentences sent over UDP to a running bridge (random ports), bad checksums counted and
   dropped, GET /gps fields and age, the log file holding every good sentence with this machine's time.
3. The provider: build_live_state() with a phone fix gives speed (validity "speed"), and position and heading only
   while the vehicle has no fix; the vehicle's own fix always wins; heading is dropped below 3 km/h; a stale or
   void phone reply changes nothing; no phone gives exactly the old state.
4. Phone only (24 Oct 2026): with the Pi 4's ESP32 record stale, null, or the bridge unreachable, a fresh phone fix
   still gives speed (and position), with the battery and every other ESP32 field absent; the provider ingests it
   while reporting the Pi 4 link as stale or offline. Both stale: nothing at all.
Run: python DashboardIntegration/tests/test_phone_gps.py   (needs PySide6 and the team's dashboard copy, as the
other tests; set TUKZIE_DASHBOARD_DIR to use another copy)
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
INTEGRATION = HERE.parent
REPO = INTEGRATION.parent
sys.path.insert(0, str(INTEGRATION))
import phone_gps_bridge as pg  # noqa: E402


def nmea(body: str) -> str:
    cs = 0
    for ch in body:
        cs ^= ord(ch)
    return f"${body}*{cs:02X}"


# ---- 1. NMEA ---------------------------------------------------------------------------------
RMC = nmea("GPRMC,123519.00,A,3357.5670,S,01827.5910,E,10.8,045.0,231026,,,A")
GGA = nmea("GNGGA,123519.00,3357.5670,S,01827.5910,E,1,12,0.9,85.3,M,32.0,M,,")
VOID = nmea("GNRMC,123520.00,V,,,,,,,231026,,,N")
assert pg.nmea_checksum_ok(RMC) and pg.nmea_checksum_ok(GGA) and pg.nmea_checksum_ok(VOID)
assert not pg.nmea_checksum_ok(RMC[:-2] + "00") and not pg.nmea_checksum_ok("GPRMC,1*00")
k, r = pg.parse_sentence(RMC)
assert k == "RMC" and r["fix"] is True
assert abs(r["lat"] - -(33 + 57.567 / 60)) < 1e-9 and abs(r["lon"] - (18 + 27.591 / 60)) < 1e-9
assert abs(r["speed_kmh"] - 10.8 * 1.852) < 1e-9 and r["course_deg"] == 45.0
k, g = pg.parse_sentence(GGA)
assert k == "GGA" and g["sats"] == 12 and g["hdop"] == 0.9 and g["alt_m"] == 85.3
k, v = pg.parse_sentence(VOID)
assert k == "RMC" and v["fix"] is False and v["lat"] is None and v["speed_kmh"] is None
k, w = pg.parse_sentence(nmea("GPRMC,0,A,4000.0000,N,07400.0000,W,0.0,,231026,,,A"))
assert w["lat"] == 40.0 and w["lon"] == -74.0 and w["speed_kmh"] == 0.0 and w["course_deg"] is None
assert pg.parse_sentence(nmea("GPGSV,3,1,12"))[0] is None
print("1 NMEA: checksums, RMC and GGA, signs, knots to km/h, void fix")


# ---- 2. bridge end to end over UDP ---------------------------------------------------------------
def free_port(kind):
    s = socket.socket(socket.AF_INET, kind)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


log_dir = tempfile.mkdtemp(prefix="sw7_phone_gps_")
state = pg.State(log_dir)
udp_port, http_port = free_port(socket.SOCK_DGRAM), free_port(socket.SOCK_STREAM)
threading.Thread(target=pg.udp_loop, args=(state, udp_port), daemon=True).start()
srv = pg.ThreadingHTTPServer(("127.0.0.1", http_port), pg.make_handler(state))
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.2)


def get_gps():
    with urllib.request.urlopen(f"http://127.0.0.1:{http_port}/gps", timeout=3) as resp:
        return json.loads(resp.read())


first = get_gps()
assert first["fix"] is False and first["age_ms"] is None and first["source"] == "phone"
u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
u.sendto((GGA + "\r\n" + RMC + "\r\n" + RMC[:-2] + "00\r\n").encode(), ("127.0.0.1", udp_port))
for _ in range(50):
    snap = get_gps()
    if snap["fix"]:
        break
    time.sleep(0.05)
assert snap["fix"] is True and abs(snap["speed_kmh"] - 20.0016) < 1e-6 and snap["sats"] == 12
assert snap["age_ms"] is not None and snap["age_ms"] < 2000
assert snap["counts"]["bad_checksum"] == 1 and snap["counts"]["rmc"] == 1 and snap["counts"]["gga"] == 1
logged = open(state.log_path, encoding="ascii").read().splitlines()
assert len(logged) == 2 and all(float(l.split(" ", 1)[0]) > 1.7e9 for l in logged) and logged[1].endswith(RMC)
u.sendto((VOID + "\r\n").encode(), ("127.0.0.1", udp_port))
time.sleep(0.2)
assert get_gps()["fix"] is False
with urllib.request.urlopen(f"http://127.0.0.1:{http_port}/", timeout=3) as resp:
    assert b"phone GPS bridge" in resp.read()
srv.shutdown()
print("2 bridge: UDP in, bad checksum dropped, /gps fix, speed, sats and age, log with this clock, void fix")

# ---- 3. provider merge ---------------------------------------------------------------------------
DEFAULT_DASH = REPO.parent / "Tukzie-Vac-Work-2026" / "Dashboard Team" / "Tukzie-Dashboard" / "v1.0-validated"
DASH = Path(os.environ.get("TUKZIE_DASHBOARD_DIR", DEFAULT_DASH))
scratch = Path(tempfile.mkdtemp(prefix="tukzie_phone_gps_"))
shutil.copytree(DASH / "app", scratch / "app", ignore=shutil.ignore_patterns("__pycache__", "logs"))
for name in ("live_data_provider.py", "sw7_live_only.py"):
    shutil.copy2(INTEGRATION / name, scratch / "app" / "data" / name)
sys.path.insert(0, str(scratch))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from app.data import live_data_provider as ldp  # noqa: E402

ESP_NOFIX = {"age_ms": 200, "soc": 57, "v": 74.6, "i": 1.0, "fix": False, "lat": None, "lon": None,
             "cell_lat": -33.9595, "cell_lon": 18.4598, "cell_acc_m": 550}
ESP_FIX = dict(ESP_NOFIX, fix=True, lat=-33.96, lon=18.46, crs=90.0, alt=40.0)
PHONE = {"fix": True, "lat": -33.95945, "lon": 18.45985, "speed_kmh": 18.5, "course_deg": 120.0, "alt_m": 85.0,
         "age_ms": 400, "source": "phone"}


def st(esp, phone=None):
    return ldp.build_live_state({"esp32": esp, "tof": None}, live_only=True, phone_gps=phone)


s = st(ESP_NOFIX, PHONE)
assert s.speed_kmh == 18.5 and s.signal_validity["speed"] is True
assert (s.latitude, s.longitude) == (PHONE["lat"], PHONE["lon"]) and s.signal_validity["gps"] is True
assert s.heading == 120.0 and s.altitude_m == 85.0 and s.sw7_position_source == "phone"
assert s.sw7_cell_position is None                       # a real fix replaces the network circle
s = st(ESP_FIX, PHONE)
assert (s.latitude, s.longitude, s.heading, s.altitude_m) == (-33.96, 18.46, 90.0, 40.0)
assert s.sw7_position_source == "vehicle" and s.speed_kmh == 18.5     # vehicle position, phone speed
s = st(ESP_NOFIX, dict(PHONE, speed_kmh=1.2))
assert s.heading is None and s.speed_kmh == 1.2                      # course is noise when nearly still
for bad in (dict(PHONE, age_ms=5000), dict(PHONE, fix=False), dict(PHONE, lat=None), None, {"junk": 1}):
    s = st(ESP_NOFIX, bad)
    assert s.signal_validity["speed"] is False and s.latitude is None and s.sw7_position_source is None
    assert s.sw7_cell_position == (-33.9595, 18.4598, 550)
old = st(ESP_NOFIX)
assert old.signal_validity["speed"] is False and old.latitude is None
print("3 provider: phone speed always; phone position only without a vehicle fix; stale or void ignored")

# ---- 4. phone only: the Pi 4 stale or gone -------------------------------------------------------------
ESP_STALE = dict(ESP_FIX, age_ms=4500)
fresh = ldp.build_live_state({"esp32": ESP_NOFIX, "tof": None}, live_only=True)
for tel in ({"esp32": ESP_STALE, "tof": None}, {"esp32": None, "tof": None}, None):
    s = ldp.build_live_state(tel, live_only=True, phone_gps=PHONE, previous=fresh)
    assert s is not None and s.speed_kmh == 18.5 and s.signal_validity["speed"] is True
    assert (s.latitude, s.longitude) == (PHONE["lat"], PHONE["lon"]) and s.sw7_position_source == "phone"
    assert s.heading == 120.0 and s.signal_validity["gps"] is True
    assert s.soc_pct is None and s.signal_validity["soc"] is False       # not the last BMS value either
    assert s.battery_power_kw is None and s.signed_battery_power_kw is None and s.sw7_cell_position is None
    assert s.sw7_rear_live is False and s.front_obstacle_distance_m is None
    assert s.rear_obstacle_distance_m is None
s = ldp.build_live_state({"esp32": ESP_STALE, "tof": None}, live_only=False, phone_gps=PHONE)
assert s.speed_kmh == 18.5 and s.soc_pct is None and s.battery_power_kw == 0.0     # simulation mode: same, no 82 %
assert ldp.build_live_state({"esp32": ESP_NOFIX, "tof": None}, live_only=True, phone_gps=PHONE).sw7_rear_live is True
# Pi 5 front ToF (dual) keeps working without the Pi 4; a stale ToF on a reachable bridge is still dropped
s = ldp.build_live_state(None, live_only=True, phone_gps=PHONE, dual=True,
                         front_telemetry={"esp32": None, "tof": {"ahead_mm": 850, "age_ms": 100}})
assert s.front_obstacle_distance_m == 0.85 and s.rear_obstacle_distance_m is None
s = ldp.build_live_state({"esp32": ESP_STALE, "tof": {"ahead_mm": 600, "age_ms": 5000}}, live_only=True,
                         phone_gps=PHONE, dual=True)
assert s.rear_obstacle_distance_m is None
for bad in (dict(PHONE, age_ms=5000), dict(PHONE, fix=False), None):          # both stale: no data
    for tel in ({"esp32": ESP_STALE, "tof": None}, {"esp32": None}, None):
        assert ldp.build_live_state(tel, live_only=True, phone_gps=bad) is None

# The provider: ingests the phone-only state, link still says the Pi 4 is stale or offline.
from PySide6.QtCore import QCoreApplication  # noqa: E402
app = QCoreApplication.instance() or QCoreApplication([])


class FakeManager:
    sim = None

    def __init__(self):
        self.ingested = []

    def ingest_live_state(self, state, source):
        self.ingested.append((state, source))


m = FakeManager()
prov = ldp.LiveDataProvider(m, url="http://127.0.0.1:9")
prov.apply({"esp32": ESP_NOFIX, "tof": None})                      # Pi 4 live, no phone yet
assert prov.link == "live" and m.ingested[-1][0].soc_pct == 57 and m.ingested[-1][0].sw7_rear_live is True
prov.phone_gps, prov._phone_gps_at = dict(PHONE), time.monotonic()
prov.apply({"esp32": ESP_STALE, "tof": None})
assert prov.link == "stale" and len(m.ingested) == 2
assert m.ingested[-1][0].speed_kmh == 18.5 and m.ingested[-1][0].soc_pct is None
prov.apply(None)                                                   # Pi 4 bridge unreachable
assert prov.link == "offline" and len(m.ingested) == 3 and m.ingested[-1][0].speed_kmh == 18.5
assert m.ingested[-1][1] == ldp.SOURCE
prov.apply({"esp32": dict(ESP_NOFIX, soc=None), "tof": None})      # Pi 4 back, soc null: last BMS value kept
assert prov.link == "live" and m.ingested[-1][0].soc_pct == 57 and m.ingested[-1][0].signal_validity["soc"] is False
prov._phone_gps_at = time.monotonic() - 3.0                        # a reply not renewed for 3 s turns stale
prov.apply(None)
assert prov.link == "offline" and len(m.ingested) == 4
prov.phone_gps = None
prov.apply({"esp32": ESP_STALE, "tof": None})
assert prov.link == "stale" and len(m.ingested) == 4                # both stale: nothing ingested
print("4 phone only: speed and position from the phone with the Pi 4 stale or gone, battery absent; both stale: no data")
print("ALL PASS")
