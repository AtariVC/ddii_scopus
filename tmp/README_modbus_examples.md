# Примеры использования PyModbus сервера

Этот каталог содержит примеры создания и использования Modbus серверов с помощью библиотеки PyModbus.

## Файлы

### 1. `modbus_server_example.py` - Полнофункциональный асинхронный сервер
- **TCP сервер** на порту 502
- **Serial сервер** (RTU) для последовательной связи
- **ASCII сервер** для ASCII протокола
- Автоматическое обновление данных
- Методы для работы с различными типами регистров

### 2. `simple_modbus_server.py` - Простой синхронный сервер
- Базовый TCP сервер для быстрого тестирования
- Предустановленные тестовые данные
- Простая настройка и запуск

### 3. `modbus_client_example.py` - Клиент для тестирования
- Асинхронный клиент для тестирования сервера
- Тестирование всех типов регистров
- Операции чтения и записи

## Установка зависимостей

```bash
pip install pymodbus
```

## Быстрый старт

### 1. Запуск простого сервера

```bash
python simple_modbus_server.py
```

Сервер будет доступен на `localhost:5020`

### 2. Тестирование клиентом

В другом терминале:

```bash
python modbus_client_example.py
```

### 3. Запуск полнофункционального сервера

```bash
python modbus_server_example.py
```

## Типы регистров

### Holding Registers (16-bit)
- **Адреса**: 0-9999
- **Функции**: 03 (чтение), 06 (запись одного), 16 (запись нескольких)
- **Использование**: Переменные, настройки, данные

### Input Registers (16-bit)
- **Адреса**: 30000-39999
- **Функции**: 04 (только чтение)
- **Использование**: Входные данные, измерения

### Coils (1-bit)
- **Адреса**: 00001-09999
- **Функции**: 01 (чтение), 05 (запись одного), 15 (запись нескольких)
- **Использование**: Выходы, флаги, переключатели

### Discrete Inputs (1-bit)
- **Адреса**: 10001-19999
- **Функции**: 02 (только чтение)
- **Использование**: Входные сигналы, датчики

## Примеры использования

### Создание сервера

```python
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext

# Создание блоков данных
hr_block = ModbusSequentialDataBlock(0, [0] * 1000)
co_block = ModbusSequentialDataBlock(0, [False] * 1000)

# Создание контекста
slave_context = ModbusSlaveContext(
    hr=hr_block,  # Holding Registers
    co=co_block,  # Coils
    zero_mode=True
)

# Запуск сервера
await StartAsyncTcpServer(context=slave_context, address=("localhost", 502))
```

### Работа с данными

```python
# Запись в holding register
context[0].setValues(3, address, [value])  # 3 = holding registers

# Чтение coils
values = context[0].getValues(1, address, count)  # 1 = coils

# Запись в coils
context[0].setValues(1, address, [True, False, True])
```

## Тестирование

### С помощью клиента

```python
from pymodbus.client import AsyncModbusTcpClient

client = AsyncModbusTcpClient("localhost", 502)
await client.connect()

# Чтение holding registers
result = await client.read_holding_registers(0, 5)
print(f"Registers: {result.registers}")

# Запись в register
await client.write_register(10, 12345)

await client.close()
```

### С помощью внешних инструментов

- **QModMaster** - GUI клиент для тестирования
- **Modbus Poll** - Профессиональный инструмент
- **Python скрипты** - Используя pymodbus клиент

## Настройка для продакшена

### Безопасность
- Ограничение доступа по IP
- Аутентификация (если поддерживается)
- Логирование всех операций

### Производительность
- Оптимизация размера блоков данных
- Асинхронная обработка запросов
- Мониторинг производительности

### Надежность
- Обработка ошибок
- Автоматический перезапуск
- Мониторинг состояния

## Устранение неполадок

### Сервер не запускается
- Проверьте, что порт 5020 свободен (используется нестандартный порт для избежания проблем с правами)
- Убедитесь, что PyModbus установлен: `pip install pymodbus`
- Проверьте логи на наличие ошибок

### Проблемы с импортами
- В новых версиях PyModbus изменился API
- `ModbusTcpFramer` больше не нужен для TCP сервера
- Используйте правильный синтаксис: `StartTcpServer(context=context, address=("localhost", 5020))`

### Клиент не подключается
- Убедитесь, что сервер запущен
- Проверьте настройки сети/файрвола
- Проверьте адрес и порт

### Ошибки чтения/записи
- Проверьте адреса регистров
- Убедитесь, что регистры доступны для записи
- Проверьте права доступа

## Дополнительные ресурсы

- [PyModbus документация](https://pymodbus.readthedocs.io/)
- [Modbus спецификация](https://modbus.org/specs.php)
- [Примеры PyModbus](https://github.com/pymodbus-dev/pymodbus/tree/master/examples)
