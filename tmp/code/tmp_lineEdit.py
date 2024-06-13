import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel

class MyWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle('LineEdit Text Changed Example')

        # Создаем вертикальный макет
        layout = QVBoxLayout()

        # Создаем виджет LineEdit
        self.line_edit = QLineEdit(self)
        self.line_edit.setPlaceholderText('Type something here...')

        # Подключаем сигнал textChanged к слоту on_text_changed
        self.line_edit.textChanged.connect(self.on_text_changed)

        # Создаем метку для отображения текста
        self.label = QLabel('', self)

        # Добавляем LineEdit и метку в макет
        layout.addWidget(self.line_edit)
        layout.addWidget(self.label)

        # Устанавливаем макет для виджета
        self.setLayout(layout)

    def on_text_changed(self, text):
        # Обновляем текст метки в зависимости от текста в LineEdit
        self.label.setText(text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec())

