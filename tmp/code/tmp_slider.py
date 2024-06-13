import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QSlider, QLineEdit
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Пример синхронизации QSlider и QLineEdit")
        self.setGeometry(100, 100, 400, 200)

        layout = QVBoxLayout()

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setTickInterval(10)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.valueChanged.connect(self.slider_value_changed)

        self.line_edit = QLineEdit()
        self.line_edit.textChanged.connect(self.line_edit_text_changed)

        layout.addWidget(self.slider)
        layout.addWidget(self.line_edit)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def slider_value_changed(self, value):
        self.line_edit.setText(str(value))

    def line_edit_text_changed(self, text):
        try:
            value = int(text)
            if 0 <= value <= 100:
                self.slider.setValue(value)
        except ValueError:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
