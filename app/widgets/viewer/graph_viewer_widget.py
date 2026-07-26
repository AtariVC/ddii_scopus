import asyncio
import re
import sys
from dataclasses import dataclass

from pathlib import Path

import numpy as np
import pyqtgraph as pg
import qasync
import qtmodern.styles
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QColor
from qtpy.uic import loadUi

from dark_pro_widgets import theme, PlaybackBar

from app.widgets.viewer.explorer_widget import ExplorerHDF5Widget
from app.widgets.oscilloscope.flux_widget import format_count
from app.src.components.log.config import get_logger, log_init

from app.src.event.event import Event
from app.src.components.plot.plot_renderer import GraphPen, HistPen
from app.src.util.write_data_to_file import read_hdf5_file, write_to_hdf5_file

_FONT = theme.FONT_FAMILY.split(",")[0].strip()
_MONO = theme.MONO_FAMILY.split(",")[0].strip()

# Цвет закреплён за каналом: и для графика, и для точки у заголовка карточки.
COLOR_PIPS = theme.PIPS        # зелёный
COLOR_SIPM = theme.SIPM        # янтарный
COLOR_COUNTER = theme.ACCENT   # синий

# Цифры в бейджах приглушённые, чтобы не спорить с цветом канала.
BADGE_COLOR = theme.TEXT_DIM


def _rgb(hex_color: str, alpha: int | None = None) -> tuple:
    """'#3fb950' -> (63, 185, 80[, alpha]) — GraphPen/HistPen ждут кортеж."""
    color = QColor(hex_color)
    rgb = (color.red(), color.green(), color.blue())
    return rgb if alpha is None else (*rgb, alpha)


