// Host-side test of the IMU pacing and consumer-health helpers
// (TelemetryUnit/include/imu_pacing.h, firmware v0.7.6). No ESP32 needed.
//
// Build and run on the laptop, from TelemetryUnit/:
//   g++ -std=c++11 -O1 -Wall -Iinclude test_host/test_imu_pacing.cpp -o test_host/test_imu_pacing
// Or: python test_host/run.py
//
// Part 1: single cases of imuPacerSkip() (on time, short stall, long stall,
// tick wrap, phase kept). Part 2: a tick-level model of the IMU task loop
// (vTaskDelayUntil semantics as in FreeRTOS: the next wake is lastWake +
// period, and the call returns at once when that is already past). It checks
// that an iteration slower than the period never sleeps without the skip
// (the starvation of 21 and 22 Oct 2026), sleeps regularly with it, keeps
// the lag bounded, and that slot numbers still account for every period.
// Part 3: consumerAgeMs() and noteHighWater().
#include <stdio.h>

#include "imu_pacing.h"

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

static const uint32_t P = 5;     // IMU_SAMPLE_PERIOD_TICKS at 1 kHz
static const uint32_t MAXLAG = 20;  // IMU_MAX_LAG_PERIODS

static void testSingleCases() {
  uint32_t lw = 1000;
  // On time and up to MAXLAG periods late: nothing changes.
  for (uint32_t late = 0; late <= MAXLAG * P + P - 1; late++) {
    lw = 1000;
    CHECK(imuPacerSkip(&lw, 1000 + late, P, MAXLAG) == 0);
    CHECK(lw == 1000);
  }
  // A 40 ms flash pause (8 periods): caught up as before, no skip.
  lw = 1000;
  CHECK(imuPacerSkip(&lw, 1040, P, MAXLAG) == 0);
  // 21 whole periods late: all 21 given up, the next wake (lw + P) is in the future, phase kept.
  lw = 1000;
  CHECK(imuPacerSkip(&lw, 1000 + 21 * P + 3, P, MAXLAG) == 21);
  CHECK(lw == 1000 + 21 * P);
  CHECK(lw % P == 1000 % P);
  CHECK(lw + P > 1000 + 21 * P + 3);
  // Far behind (30 s).
  lw = 1000;
  CHECK(imuPacerSkip(&lw, 1000 + 30000, P, MAXLAG) == 6000);
  CHECK(lw == 31000);
  // Across the 32-bit tick wrap.
  lw = 0xFFFFFFF0u;
  CHECK(imuPacerSkip(&lw, 0xFFFFFFF0u + 4, P, MAXLAG) == 0);
  lw = 0xFFFFFFF0u;
  const uint32_t now = 0xFFFFFFF0u + 200;  // wrapped
  CHECK(now < 0xFFFFFFF0u);
  CHECK(imuPacerSkip(&lw, now, P, MAXLAG) == 40);
  CHECK(lw == 0xFFFFFFF0u + 200);
  // A wake time in the future is not "late".
  lw = 2000;
  CHECK(imuPacerSkip(&lw, 1990, P, MAXLAG) == 0);
  CHECK(lw == 2000);
  // Zero period guard.
  lw = 5;
  CHECK(imuPacerSkip(&lw, 500, 0, MAXLAG) == 0);
}

// Tick-level model of one IMU task. iterTicks: time from wake to the end of
// one sample (bus read and sends). stallAt/stallLen: one stall (e.g. flash
// write) during which the task cannot run. Returns via out-params the number
// of samples taken, the number of loop passes that slept in vTaskDelayUntil,
// the final slot number, the skipped count and the worst lag seen.
struct ModelResult {
  uint32_t samples, sleeps, seq, skipped, maxLagTicks, lastSleepGap;
};

