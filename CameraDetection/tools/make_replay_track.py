#!/usr/bin/env python3
"""
Build a GPS replay file of DASH lines along a real road route, for bench
testing the dashboard's moving map without riding the kart.

This is generated data, not a recording. Every line it writes says so:
fw is "0.7.1-replay", the file starts with a "#" header naming the source,
and the bridge marks /telemetry with "replay": true when it plays the file
(telemetry_bridge.py --replay). It must never be presented as a ride.

The route geometry comes from the public OSRM demo server, which routes on
OpenStreetMap data (c) OpenStreetMap contributors, ODbL. The track follows
that geometry at a target speed (default 18 km/h), slowing at sharp turns,
sampled once a second like the ESP32's DASH line. Course is the bearing
between consecutive points. Fields and formats match firmware v0.7.1
(TELEMETRY_LINK.md section 1, plus crs and alt). Battery, current, voltage
and RPM are null because there is nothing real to put there.

Usage:
  python tools/make_replay_track.py
  python tools/make_replay_track.py --start -33.9577,18.4612 --end -33.9637,18.4725 \
      --speed-kmh 18 --out tests/replay_uct_route.txt
"""
import argparse
import json
import math
import os
import random
import sys
import urllib.request

OSRM_URL = ("https://router.project-osrm.org/route/v1/driving/"
            "{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson")
EARTH_R = 6371008.8          # mean Earth radius, m
KNOTS_PER_MPS = 1.0 / 0.514444
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "..", "tests", "replay_uct_route.txt")


def latlon(text):
    lat, lon = (float(x) for x in text.split(","))
    return lat, lon


def fetch_route(start, end, timeout=20):
    """[(lat, lon), ...] along the OSRM driving route, and its length in m."""
    url = OSRM_URL.format(lat1=start[0], lon1=start[1], lat2=end[0], lon2=end[1])
    req = urllib.request.Request(url, headers={"User-Agent": "SW7-replay-track/1.0 (student project)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RuntimeError("OSRM returned %s" % data.get("code"))
    route = data["routes"][0]
    coords = [(c[1], c[0]) for c in route["geometry"]["coordinates"]]   # GeoJSON is lon,lat
    return coords, float(route["distance"]), url


def dist_m(a, b):
    """Haversine distance between two (lat, lon) points in metres."""
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(h))


def bearing_deg(a, b):
    """Initial bearing from a to b, degrees clockwise from true north, 0 to 360."""
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return math.degrees(math.atan2(y, x)) % 360.0


def turn_deg(b1, b2):
    d = abs(b2 - b1) % 360.0
    return 360.0 - d if d > 180.0 else d


def dedupe(coords):
    out = [coords[0]]
    for c in coords[1:]:
        if dist_m(out[-1], c) > 0.5:
            out.append(c)
    return out


def speed_profile(coords, cum, v_target):
    """Allowed speed (m/s) at each vertex: v_target on straights, slower
    where the heading turns sharply, then limited so the kart can brake
    and accelerate at about 1 m/s^2 between vertices."""
    n = len(coords)
    v = [v_target] * n
    for i in range(1, n - 1):
        t = turn_deg(bearing_deg(coords[i - 1], coords[i]), bearing_deg(coords[i], coords[i + 1]))
        if t > 20.0:
            # 20 deg -> full speed, 90 deg or more -> 35 % of it (about 6 km/h at 18 km/h)
            f = max(0.35, 1.0 - 0.65 * min(1.0, (t - 20.0) / 70.0))
            v[i] = v_target * f
    v[0] = v[-1] = 0.0
    a = 1.0
    for i in range(1, n):        # acceleration limit, forward
        d = cum[i] - cum[i - 1]
        v[i] = min(v[i], math.sqrt(v[i - 1] ** 2 + 2 * a * d))
    for i in range(n - 2, -1, -1):   # braking limit, backward
        d = cum[i + 1] - cum[i]
        v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2 * a * d))
    return v


def point_at(coords, cum, s):
    """(lat, lon) at distance s along the polyline, and the segment index."""
    if s <= 0:
        return coords[0], 0
    if s >= cum[-1]:
        return coords[-1], len(coords) - 2
    lo, hi = 0, len(cum) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if cum[mid] <= s:
            lo = mid
        else:
            hi = mid
    f = (s - cum[lo]) / (cum[hi] - cum[lo])
    a, b = coords[lo], coords[hi]
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), lo


def speed_at(cum, vprof, s):
    if s >= cum[-1]:
        return 0.0
    lo = max(i for i in range(len(cum)) if cum[i] <= s)
    hi = min(lo + 1, len(cum) - 1)
    if cum[hi] == cum[lo]:
        return vprof[lo]
    f = (s - cum[lo]) / (cum[hi] - cum[lo])
    return vprof[lo] + (vprof[hi] - vprof[lo]) * f


