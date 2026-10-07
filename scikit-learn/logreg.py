import numpy as np
from sklearn import datasets 
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score

bc = datasets.load_breast_cancer()
x = bc.data
y = bc.target
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)
log_reg = LogisticRegression()
log_reg.fit(x_train, y_train)
y_pred = log_reg.predict(x_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy: {accuracy}")