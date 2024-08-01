import sys
import random
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QPushButton, QWidget
from PyQt6.QtGui import QColor, QPainter
from pymodbus.client import ModbusSerialClient as ModbusClient
import logging

# Класс для фоновой задачи - взаимодействие с Modbus через Serial
class ModbusWorker(QThread):
    # Сигнал для обновления интерфейса
    update_signal = pyqtSignal(str)

    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.client = None
        self.running = True

        # Настройка логгирования
        server_log = logging.getLogger("pysnmp.server")
        client_log = logging.getLogger("pysnmp.client")
        protocol_log = logging.getLogger("pysnmp.protocol")
        store_log = logging.getLogger("pysnmp.store")

        server_log.setLevel(logging.DEBUG)
        protocol_log.setLevel(logging.DEBUG)
        client_log.setLevel(logging.DEBUG)
        store_log.setLevel(logging.DEBUG)

    def run(self):
        # Создаем клиента Modbus для работы через Serial порт
        self.client = ModbusClient(
            method="rtu",
            port=self.port,
            baudrate=self.baudrate,
            timeout=1,
            bytesize=8,
            parity="N",
            stopbits=1,
            handle_local_echo=True,
        )
        self.client.connect()

        # Генерация команды 01 03 00 00 00 3E
        address = 0x0000  # Адрес начала чтения
        count = 0x003E    # Количество регистров для чтения
        unit = 0x01       # Unit ID

        while self.running:
            try:
                # Чтение данных с устройства
                self.client.write_registers(address=0x0001, values=1, slave=1)
                result = self.client.read_holding_registers(0x0000, 62, slave=1)
                print(result.encode())
                if result.isError():
                    self.update_signal.emit("Error reading register")
                else:
                    # Если чтение успешно, выводим количество считанных регистров
                    self.update_signal.emit(f'Registers read successfully: {len(result.registers)}')
            except Exception as e:
                self.update_signal.emit(f'Error: {str(e)}')

            self.sleep(2)  # Пауза между запросами

        # Закрываем соединение с Modbus
        self.client.close()

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

# Класс для фоновой задачи - изменение цвета квадрата
class ColorWorker(QThread):
    color_signal = pyqtSignal(QColor)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        while self.running:
            random_color = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            self.color_signal.emit(random_color)
            self.sleep(1)  # Интервал между изменениями цвета

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

# Класс для отображения квадрата с изменяющимся цветом
class ColorSquare(QWidget):
    def __init__(self):
        super().__init__()
        self.color = QColor(255, 255, 255)  # Начальный цвет - белый

    def setColor(self, color):
        self.color = color
        self.update()  # Перерисовываем квадрат

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(self.color)
        painter.drawRect(0, 0, self.width(), self.height())

# Основное окно приложения
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Инициализация интерфейса пользователя
        self.initUI()

        # Создаем объект фоновой задачи с параметрами подключения к Modbus через Serial
        self.modbus_worker = ModbusWorker('COM5', 125000)
        self.color_worker = ColorWorker()

        # Подключаем сигналы к слотам для обновления интерфейса
        self.modbus_worker.update_signal.connect(self.updateLabel)
        self.color_worker.color_signal.connect(self.colorSquare.setColor)

    def initUI(self):
        self.label = QLabel('Waiting for data...', self)
        self.startButton = QPushButton('Start Reading', self)
        self.stopButton = QPushButton('Stop Reading', self)

        self.colorSquare = ColorSquare()
        self.colorSquare.setFixedSize(100, 100)

        # Подключаем кнопки к функциям для запуска и остановки фоновой задачи
        self.startButton.clicked.connect(self.startTasks)
        self.stopButton.clicked.connect(self.stopTasks)

        # Расположение элементов в окне
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.colorSquare)
        layout.addWidget(self.startButton)
        layout.addWidget(self.stopButton)
        self.setLayout(layout)

        self.setWindowTitle('PyQt6 Modbus Serial Example with Color Square')
        self.setGeometry(100, 100, 400, 300)

    def startTasks(self):
        # Запуск фоновых задач
        self.modbus_worker.start()
        self.color_worker.start()

    def stopTasks(self):
        # Остановка фоновых задач
        self.modbus_worker.stop()
        self.color_worker.stop()

    def updateLabel(self, text):
        # Обновление текста в интерфейсе пользователя
        self.label.setText(text)

    def closeEvent(self, event):
        # Останавливаем фоновые потоки при закрытии окна
        self.modbus_worker.stop()
        self.color_worker.stop()
        event.accept()

# Запуск приложения
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
