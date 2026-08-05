"""Главное окно консоли ддии.

    [рельс] [ Заголовок экрана · хлебная крошка          ]
    [рельс] [ сайдбар | рабочая область | инспектор      ]
    [ ● Подключено │ Serial TCP │ ⚙ │ Подключить … State ]

Оболочка окна поднимается из ``ui_designer.ui`` через ``loadUi``. Рельс, страницы стека, колонки экрана собирается в 
Python, потому что зависит от модели.

Слоты из .ui: ``layout_rail``, ``label_title``/``label_crumb``, ``stack``,
``layout_connection``.

Запуск (из корня проекта):  python main.py  ·  python -m app.ui.ui_designer
"""

import asyncio
import sys
from pathlib import Path

import qasync
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget
from qtpy.uic import loadUi

from dark_pro_widgets import NavRail, qss, theme

from custom.icons import load_svg_icon

from app.plugins.connection.connection_bar import ConnectionBar
from app.src.components.log.config import log_init
from app.src.components.modbus.worker import ModbusWorker
from app.src.components.parsers.custom_parsers import Parsers
from app.src.event.event import Event
# from app.widgets.debug.debug_graph import DebugGraphWidget
from app.widgets.oscilloscope.flux_widget import FluxWidget
from app.widgets.oscilloscope.graph_widget import GraphWidget
from app.widgets.oscilloscope.run_control_widget import RunControlWidget
from app.widgets.controls.control_panel import ControlPanel
# from app.widgets.parser.cmd_wind_read_mem import CmdWindReadMemWidget
# from app.widgets.settings.cm_settings_widget import CmSettingsWidget
# from app.widgets.settings.mpp_settings_widget import MppSettingsWidget
# from app.widgets.tests.runner_widget import TestRunnerWidget
# from app.widgets.tests.tables_widget import TestTablesWidget
# from app.widgets.tests.telemetry_poll_widget import TelemetryPollWidget
from app.widgets.viewer.explorer_widget import ExplorerHDF5Widget
from app.widgets.viewer.filter_viewer_widget import FilterViewerWidget
from app.widgets.viewer.graph_viewer_widget import GraphViewerWidget
from app.widgets.oscilloscope.test_impact_ctrl import TestImpactControl

_FONT = theme.FONT_FAMILY.split(",")[0].strip()

SIDEBAR_WIDTH = 296
INSPECTOR_WIDTH = 344

# Рабочая область утоплена: темнее колонок, чтобы карточки графиков читались
# как приподнятые над фоном.
WORK_BG = theme.FIELD_BG


