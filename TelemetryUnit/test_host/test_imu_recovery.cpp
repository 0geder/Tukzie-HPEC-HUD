// Host-side test of the IMU recovery decisions
// (TelemetryUnit/include/imu_recovery.h, firmware v0.7.7). No ESP32 needed.
//
// Build and run on the laptop, from TelemetryUnit/:
//   g++ -std=c++11 -O1 -Wall -Iinclude test_host/test_imu_recovery.cpp -o test_host/test_imu_recovery
// Or: python test_host/run.py
//
// Part 1: single cases (read kinds, back-off schedule, thresholds, slot wrap,
// bus restart cadence). Part 2: a slot-level model of the IMU task (the same
// calls in the same order as ImuTask in src/main.cpp) driving a simulated
// MPU6050 that can lose its power or its SDA wire. A sensor that loses power
// comes back asleep and returns the same reading every time, as on the bench
// on 22 Oct 2026. Each scenario checks how long the sensor stays stuck or
// missing after the refit, the recovery count and how many I2C tries were
// spent while it was missing.
#include <stdio.h>

#include "imu_recovery.h"
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

// The firmware defaults (src/main.cpp IMU_REINIT_*): 1 s of bad reads, retry
// every 1 s for 10 tries, then every 5 s, bus restart every 3rd failed try.
static const ImuRecoveryConfig DEF = {200, 200, 200, 10, 1000, 3};

