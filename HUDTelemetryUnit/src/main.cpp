#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Arduino.h>
#include <Wire.h>
#include <esp_timer.h>
#include <math.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <Preferences.h>

// ============================================================
// SW-7 ESP32-S3 Firmware v0.4.0
// Dual-IMU deterministic acquisition + A7670X modem/GNSS + Pi sync pulse
// ============================================================

// ---- Makerfabs ESP32-S3 to A7670X UART and control pins (verified) ----
#define A7670X_RX_PIN 47
#define A7670X_TX_PIN 48
#define A7670X_PWRKEY_PIN 4
#define A7670X_RESET_PIN 5
#define MODEM_BAUD 115200

// ---- IMU 1: existing wiring, confirmed working on v0.3.0 ----
#define IMU1_SDA_PIN 8
#define IMU1_SCL_PIN 9

// ---- IMU 2: second I2C bus ----
// Confirmed against the Makerfabs ESP32-S3 4G LTE CAT1 A7670X schematic
// (V1.2 PDF, "Interface" sheet, connector J5/HEADER-13P): pins 7-8 are
// silkscreened IO17/I2C_SDA and IO18/I2C_SCL respectively.
#define IMU2_SDA_PIN 17
#define IMU2_SCL_PIN 18
#define ENABLE_IMU2 1

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
#define SYNC_PULSE_PIN 15

// ---- Acquisition parameters ----
// ISO 2631-1 weights whole-body vibration up to 80 Hz, so Nyquist alone
// requires >=160 Hz. 200 Hz gives clean margin above that without pushing
// the I2C bus or the consumer task.
#define IMU_SAMPLE_RATE_HZ 200
#define IMU_SAMPLE_PERIOD_TICKS pdMS_TO_TICKS(1000 / IMU_SAMPLE_RATE_HZ)
#define IMU_QUEUE_LENGTH 100
#define I2C_CLOCK_HZ 400000

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
volatile BmsSample latestBmsSample = {};
volatile GnssFix latestGnssFix = {};

static ImuTaskConfig imu1Config;
static ImuTaskConfig imu2Config;

TaskHandle_t ModemTaskHandle;
TaskHandle_t Imu1TaskHandle;
TaskHandle_t Imu2TaskHandle;
TaskHandle_t StatsTaskHandle;
TaskHandle_t SyncTaskHandle;
TaskHandle_t BmsTaskHandle;

volatile uint32_t imu1Dropped = 0;
volatile uint32_t imu2Dropped = 0;
volatile uint32_t imu1CharDropped = 0;
volatile uint32_t imu2CharDropped = 0;

QueueHandle_t imu1CharQueue;
QueueHandle_t imu2CharQueue;
volatile RideFeatures latestRideFeatures1 = {};
volatile RideFeatures latestRideFeatures2 = {};
static RideCharTaskConfig rideChar1Config;
static RideCharTaskConfig rideChar2Config;
TaskHandle_t RideChar1TaskHandle;
TaskHandle_t RideChar2TaskHandle;

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

  // Filter bandwidth: ISO 2631-1 requires content up to 80 Hz. The
  // library's narrower filter presets would attenuate exactly the band
  // this project needs, so the widest available bandwidth is set
  // explicitly rather than left at the library default.
  sensor->setFilterBandwidth(MPU6050_BAND_260_HZ);

  return true;
}

// ============================================================
// IMU acquisition task. One function drives both sensors via the
// config struct, so the 200 Hz timing path is written and tested once.
// No Serial I/O in this task - blocking on USB CDC output would eat
// directly into the sample period and defeat the point of measuring it.
// ============================================================
void ImuTask(void* pvParameters) {
  ImuTaskConfig* cfg = static_cast<ImuTaskConfig*>(pvParameters);
  uint32_t seq = 0;
  TickType_t lastWake = xTaskGetTickCount();

  for (;;) {
    if (*(cfg->ready_flag)) {
      sensors_event_t accel, gyro, temp;
      cfg->sensor->getEvent(&accel, &gyro, &temp);

      ImuSample sample;
      sample.sensor_id = cfg->sensor_id;
      sample.sequence = seq++;
      sample.timestamp_us = esp_timer_get_time();
      sample.ax = accel.acceleration.x;
      sample.ay = accel.acceleration.y;
      sample.az = accel.acceleration.z;
      sample.gx = gyro.gyro.x;
      sample.gy = gyro.gyro.y;
      sample.gz = gyro.gyro.z;

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
      Serial.printf("GNSS: %lu polls, %lu with a fix\n",
                    (unsigned long)gnssCount, (unsigned long)gnssValidCount);
      Serial.printf("BMS: connected=%s valid=%lu checksum_fail=%lu "
                    "disconnects=%lu reconnects=%lu dropped=%lu\n",
                    bmsConnected ? "yes" : "no", (unsigned long)bmsValidFrames,
                    (unsigned long)bmsChecksumFailures, (unsigned long)bmsDisconnectCount,
                    (unsigned long)bmsReconnectCount, (unsigned long)bmsDropped);
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
          f.speed_norm_index = (f.rms_mps2 * f.rms_mps2) / v;  // mean square / speed
          f.speed_used = v;
        } else {
          f.speed_norm_index = NAN;
          f.speed_used = NAN;
        }
        // Field-by-field, not *(cfg->result) = f: the compiler-generated
        // struct operator= is not volatile-qualified, so whole-struct
        // assignment through a volatile pointer does not compile.
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
    // Logged so the ESP32-side edge time can be cross-checked against
    // whatever the Pi records for the same transition.
    Serial.printf("[SYNC] pin=%s  t=%lld us\n", state ? "HIGH" : "LOW",
                  (long long)esp_timer_get_time());
    vTaskDelayUntil(&lastWake, pdMS_TO_TICKS(500));
  }
}

