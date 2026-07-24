# Конвенции построения виджетов


## 1. Разметка в `.ui`, логика + стиль в `.py`

`.ui` нужен только крупным сборным виджетам (сейчас `connection_bar`, `file_tree`
в `widgets/composite/`). Простые контролы и индикаторы — чистый Python
(`paintEvent`/QSS) без `.ui`.

**Структура composite: каждый виджет — в своей папке-пакете.** Все виджеты из
`widgets/composite/` лежат в собственной папке с именем виджета:
`widgets/composite/<name>/` содержит `<name>.py`, `<name>.ui` (если есть) и
`__init__.py`, который реэкспортит класс(ы) (`from .<name> import <Class>`). Это
держит пару `.py`+`.ui` вместе и одинаково для всех composite. Публичный импорт не
меняется: `composite/__init__.py` делает `from .<name> import <Class>` (резолвится в
папку-пакет). Контролы и индикаторы остаются одиночными `.py` — папку заводим
только для composite.

**В `.ui` (front) — только структура и статика:** layout'ы, вложенность,
margins/spacing, `sizePolicy`, `objectName`, статические тексты/`placeholderText`,
**пустые layout-слоты** под рантайм-виджеты, и промоушен кастомных виджетов через
`<customwidget>`.

**В `.ui` НЕ должно быть:** логики/обработчиков; хардкод-цветов/шрифтов в
`styleSheet`; фиксированной геометрии окна вместо layout'ов.

**В `.py` (back):** аннотации виджетов из `.ui` на уровне класса (имя аннотации =
`objectName`, для типов и автодополнения); создание рантайм-виджетов и вставка их в
пустые слоты `.ui`; подключение сигналов в `__init__` или `_wire()`; всё состояние
и данные.

**Загрузка `.ui` в библиотеке:** путь всегда рядом с модулем —
`os.path.join(os.path.dirname(os.path.abspath(__file__)), "<name>.ui")` (лежит в той
же папке-пакете), грузим `uic.loadUi(_UI_FILE, self)` (PyQt6). Promoted-`<header>` в
`.ui` — **полный** путь модуля с учётом папки:
`dark_pro_widgets.widgets.composite.<name>.<name>` (напр.
`...composite.connection_bar.connection_bar`). Promotion-адаптеры (тонкие подклассы
с конструктором `(parent)`, чтобы загрузчик `.ui` мог их инстанцировать) — вверху
composite-`.py` (см. `connection_bar._TransportSwitch`).

---

## 2. Оформление — только через `theme`, двумя разными путями

Цвета и шрифты берём **только** из `dark_pro_widgets.theme`: `BG`, `PANEL_BG`,
`FIELD_BG`, `BORDER`, `ACCENT`, `OK`/`WARN`/`ERR`, `TEXT`/`TEXT_DIM`, семантические
`PIPS`/`SIPM`, `FONT_FAMILY`/`MONO_FAMILY`, плюс `theme.rgba(hex, alpha)`. Хардкод
`#rrggbb` запрещён. `theme`/`qss` лежат в `core/`, но реэкспортятся плоско:
`from dark_pro_widgets import theme, qss`.

**Не путать два пути стилизации:**

1. **Стоковые Qt-виджеты** покрыты единым глобальным листом
   `qss.build_stylesheet()` (применяется один раз на уровне приложения). Варианты
   там — через **динамические свойства**: обычный `QPushButton` становится
   accent/danger так:
   ```python
   btn.setProperty("accent", True)
   btn.style().unpolish(btn); btn.style().polish(btn)
   ```
   Глобальный QSS ловит `QPushButton[accent="true"]` / `[danger="true"]`.

2. **Собственные виджеты dark_pro_widgets** ставят **свой** per-widget stylesheet и
   дают более богатый API вместо свойств — напр. `PrimaryButton(variant=...)` /
   `setVariant("accent"|"success"|"danger"|"neutral")` из таблицы `_VARIANTS`. Для
   нового кастомного виджета держим метод `_apply_style()`/`_apply_theme()`, который
   пересобирает лист из токенов темы, и зовём его при каждой смене состояния.

**Data-зависимое оформление**, которое нельзя выразить глобально (цвет точки
канала, фон области графика, бейджи), — в метод `_apply_theme()` в `.py`, красим
токенами темы. **Анимации** — через `QPropertyAnimation(self, b"<prop>")` над
`pyqtProperty` с `QEasingCurve` (см. анимацию `offset` в `toggle_switch`); простая
отложенная работа — `QTimer.singleShot`.

---

## 3. Библиотека презентационная — без бэкенда, с точками расширения

**Здесь НЕТ бэкенда** (ни Modbus/HDF5, ни async Event-шины — это живёт в
приложении-потребителе). Поэтому, добавляя поведение виджету, не пиши реальную
логику данных, а:

- оформляй его как **переопределяемые хук-методы и сигналы**, которые подключает
  downstream-проект — потребитель наследует виджет или переопределяет хук, чтобы
  вставить настоящую логику (duck-typing / override в Python). Дефолтная реализация
  = no-op, анимация или демо-поведение, поверх которого потребитель строит своё.
- клади **`demo_*`-хелпер** с фейковыми данными для превью (образец —
  `file_tree.demo_items()`), используемый только в блоке превью, не в проде.

### Запуск виджета в одиночку — абсолютные импорты, БЕЗ бутстрапа

**Никакого `runpy`/`sys.path`-костыля в начале файла.** Виджет должен запускаться
кнопкой Run в IDE как есть. Механика:

