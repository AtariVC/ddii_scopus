#!/usr/bin/env python3
"""
Простой синхронный клиент для быстрого тестирования Modbus сервера
"""

from pymodbus.client import ModbusTcpClient


def test_server():
    """Быстрое тестирование сервера"""
    print("Тестирование Modbus сервера на localhost:5020...")

    # Создаем клиент
    client = ModbusTcpClient("localhost", 5020)

    try:
        # Подключаемся к серверу
        if client.connect():
            print("✓ Подключение успешно")

            # Тестируем чтение holding registers
            result = client.read_holding_registers(0, 5)
            if result.isError():
                print(f"✗ Ошибка чтения holding registers: {result}")
            else:
                print(f"✓ Holding Registers 0-4: {result.registers}")

            # Тестируем чтение coils
            result = client.read_coils(0, 8)
            if result.isError():
                print(f"✗ Ошибка чтения coils: {result}")
            else:
                print(f"✓ Coils 0-7: {result.bits}")

            # Тестируем чтение input registers
            result = client.read_input_registers(0, 5)
            if result.isError():
                print(f"✗ Ошибка чтения input registers: {result}")
            else:
                print(f"✓ Input Registers 0-4: {result.registers}")

            # Тестируем запись в holding register
            result = client.write_register(10, 9999)
            if result.isError():
                print(f"✗ Ошибка записи в register 10: {result}")
            else:
                print("✓ Записано значение 9999 в register 10")

                # Проверяем записанное значение
                result = client.read_holding_registers(10, 1)
                if result.isError():
                    print(f"✗ Ошибка чтения register 10: {result}")
                else:
                    print(f"✓ Register 10 содержит: {result.registers[0]}")

            # Тестируем запись в coil
            result = client.write_coil(20, True)
            if result.isError():
                print(f"✗ Ошибка записи в coil 20: {result}")
            else:
                print("✓ Записано значение True в coil 20")

                # Проверяем записанное значение
                result = client.read_coils(20, 1)
                if result.isError():
                    print(f"✗ Ошибка чтения coil 20: {result}")
                else:
                    print(f"✓ Coil 20 содержит: {result.bits[0]}")

        else:
            print("✗ Не удалось подключиться к серверу")

    except Exception as e:
        print(f"✗ Ошибка: {e}")

    finally:
        client.close()
        print("Клиент отключен")


if __name__ == "__main__":
    test_server()
