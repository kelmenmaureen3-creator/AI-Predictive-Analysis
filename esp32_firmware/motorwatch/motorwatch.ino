/*
 * MotorWatch - ESP32 sensor node for induction-motor predictive maintenance.
 *
 * Reads DS18B20 temperature (degC), ACS712-5A current (A) and MPU6050
 * vibration (velocity RMS, mm/s), prints everything to Serial and POSTs
 * JSON to the Django API every SEND_INTERVAL_MS over Wi-Fi.
 * The response field "is_alert" drives an active buzzer.
 *
 * Serial monitor: 115200 baud.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>

#include <OneWire.h>
#include <DallasTemperature.h>

#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

#include <ArduinoJson.h>

// ---------------------------------------------------------------------------
// CONFIG - fill in your own credentials
// ---------------------------------------------------------------------------
const char* WIFI_SSID = "RM213#BARAKAHOSTEL";
const char* WIFI_PASSWORD = "selenaleo";
const char* SERVER_URL = "http://192.168.100.186:8000/api/sensor-data/";
const bool TEST_MODE = true;  // true = send fixed fake readings, no sensors needed

const unsigned long SEND_INTERVAL_MS = 2000;
const unsigned long WIFI_RETRY_MS = 5000;
const unsigned long WIFI_CONNECT_TIMEOUT_MS = 15000;
const uint16_t HTTP_TIMEOUT_MS = 3000;

// ---------------------------------------------------------------------------
// PINS
// ---------------------------------------------------------------------------
const uint8_t PIN_ONEWIRE = 4;   // DS18B20 data (external 4.7k pull-up)
const uint8_t PIN_CURRENT = 34;  // ACS712 analog out (ADC1, input-only pin)
const uint8_t PIN_I2C_SDA = 21;  // MPU6050 SDA
const uint8_t PIN_I2C_SCL = 22;  // MPU6050 SCL
const uint8_t PIN_BUZZER = 25;   // active buzzer

// ---------------------------------------------------------------------------
// SENSOR CONSTANTS
// ---------------------------------------------------------------------------

// --- ACS712-5A (AC current) ------------------------------------------------
// The ACS712 is an AC-coupled Hall sensor: its output swings around VCC/2
// (about 2.5 V when the module is powered from 5 V) at 185 mV per amp, so
// raw readings must NEVER be averaged - only the RMS of the AC component
// (after removing the zero-offset) is meaningful.
//
// The module output can reach 5 V but an ESP32 pin tolerates 3.3 V max, so
// the output goes through a 1:1 resistor divider (e.g. 10k / 10k: ACS out -
// 10k - GPIO34 - 10k - GND). DIVIDER_RATIO = V_in / V_out = 2, and the ADC
// measures the divided voltage against a 3.3 V reference; multiplying back
// by DIVIDER_RATIO recovers the real module output, so sensitivity stays
// 185 mV/A.
const float ACS_SENSITIVITY_MV_PER_A = 185.0f;
const float ADC_REF_V = 3.3f;
const float DIVIDER_RATIO = 2.0f;
const unsigned long ACS_ZERO_CAL_MS = 1000;   // startup zero-offset window
const unsigned long ACS_SAMPLE_WINDOW_MS = 100;  // 5 cycles of 50 Hz mains
const uint32_t ACS_SAMPLE_PERIOD_US = 200;       // ~5 kHz sampling
const uint8_t CURRENT_RMS_WINDOWS = 4;  // average RMS over a few windows
                                        // (motor draws ~0.8 - 3 A, this
                                        // smooths single-cycle noise)

// --- MPU6050 vibration -----------------------------------------------------
const uint16_t VIB_SAMPLES = 500;            // 500 ms of samples
const uint32_t VIB_SAMPLE_PERIOD_US = 1000;  // ~1 kHz
const float VIB_SAMPLE_RATE_HZ = 1000000.0f / VIB_SAMPLE_PERIOD_US;
const float VIB_HP_CUTOFF_HZ = 10.0f;        // high-pass / leaky-integrator cutoff

// ---------------------------------------------------------------------------
// OBJECTS / STATE
// ---------------------------------------------------------------------------
OneWire oneWire(PIN_ONEWIRE);
DallasTemperature tempSensors(&oneWire);
Adafruit_MPU6050 mpu;

bool mpuOk = false;
float currentZeroOffsetV = 0.0f;
unsigned long lastSendMs = 0;
unsigned long lastWifiRetryMs = 0;

// ---------------------------------------------------------------------------
// TEMPERATURE (DS18B20)
// ---------------------------------------------------------------------------
float readTemperatureC() {
  // Blocking conversion, ~750 ms at the default 12-bit resolution - bounded,
  // never forever. DEVICE_DISCONNECTED_C (-127) means the sensor is missing.
  tempSensors.requestTemperatures();
  return tempSensors.getTempCByIndex(0);
}

// ---------------------------------------------------------------------------
// CURRENT (ACS712-5A) - RMS in amps
// ---------------------------------------------------------------------------
float readAcsOutputVolts() {
  const int raw = analogRead(PIN_CURRENT);
  const float pinVolts = (float)raw * (ADC_REF_V / 4095.0f);
  return pinVolts * DIVIDER_RATIO;  // undo the divider -> module output
}

void calibrateCurrentZero() {
  Serial.println("[ACS712] measuring zero-offset for 1 s - keep the motor OFF");
  double sum = 0.0;
  unsigned long samples = 0;
  const unsigned long start = millis();
  while (millis() - start < ACS_ZERO_CAL_MS) {
    sum += readAcsOutputVolts();
    samples++;
    delayMicroseconds(200);
  }
  currentZeroOffsetV = samples ? (float)(sum / samples) : 0.0f;
  Serial.printf("[ACS712] zero-offset = %.4f V (expect ~2.5 V)\n",
                currentZeroOffsetV);
}

float pushCurrentWindow(float rmsAmps) {
  static float history[CURRENT_RMS_WINDOWS];
  static uint8_t count = 0;
  static uint8_t next = 0;

  history[next] = rmsAmps;
  next = (next + 1) % CURRENT_RMS_WINDOWS;
  if (count < CURRENT_RMS_WINDOWS) count++;

  float sum = 0.0f;
  for (uint8_t i = 0; i < count; i++) sum += history[i];
  return sum / count;
}

float readCurrentRms() {
  // One 100 ms window = 5 full cycles of 50 Hz mains.
  double sumSq = 0.0;
  unsigned long samples = 0;
  const uint32_t windowEnd = micros() + ACS_SAMPLE_WINDOW_MS * 1000UL;
  while ((int32_t)(micros() - windowEnd) < 0) {
    const float ac = readAcsOutputVolts() - currentZeroOffsetV;
    sumSq += (double)ac * ac;
    samples++;
    delayMicroseconds(ACS_SAMPLE_PERIOD_US);
  }

  const float rmsVolts = samples ? (float)sqrt(sumSq / samples) : 0.0f;
  const float amps = rmsVolts / (ACS_SENSITIVITY_MV_PER_A / 1000.0f);
  return pushCurrentWindow(amps);
}

// ---------------------------------------------------------------------------
// VIBRATION (MPU6050) - VELOCITY RMS in mm/s
// ---------------------------------------------------------------------------
// Method (APPROXIMATE - calibrate against a reference vibration meter before
// trusting absolute values; relative trends are still useful):
//   1. Sample the 3-axis accelerometer at ~1 kHz for 500 ms.
//   2. Remove the DC offset by subtracting each axis' window mean (kills
//      gravity and sensor bias).
//   3. Integrate acceleration to velocity with a LEAKY INTEGRATOR:
//          v = v * (1 - 2*pi*fc*dt) + a * dt
//      The leak acts as a first-order high-pass at ~10 Hz while doing the
//      integration, so low-frequency drift cannot run away.
//   4. Take the magnitude of the 3 velocity components, convert m/s -> mm/s
//      (x1000) and compute the RMS over the whole window.
// This is an engineering approximation of a velocity probe (no ISO 10816
// band weighting, single-board MEMS sensor), so treat it as relative until
// it is calibrated against a reference instrument.
// ---------------------------------------------------------------------------
float readVibrationVelocityRms() {
  if (!mpuOk) return 0.0f;

  static float ax[VIB_SAMPLES];
  static float ay[VIB_SAMPLES];
  static float az[VIB_SAMPLES];

  uint32_t nextSample = micros();
  for (uint16_t i = 0; i < VIB_SAMPLES; i++) {
    while ((int32_t)(micros() - nextSample) < 0) {
      // ~1 kHz pacing (busy-wait, bounded to 500 ms)
    }
    nextSample += VIB_SAMPLE_PERIOD_US;
    sensors_event_t event;
    sensors_event_t gyroEvent, tempEvent;
mpu.getEvent(&event, &gyroEvent, &tempEvent);
    ax[i] = event.acceleration.x;  // m/s^2
    ay[i] = event.acceleration.y;
    az[i] = event.acceleration.z;
  }

  // DC offset removal (window mean per axis).
  float meanX = 0.0f, meanY = 0.0f, meanZ = 0.0f;
  for (uint16_t i = 0; i < VIB_SAMPLES; i++) {
    meanX += ax[i];
    meanY += ay[i];
    meanZ += az[i];
  }
  meanX /= VIB_SAMPLES;
  meanY /= VIB_SAMPLES;
  meanZ /= VIB_SAMPLES;

  // Leaky integrator: acceleration -> velocity, high-pass at ~10 Hz.
  const float dt = 1.0f / VIB_SAMPLE_RATE_HZ;
  const float leak = 2.0f * PI * VIB_HP_CUTOFF_HZ * dt;

  float vx = 0.0f, vy = 0.0f, vz = 0.0f;
  double sumSq = 0.0;
  for (uint16_t i = 0; i < VIB_SAMPLES; i++) {
    vx = vx * (1.0f - leak) + (ax[i] - meanX) * dt;
    vy = vy * (1.0f - leak) + (ay[i] - meanY) * dt;
    vz = vz * (1.0f - leak) + (az[i] - meanZ) * dt;
    const float velocityMmS = sqrtf(vx * vx + vy * vy + vz * vz) * 1000.0f;
    sumSq += (double)velocityMmS * velocityMmS;
  }

  return (float)sqrt(sumSq / VIB_SAMPLES);
}

// ---------------------------------------------------------------------------
// WI-FI
// ---------------------------------------------------------------------------
void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.printf("[WiFi] connecting to %s", WIFI_SSID);
  const unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED &&
         millis() - start < WIFI_CONNECT_TIMEOUT_MS) {
    delay(250);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[WiFi] connected, IP=%s\n",
                  WiFi.localIP().toString().c_str());
  } else {
    Serial.println("[WiFi] not connected yet - will keep retrying");
  }
}

bool ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  if (millis() - lastWifiRetryMs >= WIFI_RETRY_MS) {
    lastWifiRetryMs = millis();
    Serial.println("[WiFi] connection lost - reconnecting");
    WiFi.reconnect();
  }
  return false;
}

// ---------------------------------------------------------------------------
// HTTP
// ---------------------------------------------------------------------------
void sendReading(float temperature, float current, float vibration) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP] Wi-Fi down - reading not sent");
    return;
  }

  JsonDocument payload;
  payload["temperature"] = temperature;
  payload["current"] = current;
  payload["vibration"] = vibration;
  String body;
  serializeJson(payload, body);

  HTTPClient http;
  http.setConnectTimeout(HTTP_TIMEOUT_MS);
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  const int httpCode = http.POST(body);
  if (httpCode > 0) {
    Serial.printf("[HTTP] %d\n", httpCode);
    JsonDocument reply;
        if (deserializeJson(reply, http.getString()) == DeserializationError::Ok) {
      const bool alert = reply["is_alert"] | false;
      const float confidence = reply["confidence"] | -1.0f;
      digitalWrite(PIN_BUZZER, alert ? HIGH : LOW);
      Serial.printf("[API] condition=%s alert=%s confidence=%.3f note=%s\n",
                    reply["predicted_condition"] | "?",
                    alert ? "true" : "false",
                    confidence,
                    reply["note"] | "");
    } else {
      Serial.println("[HTTP] could not parse response JSON");
    }
  } else {
    Serial.printf("[HTTP] POST failed: %s\n",
                  http.errorToString(httpCode).c_str());
  }
  http.end();
}

// ---------------------------------------------------------------------------
// ARDUINO ENTRY POINTS
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("\n[Boot] MotorWatch ESP32 firmware");

  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);

  // DS18B20
  tempSensors.begin();
  if (tempSensors.getDeviceCount() == 0) {
    Serial.println("[DS18B20] no sensor found on GPIO 4");
  }

  // MPU6050
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  if (mpu.begin()) {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    // 94 Hz hardware anti-alias filter: keeps bearing-fault harmonics while
    // still filtering content above the 1 kHz sampling Nyquist limit.
    mpu.setFilterBandwidth(MPU6050_BAND_94_HZ);
    mpuOk = true;
    Serial.println("[MPU6050] found on SDA=21 SCL=22");
  } else {
    Serial.println("[MPU6050] NOT found - vibration will read 0");
  }

  // Full ~0-3.3 V input range so the divided ACS712 signal never clips.
  analogSetPinAttenuation(PIN_CURRENT, ADC_11db);

  connectWifi();
  calibrateCurrentZero();

  lastSendMs = millis() - SEND_INTERVAL_MS;  // first reading right away
}

void loop() {
  ensureWifi();

  if (millis() - lastSendMs < SEND_INTERVAL_MS) {
    delay(10);  // short, millis()-driven pacing - no long blocking delays
    return;
  }
  lastSendMs = millis();
    if (TEST_MODE) {
    Serial.println("[TEST_MODE] sending fixed reading 45 C, 1.5 A, 1.5 mm/s");
    sendReading(45.0f, 1.5f, 1.5f);
    return;
  }

  const float temperature = readTemperatureC();
  if (temperature == DEVICE_DISCONNECTED_C || temperature < -100.0f) {
    Serial.println(
        "[Temp] ERROR: DS18B20 disconnected (-127 C) - skipping send");
    return;
  }

  const float current = readCurrentRms();
  const float vibration = readVibrationVelocityRms();

  Serial.printf("[TX] temperature=%.2f C  current=%.3f A  vibration=%.3f mm/s\n",
                temperature, current, vibration);

  sendReading(temperature, current, vibration);
}
