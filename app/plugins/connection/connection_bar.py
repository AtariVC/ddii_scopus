"""Бэкенд нижней панели подключения ДДИИ.

Публичный API для потребителей:
  * сигналы ``coroutine_finished``, ``disconnected``;
  * ``get_commands_interface() -> (ModbusCMCommand | None, ModbusMPPCommand | None)``;
  * ``check_connection(only_cm, only_mpp) -> bool`` (async);
  * ``is_modbus_ready() -> bool``;
  * ``bind_device(owner, device, tasks, on_ready, on_stop)`` — задачи потребителя;
  * атрибуты ``client``, ``tcp_client``, ``relay_server``, ``mpp_id``;
  * ``label_state_w`` — QLabel состояния (алиас статуса панели).

"""
from __future__ import annotations

import asyncio
import getpass
import os
import socket
import time
import traceback

import qasync
from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal

from custom.icons import load_svg_icon
from loguru import logger

from dark_pro_widgets import theme

from app.plugins.connection.connection_bar_ui import ConnectionBarUI
from app.plugins.connection.connection_settings import (
    ConnectionSettings,
    ConnectionSettingsDialog,
    list_serial_ports,
)
from app.plugins.connection.modbus_relay_server import ModbusRelayServer
from app.plugins.connection.device_binding import DeviceBinding
from app.plugins.connection.session import ConnectionSession
from app.src.components.log.config import get_logger
from app.src.components.modbus.command_interface import ModbusCMCommand, ModbusMPPCommand
from app.src.components.modbus.command_codec import ConnectionClosedError
from app.src.components.modbus.modbus_reg import ModbusReg
from app.src.components.modbus.worker import ModbusWorker


