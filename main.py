from PyQt6 import QtWidgets, QtCore
import sys
from engine import Engine
import qtmodern.styles
import os
from qtmodern.windows import ModernWindow


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        # loadUi(os.path.join(os.path.dirname(__file__),  f'ui/MainWindow.ui'), self)
        # self.plot_widget = pg.PlotWidget()
        # self.oscill_layout.addWidget(self.plot_widget)
        # self.plot_widget.setBackground('#F8F8F4')
        # self.pushButton_connect.clicked.connect(self.pushButtonConnect_clicked)
        # self.pushButton_single.clicked.connect(self.pushButton_single_clicked)
        # np.array([1])

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    # light(app)
    w: Engine = Engine()
    # w.show()
    mw: ModernWindow = ModernWindow(w)
    mw.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, False)  # fix flickering on resize window
    mw.show()
    # with open("style\Light.css", "r") as f:#QSS not CSS for pyqt5
    #     stylesheet = f.read()
    #     w.setStyleSheet(stylesheet)
    #     f.close()
    sys.exit(app.exec())