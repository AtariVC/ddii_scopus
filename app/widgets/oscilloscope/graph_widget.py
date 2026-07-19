"""Рабочая область осциллографа: детекторы PIPS/SiPM и их гистограммы.

Разметка — ``graph_widget.ui``: пять карточек (заголовок + бейдж + место под
график). Сами графики рисует прежний движок ``GraphPen``/``HistPen`` — в нём
живут фильтрация выбросов, биннинг и сохранение в HDF5, поэтому он не заменён
виджетами из dark_pro_widgets; здесь только оформление и цвета из темы.

Запуск отдельно, с демо-данными:

    python app/widgets/oscilloscope/graph_widget.py
    python -m app.widgets.oscilloscope.graph_widget
"""

# Прямой запуск файла: абсолютные импорты `app.*` работают только когда модуль
# исполняется в контексте пакета — перезапускаем его как модуль пакета.
if __name__ == "__main__" and __package__ in (None, ""):
    import os
    import runpy
    import sys

    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    runpy.run_module("app.widgets.oscilloscope.graph_widget", run_name="__main__", alter_sys=True)
    raise SystemExit(0)

from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QColor
from qtpy.uic import loadUi

from dark_pro_widgets import theme

from app.src.components.modbus.worker import ModbusWorker
from app.src.components.parsers.custom_parsers import Parsers
from app.src.components.plot.plot_renderer import GraphPen, HistPen
from app.widgets.oscilloscope.flux_widget import format_count

_FONT = theme.FONT_FAMILY.split(",")[0].strip()
_MONO = theme.MONO_FAMILY.split(",")[0].strip()

# Показывать ли числовые шкалы по осям. На макете область чистая, но для работы
# со шкалой значения нужны — поставь False, если хочется «как на картинке».
SHOW_AXES = True

# Цвет закреплён за каналом и используется и для графика, и для точки у заголовка
COLOR_PIPS = theme.PIPS        # зелёный
COLOR_SIPM = theme.SIPM        # янтарный
COLOR_COUNTER = theme.ACCENT   # синий

# Цифры в бейджах (пик, Σ) — приглушённые, чтобы не спорить с цветом канала
BADGE_COLOR = theme.TEXT_DIM


def _rgb(hex_color: str, alpha: int | None = None) -> tuple:
    """'#3fb950' -> (63, 185, 80[, alpha]) — GraphPen/HistPen ждут кортеж."""
    color = QColor(hex_color)
    rgb = (color.red(), color.green(), color.blue())
    return rgb if alpha is None else (*rgb, alpha)


