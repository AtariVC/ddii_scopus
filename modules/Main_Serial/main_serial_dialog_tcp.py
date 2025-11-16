import asyncio
import sys
from pathlib import Path

import qasync
import socket
import getpass
import qtmodern.styles
from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.pdu import ModbusResponse
from pymodbus.server import StartAsyncTcpServer
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

from custom.widgets import widget_led_off, widget_led_on  # noqa: E402
from src.customComboBox_COMport import CustomComboBox_COMport  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.env_var import EnvironmentVar  # noqa: E402
from src.log_config import log_init, log_s, get_logger  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402

BAUDRATE = 125000


class ModbusRelayServer:
    """Сервер для ретрансляции Modbus данных"""

    def __init__(self, serial_client, host="0.0.0.0", port=5012, cm_id: int | None = None, mpp_id: int | None = None):
        self.serial_client = serial_client
        self.host = host
        self.port = port
        self.server = None  # may be asyncio.Server in some versions
        self.server_task = None  # asyncio.Task for server lifetime
        self.context = None
        self.loop = None
        self.cm_id = cm_id
        self.mpp_id = mpp_id
        self._setup_datastore()

    def _setup_datastore(self):
        """Настройка хранилища данных Modbus.
        Создаёт прокси‑блоки, которые пробрасывают чтение/запись в serial‑клиент,
        а также отдельную область HR[80..] для сообщений идентификации клиентов.
        """
        logger = get_logger(__name__)

        class ProxySequentialDataBlock(ModbusSequentialDataBlock):
            def __init__(self, relay: 'ModbusRelayServer', unit_id: int, kind: str):
                super().__init__(0, [0] * 512)
                self.relay = relay
                self.unit_id = unit_id
                self.kind = kind  # 'hr' | 'ir'

            def getValues(self, address, count=1):  # type: ignore[override]
                # Служебная область (идентификация клиентов) обслуживается локально
                try:
                    if int(address) >= 80:
                        return super().getValues(address, count)
                except Exception:
                    ...
                cli = self.relay.serial_client
                if cli is None:
                    return [0] * int(count)
                try:
                    loop = self.relay.loop or asyncio.get_event_loop()
                    if self.kind == 'hr':
                        fut = asyncio.run_coroutine_threadsafe(
                            cli.read_holding_registers(int(address), int(count), slave=int(self.unit_id)), loop
                        )
                    else:
                        fut = asyncio.run_coroutine_threadsafe(
                            cli.read_input_registers(int(address), int(count), slave=int(self.unit_id)), loop
                        )
                    resp = fut.result(timeout=2.0)
                    regs = getattr(resp, 'registers', None)
                    if regs is None:
                        try:
                            raw = resp.encode()
                            regs = [int.from_bytes(raw[i:i+2], 'big') for i in range(0, len(raw), 2)]
                        except Exception:
                            regs = [0] * int(count)
                    return list(regs)[: int(count)]
                except Exception as e:
                    logger.error(f"Proxy getValues error ({self.kind}) addr={address} cnt={count}: {e}")
                    return [0] * int(count)

            def setValues(self, address, values):  # type: ignore[override]
                # Перехватываем служебную область идентификации — не пробрасываем в прибор
                try:
                    if int(address) >= 80:
                        super().setValues(address, values)
                        try:
                            regs = list(values) if isinstance(values, (list, tuple)) else [values]
                            bb = bytearray()
                            for v in regs:
                                try:
                                    bb.extend(int(v).to_bytes(2, byteorder='big', signed=False))
                                except Exception:
                                    pass
                            text = bb.rstrip(b"\x00").decode(errors='ignore')
                            if text:
                                logger.info(f"[TCP SERVER] Новое подключение: {text}")
                        except Exception:
                            ...
                        return
                except Exception:
                    ...
                cli = self.relay.serial_client
                if cli is None:
                    return
                try:
                    loop = self.relay.loop or asyncio.get_event_loop()
                    fut = asyncio.run_coroutine_threadsafe(
                        cli.write_registers(int(address), list(values), slave=int(self.unit_id)), loop
                    )
                    fut.result(timeout=2.0)
                except Exception as e:
                    logger.error(f"Proxy setValues error addr={address}: {e}")

        # Собираем карту slaves по unit id (ЦМ/МПП)
        try:
            slaves: dict[int, ModbusSlaveContext] = {}
            if self.cm_id is not None:
                slaves[int(self.cm_id)] = ModbusSlaveContext(
                    di=ModbusSequentialDataBlock(0, [0] * 64),
                    co=ModbusSequentialDataBlock(0, [0] * 64),
                    hr=ProxySequentialDataBlock(self, int(self.cm_id), 'hr'),
                    ir=ProxySequentialDataBlock(self, int(self.cm_id), 'ir'),
                )
            if self.mpp_id is not None:
                slaves[int(self.mpp_id)] = ModbusSlaveContext(
                    di=ModbusSequentialDataBlock(0, [0] * 64),
                    co=ModbusSequentialDataBlock(0, [0] * 64),
                    hr=ProxySequentialDataBlock(self, int(self.mpp_id), 'hr'),
                    ir=ProxySequentialDataBlock(self, int(self.mpp_id), 'ir'),
                )
            if slaves:
                self.context = ModbusServerContext(slaves=slaves, single=False)
            else:
                store = ModbusSlaveContext(
                    di=ModbusSequentialDataBlock(0, [0] * 64),
                    co=ModbusSequentialDataBlock(0, [0] * 64),
                    hr=ModbusSequentialDataBlock(0, [0] * 512),
                    ir=ModbusSequentialDataBlock(0, [0] * 64),
                )
                self.context = ModbusServerContext(slaves=store, single=True)
        except Exception as e:
            logger.error(f"Ошибка создания контекста сервера: {e}")
            store = ModbusSlaveContext(
                di=ModbusSequentialDataBlock(0, [0] * 64),
                co=ModbusSequentialDataBlock(0, [0] * 64),
                hr=ModbusSequentialDataBlock(0, [0] * 512),
                ir=ModbusSequentialDataBlock(0, [0] * 64),
            )
            self.context = ModbusServerContext(slaves=store, single=True)

    async def start_server(self):
        """Запуск TCP сервера"""
        try:
            self.loop = asyncio.get_event_loop()
            # В ряде версий pymodbus StartAsyncTcpServer является длительно живущей корутиной,
            # поэтому запускаем её как фоновую задачу, чтобы не блокировать UI-слот.
            srv_coro = StartAsyncTcpServer(context=self.context, address=(self.host, self.port))
            self.server_task = asyncio.create_task(srv_coro)
            # Дадим циклу шанс выполнить привязку сокета и отловить мгновенные ошибки
            await asyncio.sleep(0.05)
            if self.server_task.done():
                # Если задача завершилась мгновенно — проверим на исключение
                exc = self.server_task.exception()
                if exc:
                    print(f"Ошибка запуска сервера: {exc}")
                    self.server_task = None
                    return False
            print(f"Modbus TCP сервер запущен (фоново) на {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Ошибка запуска сервера: {e}")
            return False

    def stop_server(self):
        """Остановка TCP сервера"""
        stopped = False
        # Останавливаем задачу сервера, если запускается как Task
        if self.server_task:
            try:
                self.server_task.cancel()
            except Exception:
                pass
            self.server_task = None
            stopped = True
        # Дополнительно пробуем корректно закрыть объект сервера, если он есть
        if self.server:
            try:
                self.server.close()
                stopped = True
            except Exception:
                try:
                    self.server.server_close()
                    stopped = True
                except Exception:
                    pass
            self.server = None
        if stopped:
            print("Modbus TCP сервер остановлен")


