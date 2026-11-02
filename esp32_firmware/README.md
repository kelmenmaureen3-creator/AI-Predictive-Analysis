# MotorWatch ESP32 Firmware

`motorwatch/motorwatch.ino` reads three sensors on an ESP32 and POSTs JSON to
the Django backend (`POST /api/sensor-data/`) every 2 seconds.

## Required Arduino libraries

Install via Arduino IDE → **Sketch → Include Library → Manage Libraries**:

| Library | Version | Used for |
|---|---|---|
| **OneWire** (Paul Stoffregen) | latest | DS18B20 1-Wire bus |
| **DallasTemperature** (Miles Burton) | 3.x/4.x | DS18B20 readings in °C |
| **Adafruit MPU6050** | latest | MPU6050 accelerometer |
| **Adafruit Unified Sensor** | latest | dependency of the above (sensor event API) |
| **ArduinoJson** | **7.x** | request body + response parsing |

Provided by the ESP32 Arduino core (no install needed): `WiFi.h`,
`HTTPClient.h`, `Wire.h`.

Board package: **ESP32 Arduino core** (board: *ESP32 Dev Module*).

## Configuration

Edit the `CONFIG` block at the top of `motorwatch.ino`:

```cpp
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL = "http://192.168.1.xx:8000/api/sensor-data/";
const unsigned long SEND_INTERVAL_MS = 2000;
```

Serial monitor: **115200 baud**.

## Wiring

| ESP32 pin | Connects to | Notes |
|---|---|---|
| **GPIO 4** | DS18B20 **data** (yellow) | external **4.7 kΩ pull-up** to 3.3 V |
| **3.3 V** | DS18B20 **VCC** (red), MPU6050 **VCC** | 3.3 V rail |
| **5 V** (VIN/VUSB) | ACS712 module **VCC** | needed for the correct 2.5 V zero-level and 185 mV/A sensitivity |
| **GND** | DS18B20 **GND** (black), ACS712 **GND**, MPU6050 **GND**, buzzer **−** | all grounds common |
| **GPIO 34** | ACS712 **OUT** via voltage divider | divider: `ACS OUT ─ 10k ─ GPIO34 ─ 10k ─ GND` (÷2, so max 5 V out becomes 2.5 V at the pin); GPIO 34 is input-only / ADC1 |
| **GPIO 21** | MPU6050 **SDA** | I2C data |
| **GPIO 22** | MPU6050 **SCL** | I2C clock |
| **GPIO 25** | active buzzer **+** | use a transistor/NPN driver if the buzzer draws more than ~20 mA; buzzer **−** to GND |

Motor line goes through the ACS712 module's screw terminals (as marked on the
module), not through the ESP32.

## Behaviour

- **Temperature** – DS18B20 in °C; a `-127 °C` (disconnected) reading skips the
  send and prints an error.
- **Current** – zero-offset measured at startup for 1 s **with the motor off**,
  then 100 ms RMS windows (5 mains cycles) averaged over 4 windows.
- **Vibration** – velocity RMS in **mm/s**: ~1 kHz sampling for 500 ms, DC
  removal, leaky integrator (~10 Hz high-pass) while integrating acceleration
  to velocity, m/s → mm/s, then RMS. **Approximate — calibrate against a
  reference vibration meter.**
- **Response** – `is_alert: true` switches the buzzer on, otherwise off.
- Wi-Fi auto-reconnects, HTTP timeout is 3 s, timing uses `millis()` (only the
  sensor conversions themselves block, and each is bounded).
