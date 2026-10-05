#!/usr/bin/env python3
"""SW-7 Pi 5 beacon: announce the dashboard Pi on every network it is on.

The laptop's pre-test check (BenchTest/sw7_check.py) listens for it on UDP
port 50808 (the same port as the Pi 4 bridge beacon; the "sw7" field tells
them apart), so Pirate5 is found within a few seconds on any network, even a
phone hotspot that drops pings and mDNS between clients (seen on 3 Oct 2026).

Payload, one JSON object every 2 s:
  {"sw7": "pi5", "v": 1, "host": "Pirate5", "dashboard_commit": "<hash or null>", "seq": 12}
The receiver takes the address from the packet's source, not the payload.

Standard library only. Started by start_sw7_dashboard.sh (one instance).
"""
import json
import os
import socket
import subprocess
import time

PORT = int(os.environ.get("TUKZIE_BEACON_PORT", "50808"))
INTERVAL_S = 2.0


def broadcast_addresses():
    """Broadcast address of every IPv4 interface, plus 255.255.255.255."""
    targets = {"255.255.255.255"}
    try:
        out = subprocess.run(["ip", "-j", "-4", "addr"], capture_output=True, text=True, timeout=3).stdout
        for iface in json.loads(out or "[]"):
            for a in iface.get("addr_info", []):
                if a.get("broadcast"):
                    targets.add(a["broadcast"])
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return sorted(targets)


def deployed_commit():
    try:
        return open(os.path.expanduser("~/Dashboard_sw7/DEPLOYED_COMMIT")).read().strip()[:12] or None
    except OSError:
        return None


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    seq = 0
    while True:
        payload = json.dumps({"sw7": "pi5", "v": 1, "host": socket.gethostname(),
                              "dashboard_commit": deployed_commit(), "seq": seq}).encode()
        for target in broadcast_addresses():
            try:
                s.sendto(payload, (target, PORT))
            except OSError:
                pass        # no network yet, or this interface went away: try again next time
        seq += 1
        time.sleep(INTERVAL_S)


if __name__ == "__main__":
    main()
