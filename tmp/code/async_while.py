import asyncio
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
from qasync import QEventLoop


class MainHvipDialog(QMainWindow):
    def __init__(self, logger, w_ser_dialog):
        super().__init__()
        self.logger = logger
        self.w_ser_dialog = w_ser_dialog
        self.label = QLabel("Working...", self)
        self.cancel_button = QPushButton("Cancel Task", self)
        self.cancel_button.clicked.connect(self.cancel_task)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.cancel_button)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.task = None  # Сохраняем ссылку на задачу
        self.loop()
        
        
    def loop(self):
        loop.call_soon(self.start_task)

    def start_task(self):
        # Создаем задачу и сохраняем ссылку на неё
        self.task = asyncio.create_task(self.asyncio_loop_request())

    def cancel_task(self):
        # Проверяем, если задача существует и не завершена
        if self.task and not self.task.done():
            self.task.cancel()  # Отменяем задачу
            self.label.setText("Task cancelled")  # Обновляем текст

    async def asyncio_loop_request(self):
        i = 0
        try:
            while True:
                if self.logger:
                    self.logger.info("Running async loop request...")
                self.label.setText(f'Running async task... {i}')
                i += 1
                await asyncio.sleep(2)  # Пауза для бесконечного цикла
        except asyncio.CancelledError:
            self.label.setText("Async task was cancelled")  # Сообщение о завершении задачи

# Инициализация приложения и цикла событий
app = QApplication([])
loop = QEventLoop(app)
asyncio.set_event_loop(loop)

# Создаем объект окна после установки цикла
logger = None  # Замените на ваш объект логирования
w_ser_dialog = None  # Замените на ваш объект диалога
window = MainHvipDialog(logger, w_ser_dialog)

# Откладываем запуск корутины до полного старта цикла событий
app_close_event = asyncio.Event()
app.aboutToQuit.connect(app_close_event.set)
window.show()
# Запуск цикла событий
with loop:
    try:
        loop.run_until_complete(app_close_event.wait())
    except asyncio.CancelledError:
        ...
