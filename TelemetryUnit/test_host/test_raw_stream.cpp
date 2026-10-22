// Host-side test of the raw IMU stream (TelemetryUnit/include/raw_stream.h)
// and the MQTT position scrub (include/payload_privacy.h). No ESP32 needed.
//
// Build and run on the laptop, from TelemetryUnit/:
//   g++ -std=c++11 -O1 -Wall -Iinclude test_host/test_raw_stream.cpp -o test_raw_stream
//   ./test_raw_stream [capture.txt expected.csv]
// Or: python test_host/run.py (runs every host test, then the Python decoder
// tools/raw_stream_decode.py on the capture this test writes).
//
// With two arguments the test also writes a simulated capture (RAW, RAWH,
// RAWS and DASH lines interleaved, plus a damaged line and a line with other
// output in front of it) and the samples the decoder must recover from it,
// so the Python decoder is checked against bytes made by the firmware's own
// encoder.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <random>
#include <string>
#include <vector>

#include "payload_privacy.h"
#include "raw_stream.h"

static int failures = 0;
static int checks = 0;
#define CHECK(cond)                                                       \
  do {                                                                    \
    checks++;                                                             \
    if (!(cond)) {                                                        \
      failures++;                                                         \
      printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);              \
    }                                                                     \
  } while (0)

static RawSample mk(uint32_t seq, int64_t t, uint8_t flags, int16_t a, int16_t b, int16_t c, int16_t d, int16_t e,
                    int16_t f) {
  RawSample s;
  s.seq = seq;
  s.t_us = t;
  s.flags = flags;
  s.v[0] = a; s.v[1] = b; s.v[2] = c; s.v[3] = d; s.v[4] = e; s.v[5] = f;
  return s;
}

static void testCrc() {
  CHECK(rawCrc16("123456789", 9) == 0x29B1);  // CRC-16/CCITT-FALSE check value
  CHECK(rawCrc16("", 0) == 0xFFFF);
}

static void testEncodeLayout() {
  RawSample s[3];
  // Sample 0: ax +1 count, ay 4096 (1 g), az -276, gx -100, gy 0, gz -66, sync pin high
  s[0] = mk(1000, 5000000, RAW_FLAG_SYNC, 1, 4096, -276, -100, 0, -66);
  // Sample 1: 5000 us later, stuck flag
  s[1] = mk(1001, 5005000, RAW_FLAG_SYNC | RAW_FLAG_STUCK, 0, 4096, -276, -100, 0, -66);
  // Sample 2: seq jumps by 3 (two missing), 5001 us later, extremes; flag bits
  // outside the defined ones are not sent
  s[2] = mk(1004, 5010001, 0xF0, -32768, 1, 0, 0, -1, 32767);
  char line[RAW_LINE_MAX];
  const size_t n = rawEncodeLine(line, sizeof(line), "rear", 2, s, 3);
  CHECK(n > 0 && line[n - 1] == '\n' && strlen(line) == n);
  printf("example line: %s", line);
  CHECK(strncmp(line, "RAW 2 rear 2 1000 5000000 3 ", 28) == 0);
  const char* r0 = line + 28;
  CHECK(strncmp(r0, "00" "0000" "01" "0001" "1000" "feec" "ff9c" "0000" "ffbe", 32) == 0);
  const char* r1 = r0 + 32;
  CHECK(strncmp(r1, "01" "1388" "03" "0000" "1000" "feec" "ff9c" "0000" "ffbe", 32) == 0);  // dt 5000 = 0x1388
  const char* r2 = r1 + 32;
  CHECK(strncmp(r2, "03" "1389" "00" "8000" "0001" "0000" "0000" "ffff" "7fff", 32) == 0);  // dseq 3, dt 5001
  const char* crcp = r2 + 32;
  CHECK(*crcp == ' ');
  char want[8];
  snprintf(want, sizeof(want), "%04x", rawCrc16(line, (size_t)(crcp - line)));
  CHECK(strncmp(crcp + 1, want, 4) == 0);
  CHECK(crcp[5] == '\n' && crcp + 6 == line + n);
}

