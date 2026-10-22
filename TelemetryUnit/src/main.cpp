#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Arduino.h>
#include <Wire.h>
#include <esp_timer.h>
#include <math.h>
#include <Preferences.h>

// ---- Which node this build is (v0.7.5) ----
// NODE_FRONT 0: the rear unit (Makerfabs A7670X board): two IMUs, modem,
// GNSS, MQTT, BLE BMS, flash log, Hall counter. This is the default
// environment in platformio.ini.
// NODE_FRONT 1: the front IMU node (env:front_node): the same source built
// for a plain ESP32-S3 dev board with one IMU and nothing else: no modem,
// no BLE, no GNSS, no MQTT, no flash log. It sends the DASH line (fewer
// fields) and the raw stream on USB serial, and on a UART if enabled.
#ifndef NODE_FRONT
#define NODE_FRONT 0
#endif

#if !NODE_FRONT
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <LittleFS.h>

#include "payload_privacy.h"
#include "sync_ledger.h"
#endif

#include "raw_stream.h"

#define FIRMWARE_VERSION "v0.7.5"

#if NODE_FRONT
#define NODE_ID "front"
#else
#define NODE_ID "rear"
#endif

// ============================================================
// SW-7 ESP32-S3 Firmware (version: FIRMWARE_VERSION above)
// Dual-IMU deterministic acquisition + A7670X modem/GNSS + Pi sync pulse
// ============================================================

// ---- Makerfabs ESP32-S3 to A7670X UART and control pins (verified) ----
#define A7670X_RX_PIN 47
#define A7670X_TX_PIN 48
#define A7670X_PWRKEY_PIN 4
#define A7670X_RESET_PIN 5
#define MODEM_BAUD 115200

// ---- IMU 1: existing wiring, confirmed working on v0.3.0 ----
// The pins can be set from platformio.ini (-D IMU1_SDA_PIN=..), for the
// front node's board. 8 and 9 are also the default I2C pins of a generic
// ESP32-S3 dev board (ESP32-S3-DevKitC-1).
#ifndef IMU1_SDA_PIN
#define IMU1_SDA_PIN 8
#endif
#ifndef IMU1_SCL_PIN
#define IMU1_SCL_PIN 9
#endif

// ---- IMU 2: second I2C bus ----
// Confirmed against the Makerfabs ESP32-S3 4G LTE CAT1 A7670X schematic
// (V1.2 PDF, "Interface" sheet, connector J5/HEADER-13P): pins 7-8 are
// silkscreened IO17/I2C_SDA and IO18/I2C_SCL respectively.
#define IMU2_SDA_PIN 17
#define IMU2_SCL_PIN 18
#ifndef ENABLE_IMU2
#if NODE_FRONT
#define ENABLE_IMU2 0
#else
#define ENABLE_IMU2 1
#endif
#endif

// ---- JBD/Jiabaida BMS over BLE ----
// MAC and characteristic UUIDs as identified against a JBD-protocol pack in
// earlier work (BMS-Code repo). NOT YET RE-CONFIRMED against the specific
// pack fitted to this vehicle - onAdvertised() below logs every device seen
// during scanning so a mismatch is visible in the log rather than silent.
#define BMS_MAC_ADDRESS "a5:c2:37:46:13:76"
#define BMS_SERVICE_UUID "0000ff00-0000-1000-8000-00805f9b34fb"
#define BMS_NOTIFY_CHAR_UUID "0000ff01-0000-1000-8000-00805f9b34fb"
#define BMS_WRITE_CHAR_UUID "0000ff02-0000-1000-8000-00805f9b34fb"
#define BMS_QUERY_INTERVAL_MS 3000
#define BMS_RX_BUFFER_SIZE 128

// JBD basic-info query command (register 0x03): DD A5 03 00 FF FD 77
static const uint8_t BMS_QUERY_COMMAND[] = {0xDD, 0xA5, 0x03, 0x00, 0xFF, 0xFD, 0x77};

// ---- Pi time-sync pulse output ----
// GPIO21 (the original placeholder) does not exist on either of this
// board's breakout headers (J2/J5, HEADER-13P) - confirmed by direct
// physical inspection and by the Makerfabs schematic. GPIO15 is used
// instead: J5 pin 5, a plain GPIO with no strapping/alt-function role,
// sitting on the same connector as IMU2's I2C pins (J5 pins 7-8) for a
// single compact wiring loom to the Pi.
// The front node also drives a sync output (pin set by build flag), so the Pi
// can align the front node's clock the same way on a second GPIO input.
#ifndef SYNC_PULSE_PIN
#define SYNC_PULSE_PIN 15
#endif

// ---- Serial link to the Raspberry Pi 4 (v0.7.4.1, 21 Oct 2026) ----
// On the vehicle the unit runs from its own LiPo: powered from the Pi's USB it
// drew the Pi into under-voltage (and the board charges its battery from USB).
// The DASH line therefore also goes out on a plain UART, three wires to the Pi:
// IO41 (TX) to Pi pin 10 (GPIO15, RXD), IO42 (RX) from Pi pin 8 (GPIO14, TXD),
// and a common ground (already shared through the sync wire's GND on Pi pin 9).
// Both sides are 3.3 V logic. USB serial keeps working for flashing and debug.
// The front node leaves the UART off unless built with -D LINK_UART_ENABLE=1
// (pins and baud can then be set by build flags too).
#ifndef LINK_UART_ENABLE
#define LINK_UART_ENABLE (!NODE_FRONT)
#endif
#ifndef LINK_UART_TX_PIN
#define LINK_UART_TX_PIN 41
#endif
#ifndef LINK_UART_RX_PIN
#define LINK_UART_RX_PIN 42
#endif
#ifndef LINK_UART_BAUD
#define LINK_UART_BAUD 460800
#endif

// ---- Raw IMU stream (v0.7.5), format in include/raw_stream.h ----
// Every IMU sample also goes to the Pi as RAW lines. Rear unit: on the UART
// link only (the USB console would be flooded). Front node: on USB serial,
// and on the UART too when LINK_UART_ENABLE is 1.
#ifndef RAW_ON_USB
#define RAW_ON_USB NODE_FRONT
#endif
#define RAW_ON_UART LINK_UART_ENABLE
// Queue from the IMU tasks to the sender task: 0.5 s of both IMUs at 200 Hz.
// The IMU tasks never wait on it; a sample that does not fit is dropped and
// counted in rawDropped (the DASH "rawdrop" field).
#define RAW_QUEUE_LENGTH 200
// A batch is written once its first sample is this old, even if not full.
#define RAW_MAX_AGE_US 100000LL
// Room kept free in a port's TX buffer for the DASH line: a RAW line is only
// written when it leaves this much space, so DASH always fits behind it.
#define RAW_DASH_RESERVE 640
// How long the sender waits for room on a port before giving a line up
// (its samples are then counted in rawDropped too).
#define RAW_PORT_WAIT_MS 50
#define LINK_TX_BUFFER_BYTES 8192

// ---- Acquisition parameters ----
// ISO 2631-1 weights whole-body vibration up to 80 Hz, so Nyquist alone
// requires >=160 Hz. 200 Hz gives clean margin above that without pushing
// the I2C bus or the consumer task.
#define IMU_SAMPLE_RATE_HZ 200
#define IMU_SAMPLE_PERIOD_TICKS pdMS_TO_TICKS(1000 / IMU_SAMPLE_RATE_HZ)
#define IMU_QUEUE_LENGTH 100
#define I2C_CLOCK_HZ 400000
// Sensor ranges set in initImu(), and the counts per unit for them (MPU-6050
// datasheet; the same numbers the Adafruit driver uses).
#define MPU_ADDR 0x68
#define MPU_ACCEL_OUT_REG 0x3B
#define IMU_ACCEL_COUNTS_PER_G 4096   // +-8 g
#define IMU_GYRO_COUNTS_PER_DPS 65.5f // +-500 deg/s
#define IMU_DLPF_HZ 94

// ============================================================
// Data structures
// ============================================================
struct ImuSample {
  uint8_t sensor_id;     // 0 = IMU1, 1 = IMU2
  uint32_t sequence;
  int64_t timestamp_us;  // esp_timer_get_time(): monotonic since boot
  float ax, ay, az;      // m/s^2
  float gx, gy, gz;      // rad/s
};

struct ImuTaskConfig {
  uint8_t sensor_id;
  QueueHandle_t queue;
  QueueHandle_t char_queue;  // second, independent feed for ride characterisation
  Adafruit_MPU6050* sensor;
  bool* ready_flag;
  TwoWire* wire;             // the sensor's I2C bus, read directly since v0.7.5
};

// Time-domain ride-characterisation features, computed per window from the
// acceleration-magnitude signal (sqrt(ax^2+ay^2+az^2)) rather than a single
// "vertical" axis, since the sensor mounting has not yet been calibrated to
// a known vehicle-fixed frame (see Literature Review, Section 3: orientation
// compensation is required before a specific axis can be treated as
// vertical, and that step has not been implemented yet). Magnitude is
// rotation-invariant, so it remains meaningful regardless of mounting
// orientation, at the cost of not distinguishing which axis a disturbance
// came from - a reasonable first-pass tradeoff, not a final design choice.
struct RideFeatures {
  int64_t window_end_timestamp_us;
  uint32_t sample_count;
  float rms_mps2;
  float std_mps2;
  float peak_to_peak_mps2;
  float crest_factor;         // peak / RMS
  float mean_abs_jerk_mps3;   // mean |d(magnitude)/dt| across the window
  uint32_t threshold_crossings;  // samples above (mean + 2*std) - adaptive,
                                  // provisional: no field data yet exists to
                                  // set a fixed physical threshold instead.
  // Speed-normalised roughness index: mean-square acceleration divided by
  // vehicle speed. The transfer function from road profile to measured
  // acceleration is speed dependent, so a raw RMS conflates how rough the
  // road is with how fast the vehicle was driven - the same defect produces
  // a larger response at higher speed. Dividing the mean square by speed is
  // the normalisation used by Shock and Vibration 2018 (10.1155/2018/5131434)
  // for exactly this reason.
  //
  // NaN whenever it cannot be computed honestly: no GNSS fix, or a speed at
  // or below RIDE_MIN_SPEED_FOR_NORM (below which the quotient explodes and
  // means nothing - a stationary vehicle on a rough road is not experiencing
  // roughness). Consumers must check for NaN rather than assume a number.
  float speed_norm_index;
  float speed_used;           // the speed the index was divided by, for audit
};

#define RIDE_WINDOW_SAMPLES IMU_SAMPLE_RATE_HZ  // 1 s window at 200 Hz

// Below this speed the speed-normalised roughness index is not computed.
// Dividing by a near-zero speed produces an arbitrarily large number that
// says nothing about the road. Units are whatever the GNSS <speed> field
// reports - see parseGnssInfo(), which notes the units are not yet confirmed
// (knots vs km/h). CONFIRM AGAINST A REAL FIX before quoting the index
// quantitatively: drive at a known speed and compare. Until then the index
// is valid for relative comparison within one dataset, not as an absolute.
#define RIDE_MIN_SPEED_FOR_NORM 1.0f
#define RIDE_CHAR_QUEUE_LENGTH (RIDE_WINDOW_SAMPLES * 2)

struct RideCharTaskConfig {
  uint8_t sensor_id;
  QueueHandle_t queue;
  volatile RideFeatures* result;
  float mag_scale;  // per-sensor magnitude calibration factor, see loadOrCalibrateMagScale()
};

// Dual-IMU fusion. Both sensors are the same MPU6050 part in the same
// configuration, calibrated to the same scale, so their measurement noise is
// taken as equal; inverse-variance weighting then reduces to the plain mean,
// which is the minimum-variance unbiased combination of two such readings.
// The sensors are mounted at different points on the vehicle, so they are not
// measuring an identical quantity: the fused mean is reported together with a
// disagreement figure rather than hiding the difference between them.
//
// Only the linear features are averaged. Crest factor (a ratio) and the
// threshold-crossing count do not combine meaningfully by averaging, so they
// stay per-sensor.
//
// The two ride tasks fill their windows independently, so window boundaries
// are not sample-aligned. A pair is fused only when the two windows ended
// within half a window of each other (overlap of at least 50%), on the shared
// esp_timer clock. If one sensor stops producing windows, the fused output
// falls back to the other and says so via `sources`.
#define RIDE_FUSION_MAX_SKEW_US (500000LL)   // half of the 1 s window
#define RIDE_FUSION_STALE_US   (3000000LL)   // other sensor treated as absent after 3 s
#define RIDE_FUSION_STD_FLOOR  0.05f         // m/s^2, avoids dividing by near-zero std at rest

#define FUSED_SRC_IMU1 0x01
#define FUSED_SRC_IMU2 0x02

struct FusedRide {
  int64_t window_end_timestamp_us;
  uint8_t sources;            // FUSED_SRC_* bitmask of the sensors that contributed
  int64_t skew_us;            // |t1 - t2| for a two-sensor fusion, 0 for a fallback
  float rms_mps2;
  float std_mps2;
  float peak_to_peak_mps2;
  float mean_abs_jerk_mps3;
  float speed_norm_index;     // NaN unless every contributing sensor has one
  // |std1 - std2| / max(mean std, floor): how differently the two mounting
  // points are vibrating. NaN for a single-sensor fallback.
  float std_disagreement;
};

// Combines one window from each sensor. Returns false (and leaves *out
// untouched) when neither can be used. `now_us` is the time of the call, used
// only to decide whether the other sensor has gone stale.
bool fuseRideFeatures(const RideFeatures& a, const RideFeatures& b, int64_t now_us, FusedRide* out) {
  const bool aFresh = a.sample_count > 0 && (now_us - a.window_end_timestamp_us) <= RIDE_FUSION_STALE_US;
  const bool bFresh = b.sample_count > 0 && (now_us - b.window_end_timestamp_us) <= RIDE_FUSION_STALE_US;

  if (aFresh && bFresh) {
    int64_t skew = a.window_end_timestamp_us - b.window_end_timestamp_us;
    if (skew < 0) skew = -skew;
    if (skew > RIDE_FUSION_MAX_SKEW_US) return false;  // windows overlap too little to pair

    out->window_end_timestamp_us = (a.window_end_timestamp_us > b.window_end_timestamp_us)
                                       ? a.window_end_timestamp_us : b.window_end_timestamp_us;
    out->sources = FUSED_SRC_IMU1 | FUSED_SRC_IMU2;
    out->skew_us = skew;
    out->rms_mps2 = 0.5f * (a.rms_mps2 + b.rms_mps2);
    out->std_mps2 = 0.5f * (a.std_mps2 + b.std_mps2);
    out->peak_to_peak_mps2 = 0.5f * (a.peak_to_peak_mps2 + b.peak_to_peak_mps2);
    out->mean_abs_jerk_mps3 = 0.5f * (a.mean_abs_jerk_mps3 + b.mean_abs_jerk_mps3);
    out->speed_norm_index = (isnan(a.speed_norm_index) || isnan(b.speed_norm_index))
                                ? NAN : 0.5f * (a.speed_norm_index + b.speed_norm_index);
    const float denom = fmaxf(out->std_mps2, RIDE_FUSION_STD_FLOOR);
    out->std_disagreement = fabsf(a.std_mps2 - b.std_mps2) / denom;
    return true;
  }

  const RideFeatures* only = aFresh ? &a : (bFresh ? &b : nullptr);
  if (only == nullptr) return false;
  out->window_end_timestamp_us = only->window_end_timestamp_us;
  out->sources = aFresh ? FUSED_SRC_IMU1 : FUSED_SRC_IMU2;
  out->skew_us = 0;
  out->rms_mps2 = only->rms_mps2;
  out->std_mps2 = only->std_mps2;
  out->peak_to_peak_mps2 = only->peak_to_peak_mps2;
  out->mean_abs_jerk_mps3 = only->mean_abs_jerk_mps3;
  out->speed_norm_index = only->speed_norm_index;
  out->std_disagreement = NAN;
  return true;
}

// ============================================================
// Per-sensor magnitude calibration.
//
// Two "identical" MPU6050 breakouts do not read the same magnitude for the
// same physical state - factory sensitivity/bias tolerance means a
// stationary unit can read several percent away from the true 1g
// (9.80665 m/s^2) gravity magnitude. Since computeRideFeatures() works on
// magnitude only (see RideFeatures comment above), a single scalar
// correction factor applied before feature computation is the right scope
// here: it corrects the exact discrepancy this affects (RMS/std/p2p/jerk
// all scale linearly with it; crest factor and crossing counts are
// unaffected since both are scale-invariant ratios/threshold crossings
// under a uniform multiply). It does NOT correct per-axis bias or
// cross-axis coupling, which would require a full multi-orientation
// calibration - out of scope for now, since magnitude is already the only
// signal downstream code consumes.
//
// Calibrated once, at first boot after flashing (assumes the board is
// stationary then, which holds for bench bring-up), and the result is
// stored in NVS via Preferences so later boots - including on the vehicle,
// where "stationary at power-on" cannot be assumed - reuse the stored
// value instead of recalibrating blind.
// ============================================================
#define GRAVITY_MPS2 9.80665f
#define MAG_CAL_SAMPLE_COUNT 200  // 1 s at IMU_SAMPLE_RATE_HZ
#define MAG_CAL_SCALE_MIN 0.5f
#define MAG_CAL_SCALE_MAX 2.0f

Preferences imuCalPrefs;

float loadOrCalibrateMagScale(const char* nvsKey, Adafruit_MPU6050* sensor, bool ready) {
  imuCalPrefs.begin("imucal", false);
  if (imuCalPrefs.isKey(nvsKey)) {
    float scale = imuCalPrefs.getFloat(nvsKey, 1.0f);
    imuCalPrefs.end();
    Serial.printf("[CAL] %s: loaded stored scale=%.4f\n", nvsKey, scale);
    return scale;
  }
  imuCalPrefs.end();

  if (!ready) {
    // Not wired yet - don't store a bogus value, so a real calibration
    // still runs once this sensor is actually connected on a later boot.
    Serial.printf("[CAL] %s: sensor not ready, skipping calibration (scale=1.0 this run).\n", nvsKey);
    return 1.0f;
  }

  Serial.printf("[CAL] %s: no stored calibration. Assuming stationary for %ds...\n",
                nvsKey, MAG_CAL_SAMPLE_COUNT / IMU_SAMPLE_RATE_HZ);
  float sum = 0.0f;
  sensors_event_t accel, gyro, temp;
  for (int i = 0; i < MAG_CAL_SAMPLE_COUNT; i++) {
    sensor->getEvent(&accel, &gyro, &temp);
    sum += sqrtf(accel.acceleration.x * accel.acceleration.x +
                  accel.acceleration.y * accel.acceleration.y +
                  accel.acceleration.z * accel.acceleration.z);
    delay(1000 / IMU_SAMPLE_RATE_HZ);
  }
  float meanMag = sum / MAG_CAL_SAMPLE_COUNT;
  float scale = (meanMag > 1e-3f) ? (GRAVITY_MPS2 / meanMag) : 1.0f;

  if (scale < MAG_CAL_SCALE_MIN || scale > MAG_CAL_SCALE_MAX) {
    Serial.printf("[CAL] %s: computed scale=%.4f is outside sane range [%.1f, %.1f] "
                  "(likely not actually stationary) - falling back to 1.0, NOT stored.\n",
                  nvsKey, scale, MAG_CAL_SCALE_MIN, MAG_CAL_SCALE_MAX);
    return 1.0f;
  }

  imuCalPrefs.begin("imucal", false);
  imuCalPrefs.putFloat(nvsKey, scale);
  imuCalPrefs.end();
  Serial.printf("[CAL] %s: measured mean magnitude=%.4f, scale=%.4f, stored to NVS.\n",
                nvsKey, meanMag, scale);
  return scale;
}

// Pure function, no FreeRTOS/hardware dependency, so it can be exercised by
// selfTestRideFeatures() at boot without any sensor attached.
RideFeatures computeRideFeatures(const float* magnitude, uint32_t n, float sample_period_s) {
  RideFeatures f = {};
  f.sample_count = n;
  if (n == 0) return f;

  float sum = 0.0f, sumSq = 0.0f;
  float minV = magnitude[0], maxV = magnitude[0];
  for (uint32_t i = 0; i < n; i++) {
    sum += magnitude[i];
    sumSq += magnitude[i] * magnitude[i];
    if (magnitude[i] < minV) minV = magnitude[i];
    if (magnitude[i] > maxV) maxV = magnitude[i];
  }
  float mean = sum / n;
  float variance = (sumSq / n) - (mean * mean);
  if (variance < 0.0f) variance = 0.0f;  // fp rounding guard, not a real negative variance

  f.std_mps2 = sqrtf(variance);
  f.rms_mps2 = sqrtf(sumSq / n);
  f.peak_to_peak_mps2 = maxV - minV;
  f.crest_factor = (f.rms_mps2 > 1e-6f) ? (maxV / f.rms_mps2) : 0.0f;

  float jerkSum = 0.0f;
  for (uint32_t i = 1; i < n; i++) {
    jerkSum += fabsf((magnitude[i] - magnitude[i - 1]) / sample_period_s);
  }
  f.mean_abs_jerk_mps3 = (n > 1) ? (jerkSum / (n - 1)) : 0.0f;

  float threshold = mean + 2.0f * f.std_mps2;
  uint32_t crossings = 0;
  for (uint32_t i = 0; i < n; i++) {
    if (magnitude[i] > threshold) crossings++;
  }
  f.threshold_crossings = crossings;
  return f;
}

