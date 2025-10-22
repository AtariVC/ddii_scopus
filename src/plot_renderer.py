import asyncio
import datetime
import os
import sys
from pathlib import Path
from typing import Optional, Sequence, Callable, Union

import numpy as np
import pyqtgraph as pg
import qasync
import qtmodern
from PyQt6 import QtCore, QtWidgets
from src.log_config import get_logger
import operator

from src.write_data_to_file import write_to_hdf5_file

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent.parent

# from src.signal_manager import SignalManager  # noqa: E402

sys.path.append(str(src_path))

from src.print_logger import PrintLogger  # noqa: E402

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
        self.plot_item: pg.PlotDataItem # для PlotDataItem
        self.logger = get_logger(__name__)

        # if __name__ != "__main__":
        #     self.logger = args[0]
        # else:
        #     self.logger = PrintLogger()
        

    @qasync.asyncSlot()
    async def draw_graph(self, data: list, name_file_save_data: Optional[str] = None, name_data: Optional[str] = None, path_to_save: Optional[Path] = None, save_log=False, clear=False):
        try:
            if any(isinstance(item, float) for item in data):
                data = list(map(int, data))
                # print(f"Данные преобразованы в int")
            x, y = await self._prepare_graph_data(data)
            if clear: # очищать ли график. Если нет, то новые точки просто добавляются на график
                self.plt_widget.clear()
                self.plot_item = pg.PlotDataItem(x, y, pen = self.pen)
                self.plt_widget.addItem(self.plot_item)
            else:
                self.plot_item.setData(self.plot_item)
            if save_log:
                if path_to_save and name_file_save_data and name_data:
                    write_to_hdf5_file([x, y], self.name_frame, path_to_save, 
                                name_file_hdf5=name_file_save_data, 
                                name_data=name_data)
                elif path_to_save == None:
                    raise ValueError("Не передана переменная в draw_graph: path_to_save == None")
                elif name_file_save_data == None:
                    raise ValueError("Не передана переменная в draw_graph:  name_file_save_data ==  None")
                elif name_data == None:
                    raise ValueError("Не передана переменная в draw_graph: name_data == None")
            return x, y
        except Exception as e:
            self.logger.error(f"Ошибка отрисовки: {e}")
            return [],[]

    async def _prepare_graph_data(self, data):
        """Подготовка данных для графика"""
        x, y = [], []
        for index, value in enumerate(data):
            x.append(index)
            y.append(0 if value&0xFFF > 4000 else value&0xFFF)
            # self.delete_big_bytes(value)
            # y.append(value)
        return x, y

