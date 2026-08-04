"""Бэкенд нижней панели подключения ДДИИ.

Публичный API для потребителей:
  * сигналы ``coroutine_finished``, ``disconnected``;
  * ``get_commands_interface(logger) -> (ModbusCMCommand, ModbusMPPCommand)``;
  * ``check_connection(only_cm, only_mpp) -> bool`` (async);
  * ``is_modbus_ready() -> bool``;
  * атрибуты ``client``, ``tcp_client``, ``relay_server``, ``mpp_id``;
  * ``label_state_w`` — QLabel состояния (алиас статуса панели).

"""
from __future__ import annotations

import asyncio
import getpass
import socket

import qasync
from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal

from custom.icons import load_svg_icon

from dark_pro_widgets import theme

from app.plugins.connection.connection_bar_ui import ConnectionBarUI
from app.plugins.connection.connection_settings import (
    ConnectionSettings,
    ConnectionSettingsDialog,
    list_serial_ports,
)
from app.plugins.connection.modbus_relay_server import ModbusRelayServer
from app.src.components.log.config import get_logger, log_s
from app.src.components.modbus.command_interface import ModbusCMCommand, ModbusMPPCommand
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

    def __init__(self, logger=None, parent=None) -> None:
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
        self.status_CM = 1
        self.status_MPP = 1
        self.client: AsyncModbusSerialClient | None = None
        self.tcp_client: AsyncModbusTcpClient | None = None
        self.relay_server: ModbusRelayServer | None = None
        # что уже сообщали в лог — гасит повтор одинаковых сообщений (см. _log_state)
        self._log_state_cache: dict[str, str | None] = {}
        # Дамп обмена по serial (TX/RX хексом, как в DockLight). По умолчанию выключен —
        # иначе каждая команда сыплет в терминал. Включается: bar.log_serial_exchange = True
        self.log_serial_exchange = False

        # --- нулевой клиент для безопасных команд при отсутствии связи ---
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

        # SVG-иконка ⚙ залита чёрным — перекрашиваем под тему (иконку ставит владелец UI)
        self.settings_btn.setIcon(load_svg_icon("settings", theme.TEXT_DIM))
        # Алиас для потребителей, которые пишут статус операций (калибровка и т.п.)
        self.label_state_w = self._status

        # --- сигналы: UI шлёт намерение, бэкенд выполняет действие ---
        self.connectToggled.connect(self._on_conn_toggled)
        self.settingsClicked.connect(self.open_settings)

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
        self.settings = dialog.result_settings()
        self.settings.save()
        self.logger.info(
            f"Настройки соединения: {self.settings.poll_label()}, "
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
        if self.current_transport().lower().startswith("serial"):
            await self._serial_connect()
        else:
            await self._tcp_connect()

    async def disconnect_clicked(self) -> None:
        """Полное отключение: relay-сервер, TCP-клиент, Serial-клиент."""
        if self.relay_server is not None:
            self.stop_tcp_server()
        if self.tcp_client is not None:
            self.disconnect_tcp_client()
        if self.client is not None:
            self.client.close()
            self.client = None
        self.set_connected(False)
        self._update_state_label()
        self.disconnected.emit()

    # ===== Serial =====
    async def _serial_connect(self) -> None:
        port = self.settings.serial_port
        baudrate = int(self.settings.baudrate)
        if not port:
            self._set_status("Порт не задан", theme.WARN)
            return

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
        if not connected:
            self.client = None
            self._set_status("Порт занят", theme.ERR)
            return

        self.logger.debug(f"{port}, Baudrate={baudrate}, Parity=None, Stopbits=1, Bytesize=8")
        await self._check_connect()
        if self.client is not None:
            self.set_connected(True)
            self._update_state_label()
            self.coroutine_finished.emit()

    async def _check_connect(self) -> None:
        """Опрашивает только те устройства, что включены режимом опроса.

        Статус выключенного устройства = 0 и в поле State он не показывается —
        так «не отвечает» не путается с «не опрашивали».
        """
        self.status_CM = 0
        self.status_MPP = 0

        ######## MPP #######
        if self.settings.poll_mpp:
            try:
                if self.client:
                    await self.client.read_holding_registers(0x0000, 4, slave=self.mpp_id)
                    await log_s(self.mw.send_handler.mess)
                    self.status_MPP = 1
                    self._log_state("mpp", None)
            except Exception as e:
                self.status_MPP = 0
                self._log_state("mpp", f"МПП (id={self.mpp_id}) не отвечает: {e}", "warning")

        #### CM ####
        if self.settings.poll_cm:
            try:
                if self.client:
                    await self.client.write_registers(
                        address=self.ctrl_reg.DEBUG_MODE_SWITCH, values=1, slave=self.cm_id
                    )
                    await log_s(self.mw.send_handler.mess)
                    self.status_CM = 1
                    self._log_state("cm", None)
            except Exception as e:
                self.status_CM = 0
                self._log_state("cm", f"ЦМ (id={self.cm_id}) не отвечает: {e}", "warning")

        self._update_state_label()

        # Ни одно из затребованных устройств не ответило — связи с ДДИИ нет
        if not self._any_required_ok() and self.client:
            self.client.close()
            await asyncio.sleep(1)
            self.client = None
            self.set_connected(False)
            self._set_status("Нет связи", theme.ERR)
            self._update_state_label()
            self.disconnected.emit()

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

    def _any_required_ok(self) -> bool:
        """Ответило ли хоть одно устройство из включённых в опрос."""
        return bool(
            (self.settings.poll_cm and self.status_CM) or (self.settings.poll_mpp and self.status_MPP)
        )

    # ===== TCP-клиент =====
    async def _tcp_connect(self) -> None:
        host, port = self.settings.tcp_host, int(self.settings.tcp_port)
        if not host:
            self._set_status("Хост не задан", theme.WARN)
            return
        try:
            await self._tcp_preflight_diagnostics(host, port)

            tcp_client = AsyncModbusTcpClient(host=host, port=port, timeout=2)
            connected = await tcp_client.connect()
            if connected:
                self.tcp_client = tcp_client
                # Опрос выполняет сервер-ретранслятор — считаем включённые устройства доступными
                self.status_CM = 1 if self.settings.poll_cm else 0
                self.status_MPP = 1 if self.settings.poll_mpp else 0
                self.set_connected(True)
                self._update_state_label()
                self.tcp_status_changed.emit(f"Подключено к {host}:{port}", True)
                self.logger.info(f"Подключено к TCP серверу {host}:{port}")
                try:
                    await self._send_client_identity(tcp_client)
                except Exception as e:
                    self.logger.warning(f"Не удалось отправить идентификатор: {e}")
                self.coroutine_finished.emit()
            else:
                try:
                    tcp_client.close()
                except Exception:
                    pass
                self.logger.error(
                    f"AsyncModbusTcpClient.connect() вернул False (host={host}, port={port}).\n"
                    "Проверьте, что сервер запущен, порт не занят и брандмауэр не блокирует соединение."
                )
                self._set_status("Нет связи", theme.ERR)
                self.tcp_status_changed.emit("Не удалось подключиться", False)
        except Exception as e:
            self._set_status("Ошибка связи", theme.ERR)
            self.tcp_status_changed.emit(f"Ошибка подключения: {e}", False)
            self.logger.error(f"Ошибка TCP подключения: {e}")

    def disconnect_tcp_client(self) -> None:
        """Отключение TCP клиента"""
        if self.tcp_client:
            self.tcp_client.close()
            self.tcp_client = None
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
            await tcp_client.write_registers(address=80, values=regs, unit=1)
            self.logger.info("Отправлен идентификатор серверу")
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
        relay_server = ModbusRelayServer(self.client, host, port, cm_id=self.cm_id, mpp_id=self.mpp_id)
        if await relay_server.start_server():
            self.relay_server = relay_server
            self.logger.info(f"TCP сервер УСПЕШНО запущен на {host}:{port}")
            self.tcp_status_changed.emit(f"Успешный запуск сервера на {host}:{port}", True)
            return True
        self.tcp_status_changed.emit("Ошибка запуска сервера", False)
        return False

    def stop_tcp_server(self) -> None:
        """Остановка relay-сервера."""
        if self.relay_server:
            self.relay_server.stop_server()
            self.relay_server = None
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
        # Готовность при наличии любого транспорта: Serial или TCP‑клиента
        return (self.client is not None) or (self.tcp_client is not None)

    def get_commands_interface(self, logger) -> tuple[ModbusCMCommand, ModbusMPPCommand]:
        """Команды с актуальным клиентом и адресами из настроек.

        Устройство, выключенное режимом опроса, получает null-клиент: любая
        попытка обратиться к нему честно упадёт, а не уйдёт молча в шину.
        """
        cli = (
            self.client
            if self.client is not None
            else (self.tcp_client if self.tcp_client is not None else self._null_client)
        )
        cm_cli = cli if self.settings.poll_cm else self._null_client
        mpp_cli = cli if self.settings.poll_mpp else self._null_client

        slog = self.log_serial_exchange
        cm = ModbusCMCommand(cm_cli, logger, log_serial_exchange=slog)

        cm.CM_ID = self.cm_id
        try:
            mpp = ModbusMPPCommand(mpp_cli, logger, self.mpp_id, log_serial_exchange=slog)
        except Exception:
            mpp = ModbusMPPCommand(mpp_cli, logger, log_serial_exchange=slog)
        return cm, mpp

    async def check_connection(self, only_cm=True, only_mpp=True) -> bool:
        """Готово ли соединение для работы вызывающего.

        Устройство считается обязательным, если оно нужно вызывающему
        (``only_cm``/``only_mpp``) И включено режимом опроса. Так виджет,
        которому нужен только МПП, не падает из-за выключенного ЦМ.
        """
        if not self.is_modbus_ready():
            self._log_state("transport", "Modbus клиент не подключен")
            return False
        self._log_state("transport", None)
        # Как TCP‑клиент считаем подключение готовым — проверка на стороне сервера
        if self.tcp_client is not None and self.client is None:
            self.status_CM = 1 if self.settings.poll_cm else 0
            self.status_MPP = 1 if self.settings.poll_mpp else 0
            self._update_state_label()
            return True

        await self._check_connect()

        required_cm = bool(only_cm and self.settings.poll_cm)
        required_mpp = bool(only_mpp and self.settings.poll_mpp)
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
