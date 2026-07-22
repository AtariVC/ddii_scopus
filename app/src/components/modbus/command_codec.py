from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, Optional, ParamSpec, overload

from pymodbus.pdu import ModbusResponse

from app.src.components.log.config import log_s


class ModbusCommandError(Exception):
    pass


P = ParamSpec("P")

# Декоратор объявляет то, что реально делает: команда возвращает ModbusResponse,
# а обёртка кодирует его в bytes (см. wrapper ниже).
_Command = Callable[P, Awaitable[ModbusResponse]]
_Encoded = Callable[P, Awaitable[bytes]]


@overload
def mb_encode(func: _Command[P]) -> _Encoded[P]: ...


@overload
def mb_encode(*, serial_log: Optional[bool] = None) -> Callable[[_Command[P]], _Encoded[P]]: ...


def mb_encode(func: Optional[Callable[..., Any]] = None, *, serial_log: Optional[bool] = None):
    def decorator(command: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(command)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> bytes:
            try:
                response = await command(self, *args, **kwargs)
                _validate_response(response)
                if _serial_log_enabled(self, serial_log):
                    await log_s(self.mw.send_handler.mess)
                return _encode_payload(response)
            except Exception as ex:
                _log_modbus_error(self, command.__name__, ex)
                return b"-1"

        return wrapper  # type: ignore[return-value]

    if func is not None:
        return decorator(func)
    return decorator


def _validate_response(response: ModbusResponse) -> None:
    if response is None:
        raise ModbusCommandError("пустой ответ")
    if hasattr(response, "isError") and response.isError():
        raise ModbusCommandError(str(response))


def _encode_payload(response: ModbusResponse) -> bytes:
    return response.encode()[1:]


def _serial_log_enabled(command_owner: Any, override: Optional[bool]) -> bool:
    if override is not None:
        return override
    return bool(getattr(command_owner, "serial_log_enabled", True))


def _log_modbus_error(command_owner: Any, command_name: str, error: Exception) -> None:
    logger = getattr(command_owner, "logger", None)
    if logger is None:
        return
    device_name = getattr(command_owner, "device_name", "Modbus")
    logger.error(f"{device_name}: {command_name}: {_format_error_message(error)}")


def _format_error_message(error: Exception) -> str:
    message = str(error).strip()
    if not message:
        return error.__class__.__name__
    return message
