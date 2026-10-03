"""
sw7_endpoints: find the Pi 4 (telemetry bridge and camera) from the dashboard.

TELEMETRY_LINK.md section 4.3. Candidates, tried in this order on every
search:
  1. 127.0.0.1                    "localhost" (bridge and detector on the same Pi 5)
  2. TUKZIE_PI4_HOST, or the line pi4_host=<host> in ~/.config/sw7/endpoints.conf
                                  "override"
  3. 10.20.0.1                    "wired" (the sw7-link Ethernet cable)
  4. source address of the latest beacon (UDP 50808, JSON {"sw7": "pi4", ...},
     ignored when older than 10 s)
                                  "beacon"
  5. pi4-camera.local             "mdns"
  6. the last host that worked, saved in ~/.config/sw7/last_pi4_host
                                  "saved"
A candidate is accepted when GET http://<host>:8081/telemetry answers within
1 s with valid JSON. Its users (LiveDataProvider) report each poll with
report_success() or report_failure(); after 3 failures in a row the resolver
searches again from the top. host_changed(host, how) is emitted on every
change, ("", "searching") while searching.

TUKZIE_TELEMETRY_URL and TUKZIE_CAMERA_URL, when set, bypass the resolver
(handled by the users of this module). TUKZIE_CAMERA_URL alone moves the
camera only.

Qt networking only (QNetworkAccessManager, QUdpSocket), so everything runs in
the Qt event loop. Drop this file into app/data/.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import (QAbstractSocket, QHostAddress, QNetworkAccessManager, QNetworkReply,
                               QNetworkRequest, QUdpSocket)

TELEMETRY_PORT = 8081
CAMERA_PORT = 8080
BEACON_PORT = 50808
LOCALHOST = "127.0.0.1"
WIRED_HOST = "10.20.0.1"
MDNS_HOST = "pi4-camera.local"
PROBE_TIMEOUT_MS = 3000   # phone hotspots add 0.1 to 0.8 s per round trip; 1 s failed on 3 Oct
FAILURES_BEFORE_REPROBE = 3
BEACON_MAX_AGE_S = 10.0
RETRY_MS = 2000                 # wait between two full searches that found nothing

ORDER = ("localhost", "override", "wired", "beacon", "mdns", "saved")


def default_config_dir() -> Path:
    """~/.config/sw7, or SW7_CONFIG_DIR if set (tests)."""
    env = os.environ.get("SW7_CONFIG_DIR", "").strip()
    return Path(env) if env else Path.home() / ".config" / "sw7"


def read_override(config_dir: Path):
    """TUKZIE_PI4_HOST, else pi4_host= from endpoints.conf, else None."""
    env = os.environ.get("TUKZIE_PI4_HOST", "").strip()
    if env:
        return env
    try:
        text = (Path(config_dir) / "endpoints.conf").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == "pi4_host" and value.strip() and not line.lstrip().startswith("#"):
            return value.strip()
    return None


def is_beacon(payload: bytes) -> bool:
    """True for a SW-7 Pi 4 beacon: a JSON object with "sw7": "pi4"."""
    try:
        data = json.loads(payload)
    except (ValueError, UnicodeDecodeError):
        return False
    return isinstance(data, dict) and data.get("sw7") == "pi4"


def _plain_ipv4(address: QHostAddress) -> str:
    text = address.toString()
    return text[7:] if text.startswith("::ffff:") else text


class Pi4Resolver(QObject):
    host_changed = Signal(str, str)     # (host, how); ("", "searching") while searching

    def __init__(self, parent=None, telemetry_port=TELEMETRY_PORT, camera_port=CAMERA_PORT,
                 beacon_port=BEACON_PORT, config_dir=None, localhost=LOCALHOST,
                 wired_host=WIRED_HOST, mdns_host=MDNS_HOST, listen_for_beacons=True):
        super().__init__(parent)
        self.telemetry_port = int(telemetry_port)
        self.camera_port = int(camera_port)
        self.beacon_port = int(beacon_port)
        self.config_dir = Path(config_dir) if config_dir else default_config_dir()
        self.fixed = {"localhost": localhost, "wired": wired_host, "mdns": mdns_host}
        self.host = None
        self.how = "searching"
        self.failures = 0
        self.beacon_host = None
        self.beacon_time = 0.0
        self.beacons_seen = 0
        self.beacon_error = ""
        self._listen = bool(listen_for_beacons)
        self._udp = None
        self._started = False
        self._searching = False
        self._step = 0
        self._tried = set()
        self._probe_reply = None
        self._probe_candidate = None
        self._net = QNetworkAccessManager(self)
        self._probe_timer = QTimer(self)
        self._probe_timer.setSingleShot(True)
        self._probe_timer.timeout.connect(self._probe_timed_out)
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self.search)

    # ---- public --------------------------------------------------------
    def start(self):
        if self._started:
            return
        self._started = True
        if self._listen:
            self._start_beacon_listener()
        if self.host is None:
            self.search()

    def stop(self):
        self._started = False
        self._retry_timer.stop()
        self._abort_probe()
        self._searching = False
        if self._udp is not None:
            self._udp.close()
            self._udp = None

    def telemetry_url(self):
        return f"http://{self.host}:{self.telemetry_port}" if self.host else None

    def camera_url(self):
        return f"http://{self.host}:{self.camera_port}" if self.host else None

    def report_success(self):
        self.failures = 0

    def report_failure(self):
        if self.host is None:
            return
        self.failures += 1
        if self.failures >= FAILURES_BEFORE_REPROBE:
            self._set_host(None, "searching")
            self.search()

    def candidates(self):
        """The current candidate list [(host, how)], in order, without duplicates."""
        out, seen = [], set()
        for how in ORDER:
            host = self._candidate(how)
            if host and host not in seen:
                seen.add(host)
                out.append((host, how))
        return out

    # ---- search ----------------------------------------------------------
    def search(self):
        """Probe the candidates in order (no-op while a search is running)."""
        if self._searching or not self._started:
            return
        self._retry_timer.stop()
        self._searching = True
        self._step = 0
        self._tried = set()
        self._probe_next()

    def _candidate(self, how):
        if how in self.fixed:
            return self.fixed[how] or None
        if how == "override":
            return read_override(self.config_dir)
        if how == "beacon":
            fresh = self.beacon_host and time.monotonic() - self.beacon_time <= BEACON_MAX_AGE_S
            return self.beacon_host if fresh else None
        if how == "saved":
            try:
                return (self.config_dir / "last_pi4_host").read_text(encoding="utf-8").strip() or None
            except OSError:
                return None
        return None

    def _probe_next(self):
        # The candidate for each position is read when its turn comes, so a
        # beacon that arrives during the search is still used.
        while self._step < len(ORDER):
            how = ORDER[self._step]
            self._step += 1
            host = self._candidate(how)
            if host and host not in self._tried:
                self._tried.add(host)
                self._probe(host, how)
                return
        self._searching = False
        if self._started:
            self._retry_timer.start(RETRY_MS)

    def _probe(self, host, how):
        self._probe_candidate = (host, how)
        req = QNetworkRequest(QUrl(f"http://{host}:{self.telemetry_port}/telemetry"))
        req.setTransferTimeout(PROBE_TIMEOUT_MS)
        self._probe_reply = self._net.get(req)
        self._probe_reply.finished.connect(self._probe_finished)
        self._probe_timer.start(PROBE_TIMEOUT_MS)   # also covers a slow name lookup

    def _abort_probe(self):
        self._probe_timer.stop()
        reply, self._probe_reply = self._probe_reply, None
        if reply is not None:
            reply.finished.disconnect(self._probe_finished)
            reply.abort()
            reply.deleteLater()

    def _probe_timed_out(self):
        self._abort_probe()
        self._probe_next()

    def _probe_finished(self):
        self._probe_timer.stop()
        reply, self._probe_reply = self._probe_reply, None
        if reply is None:
            return
        ok = reply.error() == QNetworkReply.NetworkError.NoError
        payload = bytes(reply.readAll()) if ok else b""
        reply.deleteLater()
        if ok:
            try:
                ok = isinstance(json.loads(payload), dict)
            except (ValueError, UnicodeDecodeError):
                ok = False
        if ok:
            host, how = self._probe_candidate
            self._searching = False
            self.failures = 0
            self._save_last_good(host)
            self._set_host(host, how)
        else:
            self._probe_next()

    def _set_host(self, host, how):
        if host == self.host and how == self.how:
            return
        self.host, self.how = host, how
        self.host_changed.emit(host or "", how)

    def _save_last_good(self, host):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            (self.config_dir / "last_pi4_host").write_text(host + "\n", encoding="utf-8")
        except OSError:
            pass

    # ---- beacon ------------------------------------------------------------
    def _start_beacon_listener(self):
        udp = QUdpSocket(self)
        mode = (QAbstractSocket.BindFlag.ShareAddress | QAbstractSocket.BindFlag.ReuseAddressHint)
        if not udp.bind(QHostAddress(QHostAddress.SpecialAddress.AnyIPv4), self.beacon_port, mode):
            self.beacon_error = udp.errorString()   # the other candidates still work
            udp.deleteLater()
            return
        udp.readyRead.connect(self._read_beacons)
        self._udp = udp

    def _read_beacons(self):
        while self._udp is not None and self._udp.hasPendingDatagrams():
            dgram = self._udp.receiveDatagram()
            if not is_beacon(bytes(dgram.data())):
                continue
            self.beacon_host = _plain_ipv4(dgram.senderAddress())
            self.beacon_time = time.monotonic()
            self.beacons_seen += 1
            if self.host is None and not self._searching and self._started:
                self.search()    # idle between searches: try now rather than after RETRY_MS


_shared = None


def shared_resolver() -> Pi4Resolver:
    """The one resolver shared by the camera page and the live-data provider
    (created and started on first use; needs a QCoreApplication)."""
    global _shared
    if _shared is None:
        _shared = Pi4Resolver(parent=QCoreApplication.instance())
        _shared.start()
    return _shared
