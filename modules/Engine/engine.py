from PyQt6 import QtWidgets, QtCore
from qtpy.uic import loadUi
from qasync import asyncSlot
import qasync
import asyncio
from PyQt6.QtWidgets import QWidget, QGroupBox, QGridLayout, QSpacerItem, QSizePolicy, QSplitter
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import qtmodern.styles
import sys
from pymodbus.client import AsyncModbusSerialClient
from PyQt6.QtGui import QIntValidator, QDoubleValidator
from pathlib import Path
from qtmodern.windows import ModernWindow

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent

# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from src.modbus_worker import ModbusWorker                          # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand      # noqa: E402
from src.parsers import  Parsers                                    # noqa: E402
from modules.Main_Serial.main_serial_dialog import SerialConnect    # noqa: E402
from src.log_config import log_init, log_s                          # noqa: E402
from style.styleSheet import widget_led_on, widget_led_off          # noqa: E402
from src.parsers_pack import LineEObj, LineEditPack                 # noqa: E402
from modules.Engine.widgets.graph_widget import GraphWidget         # noqa: E402
from modules.Engine.widgets.run_meas_widget import RunMaesWidget         # noqa: E402
from src.craft_custom_widget import add_serial_widget

class Engine(QtWidgets.QMainWindow):
    # vLayout_graph                : QtWidgets.QVBoxLayout
    # vLayout_menu                 : QtWidgets.QVBoxLayout
    # vLayout_ser_connect          : QtWidgets.QVBoxLayout
    # vLayout_menu_item_1          : QtWidgets.QVBoxLayout
    gridLayout_main_split        : QtWidgets.QGridLayout

    coroutine_get_client_finished = QtCore.pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        loadUi(Path(__file__).resolve().parent.parent.parent.joinpath('frontend/MainWindiwEngine.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.logger = log_init()
        # self.init_QObjects()
        # self.config = ConfigSaver()
        self.init_widgets()

    def init_widgets(self) -> None:
        # Виджеты
        # spacer_v = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        w_ser_dialog: SerialConnect = SerialConnect(self.logger)
        w_graph_widget: GraphWidget = GraphWidget()
        w_graph_widget.setMinimumWidth(w_graph_widget.sizeHint().width() - 500)
        w_graph_widget.setMinimumHeight(w_graph_widget.sizeHint().height() -400)
        splitter = QSplitter()
        self.gridLayout_main_split.addWidget(splitter)
        run_meas_widget: RunMaesWidget = RunMaesWidget()

        # Оборачиваем меню в виджет
        menu_widget = QWidget()
        menu_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        vLayout_menu = QtWidgets.QVBoxLayout(menu_widget)
        vLayout_ser_connect = QtWidgets.QVBoxLayout()
        vLayout_menu.setContentsMargins(5, 0, 15, 16) # (left, top, right, bottom)
        # добавляем виджеты в vLayout_menu
        vLayout_menu.addWidget(run_meas_widget)
        run_meas_widget.setMaximumHeight(run_meas_widget.groupBox_run_meas.width())
        vLayout_menu.addStretch()
        vLayout_menu.addLayout(vLayout_ser_connect)
        add_serial_widget(vLayout_ser_connect, w_ser_dialog)
        #######################

        splitter.addWidget(w_graph_widget)
        splitter.addWidget(menu_widget)

    def init_tab_widget_item_meas() -> None:
        pass

    def init_tab_widget_item_parser() -> None:
        pass




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