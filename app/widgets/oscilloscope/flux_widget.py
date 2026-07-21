"""Счётчик частиц: пороговые счётчики электронов, протонов и тяжёлых ядер.

Виджет только отображает данные — их присылает ``run_flux_widget`` через события
(``update_gui_data_electron`` / ``_proton`` / ``_hcp`` / ``update_data_acq``).
Разметка — ``flux_widget.ui``: плитки объявлены там как promoted-виджеты
``_Tile``/``_TileAccent``, подписи заданы свойством ``label``.

Виджет можно запустить отдельно, с демо-данными (из корня проекта):

    python -m app.widgets.oscilloscope.flux_widget
"""

import math
from pathlib import Path

from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtProperty
from qtpy.uic import loadUi

from dark_pro_widgets import theme
from dark_pro_widgets.stat_tile import StatTile

from app.src.components.log.config import log_init
from app.src.components.modbus.worker import ModbusWorker
from app.src.components.parsers.custom_parsers import Parsers

_FONT = theme.FONT_FAMILY.split(",")[0].strip()
_MONO = theme.MONO_FAMILY.split(",")[0].strip()

# Значение-заглушка, пока данные не пришли
_EMPTY = "—"

# Порядки для сокращения счётчиков (от большего к меньшему)
_UNITS = ((1_000_000_000, "G"), (1_000_000, "M"), (1_000, "k"))


def format_count(value) -> str:
    """Сокращает счётчик: ``842000 -> '842k'``, ``1240000 -> '1.24M'``.

    Меньше тысячи показывается как есть (``403``). Точность — три значащие
    цифры, хвостовые нули убираются (``47000 -> '47k'``, а не ``'47.0k'``).
    Нечисловое значение возвращается без изменений — виджет не должен падать
    из-за неожиданных данных от прибора.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return str(value)

    sign = "-" if number < 0 else ""
    number = abs(number)

    if number < 1000:
        return f"{sign}{number:.0f}" if number.is_integer() else f"{sign}{number:.6g}"

    def _decimals(scaled: float) -> int:
        # три значащие цифры: 842 / 88.2 / 8.90
        return 0 if scaled >= 100 else (1 if scaled >= 10 else 2)

    for index, (threshold, suffix) in enumerate(_UNITS):
        if number >= threshold:
            scaled = number / threshold
            decimals = _decimals(scaled)
            # округление может переполнить разряд: 999 999 дало бы '1000k' вместо '1M'
            if round(scaled, decimals) >= 1000 and index > 0:
                threshold, suffix = _UNITS[index - 1]  # noqa: PLW2901 - переходим на старший разряд
                scaled = number / threshold
                decimals = _decimals(scaled)
            text = f"{scaled:.{decimals}f}"
            if "." in text:  # только при наличии точки, иначе '840' -> '84'
                text = text.rstrip("0").rstrip(".")
            return f"{sign}{text}{suffix}"
    return f"{sign}{number:.0f}"


# --- promotion-адаптеры (см. <customwidget> в flux_widget.ui) -----------------

class _Tile(StatTile):
    """Плитка «подпись + значение».

    ``StatTile`` требует ``(label, value, parent)``, а загрузчик .ui создаёт
    виджет как ``Class(parent)`` — отсюда адаптер. Плюс базовый ``setLabel``
    переводит подпись в верхний регистр, а по макету подписи строчные
    (``e > 0.1``, ``p > 10``), поэтому свойство переопределено.
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # StatTile стилизует карточку селектором #StatTile (по objectName), а
        # loadUi после конструктора переименовывает виджет в имя из .ui — селектор
        # перестаёт совпадать и фон/рамка пропадают. Задаём стиль без привязки к имени.
        self.setStyleSheet(
            f"QFrame {{ background-color: {theme.FIELD_BG};"
            f" border: 1px solid {theme.BORDER}; border-radius: 8px; }}"
        )

    def setLabel(self, text):  # noqa: N802 - имя из Qt-свойства
        self._label.setText(str(text))

    label = pyqtProperty(str, StatTile.getLabel, setLabel)


