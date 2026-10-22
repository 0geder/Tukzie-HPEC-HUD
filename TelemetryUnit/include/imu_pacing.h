// IMU task pacing and consumer-health helpers (firmware v0.7.6).
//
// Pure C++ with no Arduino or FreeRTOS dependency, so the same code is
// compiled into the firmware and into the host-side test
// (TelemetryUnit/test_host/test_imu_pacing.cpp).
//
// Why (fault of 21 and 22 Oct 2026, rear unit on v0.7.4.1): the IMU drop
// counters rose at about 168/s and 46/s while imu_hz stayed at 200 and vib
// went null. imu_hz is written only by StatsTask at the end of a 2 s report,
// so a frozen 200 means StatsTask had stopped completing reports; vib null
// means both ride tasks had stopped too. With the consumers stopped, every
// sample sent is dropped, so the drop rates are the producers' own rates:
// both IMU tasks had fallen below 200 Hz. All three consumers sat on core 1
// below the IMU tasks (priority 2 and 1 under 3), and an IMU task that is
// behind its vTaskDelayUntil schedule never sleeps in vTaskDelayUntil (it
// returns at once until the schedule is caught up), so two IMU tasks that
// cannot keep up hold core 1 between them whenever they are not waiting on
// the bus, and nothing below them runs.
//
// imuPacerSkip() bounds that: once a task is more than maxLagPeriods behind,
// it gives up the missed slots instead of trying to run them all back to
// back. lastWake is moved forward by whole periods (the 5 ms grid keeps its
// phase), the caller advances its slot number by the same count (so the gap
// shows in the raw stream as missing seq numbers, like a failed read) and
// counts it ("late" in DASH). After a skip the next slot is in the future,
// so the task sleeps in vTaskDelayUntil at least once every maxLagPeriods
// or so, whatever its read time. Below the limit nothing changes:
// a short stall (a flash write pauses both cores for 33 to 40 ms) is still
// caught up exactly as before.
#pragma once
#include <stdint.h>

// Called after a sample, just before vTaskDelayUntil(&lastWake, period).
// lastWake: the nominal tick of the slot just sampled (as vTaskDelayUntil left
// it). now: the current tick. When more than maxLagPeriods behind, lastWake
// moves to the last slot boundary at or before now, so the coming
// vTaskDelayUntil sleeps until the next boundary; the slots in between are
// given up. Tick arithmetic is unsigned, so it is correct across the 32-bit
// tick wrap. Returns the number of slots given up (0 when the task is at most
// maxLagPeriods behind); the caller adds it to its slot number.
static inline uint32_t imuPacerSkip(uint32_t* lastWake, uint32_t now, uint32_t period,
                                    uint32_t maxLagPeriods) {
  if (period == 0) return 0;
  const uint32_t late = now - *lastWake;  // ticks behind the slot's nominal time
  // A wake time in the future (should not happen) shows up as a huge unsigned
  // lag; treat anything past half the tick range as "not late".
  if (late >= 0x80000000u) return 0;
  const uint32_t behind = late / period;  // whole periods behind
  if (behind <= maxLagPeriods) return 0;
  *lastWake += behind * period;
  return behind;
}

// Age in ms of a consumer heartbeat (esp_timer microseconds), for DASH.
// -1 when the consumer has never run; capped at 999999 so the field width
// is bounded (the DASH line has a fixed maximum length).
static inline int32_t consumerAgeMs(int64_t nowUs, int64_t beatUs) {
  if (beatUs <= 0) return -1;
  int64_t ms = (nowUs - beatUs) / 1000;
  if (ms < 0) ms = 0;
  if (ms > 999999) ms = 999999;
  return (int32_t)ms;
}

// High-water mark of a queue's fill level.
static inline void noteHighWater(volatile uint32_t* hw, uint32_t fill) {
  if (fill > *hw) *hw = fill;
}
