from django.urls import path

from . import views

urlpatterns = [
    path('sensor-data/', views.receive_sensor_data, name='receive_sensor_data'),
    path('latest-predictions/', views.get_latest_predictions, name='get_latest_predictions'),
]
