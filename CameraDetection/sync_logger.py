"""Pi-side logger for the ESP32 time-sync pulse (test C6).

The ESP32 toggles GPIO15 every 500 ms (SyncTask in main.cpp). This script
records every edge seen on the Pi's GPIO17 with the Pi's monotonic clock
(the same clock Picamera2 uses for frame timestamps) and the wall clock,
and prints a summary of the intervals when it stops.

Wiring: ESP32 J5 pin 5 (GPIO15) to Pi physical pin 11 (GPIO17), and a
ground wire between the boards (any Pi GND pin, e.g. physical pin 9).
Both boards use 3.3 V logic, so no level shifting is needed.

Usage: python3 sync_logger.py [--chip gpiochip0] [--line 17]
                              [--duration 60] [--out sync_edges.csv]
Stop early with Ctrl-C; the CSV is written as it goes.
"""
import argparse
import csv
import statistics
import time

PERIOD_MS = 500.0
TOLERANCE_MS = 20.0


def edges_gpiod_v2(chip, line, stop_at):
    import gpiod
    from gpiod.line import Edge
    settings = gpiod.LineSettings(edge_detection=Edge.BOTH)
    with gpiod.request_lines("/dev/" + chip, consumer="sw7-sync",
                             config={line: settings}) as req:
        while time.monotonic() < stop_at:
            if req.wait_edge_events(timeout=0.5):
                for ev in req.read_edge_events():
                    rising = ev.event_type == ev.Type.RISING_EDGE
                    yield rising, ev.timestamp_ns


def edges_gpiod_v1(chip, line, stop_at):
    import gpiod
    ln = gpiod.Chip(chip).get_line(line)
    ln.request(consumer="sw7-sync", type=gpiod.LINE_REQ_EV_BOTH_EDGES)
    try:
        while time.monotonic() < stop_at:
            if ln.event_wait(sec=0, nsec=500_000_000):
                ev = ln.event_read()
                yield ev.type == gpiod.LineEvent.RISING_EDGE, ev.sec * 10**9 + ev.nsec
    finally:
        ln.release()


def edges_gpiozero(line, stop_at):
    # Fallback: timestamps taken in Python, so they carry more jitter.
    import queue
    from gpiozero import DigitalInputDevice
    q = queue.Queue()
    dev = DigitalInputDevice(line, pull_up=None, active_state=True)
    dev.when_activated = lambda: q.put((True, time.monotonic_ns()))
    dev.when_deactivated = lambda: q.put((False, time.monotonic_ns()))
    try:
        while time.monotonic() < stop_at:
            try:
                yield q.get(timeout=0.5)
            except queue.Empty:
                pass
    finally:
        dev.close()


def edge_source(chip, line, stop_at):
    try:
        import gpiod
        if hasattr(gpiod, "request_lines"):
            return "gpiod v2 (kernel timestamps)", edges_gpiod_v2(chip, line, stop_at)
        return "gpiod v1 (kernel timestamps)", edges_gpiod_v1(chip, line, stop_at)
    except ImportError:
        return "gpiozero (Python timestamps)", edges_gpiozero(line, stop_at)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--chip", default="gpiochip0")
    ap.add_argument("--line", type=int, default=17)
    ap.add_argument("--duration", type=float, default=60.0, help="seconds; 0 runs until Ctrl-C")
    ap.add_argument("--out", default="sync_edges.csv")
    a = ap.parse_args()

    stop_at = time.monotonic() + (a.duration if a.duration > 0 else 10**9)
    name, source = edge_source(a.chip, a.line, stop_at)
    print("sync logger: %s line %d via %s -> %s" % (a.chip, a.line, name, a.out))

    intervals, last_ns, n = [], None, 0
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n", "edge", "t_mono_ns", "t_wall_s", "interval_ms"])
        f.flush()
        try:
            for rising, t_ns in source:
                n += 1
                gap = (t_ns - last_ns) / 1e6 if last_ns is not None else ""
                if gap != "":
                    intervals.append(gap)
                last_ns = t_ns
                w.writerow([n, "rise" if rising else "fall", t_ns, "%.6f" % time.time(),
                            "%.3f" % gap if gap != "" else ""])
                f.flush()
        except KeyboardInterrupt:
            pass

    print("edges: %d" % n)
    if not intervals:
        print("no intervals: check the wire, the ground and that the ESP32 is running")
        return
    odd = [g for g in intervals if abs(g - PERIOD_MS) > TOLERANCE_MS]
    print("interval ms: median %.2f, min %.2f, max %.2f; %d of %d outside %.0f +/- %.0f"
          % (statistics.median(intervals), min(intervals), max(intervals),
             len(odd), len(intervals), PERIOD_MS, TOLERANCE_MS))


if __name__ == "__main__":
    main()
