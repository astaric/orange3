# Test methods with long descriptive names can omit docstrings
# pylint: disable=missing-docstring
from Orange.kernel import RBF, Matern52
from Orange.widgets.regression.owgpregression import OWGPRegression
from Orange.widgets.tests.base import (WidgetTest, WidgetLearnerTestMixin,
                                       ParameterMapping)


class TestOWGPRegression(WidgetTest, WidgetLearnerTestMixin):
    def setUp(self):
        self.widget = self.create_widget(OWGPRegression,
                                         stored_settings={"auto_apply": False})
        self.init()
        self.data = self.data[:50]
        noise_slider = self.widget.noise_slider

        def setter(val):
            index = self.widget.noises.index(val)
            self.widget.noises[noise_slider.value()]
            noise_slider.setValue(index)

        self.parameters = [
            ParameterMapping(
                'kernel', self.widget.kernel_combo,
                [kernel for kernel in self.widget.KERNELS]),
            ParameterMapping(
                "noise_var", noise_slider, setter=setter,
                values=[self.widget.noises[0], self.widget.noises[-1]],
                getter=lambda: self.widget.noises[noise_slider.value()])]

    def test_input_kernel(self):
        """Check if kernel properly changes with kernel on the input"""
        self.assertTrue(self.widget.kernel_combo.isEnabled())
        self.assertIs(self.widget.kernel, RBF)
        self.send_signal("Kernel", Matern52(range(1, len(self.data), 2)))
        self.assertFalse(self.widget.kernel_combo.isEnabled())
        self.assertIsInstance(self.widget.kernel, Matern52)
        self.widget.apply_button.button.click()
        self.assertEqual(self.widget.kernel_combo.currentText(), "None")
        self.assertIsInstance(self.get_output("Learner").params.get("kernel"),
                              Matern52)

    def test_input_kernel_disconnect(self):
        """Check kernel after disconnecting kernel on the input"""
        self.send_signal("Kernel", Matern52(range(1, len(self.data), 2)))
        self.assertIsInstance(self.widget.kernel, Matern52)
        self.send_signal("Kernel", None)
        self.assertTrue(self.widget.kernel_combo.isEnabled())
        self.assertEqual(self.widget.kernel,
                         self.widget.KERNELS[self.widget.kernel_index])
        self.widget.apply_button.button.click()
        self.assertEqual(self.widget.kernel_combo.currentText(), "RBF")
        self.assertIs(self.get_output("Learner").params.get("kernel"), RBF)
