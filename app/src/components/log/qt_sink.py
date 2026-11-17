"""ConsoleLogSink — дополнительный приёмник Loguru для Qt, без изменения log_init.

API:
* ``ConsoleLogSink(logger, parent=None, max_entries=1000, streams=None)``.
* ``levels()`` — уровни, пропускаемые обработчиками stdout/stderr.
* ``flush()`` — передать накопленные записи в GUI; автоматически каждые 100 мс.
* ``close()`` — отключить только этот приёмник.
Signals: ``entriesReady(list)`` · ``levelsChanged(tuple)``.

У Loguru нет публичного API чтения конфигурации: доступ к _core и обработчикам
изолирован здесь. Рабочие потоки пишут только в ограниченную очередь, не в Qt.
"""

import sys
from collections import deque
from threading import Lock

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication


def _remove_handler(logger, handler_id: int) -> None:
    try:
        logger.remove(handler_id)
    except ValueError:  # обработчик уже удалён при закрытии или перенастройке лога
        pass


class ConsoleLogSink(QObject):
    """Передаёт консольные записи Loguru в главный поток Qt пакетами."""

    entriesReady = pyqtSignal(list)
    levelsChanged = pyqtSignal(tuple)

    def __init__(self, logger, parent=None, max_entries: int = 1000, streams=None) -> None:
        super().__init__(parent)
        self._logger = logger
        self._streams = tuple(streams) if streams is not None else (sys.stdout, sys.stderr)
        self._pending = deque(maxlen=max(1, max_entries))
        self._lock = Lock()
        self._seen_levels: set[str] = set()
        self._levels: tuple[str, ...] = ()
        self._handler_id = logger.add(self._write, level=0, format="{message}",
                                      colorize=False, backtrace=False, diagnose=False)
        handler_id = self._handler_id
        self.destroyed.connect(lambda: _remove_handler(logger, handler_id))
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self.flush)
        self._timer.start()
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.close)
        self.flush()

    def _console_handlers(self) -> tuple:
        return tuple(handler for handler in tuple(self._logger._core.handlers.values())
                     if any(getattr(handler._sink, "_stream", None) is stream
                            for stream in self._streams))

    @staticmethod
    def _accepts(handler, record: dict) -> bool:
        if record["level"].no < handler._levelno:
            return False
        try:
            return handler._filter is None or bool(handler._filter(record))
        except (KeyError, AttributeError, TypeError):
            # Фильтр может требовать дополнительные поля: узнаем уровень
            # по реальной записи, а не по пробе конфигурации.
            return False

    def _write(self, message) -> None:
        record = message.record
        if not any(self._accepts(handler, record) for handler in self._console_handlers()):
            return
        entry = (record["time"].strftime("%H:%M:%S"), record["level"].name, str(message).rstrip("\n"))
        with self._lock:
            self._pending.append(entry)
            self._seen_levels.add(record["level"].name)

    def levels(self) -> tuple[str, ...]:
        """Имена доступных консольных уровней, без сокращений."""
        return self._levels

    def flush(self) -> None:
        """Обновить уровни и передать очередь в GUI-потоке."""
        handlers = self._console_handlers()
        registered = tuple(self._logger._core.levels.values())
        with self._lock:
            levels = self._seen_levels.copy()
            entries = [self._pending.popleft() for _ in range(min(len(self._pending), 200))]
        levels.update(level.name for level in registered
                      if any(self._accepts(handler, {"level": level}) for handler in handlers))
        ordered = tuple(level.name for level in registered if level.name in levels)
        if ordered != self._levels:
            self._levels = ordered
            self.levelsChanged.emit(ordered)
        if entries:
            self.entriesReady.emit(entries)

    def close(self) -> None:
        """Удалить дополнительный обработчик; остальные приёмники не затрагиваются."""
        self._timer.stop()
        if self._handler_id is not None:
            _remove_handler(self._logger, self._handler_id)
            self._handler_id = None
