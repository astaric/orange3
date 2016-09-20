import copy

from numpy import linalg
from PyQt4.QtCore import Qt
from PyQt4.QtGui import (QWidget, QListView, QItemSelectionModel, QDockWidget,
                         QVBoxLayout, QItemSelection, QMenu, QScrollArea)

from Orange.data import Table
from Orange.kernel import (RBF, RatQuad, Periodic, MLP, Polynomial,
                           Linear, GPKernel, GPStationaryKernel, all_kernels,
                           gpkernel_sum)
from Orange.widgets import gui
from Orange.widgets.settings import Setting
from Orange.widgets.utils.itemmodels import VariableListModel
from Orange.widgets.widget import Msg, OWWidget


# TODO - velikosti (izgled), brisanje kernelov, parametri, test, doubleclick, settings
# TODO - menjava vrstnega reda kernelov, kernel_name, report, doc, icons
# TODO - privzete vrednosti parametrov


class KernelEditor(QWidget):
    def __init__(self, domain, kernel, active_dims):
        super().__init__()
        self._kernel_instance = kernel

        self.setFixedHeight(150)
        self.main_area = gui.hBox(self)
        self.main_area.layout().setContentsMargins(10, 0, 0, 0)

        box = gui.hBox(self.main_area, "Active dimensions")
        self.attrs_view = QListView()
        self.attrs_view.setSelectionMode(QListView.ExtendedSelection)
        self.attrs_model = VariableListModel()
        self.attrs_view.setModel(self.attrs_model)
        self.attrs_view.selectionModel().selectionChanged.connect(
            self._active_dims_changed)
        self.attrs_view.setMaximumHeight(110)
        box.layout().addWidget(self.attrs_view)

        self.param_box = gui.vBox(self.main_area, "Parameters")
        self.param_box.layout().setAlignment(Qt.AlignTop)

        self._initialize(domain, active_dims)

    def _initialize(self, domain, selected):
        self.attrs_model[:] = domain.attributes
        if selected:
            self._set_active_dimensions(selected)
        else:
            self.attrs_view.selectAll()

    def _active_dims_changed(self):
        if self.nativeParentWidget():
            self.parameter_changed("active_dimensions")

    @property
    def active_dimensions(self):
        return self._get_active_dimensions()

    def parameter_changed(self, parameter):
        self.nativeParentWidget().edit_kernel(
            self._kernel_instance, parameter, getattr(self, parameter))

    def _set_active_dimensions(self, rows):
        selection = QItemSelection()
        model = self.attrs_view.model()
        for row in rows:
            index = model.index(row, 0)
            selection.select(index, index)
        self.attrs_view.selectionModel().select(
            selection, QItemSelectionModel.ClearAndSelect)

    def _get_active_dimensions(self):
        rows = self.attrs_view.selectionModel().selectedRows()
        return [index.row() for index in rows]


class VarianceKernelEditor(KernelEditor):
    dspin_args = (1e-2, 1000.0, 1e-2)
    dspin_kwargs = {"decimals": 2, "alignment": Qt.AlignRight,
                    "controlWidth": 90}
    variance = 1

    def __init__(self, domain, kernel, active_dims):
        super().__init__(domain, kernel, active_dims)

        self.variance_spin = gui.doubleSpin(
            self.param_box, self, "variance", *self.dspin_args,
            callback=lambda: self.parameter_changed("variance"),
            label="Variance:", **self.dspin_kwargs)


class StationaryKernelEditor(VarianceKernelEditor):
    lengthscale = 1
    ARD = False

    def __init__(self, domain, kernel, active_dims):
        super().__init__(domain, kernel, active_dims)

        self.lengthscale_spin = gui.doubleSpin(
            self.param_box, self, "lengthscale", *self.dspin_args,
            callback=lambda: self.parameter_changed("lengthscale"),
            label="Lengthscale:", **self.dspin_kwargs)

        ard_box = gui.hBox(self.param_box)
        self.ard_label = gui.label(ard_box, self, "ARD:")
        self.ard_check = gui.checkBox(
            ard_box, self, "ARD", label="",
            callback=lambda: self.parameter_changed("ARD"))


class RatQuadKernelEditor(StationaryKernelEditor):
    power = 2

    def __init__(self, domain, kernel, active_dims):
        super().__init__(domain, kernel, active_dims)

        self.order_spin = gui.spin(
            self.param_box, self, "power", 2, 10,
            callback=lambda: self.parameter_changed("power"),
            label="Power:", alignment=Qt.AlignRight, controlWidth=90)


