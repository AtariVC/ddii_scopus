import sys
import asyncio
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget
from qasync import QEventLoop, asyncSlot

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Async Example with PyQt6")

        # Создаем элементы интерфейса
        self.status_label = QLabel("Нажмите кнопку, чтобы начать корутину.")
        self.button = QPushButton("Запустить корутину")
        self.button.clicked.connect(self.on_button_click)

        # Настройка макета
        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    @asyncSlot()  # Используем декоратор asyncSlot для асинхронного слота
    async def on_button_click(self):
        self.status_label.setText("Корутину запущено...")
        
        # Запускаем корутину и отслеживаем ее завершение
        task = asyncio.create_task(self.example_coroutine())

        # Обновляем интерфейс до завершения корутины
        while not task.done():
            self.status_label.setText("Корутину выполняется...")
            await asyncio.sleep(0.2)

        # После завершения корутины обновляем интерфейс
        self.status_label.setText("Корутину завершена!")

    async def example_coroutine(self):
        await asyncio.sleep(2)  # Симуляция длительной операции
        print("Корутину завершена!")

app = QApplication(sys.argv)
loop = QEventLoop(app)
asyncio.set_event_loop(loop)

window = MainWindow()
window.show()

with loop:
    loop.run_forever()

