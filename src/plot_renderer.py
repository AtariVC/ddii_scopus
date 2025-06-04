import asyncio
import datetime
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
import pyqtgraph as pg
import qasync
import qtmodern
from PyQt6 import QtCore, QtWidgets
from qasync import asyncSlot

from src.write_data_to_file import hdf5_to_csv, read_hdf5_file, write_to_hdf5_file, writer_graph_data

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent.parent

# from src.signal_manager import SignalManager  # noqa: E402

sys.path.append(str(src_path))

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
        self.plot_item = None # для PlotDataItem
        #### Path ####
        self.parent_path: Path = Path("./log/graph_data").resolve()
        current_datetime = datetime.datetime.now()
        time: str = current_datetime.strftime("%d-%m-%Y_%H-%M-%S-%f")[:23]
        self.path_to_save: Path = self.parent_path / time

    @qasync.asyncSlot()
    async def draw_graph(self, data, save_log=False, name_file_save_data=None, clear=False) -> bool:
        """Обновляет поле графика с защитой от отмены"""
        try:
            x, y = await self._prepare_graph_data(data)
            if clear:
                self.plt_widget.clear()
                self.plot_item = None
            if save_log and name_file_save_data:
                self._save_graph_data(x, y, name_file_save_data)
            if self.plot_item == None:
                self.plot_item = pg.PlotDataItem(x, y, pen = self.pen)
                self.plt_widget.addItem(self.plot_item)
            else:
                self.plot_item.setData(self.plot_item)
            # self.plt_widget.plot(x, y, pen=self.pen)
            return True
        except Exception as e:
            print(f"Ошибка отрисовки: {e}")
            return False

    async def _prepare_graph_data(self, data):
        """Подготовка данных для графика"""
        x, y = [], []
        for index, value in enumerate(data):
            x.append(index)
            # y.append(0 if value > 4000 else value)
            y.append(value)
        return x, y
    
    def _save_graph_data(self, x, y, filename):
        """Сохранение данных графика"""
        write_to_hdf5_file([x, y], self.name_frame, self.parent_path, filename)

class HistPen():
    '''Отрисовщик гистограмм
    Добавляет в layout окно графика и отрисовывет гистограмму
    '''
    def __init__(self,
                layout: QtWidgets.QHBoxLayout|QtWidgets.QVBoxLayout|QtWidgets.QGridLayout,
                name: str,
                color: tuple = (0, 0, 255, 150)) -> None:
        self.hist_widget: pg.PlotWidget  = pg.PlotWidget()
        layout.addWidget(self.hist_widget)
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


