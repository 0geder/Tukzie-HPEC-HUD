"""Bench check of the dashboard's voice commands (DashboardIntegration/sw7_voice_control.py): recognition and parsing.

Each command is spoken by the Windows speech synthesiser (System.Speech, every installed voice) into a 16 kHz mono
WAV, so no person is recorded. The WAV is recognised by Vosk with the same small English model as the Pi 5, the text
goes through parse_intent, and the result is compared with the intended command. Each phrase is run clean and with
white noise added at 10 dB and 0 dB signal-to-noise ratio, a crude stand-in for wind and road noise (not a vehicle
recording). Reports the share of phrases understood and the recognition time per phrase, per voice and condition.
Synthetic voices are clearer than drivers, so these are upper bounds; a road check with the driver needs a person and is
outside the ethics approval.
Run: python BenchTest/voice_recognition_check.py --model <vosk model folder> [--out <json>]
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import wave

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "DashboardIntegration"))
from sw7_voice_control import command_grammar, correct_place, parse_intent, pick_text  # noqa: E402

PHRASES = [
    ("home", ("home", None)), ("go home", ("home", None)), ("map", ("map", None)), ("open the map", ("map", None)),
    ("reverse", ("rear", None)), ("rear camera", ("rear", None)), ("back camera", ("rear", None)),
    ("front camera", ("front", None)), ("done", ("done", None)), ("cancel", ("cancel", None)),
    ("first one", ("choose", 1)), ("second one", ("choose", 2)), ("option three", ("choose", 3)),
    ("map destination Rondebosch", ("destination", "rondebosch")),
    ("go to Claremont", ("destination", "claremont")),
    ("take me to Observatory", ("destination", "observatory")),
    ("navigate to Cape Town station", ("destination", "cape town station")),
    ("destination Kirstenbosch", ("destination", "kirstenbosch")),
]
PS = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voices = $s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }
$voices -join "|"
"""


def voices():
    r = subprocess.run(["powershell", "-NoProfile", "-Command", PS], capture_output=True, text=True)
    return [v for v in r.stdout.strip().split("|") if v]


def speak(text, voice, path):
    ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          f"$s.SelectVoice('{voice}'); "
          "$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, "
          "[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono); "
          f"$s.SetOutputToWaveFile('{path}', $f); $s.Speak('{text}'); $s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True)


def read_pcm(path):
    with wave.open(path, "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def with_noise(pcm, snr_db, rng):
    x = pcm.astype(np.float64)
    pad = np.zeros(8000)                                   # half a second either side, as a pause in speech
    x = np.concatenate([pad, x, pad])
    p_sig = np.mean(pcm.astype(np.float64) ** 2)
    if snr_db is not None:
        x = x + rng.normal(0.0, np.sqrt(p_sig / 10 ** (snr_db / 10)), x.size)
    return np.clip(x, -32768, 32767).astype(np.int16)


def recognise(model, pcm):
    """(free text, command-recogniser text, seconds for both), as the dashboard's listener runs them."""
    from vosk import KaldiRecognizer
    rec = KaldiRecognizer(model, 16000)
    cmd = KaldiRecognizer(model, 16000, json.dumps(command_grammar()))
    t0 = time.perf_counter()
    for i in range(0, pcm.size, 4000):
        rec.AcceptWaveform(pcm[i:i + 4000].tobytes())
        cmd.AcceptWaveform(pcm[i:i + 4000].tobytes())
    text = json.loads(rec.FinalResult()).get("text", "")
    ctext = json.loads(cmd.FinalResult()).get("text", "")
    return text, ctext, time.perf_counter() - t0


def judged(text, want):
    got = parse_intent(text)
    if got and got[0] == "destination":                     # as the dashboard does before searching
        got = ("destination", correct_place(got[1]).lower())
    return got, (got == tuple(want)) if got else False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default=os.path.join(REPO, "BenchTest", "logs", "voice_2026-10-25", "voice_check.json"))
    args = ap.parse_args()
    from vosk import Model, SetLogLevel
    SetLogLevel(-1)
    model = Model(args.model)
    rng = np.random.default_rng(1)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for voice in voices():
            for text, want in PHRASES:
                path = os.path.join(tmp, "p.wav")
                speak(text, voice, path)
                pcm = read_pcm(path)
                for cond, snr in (("clean", None), ("snr10", 10.0), ("snr0", 0.0)):
                    heard, cheard, dt = recognise(model, with_noise(pcm, snr, rng))
                    got_free, ok_free = judged(heard, want)
                    chosen = pick_text(cheard, heard)
                    got, ok = judged(chosen, want)
                    rows.append({"voice": voice, "condition": cond, "said": text, "heard": heard,
                                 "command_heard": cheard, "chosen": chosen, "intent": got, "want": want,
                                 "ok": ok, "ok_free_only": ok_free,
                                 "seconds": round(dt, 3), "audio_s": round(pcm.size / 16000 + 1.0, 2)})
                    print(f"{voice[:18]:18s} {cond:5s} {'ok ' if ok else 'BAD'} (free {'ok ' if ok_free else 'BAD'}) "
                          f"{text!r} -> {chosen!r}")
    summary = {}
    for r in rows:
        k = f"{r['voice']} | {r['condition']}"
        s = summary.setdefault(k, {"n": 0, "ok": 0, "ok_free_only": 0, "seconds": []})
        s["n"] += 1; s["ok"] += r["ok"]; s["ok_free_only"] += r["ok_free_only"]; s["seconds"].append(r["seconds"])
    for k, s in summary.items():
        s["share_ok"] = round(s["ok"] / s["n"], 3)
        s["median_s"] = float(np.median(s.pop("seconds")))
        print(f"{k}: {s['ok']}/{s['n']} understood with the command recogniser ({s['ok_free_only']} free only), "
              f"median {s['median_s']:.3f} s")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump({"rows": rows, "summary": summary}, open(args.out, "w"), indent=1)
    print("saved", args.out)


if __name__ == "__main__":
    main()
