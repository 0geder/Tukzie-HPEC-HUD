"""Offscreen test: destination search on the Navigation page (sw7_search.py, Planning/destination-search-prompt.md).

Builds a patched copy of the team's v1.1 dashboard (TUKZIE_DASHBOARD_DIR, as the other tests) and runs the full
dashboard offscreen in live-only mode. Photon is replaced by a fake HTTP server in the dashboard process
(TUKZIE_PHOTON_URL), with a set delay per query, so no internet is needed. Checks: recents with distances when the
empty field gets focus; offline matches before the network result, then the network results on top; stale answers
dropped; the cache; the team fallback when Photon fails; the "From:" header for GPS, network, last fix and UCT;
choosing a row sets the destination hint with lat/lon and saves it as a recent; the coordinator's start order; the
list stays above the touch keyboard and keeps finger scrolling. Screenshots in tests/search/.
Run: TUKZIE_DASHBOARD_DIR=<team Dashboard folder> python tests/test_search.py
"""
import glob, os, shutil, subprocess, sys, tempfile, time
# Paper and depth style (sw7_weather): never the real weather API in a test, and no shared weather cache.
os.environ.setdefault("TUKZIE_WEATHER_URL", "http://127.0.0.1:9/v1/forecast")
os.environ.setdefault("TUKZIE_REVERSE_URL", "http://127.0.0.1:9/reverse")
os.environ.setdefault("TUKZIE_WEATHER_CACHE", os.path.join(__import__("tempfile").mkdtemp(prefix="sw7_wx_"), "last.json"))
HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)
TEAM = os.environ.get("TUKZIE_DASHBOARD_DIR", "").strip()
if not TEAM or not os.path.isdir(os.path.join(TEAM, "app", "pages")):
    sys.exit("Set TUKZIE_DASHBOARD_DIR to a copy of the team's v1.1 Dashboard folder")
SP = tempfile.mkdtemp(prefix="sw7_search_")
out = os.path.join(HERE, "search"); os.makedirs(out, exist_ok=True)
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
recents = os.path.join(SP, "recent_destinations.json")
with open(recents, "w", encoding="utf-8") as fh:
    fh.write('[{"name": "Kirstenbosch", "label": "Kirstenbosch National Botanical Garden, Rhodes Drive, Newlands",'
             ' "lat": -33.9875, "lon": 18.4327},'
             ' {"name": "Cape Town Station", "label": "Cape Town Station, Adderley Street, City Centre",'
             ' "lat": -33.9221, "lon": 18.4252}]')
env = dict(os.environ, QT_QPA_PLATFORM="offscreen", TUKZIE_LIVE_ONLY="1",
           TUKZIE_NO_CONTROLLER="1", TUKZIE_SKIP_LOGIN="1", TUKZIE_SW7_THEME="0",
           TUKZIE_TELEMETRY_URL="http://127.0.0.1:9", TUKZIE_SW7_RECENTS=recents)
if sys.platform == "win32":
    env.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")   # offscreen Qt finds no fonts otherwise
