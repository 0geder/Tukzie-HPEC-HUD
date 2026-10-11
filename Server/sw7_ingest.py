"""SW-7 central database: MQTT to SQLite ingest.

Subscribes to the telemetry topic on any MQTT broker, checks each record and
stores it in SQLite. A record is identified by (dev, boot, seq), which the
telemetry unit (firmware v0.7.4 and later) puts in every record, so a record
that arrives twice (a replay after an outage, or a QoS 1 redelivery) is stored
once and only counted as a duplicate.

Configuration, in order of precedence: command-line options, environment
variables, a config file (KEY=VALUE lines, default Server/sw7_ingest.env if it
exists, git-ignored), defaults.

  SW7_MQTT_HOST      broker host            (default test.mosquitto.org)
  SW7_MQTT_PORT      broker port            (default 1883; 8883 with TLS)
  SW7_MQTT_USER      user name              (default none)
  SW7_MQTT_PASSWORD  password               (default none)
  SW7_MQTT_TOPIC     topic filter           (default sw7/telemetry)
  SW7_MQTT_TLS       1 to use TLS           (default 0)
  SW7_CLIENT_ID      MQTT client id         (default sw7-ingest-<hostname>)
  SW7_DB             SQLite file            (default Server/sw7_telemetry.db)

The session is persistent (clean session off, QoS 1), so a broker that keeps
sessions queues records while this program is stopped and delivers them when
it comes back. test.mosquitto.org did not (11 Oct 2026: 0 of 5 records sent
while the ingest was stopped arrived after it restarted). The broker
acknowledges a record to the telemetry unit whether or not this program is
running, so keep it running, and recover anything missed from the unit's own
log with --import-log (a copy saved by BenchTest/log_dump.py).

Run:  python Server/sw7_ingest.py            (Ctrl+C to stop)
      python Server/sw7_ingest.py --once 60  (run 60 s, print a summary, exit)
      python Server/sw7_ingest.py --import-log dump.jsonl   (backfill, then exit)
Needs paho-mqtt (version 1 or 2). Nothing else outside the standard library.
"""
import argparse
import json
import math
import os
import socket
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "sw7_telemetry.db")
DEFAULT_ENV_FILE = os.path.join(HERE, "sw7_ingest.env")

SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry (
    id            INTEGER PRIMARY KEY,
    dev           TEXT    NOT NULL,
    boot          INTEGER NOT NULL,
    seq           INTEGER NOT NULL,
    replay        INTEGER NOT NULL DEFAULT 0,  -- 1 if the first copy stored was a replay
    recv_ms       INTEGER NOT NULL,            -- server receive time, Unix ms (first copy)
    device_utc_ms INTEGER,                     -- device UTC from GNSS at record time, if known
    up_ms         INTEGER,                     -- device uptime at record time
    fw            TEXT,
    lat           REAL,                        -- GNSS position, only with a valid fix
    lon           REAL,
    cell_lat      REAL,                        -- cell-tower estimate (no GNSS fix)
    cell_lon      REAL,
    vib           REAL,                        -- fused vibration std, m/s^2
    soc           INTEGER,                     -- battery state of charge, %
    speed_raw     REAL,                        -- GNSS speed, units not yet confirmed
    csq           INTEGER,
    topic         TEXT,
    dup_count     INTEGER NOT NULL DEFAULT 0,  -- further copies received and ignored
    last_dup_ms   INTEGER,
    raw           TEXT    NOT NULL,
    UNIQUE (dev, boot, seq)
);
CREATE INDEX IF NOT EXISTS telemetry_recv ON telemetry (recv_ms);
CREATE TABLE IF NOT EXISTS rejects (
    id      INTEGER PRIMARY KEY,
    recv_ms INTEGER NOT NULL,
    topic   TEXT,
    reason  TEXT    NOT NULL,
    raw     TEXT
);
"""


def _num(v):
    """A finite number or None (JSON null, strings, NaN and booleans are not numbers here)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return v if math.isfinite(v) else None


def _int(v):
    v = _num(v)
    return int(v) if v is not None and float(v).is_integer() else None


def _sub(rec, key):
    v = rec.get(key)
    return v if isinstance(v, dict) else {}


