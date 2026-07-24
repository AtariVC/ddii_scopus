# Памятка: как строить виджеты в ddii_scopus

Единое правило: **разметка — в `*.ui`, логика — в `*.py`**. Оформление берётся из
`dark_pro_widgets` (тема + глобальный QSS), готовые компоненты переиспользуются, а не
переписываются. Ниже — конвенции, которых придерживаемся во всём проекте.

Эталоны для копирования: [graph_widget.py](../app/widgets/oscilloscope/graph_widget.py) +
[graph_widget.ui](../app/widgets/oscilloscope/graph_widget.ui),
[test_impact_ctrl.py](../app/widgets/oscilloscope/test_impact_ctrl.py).

---

## 1. Файловая пара

Каждый виджет — это пара файлов с одинаковым именем в одной папке:

```
app/widgets/<группа>/<имя>_widget.ui   ← фронт: структура, layout, статические тексты
app/widgets/<группа>/<имя>_widget.py   ← бэк: класс, логика, сигналы, данные
```

Класс наследует `QtWidgets.QWidget` (или `QDialog`) и грузит свой `.ui`:

```python
class GraphViewerWidget(QtWidgets.QWidget):
    def __init__(self, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath("graph_viewer_widget.ui"), self)
```

- Путь к `.ui` — всегда `Path(__file__).parent.joinpath(...)`, не относительный и не хардкод.
- Грузим через `from qtpy.uic import loadUi`.

---

## 2. Что живёт в `*.ui` (фронт)

**Только структура и статика:**

- Layout'ы, вложенность, отступы (`leftMargin`/`spacing`/…), `sizePolicy`, `minimumSize`.
- Статические подписи, `placeholderText`, `windowTitle`.
- Имена объектов (`objectName`) — по ним бэк находит виджеты.
- **Пустые layout-слоты** под виджеты, которые бэк создаёт в рантайме
  (`vLayout_pips` под pyqtgraph-график, `vLayout_playback` под `PlaybackBar`).
- Продвижение кастомных виджетов из `dark_pro_widgets` через `<customwidget>`
  (`<header>dark_pro_widgets.buttons</header>` и т.п.).

**Чего в `.ui` быть НЕ должно:**

- ❌ Инлайновых `styleSheet` с цветами/шрифтами. Оформление — из темы (см. §4).
  Единственное исключение — когда без per-widget стиля никак, и тогда только через
  токены темы из `.py`, а не хардкод `#rrggbb` в `.ui`.
- ❌ Логики, обработчиков, данных.
- ❌ Хардкод-геометрии окна как способа «сверстать» — используем layout'ы и stretch.

---

## 3. Что живёт в `*.py` (бэк)

- **Аннотации виджетов из `.ui`** на уровне класса — для автодополнения и типов.
  Имя аннотации = `objectName` из `.ui`:

  ```python
  class TestImpactControl(QtWidgets.QDialog):
      spinBox_dur_imp_us: QtWidgets.QSpinBox
      pushButton_impact: PrimaryButton
  ```

- **Создание рантайм-виджетов** и вставка их в пустые слоты `.ui`:

  ```python
  self.playback = PlaybackBar(total_frames=1, frame=1, time_text="—")
  self.vLayout_playback.addWidget(self.playback)
  ```

- **Подключение сигналов** — в `__init__` или в отдельном `_wire()`:

  ```python
  self.pushButton_impact.clicked.connect(self.pushButton_impact_handler)
  self.playback.frameChanged.connect(lambda _v: self.slider_graphs_updater())
  ```

- **Данные, состояние, вычисления, работа с HDF5/Modbus** — только здесь.

---

## 4. Оформление — через `dark_pro_widgets`, не вручную

- Единый источник палитры и шрифтов — [`dark_pro_widgets.theme`](../.venv/Lib/site-packages/dark_pro_widgets/theme.py):
  `theme.BG`, `PANEL_BG`, `FIELD_BG`, `BORDER`, `ACCENT`, `OK`/`WARN`/`ERR`,
  `TEXT`/`TEXT_DIM`, семантические `PIPS`/`SIPM`, `FONT_FAMILY`/`MONO_FAMILY`.
  **Цвета и шрифты берём только отсюда**, хардкод запрещён.