# TODO - ARD1, ARD2
class PeriodicKernelEditor(VarianceKernelEditor):
    period = 1
    lengthscale = 1

    def __init__(self, domain, kernel, active_dims):
        super().__init__(domain, kernel, active_dims)

        self.period_spin = gui.doubleSpin(
            self.param_box, self, "period", *self.dspin_args,
            callback=lambda: self.parameter_changed("period"),
            label="Period:", **self.dspin_kwargs)

        self.lengthscale_spin = gui.doubleSpin(
            self.param_box, self, "lengthscale", *self.dspin_args,
            callback=lambda: self.parameter_changed("lengthscale"),
            label="Lengthscale:", **self.dspin_kwargs)


# TODO - add list of variances
class LinearKernelEditor(VarianceKernelEditor):
    pass


class PolyKernelEditor(VarianceKernelEditor):
    scale = 1
    bias = 1
    order = 3

    def __init__(self, domain, kernel, active_dims):
        super().__init__(domain, kernel, active_dims)

        self.scale_spin = gui.doubleSpin(
            self.param_box, self, "scale", *self.dspin_args,
            callback=lambda: self.parameter_changed("scale"),
            label="Scale:", **self.dspin_kwargs)

        self.bias_spin = gui.doubleSpin(
            self.param_box, self, "bias", *self.dspin_args,
            callback=lambda: self.parameter_changed("bias"),
            label="Bias:", **self.dspin_kwargs)

        self.order_spin = gui.spin(
            self.param_box, self, "order", 1, 10,
            callback=lambda: self.parameter_changed("order"),
            label="Order:", alignment=Qt.AlignRight, controlWidth=90)


class MLPKernelEditor(VarianceKernelEditor):
    weight_variance = 1
    bias_variance = 1
    ARD = False

    def __init__(self, domain, kernel, active_dims):
        super().__init__(domain, kernel, active_dims)

        self.weight_variance_spin = gui.doubleSpin(
            self.param_box, self, "weight_variance", *self.dspin_args,
            callback=lambda: self.parameter_changed("weight_variance"),
            label="Weight var.:", **self.dspin_kwargs)

        self.bias_variance_spin = gui.doubleSpin(
            self.param_box, self, "bias_variance", *self.dspin_args,
            callback=lambda: self.parameter_changed("bias_variance"),
            label="Bias var.:", **self.dspin_kwargs)

        ard_box = gui.hBox(self.param_box)
        self.ard_label = gui.label(ard_box, self, "ARD:")
        self.ard_check = gui.checkBox(
            ard_box, self, "ARD", label="",
            callback=lambda: self.parameter_changed("ARD"))


class KernelDock(QDockWidget):
    def __init__(self, widget, kernel_instance):
        super().__init__()
        self._kernel_instance = kernel_instance
        self._shown = True
        self.setWindowTitle(kernel_instance.kernel_name)
        self.setWidget(widget)
        self.setFloating(False)
        self.setFeatures(QDockWidget.DockWidgetClosable)

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.setMinimumWidth(self.width())
        self._shown = not self._shown
        self.widget().setVisible(self._shown)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.nativeParentWidget().remove_kernel(self._kernel_instance)


