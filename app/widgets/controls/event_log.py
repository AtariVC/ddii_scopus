"""Журнал событий на базе dark_pro_widgets.LogView.

API:
* ``EventLogWidget(parent=None)`` — журнал событий с фильтрами и управлением RX/TX.
* ``EventLogView(parent=None, max_entries=1000)`` — LogView с ограничением истории.
* ``EventLogView.set_filters(levels)`` — выбранные уровни; ``None`` включает все.
"""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qtpy.uic import loadUi

from dark_pro_widgets import LogView, PrimaryButton, theme

from app.src.components.log.config import (
    MODBUS_TRACE_LEVELS, log_init, modbus_capture_levels, set_modbus_capture_levels,
)
from app.src.components.log.qt_sink import ConsoleLogSink

_LEVEL_LABELS = {"WARNING": "WARN", "ERROR": "ERR", "CRITICAL": "CRIT", "SUCCESS": "OK"}
_LEVEL_COLORS = {"WARNING": theme.WARN, "ERROR": theme.ERR,
                 "CRITICAL": theme.ERR, "SUCCESS": theme.OK}
_FILTER_TOOLTIPS = {
    "ALL": "Показать или скрыть все обычные уровни журнала",
    "RX": "Записывать входящие данные Modbus в журнал и файл",
    "TX": "Записывать исходящие данные Modbus в журнал и файл",
}


class EventLogView(LogView):
    """Оформление LogView с ограниченной историей и буквальным выводом сообщений."""

    def __init__(self, parent=None, max_entries: int = 1000) -> None:
        super().__init__(parent)
        self._max_entries = max(1, max_entries)
        self._selected_levels: frozenset[str] | None = None

    def _build_row(self, time: str, level: str, message: str) -> QWidget:
        row = super()._build_row(time, _LEVEL_LABELS.get(level, level), message)
        for label in row.findChildren(QLabel):
            label.setTextFormat(Qt.TextFormat.PlainText)
        return row

    def add(self, time: str, level: str, message: str) -> None:
        super().add(time, level, message)
        stored_level, row = self._rows[-1]
        row.setVisible(self._selected_levels is None or stored_level in self._selected_levels)
        while len(self._rows) > self._max_entries:
            _, row = self._rows.pop(0)
            self._vbox.removeWidget(row)
            row.deleteLater()

    def set_filters(self, levels: set[str] | None) -> None:
        """Показать выбранные уровни; None — все, пустое множество — ни одного."""
        self._selected_levels = None if levels is None else frozenset(level.upper() for level in levels)
        for level, row in self._rows:
            row.setVisible(self._selected_levels is None or level in self._selected_levels)

    def set_filter(self, level: str) -> None:
        """Сохранить совместимость с одиночным фильтром LogView."""
        self.set_filters(None if level.upper() == "ALL" else {level})

    def clear(self) -> None:
        """Очистить историю и освободить виджеты строк."""
        for _, row in self._rows:
            self._vbox.removeWidget(row)
            row.deleteLater()
        self._rows.clear()


class EventLogWidget(QWidget):
    """Поток событий с фильтрами уровней и переключателями трассировки Modbus."""

    layout_filters: QHBoxLayout
    layout_log: QVBoxLayout
    label_title: QLabel

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        loadUi(Path(__file__).with_suffix(".ui"), self)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            f"#EventLogWidget {{ background: {theme.PANEL_BG}; border: 1px solid {theme.BORDER}; "
            "border-radius: 8px; }"
        )
        self.label_title.setStyleSheet(
            f"color: {theme.TEXT}; font-family: {theme.FONT_FAMILY}; font-size: 14px; font-weight: 600;"
        )
        self.log_view = EventLogView()
        self.layout_log.addWidget(self.log_view)
        self._filters = QButtonGroup(self)
        self._filters.setExclusive(False)
        self._filters.buttonClicked.connect(self._on_filter_changed)
        self.sink = ConsoleLogSink(log_init(), self, extra_levels=MODBUS_TRACE_LEVELS)
        self.sink.entriesReady.connect(self.log_view.load)
        self.sink.levelsChanged.connect(self._set_levels)
        self._set_levels(self.sink.levels())

    def _set_levels(self, levels: tuple[str, ...]) -> None:
        buttons = self._filters.buttons()
        select_all = not buttons or any(button.property("log_level") == "ALL" and button.isChecked()
                                        for button in buttons)
        selected = {button.property("log_level") for button in buttons if button.isChecked()}
        capture = modbus_capture_levels()
        for button in self._filters.buttons():
            self._filters.removeButton(button)
            self.layout_filters.removeWidget(button)
            button.deleteLater()
        for level in ("ALL", *levels):
            label = "Все" if level == "ALL" else _LEVEL_LABELS.get(level, level)
            button = PrimaryButton(label, variant="neutral", compact=True)
            button.setCheckable(True)
            button.setProperty("log_level", level)
            button.setToolTip(_FILTER_TOOLTIPS.get(level, ""))
            color = _LEVEL_COLORS.get(level, theme.TEXT_DIM)
            button.setStyleSheet(
                f"QPushButton {{ color: {color}; background: transparent; border: 1px solid {theme.BORDER}; "
                "border-radius: 14px; min-height: 18px; padding: 4px 10px; font-size: 12px; }"
                f"QPushButton:hover {{ border-color: {theme.ACCENT}; }}"
                f"QPushButton:checked {{ color: {theme.ACCENT}; border-color: {theme.ACCENT}; "
                f"background: {theme.rgba(theme.ACCENT, 28)}; }}"
            )
            self._filters.addButton(button)
            self.layout_filters.addWidget(button)
            button.setChecked(level in capture if level in MODBUS_TRACE_LEVELS else select_all or level in selected)
        self._sync_filters()

    def _on_filter_changed(self, button) -> None:
        level = button.property("log_level")
        if level == "ALL":
            for level_button in self._filters.buttons():
                if level_button.property("log_level") not in MODBUS_TRACE_LEVELS:
                    level_button.setChecked(button.isChecked())
        elif level in MODBUS_TRACE_LEVELS:
            set_modbus_capture_levels({item.property("log_level") for item in self._filters.buttons()
                                       if item.isChecked()})
        self._sync_filters()

    def _sync_filters(self) -> None:
        buttons = self._filters.buttons()
        levels = {button.property("log_level") for button in buttons
                  if button.property("log_level") != "ALL"}
        selected = {button.property("log_level") for button in buttons
                    if button.property("log_level") != "ALL" and button.isChecked()}
        normal_levels = levels.difference(MODBUS_TRACE_LEVELS)
        select_all = bool(normal_levels) and selected.intersection(normal_levels) == normal_levels
        for button in buttons:
            if button.property("log_level") == "ALL":
                button.setChecked(select_all)
        self.log_view.set_filters(selected)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.sink.close()
        super().closeEvent(event)


if __name__ == "__main__":
    from dark_pro_widgets.core import preview

    preview(EventLogWidget, title="Журнал событий", size=(1100, 550))