class GraphViewerWidget(QtWidgets.QWidget):
    verticalLayout_graph: QtWidgets.QVBoxLayout
    vLayout_hist_pips: QtWidgets.QVBoxLayout
    vLayout_hist_sipm: QtWidgets.QVBoxLayout
    vLayout_hist_counter: QtWidgets.QVBoxLayout
    vLayout_pips: QtWidgets.QVBoxLayout
    vLayout_sipm: QtWidgets.QVBoxLayout
    vLayout_playback: QtWidgets.QVBoxLayout
    playback: PlaybackBar
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

    slider_update_event: Event

    def __init__(self, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath("graph_viewer_widget.ui"), self)
        # Графики должны быть в теме независимо от точки входа.
        pg.setConfigOptions(antialias=True, background=theme.PANEL_BG, foreground=theme.TEXT_DIM)
        self.pen_init()
        self._apply_theme()
        self.massageBox = QtWidgets.QMessageBox()
        self.massageBox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        self.logger = log_init()
        self.slider_update_event = Event(int)
        self.parent_hdf5_path = ""
        self._init_playback()
        if __name__ != "__main__":
            self.parent = args[0]
            self.explorer: ExplorerHDF5Widget = self.parent.explorer_hdf5_widget  # type: ignore
            self.explorer.double_clicked_event.subscribe(self.open_graphs)
        # External filter widget will control filtering/navigation

    def _init_playback(self) -> None:
        """Транспорт покадрового просмотра — готовый виджет из dark_pro_widgets."""
        self.playback = PlaybackBar(total_frames=1, frame=1, time_text="—")
        self.vLayout_playback.addWidget(self.playback)
        # Слайдер и кнопки ⏮/⏭ шлют frameChanged; play/pause — playToggled.
        self.playback.frameChanged.connect(lambda _v: self.slider_graphs_updater())
        self.playback.playToggled.connect(self._on_play_toggled)
        # Авто-проигрывание: таймер прокручивает кадры, пока нажат play.
        self._play_timer = QtCore.QTimer(self)
        self._play_timer.setInterval(100)  # ~10 кадров/с
        self._play_timer.timeout.connect(self._advance_frame)

    def _on_play_toggled(self, playing: bool) -> None:
        if playing and self.amount_measurements:
            self._play_timer.start()
        else:
            self._play_timer.stop()

    def _advance_frame(self) -> None:
        """Шаг авто-проигрывания: следующий кадр, в конце — стоп."""
        nxt = self.playback.current_frame() + 1
        if self.amount_measurements == 0 or nxt > self.amount_measurements:
            self._play_timer.stop()
            self.playback.set_playing(False)
            return
        self.playback.set_frame(nxt)  # не эмитит frameChanged
        self.slider_graphs_updater()

    def pen_init(self) -> None:
        self.task = None  # type: ignore
        self.name_pen_pips = "pips"
        self.name_pen_sipm = "sipm"
        self.name_pen_h_pips = "h_pips"
        self.name_pen_h_sipm = "h_sipm"
        self.name_pen_counter = "h_counter"
        self.amount_measurements = 0
        self.measure_time_list = []
        self.dataset_pips: dict = {}
        self.dataset_sipm: dict = {}
        self.dataset_h_pips: dict = {}
        self.dataset_h_sipm: dict = {}
        # Цвет закреплён за каналом: PIPS — зелёный, SiPM — янтарный (осциллограмма
        # и гистограмма одним цветом), счётчик событий — синий.
        self.gp_pips = GraphPen(layout=self.vLayout_pips, name=self.name_pen_pips, color=_rgb(COLOR_PIPS))
        self.gp_sipm = GraphPen(layout=self.vLayout_sipm, name=self.name_pen_sipm, color=_rgb(COLOR_SIPM))
        self.hp_pips = HistPen(layout=self.vLayout_hist_pips, name=self.name_pen_h_pips, color=_rgb(COLOR_PIPS, 150))
        self.hp_sipm = HistPen(layout=self.vLayout_hist_sipm, name=self.name_pen_h_sipm, color=_rgb(COLOR_SIPM, 150))
        self.counter_h = HistPen(
            layout=self.vLayout_hist_counter, name=self.name_pen_counter, color=_rgb(COLOR_COUNTER, 150)
        )
        # Filtering state managed by external widget

    # ===== оформление =====
    def _apply_theme(self) -> None:
        """Карточки, точки у заголовков и тёмные области графиков — как на макете."""
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

        # Гистограммы: контур той же краской, что и заливка (в движке он белый).
        for hist in (self.hp_pips, self.hp_sipm, self.counter_h):
            hist.outline_pen = pg.mkPen(hist.color, width=1.6)

        for widget in (self.gp_pips.plt_widget, self.gp_sipm.plt_widget,
                       self.hp_pips.hist_widget, self.hp_sipm.hist_widget,
                       self.counter_h.hist_widget):
            self._style_plot(widget)

        # Начальное состояние бейджей (транспорт оформлен самим PlaybackBar).
        for badge in (self.badge_pips, self.badge_sipm):
            self._set_badge(badge, "кадр —", BADGE_COLOR)
        for badge in (self.badge_hist_pips, self.badge_hist_sipm):
            self._set_badge(badge, "Σ —", BADGE_COLOR)
        self._set_badge(self.badge_counter, "по кадрам", BADGE_COLOR)

    @staticmethod
    def _style_plot(widget: pg.PlotWidget) -> None:
        """Тёмная область с еле заметной сеткой — как на макете."""
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

    def _set_badge(self, badge: QtWidgets.QLabel, text: str, color: str) -> None:
        badge.setText(text)
        badge.setStyleSheet(
            f"color: {color}; font-family: '{_MONO}'; font-size: 12px; font-weight: 600; "
            "background: transparent; border: none;"
        )

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

    def _refresh_badges(self, frame: int) -> None:
        """Бейджи: у детекторов — номер кадра, у гистограмм — Σ накопленного."""
        for badge in (self.badge_pips, self.badge_sipm):
            self._set_badge(badge, f"кадр {frame}", BADGE_COLOR)
        for hist, badge in ((self.hp_pips, self.badge_hist_pips),
                            (self.hp_sipm, self.badge_hist_sipm)):
            total = self._total_of(hist)
            self._set_badge(badge, f"Σ {format_count(total)}" if total else "Σ —", BADGE_COLOR)

    def open_graphs(self, path: str) -> None:
        """Открывает графики из файла"""
        self.parent_hdf5_path = path
        self.playback.set_playing(False)
        self._play_timer.stop()
        self.dataset_pips = read_hdf5_file(Path(path), self.name_pen_pips)
        self.dataset_sipm = read_hdf5_file(Path(path), self.name_pen_sipm)
        self.dataset_h_pips = read_hdf5_file(Path(path), self.name_pen_h_pips)
        self.dataset_h_sipm = read_hdf5_file(Path(path), self.name_pen_h_sipm)
        self.dataset_h_counter = read_hdf5_file(Path(path), self.name_pen_counter)
        self.amount_measurements = len(self.dataset_h_pips)
        if self.amount_measurements:
            self.measure_time_list = list(self.dataset_h_pips.keys())
            self.playback.set_total_frames(self.amount_measurements)
            self.playback.set_frame(1)
            # PlaybackBar.set_frame не эмитит frameChanged — рисуем первый кадр сами.
            self.slider_graphs_updater()
        else:
            self.playback.set_total_frames(1)
            self.playback.set_time("нет данных")
        # Filter state is external; nothing to reset here

    def time_formater(self, input_time_str: str) -> str:
        """Преобразует строку вида "2024-10-08_17-52-54-261" в формат "Время: 08.10.24 17:52:54:2610"
        Args:
            input_time_str (str): Строка времени в формате "2024-10-08_17-52-54-261"
        Returns:
            str: Преобразованная строка времени в формате "Время: 08.10.24 17
        """
        # Извлекаем компоненты даты и времени
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})-(\d{3})", input_time_str)
        if match:
            year, month, day, hour, minute, second, millis = match.groups()
            output_str = f"Время: {day}.{month}.{year[-2:]} {hour}:{minute}:{second}:{millis}0"
            return output_str
        else:
            return "Время: неверный формат"

    @qasync.asyncSlot()
    async def slider_graphs_updater(self) -> None:
        """Обновляет графики при изменении слайдера"""
        logger = get_logger()
        if self.amount_measurements == 0:
            return
        try:
            current_val = self.playback.current_frame()
            self.slider_update_event.emit(current_val)
            # PlaybackBar сам показывает «кадр N / total»; ему нужна только метка
            # времени (без префикса «Время:» — его виджет добавляет сам).
            time_str = self.time_formater(self.measure_time_list[current_val - 1])
            self.playback.set_time(time_str.replace("Время: ", ""))
            if self.dataset_pips:
                data_pips = list(self.dataset_pips.values())[current_val - 1].T
                await self.gp_pips.draw_graph(data_pips[1], clear=True)
            else:
                self.gp_pips.plt_widget.clear()
            if self.dataset_sipm:
                data_sipm = list(self.dataset_sipm.values())[current_val - 1].T
                await self.gp_sipm.draw_graph(data_sipm[1], clear=True)
            else:
                self.gp_sipm.plt_widget.clear()
            if self.dataset_h_pips:
                data_h_pips = list(self.dataset_h_pips.values())[current_val - 1].T
                await self.hp_pips.draw_hist(data_h_pips[1].tolist(), clear=True, data_is_hist=True)
            else:
                self.hp_pips.hist_clear()
            if self.dataset_h_sipm:
                data_h_sipm = list(self.dataset_h_sipm.values())[current_val - 1].T
                await self.hp_sipm.draw_hist(data_h_sipm[1].tolist(), clear=True, data_is_hist=True)
            else:
                self.hp_sipm.hist_clear()
            if self.dataset_h_counter:
                data_h_counter = list(self.dataset_h_counter.values())[current_val - 1].T
                await self.counter_h.draw_hist(data_h_counter[1].tolist(), clear=True, data_is_hist=True)
            else:
                self.counter_h.hist_clear()
            self._refresh_badges(current_val)
            # await self.hp_pips.draw_hist(data_pips[1], clear=True)
            # await self.hp_sipm.draw_hist(data_sipm[1], clear=True)
        except Exception as ex:
            logger.error(ex)

        # if value < self.amount_measurements:

        # data_pips = self.gp_pips.get_data(value)
        # data_sipm = self.gp_sipm.get_data(value)
        # self.gp_pips.draw_graph(data_pips, "pips", clear=True)
        # self.gp_sipm.draw_graph(data_sipm, "sipm", clear=True)
        # self.hp_pips.draw_histogram(data_pips, "h_pips", clear=True)
        # self.hp_sipm.draw_histogram(data_sipm, "h_sipm", clear=True)

    # Public methods for external filter widget
    def apply_filter(self, level_pips: int | None, level_sipm: int | None, use_pips: bool, use_sipm: bool) -> list[int]:
        if self.amount_measurements == 0:
            return []
        if not (use_pips or use_sipm):
            return []
        pips_thr = 0 if level_pips is None else int(level_pips)
        sipm_thr = 0 if level_sipm is None else int(level_sipm)
        matched_idx: list[int] = []
        for i in range(1, self.amount_measurements + 1):
            # невыбранный канал в условие не входит (остаётся True);
            # выбранный — должен превысить свой порог
            ok_pips = True
            ok_sipm = True
            if use_pips:
                ok_pips = False
                if self.dataset_pips:
                    try:
                        arr = list(self.dataset_pips.values())[i - 1].T[1]
                        ok_pips = max(arr) > pips_thr
                    except Exception:
                        ok_pips = False
            if use_sipm:
                ok_sipm = False
                if self.dataset_sipm:
                    try:
                        arr = list(self.dataset_sipm.values())[i - 1].T[1]
                        ok_sipm = max(arr) > sipm_thr
                    except Exception:
                        ok_sipm = False
            if ok_pips and ok_sipm:
                matched_idx.append(i)
        return matched_idx

    def get_time_for_index(self, idx: int) -> str:
        try:
            if 1 <= idx <= len(self.measure_time_list):
                return self.time_formater(self.measure_time_list[idx - 1])
        except Exception:
            ...
        return ""

    def go_to_index(self, idx: int) -> None:
        try:
            if 1 <= idx <= self.amount_measurements:
                self.playback.set_frame(idx)  # не эмитит frameChanged
                try:
                    # schedule async update
                    asyncio.create_task(self.slider_graphs_updater())
                except Exception:
                    ...
        except Exception:
            ...

    def save_desired_frame_hdf5(self, index):
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})-(\d{3})", self.measure_time_list[index - 1])
        if match:
            year, month, day, hour, minute, second, ms = match.groups()
            time = f"{year}-{month}-{day}_{hour}-{minute}-{second}-{ms}"
        save_path: Path = Path(self.parent_hdf5_path).parent / f"samples/{Path(self.parent_hdf5_path).stem}"
        if index > self.amount_measurements:
            self.massageBox.setText("Warning")
            self.massageBox.setInformativeText("The number of frames must be less than the total number of frames.")
            self.massageBox.setWindowTitle("Warning")
            self.massageBox.show()
        elif not index:
            self.massageBox.setText("Warning")
            self.massageBox.setInformativeText("Error index")
            self.massageBox.setWindowTitle("Warning")
            self.massageBox.show()
        try:
            if self.dataset_pips:
                data_pips = list(self.dataset_pips.values())[index - 1].T
                write_to_hdf5_file(data_pips, self.name_pen_pips, save_path, time, time)
            if self.dataset_sipm:
                data_sipm = list(self.dataset_sipm.values())[index - 1].T
                write_to_hdf5_file(data_sipm, self.name_pen_sipm, save_path, time, time)
            if self.dataset_h_pips:
                data_h_pips = list(self.dataset_h_pips.values())[index - 1].T
                write_to_hdf5_file(data_h_pips, self.name_pen_h_pips, save_path, time, time)
            if self.dataset_h_sipm:
                data_h_sipm = list(self.dataset_h_sipm.values())[index - 1].T
                write_to_hdf5_file(data_h_sipm, self.name_pen_h_sipm, save_path, time, time)
            if self.dataset_h_counter:
                data_h_counter = list(self.dataset_h_counter.values())[index - 1].T
                write_to_hdf5_file(data_h_counter, self.name_pen_counter, save_path, time, time)
            self.logger.info(f"Файл сохранен: {str(save_path)}")
        except Exception as e:
            self.logger.error(e)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    w: GraphViewerWidget = GraphViewerWidget()
    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    w.show()
    data: list = [1, 34.34, 324.4, 32.4, 89.4, 233.4, 234.4, 2344.4, 234.4]
    w.gp_pips.draw_graph(data, "test", clear=False)  # type: ignore
    data1: list[int] = [1, 34, 45, 435, 234, 234, 2344, 234, 23423, 324, 324234]
    w.gp_sipm.draw_graph(data1, "test", clear=False)  # type: ignore

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
