import asyncio
import sys
from pathlib import Path

import qasync
import qtmodern.styles
from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSequentialDataBlock
from pymodbus.pdu import ModbusResponse
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import QSizePolicy
from qtmodern.windows import ModernWindow
from qtpy.uic import loadUi

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from src.customComboBox_COMport import CustomComboBox_COMport  # noqa: E402
from src.env_var import EnvironmentVar  # noqa: E402
from src.log_config import log_init, log_s  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
from style.styleSheet import widget_led_off, widget_led_on  # noqa: E402


class ModbusRelayServer:
    """Сервер для ретрансляции Modbus данных"""
    
    def __init__(self, serial_client, host='0.0.0.0', port=5012):
        self.serial_client = serial_client
        self.host = host
        self.port = port
        self.server = None
        self.context = None
        self._setup_datastore()
    
    def _setup_datastore(self):
        """Настройка хранилища данных Modbus"""
        store = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [0]*100),
            co=ModbusSequentialDataBlock(0, [0]*100),
            hr=ModbusSequentialDataBlock(0, [0]*100),
            ir=ModbusSequentialDataBlock(0, [0]*100)
        )
        self.context = ModbusServerContext(slaves=store, single=True)
    
    async def start_server(self):
        """Запуск TCP сервера"""
        try:
            self.server = await StartAsyncTcpServer(
                context=self.context,
                address=(self.host, self.port),
                defer_start=False
            )
            print(f"Modbus TCP сервер запущен на {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Ошибка запуска сервера: {e}")
            return False
    
    async def stop_server(self):
        """Остановка TCP сервера"""
        if self.server:
            self.server.server_close()
            print("Modbus TCP сервер остановлен")


