#!/usr/bin/env python3
"""
SW-7 telemetry bridge for the Pi 4: ESP32 serial and ToF sensors to HTTP.

Implements section 2 of DashboardIntegration/TELEMETRY_LINK.md. It reads
the ESP32's USB serial port, keeps the latest "DASH {json}" line, reads
the three VL53L0X ToF sensors with the code in tof_reader.py, and serves:

  GET /telemetry   application/json, the shape in TELEMETRY_LINK.md:
      {"esp32": {...latest DASH object..., "age_ms": 420} or null,
       "tof": {"left_mm": 812, "ahead_mm": 1490, "right_mm": null,
               "age_ms": 35} or null,
       "bridge": {"version": "1.0", "serial_port": "/dev/ttyACM0",
                  "lines": 1234, "bad_lines": 2,
                  "replay": false, "replay_file": null}}
  GET /            a short plain-text status page

Beacon (TELEMETRY_LINK.md section 4.2): every 2 s a UDP broadcast to port
50808 on 255.255.255.255 and on each IPv4 interface's broadcast address,
payload {"sw7": "pi4", "v": 1, "host": "<hostname>", "camera_port": 8080,
"telemetry_port": 8081, "seq": n}, so the dashboard can find this Pi on
any network. The receiver uses the packet's source address. Interfaces
are looked up again before every send, so a link that comes up later
(the wired sw7-link) is included. Send failures are counted, never
fatal. --no-beacon turns it off.

Counting: "lines" is every line starting with "DASH " that was received,
"bad_lines" is the subset that could not be used (not valid JSON, not a
JSON object, or containing NaN or Infinity). Lines that do not start
with "DASH " (boot log, debug prints) are ignored and not counted.

esp32 is null until the first good line arrives, and again whenever the
serial port is lost (ESP32 unplugged or reset; the ESP32-S3 re-enumerates
on reset). The port is reopened automatically when it comes back. tof is
null with --no-tof, when the sensors or their Python libraries are
absent, or after a read error (the bridge then retries every few
seconds). A reading of 0, about 8190 (nothing in range) or anything at or
above tof_reader.OUT_OF_RANGE_MM becomes null for that sensor.

Only telemetry numbers are handled: no camera frames, no personal data.
Nothing is written to disk.

Serial access uses pyserial when installed (venv/bin/pip install
pyserial); without it, the tty is read directly with termios (Linux only).

Replay: with --replay FILE the esp32 block comes from a recorded or
generated file of DASH lines played in a loop, not from the ESP32. The
bridge block then says "replay": true and "replay_file": "<file name>", so
the dashboard can show a REPLAY badge and replayed data is never taken for
live data. From the serial port it says "replay": false, "replay_file": null.

Testing without hardware:
  python3 telemetry_bridge.py --replay tests/dash_sample.txt --fake-tof
Then open http://localhost:8081/telemetry
"""
import argparse
import ipaddress
import json
import math
import os
import signal
import socket
import subprocess
import sys
import threading
import time

import tof_reader

VERSION = "1.0"
DASH_PREFIX = "DASH "
MAX_LINE_BYTES = 4096        # a line longer than this with no newline is dropped (contract max is 400)
SERIAL_RETRY_S = 2.0         # wait between attempts to open a missing serial port
TOF_RETRY_S = 5.0            # wait between attempts to open the ToF sensors
TOF_NAMES = ("left", "ahead", "right")
BEACON_PORT = 50808          # TELEMETRY_LINK.md 4.2
BEACON_INTERVAL_S = 2.0
CAMERA_PORT = 8080           # the hazard detector's port, announced in the beacon


def _reject_constant(name):
    # json.loads accepts NaN, Infinity and -Infinity by default. The
    # contract says unknown values are null, so these make the line bad.
    raise ValueError("non-finite constant %s" % name)


def parse_dash_line(line):
    """Classify one line of serial text.

    Returns ("ignore", None) for a line that does not start with "DASH ",
    ("bad", None) for a DASH line that cannot be used, and ("ok", dict)
    for a good one."""
    line = line.strip("\r\n")
    if not line.startswith(DASH_PREFIX):
        return "ignore", None
    try:
        obj = json.loads(line[len(DASH_PREFIX):], parse_constant=_reject_constant)
    except ValueError:
        return "bad", None
    if not isinstance(obj, dict):
        return "bad", None
    return "ok", obj


