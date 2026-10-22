// Raw IMU stream to the Raspberry Pi (firmware v0.7.5).
//
// Pure C++ with no Arduino or FreeRTOS dependency, so the same code is
// compiled into the firmware and into the host-side test
// (TelemetryUnit/test_host/test_raw_stream.cpp, built with g++ on the laptop).
// The reference decoder in Python is TelemetryUnit/tools/raw_stream_decode.py;
// TelemetryUnit/RAW_STREAM.md has the same description for the Pi side.
//
// Every IMU sample goes to the Pi as text lines on the same link as the DASH
// line (the UART on the rear unit, USB serial on the front node). Every line
// ends in '\n' and starts with its own type word, so the Pi reads lines and
// splits them by the first word: "DASH " (unchanged, 1 Hz), "RAW ", "RAWH "
// and "RAWS ". Lines of other types (boot log, debug prints) are ignored.
// A line is never split by another task's output: each is written with one
// write call, and the Arduino serial drivers hold a lock for the whole call.
//
// All three raw line types end in " <crc>": CRC-16/CCITT-FALSE (poly 0x1021,
// init 0xFFFF, no reflection, no final XOR) of every byte from the first
// letter of the type word up to the character before that space, written as
// 4 lowercase hex digits. A line whose CRC does not match is discarded whole.
//
// Format version 2 (version 1 was the unfinished start without node, flags
// or sync; it was never flashed).
//
// 1. Samples, one line per up to RAW_BATCH consecutive samples of one IMU:
//
//   RAW 2 <node> <imu> <seq0> <t0_us> <n> <hex> <crc>\n
//
//   2      format version
//   node   "rear" (main unit) or "front" (front IMU node)
//   imu    1 or 2 (the front node has IMU 1 only)
//   seq0   the first sample's acquisition slot number. The IMU task counts one
//          slot per 5 ms period, read or not, so a jump in seq is a missing
//          sample: a failed I2C read (rdfail) or a sample the stream dropped
//          (rawdrop). The two counters say which.
//   t0_us  the first sample's esp_timer time, microseconds since boot
//   n      samples in this line, 1 to RAW_BATCH
//   hex    n records of 16 bytes, each written as 32 lowercase hex characters:
//            byte 0      seq step from the previous sample in the line (0 for the first)
//            bytes 1-2   time step from the previous sample, us, unsigned big-endian (0 for the first)
//            byte 3      flags: bit 0 sync pin level when the sample was read,
//                        bit 1 stuck (all six values equal to the previous good read),
//                        bit 2 first sample after the sensor was re-initialised
//                        (v0.7.7; the seq gap before it is the time it was down),
//                        bits 3-7 zero
//            bytes 4-15  ax ay az gx gy gz, signed 16-bit big-endian sensor counts
//   The encoder starts a new line when the seq step is above 255 or the time
//   step above 65535 us, so both always fit.
//
// 2. Header, per IMU at start-up and every RAW_HEADER_PERIOD_MS after:
//
//   RAWH 2 <node> <imu> <accel_counts_per_g> <gyro_counts_per_dps> <rate_hz> <dlpf_hz> <fw> <rawdrop> <rdfail> <stuck> <crc>\n
//
//   Scale factors to turn counts into units (MPU-6050 at +-8 g and +-500 deg/s:
//   4096 and 65.5), the nominal sample rate, the sensor's low-pass filter, the
//   firmware version and the three counters for this IMU since boot.
//     a [m/s^2] = count / accel_counts_per_g * 9.80665
//     w [rad/s] = count / gyro_counts_per_dps * pi / 180
//   Raw counts carry no calibration (the magnitude scale in NVS is not applied).
//   v0.7.7: an extra RAWH for an IMU is also sent right after that IMU was
//   re-initialised, so the recovery shows in the stream next to the gap.
//
// 3. Sync event, one per edge of the sync pulse output (every 500 ms):
//
//   RAWS 2 <node> <edge> <level> <t_us> <crc>\n
//
//   edge   edge counter since boot (1 for the first)
//   level  the new pin level, 0 or 1
//   t_us   esp_timer time read right after the pin was written
//   The Pi timestamps the same edge on its GPIO input with its own clock; the
//   pairs (t_us, Pi time) give the clock offset and drift. Bit 0 of each
//   sample's flags shows on which side of an edge the sample was read.
//
// Axes: the pods are mounted with the lid arrow pointing forward, and the
// arrow is the sensor's +X axis (CAD/IMU_Pod/ENGINEERING_REVIEW.md), so +ax
// is forward acceleration.
#pragma once

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RAW_FORMAT_VERSION 2
#define RAW_BATCH 10                 // samples per line: 50 ms of one IMU at 200 Hz
#define RAW_RECORD_BYTES 16
#define RAW_LINE_MAX 400             // longest RAW line is 375 bytes (test_raw_stream.cpp)
#define RAW_SMALL_LINE_MAX 128       // RAWH and RAWS lines
#define RAW_HEADER_PERIOD_MS 5000
#define RAW_FLAG_SYNC 0x01
#define RAW_FLAG_STUCK 0x02
#define RAW_FLAG_REINIT 0x04         // v0.7.7, same format version: older readers keep the byte as it is
#define RAW_FLAG_MASK (RAW_FLAG_SYNC | RAW_FLAG_STUCK | RAW_FLAG_REINIT)