class GraphWidget(QtWidgets.QWidget):
    # места под графики (в них движок добавляет свои PlotWidget)
    vLayout_pips: QtWidgets.QVBoxLayout
    vLayout_sipm: QtWidgets.QVBoxLayout
    vLayout_hist_pips: QtWidgets.QVBoxLayout
    vLayout_hist_sipm: QtWidgets.QVBoxLayout
    vLayout_hist_counter: QtWidgets.QVBoxLayout
    # карточки и бейджи
    card_pips: QtWidgets.QFrame
    card_sipm: QtWidgets.QFrame
    card_hist_pips: QtWidgets.QFrame
    card_hist_sipm: QtWidgets.QFrame
    card_counter: QtWidgets.QFrame
    badge_pips: QtWidgets.QLabel
    badge_sipm: QtWidgets.QLabel
    badge_hist_pips: QtWidgets.QLabel
    badge_hist_sipm: QtWidgets.QLabel
    badge_counter: QtWidgets.QLabel

    def __init__(self) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath("graph_widget.ui"), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.task = None  # type: ignore

        # Глобальные настройки pyqtgraph — здесь, чтобы графики были в теме
        # независимо от точки входа (main.py configure_pyqtgraph не вызывает).
        pg.setConfigOptions(antialias=True, background=theme.PANEL_BG, foreground=theme.TEXT_DIM)

        # Цвет закреплён за каналом: PIPS — зелёный, SiPM — янтарный (осциллограмма
        # и гистограмма одним цветом), счётчик телескопа — синий.
        self.gp_pips = GraphPen(layout=self.vLayout_pips, name="pips", color=_rgb(COLOR_PIPS))
        self.gp_sipm = GraphPen(layout=self.vLayout_sipm, name="sipm", color=_rgb(COLOR_SIPM))
        self.hp_pips = HistPen(layout=self.vLayout_hist_pips, name="h_pips",
                               color=_rgb(COLOR_PIPS, 150))
        self.hp_sipm = HistPen(layout=self.vLayout_hist_sipm, name="h_sipm",
                               color=_rgb(COLOR_SIPM, 150))
        self.hp_counter = HistPen(layout=self.vLayout_hist_counter, name="h_counter",
                                  color=_rgb(COLOR_COUNTER, 150))

        self._apply_theme()
        # Бейджи обновляются только по вызову refresh_badges() — дёргай её после
        # отрисовки графиков. Здесь только начальное состояние («пик —», «Σ —»).
        self.refresh_badges()

    # ===== оформление =====
    def _apply_theme(self) -> None:
        # цвет точки у заголовка = цвет графика этой карточки
        cards = {
            self.card_pips: COLOR_PIPS,
            self.card_hist_pips: COLOR_PIPS,
            self.card_sipm: COLOR_SIPM,
            self.card_hist_sipm: COLOR_SIPM,
            self.card_counter: COLOR_COUNTER,
        }
        for card, color in cards.items():
            name = card.objectName()
            card.setStyleSheet(
                f"QFrame {{ background-color: {theme.PANEL_BG};"
                f" border: 1px solid {theme.BORDER}; border-radius: 8px; }}"
            )
            title = card.findChild(QtWidgets.QLabel, f"title_{name}")
            if title is not None:
                title.setStyleSheet(
                    f"color: {theme.TEXT}; font-family: '{_FONT}'; font-size: 15px; "
                    "font-weight: 600; background: transparent; border: none;"
                )
            dot = card.findChild(QtWidgets.QLabel, f"dot_{name}")
            if dot is not None:
                dot.setStyleSheet(
                    f"color: {color}; font-size: 13px; background: transparent; border: none;"
                )

        # Гистограммы: контур той же краской, что и заливка (в движке он белый)
        for hist in (self.hp_pips, self.hp_sipm, self.hp_counter):
            hist.outline_pen = pg.mkPen(hist.color, width=1.6)

        for widget in (self.gp_pips.plt_widget, self.gp_sipm.plt_widget,
                       self.hp_pips.hist_widget, self.hp_sipm.hist_widget,
                       self.hp_counter.hist_widget):
            self._style_plot(widget)

    @staticmethod
    def _style_plot(widget: pg.PlotWidget) -> None:
        """Тёмная область с еле заметной сеткой — как на макете.

        Штатные органы управления pyqtgraph оставляем: кнопка авторазмера в углу
        (вписать весь график) и контекстное меню по правой кнопке с «View All»,
        экспортом и настройками осей. Колесо — зум, перетаскивание — панорама.
        """
        widget.setBackground(theme.FIELD_BG)
        widget.setMenuEnabled(True)
        item = widget.getPlotItem()
        item.showButtons()
        item.showGrid(x=True, y=True, alpha=0.12)
        item.setContentsMargins(4, 4, 4, 4)
        for axis in ("left", "bottom"):
            ax = item.getAxis(axis)
            ax.setPen(pg.mkPen(theme.BORDER))
            ax.setTextPen(pg.mkPen(theme.TEXT_DIM))
            # Сетку рисуют сами оси — прятать их нельзя, иначе она исчезнет.
            # Убираем только числовые подписи (по макету область чистая).
            ax.setStyle(showValues=SHOW_AXES)

    def _set_badge(self, badge: QtWidgets.QLabel, text: str, color: str) -> None:
        badge.setText(text)
        badge.setStyleSheet(
            f"color: {color}; font-family: '{_MONO}'; font-size: 12px; font-weight: 600; "
            "background: transparent; border: none;"
        )

    # ===== работа с областью просмотра =====
    def plots(self) -> list:
        """Все PlotWidget'ы (pyqtgraph) в порядке карточек."""
        return [self.gp_pips.plt_widget, self.hp_pips.hist_widget,
                self.gp_sipm.plt_widget, self.hp_sipm.hist_widget,
                self.hp_counter.hist_widget]

    def fit_view(self) -> None:
        """Вписать все графики в область — то же, что кнопка авторазмера.

        Именно ``enableAutoRange()``: разовый ``autoRange()`` подогнал бы вид, но
        выключил автослежение, и новые данные снова вылезали бы за границы.
        """
        for widget in self.plots():
            widget.getPlotItem().enableAutoRange()

    # ===== состояние в бейджах =====
    @staticmethod
    def _total_of(hist) -> float:
        """Σ накопленной гистограммы (движок хранит её в ``accum_data``)."""
        try:
            data = getattr(hist, "accum_data", None)
            if data is not None and len(data):
                return float(np.sum(data))
        except Exception:
            ...
        return 0.0

    @staticmethod
    def _peak_of(pen) -> float | None:
        """Пик текущей осциллограммы. Читаем прямо из отрисованных данных,
        чтобы не трогать движок: ``plot_item`` появляется после первой отрисовки.
        """
        item = getattr(pen, "plot_item", None)
        if item is None:
            return None
        try:
            _x, y = item.getData()
        except Exception:
            return None
        if y is None or len(y) == 0:
            return None
        return float(np.max(y))

    def refresh_badges(self) -> None:
        """Пересчитать пики и Σ по текущим данным графиков.

        Вызывается сама раз в секунду, но её можно дёрнуть вручную — например
        сразу после отрисовки, не дожидаясь тика таймера.

        Все числа приглушённые: цвет канала несёт точка у заголовка и сам
        график, а бейдж — второстепенная справка и не должен спорить с ними.
        """
        # пик осциллограмм — АЦП короткий (0..4095), показываем точно, без k/M
        for pen, badge in ((self.gp_pips, self.badge_pips),
                           (self.gp_sipm, self.badge_sipm)):
            peak = self._peak_of(pen)
            text = "пик —" if peak is None else f"пик {peak:.0f}"
            self._set_badge(badge, text, BADGE_COLOR)

        # Σ по накопленным данным гистограмм
        for hist, badge in ((self.hp_pips, self.badge_hist_pips),
                            (self.hp_sipm, self.badge_hist_sipm),
                            (self.hp_counter, self.badge_counter)):
            total = self._total_of(hist)
            self._set_badge(badge, f"Σ {format_count(total)}" if total else "Σ —", BADGE_COLOR)


