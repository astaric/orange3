# coding=utf8
import numpy as np
from numpy import dot, exp, ones


def em(X, k, nsteps=30):
    """
    k expected classes,
    m data points,
    each with dim dimensions
    """
    m, dim = X.shape

    np.random.seed(42)
    # Initialize parameters
    priors = np.ones(k) / k
    means = np.random.random((k, dim))
    covars = ones((k, dim)) * 10000
    w = np.empty((k, m))

    for i in range(1, nsteps+1):
        active = ones(k, dtype=np.bool)
        print("Step ", i)
        for l in range(X.shape[1]):
            dims = slice(l-1 if l > 0 else None, l+2 if l < dim - 1 else None)
            active_dim = 1 if l > 0 else 0
            x = X[:, dims]

            # E step
            for j in range(k):
                if any(np.abs(covars[j, dims]) < 1e-15):
                    active[j] = 0

                if active[j]:
                    det = covars[j, dims].prod()
                    inv_covars = 1. / covars[j, dims]
                    xn = x - means[j, dims]
                    factor = (2.0 * np.pi) ** (x.shape[1] / 2.0) * det ** 0.5
                    w[j] = priors[j] * exp(-.5 * np.sum(xn * inv_covars * xn, axis=1)) / factor
                else:
                    w[j] = 0
            w[active] /= w[active].sum(axis=0)

            # M step
            n = np.sum(w, axis=1)
            priors = n / np.sum(n)
            for j in range(k):
                if n[j]:
                    mu = np.dot(w[j, :], x[:, active_dim]) / n[j]

                    xn = x[:, active_dim] - mu
                    sigma = np.sum(xn ** 2 * w[j], axis=0) / n[j]

                    if np.isnan(mu).any() or np.isnan(sigma).any():
                        return w, means, covars, priors
                else:
                    active[j] = 0
                    mu = 0.
                    sigma = 0.
                means[j, l] = mu
                covars[j, l] = sigma

    w = np.zeros((k, m))
    for j in range(k):
        if active[j]:
            det = covars[j].prod()
            inv_covars = 1. / covars[j]
            xn = X - means[j]
            factor = (2.0 * np.pi) ** (xn.shape[1] / 2.0) * det ** 0.5
            w[j] = priors[j] * exp(-.5 * np.sum(xn * inv_covars * xn, axis=1)) / factor
        w[active] /= w[active].sum(axis=0)

    return w, means, covars, priors
