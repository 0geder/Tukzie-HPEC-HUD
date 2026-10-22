#!/usr/bin/env python3
"""Front IMU node capture for the Pi 5 (firmware 0.7.5 build env front_node).

The front node is a second ESP32-S3 on the Pi 5's USB serial. It sends, like
the rear unit, a 1 Hz "DASH {json}" line (with "node":"front") and the raw
IMU stream (RAW, RAWH, RAWS lines, TelemetryUnit/RAW_STREAM.md). This
script:

  - opens the port (default "auto": the first /dev/serial/by-id/*Espressif*
    device, else the first /dev/ttyACM*), and reopens it whenever it
    disappears (unplug, reset, re-enumeration as ttyACM1);
  - appends EVERY line it receives, boot log and debug prints included, to
    <out>/front_raw_YYYY-MM-DD_HHMMSS.txt as "<host_epoch_s> <line>\n"
    (host_epoch_s = this Pi's time.time() when the read that completed the
    line returned, 6 decimals). A new file at every start, every hour
    (--rotate-s) and at --max-mb; flushed every second; writing pauses
    while the disk has less than --min-free-mb free. The reference decoder
    TelemetryUnit/tools/raw_stream_decode.py reads these files as they are
    for RAW/RAWH/RAWS; for DASH lines drop the first field first;
  - checks the CRC of every raw line and counts them (as the Pi 4 bridge does);
  - keeps the latest good DASH line and serves it on HTTP, in the same shape
    as the Pi 4 bridge (CameraDetection/telemetry_bridge.py), so the road
    recorder (BenchTest/road_logger.py, source "front_node") can poll it:

  GET /telemetry  {"esp32": {...latest DASH..., "age_ms": 420} or null,
                   "tof": null,
                   "bridge": {"version", "program": "raw_capture", "serial_port",
                              "connected", "lines", "bad_lines", "other_lines",
                              "replay": false, "replay_file": null,
                              "raw": {"capture", "dir", "file", "lines", "bad_crc",
                                      "raw", "rawh", "raws", "bytes_written",
                                      "not_written", "write_errors", "files",
                                      "paused"}}}
  GET /           plain-text status

"lines"/"bad_lines" count DASH lines as the bridge does; "raw.lines" counts
lines with a raw type word, "raw.bad_crc" those that failed the CRC;
"other_lines" everything else (still written to the file).

Usage (on the Pi 5, normally as sw7-front-node.service):
  python3 raw_capture.py [--port auto|/dev/ttyACM0] [--out /home/piadam/roadtest/raw_front]
                         [--http-port 8083] [--max-mb 100] [--rotate-s 3600] [--min-free-mb 1000]
Standard library; pyserial is used when installed (python3-serial), else
the tty is read with termios. Telemetry numbers only, nothing is sent
anywhere except the HTTP replies.
"""
import argparse
import binascii
import glob
import json
import os
import shutil
import signal
import sys
import threading
import time

VERSION = "1.0"
DEFAULT_OUT = "/home/piadam/roadtest/raw_front"
FILE_PREFIX = "front_raw_"
MAX_LINE_BYTES = 4096
SERIAL_RETRY_S = 2.0
READ_IDLE_S = 0.02
READ_SHORT_BYTES = 512
RETRY_S = 10.0
DASH_BYTES = b"DASH "
RAW_WORDS = ((b"RAWH ", "rawh"), (b"RAWS ", "raws"), (b"RAW ", "raw"))
_HEX_LOWER = frozenset(b"0123456789abcdef")


def raw_crc_ok(body):
    """CRC-16/CCITT-FALSE check as in TelemetryUnit/tools/raw_stream_decode.py
    (binascii.crc_hqx with init 0xFFFF is that CRC)."""
    if len(body) < 6 or body[-5] != 0x20 or not _HEX_LOWER.issuperset(body[-4:]):
        return False
    return binascii.crc_hqx(body[:-5], 0xFFFF) == int(body[-4:], 16)


def classify_raw(line):
    for word, kind in RAW_WORDS:
        p = line.find(word)
        if p >= 0:
            return kind, raw_crc_ok(line[p:].rstrip(b"\r"))
    return None


def _reject_constant(name):
    raise ValueError("non-finite constant %s" % name)


def parse_dash(line):
    """("ok", dict), ("bad", None) or ("ignore", None), as the bridge's parse_dash_line."""
    line = line.strip("\r\n")
    if not line.startswith("DASH "):
        return "ignore", None
    try:
        obj = json.loads(line[5:], parse_constant=_reject_constant)
    except ValueError:
        return "bad", None
    return ("ok", obj) if isinstance(obj, dict) else ("bad", None)