def build_track(coords, v_target, dwell_s=3):
    """One sample per second: [(lat, lon, speed_mps, course_deg or None)].
    Starts and ends with a few stationary seconds, as a real ride would."""
    cum = [0.0]
    for i in range(1, len(coords)):
        cum.append(cum[-1] + dist_m(coords[i - 1], coords[i]))
    vprof = speed_profile(coords, cum, v_target)
    samples = []
    for _ in range(dwell_s):
        samples.append((coords[0], 0.0))
    s = 0.0
    while s < cum[-1]:
        v = max(speed_at(cum, vprof, s), 0.8)   # creep off the start line, never stall
        s = min(cum[-1], s + v)
        p, _ = point_at(coords, cum, s)
        samples.append((p, v))
    for _ in range(dwell_s):
        samples.append((coords[-1], 0.0))

    track = []
    last_crs = None
    for i, (p, v) in enumerate(samples):
        crs = None
        if v > 0.3:
            nxt = samples[i + 1][0] if i + 1 < len(samples) else p
            prv = samples[i - 1][0] if i > 0 else p
            a, b = (prv, p) if dist_m(prv, p) > 0.5 else (p, nxt)
            if dist_m(a, b) > 0.5:
                crs = bearing_deg(a, b)
            else:
                crs = last_crs
        # Stationary: the modem reports an empty course field, so null.
        last_crs = crs if crs is not None else last_crs
        track.append((p, v, crs))
    return track, cum[-1]


def dash_lines(track, seed=7, up_ms0=60000):
    rnd = random.Random(seed)
    out = []
    for seq, (p, v, crs) in enumerate(track):
        vib = 0.05 + 0.04 * min(1.0, v / 5.0) + rnd.uniform(0.0, 0.03)
        obj = {
            "seq": seq, "up_ms": up_ms0 + seq * 1000, "fw": "0.7.1-replay",
            "soc": None, "v": None, "i": None, "bms_age_s": None,
            "fix": True, "lat": round(p[0], 6), "lon": round(p[1], 6),
            "spd_raw": round(v * KNOTS_PER_MPS, 3),
            "crs": None if crs is None else round(crs, 1),
            "alt": round(80.0 + rnd.uniform(-0.6, 0.6), 1),
            "vib": round(vib, 3), "vib_dis": round(rnd.uniform(0.005, 0.02), 3),
            "imu_hz": [200.0, 200.0], "drops": [0, 0],
            "rpm": None, "csq": 20, "mqtt": True,
        }
        out.append("DASH " + json.dumps(obj, separators=(",", ":")))
    return out


def main():
    ap = argparse.ArgumentParser(description="Build a labelled GPS replay file (DASH lines) along a real OSRM road route")
    ap.add_argument("--start", type=latlon, default=(-33.9577, 18.4612), metavar="LAT,LON")
    ap.add_argument("--end", type=latlon, default=(-33.9637, 18.4725), metavar="LAT,LON")
    ap.add_argument("--speed-kmh", type=float, default=18.0, help="Target speed on straights (default 18)")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--seed", type=int, default=7, help="Seed for the small vibration and altitude jitter")
    a = ap.parse_args()

    try:
        coords, osrm_len, url = fetch_route(a.start, a.end)
    except Exception as e:
        print("Could not fetch the route from OSRM (%s). Nothing written." % e, file=sys.stderr)
        return 1
    coords = dedupe(coords)
    track, length = build_track(coords, a.speed_kmh / 3.6)
    lines = dash_lines(track, a.seed)

    header = [
        "# SW-7 GPS REPLAY, GENERATED FOR BENCH TESTING. NOT A RECORDED RIDE.",
        "# Made by CameraDetection/tools/make_replay_track.py; fw \"0.7.1-replay\" marks every line.",
        "# Route: OSRM demo server (router.project-osrm.org) driving route on OpenStreetMap data,",
        "#   (c) OpenStreetMap contributors, ODbL 1.0, https://www.openstreetmap.org/copyright",
        "# Start %.6f,%.6f  end %.6f,%.6f  route %.0f m (OSRM %.0f m), %d points at 1 Hz, target %.0f km/h"
        % (a.start[0], a.start[1], a.end[0], a.end[1], length, osrm_len, len(lines), a.speed_kmh),
        "# soc, v, i, rpm are null (no real data); alt is about 80 m with small jitter; vib is made up.",
    ]
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(header + lines) + "\n")
    moving = sum(1 for _, v, _ in track if v > 0.3)
    print("Wrote %s: %d DASH lines (%d s, %d moving), route %.0f m, mean moving speed %.1f km/h"
          % (out, len(lines), len(lines), moving, length, length / max(moving, 1) * 3.6))
    print("Source: %s" % url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
