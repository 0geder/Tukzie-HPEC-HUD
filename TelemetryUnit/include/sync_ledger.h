// Store-and-forward bookkeeping for the telemetry unit (firmware v0.7.4).
//
// Pure C++ with no Arduino, FreeRTOS or file-system dependency, so the same
// code is compiled into the firmware and into the host-side test
// (TelemetryUnit/test_host/test_sync_ledger.cpp, built with g++ on the laptop).
//
// Model
// -----
// Every telemetry record gets a sequence number `seq` (1, 2, 3, ...), unique
// and increasing across reboots. The ledger keeps:
//
//   acked   every seq <= acked is finished: the broker acknowledged it (QoS 1
//           PUBACK, seen as +CMQTTPUB: 0,0), or it was counted as lost, or it
//           never existed (seq numbers skipped at a reboot).
//   run     [runLo, runHi]: a contiguous block of seq above acked+1 that was
//           acknowledged when first published live, while older records were
//           still waiting. RAM only; if a live publish fails, a new run starts
//           and the old one is forgotten (those records are then replayed again,
//           which only costs duplicates, removed by the server).
//   skip    [skipLo, skipHi]: seq numbers that were never used because a reboot
//           jumped to the next reserved block. Treated as finished.
//   lost    records given up without a confirmed delivery (log truncated,
//           cleared, never written). Counted, never skipped silently. A record
//           whose acknowledgement was missed, or which sat in a forgotten run,
//           can be counted here although the broker has it, so `lost` is an
//           upper bound; the server-side report gives the exact figure.
//
// Backlog = seq in (acked, nextSeq) that are in neither run nor skip.
//
// Replay scans the local log in file order (which is seq order, since the log
// is append-only). For each record it calls ledgerOnLogRecord(), which says
// whether to publish it; missing seq numbers before it are counted as lost,
// except across a boot change (seq numbers skipped at a reboot are not lost).
// At the end of the file, ledgerOnEof() handles seq numbers that are in
// neither the file nor the RAM buffer. A successful replay publish calls
// ledgerReplayAck().
//
// Delivery is at least once: after a reboot, `acked` may be up to a minute
// old (it is saved to NVS with the log flush), so a few records are sent twice.
// The server stores each (dev, boot, seq) once.
#pragma once
#include <stdint.h>
#include <string.h>

struct SyncLedger {
  uint32_t acked;
  uint32_t runLo, runHi;    // runLo == 0: no run
  uint32_t skipLo, skipHi;  // skipLo == 0: no skip range
  uint32_t lost;            // cumulative, saved in NVS
  uint32_t replayed;        // this boot
  uint32_t forgotten;       // this boot: live-acked seq dropped with an old run
                            // (they are resent if still in the log, or counted
                            // in `lost` if not, although the broker has them)
};

enum SyncScanAction { SYNC_SCAN_SKIP = 0, SYNC_SCAN_PUBLISH = 1 };

static inline bool syncInRange(uint32_t s, uint32_t lo, uint32_t hi) {
  return lo != 0 && s >= lo && s <= hi;
}

static inline bool ledgerIsFinished(const SyncLedger& L, uint32_t s) {
  return s <= L.acked || syncInRange(s, L.runLo, L.runHi) || syncInRange(s, L.skipLo, L.skipHi);
}

// Number of seq in [lo, hi] overlapping [rlo, rhi] (rlo == 0: empty range).
static inline uint32_t syncOverlap(uint32_t lo, uint32_t hi, uint32_t rlo, uint32_t rhi) {
  if (rlo == 0 || hi < lo) return 0;
  uint32_t a = lo > rlo ? lo : rlo;
  uint32_t b = hi < rhi ? hi : rhi;
  return b >= a ? b - a + 1 : 0;
}

// Seq in [lo, hi] that are not covered by run or skip.
static inline uint32_t ledgerCountOpen(const SyncLedger& L, uint32_t lo, uint32_t hi) {
  if (hi < lo) return 0;
  uint32_t n = hi - lo + 1;
  n -= syncOverlap(lo, hi, L.runLo, L.runHi);
  n -= syncOverlap(lo, hi, L.skipLo, L.skipHi);
  return n;
}

