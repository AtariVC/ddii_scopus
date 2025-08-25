#!/usr/bin/env python3
"""
Пример интеграции Modbus сервера с существующим проектом
Показывает, как добавить Modbus сервер к существующему приложению
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем пути для импорта модулей проекта
src_path = Path(__file__).resolve().parent.parent / "src"
modules_path = Path(__file__).resolve().parent.parent / "modules"
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartAsyncTcpServer

# Настройка логирования
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegratedModbusServer:
    """Интегрированный Modbus сервер для проекта DDII"""

    def __init__(self):
        self.context = None
        self.server = None
        self.server_task = None

        # Данные для симуляции работы ДДИИ
        self.ddii_data = {
            "temperature": 25.0,
            "pressure": 1013.25,
            "humidity": 45.0,
            "status": 1,
            "error_code": 0,
            "battery_level": 95,
            "signal_strength": 85,
            "operation_mode": 1,
            "calibration_factor": 1.0,
            "measurement_count": 0,
        }

        # Флаги состояния
        self.system_flags = {
            "power_on": True,
            "calibration_mode": False,
            "maintenance_mode": False,
            "alarm_active": False,
            "data_logging": True,
            "remote_control": False,
            "sensor_ok": True,
            "communication_ok": True,
        }

    def setup_datastore(self) -> ModbusServerContext:
        """Настройка хранилища данных для ДДИИ"""

        # Holding Registers для основных параметров (адреса 0-99)
        hr_data = [0] * 100
        hr_data[0] = int(self.ddii_data["temperature"] * 100)  # Температура * 100
        hr_data[1] = int(self.ddii_data["pressure"] * 100)  # Давление * 100
        hr_data[2] = int(self.ddii_data["humidity"] * 100)  # Влажность * 100
        hr_data[3] = self.ddii_data["status"]  # Статус системы
        hr_data[4] = self.ddii_data["error_code"]  # Код ошибки
        hr_data[5] = self.ddii_data["battery_level"]  # Уровень батареи
        hr_data[6] = self.ddii_data["signal_strength"]  # Сила сигнала
        hr_data[7] = self.ddii_data["operation_mode"]  # Режим работы
        hr_data[8] = int(self.ddii_data["calibration_factor"] * 1000)  # Коэффициент калибровки
        hr_data[9] = self.ddii_data["measurement_count"]  # Счетчик измерений

        hr_block = ModbusSequentialDataBlock(0, hr_data)

        # Coils для флагов состояния (адреса 0-99)
        co_data = [False] * 100
        co_data[0] = self.system_flags["power_on"]
        co_data[1] = self.system_flags["calibration_mode"]
        co_data[2] = self.system_flags["maintenance_mode"]
        co_data[3] = self.system_flags["alarm_active"]
        co_data[4] = self.system_flags["data_logging"]
        co_data[5] = self.system_flags["remote_control"]
        co_data[6] = self.system_flags["sensor_ok"]
        co_data[7] = self.system_flags["communication_ok"]

        co_block = ModbusSequentialDataBlock(0, co_data)

        # Input Registers для только чтения (адреса 0-99)
        ir_data = [0] * 100
        ir_data[0] = int(self.ddii_data["temperature"] * 100)
        ir_data[1] = int(self.ddii_data["pressure"] * 100)
        ir_data[2] = int(self.ddii_data["humidity"] * 100)
        ir_data[3] = self.ddii_data["status"]

        ir_block = ModbusSequentialDataBlock(0, ir_data)

        # Discrete Inputs (адреса 0-99)
        di_data = [False] * 100
        di_data[0] = self.system_flags["power_on"]
        di_data[1] = self.system_flags["sensor_ok"]
        di_data[2] = self.system_flags["communication_ok"]

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

        return context

    async def start_server(self, host: str = "0.0.0.0", port: int = 502):
        """Запуск Modbus сервера"""
        logger.info(f"Запуск Modbus сервера ДДИИ на {host}:{port}")

        self.context = self.setup_datastore()

        # Запускаем TCP сервер
        self.server = await StartAsyncTcpServer(
            context=self.context,
            address=(host, port),
            allow_reuse_address=True,
            allow_reuse_port=True,
        )

        logger.info(f"Modbus сервер ДДИИ запущен на {host}:{port}")

        # Запускаем симуляцию работы системы
        self.server_task = asyncio.create_task(self.simulate_ddii_operation())

    async def simulate_ddii_operation(self):
        """Симуляция работы системы ДДИИ"""
        import random

        logger.info("Запуск симуляции работы ДДИИ...")

        while True:
            try:
                # Обновляем данные измерений
                self.ddii_data["temperature"] += random.uniform(-0.5, 0.5)
                self.ddii_data["pressure"] += random.uniform(-1, 1)
                self.ddii_data["humidity"] += random.uniform(-2, 2)
                self.ddii_data["measurement_count"] += 1

                # Обновляем holding registers
                if self.context:
                    self.context[0].setValues(3, 0, [int(self.ddii_data["temperature"] * 100)])
                    self.context[0].setValues(3, 1, [int(self.ddii_data["pressure"] * 100)])
                    self.context[0].setValues(3, 2, [int(self.ddii_data["humidity"] * 100)])
                    self.context[0].setValues(3, 9, [self.ddii_data["measurement_count"]])

                # Случайно изменяем флаги
                if random.random() < 0.1:  # 10% вероятность изменения
                    flag_idx = random.randint(0, 7)
                    flag_names = list(self.system_flags.keys())
                    flag_name = flag_names[flag_idx]
                    self.system_flags[flag_name] = not self.system_flags[flag_name]

                    # Обновляем coils
                    if self.context:
                        self.context[0].setValues(1, flag_idx, [self.system_flags[flag_name]])

                await asyncio.sleep(2)  # Обновляем каждые 2 секунды

            except Exception as e:
                logger.error(f"Ошибка в симуляции ДДИИ: {e}")
                break

    def update_operation_mode(self, mode: int):
        """Обновление режима работы через Modbus"""
        if self.context and 0 <= mode <= 3:
            self.ddii_data["operation_mode"] = mode
            self.context[0].setValues(3, 7, [mode])
            logger.info(f"Режим работы изменен на: {mode}")

    def set_calibration_factor(self, factor: float):
        """Установка коэффициента калибровки через Modbus"""
        if self.context and 0.1 <= factor <= 10.0:
            self.ddii_data["calibration_factor"] = factor
            self.context[0].setValues(3, 8, [int(factor * 1000)])
            logger.info(f"Коэффициент калибровки установлен: {factor}")

    async def stop_server(self):
        """Остановка сервера"""
        if self.server_task:
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass

        if self.server:
            self.server.server_close()
            logger.info("Modbus сервер ДДИИ остановлен")


async def main():
    """Основная функция для демонстрации"""

    # Создаем экземпляр интегрированного сервера
    ddii_server = IntegratedModbusServer()

    try:
        # Запускаем сервер
        await ddii_server.start_server(host="0.0.0.0", port=5020)

        logger.info("Сервер запущен. Доступные регистры:")
        logger.info("  Holding Registers (0-9): Основные параметры ДДИИ")
        logger.info("  Coils (0-7): Флаги состояния системы")
        logger.info("  Input Registers (0-3): Только для чтения")
        logger.info("  Discrete Inputs (0-2): Входные сигналы")

        # Демонстрируем обновление данных
        await asyncio.sleep(5)
        ddii_server.update_operation_mode(2)
        ddii_server.set_calibration_factor(1.5)

        # Ждем завершения работы
        await ddii_server.server_task

    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        await ddii_server.stop_server()


if __name__ == "__main__":
    print("Запуск интегрированного Modbus сервера ДДИИ...")
    print("Сервер будет доступен на localhost:5020")
    print("Для остановки нажмите Ctrl+C")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nСервер остановлен пользователем")
    except Exception as e:
        print(f"Ошибка запуска: {e}")
