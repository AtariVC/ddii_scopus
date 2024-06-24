import sys
import time
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore

start_time_1 = time.time()
start_time_2 = time.time()

timeout = 0.16  # это в секундах. Измените для настройки частоты срабатывания QTimer
time_list_1 = []
time_list_2 = []

def method_1():
    global start_time_1
    time_list_1.append((timeout - (time.time() - start_time_1)) * 1000)
    start_time_1 = time.time()

def method_2():
    global start_time_2
    time_list_2.append((timeout - (time.time() - start_time_2)) * 1000)
    start_time_2 = time.time()

def update_plot_1():
    plt1.clear()  # Очистка предыдущего графика
    y, x = np.histogram(time_list_1, bins=np.linspace(-15, 15, 40))
    plt1.plot(x, y, stepMode=True, fillLevel=0, brush=(255, 0, 0, 150))  # Красный цвет

def update_plot_2():
    plt2.clear()  # Очистка предыдущего графика
    y, x = np.histogram(time_list_2, bins=np.linspace(-15, 15, 40))
    plt2.plot(x, y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 150))  # Синий цвет

app = QtWidgets.QApplication(sys.argv)

win = pg.GraphicsLayoutWidget()
win.resize(800, 700)
win.setWindowTitle('Two Histograms')

# Создание двух графиков
plt1 = win.addPlot(title="Histogram 1")
win.nextRow()  # Переход на следующую строку
plt2 = win.addPlot(title="Histogram 2")

# Начальная инициализация графиков
update_plot_1()
update_plot_2()

win.show()

# Таймер для обновления данных и графиков
timer = QtCore.QTimer()
timer.timeout.connect(method_1)
timer.timeout.connect(method_2)
timer.timeout.connect(update_plot_1)
timer.timeout.connect(update_plot_2)
timer.start(int(timeout * 1000))

sys.exit(app.exec())