class KernelView(QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QVBoxLayout()
        self._layout.setMargin(0)
        self._layout.setAlignment(Qt.AlignTop)
        self.setLayout(self._layout)

    def insert_kernel(self, domain, kernel, selected=None):
        args = (domain, kernel, selected)
        if isinstance(kernel, RatQuad):
            kernel_widget = RatQuadKernelEditor(*args)
        elif isinstance(kernel, GPStationaryKernel):
            kernel_widget = StationaryKernelEditor(*args)
        elif isinstance(kernel, MLP):
            kernel_widget = MLPKernelEditor(*args)
        elif isinstance(kernel, Polynomial):
            kernel_widget = PolyKernelEditor(*args)
        elif isinstance(kernel, Linear):
            kernel_widget = LinearKernelEditor(*args)
        elif isinstance(kernel, Periodic):
            kernel_widget = PeriodicKernelEditor(*args)
        else:
            kernel_widget = VarianceKernelEditor(*args)
        kernel_dock = KernelDock(kernel_widget, kernel)
        self._layout.addWidget(kernel_dock)

    def remove_all(self):
        for widget in self.findChildren(KernelDock):
            widget.deleteLater()


class OWGPKernel(OWWidget):
    name = "Kernel"
    description = "Gaussian Process Kernel."
    icon = "icons/Kernel.svg"
    priority = 69

    inputs = [("Data", Table, "set_data")]
    outputs = [("Kernel", GPKernel)]

    want_main_area = False

    auto_apply = Setting(True)

    KERNELS = all_kernels

    class Warning(OWWidget.Warning):
        outdated_kernel = Msg("Press Apply to submit changes.")
        no_data_on_input = Msg("Kernel requires data (domain)"
                               " to select active dimensions.")

    class Error(OWWidget.Error):
        not_positive_definite = Msg("Matrix not positive definite")

    def __init__(self):
        self.data = None
        self.kernel = None
        self.kernels = []  # kernel instances to ADD
        self.kernel_name = "Kernel"

        # GUI
        self.setFixedWidth(550)
        box = gui.hBox(self.controlArea, "Name")
        self.name_line_edit = gui.lineEdit(
            box, self, "kernel_name", orientation=Qt.Horizontal,
            callback=self._name_edited)

        box = gui.vBox(self.controlArea, "Kernels")
        bb = gui.hBox(box)
        bb.layout().setAlignment(Qt.AlignLeft)
        menu = QMenu()
        for ker in self.KERNELS:
            menu.addAction(ker._kernel_name,
                           lambda k=ker: self._add_button_clicked(k))
        self.add_button = gui.button(bb, self, "Add", width=120, enabled=False)
        self.add_button.setMenu(menu)
        gui.separator(bb, 5)
        self.default_button = gui.button(
            bb, self, "Set to default", width=120, enabled=False,
            callback=self._default_button_clicked)

        self.kernel_view = KernelView()
        self.scroll_area = QScrollArea()
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setWidget(self.kernel_view)
        self.scroll_area.setWidgetResizable(True)
        box.layout().addWidget(self.scroll_area)

        box = gui.hBox(self.controlArea, True)
        box.layout().addWidget(self.report_button)
        gui.separator(box, 15)
        self.apply_button = gui.auto_commit(box, self, "auto_apply", "&Apply",
                                            box=False, commit=self.apply)

        self.Warning.no_data_on_input()

    # GUI
    def _enable_buttons(self):
        self.add_button.setEnabled(self.data is not None)
        self.default_button.setEnabled(self.data is not None)

    def _add_button_clicked(self, kernel):
        self.add_kernel(kernel(range(len(self.data.domain.attributes))))
        self.create_kernel()

    def _default_button_clicked(self):
        self.set_default_kernel()
        self.create_kernel()

    def _name_edited(self):
        if self.kernel:
            self.kernel.kernel_name = self.name_line_edit.text()
        self.apply()

    # Controller
    def add_kernel(self, kernel, active_dims=None):
        self.kernels.append(kernel)
        self.kernel_view.insert_kernel(self.data.domain, kernel, active_dims)

    def edit_kernel(self, kernel, parameter, value):
        self.Error.not_positive_definite.clear()
        try:
            setattr(self.kernels[self.kernels.index(kernel)], parameter, value)
            self.create_kernel()
        except linalg.LinAlgError:
            self.Error.not_positive_definite()

    def remove_kernel(self, kernel):
        del self.kernels[self.kernels.index(kernel)]
        self.create_kernel()

    def remove_all_kernels(self):
        self.kernels = []
        self.kernel_view.remove_all()

    # Model
    def set_default_kernel(self):
        self.remove_all_kernels()
        if self.data:
            attrs = self.data.domain.attributes
            if self.data.domain.has_continuous_attributes():
                dims = [i for i, attr in enumerate(attrs) if attr.is_continuous]
                self.add_kernel(RBF(dims), dims)
            if self.data.domain.has_discrete_attributes():
                dims = [i for i, attr in enumerate(attrs) if attr.is_discrete]
                self.add_kernel(Linear(dims), dims)

    def set_data(self, data):
        self.Warning.no_data_on_input.clear()
        self.Warning.no_data_on_input(shown=not data)
        self.data = data
        self.set_default_kernel()
        self._enable_buttons()
        self.create_kernel()

    def create_kernel(self):
        self.kernel = gpkernel_sum(self.kernels)
        self.kernel_name = self.kernel.kernel_name if self.kernel else "Kernel"
        self.Warning.outdated_kernel(shown=not self.auto_apply)
        self.apply()

    def apply(self):
        self.Warning.outdated_kernel.clear()
        #for k in self.kernels:
            #print("---kernel-------")
            #print(type(k), k.input_dim, k.active_dims, k.kernel_name, k._all_dims_active)
            #print(k.parameters)
        self.send("Kernel", copy.deepcopy(self.kernel))

    def send_report(self):
        if self.kernel:
            self.report_items((("Kernel", self.kernel.kernel_name),))


if __name__ == "__main__":
    from PyQt4.QtGui import QApplication

    a = QApplication([])
    ow = OWGPKernel()
    d = Table("imports-85")
    ow.set_data(d)
    ow.show()
    a.exec_()