struct RawSample {
  uint32_t seq;
  int64_t t_us;
  uint8_t flags;
  int16_t v[6];  // ax ay az gx gy gz, counts
};

// One queue element: a sample and the IMU it came from (0 = IMU1, 1 = IMU2).
struct RawItem {
  uint8_t imu;
  RawSample s;
};

static inline uint16_t rawCrc16(const char* s, size_t n) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < n; i++) {
    crc ^= (uint16_t)((uint8_t)s[i]) << 8;
    for (int b = 0; b < 8; b++) crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
  }
  return crc;
}

// Appends " <crc>\n" for the p bytes already in out. Returns the new length,
// or 0 if it does not fit in cap (terminating zero included).
static inline size_t rawAppendCrc(char* out, size_t p, size_t cap) {
  static const char hexd[] = "0123456789abcdef";
  if (p + 7 > cap) return 0;
  const uint16_t crc = rawCrc16(out, p);
  out[p++] = ' ';
  out[p++] = hexd[(crc >> 12) & 0xF];
  out[p++] = hexd[(crc >> 8) & 0xF];
  out[p++] = hexd[(crc >> 4) & 0xF];
  out[p++] = hexd[crc & 0xF];
  out[p++] = '\n';
  out[p] = '\0';
  return p;
}

// True if `next` can follow `prev` in the same line.
static inline bool rawFits(const RawSample& prev, const RawSample& next) {
  const uint32_t dseq = next.seq - prev.seq;
  const int64_t dt = next.t_us - prev.t_us;
  return dseq >= 1 && dseq <= 255 && dt >= 0 && dt <= 65535;
}

