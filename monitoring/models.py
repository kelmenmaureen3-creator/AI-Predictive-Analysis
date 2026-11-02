from django.db import models


class MotorPrediction(models.Model):
    temperature = models.FloatField()
    current = models.FloatField()
    vibration = models.FloatField()
    predicted_condition = models.CharField(max_length=20)  # Healthy / Warning / Fault
    is_alert = models.BooleanField(default=False)
    confidence = models.FloatField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp} - {self.predicted_condition}"
