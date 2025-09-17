#!/usr/bin/env python3
"""
Простой Modbus TCP клиент для тестирования сервера
"""

from pymodbus.client import ModbusTcpClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_modbus_server():
    """Тестирование Modbus сервера"""
    
    client = ModbusTcpClient('localhost', port=5020)
    
    try:
        # Подключаемся к серверу
        connection = client.connect()
        if connection:
            logger.info("✅ Подключение к серверу установлено")
            
            # Чтение Holding Registers (аналог: modbus read localhost 5020 0 10)
            result = client.read_holding_registers(address=0, count=10, slave=1)
            if not result.isError():
                logger.info(f"📖 Holding Registers 0-9: {result.registers}")
            else:
                logger.error("Ошибка чтения регистров")
                
            # Чтение Coils
            result = client.read_coils(address=0, count=10, slave=1)
            if not result.isError():
                logger.info(f"📖 Coils 0-9: {result.bits}")
            else:
                logger.error("Ошибка чтения катушек")
                
            # Запись в регистр (аналог: modbus write localhost 5020 5 999)
            client.write_registers(address=14, values=[0x01, 0x12], slave=1)
            logger.info("📝 Записано значение 999 в регистр 5")
            
            # Проверяем запись
            result = client.read_holding_registers(address=5, count=1, slave=1)
            if not result.isError():
                logger.info(f"✅ Проверка: регистр 5 = {result.registers[0]}")
                
        else:
            logger.error("❌ Не удалось подключиться к серверу")
            
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        client.close()
        logger.info("🔌 Отключение от сервера")

if __name__ == "__main__":
    test_modbus_server()