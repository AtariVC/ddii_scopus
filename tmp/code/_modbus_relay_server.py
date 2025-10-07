#!/usr/bin/env python3
"""
Modbus Relay Server - терминальное приложение для ретрансляции Modbus пакетов
между Serial портом и TCP соединениями.
"""

import argparse
import asyncio
import socket
import sys

import serial.tools.list_ports
from pymodbus.client import AsyncModbusSerialClient
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartAsyncTcpServer
from pymodbus.transaction import ModbusSocketFramer


def get_local_ip():
    """Автоматическое определение local IP адреса"""
    try:
        # Создаем временное соединение чтобы определить наш IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Подключаемся к публичному DNS серверу
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        try:
            # Альтернативный способ через hostname
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip
        except Exception:
            return "127.0.0.1"


def get_available_ports(start_port=5020, max_attempts=10):
    """Поиск доступного порта начиная с заданного"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return start_port  # Если все заняты, используем начальный


class ModbusRelayServer:
    def __init__(self, serial_port, baudrate, host=None, port=None, slave_id=1, 
                 bytesize=8, parity='N', stopbits=1, timeout=1):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.host = host or get_local_ip()
        self.port = port or get_available_ports()
        self.slave_id = slave_id
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.serial_client = None
        self.tcp_server = None
        self.running = False
        
    async def start_serial_client(self):
        """Подключение к Serial устройству"""
        try:
            print(f"Подключаемся к Serial: {self.serial_port}")
            print(f"Параметры: {self.baudrate} baud, {self.bytesize} bits, {self.parity} parity, {self.stopbits} stop bits")
            print(f"Slave ID: {self.slave_id}, Timeout: {self.timeout}s")
            
            self.serial_client = AsyncModbusSerialClient(
                port=self.serial_port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout,
                retries=3,
                retry_on_empty=True,
                handle_local_echo=False
            )
            
            connected = await self.serial_client.connect()
            if connected:
                print(f"✓ Успешно подключено к Serial порту {self.serial_port}")
                return True
            else:
                print(f"✗ Не удалось подключиться к Serial порту {self.serial_port}")
                return False
                
        except Exception as e:
            print(f"✗ Ошибка подключения к Serial: {e}")
            return False
    
    async def start_tcp_server(self):
        """Запуск TCP сервера"""
        try:
            print(f"Запускаем TCP сервер на {self.host}:{self.port}")
            
            # Создаем datastore для сервера
            store = ModbusSlaveContext(
                di=ModbusSequentialDataBlock(0, [0]*1000),
                co=ModbusSequentialDataBlock(0, [0]*1000),
                hr=ModbusSequentialDataBlock(0, [0]*1000),
                ir=ModbusSequentialDataBlock(0, [0]*1000)
            )
            
            context = ModbusServerContext(slaves=store, single=True)
            
            self.tcp_server = await StartAsyncTcpServer(
                context=context,
                address=(self.host, self.port),
                framer=ModbusSocketFramer,
                allow_reuse_address=True,
                defer_start=False
            )
            
            print(f"✓ TCP сервер запущен на {self.host}:{self.port}")
            return True
            
        except Exception as e:
            print(f"✗ Ошибка запуска TCP сервера: {e}")
            return False
    
    async def handle_tcp_request(self, request, client_address):
        """Обработка входящих TCP запросов и пересылка на Serial"""
        try:
            if not self.serial_client or not self.serial_client.connected:
                print("✗ Serial клиент не подключен, пропускаем запрос")
                return None
            
            # Логируем входящий запрос
            print(f"← TCP запрос от {client_address}: {request}")
            
            # Определяем slave_id для запроса (используем переданный или из запроса)
            slave_id = getattr(request, 'slave_id', self.slave_id)
            
            # Пересылаем запрос на Serial устройство
            if hasattr(request, 'function_code'):
                if request.function_code in [1, 2, 3, 4]:  # Read functions
                    if request.function_code == 1:
                        response = await self.serial_client.read_coils(
                            request.address, request.count, slave=slave_id
                        )
                    elif request.function_code == 2:
                        response = await self.serial_client.read_discrete_inputs(
                            request.address, request.count, slave=slave_id
                        )
                    elif request.function_code == 3:
                        response = await self.serial_client.read_holding_registers(
                            request.address, request.count, slave=slave_id
                        )
                    elif request.function_code == 4:
                        response = await self.serial_client.read_input_registers(
                            request.address, request.count, slave=slave_id
                        )
                    
                    if response and not response.isError():
                        print(f"→ Ответ от Serial: {response}")
                        return response
                    
                elif request.function_code in [5, 6, 15, 16]:  # Write functions
                    if request.function_code == 5:
                        response = await self.serial_client.write_coil(
                            request.address, request.value, slave=slave_id
                        )
                    elif request.function_code == 6:
                        response = await self.serial_client.write_register(
                            request.address, request.value, slave=slave_id
                        )
                    elif request.function_code == 15:
                        response = await self.serial_client.write_coils(
                            request.address, request.values, slave=slave_id
                        )
                    elif request.function_code == 16:
                        response = await self.serial_client.write_registers(
                            request.address, request.values, slave=slave_id
                        )
                    
                    if response and not response.isError():
                        print(f"→ Ответ от Serial: {response}")
                        return response
            
            return None
            
        except Exception as e:
            print(f"✗ Ошибка обработки TCP запроса: {e}")
            return None
    
    async def run(self):
        """Основной цикл работы ретранслятора"""
        try:
            # Подключаемся к Serial
            if not await self.start_serial_client():
                return False
            
            # Запускаем TCP сервер
            if not await self.start_tcp_server():
                return False
            
            self.running = True
            print("✓ Ретранслятор запущен. Нажмите Ctrl+C для остановки.")
            print("=" * 60)
            
            # Основной цикл
            while self.running:
                try:
                    # Здесь можно добавить периодическую проверку соединения
                    await asyncio.sleep(1)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Ошибка в основном цикле: {e}")
                    await asyncio.sleep(1)
            
            return True
            
        except KeyboardInterrupt:
            print("\nОстанавливаем ретранслятор...")
            return True
        except Exception as e:
            print(f"Критическая ошибка: {e}")
            return False
    
    async def stop(self):
        """Остановка ретранслятора"""
        self.running = False
        
        if self.tcp_server:
            print("Останавливаем TCP сервер...")
            self.tcp_server.server_close()
        
        if self.serial_client:
            print("Закрываем Serial соединение...")
            self.serial_client.close()
        
        print("Ретранслятор остановлен")


def list_serial_ports():
    """Список доступных COM портов"""
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("Не найдено доступных COM портов")
        return
    
    print("Доступные COM порты:")
    for i, port in enumerate(ports, 1):
        print(f"  {i}. {port.device} - {port.description}")


def print_network_info():
    """Вывод сетевой информации"""
    local_ip = get_local_ip()
    print(f"Определен local IP: {local_ip}")
    
    # Показываем все сетевые интерфейсы
    try:
        import netifaces
        print("Доступные сетевые интерфейсы:")
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    if addr['addr'] != '127.0.0.1':
                        print(f"  {interface}: {addr['addr']}")
    except ImportError:
        print("Установите netifaces для детальной информации: pip install netifaces")
        print(f"Используется IP: {local_ip}")


async def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(
        description='Modbus Relay Server - ретранслятор Modbus Serial↔TCP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Примеры использования:
  python modbus_relay_server.py --port COM3 --baudrate 9600 --slave-id 14
  python modbus_relay_server.py --port /dev/ttyUSB0 --baudrate 115200 --bytesize 8 --parity E --stopbits 2
  python modbus_relay_server.py --port COM4 --host 192.168.1.100 --tcp-port 5020 --timeout 2 --auto
        '''
    )
    
    parser.add_argument('--list-ports', action='store_true', help='Показать доступные COM порты')
    parser.add_argument('--network-info', action='store_true', help='Показать сетевую информацию')
    
    # Serial параметры
    parser.add_argument('--port', '-p', type=str, required=True, help='COM порт устройства (COM3, /dev/ttyUSB0)')
    parser.add_argument('--baudrate', '-b', type=int, default=9600, help='Скорость передачи (по умолчанию: 9600)')
    parser.add_argument('--slave-id', type=int, default=1, help='Slave ID устройства (по умолчанию: 1)')
    parser.add_argument('--bytesize', type=int, choices=[5, 6, 7, 8], default=8, help='Размер байта (по умолчанию: 8)')
    parser.add_argument('--parity', type=str, choices=['N', 'E', 'O', 'M', 'S'], default='N', help='Четность (N, E, O, M, S)')
    parser.add_argument('--stopbits', type=int, choices=[1, 2], default=1, help='Стоповые биты (1 или 2)')
    parser.add_argument('--timeout', type=float, default=1.0, help='Таймаут в секундах (по умолчанию: 1.0)')
    
    # TCP параметры
    parser.add_argument('--host', type=str, help='TCP хост (по умолчанию: автоматическое определение)')
    parser.add_argument('--tcp-port', type=int, help='TCP порт (по умолчанию: автоматический поиск с 5020)')
    
    parser.add_argument('--auto', '-a', action='store_true', help='Автоматический запуск без подтверждения')
    
    args = parser.parse_args()
    
    if args.list_ports:
        list_serial_ports()
        return
    
    if args.network_info:
        print_network_info()
        return
    
    # Автоматическое определение параметров
    local_ip = get_local_ip()
    tcp_port = args.tcp_port or get_available_ports()
    
    print("=" * 70)
    print("MODBUS RELAY SERVER - КОНФИГУРАЦИЯ")
    print("=" * 70)
    print("Serial параметры:")
    print(f"  Порт:        {args.port}")
    print(f"  Baudrate:    {args.baudrate}")
    print(f"  Slave ID:    {args.slave_id}")
    print(f"  Bytesize:    {args.bytesize}")
    print(f"  Parity:      {args.parity}")
    print(f"  Stopbits:    {args.stopbits}")
    print(f"  Timeout:     {args.timeout}s")
    print("TCP параметры:")
    print(f"  Хост:        {args.host or local_ip}")
    print(f"  Порт:        {tcp_port}")
    print("=" * 70)
    print("Для подключения с другого компьютера используйте:")
    print(f"  IP:   {args.host or local_ip}")
    print(f"  Port: {tcp_port}")
    print("=" * 70)
    
    if not args.auto:
        confirm = input("Запустить ретранслятор? (y/N): ")
        if confirm.lower() not in ['y', 'yes', 'д', 'да']:
            print("Отмена запуска")
            return
    
    # Создаем и запускаем ретранслятор
    relay = ModbusRelayServer(
        serial_port=args.port,
        baudrate=args.baudrate,
        host=args.host,
        port=args.tcp_port,
        slave_id=args.slave_id,
        bytesize=args.bytesize,
        parity=args.parity,
        stopbits=args.stopbits,
        timeout=args.timeout
    )
    
    try:
        success = await relay.run()
        if not success:
            print("Не удалось запустить ретранслятор")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nОстанавливаем ретранслятор...")
    finally:
        await relay.stop()


if __name__ == "__main__":
    # Запуск с обработкой Ctrl+C
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПриложение завершено")
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)