import numpy as np
from scipy import stats

import AnyQt
AnyQt.selectapi("pyqt5")

from Orange.distance import Euclidean
from Orange.regression.base_regression import LearnerRegression, ModelRegression
from Orange.widgets import gui
from Orange.widgets.settings import Setting
from Orange.widgets.utils.owlearnerwidget import OWBaseLearner



class ParametricNNLearner(LearnerRegression):
    def __init__(self, cutoff=None, aggregation='mean', weighting='linear', preprocessors=()):
        super().__init__(preprocessors)
        self.cutoff = cutoff
        self.aggregation = aggregation
        self.weighting = weighting

    def fit_storage(self, data):
        return ParametricModel(self.preprocess(data), self.cutoff, self.aggregation, self.weighting)


class ParametricModel(ModelRegression):
    def __init__(self, train_data, cutoff=None, aggregation='mean', weighting='linear'):
        self.train_data = train_data
        self.cutoff = cutoff
        self.aggregation = aggregation
        self.weighting = weighting

    def predict_storage(self, data):
        print(self.cutoff, self.aggregation, self.weighting)
        results = np.zeros((len(data),))
        for i, row in enumerate(data):
            d = Euclidean(self.train_data, row)
            a = np.hstack((d, self.train_data._Y))
            if self.cutoff:
                a = a[a[:, 0] < self.cutoff]
            if not a.size:
                a = np.array([[1., 0.]])
            agg = {
                'mean': lambda x: np.sum(x[:, 0] * x[:, 1]) / np.sum(x[:, 0]),
                'median': lambda x: np.median(x[:, 1]),
                'sum': lambda x: np.sum(x[:, 0] * x[:, 1])
            }[self.aggregation]
            weight = {
                'none': lambda _: 1.,
                'linear': lambda x: x,
            }[self.weighting]
            a[:, 0] = weight(a[:, 0])
            results[i] = agg(a)
        return results

ParametricNNLearner.__returns__ = ParametricModel


class OWParametricNN(OWBaseLearner):
    name = "Parametric nearest-neighbour"
    description = "Parametric learner based on the nearest neighbour"
    #icon = "icons/LogisticRegression.svg"
    priority = 60

    LEARNER = ParametricNNLearner

    cutoff = Setting(0)

    aggregations = ['mean', 'sum', 'median']
    aggregation = Setting(0)

    weightings = ['none', 'linear']
    weighting = Setting(1)

    def add_main_layout(self):
        box = gui.widgetBox(self.controlArea, box=True)
        self.cutoff_spin = gui.spin(box, self, "cutoff", 0., 10000, step=0.001, spinType=float, decimals=3, label="Cutoff")
        self.aggregation_combo = gui.comboBox(box, self, "aggregation", label="Aggregation",
                                              items=self.aggregations)
        self.weighting_combo = gui.comboBox(box, self, "weighting", label="Instance weight",
                                            items=self.weightings)

    def create_learner(self):
        return ParametricNNLearner(self.cutoff or None,
                                   self.aggregations[self.aggregation],
                                   self.weightings[self.weighting])

if __name__ == "__main__":
    import Orange
    iris = Orange.data.Table("housing")
    m = ParametricNNLearner(cutoff=1, aggregation='mode', weighting='none')(iris[:-1])
    p = m(iris[-1])
    print(p)
