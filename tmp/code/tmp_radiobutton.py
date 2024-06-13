import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QRadioButton, QLabel

class MyWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle('RadioButton Example')

        # Создаем вертикальный макет
        layout = QVBoxLayout()

        # Создаем радиокнопки
        self.radio_button1 = QRadioButton('Option 1', self)
        self.radio_button2 = QRadioButton('Option 2', self)

        # Подключаем сигнал toggled к обработчику
        self.radio_button1.toggled.connect(self.on_radio_button_toggled)
        self.radio_button2.toggled.connect(self.on_radio_button_toggled)

        # Создаем метку для отображения состояния радиокнопок
        self.label = QLabel('Select an option', self)

        # Добавляем радиокнопки и метку в макет
        layout.addWidget(self.radio_button1)
        layout.addWidget(self.radio_button2)
        layout.addWidget(self.label)

        # Устанавливаем макет для виджета
        self.setLayout(layout)

    def on_radio_button_toggled(self):
        if self.radio_button1.isChecked():
            self.label.setText('Option 1 selected')
        elif self.radio_button2.isChecked():
            self.label.setText('Option 2 selected')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec())
