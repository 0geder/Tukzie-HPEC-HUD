// Host-side test of the firmware's store-and-forward bookkeeping
// (TelemetryUnit/include/sync_ledger.h). No ESP32 needed.
//
// Build and run on the laptop (any g++ with C++11), from TelemetryUnit/:
//   g++ -std=c++11 -O1 -Wall -Iinclude test_host/test_sync_ledger.cpp -o test_host/test_sync_ledger
//   test_host/test_sync_ledger
// Or: python test_host/run.py
//
// Part 1 checks single cases by hand. Part 2 is a randomised simulation of
// the firmware's use of the ledger (10 s records, RAM buffer flushed every
// 6 records, size-capped log, link outages, failed and unacknowledged
// publishes, power cuts, soft reboots, log clears, logging switched off) and
// checks that after the link returns the backlog drains to zero and every
// record the server never got is counted as lost, except what a power cut
// takes: unflushed RAM lines, and lost counts made since the last NVS save
// (at most 60 s), which the firmware cannot know about.
#include <stdio.h>
#include <stdlib.h>
#include <random>
#include <set>
#include <vector>

#include "sync_ledger.h"

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

static void testBasics() {
  SyncLedger L;
  ledgerInit(L, 0, 0);
  ledgerBoot(L, 1, 0);
  CHECK(L.acked == 0);
  for (uint32_t s = 1; s <= 5; s++) ledgerLiveAck(L, s);
  CHECK(L.acked == 5 && ledgerBacklog(L, 6) == 0 && L.runLo == 0);

  // Outage: 6..8 not acknowledged, 9 and 10 acknowledged live after reconnect.
  ledgerLiveAck(L, 9);
  ledgerLiveAck(L, 10);
  CHECK(L.acked == 5 && L.runLo == 9 && L.runHi == 10);
  CHECK(ledgerBacklog(L, 11) == 3);
  // Replay scan of the file 1..10.
  uint32_t prevBoot = 0;
  int published = 0;
  for (uint32_t s = 1; s <= 10; s++) {
    if (ledgerOnLogRecord(L, s, 1, prevBoot) == SYNC_SCAN_PUBLISH) {
      published++;
      ledgerReplayAck(L, s);
    }
    prevBoot = 1;
  }
  CHECK(published == 3);
  CHECK(L.acked == 10 && L.runLo == 0 && ledgerBacklog(L, 11) == 0 && L.lost == 0 && L.replayed == 3);
}

static void testGapSameBootIsLost() {
  SyncLedger L;
  ledgerInit(L, 3, 0);
  // File holds 4, then 7 (5 and 6 were never written), same boot.
  CHECK(ledgerOnLogRecord(L, 4, 2, 2) == SYNC_SCAN_PUBLISH);
  ledgerReplayAck(L, 4);
  CHECK(ledgerOnLogRecord(L, 7, 2, 2) == SYNC_SCAN_PUBLISH);
  CHECK(L.lost == 2 && L.acked == 6);
  ledgerReplayAck(L, 7);
  CHECK(L.acked == 7);
}

static void testGapAcrossBootIsNotLost() {
  SyncLedger L;
  ledgerInit(L, 10, 0);
  // Boot 1 logged up to 12 (11 and 12 unacknowledged); boot 2 starts at 65.
  ledgerBoot(L, 65, 12);
  CHECK(L.skipLo == 13 && L.skipHi == 64);
  CHECK(ledgerBacklog(L, 65) == 2);
  ledgerLiveAck(L, 65);
  CHECK(L.runLo == 65);
  CHECK(ledgerBacklog(L, 66) == 2);
  uint32_t prev = 0;
  const uint32_t file[][2] = {{11, 1}, {12, 1}, {65, 2}};
  for (auto& r : file) {
    if (ledgerOnLogRecord(L, r[0], r[1], prev) == SYNC_SCAN_PUBLISH) ledgerReplayAck(L, r[0]);
    prev = r[1];
  }
  CHECK(L.acked == 65 && L.lost == 0 && L.replayed == 2 && ledgerBacklog(L, 66) == 0);

  // Same without the skip range (older boot gap forgotten): the boot change in
  // the file still prevents counting the gap as lost.
  SyncLedger M;
  ledgerInit(M, 12, 0);
  CHECK(ledgerOnLogRecord(M, 70, 3, 2) == SYNC_SCAN_PUBLISH);
  CHECK(M.lost == 0 && M.acked == 69);
}