class TelemetryState:
    """Latest ESP32 record and ToF reading, shared between the reader
    threads and the HTTP handler."""

    def __init__(self, serial_label, replay_file=None):
        self._lock = threading.Lock()
        self.serial_label = serial_label
        # File name only (no directories), or None for the live serial port.
        self.replay_file = os.path.basename(replay_file) if replay_file else None
        self.lines = 0
        self.bad_lines = 0
        self._esp32 = None
        self._esp32_t = None
        self._tof = None
        self._tof_t = None

    def handle_line(self, line):
        kind, obj = parse_dash_line(line)
        if kind == "ignore":
            return kind
        with self._lock:
            self.lines += 1
            if kind == "bad":
                self.bad_lines += 1
            else:
                self._esp32 = obj
                self._esp32_t = time.monotonic()
        return kind

    def clear_esp32(self):
        with self._lock:
            self._esp32 = None
            self._esp32_t = None

    def set_tof(self, values):
        """values: {"left": mm or None, ...}, or None when the sensors are absent."""
        with self._lock:
            if values is None:
                self._tof, self._tof_t = None, None
            else:
                self._tof = {"%s_mm" % n: values.get(n) for n in TOF_NAMES}
                self._tof_t = time.monotonic()

    def snapshot(self):
        now = time.monotonic()
        with self._lock:
            esp32 = None
            if self._esp32 is not None:
                esp32 = dict(self._esp32)
                esp32["age_ms"] = int(round((now - self._esp32_t) * 1000))
            tof = None
            if self._tof is not None:
                tof = dict(self._tof)
                tof["age_ms"] = int(round((now - self._tof_t) * 1000))
            return {
                "esp32": esp32,
                "tof": tof,
                "bridge": {
                    "version": VERSION,
                    "serial_port": self.serial_label,
                    "lines": self.lines,
                    "bad_lines": self.bad_lines,
                    "replay": self.replay_file is not None,
                    "replay_file": self.replay_file,
                },
            }


# Serial port access ---------------------------------------------------------

class _PySerialPort:
    def __init__(self, port, baud):
        import serial
        self._serial_mod = serial
        self._s = serial.Serial(port, baud, timeout=0.5)

    def read(self):
        """Some bytes, or b"" after the timeout. Raises OSError when the
        device has gone."""
        try:
            n = self._s.in_waiting
            return self._s.read(n if n > 0 else 1)
        except self._serial_mod.SerialException as e:
            raise OSError(str(e))

    def close(self):
        try:
            self._s.close()
        except Exception:
            pass


