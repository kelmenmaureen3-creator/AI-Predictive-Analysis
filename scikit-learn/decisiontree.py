import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
import matplotlib.pyplot as plt
from sklearn.tree import plot_tree

from sklearn.model_selection import train_test_split

data = pd.read_csv("motor_datanew.csv")
print(data.columns)
print(data.head())
x = data[["Temperature","Current","Vibration"]]
y = data["Status"]

X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)
model= DecisionTreeClassifier(max_depth=3, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print(y_pred)

plt.figure(figsize=(12, 8))
plot_tree(model, feature_names=["Temperature", "Current", "Vibration"], class_names=["Normal", "Faulty"], filled=True)
plt.show()