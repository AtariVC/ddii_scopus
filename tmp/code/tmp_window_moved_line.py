import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QSplitter

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("QSplitter с кнопками")
        self.setGeometry(100, 100, 800, 600)

        self.initUI()

    def initUI(self):
        # Создаем QSplitter
        splitter = QSplitter()
        self.setCentralWidget(splitter)

        # Создаем макеты для левого и правого виджетов
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        # Добавляем кнопки в левый макет
        for i in range(1, 4):
            button = QPushButton(f"Кнопка {i}")
            left_layout.addWidget(button)

        # Добавляем кнопки в правый макет
        for i in range(4, 7):
            button = QPushButton(f"Кнопка {i}")
            right_layout.addWidget(button)

        # Создаем виджеты для левого и правого макетов
        left_widget = QWidget()
        right_widget = QWidget()

        # Устанавливаем макеты для виджетов
        left_widget.setLayout(left_layout)
        right_widget.setLayout(right_layout)

        # Добавляем виджеты в QSplitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
