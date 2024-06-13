import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QComboBox, QVBoxLayout, QWidget

class CustomComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        # Обработка события первоначального нажатия мыши, когда выпадающий список отображается
        print("Событие первоначального нажатия, когда выпадающий список отображается")

        # Вызов реализации базового класса
        super().mousePressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Пример ComboBox")
        self.setGeometry(100, 100, 400, 300)

        self.initUI()

    def initUI(self):
        # Создание настраиваемого комбобокса
        self.comboBox = CustomComboBox()
        self.comboBox.addItems(["Элемент 1", "Элемент 2", "Элемент 3"])

        # Создание компоновки
        layout = QVBoxLayout()
        layout.addWidget(self.comboBox)

        # Создание центрального виджета
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
