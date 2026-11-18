"""FrameTable — StatTable с управлением обновлением в шапке.

API:
* ``FrameTable(title='', dot=theme.OK, parent=None)`` — карточка кадра.
* ``set_interval(seconds)`` / ``interval()`` — период опроса, 1–60 с.
* ``set_available(bool)`` / ``set_polling(bool)`` — состояние управления.
Signals: ``refreshRequested(continuous, seconds)`` · ``stopRequested()``.
Чтение прибора выполняет владелец; таблица управляет только состоянием кнопок.
"""

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIntValidator
from PyQt6.QtWidgets import QWidget
from qtpy.uic import loadUi

from dark_pro_widgets import CheckBox, IconButton, LineEdit, StatTable, theme


class FrameTable(StatTable):
    """Карточка с разовым обновлением или фиксируемой кнопкой непрерывного опроса."""

    controls: QWidget
    checkbox_continuous: CheckBox
    lineEdit_interval: LineEdit
    button_refresh: IconButton

    refreshRequested = pyqtSignal(bool, int)
    stopRequested = pyqtSignal()

    def __init__(self, title: str = "", dot: str = theme.OK, parent=None) -> None:
        super().__init__(title=title, dot=dot, parent=parent)
        self._interval = 10
        self._build_controls()
        self._wire()
        self.set_polling(False)

    def _build_controls(self) -> None:
        self.controls = QWidget(self)
        loadUi(Path(__file__).with_suffix(".ui"), self.controls)
        self.checkbox_continuous = CheckBox()
        self.checkbox_continuous.setToolTip("Непрерывный опрос: выберите и нажмите «Обновить кадр»")
        self.lineEdit_interval = LineEdit(str(self._interval))
        self.lineEdit_interval.setFixedWidth(54)
        self.lineEdit_interval.setValidator(QIntValidator(1, 60, self.lineEdit_interval))
        self.lineEdit_interval.setToolTip("Интервал опроса, с (1–60)")
        self.button_refresh = IconButton(glyph="refresh")
        self.button_refresh.setToolTip("Обновить кадр")
        self.button_refresh.setStyleSheet(self.button_refresh.styleSheet() + f"""
            QPushButton:checked {{
                background-color: {theme.rgba(theme.ACCENT, 40)};
                border: 1px solid {theme.ACCENT};
            }}
        """)
        self.controls.layout_continuous.addWidget(self.checkbox_continuous)
        self.controls.layout_interval.addWidget(self.lineEdit_interval)
        self.controls.layout_refresh.addWidget(self.button_refresh)
        self.controls.label_seconds.setStyleSheet(
            f"color: {theme.TEXT_DIM}; background: transparent; border: none;"
        )
        # У StatTable нет публичного слота шапки: расширяем её здесь, в одном месте.
        self._tags.parentWidget().layout().addWidget(self.controls)

    def _wire(self) -> None:
        self.checkbox_continuous.toggled.connect(self._on_continuous_changed)
        self.lineEdit_interval.editingFinished.connect(self._commit_interval)
        self.button_refresh.clicked.connect(self._on_refresh_clicked)

    def set_interval(self, seconds: int) -> None:
        """Установить период чтения в секундах."""
        self._interval = max(1, min(int(seconds), 60))
        self.lineEdit_interval.setText(str(self._interval))

    def interval(self) -> int:
        """Текущий период чтения в секундах."""
        return self._interval

    def _commit_interval(self) -> None:
        text = self.lineEdit_interval.text().strip()
        self.set_interval(int(text) if text.isdecimal() else self._interval)

    def set_available(self, available: bool) -> None:
        """Разрешить управление при подключённом ЦМ."""
        self.controls.setEnabled(available)
        if not available:
            self.set_polling(False)

    def set_polling(self, active: bool) -> None:
        """Обновить кнопку и поле интервала без запуска запросов."""
        self.button_refresh.setChecked(active)
        self.lineEdit_interval.setEnabled(self.checkbox_continuous.isChecked() and not active)
        self.button_refresh.setToolTip("Остановить опрос" if active else "Обновить кадр")

    def _on_continuous_changed(self, checked: bool) -> None:
        if not checked:
            self.stopRequested.emit()
        self.button_refresh.setCheckable(checked)
        self.set_polling(False)

    def _on_refresh_clicked(self, checked: bool) -> None:
        continuous = self.checkbox_continuous.isChecked()
        if continuous and not checked:
            self.set_polling(False)
            self.stopRequested.emit()
            return
        self._commit_interval()
        self.set_polling(continuous)
        self.refreshRequested.emit(continuous, self._interval)


if __name__ == "__main__":
    from dark_pro_widgets.core import preview

    preview(lambda: FrameTable("Системный кадр", theme.ACCENT), title="Карточка кадра", size=(640, 240))
