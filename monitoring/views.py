from rest_framework.decorators import api_view
from rest_framework.response import Response

from .ml_utils import (
    ModelNotAvailableError,
    is_out_of_distribution,
    model_available,
    predict_condition,
)
from .models import MotorPrediction
from .serializers import MotorPredictionSerializer, SensorInputSerializer
from .thresholds import check_hard_limits

THRESHOLD_ONLY_NOTE = "ML model not loaded - threshold-only mode"
LOW_CONFIDENCE_THRESHOLD = 0.6


def _threshold_only(limits):
    """Fallback used when no model file is available."""
    condition = "Warning" if limits["has_violation"] else "Healthy"
    return condition, None, THRESHOLD_ONLY_NOTE


@api_view(['POST'])
def receive_sensor_data(request):
    serializer = SensorInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    temperature = serializer.validated_data['temperature']
    current = serializer.validated_data['current']
    vibration = serializer.validated_data['vibration']

    limits = check_hard_limits(temperature, current, vibration)

    if limits['critical']:
        # Layer 1: critical hard limit - never trust the model here.
        condition = 'Fault'
        confidence = None
        note = 'Critical: ' + '; '.join(limits['violations'])
    elif not model_available():
        condition, confidence, note = _threshold_only(limits)
    else:
        try:
            condition, confidence = predict_condition(temperature, current, vibration)
        except ModelNotAvailableError:
            # Model disappeared between the availability check and inference.
            condition, confidence, note = _threshold_only(limits)
        else:
            notes = []
            if condition == 'Healthy' and limits['has_violation']:
                # The thresholds always win over a "Healthy" model verdict:
                # any hard-limit violation (critical ones were already
                # handled above) means the reading cannot be Healthy.
                condition = 'Warning'
                notes.extend(limits['violations'])
            if condition == 'Healthy' and is_out_of_distribution(
                temperature, current, vibration
            ):
                condition = 'Warning'
                notes.append(
                    'Reading outside model training range - condition upgraded to Warning'
                )
            if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
                notes.append(f'Low model confidence ({confidence:.2f})')
            note = '; '.join(notes)

    prediction = MotorPrediction.objects.create(
        temperature=temperature,
        current=current,
        vibration=vibration,
        predicted_condition=condition,
        is_alert=condition == 'Fault',
        confidence=confidence,
        note=note,
    )

    output = MotorPredictionSerializer(prediction)
    return Response(output.data, status=201)


@api_view(['GET'])
def get_latest_predictions(request):
    predictions = MotorPrediction.objects.order_by('-timestamp')[:50]
    serializer = MotorPredictionSerializer(predictions, many=True)
    return Response(serializer.data)
