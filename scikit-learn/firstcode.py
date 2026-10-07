import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import matplotlib.pyplot as plt
from sklearn.tree import plot_tree
from sklearn.metrics import accuracy_score
from sklearn.metrics import classification_report

from sklearn.model_selection import train_test_split

data = pd.read_csv("motor_datanew.csv")
X = data[["Temperature", "Current", "Vibration"]]
y = data["Status"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestClassifier(n_estimators=100, max_depth=3, random_state=42)
model.fit(X_train, y_train)
temperature=float(input("Enter the temperature: "))
current=float(input("Enter the current: "))
vibration=float(input("Enter the vibration: "))
new_data=[[temperature, current, vibration]]
prediction=model.predict(new_data)
print(f"Prediction for new data: {prediction}")
importance = model.feature_importances_

for feature, value in zip(X.columns, importance):
    print(feature, value)
y_pred = model.predict(X_test)
print(y_pred)
print("Accuracy:", accuracy_score(y_test, y_pred))
classification_report = classification_report(y_test, y_pred)
print("Classification Report:")
print(classification_report)