// ============================================================
// JBD BMS: frame validation and parsing
// ============================================================

// Frame layout: [0]=0xDD  [1]=register  [2]=status  [3]=data length N
//               [4 .. 4+N-1]=data  [4+N,4+N+1]=checksum (big-endian)
//               [4+N+2]=0x77 terminator
// Checksum = (0x10000 - sum(bytes[1..3] + data bytes)) & 0xFFFF. This
// formula is drawn from community-documented reverse-engineering of the
// JBD protocol, not a vendor datasheet - treat a persistent checksum
// failure as a signal to re-derive it from a freshly captured raw frame
// rather than assuming the frame itself is bad.
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

  uint16_t sum = packet[1] + packet[2] + packet[3];
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
    Serial.println("[BMS] frame failed length/checksum validation, discarded");
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

// Field order below is a WORKING HYPOTHESIS, revised after a live capture
// on 04 Sep 2026 against the actual module. The originally assumed
// 13-field SIMCom A76XX layout was wrong for this firmware: a real
// no-fix response came back as
//   +CGNSSINFO: ,,,,,,,,
// i.e. 9 comma-separated fields, not 13. That confirms the field COUNT
// but NOT the field ORDER - an all-empty response carries no positional
// evidence. The mapping assumed below is:
//   <mode>,<lat>,<N/S>,<lon>,<E/W>,<date>,<UTC-time>,<alt>,<speed>
//
// !! STILL NEEDS CONFIRMING AGAINST A WITH-FIX RESPONSE !! (outdoors,
// see the GNSS position-fix test in the methodology) before any of these
// values are trusted quantitatively - including the speed field's units
// (knots vs km/h are not yet known). Field count is checked defensively
// below, and the raw string is always logged alongside the parsed
// result, so a wrong mapping is recoverable from the log, not lost.
bool parseGnssInfo(const String& raw, GnssFix* out) {
  int start = raw.indexOf("+CGNSSINFO:");
  if (start == -1) {
    return false;
  }
  String body = raw.substring(start + strlen("+CGNSSINFO:"));
  body.trim();

  const int kExpectedFields = 9;
  String tokens[kExpectedFields];
  int n = splitFields(body, tokens, kExpectedFields);

  if (n < kExpectedFields) {
    Serial.printf("[GNSS] unexpected field count (%d, expected %d) - raw: %s\n",
                  n, kExpectedFields, body.c_str());
    return false;
  }

  out->timestamp_us = esp_timer_get_time();
  out->fix_mode = tokens[0].length() ? tokens[0].toInt() : 0;
  out->valid = out->fix_mode > 0 && tokens[1].length() > 0 && tokens[3].length() > 0;

  if (out->valid) {
    float lat = nmeaToDecimalDegrees(tokens[1]);
    if (tokens[2] == "S") lat = -lat;
    float lon = nmeaToDecimalDegrees(tokens[3]);
    if (tokens[4] == "W") lon = -lon;
    out->latitude_deg = lat;
    out->longitude_deg = lon;
    out->altitude_m = tokens[7].length() ? tokens[7].toFloat() : NAN;
    out->speed_reported = tokens[8].length() ? tokens[8].toFloat() : NAN;
  } else {
    out->latitude_deg = NAN;
    out->longitude_deg = NAN;
    out->altitude_m = NAN;
    out->speed_reported = NAN;
  }

  return true;
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

  GnssFix fix;
  if (parseGnssInfo(response, &fix)) {
    if (fix.valid) {
      Serial.printf("[GNSS] fix mode=%d lat=%.6f lon=%.6f alt=%.1fm speed=%.1f\n",
                    fix.fix_mode, fix.latitude_deg, fix.longitude_deg,
                    fix.altitude_m, fix.speed_reported);
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
#define MQTT_BROKER_HOST "test.mosquitto.org"
#define MQTT_BROKER_PORT 1883
#define MQTT_CLIENT_ID "sw7-esp32-telemetry"
#define MQTT_USERNAME ""  // leave empty if the broker does not require auth
#define MQTT_PASSWORD ""
#define MQTT_TOPIC "sw7/telemetry"
#define MQTT_KEEPALIVE_S 60
#define MQTT_PUBLISH_INTERVAL_MS 10000

volatile bool mqttConnected = false;
volatile uint32_t mqttPublishCount = 0;
volatile uint32_t mqttPublishFailures = 0;

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

// Runs the CMQTTSTART/ACCQ/CONNECT sequence once. Returns false (and
// leaves mqttConnected false) on the first step that fails, logging which
// step failed rather than failing silently.
bool mqttConnect() {
  String resp;

  if (!mqttSendCommand("AT+CMQTTSTART", "OK", 5000, &resp)) {
    Serial.print("[MQTT] CMQTTSTART failed: ");
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
  if (!mqttSendCommand(connCmd, "OK", 10000, &resp)) {
    Serial.print("[MQTT] CMQTTCONNECT failed (is MQTT_BROKER_HOST still a placeholder?): ");
    Serial.println(resp);
    return false;
  }

  Serial.println("[MQTT] Connected.");
  mqttConnected = true;
  return true;
}

// Publishes one payload to MQTT_TOPIC. Each of CMQTTTOPIC/CMQTTPAYLOAD
// expects the raw bytes to follow the command, not as a quoted argument -
// this is the standard SIMCom CMQTT pattern, distinct from the simple
// single-line AT commands used elsewhere in this file.
bool mqttPublish(const String& payload) {
  if (!mqttConnected) return false;

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
  if (!mqttSendCommand(pubCmd, "OK", 10000, &resp)) {
    Serial.print("[MQTT] CMQTTPUB failed: ");
    Serial.println(resp);
    mqttPublishFailures++;
    return false;
  }

  mqttPublishCount++;
  return true;
}

// Compact JSON combining the latest known state from every subsystem
// this project owns. Deliberately does NOT match the vac-work Cyber
// Security team's own JSON schema (their broker/credentials are not used
// here, per the note above) - this is this project's own telemetry
// payload, to whatever broker MQTT_BROKER_HOST is actually pointed at.
String buildTelemetryJson() {
  char buf[512];
  snprintf(buf, sizeof(buf),
           "{"
           "\"imu1\":{\"rms\":%.3f,\"std\":%.3f,\"p2p\":%.3f,\"crest\":%.3f,\"jerk\":%.3f,\"crossings\":%u},"
           "\"imu2\":{\"rms\":%.3f,\"std\":%.3f,\"p2p\":%.3f,\"crest\":%.3f,\"jerk\":%.3f,\"crossings\":%u},"
           "\"bms\":{\"v\":%.2f,\"i\":%.2f,\"soc\":%u,\"checksum_ok\":%s},"
           "\"gnss\":{\"valid\":%s,\"lat\":%.6f,\"lon\":%.6f,\"speed\":%.1f}"
           "}",
           latestRideFeatures1.rms_mps2, latestRideFeatures1.std_mps2,
           latestRideFeatures1.peak_to_peak_mps2, latestRideFeatures1.crest_factor,
           latestRideFeatures1.mean_abs_jerk_mps3, (unsigned)latestRideFeatures1.threshold_crossings,
           latestRideFeatures2.rms_mps2, latestRideFeatures2.std_mps2,
           latestRideFeatures2.peak_to_peak_mps2, latestRideFeatures2.crest_factor,
           latestRideFeatures2.mean_abs_jerk_mps3, (unsigned)latestRideFeatures2.threshold_crossings,
           latestBmsSample.pack_voltage_v, latestBmsSample.current_a,
           (unsigned)latestBmsSample.soc_pct, latestBmsSample.checksum_ok ? "true" : "false",
           latestGnssFix.valid ? "true" : "false", latestGnssFix.latitude_deg,
           latestGnssFix.longitude_deg, latestGnssFix.speed_reported);
  return String(buf);
}

void ModemTask(void* pvParameters) {
  Serial1.begin(MODEM_BAUD, SERIAL_8N1, A7670X_RX_PIN, A7670X_TX_PIN);

  pinMode(A7670X_RESET_PIN, OUTPUT);
  digitalWrite(A7670X_RESET_PIN, LOW);
  pinMode(A7670X_PWRKEY_PIN, OUTPUT);
  digitalWrite(A7670X_PWRKEY_PIN, HIGH);
  delay(3000);
  digitalWrite(A7670X_PWRKEY_PIN, LOW);
  delay(5000);

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
    Serial.println("[MQTT] Initial connect failed - will not retry automatically this run. "
                    "Check MQTT_BROKER_HOST/port/credentials in main.cpp.");
  }

  Serial.println("==============================");
  Serial.println("Sequence complete. Entering pass-through mode.");
  Serial.println("Type AT commands below freely:");

  unsigned long lastGnssPoll = millis() - 3000;
  unsigned long lastMqttPublish = millis() - MQTT_PUBLISH_INTERVAL_MS;
  for (;;) {
    while (Serial.available()) {
      Serial1.write(static_cast<uint8_t>(Serial.read()));
    }
    if (millis() - lastGnssPoll >= 3000) {
      lastGnssPoll = millis();
      pollAndParseGnss();
    }
    if (mqttConnected && millis() - lastMqttPublish >= MQTT_PUBLISH_INTERVAL_MS) {
      lastMqttPublish = millis();
      String payload = buildTelemetryJson();
      if (!mqttPublish(payload)) {
        Serial.println("[MQTT] publish failed");
      }
    }
    while (Serial1.available()) {
      Serial.write(static_cast<uint8_t>(Serial1.read()));
    }
    vTaskDelay(pdMS_TO_TICKS(1));
  }
}

// ============================================================
// Setup / loop
// ============================================================
void setup() {
  Serial.begin(115200);

  const unsigned long serialWaitStart = millis();
  while (!Serial && millis() - serialWaitStart < 3000) {
    delay(100);
  }
  Serial.printf("[BOOT] PSRAM: found=%s size=%u bytes free=%u bytes\n",
                psramFound() ? "yes" : "no",
                (unsigned)ESP.getPsramSize(),
                (unsigned)ESP.getFreePsram());
  Serial.printf("[BOOT] Flash: size=%u bytes\n", (unsigned)ESP.getFlashChipSize());

  Serial.println("\nSW-7 ESP32-S3 Firmware v0.4.0");
  Serial.println("==================================");
  Serial.println("System booted: ESP32-S3");
  Serial.println("Status: ONLINE\n");

  Serial.printf("Flash size:        %u bytes\n", ESP.getFlashChipSize());
  Serial.printf("Free heap (SRAM):  %u bytes\n", ESP.getFreeHeap());
  Serial.printf("PSRAM size:        %u bytes\n", ESP.getPsramSize());
  Serial.printf("Free PSRAM:        %u bytes\n", ESP.getFreePsram());
  Serial.println();

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
  float imu2MagScale = loadOrCalibrateMagScale("imu2", &mpu2, imu2Ready);
  Serial.println();

  imu1Queue = xQueueCreate(IMU_QUEUE_LENGTH, sizeof(ImuSample));
  imu2Queue = xQueueCreate(IMU_QUEUE_LENGTH, sizeof(ImuSample));
  gnssQueue = xQueueCreate(20, sizeof(GnssFix));
  bmsQueue = xQueueCreate(20, sizeof(BmsSample));
  imu1CharQueue = xQueueCreate(RIDE_CHAR_QUEUE_LENGTH, sizeof(ImuSample));
  imu2CharQueue = xQueueCreate(RIDE_CHAR_QUEUE_LENGTH, sizeof(ImuSample));

  imu1Config = {0, imu1Queue, imu1CharQueue, &mpu1, &imu1Ready};
  imu2Config = {1, imu2Queue, imu2CharQueue, &mpu2, &imu2Ready};
  rideChar1Config = {0, imu1CharQueue, &latestRideFeatures1, imu1MagScale};
  rideChar2Config = {1, imu2CharQueue, &latestRideFeatures2, imu2MagScale};

  selfTestRideFeatures();

  xTaskCreatePinnedToCore(ModemTask, "ModemTask", 4096, nullptr, 1, &ModemTaskHandle, 0);

  xTaskCreatePinnedToCore(ImuTask, "Imu1Task", 4096, &imu1Config, 3, &Imu1TaskHandle, 1);
  xTaskCreatePinnedToCore(ImuTask, "Imu2Task", 4096, &imu2Config, 3, &Imu2TaskHandle, 1);
  xTaskCreatePinnedToCore(StatsTask, "StatsTask", 4096, nullptr, 2, &StatsTaskHandle, 1);
  xTaskCreatePinnedToCore(SyncTask, "SyncTask", 2048, nullptr, 2, &SyncTaskHandle, 1);
  xTaskCreatePinnedToCore(BmsTask, "BmsTask", 8192, nullptr, 1, &BmsTaskHandle, 0);
  xTaskCreatePinnedToCore(RideCharacterizationTask, "RideChar1Task", 4096, &rideChar1Config, 1, &RideChar1TaskHandle, 1);
  xTaskCreatePinnedToCore(RideCharacterizationTask, "RideChar2Task", 4096, &rideChar2Config, 1, &RideChar2TaskHandle, 1);
}

void loop() {
  vTaskDelete(nullptr);
}
