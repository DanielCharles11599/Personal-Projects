# lab_utils_multi.py and lab_utils_common.py as well as the data itself were provided by DeepLearning.AI on Coursera

import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import SGDRegressor
from sklearn.preprocessing import StandardScaler
from lab_utils_multi import load_house_data
from lab_utils_common import dlc

# Loading the data into our arrays
x_train, y_train = load_house_data()
x_features = ["size (square meters)", "bedrooms", "floors", "age"]


# Normalize the training data
scaler = StandardScaler()
x_norm = scaler.fit_transform(x_train)
print(f"Peak to Peak range by column in Raw x: {np.ptp(x_train, axis = 0)}")
print(f"Peak to Peak range by column in Normalized x: {np.ptp(x_norm, axis = 0)}")


#Create the regression model and fit it to the data
sgdr = SGDRegressor(max_iter = 1000)
sgdr.fit(x_norm, y_train)
print(sgdr)
print(f"Number of iterations completed: {sgdr.n_iter_}, number of weight updates: {sgdr.t_}")
print("")


# Display the new, normalized parameters
b_norm = sgdr.intercept_
w_norm = sgdr.coef_
print(f"model parameters:                   w: {w_norm}, b: {b_norm}")
print("")


# Making predictions based on our regression model
y_pred_sgd = sgdr.predict(x_norm)
y_pred = np.dot(x_norm, w_norm) + b_norm
print(f"Prediction using np.dot() and sgdr.predict match: {(y_pred == y_pred_sgd).all()}")
print(f"Prediction on training set: \n{y_pred[:4]}")
print(f"Target values: \n{y_train[:4]}")
print("")


fig,ax = plt.subplots(1, 4, figsize = (12, 3), sharey = True)
for i in range(len(ax)):
    ax[i].scatter(x_train[:,i], y_train, label = "Target")
    ax[i].set_xlabel(x_features[i])
    ax[i].scatter(x_train[:,i], y_pred, color = dlc["dlorange"], label = "Predict")
ax[0].set_ylabel("Price")
ax[0].legend()
fig.suptitle("Target vs. Prediction using z-score normalized model")
plt.show()