class MainUIDesigner(QtWidgets.QMainWindow):
    coroutine_get_client_finished = QtCore.pyqtSignal()

    shared_bfr_update_event: Event

    # слоты и виджеты из .ui
    layout_rail: QVBoxLayout
    layout_connection: QVBoxLayout
    stack: QStackedWidget
    stack_control_panel: QStackedWidget
    action_quit: QtCore.QObject

    def __init__(self) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath("ui_designer.ui"), self)

        self.shared_bfr_update_event = Event(str)  # общий буфер обмена данными
        self.mw: ModbusWorker = ModbusWorker()
        self.parser: Parsers = Parsers()
        self.logger = log_init()

        self._titlebar_tinted = False
        self.init_widgets()
        self.build_ui()

    # --- системный заголовок ---------------------------------------------------
    def showEvent(self, event) -> None:  # noqa: N802 - имя из Qt
        super().showEvent(event)
        self._tint_titlebar()

    def _tint_titlebar(self) -> None:
        """Красит системную рамку окна.
        """
        if sys.platform != "win32" or self._titlebar_tinted:
            return
        self._titlebar_tinted = True
        try:
            import ctypes

            hwnd = int(self.winId())
            dwm = ctypes.windll.dwmapi  # type: ignore[attr-defined]
            flag = ctypes.c_int(1)
            # DWMWA_USE_IMMERSIVE_DARK_MODE: 20 в свежих сборках, 19 в ранних
            for attr in (20, 19):
                if dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(flag),
                                             ctypes.sizeof(flag)) == 0:
                    break
            # DWMWA_CAPTION_COLOR ждёт COLORREF в порядке 0x00BBGGRR
            rgb = QColor(theme.BG)
            colorref = ctypes.c_uint((rgb.blue() << 16) | (rgb.green() << 8) | rgb.red())
            dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(colorref),
                                      ctypes.sizeof(colorref))
        except Exception as e:  # noqa: BLE001 - косметика, падать из-за неё нельзя
            self.logger.debug(f"Не удалось покрасить заголовок окна: {e}")

    # --- виджеты -------------------------------------------------------------
    def init_widgets(self) -> None:
        # порядок важен: панель запуска в конструкторе обращается к графикам,
        # счётчику частиц и связи
        self.w_graph_widget: GraphWidget = GraphWidget()
        self.w_ser_dialog: ConnectionBar = ConnectionBar()
        self.flux_widget: FluxWidget = FluxWidget()
        self.run_control_widget: RunControlWidget = RunControlWidget(self)
        self.client = self.w_ser_dialog.client
        self.explorer_hdf5_widget: ExplorerHDF5Widget = ExplorerHDF5Widget()
        self.graph_viewer_widget: GraphViewerWidget = GraphViewerWidget(self)
        self.graph_filter_widget: FilterViewerWidget = FilterViewerWidget(self)
        # self.graph_debug_widget: DebugGraphWidget = DebugGraphWidget()
        # self.cmd_wind_read_mem: CmdWindReadMemWidget = CmdWindReadMemWidget(self)
        # self.test_tables_widget: TestTablesWidget = TestTablesWidget()
        # self.telemetry_poll_widget: TelemetryPollWidget = TelemetryPollWidget(self)
        # self.test_runner_widget: TestRunnerWidget = TestRunnerWidget()
        # self.mpp_settings_widget: MppSettingsWidget = MppSettingsWidget(self)
        # self.cm_settings_widget: CmSettingsWidget = CmSettingsWidget(self)
        self.test_impact_ctrl: TestImpactControl = TestImpactControl(self)
        self.stack_control_panel = QStackedWidget()
        self.control_panel = ControlPanel(self)
        self.control_panel.build_stack_widget()

    # --- модель экранов ------------------------------------------------------
    def screen_model(self) -> dict:
        """экран -> {иконка, крошка, сайдбар: {секция: виджет}, рабочая область, инспектор}."""
        return {
            "Измерение": {
                "icon": "board",
                "breadcrumb": "Электроны · Протоны · ТЗЧ",
                "sidebar": {"Меню запуска": self.run_control_widget,
                            "Тестовое воздействие": self.test_impact_ctrl},
                "work": self.w_graph_widget,
                "inspector": {"Счётчик частиц": self.flux_widget},
            },
            "Смотрилка": {
                "icon": "history",
                "breadcrumb": "Архив прогонов",
                "sidebar": {"Файл менеджер": self.explorer_hdf5_widget},
                "work": self.graph_viewer_widget,
                "inspector": {"Фильтр кадров": self.graph_filter_widget},
            },
            "Управление и настройка": {
                "icon": "settings",
                "breadcrumb": "Настройки",
                "sidebar": {
                    "Опрос телеметрии": self.control_panel,
                },
                "work": self.stack_control_panel,
                "inspector": None,
            },
            # "Общее состояние прибора": {
            #     "icon": "bug-report",
            #     "breadcrumb": "Параметры прибора и связи",
            #     "sidebar": {
            #         "МПП": self.mpp_settings_widget,
            #         "ЦМ: Питание": self.cm_settings_widget,
            #     },
            #     "work": None,
            #     "inspector": None,
            # },

        }

    # --- сборка окна ---------------------------------------------------------
    def build_ui(self) -> None:
        self.model = self.screen_model()

        self.rail = NavRail(
            [(self._rail_icon(cfg["icon"]), name) for name, cfg in self.model.items()]
        )
        self.rail.currentChanged.connect(self.on_screen_changed)
        self.layout_rail.addWidget(self.rail)

        for name, cfg in self.model.items():
            self.stack.addWidget(self._build_screen(name, cfg))

        # нижняя панель связи — она же w_ser_dialog: сама управляет подключением
        # и отдаёт бэкенд-API остальным виджетам
        self.connection = self.w_ser_dialog
        self.layout_connection.addWidget(self.connection)

        self.action_quit.triggered.connect(self.close) # type: ignore
        self.on_screen_changed(0)

    @staticmethod
    def _rail_icon(name: str) -> QIcon:
        size = QSize(22, 22)
        icon = QIcon()
        icon.addPixmap(load_svg_icon(name, theme.TEXT_DIM).pixmap(size),
                       QIcon.Mode.Normal, QIcon.State.Off)
        icon.addPixmap(load_svg_icon(name, theme.ACCENT).pixmap(size),
                       QIcon.Mode.Normal, QIcon.State.On)
        return icon

    def _build_screen(self, name: str, cfg: dict) -> QWidget:
        screen = QWidget()
        row = QHBoxLayout(screen)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        if cfg.get("sidebar"):
            row.addWidget(self._build_column(cfg["sidebar"], SIDEBAR_WIDTH, "left"))

        # правее сайдбара: шапка во всю ширину, под ней рабочая область и инспектор
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)
        right_lay.addWidget(self._build_header(name, cfg.get("breadcrumb", "")))

        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        # рабочая область на утопленном фоне — карточки читаются приподнятыми
        holder = QWidget()
        holder.setObjectName("WorkArea")
        holder.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        holder.setStyleSheet(f"#WorkArea {{ background-color: {WORK_BG}; }}")
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(16, 16, 16, 16)

        work = cfg.get("work")
        if work is not None:
            lay.addWidget(work, stretch=1)
        else:
            lay.addStretch(1)
        body_lay.addWidget(holder, stretch=1)

        if cfg.get("inspector"):
            body_lay.addWidget(self._build_column(cfg["inspector"], INSPECTOR_WIDTH, "right"))

        right_lay.addWidget(body, stretch=1)
        row.addWidget(right, stretch=1)
        return screen

    def _build_header(self, title: str, breadcrumb: str) -> QWidget:
        """Шапка экрана: заголовок и хлебная крошка, во всю ширину над рабочей
        областью и инспектором, отделённая линией."""
        head = QWidget()
        head.setObjectName("ScreenHeader")
        head.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        head.setStyleSheet(
            f"#ScreenHeader {{ background-color: {theme.BG}; "
            f"border-bottom: 1px solid {theme.SEPARATOR}; }}"
        )
        lay = QVBoxLayout(head)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(2)

        label_title = QLabel(title)
        label_title.setStyleSheet(
            f"color: {theme.TEXT}; font-family: '{_FONT}'; font-size: 20px; "
            "font-weight: 700; background: transparent; border: none;"
        )
        label_crumb = QLabel(breadcrumb)
        label_crumb.setStyleSheet(
            f"color: {theme.TEXT_DIM}; background: transparent; border: none;"
        )
        lay.addWidget(label_title)
        lay.addWidget(label_crumb)
        return head

    def _build_column(self, sections: dict, width: int, side: str) -> QWidget:
        """Боковая колонка. ``side`` задаёт, с какой стороны отделить её линией
        от рабочей области: 'left' — сайдбар (линия справа), 'right' — инспектор.
        """
        host = QWidget()
        host.setObjectName("SideColumn")
        # без WA_StyledBackground QWidget-подкласс не рисует рамку из QSS
        host.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        host.setFixedWidth(width)
        edge = "border-right" if side == "left" else "border-left"
        host.setStyleSheet(
            f"#SideColumn {{ background-color: {theme.BG}; "
            f"{edge}: 1px solid {theme.SEPARATOR}; }}"
        )
        lay = QVBoxLayout(host)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(14)
        for title, widget in sections.items():
            lay.addWidget(self._section_label(title))
            lay.addWidget(widget)
        lay.addStretch()
        return host

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-family: '{_FONT}'; font-size: 11px; "
            "font-weight: 600; letter-spacing: 1px; background: transparent;"
        )
        return lbl

    # --- слоты ---------------------------------------------------------------
    def on_screen_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())  # тема ddii

    w: MainUIDesigner = MainUIDesigner()

    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    w.show()

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
