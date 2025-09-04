#!/usr/bin/env python3
"""
Простой пример Modbus TCP сервера с логированием запросов
"""

import logging
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification

# Настройка логирования
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomDataBlock(ModbusSequentialDataBlock):
    """Кастомный блок данных с логированием записей"""
    
    def setValues(self, address, values):
        """Переопределяем метод записи для логирования"""
        logger.info(f"📝 ЗАПИСЬ: тип=Holding Register, адрес={address}, значения={values}")
        return super().setValues(address, values)


class CustomCoilDataBlock(ModbusSequentialDataBlock):
    """Кастомный блок данных для Coils с логированием"""
    
    def setValues(self, address, values):
        logger.info(f"📝 ЗАПИСЬ: тип=Coil, адрес={address}, значения={values}")
        return super().setValues(address, values)


class CustomSlaveContext(ModbusSlaveContext):
    """Кастомный контекст с логированием всех операций"""
    
    def validate(self, fx, address, count=1):
        """Логируем все операции чтения/записи"""
        result = super().validate(fx, address, count)
        
        # Определяем тип операции
        op_type = "ЧТЕНИЕ"
        if fx in [5, 6, 15, 16]:  # Коды функций записи
            op_type = "ЗАПИСЬ"
        
        # Определяем тип данных
        data_type = "Unknown"
        if fx in [1, 5, 15]:  # Coils
            data_type = "Coil"
        elif fx in [2]:  # Discrete Inputs
            data_type = "Discrete Input"
        elif fx in [3, 6, 16]:  # Holding Registers
            data_type = "Holding Register"
        elif fx in [4]:  # Input Registers
            data_type = "Input Register"
        
        logger.info(f"🔍 ОПЕРАЦИЯ: {op_type}, тип={data_type}, функция={fx}, адрес={address}, количество={count}")
        return result


def run_server():
    """Запуск Modbus TCP сервера с логированием запросов"""

    # Создаем блоки данных с кастомными классами для логирования записи
    hr_data = [i * 10 for i in range(100)]
    hr_block = CustomDataBlock(0, hr_data)

    co_data = [i % 2 == 0 for i in range(100)]
    co_block = CustomCoilDataBlock(0, co_data)

    ir_data = [i * 100 for i in range(100)]
    ir_block = ModbusSequentialDataBlock(0, ir_data)

    di_data = [i % 3 == 0 for i in range(100)]
    di_block = ModbusSequentialDataBlock(0, di_data)

    # Создаем кастомный контекст с логированием
    slave_context = CustomSlaveContext(
        di=di_block,
        co=co_block,
        hr=hr_block,
        ir=ir_block,
        zero_mode=True,
    )

    # Создаем серверный контекст
    context = ModbusServerContext(slaves=slave_context, single=True)

    # Настраиваем идентификацию устройства
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'Custom Modbus Server'
    identity.ProductCode = 'PM'
    identity.VendorUrl = 'http://github.com/'
    identity.ProductName = 'Python Modbus Server'
    identity.ModelName = 'Python Modbus'
    identity.MajorMinorRevision = '1.0.0'

    logger.info("Запуск Modbus TCP сервера на localhost:5020")
    logger.info("Сервер будет логировать все входящие запросы")
    logger.info("Доступные данные:")
    logger.info(f"  Holding Registers (0-99): {hr_data[:10]}...")
    logger.info(f"  Coils (0-99): {co_data[:10]}...")
    logger.info(f"  Input Registers (0-99): {ir_data[:10]}...")
    logger.info(f"  Discrete Inputs (0-99): {di_data[:10]}...")
    logger.info("Для остановки нажмите Ctrl+C")

    # Запускаем сервер
    StartTcpServer(
        context=context,
        address=("localhost", 5020),
        identity=identity,
    )


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        logger.info("Сервер остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка: {e}")