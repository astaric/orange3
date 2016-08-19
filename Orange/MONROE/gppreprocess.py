import numpy as np
from Orange.data import Table, DiscreteVariable, Domain
from Orange.preprocess.preprocess import Preprocess
from Orange.preprocess.transformation import Transformation

__all__ = ["GPTransformDiscrete"]


class GPTransformDiscrete(Preprocess):
    def __call__(self, data):
        new_data = Table(data)
        new_data.ensure_copy()
        attrs = list(new_data.domain.attributes)
        for col, attr in enumerate(new_data.domain.attributes):
            if isinstance(attr, DiscreteVariable):
                new_data.X[:, col] = np.where(new_data.X[:, col] == 0, -1, 1)
                attrs[col] = DiscreteVariable(
                    attr.name, attr.values + ["0"], compute_value=Lookup(attr))
        new_data.domain = Domain(attrs, new_data.domain.class_vars)
        return new_data


class Lookup(Transformation):
    def transform(self, column):
        return np.where(column == 0, -1, 1)
