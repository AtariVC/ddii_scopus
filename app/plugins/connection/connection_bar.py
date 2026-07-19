"""Нижняя панель подключения (ConnectionBar) — обновлённый дизайн + бэкенд.

Разметка берётся из ``connection_bar.ui`` (loadUi), тема и промоут-виджеты — из
``dark_pro_widgets``. Бэкенд (Serial / TCP‑клиент / relay‑сервер, проверка
ЦМ/МПП, фабрика команд) перенесён из
``main_serial_dialog_tcp.py`` (класс ``SerialConnect``, теперь в !old/),
поэтому ``ConnectionBar`` — полноценная замена прежнего диалога: его кладут в
``w_ser_dialog`` и он же служит постоянной нижней панелью (ТЗ §8).

Публичный API для потребителей (run_meas / run_flux / ddii_control /
cmd_wind_read_mem / *_settings):
  * сигналы ``coroutine_finished``, ``disconnected``;
  * ``get_commands_interface(logger) -> (ModbusCMCommand, ModbusMPPCommand)``;
  * ``check_connection(only_cm, only_mpp) -> bool`` (async);
  * ``is_modbus_ready() -> bool``;
  * атрибуты ``client``, ``tcp_client``, ``relay_server``, ``mpp_id``;
  * ``label_state_w`` — QLabel состояния (алиас статуса панели).

Презентационный API (совпадает с dark_pro_widgets.ConnectionBar):
  ``set_connected``/``set_ports``/``set_port``/``set_transport``/``set_mpp``/
  ``set_state`` и геттеры ``is_connected``/``current_transport``/
  ``current_port``/``current_mpp`` плюс сигналы ``connectToggled``/
  ``transportChanged``/``portChanged``.
"""
from __future__ import annotations

# Прямой запуск файла (`python app/plugins/connection/connection_bar.py` или
# кнопка Run в IDE): абсолютные импорты `app.*` и promoted-виджеты из .ui
# работают только когда модуль исполняется в контексте пакета. Перезапускаем его
# как app.plugins.connection.connection_bar, добавив корень репозитория в sys.path.
if __name__ == "__main__" and __package__ in (None, ""):
    import os
    import runpy
    import sys

    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    runpy.run_module("app.plugins.connection.connection_bar", run_name="__main__", alter_sys=True)
    raise SystemExit(0)

import asyncio
import getpass
import socket
from pathlib import Path

import qasync
from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartAsyncTcpServer
from PyQt6 import QtWidgets
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from qtpy.uic import loadUi

from custom.icons import load_svg_icon

from dark_pro_widgets import theme
from dark_pro_widgets.buttons import PrimaryButton
from dark_pro_widgets.segmented_control import SegmentedControl

from app.plugins.connection.connection_settings import (
    ConnectionSettings,
    ConnectionSettingsDialog,
    list_serial_ports,
)
from app.src.components.log.config import get_logger, log_s
from app.src.components.modbus.ddii_command import ModbusCMCommand, ModbusMPPCommand
from app.src.components.modbus.modbus_var import ModbusVar
from app.src.components.modbus.worker import ModbusWorker

# Единая высота контролов панели — продублирована в connection_bar.ui.
CONTROL_H = 32
# Фон панели — RGB(19, 20, 23); рельс — theme.FIELD_BG RGB(15, 16, 19).
BAR_BG = "#131417"

_FONT = theme.FONT_FAMILY.split(",")[0].strip()
_MONO = theme.MONO_FAMILY.split(",")[0].strip()


# --- promotion-адаптеры ------------------------------------------------------
# Загрузчик .ui создаёт promoted-виджеты только как ``Class(parent)``, а базовые
# виджеты dark_pro_widgets требуют обязательные аргументы (items/text). Тонкие
# подклассы дают конструктор ``(parent)`` с нужными умолчаниями. Подключены в
# connection_bar.ui через <customwidget> (header = этот модуль).

class _TransportSwitch(SegmentedControl):
    """Сегменты Serial | TCP."""

    def __init__(self, parent=None):
        super().__init__(["Serial", "TCP"], parent=parent)


class _ConnectButton(PrimaryButton):
    """Кнопка Подключить/Отключить — компактная, акцентная по умолчанию."""

    def __init__(self, parent=None):
        super().__init__("", variant="accent", compact=True, parent=parent)


class _IconButton(QtWidgets.QPushButton):
    """Плоская иконочная кнопка панели (32×32). Саму иконку ставит владелец —
    через ``custom.icons.load_svg_icon`` с цветом из темы."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(18, 18))
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 7px;
            }}
            QPushButton:hover {{
                background-color: {theme.FIELD_BG};
                border: 1px solid {theme.BORDER};
            }}
            QPushButton:pressed {{ background-color: #2f343d; }}
        """)