static void testLimits() {
  RawSample s[RAW_BATCH + 1];
  for (int k = 0; k <= RAW_BATCH; k++) {
    s[k] = mk(4294967200u + (uint32_t)k, 9223372036854000000LL + 5000LL * k, 3, -32768, -32768, -32768, -32768,
              -32768, -32768);
  }
  char line[RAW_LINE_MAX];
  size_t n = rawEncodeLine(line, sizeof(line), "front", 2, s, RAW_BATCH);
  printf("longest RAW line: %u bytes (RAW_LINE_MAX %d)\n", (unsigned)n, RAW_LINE_MAX);
  CHECK(n > 0 && n < RAW_LINE_MAX);
  CHECK(rawEncodeLine(line, sizeof(line), "rear", 2, s, RAW_BATCH + 1) == 0);  // too many samples
  CHECK(rawEncodeLine(line, sizeof(line), "rear", 2, s, 0) == 0);
  CHECK(rawEncodeLine(line, 100, "rear", 2, s, RAW_BATCH) == 0);               // buffer too small
  CHECK(rawEncodeLine(line, sizeof(line), "", 2, s, 1) == 0);                  // bad node names
  CHECK(rawEncodeLine(line, sizeof(line), "re ar", 2, s, 1) == 0);
  CHECK(rawEncodeLine(line, sizeof(line), "toolongname", 2, s, 1) == 0);
  // Gaps the record cannot express.
  RawSample a = s[0], b = s[1];
  b.seq = a.seq + 256;
  CHECK(!rawFits(a, b));
  b.seq = a.seq + 255;
  CHECK(rawFits(a, b));
  b.t_us = a.t_us + 65536;
  CHECK(!rawFits(a, b));
  b.t_us = a.t_us - 1;
  CHECK(!rawFits(a, b));
  b.seq = a.seq;
  b.t_us = a.t_us + 5000;
  CHECK(!rawFits(a, b));  // repeated seq
  RawSample pair[2] = {a, b};
  CHECK(rawEncodeLine(line, sizeof(line), "rear", 1, pair, 2) == 0);
  // seq wrap-around 0xFFFFFFFF -> 0 is a step of 1 and fits.
  RawSample w0 = mk(0xFFFFFFFFu, 100, 0, 1, 2, 3, 4, 5, 6), w1 = mk(0, 5100, 0, 1, 2, 3, 4, 5, 7);
  CHECK(rawFits(w0, w1));
  // Header and sync lines.
  char small[RAW_SMALL_LINE_MAX];
  n = rawEncodeHeader(small, sizeof(small), "front", 1, 4096, 65.5f, 200, 94, "0.7.5", 4294967295u, 4294967295u,
                      4294967295u);
  printf("longest RAWH line: %u bytes (RAW_SMALL_LINE_MAX %d)\n", (unsigned)n, RAW_SMALL_LINE_MAX);
  CHECK(n > 0 && n < RAW_SMALL_LINE_MAX);
  CHECK(strncmp(small, "RAWH 2 front 1 4096 65.5 200 94 0.7.5 4294967295 4294967295 4294967295 ", 71) == 0);
  n = rawEncodeSync(small, sizeof(small), "front", 4294967295u, 1, 9223372036854775807LL);
  printf("longest RAWS line: %u bytes\n", (unsigned)n);
  CHECK(n > 0 && n < RAW_SMALL_LINE_MAX);
  n = rawEncodeSync(small, sizeof(small), "rear", 7, 0, 1234567);
  CHECK(n > 0 && strncmp(small, "RAWS 2 rear 7 0 1234567 ", 24) == 0);
  snprintf(line, sizeof(line), "%04x\n", rawCrc16(small, n - 6));
  CHECK(strcmp(small + n - 5, line) == 0);
}

