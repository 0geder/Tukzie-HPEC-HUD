"""Pre-download OpenStreetMap tiles for the area the tuk-tuk drives in, into the
cache sw7_tile_map.py reads (~/.cache/sw7_tiles/{z}/{x}/{y}.png), so the map
appears at once instead of loading tile by tile over the hotspot.

Run on the Pi 5 (needs internet):
  python3 prefetch_tiles.py                 # UCT and the southern suburbs, zoom 11 to 16
  python3 prefetch_tiles.py --bbox S W N E --zmax 16 --dry-run

Kept inside the OpenStreetMap tile usage policy
(https://operations.osmfoundation.org/policies/tiles/): a small area only,
no bulk download at zoom 17 or higher (refused here), two downloads at a time,
the same identifying User-Agent as the dashboard, and tiles already cached
within 30 days are skipped. Zoom 17 to 19 still load on demand while driving;
until they arrive the map scales up the zoom 16 tile.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
USER_AGENT = "TUKZIE-SW7-dashboard/1.0 (UCT student project)"
CACHE = os.path.expanduser(os.environ.get("TUKZIE_TILE_CACHE", "").strip() or "~/.cache/sw7_tiles")
MAX_AGE_S = 30 * 24 * 3600
MAX_TILES = 2000                       # refuse anything that is not a small area
# Rondebosch, UCT, Observatory, Claremont, Newlands, Mowbray (south, west, north, east)
DEFAULT_BBOX = (-34.000, 18.400, -33.900, 18.520)


def tile_xy(lat, lon, z):
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    r = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(r)) / math.pi) / 2.0 * n)
    return max(0, min(n - 1, x)), max(0, min(n - 1, y))


def tiles_for(bbox, zmin, zmax):
    s, w, n, e = bbox
    for z in range(zmin, zmax + 1):
        x0, y0 = tile_xy(n, w, z)
        x1, y1 = tile_xy(s, e, z)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                yield z, x, y


def fresh(path):
    try:
        return time.time() - os.path.getmtime(path) < MAX_AGE_S and os.path.getsize(path) > 0
    except OSError:
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("S", "W", "N", "E"), default=DEFAULT_BBOX)
    ap.add_argument("--zmin", type=int, default=11)
    ap.add_argument("--zmax", type=int, default=16)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.zmax > 16:
        sys.exit("Refused: the OSM tile policy forbids bulk downloads at zoom 17 or higher.")
    todo = [t for t in tiles_for(a.bbox, a.zmin, a.zmax)]
    if len(todo) > MAX_TILES:
        sys.exit(f"Refused: {len(todo)} tiles is not a small area (limit {MAX_TILES}). Shrink the box.")
    need = [t for t in todo if not fresh(os.path.join(CACHE, str(t[0]), str(t[1]), f"{t[2]}.png"))]
    print(f"{len(todo)} tiles in the area, {len(todo) - len(need)} already cached, {len(need)} to download")
    if a.dry_run or not need:
        return
    lock = threading.Lock()
    done = {"ok": 0, "fail": 0, "bytes": 0}

    def fetch(t):
        z, x, y = t
        path = os.path.join(CACHE, str(z), str(x), f"{y}.png")
        req = urllib.request.Request(URL.format(z=z, x=x, y=y), headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
            if not data.startswith(b"\x89PNG"):
                raise ValueError("not a PNG")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
            with lock:
                done["ok"] += 1; done["bytes"] += len(data)
        except Exception as exc:          # one bad tile must not stop the rest
            with lock:
                done["fail"] += 1
            print(f"  failed {z}/{x}/{y}: {exc}")
        with lock:
            n = done["ok"] + done["fail"]
            if n % 50 == 0 or n == len(need):
                print(f"  {n}/{len(need)} ({done['bytes'] / 1e6:.1f} MB)", flush=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(fetch, need))
    print(f"Done in {time.time() - t0:.0f} s: {done['ok']} saved, {done['fail']} failed, "
          f"{done['bytes'] / 1e6:.1f} MB, cache {CACHE}")


if __name__ == "__main__":
    main()