script = r'''
import sys, types, json, copy, time, threading, urllib.parse, os
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

# ---- fake Photon --------------------------------------------------------------------------------------------
HITS = {}
DELAY = {"cav": 0.8, "zzslow": 1.2, "two4": 0.2}
FEATURES = {
    "cav": [("Cavendish Square", "Dreyer Street", "Claremont", -33.9806, 18.4648, "mall"),
            ("Cavendish Close", "Cavendish Street", "Claremont", -33.9790, 18.4660, "residential")],
    "two4": [("Two4One", "Lower Main Road", "Observatory", -33.9380, 18.4720, "restaurant")],
    "zzslow": [("Slow Place", "Slow Road", "Nowhere", -33.90, 18.40, "place")],
}
class Photon(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        q = qs.get("q", [""])[0]
        HITS[q] = HITS.get(q, 0) + 1
        HITS.setdefault("_params", []).append({k: v[0] for k, v in qs.items()})
        time.sleep(DELAY.get(q, 0.1))
        if q.startswith("fail"):
            self.send_response(503); self.end_headers(); return
        feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                  "properties": {"name": n, "street": st, "district": dist, "city": "Cape Town", "osm_value": kind}}
                 for n, st, dist, lat, lon, kind in FEATURES.get(q, [])]
        body = json.dumps({"type": "FeatureCollection", "features": feats}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(body)
srv = ThreadingHTTPServer(("127.0.0.1", 0), Photon)
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["TUKZIE_PHOTON_URL"] = f"http://127.0.0.1:{srv.server_address[1]}/api/"

from PySide6.QtWidgets import QApplication, QScroller
from PySide6.QtCore import QTimer, Qt, QPoint
from PySide6.QtTest import QTest
a = QApplication(sys.argv)
from app.main_window import MainWindow
w = MainWindow(); w.resize(1280, 800); w.show()
OUT = sys.argv[1]
fails = []
def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)
def wait_until(cond, ms=4000):
    t = time.monotonic()
    while not cond() and (time.monotonic() - t) * 1000 < ms:
        QTest.qWait(20)
    return cond()

def rows(lst):
    from app.pages.sw7_search import ROLE_KIND, ROLE_TITLE, ROLE_SUBTITLE, ROLE_DISTANCE
    return [(lst.item(i).data(ROLE_KIND), lst.item(i).data(ROLE_TITLE), lst.item(i).data(ROLE_SUBTITLE),
             lst.item(i).data(ROLE_DISTANCE)) for i in range(lst.count())]

def type_text(edit, text):
    for ch in text:
        edit.insert(ch); QTest.qWait(30)        # what the touch keyboard does (insert emits textEdited)

def feed(d, **fields):
    s = copy.copy(d._sw7_live_state); s.data_source = "sw7_telemetry"
    s.latitude = s.longitude = None; s.sw7_cell_position = None
    for k, v in fields.items(): setattr(s, k, v)
    d._on_vehicle_state(s)

def run():
    d = w.dashboard; nav = d.navigation; s = nav._sw7_search
    d.vehicle_data._watchdog.stop()               # no 250 ms no-data states over the positions we feed
    d.switch_page_id("navigation"); QTest.qWait(300)
    lst, edit = nav.suggestions, nav.destination
    check(edit.placeholderText() == "Where to?", f"placeholder {edit.placeholderText()!r}")
    check(wait_until(lambda: s._index is not None, 15000), f"offline index built ({len(s._index.rows) if s._index else 0} places)")
    feed(d, latitude=-33.9577, longitude=18.4612)   # UCT upper campus, GPS fix
    check(nav._last_state.latitude == -33.9577, "the page has the GPS state")
    QTest.qWait(2500)                             # let the map settle on the first fix (context and tiles)

    # 1. recents on focus
    w.activateWindow(); edit.setFocus(); QTest.qWait(250)
    check(edit.hasFocus(), "field has focus")
    rs = rows(lst)
    print("     recents:", rs)
    check(lst.isVisible() and rs and rs[0][0] == "header" and rs[0][1] == "From: Current location (GPS)", "header: From: Current location (GPS)")
    check([r[0] for r in rs[1:]] == ["recent", "recent"] and rs[1][1].startswith("Kirstenbosch"), "two recents, newest first")
    check(all(r[3].endswith("km") for r in rs[1:]) and rs[1][3] == "4.2 km", f"distances from the fix: {[r[3] for r in rs[1:]]}")
    check(nav.keyboard.isVisible(), "touch keyboard open")
    g, kb_top = lst.geometry(), nav.stage.mapFromGlobal(nav.keyboard.mapToGlobal(QPoint(0, 0))).y()
    check(g.bottom() < kb_top, f"list ({g.top()}..{g.bottom()}) above the keyboard (top {kb_top})")
    check(lst.focusPolicy() == Qt.FocusPolicy.NoFocus and QScroller.hasScroller(lst.viewport()), "list keeps finger scrolling and never takes focus")
    w.grab().save(f"{OUT}/search_recents.png")

    # 2. local matches first, network results merged on top when they arrive
    t0 = time.monotonic()
    type_text(edit, "cav")
    got_local = wait_until(lambda: any(r[0] == "local" for r in rows(lst)), 4000)
    t_local = time.monotonic() - t0
    check(got_local and not any(r[0] == "result" for r in rows(lst)), f"offline matches shown before the network answer ({t_local:.2f} s after the first key)")
    print("     before Photon:", rows(lst)[:4])
    w.grab().save(f"{OUT}/search_local_first.png")
    got_net = wait_until(lambda: any(r[0] == "result" for r in rows(lst)), 6000)
    rs = rows(lst)
    print("     after Photon:", rs[:6])
    kinds = [r[0] for r in rs]
    check(got_net and kinds[1] == "result" and rs[1][1] == "Cavendish Square" and rs[1][2].startswith("Dreyer Street, Claremont"),
          "Photon rows on top: name in bold line, address under it")
    check(rs[1][3] == "2.6 km", f"distance to Cavendish Square {rs[1][3]}")
    check(not any(r[0] == "local" and r[1].lower() == "cavendish square" for r in rs), "the offline duplicate of Cavendish Square is merged away")
    p = HITS["_params"][-1]
    check(p.get("lat") == "-33.95770" and p.get("lon") == "18.46120" and p.get("bbox") == "16.3,-35.0,33.0,-22.0" and p.get("lang") == "en",
          f"Photon biased to the fix and limited to South Africa: {p}")
    check(HITS.get("c", 0) == 0 and HITS.get("cav", 0) == 1, f"debounced: one request for 'cav', none for one letter ({HITS.get('ca', 0)} for 'ca')")
    w.grab().save(f"{OUT}/search_results.png")
    lst.grab().save(f"{OUT}/search_results_list.png")

    # 3. stale answers dropped
    edit.clear(); QTest.qWait(100)
    check(rows(lst)[1][0] == "recent", "clearing the field shows the recents again")
    type_text(edit, "zzslow"); QTest.qWait(350)       # slow request now in flight
    edit.clear(); type_text(edit, "two4")
    wait_until(lambda: any(r[1] == "Two4One" for r in rows(lst)), 2500)
    QTest.qWait(1500)                                  # the slow answer has come back by now
    titles = [r[1] for r in rows(lst)]
    check("Two4One" in titles and "Slow Place" not in titles and s.stale_dropped >= 1,
          f"stale 'zzslow' answer dropped ({s.stale_dropped} dropped), rows {titles[:4]}")

    # 4. the cache: the same query again is answered without the network
    n = HITS.get("cav", 0)
    edit.clear(); type_text(edit, "cav"); QTest.qWait(400)
    check(HITS.get("cav", 0) == n and any(r[1] == "Cavendish Square" for r in rows(lst)), "repeat query served from the cache at once")

    # 5. Photon fails: the team's request_suggestions runs
    calls = []
    orig = d.asis.request_suggestions
    def fake(field, text):
        calls.append((field, text))
        d.asis.suggestions_ready.emit(field, [{"label": "Fallback Place, Rondebosch", "lat": -33.96, "lon": 18.47, "kind": "suburb", "_query": text}])
    d.asis.request_suggestions = fake
    edit.clear(); type_text(edit, "failxq")
    wait_until(lambda: any(r[1] == "Fallback Place" for r in rows(lst)), 3000)
    check(calls and calls[-1] == ("destination", "failxq") and any(r[1] == "Fallback Place" for r in rows(lst)),
          f"Photon error falls back to the team's suggestions: {calls}")
    d.asis.request_suggestions = orig

    # 6. choose a row (a tap on it)
    edit.clear(); type_text(edit, "cav")
    wait_until(lambda: any(r[0] == "result" for r in rows(lst)), 3000)
    from app.pages.sw7_search import ROLE_KIND
    item = next(lst.item(i) for i in range(lst.count()) if lst.item(i).data(ROLE_KIND) == "result")
    QTest.mouseClick(lst.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, lst.visualItemRect(item).center())
    QTest.qWait(200)
    hint = nav._selected_destination or {}
    check(abs(hint.get("lat", 0) + 33.9806) < 1e-6 and abs(hint.get("lon", 0) - 18.4648) < 1e-6 and hint.get("_online_provider") == "Photon",
          f"tap sets the destination hint with lat/lon: {hint.get('label')}, {hint.get('lat')}, {hint.get('lon')}")
    check(edit.text() == "Cavendish Square, Dreyer Street, Claremont" and not lst.isVisible(), f"field shows the label, list closed: {edit.text()!r}")
    saved = json.load(open(os.environ["TUKZIE_SW7_RECENTS"], encoding="utf-8"))
    check(saved[0]["label"] == edit.text() and len(saved) == 3, "chosen place saved first in the recents file")
    # a tap on the header does nothing
    edit.clear(); QTest.qWait(150)
    QTest.mouseClick(lst.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, lst.visualItemRect(lst.item(0)).center())
    QTest.qWait(150)
    check(edit.text() == "" and lst.isVisible(), "the header row cannot be chosen")
    # a planned route's destination becomes a recent too
    from types import SimpleNamespace
    s._route_planned(SimpleNamespace(destination={"label": "Groote Schuur Hospital, Main Road, Observatory", "lat": -33.9411, "lon": 18.4626}))
    check(s.recents.items[0]["label"].startswith("Groote Schuur") and len(s.recents.items) == 4, "planned destination saved as a recent")

    # 7. the header for each kind of position
    feed(d, sw7_cell_position=(-33.9804, 18.4651, 550.0)); s.show_recents()
    check(rows(lst)[0][1] == "From: Approximate location (mobile network, \u00b1550 m)", f"network header: {rows(lst)[0][1]}")
    check(rows(lst)[1][3] == "4.4 km", f"distances from the network position: {rows(lst)[1][3]}")
    lst.grab().save(f"{OUT}/search_recents_network.png")
    d.asis.last_asis_fix = (-33.93, 18.42, None); feed(d); s.show_recents()
    check(rows(lst)[0][1] == "From: Last known position", f"last-fix header: {rows(lst)[0][1]}")
    d.asis.last_asis_fix = None; feed(d); s.show_recents()
    check(rows(lst)[0][1] == "From: UCT (no GPS)", f"UCT header: {rows(lst)[0][1]}")

    # 8. coordinator start order: GPS, network, last fix, UCT
    c = d.asis
    def start(raw, last=None):
        c.last_asis_fix = last
        return c._resolve_start("", raw)
    gps = start(SimpleNamespace(latitude=-33.95, longitude=18.46, sw7_cell_position=(-33.98, 18.47, 550.0)), (-33.9, 18.4, None))
    net = start(SimpleNamespace(latitude=None, longitude=None, sw7_cell_position=(-33.98, 18.47, 550.0)), (-33.9, 18.4, None))
    last = start(SimpleNamespace(latitude=None, longitude=None, sw7_cell_position=None), (-33.9, 18.4, None))
    uct = start(SimpleNamespace(latitude=None, longitude=None, sw7_cell_position=None), None)
    print("     starts:", [(p or {}).get("label") for p in (gps, net, last, uct)])
    check(gps["kind"] == "gps" and gps["lat"] == -33.95, "start 1: the GPS fix")
    check(net["label"] == "Approximate location (mobile network)" and net["lat"] == -33.98, "start 2: the network position")
    check(last["label"] == "Last known position" and last["lat"] == -33.9, "start 3: the last fix")
    check(uct and uct["label"] == "Default UCT start (GPS unavailable)", "start 4: UCT")

    print("     timings:", [(q, src, round(t, 3)) for q, src, t in s.timings if q][:12])
    QTimer.singleShot(200, lambda: (print("RESULT", "PASS" if not fails else f"FAIL {fails}"), a.quit()))
QTimer.singleShot(16000, run)
a.exec()
'''
r = subprocess.run([sys.executable, "-c", script, out], cwd=build, env=env, capture_output=True, text=True, timeout=300)
print("\n".join(l for l in r.stdout.splitlines() if l.lstrip().startswith(("ok", "FAIL", "RESULT", "recents", "before", "after", "starts", "timings"))))
err = [l for l in r.stderr.splitlines() if ("Error" in l or "Traceback" in l) and "_Dummy" not in l and "PyObject_HasAttr" not in l]
print("\n".join(err[-12:]))
shutil.rmtree(SP, ignore_errors=True)
if "RESULT PASS" not in r.stdout:
    print(r.stderr[-3000:])
    sys.exit(1)
print("ALL SEARCH TESTS PASSED")
