from django.contrib import admin

from .models import MotorPrediction


@admin.register(MotorPrediction)
class MotorPredictionAdmin(admin.ModelAdmin):
    list_display = (
        'timestamp',
        'temperature',
        'current',
        'vibration',
        'predicted_condition',
        'is_alert',
        'confidence',
        'note',
    )
    list_filter = ('predicted_condition', 'is_alert')
    ordering = ('-timestamp',)
