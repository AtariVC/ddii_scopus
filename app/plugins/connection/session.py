"""ConnectionSession — общий контроль запросов одного подключения Serial/TCP.

API: ``ConnectionSession(client, on_failure)`` · ``close()`` · ``active``.
Командные интерфейсы получают сессию вместо сырого клиента. Запросы идут
последовательно; ошибка транспорта закрывает сессию один раз. Старые команды
после переподключения больше не обращаются к прибору.
"""

import asyncio
from functools import partial

from pymodbus.exceptions import ConnectionException, ModbusIOException

from app.src.components.modbus.command_codec import ConnectionClosedError


class ConnectionSession:
    """Сессия запросов с отменой выполняющегося I/O при потере связи."""

    def __init__(self, client, on_failure) -> None:
        self.client = client
        self.active = True
        self._on_failure = on_failure
        self._lock = asyncio.Lock()
        self._requests: set[asyncio.Future] = set()
        self._disconnected = getattr(client, "callback_disconnected", None)
        if self._disconnected is not None:
            client.callback_disconnected = self._transport_lost

    def __getattr__(self, name: str):
        if name.startswith(("read_", "write_")):
            return partial(self._request, name)
        return getattr(self.client, name)

    def _ensure_active(self) -> None:
        if not self.active:
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                raise asyncio.CancelledError
            raise ConnectionClosedError("Сессия подключения закрыта")

    async def _request(self, method: str, *args, **kwargs):
        self._ensure_active()
        async with self._lock:
            self._ensure_active()
            request = None
            try:
                request = asyncio.ensure_future(getattr(self.client, method)(*args, **kwargs))
                self._requests.add(request)
                response = await request
                self._ensure_active()
                if response is None:
                    raise ModbusIOException("Устройство не ответило")
                if isinstance(response, (ConnectionException, ModbusIOException)):
                    raise response
                if getattr(response, "exception_code", None) in (10, 11):
                    raise ConnectionException("Шлюз потерял связь с устройством")
                return response
            except asyncio.CancelledError:
                self._ensure_active()
                raise
            except (ConnectionException, ModbusIOException, OSError, TimeoutError) as error:
                slave = kwargs.get("slave", kwargs.get("unit", "—"))
                self.fail(f"Ошибка связи (id={slave}, {method}): {error}")
                self._ensure_active()
            finally:
                self._requests.discard(request)

    def _transport_lost(self, error) -> None:
        self._disconnected(error)
        self.fail(f"Соединение потеряно: {error or 'транспорт закрыт'}")

    def fail(self, reason: str) -> None:
        """Сообщить владельцу о первой ошибке сессии."""
        if self.active:
            self.close()
            self._on_failure(self, reason)

    def close(self) -> None:
        """Запретить новые запросы и отменить выполняющийся обмен."""
        if not self.active:
            return
        self.active = False
        if self._disconnected is not None:
            self.client.callback_disconnected = self._disconnected
        for request in tuple(self._requests):
            request.cancel()
