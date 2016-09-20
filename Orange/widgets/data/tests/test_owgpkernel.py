# Test methods with long descriptive names can omit docstrings
# pylint: disable=missing-docstring
from Orange.data import Table
from Orange.kernel import RBF, Linear, Add
from Orange.widgets.data.owgpkernel import OWGPKernel
from Orange.widgets.tests.base import WidgetTest


class TestOWGPKernel(WidgetTest):
    def setUp(self):
        self.housing = Table("housing")
        self.widget = self.create_widget(OWGPKernel,
                                         stored_settings={"auto_apply": False})

    def test_input_data(self):
        """Check widget's data with data on the input"""
        self.assertEqual(self.widget.data, None)
        self.send_signal("Data", self.housing)
        self.assertEqual(self.widget.data, self.housing)
        self.assertTrue(self.widget.add_button.isEnabled())

    def test_input_data_disconnect(self):
        """Check widget's data and kernel after disconnecting data from input"""
        self.send_signal("Data", self.housing)
        self.assertEqual(self.widget.data, self.housing)
        self.widget.apply_button.button.click()
        self.send_signal("Data", None)
        self.assertIsNone(self.widget.data)
        self.widget.apply_button.button.click()
        self.assertIsNone(self.widget.kernel)
        self.assertIsNone(self.get_output("Kernel"))
        self.assertFalse(self.widget.add_button.isEnabled())

    def test_output_kernel(self):
        """Check if kernel is on output after sending data and apply"""
        self.assertIsNone(self.get_output("Kernel"))
        self.widget.apply_button.button.click()
        self.assertIsNone(self.get_output("Kernel"))
        self.send_signal("Data", self.housing)
        self.widget.apply_button.button.click()
        self.assertIsNotNone(self.get_output("Kernel"))

    def test_output_kernel_name(self):
        """Check if kernel's name properly changes"""
        new_name = "Kernel Name"
        self.send_signal("Data", self.housing)
        self.assertEqual(self.widget.kernel.kernel_name,
                         self.widget.name_line_edit.text())
        self.widget.name_line_edit.setText(new_name)
        self.widget._name_edited()
        self.widget.apply_button.button.click()
        self.assertEqual(self.get_output("Kernel").kernel_name, new_name)

    def test_default_kernel_continuous_attributes(self):
        """Check default kernel for dataset with continuous attributes"""
        self.send_signal("Data", self.housing)
        self.widget.apply_button.button.click()
        self.assertIsInstance(self.get_output("Kernel"), RBF)

    def test_default_kernel_discrete_attributes(self):
        """Check default kernel for dataset with discrete attributes"""
        self.send_signal("Data", Table("zoo"))
        self.widget.apply_button.button.click()
        self.assertIsInstance(self.get_output("Kernel"), Linear)

    def test_default_kernel_mixed_attributes(self):
        """Check default kernel for dataset with mixed attributes"""
        self.send_signal("Data", Table("imports-85"))
        self.widget.apply_button.button.click()
        self.assertIsInstance(self.get_output("Kernel"), Add)
