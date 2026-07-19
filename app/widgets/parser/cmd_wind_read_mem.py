from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import qasync
from PyQt6 import QtCore, QtWidgets
from qtpy.uic import loadUi


from app.plugins.connection.connection_bar import ConnectionBar
from app.src.components.modbus.ddii_command import ModbusCMCommand
from app.src.components.log.print_logger import PrintLogger
from app.widgets.parser.parse_table import DDIIFrameParser


class CmdWindReadMemWidget(QtWidgets.QWidget):
    """
    Виджет для чтения кадра из памяти ЦМ.

    Логика:
    - по нажатию на pushButton_read_frame читает указатель из lineEdit_read_ptr;
    - отправляет команду write_mem_ptr(rad_ptr);
    - через 0.5 c вызывает read_mem();
    - по получению кадра эмитит сигнал frame_received(bytes) и передаёт кадр в парсер.
    """

    pushButton_read_frame: QtWidgets.QPushButton
    lineEdit_read_ptr: QtWidgets.QLineEdit

    # Сигнал с "сырым" кадром (как вернул Modbus)
    frame_received = QtCore.pyqtSignal(bytes)

    def __init__(self, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath("cmd_wind_read_mem.ui"), self)

        self._parent: Optional[object] = args[0] if args else None
        self.logger = getattr(self._parent, "logger", PrintLogger())
        self.w_ser_dialog: Optional[ConnectionBar] = getattr(self._parent, "w_ser_dialog", None)
        self.cm_cmd: Optional[ModbusCMCommand] = None
        self.read_delay: float = 0.5  # задержка перед чтением кадра, с

        # Парсер кадра ДДИИ
        self._frame_parser = DDIIFrameParser()

        # Подписка на сигнал получения кадра
        self.frame_received.connect(self._on_frame_received)

        # Инициализация интерфейса Modbus после подключения
        if self.w_ser_dialog is not None:
            try:
                self.w_ser_dialog.coroutine_finished.connect(self.init_mb_cmd)
            except Exception:
                ...

        # Обработчик кнопки
        self.pushButton_read_frame.clicked.connect(self._on_read_frame_clicked)

    @qasync.asyncSlot()
    async def init_mb_cmd(self) -> None:
        """Инициализирует интерфейс команд ЦМ после установления соединения."""
        if self.w_ser_dialog is None:
            return
        try:
            ok = await self.w_ser_dialog.check_connection(only_cm=True, only_mpp=False)
        except Exception as e:
            self.logger.error(f"Ошибка проверки соединения: {e}")
            return
        if not ok:
            self.logger.error("Нет подключения к ЦМ")
            return
        try:
            self.cm_cmd, _mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)
        except Exception as e:
            self.logger.error(f"Не удалось получить интерфейс команд: {e}")
            self.cm_cmd = None

    def _parse_ptr(self, text: str) -> Optional[int]:
        """Парсит указатель чтения из строки (поддержка 10/16-ричных форматов)."""
        s = text.strip()
        if not s:
            return None
        try:
            # int(x, 0) позволяет использовать '123', '0x7B', '0X7B'
            return int(s, 0)
        except ValueError:
            return None

    @QtCore.pyqtSlot()
    def _on_read_frame_clicked(self) -> None:
        """
        Обёртка над асинхронным обработчиком, запускаемая из Qt-сигнала.
        Используем qasync для корректного запуска корутины.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # Если цикла нет (редкий случай), просто выходим
            self.logger.error("Event loop не инициализирован")
            return
        asyncio.ensure_future(self._read_frame_sequence(), loop=loop)

    @qasync.asyncSlot()
    async def _read_frame_sequence(self) -> None:
        """
        Основная асинхронная последовательность:
        write_mem_ptr -> sleep(0.5) -> read_mem -> emit frame_received.
        """
        if self.cm_cmd is None and self.w_ser_dialog is not None:
            await self.init_mb_cmd()

        if self.cm_cmd is None:
            self.logger.error("Интерфейс команд ЦМ не инициализирован")
            return

        ptr_text = self.lineEdit_read_ptr.text()
        rad_ptr = self._parse_ptr(ptr_text)
        if rad_ptr is None:
            self.logger.error(f"Неверный указатель чтения: '{ptr_text}'")
            return

        try:
            await self.cm_cmd.write_mem_ptr(rad_ptr)
        except Exception as e:
            self.logger.error(f"Ошибка write_mem_ptr({rad_ptr}): {e}")
            return

        await asyncio.sleep(self.read_delay)

        try:
            raw_frame: bytes = await self.cm_cmd.read_mem()
        except Exception as e:
            self.logger.error(f"Ошибка read_mem(): {e}")
            return

        if not isinstance(raw_frame, (bytes, bytearray)) or raw_frame == b"-1":
            self.logger.error("Не удалось получить корректный кадр")
            return

        self.frame_received.emit(bytes(raw_frame))

    @QtCore.pyqtSlot(bytes)
    def _on_frame_received(self, frame: bytes) -> None:
        """
        Обработчик полученного кадра:
        - парсит кадр через DDIIFrameParser;
        - выводит результат в консоль в виде таблицы (tabulate).
        """
        try:
            self._frame_parser.parse_and_print(frame)
        except Exception as e:
            self.logger.error(f"Ошибка парсинга кадра: {e}")


__all__ = ["CmdWindReadMemWidget"]

