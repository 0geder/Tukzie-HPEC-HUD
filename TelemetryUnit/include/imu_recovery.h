// Automatic IMU recovery decisions (firmware v0.7.7).
//
// Pure C++ with no Arduino or FreeRTOS dependency, so the same code is
// compiled into the firmware and into the host-side test
// (TelemetryUnit/test_host/test_imu_recovery.cpp).
//
// Why (bench, 22 Oct 2026, v0.7.6): an MPU6050's wires were pulled and
// refitted while running. v0.7.6 counted the read failures (rdfail) and the
// skipped slots (late) without stalling, but after the refit the sensor was
// back in its power-on sleep state and returned the same reading every time
// (stuck rising 200 per second, vib 0.0) until the board was reset, because
// the firmware configured each sensor only once, at boot.
//
// This file only decides; the IMU task does the I2C work. Time is counted in
// IMU slots (one per 5 ms period, the same slot number as the raw stream's
// seq), so the thresholds are times, whatever the read time or the slots the
// pacer gave up.
//
// Rules:
//  - A read is good (ok and not stuck), failed (no I2C reply) or stuck (all
//    six values equal to the previous good read).
//  - A bad run starts at the first failed or stuck read after a good one.
//    Once it is failSlots long and the latest read failed, or stuckSlots long
//    and the latest read was stuck, the sensor is due for a re-init (wake it
//    and write its settings again). A run that mixes failed and stuck reads
//    still counts as one run, so a flaky wire cannot hold it off.
//  - The first re-init of a bad run is tried at once. Further tries (the
//    re-init failed, or it worked but the readings stayed bad) wait
//    retrySlots(): fastRetrySlots for the first fastTries tries, then
//    slowRetrySlots. One good read clears the count.
//  - A failed re-init marks the sensor down: it is not read, only re-tried on
//    that schedule. A sensor absent at boot starts down, with the boot attempt
//    counted as the first try, so it is picked up when plugged in later.
//  - busResetEvery: every that many failed tries in a row, the caller may
//    restart the I2C driver (Wire end and begin) before the try, in case a
//    cut wire left the bus hung. The firmware does it only if a transaction
//    on that bus timed out since the last good read. 0 = never.
#pragma once
#include <stdint.h>

struct ImuRecoveryConfig {
  uint32_t failSlots;       // bad run that ends in a failed read, slots
  uint32_t stuckSlots;      // bad run that ends in a stuck read, slots
  uint32_t fastRetrySlots;  // wait between tries, first fastTries tries
  uint32_t fastTries;
  uint32_t slowRetrySlots;  // wait between tries after that
  uint32_t busResetEvery;   // restart the bus driver every this many failed tries (0 = never)
};

enum ImuReadKind { IMU_READ_GOOD = 0, IMU_READ_FAIL = 1, IMU_READ_STUCK = 2 };

struct ImuRecovery {
  bool up;                // configured and read every slot; false = down (absent or re-init failed)
  bool inBadRun;
  uint32_t badStartSlot;  // slot of the first bad read of the current run
  uint32_t lastTrySlot;   // slot of the last re-init try
  uint32_t triesSinceGood;  // re-init tries since the last good read (drives the back-off)
  uint32_t failedInRow;     // failed tries in a row (drives the bus restart)
  uint32_t reinits;         // re-inits that worked (DASH "reinit")
  uint32_t tries;           // every try, worked or not
  bool flagNext;            // mark the next sample sent (raw stream flag bit 2), set by a re-init that worked
};

static inline ImuReadKind imuReadKind(bool ok, bool stuck) {
  if (!ok) return IMU_READ_FAIL;
  return stuck ? IMU_READ_STUCK : IMU_READ_GOOD;
}

// Start-up state. upAtBoot: the boot-time configuration worked. A sensor
// absent at boot starts down, with the boot attempt counted as the first try,
// so its next try is fastRetrySlots after slot.
static inline void imuRecInit(ImuRecovery& r, bool upAtBoot, uint32_t slot) {
  r.up = upAtBoot;
  r.inBadRun = false;
  r.badStartSlot = 0;
  r.lastTrySlot = slot;
  r.triesSinceGood = upAtBoot ? 0 : 1;
  r.failedInRow = upAtBoot ? 0 : 1;
  r.reinits = 0;
  r.tries = 0;
  r.flagNext = false;
}

// Wait before the next try, in slots, after `tries` tries since the last good read.
static inline uint32_t imuRecRetrySlots(const ImuRecoveryConfig& c, uint32_t tries) {
  if (tries == 0) return 0;
  return tries <= c.fastTries ? c.fastRetrySlots : c.slowRetrySlots;
}

// True if a try is allowed at this slot by the back-off. Slot arithmetic is
// unsigned, so it is correct across the 32-bit wrap.
static inline bool imuRecTryAllowed(const ImuRecovery& r, const ImuRecoveryConfig& c, uint32_t slot) {
  if (r.triesSinceGood == 0) return true;
  return (uint32_t)(slot - r.lastTrySlot) >= imuRecRetrySlots(c, r.triesSinceGood);
}

// For a sensor that is down: true when its next try is due.
static inline bool imuRecDueWhileDown(const ImuRecovery& r, const ImuRecoveryConfig& c, uint32_t slot) {
  return !r.up && imuRecTryAllowed(r, c, slot);
}

// For a sensor that is up: records one read at this slot. Returns true when
// the caller should try a re-init now.
static inline bool imuRecNoteRead(ImuRecovery& r, const ImuRecoveryConfig& c, uint32_t slot, ImuReadKind kind) {
  if (kind == IMU_READ_GOOD) {
    r.inBadRun = false;
    r.triesSinceGood = 0;
    r.failedInRow = 0;
    return false;
  }
  if (!r.inBadRun) {
    r.inBadRun = true;
    r.badStartSlot = slot;
  }
  const uint32_t runSlots = slot - r.badStartSlot + 1;
  const uint32_t limit = (kind == IMU_READ_FAIL) ? c.failSlots : c.stuckSlots;
  if (limit == 0 || runSlots < limit) return false;
  return imuRecTryAllowed(r, c, slot);
}

// True if the caller should restart the I2C driver before this try.
static inline bool imuRecWantBusReset(const ImuRecovery& r, const ImuRecoveryConfig& c) {
  return c.busResetEvery > 0 && r.failedInRow > 0 && (r.failedInRow % c.busResetEvery) == 0;
}

// Records the result of a re-init try made at this slot.
static inline void imuRecAfterTry(ImuRecovery& r, uint32_t slot, bool worked) {
  r.tries++;
  r.lastTrySlot = slot;
  r.triesSinceGood++;
  r.inBadRun = false;  // a new run starts from here
  if (worked) {
    r.up = true;
    r.reinits++;
    r.failedInRow = 0;
    r.flagNext = true;
  } else {
    r.up = false;
    r.failedInRow++;
  }
}