// ---------------------------------------------------------------------------
// Part 1: single cases
// ---------------------------------------------------------------------------
static void testSingleCases() {
  CHECK(imuReadKind(true, false) == IMU_READ_GOOD);
  CHECK(imuReadKind(true, true) == IMU_READ_STUCK);
  CHECK(imuReadKind(false, false) == IMU_READ_FAIL);
  CHECK(imuReadKind(false, true) == IMU_READ_FAIL);

  // Back-off schedule.
  CHECK(imuRecRetrySlots(DEF, 0) == 0);
  for (uint32_t t = 1; t <= 10; t++) CHECK(imuRecRetrySlots(DEF, t) == 200);
  for (uint32_t t = 11; t <= 1000; t += 7) CHECK(imuRecRetrySlots(DEF, t) == 1000);

  // Start-up state.
  ImuRecovery r;
  imuRecInit(r, true, 0);
  CHECK(r.up && r.triesSinceGood == 0 && r.reinits == 0 && r.tries == 0 && !r.flagNext);
  imuRecInit(r, false, 50);
  CHECK(!r.up && r.triesSinceGood == 1 && r.lastTrySlot == 50);
  CHECK(!imuRecDueWhileDown(r, DEF, 50));
  CHECK(!imuRecDueWhileDown(r, DEF, 249));
  CHECK(imuRecDueWhileDown(r, DEF, 250));

  // Failed reads: due at exactly failSlots consecutive slots, not before.
  imuRecInit(r, true, 0);
  for (uint32_t s = 100; s < 100 + 199; s++) CHECK(!imuRecNoteRead(r, DEF, s, IMU_READ_FAIL));
  CHECK(imuRecNoteRead(r, DEF, 299, IMU_READ_FAIL));
  // A good read anywhere in the run starts it again.
  imuRecInit(r, true, 0);
  for (uint32_t s = 0; s < 150; s++) CHECK(!imuRecNoteRead(r, DEF, s, IMU_READ_STUCK));
  CHECK(!imuRecNoteRead(r, DEF, 150, IMU_READ_GOOD));
  for (uint32_t s = 151; s < 350; s++) CHECK(!imuRecNoteRead(r, DEF, s, IMU_READ_STUCK));
  CHECK(imuRecNoteRead(r, DEF, 350, IMU_READ_STUCK));

  // Stuck threshold and fail threshold set separately (build flags).
  const ImuRecoveryConfig c2 = {50, 400, 200, 10, 1000, 0};
  imuRecInit(r, true, 0);
  for (uint32_t s = 0; s < 49; s++) CHECK(!imuRecNoteRead(r, c2, s, IMU_READ_FAIL));
  CHECK(imuRecNoteRead(r, c2, 49, IMU_READ_FAIL));
  imuRecInit(r, true, 0);
  for (uint32_t s = 0; s < 399; s++) CHECK(!imuRecNoteRead(r, c2, s, IMU_READ_STUCK));
  CHECK(imuRecNoteRead(r, c2, 399, IMU_READ_STUCK));
  // Threshold 0 switches that trigger off.
  const ImuRecoveryConfig c3 = {0, 0, 200, 10, 1000, 0};
  imuRecInit(r, true, 0);
  bool any = false;
  for (uint32_t s = 0; s < 5000; s++) any = any || imuRecNoteRead(r, c3, s, (s & 1) ? IMU_READ_FAIL : IMU_READ_STUCK);
  CHECK(!any);

  // A run that alternates failed and stuck reads is still one run.
  imuRecInit(r, true, 0);
  uint32_t firstDue = 0;
  for (uint32_t s = 0; s < 1000 && firstDue == 0; s++) {
    if (imuRecNoteRead(r, DEF, s, (s & 1) ? IMU_READ_FAIL : IMU_READ_STUCK)) firstDue = s;
  }
  CHECK(firstDue == 199);

  // Slot numbers across the 32-bit wrap.
  imuRecInit(r, true, 0);
  const uint32_t w0 = 0xFFFFFFFFu - 99;  // run starts 100 slots before the wrap
  uint32_t dueAt = 0;
  bool due = false;
  for (uint32_t k = 0; k < 300 && !due; k++) {
    if (imuRecNoteRead(r, DEF, w0 + k, IMU_READ_FAIL)) {
      due = true;
      dueAt = k;
    }
  }
  CHECK(due && dueAt == 199);
  imuRecAfterTry(r, w0 + dueAt, false);
  CHECK(!imuRecDueWhileDown(r, DEF, w0 + dueAt + 199));
  CHECK(imuRecDueWhileDown(r, DEF, w0 + dueAt + 200));

  // After a try: worked sets up, counts and flags; failed sets down.
  imuRecInit(r, true, 0);
  imuRecAfterTry(r, 10, false);
  CHECK(!r.up && r.tries == 1 && r.reinits == 0 && r.failedInRow == 1 && !r.flagNext);
  imuRecAfterTry(r, 210, true);
  CHECK(r.up && r.tries == 2 && r.reinits == 1 && r.failedInRow == 0 && r.flagNext);
  CHECK(r.triesSinceGood == 2);  // still backing off until a good read
  imuRecNoteRead(r, DEF, 211, IMU_READ_GOOD);
  CHECK(r.triesSinceGood == 0);

  // Bus restart before every 3rd failed try in a row, never with busResetEvery 0.
  imuRecInit(r, true, 0);
  int resets = 0;
  for (int k = 0; k < 12; k++) {
    if (imuRecWantBusReset(r, DEF)) resets++;
    imuRecAfterTry(r, (uint32_t)k * 200, false);
  }
  CHECK(resets == 3);  // before tries 4, 7 and 10 (3, 6, 9 failed before them)
  CHECK(!imuRecWantBusReset(r, c2));

  // The raw stream carries the re-init flag (bit 2) through encode and decode.
  RawSample s[2] = {};
  s[0].seq = 7;
  s[0].t_us = 1000;
  s[1].seq = 400;  // the gap while the sensor was down: a new line in practice
  s[1].t_us = 2000;
  s[1].flags = RAW_FLAG_REINIT | RAW_FLAG_STUCK;
  char line[RAW_LINE_MAX];
  RawDecoded d;
  CHECK(rawEncodeLine(line, sizeof(line), "rear", 1, &s[1], 1) > 0);
  CHECK(rawDecodeLine(line, &d) == 1 && d.n == 1 && d.s[0].flags == (RAW_FLAG_REINIT | RAW_FLAG_STUCK));
  s[1].flags = 0xF8;  // undefined bits are still not sent
  CHECK(rawEncodeLine(line, sizeof(line), "rear", 1, &s[1], 1) > 0);
  CHECK(rawDecodeLine(line, &d) == 1 && d.s[0].flags == 0);
}