// Writes one complete RAW line, newline included, into out. Returns its
// length, or 0 if n is out of range, consecutive samples do not fit (see
// rawFits), the node name is unusable or cap is too small. Never writes past cap.
static inline size_t rawEncodeLine(char* out, size_t cap, const char* node, uint8_t imu,
                                   const RawSample* s, uint8_t n) {
  static const char hexd[] = "0123456789abcdef";
  if (n == 0 || n > RAW_BATCH || node == nullptr || node[0] == '\0' || strlen(node) > 8 ||
      strchr(node, ' ') != nullptr) {
    return 0;
  }
  for (uint8_t k = 1; k < n; k++) {
    if (!rawFits(s[k - 1], s[k])) return 0;
  }
  int len = snprintf(out, cap, "RAW %d %s %u %lu %lld %u ", RAW_FORMAT_VERSION, node, (unsigned)imu,
                     (unsigned long)s[0].seq, (long long)s[0].t_us, (unsigned)n);
  if (len < 0 || (size_t)len + (size_t)n * RAW_RECORD_BYTES * 2 + 7 > cap) return 0;
  size_t p = (size_t)len;
  for (uint8_t k = 0; k < n; k++) {
    uint8_t rec[RAW_RECORD_BYTES];
    const uint32_t dseq = k ? s[k].seq - s[k - 1].seq : 0;
    const uint32_t dt = k ? (uint32_t)(s[k].t_us - s[k - 1].t_us) : 0;
    rec[0] = (uint8_t)dseq;
    rec[1] = (uint8_t)(dt >> 8);
    rec[2] = (uint8_t)(dt & 0xFF);
    rec[3] = (uint8_t)(s[k].flags & RAW_FLAG_MASK);
    for (int a = 0; a < 6; a++) {
      const uint16_t u = (uint16_t)s[k].v[a];
      rec[4 + 2 * a] = (uint8_t)(u >> 8);
      rec[5 + 2 * a] = (uint8_t)(u & 0xFF);
    }
    for (int b = 0; b < RAW_RECORD_BYTES; b++) {
      out[p++] = hexd[rec[b] >> 4];
      out[p++] = hexd[rec[b] & 0x0F];
    }
  }
  return rawAppendCrc(out, p, cap);
}

static inline size_t rawEncodeHeader(char* out, size_t cap, const char* node, uint8_t imu,
                                     unsigned accelCountsPerG, float gyroCountsPerDps, unsigned rateHz,
                                     unsigned dlpfHz, const char* fw, uint32_t rawdrop, uint32_t rdfail,
                                     uint32_t stuck) {
  int len = snprintf(out, cap, "RAWH %d %s %u %u %.1f %u %u %s %lu %lu %lu", RAW_FORMAT_VERSION, node,
                     (unsigned)imu, accelCountsPerG, (double)gyroCountsPerDps, rateHz, dlpfHz, fw,
                     (unsigned long)rawdrop, (unsigned long)rdfail, (unsigned long)stuck);
  if (len < 0 || (size_t)len >= cap) return 0;
  return rawAppendCrc(out, (size_t)len, cap);
}

static inline size_t rawEncodeSync(char* out, size_t cap, const char* node, uint32_t edge, uint8_t level,
                                   int64_t t_us) {
  int len = snprintf(out, cap, "RAWS %d %s %lu %u %lld", RAW_FORMAT_VERSION, node, (unsigned long)edge,
                     (unsigned)(level ? 1 : 0), (long long)t_us);
  if (len < 0 || (size_t)len >= cap) return 0;
  return rawAppendCrc(out, (size_t)len, cap);
}

// ---------------------------------------------------------------------------
// Batching: the sender task collects consecutive samples of one IMU here and
// writes a line when the batch is full, when the next sample cannot follow
// (rawFits), or when the oldest sample has waited too long.
// ---------------------------------------------------------------------------
struct RawBatch {
  uint8_t n;
  RawSample s[RAW_BATCH];
};

// Adds s to b if it fits. Returns false (b unchanged) when b is full or s
// cannot follow its last sample: the caller writes b out, clears it and adds again.
static inline bool rawBatchAdd(RawBatch& b, const RawSample& s) {
  if (b.n >= RAW_BATCH) return false;
  if (b.n > 0 && !rawFits(b.s[b.n - 1], s)) return false;
  b.s[b.n++] = s;
  return true;
}

// ---------------------------------------------------------------------------
// Per-IMU read health: read failures and stuck samples.
// A read fails when the I2C transaction is not acknowledged or returns fewer
// bytes than asked. A sample is stuck when all six values equal the previous
// good read: the MPU-6050 updates its output registers at 1 kHz and the
// 16-bit values carry noise, so two identical reads 5 ms apart mean the
// registers did not update (sensor asleep, reset or hung).
// ---------------------------------------------------------------------------
struct ImuHealth {
  uint32_t rdfail;
  uint32_t stuck;
  bool havePrev;
  int16_t prev[6];
};

