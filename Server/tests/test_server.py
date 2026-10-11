"""Offline tests of Server/sw7_ingest.py and Server/sync_report.py. No broker on
the internet, no ESP32: records are fed to the store directly, and the MQTT
path is exercised end to end through a minimal MQTT 3.1.1 broker on
127.0.0.1 (FakeBroker below: CONNECT, SUBSCRIBE, PUBLISH QoS 0/1, PUBACK,
PINGREQ, DISCONNECT; enough for paho, not a real broker).

Run: python Server/tests/test_server.py   (or python -m pytest Server/tests)
Needs paho-mqtt for the broker test only (skipped without it)."""
import contextlib
import io
import json
import os
import socket
import socketserver
import sqlite3
import sys
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import sw7_ingest as ing  # noqa: E402
import sync_report as rep  # noqa: E402

DEV = "sw7-esp32-telemetry"


def firmware_line(seq, boot=3, up_ms=None, utc_ms=None, replay=False):
    """A record in exactly the layout buildTelemetryJson() writes in v0.7.4 (values made up)."""
    up_ms = seq * 10000 if up_ms is None else up_ms
    utc = "null" if utc_ms is None else str(utc_ms)
    line = ('{"dev":"%s","fw":"0.7.4","boot":%d,"seq":%d,"up_ms":%d,"utc_ms":%s,'
            '"imu1":{"rms":9.807,"std":0.034,"p2p":0.210,"crest":1.010,"jerk":4.100,"crossings":3},'
            '"imu2":{"rms":9.811,"std":0.036,"p2p":0.220,"crest":1.012,"jerk":4.300,"crossings":4},'
            '"fused":{"src":3,"rms":9.809,"std":0.035,"p2p":0.215,"jerk":4.200,"dis":0.057},'
            '"bms":{"v":74.78,"i":0.00,"soc":60,"checksum_ok":true},'
            '"gnss":{"valid":true,"lat":-33.957000,"lon":18.461000,"speed":0.0},'
            '"cell":{"csq":24,"lat":null,"lon":null,"acc_m":null},'
            '"hall":{"eps":2.0,"rpm":null}}') % (DEV, boot, seq, up_ms, utc)
    if replay:   # what syncReplayStep() sends: the stored line with "replay":true added
        line = '{"replay":true,' + line[1:]
    return line


class ParseTests(unittest.TestCase):
    def test_firmware_record(self):
        row, why = ing.parse_record(firmware_line(7, utc_ms=1790718459000).encode())
        self.assertIsNone(why)
        self.assertEqual((row["dev"], row["boot"], row["seq"], row["replay"]), (DEV, 3, 7, 0))
        self.assertEqual(row["device_utc_ms"], 1790718459000)
        self.assertAlmostEqual(row["vib"], 0.035)
        self.assertEqual(row["soc"], 60)
        self.assertAlmostEqual(row["lat"], -33.957)
        row, _ = ing.parse_record(firmware_line(7, replay=True))
        self.assertEqual(row["replay"], 1)

    def test_rejects(self):
        legacy = '{"imu1":{"rms":9.8},"gnss":{"valid":false,"lat":null}}'   # v0.7.3 record
        self.assertIn("seq", ing.parse_record(legacy)[1])
        self.assertIn("JSON", ing.parse_record('{"seq":1,"boot":1,"dev":"x","v":nan}')[1])
        self.assertIsNotNone(ing.parse_record("[1,2]")[1])
        self.assertIsNotNone(ing.parse_record('{"seq":0,"boot":1,"dev":"x"}')[1])
        self.assertIsNotNone(ing.parse_record('{"seq":1.5,"boot":1,"dev":"x"}')[1])
        self.assertIsNotNone(ing.parse_record('{"seq":1,"boot":1}')[1])
        self.assertIsNotNone(ing.parse_record('{"seq":1,"boot":1,"dev":"x","replay":"yes"}')[1])

    def test_no_fix_position_and_bad_utc(self):
        line = firmware_line(1, utc_ms=12345).replace('"valid":true', '"valid":false')
        row, _ = ing.parse_record(line)
        self.assertIsNone(row["lat"])
        self.assertIsNone(row["device_utc_ms"])   # 1970: not a plausible device time


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "t.db")
        self.store = ing.Store(self.path)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_dedupe_and_rejects(self):
        s = self.store
        self.assertEqual(s.ingest(firmware_line(1), recv_ms=1000), "stored")
        self.assertEqual(s.ingest(firmware_line(1, replay=True), recv_ms=2000), "duplicate")
        self.assertEqual(s.ingest(firmware_line(1), recv_ms=3000), "duplicate")
        self.assertEqual(s.ingest(firmware_line(1, boot=4), recv_ms=4000), "stored")   # other boot
        self.assertEqual(s.ingest(b'{"imu1":{}}', recv_ms=5000), "rejected")
        self.assertEqual(s.ingest(b"\xff\xfe", recv_ms=5000), "rejected")
        db = sqlite3.connect(self.path)
        rows = db.execute("SELECT boot, seq, replay, recv_ms, dup_count FROM telemetry ORDER BY boot").fetchall()
        self.assertEqual(rows, [(3, 1, 0, 1000, 2), (4, 1, 0, 4000, 0)])   # first copy kept
        self.assertEqual(db.execute("SELECT COUNT(*) FROM rejects").fetchone()[0], 2)
        db.close()
        self.assertEqual(s.counts, {"stored": 2, "duplicate": 2, "rejected": 2})

    def test_import_log(self):
        self.store.ingest(firmware_line(2, utc_ms=1_790_000_000_000), recv_ms=1_790_000_000_500)
        logp = os.path.join(self.tmp.name, "dump.jsonl")
        with open(logp, "w") as f:
            f.write('{"imu1":{"rms":nan}}\n')
            for s in range(1, 5):
                f.write(firmware_line(s, utc_ms=1_790_000_000_000) + "\n")
        self.assertEqual(self.store.import_log(logp), {"stored": 3, "duplicate": 1, "skipped": 1})
        self.store.close()
        rows, _ = rep.load_db(self.path)
        res = rep.analyse(rows)
        self.assertEqual(res["summary"]["missing_seq"], 0)
        self.assertEqual(res["summary"]["imported_from_log"], 3)
        self.assertEqual(res["summary"]["latency_live"]["n"], 1)   # imported rows have no real receive time
        self.store = ing.Store(self.path)

    def test_reopen_keeps_data(self):
        self.store.ingest(firmware_line(5), recv_ms=1)
        self.store.close()
        self.store = ing.Store(self.path)
        self.assertEqual(self.store.ingest(firmware_line(5), recv_ms=2), "duplicate")