static void testBootNothingPending() {
  SyncLedger L;
  ledgerInit(L, 40, 5);
  ledgerBoot(L, 129, 40);
  CHECK(L.acked == 128 && L.skipLo == 0 && L.lost == 5);
  ledgerInit(L, 0, 0);
  ledgerBoot(L, 1, 0);  // first boot ever
  CHECK(L.acked == 0 && ledgerBacklog(L, 1) == 0);
}

static void testEof() {
  SyncLedger L;
  ledgerInit(L, 20, 0);
  // Logging was off for 21..25, 26..27 are in the RAM buffer, nothing in the file.
  ledgerOnEof(L, 26, 3, 3, 1);
  CHECK(L.lost == 5 && L.acked == 25 && ledgerBacklog(L, 28) == 2);
  // A live run covering the RAM records is not lost either.
  SyncLedger M;
  ledgerInit(M, 20, 0);
  ledgerLiveAck(M, 23);
  ledgerOnEof(M, 28, 3, 3, 1);
  CHECK(M.lost == 6 && M.acked == 27);
}

static void testUnstored() {
  SyncLedger L;
  ledgerInit(L, 9, 0);
  ledgerUnstoredLost(L, 10);
  CHECK(L.lost == 1 && L.acked == 10);
  ledgerUnstoredLost(L, 12);
  CHECK(L.lost == 2 && L.runLo == 12 && ledgerBacklog(L, 13) == 1);
}

static void testTruncation() {
  SyncLedger L;
  ledgerInit(L, 100, 0);
  ledgerLiveAck(L, 105);  // 101..104 waiting, 105 acknowledged live
  ledgerGiveUpThrough(L, 106);  // file deleted, RAM buffer starts at 107
  CHECK(L.lost == 5 && L.acked == 106 && L.runLo == 0);
}

static void testParse() {
  uint32_t s = 0, b = 0;
  CHECK(syncParseSeqBoot("{\"dev\":\"x\",\"fw\":\"0.7.4\",\"boot\":12,\"seq\":3456,\"up_ms\":1}", &s, &b));
  CHECK(s == 3456 && b == 12);
  CHECK(!syncParseSeqBoot("{\"imu1\":{\"rms\":1.0}}", &s, &b));      // v0.7.3 line
  CHECK(!syncParseSeqBoot("{\"boot\":1,\"seq\":0}", &s, &b));          // seq 0 never used
  CHECK(!syncParseSeqBoot("{\"boot\":1,\"seq\":null}", &s, &b));
  CHECK(!syncParseSeqBoot("{\"boot\":1,\"seq\":99999999999}", &s, &b));
}

static void testGnssTime() {
  CHECK(syncGnssUtcToEpochMs(290926, 214739.00) == 1790718459000LL);
  CHECK(syncGnssUtcToEpochMs(290228, 0.5) == 1835395200500LL);
  CHECK(syncGnssUtcToEpochMs(311226, 235959.0) == 1798761599000LL);
  CHECK(syncGnssUtcToEpochMs(10123, 120000.0) == -1);   // 2023, before the sanity limit
  CHECK(syncGnssUtcToEpochMs(321326, 120000.0) == -1);  // day 32, month 13
  CHECK(syncGnssUtcToEpochMs(290926, 246000.0) == -1);
}

// ---------------------------------------------------------------------------
// Randomised simulation
// ---------------------------------------------------------------------------
struct Rec {
  uint32_t seq, boot;
};