- **Виджет-модули используют абсолютные импорты** от корня пакета:
  `from dark_pro_widgets.core import theme` / `... import qss`;
  `from dark_pro_widgets.widgets.controls.slider import Slider`. Относительных
  импортов (`from . / .. / ...`) в запускаемых модулях быть не должно (в `__init__.py`,
  которые напрямую не запускают, относительные допустимы).
- **Пакет установлен editable** (`uv sync`, либо `uv pip install -e .`) — поэтому
  `import dark_pro_widgets` резолвится прямо в рабочее дерево. Именно это позволяет
  `python <файл>.py` найти пакет без всякого guard. Требование одно: интерпретатор
  IDE — это venv проекта с editable-установкой.
- **Запуск**: кнопка Run по файлу, либо `python -m dark_pro_widgets.widgets.<...>.<name>`,
  либо `uv run python <путь>`.
- Нижний `if __name__ == "__main__":` делает `from dark_pro_widgets.core._preview import preview`
  и `preview(build, title=...)`, где `build()` строит виджет(ы) **после** применения
  темы/QSS (QApplication должен существовать раньше любого QWidget). Для composite с
  `.ui` (напр. `connection_bar`) блок может собирать хост-окно и грузить `.ui` сам.

**Логи:** библиотека использует **loguru** (`from loguru import logger`), а не
стандартный `logging` — вопреки строчке в памятке приложения. Косметика (напр.
`theme.tint_window_board`) не должна ронять приложение: оборачиваем в try/except и
`logger.debug(...)`, продолжаем.

---

## 4. Именование (со стороны приложения, для консистентности)

- `objectName` = `<тип><Camel/snake>`: `pushButton_impact`, `lineEdit_threshold_pips`,
  `checkBox_sipm`, `label_time_data`, `spinBox_dur_imp_us`.
- Layout-слоты под рантайм-виджеты: `vLayout_<что>` (`vLayout_pips`, `vLayout_playback`).
- Карточка и её части: `card_<x>`, `title_card_<x>`, `dot_card_<x>`, `badge_<x>`.
- Обработчики: `<widget>_handler` (`pushButton_impact_handler`) или `_on_<событие>`.

---

## 5. Объявление имен перед инициализацией.
Перед инициализации класса сделать аннотацию компонентов из *.ui, к которым будет обращение в коде, для нормальной работы линтера.

Пример:

```py
class ExplorerHDF5Widget(QtWidgets.QDialog):
    lineEdit_path_edit: QtWidgets.QLineEdit
    pushButton_down: PrimaryButton
    pushButton_browser: PrimaryButton
    pushButton_close_hdf5: PrimaryButton
    pushButton_up: PrimaryButton
    columnView_explorer: QtWidgets.QColumnView
    treeView_file_tree: QtWidgets.QTreeView

    def __init__(self) -> None:
        super().__init__()
        
```
## 6. Разделение классов на модули

#### Когда разделять классы по разным файлам
Большой объем кода: Если один класс содержит сотни строк и сложную логику.Независимость: Если классы решают разные задачи и не зависят друг от друга.Удобство чтения: Когда разделение помогает быстрее находить нужный код.

#### Когда объединять классы в одном файле
Вспомогательные классы: Если маленький класс нужен только для работы основного главного класса.Логическая связь: Группа тесно связанных мелких классов (например, исключения для модуля или мини-модели).

## 7. Пути к файлам через pathlib

Пример:

```py
loadUi(Path(__file__).parent.joinpath("explorer_widget.ui"), self)
```

## 8. Загрузка *.ui через qtpy

```py
from qtpy.uic import loadUi
loadUi(Path(__file__).parent.joinpath("explorer_widget.ui"), self)
```

## 9. Демо с тинтборд
Изменять цвет системной рамки  
Пример:
```py
if __name__ == "__main__":
    import sys

    from dark_pro_widgets import qss, theme

    from app.widgets.oscilloscope.flux_widget import FluxWidget
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())
    widget: ExplorerHDF5Widget = ExplorerHDF5Widget()

    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    
    host = QtWidgets.QWidget()
    host.setWindowTitle("Файловое дерево — demo")
    host.setStyleSheet(f"background-color: {theme.BG};")
    layout = QtWidgets.QVBoxLayout(host)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.addWidget(widget)
    layout.addStretch()

    theme.tint_window_board(int(host.winId()))
    host.show()

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
```

# 10. Готовые иконки
Прежде чем создать новую иконку сходи провеь нет ли ее в: .venv\Lib\site-packages\qcustomwidgets
## Чек-лист перед коммитом виджета

- [ ] Если есть `.ui` — пара `<name>.ui` + `<name>.py`, имена совпадают.
- [ ] В `.ui` нет логики и нет хардкод-цветов/шрифтов в `styleSheet`.
- [ ] Все виджеты из `.ui`, к которым обращается `.py`, аннотированы на уровне класса.
- [ ] Рантайм-виджеты кладутся в пустые layout-слоты, а не мимо layout.
- [ ] Цвета/шрифты — из `theme`; варианты стоковых кнопок — через свойства,
      кастомных — через `setVariant`/конструктор.
- [ ] Проверено, нет ли готового компонента в `dark_pro_widgets` (не дублируем).
- [ ] Поведение — за переопределяемым хуком/сигналом, не хардкод-логика.
- [ ] Импорты абсолютные (`from dark_pro_widgets...`), в начале файла НЕТ
      `runpy`/`sys.path`-костыля.
- [ ] Есть `demo_*` и рабочий блок превью (`if __name__ == "__main__"`), файл
      запускается кнопкой Run напрямую (venv с editable-установкой).
- [ ] Объявление имен перед инициализацией