import unittest

import numpy as np

from Orange.data import Table
from Orange.kernel import RBF, all_kernels
from Orange.regression import LinearRegressionLearner, GPRegressionLearner
from Orange.evaluation import CrossValidation, MSE, TestOnTrainingData


class TestGPRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.housing = Table('housing')
        cls.learner = GPRegressionLearner()

    def test_gpregression(self):
        learners = [LinearRegressionLearner(), self.learner]
        results = CrossValidation(self.housing, learners, k=3)
        mse = MSE(results)  # [ 23.77600204  14.49785997]
        self.assertGreater(mse[0], mse[1])

    def test_predict_single_instance(self):
        model = self.learner(self.housing)
        ins = self.housing[0]
        _ = model(ins)

    def test_predict_numpy(self):
        model = self.learner(self.housing)
        _ = model(self.housing.X)

    def test_kernels(self):
        for kernel in all_kernels:
            try:
                learner = GPRegressionLearner(kernel)
                model = learner(self.housing[:10])
                _ = model(self.housing[:10])
            except np.linalg.LinAlgError:
                pass

    def test_kernel_instance(self):
        kernel = RBF(range(self.housing.X.shape[1]))
        learners = [GPRegressionLearner(), GPRegressionLearner(kernel)]
        results = CrossValidation(self.housing, learners, k=3)
        _ = MSE(results)

    def test_kernel_active_dims_changed(self):
        kernel1 = RBF(range(self.housing.X.shape[1]))
        kernel2 = RBF(range(self.housing.X.shape[1]))
        kernel2.active_dimensions = range(3)
        learner1 = GPRegressionLearner(kernel1)
        learner2 = GPRegressionLearner(kernel2)
        results = TestOnTrainingData(self.housing[:100], [learner1, learner2])
        self.assertNotEqual(MSE(results)[0], MSE(results)[1])
