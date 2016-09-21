import numpy as np

from sklearn.neighbors.kd_tree import KDTree

from Orange.regression.base_regression import LearnerRegression, ModelRegression
from Orange.widgets import gui
from Orange.widgets.settings import Setting
from Orange.widgets.utils.owlearnerwidget import OWBaseLearner


class ParametricNNLearner(LearnerRegression):
    def __init__(self, cutoff=None, aggregate_function=None,
                 weight_function=None, preprocessors=()):
        super().__init__(preprocessors)
        self.cutoff = cutoff
        self.aggregate_function = aggregate_function
        self.weight_function = weight_function

    def fit(self, X, Y, W=None):
        kd_tree = KDTree(X)
        return ParametricModel(kd_tree, Y,
                               self.cutoff,
                               self.aggregate_function, self.weight_function)


class ParametricModel(ModelRegression):
    def __init__(self, kd_tree, values,
                 cutoff=None, aggregate_function=None, weight_function=None):
        self.kd_tree = kd_tree
        self.values = values
        self.cutoff = cutoff
        self.aggregate_function = aggregate_function or "0."
        self.weight_function = weight_function or "1."

    def predict(self, X):
        results = np.zeros((len(X),))
        indices, distances = self.kd_tree.query_radius(X, r=self.cutoff,
                                                       return_distance=True)

        g = dict(np.__dict__)

        for i, (distance, ind) in enumerate(zip(distances, indices)):
            g["distance"] = distance[:, None]
            g["value"] = self.values[ind, None]
            weight = np.zeros((len(distance), 1))
            weight[:] = eval(self.weight_function, g)
            g["weight"] = weight

            results[i] = eval(self.aggregate_function, g)
        return np.nan_to_num(results)

ParametricNNLearner.__returns__ = ParametricModel


class OWParametricNN(OWBaseLearner):
    name = "Parametric nearest-neighbour"
    description = "Parametric learner based on the nearest neighbour"
    #icon = "icons/LogisticRegression.svg"
    priority = 60

    LEARNER = ParametricNNLearner

    cutoff = Setting(1.)

    weight_function = Setting("1.")
    aggregate_function = Setting("mean(value)")

    def add_main_layout(self):
        box = gui.widgetBox(self.controlArea, box=True)
        self.cutoff_spin = gui.spin(box, self, "cutoff", 0., 10000, step=0.001, spinType=float, decimals=3, label="Cutoff")

        self.weight_function_edit = gui.lineEdit(box, self, "weight_function",
                                                 label="weight function")
        self.aggregate_function_edit = gui.lineEdit(box, self, "aggregate_function",
                                                    label="agregate function")


    def create_learner(self):
        return ParametricNNLearner(self.cutoff or None,
                                   self.aggregate_function,
                                   self.weight_function)

if __name__ == "__main__":
    import Orange
    iris = Orange.data.Table("housing")
    m = ParametricNNLearner(cutoff=35, aggregate_function='mean(value)')(iris[:-1])
    p = m(iris[-1])
    print(p)
