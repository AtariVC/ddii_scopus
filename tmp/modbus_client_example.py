#!/usr/bin/env python3
"""
Пример Modbus клиента для тестирования сервера
Демонстрирует различные операции чтения и записи
"""

import asyncio
import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

# Настройка логирования
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


class ModbusTestClient:
    """Клиент для тестирования Modbus сервера"""

    def __init__(self, host: str = "localhost", port: int = 5020):
        self.host = host
        self.port = port
        self.client = AsyncModbusTcpClient(host, port)

    async def connect(self) -> bool:
        """Подключение к серверу"""
        try:
            connected = await self.client.connect()
            if connected:
                logger.info(f"Подключен к {self.host}:{self.port}")
                return True
            else:
                logger.error("Не удалось подключиться к серверу")
                return False
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False

    async def disconnect(self):
        """Отключение от сервера"""
        await self.client.close()
        logger.info("Отключен от сервера")

    async def test_holding_registers(self):
        """Тестирование Holding Registers"""
        logger.info("=== Тестирование Holding Registers ===")

        try:
            # Чтение одного регистра
            result = await self.client.read_holding_registers(0, 1)
            if result.isError():
                logger.error(f"Ошибка чтения: {result}")
            else:
                logger.info(f"Holding Register 0: {result.registers[0]}")

            # Чтение нескольких регистров
            result = await self.client.read_holding_registers(0, 5)
            if result.isError():
                logger.error(f"Ошибка чтения: {result}")
            else:
                logger.info(f"Holding Registers 0-4: {result.registers}")

            # Запись в регистр
            result = await self.client.write_register(10, 9999)
            if result.isError():
                logger.error(f"Ошибка записи: {result}")
            else:
                logger.info("Записано значение 9999 в Holding Register 10")

            # Проверяем записанное значение
            result = await self.client.read_holding_registers(10, 1)
            if result.isError():
                logger.error(f"Ошибка чтения: {result}")
            else:
                logger.info(f"Holding Register 10 после записи: {result.registers[0]}")

        except Exception as e:
            logger.error(f"Ошибка тестирования Holding Registers: {e}")

    async def test_coils(self):
        """Тестирование Coils"""
        logger.info("=== Тестирование Coils ===")

        try:
            # Чтение одного coil
            result = await self.client.read_coils(0, 1)
            if result.isError():
                logger.error(f"Ошибка чтения: {result}")
            else:
                logger.info(f"Coil 0: {result.bits[0]}")

            # Чтение нескольких coils
            result = await self.client.read_coils(0, 8)
            if result.isError():
                logger.error(f"Ошибка чтения: {result}")
            else:
                logger.info(f"Coils 0-7: {result.bits}")

            # Запись в coil
            result = await self.client.write_coil(20, True)
            if result.isError():
                logger.error(f"Ошибка записи: {result}")
            else:
                logger.info("Записано значение True в Coil 20")

            # Проверяем записанное значение
            result = await self.client.read_coils(20, 1)
            if result.isError():
                logger.error(f"Ошибка чтения: {result}")
            else:
                logger.info(f"Coil 20 после записи: {result.bits[0]}")

        except Exception as e:
            logger.error(f"Ошибка тестирования Coils: {e}")

    async def test_input_registers(self):
        """Тестирование Input Registers"""
        logger.info("=== Тестирование Input Registers ===")

        try:
            # Чтение одного регистра
            result = await self.client.read_input_registers(0, 1)
            if result.isError():
                logger.error(f"Ошибка чтения: {result}")
            else:
                logger.info(f"Input Register 0: {result.registers[0]}")

            # Чтение нескольких регистров
            result = await self.client.read_input_registers(0, 5)
            if result.isError():
                logger.error(f"Ошибка чтения: {result}")
            else:
                logger.info(f"Input Registers 0-4: {result.registers}")

        except Exception as e:
            logger.error(f"Ошибка тестирования Input Registers: {e}")

    async def test_discrete_inputs(self):
        """Тестирование Discrete Inputs"""
        logger.info("=== Тестирование Discrete Inputs ===")

        try:
            # Чтение одного discrete input
            result = await self.client.read_discrete_inputs(0, 1)
            if result.isError():
                logger.error(f"Ошибка чтения: {result}")
            else:
                logger.info(f"Discrete Input 0: {result.bits[0]}")

            # Чтение нескольких discrete inputs
            result = await self.client.read_discrete_inputs(0, 8)
            if result.isError():
                logger.error(f"Ошибка чтения: {result}")
            else:
                logger.info(f"Discrete Inputs 0-7: {result.bits}")

        except Exception as e:
            logger.error(f"Ошибка тестирования Discrete Inputs: {e}")

    async def run_all_tests(self):
        """Запуск всех тестов"""
        logger.info("Начало тестирования Modbus сервера")

        if not await self.connect():
            return

        try:
            await self.test_holding_registers()
            await asyncio.sleep(0.5)

            await self.test_coils()
            await asyncio.sleep(0.5)

            await self.test_input_registers()
            await asyncio.sleep(0.5)

            await self.test_discrete_inputs()

        finally:
            await self.disconnect()

        logger.info("Тестирование завершено")


async def main():
    """Основная функция"""
    client = ModbusTestClient()
    await client.run_all_tests()


if __name__ == "__main__":
    print("Запуск тестирования Modbus сервера...")
    print("Убедитесь, что сервер запущен на localhost:5020")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nТестирование прервано пользователем")
    except Exception as e:
        print(f"Ошибка: {e}")
