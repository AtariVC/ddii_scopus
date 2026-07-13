---
name: architecture-rules
description: "Architectural rules and conventions for the ddii_scopus PyQt6 application — UI patterns, Modbus layer, widget structure, tab system"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8d53f832-ade7-4947-b43b-45a00ffb5c80
---

# Архитектурные правила ddii_scopus

## 1. UI — только .ui файлы

**Правило:** Каждый виджет имеет парный `.ui` файл (Qt Designer), загружаемый через `loadUi`. Программный код на Python не строит layout.

**Исключение:** Динамически генерируемые коллекции (например, 32 поля HH-уровней) строятся кодом внутри именованного placeholder-виджета из `.ui` (например `widget_hh_container`).

```python
# Правильно
loadUi(Path(__file__).parent / "my_widget.ui", self)
self._build_hh_grid()  # только если есть динамический контент

# Запрещено
layout = QVBoxLayout(self)
layout.addWidget(QLabel("..."))
```

**Why:** Весь проект использует этот паттерн. Нарушение создаёт несогласованность стиля.

**How to apply:** Перед созданием нового виджета — сначала `.ui`, потом минимальный `.py`.

---

## 2. Табовая система — плоские виджеты без внешнего скролла

**Правило:** Виджеты, передаваемые в `widget_model` для `create_tab_widget_items()`, не должны иметь собственного внешнего `QScrollArea`.

**Why:** `create_tab_widget_items()` автоматически оборачивает каждый виджет в `QGroupBox` и помещает все в один `QScrollArea`. Если виджет сам добавляет скролл — получаются вложенные scrollbar'ы.

**Паттерн «Осциллограф»** — эталон для правой панели:
```python
"Настройка": {
    "МПП": self.mpp_settings_widget,        # → GroupBox "МПП" в общем скролле
    "ЦМ: Питание": self.cm_settings_widget, # → GroupBox "ЦМ: Питание"
}
```

Каждый виджет в словаре — отдельная секция. Виджет плоский, скроллится внешней системой.

**Допустимый внутренний скролл:** ограниченные по высоте подсекции (например, `QScrollArea` фиксированной высоты для HH-сетки) — это нормально, они не конфликтуют с внешним.

---

## 3. Структура вкладок (4 вкладки)

```python
widget_model = {
    "Осциллограф": {          # левая панель: GraphWidget
        "Меню запуска":          run_meas_widget,
        "Опрос счетчика частиц": run_flux_widget,
        "Счетчик частиц":        flux_widget,
        "spacer":                QSpacerItem(...),
        "Подключение":           w_ser_dialog,   # особый: рендерится ВНЕ скролла
    },
    "Настройка": {            # левая панель: GraphWidget
        "МПП":        mpp_settings_widget,
        "ЦМ: Питание": cm_settings_widget,
    },
    "Диагностика": {          # левая панель: test_tables_widget (DDII + SYS кадры)
        "Опрос телеметрии": telemetry_poll_widget,
        "Тестирование":     test_runner_widget,
        "Чтение памяти":    cmd_wind_read_mem,
    },
    "Вьюер": {                # левая панель: graph_viewer_widget
        "Файл менеджер": explorer_hdf5_widget,
        "Фильтр кадров": graph_filter_widget,
    },
}
```

`on_tab_widget_handler` переключает левую панель:
- "Вьюер" → `graph_viewer_widget`
- "Диагностика" → `test_tables_widget`
- всё остальное → `w_graph_widget`

---

## 4. Два устройства на шине

| Устройство | Класс команд | slave ID |
|---|---|---|
| ЦМ (CM) | `ModbusCMCommand` | 1 (`CM_ID`) |
| МПП | `ModbusMPPCommand` | 14 по умолчанию (`MPP_ID_DEFAULT`) |

Оба команды создаются через `w_ser_dialog.get_commands_interface(logger)` → `(cm_cmd, mpp_cmd)`.

---

## 5. Паттерн виджета с Modbus

```python
class MyWidget(QtWidgets.QWidget):
    def __init__(self, mw=None) -> None:
        super().__init__(mw)
        self._mw = mw
        self.cm_cmd: Optional[ModbusCMCommand] = None   # или mpp_cmd
        self.parser = Parsers()
        self.logger = getattr(mw, "logger", None) or log_init()

        loadUi(Path(__file__).parent / "my_widget.ui", self)
        # ... validators, signal connections ...

        if mw is not None:
            try:
                mw.w_ser_dialog.coroutine_finished.connect(self.init_mb_cmd)
            except Exception:
                pass

    @qasync.asyncSlot()
    async def init_mb_cmd(self) -> None:
        self.cm_cmd, self.mpp_cmd = self._mw.w_ser_dialog.get_commands_interface(self.logger)
        await self._on_update()  # автообновление при подключении
```

**Сигнал подключения:** `w_ser_dialog.coroutine_finished` — испускается при успешном Serial/TCP connect.