// One-shot self-test run from setup(), independent of whether any IMU is
// physically connected: generates a pure sine wave of known amplitude, for
// which RMS, peak-to-peak, and crest factor have closed-form expected
// values, and checks computeRideFeatures() against them within tolerance.
// This validates the feature-computation logic itself; it does NOT validate
// behaviour against real vehicle motion, which requires the physical IMUs.
void selfTestRideFeatures() {
  const uint32_t n = RIDE_WINDOW_SAMPLES;
  const float amplitude = 2.0f;   // m/s^2
  const float freq_hz = 5.0f;
  const float sample_period_s = 1.0f / IMU_SAMPLE_RATE_HZ;

  static float testSignal[RIDE_WINDOW_SAMPLES];
  for (uint32_t i = 0; i < n; i++) {
    testSignal[i] = amplitude * sinf(2.0f * PI * freq_hz * i * sample_period_s);
  }

  RideFeatures f = computeRideFeatures(testSignal, n, sample_period_s);

  const float expectedRms = amplitude / sqrtf(2.0f);
  const float expectedP2p = 2.0f * amplitude;
  const float expectedCrest = sqrtf(2.0f);
  const float tol = 0.05f;  // 5% - a discretely-sampled sine won't match the continuous ideal exactly

  bool rmsOk = fabsf(f.rms_mps2 - expectedRms) / expectedRms < tol;
  bool p2pOk = fabsf(f.peak_to_peak_mps2 - expectedP2p) / expectedP2p < tol;
  bool crestOk = fabsf(f.crest_factor - expectedCrest) / expectedCrest < tol;

  Serial.println("--- Ride-characterisation self-test (synthetic sine, no IMU needed) ---");
  Serial.printf("  RMS:    got=%.3f expected=%.3f  %s\n", f.rms_mps2, expectedRms, rmsOk ? "PASS" : "FAIL");
  Serial.printf("  P2P:    got=%.3f expected=%.3f  %s\n", f.peak_to_peak_mps2, expectedP2p, p2pOk ? "PASS" : "FAIL");
  Serial.printf("  Crest:  got=%.3f expected=%.3f  %s\n", f.crest_factor, expectedCrest, crestOk ? "PASS" : "FAIL");
  Serial.printf("  Overall: %s\n\n", (rmsOk && p2pOk && crestOk) ? "PASS" : "FAIL - check computeRideFeatures()");
}

// One-shot self-test of fuseRideFeatures() with synthetic windows: checks the
// averaging, the disagreement figure, rejection of badly misaligned windows,
// and fallback to a single sensor when the other has gone stale.
void selfTestRideFusion() {
  const int64_t now = 10000000LL;  // arbitrary 10 s
  RideFeatures a = {};
  RideFeatures b = {};
  a.sample_count = b.sample_count = RIDE_WINDOW_SAMPLES;
  a.window_end_timestamp_us = now - 100000LL;   // 100 ms apart: should pair
  b.window_end_timestamp_us = now - 200000LL;
  a.rms_mps2 = 10.0f; b.rms_mps2 = 9.8f;
  a.std_mps2 = 0.30f; b.std_mps2 = 0.10f;
  a.peak_to_peak_mps2 = 2.0f; b.peak_to_peak_mps2 = 1.0f;
  a.mean_abs_jerk_mps3 = 40.0f; b.mean_abs_jerk_mps3 = 20.0f;
  a.speed_norm_index = 2.0f; b.speed_norm_index = NAN;

  FusedRide f = {};
  const bool paired = fuseRideFeatures(a, b, now, &f);
  const bool meanOk = paired && f.sources == (FUSED_SRC_IMU1 | FUSED_SRC_IMU2)
                      && fabsf(f.rms_mps2 - 9.9f) < 1e-4f && fabsf(f.std_mps2 - 0.20f) < 1e-4f
                      && fabsf(f.peak_to_peak_mps2 - 1.5f) < 1e-4f && fabsf(f.mean_abs_jerk_mps3 - 30.0f) < 1e-4f
                      && f.skew_us == 100000LL;
  const bool disOk = paired && fabsf(f.std_disagreement - 1.0f) < 1e-4f;   // |0.3-0.1| / 0.2
  const bool normOk = paired && isnan(f.speed_norm_index);                 // one side missing -> NaN

  RideFeatures bLate = b;
  bLate.window_end_timestamp_us = now - 800000LL;  // 700 ms from a: too little overlap
  FusedRide g = {};
  const bool skewOk = !fuseRideFeatures(a, bLate, now, &g);

  RideFeatures bStale = b;
  bStale.window_end_timestamp_us = now - 5000000LL;  // 5 s old: treated as absent
  FusedRide h = {};
  const bool fbOk = fuseRideFeatures(a, bStale, now, &h) && h.sources == FUSED_SRC_IMU1
                    && fabsf(h.rms_mps2 - 10.0f) < 1e-4f && isnan(h.std_disagreement);

  Serial.println("--- Dual-IMU fusion self-test (synthetic windows, no IMU needed) ---");
  Serial.printf("  Mean of both sensors:     %s\n", meanOk ? "PASS" : "FAIL");
  Serial.printf("  Disagreement figure:      %s\n", disOk ? "PASS" : "FAIL");
  Serial.printf("  Speed index needs both:   %s\n", normOk ? "PASS" : "FAIL");
  Serial.printf("  Misaligned pair rejected: %s\n", skewOk ? "PASS" : "FAIL");
  Serial.printf("  Stale sensor fallback:    %s\n", fbOk ? "PASS" : "FAIL");
  Serial.printf("  Overall: %s\n\n", (meanOk && disOk && normOk && skewOk && fbOk)
                                        ? "PASS" : "FAIL - check fuseRideFeatures()");
}

struct BmsSample {
  int64_t timestamp_us;
  bool checksum_ok;       // frame passed length + checksum validation
  bool plausible;         // secondary sanity-range check, see validateBmsFrame()
  float pack_voltage_v;
  float current_a;        // positive = discharging, per original decode
  float remaining_ah;
  float nominal_ah;
  uint8_t soc_pct;
  uint16_t protection_flags;
  float mos_temp_c;
  float t1_temp_c;
  float t2_temp_c;
  uint8_t ntc_count;
};

struct GnssFix {
  int64_t timestamp_us;   // esp_timer_get_time() at time of parse
  bool valid;             // true only if fix_mode and coordinates are present
  uint8_t fix_mode;       // raw <mode> field, meaning not yet cross-checked
  float latitude_deg;
  float longitude_deg;
  float altitude_m;
  float speed_reported;   // units NOT confirmed - see parseGnssInfo() comment
  float course_deg;       // course over ground
  float hdop;             // horizontal dilution of precision (lower is better)
  uint8_t satellites;     // satellites used, summed over the constellations reported
  uint32_t utc_date;      // ddmmyy as sent by the modem
  float utc_time;         // hhmmss.ss as sent by the modem
};

// ============================================================
// Globals
// ============================================================
Adafruit_MPU6050 mpu1;
Adafruit_MPU6050 mpu2;
bool imu1Ready = false;
bool imu2Ready = false;

QueueHandle_t imu1Queue;
QueueHandle_t imu2Queue;
QueueHandle_t gnssQueue;
QueueHandle_t bmsQueue;

// BLE / BMS state. pClient is created exactly once in setup() and reused
// for every connect/reconnect - the original implementation called
// BLEDevice::createClient() on every cycle, leaking a client object every
// ~10 s of runtime.
#if !NODE_FRONT
static BLEClient* bmsClient = nullptr;
static BLERemoteCharacteristic* bmsNotifyChar = nullptr;
static BLERemoteCharacteristic* bmsWriteChar = nullptr;
static BLEAddress* bmsAddress = nullptr;

volatile bool bmsConnected = false;
volatile bool bmsShouldConnect = false;
static uint8_t bmsRxBuffer[BMS_RX_BUFFER_SIZE];
static size_t bmsRxIndex = 0;

volatile uint32_t bmsValidFrames = 0;
volatile uint32_t bmsChecksumFailures = 0;
volatile uint32_t bmsDisconnectCount = 0;
volatile uint32_t bmsReconnectCount = 0;
volatile uint32_t bmsDropped = 0;
#endif
volatile BmsSample latestBmsSample = {};
volatile GnssFix latestGnssFix = {};

// ---- Phone-style positioning (v0.7.3) ----
// Assisted GNSS: AT+CAGPS downloads satellite orbit data over LTE so the receiver
// can fix in seconds outdoors instead of searching for minutes ("+AGPS: success."
// on this modem, 10 Oct 2026). Refreshed every 2 h, retried every minute until it works.
// Cell-tower position: AT+CLBS=4 returns the modem's own estimate from the towers it
// hears, with its accuracy (about 550 m indoors on 10 Oct). It is what a phone shows
// indoors. It is kept apart from the GNSS fix and never feeds speed, course or the
// ride index; it is only polled while there is no GNSS fix.
struct CellLocation {
  int64_t timestamp_us;
  bool valid;
  float latitude_deg;
  float longitude_deg;
  float accuracy_m;
};
volatile CellLocation latestCellLoc = {};
bool agpsOk = false;
uint32_t agpsAttempts = 0;
unsigned long agpsNextMs = 15000;       // first try 15 s after boot, once the network is up
unsigned long cellLocNextMs = 20000;
#define AGPS_REFRESH_MS (2UL * 60UL * 60UL * 1000UL)
#define AGPS_RETRY_MS 60000UL
#define CELL_LOC_INTERVAL_MS 60000UL
#define CELL_LOC_STALE_US (5LL * 60LL * 1000000LL)   // older than 5 min: not shown
// "!gnssraw" toggles printing the modem's raw +CGNSSINFO reply on every
// poll, for checking the parser without sending extra AT commands.
volatile bool gnssPrintRaw = false;

static ImuTaskConfig imu1Config;
static ImuTaskConfig imu2Config;

TaskHandle_t ModemTaskHandle;
TaskHandle_t Imu1TaskHandle;
TaskHandle_t Imu2TaskHandle;
TaskHandle_t StatsTaskHandle;
TaskHandle_t SyncTaskHandle;
TaskHandle_t BmsTaskHandle;
TaskHandle_t DashTaskHandle;

volatile uint32_t imu1Dropped = 0;
volatile uint32_t imu2Dropped = 0;
volatile uint32_t imu1CharDropped = 0;
volatile uint32_t imu2CharDropped = 0;
// Achieved sample rate per IMU over StatsTask's last 2 s report window
// (v0.7.0), published for DashTask. 0 when a sensor produced no samples.
volatile float imu1RateHz = 0.0f;
volatile float imu2RateHz = 0.0f;

QueueHandle_t imu1CharQueue;
QueueHandle_t imu2CharQueue;
volatile RideFeatures latestRideFeatures1 = {};
volatile RideFeatures latestRideFeatures2 = {};
volatile FusedRide latestFusedRide = {};
// Guards latestRideFeatures1/2 and latestFusedRide. The two ride tasks and the
// modem task read and write these from different contexts, and field-by-field
// copies of a volatile struct could otherwise be torn mid-update.
portMUX_TYPE rideMux = portMUX_INITIALIZER_UNLOCKED;
static RideCharTaskConfig rideChar1Config;
static RideCharTaskConfig rideChar2Config;
TaskHandle_t RideChar1TaskHandle;
TaskHandle_t RideChar2TaskHandle;

// ---- Raw stream and read-health state (v0.7.5) ----
// Thin wrapper so rawOffer() (include/raw_stream.h) can be host-tested with a
// plain ring in place of the FreeRTOS queue.
struct RawQueue {
  QueueHandle_t h;
  bool trySend(const RawItem& it) { return xQueueSend(h, &it, 0) == pdTRUE; }
};
RawQueue rawQueue = {nullptr};
QueueHandle_t rawSyncQueue;          // sync edges for the sender, see SyncTask
TaskHandle_t RawSenderTaskHandle;
volatile bool rawEnabled = true;     // "!raw off" / "!raw on"
// Samples produced but never sent, per IMU (DASH "rawdrop" is the sum):
// queue full, the sender fell behind (counted by the IMU task), and lines no
// port took (counted by the sender). Two counters so each has one writer.
volatile uint32_t rawQueueDropped[2] = {0, 0};
volatile uint32_t rawPortDropped[2] = {0, 0};
static inline uint32_t rawDropped(int imu) { return rawQueueDropped[imu] + rawPortDropped[imu]; }
volatile uint32_t rawLinesSent = 0;
volatile uint32_t rawSyncDropped = 0;
// Read failures and stuck samples per IMU (DASH "rdfail" and "stuck").
// Written only by that IMU's task.
ImuHealth imuHealth[2] = {};
// Sync pulse state, written by SyncTask, read by the IMU tasks for the flag bit.
volatile uint8_t syncLevel = 0;
volatile uint32_t syncEdgeCount = 0;
struct RawSyncEvent {
  uint32_t edge;
  uint8_t level;
  int64_t t_us;
};

// ============================================================
// IMU initialisation
// ============================================================
bool initImu(Adafruit_MPU6050* sensor, TwoWire* wire, int sda, int scl) {
  wire->begin(sda, scl);
  wire->setClock(I2C_CLOCK_HZ);

  if (!sensor->begin(0x68, wire)) {
    return false;
  }

  // Range: +-8g. Chosen for headroom against clipping on pothole/kerb
  // impacts while retaining resolution; revisit once field data shows
  // the actual peak levels this vehicle produces.
  sensor->setAccelerometerRange(MPU6050_RANGE_8_G);
  sensor->setGyroRange(MPU6050_RANGE_500_DEG);

  // Filter bandwidth (v0.7.4): 94 Hz, was 260 Hz up to v0.7.3. Sampling is
  // 200 Hz, so the Nyquist frequency is 100 Hz: with the 260 Hz filter,
  // vibration between 100 and 260 Hz passed the sensor's own low-pass filter
  // and aliased into the 0 to 100 Hz band the ride features are computed
  // from. 94 Hz is the widest MPU6050 preset below Nyquist and still covers
  // the ISO 2631-1 whole-body band (weighting up to 80 Hz), as the report's
  // Methodology (ride features) recommends before field data. The filter
  // adds a few ms of group delay, which the 1 s ride windows do not notice.
  sensor->setFilterBandwidth(MPU6050_BAND_94_HZ);

  return true;
}

// ============================================================
// IMU acquisition task. One function drives both sensors via the
// config struct, so the 200 Hz timing path is written and tested once.
// No Serial I/O in this task - blocking on USB CDC output would eat
// directly into the sample period and defeat the point of measuring it.
//
// v0.7.5: the sensor is read with one 14-byte I2C burst (accel, temperature,
// gyro) instead of the Adafruit getEvent(). getEvent() always returns true,
// even when the bus read failed (it then converts whatever was in its
// buffer), and it reads the two range registers again on every call (three
// transactions per sample). The direct read checks the bus result, gives
// the raw counts for the raw stream, and converts them with the same
// arithmetic as the driver, so the float values are unchanged. A failed read
// sends nothing (the slot number still advances, so the gap is visible) and
// is counted; a read identical to the previous one is counted as stuck.
// ============================================================

// Reads ax ay az, temperature, gx gy gz as counts. False if the bus did not
// acknowledge or returned fewer than 14 bytes.
static bool readImuRaw(TwoWire* wire, int16_t out[7]) {
  wire->beginTransmission(MPU_ADDR);
  wire->write(MPU_ACCEL_OUT_REG);
  if (wire->endTransmission(false) != 0) return false;
  if (wire->requestFrom((uint8_t)MPU_ADDR, (uint8_t)14) != 14) return false;
  uint8_t b[14];
  for (int i = 0; i < 14; i++) {
    const int c = wire->read();
    if (c < 0) return false;
    b[i] = (uint8_t)c;
  }
  for (int i = 0; i < 7; i++) out[i] = (int16_t)((b[2 * i] << 8) | b[2 * i + 1]);
  return true;
}

void ImuTask(void* pvParameters) {
  ImuTaskConfig* cfg = static_cast<ImuTaskConfig*>(pvParameters);
  uint32_t seq = 0;
  TickType_t lastWake = xTaskGetTickCount();
  ImuHealth& health = imuHealth[cfg->sensor_id];

  for (;;) {
    if (*(cfg->ready_flag)) {
      int16_t raw[7];
      const bool ok = readImuRaw(cfg->wire, raw);
      const uint32_t slot = seq++;
      const int16_t motion[6] = {raw[0], raw[1], raw[2], raw[4], raw[5], raw[6]};
      const bool stuck = imuHealthNote(health, ok, motion);
      if (!ok) {
        vTaskDelayUntil(&lastWake, IMU_SAMPLE_PERIOD_TICKS);
        continue;
      }

      ImuSample sample;
      sample.sensor_id = cfg->sensor_id;
      sample.sequence = slot;
      sample.timestamp_us = esp_timer_get_time();
      // As Adafruit_MPU6050::_read() and fillAccelEvent()/fillGyroEvent().
      sample.ax = ((float)motion[0] / (float)IMU_ACCEL_COUNTS_PER_G) * SENSORS_GRAVITY_STANDARD;
      sample.ay = ((float)motion[1] / (float)IMU_ACCEL_COUNTS_PER_G) * SENSORS_GRAVITY_STANDARD;
      sample.az = ((float)motion[2] / (float)IMU_ACCEL_COUNTS_PER_G) * SENSORS_GRAVITY_STANDARD;
      sample.gx = ((float)motion[3] / IMU_GYRO_COUNTS_PER_DPS) * SENSORS_DPS_TO_RADS;
      sample.gy = ((float)motion[4] / IMU_GYRO_COUNTS_PER_DPS) * SENSORS_DPS_TO_RADS;
      sample.gz = ((float)motion[5] / IMU_GYRO_COUNTS_PER_DPS) * SENSORS_DPS_TO_RADS;

      // Raw stream: one try on its own queue, never waiting (see RawSenderTask).
      if (rawEnabled && rawQueue.h != nullptr) {
        RawItem it;
        it.imu = cfg->sensor_id;
        it.s.seq = slot;
        it.s.t_us = sample.timestamp_us;
        it.s.flags = (syncLevel ? RAW_FLAG_SYNC : 0) | (stuck ? RAW_FLAG_STUCK : 0);
        for (int a = 0; a < 6; a++) it.s.v[a] = motion[a];
        rawOffer(rawQueue, it, &rawQueueDropped[cfg->sensor_id]);
      }

      if (xQueueSend(cfg->queue, &sample, 0) != pdTRUE) {
        // Queue full: the consumer is falling behind. Count and drop
        // rather than block, so acquisition timing is never held
        // hostage by a slow consumer.
        if (cfg->sensor_id == 0) {
          imu1Dropped++;
        } else {
          imu2Dropped++;
        }
      }

      // Independent second feed for ride-characterisation windowing. Kept
      // as a separate queue rather than sharing cfg->queue, so that adding
      // this consumer cannot change StatsTask's already-validated jitter
      // and dropped-sample accounting for the acquisition path itself.
      if (xQueueSend(cfg->char_queue, &sample, 0) != pdTRUE) {
        if (cfg->sensor_id == 0) {
          imu1CharDropped++;
        } else {
          imu2CharDropped++;
        }
      }
    }

    // vTaskDelayUntil measures the period from the *target* wake time,
    // not from when this iteration happened to finish - this is what
    // keeps long-run sample timing from drifting under load.
    vTaskDelayUntil(&lastWake, IMU_SAMPLE_PERIOD_TICKS);
  }
}