struct Sim {
  std::mt19937 rng;
  // Options
  bool reboots, ackMisses, truncation, clears, loggingToggles;
  size_t fileCap;
  // "NVS"
  uint32_t nvsBoot = 0, nvsSeqBlk = 1, nvsAcked = 0, nvsLost = 0;
  // Device
  uint32_t bootId = 0, bootFirstSeq = 0, nextSeq = 0, seqReservedTo = 0;
  std::vector<Rec> file, ram;
  bool loggingOn = true;
  SyncLedger L;
  size_t replayIdx = 0;
  uint32_t replayPrevBoot = 0;
  bool linkUp = true;
  // Truth
  std::set<uint32_t> generated, delivered, powercutSeqs;
  uint64_t ackMissed = 0, unusedSeqs = 0, replayPublishes = 0, forgotten = 0, vanishedLost = 0;
  int ticks = 0;

  explicit Sim(unsigned seed) : rng(seed) {}
  double u() { return std::uniform_real_distribution<double>(0.0, 1.0)(rng); }

  void boot() {
    bootId = ++nvsBoot;
    bootFirstSeq = nvsSeqBlk;
    nextSeq = bootFirstSeq;
    seqReservedTo = bootFirstSeq + 64;
    nvsSeqBlk = seqReservedTo;
    ledgerInit(L, nvsAcked, nvsLost);
    uint32_t last = file.empty() ? 0 : file.back().seq;
    ledgerBoot(L, bootFirstSeq, last);
    replayIdx = 0;
    replayPrevBoot = 0;
    ram.clear();
  }
  uint32_t newSeq() {
    uint32_t s = nextSeq++;
    if (nextSeq >= seqReservedTo) {
      seqReservedTo += 64;
      nvsSeqBlk = seqReservedTo;
    }
    return s;
  }
  void persist() {
    nvsAcked = L.acked;
    nvsLost = L.lost;
  }
  void flush() {
    if (ram.empty()) return;
    if (truncation && file.size() + ram.size() > fileCap) {
      ledgerGiveUpThrough(L, ram.front().seq - 1);
      file.clear();
      replayIdx = 0;
      replayPrevBoot = 0;
    }
    file.insert(file.end(), ram.begin(), ram.end());
    ram.clear();
    persist();
  }
  bool publish(uint32_t s) {
    if (!linkUp) return false;
    if (u() < 0.03) return false;  // publish failed outright
    delivered.insert(s);
    if (ackMisses && u() < 0.05) {  // broker got it, acknowledgement lost
      ackMissed++;
      return false;
    }
    return true;
  }
  // One pass of the firmware's replay step: at most 25 lines read, at most one publish.
  void replayStep() {
    if (!linkUp || ledgerBacklog(L, nextSeq) == 0) return;
    for (int budget = 0; budget < 25; budget++) {
      if (replayIdx >= file.size()) {
        uint32_t firstUnflushed = ram.empty() ? nextSeq : ram.front().seq;
        ledgerOnEof(L, firstUnflushed, replayPrevBoot, bootId, bootFirstSeq);
        if (ledgerBacklog(L, nextSeq) > 0 && !ram.empty()) flush();
        return;
      }
      const Rec r = file[replayIdx];
      SyncScanAction a = ledgerOnLogRecord(L, r.seq, r.boot, replayPrevBoot);
      replayPrevBoot = r.boot;
      if (a == SYNC_SCAN_SKIP) {
        replayIdx++;
        continue;
      }
      replayPublishes++;
      if (publish(r.seq)) {
        ledgerReplayAck(L, r.seq);
        replayIdx++;
      }
      return;
    }
  }
  void tick() {
    // Events
    if (linkUp && u() < 0.02) linkUp = false;
    else if (!linkUp && u() < 0.08) linkUp = true;
    if (reboots && u() < 0.004) {  // power cut: RAM buffer lost
      for (const Rec& r : ram)
        if (!delivered.count(r.seq)) powercutSeqs.insert(r.seq);
      vanishedLost += L.lost - nvsLost;  // counted since the last NVS save, gone with the power
      unusedSeqs += seqReservedTo - nextSeq;
      forgotten += L.forgotten;
      boot();
    } else if (reboots && u() < 0.003) {  // soft restart: flush first
      flush();
      persist();
      unusedSeqs += seqReservedTo - nextSeq;
      forgotten += L.forgotten;
      boot();
    }
    if (clears && u() < 0.001) {  // !log clear
      flush();
      ledgerGiveUpThrough(L, nextSeq - 1);
      file.clear();
      replayIdx = 0;
      replayPrevBoot = 0;
      persist();
    }
    if (loggingToggles && u() < 0.005) {
      if (loggingOn) flush();
      loggingOn = !loggingOn;
    }
    // The firmware also saves the ledger every 60 s when it changed, so the
    // lost count is kept while logging is off (no flushes then).
    if (++ticks % 6 == 0) persist();
    // One 10 s record
    uint32_t s = newSeq();
    generated.insert(s);
    if (loggingOn) {
      ram.push_back({s, bootId});
      if (ram.size() >= 6) flush();
    }
    if (linkUp && publish(s)) ledgerLiveAck(L, s);
    else if (!loggingOn) ledgerUnstoredLost(L, s);
    for (int i = 0; i < 30; i++) replayStep();  // about 3 per second over 10 s
  }
  void drain() {
    linkUp = true;
    for (int i = 0; i < 200000 && ledgerBacklog(L, nextSeq) > 0; i++) replayStep();
  }
};

