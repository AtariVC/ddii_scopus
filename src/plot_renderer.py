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
        # Threshold for selective saving (None disables filtering)
        self._save_threshold: int | None = None
        # Window size for spike detection (neighbors on each side)
        self._spike_window: int = 1

        # if __name__ != "__main__":
        #     self.logger = args[0]
        # else:
        #     self.logger = PrintLogger()
        

    @qasync.asyncSlot()
    async def draw_graph(self, data: list, name_file_save_data: Optional[str] = None, name_data: Optional[str] = None, path_to_save: Optional[Path] = None, save_log=False, clear=False, filter: Optional[Callable] = None):
        try:
            if any(isinstance(item, float) for item in data):
                data = list(map(int, data))
                # print(f"Данные преобразованы в int")
            x, y = await self._prepare_graph_data(data)
            y = self._filter_implement(y, filter)
            if clear: # очищать ли график. Если нет, то новые точки просто добавляются на график
                self.plt_widget.clear()
                self.plot_item = pg.PlotDataItem(x, y, pen = self.pen)
                self.plt_widget.addItem(self.plot_item)
            else:
                # обновляем существующие данные
                self.plot_item.setData(x, y)
            if save_log:
                if path_to_save and name_file_save_data and name_data:
                    # Apply threshold filter for saving if configured
                    # if self._save_threshold is not None:
                    #     xf = []
                    #     yf = []
                    #     for xi, yi in zip(x, y):
                    #         if yi is not None and yi > self._save_threshold:
                    #             xf.append(xi)
                    #             yf.append(yi)
                    #     # Skip saving if nothing passes the threshold
                    #     if len(yf) == 0:
                    #         return x, y
                        # write_to_hdf5_file([xf, yf], self.name_frame, path_to_save,
                        #                    name_file_hdf5=name_file_save_data,
                        #                    name_data=name_data)
                    # else:
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
        """Подготовка данных для графика
        Входные элементы содержат дополнительный код в старших битах; выделяем 12‑битную амплитуду.
        """
        x, y = [], []
        for index, value in enumerate(data):
            x.append(index)
            try:
                amp = int(value) & 0x0FFF
            except Exception:
                amp = 0
            y.append(amp)
        # Дополнительная обработка: сглаживание случайных выбросов
        try:
            y = self._fix_spikes(y, window=self._spike_window)
        except Exception:
            ...
        return x, y

    def _fix_spikes(self, y: list[int], window: int = 5) -> list[int]:
        """Ищет и исправляет случайные выбросы, интерполируя по соседям.
        Принцип:
        - Для каждой точки i берется локальный разброс соседей в окне window:
          d = |median(left_window) - median(right_window)|.
        - Точка считается выбросом, если она значительно отклоняется от среднего соседей:
            |y[i] - (median(left_window)+median(right_window))/2| > max(20, 3*d + 10)
        - Последовательности подряд идущих выбросов интерполируются линейно между опорными точками
          (значения до и после последовательности).

        Пример: [2, 3, 250, 254, 6, 6] -> [2, 3, 4, 5, 6, 6]
        """
        n = len(y)
        if n < 3:
            return y
        window = max(1, int(window))
        y_out = y.copy()
        spike = [False] * n
        for i in range(1, n - 1):
            # Немедленно помечаем как выброс всё, что выше 3000
            mid = y[i]
            if mid > 3000:
                spike[i] = True
                continue
            # Окна слева и справа от точки (исключая саму точку)
            l0 = max(0, i - window)
            r0 = min(n, i + 1 + window)
            left_win = y[l0:i]
            right_win = y[i + 1 : r0]
            if not left_win or not right_win:
                # fallback к соседям, если окно пустое (на границах)
                left_stat = y[i - 1]
                right_stat = y[i + 1]
            else:
                left_stat = float(np.median(left_win))
                right_stat = float(np.median(right_win))
            d = abs(left_stat - right_stat)
            center = (left_stat + right_stat) / 2.0
            # адаптивный порог: чем ближе соседи, тем жёстче критерий
            thresh = max(20, 3 * d + 10)
            if abs(mid - center) > thresh:
                spike[i] = True
        i = 1
        while i < n - 1:
            if spike[i]:
                s = i
                e = i
                while e + 1 < n - 1 and spike[e + 1]:
                    e += 1
                # Интерполируем только если есть обе опорные точки
                if s - 1 >= 0 and e + 1 < n:
                    L = e - s + 1
                    A = y_out[s - 1]
                    B = y_out[e + 1]
                    step = (B - A) / float(L + 1)
                    for k in range(L):
                        y_out[s + k] = int(round(A + (k + 1) * step))
                i = e + 1
            else:
                i += 1
        return y_out

    def set_spike_window(self, window: int) -> None:
        """Установить окно обнаружения выбросов (число соседей с каждой стороны)."""
        try:
            w = int(window)
            self._spike_window = max(1, w)
        except Exception:
            self._spike_window = 1
    

    def _filter_implement(self, data: list[int], filter: Optional[Callable] = None) -> list[int]:
        if filter is not None:
            try:
                data_out = filter(data)
            except Exception as e:
                self.logger.error(f"Ошибка применении фильтра в _filter_implement: {e}")
        else:
            data_out = data
        return data_out

    def set_save_threshold(self, value: int | None):
        """Set amplitude threshold for selective saving.
        None disables threshold filtering.
        """
        try:
            self._save_threshold = None if value is None else int(value)
        except Exception:
            self._save_threshold = None

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
        # Threshold for selective saving (applies to raw values before binning when possible)
        self._save_threshold: int | None = None

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
            data_tohist = [max(data)]
            if isinstance(self.accum_data, list):
                self.accum_data.extend(data_tohist)
            bins = np.linspace(0, float(bin_count), int(bin_count) + 1)
            # Build histogram for display using all accumulated values
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
                # Apply threshold filtering for saving
                if not data_is_hist:
                    # Filter accumulated raw values by threshold and compute histogram for saving
                    acc = np.asarray(self.accum_data)
                    # acc = acc[acc > self._save_threshold]
                    # if acc.size == 0:
                    #     return
                    y_save, x_save = np.histogram(acc, bins)
                    write_to_hdf5_file([x_save[:-1], y_save], self.name_frame, self.path_to_save,
                                       name_file_hdf5=name_file_save_data,
                                       name_data=name_data)
                elif data_is_hist and self._save_threshold is not None:
                    # Threshold applies to bin counts in this mode; skip bins <= threshold
                    xi = np.asarray(x[:-1])
                    yi = np.asarray(y)
                    mask = yi > self._save_threshold
                    if not mask.any():
                        return
                    write_to_hdf5_file([xi[mask], yi[mask]], self.name_frame, self.path_to_save,
                                       name_file_hdf5=name_file_save_data,
                                       name_data=name_data)
                else:
                    write_to_hdf5_file([x[:-1], y], self.name_frame, self.path_to_save, 
                                name_file_hdf5=name_file_save_data, 
                                name_data=name_data)
            elif path_to_save == None:
                raise ValueError("Не передана переменная в draw_hist: path_to_save == None")
            elif name_file_save_data == None:
                raise ValueError("Не передана переменная в draw_hist: name_file_save_data ==  None")
            elif name_data == None:
                raise ValueError("Не передана переменная в draw_hist: name_data == None")

    def set_save_threshold(self, value: int | None):
        """Set amplitude threshold for selective saving.
        None disables threshold filtering.
        """
        try:
            self._save_threshold = None if value is None else int(value)
        except Exception:
            self._save_threshold = None