def parse_record(payload):
    """Parse and check one MQTT payload. Returns (row dict, None) or (None, reason)."""
    try:
        text = payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else str(payload)
    except UnicodeDecodeError:
        return None, "not UTF-8"
    try:
        rec = json.loads(text)
    except ValueError as e:
        return None, f"not JSON ({e.__class__.__name__})"
    if not isinstance(rec, dict):
        return None, "not a JSON object"
    seq, boot = _int(rec.get("seq")), _int(rec.get("boot"))
    if seq is None or boot is None:
        return None, "no seq/boot (firmware before v0.7.4?)"
    if seq < 1 or boot < 0:
        return None, "seq or boot out of range"
    dev = rec.get("dev")
    if not isinstance(dev, str) or not dev.strip():
        return None, "no dev"
    replay = rec.get("replay", False)
    if not isinstance(replay, bool):
        return None, "replay is not true/false"
    gnss, cell, fused, bms = _sub(rec, "gnss"), _sub(rec, "cell"), _sub(rec, "fused"), _sub(rec, "bms")
    fix = gnss.get("valid") is True
    utc = _int(rec.get("utc_ms"))
    if utc is not None and not (1_704_067_200_000 <= utc <= 4_102_444_800_000):   # 2024 to 2100
        utc = None
    row = {
        "dev": dev.strip(),
        "boot": boot,
        "seq": seq,
        "replay": 1 if replay else 0,
        "device_utc_ms": utc,
        "up_ms": _int(rec.get("up_ms")),
        "fw": rec.get("fw") if isinstance(rec.get("fw"), str) else None,
        "lat": _num(gnss.get("lat")) if fix else None,
        "lon": _num(gnss.get("lon")) if fix else None,
        "cell_lat": _num(cell.get("lat")),
        "cell_lon": _num(cell.get("lon")),
        "vib": _num(fused.get("std")),
        "soc": _int(bms.get("soc")),
        "speed_raw": _num(gnss.get("speed")) if fix else None,
        "csq": _int(cell.get("csq")),
        "raw": text,
    }
    return row, None


class Store:
    """The SQLite side, kept apart from MQTT so it can be tested by feeding payloads directly."""

    def __init__(self, path):
        self.path = path
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")   # sync_report can read while ingest writes
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(SCHEMA)
        self.db.commit()
        self.counts = {"stored": 0, "duplicate": 0, "rejected": 0}

    def ingest(self, payload, topic="", recv_ms=None):
        """Store one payload. Returns 'stored', 'duplicate' or 'rejected'."""
        recv_ms = int(time.time() * 1000) if recv_ms is None else int(recv_ms)
        row, reason = parse_record(payload)
        if row is None:
            raw = payload.decode("utf-8", "replace") if isinstance(payload, (bytes, bytearray)) else str(payload)
            self.db.execute("INSERT INTO rejects (recv_ms, topic, reason, raw) VALUES (?,?,?,?)",
                            (recv_ms, topic, reason, raw[:4000]))
            self.db.commit()
            self.counts["rejected"] += 1
            return "rejected"
        row["recv_ms"], row["topic"] = recv_ms, topic
        cols = list(row)
        cur = self.db.execute(
            f"INSERT INTO telemetry ({','.join(cols)}) VALUES ({','.join('?' * len(cols))}) "
            "ON CONFLICT (dev, boot, seq) DO NOTHING", [row[c] for c in cols])
        if cur.rowcount == 1:
            status = "stored"
        else:
            self.db.execute("UPDATE telemetry SET dup_count = dup_count + 1, last_dup_ms = ? "
                            "WHERE dev = ? AND boot = ? AND seq = ?",
                            (recv_ms, row["dev"], row["boot"], row["seq"]))
            status = "duplicate"
        self.db.commit()
        self.counts[status] += 1
        return status

    def import_log(self, path, recv_ms=None):
        """Backfill from a device log copy (one record per line, as saved by log_dump.py).
        Rows get topic 'log-import' and are left out of latency and replay figures."""
        recv_ms = int(time.time() * 1000) if recv_ms is None else int(recv_ms)
        counts = {"stored": 0, "duplicate": 0, "skipped": 0}
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                row, _ = parse_record(line)
                if row is None:   # older firmware lines, or nan (fixed in v0.6.3)
                    counts["skipped"] += 1
                    continue
                row["recv_ms"], row["topic"] = recv_ms, "log-import"
                cols = list(row)
                cur = self.db.execute(
                    f"INSERT INTO telemetry ({','.join(cols)}) VALUES ({','.join('?' * len(cols))}) "
                    "ON CONFLICT (dev, boot, seq) DO NOTHING", [row[c] for c in cols])
                counts["stored" if cur.rowcount == 1 else "duplicate"] += 1
        self.db.commit()
        return counts

    def close(self):
        self.db.close()


