import sys
import asyncio
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel
from qasync import QEventLoop, asyncSlot
from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException

class ModbusWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Настройка окна
        self.setWindowTitle("Modbus COM5 Example")
        self.setGeometry(100, 100, 300, 200)

        # Интерфейс
        layout = QVBoxLayout()

        self.status_label = QLabel("Status: Not Connected")
        layout.addWidget(self.status_label)

        self.connect_button = QPushButton("Connect to COM5")
        layout.addWidget(self.connect_button)

        self.send_button = QPushButton("Send Command")
        self.send_button.setEnabled(False)  # Кнопка отключена до подключения
        layout.addWidget(self.send_button)

        self.setLayout(layout)

        # Подключаем обработчики событий
        self.connect_button.clicked.connect(self.on_connect_click)
        self.send_button.clicked.connect(self.on_send_click)

        # Инициализация клиента Modbus
        self.modbus_client = None

    @asyncSlot()
    async def on_connect_click(self):
        """Обработчик подключения к COM5."""
        try:
            # Подключаемся к COM5 с использованием Modbus RTU
            self.modbus_client = AsyncModbusSerialClient(
                method='rtu', port='COM5', baudrate=9600, timeout=1
            )
            connected = await self.modbus_client.connect()
            if connected:
                self.status_label.setText("Status: Connected to COM5")
                self.send_button.setEnabled(True)
                print("Connected to COM5")
            else:
                self.status_label.setText("Status: Connection Failed")
                print("Failed to connect to COM5")
        except ModbusException as e:
            self.status_label.setText(f"Status: Error - {e}")
            print(f"Modbus Error: {e}")

    @asyncSlot()
    async def on_send_click(self):
        """Отправка команды через Modbus."""
        if self.modbus_client:
            try:
                # Отправляем запрос (например, чтение регистра или запись)
                # В данном примере отправляем фиктивный запрос чтения регистра
                result = await self.modbus_client.read_holding_registers(address=1, count=1, unit=1)
                if result.isError():
                    self.status_label.setText("Status: Error sending command")
                    print("Error in response")
                else:
                    self.status_label.setText("Status: Command sent successfully")
                    print(f"Response: {result.registers}")
            except ModbusException as e:
                self.status_label.setText(f"Status: Error - {e}")
                print(f"Modbus Error: {e}")

# Главная функция
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Интеграция asyncio с PyQt
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = ModbusWindow()
    window.show()

    # Запускаем цикл событий
    with loop:
        loop.run_forever()
