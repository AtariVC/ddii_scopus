import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QCheckBox, QLabel

class CheckBoxApp(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        # Устанавливаем заголовок окна
        self.setWindowTitle('CheckBox Example')

        # Создаем вертикальный слой (layout)
        layout = QVBoxLayout()

        # Создаем QLabel для отображения состояния чекбокса
        self.label = QLabel('CheckBox is unchecked', self)
        layout.addWidget(self.label)

        # Создаем QCheckBox
        self.checkbox = QCheckBox('Check me', self)
        layout.addWidget(self.checkbox)

        # Подключаем сигнал stateChanged к методу onStateChanged
        self.checkbox.stateChanged.connect(self.onStateChanged)

        # Устанавливаем слой для основного окна
        self.setLayout(layout)

    def onStateChanged(self, state):
        if state:  # Qt.Checked
            self.label.setText('CheckBox is checked')
        else:
            self.label.setText('CheckBox is unchecked')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CheckBoxApp()
    ex.show()
    sys.exit(app.exec())
