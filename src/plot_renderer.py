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
from typing import Optional, Sequence

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
    async def draw_graph(self, data, save_log=False, name_file_save_data=None, clear=True):
        """Обновляет поле графика с защитой от отмены"""
        try:
            x, y = await self._prepare_graph_data(data)
            if clear:
                self.plt_widget.clear()
            
            if save_log and name_file_save_data:
                self._save_graph_data(x, y, name_file_save_data)

            self.plt_widget.plot(x, y, pen=self.pen)
            
        except asyncio.CancelledError:
            # Чистый выход без проброса исключения
            return None
        except Exception as e:
            print(f"Ошибка отрисовки: {e}")
            raise

    async def _prepare_graph_data(self, data):
        """Подготовка данных для графика"""
        x, y = [], []
        for index, value in enumerate(data):
            x.append(index)
            y.append(0 if value > 4000 else value)
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


