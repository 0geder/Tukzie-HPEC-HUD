"""
Virtual Tukzie bench-test harness (v1).

Reads the real [RIDE1]/[RIDE2] ride-characterisation lines that the SW-7
ESP32-S3 firmware already streams over serial from the physically connected
MPU6050s, and classifies each window against provisional road-event
signatures. Does not fake or inject any sensor data - the IMUs stay real and
in the loop; this only interprets what they genuinely report.

Thresholds below are provisional (no real vehicle field-test data exists yet
to calibrate against). They were picked from the observed stationary-bench
baseline (p2p ~0.15-0.25, crest ~1.01) with headroom above it, and should be
tightened once real ride data is available.

Usage:
    python live_classifier.py [COM_PORT] [BAUD]
    (defaults: COM15, 115200)
"""

import re
import sys
import time
from collections import deque

import serial

RIDE_RE = re.compile(
    r"\[RIDE(?P<imu>\d)\]\s+n=(?P<n>\d+)\s+rms=(?P<rms>[\d.]+)\s+"
    r"std=(?P<std>[\d.]+)\s+p2p=(?P<p2p>[\d.]+)\s+crest=(?P<crest>[\d.]+)\s+"
    r"jerk=(?P<jerk>[\d.]+)\s+crossings=(?P<crossings>\d+)"
)

# Provisional thresholds - see module docstring.
P2P_MODERATE = 1.5
P2P_SHARP = 6.0
CREST_IMPULSIVE = 2.0


def classify(p2p: float, crest: float) -> str:
    if p2p < P2P_MODERATE:
        return "quiescent"
    if p2p < P2P_SHARP:
        return "moderate vibration"
    if crest > CREST_IMPULSIVE:
        return "sharp jerk event"
    return "sustained large motion"


def main() -> None:
    port = sys.argv[1] if len(sys.argv) > 1 else "COM15"
    baud = int(sys.argv[2]) if len(sys.argv) > 2 else 115200

    history: dict[str, deque] = {"1": deque(maxlen=5), "2": deque(maxlen=5)}

    print(f"Virtual Tukzie bench-test harness - listening on {port} @ {baud}")
    print("Move/tap the real IMUs by hand to see live classification.")
    print("Ctrl+C to stop.\n")

    with serial.Serial(port, baud, timeout=1) as ser:
        while True:
            try:
                raw = ser.readline()
            except serial.SerialException as exc:
                print(f"[serial error] {exc}")
                break
            if not raw:
                continue
            line = raw.decode(errors="replace").strip()
            match = RIDE_RE.search(line)
            if not match:
                continue

            imu = match.group("imu")
            p2p = float(match.group("p2p"))
            crest = float(match.group("crest"))
            rms = float(match.group("rms"))
            jerk = float(match.group("jerk"))
            crossings = int(match.group("crossings"))

            label = classify(p2p, crest)
            history[imu].append(label)

            ts = time.strftime("%H:%M:%S")
            print(
                f"[{ts}] IMU{imu}: rms={rms:6.3f} p2p={p2p:6.3f} "
                f"crest={crest:5.3f} jerk={jerk:6.3f} crossings={crossings:2d}"
                f"  ->  {label}"
            )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
