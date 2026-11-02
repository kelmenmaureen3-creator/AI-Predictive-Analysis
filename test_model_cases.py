"""API test cases for the MotorWatch backend.

Requires the Django dev server to be running:

    python manage.py runserver

Usage:

    python test_model_cases.py
    python test_model_cases.py --delay 1.5   # pause between cases (watch the dashboard)
"""

import argparse
import sys
import time

import requests

API_URL = "http://127.0.0.1:8000/api/sensor-data/"
LATEST_URL = "http://127.0.0.1:8000/api/latest-predictions/"
REQUEST_TIMEOUT = 10

# name, temperature, current, vibration -> expected outcome
CASES = [
    ("healthy typical", 45, 1.5, 1.5, "Healthy"),
    ("healthy low-end", 28, 0.9, 0.5, "Healthy"),
    ("healthy upper edge", 64, 2.2, 2.7, "Healthy"),
    ("warning temp", 75, 1.5, 1.5, "Warning"),
    ("warning current", 45, 2.6, 1.5, "Warning"),
    ("warning vibration", 45, 1.5, 3.5, "Warning"),
    ("warning all", 75, 2.6, 3.5, "Warning"),
    ("fault temp", 92, 1.5, 1.5, "Fault"),
    ("fault current", 45, 3.3, 1.5, "Fault"),
    ("fault vibration", 45, 1.5, 5.5, "Fault"),
    ("fault all", 92, 3.3, 5.5, "Fault"),
    ("motor off", 25, 0, 0, "Healthy"),
    ("invalid temperature", "abc", 1.5, 1.5, "HTTP 400"),
]


def run_case(session, case):
    name, temperature, current, vibration, expected = case
    invalid = expected == "HTTP 400"
    payload = {
        "temperature": temperature,
        "current": current,
        "vibration": vibration,
    }

    print("=" * 64)
    print(f"Case      : {name}")
    print(f"Sent      : temperature={temperature}, current={current}, "
          f"vibration={vibration}")
    print(f"Expected  : {expected}")

    try:
        response = session.post(API_URL, json=payload, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        print(f"Actual    : request failed ({exc})")
        print("Result    : FAIL")
        return False

    if invalid:
        print(f"HTTP      : {response.status_code} (expected 400)")
        print(f"Body      : {response.text}")
        passed = response.status_code == 400
        print(f"Result    : {'PASS' if passed else 'FAIL'}")
        return passed

    if response.status_code != 201:
        print(f"HTTP      : {response.status_code} (expected 201)")
        print(f"Body      : {response.text}")
        print("Result    : FAIL")
        return False

    data = response.json()
    actual = data.get("predicted_condition")
    print(f"Actual    : {actual}")
    print(f"is_alert  : {data.get('is_alert')}")
    print(f"confidence: {data.get('confidence')}")
    print(f"note      : {data.get('note')}")
    passed = actual == expected
    print(f"Result    : {'PASS' if passed else 'FAIL'}")
    return passed


def main():
    parser = argparse.ArgumentParser(
        description="POST sensor cases to the running Django API and check "
                    "the predicted condition."
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="seconds to wait between cases (default: 0)",
    )
    args = parser.parse_args()

    try:
        requests.get(LATEST_URL, timeout=5)
    except requests.RequestException as exc:
        print(f"ERROR: Django server is not running at {LATEST_URL} ({exc})")
        print("Start it with: python manage.py runserver")
        sys.exit(1)

    session = requests.Session()
    results = []

    for index, case in enumerate(CASES):
        results.append(run_case(session, case))
        if args.delay and index < len(CASES) - 1:
            time.sleep(args.delay)

    passed = sum(results)
    failed = len(results) - passed
    print("=" * 64)
    print(f"SUMMARY: {passed}/{len(results)} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
