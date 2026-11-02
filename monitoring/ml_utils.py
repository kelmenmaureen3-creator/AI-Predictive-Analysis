"""Inference helpers for the trained Random Forest model.

The model file is produced by a separate training pipeline and may not be
present yet - Django must still start without it.
"""

import math
import os

# The model was trained on these features, in this order. Always feed rows
# in exactly this order.
FEATURE_ORDER = ["temperature", "current", "vibration"]

# Integer class index -> human readable condition.
# map_label() also accepts models that already return string labels.
LABEL_MAP = {0: "Healthy", 1: "Warning", 2: "Fault"}

# Inferred from the model's split thresholds - these are NOT confirmed
# training ranges. Replace them with the real training data ranges from the
# teammate who trained the model before relying on the OOD check.
TRAINING_RANGE = {
    "temperature": {"min": 30, "max": 90},
    "current": {"min": 0, "max": 3.5},
    "vibration": {"min": 0, "max": 20},
}

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "ml_model", "motor_model.pkl"
)


class ModelNotAvailableError(RuntimeError):
    """Raised when inference is requested but the model file is missing."""


# Module level cache: None = not loaded yet, object = loaded model.
_model = None
_model_loaded = False


def _get_model():
    """Return the cached model, loading it on first use.

    Returns None while the .pkl file does not exist, without raising, so the
    backend can run in threshold-only mode.
    """
    global _model, _model_loaded

    if _model_loaded:
        return _model
    if not os.path.isfile(MODEL_PATH):
        # Not cached - the file may be dropped in later without a restart.
        return None

    import joblib

    _model = joblib.load(MODEL_PATH)
    _model_loaded = True
    return _model


def model_available():
    """True when a loadable model file exists."""
    return _get_model() is not None


def map_label(raw_label):
    """Normalise a raw model output into a condition string.

    Handles integer labels (0/1/2), float labels (0.0/1.0/2.0) and string
    labels ("Healthy"/"Warning"/"Fault").
    """
    if isinstance(raw_label, str):
        candidate = raw_label.strip()
        if candidate in LABEL_MAP.values():
            return candidate
        try:
            value = float(candidate)
        except ValueError:
            return candidate
    else:
        try:
            value = float(raw_label)
        except (TypeError, ValueError):
            return str(raw_label)

    if math.isfinite(value) and value == int(value):
        mapped = LABEL_MAP.get(int(value))
        if mapped is not None:
            return mapped
    return str(raw_label)


def is_out_of_distribution(temperature, current, vibration):
    """True only when a value sits ABOVE its TRAINING_RANGE max.

    Values below the training minimum are deliberately NOT treated as
    out-of-distribution: a cool or idling motor just lands in a region the
    model never saw, which is harmless, so such a reading must never
    downgrade its condition. Only readings hotter/faster/louder than
    anything in the training data are suspicious enough to count.
    (NaN / non-numeric input stays out-of-distribution - it is invalid
    data, not a safe low reading.)
    """
    readings = {
        "temperature": temperature,
        "current": current,
        "vibration": vibration,
    }
    for feature, limits in TRAINING_RANGE.items():
        value = readings[feature]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return True
        if math.isnan(value) or math.isinf(value):
            return True
        if value > limits["max"]:
            return True
    return False


def predict_condition(temperature, current, vibration):
    """Run the model and return (condition, confidence).

    Raises ModelNotAvailableError when the model file is missing.
    confidence is None when the model exposes no predict_proba().
    """
    model = _get_model()
    if model is None:
        raise ModelNotAvailableError(
            f"ML model file not found at {MODEL_PATH}. "
            "Supply the trained model or run in threshold-only mode."
        )

    import pandas as pd

    values = {
        "temperature": temperature,
        "current": current,
        "vibration": vibration,
    }
    # The model was trained on a DataFrame, so hand it one back - named
    # columns let the estimator validate the feature order itself.
    features = pd.DataFrame(
        [[values[name] for name in FEATURE_ORDER]], columns=FEATURE_ORDER
    )

    raw_prediction = model.predict(features)[0]
    condition = map_label(raw_prediction)

    confidence = None
    predict_proba = getattr(model, "predict_proba", None)
    if predict_proba is not None:
        probabilities = list(predict_proba(features)[0])
        classes = list(getattr(model, "classes_", range(len(probabilities))))
        index = None
        for position, class_label in enumerate(classes):
            if class_label == raw_prediction or map_label(class_label) == condition:
                index = position
                break
        if index is None:
            index = max(range(len(probabilities)), key=lambda i: probabilities[i])
        confidence = float(probabilities[index])

    return condition, confidence
