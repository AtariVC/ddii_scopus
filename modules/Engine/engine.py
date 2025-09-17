from PyQt6 import QtWidgets, QtCore
from qtpy.uic import loadUi
import qasync
import asyncio
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QSpacerItem, QSizePolicy, QSplitter, QTabWidget, QScrollArea
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
import qtmodern.styles
import sys
from pymodbus.client import AsyncModbusSerialClient
from PyQt6.QtGui import QIntValidator, QDoubleValidator
from pathlib import Path
from qtmodern.windows import ModernWindow

####### импорты из других директорий ######````
# /src
src_path = Path(__file__).resolve().parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent

# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from src.modbus_worker import ModbusWorker                                         # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand                     # noqa: E402
from src.parsers import  Parsers                                                   # noqa: E402
from modules.Main_Serial.main_serial_dialog import SerialConnect                   # noqa: E402
from src.log_config import log_init, log_s                                         # noqa: E402
from style.styleSheet import widget_led_on, widget_led_off                         # noqa: E402
from src.parsers_pack import LineEObj, LineEditPack                                # noqa: E402
from modules.Engine.widgets.oscilloscope.graph_widget import GraphWidget           # noqa: E402
from modules.Engine.widgets.oscilloscope.run_meas_widget import RunMeasWidget      # noqa: E402
from modules.Engine.widgets.oscilloscope.flux_widget import FluxWidget             # noqa: E402
from modules.Engine.widgets.oscilloscope.run_flux_widget import RunFluxWidget      # noqa: E402
from modules.Engine.widgets.viewer.graph_viewer_widget import GraphViewerWidget    # noqa: E402
from modules.Engine.widgets.viewer.explorer_hdf5_widget import ExplorerHDF5Widget  # noqa: E402
from src.craft_custom_widget import add_serial_widget
from src.main_window_maker import create_split_widget, clear_left_widget, create_tab_widget_items
from qcustomwindow import (CustomWindow, QtWidgets, QMovie, QtGui,
                                   __version__, dark, light, stylesheet)  # noqa: F401

class Engine(QtWidgets.QMainWindow, CustomWindow):

    gridLayout_main_split        : QtWidgets.QGridLayout

    coroutine_get_client_finished = QtCore.pyqtSignal()


    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        loadUi(Path(__file__).parent.joinpath('engine.ui'), self)
        self.resize(1300, 800)
        self.mw: ModbusWorker = ModbusWorker()
        self.parser: Parsers = Parsers()
        self.logger = log_init()
        self.setTitle('ddii scopus')
        nyancat_label = QtWidgets.QLabel()
        assets = Path(__file__).parent / 'assets'
        
        
        self.dark_icon = QtGui.QIcon(str(assets / 'dark.svg'))
        self.light_icon = QtGui.QIcon(str(assets / 'light.svg'))
        self.style_button = QtWidgets.QPushButton()
        self.style_button.setIcon(self.dark_icon)
        self.style_button.setFlat(True)
        self.style_button.clicked.connect(self.on_change_style)
        self.add_right_widget(self.style_button)
        self.is_dark = True
        
        # self.init_QObjects()
        # self.config = ConfigSaver()
        self.init_widgets()
        
    def on_change_style(self):
        if not self.is_dark:
            dark()
            self.style_button.setIcon(self.dark_icon)
        else:
            light()
            self.style_button.setIcon(self.light_icon)
        self.is_dark = not self.is_dark

    def widget_model(self):
        spacer_v = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return{
            "Осциллограф": {
                "Меню запуска": self.run_meas_widget,
                "Опрос счетчика частиц": self.run_flux_widget,
                "Счетчик частиц": self.flux_widget,
                "spacer": spacer_v, 
                "Подключение": self.w_ser_dialog
            },
            "Вьюер":{
                "Файл менеджер": self.explorer_hdf5_widget,
            },
            "Парсер": {

            }
        }
    
    def on_tab_widget_handler(self, index: int):
        tab_text: str = self.tab_widget.tabText(index)
        if tab_text == "Вьюер":
            clear_left_widget(self.w_graph_widget, self.graph_viewer_widget)

        if tab_text == "Осциллограф":
            clear_left_widget(self.graph_viewer_widget, self.w_graph_widget)

        if tab_text == "Вьюер":
            self.current_left_widget = self.graph_viewer_widget
        elif tab_text == "Осциллограф":
            self.current_left_widget = self.w_graph_widget

    def init_widgets(self) -> None:
        # Виджеты
        self.w_graph_widget: GraphWidget = GraphWidget()
        self.w_ser_dialog: SerialConnect = SerialConnect(self.logger)
        self.run_flux_widget: RunFluxWidget = RunFluxWidget(self)
        self.flux_widget: FluxWidget = FluxWidget(self)
        self.run_meas_widget: RunMeasWidget = RunMeasWidget(self)
        self.client = self.w_ser_dialog.client
        self.explorer_hdf5_widget: ExplorerHDF5Widget = ExplorerHDF5Widget(self)
        self.graph_viewer_widget: GraphViewerWidget = GraphViewerWidget(self) 
        model = self.widget_model()
        self.tab_widget = create_tab_widget_items(model, self.on_tab_widget_handler)
        #### отдельно добавляем SerialConnectWidget
        vLayout_ser_connect = QVBoxLayout()
        # add_serial_widget(vLayout_ser_connect, self.w_ser_dialog)
        spacer_v = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # tab_widget.layout.addItem(spacer_v)
        # tab_widget.layout.addLayout(vLayout_ser_connect)
        create_split_widget(self.gridLayout_main_split, self.w_graph_widget, self.tab_widget)



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    w: Engine = Engine()
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