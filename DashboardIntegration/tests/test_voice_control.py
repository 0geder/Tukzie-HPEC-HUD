"""Test: voice control of the dashboard (sw7_voice_control.py, Planning/voice-control-prompt.md).

1. parse_intent on the host: every command, the destination and choice phrases, fillers, the wake word, and phrases
   that must do nothing.
2. The full dashboard offscreen (patched copy of the team's v1.1, TUKZIE_DASHBOARD_DIR as the other tests) with
   TUKZIE_SW7_VOICE=1 and no microphone model (the listener stays off; recognised text is fed in): home, map, rear and
   front camera on Surroundings, reverse mode ending after the timeout and after a steady forward speed, "done", a
   phrase that is not a command, and the destination flow against a fake Photon (three options read out, "second one"
   picks the second). Off by default: without TUKZIE_SW7_VOICE the controller is not installed.
Screenshots in tests/voice/.
Run: TUKZIE_DASHBOARD_DIR=<team Dashboard folder> python tests/test_voice_control.py
"""
import glob, os, shutil, subprocess, sys, tempfile, time
os.environ.setdefault("TUKZIE_WEATHER_URL", "http://127.0.0.1:9/v1/forecast")
os.environ.setdefault("TUKZIE_REVERSE_URL", "http://127.0.0.1:9/reverse")
os.environ.setdefault("TUKZIE_WEATHER_CACHE", os.path.join(tempfile.mkdtemp(prefix="sw7_wx_"), "last.json"))
HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)

# ---- 1. parser ---------------------------------------------------------------------------------------------------
sys.path.insert(0, INTEG)
from sw7_voice_control import parse_intent, correct_place  # noqa: E402
CASES = [
    ("home", ("home", None)), ("go home", ("home", None)), ("Home, please.", ("home", None)), ("speed", ("home", None)),
    ("map", ("map", None)), ("open the map", ("map", None)), ("navigation", ("map", None)),
    ("reverse", ("rear", None)), ("rear camera", ("rear", None)), ("show rear camera", ("rear", None)),
    ("back camera", ("rear", None)), ("front camera", ("front", None)), ("switch to front camera", ("front", None)),
    ("done", ("done", None)), ("finished reversing", ("done", None)), ("cancel", ("cancel", None)),
    ("map destination rondebosch", ("destination", "rondebosch")), ("destination cavendish square", ("destination", "cavendish square")),
    ("go to kirstenbosch", ("destination", "kirstenbosch")), ("take me to the station", ("destination", "the station")),
    ("navigate to main road", ("destination", "main road")),
    ("first", ("choose", 1)), ("second one", ("choose", 2)), ("option three", ("choose", 3)), ("number two", ("choose", 2)),
    ("the first one", ("choose", 1)), ("2", ("choose", 2)),
    ("hey map please", ("map", None)),
    ("what time is it", None), ("i think the map is wrong", None), ("", None), ("go to map", ("map", None)),
]
bad = [(t, parse_intent(t), want) for t, want in CASES if parse_intent(t) != want]
for t, got, want in bad:
    print(f"FAIL parse {t!r}: {got} (want {want})")
assert parse_intent("map", wake="dash") is None and parse_intent("dash map", wake="dash") == ("map", None)
assert parse_intent("dash destination rondebosch", wake="dash") == ("destination", "rondebosch")
assert correct_place("round bosh") == "Rondebosch" and correct_place("kyrstin bosh") == "Kirstenbosch"
assert correct_place("cape town station") == "cape town station" and correct_place("the station") == "the station"
if bad:
    sys.exit(1)
print(f"1 parser: {len(CASES)} phrases, the wake word and the place-name correction as expected")

# ---- 2. dashboard -------------------------------------------------------------------------------------------------
TEAM = os.environ.get("TUKZIE_DASHBOARD_DIR", "").strip()
if not TEAM or not os.path.isdir(os.path.join(TEAM, "app", "pages")):
    sys.exit("Set TUKZIE_DASHBOARD_DIR to a copy of the team's v1.1 Dashboard folder")