- Глобальный стиль применяется один раз на уровне приложения:
  `app.setStyleSheet(qss.build_stylesheet())`. Стандартные Qt-виджеты
  (кнопки, поля, списки, чекбоксы, деревья) уже оформлены — доп. стилизация не нужна.
- **Варианты вида — через динамические свойства**, а не свой QSS:

  ```python
  btn.setProperty("accent", True)   # синяя главная кнопка
  btn.style().unpolish(btn); btn.style().polish(btn)
  ```

  (глобальный QSS ловит `QPushButton[accent="true"]`, `[danger="true"]`).
- **Data-зависимое оформление**, которое нельзя выразить глобально (цвет точки канала,
  фон области графика, бейджи), выносим в метод `_apply_theme()` в `.py` и красим
  токенами темы. Образец — `GraphWidget._apply_theme` / `_style_plot`.

---

## 5. Переиспользуй готовые компоненты

Прежде чем верстать руками — проверь, нет ли готового виджета в `dark_pro_widgets`:

| Нужно | Берём |
|---|---|
| Кнопка (обычная/акцентная/toggle) | `PrimaryButton`, `ToggleButton`, свойство `accent` |
| Карточка с заголовком и бейджем | `PanelCard`, `BadgeLabel` |
| Транспорт кадров (время + слайдер + ⏮▶⏭) | `PlaybackBar` |
| Осциллограмма / гистограмма (pyqtgraph) | `ScopePlot`, `HistogramPlot`, `configure_pyqtgraph` |
| Поля/списки/переключатели | `LineEdit`, `ComboBox`, `SpinBox`, `Slider`, `ToggleSwitch`, `SegmentedControl`, `LogView` |
| Навигация/статус связи | `NavRail`, `ConnectionBar` |

Не дублируй фронт этих компонентов — импортируй и настраивай.

---

## 6. Разделение классов на модули

**Когда разделять классы по разным файлам:**

- **Большой объём.** Класс на сотни строк со своей сложной логикой.
- **Независимость.** Классы решают разные задачи и не зависят друг от друга.
- **Удобство чтения.** Разделение помогает быстрее находить нужный код.

**Когда держать классы в одном файле:**

- **Вспомогательные классы.** Маленький класс нужен только для работы основного
  (промоут-адаптеры под `.ui`, мини-модель одной записи).
- **Логическая связь.** Группа тесно связанных мелких классов (исключения модуля,
  мини-модель), которые всегда используются вместе.

Ориентир — «одна ответственность на файл»: главный виджет + его обслуга рядом,
самостоятельная подсистема — отдельно.

**Пример** ([connection_bar.py](../app/plugins/connection/connection_bar.py) — оба случая в одном месте):

- *Оставляем рядом:* промоут-адаптеры `_TransportSwitch` / `_ConnectButton` /
  `_IconButton` (существуют только чтобы `.ui` собрал `ConnectionBar`) и
  вложенный `ProxySequentialDataBlock` (мини-модель, живёт только внутри relay).
- *Кандидат на вынос:* `ModbusRelayServer` — самостоятельная подсистема на ~180
  строк, не зависящая от виджета; её логично держать в отдельном модуле.

Второй ориентир из библиотеки: `FileItem` вынесен из `file_tree.py` в
`file_item.py` — независимая мини-модель записи, переиспользуемая виджетом и демо.

---

## 7. Именование

- `objectName` = `<тип><Camel/snake>`: `pushButton_impact`, `lineEdit_threshold_pips`,
  `checkBox_sipm`, `label_time_data`, `spinBox_dur_imp_us`, `listWidget_times`.
- Layout-слоты под рантайм-виджеты: `vLayout_<что>` (`vLayout_pips`, `vLayout_playback`).
- Карточка + её части: `card_<x>`, `title_card_<x>`, `dot_card_<x>`, `badge_<x>`.
- Обработчики: `<widget>_handler` (`pushButton_impact_handler`) или `_on_<событие>`.

---

## 8. Связи между виджетами

- Зависимости прокидываем через `parent` (главное окно), а сам виджет получает его
  как `args[0]`; к соседям обращаемся через parent:

  ```python
  def __init__(self, *args) -> None:
      super().__init__()
      self.parent = args[0]
      self.w_ser_dialog = self.parent.w_ser_dialog
  ```

- Слабая связанность между экранами/виджетами — через `app.src.event.event.Event`
  (pub/sub): одна сторона `event.subscribe(callback)`, другая `event.emit(value)`.
  Пример: `explorer.double_clicked_event` → `graph_viewer.open_graphs`,
  `graph_viewer.slider_update_event` → фильтр.
