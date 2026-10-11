"""Offscreen test: the map's simulated drive in step on every dashboard page, and back to live after.

Builds a patched copy of the team's v1.1 dashboard (TUKZIE_DASHBOARD_DIR, as the other tests), runs it offscreen
in live-only mode with no bridge, plans a route, starts the simulated drive and checks that every page gets one
simulated state (speed, battery drain from the default 80 %, power, range, trip matching the map, gear D), that the
live state is untouched, that the SIMULATED strip (in the layout) and chip show, and that ending the drive restores
live data, the NO DATA chip and the Analytics chart history. Saves a screenshot of each page in tests/sim_sync/.
Run: TUKZIE_DASHBOARD_DIR=<team Dashboard folder> python tests/test_sim_sync.py
"""
import glob, os, shutil, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)
TEAM = os.environ.get("TUKZIE_DASHBOARD_DIR", "").strip()
if not TEAM or not os.path.isdir(os.path.join(TEAM, "app", "pages")):
    sys.exit("Set TUKZIE_DASHBOARD_DIR to a copy of the team's v1.1 Dashboard folder")
SP = tempfile.mkdtemp(prefix="sw7_simsync_")
out = os.path.join(HERE, "sim_sync"); os.makedirs(out, exist_ok=True)
stamp = str(int(time.time()))
build, src = os.path.join(SP, "build_" + stamp), os.path.join(SP, "src_" + stamp)
shutil.copytree(TEAM, build)
os.makedirs(src)
for f in glob.glob(os.path.join(INTEG, "*.py")):
    shutil.copy(f, src)
shutil.copy(os.path.join(INTEG, "tests", "dashboard_patches.py"), src)
shutil.copytree(os.path.join(INTEG, "fonts"), os.path.join(src, "fonts"))
r = subprocess.run([sys.executable, os.path.join(INTEG, "deploy", "apply_patches.py"), build, "--source", src,
                    "--native-map", "--team-dir", os.path.join(SP, "nonexistent")], capture_output=True, text=True)
print(r.stdout.strip().splitlines()[-1] if r.returncode == 0 else r.stdout + r.stderr)
if r.returncode:
    sys.exit(1)
env = dict(os.environ, QT_QPA_PLATFORM="offscreen", TUKZIE_LIVE_ONLY="1",
           TUKZIE_NO_CONTROLLER="1", TUKZIE_SKIP_LOGIN="1", TUKZIE_SW7_THEME="0",
           TUKZIE_TELEMETRY_URL="http://127.0.0.1:9")
if sys.platform == "win32":
    env.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")   # offscreen Qt finds no fonts otherwise