// ============================================================
// Stats / consumer task. Drains both queues and periodically reports
// the acquisition-integrity evidence: achieved rate, inter-sample
// jitter (min/avg/max), and dropped-sample counts per sensor.
// ============================================================
void StatsTask(void* pvParameters) {
  const TickType_t reportInterval = pdMS_TO_TICKS(2000);
  TickType_t lastReport = xTaskGetTickCount();

  uint32_t imu1Count = 0, imu2Count = 0;
  int64_t imu1LastTs = -1, imu2LastTs = -1;
  int64_t imu1MinDt = INT64_MAX, imu1MaxDt = 0, imu1SumDt = 0;
  int64_t imu2MinDt = INT64_MAX, imu2MaxDt = 0, imu2SumDt = 0;

  uint32_t gnssCount = 0, gnssValidCount = 0;

  for (;;) {
    ImuSample sample;
    GnssFix fix;

    // GNSS polls at ~1/3s, far below IMU rate - draining here (rather
    // than a dedicated task) is enough. Without this the queue fills
    // silently over about a minute, since nothing else was consuming it.
    while (xQueueReceive(gnssQueue, &fix, 0) == pdTRUE) {
      gnssCount++;
      if (fix.valid) gnssValidCount++;
    }

    BmsSample bmsSample;
    while (xQueueReceive(bmsQueue, &bmsSample, 0) == pdTRUE) {
      // Draining only - the per-frame summary is already printed from
      // parseBmsData() at the moment each frame arrives.
    }

    while (xQueueReceive(imu1Queue, &sample, 0) == pdTRUE) {
      if (imu1LastTs >= 0) {
        int64_t dt = sample.timestamp_us - imu1LastTs;
        if (dt < imu1MinDt) imu1MinDt = dt;
        if (dt > imu1MaxDt) imu1MaxDt = dt;
        imu1SumDt += dt;
      }
      imu1LastTs = sample.timestamp_us;
      imu1Count++;
    }

    while (xQueueReceive(imu2Queue, &sample, 0) == pdTRUE) {
      if (imu2LastTs >= 0) {
        int64_t dt = sample.timestamp_us - imu2LastTs;
        if (dt < imu2MinDt) imu2MinDt = dt;
        if (dt > imu2MaxDt) imu2MaxDt = dt;
        imu2SumDt += dt;
      }
      imu2LastTs = sample.timestamp_us;
      imu2Count++;
    }

    if (xTaskGetTickCount() - lastReport >= reportInterval) {
      lastReport = xTaskGetTickCount();
      float elapsed_s = reportInterval / 1000.0f;
      imu1RateHz = imu1Count / elapsed_s;
      imu2RateHz = imu2Count / elapsed_s;

      Serial.println("--- Acquisition stats (2s window) ---");
      if (imu1Count > 0) {
        uint32_t divisor = imu1Count > 1 ? imu1Count - 1 : 1;
        Serial.printf("IMU1: %lu samples (%.1f Hz)  dt_us[min=%lld avg=%lld max=%lld]  dropped=%lu\n",
                      (unsigned long)imu1Count, imu1Count / elapsed_s,
                      (long long)imu1MinDt, (long long)(imu1SumDt / divisor),
                      (long long)imu1MaxDt, (unsigned long)imu1Dropped);
      } else {
        Serial.println("IMU1: no samples (not ready)");
      }
      if (imu2Count > 0) {
        uint32_t divisor = imu2Count > 1 ? imu2Count - 1 : 1;
        Serial.printf("IMU2: %lu samples (%.1f Hz)  dt_us[min=%lld avg=%lld max=%lld]  dropped=%lu\n",
                      (unsigned long)imu2Count, imu2Count / elapsed_s,
                      (long long)imu2MinDt, (long long)(imu2SumDt / divisor),
                      (long long)imu2MaxDt, (unsigned long)imu2Dropped);
      } else {
        Serial.println("IMU2: no samples (not ready / not connected)");
      }
      // Read health and raw stream (v0.7.5), totals since boot.
      Serial.printf("IMU health: rdfail=[%lu,%lu] stuck=[%lu,%lu] rawdrop=[%lu,%lu] raw_lines=%lu\n",
                    (unsigned long)imuHealth[0].rdfail, (unsigned long)imuHealth[1].rdfail,
                    (unsigned long)imuHealth[0].stuck, (unsigned long)imuHealth[1].stuck,
                    (unsigned long)rawDropped(0), (unsigned long)rawDropped(1),
                    (unsigned long)rawLinesSent);
#if !NODE_FRONT
      Serial.printf("GNSS: %lu polls, %lu with a fix\n",
                    (unsigned long)gnssCount, (unsigned long)gnssValidCount);
      Serial.printf("BMS: connected=%s valid=%lu checksum_fail=%lu "
                    "disconnects=%lu reconnects=%lu dropped=%lu\n",
                    bmsConnected ? "yes" : "no", (unsigned long)bmsValidFrames,
                    (unsigned long)bmsChecksumFailures, (unsigned long)bmsDisconnectCount,
                    (unsigned long)bmsReconnectCount, (unsigned long)bmsDropped);
#endif
      Serial.printf("Free heap: %u bytes\n\n", ESP.getFreeHeap());

      imu1Count = 0; imu2Count = 0;
      imu1MinDt = INT64_MAX; imu1MaxDt = 0; imu1SumDt = 0;
      imu2MinDt = INT64_MAX; imu2MaxDt = 0; imu2SumDt = 0;
      gnssCount = 0; gnssValidCount = 0;
    }

    vTaskDelay(pdMS_TO_TICKS(5));
  }
}

// ============================================================
// Ride-characterisation task: one instance per IMU (via config, same
// pattern as ImuTask/BmsTask). Fills a fixed-size window from its own
// dedicated queue, computes time-domain features once the window is full,
// and stores the result for the (separate) networking task to publish.
// Lower priority than ImuTask so this never competes with acquisition
// timing - falling behind here drops characterisation windows, which is
// far preferable to perturbing the 200 Hz sample clock.
// ============================================================
// Field-by-field copy out of a volatile struct (whole-struct assignment from a
// volatile source does not compile). Callers hold rideMux.
static void copyRide(RideFeatures& dst, const volatile RideFeatures& src) {
  dst.window_end_timestamp_us = src.window_end_timestamp_us;
  dst.sample_count = src.sample_count;
  dst.rms_mps2 = src.rms_mps2;
  dst.std_mps2 = src.std_mps2;
  dst.peak_to_peak_mps2 = src.peak_to_peak_mps2;
  dst.crest_factor = src.crest_factor;
  dst.mean_abs_jerk_mps3 = src.mean_abs_jerk_mps3;
  dst.threshold_crossings = src.threshold_crossings;
  dst.speed_norm_index = src.speed_norm_index;
  dst.speed_used = src.speed_used;
}

// Called by each ride task after it publishes a window. Snapshots both
// sensors under the lock, fuses outside it, then publishes the result.
static void updateFusedRide() {
  RideFeatures a, b;
  portENTER_CRITICAL(&rideMux);
  copyRide(a, latestRideFeatures1);
  copyRide(b, latestRideFeatures2);
  portEXIT_CRITICAL(&rideMux);

  FusedRide f;
  if (!fuseRideFeatures(a, b, esp_timer_get_time(), &f)) return;

  portENTER_CRITICAL(&rideMux);
  latestFusedRide.window_end_timestamp_us = f.window_end_timestamp_us;
  latestFusedRide.sources = f.sources;
  latestFusedRide.skew_us = f.skew_us;
  latestFusedRide.rms_mps2 = f.rms_mps2;
  latestFusedRide.std_mps2 = f.std_mps2;
  latestFusedRide.peak_to_peak_mps2 = f.peak_to_peak_mps2;
  latestFusedRide.mean_abs_jerk_mps3 = f.mean_abs_jerk_mps3;
  latestFusedRide.speed_norm_index = f.speed_norm_index;
  latestFusedRide.std_disagreement = f.std_disagreement;
  portEXIT_CRITICAL(&rideMux);

  const char* src = (f.sources == (FUSED_SRC_IMU1 | FUSED_SRC_IMU2)) ? "1+2"
                    : (f.sources == FUSED_SRC_IMU1 ? "1 only" : "2 only");
  Serial.printf("[FUSED] src=%s skew=%lldms rms=%.3f std=%.3f p2p=%.3f jerk=%.3f dis=%.2f\n",
                src, (long long)(f.skew_us / 1000), f.rms_mps2, f.std_mps2,
                f.peak_to_peak_mps2, f.mean_abs_jerk_mps3, f.std_disagreement);
}

void RideCharacterizationTask(void* pvParameters) {
  RideCharTaskConfig* cfg = static_cast<RideCharTaskConfig*>(pvParameters);
  static float window1[RIDE_WINDOW_SAMPLES];
  static float window2[RIDE_WINDOW_SAMPLES];
  float* window = (cfg->sensor_id == 0) ? window1 : window2;
  uint32_t count = 0;
  const float samplePeriodS = 1.0f / IMU_SAMPLE_RATE_HZ;

  for (;;) {
    ImuSample sample;
    if (xQueueReceive(cfg->queue, &sample, pdMS_TO_TICKS(50)) == pdTRUE) {
      window[count++] = cfg->mag_scale *
          sqrtf(sample.ax * sample.ax + sample.ay * sample.ay + sample.az * sample.az);

      if (count >= RIDE_WINDOW_SAMPLES) {
        RideFeatures f = computeRideFeatures(window, count, samplePeriodS);
        f.window_end_timestamp_us = sample.timestamp_us;

        // Speed-normalise against the most recent GNSS fix. Deliberately
        // yields NaN rather than a misleading number when there is no fix or
        // the vehicle is too slow for the quotient to mean anything.
        const bool fixValid = latestGnssFix.valid;
        const float v = latestGnssFix.speed_reported;
        if (fixValid && !isnan(v) && v >= RIDE_MIN_SPEED_FOR_NORM) {
          // Variance, not the raw mean square: the magnitude includes gravity, so its mean square
          // sits near 96 m^2/s^4 at rest and would swamp the vibration (review, 10 Oct 2026).
          f.speed_norm_index = (f.std_mps2 * f.std_mps2) / v;  // vibration variance / speed
          f.speed_used = v;
        } else {
          f.speed_norm_index = NAN;
          f.speed_used = NAN;
        }
        // Field-by-field, not *(cfg->result) = f: the compiler-generated
        // struct operator= is not volatile-qualified, so whole-struct
        // assignment through a volatile pointer does not compile.
        portENTER_CRITICAL(&rideMux);
        cfg->result->window_end_timestamp_us = f.window_end_timestamp_us;
        cfg->result->sample_count = f.sample_count;
        cfg->result->rms_mps2 = f.rms_mps2;
        cfg->result->std_mps2 = f.std_mps2;
        cfg->result->peak_to_peak_mps2 = f.peak_to_peak_mps2;
        cfg->result->crest_factor = f.crest_factor;
        cfg->result->mean_abs_jerk_mps3 = f.mean_abs_jerk_mps3;
        cfg->result->threshold_crossings = f.threshold_crossings;
        cfg->result->speed_norm_index = f.speed_norm_index;
        cfg->result->speed_used = f.speed_used;
        portEXIT_CRITICAL(&rideMux);

        if (isnan(f.speed_norm_index)) {
          Serial.printf("[RIDE%d] n=%lu rms=%.3f std=%.3f p2p=%.3f crest=%.3f jerk=%.3f "
                        "crossings=%lu norm=n/a\n",
                        cfg->sensor_id + 1, (unsigned long)f.sample_count, f.rms_mps2, f.std_mps2,
                        f.peak_to_peak_mps2, f.crest_factor, f.mean_abs_jerk_mps3,
                        (unsigned long)f.threshold_crossings);
        } else {
          Serial.printf("[RIDE%d] n=%lu rms=%.3f std=%.3f p2p=%.3f crest=%.3f jerk=%.3f "
                        "crossings=%lu norm=%.4f v=%.2f\n",
                        cfg->sensor_id + 1, (unsigned long)f.sample_count, f.rms_mps2, f.std_mps2,
                        f.peak_to_peak_mps2, f.crest_factor, f.mean_abs_jerk_mps3,
                        (unsigned long)f.threshold_crossings, f.speed_norm_index, f.speed_used);
        }
        count = 0;
        updateFusedRide();
      }
    }
    // No fixed vTaskDelay here: the 50ms queue-receive timeout above already
    // paces this task without busy-waiting when data is slow or absent.
  }
}

// ============================================================
// Pi time-sync pulse: 1 Hz toggle on a dedicated GPIO. The Raspberry Pi
// watches the same line on its own GPIO input and timestamps the edge
// with its own clock; comparing the two logs post-hoc gives the clock
// offset and drift between the two boards. See lab plan session D4.
// ============================================================
void SyncTask(void* pvParameters) {
  pinMode(SYNC_PULSE_PIN, OUTPUT);
  bool state = false;
  TickType_t lastWake = xTaskGetTickCount();

  for (;;) {
    state = !state;
    digitalWrite(SYNC_PULSE_PIN, state);
    // Edge time taken right after the write (v0.7.5), for the RAWS line.
    const int64_t edgeUs = esp_timer_get_time();
    syncLevel = state ? 1 : 0;
    const uint32_t edge = ++syncEdgeCount;
    if (rawSyncQueue != nullptr) {
      RawSyncEvent ev = {edge, (uint8_t)(state ? 1 : 0), edgeUs};
      if (xQueueSend(rawSyncQueue, &ev, 0) != pdTRUE) rawSyncDropped++;
    }
    // Logged so the ESP32-side edge time can be cross-checked against
    // whatever the Pi records for the same transition.
    Serial.printf("[SYNC] pin=%s  t=%lld us\n", state ? "HIGH" : "LOW", (long long)edgeUs);
    vTaskDelayUntil(&lastWake, pdMS_TO_TICKS(500));
  }
}

// ============================================================
// Raw stream sender (v0.7.5). Format in include/raw_stream.h and
// RAW_STREAM.md.
//
// The IMU tasks put each sample on rawQueue with no wait (a full queue drops
// and counts the sample, see ImuTask). This task, at the lowest priority on
// core 0 (away from the IMU tasks on core 1), groups consecutive samples of
// one IMU into lines of up to RAW_BATCH and writes each line with a single
// write call, so no other task's output lands inside it. A line is written
// only when the port's TX buffer keeps RAW_DASH_RESERVE bytes free after it,
// so the 1 Hz DASH line always fits; if a port stays full for
// RAW_PORT_WAIT_MS the line is given up there, and if no port took it its
// samples are counted in rawDropped as well.
//
// Link budget at 460800 baud, 8N1: 46080 bytes/s. A full line of 10 samples
// is about 363 bytes on the rear unit, so 2 IMUs at 200 Hz need about
// 14.5 kB/s, plus RAWH (about 30 B/s), RAWS (about 80 B/s) and DASH
// (under 0.6 kB/s): about 15.2 kB/s, a third of the link.
// ============================================================
static Print* rawPorts[2] = {nullptr, nullptr};
static bool rawPortIsUsb[2] = {false, false};
static uint8_t rawPortCount = 0;

// Writes one line to every raw port. Returns true if at least one port took it.
static bool rawWriteLine(const char* line, size_t len) {
  bool any = false;
  for (uint8_t i = 0; i < rawPortCount; i++) {
    Print* port = rawPorts[i];
    // USB serial with no host attached: skip at once rather than wait.
    if (rawPortIsUsb[i] && !Serial) continue;
    bool room = false;
    for (int waited = 0; waited <= RAW_PORT_WAIT_MS; waited += 2) {
      if (port->availableForWrite() >= (int)(len + RAW_DASH_RESERVE)) {
        room = true;
        break;
      }
      vTaskDelay(pdMS_TO_TICKS(2));
    }
    if (!room) continue;
    port->write(reinterpret_cast<const uint8_t*>(line), len);
    any = true;
  }
  return any;
}

static void rawFlushBatch(RawBatch& b, uint8_t imu) {
  static char line[RAW_LINE_MAX];
  if (b.n == 0) return;
  const size_t len = rawEncodeLine(line, sizeof(line), NODE_ID, (uint8_t)(imu + 1), b.s, b.n);
  if (len > 0 && rawWriteLine(line, len)) {
    rawLinesSent++;
  } else {
    rawPortDropped[imu] += b.n;
  }
  b.n = 0;
}

void RawSenderTask(void* pvParameters) {
  static RawBatch batches[2];
  static char small[RAW_SMALL_LINE_MAX];
  int64_t nextHeaderUs = 0;
  const char* fw = FIRMWARE_VERSION;
  if (fw[0] == 'v') fw++;

  for (;;) {
    // Sync edges first: small and the reason the Pi can align clocks.
    RawSyncEvent ev;
    while (xQueueReceive(rawSyncQueue, &ev, 0) == pdTRUE) {
      const size_t len = rawEncodeSync(small, sizeof(small), NODE_ID, ev.edge, ev.level, ev.t_us);
      if (len > 0) rawWriteLine(small, len);
    }

    RawItem it;
    if (xQueueReceive(rawQueue.h, &it, pdMS_TO_TICKS(10)) == pdTRUE && it.imu < 2) {
      RawBatch& b = batches[it.imu];
      if (!rawBatchAdd(b, it.s)) {
        rawFlushBatch(b, it.imu);
        rawBatchAdd(b, it.s);
      }
      if (b.n >= RAW_BATCH) rawFlushBatch(b, it.imu);
    }

    const int64_t nowUs = esp_timer_get_time();
    for (uint8_t imu = 0; imu < 2; imu++) {
      if (batches[imu].n > 0 && nowUs - batches[imu].s[0].t_us > RAW_MAX_AGE_US) rawFlushBatch(batches[imu], imu);
    }

    // Scale header per IMU at start and every RAW_HEADER_PERIOD_MS.
    if (rawEnabled && nowUs >= nextHeaderUs) {
      nextHeaderUs = nowUs + (int64_t)RAW_HEADER_PERIOD_MS * 1000;
      for (uint8_t imu = 0; imu < 2; imu++) {
        if (!(imu == 0 ? imu1Ready : imu2Ready)) continue;
        const size_t len = rawEncodeHeader(small, sizeof(small), NODE_ID, (uint8_t)(imu + 1),
                                           IMU_ACCEL_COUNTS_PER_G, IMU_GYRO_COUNTS_PER_DPS,
                                           IMU_SAMPLE_RATE_HZ, IMU_DLPF_HZ, fw, rawDropped(imu),
                                           imuHealth[imu].rdfail, imuHealth[imu].stuck);
        if (len > 0) rawWriteLine(small, len);
      }
    }
  }
}

// ============================================================
// Everything from here to the DASH line is the rear unit only: BLE BMS,
// modem, GNSS, MQTT, flash log, store-and-forward sync, Hall counter and the
// MQTT record. The front node (NODE_FRONT 1) is built without it.
// ============================================================
#if !NODE_FRONT

// ============================================================
// JBD BMS: frame validation and parsing
// ============================================================

// Frame layout: [0]=0xDD  [1]=register  [2]=status  [3]=data length N
//               [4 .. 4+N-1]=data  [4+N,4+N+1]=checksum (big-endian)
//               [4+N+2]=0x77 terminator
// Checksum = (0x10000 - sum(bytes[2..3] + data bytes)) & 0xFFFF, i.e.
// status, length and data, NOT the register byte [1]. Same rule as the
// query: DD A5 03 00 FF FD 77 sums only 03 00 (0x10000 - 3 = 0xFFFD), not
// the A5. Up to v0.5.3 the register byte was included, so every real
// frame failed by exactly 3 (first seen on the vehicle 30 Sep 2026: three
// frames received, all rejected). Rejected frames are now printed raw.
bool validateBmsFrame(const uint8_t* packet, size_t length, uint8_t* outDataLen) {
  if (length < 7) {
    return false;
  }
  if (packet[0] != 0xDD) {
    return false;
  }
  uint8_t dataLen = packet[3];
  size_t expectedLen = 4 + (size_t)dataLen + 2 + 1;
  if (length != expectedLen) {
    return false;
  }
  if (packet[length - 1] != 0x77) {
    return false;
  }

  uint16_t sum = packet[2] + packet[3];
  for (uint8_t i = 0; i < dataLen; i++) {
    sum += packet[4 + i];
  }
  uint16_t computed = (uint16_t)(0x10000 - sum);
  uint16_t frameChecksum = (packet[4 + dataLen] << 8) | packet[4 + dataLen + 1];

  if (computed != frameChecksum) {
    return false;
  }

  *outDataLen = dataLen;
  return true;
}