class SerialConnect(QtWidgets.QWidget, EnvironmentVar):

    tabWidget_serial: QtWidgets.QTabWidget
    # serial
    pushButton_connect_w: QtWidgets.QPushButton
    lineEdit_Bauderate_w: QtWidgets.QLineEdit
    lineEdit_ID_w: QtWidgets.QLineEdit
    widget_led_w: QtWidgets.QWidget
    label_state_w: QtWidgets.QLabel
    horizontalLayout_comport: QtWidgets.QHBoxLayout
    # tcp
    lineEdit_ip: QtWidgets.QLineEdit
    lineEdit_tcp_port: QtWidgets.QLineEdit
    pushButton_connect_tcp: QtWidgets.QPushButton
    widget_led_tcp: QtWidgets.QWidget
    label_tcp: QtWidgets.QLabel

    coroutine_finished = QtCore.pyqtSignal()
    tcp_status_changed = QtCore.pyqtSignal(str, bool)

    def __init__(self, logger, **kwargs) -> None:
        super().__init__(**kwargs)
        loadUi(Path(__file__).parents[0].joinpath("DialogSerialTCP.ui"), self)
        self.mw = ModbusWorker()
        self.logger = logger
        self.comboBox_comm = CustomComboBox_COMport()
        self.horizontalLayout_comport.addWidget(self.comboBox_comm)
        self.size_policy: QSizePolicy = self.comboBox_comm.sizePolicy()
        self.pushButton_connect_flag = 0
        self.size_policy.setHorizontalPolicy(QSizePolicy.Policy.Preferred)
        self.comboBox_comm.setSizePolicy(self.size_policy)
        self.mpp_id: int = 14
        self.state_serial: int = 0
        self.serial_task = None
        self.status_CM = 1
        self.status_MPP = 1
        self.client: AsyncModbusSerialClient = None
        self.tcp_client: AsyncModbusTcpClient = None
        self.relay_server: ModbusRelayServer = None
        self.server_task = None
        self.tcp_connected = False
        self.server_running = False
        
        # Подключаем обработчики
        self.pushButton_connect_w.clicked.connect(self.pushButton_connect_Handler)
        self.pushButton_connect_tcp.clicked.connect(self.tcp_button_handler)
        self.tcp_status_changed.connect(self.update_tcp_status)
        
        # Обновляем интерфейс при смене вкладок
        self.tabWidget_serial.currentChanged.connect(self.update_tcp_interface)

    def update_tcp_interface(self, index):
        """Обновление интерфейса TCP в зависимости от состояния serial"""
        if index == 1:  # Вкладка TCP
            if self.pushButton_connect_flag == 1:  # Есть serial подключение
                self.pushButton_connect_tcp.setText("Запустить сервер" if not self.server_running else "Остановить сервер")
                self.label_tcp.setText("Состояние сервера:")
            else:  # Нет serial подключения
                self.pushButton_connect_tcp.setText("Подключить" if not self.tcp_connected else "Отключить")
                self.label_tcp.setText("Состояние подключения:")

    @qasync.asyncSlot()
    async def tcp_button_handler(self):
        """Обработчик кнопки TCP"""
        if self.pushButton_connect_flag == 1:  # Есть serial подключение - управляем сервером
            await self.tcp_server_handler()
        else:  # Нет serial подключения - подключаемся как клиент
            await self.tcp_client_handler()

    async def tcp_server_handler(self):
        """Обработчик для режима сервера"""
        if self.server_running:
            await self.stop_tcp_server()
        else:
            await self.start_tcp_server()

    async def tcp_client_handler(self):
        """Обработчик для режима клиента"""
        if self.tcp_connected:
            await self.disconnect_tcp_client()
        else:
            await self.connect_tcp_client()

    async def start_tcp_server(self):
        """Запуск TCP сервера"""
        host = self.lineEdit_ip.text()
        port = int(self.lineEdit_tcp_port.text())
        
        self.relay_server = ModbusRelayServer(self.client, host, port)
        
        if await self.relay_server.start_server():
            self.server_running = True
            self.tcp_status_changed.emit(f"Сервер запущен на {host}:{port}", True)
            self.logger.info(f"TCP сервер запущен на {host}:{port}")
        else:
            self.tcp_status_changed.emit("Ошибка запуска сервера", False)

    async def stop_tcp_server(self):
        """Остановка TCP сервера"""
        if self.relay_server:
            await self.relay_server.stop_server()
            self.relay_server = None
            self.server_running = False
            self.tcp_status_changed.emit("Сервер остановлен", False)
            self.logger.info("TCP сервер остановлен")

    async def connect_tcp_client(self):
        """Подключение как TCP клиент"""
        host = self.lineEdit_ip.text()
        port = int(self.lineEdit_tcp_port.text())
        
        try:
            self.tcp_client = AsyncModbusTcpClient(
                host=host,
                port=port,
                timeout=2
            )
            
            connected = await self.tcp_client.connect()
            if connected:
                self.tcp_connected = True
                self.tcp_status_changed.emit(f"Подключено к {host}:{port}", True)
                self.logger.info(f"Подключено к TCP серверу {host}:{port}")
            else:
                self.tcp_status_changed.emit("Не удалось подключиться", False)
                
        except Exception as e:
            self.tcp_status_changed.emit(f"Ошибка подключения: {e}", False)
            self.logger.error(f"Ошибка TCP подключения: {e}")

    async def disconnect_tcp_client(self):
        """Отключение TCP клиента"""
        if self.tcp_client:
            self.tcp_client.close()
            self.tcp_client = None
            self.tcp_connected = False
            self.tcp_status_changed.emit("Отключено", False)
            self.logger.info("TCP подключение закрыто")

    def update_tcp_status(self, message, is_connected):
        """Обновление статуса TCP"""
        if self.pushButton_connect_flag == 1:  # Режим сервера
            self.label_tcp.setText(f"Состояние сервера: {message}")
        else:  # Режим клиента
            self.label_tcp.setText(f"Состояние подключения: {message}")
        
        self.widget_led_tcp.setStyleSheet(widget_led_on() if is_connected else widget_led_off())
        
        # Обновляем текст кнопки
        if self.pushButton_connect_flag == 1:
            self.pushButton_connect_tcp.setText("Остановить сервер" if is_connected else "Запустить сервер")
        else:
            self.pushButton_connect_tcp.setText("Отключить" if is_connected else "Подключить")

    @qasync.asyncSlot()
    async def pushButton_connect_Handler(self) -> None:
        await self.serialConnect()
        if self.pushButton_connect_flag == 1:
            self.coroutine_finished.emit()
        # Обновляем интерфейс TCP при изменении состояния serial
        self.update_tcp_interface(self.tabWidget_serial.currentIndex())

    @qasync.asyncSlot()
    async def serialConnect(self) -> None:
        baudrate = int(self.lineEdit_Bauderate_w.text())
        self.mpp_id = int(self.lineEdit_ID_w.text())
        
        if self.pushButton_connect_flag == 0:
            port = self.comboBox_comm.currentText()
            self.client = AsyncModbusSerialClient(
                port,
                timeout=1,
                baudrate=baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
                handle_local_echo=True,
            )
            
            connected: bool = await self.client.connect()
            if connected:
                self.state_serial = 1
                self.logger.debug(
                    f"{port}, Baudrate={baudrate}, Parity=None, Stopbits=1, Bytesize=8"
                )
            else:
                self.label_state_w.setText("State: COM-порт занят. Попробуйте переподключиться")
                self.state_serial = 0

            if self.state_serial == 1:
                self.pushButton_connect_w.setText("Отключить")
                self.pushButton_connect_flag = 1
                await self.check_connect()
                if self.status_CM and self.status_MPP == 0:
                    self.client.close()
                    await asyncio.sleep(1)
                    self.label_state_w.setText("State: Нет подключения к ДДИИ")
                    self.pushButton_connect_flag = 0
                    self.pushButton_connect_w.setText("Подключить")
        else:
            # Останавливаем TCP сервер при отключении
            if self.server_running:
                await self.stop_tcp_server()
            
            # Закрываем TCP клиент если был подключен
            if self.tcp_connected:
                await self.disconnect_tcp_client()
            
            self.pushButton_connect_w.setText("Подключить")
            self.pushButton_connect_flag = 0
            self.widget_led_w.setStyleSheet(widget_led_off())
            self.label_state_w.setText("State:")
            self.client.close()

    @qasync.asyncSlot()
    async def check_connect(self) -> None:
        self.status_CM = 1
        self.status_MPP = 1

        #### CM ####
        try:
            await self.client.write_registers(address=self.DDII_SWITCH_MODE, values=self.SILENT_MODE, slave=self.CM_ID)
            await log_s(self.mw.send_handler.mess)
        except Exception as e:
            self.logger.debug("Соединение c ЦМ не установлено")
            self.logger.error(e)
            self.status_CM = 0

        ######## MPP #######
        try:
            response: ModbusResponse = await self.client.read_holding_registers(0x0000, 4, slave=self.mpp_id)
            await log_s(self.mw.send_handler.mess)
        except Exception as e:
            self.status_MPP = 0
            self.logger.debug("Соединение c МПП не установлено")
            self.logger.error(e)

        await self.update_label_connect()

    @qasync.asyncSlot()
    async def update_label_connect(self):
        cheak_st_connect = self.status_CM, self.status_MPP
        if cheak_st_connect == (1, 1):
            self.widget_led_w.setStyleSheet(widget_led_on())
            self.label_state_w.setText("State: CM - OK, MPP - OK")
        elif cheak_st_connect == (1, 0):
            self.label_state_w.setText("State: CM - OK, MPP - None")
            self.widget_led_w.setStyleSheet(widget_led_on())
        elif cheak_st_connect == (0, 1):
            self.label_state_w.setText("State: CM - None, MPP - OK")
        elif cheak_st_connect == (0, 0):
            self.label_state_w.setText("State: CM - None, MPP - None")
            self.widget_led_w.setStyleSheet(widget_led_off())


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    logger = log_init()
    w: SerialConnect = SerialConnect(logger)
    
    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    w.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, False)
    w.show()

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...