- Прямых импортов «виджет ↔ виджет» ради вызова методов избегаем; идём через parent или Event.

---

## 9. Асинхронность и логи

- Асинхронные обработчики — `@qasync.asyncSlot()` (без своей `asyncio`-петли слот не
  выполнится). Ручной запуск из кода — `asyncio.create_task(self.some_async_slot())`.
- Логи — `loguru` (`from loguru import logger`) либо `log_init()` / `get_logger()`
  из `app.src.components.log.config`.
- Косметика (покраска заголовка и т.п.) не должна ронять приложение: ошибку логируем на
  `debug` и продолжаем, не пробрасываем.

---

## 10. Автономный запуск виджета (`if __name__ == "__main__"`)

Каждый виджет должен запускаться в одиночку для отладки. Для этого есть готовый
хелпер `preview` из `dark_pro_widgets.core` — он сам создаёт `QApplication`,
применяет тему (`qss.build_stylesheet()`), кладёт виджет в хост-окно и красит
заголовок. Ручной скелет писать не нужно:

```python
if __name__ == "__main__":
    from dark_pro_widgets.core import preview
    preview(FilterViewerWidget, title="Фильтр кадров — demo", size=(320, 760), stretch=False)
```

- Передаём **фабрику** (класс или функция без аргументов), а не готовый объект:
  QApplication должен существовать раньше любого QWidget, поэтому виджет строится
  внутри `preview`. Для сложного демо используем функцию:
  `preview(lambda: _build_demo(), ...)`; можно вернуть и список виджетов.
- Сигнатура: `preview(build, title="preview", size=None, spacing=14,
  margins=(24,24,24,24), stretch=True)`.

**Исключение — виджеты с async-слотами** (`@qasync.asyncSlot()`): им нужна
qasync-петля, а `preview` крутит обычный `app.exec()`, поэтому слоты не выполнятся.
Для таких виджетов оставляем ручной скелет с `qasync.QEventLoop` (образец —
[connection_bar.py](../app/plugins/connection/connection_bar.py)). Там же — правило
покраски заголовка: красим **верхнеуровневое** окно (`host`, не вложенный виджет)
и **до** `show()` (на Win10 immersive-dark применяется только до первой отрисовки;
только Windows) — но `preview` это делает сам.

**Сырой запуск без `preview`** (на всякий случай — если хелпер недоступен или нужен
полный контроль над окном/петлёй). Виджет строим только ПОСЛЕ `QApplication`:

```python
if __name__ == "__main__":
    import sys
    from PyQt6 import QtWidgets
    from dark_pro_widgets import qss, theme

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())          # тема ddii

    host = QtWidgets.QWidget()
    host.setStyleSheet(f"background-color: {theme.BG};")
    layout = QtWidgets.QVBoxLayout(host)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.addWidget(WidgetClass())                    # мок; parent при необходимости

    host.resize(320, 760)
    theme.tint_window_board(int(host.winId()))         # тёмный заголовок ДО show()
    host.show()
    sys.exit(app.exec())                               # для async-слотов — qasync.QEventLoop
```

---

## 11. Чек-лист перед коммитом виджета

- [ ] Есть пара `<имя>_widget.ui` + `<имя>_widget.py`, имена совпадают.
- [ ] В `.ui` нет логики и нет хардкод-цветов/шрифтов в `styleSheet`.
- [ ] Все виджеты из `.ui`, которые дёргает бэк, аннотированы на уровне класса.
- [ ] Рантайм-виджеты кладутся в пустые layout-слоты, а не создаются мимо layout.
- [ ] Цвета/шрифты — из `theme`; варианты кнопок — через свойства (`accent`/`danger`).
- [ ] Проверено, нет ли готового компонента в `dark_pro_widgets`.
- [ ] Классы разложены по правилу §6: самостоятельная подсистема — отдельный модуль,
      обслуга главного класса — рядом.
- [ ] Сигналы подключены в `__init__`/`_wire()`; обработчики названы по конвенции.
- [ ] Асинхронные слоты — `@qasync.asyncSlot()`.
- [ ] Есть рабочий `if __name__ == "__main__"` для автономного запуска — через
      `preview(Factory, …)`; ручной qasync-скелет только если у виджета async-слоты.
