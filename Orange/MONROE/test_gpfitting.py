import unittest

import numpy as np
from GPy.kern import Coregionalize

from Orange.MONROE.gppreprocess import GPTransformDiscrete
from Orange.data import Table, Domain
from Orange.evaluation import MSE, TestOnTestData
from Orange.kernel import RBF, Linear
from Orange.regression import (LinearRegressionLearner, GPRegressionLearner,
                               RandomForestRegressionLearner)


# [grid_id, lat1, lon1, avg_speed, start, end, total, 4G, 3G, 2G, nos, 4gd, 2gd, nosd, static, full_mobile, tunnel | 3gd]
def get_data(cls_name, start=0, finish=0, split=150):
    data = Table("data/cov_all_netcom_oslo_stav_1.tab")
    cls_index = data.domain.index(cls_name)
    data_X = np.hstack((data.X[:, :cls_index], data.X[:, cls_index + 1:]))
    data_Y = data.X[:, cls_index]
    attrs = list(data.domain.attributes)
    class_var = attrs.pop(cls_index)
    if start < finish:
        data_X = data_X[:, start:finish]
        attrs = attrs[start:finish]
    new_domain = Domain(attrs, class_var)
    train_data = Table(new_domain, data_X[:split], data_Y[:split])
    test_data = Table(new_domain, data_X[split:], data_Y[split:])
    return train_data, test_data


def get_data_lon_lat(cls_name, split=150):
    data = Table("data/cov_all_netcom_oslo_stav_1.tab")
    print(len(data))
    cls_index = data.domain.index(cls_name)
    data_X = data.X[:, 1:3]
    data_Y = data.X[:, cls_index]
    attrs = list(data.domain.attributes)
    class_var = attrs.pop(cls_index)
    new_domain = Domain(attrs[1:3], class_var)
    train_data = Table(new_domain, data_X[:split], data_Y[:split])
    test_data = Table(new_domain, data_X[split:], data_Y[split:])
    return train_data, test_data


class TestGPRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.learners = [LinearRegressionLearner(),
                        RandomForestRegressionLearner(),
                        GPRegressionLearner()]

    def test_lon_lat(self):
        train_data, test_data = get_data_lon_lat("3gd")
        results = TestOnTestData(train_data, test_data, [GPRegressionLearner()])
        print(MSE(results))  # [  248.51425864   187.95407407  2876.60185185]

    def test_3gd(self):
        train_data, test_data = get_data("3gd")
        results = TestOnTestData(train_data, test_data, self.learners)
        print(MSE(results))  # [  248.51425864   187.95407407  2876.60185185]

    def test_3gd_remove_grid_id(self):
        train_data, test_data = get_data("3gd", 1, 17)
        results = TestOnTestData(train_data, test_data, self.learners)
        print(MSE(results))  # [  248.42523245   132.64675926  2876.60185185]

    def test_3gd_remove_grid_id_and_disc(self):
        # Objective : 827.5678901852518
        train_data, test_data = get_data("3gd", 1, 14)
        results = TestOnTestData(train_data, test_data, self.learners)
        print(MSE(results))  # [  248.42523245   384.64675926  2876.60185185]

    def test_3gd_with_lat_lon(self):
        train_data, test_data = get_data("3gd", 1, 3)
        results = TestOnTestData(train_data, test_data, self.learners)
        print(MSE(results))  # [ 12317.09964835   2800.97481481   2876.58650428]

    def test_3gd_with_tunnel(self):
        train_data, test_data = get_data("3gd", 16, 17)
        results = TestOnTestData(train_data, test_data, self.learners)
        print(MSE(results))  # [ 1841.60185185  1953.50176458  1877.18519375]

    def test_3gd_with_discrete_attrs(self):
        train_data, test_data = get_data("3gd", 14, 17)
        results = TestOnTestData(train_data, test_data, self.learners)
        print(MSE(results))  # [ 1878.8587963   1855.07034657  1845.91074726]

    def test_3gd_with_tunnel_lin(self):
        train_data, test_data = get_data("3gd", 16, 17)
        learners = self.learners + [GPRegressionLearner(Linear),
                                    GPRegressionLearner(Linear, preprocessors=[
                                        GPTransformDiscrete])]
        results = TestOnTestData(train_data, test_data, learners)
        print(MSE(results))  # [ 1841.60185185  1931.6769696   1877.18519375  2630.54458522  2867.08807996]

    def test_3gd_with_discrete_attrs_lin(self):
        train_data, test_data = get_data("3gd", 14, 17)
        learners = self.learners + [GPRegressionLearner(Linear),
                                    GPRegressionLearner(Linear, preprocessors=[
                                        GPTransformDiscrete])]
        results = TestOnTestData(train_data, test_data, learners)
        print(MSE(results))  # [ 1878.8587963   1854.43766528  1845.91074726  1857.39949722  2209.56636602]

    # yes!!!
    def test_3gd_rbf_lin(self):
        train_data, test_data = get_data("3gd")
        rbf_ad = [1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13]
        lin_ad = [14, 15, 16]
        kernel = RBF(rbf_ad) + Linear(lin_ad)    # 105, 78
        kernel = Linear(lin_ad) + RBF(rbf_ad)   # 69, 69
        learners = self.learners + [GPRegressionLearner(kernel),
                                    GPRegressionLearner(kernel, preprocessors=[
                                        GPTransformDiscrete])]
        results = TestOnTestData(train_data, test_data, learners)
        print(MSE(results))

    def test_3gb_coregionalized(self):
        train_data, test_data = get_data("3gd", 1, 13)
        print(train_data.domain)
        rbf_ad = [0, 1]
        kernel = RBF(len(rbf_ad), active_dims=rbf_ad) ** \
                 Coregionalize(2, output_dim=6, rank=5)
        learners = [GPRegressionLearner(kernel),
                    GPRegressionLearner(kernel, preprocessors=[
                        GPTransformDiscrete])]
        results = TestOnTestData(train_data, test_data, learners)
        print(MSE(results))
        self.assertFalse("TODO")
