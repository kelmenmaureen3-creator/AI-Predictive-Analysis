from sklearn.datasets import load_iris

iris=load_iris()
print("No of samples:",iris.data.shape[0])
print("No of features:",iris.data.shape[1])
print("No of Targets:",len(iris.target_names))
print("Target Names:",iris.target_names)
print("Feature Names:",iris.feature_names)
print("First flower:",iris.data[99])
print(iris.target[99])
print(iris.target_names[iris.target[99]])