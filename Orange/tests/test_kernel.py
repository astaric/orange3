import unittest

import numpy as np
from GPy.kern import RBF as GP_RBF, Linear as GP_Linear
from GPy.models import GPRegression
from sklearn.svm import SVC

from Orange.kernel import (RBF, Linear, all_kernels, Kernel, gpkernel_sum,
                           gpkernel_mul, GPKernel)


class TestKernel(unittest.TestCase):
    def setUp(self):
        self.X = np.array([[-1, -1], [-2, -1], [1, 1], [2, 1]])
        self.y = np.array([1, 1, 2, 2])

    def test_abstract_kernel(self):
        self.assertRaises(TypeError, Kernel)
        self.assertRaises(TypeError, GPKernel)

    def test_use_svm_rbf(self):
        gp_kernel = GP_RBF(2)
        gp_l = SVC(kernel=gp_kernel.K)
        gp_l.fit(self.X, self.y)

        kernel = RBF(range(2))
        l = SVC(kernel=kernel)
        l.fit(self.X, self.y)
        self.assertEqual(gp_l.predict([[-0.8, -1]]), l.predict([[-0.8, -1]]))

    def test_use_gp_rbf(self):
        gp_kernel = GP_RBF(2)
        gp_l = GPRegression(self.X, self.y[:, None], kernel=gp_kernel)
        gp_l.optimize()
        gp_mu, _ = gp_l.predict(np.array([[-0.8, -1]]))

        kernel = RBF(range(2))
        l = GPRegression(self.X, self.y[:, None], kernel=kernel)
        l.optimize()
        mu, var = l.predict(np.array([[-0.8, -1]]))
        self.assertAlmostEqual(gp_mu[0, 0], mu[0, 0], 5)

    def test_kernel_input_dim(self):
        n = self.X.shape[1]
        kernel1 = RBF(range(n))
        self.assertEqual(kernel1.input_dim, n)
        kernel1.active_dimensions = range(n // 2)
        self.assertEqual(kernel1.input_dim, n // 2)
        kernel2 = RBF(range(n // 2))
        self.assertEqual(kernel2.input_dim, kernel1.input_dim)
        np.testing.assert_array_equal(kernel1(self.X), kernel2(self.X))

    def test_kernel_add(self):
        gp_kernel = GP_RBF(1) + GP_Linear(1) + GP_RBF(1)
        kernel = RBF(range(1)) + Linear(range(1)) + RBF(range(1))
        gp_C = gp_kernel.K(self.X)
        C = kernel(self.X)
        np.testing.assert_array_equal(gp_C, C)

    def test_kernel_prod(self):
        gp_kernel = GP_RBF(1) * GP_Linear(1) * GP_RBF(1)
        kernel = RBF(range(1)) * Linear(range(1)) * RBF(range(1))
        gp_C = gp_kernel.K(self.X)
        C = kernel(self.X)
        np.testing.assert_array_equal(gp_C, C)

    def test_kernel_sum(self):
        k1 = RBF(range(1)) + Linear(range(1)) + RBF(range(1))
        k2 = gpkernel_sum([RBF(range(1)), Linear(range(1)), RBF(range(1))])
        np.testing.assert_array_equal(k1(self.X), k2(self.X))
        self.assertIsNone(gpkernel_sum([]))

    def test_kernel_mul(self):
        k1 = RBF(range(1)) * Linear(range(1)) * RBF(range(1))
        k2 = gpkernel_mul([RBF(range(1)), Linear(range(1)), RBF(range(1))])
        np.testing.assert_array_equal(k1(self.X), k2(self.X))
        self.assertIsNone(gpkernel_mul([]))

    def test_all_kernels(self):
        for kernel in all_kernels:
            inst = kernel(range(10))
            name = inst.kernel_name
            self.assertIsInstance(inst, Kernel)
            sum_kern = kernel([0]) + kernel([0]) + kernel([0])
            self.assertIsInstance(sum_kern, Kernel)
            self.assertEqual(sum_kern.kernel_name,
                             "{}_sum_{}_sum_{}".format(name, name, name))
            prod_kern = kernel([0]) * kernel([0]) * kernel([0])
            self.assertIsInstance(prod_kern, Kernel)
            self.assertEqual(prod_kern.kernel_name,
                             "{}_prod_{}_prod_{}".format(name, name, name))


class TestGPKernel(unittest.TestCase):
    def test_gpkernel(self):
        from GPy.kern import (RBF, Exponential, Matern32, Matern52, MLP, Poly,
                              Linear, Bias, Cosine, White)
        kernels = (("RBF", RBF), ("Exponential", Exponential), ("Bias", Bias),
                   ("Matern 3/2", Matern32), ("Matern 5/2", Matern52),
                   ("Linear", Linear), ("White noise", White), ("MLP", MLP),
                   ("Polynomial", Poly), ("Cosine", Cosine))
        kernel = RBF(1, name="neki")
        kernel = MLP(1, name="nekiMLP")

        for kernel in kernels:
            kernel = kernel[1](1)
            print(kernel.active_dims)

        kernels = (kernel,)
        for kernel in kernels:
            print("------------------------")
            for prop, value in kernel.__dict__.items():
                if prop[0] != "_":
                    # getattr(kernel, prop)
                    print(prop)  # , value)

        kernel.ARD = True
        kernel.active_dims = 2
        kernel.input_dim = 2
        kernel.name = "bla"
        for param in kernel.parameters:
            print(param._name, getattr(kernel, param._name).values[0])
            getattr(kernel, param._name).fix()
            getattr(kernel, param._name).constrain_bounded(0.1, 0.5)
