"""FrameViewerWidget — системный кадр и кадр ДДИИ с независимым опросом.

API:
* ``FrameViewerWidget(client=None, parent=None)`` — две карточки без истории.
* ``table(key)`` — карточка ``'system'`` / ``'ddii'``.
* ``push_frame(key, raw)`` — разобрать кадр и заменить отображаемые значения.
* ``stop_polling()`` — остановить чтение обеих карточек.
Опрос запускается кнопкой обновления, непрерывный режим выбирается кнопкой повтора.
Все задачи привязаны к подключению ЦМ через ConnectionBar.bind_device.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from loguru import logger
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QScrollArea, QWidget
from qtpy.uic import loadUi

from dark_pro_widgets import theme

from app.src.components.frames.stream_frames import FRAME_SIZE, parse_stream_frame
from app.src.components.modbus.command_interface import ModbusCMCommand
from app.src.util.async_task_manager import AsyncTaskManager
from app.widgets.controls.frame_table import FrameTable


@dataclass(frozen=True)
class FrameConfig:
    """Описание карточки и метода чтения кадра у ЦМ."""

    key: str
    title: str
    dot: str
    reader: str


_FRAMES = (
    FrameConfig("system", "Системный кадр", theme.ACCENT, "read_system_frame"),
    FrameConfig("ddii", "Кадр ДДИИ", theme.OK, "read_ddii_frame"),
)


class FrameViewerWidget(QWidget):
    """Две таблицы с разовым чтением и независимым непрерывным опросом."""

    layout_frames: QHBoxLayout
    scroll_frames: QScrollArea
    widget_frames: QWidget

    def __init__(self, client=None, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.cm_ib: ModbusCMCommand | None = None
        self.logger = logger
        self._tasks = AsyncTaskManager()
        self._tables: dict[str, FrameTable] = {}
        self._build_widget()
        self._wire_connection()

    def _build_widget(self) -> None:
        loadUi(Path(__file__).with_suffix(".ui"), self)
        self.scroll_frames.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll_frames.viewport().setStyleSheet("background: transparent;")
        self.widget_frames.setStyleSheet("background: transparent;")
        for cfg in _FRAMES:
            table = FrameTable(cfg.title, cfg.dot)
            table.refreshRequested.connect(partial(self._request_frame, cfg))
            table.stopRequested.connect(partial(self._stop_frame, cfg.key))
            table.set_available(False)
            self._tables[cfg.key] = table
            self.layout_frames.addWidget(table, 1, Qt.AlignmentFlag.AlignTop)

    def _wire_connection(self) -> None:
        if self.client is not None:
            self._connection = self.client.bind_device(
                self, "cm", self._tasks, self._on_device_ready, self._on_disconnected,
            )

    def _on_device_ready(self, command: ModbusCMCommand) -> None:
        self.cm_ib = command
        for table in self._tables.values():
            table.set_available(True)

    def _on_disconnected(self) -> None:
        self.cm_ib = None
        self.stop_polling()
        for table in self._tables.values():
            table.set_available(False)

    def _request_frame(self, cfg: FrameConfig, continuous: bool, interval: int) -> None:
        if self.cm_ib is None:
            self._tables[cfg.key].set_polling(False)
            return
        name = f"frame_{cfg.key}"
        task = self._tasks.tasks.get(name)
        if task is not None and not task.done() and not task.cancelling():
            if not continuous:
                return
            self._tasks.cancel_task(name)
        self._tasks.create_task(self._read_frames(cfg, continuous, interval), name)

    async def _read_frames(self, cfg: FrameConfig, continuous: bool, interval: int) -> None:
        """Читать сразу, затем с заданным периодом, пока пользователь не остановит."""
        try:
            while self.cm_ib is not None:
                raw = await getattr(self.cm_ib, cfg.reader)()
                if raw == b"-1":
                    return
                self.push_frame(cfg.key, raw)
                if not continuous:
                    return
                await asyncio.sleep(interval)
        finally:
            if self._tasks.tasks.get(f"frame_{cfg.key}") is asyncio.current_task():
                self._tables[cfg.key].set_polling(False)

    def _stop_frame(self, key: str) -> None:
        name = f"frame_{key}"
        if name in self._tasks.tasks:
            self._tasks.cancel_task(name)
        self._tables[key].set_polling(False)

    def stop_polling(self) -> None:
        """Остановить все запросы просмотрщика и сбросить обе кнопки."""
        self._tasks.cancel_all_tasks()
        for table in self._tables.values():
            table.set_polling(False)

    def push_frame(self, key: str, raw: bytes) -> None:
        """Показать последний кадр, не сохраняя предыдущие."""
        table = self._tables[key]
        try:
            parsed = parse_stream_frame(key, raw)
        except Exception as error:  # битый кадр не должен ронять опрос
            self.logger.debug(f"Кадр '{key}' не разобран: {error}")
            return
        table.set_dataframe(parsed)

    def table(self, key: str) -> FrameTable | None:
        """Карточка по ключу 'system' / 'ddii' или None."""
        return self._tables.get(key)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.stop_polling()
        super().closeEvent(event)


if __name__ == "__main__":
    import sys

    import qasync
    from PyQt6.QtWidgets import QApplication

    from dark_pro_widgets import qss

    class DemoCommand:
        """Синтетические ответы для проверки обеих кнопок без прибора."""

        async def read_system_frame(self) -> bytes:
            await asyncio.sleep(0.1)
            return bytes(FRAME_SIZE)

        read_ddii_frame = read_system_frame

    app = QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())
    viewer = FrameViewerWidget()
    viewer._on_device_ready(DemoCommand())
    viewer.setWindowTitle("Просмотрщик кадров")
    viewer.setStyleSheet(f"background-color: {theme.BG};")
    viewer.resize(1150, 760)
    theme.tint_window_board(int(viewer.winId()))
    viewer.show()

    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    with event_loop:
        event_loop.run_forever()