def load_env_file(path):
    """KEY=VALUE lines; # comments and blank lines ignored; values may be quoted."""
    out = {}
    if not path or not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_config(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", help="KEY=VALUE file (default Server/sw7_ingest.env if present)")
    ap.add_argument("--host")
    ap.add_argument("--port", type=int)
    ap.add_argument("--user")
    ap.add_argument("--password")
    ap.add_argument("--topic")
    ap.add_argument("--tls", action="store_true", default=None)
    ap.add_argument("--client-id")
    ap.add_argument("--db")
    ap.add_argument("--once", type=float, metavar="SECONDS", help="run this long, print a summary, exit")
    ap.add_argument("--quiet", action="store_true", help="no line per record")
    ap.add_argument("--import-log", metavar="JSONL", help="backfill from a log_dump.py copy, then exit")
    a = ap.parse_args(argv)
    filecfg = load_env_file(a.config or DEFAULT_ENV_FILE)
    if a.config and not os.path.exists(a.config):
        ap.error(f"config file not found: {a.config}")

    def pick(cli, key, default):
        if cli is not None:
            return cli
        if os.environ.get(key):
            return os.environ[key]
        if filecfg.get(key):
            return filecfg[key]
        return default

    tls = pick(a.tls, "SW7_MQTT_TLS", "0")
    tls = tls is True or str(tls).lower() in ("1", "true", "yes")
    cfg = {
        "host": pick(a.host, "SW7_MQTT_HOST", "test.mosquitto.org"),
        "port": int(pick(a.port, "SW7_MQTT_PORT", 8883 if tls else 1883)),
        "user": pick(a.user, "SW7_MQTT_USER", None),
        "password": pick(a.password, "SW7_MQTT_PASSWORD", None),
        "topic": pick(a.topic, "SW7_MQTT_TOPIC", "sw7/telemetry"),
        "tls": tls,
        "client_id": pick(a.client_id, "SW7_CLIENT_ID", f"sw7-ingest-{socket.gethostname()}"),
        "db": pick(a.db, "SW7_DB", DEFAULT_DB),
        "once": a.once,
        "quiet": a.quiet,
        "import_log": a.import_log,
    }
    return cfg


def make_client(cfg, store, log=print):
    """Builds a paho client (version 1 or 2) wired to the store. Not yet connected."""
    import paho.mqtt.client as mqtt

    try:   # paho-mqtt 2.x
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cfg["client_id"],
                             clean_session=False, protocol=mqtt.MQTTv311)
    except AttributeError:   # paho-mqtt 1.x
        client = mqtt.Client(client_id=cfg["client_id"], clean_session=False, protocol=mqtt.MQTTv311)
    if cfg.get("user"):
        client.username_pw_set(cfg["user"], cfg.get("password"))
    if cfg.get("tls"):
        client.tls_set()
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    state = {"connected": False, "subscribed": False}

    def on_connect(c, userdata, flags, reason_code, properties=None):
        failed = getattr(reason_code, "is_failure", reason_code != 0)
        if failed:
            log(f"[ingest] connect refused: {reason_code}")
            return
        state["connected"] = True
        c.subscribe(cfg["topic"], qos=1)
        log(f"[ingest] connected to {cfg['host']}:{cfg['port']}, subscribed to {cfg['topic']} (QoS 1)")

    def on_subscribe(c, userdata, mid, *rest):
        state["subscribed"] = True

    def on_disconnect(c, userdata, *rest):
        state["connected"] = False
        log("[ingest] disconnected, paho will reconnect")

    def on_message(c, userdata, msg):
        status = store.ingest(msg.payload, msg.topic)
        if not cfg.get("quiet"):
            try:
                rec = json.loads(msg.payload)
                ident = f"boot {rec.get('boot')} seq {rec.get('seq')}{' replay' if rec.get('replay') else ''}"
            except Exception:
                ident = f"{len(msg.payload)} bytes"
            log(f"[ingest] {status}: {ident}")

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.sw7_state = state
    return client


def main(argv=None):
    cfg = load_config(argv)
    store = Store(cfg["db"])
    print(f"[ingest] database {os.path.abspath(cfg['db'])}")
    if cfg["import_log"]:
        counts = store.import_log(cfg["import_log"])
        print(f"[ingest] imported {cfg['import_log']}: {counts['stored']} new, {counts['duplicate']} already "
              f"stored, {counts['skipped']} lines without dev/boot/seq skipped")
        store.close()
        return 0
    print(f"[ingest] broker {cfg['host']}:{cfg['port']} topic {cfg['topic']} as {cfg['user'] or '(no user)'}"
          f"{' TLS' if cfg['tls'] else ''}, client id {cfg['client_id']}")
    client = make_client(cfg, store, log=lambda m: print(m, flush=True))
    client.connect_async(cfg["host"], cfg["port"], keepalive=60)
    client.loop_start()
    t0, last_summary = time.time(), time.time()
    try:
        while cfg["once"] is None or time.time() - t0 < cfg["once"]:
            time.sleep(0.5)
            if time.time() - last_summary >= 300:
                last_summary = time.time()
                print(f"[ingest] totals: {store.counts}", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()
        print(f"[ingest] stopped. This run: {store.counts}", flush=True)
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