class HistPen():
    def __init__(self, *args,
                layout: QtWidgets.QHBoxLayout|QtWidgets.QVBoxLayout|QtWidgets.QGridLayout,
                name: str,
                color: tuple = (0, 0, 255, 150)) -> None:
        self.logger = get_logger(__name__)
        self.hist_widget: pg.PlotWidget = pg.PlotWidget()
        layout.addWidget(self.hist_widget)
        self.color = color
        self.pen = pg.mkPen(color)
        # белый контур
        self.outline_pen = pg.mkPen((255, 255, 255), width=2)
        self.name_frame: str = name
        self.hist_item = None
        self.hist_outline_item = None  # для белого контура
        
        # Настройки гистограммы
        self.accum_data: list|np.ndarray = []
        ###
        # self.bin_count = 100  # начальное количество бинов
        self.padding_factor = 0.1  # отступ по краям (10% от диапазона данных)
        # if __name__ != "__main__":
        #     self.logger = args[0]
        # else:
        #     self.logger = PrintLogger()

        #### Path ####
        # self.parent_path: Path = Path("./log/graph_data").resolve()
        # current_datetime = datetime.datetime.now()
        # time: str = current_datetime.strftime("%d-%m-%Y_%H")[:23]
        # self.path_to_save: Path = self.parent_path / time

    def hist_clear(self):
        if isinstance(self.accum_data, list):
            self.accum_data.clear()
        else:
            self.accum_data = np.zeros(len(self.accum_data))
        self.hist_widget.clear()
        self.hist_item = None
        self.hist_outline_item = None

    def _calculate_bins(self, data):
        """Вычисляет оптимальные бины и диапазон для данных"""
        if not data or len(data) < 2:
            return np.linspace(0, 1, 10), (0, 1)  # значения по умолчанию

        min_val = min(data)
        max_val = max(data)

        # Добавляем отступ по краям (10% от диапазона данных)
        padding = (max_val - min_val) * self.padding_factor
        if padding == 0:  # если все значения одинаковые
            padding = 1

        x_min = min_val - padding
        x_max = max_val + padding

        # Правило Фридмана-Диакониса для определения количества бинов
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        if iqr > 0:  # защита от деления на ноль
            bin_width = 2 * iqr / (len(data) ** (1/3))
            self.bin_count = max(5, min(100, int((x_max - x_min) / bin_width)))
        else:
            # Если IQR = 0, используем правило Стёрджеса
            self.bin_count = min(50, max(5, int(1 + 3.322 * np.log10(len(data)))))

        bins = np.linspace(x_min, x_max, self.bin_count)
        return bins, (x_min, x_max)

    @qasync.asyncSlot()
    async def draw_hist(self, data: Sequence[Union[int, float]], 
                    save_log: Optional[bool] = False,
                    name_file_save_data: Optional[str] = None,
                    name_data: Optional[str] = None,
                    path_to_save: Optional[Path] = None,
                    filter: Optional[Callable] = None,
                    clear: Optional[bool] = False,
                    data_is_hist: Optional[bool] = False,
                    bin_count: int = 4096) -> None:
        """
        Отрисовывает гистограмму данных с возможностью фильтрации и сохранения
        Args:
            data: Список числовых значений для построения гистограммы
            save_log: Флаг сохранения данных
            name_file_save_data: Имя файла для сохранения данных (None если не нужно сохранять)
            name_data: Название данных (None если не нужно сохранять)
            filter: Функция фильтрации данных (если None, используется максимум)
            clear: Нужно ли очищать старый график перед отрисовкой нового
            calculate_hist: Если данные не являются уже готовой гистограммой, то преобразует их в гистограмму
            name_file_save_data: Имя файла для сохранения
        """
        # parent_path: Path = Path("./log/output_graph_data").resolve()
        # current_datetime = datetime.datetime.now()
        # time: str = current_datetime.strftime("%d-%m-%Y")[:23]
        # path_to_save: Path = parent_path / time
        if clear:
            self.hist_clear()
        if not data:
            raise ValueError("data == [], нет данных для отрисовки")
        # Если данные не являются уже готовой гистограммой

        if not data_is_hist:
            if filter is not None:
                filtered_value = filter(data)
                data_tohist = [filtered_value] if filtered_value is not None else []
                if data_tohist == []:
                    filter_name = getattr(filter, "__name__", str(filter))
                    self.logger.error(f"Не получилось применить фильтр: {filter_name}")
                    raise ValueError("data_tohist == [], нет данных для отрисовки гистограммы")
            else:
                data_tohist = [max(data)]
                if isinstance(self.accum_data, list):
                    self.accum_data.extend(data_tohist)
                bins = np.linspace(0, float(bin_count), int(bin_count) + 1)
                y, x = np.histogram(self.accum_data, bins)
        else:
            bin_count = len(data)
            bins = np.linspace(0, float(bin_count), int(bin_count) + 1)
            y, x = data, bins           
                # Фильтрация выбросов и установка разумного диапазона X
        # Recompute histogram with correct bins based on bin_count
        if bin_count is None or bin_count < 1:
            self.logger.error(f"bin_count is None or bin_count < 1")
            raise ValueError("bin_count is None or bin_count < 1")
        try:
            # обновляем контур
            if self.hist_outline_item is None:
                self.hist_outline_item = pg.PlotDataItem(x, y, pen=self.outline_pen, stepMode=True, fillLevel=0)
                self.hist_widget.addItem(self.hist_outline_item)
            else:
                self.hist_outline_item.setData(x, y)
            # обновляем основную гистограмму
            if self.hist_item is None:
                self.hist_item = pg.PlotDataItem(x, y, pen=self.pen, stepMode=True, brush=self.color, fillLevel=0)
                self.hist_widget.addItem(self.hist_item)
            else:
                self.hist_item.setData(x, y)
        except Exception as er:
            self.logger.error(str(er))
        if save_log:
            if path_to_save and name_file_save_data and name_data:
                self.path_to_save: Path = path_to_save
                write_to_hdf5_file([x[:-1], y], self.name_frame, self.path_to_save, 
                            name_file_hdf5=name_file_save_data, 
                            name_data=name_data)
            elif path_to_save == None:
                raise ValueError("Не передана переменная в draw_hist: path_to_save == None")
            elif name_file_save_data == None:
                raise ValueError("Не передана переменная в draw_hist: name_file_save_data ==  None")
            elif name_data == None:
                raise ValueError("Не передана переменная в draw_hist: name_data == None")



