import pyqtgraph as pg
from PyQt6 import QtWidgets
from qasync import asyncSlot
import asyncio
from src.write_data_to_file import writer_graph_data, write_to_hdf5_file, read_hdf5_file, hdf5_to_csv
from pathlib import Path
import os
import datetime
import sys
import qtmodern
import numpy as np


class GraphPen():
    '''Отрисовщик графиков

    Добавляет в layout окно графика и отрисовывет график
    '''
    def __init__(self,
        layout: QtWidgets.QHBoxLayout | QtWidgets.QVBoxLayout | QtWidgets.QGridLayout,
        name: str = "default_graph",
        color: tuple = (255, 120, 10)) -> None:
        self.plt_widget = pg.PlotWidget()
        layout.addWidget(self.plt_widget)
        self.pen = pg.mkPen(color)
        self.name_frame: str = name
        #### Path ####
        self.parent_path: Path = Path("./log/graph_data").resolve()
        current_datetime = datetime.datetime.now()
        time: str = current_datetime.strftime("%d-%m-%Y_%H-%M-%S-%f")[:23]
        self.path_to_save: Path = self.parent_path / time

    @asyncSlot()
    async def draw_graph(self,
                        data: list[int | float],
                        name_file_save_data: str = "",
                        clear: bool = True) -> None:
        '''Обновляет поле графика
        Parameters:
        clear (bool) = True: если False, то перед отрисовкой графика поле графика не очищается
        '''
        x, y = await self.graph_data_complit(data)
        if clear:
            self.plt_widget.clear()
        if name_file_save_data:
            write_to_hdf5_file([x, y], self.name_frame, self.parent_path, name_file_save_data)
            # hdf5_to_csv(self.parent_path/Path(f"{name_file_save_data}.phd5"))
        data_line = self.plt_widget.plot(x, y, pen=self.pen)
        data_line.setData(x, y)  # обновляем данные графика
        # self.plt_widget.addItem(v_line) # линия уровня
        #
    @asyncSlot()
    async def graph_data_complit(self, data: list[int | float]) -> tuple[list[int|float], list[int|float]]:
        x: list = []
        y: list = []
        for index, value in enumerate(data):
            if value > 4000:
                value = 0
            x.append(index)
            y.append(value)
        return x, y

class HistPen():
    '''Отрисовщик гистограмм
    Добавляет в layout окно графика и отрисовывет гистограмму
    '''
    def __init__(self,
                layaut: QtWidgets.QHBoxLayout|QtWidgets.QVBoxLayout|QtWidgets.QGridLayout,
                name: str,
                color: tuple = (0, 0, 255, 150)) -> None:
        self.hist_widget: pg.PlotWidget  = pg.PlotWidget()
        layaut.addWidget(self.hist_widget)
        self.color = color
        self.pen = pg.mkPen(color)
        self.name_frame_data: str = name
        #### Path ####
        self.parent_path: Path = Path("./log/hist_data").resolve()
        current_datetime = datetime.datetime.now()
        time: str = current_datetime.strftime("%d-%m-%Y_%H-%M-%S-%f")[:23]
        self.path_to_save: str = str(self.parent_path / time)

    def draw_graph(self, data: list[int | float]) -> None:
        bin_count = 4096
        self.hist_widget.clear()
        y, x  = np.histogram(data, bins=np.linspace(0, bin_count, bin_count))
        self.hist_widget.plot(x, y, stepMode=True, fillLevel=0, brush=self.color)

    @asyncSlot()
    async def draw_hist(self, max_val: int | float) -> None:
        pass