# Capture file ---------------------------------------------------------------

class CaptureFile:
    """Rotating capture file: every line with its host receive time."""

    def __init__(self, directory, prefix=FILE_PREFIX, max_mb=100.0, rotate_s=3600.0, min_free_mb=1000.0,
                 flush_s=1.0, retry_s=RETRY_S, enabled=True):
        self.directory = directory
        self.prefix = prefix
        self.max_bytes = int(max_mb * 1e6)
        self.rotate_s = rotate_s
        self.min_free_bytes = int(min_free_mb * 1e6)
        self.flush_s = flush_s
        self.retry_s = retry_s
        self.enabled = enabled
        self.disk_free = lambda d: shutil.disk_usage(d).free
        self.bytes_written = 0
        self.not_written = 0
        self.write_errors = 0
        self.files = 0
        self.paused = None
        self.path = None
        self._f = None
        self._file_bytes = 0
        self._opened = 0.0
        self._last_flush = 0.0
        self._retry_at = 0.0
        self._space_check_at = 0.0

    def _pause(self, reason):
        if reason != self.paused:
            print("Capture paused: %s" % reason, flush=True)
        self.paused = reason
        self._retry_at = time.monotonic() + self.retry_s

    def _space_ok(self):
        try:
            free = self.disk_free(self.directory)
        except OSError as e:
            self._pause("cannot read free space: %s" % e)
            return False
        if free < self.min_free_bytes:
            self._pause("disk free %.0f MB, below %.0f MB" % (free / 1e6, self.min_free_bytes / 1e6))
            return False
        return True

    def _open(self, now):
        try:
            os.makedirs(self.directory, exist_ok=True)
        except OSError as e:
            self._pause("cannot create %s: %s" % (self.directory, e))
            return False
        if not self._space_ok():
            return False
        stem = os.path.join(self.directory, self.prefix + time.strftime("%Y-%m-%d_%H%M%S"))
        path, n = stem + ".txt", 1
        while os.path.exists(path):
            path, n = "%s_%d.txt" % (stem, n), n + 1
        try:
            self._f = open(path, "xb")
        except OSError as e:
            self._pause("cannot open %s: %s" % (path, e))
            return False
        if self.paused is not None:
            print("Capture resumed", flush=True)
        self.paused = None
        self.path = path
        self._file_bytes = 0
        self._opened = self._last_flush = now
        self._space_check_at = now + self.retry_s
        self.files += 1
        print("Capture file %s" % path, flush=True)
        return True

    def write_line(self, line, t_host):
        if not self.enabled:
            return
        data = b"%.6f " % t_host + line.rstrip(b"\r") + b"\n"
        now = time.monotonic()
        if self._f is not None and (self._file_bytes + len(data) > self.max_bytes
                                    or now - self._opened >= self.rotate_s):
            self.close()
        if self._f is None:
            if now < self._retry_at or not self._open(now):
                self.not_written += 1
                return
        elif now >= self._space_check_at:
            self._space_check_at = now + self.retry_s
            if not self._space_ok():
                self.close()
                self.not_written += 1
                return
        try:
            self._f.write(data)
        except OSError as e:
            self.write_errors += 1
            self.not_written += 1
            self.close()
            self._pause("write error: %s" % e)
            return
        self._file_bytes += len(data)
        self.bytes_written += len(data)

    def tick(self):
        if self._f is not None and time.monotonic() - self._last_flush >= self.flush_s:
            self.flush()

    def flush(self):
        if self._f is None:
            return
        self._last_flush = time.monotonic()
        try:
            self._f.flush()
        except OSError as e:
            self.write_errors += 1
            self.close()
            self._pause("flush error: %s" % e)

    def close(self):
        f, self._f = self._f, None
        if f is not None:
            try:
                f.close()
            except OSError:
                self.write_errors += 1


# State ----------------------------------------------------------------------

