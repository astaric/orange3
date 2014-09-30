# coding=utf8
from collections import defaultdict
import numpy as np
from numpy import dot, exp, ones
import sklearn.cluster
from Orange.data.discretization import DiscretizeTable
from Orange.feature.discretization import EqualFreq


def initialize_random(conts, k):
    mu = np.zeros((k, len(conts)))
    sigma = np.zeros((k, len(conts)))
    for i, (c, cw) in enumerate(conts):
        w = np.random.random((len(c), k))
        w /= w.sum(axis=1)[:, None]

        c = c[:, 0] if i == 0 else c[:, 1]

        for j in range(k):
            mu1 = np.dot(w[:, j] * cw, c) / (w[:, j] * cw).sum()
            cn = c - mu1
            sigma1 = np.sum(cn ** 2 * w[:, j] * cw, axis=0) / (w[:, j] * cw).sum()

            mu[j, i] = mu1
            sigma[j, i] = sigma1

    return mu, sigma


def em(conts, k, nsteps=30, window_size=1):
    """
    k expected classes,
    m data points,
    each with dim dimensions
    """
    dim = len(conts)

    np.random.seed(42)
    # Initialize parameters
    priors = np.ones(k) / k

    means, covars = initialize_random(conts, k)

    w = [np.empty((k, len(c[0]),)) for c in conts]
    active = ones(k, dtype=np.bool)

    for i in range(1, nsteps + 1):
        for l, (c, cw) in enumerate(conts):
            lower = l - window_size if l - window_size >= 0 else None
            upper = l + window_size + 1 if l + window_size + 1 <= dim else None
            dims = slice(lower, upper)
            active_dim = min(l, window_size)

            x = c

            # E step
            for j in range(k):
                if any(np.abs(covars[j, dims]) < 1e-15):
                    active[j] = 0

                if active[j]:
                    det = covars[j, dims].prod()
                    inv_covars = 1. / covars[j, dims]
                    xn = x - means[j, dims]
                    factor = (2.0 * np.pi) ** (x.shape[1]/ 2.0) * det ** 0.5
                    w[l][j] = priors[j] * np.exp(np.sum(xn * inv_covars * xn, axis=1) * -.5) / factor
                else:
                    w[l][j] = 0
            w[l][active] /= w[l][active].sum(axis=0)

            # M step
            n = np.sum(w[l], axis=1)
            priors = n / np.sum(n)
            for j in range(k):
                if n[j]:
                    mu = np.dot(w[l][j, :] * cw, x[:, active_dim]) / (w[l][j, :] * cw).sum()

                    xn = x[:, active_dim] - mu
                    sigma = np.sum(xn ** 2 * w[l][j], axis=0) / (w[l][j, :] * cw).sum()

                    if np.isnan(mu).any() or np.isnan(sigma).any():
                        return w, means, covars, priors
                else:
                    active[j] = 0
                    mu = 0.
                    sigma = 0.
                means[j, l] = mu
                covars[j, l] = sigma

    # w = np.zeros((k, m))
    # for j in range(k):
    #     if active[j]:
    #         det = covars[j].prod()
    #         inv_covars = 1. / covars[j]
    #         xn = X - means[j]
    #         factor = (2.0 * np.pi) ** (xn.shape[1] / 2.0) * det ** 0.5
    #         w[j] = priors[j] * exp(-.5 * np.sum(xn * inv_covars * xn, axis=1)) / factor
    # w[active] /= w[active].sum(axis=0)

    return w, means, covars, priors


def create_contingencies(X):
    window_size = 1
    dim = len(X.domain)

    X_ = DiscretizeTable(X, method=EqualFreq(n=10))
    vals = [[tuple(map(str.strip, v.strip('[]()<>=').split(','))) for v in var.values]
            for var in X_.domain]
    m = [{i: (float(v[0]) if len(v) == 1 else (float(v[0]) + (float(v[1]) - float(v[0])) / 2))
          for i, v in enumerate(val)} for val in vals]

    conts = [defaultdict(float) for i in range(len(X_.domain))]
    for i, r in enumerate(X_):
        row = tuple(m[vi].get(v) for vi, v in enumerate(r))
        for l in range(len(X_.domain)):
            lower = l - window_size if l - window_size >= 0 else None
            upper = l + window_size + 1 if l + window_size + 1 <= dim else None
            dims = slice(lower, upper)
            active_dim = min(l, window_size)

            conts[l][row[dims]] += 1

    conts = [zip(*c.items()) for c in conts]

    return [(np.array(c), np.array(cw)) for c, cw in conts]