// Field offsets below were confirmed against the JBD 0x03 basic-info
// register layout in earlier review; only the framing/checksum handling
// around them has changed here.
void parseBmsData(const uint8_t* packet, uint8_t dataLen, bool checksumOk) {
  BmsSample sample;
  sample.timestamp_us = esp_timer_get_time();
  sample.checksum_ok = checksumOk;

  sample.pack_voltage_v = ((packet[4] << 8) | packet[5]) / 100.0f;
  int16_t rawCurrent = (int16_t)((packet[6] << 8) | packet[7]);
  sample.current_a = rawCurrent / 100.0f;
  sample.remaining_ah = ((packet[8] << 8) | packet[9]) / 100.0f;
  sample.nominal_ah = ((packet[10] << 8) | packet[11]) / 100.0f;
  sample.protection_flags = (packet[20] << 8) | packet[21];
  sample.soc_pct = packet[23];

  sample.ntc_count = packet[26];
  sample.mos_temp_c = NAN;
  sample.t1_temp_c = NAN;
  sample.t2_temp_c = NAN;
  size_t idx = 27;
  for (uint8_t i = 0; i < sample.ntc_count && idx + 1 < (size_t)(4 + dataLen); i++) {
    uint16_t rawTemp = (packet[idx] << 8) | packet[idx + 1];
    float tempC = (rawTemp - 2731) / 10.0f;
    if (i == 0) sample.mos_temp_c = tempC;
    else if (i == 1) sample.t1_temp_c = tempC;
    else if (i == 2) sample.t2_temp_c = tempC;
    idx += 2;
  }

  // Secondary sanity check, independent of the checksum: is this reading
  // within a plausible range for a 72 V nominal pack? A checksum-valid but
  // implausible reading is more likely a genuine fault condition than a
  // parsing bug, so this is logged rather than used to discard the sample.
  sample.plausible = sample.pack_voltage_v > 40.0f && sample.pack_voltage_v < 100.0f &&
                      sample.soc_pct <= 100 &&
                      fabsf(sample.current_a) < 300.0f;

  if (!sample.plausible) {
    Serial.printf("[BMS] WARNING: checksum-valid frame outside plausible range - "
                  "V=%.2f I=%.2f SOC=%d\n",
                  sample.pack_voltage_v, sample.current_a, sample.soc_pct);
  }

  if (xQueueSend(bmsQueue, &sample, 0) != pdTRUE) {
    bmsDropped++;
  }

  // Field-by-field, not a whole-struct assignment: see the identical note
  // in RideCharacterizationTask - the compiler-generated struct operator=
  // is not volatile-qualified.
  latestBmsSample.timestamp_us = sample.timestamp_us;
  latestBmsSample.checksum_ok = sample.checksum_ok;
  latestBmsSample.plausible = sample.plausible;
  latestBmsSample.pack_voltage_v = sample.pack_voltage_v;
  latestBmsSample.current_a = sample.current_a;
  latestBmsSample.remaining_ah = sample.remaining_ah;
  latestBmsSample.nominal_ah = sample.nominal_ah;
  latestBmsSample.soc_pct = sample.soc_pct;
  latestBmsSample.protection_flags = sample.protection_flags;
  latestBmsSample.mos_temp_c = sample.mos_temp_c;
  latestBmsSample.t1_temp_c = sample.t1_temp_c;
  latestBmsSample.t2_temp_c = sample.t2_temp_c;
  latestBmsSample.ntc_count = sample.ntc_count;

  Serial.printf("[BMS] V=%.2fV I=%.2fA SOC=%d%% cap=%.2f/%.2fAh flags=0x%04X "
                "mos=%.1fC t1=%.1fC t2=%.1fC%s\n",
                sample.pack_voltage_v, sample.current_a, sample.soc_pct,
                sample.remaining_ah, sample.nominal_ah, sample.protection_flags,
                sample.mos_temp_c, sample.t1_temp_c, sample.t2_temp_c,
                checksumOk ? "" : " [CHECKSUM FAIL]");
}

// Reassembles notification fragments and hands a complete frame to the
// parser once the declared length (packet[3]) says it is complete -
// replaces the original "ends with 0x77 and length>=35" heuristic, which
// could be fooled by 0x77 appearing inside the data payload itself.
static void bmsNotifyCallback(BLERemoteCharacteristic* characteristic, uint8_t* data,
                              size_t length, bool isNotify) {
  if (bmsRxIndex + length >= BMS_RX_BUFFER_SIZE) {
    bmsRxIndex = 0;
    return;
  }
  memcpy(&bmsRxBuffer[bmsRxIndex], data, length);
  bmsRxIndex += length;

  if (bmsRxBuffer[0] != 0xDD) {
    bmsRxIndex = 0;
    return;
  }
  if (bmsRxIndex < 4) {
    return;  // not enough bytes yet to know the declared data length
  }

  uint8_t dataLen = bmsRxBuffer[3];
  size_t expectedLen = 4 + (size_t)dataLen + 2 + 1;
  if (bmsRxIndex < expectedLen) {
    return;  // frame still incomplete, wait for more fragments
  }

  uint8_t outDataLen = 0;
  if (validateBmsFrame(bmsRxBuffer, bmsRxIndex, &outDataLen)) {
    bmsValidFrames++;
    parseBmsData(bmsRxBuffer, outDataLen, true);
  } else {
    bmsChecksumFailures++;
    Serial.printf("[BMS] frame failed length/checksum validation, discarded (%u bytes):",
                  (unsigned)bmsRxIndex);
    for (size_t i = 0; i < bmsRxIndex; i++) {
      Serial.printf(" %02X", bmsRxBuffer[i]);
    }
    Serial.println();
  }
  bmsRxIndex = 0;
}

class BmsClientCallbacks : public BLEClientCallbacks {
  void onConnect(BLEClient* client) override {}
  void onDisconnect(BLEClient* client) override {
    bmsConnected = false;
    bmsDisconnectCount++;
    Serial.println("[BMS] disconnected");
  }
};

class BmsAdvertisedDeviceCallbacks : public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice advertisedDevice) override {
    // Logged for every device seen, not just the target MAC, so a wrong
    // or out-of-date BMS_MAC_ADDRESS is visible in the log rather than
    // producing silent "never connects" behaviour.
    Serial.printf("[BMS] scan saw: %s (%s)\n",
                  advertisedDevice.getAddress().toString().c_str(),
                  advertisedDevice.haveName() ? advertisedDevice.getName().c_str() : "no name");

    if (advertisedDevice.getAddress().toString() == BMS_MAC_ADDRESS) {
      BLEDevice::getScan()->stop();
      if (bmsAddress != nullptr) {
        delete bmsAddress;
      }
      bmsAddress = new BLEAddress(advertisedDevice.getAddress());
      bmsShouldConnect = true;
    }
  }
};

// Connects using the single persistent bmsClient created in setup() -
// the original implementation called BLEDevice::createClient() on every
// attempt, leaking a client object roughly every 10 s of runtime.
//
// Characteristic lookup deliberately does NOT assume the notify/write
// characteristics live under BMS_SERVICE_UUID (0xff00). Live testing against
// the vehicle's actual pack (2026-09-11) showed connect() succeeding but
// getService(BMS_SERVICE_UUID) returning null, i.e. this unit's GATT server
// does not expose that service UUID even though a companion reference
// implementation (Wireless Charging team's battery_BMS_Data.py, same MAC,
// same characteristic UUIDs) works - because that script (via bleak's
// start_notify/write_gatt_char) searches all services for the characteristic
// UUID directly rather than requiring a specific parent service UUID. This
// searches every discovered service the same way, rather than assuming which
// service the characteristics are nested under.
bool connectToBms() {
  Serial.printf("[BMS] connecting to %s...\n", bmsAddress->toString().c_str());

  if (!bmsClient->connect(*bmsAddress)) {
    Serial.println("[BMS] connect() failed");
    return false;
  }

  std::map<std::string, BLERemoteService*>* services = bmsClient->getServices();
  bmsNotifyChar = nullptr;
  bmsWriteChar = nullptr;
  for (auto& entry : *services) {
    BLERemoteService* service = entry.second;
    BLERemoteCharacteristic* notifyChar = service->getCharacteristic(BMS_NOTIFY_CHAR_UUID);
    BLERemoteCharacteristic* writeChar = service->getCharacteristic(BMS_WRITE_CHAR_UUID);
    if (notifyChar != nullptr && writeChar != nullptr) {
      bmsNotifyChar = notifyChar;
      bmsWriteChar = writeChar;
      Serial.printf("[BMS] found characteristics under service %s\n", entry.first.c_str());
      break;
    }
  }
  if (bmsNotifyChar == nullptr || bmsWriteChar == nullptr) {
    Serial.println("[BMS] characteristic(s) not found in any service, disconnecting");
    bmsClient->disconnect();
    return false;
  }

  if (bmsNotifyChar->canNotify()) {
    bmsNotifyChar->registerForNotify(bmsNotifyCallback);
  }

  bmsRxIndex = 0;
  return true;
}

// Holds one persistent connection and polls on a timer, rather than the
// original connect/query/wait-4s/disconnect cycle every 10 s. Reconnects
// only in response to BmsClientCallbacks::onDisconnect(), not on a fixed
// timer, and read-only throughout: the write characteristic is used only
// to send the basic-info query, never a configuration or control command.
void BmsTask(void* pvParameters) {
  BLEDevice::init("");
  bmsClient = BLEDevice::createClient();
  bmsClient->setClientCallbacks(new BmsClientCallbacks());

  BLEScan* scan = BLEDevice::getScan();
  scan->setAdvertisedDeviceCallbacks(new BmsAdvertisedDeviceCallbacks());
  scan->setInterval(1349);
  scan->setWindow(449);
  scan->setActiveScan(true);
  scan->start(5, false);

  TickType_t lastQuery = 0;

  for (;;) {
    if (bmsShouldConnect && !bmsConnected) {
      bmsShouldConnect = false;
      if (connectToBms()) {
        bmsConnected = true;
        bmsReconnectCount++;
        Serial.println("[BMS] connected");
      } else {
        // Retry the scan rather than looping connect attempts tightly.
        BLEDevice::getScan()->start(5, false);
      }
    }

    if (bmsConnected && bmsWriteChar != nullptr &&
        (xTaskGetTickCount() - lastQuery) >= pdMS_TO_TICKS(BMS_QUERY_INTERVAL_MS)) {
      lastQuery = xTaskGetTickCount();
      bmsWriteChar->writeValue((uint8_t*)BMS_QUERY_COMMAND, sizeof(BMS_QUERY_COMMAND), false);
    }

    if (!bmsConnected && !bmsShouldConnect) {
      // Not connected and not currently mid-scan: keep looking. This must
      // NOT be gated on bmsAddress being set - that only becomes true once
      // the target has already been found once, which would make retry
      // scanning depend on having already succeeded.
      BLEDevice::getScan()->start(5, false);
      vTaskDelay(pdMS_TO_TICKS(6000));
    }

    vTaskDelay(pdMS_TO_TICKS(200));
  }
}

// ============================================================
// Modem / GNSS task - unchanged from v0.3.0, already verified working
// (live AT/OK handshake confirmed on hardware).
// ============================================================
// ============================================================
// GNSS response parsing
// ============================================================

// Splits `raw` on commas into up to `maxTokens` entries. Empty fields
// (consecutive commas, common in a no-fix response) are preserved as
// empty strings so field *position* stays meaningful even when the
// module omits a value.
int splitFields(const String& raw, String* tokens, int maxTokens) {
  int count = 0;
  int start = 0;
  while (count < maxTokens) {
    int comma = raw.indexOf(',', start);
    if (comma == -1) {
      tokens[count++] = raw.substring(start);
      break;
    }
    tokens[count++] = raw.substring(start, comma);
    start = comma + 1;
  }
  return count;
}

// Converts NMEA ddmm.mmmmmm / dddmm.mmmmmm format to decimal degrees.
float nmeaToDecimalDegrees(const String& value) {
  if (value.length() == 0) {
    return NAN;
  }
  float raw = value.toFloat();
  int degrees = static_cast<int>(raw / 100);
  float minutes = raw - (degrees * 100);
  return degrees + (minutes / 60.0f);
}

// Field layout CONFIRMED against a real fix on 29 Sep 2026 (rooftop, 3D
// fix after 51 s, log BenchTest/logs/2026-09-29_gnss_rooftop.log). A with-fix
// reply from this module is, for example:
//   +CGNSSINFO: 3,15,,09,02,33.9801178,S,18.4654350,E,290926,214739.00,82.4,0.000,69.44,1.68,0.86,1.44
// i.e. <mode>,<GPS sats>,<GLONASS sats>,<BeiDou sats>,<Galileo sats>,
//      <lat>,<N/S>,<lon>,<E/W>,<date ddmmyy>,<UTC hhmmss.ss>,<alt m>,
//      <speed>,<course>,<PDOP>,<HDOP>,<VDOP>
// 17 fields, with latitude and longitude in DECIMAL degrees (not NMEA
// ddmm.mmmm). The manual (v1.09) documents a 16-field variant without the
// Galileo count, and the earlier no-fix reply had 9 empty fields, so the
// satellite block is not a fixed length. The parser therefore locates the
// hemisphere letter and reads every other field relative to it, which fits
// all of these layouts. The previous parser assumed the 9-field layout was
// <mode>,<lat>,... and read the satellite counts as the position.
//
// Speed units are still NOT confirmed: the fix was stationary (0.000). The
// manual gives knots; check against a known speed on the road test before
// the speed-normalised index is trusted.
// True if v is digits with exactly one decimal point and at least
// minDecimals digits after it (a value with dropped characters fails).
static bool gnssDecimalShape(const String& v, int maxInt, int minDecimals) {
  int dot = v.indexOf('.');
  if (dot < 1 || dot > maxInt || v.indexOf('.', dot + 1) >= 0) return false;
  if ((int)v.length() - dot - 1 < minDecimals) return false;
  for (int i = 0; i < (int)v.length(); i++) {
    if (i != dot && !isDigit(v[i])) return false;
  }
  return true;
}

static bool gnssValidCoordinate(const String& v, float limit, float* out) {
  if (v.length() == 0) return false;
  float x = v.toFloat();
  // Decimal degrees on this module; accept NMEA ddmm.mmmm too, which some
  // firmware versions send (a value above the limit can only be ddmm).
  if (x > limit) x = nmeaToDecimalDegrees(v);
  if (!(x >= 0.0f && x <= limit)) return false;
  *out = x;
  return true;
}

bool parseGnssInfo(const String& raw, GnssFix* out) {
  int start = raw.indexOf("+CGNSSINFO:");
  if (start == -1) {
    return false;
  }
  String body = raw.substring(start + strlen("+CGNSSINFO:"));
  int eol = body.indexOf('\n');
  if (eol >= 0) body = body.substring(0, eol);
  body.trim();

  const int kMaxFields = 24;
  String t[kMaxFields];
  int n = splitFields(body, t, kMaxFields);
  if (n < 9) {
    Serial.printf("[GNSS] unexpected field count (%d, expected at least 9) - raw: %s\n", n, body.c_str());
    return false;
  }

  out->timestamp_us = esp_timer_get_time();
  out->fix_mode = t[0].length() ? t[0].toInt() : 0;
  out->valid = false;
  out->latitude_deg = out->longitude_deg = out->altitude_m = NAN;
  out->speed_reported = out->course_deg = out->hdop = NAN;
  out->satellites = 0;
  out->utc_date = 0;
  out->utc_time = NAN;

  if (out->fix_mode == 0) {
    return true;  // well-formed no-fix reply
  }

  // Find the latitude hemisphere; latitude is the field before it.
  int h = -1;
  for (int i = 2; i < n; i++) {
    if (t[i] == "N" || t[i] == "S") { h = i; break; }
  }
  if (h < 2 || h + 2 >= n || !(t[h + 2] == "E" || t[h + 2] == "W")) {
    Serial.printf("[GNSS] fix reply without a readable position - raw: %s\n", body.c_str());
    return true;  // counts as no usable fix, but the reply itself parsed
  }

  // A with-fix reply is 16 to 18 fields (with or without the Galileo count,
  // and with or without one trailing field seen while a fix settles, when
  // the course is empty) and has the hemisphere at index 6 or 7. Anything else, or a coordinate,
  // date or time with the wrong shape, is treated as a damaged reply.
  bool shapeOk = (h == 6 || h == 7) && (n == h + 11 || n == h + 12) &&
                 gnssDecimalShape(t[h - 1], 2, 6) && gnssDecimalShape(t[h + 1], 3, 6) &&
                 t[h + 3].length() == 6 && gnssDecimalShape(t[h + 4], 6, 1);
  if (!shapeOk) {
    Serial.printf("[GNSS] damaged fix reply ignored - raw: %s\n", body.c_str());
    return true;
  }

  float lat, lon;
  if (!gnssValidCoordinate(t[h - 1], 90.0f, &lat) || !gnssValidCoordinate(t[h + 1], 180.0f, &lon)) {
    Serial.printf("[GNSS] coordinates out of range - raw: %s\n", body.c_str());
    return true;
  }
  out->latitude_deg = (t[h] == "S") ? -lat : lat;
  out->longitude_deg = (t[h + 2] == "W") ? -lon : lon;

  // A dropped digit can still leave a well-shaped number (33.98 read as
  // 3.98). Reject a fix that is further from the previous accepted fix than
  // 100 m/s (360 km/h) allows for the time between them. The first fix, and
  // one after a gap of more than 60 s, are accepted without this check.
  static bool havePrev = false;
  static float prevLat = 0, prevLon = 0;
  static int64_t prevUs = 0;
  if (havePrev) {
    float dt = (out->timestamp_us - prevUs) / 1e6f;
    float dN = (out->latitude_deg - prevLat) * 111320.0f;
    float dE = (out->longitude_deg - prevLon) * 111320.0f * cosf(prevLat * (float)M_PI / 180.0f);
    float jump = sqrtf(dN * dN + dE * dE);
    if (dt < 60.0f && jump > 100.0f * (dt > 1.0f ? dt : 1.0f)) {
      Serial.printf("[GNSS] implausible jump of %.0f m in %.1f s ignored - raw: %s\n", jump, dt, body.c_str());
      out->latitude_deg = out->longitude_deg = NAN;
      return true;
    }
  }
  havePrev = true;
  prevLat = out->latitude_deg;
  prevLon = out->longitude_deg;
  prevUs = out->timestamp_us;

  int sats = 0;
  for (int i = 1; i < h - 1; i++) {
    if (t[i].length()) sats += t[i].toInt();
  }
  out->satellites = sats > 255 ? 255 : sats;
  if (h + 3 < n && t[h + 3].length()) out->utc_date = (uint32_t)t[h + 3].toInt();
  if (h + 4 < n && t[h + 4].length()) out->utc_time = t[h + 4].toFloat();
  if (h + 5 < n && t[h + 5].length()) out->altitude_m = t[h + 5].toFloat();
  if (h + 6 < n && t[h + 6].length()) out->speed_reported = t[h + 6].toFloat();
  if (h + 7 < n && t[h + 7].length()) out->course_deg = t[h + 7].toFloat();
  if (h + 9 < n && t[h + 9].length()) out->hdop = t[h + 9].toFloat();
  out->valid = true;
  return true;
}

// ============================================================
// Device UTC from GNSS (v0.7.4), for the record's utc_ms and the server's
// end-to-end latency figure. Kept as an offset between UTC and the ESP32's
// own esp_timer clock, set from each fix's date and time. +CGNSSINFO reports
// the time of the last fix, which is at or before the poll, so the largest
// offset seen is the freshest: a new fix replaces the anchor when its offset
// is larger (by under 5 s; anything bigger is treated as a glitch), or when
// the anchor is over 10 minutes old (clock drift). Uncertainty is about the
// modem's fix-to-report delay, under about 1 s (not measured). Without a fix
// for 6 hours, utc_ms goes back to null rather than trusting the drift.
// ============================================================
bool utcAnchorValid = false;
int64_t utcOffsetMs = 0;      // UTC ms minus esp_timer ms
int64_t utcAnchorSetUs = 0;
#define UTC_ANCHOR_REFRESH_US (600LL * 1000000LL)
#define UTC_ANCHOR_MAX_AGE_US (6LL * 3600LL * 1000000LL)

void updateUtcAnchor(const GnssFix& fix) {
  if (!fix.valid || fix.utc_date == 0 || isnan(fix.utc_time)) return;
  const int64_t epochMs = syncGnssUtcToEpochMs(fix.utc_date, (double)fix.utc_time);
  if (epochMs < 0) return;
  const int64_t offset = epochMs - fix.timestamp_us / 1000;
  const bool stale = (fix.timestamp_us - utcAnchorSetUs) > UTC_ANCHOR_REFRESH_US;
  if (!utcAnchorValid || stale || (offset > utcOffsetMs && offset - utcOffsetMs < 5000)) {
    if (!utcAnchorValid) Serial.printf("[UTC] device time set from GNSS: %lld ms\n", (long long)epochMs);
    utcOffsetMs = offset;
    utcAnchorSetUs = fix.timestamp_us;
    utcAnchorValid = true;
  }
}

// UTC in ms for esp_timer time nowUs, or -1 when not known.
int64_t deviceUtcMs(int64_t nowUs) {
  if (!utcAnchorValid || (nowUs - utcAnchorSetUs) > UTC_ANCHOR_MAX_AGE_US) return -1;
  return nowUs / 1000 + utcOffsetMs;
}