class _TermiosPort:
    """Plain tty reading for a Pi without pyserial. Raw mode, 8N1, no echo."""

    def __init__(self, port, baud):
        import select
        import termios
        self._select = select
        self._fd = os.open(port, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            attrs = termios.tcgetattr(self._fd)
            speed = getattr(termios, "B%d" % baud, termios.B115200)
            attrs[0] = 0                                                      # iflag
            attrs[1] = 0                                                      # oflag
            attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL           # cflag
            attrs[3] = 0                                                      # lflag
            attrs[4] = speed
            attrs[5] = speed
            termios.tcsetattr(self._fd, termios.TCSANOW, attrs)
        except Exception:
            os.close(self._fd)
            raise

    def read(self):
        r, _, _ = self._select.select([self._fd], [], [], 0.5)
        if not r:
            return b""
        data = os.read(self._fd, 512)
        if not data:
            # Readable but empty means the device was unplugged.
            raise OSError("serial device disconnected")
        return data

    def close(self):
        try:
            os.close(self._fd)
        except OSError:
            pass


def open_serial(port, baud):
    try:
        import serial  # noqa: F401
    except ImportError:
        try:
            import termios  # noqa: F401
        except ImportError:
            raise OSError("pyserial is not installed and termios is not available on this system")
        return _TermiosPort(port, baud)
    return _PySerialPort(port, baud)


class LineSource(threading.Thread):
    """Feeds lines into the state, from the serial port or a replay file."""

    def __init__(self, state, stop, port=None, baud=115200, replay=None, replay_interval=1.0):
        super().__init__(daemon=True)
        self.state = state
        self.stop = stop
        self.port = port
        self.baud = baud
        self.replay = replay
        self.replay_interval = replay_interval

    def run(self):
        if self.replay:
            self._run_replay()
        else:
            self._run_serial()

    def _run_replay(self):
        with open(self.replay, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        if not lines:
            print("Replay file %s is empty" % self.replay)
            return
        i = 0
        while not self.stop.is_set():
            self.state.handle_line(lines[i % len(lines)])
            i += 1
            self.stop.wait(self.replay_interval)

    def _run_serial(self):
        last_error = None
        while not self.stop.is_set():
            try:
                dev = open_serial(self.port, self.baud)
            except (OSError, ValueError) as e:
                msg = str(e)
                if msg != last_error:
                    print("Serial %s not available (%s); retrying every %.0f s"
                          % (self.port, msg, SERIAL_RETRY_S))
                    last_error = msg
                self.stop.wait(SERIAL_RETRY_S)
                continue
            last_error = None
            print("Serial %s open" % self.port)
            buf = b""
            first = True     # the first line after opening may be a fragment
            try:
                while not self.stop.is_set():
                    data = dev.read()
                    if not data:
                        continue
                    buf += data
                    while b"\n" in buf:
                        raw, buf = buf.split(b"\n", 1)
                        text = raw.decode("utf-8", errors="replace")
                        if first:
                            first = False
                            if not text.startswith(DASH_PREFIX):
                                continue
                        self.state.handle_line(text)
                    if len(buf) > MAX_LINE_BYTES:
                        buf = b""
            except OSError as e:
                print("Serial %s lost (%s); waiting for it to come back" % (self.port, e))
            finally:
                dev.close()
                self.state.clear_esp32()
            self.stop.wait(SERIAL_RETRY_S / 4)


# ToF sensors ----------------------------------------------------------------

class TofReader(threading.Thread):
    """Reads the three VL53L0X sensors with tof_reader.open_sensors, or
    makes up plausible changing distances with fake=True."""

    def __init__(self, state, stop, fake=False, period_s=0.05):
        super().__init__(daemon=True)
        self.state = state
        self.stop = stop
        self.fake = fake
        self.period_s = period_s

    def run(self):
        if self.fake:
            self._run_fake()
        else:
            self._run_real()

    def _run_fake(self):
        t0 = time.monotonic()
        while not self.stop.is_set():
            t = time.monotonic() - t0
            raw = {
                "left": 800 + 150 * math.sin(t / 3.0),
                "ahead": 1500 + 600 * math.sin(t / 5.0),
                # Nothing in range (8190) about a third of the time, so
                # the null path is exercised too.
                "right": 8190 if math.sin(t / 2.0) > 0.5 else 650 + 100 * math.cos(t / 2.0),
            }
            self.state.set_tof({n: tof_reader.clean_mm(v) for n, v in raw.items()})
            self.stop.wait(self.period_s)

    @staticmethod
    def _release(sensors, handles):
        for s in (sensors or {}).values():
            try:
                s.stop_continuous()
            except Exception:
                pass
        for h in reversed(handles):
            try:
                h.deinit()
            except Exception:
                pass
        handles.clear()

    def _run_real(self):
        last_error = None
        while not self.stop.is_set():
            handles = []
            sensors = None
            try:
                sensors = tof_reader.open_sensors(False, handles)
                for s in sensors.values():
                    s.start_continuous()
                print("ToF sensors open: %s" % ", ".join(sensors))
                last_error = None
                while not self.stop.is_set():
                    self.state.set_tof({n: tof_reader.clean_mm(s.range) for n, s in sensors.items()})
                    self.stop.wait(self.period_s)
            except Exception as e:   # ImportError, OSError, RuntimeError, ValueError from Blinka
                msg = "%s: %s" % (type(e).__name__, e)
                if msg != last_error:
                    print("ToF sensors not available (%s); tof is null, retrying every %.0f s"
                          % (msg, TOF_RETRY_S))
                    last_error = msg
                self.state.set_tof(None)
            finally:
                self._release(sensors, handles)
            self.stop.wait(TOF_RETRY_S)


# Beacon ---------------------------------------------------------------------

def parse_ip_json(text):
    """Broadcast addresses from `ip -j -4 addr` output, loopback and
    point-to-point (/31, /32) excluded. Never raises."""
    try:
        ifaces = json.loads(text or "[]")
    except ValueError:
        return []
    found = []
    for iface in ifaces if isinstance(ifaces, list) else []:
        try:
            if "LOOPBACK" in (iface.get("flags") or []):
                continue
            for a in iface.get("addr_info") or []:
                if a.get("family") != "inet":
                    continue
                b = a.get("broadcast")
                if not b:
                    net = ipaddress.ip_network("%s/%s" % (a["local"], a["prefixlen"]), strict=False)
                    if net.prefixlen >= 31:
                        continue
                    b = str(net.broadcast_address)
                if b not in found:
                    found.append(b)
        except Exception:
            continue
    return found


def broadcast_addresses():
    """IPv4 broadcast addresses of this machine's interfaces. On Linux from
    `ip -j -4 addr`; elsewhere, or if that fails, an empty list."""
    if not sys.platform.startswith("linux"):
        return []
    try:
        out = subprocess.run(["ip", "-j", "-4", "addr"], capture_output=True, text=True,
                             timeout=2).stdout
    except Exception:
        return []
    return parse_ip_json(out)


def default_beacon_targets():
    return ["255.255.255.255"] + [b for b in broadcast_addresses() if b != "255.255.255.255"]


class Beacon(threading.Thread):
    """Sends the discovery packet every interval_s. targets is a list of
    addresses, or None for 255.255.255.255 plus every interface's
    broadcast address (looked up again before each send)."""

    def __init__(self, stop, telemetry_port, camera_port=CAMERA_PORT, port=BEACON_PORT,
                 interval_s=BEACON_INTERVAL_S, targets=None, host=None):
        super().__init__(daemon=True)
        self.stop = stop
        self.telemetry_port = telemetry_port
        self.camera_port = camera_port
        self.port = port
        self.interval_s = interval_s
        self.targets = list(targets) if targets else None
        self.host = host or socket.gethostname().split(".")[0]
        self.seq = 0
        self.sent = 0
        self.send_errors = 0
        self.last_error = None

    def payload(self):
        return {"sw7": "pi4", "v": 1, "host": self.host, "camera_port": self.camera_port,
                "telemetry_port": self.telemetry_port, "seq": self.seq}

    def send_once(self, sock):
        targets = self.targets if self.targets is not None else default_beacon_targets()
        data = json.dumps(self.payload(), separators=(",", ":")).encode()
        for t in targets:
            try:
                sock.sendto(data, (t, self.port))
                self.sent += 1
            except OSError as e:     # no route, network down, broadcast refused
                self.send_errors += 1
                self.last_error = "%s: %s" % (t, e)
        self.seq += 1

    def run(self):
        sock = None
        while not self.stop.is_set():
            try:
                if sock is None:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                self.send_once(sock)
            except Exception as e:   # never let the beacon take the bridge down
                self.send_errors += 1
                self.last_error = str(e)
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass
                    sock = None
            self.stop.wait(self.interval_s)
        if sock is not None:
            sock.close()


# HTTP -----------------------------------------------------------------------

class TelemetryServer:
    def __init__(self, state, port, host="0.0.0.0"):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        server = self
        self.state = state
        self.beacon = None       # set by Bridge, for the status page

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, ctype, body):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                path = self.path.split("?", 1)[0]
                if path == "/telemetry":
                    body = json.dumps(server.state.snapshot()).encode()
                    self._send(200, "application/json", body)
                elif path == "/":
                    self._send(200, "text/plain; charset=utf-8", server.status_text().encode())
                else:
                    self.send_error(404)

        self._httpd = ThreadingHTTPServer((host, port), Handler)
        self._httpd.daemon_threads = True
        self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def status_text(self):
        snap = self.state.snapshot()
        b = snap["bridge"]
        e = snap["esp32"]
        t = snap["tof"]
        lines = [
            "SW-7 telemetry bridge %s" % b["version"],
            "serial: %s, %d DASH lines, %d bad" % (b["serial_port"], b["lines"], b["bad_lines"]),
            "source: %s" % ("REPLAY of %s (not live data)" % b["replay_file"] if b["replay"] else "live serial"),
            "esp32: %s" % ("no data" if e is None else "seq %s, %d ms ago" % (e.get("seq"), e["age_ms"])),
            "tof: %s" % ("absent" if t is None else "left %s, ahead %s, right %s mm, %d ms ago" % (
                t["left_mm"], t["ahead_mm"], t["right_mm"], t["age_ms"])),
            "beacon: %s" % ("off" if self.beacon is None else "UDP port %d, %d sent, %d failed%s" % (
                self.beacon.port, self.beacon.sent, self.beacon.send_errors,
                "" if not self.beacon.last_error else " (last: %s)" % self.beacon.last_error)),
            "JSON: /telemetry",
        ]
        return "\n".join(lines) + "\n"

    def close(self):
        self._httpd.shutdown()
        self._httpd.server_close()


class Bridge:
    """The whole bridge: line source, ToF reader and HTTP server."""

    def __init__(self, serial_port="/dev/ttyACM0", baud=115200, host="0.0.0.0", port=8081,
                 replay=None, replay_interval=1.0, tof=True, fake_tof=False,
                 beacon=True, beacon_port=BEACON_PORT, beacon_targets=None,
                 beacon_interval_s=BEACON_INTERVAL_S, camera_port=CAMERA_PORT):
        label = ("replay:%s" % replay) if replay else serial_port
        self.state = TelemetryState(label, replay_file=replay)
        self.stop = threading.Event()
        self.source = LineSource(self.state, self.stop, serial_port, baud, replay, replay_interval)
        self.tof = TofReader(self.state, self.stop, fake=fake_tof) if (tof or fake_tof) else None
        self.server = TelemetryServer(self.state, port, host)
        self.port = self.server.port
        self.beacon = None
        if beacon:
            self.beacon = Beacon(self.stop, self.port, camera_port, beacon_port,
                                 beacon_interval_s, beacon_targets)
            self.server.beacon = self.beacon

    def start(self):
        self.source.start()
        if self.tof is not None:
            self.tof.start()
        if self.beacon is not None:
            self.beacon.start()
        return self

    def close(self):
        self.stop.set()
        self.server.close()
        for t in (self.source, self.tof, self.beacon):
            if t is not None and t.is_alive():
                t.join(timeout=3)


def main():
    ap = argparse.ArgumentParser(description="SW-7 telemetry bridge: ESP32 serial and ToF to HTTP /telemetry")
    ap.add_argument("--serial-port", default="/dev/ttyACM0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--host", default="0.0.0.0",
                    help="0.0.0.0 = reachable from the Pi 5 on the local network; 127.0.0.1 = this Pi only")
    ap.add_argument("--port", type=int, default=8081)
    ap.add_argument("--replay", default=None, metavar="FILE",
                    help="Read DASH lines from FILE in a loop instead of the serial port (testing)")
    ap.add_argument("--replay-interval", type=float, default=1.0,
                    help="Seconds between replayed lines (default 1, like the ESP32)")
    ap.add_argument("--no-tof", action="store_true", help="Do not read the ToF sensors (tof is null)")
    ap.add_argument("--fake-tof", action="store_true", help="Made-up changing ToF distances (testing)")
    ap.add_argument("--no-beacon", action="store_true",
                    help="Do not send the UDP discovery beacon (port %d)" % BEACON_PORT)
    ap.add_argument("--beacon-port", type=int, default=BEACON_PORT)
    ap.add_argument("--beacon-interval", type=float, default=BEACON_INTERVAL_S)
    ap.add_argument("--beacon-target", action="append", default=None, metavar="ADDR",
                    help="Send the beacon to ADDR only (repeatable; testing). Default: "
                         "255.255.255.255 and every interface's broadcast address")
    ap.add_argument("--camera-port", type=int, default=CAMERA_PORT,
                    help="Camera port announced in the beacon")
    ap.add_argument("--duration", type=float, default=0, help="Seconds to run, 0 = until Ctrl+C or SIGTERM")
    a = ap.parse_args()

    # Stop cleanly under systemd (SIGTERM) the same way as Ctrl+C.
    def _on_sigterm(signum, frame_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, _on_sigterm)

    bridge = Bridge(a.serial_port, a.baud, a.host, a.port, a.replay, a.replay_interval,
                    tof=not a.no_tof, fake_tof=a.fake_tof, beacon=not a.no_beacon,
                    beacon_port=a.beacon_port, beacon_targets=a.beacon_target,
                    beacon_interval_s=a.beacon_interval, camera_port=a.camera_port).start()
    print("Telemetry bridge %s on http://%s:%d/telemetry, source %s, tof %s" % (
        VERSION, a.host, bridge.port, bridge.state.serial_label,
        "fake" if a.fake_tof else ("off" if a.no_tof else "sensors")))
    if bridge.beacon is not None:
        print("Beacon every %.0f s to UDP port %d (%s)" % (
            a.beacon_interval, a.beacon_port,
            ", ".join(a.beacon_target) if a.beacon_target else "broadcast on every interface"))
    start = time.monotonic()
    try:
        while a.duration == 0 or time.monotonic() - start < a.duration:
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        bridge.close()
        b = bridge.state.snapshot()["bridge"]
        print("Stopped. %d DASH lines, %d bad, in %.1f s" % (b["lines"], b["bad_lines"], time.monotonic() - start))
        if bridge.beacon is not None:
            print("Beacon: %d sent, %d failed" % (bridge.beacon.sent, bridge.beacon.send_errors))


if __name__ == "__main__":
    main()
