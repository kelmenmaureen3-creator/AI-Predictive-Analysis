import pandas as pd
import joblib

model = joblib.load("random_forest_motor_model.pkl")
temperature = float(input("Enter temperature (°C): "))
current = float(input("Enter current (A): "))
vibration = float(input("Enter vibration (mm/s): "))
new_data = pd.DataFrame({
    "temperature": [temperature],
    "current": [current / 10.0],
    "vibration": [vibration]
})
prediction = model.predict(new_data)
if prediction == 0:
    print("Motor condition: HEALTHY")
else:
    print("Motor condition: FAULTY")