// Polls AT+CGNSSINFO, parses the response, logs a one-line summary
// (instead of the raw dump used elsewhere), and enqueues the result for
// later consumers (local logging / the unified telemetry packet).
void pollAndParseGnss() {
  Serial1.println("AT+CGNSSINFO");

  String response;
  unsigned long startWait = millis();
  while (millis() - startWait < 2000) {
    while (Serial1.available()) {
      response += static_cast<char>(Serial1.read());
    }
    if (response.indexOf("OK") >= 0 || response.indexOf("ERROR") >= 0) {
      break;
    }
    vTaskDelay(pdMS_TO_TICKS(1));
  }

  if (response.length() == 0) {
    Serial.println("[GNSS] poll timeout");
    return;
  }

  if (gnssPrintRaw) {
    int r = response.indexOf("+CGNSSINFO:");
    if (r >= 0) {
      int e = response.indexOf('\n', r);
      String line = response.substring(r, e >= 0 ? e : response.length());
      line.trim();
      Serial.printf("[GNSS] raw %s\n", line.c_str());
    }
  }

  GnssFix fix;
  if (parseGnssInfo(response, &fix)) {
    if (fix.valid) {
      Serial.printf("[GNSS] fix mode=%d lat=%.6f lon=%.6f alt=%.1fm speed=%.3f sats=%u hdop=%.2f\n",
                    fix.fix_mode, fix.latitude_deg, fix.longitude_deg,
                    fix.altitude_m, fix.speed_reported, (unsigned)fix.satellites, fix.hdop);
    } else {
      Serial.printf("[GNSS] no fix yet (mode=%d)\n", fix.fix_mode);
    }

    latestGnssFix.timestamp_us = fix.timestamp_us;
    latestGnssFix.valid = fix.valid;
    latestGnssFix.fix_mode = fix.fix_mode;
    latestGnssFix.latitude_deg = fix.latitude_deg;
    latestGnssFix.longitude_deg = fix.longitude_deg;
    latestGnssFix.altitude_m = fix.altitude_m;
    latestGnssFix.speed_reported = fix.speed_reported;
    latestGnssFix.course_deg = fix.course_deg;
    latestGnssFix.hdop = fix.hdop;
    latestGnssFix.satellites = fix.satellites;
    latestGnssFix.utc_date = fix.utc_date;
    latestGnssFix.utc_time = fix.utc_time;
    updateUtcAnchor(fix);

    // Queue is not expected to fill at a 3 s poll rate, but don't block
    // the modem task if it somehow does.
    if (xQueueSend(gnssQueue, &fix, 0) != pdTRUE) {
      Serial.println("[GNSS] queue full, dropping fix");
    }
  } else {
    Serial.print("[GNSS] unparsed raw response: ");
    Serial.println(response);
  }
}

extern volatile bool mqttConnected;      // defined with the MQTT code below
extern unsigned long mqttNextAttemptMs;

// Reads modem output until a line containing `tag` has fully arrived, or ERROR,
// or the timeout. Returns true if the tag line arrived. MQTT loss URCs that turn
// up while waiting are still honoured, since this read consumes them.
bool readModemUntil(String& response, const char* tag, unsigned long timeoutMs) {
  unsigned long start = millis();
  while (millis() - start < timeoutMs) {
    while (Serial1.available()) {
      response += static_cast<char>(Serial1.read());
    }
    int t = response.indexOf(tag);
    if (t >= 0 && response.indexOf('\n', t) >= 0) break;
    if (response.indexOf("ERROR") >= 0) break;
    vTaskDelay(pdMS_TO_TICKS(5));
  }
  if (response.indexOf("+CMQTTCONNLOST") >= 0 || response.indexOf("+CMQTTNONET") >= 0) {
    mqttConnected = false;
    mqttNextAttemptMs = millis() + 5000;
  }
  return response.indexOf(tag) >= 0;
}

// Downloads and injects assisted-GNSS data (AT+CAGPS). Typically a few seconds.
bool requestAgps() {
  agpsAttempts++;
  unsigned long t0 = millis();
  Serial1.println("AT+CAGPS");
  String r;
  bool got = readModemUntil(r, "+AGPS:", 30000);
  agpsOk = got && r.indexOf("success") >= 0;
  Serial.printf("[AGPS] %s after %lu ms (attempt %u)\n",
                agpsOk ? "assistance data loaded" : (got ? "server refused" : "no reply"),
                millis() - t0, (unsigned)agpsAttempts);
  return agpsOk;
}

// Polls the cell-tower position (AT+CLBS=4):
//   +CLBS: 0,-33.980381,18.465xxx,550,2026/10/10,22:35:42
// <code>,<lat>,<lon>,<accuracy m>,<date>,<time>; code 0 is success.
bool pollCellLocation() {
  unsigned long t0 = millis();
  Serial1.println("AT+CLBS=4");
  String r;
  if (!readModemUntil(r, "+CLBS:", 25000)) {
    Serial.printf("[CELLPOS] no reply after %lu ms\n", millis() - t0);
    return false;
  }
  int s = r.indexOf("+CLBS:") + 6;
  int e = r.indexOf('\n', s);
  String body = r.substring(s, e >= 0 ? e : r.length());
  body.trim();
  float f[4] = {NAN, NAN, NAN, NAN};
  int code = -1, from = 0;
  for (int k = 0; k < 4; k++) {
    int c = body.indexOf(',', from);
    String tok = body.substring(from, c >= 0 ? c : body.length());
    if (k == 0) code = tok.toInt(); else f[k] = tok.toFloat();
    if (c < 0) break;
    from = c + 1;
  }
  const bool ok = code == 0 && isfinite(f[1]) && isfinite(f[2]) && f[1] != 0.0f && f[2] != 0.0f &&
                  fabsf(f[1]) <= 90.0f && fabsf(f[2]) <= 180.0f;
  if (!ok) {
    Serial.printf("[CELLPOS] not available (%s) after %lu ms\n", body.c_str(), millis() - t0);
    return false;
  }
  latestCellLoc.timestamp_us = esp_timer_get_time();
  latestCellLoc.latitude_deg = f[1];
  latestCellLoc.longitude_deg = f[2];
  latestCellLoc.accuracy_m = isfinite(f[3]) ? f[3] : NAN;
  latestCellLoc.valid = true;
  Serial.printf("[CELLPOS] lat=%.6f lon=%.6f accuracy=%.0f m (%lu ms)\n",
                f[1], f[2], f[3], millis() - t0);
  return true;
}

void sendGnssCommand(const char* command) {
  Serial1.println(command);

  String response;
  unsigned long startWait = millis();
  while (millis() - startWait < 2000) {
    while (Serial1.available()) {
      response += static_cast<char>(Serial1.read());
    }
    if (response.indexOf("OK") >= 0 || response.indexOf("ERROR") >= 0) {
      break;
    }
    vTaskDelay(pdMS_TO_TICKS(1));
  }

  if (response.length() == 0) {
    Serial.println("GNSS poll timeout");
    return;
  }

  Serial.println("--- GNSS Telemetry ---");
  Serial.print(response);
}

// ============================================================
// MQTT over cellular, using the A7670X's native AT+CMQTT command set
// (the same family as SIMCom's other modems, e.g. SIM7600/SIM7070). This
// avoids needing a TCP/IP socket library on the ESP32 side - the modem
// itself handles the MQTT session once told to.
//
// PLACEHOLDER credentials/broker: deliberately NOT the existing Tukzie
// vac-work team's Mosquitto broker credentials, even though this project
// has read access to that team's documentation. That document explicitly
// states its credentials must not be shared with an LLM, so they are not
// embedded here. Replace MQTT_BROKER_HOST (and the username/password
// fields, if the target broker requires them) with a real broker before
// relying on this - either the student's own test broker, or the real
// Tukzie broker details obtained directly (not through this codebase) if
// integrating with that existing backend is the intended target.
//
// Runs entirely inside ModemTask, not a separate task: Serial1 (the
// modem UART) is only ever touched from ModemTask elsewhere in this file
// (GNSS polling, the AT pass-through loop), and a second task sending AT
// commands on the same UART concurrently would interleave and corrupt
// both command streams. Keeping MQTT in the same task avoids that.
// ============================================================
#define MQTT_CLIENT_INDEX 0
// test.mosquitto.org: public, free, no-auth broker - used here only to
// prove the AT+CMQTT* sequence and cellular path work end-to-end. Not a
// destination for real vehicle telemetry; replace before any real use.
// Real broker details live only in include/mqtt_secrets.h on the student's machine (git-ignored, never
// committed and never shown to an AI assistant); copy include/mqtt_secrets.example.h to start it. Without
// that file the unit keeps using the public test broker below.
#if __has_include("mqtt_secrets.h")
#include "mqtt_secrets.h"
#endif
#ifndef MQTT_BROKER_HOST
#define MQTT_BROKER_HOST "test.mosquitto.org"
#endif
#ifndef MQTT_BROKER_PORT
#define MQTT_BROKER_PORT 1883
#endif
#define MQTT_CLIENT_ID "sw7-esp32-telemetry"
#ifndef MQTT_USERNAME
#define MQTT_USERNAME ""  // empty if the broker does not require auth
#endif
#ifndef MQTT_PASSWORD
#define MQTT_PASSWORD ""
#endif
#ifndef MQTT_TOPIC
#define MQTT_TOPIC "sw7/telemetry"
#endif
#define MQTT_KEEPALIVE_S 60
#define MQTT_PUBLISH_INTERVAL_MS 10000
// Position in the published record (v0.7.5): off by default, since the
// default broker is public. mqttPublish() removes "lat", "lon" and "acc_m"
// from every payload (include/payload_privacy.h); the local log and the DASH
// line keep them. Set to 1 (build flag, or in mqtt_secrets.h) only for a
// private broker.
#ifndef MQTT_INCLUDE_POSITION
#define MQTT_INCLUDE_POSITION 0
#endif

volatile bool mqttConnected = false;
volatile uint32_t mqttPublishCount = 0;
volatile uint32_t mqttPublishFailures = 0;
uint32_t mqttConsecutivePublishFailures = 0;
uint32_t mqttConnectAttempts = 0;

// Reconnect with backoff: first retry 30 s after a failure, doubling up to
// 5 min, reset on success. Three failed publishes in a row, or the modem's
// +CMQTTCONNLOST / +CMQTTNONET URC, mark the session as lost.
#define MQTT_RETRY_MIN_MS 30000UL
#define MQTT_RETRY_MAX_MS 300000UL
#define MQTT_MAX_CONSECUTIVE_PUB_FAILURES 3
unsigned long mqttRetryDelayMs = MQTT_RETRY_MIN_MS;
unsigned long mqttNextAttemptMs = 0;

// Sends one AT command and waits up to timeoutMs for a line containing
// expectSubstring. Returns the full accumulated response via outResponse
// (may be nullptr if not needed) and true/false for whether expectSubstring
// was seen. Mirrors the existing busy-wait style already used by
// pollAndParseGnss()/sendGnssCommand() elsewhere in this file, kept as a
// separate function rather than refactoring those (which already work and
// are validated) to share it.
bool mqttSendCommand(const String& command, const char* expectSubstring, unsigned long timeoutMs, String* outResponse = nullptr) {
  Serial1.println(command);

  String response;
  unsigned long startWait = millis();
  bool found = false;
  while (millis() - startWait < timeoutMs) {
    while (Serial1.available()) {
      response += static_cast<char>(Serial1.read());
    }
    if (response.indexOf(expectSubstring) >= 0) {
      found = true;
      break;
    }
    if (response.indexOf("ERROR") >= 0) {
      break;
    }
    vTaskDelay(pdMS_TO_TICKS(1));
  }

  if (outResponse != nullptr) *outResponse = response;
  return found;
}

// For the commands whose real outcome arrives after OK as a result line
// (AT+CMQTTSTART, AT+CMQTTCONNECT, AT+CMQTTPUB, AT+CMQTTDISC): the SIMCom
// A76XX manual v1.09 (section 18.2) gives both success and failure as
// "OK" followed by "+CMQTTxxx: [<client>,]<err>", where err 0 is success.
// OK alone therefore proves nothing. Sends `command` (unless empty), waits
// for a complete line starting with `resultPrefix`, and returns the last
// number on it through *err. Returns false on ERROR or timeout.
bool mqttAwaitResult(const String& command, const char* resultPrefix, unsigned long timeoutMs,
                     int* err, String* outResponse = nullptr) {
  if (command.length() > 0) Serial1.println(command);
  String response;
  unsigned long startWait = millis();
  bool got = false;
  while (millis() - startWait < timeoutMs) {
    while (Serial1.available()) {
      response += static_cast<char>(Serial1.read());
    }
    int at = response.indexOf(resultPrefix);
    if (at >= 0) {
      int eol = response.indexOf('\n', at);
      if (eol >= 0) {
        String line = response.substring(at + strlen(resultPrefix), eol);
        line.trim();
        int comma = line.lastIndexOf(',');
        *err = (comma >= 0 ? line.substring(comma + 1) : line).toInt();
        got = true;
        break;
      }
    } else if (response.indexOf("ERROR") >= 0) {
      break;
    }
    vTaskDelay(pdMS_TO_TICKS(1));
  }
  if (outResponse != nullptr) *outResponse = response;
  return got;
}

// Clean shutdown in the order the manual requires (AT+CMQTTREL "must be
// called after AT+CMQTTDISC and before AT+CMQTTSTOP"), so a reconnect
// starts from a known state. Each step may fail harmlessly when that stage
// was never reached; results are ignored.
void mqttTeardown() {
  int err = 0;
  String resp;
  mqttAwaitResult(String("AT+CMQTTDISC=") + MQTT_CLIENT_INDEX + ",60", "+CMQTTDISC: ", 5000, &err, &resp);
  mqttSendCommand(String("AT+CMQTTREL=") + MQTT_CLIENT_INDEX, "OK", 3000, &resp);
  mqttAwaitResult("AT+CMQTTSTOP", "+CMQTTSTOP: ", 5000, &err, &resp);
  mqttConnected = false;
}

// Runs the CMQTTSTART/ACCQ/CONNECT sequence once. Returns false (and
// leaves mqttConnected false) on the first step that fails, logging which
// step failed rather than failing silently.
bool mqttConnect() {
  String resp;
  int err = -1;
  mqttConnectAttempts++;

  // Per the manual, ERROR here means the service was already started,
  // which is fine; a +CMQTTSTART line with a non-zero code is a failure.
  bool gotStart = mqttAwaitResult("AT+CMQTTSTART", "+CMQTTSTART: ", 12000, &err, &resp);
  if (gotStart && err != 0) {
    Serial.printf("[MQTT] CMQTTSTART failed, code %d\n", err);
    return false;
  }
  if (!gotStart && resp.indexOf("ERROR") < 0) {
    Serial.print("[MQTT] CMQTTSTART gave no result: ");
    Serial.println(resp);
    return false;
  }

  String acqCmd = String("AT+CMQTTACCQ=") + MQTT_CLIENT_INDEX + ",\"" + MQTT_CLIENT_ID + "\"";
  if (!mqttSendCommand(acqCmd, "OK", 5000, &resp)) {
    Serial.print("[MQTT] CMQTTACCQ failed: ");
    Serial.println(resp);
    return false;
  }

  String connCmd = String("AT+CMQTTCONNECT=") + MQTT_CLIENT_INDEX + ",\"tcp://" +
                    MQTT_BROKER_HOST + ":" + MQTT_BROKER_PORT + "\"," +
                    MQTT_KEEPALIVE_S + ",1";
  if (strlen(MQTT_USERNAME) > 0) {
    connCmd += String(",\"") + MQTT_USERNAME + "\",\"" + MQTT_PASSWORD + "\"";
  }
  if (!mqttAwaitResult(connCmd, "+CMQTTCONNECT: ", 30000, &err, &resp)) {
    Serial.print("[MQTT] CMQTTCONNECT gave no result: ");
    Serial.println(resp);
    return false;
  }
  if (err != 0) {
    Serial.printf("[MQTT] CMQTTCONNECT failed, code %d (manual section 18.3)\n", err);
    return false;
  }

  Serial.println("[MQTT] Connected.");
  mqttConnected = true;
  mqttConsecutivePublishFailures = 0;
  return true;
}

// Publishes one payload to MQTT_TOPIC. Each of CMQTTTOPIC/CMQTTPAYLOAD
// expects the raw bytes to follow the command, not as a quoted argument -
// this is the standard SIMCom CMQTT pattern, distinct from the simple
// single-line AT commands used elsewhere in this file.
bool mqttPublish(const String& record) {
  if (!mqttConnected) return false;
#if MQTT_INCLUDE_POSITION
  const String& payload = record;
#else
  // Static: only ModemTask publishes, and its stack is 4 KB.
  static char scrubbed[1280];
  if (scrubPositionJson(record.c_str(), scrubbed, sizeof(scrubbed)) == 0) {
    Serial.println("[MQTT] record too long to clean of position, not published");
    return false;
  }
  const String payload(scrubbed);
#endif

  String resp;
  String topicCmd = String("AT+CMQTTTOPIC=") + MQTT_CLIENT_INDEX + "," + String(strlen(MQTT_TOPIC));
  if (!mqttSendCommand(topicCmd, ">", 3000, &resp)) {
    Serial.println("[MQTT] CMQTTTOPIC did not prompt for data");
    return false;
  }
  Serial1.print(MQTT_TOPIC);
  if (!mqttSendCommand("", "OK", 3000, &resp)) {
    Serial.print("[MQTT] topic write failed: ");
    Serial.println(resp);
    return false;
  }

  String payloadCmd = String("AT+CMQTTPAYLOAD=") + MQTT_CLIENT_INDEX + "," + String(payload.length());
  if (!mqttSendCommand(payloadCmd, ">", 3000, &resp)) {
    Serial.println("[MQTT] CMQTTPAYLOAD did not prompt for data");
    return false;
  }
  Serial1.print(payload);
  if (!mqttSendCommand("", "OK", 3000, &resp)) {
    Serial.print("[MQTT] payload write failed: ");
    Serial.println(resp);
    return false;
  }

  String pubCmd = String("AT+CMQTTPUB=") + MQTT_CLIENT_INDEX + ",1,60";
  int err = -1;
  if (!mqttAwaitResult(pubCmd, "+CMQTTPUB: ", 15000, &err, &resp) || err != 0) {
    Serial.printf("[MQTT] CMQTTPUB failed, code %d: ", err);
    Serial.println(resp);
    mqttPublishFailures++;
    return false;
  }

  mqttPublishCount++;
  return true;
}

// Shared by live and replay publishes: three failures in a row mark the
// session as lost, so the reconnect logic takes over.
void mqttNotePublishResult(bool ok) {
  if (ok) {
    mqttConsecutivePublishFailures = 0;
    return;
  }
  if (++mqttConsecutivePublishFailures >= MQTT_MAX_CONSECUTIVE_PUB_FAILURES) {
    Serial.println("[MQTT] 3 publishes failed in a row, treating the session as lost.");
    mqttConnected = false;
    mqttNextAttemptMs = millis();
  }
}

// ============================================================
// Local telemetry logging.
//
// The project brief requires telemetry to be "logged locally and
// transmitted via a cellular module... to a central database" - two
// separate obligations, not one. Every telemetry sample is appended here
// unconditionally, regardless of MQTT connection state, so a genuine local
// record exists even through a connectivity outage (this is also the
// evidence this project's narrowed gap claim G3 rests on: that store-and-
// forward buffering under intermittent uplink is addressed, not merely
// assumed).
//
// Since v0.7.4 every line carries dev, boot and seq, and the sync section
// below replays the lines the broker has not acknowledged after an outage.
// The file is still a single append-only file with a size cap that deletes
// it when exceeded; unacknowledged records deleted that way are counted as
// lost in the sync ledger, not skipped silently.
// ============================================================
// Store-and-forward sync state (v0.7.4). The bookkeeping itself is the pure
// code in include/sync_ledger.h (model and state machine described there,
// tested on the laptop by test_host/test_sync_ledger.cpp); this file only
// feeds it and keeps it in NVS. Everything here runs on ModemTask (core 0),
// the only task that touches the modem UART and the log file.
//
// NVS namespace "sw7sync":
//   boot    boot counter, +1 at every boot (the record's "boot")
//   seqblk  seq numbers below this may have been used. At boot the unit
//           starts at seqblk and reserves the next SYNC_SEQ_BLOCK, so NVS is
//           written once per 64 records (about 11 min), not per record.
//   acked   ledger watermark, and lost, the lost count: saved together after
//           each log flush (about once a minute, next to the flush's own flash
//           write) or, with logging off, every 60 s when changed. After a
//           power cut up to a minute of acknowledgements is forgotten, so a few
//           records are sent twice; the server stores them once.
// ============================================================
#define SYNC_SEQ_BLOCK 64
#define SYNC_REPLAY_INTERVAL_MS 300      // at most about 3 replayed records per second
#define SYNC_REPLAY_RETRY_MS 5000        // after a failed replay publish
#define SYNC_REPLAY_LINES_PER_PASS 25    // log lines read per pass, bounds the time per pass
#define SYNC_PERSIST_INTERVAL_MS 60000UL // only used while logging is off

