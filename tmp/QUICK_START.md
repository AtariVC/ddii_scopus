# Быстрый старт Modbus сервера

## 🚀 Запуск за 3 шага

### 1. Активируйте виртуальное окружение
```bash
source ../.venv/bin/activate
```

### 2. Запустите простой сервер
```bash
python simple_modbus_server.py
```

Сервер запустится на **localhost:5020**

### 3. Протестируйте в другом терминале
```bash
source ../.venv/bin/activate
python test_quick_client.py
```

## 📋 Что доступно

- **Holding Registers (0-99)**: 0, 10, 20, 30, 40, 50, 60, 70, 80, 90...
- **Coils (0-99)**: True, False, True, False, True, False...
- **Input Registers (0-99)**: 0, 100, 200, 300, 400, 500...
- **Discrete Inputs (0-99)**: True, False, False, True, False, False...

## 🔧 Основные команды

### Чтение данных
```python
# Holding Registers
result = client.read_holding_registers(0, 5)  # Читаем 5 регистров с адреса 0

# Coils
result = client.read_coils(0, 8)  # Читаем 8 coils с адреса 0
```

### Запись данных
```python
# В Holding Register
client.write_register(10, 9999)  # Записываем 9999 в регистр 10

# В Coil
client.write_coil(20, True)  # Устанавливаем coil 20 в True
```

## 🛠️ Устранение проблем

- **Порт занят**: Сервер использует порт 5020 (нестандартный)
- **PyModbus не найден**: Активируйте виртуальное окружение
- **Ошибки импорта**: Используйте обновленные примеры

## 📚 Дополнительные примеры

- `modbus_server_example.py` - Полнофункциональный асинхронный сервер
- `modbus_client_example.py` - Асинхронный клиент
- `integration_example.py` - Интеграция с проектом ДДИИ
