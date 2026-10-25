"""SW-7: voice control of the dashboard, like a car assistant (Planning/voice-control-prompt.md).

Spoken commands change what the dashboard shows; nothing controls the vehicle. Recognition is offline (Vosk, a small
English model) so it works without coverage, and audio is processed in memory and never stored.

  "home", "speed", "driving"              -> Driving page
  "map", "navigation"                     -> Map page
  "reverse", "rear camera", "back camera" -> Surroundings, rear side (reverse mode)
  "front camera", "front view"            -> Surroundings, front side
  "done", "forward" (in reverse mode)     -> Driving page
  "destination X", "map destination X", "go to X", "navigate to X", "take me to X"
                                          -> Map page, X searched; the first three suggestions are read out and the
                                             driver says "first", "second" or "third" (or "option two", "number one")
  "cancel", "stop"                        -> ends the choice or reverse mode

There is no gear signal on the TUKZIE, so reverse mode ends by itself and the Driving page returns: after
REVERSE_TIMEOUT_S on the rear view with no command, or once the speed has stayed at or above FORWARD_KMH for
FORWARD_HOLD_S (the vehicle is clearly driving forward). Each action is confirmed through dashboard.asis.voice, so the
team's voice choice, volume and mute apply.

parse_intent() is pure Python (host-tested); VoiceControl acts on the dashboard; VoskListener reads the microphone on a
thread and hands each final phrase to the GUI thread. TUKZIE_SW7_VOICE=1 turns it on (off by default);
TUKZIE_VOSK_MODEL points at the model folder; TUKZIE_SW7_VOICE_WAKE, if set (for example "dash"), must start a phrase.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time

from PySide6.QtCore import QObject, QTimer, Signal

try:
    from ..asis.models import Severity
except ImportError:
    Severity = None

CATEGORY = "SW7_VOICE"
REVERSE_TIMEOUT_S = 45.0
FORWARD_KMH = 8.0
FORWARD_HOLD_S = 3.0
CHOICE_WINDOW_S = 20.0
ASK_WINDOW_S = 15.0             # after "Hello. Where are we headed today?" the next phrase is a destination
SUGGESTION_WAIT_S = 6.0
READ_OUT = 3                     # suggestions read out and choosable by number

HOME = {"home", "speed", "driving", "drive", "drive page", "dashboard", "main page", "home page"}
MAP = {"map", "navigation", "the map", "maps"}
PAGES = {"analytics": {"analytics", "stats", "statistics", "trip", "trip stats"},
         "diagnostics": {"diagnostics", "health", "system health", "status"},
         "charging": {"charging", "charge", "charging page"},
         "settings": {"settings", "setting"},
         "sensors": {"surroundings", "sensors", "camera", "cameras", "around"}}
GREETING = {"hello", "hi", "hey", "good morning", "good afternoon", "good evening", "hey dashboard", "hello dashboard"}
WEATHER = {"weather", "the weather", "whats the weather", "what is the weather", "how is the weather", "temperature"}
ALERTS = {"alerts", "any alerts", "hazards", "any hazards", "warnings", "any warnings", "whats around"}
BATTERY = {"battery level", "how much battery", "battery status", "state of charge", "range"}
HELP = {"help", "what can you do", "what can i say", "commands"}
REAR = {"reverse", "rear camera", "rear view", "back camera", "back view", "rear", "reversing", "reverse camera"}
FRONT = {"front camera", "front view", "front"}
DONE = {"done", "forward", "finished", "done reversing", "finished reversing", "stop reversing"}
CANCEL = {"cancel", "stop", "never mind", "nevermind"}
VERBS = ("go to ", "show ", "open ", "switch to ", "show me ", "go ")
ORDINALS = {"first": 1, "one": 1, "1": 1, "second": 2, "two": 2, "2": 2, "third": 3, "three": 3, "3": 3}
DESTINATION = re.compile(r"^(?:map\s+)?(?:destination|go to|navigate to|take me to|drive to|directions to)\s+(.+)$")
CHOICE = re.compile(r"^(?:the\s+)?(?:option|number|choice)?\s*(first|second|third|one|two|three|[123])"
                    r"(?:\s+(?:one|option|place))?$")


# Cape Town places that an English model mishears ("Rondebosch" as "round bosh"); a heard destination close to one in
# spelling (letters only, difflib ratio at least PLACE_CUTOFF) is replaced by it before the search. Recent destinations
# are added at run time. Phrases that match nothing closely are searched as heard.
PLACES = ("Rondebosch", "Kirstenbosch", "Claremont", "Observatory", "Newlands", "Mowbray", "Rosebank", "Woodstock",
          "Salt River", "Wynberg", "Kenilworth", "Pinelands", "Sea Point", "Green Point", "Gardens", "Muizenberg",
          "Bellville", "Athlone", "Langa", "Gugulethu", "Khayelitsha", "Mitchells Plain", "Durbanville", "Stellenbosch",
          "Camps Bay", "Constantia", "Tokai", "Plumstead", "Diep River", "Bergvliet", "Cape Town", "Cavendish Square",
          "Canal Walk", "Groote Schuur", "Table Mountain", "Rhodes Memorial", "Belhar", "Bishopscourt", "Oranjezicht",
          "Tamboerskloof", "Vredehoek", "Zonnebloem", "Maitland", "Ndabeni", "Hout Bay", "Fish Hoek", "Simon's Town",
          # UCT upper campus, where the vehicle is tested (Photon finds each of these first near campus, 25 Oct)
          "Menzies Building", "R W James Building", "New Engineering Building", "Snape Building", "Jameson Hall",
          "Sarah Baartman Hall", "Leslie Social Sciences Building", "Chancellor Oppenheimer Library", "Steve Biko Students Union",
          "Kramer Law Building", "Hoerikwaggo Building", "PD Hahn Building", "John Day Building", "Molly Blackburn Hall",
          "Upper Campus", "Middle Campus", "Lower Campus", "UCT")
PLACE_CUTOFF = 0.75


def correct_place(said, names=PLACES):
    """The name in names closest in spelling to said, if at least PLACE_CUTOFF alike; otherwise said unchanged."""
    import difflib
    key = re.sub(r"[^a-z]", "", said.lower())
    best, score = said, 0.0
    for n in names:
        r = difflib.SequenceMatcher(None, key, re.sub(r"[^a-z]", "", n.lower())).ratio()
        if r > score:
            best, score = n, r
    return best if score >= PLACE_CUTOFF else said


def enabled():
    return os.environ.get("TUKZIE_SW7_VOICE", "0").strip() == "1"


def normalise(text):
    t = re.sub(r"[^a-z0-9 ]+", " ", str(text or "").lower())
    t = re.sub(r"\s+", " ", t).strip()
    for filler in ("please ", "hey ", "okay ", "ok "):
        if t.startswith(filler):
            t = t[len(filler):]
    return t[:-7].strip() if t.endswith(" please") else t


def parse_intent(text, wake=""):
    """(kind, argument) for one recognised phrase, or None. kind: home, map, rear, front, done, cancel,
    destination (argument: the place as said) or choose (argument: 1 to 3)."""
    t = normalise(text)
    wake = normalise(wake)
    if wake:
        if not (t == wake or t.startswith(wake + " ")):
            return None
        t = t[len(wake):].strip()
    if not t:
        return None
    m = DESTINATION.match(t)
    if m and m.group(1).strip() not in MAP | HOME | REAR | FRONT:   # "go to map" is a page, not a place
        return ("destination", m.group(1).strip())
    m = CHOICE.match(t)
    if m:
        return ("choose", ORDINALS[m.group(1)])
    bare = t
    for v in VERBS:
        if bare.startswith(v):
            bare = bare[len(v):].strip()
            break
    if bare.startswith("the "):
        bare = bare[4:]
    for kind, words in (("rear", REAR), ("front", FRONT), ("home", HOME), ("map", MAP), ("done", DONE),
                        ("cancel", CANCEL), ("greet", GREETING), ("weather", WEATHER), ("alerts", ALERTS),
                        ("battery", BATTERY), ("help", HELP)):
        if t in words or bare in words:
            return (kind, None)
    for pid, words in PAGES.items():
        if t in words or bare in words or bare.removesuffix(" page") in words:
            return ("page", pid)
    return None


class VoiceControl(QObject):
    heard = Signal(str)              # a final phrase from the listener thread, handled on the GUI thread

    def __init__(self, main, speed_fn=None, clock=time.monotonic):
        super().__init__(main)
        self.main = main
        self.clock = clock
        self.speed_fn = speed_fn or self._speed
        self.wake = os.environ.get("TUKZIE_SW7_VOICE_WAKE", "")
        self.reverse = False
        self.reverse_since = 0.0
        self.last_command = 0.0
        self.fast_since = None
        self.choosing_until = 0.0
        self.asking_until = 0.0
        self.choices = []            # (label, item) read out for the current destination search
        self.query = ""
        self.log = []                # (time, text, intent) for the tests and the bench check
        self.heard.connect(self.handle_text)
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._wait = QTimer(self)    # waits for suggestions after a destination is searched
        self._wait.setInterval(250)
        self._wait.timeout.connect(self._poll_suggestions)
        self._wait_until = 0.0

    # ---- dashboard hooks -------------------------------------------------------------------------------------------
    def _speed(self):
        st = getattr(self.main, "current_state", None)
        v = getattr(st, "speed_kmh", None)
        return float(v) if isinstance(v, (int, float)) else 0.0

    def _nav(self):
        return getattr(self.main, "page_by_id", {}).get("navigation")

    def _page(self, pid):
        self.main.switch_page_id(pid)

    def _side(self, side):
        dual = getattr(self.main, "sw7_dual", None)
        if dual is not None:
            dual.set_side(side, user=True)

    def say(self, text):
        voice = getattr(getattr(self.main, "asis", None), "voice", None)
        if voice is None or Severity is None:
            return
        try:
            voice.speak(text, CATEGORY, Severity.ADVICE, expires_at=self.clock() + 8.0, cooldown_s=0)
        except Exception:
            pass

    # ---- commands --------------------------------------------------------------------------------------------------
    def handle_text(self, text):
        intent = parse_intent(text, self.wake)
        if intent is None and self.asking_until > self.clock() and normalise(text):
            intent = ("destination", normalise(text))   # the answer to "Where are we headed today?"
        self.asking_until = 0.0
        self.log.append((self.clock(), text, intent))
        if intent is None:
            return None
        kind, arg = intent
        self.last_command = self.clock()
        if kind == "choose":
            if self.choosing_until > self.clock() and self.choices:
                self._choose(arg)
            return intent
        if kind == "home" or (kind == "done" and self.reverse):
            self._end_reverse()
            self._page("driving")
            self.say("Home")
        elif kind == "map":
            self._page("navigation")
            self.say("Map")
        elif kind == "rear":
            self.reverse, self.reverse_since, self.fast_since = True, self.clock(), None
            self._page("sensors")
            self._side("rear")
            self.say("Rear camera")
        elif kind == "front":
            self._end_reverse()
            self._page("sensors")
            self._side("front")
            self.say("Front camera")
        elif kind == "cancel":
            self.choosing_until, self.choices = 0.0, []
            self._end_reverse()
            self.say("Cancelled")
        elif kind == "destination":
            self._search(arg)
        elif kind == "page":
            self._page(arg)
            self.say(arg.capitalize() if arg != "sensors" else "Surroundings")
        elif kind == "greet":
            self.asking_until = self.clock() + ASK_WINDOW_S
            self.say("Hello. Where are we headed today?")
        elif kind == "weather":
            self.say(self.weather_text())
        elif kind == "alerts":
            self.say(self.alerts_text())
        elif kind == "battery":
            self.say(self.battery_text())
        elif kind == "help":
            self.say("You can say home, map, rear camera, front camera, a page name, weather, alerts, battery level, "
                     "or go to, and a place.")
        return intent

    # ---- spoken information ----------------------------------------------------------------------------------------
    def weather_text(self):
        rep = getattr(getattr(self.main, "sw7_weather", None), "report", None)
        if rep is None:
            return "No weather report yet."
        parts = [f"{rep.condition}, {round(rep.temp_c)} degrees"]
        if rep.wind_kmh is not None:
            parts.append(f"wind {round(rep.wind_kmh)} kilometres per hour")
        return ", ".join(parts) + (f", in {rep.place}." if rep.place else ".")

    def alerts_text(self):
        banner = getattr(self.main, "hazard_banner", None)
        label = getattr(banner, "text", None)
        if banner is not None and banner.isVisible() and label is not None and label.text().strip():
            return label.text().strip().capitalize() + "."
        return "No alerts."

    def battery_text(self):
        soc = getattr(getattr(self.main, "current_state", None), "soc_pct", None)
        if not isinstance(soc, (int, float)):
            return "Battery level unavailable."
        return f"Battery at {round(soc)} percent."

    def _end_reverse(self):
        self.reverse, self.fast_since = False, None

    def _search(self, place):
        nav = self._nav()
        if nav is None or getattr(nav, "destination", None) is None:
            return
        self._page("navigation")
        recents = getattr(getattr(getattr(nav, "_sw7_search", None), "recents", None), "items", None) or []
        names = PLACES + tuple(str(r.get("name") or "") for r in recents if isinstance(r, dict) and r.get("name"))
        place = correct_place(place, names)
        self.query, self.choices, self.choosing_until = place, [], 0.0
        nav.destination.setFocus()
        nav.destination.setText(place)
        search = getattr(nav, "_sw7_search", None)  # the type-ahead runs on typing (textEdited), not on setText
        if search is not None:
            search.request(place)
        else:
            nav.destination.textEdited.emit(place)
        self._wait_until = self.clock() + SUGGESTION_WAIT_S
        self._wait.start()

    def _choosable(self):
        nav = self._nav()
        lst = getattr(nav, "suggestions", None)
        if lst is None:
            return []
        try:
            from .sw7_search import ROLE_KIND, ROLE_TITLE, CHOOSABLE
        except ImportError:
            ROLE_KIND = ROLE_TITLE = CHOOSABLE = None
        out = []
        for i in range(lst.count()):
            item = lst.item(i)
            if ROLE_KIND is not None and item.data(ROLE_KIND) not in CHOOSABLE:
                continue
            title = item.data(ROLE_TITLE) if ROLE_TITLE is not None else None   # the short name, for speech
            out.append(((title or item.text()).split("\n")[0].split(",")[0].strip(), item))
        return out

    def _poll_suggestions(self):
        rows = self._choosable()
        if rows or self.clock() >= self._wait_until:
            self._wait.stop()
            if not rows:
                self.say(f"No places found for {self.query}")
                return
            self.choices = rows[:READ_OUT]
            self.choosing_until = self.clock() + CHOICE_WINDOW_S
            words = ("one", "two", "three")
            self.say(". ".join(f"Option {words[i]}, {label}" for i, (label, _) in enumerate(self.choices))
                     + ". Which one?")

    def _choose(self, n):
        if not 1 <= n <= len(self.choices):
            self.say(f"There is no option {n}")
            return
        label, item = self.choices[n - 1]
        self.choosing_until, self.choices = 0.0, []
        nav = self._nav()
        search = getattr(nav, "_sw7_search", None)
        if search is not None:
            search._choose(item)
        else:
            nav._choose_suggestion(item)
        self.say(f"Going to {label}")

    # ---- reverse mode ends by itself -------------------------------------------------------------------------------
    def _tick(self):
        if not self.reverse:
            return
        now = self.clock()
        if self.speed_fn() >= FORWARD_KMH:
            self.fast_since = self.fast_since if self.fast_since is not None else now
            if now - self.fast_since >= FORWARD_HOLD_S:
                self._leave_reverse()
                return
        else:
            self.fast_since = None
        if now - max(self.reverse_since, self.last_command) >= REVERSE_TIMEOUT_S:
            self._leave_reverse()

    def _leave_reverse(self):
        self._end_reverse()
        self._side("front")
        self._page("driving")


def command_grammar():
    """Every command phrase, for a second recogniser that knows only these (Vosk grammar mode, with "[unk]" for
    anything else). It is far more reliable on short commands than free recognition, which is kept for place names."""
    words = set()
    for group in (HOME, MAP, REAR, FRONT, DONE, CANCEL, GREETING, WEATHER, ALERTS, BATTERY, HELP, *PAGES.values()):
        for w in group:
            words.add(w)
            for v in VERBS:
                words.add(v + w)
    for o in ("first", "second", "third", "one", "two", "three"):
        words.update({o, f"{o} one", f"option {o}", f"number {o}", f"the {o} one"})
    return sorted(words) + ["[unk]"]


def pick_text(command_text, free_text, wake=""):
    """The phrase to act on, from the command recogniser and the free one on the same audio: a destination heard by
    the free recogniser wins (place names are not in the grammar); otherwise a command the grammar recogniser parsed;
    otherwise the free text."""
    free = parse_intent(free_text, wake)
    if free and free[0] == "destination":
        return free_text
    if command_text and "[unk]" not in command_text and parse_intent(command_text, wake):
        return command_text
    return free_text


class VoskListener(threading.Thread):
    """Microphone to final phrases, on its own thread. Needs the vosk and sounddevice packages and a model folder;
    if any is missing, available() says why and the dashboard runs without voice."""

    def __init__(self, on_text, model_path=None, rate=16000):
        super().__init__(daemon=True, name="sw7-voice")
        self.on_text, self.rate = on_text, rate
        self.model_path = model_path or os.environ.get(
            "TUKZIE_VOSK_MODEL", os.path.expanduser("~/vosk-model-small-en-us-0.15"))
        self.stop_flag = threading.Event()
        self.error = None

    def available(self):
        try:
            import vosk  # noqa: F401
            import sounddevice  # noqa: F401
        except ImportError as e:
            return f"missing package: {e.name}"
        if not os.path.isdir(self.model_path):
            return f"no model at {self.model_path}"
        return None

    def run(self):
        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model, SetLogLevel
            SetLogLevel(-1)
            model = Model(self.model_path)
            rec = KaldiRecognizer(model, self.rate)                                   # free: place names
            cmd = KaldiRecognizer(model, self.rate, json.dumps(command_grammar()))    # commands only
            with sd.RawInputStream(samplerate=self.rate, blocksize=4000, dtype="int16", channels=1) as stream:
                while not self.stop_flag.is_set():
                    data, _ = stream.read(4000)
                    cmd.AcceptWaveform(bytes(data))
                    if rec.AcceptWaveform(bytes(data)):
                        free_text = json.loads(rec.Result()).get("text", "")
                        command_text = json.loads(cmd.FinalResult()).get("text", "")
                        if hasattr(cmd, "Reset"):
                            cmd.Reset()
                        text = pick_text(command_text, free_text)
                        if text:
                            self.on_text(text)
        except Exception as e:                       # no microphone, device busy: the dashboard carries on
            self.error = repr(e)


def install(main):
    """Called at the end of DashboardMain.__init__ (dashboard_patches). Off unless TUKZIE_SW7_VOICE=1."""
    if not enabled() or getattr(main, "_sw7_voice", None) is not None:
        return getattr(main, "_sw7_voice", None)
    vc = VoiceControl(main)
    main._sw7_voice = vc
    listener = VoskListener(vc.heard.emit)
    reason = listener.available()
    if reason is None:
        listener.start()
    vc.listener, vc.listener_reason = listener, reason
    return vc