Preferences syncPrefs;
SyncLedger syncLedger;
bool syncReady = false;
uint32_t syncBootId = 0;
uint32_t syncBootFirstSeq = 0;
uint32_t syncNextSeq = 0;
uint32_t syncSeqReservedTo = 0;
uint32_t syncLastLoggedAtBoot = 0;
uint32_t syncLastSavedAcked = 0, syncLastSavedLost = 0;
unsigned long syncLastSaveMs = 0;
uint32_t syncBufferFirstSeq = 0;   // seq of the first line waiting in the RAM log buffer
uint32_t syncReplayOffset = 0;     // byte offset of the next log line to examine
uint32_t syncReplayPrevBoot = 0;   // boot of the last seq-carrying line examined
unsigned long syncReplayNextMs = 0;
uint32_t syncReplayFailures = 0;
uint32_t syncLiveAcked = 0;        // this boot

void syncSave(bool force) {
  if (!syncReady) return;
  if (!force && syncLedger.acked == syncLastSavedAcked && syncLedger.lost == syncLastSavedLost) return;
  syncPrefs.putUInt("acked", syncLedger.acked);
  syncPrefs.putUInt("lost", syncLedger.lost);
  syncLastSavedAcked = syncLedger.acked;
  syncLastSavedLost = syncLedger.lost;
  syncLastSaveMs = millis();
}

uint32_t syncAssignSeq() {
  uint32_t s = syncNextSeq++;
  if (syncNextSeq >= syncSeqReservedTo) {
    syncSeqReservedTo += SYNC_SEQ_BLOCK;
    syncPrefs.putUInt("seqblk", syncSeqReservedTo);
  }
  return s;
}

#define LOCAL_LOG_PATH "/telemetry.log"
#define LOCAL_LOG_MAX_BYTES (3 * 1024 * 1024)  // stay under the ~3.375MB
                                                 // LittleFS partition with margin
bool localLogReady = false;
// Runtime switch (serial command "!log off" / "!log on"), for testing
// whether the periodic acquisition stalls come from these flash writes.
volatile bool localLogEnabled = true;
uint32_t localLogAppendCount = 0;
uint32_t localLogAppendFailures = 0;

// Lines are collected in RAM and written to flash in one go about once a
// minute (v0.6.0). Every flash write or erase suspends the cache on both
// cores, so code running from flash, including the IMU tasks, pauses; the
// v0.5.0 bench test measured 33 to 40 ms acquisition gaps at every 10 s
// append, and 5.9 ms worst case with logging off. One write per minute
// gives the same pause about six times less often, and the file size is
// kept in RAM so no extra open or stat is needed. Cost: up to a minute of
// lines is lost if power is cut before a flush.
#define LOCAL_LOG_FLUSH_INTERVAL_MS 60000
#define LOCAL_LOG_BUFFER_BYTES 8192
static String localLogBuffer;
static uint32_t localLogBufferedLines = 0;
static size_t localLogFileBytes = 0;
static unsigned long localLogLastFlushMs = 0;
uint32_t localLogFlushCount = 0;
uint32_t localLogLastFlushUs = 0;
uint32_t localLogMaxFlushUs = 0;

bool initLocalLog() {
  // true = format the partition if mount fails (e.g. first boot on a chip
  // that has never had this partition table before). Same trust model as
  // Preferences/NVS elsewhere in this file: local flash storage, not a
  // removable medium, so an automatic format on a genuinely corrupt/blank
  // partition is the right default rather than refusing to boot.
  if (!LittleFS.begin(true)) {
    Serial.println("[LOG] LittleFS mount failed even after format attempt - local logging disabled.");
    return false;
  }
  Serial.printf("[LOG] LittleFS mounted. Total: %u bytes, used: %u bytes\n",
                (unsigned)LittleFS.totalBytes(), (unsigned)LittleFS.usedBytes());
  if (LittleFS.exists(LOCAL_LOG_PATH)) {
    File existing = LittleFS.open(LOCAL_LOG_PATH, "r");
    localLogFileBytes = existing ? existing.size() : 0;
    if (existing) existing.close();
  }
  localLogBuffer.reserve(LOCAL_LOG_BUFFER_BYTES);
  localLogLastFlushMs = millis();
  return true;
}

// Writes the buffered lines to flash in a single append.
void flushLocalLog() {
  if (!localLogReady || localLogBuffer.length() == 0) return;
  uint32_t t0 = micros();
  bool truncated = false;
  if (localLogFileBytes + localLogBuffer.length() > LOCAL_LOG_MAX_BYTES) {
    // Truncate rather than rotate to a second file: the oldest data is lost.
    // At 10 s records the 3 MB cap is roughly two days, so this only bites
    // after a very long outage or if the log is never read back and cleared.
    // Records not yet acknowledged by the broker are counted as lost (v0.7.4).
    if (syncReady && syncBufferFirstSeq > 0) ledgerGiveUpThrough(syncLedger, syncBufferFirstSeq - 1);
    LittleFS.remove(LOCAL_LOG_PATH);
    localLogFileBytes = 0;
    syncReplayOffset = 0;
    syncReplayPrevBoot = 0;
    truncated = true;
    Serial.printf("[LOG] Local log exceeded size cap, truncated (sync: %u records lost in total).\n",
                  (unsigned)syncLedger.lost);
  }
  File f = LittleFS.open(LOCAL_LOG_PATH, "a");
  uint32_t lines = localLogBufferedLines;
  if (!f) {
    localLogAppendFailures += lines;
  } else {
    size_t written = f.print(localLogBuffer);
    f.close();
    if (written == localLogBuffer.length()) {
      localLogAppendCount += lines;
      localLogFileBytes += written;
    } else {
      localLogAppendFailures += lines;
    }
  }
  localLogLastFlushUs = micros() - t0;
  if (localLogLastFlushUs > localLogMaxFlushUs) localLogMaxFlushUs = localLogLastFlushUs;
  localLogFlushCount++;
  Serial.printf("[LOG] flushed %u lines, %u bytes in %.1f ms\n", (unsigned)lines,
                (unsigned)localLogBuffer.length(), localLogLastFlushUs / 1000.0f);
  localLogBuffer = "";
  localLogBufferedLines = 0;
  syncBufferFirstSeq = 0;
  localLogLastFlushMs = millis();
  // Saved straight after the log write, so the NVS write lands next to the
  // flush's own flash pause instead of adding a second one each minute.
  syncSave(truncated);
}

// Returns false if the line was not kept (logging off or not mounted).
bool appendLocalLog(const String& jsonLine, uint32_t seq) {
  if (!localLogReady || !localLogEnabled) return false;
  if (localLogBufferedLines == 0) syncBufferFirstSeq = seq;
  localLogBuffer += jsonLine;
  localLogBuffer += '\n';
  localLogBufferedLines++;
  if (localLogBuffer.length() >= LOCAL_LOG_BUFFER_BYTES - 700 ||
      millis() - localLogLastFlushMs >= LOCAL_LOG_FLUSH_INTERVAL_MS) {
    flushLocalLog();
  }
  return true;
}

// ============================================================
// Store-and-forward sync (v0.7.4): boot, replay and status.
// ============================================================

// Highest seq in the last ~2 KB of the log (a record is under 1.2 KB), 0 if
// none (no file, or only lines from firmware before v0.7.4).
uint32_t findLastLoggedSeq() {
  File f = LittleFS.open(LOCAL_LOG_PATH, "r");
  if (!f) return 0;
  const size_t size = f.size();
  if (size > 2048) f.seek(size - 2048);
  uint32_t last = 0;
  while (f.available()) {
    String rec = f.readStringUntil('\n');
    uint32_t s, b;
    if (syncParseSeqBoot(rec.c_str(), &s, &b) && s > last) last = s;
  }
  f.close();
  return last;
}

void initSync() {
  syncPrefs.begin("sw7sync", false);
  syncBootId = syncPrefs.getUInt("boot", 0) + 1;
  syncPrefs.putUInt("boot", syncBootId);
  syncBootFirstSeq = syncPrefs.getUInt("seqblk", 1);
  if (syncBootFirstSeq == 0) syncBootFirstSeq = 1;
  syncNextSeq = syncBootFirstSeq;
  syncSeqReservedTo = syncBootFirstSeq + SYNC_SEQ_BLOCK;
  syncPrefs.putUInt("seqblk", syncSeqReservedTo);
  ledgerInit(syncLedger, syncPrefs.getUInt("acked", 0), syncPrefs.getUInt("lost", 0));
  syncLastLoggedAtBoot = localLogReady ? findLastLoggedSeq() : 0;
  ledgerBoot(syncLedger, syncBootFirstSeq, syncLastLoggedAtBoot);
  syncReady = true;
  syncSave(true);
  Serial.printf("[SYNC] boot %u, first seq %u, last logged seq %u, acked through %u, backlog %u, lost so far %u\n",
                (unsigned)syncBootId, (unsigned)syncBootFirstSeq, (unsigned)syncLastLoggedAtBoot,
                (unsigned)syncLedger.acked, (unsigned)ledgerBacklog(syncLedger, syncNextSeq),
                (unsigned)syncLedger.lost);
}

// One replay pass, called from ModemTask's loop. Reads at most
// SYNC_REPLAY_LINES_PER_PASS log lines from the saved offset and publishes at
// most one record, then returns, so GNSS polling, the live 10 s publish and
// the serial console keep running between replayed records. Replayed records
// are the stored line with "replay":true added, on the same topic.
void syncReplayStep() {
  if (!syncReady || !mqttConnected) return;
  if ((long)(millis() - syncReplayNextMs) < 0) return;
  if (ledgerBacklog(syncLedger, syncNextSeq) == 0) return;

  File f;
  if (localLogReady) f = LittleFS.open(LOCAL_LOG_PATH, "r");
  if (f) {
    if (syncReplayOffset > f.size()) {  // file replaced since the last pass
      syncReplayOffset = 0;
      syncReplayPrevBoot = 0;
    }
    f.seek(syncReplayOffset);
    for (int i = 0; i < SYNC_REPLAY_LINES_PER_PASS && f.available(); i++) {
      String rec = f.readStringUntil('\n');
      const uint32_t lineEnd = f.position();
      if (rec.endsWith("\r")) rec.remove(rec.length() - 1);
      uint32_t s, b;
      if (rec.length() < 2 || rec[0] != '{' || !syncParseSeqBoot(rec.c_str(), &s, &b)) {
        syncReplayOffset = lineEnd;  // line from older firmware, or damaged
        continue;
      }
      const SyncScanAction action = ledgerOnLogRecord(syncLedger, s, b, syncReplayPrevBoot);
      syncReplayPrevBoot = b;
      if (action == SYNC_SCAN_SKIP) {
        syncReplayOffset = lineEnd;
        continue;
      }
      f.close();
      String out;
      out.reserve(rec.length() + 16);
      out = "{\"replay\":true,";
      out += rec.c_str() + 1;
      const bool ok = mqttPublish(out);
      mqttNotePublishResult(ok);
      if (ok) {
        ledgerReplayAck(syncLedger, s);
        syncReplayOffset = lineEnd;
        syncReplayNextMs = millis() + SYNC_REPLAY_INTERVAL_MS;
        if (ledgerBacklog(syncLedger, syncNextSeq) == 0) {
          Serial.printf("[SYNC] backlog cleared, %u replayed this boot\n", (unsigned)syncLedger.replayed);
        }
      } else {
        syncReplayFailures++;
        syncReplayNextMs = millis() + SYNC_REPLAY_RETRY_MS;
      }
      return;
    }
    const bool atEnd = !f.available();
    f.close();
    if (!atEnd) return;  // line budget used; carry on next pass
  }
  // End of the file (or no file). What is still open is either in the RAM
  // buffer or was never stored.
  const uint32_t firstUnflushed = localLogBufferedLines > 0 ? syncBufferFirstSeq : syncNextSeq;
  const uint32_t lostBefore = syncLedger.lost;
  ledgerOnEof(syncLedger, firstUnflushed, syncReplayPrevBoot, syncBootId, syncBootFirstSeq);
  if (syncLedger.lost != lostBefore) {
    Serial.printf("[SYNC] %u records not in the log, counted lost\n", (unsigned)(syncLedger.lost - lostBefore));
  }
  if (ledgerBacklog(syncLedger, syncNextSeq) > 0 && localLogBufferedLines > 0) {
    flushLocalLog();  // the rest is in RAM: write it now so the next pass can send it
  } else {
    syncReplayNextMs = millis() + 1000;
  }
}

void printSyncStatus() {
  const uint32_t backlog = syncReady ? ledgerBacklog(syncLedger, syncNextSeq) : 0;
  Serial.printf("[SYNC] boot=%u first_seq=%u next_seq=%u generated=%u acked=%u run=%u-%u skip=%u-%u "
                "backlog=%u live_acked=%u replayed=%u replay_failures=%u lost=%u forgotten=%u "
                "replay_offset=%u buffered=%u mqtt=%s\n",
                (unsigned)syncBootId, (unsigned)syncBootFirstSeq, (unsigned)syncNextSeq,
                (unsigned)(syncNextSeq - syncBootFirstSeq), (unsigned)syncLedger.acked,
                (unsigned)syncLedger.runLo, (unsigned)syncLedger.runHi,
                (unsigned)syncLedger.skipLo, (unsigned)syncLedger.skipHi, (unsigned)backlog,
                (unsigned)syncLiveAcked, (unsigned)syncLedger.replayed, (unsigned)syncReplayFailures,
                (unsigned)syncLedger.lost, (unsigned)syncLedger.forgotten,
                (unsigned)syncReplayOffset, (unsigned)localLogBufferedLines,
                mqttConnected ? "up" : "down");
  const int64_t utc = deviceUtcMs(esp_timer_get_time());
  if (utc < 0) {
    Serial.println("[SYNC] utc=unknown (no GNSS time yet, or none for 6 h)");
  } else {
    Serial.printf("[SYNC] utc_ms=%lld anchor_age_s=%lld\n", (long long)utc,
                  (long long)((esp_timer_get_time() - utcAnchorSetUs) / 1000000LL));
  }
}

// ============================================================
// Cellular signal strength (v0.6.0). AT+CSQ every publish cycle, so the
// road test records where coverage is weak along the route. CSQ 0..31
// maps to about -113 + 2*CSQ dBm (A76XX AT manual); 99 means unknown.
// ============================================================
volatile int cellCsqRaw = -1;

void pollSignalQuality() {
  Serial1.println("AT+CSQ");
  String response;
  unsigned long startWait = millis();
  while (millis() - startWait < 1000) {
    while (Serial1.available()) {
      response += static_cast<char>(Serial1.read());
    }
    if (response.indexOf("OK") >= 0 || response.indexOf("ERROR") >= 0) break;
    vTaskDelay(pdMS_TO_TICKS(1));
  }
  int p = response.indexOf("+CSQ:");
  if (p < 0) return;
  int v = response.substring(p + 5).toInt();
  if (v >= 0 && v <= 99) cellCsqRaw = v;
}

// ============================================================
// Motor Hall-sensor pulse counting (v0.6.0), for the optocoupler tap.
// The PC817 module's output (pull-up to VCC, transistor to GND) goes to
// HALL_INPUT_PIN; the hardware pulse counter counts both edges, so
// counting never touches the IMU tasks. One Hall wire gives one cycle per
// pole pair per motor revolution, i.e. 2 * pole_pairs edges per rev.
//
// Until the tap is wired, HALL_INPUT_PIN is the sync-pulse pin itself, as
// a bench loopback: the counter must then read exactly 2 edges/s (the
// sync output toggles every 500 ms). Change it to the real pin, and set
// HALL_POLE_PAIRS from the motor, before the vehicle test; with pole
// pairs 0 the rpm is not computed.
// ============================================================
#include "driver/pcnt.h"
#define HALL_INPUT_PIN SYNC_PULSE_PIN
#define HALL_LOOPBACK (HALL_INPUT_PIN == SYNC_PULSE_PIN)
#define HALL_POLE_PAIRS 0
#define HALL_PCNT_UNIT PCNT_UNIT_0
#define HALL_FILTER_APB_CYCLES 1000  // 12.5 us at 80 MHz: ignores contact noise

volatile uint32_t hallTotalEdges = 0;
volatile float hallEdgesPerSecond = 0.0f;

float hallRpm() {
  if (HALL_POLE_PAIRS == 0) return NAN;
  return hallEdgesPerSecond / (2.0f * HALL_POLE_PAIRS) * 60.0f;
}

bool initHallCounter() {
  pcnt_config_t cfg = {};
  cfg.pulse_gpio_num = HALL_INPUT_PIN;
  cfg.ctrl_gpio_num = PCNT_PIN_NOT_USED;
  cfg.channel = PCNT_CHANNEL_0;
  cfg.unit = HALL_PCNT_UNIT;
  cfg.pos_mode = PCNT_COUNT_INC;   // rising edge
  cfg.neg_mode = PCNT_COUNT_INC;   // falling edge
  cfg.lctrl_mode = PCNT_MODE_KEEP;
  cfg.hctrl_mode = PCNT_MODE_KEEP;
  cfg.counter_h_lim = 32767;
  cfg.counter_l_lim = 0;
  if (pcnt_unit_config(&cfg) != ESP_OK) return false;
  pcnt_set_filter_value(HALL_PCNT_UNIT, HALL_FILTER_APB_CYCLES);
  pcnt_filter_enable(HALL_PCNT_UNIT);
  if (HALL_LOOPBACK) {
    // pcnt_unit_config makes the pin an input only; keep the sync output.
    gpio_set_direction((gpio_num_t)HALL_INPUT_PIN, GPIO_MODE_INPUT_OUTPUT);
  } else {
    gpio_pullup_en((gpio_num_t)HALL_INPUT_PIN);  // opto output is open-collector
  }
  pcnt_counter_pause(HALL_PCNT_UNIT);
  pcnt_counter_clear(HALL_PCNT_UNIT);
  pcnt_counter_resume(HALL_PCNT_UNIT);
  return true;
}

// Reads and clears the counter once a second. At most 32767 edges per
// second before the counter limit, far above a hub motor's Hall rate.
void HallTask(void* pvParameters) {
  TickType_t lastWake = xTaskGetTickCount();
  unsigned long lastUs = micros();
  for (;;) {
    vTaskDelayUntil(&lastWake, pdMS_TO_TICKS(1000));
    int16_t count = 0;
    pcnt_get_counter_value(HALL_PCNT_UNIT, &count);
    pcnt_counter_clear(HALL_PCNT_UNIT);
    unsigned long now = micros();
    float dt = (now - lastUs) / 1e6f;
    lastUs = now;
    hallTotalEdges += (uint32_t)count;
    hallEdgesPerSecond = dt > 0 ? count / dt : 0.0f;
  }
}