class SerialConnect(QtWidgets.QWidget, EnvironmentVar):
    tabWidget_serial: QtWidgets.QTabWidget
    # serial
    pushButton_connect_w: QtWidgets.QPushButton
    checkBox_mpp_only: QtWidgets.QCheckBox
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
    checkBox_host: QtWidgets.QCheckBox

    coroutine_finished = QtCore.pyqtSignal()
    tcp_status_changed = QtCore.pyqtSignal(str, bool)
    disconnected = QtCore.pyqtSignal()

    def __init__(self, logger, **kwargs) -> None:
        super().__init__(**kwargs)
        loadUi(Path(__file__).parents[0].joinpath("DialogSerialTCP.ui"), self)
        self.mw = ModbusWorker()
        self.logger = logger
        self.comboBox_comm = CustomComboBox_COMport()
        self.horizontalLayout_comport.addWidget(self.comboBox_comm)
        self.size_policy: QSizePolicy = self.comboBox_comm.sizePolicy()
        # Признак подключения Serial определяется по self.client
        self.size_policy.setHorizontalPolicy(QSizePolicy.Policy.Preferred)
        self.comboBox_comm.setSizePolicy(self.size_policy)
        self.mpp_id: int = 14
        self.status_CM = 1
        self.status_MPP = 1
        self.client: AsyncModbusSerialClient | None = None
        self.tcp_client: AsyncModbusTcpClient | None = None
        self.relay_server: ModbusRelayServer | None = None
        # Признаки TCP клиента/сервера определяются по self.tcp_client/self.relay_server
        # Устанавливаем локальный IP при запуске, если доступен
        try:
            self.lineEdit_ip.setText(self._get_local_ip())
        except Exception:
            ...
        # Подключаем обработчики
        self.pushButton_connect_w.clicked.connect(self.pushButton_connect_Handler)
        self.pushButton_connect_tcp.clicked.connect(self.tcp_button_handler)
        self.tcp_status_changed.connect(self.update_tcp_status)
        # Реакция на смену режима Хост/Клиент
        try:
            self.checkBox_host.toggled.connect(lambda _: self.update_tcp_mode_ui())
        except Exception:
            ...

        # Обновляем интерфейс при смене вкладок
        self.tabWidget_serial.currentChanged.connect(self.update_tcp_interface)

        # Нулевой клиент для безопасных команд при отсутствии связи
        class _NullModbusClient(AsyncModbusSerialClient):
            def __init__(self):
                pass

            async def read_holding_registers(self, *args, **kwargs):
                raise RuntimeError("No Modbus client connected")

            async def write_registers(self, *args, **kwargs):
                raise RuntimeError("No Modbus client connected")

            async def connect(self, *args, **kwargs):
                return False

            def close(self):
                return None

        self._null_client = _NullModbusClient()

    def _get_local_ip(self) -> str:
        """Возвращает локальный IPv4 адрес (не loopback), если возможно.

        Порядок попыток:
        1) UDP-сокет к 8.8.8.8:80 (без реальной отправки) и чтение адреса интерфейса.
        2) Перебор адресов хоста через gethostbyname_ex и выбор не-127.*
        3) Fallback: 127.0.0.1
        """
        # Try UDP trick — не выполняет сетевой обмен, только выбор интерфейса
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                if ip and not ip.startswith("127."):
                    return ip
        except Exception:
            pass
        # Fallback: resolve hostname
        try:
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                if ip and not ip.startswith("127."):
                    return ip
        except Exception:
            pass
        return "127.0.0.1"

    def update_tcp_interface(self, index):
        """Обновление интерфейса TCP в зависимости от состояния serial"""
        if index == 1:  # Вкладка TCP
            self.update_tcp_mode_ui()

    def update_tcp_mode_ui(self):
        """Настройка UI под выбранный режим TCP (Хост/Клиент)."""
        is_host = bool(self.checkBox_host.isChecked())
        if is_host:
            # Режим сервера (Хост)
            self.pushButton_connect_tcp.setText("Остановить" if self.relay_server is not None else "Запустить")
            self.label_tcp.setText("Состояние сервера:")
        else:
            # Режим клиента
            self.pushButton_connect_tcp.setText("Отключить" if self.tcp_client is not None else "Подключить")
            self.label_tcp.setText("Состояние подключения:")

    @qasync.asyncSlot()
    async def tcp_button_handler(self):
        """Обработчик кнопки TCP"""
        if self.checkBox_host.isChecked():
            # Режим Хост: запуск/остановка локального сервера
            await self.tcp_server_handler()
        else:
            # Режим Клиент: подключение/отключение к серверу
            await self.tcp_client_handler()

    async def tcp_server_handler(self):
        """Обработчик для режима сервера"""
        if self.relay_server is not None:
            self.stop_tcp_server()
        else:
            await self.start_tcp_server()

    async def tcp_client_handler(self):
        """Обработчик для режима клиента"""
        if self.tcp_client is not None:
            self.disconnect_tcp_client()
        else:
            await self.connect_tcp_client()

    async def start_tcp_server(self):
        """Запуск TCP сервера"""
        host = self.lineEdit_ip.text()
        port = int(self.lineEdit_tcp_port.text())

        # Создаем сервер и сохраняем только при успешном запуске
        relay_server = ModbusRelayServer(self.client, host, port, cm_id=self.CM_ID, mpp_id=self.mpp_id)

        if await relay_server.start_server():
            self.relay_server = relay_server
            # Попробуем получить фактический адрес сокета
            bound_addr = None
            try:
                server_obj = getattr(relay_server, "server", None)
                if server_obj is not None and hasattr(server_obj, "sockets"):
                    sockets = getattr(server_obj, "sockets", [])
                    if sockets:
                        bound_addr = sockets[0].getsockname()
            except Exception:
                bound_addr = None
            addr_str = f"{host}:{port}" if not bound_addr else f"{bound_addr[0]}:{bound_addr[1]}"
            # Логируем подробности сервера
            self.logger.info(f"TCP сервер УСПЕШНО запущен на {addr_str}")
            # Обновляем кнопку сразу
            self.pushButton_connect_tcp.setText("Остановить")
            # Сообщаем в статус: успех
            self.tcp_status_changed.emit(f"Успешный запуск сервера на {addr_str}", True)
        else:
            # Сообщаем в статус: ошибка
            self.tcp_status_changed.emit("Ошибка запуска сервера", False)
            self.pushButton_connect_tcp.setText("Запустить")

    def stop_tcp_server(self):
        """Остановка TCP сервера"""
        if self.relay_server:
            self.relay_server.stop_server()
            self.relay_server = None
            self.tcp_status_changed.emit("Сервер остановлен", False)
            self.logger.info("TCP сервер остановлен")

    async def connect_tcp_client(self):
        """Подключение как TCP клиент"""
        host = self.lineEdit_ip.text()
        port = int(self.lineEdit_tcp_port.text())

        try:
            # Предварительная диагностика подключения (DNS/доступность порта)
            await self._tcp_preflight_diagnostics(host, port)

            tcp_client = AsyncModbusTcpClient(host=host, port=port, timeout=2)

            connected = await tcp_client.connect()
            if connected:
                self.tcp_client = tcp_client
                self.tcp_status_changed.emit(f"Подключено к {host}:{port}", True)
                self.logger.info(f"Подключено к TCP серверу {host}:{port}")
                # Отправляем идентификацию клиента на сервер (в holding registers начиная с 80)
                try:
                    await self._send_client_identity(tcp_client)
                except Exception as e:
                    self.logger.warning(f"Не удалось подключиться: {e}")
            else:
                # Закрываем созданный клиент, если не удалось подключиться
                try:
                    tcp_client.close()
                except Exception:
                    pass
                self.logger.error(
                    f"AsyncModbusTcpClient.connect() вернул False (host={host}, port={port}).\n"
                    "Проверьте, что сервер запущен, порт не занят и брандмауэр не блокирует соединение."
                )
                self.tcp_status_changed.emit("Не удалось подключиться", False)

        except Exception as e:
            self.tcp_status_changed.emit(f"Ошибка подключения: {e}", False)
            self.logger.error(f"Ошибка TCP подключения: {e}")

    async def _send_client_identity(self, tcp_client: AsyncModbusTcpClient) -> None:
        """Отправка на сервер краткой информации о клиенте в HR[80..]."""
        try:
            user = None
            try:
                user = getpass.getuser()
            except Exception:
                user = None
            hostname = socket.gethostname()
            local_ip = self._get_local_ip()
            info = f"client={user or 'unknown'} host={hostname} ip={local_ip}"
            data = info.encode("utf-8")
            if len(data) % 2 == 1:
                data += b"\x00"
            regs: list[int] = []
            for i in range(0, len(data), 2):
                regs.append(int.from_bytes(data[i : i + 2], byteorder="big", signed=False))
            # Пишем начиная с адреса 80, unit id 1 (single=True в сервере игнорирует unit)
            await tcp_client.write_registers(address=80, values=regs, unit=1)
            self.logger.info("Отправлен идентификатор серверу")
        except Exception as e:
            self.logger.warning(f"Ошибка при формировании/отправке идентификации клиента: {e}")

    async def _tcp_preflight_diagnostics(self, host: str, port: int) -> None:
        """Диагностика TCP перед подключением: DNS и доступность порта.

        Пишет подробности в лог, не выбрасывает исключений наружу.
        """
        # DNS‑резолвинг
        try:
            infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
            addrs = [f"{ai[4][0]}:{ai[4][1]}" for ai in infos]
            self.logger.debug(f"DNS {host}:{port} -> {', '.join(addrs)}")
        except Exception as e:
            self.logger.error(f"DNS ошибка для {host}:{port}: {e}")
        # Пробный коннект с таймаутом через asyncio (не Modbus)
        try:
            conn = asyncio.open_connection(host=host, port=port)
            reader, writer = await asyncio.wait_for(conn, timeout=1.5)
            try:
                sock = writer.get_extra_info("socket")
                peer = writer.get_extra_info("peername")
                lcl = writer.get_extra_info("sockname")
                self.logger.debug(f"TCP порт доступен, peer={peer}, local={lcl}, sock={sock}")
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    ...
        except Exception as e:
            self.logger.error(f"Порт недоступен для TCP: {host}:{port} — {e}")

    def disconnect_tcp_client(self):
        """Отключение TCP клиента"""
        if self.tcp_client:
            self.tcp_client.close()
            self.tcp_client = None
            self.tcp_status_changed.emit("Отключено", False)
            self.logger.info("TCP подключение закрыто")

    def disconnect_serial_client(self):
        """Отключение Serial клиента"""
        # Останавливаем TCP сервер при отключении
        if self.relay_server is not None:
            self.stop_tcp_server()

        # Закрываем TCP клиент если был подключен
        if self.tcp_client is not None:
            self.disconnect_tcp_client()
            self.logger.info("TCP подключение закрыто")
            self.tcp_status_changed.emit("Отключено", False)
            self.disconnected.emit()

        if self.client:
            self.client.close()
            self.client = None
            self.label_state_w.setText("State: Отключено")
            self.pushButton_connect_w.setText("Подключить")

    def update_tcp_status(self, message, is_connected):
        """Обновление статуса TCP"""
        if self.checkBox_host.isChecked():  # Режим сервера
            self.label_tcp.setText(f"Состояние сервера: {message}")
        else:  # Режим клиента
            self.label_tcp.setText(f"Состояние подключения: {message}")

        self.widget_led_tcp.setStyleSheet(widget_led_on() if is_connected else widget_led_off())

        # Обновляем текст кнопки
        if self.checkBox_host.isChecked():
            self.pushButton_connect_tcp.setText("Остановить" if is_connected else "Запустить")
        else:
            self.pushButton_connect_tcp.setText("Отключить" if is_connected else "Подключить")

    @qasync.asyncSlot()
    async def pushButton_connect_Handler(self) -> None:
        await self.serialConnect()
        if self.client is not None:
            # Обновляем интерфейс TCP при изменении состояния serial
            self.update_tcp_interface(self.tabWidget_serial.currentIndex())
            self.coroutine_finished.emit()

    @qasync.asyncSlot()
    async def serialConnect(self) -> None:
        self.mpp_id = int(self.lineEdit_ID_w.text())

        if self.client is None:
            port = self.comboBox_comm.currentText()
            self.client = AsyncModbusSerialClient(
                port,
                timeout=1,
                baudrate=BAUDRATE,
                bytesize=8,
                parity="N",
                stopbits=1,
                handle_local_echo=True,
            )

            connected: bool = await self.client.connect()
            if connected:
                self.logger.debug(f"{port}, Baudrate={BAUDRATE}, Parity=None, Stopbits=1, Bytesize=8")
                self.pushButton_connect_w.setText("Отключить")
                await self._check_connect()
            else:
                self.label_state_w.setText("State: COM-порт занят. Попробуйте переподключиться")
        else:
            self.pushButton_connect_w.setText("Подключить")
            self.widget_led_w.setStyleSheet(widget_led_off())
            self.label_state_w.setText("State:")
            if self.client:
                self.client.close()
                self.client = None
            else:
                ...
            self.disconnected.emit()

    @qasync.asyncSlot()
    async def _check_connect(self) -> None:
        self.status_CM = 1
        self.status_MPP = 1

        ######## MPP #######
        try:
            if self.client:
                response: ModbusResponse = await self.client.read_holding_registers(0x0000, 4, slave=self.mpp_id)
                await log_s(self.mw.send_handler.mess)
                self.status_MPP = 1
        except Exception as e:
            self.status_MPP = 0
            self.logger.debug("Соединение c МПП не установлено")
            self.logger.error(str(e))

        #### CM ####
        if self.checkBox_mpp_only.isChecked() is False:
            try:
                if self.client:
                    await self.client.write_registers(
                        address=self.DDII_SWITCH_MODE, values=self.SILENT_MODE, slave=self.CM_ID
                    )
                    await log_s(self.mw.send_handler.mess)
                    self.status_CM = 1
            except Exception as e:
                self.logger.debug("Соединение c ЦМ не установлено")
                self.logger.error(str(e))
                self.status_CM = 0
        else:
            self.status_CM = 0
        await self.update_label_connect()
        if self.status_CM and self.status_MPP == 0 and self.client:
            self.client.close()
            await asyncio.sleep(1)
            self.client = None
            self.label_state_w.setText("State: Нет подключения к ДДИИ")
            self.pushButton_connect_w.setText("Подключить")
            self.disconnected.emit()

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

    # ===== Проверки состояния подключения по Serial =====
    def is_modbus_ready(self) -> bool:
        # Готовность при наличии любого транспорта: Serial или TCP‑клиента
        return (self.client is not None) or (self.tcp_client is not None)

    def get_commands_interface(self, logger) -> tuple[ModbusCMCommand, ModbusMPPCommand]:
        """Возвращает новые объекты команд с актуальным клиентом и MPP_ID.
        Если соединения нет, возвращает команды с null‑клиентом.
        """
        # Выбираем доступный транспорт: приоритет у Serial, затем TCP‑клиента
        cli = (
            self.client
            if self.client is not None
            else (self.tcp_client if self.tcp_client is not None else self._null_client)
        )
        if bool(self.checkBox_mpp_only.isChecked()):
            cm = ModbusCMCommand(self._null_client, logger)
        else:
            cm = ModbusCMCommand(cli, logger)
        try:
            mpp = ModbusMPPCommand(cli, logger, self.mpp_id)
        except Exception:
            mpp = ModbusMPPCommand(cli, logger)
        return cm, mpp

    async def check_connection(self, only_cm=True, only_mpp=True) -> bool:
        """
        Проверка подключения CM и MPP по Serial. Для внешнего использования.

        - Проверяет наличие клиента; при его отсутствии возвращает False.
        - Обновляет статусы устройств через `check_connect()`.
        - Если активен `checkBox_mpp_only`, то для готовности устройств достаточно
        доступности МПП; ЦМ игнорируется. Иначе требуются ЦМ и МПП.

        Returns:
            bool: True, если условия подключения выполнены, иначе False.
        """
        if not self.is_modbus_ready():
            self.logger.debug("Modbus клиент не подключен")
            return False
        # Если работаем как TCP‑клиент, считаем подключение готовым (проверка выполнится на стороне сервера)
        if self.tcp_client is not None and self.client is None:
            self.status_CM = 1
            self.status_MPP = 1
            await self.update_label_connect()
            return True
        await self._check_connect()
        if self.status_CM and self.status_MPP:
            return True  # Оба устройства подключены
        elif self.status_MPP and self.checkBox_mpp_only.isChecked():
            return True  # Только МПП подключен, ЦМ игнорируется
        elif self.status_CM and not only_mpp:
            return True  # Только ЦМ требуется и он подключен
        elif self.status_MPP and not only_cm:
            return True  # Только МПП требуется и он подключен
        else:
            self.logger.error("Подключение потеряно")
            return False  # Устройства не готовы


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
