
"""MPPLevel — пороговые уровни МПП (32 уровня HH) с пересчётом кэВ ↔ кв. АЦП.

API:
* ``MPPLevel(client=None, parent=None)`` — таблица уровней, коэффициенты пересчёта
  и загрузка уровней из файла; ``client`` (ConnectionBar) даёт командные
  интерфейсы ЦМ и МПП, в demo — ``None``.
* ``refresh_levels()`` — прочитать уровни из регистров МПП (кнопка ⟳ над таблицей).
* ``apply_levels()`` — записать уровни и коэффициенты в прибор (кнопка «Применить»).
* ``apply_config()`` — записать уровни из файла в регистры ЦМ и обновить его конфигурацию.
* ``compare_config()`` — сравнить файл с тем, что сейчас в таблице.
* ``levels_kev()`` / ``levels_lsb()`` — текущие уровни; ``coefficients()`` — коэффициенты.

**Два разных пути записи.** Кнопка «Применить» над таблицей пишет **напрямую в
регистры МПП** (уровни — в квантах АЦП, ``set_hh``) и коэффициенты пересчёта — в
ЦМ (``set_mpp_coef_elv_lsb``). Файл конфигурации идёт иначе: уровни (в кэВ)
уходят в регистры ЦМ (``set_mpp_hh_levels``), а следом — команда обновления
конфигурации ЦМ (сохранить + применить, ``update_config``); перевод кэВ → кв. АЦП
в этом пути делает сама прошивка.

Пересчёт кэВ ↔ кв. АЦП повторяет код прошивки ЦМ (``mpp_hh_level_get_coef_elv_lsb``
и ``mpp_hh_level_kev_to_lsb``): коэффициент зависит от номера уровня — у «электронных» уровней в него входит
восьмикратный коэффициент СцД1, у «протонных» групп первые два уровня идут по
тракту ПД1, вторые два — по СцД1. Уровни разложены по группам ``_GROUPS``
(6 + 2 + 6×4 = 32) — порядок групп = порядок индексов HH в прошивке.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import qasync
from loguru import logger

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel,
                             QScrollArea, QVBoxLayout, QWidget)
from dark_pro_widgets.core import theme
from dark_pro_widgets.widgets.composite.data_table import DataTable
from dark_pro_widgets.widgets.composite.level_table import LevelTable
from dark_pro_widgets.widgets.controls.buttons import PrimaryButton
from dark_pro_widgets.widgets.controls.icon_button import IconButton
from dark_pro_widgets.widgets.controls.line_edit import LineEdit
from dark_pro_widgets.widgets.controls.segmented_control import SegmentedControl

from app.src.components.modbus.command_interface import (ModbusCMCommand,
                                                         ModbusMPPCommand)
from app.src.components.parsers.custom_parsers import Parsers

_FONT = theme.FONT_FAMILY.split(",")[0].strip()

#: Число пороговых уровней HH (``MPP_HH_LEVEL_NUM`` прошивки).
HH_LEVEL_NUM = 32


@dataclass(frozen=True)
class LevelGroup:
    """Группа уровней — строка таблицы.

    Attributes:
        key (str): ключ группы в файле конфигурации.
        title (str): подпись строки.
        size (int): сколько уровней HH в группе.
    """
    key: str
    title: str
    size: int


# Порядок групп = порядок индексов HH в прошивке: 6 «электронных» + 2 «условный
# max» + шесть протонных групп по 4 (см. mpp_hh_level_get_coef_elv_lsb).
_GROUPS: list[LevelGroup] = [
    LevelGroup("electrons", "Электроны 0,1–5 МэВ", 6),
    LevelGroup("electrons_max", "Электроны · Усл. max 1,2–8 МэВ", 2),
    LevelGroup("protons_10_30", "Протоны 10..30 МэВ", 4),
    LevelGroup("protons_30_60", "Протоны 30..60 МэВ", 4),
    LevelGroup("protons_60_100", "Протоны 60..100 МэВ", 4),
    LevelGroup("protons_100_200", "Протоны 100..200 МэВ", 4),
    LevelGroup("protons_200_500", "Протоны 200..500 МэВ", 4),
    LevelGroup("protons_500", "Протоны > 500 МэВ", 4),
]
#: Индекс первого уровня каждой группы в плоском массиве HH.
_GROUP_START: list[int] = [sum(g.size for g in _GROUPS[:i]) for i in range(len(_GROUPS))]

# Коэффициенты пересчёта: ключ структуры прошивки -> подпись поля. Единицы — из
# сишного кода (coef_elv_lsb, lsb/MeV), а не «кэВ на квант».
_COEF_FIELDS: tuple[tuple[str, str], ...] = (
    ("pd_k", "k ПД1, кв. АЦП/МэВ"),
    ("sc_k", "k СцД1, кв. АЦП/МэВ"),
    ("pd_b", "b, кв. АЦП"),
)
_DEFAULT_COEF: dict[str, int] = {"pd_k": 400, "sc_k": 48, "pd_b": 400}

_UNIT_KEV, _UNIT_LSB = "кэВ", "кв. АЦП"
#: Файл конфигурации уровней, который подставляется при старте.
_DEFAULT_CONFIG = Path(__file__).parent.joinpath("mpp_levels_default.json")
_MAX_U16 = 0xFFFF


# --- пересчёт кэВ ↔ кв. АЦП (перенос сишного кода прошивки ЦМ) ---------------
def coef_elv_lsb(index: int, pd_k: int, sc_k: int, pd_b: int) -> int:
    """Коэффициент пересчёта одного уровня HH, кв. АЦП/МэВ.

    Перенос ``mpp_hh_level_get_coef_elv_lsb``: у уровней 0..5 и 7 в коэффициент
    входит восьмикратный СцД1, у уровня 6 — только ПД1, а в протонных группах
    (с 8-го) первые два уровня идут по ПД1, вторые два — по СцД1.

    Args:
        index (int): номер уровня HH [0..``HH_LEVEL_NUM``).
        pd_k (int): коэффициент ПД1 (``pd_k_elv_lsb``).
        sc_k (int): коэффициент СцД1 (``sc_k_elv_lsb``).
        pd_b (int): смещение (``pd_b_elv_lsb``).

    Returns:
        Коэффициент, обрезанный до uint16 — как в прошивке.
    """
    if index < 6 or index == 7:
        return (pd_k + 8 * sc_k + pd_b) & _MAX_U16
    if index == 6:
        return (pd_k + pd_b) & _MAX_U16
    if (index - 8) % 4 < 2:
        return (pd_k + pd_b) & _MAX_U16
    return (8 * sc_k + pd_b) & _MAX_U16


def kev_to_lsb(kev: int, coef: int) -> int:
    """Уровень из кэВ в кванты АЦП (перенос ``mpp_hh_level_kev_to_lsb``)."""
    return ((kev * coef + 500) // 1000) & _MAX_U16


def lsb_to_kev(lsb: int, coef: int) -> int:
    """Уровень из квантов АЦП обратно в кэВ (обратная к :func:`kev_to_lsb`).

    Прямой пересчёт — целочисленный с округлением, поэтому в один квант АЦП
    попадает целая полоса кэВ ``[lsb*1000 - 500, lsb*1000 + 499] / coef``. Берём
    из этой полосы целое, ближайшее к середине: тогда обратный ход не «уезжает»
    (``kev_to_lsb(lsb_to_kev(x)) == x``). При ``coef > 1000`` квант мельче одного
    кэВ, и в полосе целого может не оказаться — тогда возвращается ближайшее кэВ,
    и точный обратный ход невозможен в принципе.
    """
    if coef <= 0:
        return 0
    nearest = round(lsb * 1000 / coef)
    low = -((500 - lsb * 1000) // coef)          # ceil((lsb*1000 - 500) / coef)
    high = (lsb * 1000 + 499) // coef
    if low <= high:                              # в полосе есть целые кэВ
        nearest = min(max(nearest, low), high)
    return max(0, min(nearest, _MAX_U16))


@dataclass(frozen=True)
class LevelsConfig:
    """Содержимое файла конфигурации уровней.

    Attributes:
        levels_kev (list[int]): 32 уровня HH в кэВ (в порядке групп).
        coefficients (dict[str, int]): коэффициенты пересчёта (``pd_k``/``sc_k``/``pd_b``).
        name (str): имя конфигурации из файла (для подписи в сравнении).
    """
    levels_kev: list[int]
    coefficients: dict[str, int]
    name: str = ""


def load_levels_config(path: str | Path) -> LevelsConfig:
    """Прочитать файл конфигурации уровней (JSON).

    Уровни берутся из ``levels_kev``: либо словарь «ключ группы -> список уровней»,
    либо плоский список из ``HH_LEVEL_NUM`` значений. Коэффициенты — из
    ``coefficients`` (чего нет в файле, берётся из значений по умолчанию).

    Args:
        path (str | Path): путь к файлу.

    Returns:
        Разобранная конфигурация.

    Raises:
        ValueError: уровней не ``HH_LEVEL_NUM`` или файл не разбирается как JSON.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = data.get("levels_kev", data) if isinstance(data, dict) else data
    if isinstance(raw, dict):
        levels = [int(value) for group in _GROUPS for value in raw.get(group.key, ())]
    else:
        levels = [int(value) for value in raw]
    if len(levels) != HH_LEVEL_NUM:
        raise ValueError(f"уровней {len(levels)}, ожидалось {HH_LEVEL_NUM}")
    coefficients = dict(_DEFAULT_COEF)
    for key, value in (data.get("coefficients", {}) if isinstance(data, dict) else {}).items():
        if key in coefficients:
            coefficients[key] = int(value)
    name = str(data.get("name", "")) if isinstance(data, dict) else ""
    return LevelsConfig(levels, coefficients, name)


