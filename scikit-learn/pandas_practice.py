import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
data=pd.read_csv("https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv")
print(data.head())
print(data.tail())
print(data.shape)