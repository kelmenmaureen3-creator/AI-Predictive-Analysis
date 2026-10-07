import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib

#Load Dataset
df = pd.read_csv('industrial_motor_sensor_data_8000.csv')
df.columns = [c.replace('?C', 'C') for c in df.columns]

#Preprocess & Scale Parameters

df['current'] = df['Current (A)'] / 10.0
df['temperature'] = df['Temperature (C)']
df['vibration'] = df['Vibration (mm/s)']

# Binary Label Mapping: Healthy (0) vs Faulty (1)
label_map = {
    'normal': 0,     # Healthy
    'moderate': 1,   # Faulty (Warning/Degraded)
    'high': 1        # Faulty (Critical)
}

df['status'] = df['Label'].str.strip().str.lower().map(label_map)

# Drop any unmapped records
df = df.dropna(subset=['status'])

#Define Features and Labels

X = df[['temperature', 'current', 'vibration']]
y = df['status']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Train Binary Random Forest Classifier
rf = RandomForestClassifier(random_state=42)

param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [10, 20, None],
    'min_samples_split': [2, 5],
    'criterion': ['gini', 'entropy']
}

print("Training Binary Random Forest Model...")
grid_search = GridSearchCV(
    estimator=rf,
    param_grid=param_grid,
    cv=5,
    scoring='f1',
    n_jobs=-1
)

grid_search.fit(X_train, y_train)
best_model = grid_search.best_estimator_

#Evaluate Performance
y_pred = best_model.predict(X_test)

print("\n================ EVALUATION METRICS ================")
print(f"Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")
print("\nClassification Report:\n", classification_report(y_test, y_pred, target_names=['Healthy (0)', 'Faulty (1)']))
print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))
# Save  Model
joblib.dump(best_model, 'random_forest_motor_model.pkl')
print(f"\nTrained binary model saved successfully to: random_forest_motor_model.pkl")
