from GPy.models import GPRegression

from Orange.kernel import GPKernel, RBF
from Orange.regression import Learner, Model

__all__ = ["GPRegressionLearner"]


class GPRegressionModel(Model):
    def __init__(self, model, params):
        self.model = model
        self.params = params

    def predict(self, X):
        #print("Objective: ", self.model.objective_function())
        pred, var = self.model.predict(X)
        return pred.flatten()


class GPRegressionLearner(Learner):
    __returns__ = GPRegressionModel
    DEFAULT_KERNEL = RBF

    def __init__(self, kernel=None, noise_var=1, preprocessors=None):
        super().__init__(preprocessors=preprocessors)
        self.kernel = kernel
        self.noise_var = noise_var
        self.params = vars()

    def fit(self, X, Y, W=None):
        Y = Y[:, None] if Y.ndim == 1 else Y
        k = self.kernel or self.DEFAULT_KERNEL
        k = k if isinstance(k, GPKernel) else k(range(X.shape[1]))
        m = GPRegression(X, Y, k, noise_var=self.noise_var)
        m.optimize()
        return GPRegressionModel(m, self.params)
