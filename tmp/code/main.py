import sys
import os
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

from py_toggle import pyToggle

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.resize(500, 500)

        self.container = QFrame()
        self.container.setObjectName("container")
        self.container.setStyleSheet("# container { background-color: #222;")
        self.layot = QVBoxLayout()

        # ADD WIDGET ON LAYOUT
        self.toggle = pyToggle()

        self.layot.addWidget(self.toggle, Qt.AlignmentFlag.AlignCenter, Qt.AlignmentFlag.AlignCenter)

        self.container.setLayout(self.layot)
        self.setCentralWidget(self.container)
        self.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())



