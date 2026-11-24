"""Консоль, файлы приложения и трассировка обмена PyModbus."""

import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from threading import Lock

from loguru import logger

MODBUS_TRACE_LEVELS = ("RX", "TX")

_initialized = False
_init_lock = Lock()
_modbus_capture: frozenset[str] = frozenset()
_hex_byte = re.compile(r"0x([0-9a-f]{1,2})", re.IGNORECASE)
# Обычная фрагментация TCP ("short frame", "missing part") остаётся вне журнала.
_modbus_debug_warnings = (
    "Frame check failed, ignoring",
    "Not a valid slave id",
    "Not in valid slave id",
    "Connection lost ",
    "Transaction failed.",
    "-> error_received ",
)


def modbus_capture_levels() -> frozenset[str]:
    """Вернуть включённые направления на время текущего запуска приложения."""
    return _modbus_capture


def set_modbus_capture_levels(levels: set[str]) -> None:
    """Записывать только выбранные направления обмена."""
    global _modbus_capture
    _modbus_capture = frozenset(levels).intersection(MODBUS_TRACE_LEVELS)


class _PyModbusHandler(logging.Handler):
    """Маршрутизирует сообщения PyModbus 3.6.8 в Loguru при их появлении."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
            if record.levelno == logging.DEBUG:
                prefix, _, payload = message.partition(":")
                direction = {"recv": "RX", "send": "TX"}.get(prefix.lower())
                if direction:
                    if direction in _modbus_capture:
                        data = payload.partition(" old_data:")[0]
                        hex_bytes = " ".join(byte.zfill(2).upper() for byte in _hex_byte.findall(data))
                        if hex_bytes:
                            logger.log(direction, hex_bytes)
                    return

            level = record.levelname
            if record.levelno < logging.INFO:
                if not message.startswith(_modbus_debug_warnings):
                    return
                level = "WARNING"
            logger.opt(exception=record.exc_info).log(level, "PyModbus: {}", message)
        except Exception:
            self.handleError(record)


def log_init():
    """Один раз настроить обработчики и вернуть общий логгер."""
    global _initialized
    with _init_lock:
        if _initialized:
            return logger

        logger.remove()
        logger.level("RX", no=0, color="<magenta>", icon="")
        logger.level("TX", no=0, color="<green>", icon="")

        filename = datetime.now().strftime("%Y-%m-%d %H_%M_%S.log")
        log_dir = Path.cwd() / "log"
        format_events = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <4}</level> | "
            "<yellow>{file}:{line}</yellow> | <w>{message}</w>"
        )
        format_trace = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}"

        logger.add(sys.stderr, level="DEBUG", format=format_events, colorize=True)
        logger.add(log_dir / "debug" / filename, level="DEBUG", format=format_events,
                   rotation="100 MB", enqueue=True, encoding="utf-8")
        logger.add(log_dir / "serial" / filename, level=0, format=format_trace,
                   rotation="100 MB", enqueue=True, delay=True, encoding="utf-8",
                   filter=lambda record: record["level"].name in _modbus_capture)

        pymodbus_logger = logging.getLogger("pymodbus")
        pymodbus_logger.setLevel(logging.DEBUG)
        pymodbus_logger.propagate = False
        pymodbus_logger.addHandler(_PyModbusHandler())
        _initialized = True
        return logger


def get_logger(name: str | None = None):
    """Получить общий логгер."""
    return logger if _initialized else log_init()