static void runSim(const char* name, unsigned seeds, bool reboots, bool ackMisses, bool truncation,
                   bool clears, bool toggles, bool exactLost) {
  int bad = 0;
  uint64_t totGen = 0, totLost = 0, totReplay = 0;
  for (unsigned seed = 1; seed <= seeds; seed++) {
    Sim sim(seed);
    sim.reboots = reboots;
    sim.ackMisses = ackMisses;
    sim.truncation = truncation;
    sim.clears = clears;
    sim.loggingToggles = toggles;
    sim.fileCap = 150;
    sim.boot();
    for (int t = 0; t < 3000; t++) sim.tick();
    sim.drain();
    sim.forgotten += sim.L.forgotten;

    uint64_t undelivered = 0, undeliveredNotPowercut = 0;
    for (uint32_t s : sim.generated) {
      if (!sim.delivered.count(s)) {
        undelivered++;
        if (!sim.powercutSeqs.count(s)) undeliveredNotPowercut++;
      }
    }
    const uint64_t lost = sim.L.lost;
    bool ok = ledgerBacklog(sim.L, sim.nextSeq) == 0;
    ok = ok && undeliveredNotPowercut <= lost + sim.vanishedLost;    // nothing lost silently
    ok = ok && lost <= undelivered + sim.ackMissed + sim.unusedSeqs + sim.forgotten;  // overcount explained
    if (exactLost) ok = ok && lost == undelivered;
    if (!ok) {
      bad++;
      if (bad <= 3)
        printf("  seed %u: backlog=%u undelivered=%llu (not power cut %llu) lost=%llu ackMissed=%llu unused=%llu\n",
               seed, ledgerBacklog(sim.L, sim.nextSeq), (unsigned long long)undelivered,
               (unsigned long long)undeliveredNotPowercut, (unsigned long long)lost,
               (unsigned long long)sim.ackMissed, (unsigned long long)sim.unusedSeqs);
    }
    totGen += sim.generated.size();
    totLost += lost;
    totReplay += sim.L.replayed;
  }
  checks++;
  if (bad) failures++;
  printf("%s %s: %u runs, %llu records, %llu replayed in the last boot, %llu counted lost, %d failing runs\n",
         bad ? "FAIL" : "ok  ", name, seeds, (unsigned long long)totGen, (unsigned long long)totReplay,
         (unsigned long long)totLost, bad);
}

int main() {
  testBasics();
  testGapSameBootIsLost();
  testGapAcrossBootIsNotLost();
  testBootNothingPending();
  testEof();
  testTruncation();
  testUnstored();
  testParse();
  testGnssTime();
  printf("unit checks: %d run, %d failed\n", checks, failures);

  runSim("outages only (lost must be 0)", 200, false, false, false, false, false, true);
  runSim("outages + logging off", 200, false, false, false, false, true, false);
  runSim("outages + truncation + clears", 200, false, false, true, true, false, false);
  runSim("everything (reboots, lost acks, truncation, clears, logging off)", 300, true, true, true, true, true, false);

  printf("%s: %d checks, %d failed\n", failures ? "FAILED" : "PASSED", checks, failures);
  return failures ? 1 : 0;
}