SP = tempfile.mkdtemp(prefix="sw7_voice_")
out = os.path.join(HERE, "voice"); os.makedirs(out, exist_ok=True)
build, src = os.path.join(SP, "build"), os.path.join(SP, "src")
shutil.copytree(TEAM, build, ignore=shutil.ignore_patterns("__pycache__"))
os.makedirs(src)
for f in glob.glob(os.path.join(INTEG, "*.py")):
    shutil.copy(f, src)
shutil.copy(os.path.join(INTEG, "tests", "dashboard_patches.py"), src)
shutil.copytree(os.path.join(INTEG, "fonts"), os.path.join(src, "fonts"))
shutil.copytree(os.path.join(INTEG, "assets"), os.path.join(src, "assets"))
r = subprocess.run([sys.executable, os.path.join(INTEG, "deploy", "apply_patches.py"), build, "--source", src,
                    "--native-map", "--team-dir", os.path.join(SP, "nonexistent")], capture_output=True, text=True)
print(r.stdout.strip().splitlines()[-1] if r.returncode == 0 else r.stdout + r.stderr)
if r.returncode:
    sys.exit(1)
env = dict(os.environ, QT_QPA_PLATFORM="offscreen", TUKZIE_LIVE_ONLY="1", TUKZIE_NO_CONTROLLER="1",
           TUKZIE_SKIP_LOGIN="1", TUKZIE_TELEMETRY_URL="http://127.0.0.1:9", TUKZIE_CAMERA_URL="http://192.0.2.1:9",
           TUKZIE_SW7_RECENTS=os.path.join(SP, "recents.json"), TUKZIE_VOSK_MODEL=os.path.join(SP, "no-model"))
if sys.platform == "win32":
    env.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
