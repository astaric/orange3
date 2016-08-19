import sys
import inspect
from functools import reduce

import numpy as np
import GPy

__all__ = ["Kernel", "GPKernel", "GPStationaryKernel", "RBF", "Matern32",
           "Matern52", "Exponential", "Cosine", "RatQuad", "White", "Bias",
           "Periodic", "Linear", "Polynomial", "MLP", "Add", "Prod",
           "all_kernels", "gpkernel_sum", "gpkernel_mul"]


class Kernel:
    _kernel_name = "Kernel"

    def __init__(self):
        raise TypeError(
            "{} represents an abstract class and cannot "
            "be instantiated".format(self._kernel_name))

    def __call__(self, *args):
        return self.cov(*args)

    def cov(self, *args):
        raise NotImplementedError


class GPKernel(Kernel):
    _kernel_name = "GP Kernel"

    def cov(self, *args):
        return self.K(*args)

        # m.parameter_names()
        # m._param_array_

    @property
    def kernel_name(self):
        return self._kernel_name

    @kernel_name.setter
    def kernel_name(self, name):
        self._kernel_name = name
        self.name = name

    @property
    def active_dimensions(self):
        return self.active_dims

    @active_dimensions.setter
    def active_dimensions(self, active_dims):
        self.active_dims = active_dims
        self.input_dim = len(active_dims)
        self._all_dims_active = np.atleast_1d(active_dims).astype(int)

    def __add__(self, other):
        return Add([self, other])

    def __iadd__(self, other):
        return Add([self, other])

    def __mul__(self, other):
        return Prod([self, other])

    def __imul__(self, other):
        return Prod([self, other])


class GPStationaryKernel(GPKernel):
    _kernel_name = "Stationary Kernel"


class RBF(GPStationaryKernel, GPy.kern.RBF):
    _kernel_name = "RBF"

    def __init__(self, active_dims, variance=1, lengthscale=1, ARD=False):
        GPy.kern.RBF.__init__(
            self, len(active_dims), variance, lengthscale, ARD, active_dims,
            self.kernel_name)


class Matern32(GPStationaryKernel, GPy.kern.Matern32):
    _kernel_name = "Matern 3/2"

    def __init__(self, active_dims, variance=1, lengthscale=1, ARD=False):
        GPy.kern.Matern32.__init__(
            self, len(active_dims), variance, lengthscale, ARD, active_dims,
            self.kernel_name)


class Matern52(GPStationaryKernel, GPy.kern.Matern52):
    _kernel_name = "Matern 5/2"

    def __init__(self, active_dims, variance=1, lengthscale=1, ARD=False):
        GPy.kern.Matern52.__init__(
            self, len(active_dims), variance, lengthscale, ARD, active_dims,
            self.kernel_name)


class Exponential(GPStationaryKernel, GPy.kern.Exponential):
    _kernel_name = "Exponential"

    def __init__(self, active_dims, variance=1, lengthscale=1, ARD=False):
        GPy.kern.Exponential.__init__(
            self, len(active_dims), variance, lengthscale, ARD, active_dims,
            self.kernel_name)


class Cosine(GPStationaryKernel, GPy.kern.Cosine):
    _kernel_name = "Cosine"

    def __init__(self, active_dims, variance=1, lengthscale=1, ARD=False):
        GPy.kern.Cosine.__init__(
            self, len(active_dims), variance, lengthscale, ARD, active_dims,
            self.kernel_name)


class RatQuad(GPStationaryKernel, GPy.kern.RatQuad):
    _kernel_name = "Rational Quadratic"

    def __init__(self, active_dims, variance=1, lengthscale=1, power=2,
                 ARD=False):
        GPy.kern.RatQuad.__init__(
            self, len(active_dims), variance, lengthscale, power, ARD,
            active_dims, self.kernel_name)


class White(GPKernel, GPy.kern.White):
    _kernel_name = "White Noise"

    def __init__(self, active_dims, variance=1):
        GPy.kern.White.__init__(
            self, len(active_dims), variance, active_dims, self.kernel_name)


class Bias(GPKernel, GPy.kern.Bias):
    _kernel_name = "Bias"

    def __init__(self, active_dims, variance=1):
        GPy.kern.Bias.__init__(
            self, len(active_dims), variance, active_dims, self.kernel_name)


class Periodic(GPKernel, GPy.kern.StdPeriodic):
    _kernel_name = "Periodic"

    def __init__(self, active_dims, variance=1, period=None, lengthscale=None,
                 ARD1=False, ARD2=False):
        GPy.kern.StdPeriodic.__init__(
            self, len(active_dims), variance, period, lengthscale, ARD1, ARD2,
            active_dims, self.kernel_name)


class Linear(GPKernel, GPy.kern.Linear):
    _kernel_name = "Linear"

    def __init__(self, active_dims, variances=[1], ARD=False):
        GPy.kern.Linear.__init__(
            self, len(active_dims), variances, ARD, active_dims,
            self.kernel_name)


class Polynomial(GPKernel, GPy.kern.Poly):
    _kernel_name = "Polynomial"

    def __init__(self, active_dims, variance=1, scale=1, bias=1, order=3):
        GPy.kern.Poly.__init__(
            self, len(active_dims), variance, scale, bias, order, active_dims,
            self.kernel_name)


class MLP(GPKernel, GPy.kern.MLP):
    _kernel_name = "MLP"

    def __init__(self, active_dims, variance=1, weight_variance=1,
                 bias_variance=1, ARD=False):
        GPy.kern.MLP.__init__(
            self, len(active_dims), variance, weight_variance, bias_variance,
            ARD, active_dims, self.kernel_name)


class Add(GPKernel, GPy.kern.Add):
    def __init__(self, subkerns):
        name = "{}_sum_{}".format(subkerns[0].kernel_name,
                                  subkerns[1].kernel_name)
        GPy.kern.Add.__init__(self, subkerns, name)
        self.kernel_name = name


class Prod(GPKernel, GPy.kern.Prod):
    def __init__(self, subkerns):
        name = "{}_prod_{}".format(subkerns[0].kernel_name,
                                   subkerns[1].kernel_name)
        GPy.kern.Prod.__init__(self, subkerns, name)
        self.kernel_name = name


def gpkernel_sum(kernels):
    """
    Function sums all kernels in passed list of kernels.

    :param kernels: list of kernels
    :return: sum of kernels
    """
    if not kernels:
        return None
    return reduce(lambda x, y: x.copy() + y.copy(), kernels)


def gpkernel_mul(kernels):
    """
    Function multiplies all kernels in passed list of kernels.

    :param kernels: list of GPKernel instances
    :return: sum of kernels
    """
    if not kernels:
        return None
    return reduce(lambda x, y: x.copy() * y.copy(), kernels)


def get_all_kernels():
    return [m[1] for m in inspect.getmembers(sys.modules[__name__],
                                             inspect.isclass) if m[0] not
            in ("Kernel", "GPKernel", "GPStationaryKernel", "Add", "Prod")]


all_kernels = get_all_kernels()