class _TileAccent(_Tile):
    """Плитка ACQ: акцентный цвет и более крупное значение."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._value.setStyleSheet(
            f"color: {theme.ACCENT}; font-size: 26px; font-weight: 700; "
            f"font-family: {_MONO}; border: none; background: transparent;"
        )


class FluxWidget(QtWidgets.QDialog):
    # ACQ
    tile_acq1: _TileAccent
    tile_acq2: _TileAccent
    # подписи групп (общий заголовок панели рисует колонка инспектора)
    title_e: QtWidgets.QLabel
    title_p: QtWidgets.QLabel
    title_hcp: QtWidgets.QLabel

    def __init__(self) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath("flux_widget.ui"), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.logger = log_init()
        self.init_QObjects()
        self._apply_theme()

    def init_QObjects(self) -> None:
        """Плитки в том же порядке, в каком приходят значения от МПП."""
        self.tiles_electron: list[_Tile] = [
            self.tile_e_0_1, self.tile_e_0_5, self.tile_e_0_8,
            self.tile_e_1_6, self.tile_e_3, self.tile_e_5,
        ]
        self.tiles_proton: list[_Tile] = [
            self.tile_p_10, self.tile_p_30, self.tile_p_60,
            self.tile_p_100, self.tile_p_200, self.tile_p_500,
        ]
        self.tiles_hcp: list[_Tile] = [
            self.tile_hcp_1, self.tile_hcp_5, self.tile_hcp_10,
            self.tile_hcp_20, self.tile_hcp_45,
        ]

    def _apply_theme(self) -> None:
        """Подписи групп — тусклые. Общий заголовок панели («СЧЁТЧИК ЧАСТИЦ»)
        рисует колонка инспектора, поэтому внутри виджета его нет.
        """
        for lbl in (self.title_e, self.title_p, self.title_hcp):
            lbl.setStyleSheet(
                f"color: {theme.TEXT_DIM}; font-family: '{_FONT}'; font-size: 12px; "
                "background: transparent; border: none;"
            )

    # ===== приём данных (контракт для run_flux_widget) =====
    @staticmethod
    def _fill(tiles: list, values: list, compact: bool = True) -> None:
        """Раскладывает значения по плиткам.

        ``compact`` — сокращать ли большие числа (k/M). Точное значение уходит
        в подсказку, поэтому округление ничего не скрывает: навёл — увидел.
        """
        for tile, value in zip(tiles, values):
            if value is None:
                tile.setValue(_EMPTY)
                tile.setToolTip("")
                continue
            exact = str(value)
            tile.setValue(format_count(value) if compact else exact)
            tile.setToolTip(exact)

    def update_gui_data_electron(self, massage: list) -> None:
        try:
            self._fill(self.tiles_electron, massage)
        except Exception as e:
            self.logger.error(str(e))

    def update_gui_data_proton(self, massage: list) -> None:
        try:
            self._fill(self.tiles_proton, massage)
        except Exception as e:
            self.logger.error(str(e))

    def update_gui_data_hcp(self, massage: list) -> None:
        try:
            self._fill(self.tiles_hcp, massage)
        except Exception as e:
            self.logger.error(str(e))

    def update_data_acq(self, acq: list[str]) -> None:
        # ACQ — пик АЦП, а не счётчик частиц: показываем как есть, без k/M
        try:
            self._fill([self.tile_acq1, self.tile_acq2], acq, compact=False)
        except Exception as e:
            self.logger.error(str(e))

    def clear_values(self) -> None:
        """Сбросить все значения в прочерк (например, при обрыве связи)."""
        for tile in (*self.tiles_electron, *self.tiles_proton, *self.tiles_hcp,
                     self.tile_acq1, self.tile_acq2):
            tile.setValue(_EMPTY)


if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget

    from dark_pro_widgets import qss

    app = QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())  # тема ddii (как в приложении)

    # хост-окно повторяет колонку инспектора: тот же фон и ширина
    host = QWidget()
    host.setWindowTitle("Счётчик частиц — автономный запуск")
    host.setStyleSheet(f"background-color: {theme.BG};")
    layout = QVBoxLayout(host)
    layout.setContentsMargins(16, 16, 16, 16)

    widget = FluxWidget()
    layout.addWidget(widget)
    layout.addStretch()

    # демо-данные, чтобы плитки не стояли пустыми
    widget.update_data_acq(["0", "0"])
    widget.update_gui_data_electron(["0", "0", "0", "0", "0", "0"])
    widget.update_gui_data_proton(["0", "0", "0", "0", "0", "0"])
    widget.update_gui_data_hcp(["0", "0", "0", "0", "0"])

    host.resize(376, 720)
    host.show()
    sys.exit(app.exec())