script = r'''
import sys, types, json, time, threading, urllib.parse, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
FEATURES = [("Rondebosch", "Main Road", "Rondebosch", -33.9620, 18.4720, "suburb"),
            ("Rondebosch Station", "Station Road", "Rondebosch", -33.9630, 18.4760, "station"),
            ("Rondebosch Common", "Campground Road", "Rondebosch", -33.9600, 18.4810, "park")]
class Photon(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("q", [""])[0]
        feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                  "properties": {"name": n, "street": st, "district": d, "city": "Cape Town", "osm_value": k}}
                 for n, st, d, lat, lon, k in FEATURES] if q.lower().startswith("rondebosch") else []
        body = json.dumps({"type": "FeatureCollection", "features": feats}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(body)
srv = ThreadingHTTPServer(("127.0.0.1", 0), Photon)
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["TUKZIE_PHOTON_URL"] = f"http://127.0.0.1:{srv.server_address[1]}/api/"
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
a = QApplication(sys.argv)
from app.main_window import MainWindow
w = MainWindow(); w.resize(1280, 800); w.show()
OUT, MODE = sys.argv[1], sys.argv[2]
fails = []
def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg, flush=True)
    if not cond: fails.append(msg)
def wait_until(cond, ms=6000):
    t = time.monotonic()
    while not cond() and (time.monotonic() - t) * 1000 < ms:
        QTest.qWait(20)
    return cond()
def page(d): return d.page_ids[d.stack.currentIndex()]

def run():
    d = w.dashboard
    vc = getattr(d, "_sw7_voice", None)
    if MODE == "off":
        check(vc is None, "off by default: no voice controller without TUKZIE_SW7_VOICE")
        return finish()
    check(vc is not None, "voice controller installed with TUKZIE_SW7_VOICE=1")
    check(getattr(vc, "listener_reason", "") and "no model" in vc.listener_reason, f"listener off without a model ({getattr(vc, 'listener_reason', None)})")
    said = []
    vc.say = lambda text: said.append(text)
    d.vehicle_data._watchdog.stop()
    dual = getattr(d, "sw7_dual", None)

    vc.handle_text("map"); QTest.qWait(200)
    check(page(d) == "navigation" and said[-1] == "Map", f"'map': page {page(d)}")
    vc.handle_text("home"); QTest.qWait(200)
    check(page(d) == "driving", f"'home': page {page(d)}")
    vc.handle_text("rear camera"); QTest.qWait(400)
    check(page(d) == "sensors" and vc.reverse, f"'rear camera': page {page(d)}, reverse mode {vc.reverse}")
    if dual is not None:
        check(dual.selected == "rear", f"rear side selected ({dual.selected})")
    w.grab().save(f"{OUT}/voice_rear_camera.png")
    vc.handle_text("front camera"); QTest.qWait(300)
    check(page(d) == "sensors" and not vc.reverse and (dual is None or dual.selected == "front"), "'front camera': front side, reverse mode off")
    vc.handle_text("i think it is going to rain"); QTest.qWait(100)
    check(page(d) == "sensors" and vc.log[-1][2] is None, "a phrase that is not a command changes nothing")

    # reverse mode ends by itself (fake clock)
    T = [1000.0]; vc.clock = lambda: T[0]
    vc.speed_fn = lambda: 0.0
    vc.handle_text("reverse"); QTest.qWait(200)
    T[0] += 30; vc._tick()
    check(page(d) == "sensors" and vc.reverse, "still on the rear view after 30 s")
    T[0] += 16; vc._tick(); QTest.qWait(200)
    check(page(d) == "driving" and not vc.reverse, f"back to Driving 46 s after 'reverse' ({page(d)})")
    vc.handle_text("reverse"); QTest.qWait(200)
    vc.speed_fn = lambda: 12.0
    vc._tick(); T[0] += 2; vc._tick()
    check(page(d) == "sensors", "12 km/h for 2 s: still on the rear view")
    T[0] += 1.5; vc._tick(); QTest.qWait(200)
    check(page(d) == "driving", "12 km/h held for 3.5 s: back to Driving")
    vc.speed_fn = lambda: 0.0
    vc.handle_text("reverse"); T[0] += 5; vc.handle_text("done"); QTest.qWait(200)
    check(page(d) == "driving" and not vc.reverse, "'done' in reverse mode: Driving")
    vc.clock = time.monotonic

    # destination flow against the fake Photon
    said.clear()
    vc.handle_text("map destination round bosh")   # as the model hears it
    check(page(d) == "navigation" and d.navigation.destination.text() == "Rondebosch", f"'round bosh' corrected and typed into the field ({d.navigation.destination.text()!r})")
    check(wait_until(lambda: len(vc.choices) == 3, 8000), f"three options found ({[c[0] for c in vc.choices]})")
    check(said and said[-1].startswith("Option one, Rondebosch") and "Option two, Rondebosch Station" in said[-1],
          f"options read out: {said[-1] if said else None!r}")
    w.grab().save(f"{OUT}/voice_destination_options.png")
    vc.handle_text("second one"); QTest.qWait(600)
    check(said[-1] == "Going to Rondebosch Station", f"'second one' chosen: {said[-1]!r}")
    check("Rondebosch Station" in d.navigation.destination.text(), f"destination field: {d.navigation.destination.text()!r}")
    check(not vc.choices, "choice window closed")
    vc.handle_text("first"); QTest.qWait(100)
    check(said[-1] == "Going to Rondebosch Station", "'first' after the choice is ignored")
    w.grab().save(f"{OUT}/voice_destination_set.png")
    finish()

def finish():
    QTimer.singleShot(200, lambda: (print("RESULT", "PASS" if not fails else f"FAIL {fails}"), a.quit()))
QTimer.singleShot(8000, run)
a.exec()
'''
ok = True
for mode, extra in (("on", {"TUKZIE_SW7_VOICE": "1"}), ("off", {})):
    e = dict(env, **extra)
    if mode == "off":
        e.pop("TUKZIE_SW7_VOICE", None)
    r = subprocess.run([sys.executable, "-c", script, out, mode], cwd=build, env=e, capture_output=True, text=True,
                       timeout=300)
    print(f"-- {mode}")
    print("\n".join(l for l in r.stdout.splitlines() if l.lstrip().startswith(("ok", "FAIL", "RESULT"))))
    if "RESULT PASS" not in r.stdout:
        ok = False
        print(r.stderr[-3000:])
shutil.rmtree(SP, ignore_errors=True)
if not ok:
    sys.exit(1)
print("ALL VOICE CONTROL TESTS PASSED")