class FrontState:
    def __init__(self, port_label, capture):
        self._lock = threading.Lock()
        self.port_label = port_label
        self.capture = capture
        self.connected = False
        self.lines = 0
        self.bad_lines = 0
        self.other_lines = 0
        self.raw_lines = 0
        self.bad_crc = 0
        self.by_kind = {"raw": 0, "rawh": 0, "raws": 0}
        self._dash = None
        self._dash_t = None

    def handle(self, line, t_host, count=True):
        """line: bytes, newline removed. Written to the capture always; counted
        unless count is False (the fragment that may start a connection)."""
        self.capture.write_line(line, t_host)
        if not count:
            return "fragment"
        if line.startswith(DASH_BYTES):
            kind, obj = parse_dash(line.decode("utf-8", errors="replace"))
            with self._lock:
                self.lines += 1
                if kind == "ok":
                    self._dash, self._dash_t = obj, time.monotonic()
                else:
                    self.bad_lines += 1
            return "dash" if kind == "ok" else "bad"
        r = classify_raw(line)
        with self._lock:
            if r is None:
                self.other_lines += 1
                return "other"
            self.raw_lines += 1
            if r[1]:
                self.by_kind[r[0]] += 1
                return r[0]
            self.bad_crc += 1
            return "bad_crc"

    def set_connected(self, port, up):
        with self._lock:
            self.connected = up
            if port:
                self.port_label = port
            if not up:
                self._dash, self._dash_t = None, None

    def snapshot(self):
        now = time.monotonic()
        c = self.capture
        with self._lock:
            esp32 = None
            if self._dash is not None:
                esp32 = dict(self._dash)
                esp32["age_ms"] = int(round((now - self._dash_t) * 1000))
            return {
                "esp32": esp32,
                "tof": None,
                "bridge": {
                    "version": VERSION, "program": "raw_capture", "serial_port": self.port_label,
                    "connected": self.connected, "lines": self.lines, "bad_lines": self.bad_lines,
                    "other_lines": self.other_lines, "replay": False, "replay_file": None,
                    "raw": {
                        "capture": c.enabled, "dir": c.directory if c.enabled else None,
                        "file": os.path.basename(c.path) if (c.enabled and c.path) else None,
                        "lines": self.raw_lines, "bad_crc": self.bad_crc,
                        "raw": self.by_kind["raw"], "rawh": self.by_kind["rawh"], "raws": self.by_kind["raws"],
                        "bytes_written": c.bytes_written, "not_written": c.not_written,
                        "write_errors": c.write_errors, "files": c.files, "paused": c.paused,
                    },
                },
            }


# Serial ---------------------------------------------------------------------

def find_port(spec):
    """spec "auto": the first Espressif device by id, else the first ttyACM; else spec itself."""
    if spec != "auto":
        return spec
    for pattern in ("/dev/serial/by-id/*Espressif*", "/dev/serial/by-id/*ESP32*", "/dev/ttyACM*"):
        found = sorted(glob.glob(pattern))
        if found:
            return found[0]
    raise OSError("no ESP32 serial device found (/dev/serial/by-id/*Espressif*, /dev/ttyACM*)")


class _PySerialPort:
    def __init__(self, port, baud):
        import serial
        self._mod = serial
        self._s = serial.Serial(port, baud, timeout=0.5)

    def read(self):
        try:
            n = self._s.in_waiting
            return self._s.read(n if n > 0 else 1)
        except self._mod.SerialException as e:
            raise OSError(str(e))

    def close(self):
        try:
            self._s.close()
        except Exception:
            pass


