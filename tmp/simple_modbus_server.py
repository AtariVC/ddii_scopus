#!/usr/bin/env python3
"""
Простой пример Modbus TCP сервера
Для быстрого тестирования и понимания основ
"""

import logging

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartTcpServer

# Настройка логирования
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def run_server():
    """Запуск простого Modbus TCP сервера"""

    # Создаем блоки данных
    # Holding Registers (16-bit) - адреса 0-99
    hr_data = [i * 10 for i in range(100)]  # 0, 10, 20, 30, ...
    hr_block = ModbusSequentialDataBlock(0, hr_data)

    # Coils (1-bit) - адреса 0-99
    co_data = [i % 2 == 0 for i in range(100)]  # True, False, True, False, ...
    co_block = ModbusSequentialDataBlock(0, co_data)

    # Input Registers (16-bit) - адреса 0-99
    ir_data = [i * 100 for i in range(100)]  # 0, 100, 200, 300, ...
    ir_block = ModbusSequentialDataBlock(0, ir_data)

    # Discrete Inputs (1-bit) - адреса 0-99
    di_data = [i % 3 == 0 for i in range(100)]  # True, False, False, True, ...
    di_block = ModbusSequentialDataBlock(0, di_data)

    # Создаем контекст для одного устройства
    slave_context = ModbusSlaveContext(
        di=di_block,  # Discrete Inputs
        co=co_block,  # Coils
        hr=hr_block,  # Holding Registers
        ir=ir_block,  # Input Registers
        zero_mode=True,  # Адресация начинается с 0
    )

    # Создаем серверный контекст
    context = ModbusServerContext(slaves=slave_context, single=True)

    logger.info("Запуск Modbus TCP сервера на localhost:5020")
    logger.info("Доступные данные:")
    logger.info(f"  Holding Registers (0-99): {hr_data[:10]}...")
    logger.info(f"  Coils (0-99): {co_data[:10]}...")
    logger.info(f"  Input Registers (0-99): {ir_data[:10]}...")
    logger.info(f"  Discrete Inputs (0-99): {di_data[:10]}...")
    logger.info("Для остановки нажмите Ctrl+C")

    # Запускаем сервер
    StartTcpServer(context=context, address=("localhost", 5020))


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        logger.info("Сервер остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