static void testDecode() {
  RawSample s[RAW_BATCH];
  for (int k = 0; k < RAW_BATCH; k++) {
    s[k] = mk(77, 1000000 + 5000 * k + (k % 3), (uint8_t)(k & 3), (int16_t)(k * 1000),
              (int16_t)-k, 4096, (int16_t)(-32768 + k), 32767, (int16_t)(k * 7));
  }
  // Steps of 1, and one of 3 (two samples missing).
  for (int k = 1; k < RAW_BATCH; k++) s[k].seq = s[k - 1].seq + (k == 4 ? 3 : 1);
  char line[RAW_LINE_MAX];
  const size_t n = rawEncodeLine(line, sizeof(line), "rear", 1, s, RAW_BATCH);
  CHECK(n > 0);
  RawDecoded d;
  CHECK(rawDecodeLine(line, &d) == 1);
  CHECK(strcmp(d.node, "rear") == 0 && d.imu == 1 && d.n == RAW_BATCH);
  bool same = true;
  for (int k = 0; k < RAW_BATCH; k++) {
    same = same && d.s[k].seq == s[k].seq && d.s[k].t_us == s[k].t_us && d.s[k].flags == s[k].flags;
    for (int a = 0; a < 6; a++) same = same && d.s[k].v[a] == s[k].v[a];
  }
  CHECK(same);
  // Other output in front of the line still decodes.
  std::string junk = std::string("--- Acquisition stats (2s window) ---") + line;
  CHECK(rawDecodeLine(junk.c_str(), &d) == 1);
  // Any one changed character is caught.
  int caught = 0, tried = 0;
  for (size_t i = 0; i + 1 < n; i++) {
    std::string bad(line);
    bad[i] = (bad[i] == '1') ? '2' : '1';
    tried++;
    if (rawDecodeLine(bad.c_str(), &d) != 1) caught++;
  }
  CHECK(caught == tried);
  // A cut line (lost bytes on the link) is caught.
  std::string cut(line);
  cut.erase(100, 32);
  CHECK(rawDecodeLine(cut.c_str(), &d) == -1);
  CHECK(rawDecodeLine("DASH {\"seq\":1}", &d) == 0);
}

// The FreeRTOS queue stand-in: bounded, try once, never wait.
struct Ring {
  std::vector<RawItem> buf;
  size_t cap;
  explicit Ring(size_t c) : cap(c) {}
  bool trySend(const RawItem& it) {
    if (buf.size() >= cap) return false;
    buf.push_back(it);
    return true;
  }
};

struct Expected {
  uint8_t imu;
  RawSample s;
};