class _TermiosPort:
    def __init__(self, port, baud):
        import select
        import termios
        self._select = select
        self._fd = os.open(port, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            attrs = termios.tcgetattr(self._fd)
            speed = getattr(termios, "B%d" % baud, termios.B115200)
            attrs[0] = attrs[1] = attrs[3] = 0
            attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
            attrs[4] = attrs[5] = speed
            termios.tcsetattr(self._fd, termios.TCSANOW, attrs)
        except Exception:
            os.close(self._fd)
            raise

    def read(self):
        r, _, _ = self._select.select([self._fd], [], [], 0.5)
        if not r:
            return b""
        data = os.read(self._fd, 4096)
        if not data:
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
        return _TermiosPort(port, baud)
    return _PySerialPort(port, baud)


class Reader(threading.Thread):
    def __init__(self, state, stop, port_spec="auto", baud=115200):
        super().__init__(daemon=True)
        self.state = state
        self.stop = stop
        self.port_spec = port_spec
        self.baud = baud
        self.opens = 0

    def run(self):
        last_error = None
        cap = self.state.capture
        while not self.stop.is_set():
            try:
                port = find_port(self.port_spec)
                dev = open_serial(port, self.baud)
            except (OSError, ValueError) as e:
                msg = str(e)
                if msg != last_error:
                    print("Serial %s not available (%s); retrying every %.0f s"
                          % (self.port_spec, msg, SERIAL_RETRY_S), flush=True)
                    last_error = msg
                cap.tick()
                self.stop.wait(SERIAL_RETRY_S)
                continue
            last_error = None
            self.opens += 1
            self.state.set_connected(port, True)
            print("Serial %s open" % port, flush=True)
            buf = bytearray()
            first = True
            try:
                while not self.stop.is_set():
                    data = dev.read()
                    if data:
                        buf += data
                        if b"\n" in data:
                            t_host = time.time()
                            lines = buf.split(b"\n")
                            buf = bytearray(lines.pop())
                            for line in lines:
                                self.state.handle(line, t_host, count=not first or line.startswith(DASH_BYTES)
                                                  or classify_raw(line) is not None)
                                first = False
                        if len(buf) > MAX_LINE_BYTES:
                            cap.write_line(bytes(buf), time.time())     # keep it, it may be a long print
                            buf = bytearray()
                    cap.tick()
                    if len(data) < READ_SHORT_BYTES:
                        self.stop.wait(READ_IDLE_S)
            except OSError as e:
                print("Serial %s lost (%s); waiting for it to come back" % (port, e), flush=True)
            finally:
                dev.close()
                self.state.set_connected(None, False)
                cap.flush()
            self.stop.wait(SERIAL_RETRY_S / 4)
        cap.close()


# HTTP -----------------------------------------------------------------------

def status_text(snap):
    b, e, r = snap["bridge"], snap["esp32"], snap["bridge"]["raw"]
    lines = [
        "SW-7 front node capture %s" % VERSION,
        "serial: %s, %s, %d DASH lines, %d bad, %d other lines" % (
            b["serial_port"], "connected" if b["connected"] else "NOT CONNECTED", b["lines"], b["bad_lines"],
            b["other_lines"]),
        "front node: %s" % ("no data" if e is None else "seq %s, fw %s, %d ms ago" % (
            e.get("seq"), e.get("fw"), e["age_ms"])),
        "raw: %d lines (RAW %d, RAWH %d, RAWS %d), %d bad CRC" % (
            r["lines"], r["raw"], r["rawh"], r["raws"], r["bad_crc"]),
        "capture: %s" % ("off" if not r["capture"] else "%s/%s, %.1f MB written, %d not written%s" % (
            r["dir"], r["file"] or "(no file yet)", r["bytes_written"] / 1e6, r["not_written"],
            "; PAUSED: %s" % r["paused"] if r["paused"] else "")),
        "JSON: /telemetry",
    ]
    return "\n".join(lines) + "\n"


def start_http(state, host, port):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, ctype, body):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/telemetry":
                self._send("application/json", json.dumps(state.snapshot()).encode())
            elif path == "/":
                self._send("text/plain; charset=utf-8", status_text(state.snapshot()).encode())
            else:
                self.send_error(404)

    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", default="auto", help="serial device, or auto (default)")
    ap.add_argument("--baud", type=int, default=115200, help="ignored by USB CDC; matters on a UART")
    ap.add_argument("--out", default=DEFAULT_OUT, help="capture directory (default %s)" % DEFAULT_OUT)
    ap.add_argument("--prefix", default=FILE_PREFIX)
    ap.add_argument("--no-capture", action="store_true", help="serve DASH only, write nothing")
    ap.add_argument("--max-mb", type=float, default=100.0)
    ap.add_argument("--rotate-s", type=float, default=3600.0)
    ap.add_argument("--min-free-mb", type=float, default=1000.0)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--http-port", type=int, default=8083)
    ap.add_argument("--duration", type=float, default=0, help="seconds; 0 = until Ctrl+C or SIGTERM")
    a = ap.parse_args(argv)

    def _on_sigterm(signum, frame_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, _on_sigterm)

    cap = CaptureFile(a.out, a.prefix, a.max_mb, a.rotate_s, a.min_free_mb, enabled=not a.no_capture)
    state = FrontState(a.port, cap)
    stop = threading.Event()
    httpd = start_http(state, a.host, a.http_port)
    reader = Reader(state, stop, a.port, a.baud)
    reader.start()
    print("Front node capture %s on http://%s:%d/telemetry, port %s, capture %s" % (
        VERSION, a.host, httpd.server_address[1], a.port, "off" if a.no_capture else a.out), flush=True)
    start = time.monotonic()
    try:
        while a.duration == 0 or time.monotonic() - start < a.duration:
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        httpd.shutdown()
        httpd.server_close()
        reader.join(3)
        b = state.snapshot()["bridge"]
        print("Stopped. %d DASH lines (%d bad), %d raw lines (%d bad CRC), %.1f MB written, %d not written" % (
            b["lines"], b["bad_lines"], b["raw"]["lines"], b["raw"]["bad_crc"], b["raw"]["bytes_written"] / 1e6,
            b["raw"]["not_written"]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
