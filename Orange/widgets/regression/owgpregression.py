from itertools import chain
from numpy import linalg

from PyQt4.QtCore import Qt

from Orange.kernel import GPKernel, all_kernels
from Orange.regression import GPRegressionLearner
from Orange.widgets import settings, gui
from Orange.widgets.utils.owlearnerwidget import OWBaseLearner
from Orange.widgets.widget import Msg


class OWGPRegression(OWBaseLearner):
    name = "GP Regression"
    description = "Gaussian Process Regression."
    icon = "icons/GPRegression.svg"
    priority = 70

    inputs = [("Kernel", GPKernel, "set_kernel")]

    LEARNER = GPRegressionLearner

    KERNELS = all_kernels
    kernel_index = settings.Setting(9)
    noise_index = settings.Setting(45)
    noises = list(chain([x / 100000 for x in range(1, 10)],
                        [x / 10000 for x in range(1, 10)],
                        [x / 1000 for x in range(1, 10)],
                        [x / 100 for x in range(1, 10)],
                        [x / 10 for x in range(1, 10)],
                        range(1, 10),
                        [x * 10 for x in range(1, 10)],
                        [x * 100 for x in range(1, 10)],
                        [x * 1000 for x in range(1, 10)],
                        [x * 10000 for x in range(1, 10)]))

    class Error(OWBaseLearner.Error):
        not_positive_definite = Msg("Matrix not positive definite")

    def _set_noise_label(self):
        self.noise_label.setText(
            "Noise: {}".format(self.noises[self.noise_index]))

    def _on_noise_changed(self):
        self._set_noise_label()
        self.settings_changed()

    def add_main_layout(self):
        box = gui.widgetBox(self.controlArea, box=True)
        self.kernel_combo = gui.comboBox(
            box, self, "kernel_index", label="Default Kernel: ", addSpace=4,
            items=[kernel._kernel_name for kernel in self.KERNELS],
            orientation=Qt.Horizontal, callback=self._kernel_changed)

        self.kernel = self.KERNELS[self.kernel_index]
        self.input_kernel_name = "None"
        self.input_kernel_label = gui.label(
            box, self, "Input Kernel:          %(input_kernel_name)s",
            addSpace=10)

        gui.widgetLabel(box, "Gaussian noise variance:")
        self.noise_slider = gui.hSlider(
            box, self, "noise_index", minValue=0, maxValue=len(self.noises) - 1,
            callback=self._on_noise_changed, createLabel=False)
        hbox = gui.hBox(box)
        hbox.layout().setAlignment(Qt.AlignCenter)
        self.noise_label = gui.widgetLabel(hbox, "")
        self._set_noise_label()

    def create_learner(self):
        return self.LEARNER(kernel=self.kernel,
                            noise_var=self.noises[self.noise_index],
                            preprocessors=self.preprocessors)

    def set_kernel(self, kernel):
        self.input_kernel_name = kernel.kernel_name if kernel else "None"
        self.kernel_combo.setEnabled(kernel is None)
        self.kernel_combo.setItemText(
            self.kernel_combo.currentIndex(), "None" if kernel else
            self.KERNELS[self.kernel_index]._kernel_name)
        self.kernel = kernel if kernel else self.KERNELS[self.kernel_index]
        self.apply()

    def _kernel_changed(self):
        self.kernel = self.KERNELS[self.kernel_index]
        self.settings_changed()

    def get_learner_parameters(self):
        """Called by send report to list the parameters of the learner."""
        return (("Kernel", self.kernel._kernel_name),
                ("Gaussian noise variance", self.noises[self.noise_index]))

    def update_model(self):
        self.Error.not_positive_definite.clear()
        self.model = None
        if self.check_data():
            try:
                self.model = self.learner(self.data)
                self.model.name = self.learner_name
                self.model.instances = self.data
            except linalg.LinAlgError:
                self.Error.not_positive_definite()
        self.send(self.OUTPUT_MODEL_NAME, self.model)


if __name__ == "__main__":
    import sys
    from PyQt4.QtGui import QApplication
    from Orange.data import Table
    from Orange.kernel import Matern52

    a = QApplication(sys.argv)
    ow = OWGPRegression()
    d = Table('housing')[:100]
    ow.set_data(d)
   # ow.set_kernel(Matern52(range(len(d.domain.attributes))))
    ow.show()
    a.exec_()
    ow.saveSettings()
