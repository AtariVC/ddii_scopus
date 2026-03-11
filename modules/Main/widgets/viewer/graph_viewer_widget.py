import asyncio
import re
import sys
from dataclasses import dataclass

# from save_config import ConfigSaver
from pathlib import Path

import qasync
import qtmodern.styles
from PyQt6 import QtCore, QtWidgets
from qtpy.uic import loadUi

from modules.Main.widgets.viewer.explorer_hdf5_widget import ExplorerHDF5Widget
from src.log_config import get_logger, log_init

####### импорты из других директорий ######
# /src

src_path = Path(__file__).resolve().parents[4]
# modules_path = Path(__file__).resolve().parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
# sys.path.append(str(modules_path))

# from src.modbus_worker import ModbusWorker                          # noqa: E402
# from src.ddii_command import ModbusCMCommand, ModbusMPPCommand      # noqa: E402
# from src.parsers import  Parsers                                    # noqa: E402
# from modules.Main_Serial.main_serial_dialog_tcp import SerialConnect    # noqa: E402
# from src.log_config import log_init, log_s                          # noqa: E402
# from src.parsers_pack import LineEObj, LineEditPack                 # noqa: E402
from src.event.event import Event  # noqa: E402
from src.plot_renderer import GraphPen, HistPen  # noqa: E402
from src.write_data_to_file import read_hdf5_file, write_to_hdf5_file  # noqa: E402


class GraphViewerWidget(QtWidgets.QWidget):
    verticalLayout_graph: QtWidgets.QVBoxLayout
    vLayout_hist_EdE: QtWidgets.QVBoxLayout
    vLayout_hist_pips: QtWidgets.QVBoxLayout
    vLayout_hist_sipm: QtWidgets.QVBoxLayout
    vLayout_hist_counter: QtWidgets.QVBoxLayout
    vLayout_pips: QtWidgets.QVBoxLayout
    vLayout_sipm: QtWidgets.QVBoxLayout
    label_counter_data: QtWidgets.QLabel
    label_time_data: QtWidgets.QLabel
    horizontalSlider_time_scale: QtWidgets.QSlider

    slider_update_event: Event

    def __init__(self, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath("graph_viewer_widget.ui"), self)
        self.pen_init()
        self.massageBox = QtWidgets.QMessageBox()
        self.massageBox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        self.logger = log_init()
        self.slider_update_event = Event(int)
        self.parent_hdf5_path = ""
        if __name__ != "__main__":
            self.parent = args[0]
            self.explorer: ExplorerHDF5Widget = self.parent.explorer_hdf5_widget  # type: ignore
            self.explorer.double_clicked_event.subscribe(self.open_graphs)
            self.horizontalSlider_time_scale.actionTriggered.connect(lambda: self.slider_graphs_updater())
        # External filter widget will control filtering/navigation

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
        self.gp_pips = GraphPen(layout=self.vLayout_pips, name=self.name_pen_pips, color=(255, 255, 0))
        self.gp_sipm = GraphPen(layout=self.vLayout_sipm, name=self.name_pen_sipm, color=(0, 255, 255))
        self.hp_pips = HistPen(layout=self.vLayout_hist_pips, name=self.name_pen_h_pips, color=(255, 0, 0, 150))
        self.hp_sipm = HistPen(layout=self.vLayout_hist_sipm, name=self.name_pen_h_sipm, color=(0, 0, 255, 150))
        self.counter_h = HistPen(
            layout=self.vLayout_hist_counter, name=self.name_pen_counter, color=(123, 195, 121, 150)
        )
        # Filtering state managed by external widget

    def open_graphs(self, path: str) -> None:
        """Открывает графики из файла"""
        self.parent_hdf5_path = path
        self.horizontalSlider_time_scale.setValue(0)
        self.dataset_pips = read_hdf5_file(Path(path), self.name_pen_pips)
        self.dataset_sipm = read_hdf5_file(Path(path), self.name_pen_sipm)
        self.dataset_h_pips = read_hdf5_file(Path(path), self.name_pen_h_pips)
        self.dataset_h_sipm = read_hdf5_file(Path(path), self.name_pen_h_sipm)
        self.dataset_h_counter = read_hdf5_file(Path(path), self.name_pen_counter)
        self.amount_measurements = len(self.dataset_h_pips)
        if self.amount_measurements:
            self.measure_time_list = list(self.dataset_h_pips.keys())
            time_str = self.time_formater(self.measure_time_list[0])
            self.label_time_data.setText(f"{time_str}")
            self.horizontalSlider_time_scale.setMaximum(self.amount_measurements)
            self.label_counter_data.setText(f"{self.horizontalSlider_time_scale.value()}/{self.amount_measurements}")
            self.horizontalSlider_time_scale.setValue(1)
        else:
            self.label_time_data.setText(f"Нет данных")
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
            current_val = self.horizontalSlider_time_scale.value()
            self.slider_update_event.emit(current_val)
            self.label_counter_data.setText(f"{current_val}/{self.amount_measurements}")
            time_str = self.time_formater(self.measure_time_list[current_val - 1])
            self.label_time_data.setText(f"{time_str}")
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
            ok_pips = False
            ok_sipm = False
            if use_pips and self.dataset_pips:
                try:
                    arr = list(self.dataset_pips.values())[i - 1].T[1]
                    if max(arr) > pips_thr:
                        ok_pips = True
                except Exception:
                    ...
            if use_sipm and self.dataset_sipm:
                try:
                    arr = list(self.dataset_sipm.values())[i - 1].T[1]
                    if max(arr) > sipm_thr:
                        ok_sipm = True
                except Exception:
                    ...
            if ok_pips and ok_sipm:
                matched_idx.append(i)
            if not matched_idx:
                self.massageBox.setText("Warning")
                self.massageBox.setInformativeText("No data found")
                self.massageBox.setWindowTitle("Warning")
                self.massageBox.show()
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
                self.horizontalSlider_time_scale.setValue(idx)
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