// Compact JSON combining the latest known state from every subsystem
// this project owns. Deliberately does NOT match the vac-work Cyber
// Security team's own JSON schema (their broker/credentials are not used
// here, per the note above) - this is this project's own telemetry
// payload, to whatever broker MQTT_BROKER_HOST is actually pointed at.
String buildTelemetryJson(uint32_t seq) {
  RideFeatures r1, r2;
  FusedRide fz;
  portENTER_CRITICAL(&rideMux);
  copyRide(r1, latestRideFeatures1);
  copyRide(r2, latestRideFeatures2);
  fz.sources = latestFusedRide.sources;
  fz.rms_mps2 = latestFusedRide.rms_mps2;
  fz.std_mps2 = latestFusedRide.std_mps2;
  fz.peak_to_peak_mps2 = latestFusedRide.peak_to_peak_mps2;
  fz.mean_abs_jerk_mps3 = latestFusedRide.mean_abs_jerk_mps3;
  fz.std_disagreement = latestFusedRide.std_disagreement;
  portEXIT_CRITICAL(&rideMux);

  // JSON has no NaN; the disagreement is undefined for a single-sensor fallback.
  char dis[16];
  if (isnan(fz.std_disagreement)) snprintf(dis, sizeof(dis), "null");
  else snprintf(dis, sizeof(dis), "%.3f", fz.std_disagreement);
  char rpm[16];
  float rpmValue = hallRpm();
  if (isnan(rpmValue)) snprintf(rpm, sizeof(rpm), "null");
  else snprintf(rpm, sizeof(rpm), "%.1f", rpmValue);

  // Cell-tower position in the record only while there is no GNSS fix (as on the DASH line).
  const bool cellJson = !latestGnssFix.valid && latestCellLoc.valid &&
                        (esp_timer_get_time() - latestCellLoc.timestamp_us) <= CELL_LOC_STALE_US;
  // Record identity (v0.7.4): device, firmware, boot, seq, uptime and device
  // UTC (null until the first GNSS time). dev, boot and seq identify the
  // record on the server, which stores each (dev, boot, seq) once. Kept at the
  // start of the line so syncParseSeqBoot() finds them quickly.
  const int64_t nowUs = esp_timer_get_time();
  const int64_t utcMs = deviceUtcMs(nowUs);
  char utc[24];
  if (utcMs < 0) snprintf(utc, sizeof(utc), "null");
  else snprintf(utc, sizeof(utc), "%lld", (long long)utcMs);
  const char* fw = FIRMWARE_VERSION;
  if (fw[0] == 'v') fw++;

  // Static: only ModemTask calls this, and 1.1 KB is too much for its 4 KB stack.
  static char buf[1152];
  snprintf(buf, sizeof(buf),
           "{"
           "\"dev\":\"%s\",\"fw\":\"%s\",\"boot\":%lu,\"seq\":%lu,\"up_ms\":%lld,\"utc_ms\":%s,"
           "\"imu1\":{\"rms\":%.3f,\"std\":%.3f,\"p2p\":%.3f,\"crest\":%.3f,\"jerk\":%.3f,\"crossings\":%u},"
           "\"imu2\":{\"rms\":%.3f,\"std\":%.3f,\"p2p\":%.3f,\"crest\":%.3f,\"jerk\":%.3f,\"crossings\":%u},"
           "\"fused\":{\"src\":%u,\"rms\":%.3f,\"std\":%.3f,\"p2p\":%.3f,\"jerk\":%.3f,\"dis\":%s},"
           "\"bms\":{\"v\":%.2f,\"i\":%.2f,\"soc\":%u,\"checksum_ok\":%s},"
           "\"gnss\":{\"valid\":%s,\"lat\":%.6f,\"lon\":%.6f,\"speed\":%.1f},"
           "\"cell\":{\"csq\":%d,\"lat\":%.6f,\"lon\":%.6f,\"acc_m\":%.0f},"
           "\"hall\":{\"eps\":%.1f,\"rpm\":%s}"
           "}",
           MQTT_CLIENT_ID, fw, (unsigned long)syncBootId, (unsigned long)seq, (long long)(nowUs / 1000), utc,
           r1.rms_mps2, r1.std_mps2, r1.peak_to_peak_mps2, r1.crest_factor,
           r1.mean_abs_jerk_mps3, (unsigned)r1.threshold_crossings,
           r2.rms_mps2, r2.std_mps2, r2.peak_to_peak_mps2, r2.crest_factor,
           r2.mean_abs_jerk_mps3, (unsigned)r2.threshold_crossings,
           (unsigned)fz.sources, fz.rms_mps2, fz.std_mps2, fz.peak_to_peak_mps2,
           fz.mean_abs_jerk_mps3, dis,
           latestBmsSample.pack_voltage_v, latestBmsSample.current_a,
           (unsigned)latestBmsSample.soc_pct, latestBmsSample.checksum_ok ? "true" : "false",
           latestGnssFix.valid ? "true" : "false", latestGnssFix.latitude_deg,
           latestGnssFix.longitude_deg, latestGnssFix.speed_reported,
           (int)cellCsqRaw,
           cellJson ? latestCellLoc.latitude_deg : NAN, cellJson ? latestCellLoc.longitude_deg : NAN,
           cellJson ? latestCellLoc.accuracy_m : NAN,
           (float)hallEdgesPerSecond, rpm);
  // JSON has no NaN or infinity: before a GNSS fix, for example, the
  // position fields are NaN and printf writes "nan", which made every
  // such record invalid JSON up to v0.6.2 (found reading the log back).
  String json(buf);
  json.replace(":-nan", ":null");
  json.replace(":nan", ":null");
  json.replace(":-inf", ":null");
  json.replace(":inf", ":null");
  return json;
}

#endif  // !NODE_FRONT

// ============================================================
// Dashboard line (v0.7.0, crs and alt added in v0.7.1), section 1 of DashboardIntegration/TELEMETRY_LINK.md.
// Once a second, one line "DASH {json}\n" on the USB serial console, read by
// the Pi 4 telemetry bridge, which ignores every other line. The field names
// and types are a contract shared with the bridge and the dashboard: change
// them only together with that document.
//
// Its own low-priority task on core 0, so the line keeps its 1 s cadence
// while ModemTask is blocked for seconds in an AT command, and core 1 (IMU
// acquisition) is never involved. Built in a fixed static buffer with
// snprintf, no String, and written with a single Serial.write so this task
// does not split its own line (there is no print lock in this firmware, so
// another task's output can still land next to it, not inside it).
// Shared state is read the same way buildTelemetryJson() reads it: the
// fused ride result under rideMux, everything else as plain volatile reads.
// ============================================================
#define DASH_PERIOD_MS 1000
// Bytes including "DASH " and the newline: 480 up to v0.7.4.1 (400 until
// v0.7.3); 576 since v0.7.5 for the node, rdfail, stuck and rawdrop fields
// (about 60 bytes more in practice; the bridge accepts lines up to 4096).
#define DASH_LINE_MAX 576

// Runtime switch (serial command "!dash off" / "!dash on"), default on.
volatile bool dashEnabled = true;
uint32_t dashLineCount = 0;
uint32_t dashTruncatedCount = 0;
uint32_t dashUartSkipped = 0;   // DASH lines not sent on the Pi UART because its TX buffer was full

// Writes v with fmt into out, or "null" when v is NaN or infinite, since
// JSON has neither (same rule as the replace() pass in buildTelemetryJson).
static void dashNum(char* out, size_t n, const char* fmt, float v) {
  if (!isfinite(v)) snprintf(out, n, "null");
  else snprintf(out, n, fmt, v);
}

void DashTask(void* pvParameters) {
  static char line[DASH_LINE_MAX];
  uint32_t seq = 0;
  TickType_t lastWake = xTaskGetTickCount();

  for (;;) {
    vTaskDelayUntil(&lastWake, pdMS_TO_TICKS(DASH_PERIOD_MS));
    if (!dashEnabled) continue;

    const int64_t nowUs = esp_timer_get_time();

    // Read health and raw stream counters (v0.7.5), totals since boot, added
    // at the end of the line so every older field keeps its place.
    char health[160];
#if NODE_FRONT
    snprintf(health, sizeof(health), "\"node\":\"%s\",\"rdfail\":[%lu],\"stuck\":[%lu],\"rawdrop\":[%lu]",
             NODE_ID, (unsigned long)imuHealth[0].rdfail, (unsigned long)imuHealth[0].stuck,
             (unsigned long)rawDropped(0));
#else
    snprintf(health, sizeof(health),
             "\"node\":\"%s\",\"rdfail\":[%lu,%lu],\"stuck\":[%lu,%lu],\"rawdrop\":[%lu,%lu]", NODE_ID,
             (unsigned long)imuHealth[0].rdfail, (unsigned long)imuHealth[1].rdfail,
             (unsigned long)imuHealth[0].stuck, (unsigned long)imuHealth[1].stuck,
             (unsigned long)rawDropped(0), (unsigned long)rawDropped(1));
#endif

#if !NODE_FRONT
    // BMS: parseBmsData() only runs for a frame that passed the checksum, so
    // a non-zero timestamp means at least one valid frame has arrived.
    const int64_t bmsTs = latestBmsSample.timestamp_us;
    const bool haveBms = bmsTs > 0;
    char soc[8], v[16], cur[16], bmsAge[16];
    if (haveBms) snprintf(soc, sizeof(soc), "%u", (unsigned)latestBmsSample.soc_pct);
    else snprintf(soc, sizeof(soc), "null");
    dashNum(v, sizeof(v), "%.2f", haveBms ? latestBmsSample.pack_voltage_v : NAN);
    dashNum(cur, sizeof(cur), "%.2f", haveBms ? latestBmsSample.current_a : NAN);
    dashNum(bmsAge, sizeof(bmsAge), "%.1f", haveBms ? (nowUs - bmsTs) / 1e6f : NAN);

    // GNSS: position only with a valid fix (the parser leaves it NaN otherwise).
    const bool fix = latestGnssFix.valid;
    char lat[16], lon[16], spd[16], crs[16], alt[16];
    dashNum(lat, sizeof(lat), "%.6f", fix ? latestGnssFix.latitude_deg : NAN);
    dashNum(lon, sizeof(lon), "%.6f", fix ? latestGnssFix.longitude_deg : NAN);
    dashNum(spd, sizeof(spd), "%.3f", latestGnssFix.speed_reported);
    // Course over ground (v0.7.1): the parser leaves it NaN when the modem
    // sends an empty field (typically when stationary). Anything outside
    // 0..360 is treated as invalid rather than wrapped.
    float crsDeg = fix ? latestGnssFix.course_deg : NAN;
    if (isfinite(crsDeg) && (crsDeg < 0.0f || crsDeg > 360.0f)) crsDeg = NAN;
    dashNum(crs, sizeof(crs), "%.1f", crsDeg);
    // Altitude above mean sea level in metres (v0.7.1), only with a fix.
    // A value outside -1000..20000 m can only be a misparsed field; it is
    // sent as null, which also bounds the field to 7 characters so the
    // worst-case line stays under DASH_LINE_MAX (396 bytes with every other
    // number at its 15-character buffer limit, about 320 in practice).
    float altM = fix ? latestGnssFix.altitude_m : NAN;
    if (isfinite(altM) && (altM < -1000.0f || altM > 20000.0f)) altM = NAN;
    dashNum(alt, sizeof(alt), "%.1f", altM);

    // Cell-tower position (v0.7.3): sent alongside, never in lat/lon, and only while
    // there is no GNSS fix and the estimate is under 5 min old.
    const bool cellShown = !fix && latestCellLoc.valid &&
                           (nowUs - latestCellLoc.timestamp_us) <= CELL_LOC_STALE_US;
    char cLat[16], cLon[16], cAcc[16], cAge[16];
    dashNum(cLat, sizeof(cLat), "%.6f", cellShown ? latestCellLoc.latitude_deg : NAN);
    dashNum(cLon, sizeof(cLon), "%.6f", cellShown ? latestCellLoc.longitude_deg : NAN);
    dashNum(cAcc, sizeof(cAcc), "%.0f", cellShown ? latestCellLoc.accuracy_m : NAN);
    dashNum(cAge, sizeof(cAge), "%.0f",
            cellShown ? (float)((nowUs - latestCellLoc.timestamp_us) / 1000000LL) : NAN);

#endif  // !NODE_FRONT

    // Fused vibration: null until the first fused window, or once the last
    // one is older than the fusion stale limit (both IMUs stopped).
    int64_t fzTs;
    float fzStd, fzDis;
    portENTER_CRITICAL(&rideMux);
    fzTs = latestFusedRide.window_end_timestamp_us;
    fzStd = latestFusedRide.std_mps2;
    fzDis = latestFusedRide.std_disagreement;
    portEXIT_CRITICAL(&rideMux);
    const bool fzFresh = fzTs > 0 && (nowUs - fzTs) <= RIDE_FUSION_STALE_US;
    char vib[16], vibDis[16];
    dashNum(vib, sizeof(vib), "%.3f", fzFresh ? fzStd : NAN);
    dashNum(vibDis, sizeof(vibDis), "%.3f", fzFresh ? fzDis : NAN);

#if !NODE_FRONT
    char rpm[16];
    dashNum(rpm, sizeof(rpm), "%.1f", hallRpm());

    // CSQ 99 is the modem's "unknown"; -1 means no reply parsed yet.
    const int csqRaw = cellCsqRaw;
    char csq[8];
    if (csqRaw < 0 || csqRaw > 31) snprintf(csq, sizeof(csq), "null");
    else snprintf(csq, sizeof(csq), "%d", csqRaw);

#endif  // !NODE_FRONT

    const char* fw = FIRMWARE_VERSION;
    if (fw[0] == 'v') fw++;  // the contract carries the bare number, e.g. "0.7.1"

#if NODE_FRONT
    // Front node: the fields it has, same names and types as the rear unit's.
    (void)vibDis;
    int len = snprintf(line, sizeof(line),
                       "DASH {\"seq\":%lu,\"up_ms\":%lld,\"fw\":\"%s\",\"vib\":%s,"
                       "\"imu_hz\":[%.1f],\"drops\":[%lu],%s}\n",
                       (unsigned long)seq, (long long)(nowUs / 1000), fw, vib, (float)imu1RateHz,
                       (unsigned long)imu1Dropped, health);
#else
    int len = snprintf(line, sizeof(line),
                       "DASH {\"seq\":%lu,\"up_ms\":%lld,\"fw\":\"%s\","
                       "\"soc\":%s,\"v\":%s,\"i\":%s,\"bms_age_s\":%s,"
                       "\"fix\":%s,\"lat\":%s,\"lon\":%s,\"spd_raw\":%s,\"crs\":%s,\"alt\":%s,"
                       "\"vib\":%s,\"vib_dis\":%s,\"imu_hz\":[%.1f,%.1f],\"drops\":[%lu,%lu],"
                       "\"rpm\":%s,\"csq\":%s,\"mqtt\":%s,"
                       "\"cell_lat\":%s,\"cell_lon\":%s,\"cell_acc_m\":%s,\"cell_age_s\":%s,\"agps\":%s,"
                       "%s}\n",
                       (unsigned long)seq, (long long)(nowUs / 1000), fw,
                       soc, v, cur, bmsAge,
                       fix ? "true" : "false", lat, lon, spd, crs, alt,
                       vib, vibDis, (float)imu1RateHz, (float)imu2RateHz,
                       (unsigned long)imu1Dropped, (unsigned long)imu2Dropped,
                       rpm, csq, mqttConnected ? "true" : "false",
                       cLat, cLon, cAcc, cAge, agpsOk ? "true" : "false", health);
#endif
    if (len < 0 || len >= (int)sizeof(line)) {
      // A cut line would be invalid JSON; skip it rather than send half.
      dashTruncatedCount++;
      continue;
    }
    Serial.write(reinterpret_cast<const uint8_t*>(line), (size_t)len);
#if LINK_UART_ENABLE
    // Same line on the UART to the Pi. The TX buffer (8 KB since v0.7.5, set in
    // setup) holds several lines, and the raw stream always leaves
    // RAW_DASH_RESERVE bytes of it free, so this line fits.
    if (Serial2.availableForWrite() >= len) {
      Serial2.write(reinterpret_cast<const uint8_t*>(line), (size_t)len);
    } else {
      dashUartSkipped++;
    }
#endif
    seq++;
    dashLineCount++;
  }
}

// ============================================================
// Local serial commands.
//
// Everything typed on the USB serial console is still passed straight to
// the modem (AT pass-through), except a line starting with '!', which is
// handled here instead:
//   !help        list the commands
//   !status      logging, MQTT and calibration state
//   !log off     stop local flash logging (flash-write stall test)
//   !log on      start it again
//   !log flush   write the buffered log lines to flash now
//   !log dump    print the stored log (BenchTest/log_dump.py saves it)
//   !log clear   delete the stored log file
//   !mqtt        try to reconnect MQTT now
//   !gnssraw     toggle printing the raw GNSS reply on every poll
//   !dash off    stop the once-a-second DASH line for the Pi 4 bridge
//   !dash on     start it again (default on)
//   !recal       erase both stored IMU calibrations and restart; the board
//                must be kept still for the ~2 s calibration after boot
//   !sync        store-and-forward status: boot, seq, acked, backlog, replayed,
//                lost (one key=value line, read by tests), and device UTC
//   !sync drop   give up the whole backlog (counted as lost), for tests
//   !raw off     stop the raw IMU stream to the Pi (v0.7.5)
//   !raw on      start it again (default on)
// The front node has !help, !status, !dash, !raw and !recal only.
// ============================================================

// Read health and raw stream, for !status on both nodes (v0.7.5).
static void printRawStatus() {
  Serial.printf("[CMD] node %s, raw stream %s, %u lines sent, ports:%s%s\n", NODE_ID,
                rawEnabled ? "on" : "OFF", (unsigned)rawLinesSent, RAW_ON_USB ? " usb" : "",
                RAW_ON_UART ? " uart" : "");
  for (int i = 0; i < 2; i++) {
    if (!(i == 0 ? imu1Ready : imu2Ready)) continue;
    Serial.printf("[CMD] imu%d: rdfail=%u stuck=%u rawdrop=%u (queue %u, port %u)\n", i + 1,
                  (unsigned)imuHealth[i].rdfail, (unsigned)imuHealth[i].stuck, (unsigned)rawDropped(i),
                  (unsigned)rawQueueDropped[i], (unsigned)rawPortDropped[i]);
  }
  Serial.printf("[CMD] sync edges=%u, events dropped=%u\n", (unsigned)syncEdgeCount, (unsigned)rawSyncDropped);
}

// Commands both nodes share. True if the line was one of them.
static bool handleCommonCommand(const String& line) {
  if (line == "!dash off") {
    dashEnabled = false;
    Serial.println("[CMD] DASH line OFF");
  } else if (line == "!dash on") {
    dashEnabled = true;
    Serial.println("[CMD] DASH line on");
  } else if (line == "!raw off") {
    rawEnabled = false;
    Serial.println("[CMD] raw IMU stream OFF");
  } else if (line == "!raw on") {
    rawEnabled = true;
    Serial.println("[CMD] raw IMU stream on");
  } else {
    return false;
  }
  return true;
}

#if NODE_FRONT
void handleLocalCommand(String line) {
  line.trim();
  line.toLowerCase();
  if (handleCommonCommand(line)) return;
  if (line == "!help") {
    Serial.println("[CMD] !status  !dash off  !dash on  !raw off  !raw on  !recal");
  } else if (line == "!status") {
    Serial.printf("[CMD] firmware %s (front node)\n", FIRMWARE_VERSION);
    Serial.printf("[CMD] IMU scale factor: imu1=%.4f\n", rideChar1Config.mag_scale);
    Serial.printf("[CMD] dash line: %s, %u lines sent, %u skipped as too long\n", dashEnabled ? "on" : "OFF",
                  (unsigned)dashLineCount, (unsigned)dashTruncatedCount);
    printRawStatus();
  } else if (line == "!recal") {
    imuCalPrefs.begin("imucal", false);
    imuCalPrefs.remove("imu1");
    imuCalPrefs.end();
    Serial.println("[CMD] Stored IMU calibration erased. Keep the board STILL: restarting to recalibrate...");
    Serial.flush();
    delay(500);
    ESP.restart();
  } else {
    Serial.printf("[CMD] unknown command '%s', try !help\n", line.c_str());
  }
}

