#!/usr/bin/env python3
"""
Phone GPS bridge for the Pi 5: a phone's GNSS as the speed and position source while the vehicle's own receiver has
no fix (23 Oct 2026). Standard library only.

Input: NMEA 0183 sentences from a phone app, either way round (both can run at once):
  UDP  the app sends to this Pi, port --udp-port (default 10110, the NMEA-over-IP port). Android: "GPSd Forwarder".
  TCP  the app is a server on the phone and this bridge connects to it: --tcp HOST:PORT[,HOST:PORT...]. HOST
       "gateway" means the default gateway, which on a phone hotspot is the phone itself. Android: "Share GPS"
       (port 50000 by default); iPhone: "GPS2IP" (port 11123 by default).
Every sentence with a valid checksum is logged with this Pi's clock (chrony-synced to the Pi 4) to
--log-dir/phone_gps_YYYY-MM-DD_HHMMSS.txt, one line "<unix time> <sentence>", so the phone's speed can be aligned
with the IMU streams afterwards. Sentences with a bad checksum are counted and dropped.

Output: GET http://<this Pi>:--http-port/gps (default 8084) answers JSON:
  {"fix": bool, "lat": deg, "lon": deg, "speed_kmh": km/h, "course_deg": deg, "alt_m": m, "sats": n, "hdop": x,
   "age_ms": ms since the last valid RMC, "source": "phone", "counts": {...}}
fix is true only for an RMC with status A; lat/lon/speed/course come from RMC, alt/sats/hdop from GGA. speed_kmh is
RMC speed over ground (knots) x 1.852. GET / gives a one-screen text status.

Run:  python3 phone_gps_bridge.py [--udp-port 10110] [--tcp gateway:50000] [--http-port 8084] [--log-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KNOT_KMH = 1.852


def nmea_checksum_ok(line: str) -> bool:
    """True for "$...*hh" whose XOR of the characters between $ and * equals hh."""
    if not line.startswith("$") or "*" not in line:
        return False
    body, _, cs = line[1:].partition("*")
    try:
        want = int(cs[:2], 16)
    except ValueError:
        return False
    got = 0
    for ch in body:
        got ^= ord(ch)
    return got == want


def _deg(value: str, hemi: str):
    """ddmm.mmmm / dddmm.mmmm plus N/S/E/W to signed decimal degrees, or None."""
    if not value or hemi not in "NSEW" or not hemi:
        return None
    try:
        v = float(value)
    except ValueError:
        return None
    d = int(v // 100)
    out = d + (v - 100 * d) / 60.0
    return -out if hemi in "SW" else out


def _float(s):
    try:
        return float(s) if s != "" else None
    except ValueError:
        return None


def parse_sentence(line: str):
    """Parse one checked NMEA sentence. Returns ("RMC", dict), ("GGA", dict) or (None, None).
    Talker IDs GP, GN, GL, GA, BD and so on are all accepted."""
    body = line[1:].partition("*")[0]
    f = body.split(",")
    kind = f[0][2:] if len(f[0]) >= 5 else ""
    if kind == "RMC" and len(f) >= 9:
        valid = f[2] == "A"
        spd = _float(f[7])
        return "RMC", {
            "fix": valid,
            "lat": _deg(f[3], f[4]) if valid else None,
            "lon": _deg(f[5], f[6]) if valid else None,
            "speed_kmh": spd * KNOT_KMH if (valid and spd is not None) else None,
            "course_deg": _float(f[8]) if valid else None,
            "utc": f[1],
        }
    if kind == "GGA" and len(f) >= 10:
        q = int(f[6]) if f[6].isdigit() else 0
        return "GGA", {
            "quality": q,
            "sats": int(f[7]) if f[7].isdigit() else None,
            "hdop": _float(f[8]),
            "alt_m": _float(f[9]) if q > 0 else None,
        }
    return None, None


class State:
    def __init__(self, log_dir: str):
        self.lock = threading.Lock()
        self.rmc = None
        self.rmc_t = None
        self.gga = None
        self.counts = {"lines": 0, "bad_checksum": 0, "rmc": 0, "gga": 0, "udp": 0, "tcp": 0}
        self.tcp_status = {}          # spec -> status
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, time.strftime("phone_gps_%Y-%m-%d_%H%M%S.txt"))
        self._log = open(self.log_path, "a", encoding="ascii", errors="replace", buffering=1)

    def feed(self, raw: bytes, via: str):
        now = time.time()
        for part in raw.replace(b"\r", b"\n").split(b"\n"):
            line = part.strip().decode("ascii", "replace")
            if not line:
                continue
            with self.lock:
                self.counts["lines"] += 1
                self.counts[via] += 1
                if not nmea_checksum_ok(line):
                    self.counts["bad_checksum"] += 1
                    continue
                self._log.write(f"{now:.3f} {line}\n")
                kind, data = parse_sentence(line)
                if kind == "RMC":
                    self.counts["rmc"] += 1
                    self.rmc, self.rmc_t = data, now
                elif kind == "GGA":
                    self.counts["gga"] += 1
                    self.gga = data

    def snapshot(self) -> dict:
        with self.lock:
            rmc, gga = self.rmc or {}, self.gga or {}
            age = None if self.rmc_t is None else int((time.time() - self.rmc_t) * 1000)
            return {
                "fix": bool(rmc.get("fix")), "lat": rmc.get("lat"), "lon": rmc.get("lon"),
                "speed_kmh": rmc.get("speed_kmh"), "course_deg": rmc.get("course_deg"),
                "alt_m": gga.get("alt_m"), "sats": gga.get("sats"), "hdop": gga.get("hdop"),
                "age_ms": age, "source": "phone", "counts": dict(self.counts), "tcp": dict(self.tcp_status),
                "log": self.log_path,
            }


def default_gateway():
    try:
        out = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, timeout=2).stdout
        for line in out.splitlines():
            parts = line.split()
            if "via" in parts:
                return parts[parts.index("via") + 1]
    except Exception:
        pass
    return None


def udp_loop(state: State, port: int):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    while True:
        data, _ = s.recvfrom(4096)
        state.feed(data, "udp")


def tcp_loop(state: State, spec: str):
    host_spec, _, port_s = spec.rpartition(":")
    port = int(port_s)
    while True:
        host = default_gateway() if host_spec == "gateway" else host_spec
        if not host:
            state.tcp_status[spec] = "no gateway"
            time.sleep(3)
            continue
        try:
            state.tcp_status[spec] = f"connecting {host}:{port}"
            with socket.create_connection((host, port), timeout=5) as c:
                c.settimeout(10)
                state.tcp_status[spec] = f"connected {host}:{port}"
                while True:
                    data = c.recv(4096)
                    if not data:
                        break
                    state.feed(data, "tcp")
        except OSError as e:
            state.tcp_status[spec] = f"retrying {host}:{port} ({e.__class__.__name__})"
        time.sleep(3)


def make_handler(state: State):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype):
            b = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            snap = state.snapshot()
            if self.path.split("?")[0] in ("/gps", "/telemetry"):
                self._send(200, json.dumps(snap), "application/json")
            elif self.path == "/":
                spd = "-" if snap["speed_kmh"] is None else f"{snap['speed_kmh']:.1f} km/h"
                txt = (f"SW-7 phone GPS bridge\nfix: {snap['fix']}, speed {spd}, sats {snap['sats']}, "
                       f"hdop {snap['hdop']}, age {snap['age_ms']} ms\nlat {snap['lat']}, lon {snap['lon']}\n"
                       f"tcp: {snap['tcp']}\ncounts: {snap['counts']}\nlog: {snap['log']}\nJSON: /gps\n")
                self._send(200, txt, "text/plain; charset=utf-8")
            else:
                self._send(404, "not found\n", "text/plain")
    return H


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--udp-port", type=int, default=10110, help="0 turns UDP off")
    ap.add_argument("--tcp", default="", help="HOST:PORT of a phone NMEA server; HOST 'gateway' = the hotspot phone")
    ap.add_argument("--http-port", type=int, default=8084)
    ap.add_argument("--log-dir", default=os.path.expanduser("~/roadtest/phone_gps"))
    a = ap.parse_args()
    state = State(a.log_dir)
    if a.udp_port:
        threading.Thread(target=udp_loop, args=(state, a.udp_port), daemon=True).start()
    for spec in filter(None, (x.strip() for x in a.tcp.split(","))):
        threading.Thread(target=tcp_loop, args=(state, spec), daemon=True).start()
    print(f"Phone GPS bridge on http://0.0.0.0:{a.http_port}/gps, UDP {a.udp_port or 'off'}, "
          f"TCP {a.tcp or 'off'}, log {state.log_path}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", a.http_port), make_handler(state)).serve_forever()


if __name__ == "__main__":
    main()