// ---------------------------------------------------------------------------
// Part 2: slot-level model of the IMU task with a simulated MPU6050
// ---------------------------------------------------------------------------
struct SimSensor {
  bool power;
  bool sda;
  bool asleep;       // power-on state: output registers do not update
  bool broken;       // answers and accepts the settings but never updates (worst case)
  bool configured;   // settings written since power-up
  uint32_t n;        // sample counter for the noise
  int16_t frozen[6];

  void init(bool present) {
    power = present;
    sda = true;
    asleep = !present;
    broken = false;
    configured = present;
    n = 0;
    for (int a = 0; a < 6; a++) frozen[a] = (int16_t)(100 * a - 7);
  }
  void setPower(bool on) {
    if (on && !power) {
      asleep = true;
      configured = false;
    }
    power = on;
  }
  bool read(int16_t v[6]) {
    if (!power || !sda) return false;
    if (asleep || broken) {
      for (int a = 0; a < 6; a++) v[a] = frozen[a];
      return true;
    }
    n++;
    for (int a = 0; a < 6; a++) v[a] = (int16_t)(((n * 2654435761u) >> (a * 3 + 4)) & 0x3F) - 32 + 4096 * (a == 2);
    return true;
  }
  bool reinit() {
    if (!power || !sda) return false;
    asleep = false;
    configured = true;
    return true;
  }
};

struct Run {
  uint32_t reads, sent, failedReads, stuckReads, triesFailed, busResets, flagged;
  uint32_t lastBadSlot;   // last slot with no good sample (missing, failed or stuck)
  int firstFlagSlot;
};

// One slot of ImuTask (src/main.cpp), same order of calls.
static void slotStep(ImuRecovery& rec, const ImuRecoveryConfig& c, ImuHealth& health, SimSensor& sen,
                     uint32_t slot, Run& out) {
  bool good = false;
  if (imuRecDueWhileDown(rec, c, slot)) {
    if (imuRecWantBusReset(rec, c)) out.busResets++;
    const bool worked = sen.reinit();
    imuRecAfterTry(rec, slot, worked);
    if (!worked) out.triesFailed++;
  } else if (rec.up) {
    int16_t v[6] = {0, 0, 0, 0, 0, 0};
    const bool ok = sen.read(v);
    out.reads++;
    const bool stuck = imuHealthNote(health, ok, v);
    if (!ok) out.failedReads++;
    if (stuck) out.stuckReads++;
    if (ok) {
      out.sent++;
      if (rec.flagNext) {
        rec.flagNext = false;
        out.flagged++;
        if (out.firstFlagSlot < 0) out.firstFlagSlot = (int)slot;
      }
      good = !stuck;
    }
    if (imuRecNoteRead(rec, c, slot, imuReadKind(ok, stuck))) {
      if (imuRecWantBusReset(rec, c)) out.busResets++;
      const bool worked = sen.reinit();
      imuRecAfterTry(rec, slot, worked);
      if (!worked) out.triesFailed++;
    }
  }
  if (!good) out.lastBadSlot = slot;
}

struct Event {
  uint32_t slot;
  int what;  // 0 power off, 1 power on, 2 sda off, 3 sda on, 4 broken on
};

