import math

# Operating bands for the motor:
#   max          -> upper limit of Healthy; above it is a non-critical
#                   violation (Warning)
#   critical_max -> upper limit of Warning; strictly above it is critical
#                   (Fault)
SAFE_RANGES = {
    "temperature": {"min": 0, "max": 65, "critical_max": 85},     # degC
    "current": {"min": 0, "max": 2.25, "critical_max": 3.0},      # A
    "vibration": {"min": 0, "max": 2.8, "critical_max": 4.5},     # mm/s
}

# Sensors whose warning limit is inclusive: a reading exactly equal to "max"
# is already a Warning (vibration: 2.8 mm/s and up). Temperature and current
# use a strict comparison, so exactly 65 degC / 2.25 A stay Healthy.
# Low current (motor off or idling) is never treated as a fault.
INCLUSIVE_MAX = {"vibration"}


def check_hard_limits(temperature, current, vibration):
    readings = {
        "temperature": temperature,
        "current": current,
        "vibration": vibration,
    }

    violations = []
    critical = False

    for name, value in readings.items():
        limits = SAFE_RANGES[name]

        try:
            value = float(value)
        except (TypeError, ValueError):
            violations.append(f"{name} is not a valid number")
            critical = True
            continue

        if math.isnan(value) or math.isinf(value):
            violations.append(f"{name} is not a valid number (NaN/inf)")
            critical = True
            continue

        above_max = (
            value >= limits["max"] if name in INCLUSIVE_MAX else value > limits["max"]
        )

        if value < limits["min"]:
            violations.append(f"{name} {value} below minimum {limits['min']}")
        elif value > limits["critical_max"]:
            violations.append(
                f"{name} {value} above critical limit {limits['critical_max']}"
            )
            critical = True
        elif above_max:
            bound = "at or above" if name in INCLUSIVE_MAX else "above"
            violations.append(f"{name} {value} {bound} safe maximum {limits['max']}")

    return {
        "violations": violations,
        "critical": critical,
        "has_violation": bool(violations),
    }
