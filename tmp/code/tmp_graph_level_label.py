import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6 import QtCore
import pyqtgraph as pg

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Создание виджета графика
        self.layout = pg.GraphicsLayoutWidget()
        self.setCentralWidget(self.layout)

        self.plot = self.layout.addPlot()

        # Создание вертикальной линии
        self.v_line = pg.InfiniteLine(pos=3, angle=0, movable=True, 
                                    hoverPen = pg.mkPen(color=(200, 100, 0), 
                                                    width=5, 
                                                    style=QtCore.Qt.PenStyle.DashDotLine), 
                                    pen = pg.mkPen(color=(100, 100, 0), width=5, style=QtCore.Qt.PenStyle.DashDotLine),
                                    label='(3, 5)')  # Инициализация с подписью
        self.plot.addItem(self.v_line)

        # Функция, вызываемая при изменении положения вертикальной линии
        def update_line():
            x_pos = self.v_line.value()  # Текущая позиция вертикальной линии по оси x
            y_pos = self.plot.viewRange()[1][1]  # Текущая верхняя граница графика по оси y
            self.v_line.setLabel(f"({x_pos}, {y_pos})", color=(255, 255, 255))

        def update_line_finished():
            self.v_line.setPen(color=(100, 100, 0), width=5, style=QtCore.Qt.PenStyle.DashDotLine)

        self.v_line.sigPositionChanged.connect(update_line)
        self.v_line.sigPositionChangeFinished.connect(update_line_finished)

        # Отображение графика
        self.plot.plot([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
