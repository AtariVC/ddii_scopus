"""Relay-сервер Modbus TCP → Serial.

Самостоятельная бэкенд-подсистема (без Qt/UI): поднимает Modbus TCP сервер,
чьи регистры проксируются в подключённый serial-клиент, плюс служебная область
HR[80..] для идентификации подключающихся клиентов. Вынесена из
``connection_bar.py`` по правилу «разделение классов на модули» (docs/
widget_conventions.md §6): не зависит от виджета и используется только через
``ConnectionBar.start_tcp_server`` / ``stop_tcp_server``.

Мини-модель ``ProxySequentialDataBlock`` оставлена вложенной: она существует
исключительно внутри этого сервера и наружу не переиспользуется.
"""
from __future__ import annotations

import asyncio

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartAsyncTcpServer

from app.src.components.log.config import get_logger


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