// Absorbs run and skip into acked whenever they start at or below acked+1,
// and drops ranges that lie wholly below acked.
static inline void ledgerMerge(SyncLedger& L) {
  bool changed = true;
  while (changed) {
    changed = false;
    if (L.runLo != 0 && L.runLo <= L.acked + 1) {
      if (L.runHi > L.acked) L.acked = L.runHi;
      L.runLo = L.runHi = 0;
      changed = true;
    }
    if (L.skipLo != 0 && L.skipLo <= L.acked + 1) {
      if (L.skipHi > L.acked) L.acked = L.skipHi;
      L.skipLo = L.skipHi = 0;
      changed = true;
    }
  }
}

static inline void ledgerInit(SyncLedger& L, uint32_t acked, uint32_t lost) {
  memset(&L, 0, sizeof(L));
  L.acked = acked;
  L.lost = lost;
}

// At boot. bootFirstSeq: first seq of this boot (start of the reserved block).
// lastLoggedSeq: highest seq found at the end of the stored log, 0 if none.
// If everything logged is already finished, there is nothing to replay and
// acked moves straight to bootFirstSeq - 1. Otherwise the unused seq numbers
// between the last logged record and this boot become the skip range.
static inline void ledgerBoot(SyncLedger& L, uint32_t bootFirstSeq, uint32_t lastLoggedSeq) {
  L.runLo = L.runHi = 0;
  L.skipLo = L.skipHi = 0;
  L.replayed = 0;
  if (bootFirstSeq == 0) return;
  if (lastLoggedSeq <= L.acked || lastLoggedSeq >= bootFirstSeq) {
    if (bootFirstSeq - 1 > L.acked) L.acked = bootFirstSeq - 1;
    return;
  }
  if (lastLoggedSeq + 1 <= bootFirstSeq - 1) {
    L.skipLo = lastLoggedSeq + 1;
    L.skipHi = bootFirstSeq - 1;
  }
  ledgerMerge(L);
}

// Moves acked up to upTo without counting anything as lost.
static inline void ledgerSkipThrough(SyncLedger& L, uint32_t upTo) {
  if (upTo <= L.acked) return;
  L.acked = upTo;
  if (L.runLo != 0 && L.runHi <= L.acked) L.runLo = L.runHi = 0;
  if (L.skipLo != 0 && L.skipHi <= L.acked) L.skipLo = L.skipHi = 0;
  ledgerMerge(L);
}

// Moves acked up to upTo, counting every open seq on the way as lost.
static inline void ledgerGiveUpThrough(SyncLedger& L, uint32_t upTo) {
  if (upTo <= L.acked) return;
  L.lost += ledgerCountOpen(L, L.acked + 1, upTo);
  ledgerSkipThrough(L, upTo);
}

// A live (first-time) publish of seq s was acknowledged.
static inline void ledgerLiveAck(SyncLedger& L, uint32_t s) {
  if (ledgerIsFinished(L, s)) return;
  if (s == L.acked + 1) {
    L.acked = s;
    ledgerMerge(L);
    return;
  }
  if (L.runLo != 0 && s == L.runHi + 1) {
    L.runHi = s;
    ledgerMerge(L);
    return;
  }
  if (L.runLo != 0) L.forgotten += L.runHi - L.runLo + 1;
  L.runLo = L.runHi = s;  // older run forgotten: replayed again, server dedupes
  ledgerMerge(L);
}

// A record that was not stored locally (logging off, buffer refused it) and
// was not acknowledged live can never be sent: count it as lost now, while
// its seq is known, and treat it as finished. Without this, such a record
// just before a reboot would vanish into the seq numbers skipped at boot.
static inline void ledgerUnstoredLost(SyncLedger& L, uint32_t s) {
  if (ledgerIsFinished(L, s)) return;
  L.lost++;
  ledgerLiveAck(L, s);
}

// A replay publish of seq s was acknowledged (s was returned as PUBLISH by
// ledgerOnLogRecord, so every seq below it is already finished).
static inline void ledgerReplayAck(SyncLedger& L, uint32_t s) {
  if (s > L.acked) {
    L.acked = s;
    ledgerMerge(L);
  }
  L.replayed++;
}