// Records one read. Returns true if the sample is stuck (only for ok reads).
static inline bool imuHealthNote(ImuHealth& h, bool ok, const int16_t v[6]) {
  if (!ok) {
    h.rdfail++;
    return false;
  }
  bool same = h.havePrev;
  for (int a = 0; a < 6 && same; a++) same = (v[a] == h.prev[a]);
  for (int a = 0; a < 6; a++) h.prev[a] = v[a];
  h.havePrev = true;
  if (same) h.stuck++;
  return same;
}

// The non-blocking hand-off from an IMU task to the sender: one try, no
// waiting. Q is anything with bool trySend(const RawItem&) (the FreeRTOS
// queue in the firmware, a plain ring in the host test). A sample that does
// not fit is dropped and counted.
template <class Q>
static inline bool rawOffer(Q& q, const RawItem& it, volatile uint32_t* dropped) {
  if (q.trySend(it)) return true;
  (*dropped)++;
  return false;
}

// ---------------------------------------------------------------------------
// Decoder for RAW lines (used by the host test; the Pi uses the Python one).
// Finds "RAW " anywhere in the line, so a line with another task's text in
// front of it still decodes if its CRC is right.
// ---------------------------------------------------------------------------
struct RawDecoded {
  char node[12];
  uint8_t imu;
  uint8_t n;
  RawSample s[RAW_BATCH];
};

static inline int rawHexNibble(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  return -1;
}

// Returns 1 for a good RAW line, 0 for a line that is not a RAW line,
// -1 for a RAW line that is damaged (bad CRC or layout).
static inline int rawDecodeLine(const char* line, RawDecoded* out) {
  const char* p = strstr(line, "RAW 2 ");
  if (p == nullptr) return 0;
  size_t len = strlen(p);
  while (len > 0 && (p[len - 1] == '\n' || p[len - 1] == '\r')) len--;
  if (len < 6 || p[len - 5] != ' ') return -1;
  unsigned crcGot = 0;
  for (int i = 0; i < 4; i++) {
    const int h = rawHexNibble(p[len - 4 + i]);
    if (h < 0) return -1;
    crcGot = (crcGot << 4) | (unsigned)h;
  }
  if (rawCrc16(p, len - 5) != crcGot) return -1;
  char node[12];
  unsigned imu, n;
  unsigned long seq0;
  long long t0;
  int hdr = 0;
  if (sscanf(p, "RAW 2 %11s %u %lu %lld %u %n", node, &imu, &seq0, &t0, &n, &hdr) != 5 || hdr == 0) return -1;
  if (n == 0 || n > RAW_BATCH) return -1;
  const char* hex = p + hdr;
  if ((size_t)(hex - p) + n * RAW_RECORD_BYTES * 2 != len - 5) return -1;
  memcpy(out->node, node, sizeof(node));
  out->imu = (uint8_t)imu;
  out->n = (uint8_t)n;
  uint32_t seq = (uint32_t)seq0;
  int64_t t = (int64_t)t0;
  for (unsigned k = 0; k < n; k++) {
    uint8_t rec[RAW_RECORD_BYTES];
    for (int b = 0; b < RAW_RECORD_BYTES; b++) {
      const int hi = rawHexNibble(hex[2 * b]), lo = rawHexNibble(hex[2 * b + 1]);
      if (hi < 0 || lo < 0) return -1;
      rec[b] = (uint8_t)((hi << 4) | lo);
    }
    hex += RAW_RECORD_BYTES * 2;
    if (k > 0) {
      seq += rec[0];
      t += (int64_t)((rec[1] << 8) | rec[2]);
    }
    out->s[k].seq = seq;
    out->s[k].t_us = t;
    out->s[k].flags = rec[3];
    for (int a = 0; a < 6; a++) out->s[k].v[a] = (int16_t)(uint16_t)((rec[4 + 2 * a] << 8) | rec[5 + 2 * a]);
  }
  return 1;
}
