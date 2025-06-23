from PyQt6 import QtWidgets, QtCore
from qtpy.uic import loadUi
import asyncio
import qtmodern.styles
import sys
import qasync
# from save_config import ConfigSaver
from pathlib import Path
from dataclasses import dataclass
import re

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
# from modules.Main_Serial.main_serial_dialog import SerialConnect    # noqa: E402
# from src.log_config import log_init, log_s                          # noqa: E402
# from src.parsers_pack import LineEObj, LineEditPack                 # noqa: E402
from src.plot_renderer import GraphPen, HistPen                       # noqa: E402
from src.event.event import Event                                     # noqa: E402
from src.write_data_to_file import read_hdf5_file                                     # noqa: E402





class GraphViewerWidget(QtWidgets.QWidget):
    vLayout_hist_EdE                : QtWidgets.QVBoxLayout
    vLayout_hist_pips               : QtWidgets.QVBoxLayout
    vLayout_hist_sipm               : QtWidgets.QVBoxLayout
    vLayout_hist_counter            : QtWidgets.QVBoxLayout
    vLayout_pips                    : QtWidgets.QVBoxLayout
    vLayout_sipm                    : QtWidgets.QVBoxLayout
    label_counter_data              : QtWidgets.QLabel
    label_time_data                 : QtWidgets.QLabel
    horizontalSlider_time_scale     : QtWidgets.QSlider

    def __init__(self, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath('graph_viewer_widget.ui'), self)
        self.pen_init()
        if __name__ != "__main__":
            self.parent = args[0]
            self.parent.explorer_hdf5_widget.double_clicked_event.subscribe(self.open_graphs)
            self.horizontalSlider_time_scale.actionTriggered.connect(lambda: self.slider_graphs_updater())

    def pen_init(self) -> None:
        self.task = None # type: ignore
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
        self.gp_pips = GraphPen(layout = self.vLayout_pips, name = self.name_pen_pips, color = (255, 255, 0))
        self.gp_sipm = GraphPen(layout = self.vLayout_sipm, name = self.name_pen_sipm, color = (0, 255, 255))
        self.hp_pips = HistPen(layout = self.vLayout_hist_pips, name = self.name_pen_h_pips, color = (255, 0, 0, 150))
        self.hp_sipm = HistPen(layout = self.vLayout_hist_sipm, name = self.name_pen_h_sipm, color = (0, 0, 255, 150))
        self.counter_h = HistPen(layout = self.vLayout_hist_counter, name = self.name_pen_counter, color = (123, 195, 121, 150))



    def open_graphs(self, path: str) -> None:
        """Открывает графики из файла"""
        self.horizontalSlider_time_scale.setValue(0)
        self.dataset_pips = read_hdf5_file(Path(path), self.name_pen_pips)
        self.dataset_sipm = read_hdf5_file(Path(path), self.name_pen_sipm)
        self.dataset_h_pips = read_hdf5_file(Path(path), self.name_pen_h_pips)
        self.dataset_h_sipm = read_hdf5_file(Path(path), self.name_pen_h_sipm)
        self.amount_measurements = len(self.dataset_pips)
        self.measure_time_list = list(self.dataset_pips.keys())
        time_str = self.time_formater(self.measure_time_list[0])
        self.label_time_data.setText(f"{time_str}")
        self.horizontalSlider_time_scale.setMaximum(self.amount_measurements)
        self.label_counter_data.setText(f"{self.horizontalSlider_time_scale.value()}/{self.amount_measurements}")
    
    def time_formater(self, input_time_str: str) -> str:
        """Преобразует строку вида "2024-10-08_17-52-54-261" в формат "Время: 08.10.24 17:52:54:2610"
        Args:
            input_time_str (str): Строка времени в формате "2024-10-08_17-52-54-261"
        Returns:
            str: Преобразованная строка времени в формате "Время: 08.10.24 17
        """
        # Извлекаем компоненты даты и времени
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})-(\d{3})',       input_time_str)
        if match:
            year, month, day, hour, minute, second, millis = match.groups()
            output_str = f"Время: {day}.{month}.{year[-2:]} {hour}:{minute}:{second}:{millis}0"
            return output_str
        else:
            return "Время: неверный формат"

    @qasync.asyncSlot()
    async def slider_graphs_updater(self) -> None:
        """Обновляет графики при изменении слайдера"""

        if self.amount_measurements == 0:
            return
        current_val = self.horizontalSlider_time_scale.value()-1
        self.label_counter_data.setText(f"{current_val}/{self.amount_measurements}")
        time_str = self.time_formater(self.measure_time_list[current_val-1])
        self.label_time_data.setText(f"{time_str}")

        data_pips = list(self.dataset_pips.values())[current_val].T
        data_sipm = list(self.dataset_sipm.values())[current_val].T
        data_h_pips = list(self.dataset_h_pips.values())[current_val].T
        data_h_sipm = list(self.dataset_h_sipm.values())[current_val].T

        await self.gp_pips.draw_graph(data_pips[1], clear=True)
        await self.gp_sipm.draw_graph(data_sipm[1], clear=True)
        # await self.hp_pips.draw_hist(data_pips[1], clear=True)
        # await self.hp_sipm.draw_hist(data_sipm[1], clear=True)
        await self.hp_pips._draw_graph(data_h_pips[0], clear=True)
        await self.hp_sipm._draw_graph(data_h_sipm[0], clear=True)

        # if value < self.amount_measurements:

            # data_pips = self.gp_pips.get_data(value)
            # data_sipm = self.gp_sipm.get_data(value)
            # self.gp_pips.draw_graph(data_pips, "pips", clear=True)
            # self.gp_sipm.draw_graph(data_sipm, "sipm", clear=True)
            # self.hp_pips.draw_histogram(data_pips, "h_pips", clear=True)
            # self.hp_sipm.draw_histogram(data_sipm, "h_sipm", clear=True)

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
    w.gp_pips.draw_graph(data, "test", clear=False) # type: ignore
    data1: list[int] = [1, 34, 45, 435, 234, 234, 2344 ,234, 23423, 324, 324234]
    w.gp_sipm.draw_graph(data1, "test", clear=False) # type: ignore

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...