class ReportTests(unittest.TestCase):
    def test_percentiles(self):
        v = list(range(1, 101))
        self.assertEqual(rep.percentile(v, 95), 95)
        self.assertEqual(rep.percentile(v, 50), 50)
        self.assertEqual(rep.percentile([7], 95), 7)
        self.assertIsNone(rep.percentile([], 95))
        self.assertEqual(rep.median([1, 3, 2, 4]), 2.5)
        self.assertEqual(rep.ranges([1, 2, 3, 7, 9, 10]), [(1, 3), (7, 7), (9, 10)])

    def make_rows(self):
        """Boot 3: seq 1..20 live except an outage over 8..12 replayed later, 15 never arrived.
        Boot 4 starts at seq 65 (reserved block skipped at reboot): not a gap."""
        rows = []
        t0 = 1_790_000_000_000
        for s in range(1, 21):
            if s == 15:
                continue
            dev_t = t0 + s * 10_000
            if 8 <= s <= 12:
                recv = t0 + 13 * 10_000 + 500 + (s - 8) * 400   # replayed after the outage, 0.4 s apart
                rows.append(dict(dev=DEV, boot=3, seq=s, replay=1, recv_ms=recv, device_utc_ms=dev_t,
                                 up_ms=s * 10_000, dup_count=0))
            else:
                rows.append(dict(dev=DEV, boot=3, seq=s, replay=0, recv_ms=dev_t + 300 + s * 10,
                                 device_utc_ms=dev_t, up_ms=s * 10_000, dup_count=1 if s == 13 else 0))
        for s in range(65, 70):
            rows.append(dict(dev=DEV, boot=4, seq=s, replay=0, recv_ms=t0 + s * 10_000, device_utc_ms=None,
                             up_ms=(s - 64) * 10_000, dup_count=0))
        return rows

    def test_analyse(self):
        res = rep.analyse(self.make_rows(), rejects=2)
        s = res["summary"]
        self.assertEqual(s["records_stored"], 24)
        self.assertEqual(s["missing_seq"], 1)
        b3 = [b for b in res["boots"] if b["boot"] == 3][0]
        self.assertEqual(b3["missing_ranges"], [(15, 15)])
        self.assertEqual((b3["replayed"], b3["duplicates"]), (5, 1))
        b4 = [b for b in res["boots"] if b["boot"] == 4][0]
        self.assertEqual((b4["first_seq"], b4["missing"]), (65, 0))
        live = s["latency_live"]
        self.assertEqual(live["n"], 14)
        lats = sorted(300 + q * 10 for q in [1, 2, 3, 4, 5, 6, 7, 13, 14, 16, 17, 18, 19, 20])
        self.assertEqual(live["p95_ms"], lats[13])          # ceil(14 * 0.95) = 14th value
        self.assertEqual(live["median_ms"], (lats[6] + lats[7]) / 2)
        self.assertEqual(s["latency_replay"]["n"], 5)
        self.assertEqual(len(res["episodes"]), 1)
        ep = res["episodes"][0]
        self.assertEqual(ep["records"], 5)
        self.assertAlmostEqual(ep["drain_s"], 1.6)
        self.assertAlmostEqual(ep["rate_per_s"], 2.5)
        self.assertAlmostEqual(ep["outage_span_s"], 50.0)    # seq 8..12, 40 s apart + one period
        text = rep.format_text(res)
        self.assertIn("missing 1 [15]", text)
        self.assertIn("Replay episode 1", text)

    def test_log_comparison(self):
        rows = self.make_rows()
        log = [dict(dev=DEV, boot=3, seq=s, up_ms=None, device_utc_ms=None) for s in range(1, 23)]
        res = rep.analyse(rows, log)
        s = res["summary"]
        self.assertEqual(s["log_records"], 22)
        self.assertEqual(s["log_records_missing_in_db"], 3)   # 15, and 21-22 at the end of the boot
        self.assertEqual(s["missing_seq"], 3)                  # the log reveals the tail
        self.assertEqual(s["db_records_not_in_log"], 5)        # boot 4 not in this log copy
        self.assertAlmostEqual(s["completeness_vs_log_pct"], 100 * 19 / 22)

    def test_cli_csv_and_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbp = os.path.join(tmp, "t.db")
            st = ing.Store(dbp)
            for s in range(1, 6):
                st.ingest(firmware_line(s, utc_ms=1_790_000_000_000 + s * 10_000),
                          recv_ms=1_790_000_000_000 + s * 10_000 + 800)
            st.close()
            logp = os.path.join(tmp, "dump.jsonl")
            with open(logp, "w") as f:   # log_dump.py output; one older line with nan, one v0.7.3 line
                f.write('{"imu1":{"rms":nan}}\n')
                for s in range(1, 6):
                    f.write(firmware_line(s).replace('"rpm":null', '"rpm":nan') + "\n")
            prefix = os.path.join(tmp, "out", "sync")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = rep.main(["--db", dbp, "--log", logp, "--csv", prefix, "--check"])
            out = buf.getvalue()
            self.assertEqual(code, 0, out)
            self.assertIn("median 800 ms", out)
            self.assertIn("100.00%", out)
            for name in ("summary", "boots", "latency", "replay"):
                self.assertTrue(os.path.exists(f"{prefix}_{name}.csv"))
            with open(f"{prefix}_latency.csv") as f:
                self.assertEqual(len(f.readlines()), 6)
            # A missing record makes --check fail.
            with open(logp, "a") as f:
                f.write(firmware_line(6) + "\n")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(rep.main(["--db", dbp, "--log", logp, "--check"]), 1)
                self.assertEqual(rep.main(["--db", dbp, "--check", "--max-p95-ms", "500"]), 1)