script = r'''
import sys, types, math, copy
class _Meta(type):
    def __getattr__(cls, name): return _Dummy
class _Dummy(metaclass=_Meta):
    def __init__(self, *a, **k): pass
    def __getattr__(self, name): return _Dummy()
    def __call__(self, *a, **k): return _Dummy()
    def __bool__(self): return False
    def __int__(self): return 0
_m = types.ModuleType("PySide6.QtMultimedia")
for _n in ("QSoundEffect", "QMediaPlayer", "QAudioOutput", "QMediaDevices", "QAudioDevice"):
    setattr(_m, _n, _Dummy)
sys.modules["PySide6.QtMultimedia"] = _m
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
a = QApplication(sys.argv)
from app.main_window import MainWindow
w = MainWindow(); w.resize(1280, 800); w.show()
OUT = sys.argv[1]
lat0, lon0 = -33.9600, 18.4600
mlat, mlon = 1 / 111320.0, 1 / (111320.0 * math.cos(math.radians(lat0)))
pts = [SimpleNamespace(lat=lat0 + i * 10 * mlat, lon=lon0, road_name="Main Road") for i in range(41)]
pts += [SimpleNamespace(lat=lat0 + 400 * mlat, lon=lon0 + i * 10 * mlon, road_name="Station Road") for i in range(1, 41)]
plan = SimpleNamespace(route=pts, nearby_roads=[], destination={"lat": pts[-1].lat, "lon": pts[-1].lon}, duration_s=120.0)
PAGES = ["driving", "analytics", "diagnostics", "navigation", "charging", "sensors"]
fails = []
def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)
def start():
    d = w.dashboard; m = d.navigation.map
    check(d._sw7_marks.chip.text() == "NO DATA", f"chip before simulation: {d._sw7_marks.chip.text()!r}")
    d.analytics.speed_chart.push(11.0)          # a 'live' point that must survive the simulation
    d._sw7_before = list(d.analytics.speed_chart._data)
    m.set_plan(plan, reset_view=False)
    check(m.start_simulation(), "simulation started")
    for _ in range(20): m._sim_step()          # about 140 m
    QTimer.singleShot(500, lambda: shoot(0))
def shoot(i):
    d = w.dashboard
    if i == 0:
        s = d.current_state
        check(s.data_source == "sw7_simulated_drive", "every page gets the simulated state")
        check(abs(s.speed_kmh - 25.0) < 0.01, f"speed {s.speed_kmh}")
        check(s.soc_pct < 80.0 and s.soc_pct > 79.0, f"battery drains from the default 80 %: {s.soc_pct:.3f}")
        check(s.battery_power_kw > 1.0, f"battery power {s.battery_power_kw} kW")
        check(s.range_km is not None and s.range_km > 0, f"range {s.range_km}")
        check(abs(s.trip_km - d.navigation.map._sim_m / 1000) < 1e-6, f"trip {s.trip_km:.3f} km matches the map")
        check(str(getattr(s.gear, "value", s.gear)) == "D", f"gear {s.gear}")
        check(d._sw7_live_state.data_source == "no_data", "live state untouched")
        check(d._sw7_marks.in_layout and d._sw7_marks.strip.isVisible() and d._sw7_marks.chip.text() == "SIMULATED", "strip and SIMULATED chip")
    if i < len(PAGES):
        d.switch_page_id(PAGES[i])
        QTimer.singleShot(900, lambda: (w.grab().save(f"{OUT}/sim_{PAGES[i]}.png"), shoot(i + 1)))
    else:
        d.navigation.map.stop_simulation()
        QTimer.singleShot(800, after)
def after():
    d = w.dashboard
    s = d.current_state
    check(s.data_source == "no_data", f"after the simulation every page is back on live: {s.data_source}")
    check(not d._sw7_marks.strip.isVisible() and d._sw7_marks.chip.text() == "NO DATA", "strip gone, NO DATA chip")
    check(list(d.analytics.speed_chart._data) == d._sw7_before, "Analytics chart points from the simulation removed")
    live = copy.copy(d._sw7_live_state); live.data_source = "sw7_telemetry"
    d._on_vehicle_state(live)
    check(d._sw7_marks.chip.text() == "LIVE", "LIVE chip with live telemetry")
    # the echo of the map's own position must not disturb its glide timing (the jerky drive of 11 Oct)
    m = d.navigation.map
    m.start_simulation(); m._sim_step()
    t_fix, interval = m._last_fix_time, m._interval
    for _ in range(5): d._on_vehicle_state(d._sw7_live_state)
    check(m._last_fix_time == t_fix and m._interval == interval, "the map ignores its own simulated position echoed back")
    # spoken directions over the whole simulated route: right onto Station Road at 400 m, arrival at 800 m
    g = d._sw7_voice_guide
    m.stop_simulation(); g.tick()
    g.spoken.clear()
    m.start_simulation(); g.tick()
    for _ in range(200):
        if m.sim_arrived: break
        m._sim_step(); g.tick()
    said = [t for _, t in g.spoken]
    print("     spoken:", said)
    want = ["Continue for 400 metres, then turn right onto Station Road.",
            "In 200 metres, turn right onto Station Road.",
            "Turn right onto Station Road.",
            "In 200 metres, you will arrive at your destination.",
            "You have arrived at your destination."]
    check(said == want, "spoken directions: start, 200 m, the turn, arrival warning, arrival, each once")
    m.stop_simulation(); m.start_simulation(); m._sim_step()
    # a real GPS fix ends the simulation on every page
    fix = copy.copy(d._sw7_live_state); fix.data_source = "sw7_telemetry"
    fix.latitude, fix.longitude = -33.9570, 18.4610
    fix.signal_validity = dict(fix.signal_validity or {}, gps=True)
    d._on_vehicle_state(fix)
    check(not m.simulating and d.current_state.data_source == "sw7_telemetry" and m.vehicle == (-33.9570, 18.4610),
          "a real GPS fix stops the simulation and every page shows live data")
    d.switch_page_id("driving")
    QTimer.singleShot(800, lambda: (w.grab().save(f"{OUT}/live_driving.png"), print("RESULT", "PASS" if not fails else f"FAIL {fails}"), a.quit()))
QTimer.singleShot(18000, start)
a.exec()
'''
r = subprocess.run([sys.executable, "-c", script, out], cwd=build, env=env, capture_output=True, text=True, timeout=240)
print("\n".join(l for l in r.stdout.splitlines() if l.lstrip().startswith(("ok", "FAIL", "RESULT", "spoken"))))
err = [l for l in r.stderr.splitlines() if "Error" in l and "_Dummy" not in l and "PyObject_HasAttr" not in l]
print("\n".join(err[-8:]))
shutil.rmtree(SP, ignore_errors=True)
if "RESULT PASS" not in r.stdout:
    sys.exit(1)
print("ALL SIM SYNC TESTS PASSED")