// Simulates the firmware path end to end: two IMU producers at 200 Hz with
// read failures and stuck reads, a bounded queue, a sender that is starved
// now and then (so the queue overflows), batching into lines, a port that is
// sometimes full (lines given up), sync edges and DASH lines in between.
// Checks that every sample produced is either decoded or counted (rdfail,
// queue drop, port drop), and that the gaps in seq add up to those counts.
static void testDropAccounting(const char* capturePath, const char* expectedPath) {
  std::mt19937 rng(12345);
  Ring q(200);  // RAW_QUEUE_LENGTH
  volatile uint32_t queueDropped[2] = {0, 0};
  uint32_t portDropped[2] = {0, 0};
  ImuHealth health[2] = {};
  uint32_t seq[2] = {0, 0};
  int16_t last[2][6] = {{0}};
  RawBatch batch[2] = {};
  std::vector<std::string> out;           // the capture, line by line
  std::vector<Expected> delivered;        // samples in lines that reached the port
  uint32_t produced[2] = {0, 0};
  uint32_t syncEdge = 0;
  uint8_t syncLevel = 0;
  int damagedWritten = 0, junkWritten = 0;
  char line[RAW_LINE_MAX];

  auto flush = [&](uint8_t imu) {
    RawBatch& b = batch[imu];
    if (b.n == 0) return;
    size_t n = rawEncodeLine(line, sizeof(line), "rear", (uint8_t)(imu + 1), b.s, b.n);
    CHECK(n > 0);
    const bool portFull = (rng() % 50) == 0;  // 2 % of lines find the port full
    if (portFull) {
      portDropped[imu] += b.n;
    } else {
      std::string l(line);
      if ((rng() % 40) == 0) {
        l = "[SYNC] pin=HIGH  t=1 us" + l;  // another task's text in front: still decodes
        junkWritten++;
      }
      out.push_back(l);
      for (int k = 0; k < b.n; k++) delivered.push_back({imu, b.s[k]});
    }
    b.n = 0;
  };

  const int64_t t0 = 3000000;
  const int slots = 200 * 60;  // one minute at 200 Hz
  int starvedUntil = -1;
  for (int slot = 0; slot < slots; slot++) {
    const int64_t now = t0 + 5000LL * slot;
    if (slot % 100 == 0) {  // sync edge every 500 ms
      syncLevel ^= 1;
      syncEdge++;
      rawEncodeSync(line, sizeof(line), "rear", syncEdge, syncLevel, now);
      out.push_back(line);
    }
    if (slot % 200 == 50) {  // DASH once a second
      char dash[128];
      snprintf(dash, sizeof(dash), "DASH {\"seq\":%d,\"node\":\"rear\",\"rawdrop\":[%u,%u]}\n", slot / 200,
               (unsigned)(queueDropped[0] + portDropped[0]), (unsigned)(queueDropped[1] + portDropped[1]));
      out.push_back(dash);
    }
    if (slot % 1000 == 0) {
      for (uint8_t imu = 0; imu < 2; imu++) {
        rawEncodeHeader(line, sizeof(line), "rear", (uint8_t)(imu + 1), 4096, 65.5f, 200, 94, "0.7.5",
                        queueDropped[imu] + portDropped[imu], health[imu].rdfail, health[imu].stuck);
        out.push_back(line);
      }
    }
    if (slot == 3000) {  // a damaged line, as from a noisy link
      out.push_back("RAW 2 rear 1 5 5 1 00000000000000000000000000000000 0000\n");
      damagedWritten++;
    }
    // Producers.
    for (uint8_t imu = 0; imu < 2; imu++) {
      const uint32_t s = seq[imu]++;
      const bool ok = (rng() % 300) != 0;  // a read failure now and then
      int16_t v[6];
      const bool repeat = (rng() % 400) == 0;
      for (int a = 0; a < 6; a++) v[a] = repeat ? last[imu][a] : (int16_t)(rng() % 65536);
      const bool stuck = imuHealthNote(health[imu], ok, v);
      if (!ok) continue;
      for (int a = 0; a < 6; a++) last[imu][a] = v[a];
      produced[imu]++;
      RawItem it;
      it.imu = imu;
      it.s.seq = s;
      it.s.t_us = now + imu * 37 + (rng() % 50);  // read jitter
      it.s.flags = (uint8_t)((syncLevel ? RAW_FLAG_SYNC : 0) | (stuck ? RAW_FLAG_STUCK : 0));
      for (int a = 0; a < 6; a++) it.s.v[a] = v[a];
      rawOffer(q, it, &queueDropped[imu]);
    }
    // Consumer: normally drains everything every slot; starved for up to
    // 1.5 s at random (as if the port or core 0 were busy), so the 200-deep
    // queue overflows.
    if (starvedUntil < slot && (rng() % 2000) == 0) starvedUntil = slot + 100 + (int)(rng() % 200);
    if (slot > starvedUntil) {
      for (const RawItem& it : q.buf) {
        RawBatch& b = batch[it.imu];
        if (!rawBatchAdd(b, it.s)) {
          flush(it.imu);
          CHECK(rawBatchAdd(b, it.s));
        }
        if (b.n >= RAW_BATCH) flush(it.imu);
      }
      q.buf.clear();
      for (uint8_t imu = 0; imu < 2; imu++) {
        if (batch[imu].n > 0 && now - batch[imu].s[0].t_us > 100000) flush(imu);
      }
    }
  }
  for (const RawItem& it : q.buf) {
    RawBatch& b = batch[it.imu];
    if (!rawBatchAdd(b, it.s)) {
      flush(it.imu);
      rawBatchAdd(b, it.s);
    }
  }
  q.buf.clear();
  flush(0);
  flush(1);

  // Decode the capture with the C++ decoder.
  std::vector<Expected> decoded;
  int good = 0, bad = 0;
  for (const std::string& l : out) {
    RawDecoded d;
    const int r = rawDecodeLine(l.c_str(), &d);
    if (r == 1) {
      good++;
      for (int k = 0; k < d.n; k++) decoded.push_back({(uint8_t)(d.imu - 1), d.s[k]});
    } else if (r == -1) {
      bad++;
    }
  }
  CHECK(bad == damagedWritten);
  CHECK(decoded.size() == delivered.size());
  bool same = decoded.size() == delivered.size();
  for (size_t i = 0; same && i < decoded.size(); i++) {
    same = decoded[i].imu == delivered[i].imu && decoded[i].s.seq == delivered[i].s.seq &&
           decoded[i].s.t_us == delivered[i].s.t_us && decoded[i].s.flags == delivered[i].s.flags &&
           memcmp(decoded[i].s.v, delivered[i].s.v, sizeof(decoded[i].s.v)) == 0;
  }
  CHECK(same);

  // Accounting per IMU: produced = delivered + queue drops + port drops, and
  // the missing seq numbers = read failures + queue drops + port drops.
  for (uint8_t imu = 0; imu < 2; imu++) {
    uint32_t got = 0, stuckFlags = 0;
    std::vector<bool> seen(slots, false);
    for (const Expected& e : decoded) {
      if (e.imu != imu) continue;
      got++;
      seen[e.s.seq] = true;
      if (e.s.flags & RAW_FLAG_STUCK) stuckFlags++;
    }
    uint32_t missing = 0;
    for (int i = 0; i < slots; i++) missing += seen[i] ? 0 : 1;
    printf("imu%u: slots %d, produced %u, decoded %u, rdfail %u, stuck %u, queue drops %u, port drops %u\n",
           imu + 1, slots, (unsigned)produced[imu], (unsigned)got, (unsigned)health[imu].rdfail,
           (unsigned)health[imu].stuck, (unsigned)queueDropped[imu], (unsigned)portDropped[imu]);
    CHECK(produced[imu] == got + queueDropped[imu] + portDropped[imu]);
    CHECK(missing == health[imu].rdfail + queueDropped[imu] + portDropped[imu]);
    CHECK(health[imu].rdfail > 0 && queueDropped[imu] > 0 && portDropped[imu] > 0);  // every path exercised
    CHECK(health[imu].stuck > 0 && stuckFlags <= health[imu].stuck);
  }
  CHECK(junkWritten > 0);

  if (capturePath && expectedPath) {
    FILE* f = fopen(capturePath, "wb");
    CHECK(f != nullptr);
    if (f) {
      for (const std::string& l : out) fwrite(l.data(), 1, l.size(), f);
      fclose(f);
    }
    FILE* e = fopen(expectedPath, "wb");
    CHECK(e != nullptr);
    if (e) {
      fprintf(e, "node,imu,seq,t_us,flags,ax,ay,az,gx,gy,gz\n");
      for (const Expected& x : decoded) {
        fprintf(e, "rear,%u,%lu,%lld,%u,%d,%d,%d,%d,%d,%d\n", (unsigned)(x.imu + 1), (unsigned long)x.s.seq,
                (long long)x.s.t_us, (unsigned)x.s.flags, x.s.v[0], x.s.v[1], x.s.v[2], x.s.v[3], x.s.v[4],
                x.s.v[5]);
      }
      fprintf(e, "# raw_lines=%d bad_lines=%d sync_lines=%u dash_lines=%d\n", good, bad, (unsigned)syncEdge, 60);
      fclose(e);
    }
    printf("capture written: %s (%u lines), expected samples: %s\n", capturePath, (unsigned)out.size(),
           expectedPath);
  }
}

