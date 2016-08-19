import unittest
import numpy as np
from GPy.kern import Linear, RBF
from Orange.data import Table, Domain, ContinuousVariable, DiscreteVariable
from Orange.MONROE.gppreprocess import GPTransformDiscrete


class TestGPPreprocess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.domain = Domain([ContinuousVariable("c1"),
                             DiscreteVariable("d1", ("0", "1"))])
        cls.data = Table(cls.domain, np.array([[1, 1], [0, 0], [0.5, 0]]))

    def test_gptransformdiscrete(self):
        transformer = GPTransformDiscrete()
        new_data = transformer(self.data)
        np.testing.assert_array_equal(new_data.X[:, 0], self.data.X[:, 0])
        np.testing.assert_array_equal(new_data.X[:, 1], np.array([1, -1, -1]))
        self.assertNotEqual(self.domain, new_data.domain)

    def test_from_table(self):
        transformer = GPTransformDiscrete()
        new_data = transformer(self.data)
        data = self.data.from_table(new_data.domain, self.data)
        np.testing.assert_array_equal(data.X[:, 1], np.array([1, -1, -1]))
