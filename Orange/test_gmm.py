import os
import sys

from Orange import gmm

from PyQt4.QtGui import QApplication
import numpy as np
from sklearn.mixture import GMM
from Orange.clustering import anze_gmm, _anze_gmm, anze_skl_gmm

from Orange.data import Table, DiscreteVariable, Domain
from Orange.widgets.utils.colorpalette import ColorPaletteGenerator
from Orange.widgets.visualize.owparallelcoordinates import OWParallelCoordinates


if "PYCHARM_HOSTED" in os.environ:
    PLOT = False
else:
    PLOT = True

data = Table('wine')
X = data.X[:, np.arange(len(data.domain.attributes))]
k = 5
#method="my"
method = "my"
class_ = "cluster"


if method == "sklearn":
    gmm = GMM(n_components=k)
    gmm.fit(X)
    w = gmm.predict_proba(X)
    mu = gmm.means_
    sigma = gmm.covars_
    phi = gmm.weights_
    Y = np.argmax(w.T, axis=0).reshape(-1, 1)
elif method == "sklearn-full":
    gmm = GMM(n_components=k, covariance_type='full')
    gmm.fit(X)
    w = gmm.predict_proba(X)
    mu = gmm.means_
    sigma = np.array([cov.diagonal() for cov in gmm.covars_])
    phi = gmm.weights_
    Y = np.argmax(w.T, axis=0).reshape(-1, 1)
elif method == "my":
    w, mu, sigma, phi = anze_gmm.lac(X, k)
    Y = np.argmax(w, axis=0).reshape(-1, 1)
elif method == "myc":
    w, mu, sigma, phi = _anze_gmm.em(X, k)
    Y = np.argmax(w, axis=0).reshape(-1, 1)
elif method == "myskl":
    gmm = anze_skl_gmm.MyGMM(n_components=k)
    gmm.fit(X)
    w = gmm.predict_proba(X)
    mu = gmm.means_
    sigma = gmm.covars_
    phi = gmm.weights_
    Y = np.argmax(w.T, axis=0).reshape(-1, 1)
else:
    raise ValueError("Invalid method")


if class_ == "original":
    annotated_data = data
elif class_ == "cluster":
    cluster = DiscreteVariable("Cluster", values=map(str, range(k)))
    new_domain = Domain(data.domain.attributes, cluster)
    annotated_data = Table(new_domain, data.X, Y)
else:
    new_domain = Domain(data.domain.attributes)
    annotated_data = Table(new_domain, data.X)

#test widget appearance
if __name__ == "__main__":
    sys.exit(0)
    a = QApplication(sys.argv)
    ow = OWParallelCoordinates()
    ow.show()
    ow.graph.discPalette = ColorPaletteGenerator(rgbColors=[(127, 201, 127), (190, 174, 212), (253, 192, 134), (255, 255, 153), (56, 108, 176)])
    ow.set_data(annotated_data)
    ow.handleNewSignals()
    ow.setClusters(mu, sigma, phi)

    a.exec_()

    ow.settingsHandler.update_class_defaults(ow)