if __name__ == "__main__":
    import asyncio
    import sys

    import qasync

    from dark_pro_widgets import qss

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())

    # draw_graph/draw_hist — асинхронные слоты, без qasync-петли они не выполнятся
    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    host = QtWidgets.QWidget()
    host.setWindowTitle("Осциллограф — автономный запуск")
    host.setStyleSheet(f"background-color: {theme.BG};")
    layout = QtWidgets.QVBoxLayout(host)
    layout.setContentsMargins(16, 16, 16, 16)

    widget = GraphWidget()
    layout.addWidget(widget)

    # демо-данные: два пика на осциллограмме, как на макете
    rng = np.random.default_rng(7)
    base = np.linspace(0, 1, 400)
    trace = (900 * np.exp(-((base - 0.25) ** 2) / 0.0008)
             + 450 * np.exp(-((base - 0.55) ** 2) / 0.006)
             + rng.normal(0, 25, base.size) + 120)
    # гистограммы накапливают амплитуды пиков в диапазоне АЦП [0, bin_count]
    peaks = np.concatenate([rng.normal(1100, 120, 9000), rng.normal(2600, 90, 2200)])
    peaks = np.clip(peaks, 0, 4095).astype(int)

    async def _draw_demo():
        await widget.gp_pips.draw_graph(trace.astype(int).tolist(), clear=True)
        await widget.gp_sipm.draw_graph((trace * 0.92).astype(int).tolist(), clear=True)
        await widget.hp_pips.draw_hist(peaks.tolist(), clear=True)
        await widget.hp_sipm.draw_hist((peaks * 0.95).astype(int).tolist(), clear=True)
        widget.refresh_badges()

    QtCore.QTimer.singleShot(0, lambda: asyncio.ensure_future(_draw_demo()))

    host.resize(1000, 780)
    host.show()

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