class ConnectionBar(ConnectionBarUI, ModbusReg):
    """Нижняя панель связи ДДИИ = UI (``ConnectionBarUI``) + бэкенд подключения.

    ● статус │ [Serial|TCP] │ ⚙ │ [Подключить] … State: ЦМ ✓ · МПП ✓

    Параметры (порт, baudrate, ID ЦМ/МПП, режим опроса) живут в диалоге настроек
    ``ConnectionSettingsDialog`` и сохраняются между запусками. Поле ``State``
    показывает результат подключения по каждому устройству — в объёме выбранного
    режима опроса.
    """

    # Бэкенд-сигналы (совместимость с прежним SerialConnect).
    # Презентационные сигналы (connectToggled/transportChanged/portChanged/
    # settingsClicked) наследуются от ConnectionBarUI.
    settingsChanged = pyqtSignal(object)  # применены новые ConnectionSettings
    coroutine_finished = pyqtSignal()
    tcp_status_changed = pyqtSignal(str, bool)
    disconnected = pyqtSignal()
    # (ЦМ доступен, МПП доступен) — шлётся при смене доступности, в том числе
    # при частичной связи. По нему виджеты гасят/включают свои кнопки.
    device_state_changed = pyqtSignal(bool, bool)

    def __init__(self, parent=None) -> None:
        # ConnectionBarUI: loadUi, тема, презентационная разводка сигналов.
        super().__init__(parent)

        self.logger = logger or get_logger(__name__)
        self.mw = ModbusWorker()

        # --- настройки (порт, baudrate, ID, режим опроса); переживают перезапуск ---
        self.settings: ConnectionSettings = ConnectionSettings.load()
        if not self.settings.serial_port:
            # первый запуск — подставляем первый доступный COM-порт
            ports = list_serial_ports()
            if ports:
                self.settings.serial_port = ports[0]
        if not self.settings.tcp_host:
            self.settings.tcp_host = self._get_local_ip()

        # --- состояние бэкенда ---
        self.status_CM = 0
        self.status_MPP = 0
        self._session: ConnectionSession | None = None
        self._commands = (None, None)
        self._connect_task: asyncio.Task | None = None
        self.client: AsyncModbusSerialClient | None = None
        self.tcp_client: AsyncModbusTcpClient | None = None
        self.relay_server: ModbusRelayServer | None = None
        # что уже сообщали в лог — гасит повтор одинаковых сообщений (см. _log_state)
        self._log_state_cache: dict[str, str | None] = {}

        # SVG-иконка ⚙ залита чёрным — перекрашиваем под тему (иконку ставит владелец UI)
        self.settings_btn.setIcon(load_svg_icon("settings", theme.TEXT_DIM))
        # Алиас для потребителей, которые пишут статус операций (калибровка и т.п.)
        self.label_state_w = self._status

        # --- сигналы: UI шлёт намерение, бэкенд выполняет действие ---
        self.connectToggled.connect(self._on_conn_toggled)
        self.settingsClicked.connect(self.open_settings)
        self.transportChanged.connect(self._on_transport_changed)
        QtWidgets.QApplication.instance().aboutToQuit.connect(self._disconnect)

        # --- начальное состояние ---
        self.transport.setCurrentIndex(0)  # Serial
        self.set_connected(False)
        self._update_state_label()

    # ===== настройки/состояние, зависящие от бэкенда =====
    def set_ports(self, ports, current=None) -> None:
        """Совместимость: порт живёт в настройках, список берётся системно."""
        if current:
            self.set_port(current)

    def set_port(self, port: str) -> None:
        self.settings.serial_port = str(port)
        self.settings.save()

    def set_mpp(self, mpp) -> None:
        self.settings.mpp_id = int(mpp)
        self.settings.save()

    def current_port(self) -> str:
        """Порт для текущего транспорта: COM-порт либо ``host:port``."""
        if self.is_serial_transport():
            return self.settings.serial_port
        return f"{self.settings.tcp_host}:{self.settings.tcp_port}"

    def current_mpp(self) -> int:
        return int(self.settings.mpp_id)

    # ID устройств — потребители читают ``w_ser_dialog.mpp_id``
    @property
    def mpp_id(self) -> int:
        return int(self.settings.mpp_id)

    @mpp_id.setter
    def mpp_id(self, value: int) -> None:
        self.settings.mpp_id = int(value)

    @property
    def cm_id(self) -> int:
        return int(self.settings.cm_id)

    # ===== настройки =====
    def open_settings(self) -> None:
        """Модальный диалог параметров соединения (⚙ на панели).

        Вызывается по ``settingsClicked`` (его шлёт UI при клике по ⚙), поэтому
        сам сигнал здесь не эмитим — иначе была бы рекурсия.
        """
        dialog = ConnectionSettingsDialog(self.settings, self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        settings = dialog.result_settings()
        if settings != self.settings:
            self._disconnect()
        self.settings = settings
        self.settings.save()
        self.logger.info(
            f"Настройки соединения: {self.settings.poll_label()}, "
            f"Legasy: {self.settings.legacy}, "
            f"порт={self.settings.serial_port or '—'}, baudrate={self.settings.baudrate}, "
            f"ЦМ={self.settings.cm_id}, МПП={self.settings.mpp_id}"
        )
        self.settingsChanged.emit(self.settings)
        # Режим опроса влияет на трактовку статусов — перерисуем State
        self._update_state_label()

    # ===== поле State: что реально опросили =====
    def _update_state_label(self) -> None:
        """Показывает результат по каждому устройству в объёме режима опроса.

        Примеры: ``ЦМ ✓ · МПП ✓``, ``ЦМ ✓ · МПП ✗``, ``только МПП: МПП ✓``.
        Пока не подключено — прочерк.
        """
        if not self._connected:
            self.set_state("—", theme.TEXT_DIM)
            self._notify_device_state()  # иначе кнопки остались бы активными
            return

        parts: list[str] = []
        oks: list[bool] = []
        if self.settings.poll_cm:
            ok = bool(self.status_CM)
            parts.append(f"ЦМ {'✓' if ok else '✗'}")
            oks.append(ok)
        if self.settings.poll_mpp:
            ok = bool(self.status_MPP)
            parts.append(f"МПП {'✓' if ok else '✗'}")
            oks.append(ok)

        if not parts:  # режим без устройств — теоретически недостижимо
            self.set_state("—", theme.TEXT_DIM)
            self._notify_device_state()
            return

        if all(oks):
            color, verdict = theme.OK, "Подключено"
        elif any(oks):
            color, verdict = theme.WARN, "Частично"
        else:
            color, verdict = theme.ERR, "Нет связи"
        self.set_state(" · ".join(parts), color)
        # слева — короткий вердикт тем же цветом; справа остаётся детализация
        self._set_status(verdict, color)
        self._notify_device_state()

    # ===== доступность устройств (для кнопок в виджетах) =====
    @property
    def cm_ready(self) -> bool:
        """ЦМ опрашивается и отвечает."""
        return bool(self.is_modbus_ready() and self.settings.poll_cm and self.status_CM)

    @property
    def mpp_ready(self) -> bool:
        """МПП опрашивается и отвечает."""
        return bool(self.is_modbus_ready() and self.settings.poll_mpp and self.status_MPP)

    def device_hint(self, device: str) -> str:
        """Почему устройство недоступно — текст для подсказки на кнопке."""
        poll = self.settings.poll_cm if device == "ЦМ" else self.settings.poll_mpp
        if not self.is_modbus_ready():
            return "Нет подключения к прибору"
        if not poll:
            return f"{device} отключён в настройках опроса (⚙)"
        return f"{device} не отвечает"

    def _notify_device_state(self) -> None:
        """Шлёт ``device_state_changed`` только при реальной смене доступности."""
        state = (self.cm_ready, self.mpp_ready)
        if state != getattr(self, "_last_device_state", None):
            self._last_device_state = state
            self.device_state_changed.emit(*state)

    # ===== кнопка подключения =====
    @qasync.asyncSlot(bool)
    async def _on_conn_toggled(self, connect_requested: bool) -> None:
        """Реакция на ``connectToggled`` из UI: подключить или отключить."""
        if connect_requested:
            await self.connect_clicked()
        else:
            await self.disconnect_clicked()

    async def connect_clicked(self) -> None:
        """Подключение согласно выбранному транспорту (Serial / TCP-клиент)."""
        if self._connect_task is not None or self.is_modbus_ready():
            return
        self._connect_task = asyncio.current_task()
        task = self._connect_task
        try:
            if self.is_serial_transport():
                await self._serial_connect()
            else:
                await self._tcp_connect()
        except asyncio.CancelledError:
            if self._connect_task is task:
                self._disconnect()
        except ConnectionClosedError:
            pass  # сессия уже выполнила отключение и сообщила причину
        except Exception as error:
            self._disconnect(f"Ошибка подключения: {error}", error)
        finally:
            if self._connect_task is asyncio.current_task():
                self._connect_task = None

    async def disconnect_clicked(self) -> None:
        """Полное отключение: relay-сервер, TCP-клиент, Serial-клиент."""
        self._disconnect()

    def _on_transport_changed(self, _transport: str) -> None:
        self._disconnect()

    def _disconnect(self, reason: str | None = None,
                    exc: BaseException | None = None) -> None:
        """Единая остановка: запрет запросов, закрытие транспорта, сброс UI и задач.

        Args:
            reason (str | None): причина отключения для лога и поля State.
            exc (BaseException | None): исходное исключение (если отключение
                вызвано сбоем) — попадёт в лог вместе с трейсбеком.
        """
        session, self._session = self._session, None
        was_active = session is not None or self.client is not None or self.tcp_client is not None
        self._commands = (None, None)
        self.status_CM = self.status_MPP = 0
        if session is not None:
            session.close()
        connecting, self._connect_task = self._connect_task, None
        if connecting is not None and not connecting.done():
            try:
                current = asyncio.current_task()
            except RuntimeError:
                current = None
            if connecting is not current:
                connecting.cancel()
        self.set_connected(False)
        self._update_state_label()
        if was_active:
            self.disconnected.emit()
        if self.relay_server is not None:
            self.stop_tcp_server()
        self.disconnect_tcp_client()
        self._close_serial_client()
        if reason:
            self._set_status("Нет связи", theme.ERR)
            caller = " <- ".join(
                f"{os.path.basename(frame.filename)}:{frame.lineno}"
                for frame in traceback.extract_stack()[-3:-1])
            self.logger.opt(exception=exc).error(f"{reason} [caller: {caller}]")

    def _on_session_failure(self, session: ConnectionSession, reason: str,
                            exc: BaseException | None = None) -> None:
        if session is self._session:
            self._disconnect(reason, exc)

    def bind_device(self, owner, device: str, tasks, on_ready, on_stop) -> DeviceBinding:
        """Связать задачи виджета с сессией ЦМ/МПП без собственного опроса связи."""
        return DeviceBinding(self, owner, device, tasks, on_ready, on_stop)

    # ===== Serial =====
    async def _serial_connect(self) -> None:
        port = self.settings.serial_port
        baudrate = int(self.settings.baudrate)
        if not port:
            self._set_status("Порт не задан", theme.WARN)
            return

        self.client = AsyncModbusSerialClient(
            port,
            timeout=3,
            baudrate=baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            handle_local_echo=True,
            # Соединением управляет кнопка панели, а не pymodbus: без этого первый
            # же таймаут запроса поднимал фоновую задачу переподключения, которая
            # молча открывала порт заново уже после нашего close().
            reconnect_delay=0,
            retries=3,
        )
        connected: bool = await self.client.connect()
        if not connected:
            self._disconnect("Порт занят или недоступен")
            return

        if not await self._await_serial_transport_ready():
            self._disconnect(f"{port}: транспорт pymodbus не поднялся — порт освобождён")
            return

        self.logger.debug(f"{port}, Baudrate={baudrate}, Parity=None, Stopbits=1, Bytesize=8")
        self._session = ConnectionSession(self.client, self._on_session_failure)
        if await self._check_connect():
            self.set_connected(True)
            self._update_state_label()
            self.coroutine_finished.emit()

    async def _check_connect(self) -> bool:
        """Опрашивает только те устройства, что включены режимом опроса.

        Статус выключенного устройства = 0 и в поле State он не показывается —
        так «не отвечает» не путается с «не опрашивали».
        """
        session = self._session
        if session is None:
            return False
        self.status_CM = self.status_MPP = 0
        probes = ((self.settings.poll_cm, "ЦМ", self.cm_id, self.dbg_reg.CM_STATUS, 1),
                  (self.settings.poll_mpp, "МПП", self.mpp_id, 0, 4))
        for enabled, name, slave, address, count in probes:
            if not enabled:
                continue
            response = await session.read_holding_registers(address, count, slave=slave)
            if response.isError():
                self.logger.error(
                    f"{name} (id={slave}) addr={address} cnt={count}: {response} "
                    f"exc_code={getattr(response, 'exception_code', None)} "
                    f"function={getattr(response, 'function_code', None)}")
                self._disconnect(f"{name} (id={slave}): проверка подключения отклонена: {response}")
                return False
            if name == "ЦМ":
                self.status_CM = 1
            else:
                self.status_MPP = 1
        return session.active

    async def _await_serial_transport_ready(self, timeout: float = 2.0) -> bool:
        """Дождаться, пока pymodbus действительно поднимет Serial-транспорт.

        ``create_serial_connection()`` только планирует ``SerialTransport.setup()``
        через ``loop.call_soon`` и сразу отдаёт транспорт, а ``connect()`` возвращает
        True. Под qasync (Qt-таймеры вместо очереди asyncio) этот callback успевает
        отработать не всегда, а от ``connect()`` до первой команды у нас нет ни одной
        точки передачи управления циклу. Пока ``setup()`` не отработал, ``poll_task``
        пуст, и ``SerialTransport.write()`` уходит в ветку
        ``add_writer(self.sync_serial.fileno())`` — а у pyserial на Windows нет
        ``fileno()`` (``io.UnsupportedOperation``). Ждём появления задачи опроса
        порта: она и есть признак, что транспорт умеет писать.

        На POSIX ``setup()`` вместо задачи вешает ``add_reader`` и ``poll_task``
        остаётся пустым навсегда — там ждать нечего (кроме отладочного
        ``SerialTransport.force_poll``, который мы не включаем).
        """
        if os.name != "nt":
            return True
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            transport = getattr(self.client, "transport", None)
            if getattr(transport, "poll_task", None) is not None:
                return True
            await asyncio.sleep(0.01)
        return False

    def _close_serial_client(self) -> None:
        """Закрывает Serial-клиент и обнуляет ссылку, чем бы ни кончился close().

        На Windows транспорт pymodbus местами дёргает ``fileno()`` у pyserial,
        которого там нет (``io.UnsupportedOperation``). Исключение из ``close()``
        раньше улетало наружу, оставляя ``self.client`` живым, а порт — занятым.
        """
        client, self.client = self.client, None
        if client is None:
            return
        try:
            client.close()
        except Exception as e:  # noqa: BLE001 — закрытие не должно ронять UI
            self.logger.debug(f"Ошибка при закрытии Serial-клиента: {e}")

    def _log_state(self, key: str, message: str | None, level: str = "debug") -> None:
        """Пишет в лог только при смене состояния по ключу.

        Потребители дёргают ``check_connection``/``get_commands_interface`` на
        каждое нажатие кнопки и в циклах опроса. Без этого фильтра одно и то же
        «устройство не отвечает» сыпалось бы в терминал десятки раз подряд.
        Передача ``None`` означает «состояние снова в норме» — следующий сбой
        будет залогирован заново.
        """
        if self._log_state_cache.get(key) == message:
            return
        self._log_state_cache[key] = message
        if message:
            getattr(self.logger, level, self.logger.debug)(message)

    # ===== TCP-клиент =====
    async def _tcp_connect(self) -> None:
        host, port = self.settings.tcp_host, int(self.settings.tcp_port)
        if not host:
            self._set_status("Хост не задан", theme.WARN)
            return
        try:
            await self._tcp_preflight_diagnostics(host, port)

            # reconnect_delay=0 — переподключением управляет кнопка панели, не pymodbus
            tcp_client = AsyncModbusTcpClient(host=host, port=port, timeout=2, reconnect_delay=0, retries=0)
            self.tcp_client = tcp_client
            connected = await tcp_client.connect()
            if connected:
                self._session = ConnectionSession(tcp_client, self._on_session_failure)
                if not await self._check_connect():
                    return
                self.set_connected(True)
                self._update_state_label()
                self.tcp_status_changed.emit(f"Подключено к {host}:{port}", True)
                self.logger.info(f"Подключено к TCP серверу {host}:{port}")
                try:
                    await self._send_client_identity(self._session)
                except Exception as e:
                    self.logger.warning(f"Не удалось отправить идентификатор: {e}")
                if self.is_modbus_ready():
                    self.coroutine_finished.emit()
            else:
                self._disconnect(f"Не удалось подключиться к {host}:{port}")
                self.tcp_status_changed.emit("Не удалось подключиться", False)
        except ConnectionClosedError:
            return
        except Exception as e:
            self._disconnect(f"Ошибка TCP подключения: {e}", e)
            self.tcp_status_changed.emit(f"Ошибка подключения: {e}", False)

    def disconnect_tcp_client(self) -> None:
        """Отключение TCP клиента"""
        client, self.tcp_client = self.tcp_client, None
        if client is not None:
            try:
                client.close()
            except Exception as error:
                self.logger.debug(f"Ошибка закрытия TCP: {error}")
            self.tcp_status_changed.emit("Отключено", False)
            self.logger.info("TCP подключение закрыто")

    async def _send_client_identity(self, tcp_client: AsyncModbusTcpClient) -> None:
        """Отправка на сервер краткой информации о клиенте в HR[80..]."""
        try:
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
            slave = self.cm_id if self.settings.poll_cm else self.mpp_id
            await tcp_client.write_registers(address=80, values=regs, slave=slave)
            self.logger.info("Отправлен идентификатор серверу")
        except ConnectionClosedError:
            return
        except Exception as e:
            self.logger.warning(f"Ошибка при формировании/отправке идентификации клиента: {e}")

    async def _tcp_preflight_diagnostics(self, host: str, port: int) -> None:
        """Диагностика TCP перед подключением: DNS и доступность порта.

        Пишет подробности в лог, не выбрасывает исключений наружу.
        """
        try:
            infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
            addrs = [f"{ai[4][0]}:{ai[4][1]}" for ai in infos]
            self.logger.debug(f"DNS {host}:{port} -> {', '.join(addrs)}")
        except Exception as e:
            self.logger.error(f"DNS ошибка для {host}:{port}: {e}")
        try:
            conn = asyncio.open_connection(host=host, port=port)
            reader, writer = await asyncio.wait_for(conn, timeout=1.5)
            try:
                peer = writer.get_extra_info("peername")
                lcl = writer.get_extra_info("sockname")
                self.logger.debug(f"TCP порт доступен, peer={peer}, local={lcl}")
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    ...
        except Exception as e:
            self.logger.error(f"Порт недоступен для TCP: {host}:{port} — {e}")

    # ===== relay-сервер (host-режим; вызывается программно) =====
    async def start_tcp_server(self, host: str | None = None, port: int | None = None) -> bool:
        """Запуск локального relay-сервера, проксирующего TCP → Serial."""
        host = host or self.settings.tcp_host or self._get_local_ip()
        port = int(port or self.settings.tcp_port)
        if not self.is_modbus_ready() or self.client is None:
            return False
        relay_server = ModbusRelayServer(self._session, host, port,
                                        cm_id=self.cm_id if self.settings.poll_cm else None,
                                        mpp_id=self.mpp_id if self.settings.poll_mpp else None)
        if await relay_server.start_server():
            self.relay_server = relay_server
            self.logger.info(f"TCP сервер УСПЕШНО запущен на {host}:{port}")
            self.tcp_status_changed.emit(f"Успешный запуск сервера на {host}:{port}", True)
            return True
        self.tcp_status_changed.emit("Ошибка запуска сервера", False)
        return False

    def stop_tcp_server(self) -> None:
        """Остановка relay-сервера."""
        server, self.relay_server = self.relay_server, None
        if server is not None:
            try:
                server.stop_server()
            except Exception as error:
                self.logger.debug(f"Ошибка остановки relay: {error}")
            self.tcp_status_changed.emit("Сервер остановлен", False)
            self.logger.info("TCP сервер остановлен")

    # ===== вспомогательное =====
    def _get_local_ip(self) -> str:
        """Возвращает локальный IPv4 (не loopback), если возможно."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                if ip and not ip.startswith("127."):
                    return ip
        except Exception:
            pass
        try:
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                if ip and not ip.startswith("127."):
                    return ip
        except Exception:
            pass
        return "127.0.0.1"

    # ===== публичный API для потребителей (совместимость с SerialConnect) =====
    def is_modbus_ready(self) -> bool:
        return bool(self._connected and self._session is not None and self._session.active)

    def get_commands_interface(self) -> tuple[ModbusCMCommand | None, ModbusMPPCommand | None]:
        """Команды с актуальным клиентом и адресами из настроек.

        ``None`` вместо команды означает «этим устройством сейчас работать
        нельзя»: нет транспорта или устройство выключено режимом опроса.
        Потребители уже проверяют ``is None`` перед каждой командой — так
        выключенный ЦМ не порождает ни трафика в шину, ни вечного цикла опроса,
        молча падающего в ``b"-1"``.
        """
        if not self.is_modbus_ready():
            return None, None
        if any(command is not None for command in self._commands):
            return self._commands
        cli = self._session
        cm = None
        if self.settings.poll_cm:
            cm = ModbusCMCommand(cli)
            cm.CM_ID = self.cm_id

        mpp = None
        if self.settings.poll_mpp:
            mpp = ModbusMPPCommand(cli, self.mpp_id)
        self._commands = (cm, mpp)
        return self._commands

    async def check_connection(self, only_cm=True, only_mpp=True) -> bool:
        """Готово ли соединение для работы вызывающего.

        Не обращается к шине: устройства проверены при подключении, последующие
        запросы контролирует ConnectionSession.

        ``only_cm``/``only_mpp`` — что нужно вызывающему. Устройство, выключенное
        режимом опроса, для того, кто его запросил, недоступно: виджет ЦМ в
        режиме «только МПП» обязан получить ``False`` и не запускать свой опрос,
        а не ориентироваться на статус чужого устройства. Поэтому флаги нужно
        указывать честно — дефолт ``True/True`` означает «нужны оба».
        """
        if not self.is_modbus_ready():
            self._log_state("transport", "Modbus клиент не подключен")
            return False
        self._log_state("transport", None)

        # Отказ по режиму опроса — до любого обращения к шине
        if only_cm and not self.settings.poll_cm:
            self._log_state("need_cm", f"ЦМ выключен режимом опроса ({self.settings.poll_label()})")
            return False
        self._log_state("need_cm", None)
        if only_mpp and not self.settings.poll_mpp:
            self._log_state("need_mpp", f"МПП выключен режимом опроса ({self.settings.poll_label()})")
            return False
        self._log_state("need_mpp", None)
        required_cm = bool(only_cm)
        required_mpp = bool(only_mpp)
        if not required_cm and not required_mpp:
            # Вызывающему из опрашиваемых устройств ничего не нужно — достаточно живого транспорта
            return self.is_modbus_ready()

        ok = True
        if required_cm:
            ok = ok and bool(self.status_CM)
        if required_mpp:
            ok = ok and bool(self.status_MPP)
        # конкретика по устройствам уже ушла в лог из _check_connect
        self._log_state("ready", None if ok else "Подключение потеряно", "error")
        return ok

    def closeEvent(self, event) -> None:  # noqa: N802
        self._disconnect()
        super().closeEvent(event)


if __name__ == "__main__":
    # Сырой запуск (памятка §10): у ConnectionBar есть async-слот (кнопка
    # подключения), поэтому вместо preview нужен ручной qasync-скелет.
    import sys

    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget

    from dark_pro_widgets import qss

    from app.src.components.log.config import log_init

    app = QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())  # тема ddii (как в приложении)

    # хост-окно: бар прижат к низу, как в реальном приложении (ТЗ §8)
    host = QWidget()
    host.setWindowTitle("ConnectionBar — автономный запуск")
    host.setStyleSheet(f"background-color: {theme.BG};")
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addStretch()

    bar = ConnectionBar(log_init())
    layout.addWidget(bar)

    host.resize(960, 240)
    # Тёмный системный заголовок верхнеуровневого окна — ДО show() (см. §10).
    theme.tint_window_board(int(host.winId()))
    host.show()

    # qasync-петля обязательна: кнопка подключения — async-слот (Serial/TCP).
    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