static ModelResult runModel(bool withSkip, uint32_t iterTicks, uint32_t totalTicks, uint32_t startTick,
                            uint32_t stallAt = 0, uint32_t stallLen = 0) {
  ModelResult r = {0, 0, 0, 0, 0, 0};
  uint32_t t = startTick;  // current tick
  uint32_t lastWake = startTick;
  uint32_t lastSleepAt = startTick;
  const uint32_t end = startTick + totalTicks;
  while ((int32_t)(end - t) > 0) {
    if (stallLen > 0 && t - startTick >= stallAt && t - startTick < stallAt + stallLen) {
      t = startTick + stallAt + stallLen;  // task frozen
      continue;
    }
    const uint32_t lag = t - lastWake;
    if (lag > r.maxLagTicks) r.maxLagTicks = lag;
    t += iterTicks;  // read and send
    r.samples++;
    r.seq++;
    if (withSkip) {  // as ImuTask: just before vTaskDelayUntil
      const uint32_t s = imuPacerSkip(&lastWake, t, P, MAXLAG);
      r.seq += s;
      r.skipped += s;
    }
    // vTaskDelayUntil(&lastWake, P)
    const uint32_t wake = lastWake + P;
    lastWake = wake;
    if ((int32_t)(wake - t) > 0) {
      r.sleeps++;
      const uint32_t gap = t - lastSleepAt;
      if (gap > r.lastSleepGap) r.lastSleepGap = gap;
      t = wake;
      lastSleepAt = t;
    }
  }
  return r;
}

static void testModel() {
  const uint32_t T = 60000;  // 60 s
  // Normal: 1 tick per sample, 200 Hz, sleeps every period, no skips.
  for (int skip = 0; skip < 2; skip++) {
    ModelResult r = runModel(skip == 1, 1, T, 12345);
    CHECK(r.samples == T / P);
    CHECK(r.sleeps == r.samples);
    CHECK(r.skipped == 0);
    CHECK(r.seq == T / P);
  }
  // A 40 ms stall is caught up identically with and without the skip.
  {
    ModelResult a = runModel(false, 1, T, 0, 10000, 40);
    ModelResult b = runModel(true, 1, T, 0, 10000, 40);
    CHECK(a.samples == b.samples);
    CHECK(a.seq == b.seq);
    CHECK(b.skipped == 0);
    CHECK(a.samples == T / P);  // every slot still sampled (catch-up burst)
  }
  // Slower than the period (6 ticks per sample, like IMU1 at 168 Hz):
  // without the skip the task never sleeps after the first pass, so nothing
  // below it on the core runs; with it, it sleeps and the lag is bounded.
  {
    ModelResult a = runModel(false, 6, T, 777);
    CHECK(a.sleeps <= 1);
    CHECK(a.maxLagTicks > 9000);  // falls ever further behind
    ModelResult b = runModel(true, 6, T, 777);
    // One sleep each time the lag passes 20 periods: about every 105 samples
    // (630 ms) at 1 tick of extra lag per sample, so about 95 in 60 s.
    CHECK(b.sleeps > 80);
    CHECK(b.maxLagTicks <= (MAXLAG + 1) * P + 6);
    CHECK(b.lastSleepGap <= (MAXLAG + 2) * P * 6 + 50);
    // Slot accounting: samples + skipped = slot number, and the slot number
    // tracks elapsed periods to within the bounded lag.
    CHECK(b.seq == b.samples + b.skipped);
    CHECK(b.seq * P + (MAXLAG + 2) * P >= T);
    CHECK(b.seq * P <= T + P * 2);
    CHECK(b.samples > T / 6 - 2000);  // the skip costs few samples overall
  }
  // Much slower (22 ticks, like IMU2 at 46 Hz), and across the tick wrap.
  {
    ModelResult b = runModel(true, 22, T, 0xFFFFFFFFu - 30000);
    CHECK(b.sleeps > 400);  // lag passes 20 periods about every 6 samples
    CHECK(b.seq == b.samples + b.skipped);
    CHECK(b.maxLagTicks <= (MAXLAG + 1) * P + 22);
  }
}

static void testHealthHelpers() {
  CHECK(consumerAgeMs(5000000, 0) == -1);
  CHECK(consumerAgeMs(5000000, 4990000) == 10);
  CHECK(consumerAgeMs(5000000, 5000500) == 0);  // beat written just after now was read
  CHECK(consumerAgeMs(5000000000LL, 1) == 999999);
  volatile uint32_t hw = 0;
  noteHighWater(&hw, 3);
  noteHighWater(&hw, 1);
  CHECK(hw == 3);
  noteHighWater(&hw, 100);
  CHECK(hw == 100);
}

int main() {
  testSingleCases();
  testModel();
  testHealthHelpers();
  printf("%d checks, %d failures\n", checks, failures);
  return failures == 0 ? 0 : 1;
}
