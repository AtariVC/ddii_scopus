"""FrameTable — StatTable с управлением обновлением в шапке.

API:
* ``FrameTable(title='', dot=theme.OK, parent=None)`` — карточка кадра.
* ``set_interval(seconds)`` / ``interval()`` — период опроса, 1–60 с.
* ``set_available(bool)`` / ``set_polling(bool)`` — состояние управления.
Signals: ``refreshRequested(continuous, seconds)`` · ``stopRequested()``.
Чтение прибора выполняет владелец; таблица управляет только состоянием кнопок.
"""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIntValidator
from PyQt6.QtWidgets import QWidget
from qtpy.uic import loadUi

from dark_pro_widgets import IconButton, LineEdit, StatTable, theme


_CONTROL_HEIGHT = 28


class _IntervalEdit(LineEdit):
    """Адаптер LineEdit для загрузки поля интервала из .ui."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)


class FrameTable(StatTable):
    """Карточка с разовым обновлением или фиксируемой кнопкой непрерывного опроса."""

    controls: QWidget
    button_continuous: IconButton
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
        self.controls.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.controls.setStyleSheet(
            f"#FramePollControls {{ background: {theme.FIELD_BG}; "
            f"border: 1px solid {theme.BORDER}; border-radius: 8px; }}"
        )
        self.button_continuous = self._icon_button("repeat", "Непрерывный опрос")
        self.button_continuous.setCheckable(True)
        self.button_continuous.setToolTip("Непрерывный опрос. Для запуска нажмите «Обновить кадр»")
        self.button_refresh = self._icon_button("update", "Обновить кадр")
        self.lineEdit_interval = self.controls.lineEdit_interval
        self.lineEdit_interval.setFixedSize(46, _CONTROL_HEIGHT)
        self.lineEdit_interval.setValidator(QIntValidator(1, 60, self.lineEdit_interval))
        self.lineEdit_interval.setToolTip("Интервал опроса, с (1–60)")
        self.lineEdit_interval.setStyleSheet(self.lineEdit_interval.styleSheet() + f"""
            QLineEdit {{
                background: transparent; border: 1px solid transparent; border-radius: 5px;
                padding: 0 5px; font-size: 13px;
            }}
            QLineEdit:focus {{ background: {theme.PANEL_BG}; border-color: {theme.ACCENT}; }}
        """)
        suffix = self.controls.label_seconds
        suffix.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        suffix.setStyleSheet(f"color: {theme.TEXT_DIM}; background: transparent; border: none; font-size: 13px;")
        self.lineEdit_interval.setTextMargins(0, 0, suffix.sizeHint().width() + 1, 0)
        self.set_interval(self._interval)
        self.controls.separator_refresh.setStyleSheet(f"background: {theme.BORDER}; border: none;")
        self.controls.layout_continuous.addWidget(self.button_continuous)
        self.controls.layout_refresh.addWidget(self.button_refresh)
        # StatTable не предоставляет публичный слот шапки.
        header = self._tags.parentWidget().layout()
        margins = header.contentsMargins()
        header.setContentsMargins(margins.left(), 8, margins.right(), 8)
        header.addWidget(self.controls)

    @staticmethod
    def _icon_button(icon: str, name: str) -> IconButton:
        button = IconButton(icon=icon, size=_CONTROL_HEIGHT, icon_size=20)
        button.setAccessibleName(name)
        button.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: 1px solid transparent; border-radius: 5px;
                padding: 0;
            }}
            QPushButton:enabled:hover {{ background-color: {theme.rgba(theme.TEXT, 18)}; }}
            QPushButton:enabled:pressed {{ background-color: {theme.rgba(theme.TEXT, 34)}; }}
            QPushButton:enabled:checked {{
                background-color: {theme.rgba(theme.ACCENT, 64)};
                border-color: {theme.rgba(theme.ACCENT, 172)};
            }}
            QPushButton:enabled:checked:hover {{ background-color: {theme.rgba(theme.ACCENT, 86)}; }}
            QPushButton:enabled:checked:pressed {{ background-color: {theme.rgba(theme.ACCENT, 112)}; }}
        """)
        button.toggled.connect(
            lambda checked: button.setIconColor(theme.TEXT_LABLE if checked else theme.TEXT_DIM, theme.TEXT)
        )
        return button

    def _wire(self) -> None:
        self.button_continuous.toggled.connect(self._on_continuous_changed)
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
        self.set_polling(available and self.button_refresh.isChecked())

    def set_polling(self, active: bool) -> None:
        """Обновить кнопку и поле интервала без запуска запросов."""
        self.button_refresh.setChecked(active)
        self.lineEdit_interval.setEnabled(self.button_continuous.isChecked() and not active)
        tooltip = "Остановить опрос" if active else "Обновить кадр"
        if not self.button_refresh.isEnabled():
            tooltip = "Подключите ЦМ, чтобы обновить кадр"
        self.button_refresh.setToolTip(tooltip)

    def _on_continuous_changed(self, checked: bool) -> None:
        if not checked:
            self.stopRequested.emit()
        self.button_refresh.setCheckable(checked)
        self.set_polling(False)

    def _on_refresh_clicked(self, checked: bool) -> None:
        continuous = self.button_continuous.isChecked()
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
