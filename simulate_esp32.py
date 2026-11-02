"""ESP32 sensor simulator for the MotorWatch API.

Sends a POST to /api/sensor-data/ every 2 seconds, cycling through three
scenarios (30 readings each) with small random noise on every value.

Usage:
    python simulate_esp32.py

Stop with Ctrl+C.
"""

import random
import time

import requests

API_URL = "http://127.0.0.1:8000/api/sensor-data/"
INTERVAL_SECONDS = 2.0
READINGS_PER_SCENARIO = 30
NOISE = {"temperature": 0.8, "current": 0.4, "vibration": 0.15}

SCENARIOS = [
    {
        "name": "Healthy",
        "start": {"temperature": 45.0, "current": 1.5, "vibration": 1.5},
        "end": {"temperature": 45.0, "current": 1.5, "vibration": 1.5},
    },
    {
        "name": "Bearing fault",
        "start": {"temperature": 55.0, "current": 2.6, "vibration": 2.0},
        "end": {"temperature": 75.0, "current": 2.6, "vibration": 5.0},
    },
    {
        "name": "Overload/overheat",
        "start": {"temperature": 80.0, "current": 2.6, "vibration": 2.5},
        "end": {"temperature": 92.0, "current": 3.4, "vibration": 2.5},
    },
]


def build_reading(scenario, reading_index):
    progress = reading_index / max(READINGS_PER_SCENARIO - 1, 1)
    reading = {}
    for sensor in ("temperature", "current", "vibration"):
        start = scenario["start"][sensor]
        end = scenario["end"][sensor]
        base = start + (end - start) * progress
        noise = random.uniform(-NOISE[sensor], NOISE[sensor])
        reading[sensor] = round(base + noise, 2)
    return reading


def main():
    print(f"Simulating ESP32 -> {API_URL}")
    print("Press Ctrl+C to stop.\n")

    scenario_index = 0
    reading_in_scenario = 0

    try:
        while True:
            scenario = SCENARIOS[scenario_index]
            reading = build_reading(scenario, reading_in_scenario)
            label = f"[{scenario['name']}] #{reading_in_scenario + 1}"

            try:
                response = requests.post(API_URL, json=reading, timeout=5)
            except requests.RequestException as exc:
                print(f"{label} {reading} -> request failed: {exc}")
            else:
                if response.status_code == 201:
                    data = response.json()
                    print(
                        f"{label} T={reading['temperature']:>6} "
                        f"A={reading['current']:>6} V={reading['vibration']:>6} "
                        f"-> {data['predicted_condition']} "
                        f"(alert={data['is_alert']}, confidence={data['confidence']})"
                    )
                    if data.get("note"):
                        print(f"    note: {data['note']}")
                else:
                    print(
                        f"{label} {reading} -> HTTP {response.status_code}: {response.text}"
                    )

            reading_in_scenario += 1
            if reading_in_scenario >= READINGS_PER_SCENARIO:
                reading_in_scenario = 0
                scenario_index = (scenario_index + 1) % len(SCENARIOS)
                print(
                    f"\n--- switching scenario: {SCENARIOS[scenario_index]['name']} ---\n"
                )

            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped by user.")


if __name__ == "__main__":
    main()
