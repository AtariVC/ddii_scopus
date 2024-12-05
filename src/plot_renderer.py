import pyqtgraph as pg
from qasync import asyncSlot
import asyncio

@asyncSlot
class GraphPen():
    '''Отрисовщик графиков

    Добавляет в layout окно графика и отрисовывет график
    '''
    def __init__(self, layaut) -> None:
        plt_widget = pg.PlotWidget
        layaut.addWidget(plt_widget)
        color: tuple  = (255, 120, 10) # yelow default
        pen = pg.mkPen(color)
        data: list[int|float] = []

    @asyncSlot()
    async def draw_graph(self, 
                        clear: bool = True) -> None:
        '''Обновляет поле графика
        Parameters:
        clear (bool) = True: если False, то перед отрисовкой графика поле графика не очищается
        '''
        if type(data) == type(list):
            x, y = await self.graph_data_processing(data) # type: ignore
        elif type(data) == type(tuple):
            for data_item in data: # type: ignore
                x, y = await self.graph_data_processing(data_item)
        plot_widget.clear()
        pen = pg.mkPen(color)

        if self.data_flow_flag == 1: # раскомментировать
            self.writer_data(color, x, y)
        
        data_line = plot_widget.plot(x, y, pen=pen)
        data_line.setData(x, y)  # обновляем данные графика
        plot_widget.addItem(v_line)
        return y

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
    async def draw_hist(self, max_val: int | float):
        pass