class MPPLevel(QWidget):
    """Пороговые уровни МПП: таблица уровней, коэффициенты и файл конфигурации.

    Attributes:
        table_levels (LevelTable): таблица уровней «группа × колонки».
        button_refresh (IconButton): чтение уровней из регистров МПП.
        segmented_unit (SegmentedControl): единицы в полях таблицы (кэВ / кв. АЦП).
        button_apply (PrimaryButton): запись уровней и коэффициентов в прибор.
        lineEdit_config (LineEdit): путь к файлу конфигурации уровней.
    """

    table_levels: LevelTable
    button_refresh: IconButton
    segmented_unit: SegmentedControl
    button_apply: PrimaryButton
    lineEdit_config: LineEdit

    def __init__(self, client=None, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.cm_ib: ModbusCMCommand | None = None    # берутся у ConnectionBar при подключении
        self.mpp_ib: ModbusMPPCommand | None = None
        self.logger = logger
        self.parser = Parsers()

        self._coef: dict[str, int] = dict(_DEFAULT_COEF)
        self._levels_kev: list[int] = [0] * HH_LEVEL_NUM
        self._levels_lsb: list[int] = [0] * HH_LEVEL_NUM
        self._coef_edits: dict[str, LineEdit] = {}

        self._build_widget_wholly()
        self._load_default_config()
        self._refresh_table()
        self._wire_connection()

    # --- сборка --------------------------------------------------------------
    def _build_widget_wholly(self) -> None:
        """Собирает виджет целиком: таблица уровней, «Применить», нижние карточки."""
        holder = QWidget()
        holder.setStyleSheet("background: transparent;")
        vcontainer = QVBoxLayout(holder)
        vcontainer.setContentsMargins(0, 0, 0, 0)
        vcontainer.setSpacing(12)
        vcontainer.addWidget(self._build_topbar())
        vcontainer.addWidget(self._build_table())
        vcontainer.addLayout(self._build_apply_row())
        vcontainer.addLayout(self._build_bottom_row())
        vcontainer.addStretch(1)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self._wrap_scroll(holder))

    def _wrap_scroll(self, holder: QWidget) -> QScrollArea:
        """Положить содержимое в прокручиваемую область (таблица шире и выше окна)."""
        scroll = QScrollArea()
        scroll.setWidget(holder)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        # прозрачный контейнер: сливаемся с фоном рабочей зоны, иначе QScrollArea
        # красит свой фон серым из палитры
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setStyleSheet("background: transparent;")  # type: ignore
        return scroll

    def _build_topbar(self) -> QWidget:
        """Шапка секции: заголовок · линия · кнопка чтения · переключатель единиц."""
        bar = QWidget()
        bar.setStyleSheet("background: transparent;")
        hbox = QHBoxLayout(bar)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(12)
        hbox.addWidget(self._section_title("ПОРОГОВЫЕ УРОВНИ"))
        hbox.addWidget(self._hline(), 1)

        self.button_refresh = IconButton(glyph="refresh", size=34)
        self.button_refresh.setToolTip("Прочитать уровни из регистров МПП")
        self.button_refresh.clicked.connect(self.refresh_levels)

        self.segmented_unit = SegmentedControl([_UNIT_KEV, _UNIT_LSB])
        self.segmented_unit.setToolTip("Единицы в полях таблицы (под полем — вторые)")
        self.segmented_unit.currentChanged.connect(lambda _index: self._refresh_table())

        hbox.addWidget(self.button_refresh)
        hbox.addWidget(self.segmented_unit)
        return bar

    def _build_table(self) -> LevelTable:
        """Таблица уровней: строка на группу, колонок — по самой длинной группе."""
        self.table_levels = LevelTable(columns=max(group.size for group in _GROUPS))
        self.table_levels.set_rows([(group.title, [""] * group.size) for group in _GROUPS])
        self.table_levels.valueEdited.connect(self._on_cell_edited)
        return self.table_levels

    def _build_apply_row(self) -> QHBoxLayout:
        """Строка с кнопкой «Применить» (запись в регистры МПП), прижатой вправо."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        self.button_apply = PrimaryButton("Применить", variant="blue")
        self.button_apply.setMinimumWidth(200)
        self.button_apply.setMinimumHeight(44)
        self.button_apply.setToolTip("Записать уровни в МПП, коэффициенты — в ЦМ")
        self.button_apply.clicked.connect(self.apply_levels)
        row.addWidget(self.button_apply)
        return row

    def _build_bottom_row(self) -> QHBoxLayout:
        """Нижний ряд: карточка коэффициентов и карточка файла конфигурации."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(24)
        row.addLayout(self._build_section("КОЭФФИЦИЕНТЫ ПЕРЕСЧЕТА", self._build_coef_card()), 1)
        row.addLayout(self._build_section("ЗАГРУЗИТЬ КОНФИГУРАЦИЮ УРОВНЕЙ",
                                          self._build_config_card()), 1)
        return row

    def _build_section(self, title: str, body: QWidget) -> QVBoxLayout:
        """Колонка «заголовок секции + карточка»."""
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        column.addWidget(self._section_title(title))
        column.addWidget(body)
        column.addStretch(1)
        return column

    def _build_coef_card(self) -> QFrame:
        """Карточка коэффициентов пересчёта: три поля ``pd_k`` · ``sc_k`` · ``pd_b``."""
        card = self._card()
        box = QVBoxLayout(card)
        box.setContentsMargins(20, 18, 20, 20)
        box.setSpacing(16)
        for key, label in _COEF_FIELDS:
            edit = LineEdit(str(self._coef[key]))
            edit.setFixedWidth(150)
            edit.setFixedHeight(38)
            edit.editingFinished.connect(lambda k=key: self._on_coef_edited(k))
            self._coef_edits[key] = edit

            line = QHBoxLayout()
            line.setContentsMargins(0, 0, 0, 0)
            line.setSpacing(12)
            line.addWidget(self._field_label(label))
            line.addStretch(1)
            line.addWidget(edit)
            box.addLayout(line)
        return card

    def _build_config_card(self) -> QFrame:
        """Карточка файла конфигурации: путь · открыть в редакторе · выбрать · кнопки."""
        card = self._card()
        box = QVBoxLayout(card)
        box.setContentsMargins(20, 18, 20, 20)
        box.setSpacing(16)

        self.lineEdit_config = LineEdit(_DEFAULT_CONFIG.name)
        self.lineEdit_config.setAlignment(Qt.AlignmentFlag.AlignLeft
                                          | Qt.AlignmentFlag.AlignVCenter)
        self.lineEdit_config.setFixedHeight(38)
        self.lineEdit_config.setToolTip(str(_DEFAULT_CONFIG))

        button_edit = IconButton(icon="edit", size=38)
        button_edit.setToolTip("Открыть файл конфигурации в редакторе")
        button_edit.clicked.connect(self.edit_config)
        button_open = IconButton(icon="folder", size=38)
        button_open.setToolTip("Выбрать файл конфигурации")
        button_open.clicked.connect(self.browse_config)

        path_line = QHBoxLayout()
        path_line.setContentsMargins(0, 0, 0, 0)
        path_line.setSpacing(8)
        path_line.addWidget(self.lineEdit_config, 1)
        path_line.addWidget(button_edit)
        path_line.addWidget(button_open)
        box.addLayout(path_line)

        button_compare = PrimaryButton("Сравнить", variant="neutral")
        button_compare.setMinimumHeight(44)
        button_compare.setToolTip("Сравнить уровни файла с тем, что в таблице")
        button_compare.clicked.connect(self.compare_config)
        button_apply_config = PrimaryButton("Применить", variant="neutral")
        button_apply_config.setMinimumHeight(44)
        button_apply_config.setToolTip("Записать уровни файла в ЦМ и обновить его конфигурацию")
        button_apply_config.clicked.connect(self.apply_config)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(16)
        buttons.addWidget(button_compare, 1)
        buttons.addWidget(button_apply_config, 1)
        box.addLayout(buttons)
        return card

    def _card(self) -> QFrame:
        """Пустая карточка в стиле таблицы уровней (панель + рамка + скругление)."""
        card = QFrame()
        card.setObjectName("MPPLevelCard")
        card.setStyleSheet(f"""
            #MPPLevelCard {{
                background-color: {theme.PANEL_BG};
                border: 1px solid {theme.BORDER};
                border-radius: 12px;
            }}
        """)
        return card

    def _section_title(self, text: str) -> QLabel:
        """Заголовок секции: прописные, разреженные, акцентного цвета."""
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {theme.TEXT_LABLE}; font-family: '{_FONT}'; font-size: 13px; "
            "font-weight: 700; letter-spacing: 2px; background: transparent; border: none;")
        return label

    def _field_label(self, text: str) -> QLabel:
        """Подпись поля в карточке."""
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {theme.TEXT}; font-family: '{_FONT}'; font-size: 15px; "
            "background: transparent; border: none;")
        return label

    def _hline(self) -> QFrame:
        """Тонкая линия-заполнитель справа от заголовка секции."""
        line = QFrame()
        line.setObjectName("mppLevelSep")
        line.setFixedHeight(1)
        line.setStyleSheet(f"#mppLevelSep {{ background-color: {theme.BORDER}; border: none; }}")
        return line

    # --- связь ---------------------------------------------------------------
    def _wire_connection(self) -> None:
        """Подписка на события связи: подключились — взять интерфейсы и прочитать
        уровни из МПП; связь потеряна — забыть интерфейсы."""
        if self.client is None:
            return
        self._refresh_interfaces()   # начальные интерфейсы (до подключения — null-клиент)
        self.client.coroutine_finished.connect(self._on_connection_finished)
        self.client.disconnected.connect(self._on_disconnected)

    @qasync.asyncSlot()
    async def _on_connection_finished(self) -> None:
        """Соединение установлено: обновить интерфейсы и прочитать уровни из МПП."""
        self._refresh_interfaces()
        try:
            ready = await self.client.check_connection()  # type: ignore
        except Exception:
            ready = self.client.is_modbus_ready()  # type: ignore
        if ready:
            await self._read_levels()

    def _on_disconnected(self) -> None:
        """Связь потеряна — командные интерфейсы больше не действительны."""
        self.cm_ib = self.mpp_ib = None

    def _refresh_interfaces(self) -> None:
        """Свежие командные интерфейсы ЦМ и МПП."""
        self.cm_ib, self.mpp_ib = self.client.get_commands_interface()  # type: ignore

    # --- уровни: чтение и запись в прибор ------------------------------------
    @qasync.asyncSlot()
    async def refresh_levels(self) -> None:
        """Прочитать уровни из регистров МПП (кнопка ⟳ над таблицей)."""
        await self._read_levels()

    async def _read_levels(self) -> None:
        """Прочитать 32 уровня HH из МПП (кванты АЦП) и разложить по таблице."""
        if self.mpp_ib is None:
            self.logger.error("МПП: нет связи — уровни не прочитаны")
            return
        raw = await self.mpp_ib.get_hh()
        if raw == b"-1":
            self.logger.error("МПП: уровни не прочитаны")
            return
        values = self.parser._u16_values(raw)
        if len(values) < HH_LEVEL_NUM:
            self.logger.error(f"МПП: уровней {len(values)}, ожидалось {HH_LEVEL_NUM}")
            return
        self.set_levels_lsb(values[:HH_LEVEL_NUM])

    @qasync.asyncSlot()
    async def apply_levels(self) -> None:
        """Записать коэффициенты в ЦМ, уровни (кв. АЦП) — в регистры МПП."""
        if self.cm_ib is None or self.mpp_ib is None:
            self.logger.error("Уровни МПП: нет связи — запись не выполнена")
            return
        if await self.cm_ib.set_mpp_coef_elv_lsb(**self._coef) == b"-1":
            self.logger.error("ЦМ: коэффициенты пересчёта не записаны")
            return
        if await self.mpp_ib.set_hh(list(self._levels_lsb)) == b"-1":
            self.logger.error("МПП: уровни не записаны")
            return
        self.logger.debug("Уровни МПП и коэффициенты пересчёта записаны")

    # --- файл конфигурации ---------------------------------------------------
    def browse_config(self) -> None:
        """Выбрать файл конфигурации уровней и подставить его значения в таблицу."""
        path, _filter = QFileDialog.getOpenFileName(
            self, "Файл конфигурации уровней", str(self.config_path().parent),
            "Конфигурация уровней (*.json);;Все файлы (*)")
        if not path:
            return
        config = self._read_config(Path(path))
        if config is None:
            return
        self._set_config_path(Path(path))
        self.set_coefficients(config.coefficients)
        self.set_levels_kev(config.levels_kev)

    def edit_config(self) -> None:
        """Открыть файл конфигурации системным редактором."""
        path = self.config_path()
        if not path.is_file():
            self.logger.error(f"Файл конфигурации не найден: {path}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def compare_config(self) -> None:
        """Показать расхождения файла конфигурации с текущей таблицей."""
        config = self._read_config(self.config_path())
        if config is None:
            return
        dialog = LevelsCompareDialog(config, self.levels_kev(), self.coefficients(), self)
        dialog.exec()

    @qasync.asyncSlot()
    async def apply_config(self) -> None:
        """Записать уровни файла в регистры ЦМ и обновить конфигурацию ЦМ.

        Путь через ЦМ (а не через МПП): в регистры уходят уровни в кэВ, перевод в
        кванты АЦП делает прошивка, а следом идёт команда обновления конфигурации
        (сохранить текущее состояние + применить его).
        """
        config = self._read_config(self.config_path())
        if config is None:
            return
        if self.cm_ib is None:
            self.logger.error("ЦМ: нет связи — конфигурация уровней не записана")
            return
        if await self.cm_ib.set_mpp_coef_elv_lsb(**config.coefficients) == b"-1":
            self.logger.error("ЦМ: коэффициенты пересчёта не записаны")
            return
        if await self.cm_ib.set_mpp_hh_levels(config.levels_kev) == b"-1":
            self.logger.error("ЦМ: уровни из файла не записаны")
            return
        if await self.cm_ib.update_config() == b"-1":
            self.logger.error("ЦМ: конфигурация не обновлена")
            return
        self.set_coefficients(config.coefficients)
        self.set_levels_kev(config.levels_kev)
        self.logger.debug(f"ЦМ: конфигурация уровней обновлена из {self.config_path().name}")

    def config_path(self) -> Path:
        """Путь к файлу конфигурации уровней (из поля ввода)."""
        text = self.lineEdit_config.text().strip()
        if not text:
            return _DEFAULT_CONFIG
        path = Path(text)
        return path if path.is_absolute() else _DEFAULT_CONFIG.parent.joinpath(path)

    def _set_config_path(self, path: Path) -> None:
        """Показать выбранный файл: имя в поле, полный путь — в подсказке."""
        self.lineEdit_config.setText(path.name if path.parent == _DEFAULT_CONFIG.parent
                                     else str(path))
        self.lineEdit_config.setToolTip(str(path))

    def _read_config(self, path: Path) -> LevelsConfig | None:
        """Прочитать конфигурацию уровней; ``None`` и запись в лог при ошибке."""
        try:
            return load_levels_config(path)
        except Exception as ex:  # noqa: BLE001 - битый файл не должен ронять виджет
            self.logger.error(f"Файл конфигурации '{path}' не прочитан: {ex}")
            return None

    def _load_default_config(self) -> None:
        """Подставить уровни из файла по умолчанию (если он есть)."""
        if not _DEFAULT_CONFIG.is_file():
            return
        config = self._read_config(_DEFAULT_CONFIG)
        if config is None:
            return
        self._coef = dict(config.coefficients)
        for key, edit in self._coef_edits.items():
            edit.setText(str(self._coef[key]))
        self._levels_kev = list(config.levels_kev)
        self._levels_lsb = [kev_to_lsb(kev, self._coef_at(index))
                            for index, kev in enumerate(self._levels_kev)]

    # --- значения уровней ----------------------------------------------------
    def levels_kev(self) -> list[int]:
        """Текущие уровни в кэВ (32 значения в порядке групп)."""
        return list(self._levels_kev)

    def levels_lsb(self) -> list[int]:
        """Текущие уровни в квантах АЦП (32 значения в порядке групп)."""
        return list(self._levels_lsb)

    def coefficients(self) -> dict[str, int]:
        """Текущие коэффициенты пересчёта (``pd_k``/``sc_k``/``pd_b``)."""
        return dict(self._coef)

    def set_levels_kev(self, levels: list[int]) -> None:
        """Задать уровни в кэВ; кванты АЦП пересчитываются по коэффициентам."""
        self._levels_kev = [self._clamp(value) for value in levels]
        self._levels_lsb = [kev_to_lsb(kev, self._coef_at(index))
                            for index, kev in enumerate(self._levels_kev)]
        self._refresh_table()

    def set_levels_lsb(self, levels: list[int]) -> None:
        """Задать уровни в квантах АЦП (как их отдаёт МПП); кэВ — обратным пересчётом."""
        self._levels_lsb = [self._clamp(value) for value in levels]
        self._levels_kev = [lsb_to_kev(lsb, self._coef_at(index))
                            for index, lsb in enumerate(self._levels_lsb)]
        self._refresh_table()

    def set_coefficients(self, coefficients: dict[str, int]) -> None:
        """Задать коэффициенты пересчёта; кванты АЦП пересчитываются из кэВ."""
        for key in self._coef:
            if key in coefficients:
                self._coef[key] = self._clamp(coefficients[key])
            self._coef_edits[key].setText(str(self._coef[key]))
        self.set_levels_kev(self._levels_kev)

    def _coef_at(self, index: int) -> int:
        """Коэффициент пересчёта уровня ``index`` при текущих ``pd_k``/``sc_k``/``pd_b``."""
        return coef_elv_lsb(index, **self._coef)

    @staticmethod
    def _clamp(value) -> int:
        """Целое в диапазоне регистра [0, 65535]; мусор — в ноль."""
        try:
            return max(0, min(int(value), _MAX_U16))
        except (TypeError, ValueError):
            return 0

    # --- отрисовка и правка --------------------------------------------------
    def _unit_is_kev(self) -> bool:
        """Показываем ли в полях кэВ (иначе — кванты АЦП)."""
        return self.segmented_unit.currentIndex() == 0

    def _refresh_table(self) -> None:
        """Перерисовать все ячейки таблицы под выбранные единицы."""
        for row, group in enumerate(_GROUPS):
            for col in range(group.size):
                self._refresh_cell(row, col)

    def _refresh_cell(self, row: int, col: int) -> None:
        """Обновить значение ячейки и подпись под ней (вторые единицы)."""
        index = _GROUP_START[row] + col
        kev, lsb = self._levels_kev[index], self._levels_lsb[index]
        value, caption = ((kev, f"{lsb} {_UNIT_LSB}") if self._unit_is_kev()
                          else (lsb, f"{kev} {_UNIT_KEV}"))
        self.table_levels.set_value(row, col, str(value))
        self.table_levels.set_caption(row, col, caption)

    def _on_cell_edited(self, row: int, col: int, text: str) -> None:
        """Правка ячейки: пересчитать вторые единицы и нормализовать поле.

        Args:
            row (int): строка (группа уровней).
            col (int): колонка внутри группы.
            text (str): что ввёл пользователь.
        """
        index = _GROUP_START[row] + col
        value = self._clamp(text)
        coef = self._coef_at(index)
        if self._unit_is_kev():
            self._levels_kev[index] = value
            self._levels_lsb[index] = kev_to_lsb(value, coef)
        else:
            self._levels_lsb[index] = value
            self._levels_kev[index] = lsb_to_kev(value, coef)
        self._refresh_cell(row, col)

    def _on_coef_edited(self, key: str) -> None:
        """Правка коэффициента: пересчитать кванты АЦП всех уровней из кэВ."""
        self.set_coefficients({key: self._clamp(self._coef_edits[key].text())})


class LevelsCompareDialog(QDialog):
    """Расхождения файла конфигурации с текущей таблицей уровней (в кэВ).

    Attributes:
        table (DataTable): строки-расхождения «уровень · в таблице · в файле».
    """

    table: DataTable

    def __init__(self, config: LevelsConfig, levels_kev: list[int],
                 coefficients: dict[str, int], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Сравнение с файлом конфигурации")
        self.setMinimumWidth(520)

        self.table = DataTable()
        self.table.set_title(config.name or "Расхождения")
        self.table.set_columns(["Параметр", "В таблице", "В файле"])
        rows = self._diff_rows(config, levels_kev, coefficients)
        self.table.set_rows(rows or [["Расхождений нет", "—", "—"]])

        box = QVBoxLayout(self)
        box.setContentsMargins(20, 18, 20, 16)
        box.setSpacing(12)
        box.addWidget(self.table)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addStretch(1)
        button_close = PrimaryButton("Закрыть", variant="neutral", compact=True)
        button_close.clicked.connect(self.accept)
        buttons.addWidget(button_close)
        box.addLayout(buttons)

    @staticmethod
    def _diff_rows(config: LevelsConfig, levels_kev: list[int],
                   coefficients: dict[str, int]) -> list[list[str]]:
        """Строки-расхождения: сначала уровни (кэВ), затем коэффициенты."""
        rows: list[list[str]] = []
        for row, group in enumerate(_GROUPS):
            for col in range(group.size):
                index = _GROUP_START[row] + col
                current, from_file = levels_kev[index], config.levels_kev[index]
                if current != from_file:
                    rows.append([f"{group.title} · {col + 1}", f"{current} {_UNIT_KEV}",
                                 f"{from_file} {_UNIT_KEV}"])
        for key, label in _COEF_FIELDS:
            if coefficients.get(key) != config.coefficients.get(key):
                rows.append([label, str(coefficients.get(key)),
                             str(config.coefficients.get(key))])
        return rows


if __name__ == "__main__":
    # Сырой запуск (памятка §10): у виджета есть async-слоты, поэтому вместо
    # preview — ручной qasync-скелет.
    import asyncio
    import sys

    from PyQt6.QtWidgets import QApplication

    from dark_pro_widgets import qss

    app = QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())  # тема ddii (как в приложении)

    host = QWidget()
    host.setWindowTitle("Уровни МПП — автономный запуск")
    host.setStyleSheet(f"background-color: {theme.BG};")
    layout = QVBoxLayout(host)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.addWidget(MPPLevel())

    host.resize(1360, 980)
    theme.tint_window_board(int(host.winId()))  # тёмный заголовок ДО show()
    host.show()

    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
