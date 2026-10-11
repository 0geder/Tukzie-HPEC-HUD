"""SW-7: spoken turn-by-turn directions from the map's turn banner, through the team's voice system.

The map (sw7_tile_map) knows the next manoeuvres and the distance to each, for a real drive or the simulated drive.
Every half second this reads them and, like a phone's navigation, says:
  - when a route starts: "Continue for 300 metres, then turn right onto Station Road";
  - an early prompt about EARLY_M before a turn: "In 200 metres, turn right onto Station Road";
  - a near prompt about NEAR_M before it: "Turn right onto Station Road", merged with the next one when that
    follows within CHAIN_M ("Turn right onto Station Road, then turn left onto Main Road");
  - "You have arrived at your destination" at the end.
Each phrase is said once per manoeuvre and expires if the queue delays it past its use. Speech goes through
dashboard.asis.voice (asis/voice_manager.VoiceManager), so the team's voice choice, volume and mute apply.
"""
import time

from PySide6.QtCore import QObject, QTimer

try:
    from ..asis.models import Severity
except ImportError:
    Severity = None

EARLY_M = 200.0        # about 30 s ahead at the trike's 25 km/h
NEAR_M = 45.0          # about 6 s ahead, leaving time for the speech to be made
CHAIN_M = 80.0         # a following turn this close is announced with the near prompt
ARRIVE_M = 25.0
CATEGORY = "SW7_NAV"


def distance_text(m):
    m = max(0.0, float(m))
    if m >= 1000:
        return f"{m / 1000:.1f} kilometres"
    return f"{max(50, int(round(m / 50.0)) * 50)} metres"


def _lower_first(text):
    return text[:1].lower() + text[1:] if text else text


class VoiceGuide(QObject):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self._plan = None
        self._said = set()
        self._last_along = 0.0
        self._was_sim = False
        self.spoken = []                     # (time, text) of what was sent, for tests and the log
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    @property
    def map(self):
        return getattr(getattr(self.main, "navigation", None), "map", None)

    @property
    def voice(self):
        return getattr(getattr(self.main, "asis", None), "voice", None)

    def _say(self, key, text, life_s):
        if key in self._said:
            return
        self._said.add(key)
        v = self.voice
        if v is None or Severity is None:
            return
        self.spoken.append((time.monotonic(), text))
        try:
            v.speak(text, CATEGORY, Severity.ADVICE, expires_at=time.monotonic() + life_s, cooldown_s=0)
        except Exception as exc:              # speech must never break navigation
            print(f"[SW-7] voice guidance: {exc}")

    def tick(self):
        m = self.map
        if m is None or not getattr(m, "navigating", False):
            self._plan, self._said, self._was_sim = None, set(), False
            return
        plan = id(m._maneuvers)
        along = getattr(m, "_along_m", None) or 0.0
        simulating = bool(getattr(m, "simulating", False))
        # new route, a simulation just started, or back along the route by more than 30 m (rerouted): start again
        if plan != self._plan or (simulating and not self._was_sim) or along < self._last_along - 30.0:
            self._plan, self._said = plan, set()
        self._last_along, self._was_sim = along, simulating
        ahead = m.next_maneuvers(2)
        if not ahead:
            return
        man, dist = ahead[0]
        at = round(man["at_m"], 1)
        if man["kind"] == "arrive":
            if dist <= ARRIVE_M:
                self._say(("arrive", at), "You have arrived at your destination.", 10)
            elif dist <= EARLY_M:
                self._say(("early", at), f"In {distance_text(dist)}, you will arrive at your destination.", 8)
            elif not self._said:
                self._say(("start", at), f"Continue for {distance_text(dist)} to your destination.", 8)
            return
        instr = m._instruction(man)
        if dist <= NEAR_M:
            text = instr
            if len(ahead) > 1 and ahead[1][1] - dist <= CHAIN_M:
                nxt = ahead[1][0]
                then = ("you will arrive at your destination" if nxt["kind"] == "arrive"
                        else _lower_first(m._instruction(nxt)))
                text = f"{instr}, then {then}"
                self._said.add(("early", round(nxt["at_m"], 1)))   # too close for its own early prompt
            self._said.add(("early", at))
            self._say(("near", at), text + ".", 6)
        elif dist <= EARLY_M:
            self._said.add(("start", at))
            self._say(("early", at), f"In {distance_text(dist)}, {_lower_first(instr)}.", 8)
        elif not self._said:
            self._say(("start", at), f"Continue for {distance_text(dist)}, then {_lower_first(instr)}.", 8)


def install(main):
    if getattr(main, "_sw7_voice_guide", None) is None:
        main._sw7_voice_guide = VoiceGuide(main)
    return main._sw7_voice_guide
