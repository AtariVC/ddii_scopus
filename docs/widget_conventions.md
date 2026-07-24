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

## 6. Именование

- `objectName` = `<тип><Camel/snake>`: `pushButton_impact`, `lineEdit_threshold_pips`,
  `checkBox_sipm`, `label_time_data`, `spinBox_dur_imp_us`, `listWidget_times`.
- Layout-слоты под рантайм-виджеты: `vLayout_<что>` (`vLayout_pips`, `vLayout_playback`).
- Карточка + её части: `card_<x>`, `title_card_<x>`, `dot_card_<x>`, `badge_<x>`.
- Обработчики: `<widget>_handler` (`pushButton_impact_handler`) или `_on_<событие>`.

---

## 7. Связи между виджетами

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

## 8. Асинхронность и логи

- Асинхронные обработчики — `@qasync.asyncSlot()` (без своей `asyncio`-петли слот не
  выполнится). Ручной запуск из кода — `asyncio.create_task(self.some_async_slot())`.
- Логи — `loguru` (`from loguru import logger`) либо `log_init()` / `get_logger()`
  из `app.src.components.log.config`.
- Косметика (покраска заголовка и т.п.) не должна ронять приложение: ошибку логируем на
  `debug` и продолжаем, не пробрасываем.

---

## 9. Автономный запуск виджета (`if __name__ == "__main__"`)

Каждый виджет должен запускаться в одиночку для отладки. Скелет:

```python
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())          # тема ddii

    event_loop = qasync.QEventLoop(app)                # для asyncSlot
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    host = QtWidgets.QWidget()
    host.setStyleSheet(f"background-color: {theme.BG};")
    layout = QtWidgets.QVBoxLayout(host)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.addWidget(WidgetClass(host_parent))          # parent при необходимости

    host.resize(...)
    theme.tint_window_board(int(host.winId()))          # тёмный заголовок ДО show()
    host.show()

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
```

Ключевое:
- Стиль приложения — `qss.build_stylesheet()`.
- Красим системный заголовок **верхнеуровневого** окна (`host`, не вложенного виджета)
  и **до** `show()` (`winId()` создаёт нативное окно; на Win10 immersive-dark
  применяется только до первой отрисовки). Только Windows.

---

## 10. Чек-лист перед коммитом виджета

- [ ] Есть пара `<имя>_widget.ui` + `<имя>_widget.py`, имена совпадают.
- [ ] В `.ui` нет логики и нет хардкод-цветов/шрифтов в `styleSheet`.
- [ ] Все виджеты из `.ui`, которые дёргает бэк, аннотированы на уровне класса.
- [ ] Рантайм-виджеты кладутся в пустые layout-слоты, а не создаются мимо layout.
- [ ] Цвета/шрифты — из `theme`; варианты кнопок — через свойства (`accent`/`danger`).
- [ ] Проверено, нет ли готового компонента в `dark_pro_widgets`.
- [ ] Сигналы подключены в `__init__`/`_wire()`; обработчики названы по конвенции.
- [ ] Асинхронные слоты — `@qasync.asyncSlot()`.
- [ ] Есть рабочий `if __name__ == "__main__"` для автономного запуска.