---

## 6. Декоратор @mb_encode и паттерн команд

```python
@mb_encode
async def get_something(self) -> ModbusResponse:
    return await self.client.read_holding_registers(addr, count, slave=CM_ID)
```

Возвращает `bytes` (payload без byte_count) или `b"-1"` при ошибке. Всегда проверяй `if result != b"-1"` перед обработкой.

---

## 7. Карта регистров прошивки (modbus_debug.h)

| Область | Базовый адрес | Кол-во регистров | Доступ |
|---|---|---|---|
| Статус ЦМ | 100 | 13 | R |
| Кадр DDII | 200 | 32 | R |
| Системный кадр | 240 | 32 | R |
| HVIP (per channel) | 300 | 18 | R/W |
| Конфигурация | 400 | 58 | R/W |
| Команды управления | 0–17 | — | W (FC16) |

Команды управления (FC16 на адреса 0–17): DEBUG_MODE=0, CONST_MODE=1, HVIP_POWER=2, INTERVAL=3, GET_FRAME=4, START_AUTOTEST=12, GPIO_IMPACT=13, LOAD_CFG=14, SAVE_CFG=15, RESET=17 (magic=0xA55A).

**Важно:** Старые константы в `modbus_var.py` (CMD_DBG_* по адресам 0x00–0x0F) — от старой прошивки. Новая архитектура должна использовать `modbus_debug.h`.

---

## 8. Фильтр МПП (mppa.h)

`CMD_FILTER_BYPASS = 10`, команда: `write_mpp_ctrl([10, mask])`

`mask = {median_en[bit2], bypass_lp[bit1], bypass_hp[bit0]}`

```python
_FILTER_MASKS = {
    "нет":       0b011,  # bypass LP + HP, no median
    "медианный": 0b100,  # median on
    "ФНЧ":       0b001,  # LP active
    "ФВЧ":       0b010,  # HP active
}
```

---

## 9. Порядок каналов HVIP в командах ЦМ

`set_voltage_pwm(data)` ожидает порядок: **CH, PIPS, SiPM**.

UI отображает в порядке: PIPS[0], SiPM[1], CH[2].

При упаковке для отправки: `_SEND_ORDER = [2, 0, 1]` (индексы UI → CH, PIPS, SiPM).

---

## 10. Async

- Event loop: `qasync.QEventLoop`
- Async слоты: `@qasync.asyncSlot()` (не `@asyncSlot` без qasync)
- Нет `asyncio.run()` — всё через уже запущенный loop

**Фоновые задачи — через `AsyncTaskManager`** (`app/src/util/async_task_manager.py`):

```python
from app.src.util.async_task_manager import AsyncTaskManager

class MyWidget(...):
    def __init__(self, mw=None):
        ...
        self._task_mgr = AsyncTaskManager(self.logger)

    def _start_poll(self):
        self._task_mgr.create_task(self._poll_loop(), "poll")

    def _stop_poll(self):
        self._task_mgr.cancel_task("poll")
```

- `create_task(coroutine, name)` — создаёт задачу, пропускает если уже активна
- `cancel_task(name)` — отменяет по имени
- `cancel_all_tasks()` — отменяет все (вызывать в `closeEvent`)
- Никогда не использовать голый `asyncio.create_task()` для polling-циклов — нет именования и нет защиты от дублирования

---

## 11. Event — собственная шина событий

`app/src/event/event.py` — threading-based pub/sub с проверкой типов.

```python
from app.src.event.event import Event

# Объявление (обычно в MainUIRenderer)
shared_bfr_update_event: Event = Event(str)

# Подписка
shared_bfr_update_event.subscribe(self._on_data)

# Отписка
shared_bfr_update_event.unsubscribe(self._on_data)

# Отправка (каждый подписчик вызывается в отдельном daemon-Thread)
shared_bfr_update_event.emit("payload")
```

- `Event(*types)` — объявляет сигнатуру; emit проверяет типы и бросает `TypeError` при несоответствии
- Каждый вызов `emit()` создаёт по потоку на каждого подписчика — callback должен быть потокобезопасным
- Используется для межкомпонентного обмена данными (буферы измерений и т.п.), не для UI-слотов — для UI используются Qt-сигналы (`pyqtSignal`)

---

## 12. Файловая структура settings

```
app/widgets/settings/
├── __init__.py
├── mpp_settings_widget.py   # МПП: Level, Filter, HH[32]
├── mpp_settings_widget.ui
├── cm_settings_widget.py    # ЦМ: U/PWM по каналам, интервал
└── cm_settings_widget.ui
```

Будущие секции (по архитектурному плану, ещё не реализованы):
- `cm_status_widget` — статусные регистры ЦМ (addr 100, 13 регистров)
- `hvip_control_widget` — управление HVIP по каналу (addr 300, 18 регистров)
- `cm_control_widget` — панель команд (debug mode, const mode, reset и т.д.)