static Run simulate(bool presentAtBoot, const Event* ev, int nev, uint32_t slots, const ImuRecoveryConfig& c,
                    ImuRecovery& rec, uint32_t slot0 = 0) {
  SimSensor sen;
  sen.init(presentAtBoot);
  ImuHealth health = {};
  imuRecInit(rec, presentAtBoot, slot0);
  Run out = {};
  out.firstFlagSlot = -1;
  int e = 0;
  for (uint32_t k = 0; k < slots; k++) {
    while (e < nev && ev[e].slot == k) {
      switch (ev[e].what) {
        case 0: sen.setPower(false); break;
        case 1: sen.setPower(true); break;
        case 2: sen.sda = false; break;
        case 3: sen.sda = true; break;
        case 4: sen.broken = true; break;
      }
      e++;
    }
    slotStep(rec, c, health, sen, slot0 + k, out);
  }
  return out;
}

static void testScenarios() {
  ImuRecovery rec;

  // 1. Healthy sensor for 10 minutes: never re-initialised, nothing lost.
  {
    Run r = simulate(true, nullptr, 0, 120000, DEF, rec);
    CHECK(rec.reinits == 0 && rec.tries == 0 && r.failedReads == 0 && r.stuckReads == 0);
    CHECK(r.sent == 120000 && rec.up);
  }

  // 2. Power wire pulled for 3 s, refitted (the 22 Oct bench case, long pull).
  //    Down after 1 s, tried every 1 s, back within 1 s of the refit.
  {
    const uint32_t off = 2000, on = 2600;
    Event ev[] = {{off, 0}, {on, 1}};
    Run r = simulate(true, ev, 2, 6000, DEF, rec);
    CHECK(rec.reinits == 1 && rec.up);
    CHECK(r.lastBadSlot >= on && r.lastBadSlot - on <= 200);  // within 1 s of the refit
    printf("power pull 3 s: good again %u slots after the refit, %u tries (%u failed), reinit %u\n",
           (unsigned)(r.lastBadSlot - on + 1), (unsigned)rec.tries, (unsigned)r.triesFailed, (unsigned)rec.reinits);
    CHECK(r.failedReads == 200);  // read only until the first try; then down, not read
    CHECK(r.firstFlagSlot > (int)on && r.flagged == 1);
  }

  // 3. Short power glitch (0.3 s): the sensor comes back asleep, stuck. Its
  //    first reading differs from the last one before the pull, so the stuck
  //    run starts at the refit and the re-init comes 1 s after it.
  {
    const uint32_t off = 2000, on = 2060;
    Event ev[] = {{off, 0}, {on, 1}};
    Run r = simulate(true, ev, 2, 6000, DEF, rec);
    CHECK(rec.reinits == 1 && rec.tries == 1);
    CHECK(r.lastBadSlot - on <= 300);  // the bench pass: stuck stops within 1.5 s of the refit
    printf("power glitch 0.3 s: good again %u slots after the refit, stuck reads %u\n",
           (unsigned)(r.lastBadSlot - on + 1), (unsigned)r.stuckReads);
    CHECK(r.stuckReads > 0 && r.stuckReads <= 200);
  }

  // 4. Glitch of a few slots: the stuck run alone is 1 s long.
  {
    const uint32_t off = 2000, on = 2003;
    Event ev[] = {{off, 0}, {on, 1}};
    Run r = simulate(true, ev, 2, 6000, DEF, rec);
    CHECK(rec.reinits == 1 && r.lastBadSlot - on <= 300);
  }

  // 5. SDA pulled for 3 s with the sensor still powered: same recovery.
  {
    const uint32_t off = 3000, on = 3600;
    Event ev[] = {{off, 2}, {on, 3}};
    Run r = simulate(true, ev, 2, 6000, DEF, rec);
    CHECK(rec.reinits == 1 && r.lastBadSlot - on <= 200 && r.stuckReads == 0);
  }

  // 6. SDA pulled for 0.5 s: reads resume by themselves, no re-init needed.
  {
    const uint32_t off = 3000, on = 3100;
    Event ev[] = {{off, 2}, {on, 3}};
    Run r = simulate(true, ev, 2, 6000, DEF, rec);
    CHECK(rec.reinits == 0 && rec.tries == 0 && r.failedReads == 100 && r.lastBadSlot == on - 1);
  }

  // 7. Absent at boot, plugged in at 7 s: found within 1 s.
  {
    Event ev[] = {{1400, 1}};
    Run r = simulate(false, ev, 1, 4000, DEF, rec);
    CHECK(rec.reinits == 1 && rec.up && r.lastBadSlot - 1400 <= 200);
    CHECK(r.reads > 0 && r.sent == r.reads);
  }

  // 8. Missing for 10 min: 10 tries 1 s apart, then one every 5 s; found
  //    within 5 s of plugging in; bus restarted before every 3rd failed try.
  {
    const uint32_t plug = 120000;
    Event ev[] = {{plug, 1}};
    Run r = simulate(false, ev, 1, plug + 2000, DEF, rec);
    CHECK(rec.reinits == 1 && r.lastBadSlot - plug <= 1000);
    // Boot counts as try 1; the waits after tries 1 to 10 are 1 s (tries at
    // slots 200 to 2000), then 5 s (slots 3000, 4000, ...).
    const uint32_t expected = 10 + (plug - 1 - 2000) / 1000;
    printf("missing 10 min: %u failed tries (%.2f per s), %u bus restarts, found %u slots after plugging in\n",
           (unsigned)r.triesFailed, r.triesFailed / 600.0, (unsigned)r.busResets, (unsigned)(r.lastBadSlot - plug + 1));
    CHECK(r.triesFailed == expected);
    CHECK(r.busResets == (r.triesFailed + 1) / 3);  // 3, 6, 9, ... failed in a row before a try
    CHECK(r.reads == r.sent);  // never read while down
  }

  // 9. A broken sensor that accepts the settings but never updates: each
  //    re-init "works" and the data stays stuck. The tries are spaced by the
  //    back-off, so the bus load stays bounded (no tight re-init loop).
  {
    Event ev[] = {{1000, 4}};
    Run r = simulate(true, ev, 1, 1000 + 120000, DEF, rec);
    printf("broken sensor 10 min: %u re-inits\n", (unsigned)rec.reinits);
    CHECK(rec.reinits >= 100 && rec.reinits <= 140);  // 10 at about 1 s, then about one per 5 s
    CHECK(rec.tries == rec.reinits);
    (void)r;
  }

  // 10. Repeated pulls: one recovery each.
  {
    Event ev[] = {{1000, 0}, {1500, 1}, {5000, 2}, {5800, 3}, {9000, 0}, {9010, 1}};
    Run r = simulate(true, ev, 6, 14000, DEF, rec);
    CHECK(rec.reinits == 3 && rec.up && r.lastBadSlot < 9010 + 300);
  }

  // 11. Across the slot-number wrap.
  {
    const uint32_t s0 = 0xFFFFFFFFu - 2500;
    Event ev[] = {{2000, 0}, {2600, 1}};
    Run r = simulate(true, ev, 2, 6000, DEF, rec, s0);
    CHECK(rec.reinits == 1 && (uint32_t)(r.lastBadSlot - (s0 + 2600)) <= 200);
  }

  // 12. Faster thresholds by build flag: 50-slot fail limit, quicker recovery.
  {
    const ImuRecoveryConfig fast = {50, 100, 100, 5, 500, 3};
    const uint32_t off = 2000, on = 2300;
    Event ev[] = {{off, 0}, {on, 1}};
    Run r = simulate(true, ev, 2, 6000, fast, rec);
    CHECK(rec.reinits == 1 && r.lastBadSlot - on <= 100);
  }
}

int main() {
  testSingleCases();
  testScenarios();
  printf("%d checks, %d failures\n", checks, failures);
  return failures ? 1 : 0;
}