// Replay scan found a record (seq s, boot b) in the log. prevBoot is the boot
// of the previous record that carried a seq in this scan (0 = none yet).
// Missing seq before s are lost, unless the boot changed or is unknown: then
// they were never used (reserved block skipped at reboot).
static inline SyncScanAction ledgerOnLogRecord(SyncLedger& L, uint32_t s, uint32_t b, uint32_t prevBoot) {
  if (ledgerIsFinished(L, s)) return SYNC_SCAN_SKIP;
  if (s > L.acked + 1) {
    if (prevBoot == 0 || prevBoot != b) ledgerSkipThrough(L, s - 1);
    else ledgerGiveUpThrough(L, s - 1);
  }
  if (ledgerIsFinished(L, s)) return SYNC_SCAN_SKIP;
  return SYNC_SCAN_PUBLISH;
}

// Replay scan reached the end of the file. firstUnflushedSeq: seq of the first
// record still in the RAM buffer, or nextSeq if the buffer is empty. Records
// below it that were not in the file are lost, except the seq numbers skipped
// at this boot's start when the last record in the file came from an earlier
// boot (lastFileBoot != bootId, or 0 = no record).
static inline void ledgerOnEof(SyncLedger& L, uint32_t firstUnflushedSeq, uint32_t lastFileBoot,
                               uint32_t bootId, uint32_t bootFirstSeq) {
  if (lastFileBoot != bootId && bootFirstSeq > 0) ledgerSkipThrough(L, bootFirstSeq - 1);
  if (firstUnflushedSeq > 0) ledgerGiveUpThrough(L, firstUnflushedSeq - 1);
}

// Records still waiting to be acknowledged.
static inline uint32_t ledgerBacklog(const SyncLedger& L, uint32_t nextSeq) {
  if (nextSeq == 0) return 0;
  return ledgerCountOpen(L, L.acked + 1, nextSeq - 1);
}

// Reads "seq" and "boot" from a stored record line. The firmware writes them
// near the start ({"dev":...,"fw":...,"boot":N,"seq":N,...}); a line from older
// firmware has neither and returns false.
static inline bool syncParseUint(const char* line, const char* key, uint32_t* out) {
  const char* p = strstr(line, key);
  if (p == nullptr) return false;
  p += strlen(key);
  if (*p < '0' || *p > '9') return false;
  uint64_t v = 0;
  while (*p >= '0' && *p <= '9') {
    v = v * 10 + (uint64_t)(*p - '0');
    if (v > 0xFFFFFFFFull) return false;
    p++;
  }
  *out = (uint32_t)v;
  return true;
}

static inline bool syncParseSeqBoot(const char* line, uint32_t* seq, uint32_t* boot) {
  uint32_t s = 0, b = 0;
  if (!syncParseUint(line, "\"seq\":", &s) || !syncParseUint(line, "\"boot\":", &b)) return false;
  if (s == 0) return false;
  *seq = s;
  *boot = b;
  return true;
}

// GNSS date ddmmyy and time hhmmss.ss (as +CGNSSINFO sends them, UTC) to Unix
// time in ms. Returns -1 for an implausible value (year before 2024, bad
// month/day/time). Days-from-civil after H. Hinnant's public-domain algorithm.
static inline int64_t syncGnssUtcToEpochMs(uint32_t ddmmyy, double hhmmss) {
  const int dd = (int)(ddmmyy / 10000);
  const int mm = (int)((ddmmyy / 100) % 100);
  const int yy = (int)(ddmmyy % 100);
  if (dd < 1 || dd > 31 || mm < 1 || mm > 12 || !(hhmmss >= 0.0) || hhmmss >= 240000.0) return -1;
  const int year = 2000 + yy;
  if (year < 2024) return -1;
  const int hh = (int)(hhmmss / 10000.0);
  const int mi = (int)((long)(hhmmss / 100.0) % 100);
  const double ss = hhmmss - hh * 10000.0 - mi * 100.0;
  if (hh > 23 || mi > 59 || ss < 0.0 || ss >= 61.0) return -1;
  const int y = year - (mm <= 2 ? 1 : 0);
  const int era = y / 400;
  const unsigned yoe = (unsigned)(y - era * 400);
  const unsigned doy = (unsigned)((153 * (mm + (mm > 2 ? -3 : 9)) + 2) / 5 + dd - 1);
  const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  const int64_t days = (int64_t)era * 146097 + (int64_t)doe - 719468;
  return days * 86400000LL + (int64_t)hh * 3600000LL + (int64_t)mi * 60000LL + (int64_t)(ss * 1000.0 + 0.5);
}
