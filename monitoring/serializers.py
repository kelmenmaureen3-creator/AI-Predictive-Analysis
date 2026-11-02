from rest_framework import serializers

from .models import MotorPrediction


class SensorInputSerializer(serializers.Serializer):
    temperature = serializers.FloatField()
    current = serializers.FloatField()
    vibration = serializers.FloatField()


class MotorPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MotorPrediction
        fields = '__all__'