static void testHealth() {
  ImuHealth h = {};
  int16_t a[6] = {1, 2, 3, 4, 5, 6}, b[6] = {1, 2, 3, 4, 5, 7};
  CHECK(!imuHealthNote(h, true, a));   // first read: nothing to compare with
  CHECK(imuHealthNote(h, true, a));    // identical: stuck
  CHECK(!imuHealthNote(h, false, b));  // failed read: counted, not compared
  CHECK(imuHealthNote(h, true, a));    // still identical to the last good read
  CHECK(!imuHealthNote(h, true, b));
  CHECK(h.rdfail == 1 && h.stuck == 2);
}

static void testScrub() {
  // Shape of buildTelemetryJson() in src/main.cpp (v0.7.5), with a fix and a cell position.
  const char* rec =
      "{\"dev\":\"sw7-esp32-telemetry\",\"fw\":\"0.7.5\",\"boot\":3,\"seq\":41,\"up_ms\":5000,\"utc_ms\":null,"
      "\"imu1\":{\"rms\":9.812,\"std\":0.034,\"p2p\":0.215,\"crest\":1.012,\"jerk\":3.456,\"crossings\":4},"
      "\"fused\":{\"src\":3,\"rms\":9.8,\"std\":0.03,\"p2p\":0.2,\"jerk\":3.4,\"dis\":null},"
      "\"bms\":{\"v\":52.10,\"i\":1.20,\"soc\":80,\"checksum_ok\":true},"
      "\"gnss\":{\"valid\":true,\"lat\":-33.957512,\"lon\":18.460911,\"speed\":12.5},"
      "\"cell\":{\"csq\":17,\"lat\":null,\"lon\":null,\"acc_m\":null},"
      "\"hall\":{\"eps\":2.0,\"rpm\":null}}";
  char out[1280];
  const size_t n = scrubPositionJson(rec, out, sizeof(out));
  CHECK(n > 0 && n == strlen(out));
  const std::string s(out);
  CHECK(s.find("\"lat\"") == std::string::npos && s.find("\"lon\"") == std::string::npos &&
        s.find("acc_m") == std::string::npos && s.find("-33.95") == std::string::npos &&
        s.find("18.46") == std::string::npos);
  CHECK(s.find("\"gnss\":{\"valid\":true,\"speed\":12.5}") != std::string::npos);
  CHECK(s.find("\"cell\":{\"csq\":17}") != std::string::npos);
  CHECK(s.find("\"hall\":{\"eps\":2.0,\"rpm\":null}}") != std::string::npos);
  CHECK(s.find(",,") == std::string::npos && s.find(",}") == std::string::npos && s.find("{,") == std::string::npos);
  // Replayed records carry a prefix; same result after it.
  const std::string replay = std::string("{\"replay\":true,") + (rec + 1);
  char out2[1280];
  CHECK(scrubPositionJson(replay.c_str(), out2, sizeof(out2)) > 0);
  CHECK(std::string(out2) == std::string("{\"replay\":true,") + (out + 1));
  // Position first or last in its object.
  CHECK(scrubPositionJson("{\"lat\":1.5,\"x\":2}", out, sizeof(out)) > 0 && strcmp(out, "{\"x\":2}") == 0);
  CHECK(scrubPositionJson("{\"x\":2,\"lon\":-1}", out, sizeof(out)) > 0 && strcmp(out, "{\"x\":2}") == 0);
  CHECK(scrubPositionJson("{\"lat\":1,\"lon\":2}", out, sizeof(out)) > 0 && strcmp(out, "{}") == 0);
  // Other keys that end in lat or lon stay (the DASH names are not in the record, but be safe).
  CHECK(scrubPositionJson("{\"cell_lat\":1}", out, sizeof(out)) > 0 && strcmp(out, "{\"cell_lat\":1}") == 0);
  // Too small an output buffer gives 0 and an empty string, never a cut record.
  char tiny[20];
  CHECK(scrubPositionJson(rec, tiny, sizeof(tiny)) == 0 && tiny[0] == '\0');
}

int main(int argc, char** argv) {
  testCrc();
  testEncodeLayout();
  testLimits();
  testDecode();
  testHealth();
  testDropAccounting(argc >= 3 ? argv[1] : nullptr, argc >= 3 ? argv[2] : nullptr);
  testScrub();
  printf("%d checks, %d failed\n", checks, failures);
  return failures ? 1 : 0;
}