# ---------------------------------------------------------------------------
# Minimal MQTT 3.1.1 broker for the end-to-end test
# ---------------------------------------------------------------------------
def _enc_len(n):
    out = bytearray()
    while True:
        b = n % 128
        n //= 128
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _str(b, i):
    n = int.from_bytes(b[i:i + 2], "big")
    return b[i + 2:i + 2 + n].decode(), i + 2 + n


class FakeBroker(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self):
        self.subs = []          # (handler, filter, qos)
        self.lock = threading.Lock()
        self.received = 0
        super().__init__(("127.0.0.1", 0), _Handler)

    def route(self, topic, payload):
        with self.lock:
            targets = [(h, q) for h, f, q in self.subs
                       if f == topic or f == "#" or (f.endswith("/#") and topic.startswith(f[:-2]))]
        for h, q in targets:
            h.send_publish(topic, payload, min(q, 1))


class _Handler(socketserver.BaseRequestHandler):
    def setup(self):
        self.wlock = threading.Lock()
        self.pid = 0

    def send(self, data):
        with self.wlock:
            self.request.sendall(data)

    def send_publish(self, topic, payload, qos):
        t = topic.encode()
        body = len(t).to_bytes(2, "big") + t
        if qos:
            self.pid = self.pid % 65535 + 1
            body += self.pid.to_bytes(2, "big")
        body += payload
        self.send(bytes([0x30 | (qos << 1)]) + _enc_len(len(body)) + body)

    def recv_exact(self, n):
        b = b""
        while len(b) < n:
            c = self.request.recv(n - len(b))
            if not c:
                raise ConnectionError
            b += c
        return b

    def handle(self):
        srv = self.server
        try:
            while True:
                h = self.recv_exact(1)[0]
                n, mult = 0, 1
                while True:
                    d = self.recv_exact(1)[0]
                    n += (d & 0x7F) * mult
                    mult *= 128
                    if not d & 0x80:
                        break
                body = self.recv_exact(n) if n else b""
                kind = h >> 4
                if kind == 1:                                  # CONNECT
                    self.send(b"\x20\x02\x00\x00")
                elif kind == 8:                                # SUBSCRIBE
                    pid, i, granted = body[:2], 2, bytearray()
                    while i < len(body):
                        f, i = _str(body, i)
                        q = body[i] & 3
                        i += 1
                        with srv.lock:
                            srv.subs.append((self, f, q))
                        granted.append(min(q, 1))
                    self.send(bytes([0x90]) + _enc_len(2 + len(granted)) + pid + bytes(granted))
                elif kind == 3:                                # PUBLISH
                    qos = (h >> 1) & 3
                    topic, i = _str(body, 0)
                    if qos:
                        pid = body[i:i + 2]
                        i += 2
                        self.send(b"\x40\x02" + pid)
                    srv.received += 1
                    srv.route(topic, body[i:])
                elif kind == 12:                               # PINGREQ
                    self.send(b"\xd0\x00")
                elif kind == 14:                               # DISCONNECT
                    break
                # PUBACK (4) and anything else: ignored
        except (ConnectionError, OSError):
            pass
        finally:
            with srv.lock:
                srv.subs = [s for s in srv.subs if s[0] is not self]


