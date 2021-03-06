from math import sqrt
from numba import jit
import numpy as np

@jit
def hayashi_yoshida_cross_corr(times_X, values_X, times_Y, values_Y, lag=0.):
    """
    This implementation of Lead-Lag Cross-Correlation is based
    on the algorithm given in "High Frequency Lead/lag Relationships
    Empirical Facts" by N. Huth and F. Abergel, on page 6
    """
    n_X = len(times_X)
    n_Y = len(times_Y)
    # init variables
    j = 1
    r_X_sq = 0.
    r_Y_sq = 0.
    r_XY = 0.

    for i in range(1, n_X):
        t = times_X[i]
        t_old = times_X[i-1]
        if t == t_old: continue

        r_X = values_X[i] - values_X[i-1]
        r_X_sq += r_X * r_X

        while j < n_Y:
            if times_Y[j] == times_Y[j-1]:
                j += 1
            elif times_Y[j] - lag <= t_old:
                r_Y = values_Y[j] - values_Y[j-1]
                r_Y_sq += r_Y * r_Y
                j += 1
            else:
                break
        k = j
        while k < n_Y:
            if times_Y[k] == times_Y[k-1]:
                k += 1
            elif times_Y[k-1] - lag < t:
                r_Y = values_Y[k] - values_Y[k-1]
                r_XY += r_X * r_Y
                k += 1
            else:
                break
    while j < n_Y:
        r_Y = values_Y[j] - values_Y[j-1]
        r_Y_sq += r_Y * r_Y
        j += 1

    return r_XY / sqrt(r_X_sq * r_Y_sq)
