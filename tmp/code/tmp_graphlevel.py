
import sys
from PyQt6 import QtCore
from PyQt6.QtWidgets import QApplication, QMainWindow
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
                                    pen = pg.mkPen(color=(100, 100, 0), width=5, style=QtCore.Qt.PenStyle.DashDotLine))
        self.plot.addItem(self.v_line)

        # Подключение обработчиков событий наведения мыши на графическую сцену
        # self.plot.scene().sigMouseMoved.connect(self.on_mouse_moved)
        # self.plot.scene().sigMouseHover.connect(self.on_mouse_leave)

        # Флаг, указывающий на наличие наведения на линию
        # self.hovering = False

        # Функция для изменения цвета при наведении
    def on_mouse_moved(self, pos):
        print(self.v_line.mouseDragEvent)
        # if self.v_line.mouseShape().contains(pos):
            
        #     if not self.hovering:
        #         self.hovering = True
        #         self.v_line.setPen(color='r')
        # else:
        #     if self.hovering:
        #         self.hovering = False
        #         self.v_line.setPen(color='b')

        # Функция для сброса цвета при уходе курсора
    # def on_mouse_leave(self):
    #     if self.hovering:
    #         self.hovering = False

        # Функция, вызываемая при изменении положения вертикальной линии
        def update_line():
            print("Положение вертикальной линии:", self.v_line.value())
            self.v_line.setPen(color=(200, 100, 0), width=5, style=QtCore.Qt.PenStyle.DashDotLine)

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