try:
    import paho.mqtt.client as mqtt
except ImportError:   # pragma: no cover
    mqtt = None


@unittest.skipIf(mqtt is None, "paho-mqtt not installed")
class BrokerEndToEndTest(unittest.TestCase):
    def test_ingest_through_broker(self):
        broker = FakeBroker()
        port = broker.server_address[1]
        threading.Thread(target=broker.serve_forever, daemon=True).start()
        tmp = tempfile.TemporaryDirectory()
        try:
            dbp = os.path.join(tmp.name, "e2e.db")
            store = ing.Store(dbp)
            cfg = {"host": "127.0.0.1", "port": port, "user": None, "password": None, "topic": "sw7/telemetry",
                   "tls": False, "client_id": "sw7-ingest-test", "quiet": True}
            logs = []
            client = ing.make_client(cfg, store, log=logs.append)
            client.connect("127.0.0.1", port, keepalive=30)
            client.loop_start()
            deadline = time.time() + 5
            while not client.sw7_state["subscribed"] and time.time() < deadline:
                time.sleep(0.02)
            self.assertTrue(client.sw7_state["subscribed"], logs)

            try:
                pub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="fake-esp32")
            except AttributeError:
                pub = mqtt.Client(client_id="fake-esp32")
            pub.connect("127.0.0.1", port)
            pub.loop_start()
            now = int(time.time() * 1000)
            # Live 1..10, outage over 4..6, then the replays, one QoS 1 redelivery and one v0.7.3 record.
            for s in range(1, 11):
                if 4 <= s <= 6:
                    continue
                pub.publish("sw7/telemetry", firmware_line(s, utc_ms=now), qos=1).wait_for_publish(5)
            for s in (4, 5, 6):
                pub.publish("sw7/telemetry", firmware_line(s, utc_ms=now - 60_000, replay=True), qos=1)
            pub.publish("sw7/telemetry", firmware_line(9, utc_ms=now), qos=1)
            pub.publish("sw7/telemetry", '{"imu1":{"rms":9.8}}', qos=1).wait_for_publish(5)
            deadline = time.time() + 5
            while sum(store.counts.values()) < 12 and time.time() < deadline:
                time.sleep(0.02)
            pub.disconnect()
            pub.loop_stop()
            client.disconnect()
            client.loop_stop()
            self.assertEqual(store.counts, {"stored": 10, "duplicate": 1, "rejected": 1})
            store.close()
            rows, rejects = rep.load_db(dbp)
            res = rep.analyse(rows, rejects=rejects)
            self.assertEqual(res["summary"]["missing_seq"], 0)
            self.assertEqual(res["summary"]["replayed_stored"], 3)
            self.assertEqual(res["summary"]["duplicates_received"], 1)
            self.assertEqual(res["summary"]["latency_live"]["n"], 7)
            self.assertGreaterEqual(res["summary"]["latency_replay"]["min_ms"], 60_000)
        finally:
            broker.shutdown()
            broker.server_close()
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
