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
from modules.Engine.widgets.run_meas_widget import RunMeasWidget         # noqa: E402
from src.craft_custom_widget import add_serial_widget

class Engine(QtWidgets.QMainWindow):

    gridLayout_main_split        : QtWidgets.QGridLayout

    coroutine_get_client_finished = QtCore.pyqtSignal()


    def __init__(self) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath('engine.ui'), self)
        self.resize(1300, 800)
        self.mw: ModbusWorker = ModbusWorker()
        self.parser: Parsers = Parsers()
        self.logger = log_init()
        # self.init_QObjects()
        # self.config = ConfigSaver()
        self.init_widgets()

    def init_widgets(self) -> None:
        # Виджеты
        self.w_graph_widget: GraphWidget = GraphWidget()
        self.w_ser_dialog: SerialConnect = SerialConnect(self.logger)
        self.client = self.w_ser_dialog.client
        self.run_meas_widget: RunMeasWidget = RunMeasWidget(self)
        tab_widget = self.create_tab_widget_items()
        splitter = QSplitter()
        self.gridLayout_main_split.addWidget(splitter)
        splitter.addWidget(self.w_graph_widget)
        splitter.addWidget(tab_widget)

    def create_tab_widget_items(self) -> QTabWidget:
        """
        Создает QTabWidget с вкладками, возвращая все вкладки через фабрику.
        """
        def build_grBox(widget: QWidget, name: str) -> QGroupBox:
            grBox_widget: QGroupBox = QGroupBox(name)
            vLayout_grBox_widget: QVBoxLayout = QVBoxLayout(grBox_widget)
            grBox_widget.setMaximumHeight(widget.minimumHeight() + 40)
            grBox_widget.setMinimumWidth(widget.minimumWidth() + 0)
            vLayout_grBox_widget.addWidget(widget)
            font = QFont()
            font.setFamily("Arial")
            font.setPointSize(12)
            grBox_widget.setFont(font)
            return grBox_widget

        # Фабрика функций для инициализации вкладок
        def build_tab_factories():
            return {
                "Осциллограф": init_tab_widget_item_meas,
                "Парсер": init_tab_widget_item_parser,
                # Добавьте сюда другие вкладки
            }

        # Функция для создания вкладки "Осциллограф"
        def init_tab_widget_item_meas() -> QWidget:
    
            ######################
            spacer_v = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            spacer_v_scroll = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            # Создание виджетов в grBox
            grBox_run_meas_widget = build_grBox(self.run_meas_widget, name="Меню запуска")
            ######################
            # Создаем QScrollArea для прокручиваемого содержимого
            scroll_area_menu = QScrollArea()
            scroll_area_menu.setWidgetResizable(True)
            scroll_content_widget = QWidget()
            scroll_content_layout = QVBoxLayout(scroll_content_widget)
            # Добавляем виджеты в scroll_content_layout
            scroll_content_layout.addWidget(grBox_run_meas_widget)
            ######################
            scroll_content_layout.addItem(spacer_v_scroll)
            scroll_area_menu.setWidget(scroll_content_widget)
            menu_widget = QWidget()
            menu_layout = QVBoxLayout(menu_widget)
            menu_layout.addWidget(scroll_area_menu)
            # Создаем макет для подключения
            vLayout_ser_connect = QVBoxLayout()
            add_serial_widget(vLayout_ser_connect, self.w_ser_dialog)
            menu_layout.addItem(spacer_v)
            menu_layout.addLayout(vLayout_ser_connect)
            return menu_widget

        # Функция для создания вкладки "Парсер"
        def init_tab_widget_item_parser() -> QWidget:
            parser_widget = QWidget()
            # vLayout_parser = QVBoxLayout(parser_widget)
            return parser_widget

        tab_widget = QTabWidget()
        tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Настройка шрифта для вкладок
        tab_font = QFont()
        tab_font.setFamily("Arial")
        tab_font.setPointSize(12)
        tab_widget.setFont(tab_font)

        # Используем фабрику для добавления вкладок
        factories = build_tab_factories()
        for tab_name, factory in factories.items():
            tab_widget.addTab(factory(), tab_name)
        return tab_widget




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