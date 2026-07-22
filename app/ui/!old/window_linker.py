import asyncio
import sys
from pathlib import Path

import qasync
import qtmodern.styles
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import (
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
)
from qtmodern.windows import ModernWindow
from qtpy.uic import loadUi

from app.src.components.log.config import log_init
from app.src.components.ui.main_window_maker import create_split_widget, create_tab_widget_items, replace_left_widget
from app.src.components.modbus.worker import ModbusWorker
from app.src.components.parsers.custom_parsers import Parsers
from app.src.event.event import Event
from app.plugins.connection.connection_bar import ConnectionBar
from app.widgets.debug.debug_graph import DebugGraphWidget
from app.widgets.oscilloscope.flux_widget import FluxWidget
from app.widgets.oscilloscope.graph_widget import GraphWidget
from app.widgets.oscilloscope.run_flux_widget import RunFluxWidget
from app.widgets.oscilloscope.run_meas_widget import RunMeasWidget
from app.widgets.parser.cmd_wind_read_mem import CmdWindReadMemWidget
from app.widgets.settings.mpp_settings_widget import MppSettingsWidget
from app.widgets.settings.cm_settings_widget import CmSettingsWidget
from app.widgets.tests.telemetry_poll_widget import TelemetryPollWidget
from app.widgets.tests.runner_widget import TestRunnerWidget
from app.widgets.tests.tables_widget import TestTablesWidget
from app.widgets.viewer_hdf5.explorer_widget import ExplorerHDF5Widget
from app.widgets.viewer_hdf5.filter_viewer_widget import FilterViewerWidget
from app.widgets.viewer_hdf5.graph_viewer_widget import GraphViewerWidget


class MainUIRenderer(QtWidgets.QMainWindow):
    gridLayout_main_split: QtWidgets.QGridLayout

    coroutine_get_client_finished = QtCore.pyqtSignal()
    
    shared_bfr_update_event: Event

    def __init__(self) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath("window_linker.ui"), self)
        self.resize(1300, 800)
        self.shared_bfr_update_event = Event(str) # общий буфер для обмена данными между процессами
        self.mw: ModbusWorker = ModbusWorker()
        self.parser: Parsers = Parsers()
        self.logger = log_init()
        self.init_widgets()

    def widget_model(self):
        spacer_v = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return {
            "Осциллограф": {
                "Меню запуска": self.run_meas_widget,
                "Опрос счетчика частиц": self.run_flux_widget,
                "Счетчик частиц": self.flux_widget,
                "spacer": spacer_v,
                "Подключение": self.w_ser_dialog,
            },
            "Настройка": {
                "МПП": self.mpp_settings_widget,
                "ЦМ: Питание": self.cm_settings_widget,
            },
            "Диагностика": {
                "Опрос телеметрии": self.telemetry_poll_widget,
                "Тестирование": self.test_runner_widget,
                "Чтение памяти": self.cmd_wind_read_mem,
            },
            "Вьюер": {
                "Файл менеджер": self.explorer_hdf5_widget,
                "Фильтр кадров": self.graph_filter_widget,
            },
        }

    def on_tab_widget_handler(self, index: int):
        tab_text: str = self.tab_widget.tabText(index)
        if tab_text == "Вьюер":
            replace_left_widget(self.graph_viewer_widget)
        elif tab_text == "Диагностика":
            replace_left_widget(self.test_tables_widget)
        else:
            replace_left_widget(self.w_graph_widget)

    def init_widgets(self) -> None:
        self.w_graph_widget: GraphWidget = GraphWidget()
        self.w_ser_dialog: ConnectionBar = ConnectionBar(self.logger)
        self.flux_widget: FluxWidget = FluxWidget()
        self.run_flux_widget: RunFluxWidget = RunFluxWidget(self)
        self.run_meas_widget: RunMeasWidget = RunMeasWidget(self)
        self.client = self.w_ser_dialog.client
        self.explorer_hdf5_widget: ExplorerHDF5Widget = ExplorerHDF5Widget()
        self.graph_viewer_widget: GraphViewerWidget = GraphViewerWidget(self)
        self.graph_filter_widget: FilterViewerWidget = FilterViewerWidget(self)
        self.graph_debug_widget: DebugGraphWidget = DebugGraphWidget()
        self.cmd_wind_read_mem: CmdWindReadMemWidget = CmdWindReadMemWidget(self)
        self.test_tables_widget: TestTablesWidget = TestTablesWidget()
        self.telemetry_poll_widget: TelemetryPollWidget = TelemetryPollWidget(self)
        self.test_runner_widget: TestRunnerWidget = TestRunnerWidget()
        self.mpp_settings_widget: MppSettingsWidget = MppSettingsWidget(self)
        self.cm_settings_widget: CmSettingsWidget = CmSettingsWidget(self)
        model = self.widget_model()
        self.tab_widget = create_tab_widget_items(model, self.on_tab_widget_handler)
        create_split_widget(self.gridLayout_main_split, self.w_graph_widget, self.tab_widget)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    w: MainUIRenderer = MainUIRenderer()
    mw: ModernWindow = ModernWindow(w)
    mw.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, False)  # fix flickering on resize window
    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    mw.show()

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
