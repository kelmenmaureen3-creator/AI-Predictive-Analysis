import seaborn as sns
import matplotlib.pyplot as plt
iris = sns.load_dataset("iris")
print(iris.head())
sns.scatterplot(
    data=iris,
    x="sepal_length",
    y="petal_length",
    hue="species"
)

plt.show()