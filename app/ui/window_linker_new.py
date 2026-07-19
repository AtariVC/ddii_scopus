"""Новый window_linker — ваша архитектура + компоновка из схемы (ТЗ §2).

    [рельс] [ Заголовок экрана · хлебная крошка          ]
    [рельс] [ сайдбар | рабочая область | инспектор      ]
    [ ● Подключено · Serial · MPP 14 · [btn] · State: RUN ]

Что сохранено из вашего window_linker.py:
  * класс MainUIRenderer(QMainWindow), сигналы и общие поля;
  * init_widgets() — те же виджеты, с тем же `self` в конструкторе;
  * декларативная модель (widget_model → screen_model) вместо ручной вёрстки;
  * bootstrap на qasync в __main__.

Что изменилось по ТЗ:
  * вместо табов — рельс иконок + QStackedWidget (§3: единственный способ
    переключения экранов);
  * loadUi/.ui больше не нужен — центральный виджет строится кодом;
  * подключение переехало из секции сайдбара в постоянную нижнюю панель (§8);
    детальные параметры связи остались на экране «Настройка → Соединение»;
  * тема — глобальный QSS палитры ddii (§9/§10) вместо qtmodern.

Положить вместо app/window_linker.py (импорты app.* оставлены как у вас).
"""
import asyncio
import sys

import qasync
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget, QFrame
)

from dark_pro_widgets import theme, qss, NavRail, configure_pyqtgraph

from app.src.components.log.config import log_init
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
from app.widgets.viewer_hdf5.explorer_hdf5_widget import ExplorerHDF5Widget
from app.widgets.viewer_hdf5.filter_viewer_widget import FilterViewerWidget
from app.widgets.viewer_hdf5.graph_viewer_widget import GraphViewerWidget

_FONT = theme.FONT_FAMILY.split(",")[0].strip()

SIDEBAR_WIDTH = 296
INSPECTOR_WIDTH = 344


class MainUIRenderer(QtWidgets.QMainWindow):
    coroutine_get_client_finished = QtCore.pyqtSignal()

    shared_bfr_update_event: Event

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Консоль детектора ddii")
        self.resize(1300, 820)

        self.shared_bfr_update_event = Event(str)  # общий буфер обмена данными
        self.mw: ModbusWorker = ModbusWorker()
        self.parser: Parsers = Parsers()
        self.logger = log_init()

        self.init_widgets()
        self.build_ui()

    # --- виджеты (как в вашем init_widgets) ----------------------------------
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

    # --- модель экранов -----------------------
    def screen_model(self) -> dict:
        """экран -> {иконка, сайдбар: {секция: виджет}, рабочая область, инспектор}."""
        return {
            "Осциллограф": {
                "icon": "∿",
                "breadcrumb": "2 детектора · телескоп совпадений",
                "sidebar": {
                    "Меню запуска": self.run_meas_widget,
                    "Опрос счётчика частиц": self.run_flux_widget,
                },
                "work": self.w_graph_widget,
                "inspector": {"Счётчик частиц": self.flux_widget},
            },
            "Настройка": {
                "icon": "⚙",
                "breadcrumb": "Параметры прибора и связи",
                "sidebar": {
                    "МПП": self.mpp_settings_widget,
                    "ЦМ: Питание": self.cm_settings_widget,
                },
                # подключение вынесено в постоянную нижнюю панель (ТЗ §8);
                # детальный экран «Соединение» появится здесь позже
                "work": None,
                "inspector": None,
            },
            "Диагностика": {
                "icon": "◷",
                "breadcrumb": "Телеметрия и журнал событий",
                "sidebar": {
                    "Опрос телеметрии": self.telemetry_poll_widget,
                    "Тестирование": self.test_runner_widget,
                    "Чтение памяти": self.cmd_wind_read_mem,
                },
                "work": self.test_tables_widget,
                "inspector": None,
            },
            "Вьюер": {
                "icon": "▤",
                "breadcrumb": "Архив прогонов",
                "sidebar": {"Файл менеджер": self.explorer_hdf5_widget},
                "work": self.graph_viewer_widget,
                "inspector": {"Фильтр кадров": self.graph_filter_widget},
            },
        }

    # --- сборка окна ---------------------------------------------------------
    def build_ui(self) -> None:
        self.model = self.screen_model()

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # верхняя область: рельс | (заголовок + стек экранов)
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(0)

        self.rail = NavRail([(cfg["icon"], name) for name, cfg in self.model.items()])
        self.rail.currentChanged.connect(self.on_screen_changed)
        top.addWidget(self.rail)

        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        content.addWidget(self._build_header())

        self.stack = QStackedWidget()
        for cfg in self.model.values():
            self.stack.addWidget(self._build_screen(cfg))
        content.addWidget(self.stack, stretch=1)
        top.addLayout(content, stretch=1)
        outer.addLayout(top, stretch=1)

        # постоянная нижняя панель связи (ТЗ §8) — она же w_ser_dialog: панель
        # сама управляет подключением и отдаёт бэкенд-API потребителям.
        self.connection = self.w_ser_dialog
        outer.addWidget(self.connection)

        self.on_screen_changed(0)

    def _build_header(self) -> QFrame:
        bar = QFrame()
        bar.setStyleSheet(
            f"background-color: {theme.BG}; border-bottom: 1px solid {theme.BORDER};"
        )
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(2)
        self._title = QLabel()
        self._title.setStyleSheet(
            f"color: {theme.TEXT}; font-family: '{_FONT}'; font-size: 20px; "
            "font-weight: 700; background: transparent; border: none;"
        )
        self._crumb = QLabel()
        self._crumb.setStyleSheet(
            f"color: {theme.TEXT_DIM}; background: transparent; border: none;"
        )
        lay.addWidget(self._title)
        lay.addWidget(self._crumb)
        return bar

    def _build_screen(self, cfg: dict) -> QWidget:
        screen = QWidget()
        row = QHBoxLayout(screen)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        if cfg.get("sidebar"):
            row.addWidget(self._build_column(cfg["sidebar"], SIDEBAR_WIDTH))

        work = cfg.get("work")
        if work is not None:
            holder = QWidget()
            holder.setStyleSheet(f"background-color: {theme.BG};")
            lay = QVBoxLayout(holder)
            lay.setContentsMargins(16, 16, 16, 16)
            lay.addWidget(work)
            row.addWidget(holder, stretch=1)
        else:
            row.addStretch(1)

        if cfg.get("inspector"):
            row.addWidget(self._build_column(cfg["inspector"], INSPECTOR_WIDTH))
        return screen

    def _build_column(self, sections: dict, width: int) -> QWidget:
        host = QWidget()
        host.setFixedWidth(width)
        host.setStyleSheet(f"background-color: {theme.BG};")
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
        name = list(self.model.keys())[index]
        self._title.setText(name)
        self._crumb.setText(self.model[name].get("breadcrumb", ""))

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())   # тема ddii вместо qtmodern
    configure_pyqtgraph()

    w: MainUIRenderer = MainUIRenderer()

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
