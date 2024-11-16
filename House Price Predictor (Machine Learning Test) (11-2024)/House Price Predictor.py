# Please note that the lab_utils_uni.py and lab_utils_uni.py files were NOT created by me and were provided by DeepLearning.AI
# This project will constantly be updated as I progress further through Machine Learning concepts

import math, copy
import numpy as np
import matplotlib.pyplot as plt
from lab_utils_uni import plt_intuition, plt_stationary, plt_update_onclick, soup_bowl
from lab_utils_uni import plt_house_x, plt_contour_wgrad, plt_divergence, plt_gradients


def compute_cost(x, y, w, b):
    m = x.shape[0] # Can use m = len(x_train) instead

    cost_sum = 0

    for i in range(m):
        f_wb = w * x[i] + b
        cost = (f_wb - y[i]) ** 2
        cost_sum += cost

    total_cost = (1 / (2 * m)) * cost_sum

    return total_cost


def compute_gradient(x, y, w, b):
    m = len(x)

    dj_dw = 0 # The gradients of the cost functions for parameter w
    dj_db = 0 # The gradients of the cost functions for parameter b

    for i in range(m):
        f_wb = w * x[i] + b
        dj_dw_i = (f_wb - y[i]) * x[i]
        dj_db_i = (f_wb - y[i])
        dj_dw += dj_dw_i
        dj_db += dj_db_i

    dj_dw = dj_dw / m
    dj_db = dj_db / m

    return dj_dw, dj_db
    

def gradient_descent(x, y, w_in, b_in, alpha, num_iters):
    # Arrays to hold all previous values to be used for graphing later
    J_history = []
    w_history = []

    # Initialise w and b parameters with the initial values
    b = b_in
    w = w_in

    for i in range(num_iters):
        dj_dw, dj_db = compute_gradient(x, y, w, b)

        temp_b = b - alpha * dj_db
        temp_w = w - alpha * dj_dw

        b = temp_b
        w = temp_w

        # Saves the cost value after each iteration
        if i < 100000:
            J_history.append(compute_cost(x, y, w, b))
            w_history.append([w,b])

    return w, b, J_history, w_history


def show_graphs(x_train, y_train, J_history, w_history):
    plt_intuition(x_train, y_train)
    plt.close("all")

    fig, ax, dyn_items, = plt_stationary(x_train, y_train)
    updater = plt_update_onclick(fig, ax, x_train, y_train, dyn_items)

    soup_bowl()

    # Shows the graph for the history of the Cost value over iterations
    fig, (ax1,ax2) = plt.subplots(1, 2, constrained_layout = True, figsize = (12,4))
    ax1.plot(J_history[:100])
    ax2.plot(1000 + np.arange(len(J_history[1000:])), J_history[1000:])
    ax1.set_title("Cost vs. iteration(start)"); ax2.set_title("Cost vs. iteration(end)")
    ax1.set_ylabel("Cost"); ax2.set_ylabel("Cost")
    ax1.set_xlabel("Iteration Step"); ax2.set_xlabel("Iteration Step")
    plt.show()

    # Shows the divergence of the parameters w and b
    plt_divergence(w_history, J_history, x_train, y_train)
    plt.show()

    
def main():
    # Both input variables and targets are stored as one-dimensional NumpPy arrays
    x_train = np.array([1.0, 1.7, 2.0, 2.5, 3.0, 3.2])
    y_train = np.array([250, 300, 480, 430, 630, 730])
    print(f"Input Variables (In 100 square meters): {x_train}")
    print(f"Target Price (In thousands of Rands: {y_train}")
    print("")
    print("")

    w_init = 0
    b_init = 0

    iterations = 10000

    temp_alpha = 1.0e-2

    w_final, b_final, J_history, w_history = gradient_descent(x_train, y_train, w_init, b_init, temp_alpha, iterations)

    print(f"(w,b) found by gradient descent: ({w_final:8.4f},{b_final:8.4f})")
    print("")


    show_graphs_choice = input("Show graphical data? (y/n): ")
    if show_graphs_choice.lower() == "y":
        show_graphs(x_train, y_train, J_history, w_history)
    else:
        exit()




if __name__ == "__main__":
    main()
