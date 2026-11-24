from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec

from pymodbus.pdu import ModbusResponse


class ModbusCommandError(Exception):
    pass


class ConnectionClosedError(Exception):
    """Сессия уже закрыта; причина сообщена владельцем подключения."""


P = ParamSpec("P")

# Декоратор объявляет то, что реально делает: команда возвращает ModbusResponse,
# а обёртка кодирует его в bytes (см. wrapper ниже).
_Command = Callable[P, Awaitable[ModbusResponse]]
_Encoded = Callable[P, Awaitable[bytes]]


def mb_encode(command: _Command[P]) -> _Encoded[P]:
    @wraps(command)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> bytes:
        try:
            response = await command(self, *args, **kwargs)
            _validate_response(response)
            return _encode_payload(response)
        except ConnectionClosedError:
            return b"-1"
        except Exception as ex:
            _log_modbus_error(self, command.__name__, ex)
            return b"-1"

    return wrapper  # type: ignore[return-value]


def _validate_response(response: ModbusResponse) -> None:
    if response is None:
        raise ModbusCommandError("пустой ответ")
    if hasattr(response, "isError") and response.isError():
        raise ModbusCommandError(str(response))


def _encode_payload(response: ModbusResponse) -> bytes:
    return response.encode()[1:]


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