class ModbusRelayServer:
    """Сервер для ретрансляции Modbus данных (перенесён из SerialConnect)."""

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
            def __init__(self, relay: "ModbusRelayServer", unit_id: int, kind: str):
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
                    if self.kind == "hr":
                        fut = asyncio.run_coroutine_threadsafe(
                            cli.read_holding_registers(int(address), int(count), slave=int(self.unit_id)), loop
                        )
                    else:
                        fut = asyncio.run_coroutine_threadsafe(
                            cli.read_input_registers(int(address), int(count), slave=int(self.unit_id)), loop
                        )
                    resp = fut.result(timeout=2.0)
                    regs = getattr(resp, "registers", None)
                    if regs is None:
                        try:
                            raw = resp.encode()
                            regs = [int.from_bytes(raw[i:i + 2], "big") for i in range(0, len(raw), 2)]
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
                                    bb.extend(int(v).to_bytes(2, byteorder="big", signed=False))
                                except Exception:
                                    pass
                            text = bb.rstrip(b"\x00").decode(errors="ignore")
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
                    hr=ProxySequentialDataBlock(self, int(self.cm_id), "hr"),
                    ir=ProxySequentialDataBlock(self, int(self.cm_id), "ir"),
                )
            if self.mpp_id is not None:
                slaves[int(self.mpp_id)] = ModbusSlaveContext(
                    di=ModbusSequentialDataBlock(0, [0] * 64),
                    co=ModbusSequentialDataBlock(0, [0] * 64),
                    hr=ProxySequentialDataBlock(self, int(self.mpp_id), "hr"),
                    ir=ProxySequentialDataBlock(self, int(self.mpp_id), "ir"),
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
        logger = get_logger(__name__)
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
                    logger.error(f"Ошибка запуска сервера: {exc}")
                    self.server_task = None
                    return False
            logger.info(f"Modbus TCP сервер запущен (фоново) на {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Ошибка запуска сервера: {e}")
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
            get_logger(__name__).info("Modbus TCP сервер остановлен")


class ConnectionBar(QtWidgets.QWidget, ModbusVar):
    """Постоянная нижняя панель связи + бэкенд подключения ДДИИ.

    ● статус │ [Serial|TCP] │ ⚙ │ [Подключить] … State: ЦМ ✓ · МПП ✓

    Параметры (порт, baudrate, ID ЦМ/МПП, режим опроса) живут в диалоге настроек
    ``ConnectionSettingsDialog`` и сохраняются между запусками. Поле ``State``
    показывает результат подключения по каждому устройству — в объёме выбранного
    режима опроса.
    """

    # Презентационные сигналы (совместимость с dark_pro_widgets.ConnectionBar)
    connectToggled = pyqtSignal(bool)
    transportChanged = pyqtSignal(str)
    portChanged = pyqtSignal(str)
    settingsClicked = pyqtSignal()  # ⚙ нажата (панель сама открывает диалог)
    settingsChanged = pyqtSignal(object)  # применены новые ConnectionSettings
    # Бэкенд-сигналы (совместимость с прежним SerialConnect)
    coroutine_finished = pyqtSignal()
    tcp_status_changed = pyqtSignal(str, bool)
    disconnected = pyqtSignal()

    # Аннотации виджетов из .ui
    _dot: QtWidgets.QLabel
    _status: QtWidgets.QLabel
    sep1: QtWidgets.QFrame
    transport: _TransportSwitch
    settings_btn: _IconButton
    _btn: _ConnectButton
    _state_caption: QtWidgets.QLabel
    _state: QtWidgets.QLabel

    def __init__(self, logger=None, parent=None) -> None:
        super().__init__(parent)
        # виджеты .ui становятся атрибутами self (см. аннотации выше)
        loadUi(Path(__file__).parent / "connection_bar.ui", self)

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
        self._connected = False
        # что уже сообщали в лог — гасит повтор одинаковых сообщений (см. _log_state)
        self._log_state_cache: dict[str, str | None] = {}
        # Дамп обмена по serial (TX/RX хексом, как в DockLight). По умолчанию выключен —
        # иначе каждая команда сыплет в терминал. Включается: bar.serial_log_enabled = True
        self.serial_log_enabled = False

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

        # --- оформление панели/виджетов (цвета из theme.*) ---
        self.setObjectName("ConnectionBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(46)
        self.setStyleSheet(
            f"#ConnectionBar {{ background-color: {BAR_BG}; "
            f"border-top: 1px solid {theme.SEPARATOR}; }}"
        )
        self._status.setStyleSheet(
            f"color: {theme.TEXT}; font-family: '{_FONT}'; background: transparent; border: none;"
        )
        self.sep1.setStyleSheet(f"background-color: {theme.BORDER}; border: none;")
        # SVG-иконки залиты чёрным — перекрашиваем под тему, иначе не видно
        self.settings_btn.setIcon(load_svg_icon("settings", theme.TEXT_DIM))
        self._state_caption.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-family: '{_MONO}'; background: transparent; border: none;"
        )

        # Алиас для потребителей, которые пишут статус операций (калибровка и т.п.)
        self.label_state_w = self._status

        # --- сигналы ---
        self.transport.currentTextChanged.connect(self.transportChanged)
        self._btn.clicked.connect(self._on_btn_clicked)
        self.settings_btn.clicked.connect(self.open_settings)

        # --- начальное состояние ---
        self.transport.setCurrentIndex(0)  # Serial
        self.set_connected(False)
        self._update_state_label()

    # ===== презентационный API (как у dark_pro_widgets.ConnectionBar) =====
    def _set_dot(self, ok: bool) -> None:
        self._paint_status(color=theme.OK if ok else theme.TEXT_DIM)

    def _paint_status(self, color: str) -> None:
        """Красит точку и надпись статуса одним цветом состояния."""
        self._dot.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        self._status.setStyleSheet(
            f"color: {color}; font-family: '{_FONT}'; font-weight: 600; "
            "background: transparent; border: none;"
        )

    def _set_status(self, text: str, color: str) -> None:
        """Короткий вердикт слева: текст + цвет. Детализация по ЦМ/МПП — в State."""
        self._status.setText(text)
        self._paint_status(color)

    def set_connected(self, connected: bool) -> None:
        self._connected = bool(connected)
        if self._connected:
            self._set_status("Подключено", theme.OK)
        else:
            self._set_status("Отключено", theme.TEXT_DIM)
        # 'Отключить' — нейтральная тёмная; 'Подключить' — акцентная
        self._btn.setText("Отключить" if self._connected else "Подключить")
        self._btn.setVariant("neutral" if self._connected else "accent")

    def set_ports(self, ports, current=None) -> None:
        """Совместимость: порт живёт в настройках, список берётся системно."""
        if current:
            self.set_port(current)

    def set_port(self, port: str) -> None:
        self.settings.serial_port = str(port)
        self.settings.save()

    def set_transport(self, name: str) -> None:
        idx = 0 if name.lower().startswith("serial") else 1
        self.transport.setCurrentIndex(idx)

    def set_mpp(self, mpp) -> None:
        self.settings.mpp_id = int(mpp)
        self.settings.save()

    def set_state(self, text: str, color: str | None = None) -> None:
        """Прямая установка поля State (обычно вызывается ``_update_state_label``)."""
        self._state.setText(text)
        self._state.setStyleSheet(
            f"color: {color or theme.TEXT_DIM}; font-family: '{_MONO}'; font-weight: 600; "
            "background: transparent; border: none;"
        )

    def is_connected(self) -> bool:
        return self._connected

    def current_transport(self) -> str:
        return self.transport.currentText()

    def is_serial_transport(self) -> bool:
        return self.current_transport().lower().startswith("serial")

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
        """Модальный диалог параметров соединения (⚙ на панели)."""
        self.settingsClicked.emit()
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

    # ===== кнопка подключения =====
    @qasync.asyncSlot()
    async def _on_btn_clicked(self) -> None:
        # Уведомляем внешних наблюдателей (панель сама выполняет действие)
        self.connectToggled.emit(not self._connected)
        if self._connected:
            await self.disconnect_clicked()
        else:
            await self.connect_clicked()

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
                        address=self.DDII_SWITCH_MODE, values=self.SILENT_MODE, slave=self.cm_id
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
        # serial_log_enabled передаём явно обеим командам: их конструкторы дёргают
        # глобальный set_serial_log_enabled, и без этого TX/RX-дамп в терминале
        # включался бы или нет в зависимости от того, какая команда создана последней.
        slog = self.serial_log_enabled
        cm = ModbusCMCommand(cm_cli, logger, serial_log_enabled=slog)
        # CM_ID — константа ModbusVar; подменяем на экземпляре адресом из настроек
        cm.CM_ID = self.cm_id
        try:
            mpp = ModbusMPPCommand(mpp_cli, logger, self.mpp_id, serial_log_enabled=slog)
        except Exception:
            mpp = ModbusMPPCommand(mpp_cli, logger, serial_log_enabled=slog)
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
    import sys

    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget

    from dark_pro_widgets import qss

    from app.src.components.log.config import log_init

    app = QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())  # тема ddii (как в приложении)

    # хост-окно: бар прижат к низу, как в реальном приложении (ТЗ §8)
    host = QWidget()
    host.setWindowTitle("ConnectionBar — автономный запуск")
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addStretch()

    bar = ConnectionBar(log_init())
    layout.addWidget(bar)

    host.resize(960, 240)
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
