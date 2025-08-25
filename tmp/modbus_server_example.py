#!/usr/bin/env python3
"""
Пример использования сервера PyModbus
Демонстрирует создание Modbus TCP и Serial серверов с различными типами регистров
"""

import asyncio
import logging
from typing import Any, Dict

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.framer import ModbusAsciiFramer, ModbusRtuFramer
from pymodbus.server import StartAsyncSerialServer, StartAsyncTcpServer

# Настройка логирования
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomModbusServer:
    """Кастомный Modbus сервер с расширенной функциональностью"""

    def __init__(self):
        self.context = None
        self.server = None

    def setup_datastore(self) -> ModbusServerContext:
        """Настройка хранилища данных для сервера"""

        # Создаем блоки данных для различных типов регистров
        # Holding Registers (16-bit) - адреса 0-9999
        hr_block = ModbusSequentialDataBlock(0, [0] * 10000)

        # Input Registers (16-bit) - адреса 30000-39999
        ir_block = ModbusSequentialDataBlock(0, [0] * 10000)

        # Coils (1-bit) - адреса 00001-09999
        co_block = ModbusSequentialDataBlock(0, [False] * 10000)

        # Discrete Inputs (1-bit) - адреса 10001-19999
        di_block = ModbusSequentialDataBlock(0, [False] * 10000)

        # Создаем контекст для одного устройства (slave)
        slave_context = ModbusSlaveContext(
            di=di_block,  # Discrete Inputs
            co=co_block,  # Coils
            hr=hr_block,  # Holding Registers
            ir=ir_block,  # Input Registers
            zero_mode=True,  # Адресация начинается с 0
        )

        # Создаем серверный контекст
        context = ModbusServerContext(slaves=slave_context, single=True)

        return context

    async def start_tcp_server(self, host: str = "localhost", port: int = 502):
        """Запуск TCP сервера"""
        logger.info(f"Запуск TCP сервера на {host}:{port}")

        self.context = self.setup_datastore()

        # Запускаем TCP сервер
        self.server = await StartAsyncTcpServer(
            context=self.context,
            address=(host, port),
            allow_reuse_address=True,
            allow_reuse_port=True,
        )

        logger.info(f"TCP сервер запущен на {host}:{port}")

    async def start_serial_server(self, port: str = "/dev/ttyUSB0", baudrate: int = 9600):
        """Запуск Serial сервера (RTU)"""
        logger.info(f"Запуск Serial сервера на {port} с baudrate {baudrate}")

        self.context = self.setup_datastore()

        # Запускаем Serial сервер
        self.server = await StartAsyncSerialServer(
            context=self.context,
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            framer=ModbusRtuFramer,
        )

        logger.info(f"Serial сервер запущен на {port}")

    async def start_ascii_server(self, port: str = "/dev/ttyUSB0", baudrate: int = 9600):
        """Запуск ASCII сервера"""
        logger.info(f"Запуск ASCII сервера на {port} с baudrate {baudrate}")

        self.context = self.setup_datastore()

        # Запускаем ASCII сервер
        self.server = await StartAsyncSerialServer(
            context=self.context,
            port=port,
            baudrate=baudrate,
            bytesize=7,
            parity="E",
            stopbits=1,
            framer=ModbusAsciiFramer,
        )

        logger.info(f"ASCII сервер запущен на {port}")

    def update_holding_register(self, address: int, value: int, unit: int = 0):
        """Обновление holding register"""
        if self.context:
            self.context[unit].setValues(3, address, [value])  # 3 = holding registers
            logger.info(f"Обновлен holding register {address}: {value}")

    def update_coil(self, address: int, value: bool, unit: int = 0):
        """Обновление coil"""
        if self.context:
            self.context[unit].setValues(1, address, [value])  # 1 = coils
            logger.info(f"Обновлен coil {address}: {value}")

    def get_holding_register(self, address: int, unit: int = 0) -> int:
        """Получение значения holding register"""
        if self.context:
            values = self.context[unit].getValues(3, address, 1)  # 3 = holding registers
            return values[0] if values else 0
        return 0

    def get_coil(self, address: int, unit: int = 0) -> bool:
        """Получение значения coil"""
        if self.context:
            values = self.context[unit].getValues(1, address, 1)  # 1 = coils
            return values[0] if values else False
        return False

    async def simulate_data_changes(self):
        """Симуляция изменения данных для демонстрации"""
        import random
        import time

        logger.info("Запуск симуляции изменения данных...")

        while True:
            try:
                # Случайно обновляем holding registers
                for i in range(10):
                    addr = random.randint(0, 99)
                    value = random.randint(0, 65535)
                    self.update_holding_register(addr, value)

                # Случайно обновляем coils
                for i in range(5):
                    addr = random.randint(0, 99)
                    value = random.choice([True, False])
                    self.update_coil(addr, value)

                await asyncio.sleep(5)  # Обновляем каждые 5 секунд

            except Exception as e:
                logger.error(f"Ошибка в симуляции: {e}")
                break

    async def stop_server(self):
        """Остановка сервера"""
        if self.server:
            self.server.server_close()
            logger.info("Сервер остановлен")


async def main():
    """Основная функция для демонстрации"""

    # Создаем экземпляр сервера
    server = CustomModbusServer()

    try:
        # Запускаем TCP сервер
        await server.start_tcp_server(host="0.0.0.0", port=5020)

        # Запускаем симуляцию изменения данных в фоне
        simulation_task = asyncio.create_task(server.simulate_data_changes())

        # Демонстрируем работу с данными
        logger.info("Демонстрация работы сервера:")

        # Устанавливаем начальные значения
        server.update_holding_register(0, 12345)
        server.update_holding_register(1, 67890)
        server.update_coil(0, True)
        server.update_coil(1, False)

        # Читаем значения
        logger.info(f"Holding Register 0: {server.get_holding_register(0)}")
        logger.info(f"Holding Register 1: {server.get_holding_register(1)}")
        logger.info(f"Coil 0: {server.get_coil(0)}")
        logger.info(f"Coil 1: {server.get_coil(1)}")

        # Ждем завершения симуляции или прерывания
        try:
            await simulation_task
        except asyncio.CancelledError:
            logger.info("Симуляция прервана")

    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        await server.stop_server()


if __name__ == "__main__":
    print("Запуск Modbus сервера...")
    print("Для остановки нажмите Ctrl+C")
    print("Сервер будет доступен на localhost:5020")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nСервер остановлен пользователем")
    except Exception as e:
        print(f"Ошибка запуска: {e}")
