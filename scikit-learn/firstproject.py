import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier


from sklearn import metrics
data=pd.read_csv("motor_datanew.csv")
print(data.head())
x = data[["Temperature", "Current", "Vibration"]]
y = data[["Status"]]
x_train, x_test, y_train, y_test = train_test_split(x,
                                                     y, 
                                                     test_size=0.4, 
                                                     random_state=42,
                                                     stratify=y)

knn= KNeighborsClassifier(n_neighbors=3)
knn.fit(x_train, y_train)
predictions = knn.predict(x_test)
print(predictions)
print(metrics.accuracy_score(y_test, predictions))
temperature = float(input("Temperature: "))
current = float(input("Current: "))
vibration = float(input("Vibration: "))
new_motor = [[temperature, current, vibration]]
print(knn.predict(new_motor))