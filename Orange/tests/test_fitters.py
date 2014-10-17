from itertools import chain
from unittest import TestCase

import numpy as np

from Orange.classification.knn import KNNLearner
from Orange.classification.linear_regression import LinearRegressionLearner
from Orange.classification.logistic_regression import LogisticRegressionLearner
from Orange.classification.majority import MajorityFitter
from Orange.classification.naive_bayes import BayesLearner
from Orange.classification.softmax_regression import SoftmaxRegressionLearner
from Orange.classification.svm import SVMLearner
from Orange.data import Table, Domain, ContinuousVariable, DiscreteVariable


FEATURES = {
    'c1': (ContinuousVariable("c1"),
           [0.06, 0.3, 0.72, 0.43, 0.31, 0.05, 0.63, 0.42, 0.02, 0.55]),
    'c2': (ContinuousVariable("c2"),
           [0.1, 0.23, 0.64, 0.5, 0.22, 0.3, 0.18, 0.3, 0.36, 0.79]),
    'c3': (ContinuousVariable("c3"),
           [0.11, 0.11, 0.08, 0.08, 0.54, 0.34, 0.6, 0.82, 0.22, 0.88]),
    'd1': (DiscreteVariable("d1", values=["0", "1"]),
           [0., 0., 0., 0., 0., 1., 1., 1., 1., 1.]),
    'd2': (DiscreteVariable("d2", values=["0", "1", "2", "3"]),
           [0., 0., 1., 1., 2., 2., 2., 3., 3., 3.]),
    'd3': (DiscreteVariable("d3", values=["0", "1", "2", "3"]),
           [0., 0., 0., 0., 2., 2., 2., 3., 3., 3.]),
}


def create_dataset(features, classes, missing=()):
    vars, vals = zip(*map(FEATURES.get, features))
    class_vars, class_vals = zip(*map(FEATURES.get, classes))
    data = zip(*chain(vals, class_vals))

    table = Table(Domain(vars, class_vars), list(data))
    for x, y in missing:
        table[x, y] = np.nan

    return table


class FitterTests:
    def test_on_continuous_data(self):
        self.fit_predict_on_data(
            self.fitter.supports_continuous_features,
            create_dataset(['c1', 'c2', 'c3'], ['d1'])
        )

    def test_on_discrete_data(self):
        self.fit_predict_on_data(
            self.fitter.supports_discrete_features,
            create_dataset(['d1', 'd2', 'd3'], ['d1'])
        )

    def test_on_mixed_data(self):
        self.fit_predict_on_data(
            self.fitter.supports_discrete_features and
            self.fitter.supports_continuous_features,
            create_dataset(['c1', 'd1', 'c2', 'd2', 'c3', 'd3'], ['d1'])
        )

    def test_missing_continuous_values_in_features(self):
        data = create_dataset(['c1', 'c2', 'c3'], ['d1'],
                              missing=((0, 0), (0, 2), (1, 1), (2, 1)))

        self.fit_predict_on_data(
            self.fitter.supports_continuous_features,
            data
        )

    def test_all_missing_continuous_feature(self):
        data = create_dataset(['c1', 'c2', 'c3'], ['d1'],
                              missing=[(i, 0) for i in range(10)])

        self.fit_predict_on_data(
            self.fitter.supports_continuous_features,
            data
        )

    def test_missing_discrete_values_in_features(self):
        data = create_dataset(['d1', 'd2', 'd3'], ['d1'],
                              missing=((0, 0), (0, 2), (1, 1), (2, 1)))

        self.fit_predict_on_data(
            self.fitter.supports_discrete_features,
            data
        )

    def test_all_missing_discrete_feature(self):
        data = create_dataset(['d1', 'd2', 'd3'], ['d1'],
                              missing=[(i, 0) for i in range(10)])

        self.fit_predict_on_data(
            self.fitter.supports_discrete_features,
            data
        )

    def test_missing_values_in_class(self):
        data = create_dataset(['d1', 'd2', 'd3'], ['d1'],
                              missing=((0, 3), (1, 3), (3, 3), (7, 3)))

        self.fit_predict_on_data(
            self.fitter.supports_discrete_features,
            data
        )

    def test_all_missing_class(self):
        data = create_dataset(['d1', 'd2', 'd3'], ['d1'],
                              missing=[(i, 3) for i in range(10)])

        self.fit_predict_on_data(
            self.fitter.supports_discrete_features,
            data
        )

    def fit_predict_on_data(self, supported, data):
        if supported:
            model = self.fitter(data)
            predictions = model(data)
            self.assertEqual(len(predictions), len(data))
        else:
            with self.assertRaises(ValueError):
                self.fitter(data)
            self.skipTest("%s does not support input dataset" %
                          self.__class__.__name__)


class BayesTestCase(TestCase, FitterTests):
    fitter = BayesLearner()


class KNNTestCase(TestCase, FitterTests):
    fitter = KNNLearner()


class LinearRegressionTestCase(TestCase, FitterTests):
    fitter = LinearRegressionLearner()


class LogisticRegressionTestCase(TestCase, FitterTests):
    fitter = LogisticRegressionLearner()


class MajorityTestCase(TestCase, FitterTests):
    fitter = MajorityFitter()


class SoftmaxRegressionTestCase(TestCase, FitterTests):
    fitter = SoftmaxRegressionLearner()


class SVMLearnerTestCase(TestCase, FitterTests):
    fitter = SVMLearner()
