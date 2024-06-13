from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QToolBar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Создание тулбара
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        # Создание QAction для кнопки "Старт/Пауза"
        self.start_pause_action = QAction(QIcon("https://www.flaticon.com/ru/free-icons/start"), None, self)
        self.start_pause_action.triggered.connect(self.on_start_pause_button_clicked)

        # Добавление QAction на тулбар
        self.toolbar.addAction(self.start_pause_action)

    def on_start_pause_button_clicked(self):
        # Изменение текста и иконки через QAction
        if self.start_pause_action.text() == "Старт":
            self.start_pause_action.setText("Пауза")
            self.start_pause_action.setIcon(QIcon("https://www.flaticon.com/ru/free-icons/pause"))
        else:
            self.start_pause_action.setText("Старт")
            self.start_pause_action.setIcon(QIcon("https://www.flaticon.com/ru/free-icons/start"))

        # Вставьте сюда код, который должен выполняться при нажатии кнопки

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