// The front node has no modem task, so this small task reads '!' commands
// from USB serial (and from the UART when it is enabled).
void CommandTask(void* pvParameters) {
  String usbCmd, uartCmd;
  for (;;) {
    while (Serial.available()) {
      char c = static_cast<char>(Serial.read());
      if (c == '\n' || c == '\r') {
        if (usbCmd.length() > 1 && usbCmd[0] == '!') handleLocalCommand(usbCmd);
        usbCmd = "";
      } else if (usbCmd.length() < 64) {
        usbCmd += c;
      }
    }
#if LINK_UART_ENABLE
    while (Serial2.available()) {
      char c = static_cast<char>(Serial2.read());
      if (c == '\n' || c == '\r') {
        if (uartCmd.length() > 1 && uartCmd[0] == '!') handleLocalCommand(uartCmd);
        uartCmd = "";
      } else if (uartCmd.length() < 64) {
        uartCmd += c;
      }
    }
#endif
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}
#else
void handleLocalCommand(String line) {
  line.trim();
  line.toLowerCase();
  if (handleCommonCommand(line)) return;
  if (line == "!help") {
    Serial.println("[CMD] !status  !sync  !sync drop  !log off  !log on  !log flush  !log dump  !log clear  !mqtt  !gnssraw  !dash off  !dash on  !raw off  !raw on  !recal  !agps  !cellpos");
  } else if (line == "!sync") {
    printSyncStatus();
  } else if (line == "!sync drop") {
    flushLocalLog();
    const uint32_t before = syncLedger.lost;
    ledgerGiveUpThrough(syncLedger, syncNextSeq - 1);
    syncSave(true);
    Serial.printf("[CMD] sync backlog dropped, %u records counted lost\n", (unsigned)(syncLedger.lost - before));
  } else if (line == "!agps") {
    agpsNextMs = millis();      // the modem loop runs it on its next pass
    Serial.println("[CMD] assisted GNSS download requested");
  } else if (line == "!cellpos") {
    cellLocNextMs = millis();
    Serial.println("[CMD] cell-tower position requested (only while there is no GNSS fix)");
  } else if (line == "!status") {
    Serial.printf("[CMD] firmware %s\n", FIRMWARE_VERSION);
    Serial.printf("[CMD] local log: %s, %u lines written, %u failures\n",
                  !localLogReady ? "not mounted" : (localLogEnabled ? "on" : "OFF"),
                  (unsigned)localLogAppendCount, (unsigned)localLogAppendFailures);
    Serial.printf("[CMD] log buffer: %u lines waiting, %u flushes, last %.1f ms, max %.1f ms, file %u bytes\n",
                  (unsigned)localLogBufferedLines, (unsigned)localLogFlushCount,
                  localLogLastFlushUs / 1000.0f, localLogMaxFlushUs / 1000.0f,
                  (unsigned)localLogFileBytes);
    if (cellCsqRaw == 99 || cellCsqRaw < 0) {
      Serial.println("[CMD] signal: unknown");
    } else {
      Serial.printf("[CMD] signal: CSQ %d (about %d dBm)\n", cellCsqRaw, -113 + 2 * cellCsqRaw);
    }
    Serial.printf("[CMD] hall: %u edges total, %.1f edges/s, %.1f rpm (pole pairs %u)\n",
                  (unsigned)hallTotalEdges, hallEdgesPerSecond, hallRpm(),
                  (unsigned)HALL_POLE_PAIRS);
    Serial.printf("[CMD] mqtt: %s, %u published, %u failed, %u connect attempts",
                  mqttConnected ? "connected" : "not connected",
                  (unsigned)mqttPublishCount, (unsigned)mqttPublishFailures,
                  (unsigned)mqttConnectAttempts);
    if (!mqttConnected) {
      long wait = (long)(mqttNextAttemptMs - millis());
      Serial.printf(", next attempt in %ld s", wait > 0 ? wait / 1000 : 0);
    }
    Serial.println();
    Serial.printf("[CMD] IMU scale factors: imu1=%.4f imu2=%.4f\n",
                  rideChar1Config.mag_scale, rideChar2Config.mag_scale);
    Serial.printf("[CMD] dash line: %s, %u lines sent, %u skipped as too long, %u not sent on the Pi UART (busy)\n",
                  dashEnabled ? "on" : "OFF", (unsigned)dashLineCount,
                  (unsigned)dashTruncatedCount, (unsigned)dashUartSkipped);
    Serial.printf("[CMD] mqtt position: %s\n", MQTT_INCLUDE_POSITION ? "published (private broker build)"
                                                                     : "removed from the published record");
    printRawStatus();
    printSyncStatus();
  } else if (line == "!log off") {
    flushLocalLog();
    localLogEnabled = false;
    Serial.println("[CMD] local flash logging OFF");
  } else if (line == "!log flush") {
    flushLocalLog();
  } else if (line == "!log dump") {
    // Prints the stored log, one "LOG|<line>" per record in a single
    // write each, so the lines can be picked out of the other tasks'
    // output on the laptop (BenchTest/log_dump.py). The end marker gives
    // the line and byte counts for a completeness check.
    flushLocalLog();
    File f = LittleFS.open(LOCAL_LOG_PATH, "r");
    if (!f) {
      Serial.println("[LOGDUMP] no log file");
    } else {
      Serial.printf("[LOGDUMP] begin %u bytes\n", (unsigned)f.size());
      uint32_t n = 0, bytes = 0;
      while (f.available()) {
        String rec = f.readStringUntil('\n');
        bytes += rec.length() + 1;
        if (rec.endsWith("\r")) rec.remove(rec.length() - 1);  // older lines end in CRLF
        // Index and length prefix: other tasks' output can land inside a
        // line, so the laptop keeps only lines whose length matches and
        // repeats the dump to fill any gaps by index. Paced so the USB
        // serial buffer is not overrun.
        Serial.printf("LOG|%u|%u|%s\n", (unsigned)n, (unsigned)rec.length(), rec.c_str());
        n++;
        vTaskDelay(pdMS_TO_TICKS(4));
      }
      f.close();
      Serial.printf("[LOGDUMP] end %u lines %u bytes\n", (unsigned)n, (unsigned)bytes);
    }
  } else if (line == "!log clear") {
    flushLocalLog();
    // Unacknowledged records in the file go with it: counted as lost.
    const uint32_t before = syncLedger.lost;
    ledgerGiveUpThrough(syncLedger, syncNextSeq - 1);
    LittleFS.remove(LOCAL_LOG_PATH);
    localLogFileBytes = 0;
    syncReplayOffset = 0;
    syncReplayPrevBoot = 0;
    syncSave(true);
    Serial.printf("[CMD] local log file deleted (%u unacknowledged records counted lost)\n",
                  (unsigned)(syncLedger.lost - before));
  } else if (line == "!log on") {
    localLogEnabled = true;
    Serial.println("[CMD] local flash logging on");
  } else if (line == "!gnssraw") {
    gnssPrintRaw = !gnssPrintRaw;
    Serial.printf("[CMD] raw GNSS replies %s\n", gnssPrintRaw ? "on" : "off");
  } else if (line == "!mqtt") {
    mqttNextAttemptMs = millis();
    mqttConnected = false;
    Serial.println("[CMD] MQTT reconnect requested");
  } else if (line == "!recal") {
    flushLocalLog();
    imuCalPrefs.begin("imucal", false);
    imuCalPrefs.remove("imu1");
    imuCalPrefs.remove("imu2");
    imuCalPrefs.end();
    Serial.println("[CMD] Stored IMU calibration erased. Keep the board STILL: restarting to recalibrate...");
    Serial.flush();
    delay(500);
    ESP.restart();
  } else {
    Serial.printf("[CMD] unknown command '%s', try !help\n", line.c_str());
  }
}

// True if the modem answers "AT" with OK within about 0.7 s, on any of
// `tries` attempts.
static bool modemResponds(int tries) {
  for (int i = 0; i < tries; i++) {
    while (Serial1.available()) Serial1.read();
    Serial1.println("AT");
    String r;
    unsigned long t0 = millis();
    while (millis() - t0 < 700) {
      while (Serial1.available()) r += static_cast<char>(Serial1.read());
      if (r.indexOf("OK") >= 0) return true;
      vTaskDelay(pdMS_TO_TICKS(5));
    }
  }
  return false;
}

void ModemTask(void* pvParameters) {
  Serial1.begin(MODEM_BAUD, SERIAL_8N1, A7670X_RX_PIN, A7670X_TX_PIN);

  pinMode(A7670X_RESET_PIN, OUTPUT);
  digitalWrite(A7670X_RESET_PIN, LOW);
  pinMode(A7670X_PWRKEY_PIN, OUTPUT);
  digitalWrite(A7670X_PWRKEY_PIN, LOW);
  vTaskDelay(pdMS_TO_TICKS(200));

  // The power key TOGGLES the modem. The modem keeps its own supply when
  // only the ESP32 resets (after reprogramming, or a software restart), so
  // an unconditional pulse at every boot switched an already-running modem
  // OFF: seen on 29 Sep 2026, when every GNSS poll and MQTT command went
  // unanswered after a reflash. Pulse only if the modem does not answer.
  if (modemResponds(3)) {
    Serial.println("[MODEM] already on, power key not pulsed");
  } else {
    Serial.println("[MODEM] no reply, pulsing power key");
    digitalWrite(A7670X_PWRKEY_PIN, HIGH);
    delay(3000);
    digitalWrite(A7670X_PWRKEY_PIN, LOW);
    bool up = false;
    for (int i = 0; i < 20 && !up; i++) {
      delay(1000);
      up = modemResponds(1);
    }
    Serial.println(up ? "[MODEM] on" : "[MODEM] still not answering after 20 s");
  }

  const char* testCommands[] = {
      "AT", "AT+CPIN?", "AT+CSQ", "AT+CREG?", "AT+CGREG?", "AT+CPSI?"};

  for (size_t i = 0; i < sizeof(testCommands) / sizeof(testCommands[0]); i++) {
    Serial.print("---> Sending: ");
    Serial.println(testCommands[i]);
    Serial1.println(testCommands[i]);

    unsigned long startWait = millis();
    while (millis() - startWait < 2000) {
      while (Serial1.available()) {
        Serial.write(static_cast<uint8_t>(Serial1.read()));
      }
      vTaskDelay(pdMS_TO_TICKS(1));
    }
    Serial.println("\n-----------------");
  }

  Serial.println("---> Sending: AT+CGNSSPWR=1");
  sendGnssCommand("AT+CGNSSPWR=1");
  Serial.println("GNSS engine enabled; waiting for navigation data.");

  Serial.println("---> Connecting MQTT...");
  if (!mqttConnect()) {
    mqttNextAttemptMs = millis() + mqttRetryDelayMs;
    Serial.printf("[MQTT] Initial connect failed, retrying in %lu s.\n", mqttRetryDelayMs / 1000);
  }

  Serial.println("==============================");
  Serial.println("Sequence complete. Entering pass-through mode.");
  Serial.println("Type AT commands below freely, or !help for local commands:");

  unsigned long lastGnssPoll = millis() - 3000;
  unsigned long lastMqttPublish = millis() - MQTT_PUBLISH_INTERVAL_MS;
  String localCmd;          // a '!' line being typed
  bool forwardingLine = false;  // mid-way through a line going to the modem
  String modemLine;         // modem output, scanned for connection-lost URCs
  String uartCmd;           // a '!' line arriving from the Pi on the UART link
  for (;;) {
    while (Serial.available()) {
      char c = static_cast<char>(Serial.read());
      if (!forwardingLine && localCmd.length() == 0 && c == '!') {
        localCmd = "!";
        continue;
      }
      if (localCmd.length() > 0) {
        if (c == '\n' || c == '\r') {
          handleLocalCommand(localCmd);
          localCmd = "";
        } else if (localCmd.length() < 64) {
          localCmd += c;
        }
        continue;
      }
      Serial1.write(static_cast<uint8_t>(c));
      forwardingLine = !(c == '\n' || c == '\r');
    }
    // Local '!' commands from the Pi over the UART link (no AT pass-through here).
    while (Serial2.available()) {
      char c = static_cast<char>(Serial2.read());
      if (c == '\n' || c == '\r') {
        if (uartCmd.length() > 1 && uartCmd[0] == '!') handleLocalCommand(uartCmd);
        uartCmd = "";
      } else if (uartCmd.length() < 64) {
        uartCmd += c;
      }
    }
    if (!mqttConnected && (long)(millis() - mqttNextAttemptMs) >= 0) {
      Serial.println("[MQTT] Reconnecting...");
      mqttTeardown();
      if (mqttConnect()) {
        mqttRetryDelayMs = MQTT_RETRY_MIN_MS;
      } else {
        mqttNextAttemptMs = millis() + mqttRetryDelayMs;
        Serial.printf("[MQTT] Reconnect failed, next attempt in %lu s.\n", mqttRetryDelayMs / 1000);
        mqttRetryDelayMs = min(mqttRetryDelayMs * 2, MQTT_RETRY_MAX_MS);
      }
    }
    if (millis() - lastGnssPoll >= 3000) {
      lastGnssPoll = millis();
      pollAndParseGnss();
    }
    if ((long)(millis() - agpsNextMs) >= 0) {
      agpsNextMs = millis() + (requestAgps() ? AGPS_REFRESH_MS : AGPS_RETRY_MS);
    }
    if (!latestGnssFix.valid && (long)(millis() - cellLocNextMs) >= 0) {
      pollCellLocation();
      cellLocNextMs = millis() + CELL_LOC_INTERVAL_MS;
    }
    if (millis() - lastMqttPublish >= MQTT_PUBLISH_INTERVAL_MS) {
      lastMqttPublish = millis();
      // Built and logged locally on this cadence regardless of MQTT state -
      // the "logged locally" obligation does not depend on connectivity.
      pollSignalQuality();
      const uint32_t seq = syncAssignSeq();
      String payload = buildTelemetryJson(seq);
      const bool stored = appendLocalLog(payload, seq);
      bool acked = false;
      if (mqttConnected) {
        acked = mqttPublish(payload);
        if (!acked) Serial.println("[MQTT] publish failed");
        mqttNotePublishResult(acked);
      }
      if (acked) {
        ledgerLiveAck(syncLedger, seq);
        syncLiveAcked++;
      } else if (!stored) {
        ledgerUnstoredLost(syncLedger, seq);  // neither sent nor kept: can never be replayed
      }
    }
    // Backlog replay after an outage: at most one record per pass.
    syncReplayStep();
    if (!(localLogReady && localLogEnabled) && millis() - syncLastSaveMs >= SYNC_PERSIST_INTERVAL_MS) {
      syncSave(false);  // with logging on, the log flush saves the ledger instead
    }
    while (Serial1.available()) {
      char c = static_cast<char>(Serial1.read());
      Serial.write(static_cast<uint8_t>(c));
      if (c == '\n') {
        // Manual 18.4: +CMQTTCONNLOST means the server dropped the client;
        // +CMQTTNONET means the network went away and MQTT must be restarted.
        if (modemLine.indexOf("+CMQTTCONNLOST") >= 0 || modemLine.indexOf("+CMQTTNONET") >= 0) {
          if (mqttConnected) Serial.println("[MQTT] Connection lost (modem URC), will reconnect.");
          mqttConnected = false;
          mqttNextAttemptMs = millis() + 5000;
        }
        // +CGEV: ... PDN ACT means the network data connection is back.
        // Seen on 30 Sep 2026: after AT+CFUN=1 the network returned in 2.4 s
        // but the reconnect waited 36 s for its backoff timer. Retry soon
        // instead, and restart the backoff from its minimum.
        if (!mqttConnected && modemLine.indexOf("+CGEV:") >= 0 && modemLine.indexOf("PDN ACT") >= 0) {
          Serial.println("[MQTT] Network data connection back, reconnecting shortly.");
          mqttRetryDelayMs = MQTT_RETRY_MIN_MS;
          mqttNextAttemptMs = millis() + 2000;
        }
        modemLine = "";
      } else if (modemLine.length() < 120) {
        modemLine += c;
      }
    }
    vTaskDelay(pdMS_TO_TICKS(1));
  }
}

#endif  // !NODE_FRONT

// ============================================================
// Setup / loop
// ============================================================
void setup() {
#if RAW_ON_USB
  // Room for the raw stream on USB serial (the default is 256 bytes); must be
  // set before begin().
  Serial.setTxBufferSize(LINK_TX_BUFFER_BYTES);
#endif
  Serial.begin(115200);
#if LINK_UART_ENABLE
  // UART link to the Raspberry Pi 4 (see LINK_UART_*): DASH lines and the raw
  // stream go out here. 8 KB TX buffer since v0.7.5 (2 KB before): about
  // 0.18 s of the link at 460800 baud.
  Serial2.setTxBufferSize(LINK_TX_BUFFER_BYTES);
  Serial2.begin(LINK_UART_BAUD, SERIAL_8N1, LINK_UART_RX_PIN, LINK_UART_TX_PIN);
#endif

  const unsigned long serialWaitStart = millis();
  while (!Serial && millis() - serialWaitStart < 3000) {
    delay(100);
  }
  Serial.printf("[BOOT] PSRAM: found=%s size=%u bytes free=%u bytes\n",
                psramFound() ? "yes" : "no",
                (unsigned)ESP.getPsramSize(),
                (unsigned)ESP.getFreePsram());
  Serial.printf("[BOOT] Flash: size=%u bytes\n", (unsigned)ESP.getFlashChipSize());

  Serial.printf("\nSW-7 ESP32-S3 Firmware %s, node %s\n", FIRMWARE_VERSION, NODE_ID);
  Serial.println("==================================");
  Serial.println("System booted: ESP32-S3");
  Serial.println("Status: ONLINE\n");

  Serial.printf("Flash size:        %u bytes\n", ESP.getFlashChipSize());
  Serial.printf("Free heap (SRAM):  %u bytes\n", ESP.getFreeHeap());
  Serial.printf("PSRAM size:        %u bytes\n", ESP.getPsramSize());
  Serial.printf("Free PSRAM:        %u bytes\n", ESP.getFreePsram());
  Serial.println();

#if !NODE_FRONT
  localLogReady = initLocalLog();
  initSync();
#endif

  imu1Ready = initImu(&mpu1, &Wire, IMU1_SDA_PIN, IMU1_SCL_PIN);
  Serial.println(imu1Ready ? "IMU1 found and configured (stem/chassis - confirm on bracket)."
                            : "IMU1 not found.");

#if ENABLE_IMU2
  imu2Ready = initImu(&mpu2, &Wire1, IMU2_SDA_PIN, IMU2_SCL_PIN);
  Serial.println(imu2Ready ? "IMU2 found and configured."
                            : "IMU2 not found (expected if not yet wired, or pins need verifying).");
#else
  Serial.println("IMU2 disabled (ENABLE_IMU2 = 0).");
#endif
  Serial.println();

  float imu1MagScale = loadOrCalibrateMagScale("imu1", &mpu1, imu1Ready);
#if ENABLE_IMU2
  float imu2MagScale = loadOrCalibrateMagScale("imu2", &mpu2, imu2Ready);
#else
  float imu2MagScale = 1.0f;
#endif
  Serial.println();

  imu1Queue = xQueueCreate(IMU_QUEUE_LENGTH, sizeof(ImuSample));
  imu2Queue = xQueueCreate(IMU_QUEUE_LENGTH, sizeof(ImuSample));
  gnssQueue = xQueueCreate(20, sizeof(GnssFix));
  bmsQueue = xQueueCreate(20, sizeof(BmsSample));
  imu1CharQueue = xQueueCreate(RIDE_CHAR_QUEUE_LENGTH, sizeof(ImuSample));
  imu2CharQueue = xQueueCreate(RIDE_CHAR_QUEUE_LENGTH, sizeof(ImuSample));

  imu1Config = {0, imu1Queue, imu1CharQueue, &mpu1, &imu1Ready, &Wire};
  imu2Config = {1, imu2Queue, imu2CharQueue, &mpu2, &imu2Ready, &Wire1};

  // Raw stream (v0.7.5): queues before the IMU and sync tasks start.
  rawQueue.h = xQueueCreate(RAW_QUEUE_LENGTH, sizeof(RawItem));
  rawSyncQueue = xQueueCreate(8, sizeof(RawSyncEvent));
#if RAW_ON_UART
  rawPortIsUsb[rawPortCount] = false;
  rawPorts[rawPortCount++] = &Serial2;
#endif
#if RAW_ON_USB
  rawPortIsUsb[rawPortCount] = true;
  rawPorts[rawPortCount++] = &Serial;
#endif
  rideChar1Config = {0, imu1CharQueue, &latestRideFeatures1, imu1MagScale};
  rideChar2Config = {1, imu2CharQueue, &latestRideFeatures2, imu2MagScale};

  selfTestRideFeatures();
  selfTestRideFusion();

#if NODE_FRONT
  xTaskCreatePinnedToCore(CommandTask, "CommandTask", 4096, nullptr, 1, nullptr, 0);
#else
  xTaskCreatePinnedToCore(ModemTask, "ModemTask", 4096, nullptr, 1, &ModemTaskHandle, 0);
#endif

  xTaskCreatePinnedToCore(ImuTask, "Imu1Task", 4096, &imu1Config, 3, &Imu1TaskHandle, 1);
  xTaskCreatePinnedToCore(ImuTask, "Imu2Task", 4096, &imu2Config, 3, &Imu2TaskHandle, 1);
  xTaskCreatePinnedToCore(StatsTask, "StatsTask", 4096, nullptr, 2, &StatsTaskHandle, 1);
  xTaskCreatePinnedToCore(SyncTask, "SyncTask", 2048, nullptr, 2, &SyncTaskHandle, 1);
  xTaskCreatePinnedToCore(RawSenderTask, "RawSender", 4096, nullptr, 1, &RawSenderTaskHandle, 0);
#if !NODE_FRONT
  // After SyncTask has set its pin as an output, so that in loopback the
  // counter's input setup keeps the output enabled (see initHallCounter).
  vTaskDelay(pdMS_TO_TICKS(50));
  if (initHallCounter()) {
    xTaskCreatePinnedToCore(HallTask, "HallTask", 2048, nullptr, 1, nullptr, 0);
    Serial.printf("[HALL] pulse counter on GPIO%d%s, pole pairs %d\n", HALL_INPUT_PIN,
                  HALL_LOOPBACK ? " (bench loopback on the sync pin: expect 2 edges/s)" : "",
                  HALL_POLE_PAIRS);
  } else {
    Serial.println("[HALL] pulse counter setup failed");
  }
  xTaskCreatePinnedToCore(BmsTask, "BmsTask", 8192, nullptr, 1, &BmsTaskHandle, 0);
#endif
  xTaskCreatePinnedToCore(DashTask, "DashTask", 4096, nullptr, 1, &DashTaskHandle, 0);
  xTaskCreatePinnedToCore(RideCharacterizationTask, "RideChar1Task", 4096, &rideChar1Config, 1, &RideChar1TaskHandle, 1);
#if ENABLE_IMU2
  xTaskCreatePinnedToCore(RideCharacterizationTask, "RideChar2Task", 4096, &rideChar2Config, 1, &RideChar2TaskHandle, 1);
#endif
}

void loop() {
  vTaskDelete(nullptr);
}
