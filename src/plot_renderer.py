import pyqtgraph as pg
from PyQt6 import QtWidgets
from qasync import asyncSlot
import asyncio
import qasync
from src.write_data_to_file import writer_graph_data
from pathlib import Path
import os
import datetime
import sys
import qtmodern


@asyncSlot
class GraphPen(QtWidgets.QDialog):
    '''Отрисовщик графиков

    Добавляет в layout окно графика и отрисовывет график
    '''
    def __init__(self,
                layout: QtWidgets.QHBoxLayout|QtWidgets.QVBoxLayout|QtWidgets.QGridLayout,
                name: str = "default_graph") -> None:
        self.plt_widget = pg.PlotWidget()
        layout.addWidget(self.plt_widget)
        color: tuple  = (255, 120, 10) # yelow default
        self.pen = pg.mkPen(color)
        self.data: list[int|float] = []
        self.name_frame_data: str = name
        self.parent_path: Path = Path("/ddii_scopus/log/graph_data").resolve()
        if not self.parent_path.exists():
            os.makedirs(str(self.parent_path), exist_ok=True)
        current_datetime = datetime.datetime.now()
        time: str = current_datetime.strftime("%d-%m-%Y_%H-%M-%S-%f")[:23]
        self.path_to_save: str = str(self.parent_path) + str(Path("/")) + time
        os.makedirs(self.path_to_save, exist_ok=True)

    @asyncSlot()
    async def draw_graph(self, 
                        clear: bool = True) -> None:
        '''Обновляет поле графика
        Parameters:
        clear (bool) = True: если False, то перед отрисовкой графика поле графика не очищается
        '''
        x, y = await self.graph_data_complit(self.data)
        if clear:
            self.plt_widget.clear()
        writer_graph_data(x, y, self.name_frame_data, self.path_to_save)
        
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
                decimal_value = 0
            x.append(index)
            y.append(decimal_value)
        return x, y

@asyncSlot
class HistPen():
    '''Отрисовщик гистограмм
    Добавляет в layout окно графика и отрисовывет гистограмму
    '''
    def __init__(self, layaut) -> None:
        hist_widget = pg.PlotWidget
        layaut.addWidget(hist_widget)
        color: tuple  = (255, 120, 10) # yelow default
        pen = pg.mkPen(color)
        data: list[int|float] = []



    @asyncSlot()
    async def draw_hist(self, max_val: int | float) -> None:
        pass


