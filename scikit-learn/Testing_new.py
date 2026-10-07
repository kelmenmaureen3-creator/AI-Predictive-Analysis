import pandas as pd
import joblib

# Load the trained model
model = joblib.load("random_forest_motor_model.pkl")

# Load new motor data
new_data = pd.read_csv("motor_datanew.csv")

# Prepare the data in the same format used during training
new_data["current"] = new_data["Current"] / 10.0
new_data["temperature"] = new_data["Temperature"]
new_data["vibration"] = new_data["Vibration"]

# Select the features
X_new = new_data[["temperature", "current", "vibration"]]

# Make predictions
predictions = model.predict(X_new)

# Add predictions to the dataset
new_data["Prediction"] = predictions

# Convert 0/1 into readable labels
new_data["Condition"] = new_data["Prediction"].map({
    0: "Healthy",
    1: "Faulty"
})

print(new_data)

# Save the results
new_data.to_csv("motor_predictions.csv", index=False)

print("\nPredictions saved to motor_predictions.csv")