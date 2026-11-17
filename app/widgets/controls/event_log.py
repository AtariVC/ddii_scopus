"""Журнал событий на базе dark_pro_widgets.LogView.

API:
* ``EventLogWidget(parent=None)`` — поток консольного лога с фильтрами уровней.
* ``EventLogView(parent=None, max_entries=1000)`` — LogView с ограничением истории.
Базовые LogView и log_init не изменяются; фильтры обновляются из конфигурации Loguru.
"""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qtpy.uic import loadUi

from dark_pro_widgets import LogView, PrimaryButton, theme

from app.src.components.log.config import log_init
from app.src.components.log.qt_sink import ConsoleLogSink

_LEVEL_LABELS = {"WARNING": "WARN", "ERROR": "ERR", "CRITICAL": "CRIT", "SUCCESS": "OK"}
_LEVEL_COLORS = {"WARNING": theme.WARN, "ERROR": theme.ERR,
                 "CRITICAL": theme.ERR, "SUCCESS": theme.OK}


class EventLogView(LogView):
    """Оформление LogView с ограниченной историей и буквальным выводом сообщений."""

    def __init__(self, parent=None, max_entries: int = 1000) -> None:
        super().__init__(parent)
        self._max_entries = max(1, max_entries)

    def _build_row(self, time: str, level: str, message: str) -> QWidget:
        row = super()._build_row(time, _LEVEL_LABELS.get(level, level), message)
        for label in row.findChildren(QLabel):
            label.setTextFormat(Qt.TextFormat.PlainText)
        return row

    def add(self, time: str, level: str, message: str) -> None:
        super().add(time, level, message)
        while len(self._rows) > self._max_entries:
            _, row = self._rows.pop(0)
            self._vbox.removeWidget(row)
            row.deleteLater()

    def clear(self) -> None:
        """Очистить историю и освободить виджеты строк."""
        for _, row in self._rows:
            self._vbox.removeWidget(row)
            row.deleteLater()
        self._rows.clear()


class EventLogWidget(QWidget):
    """Поток событий с автоматически обновляемыми фильтрами консольных уровней."""

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
        self._filters.setExclusive(True)
        self._filters.buttonClicked.connect(self._on_filter_changed)
        self.sink = ConsoleLogSink(log_init(), self)
        self.sink.entriesReady.connect(self.log_view.load)
        self.sink.levelsChanged.connect(self._set_levels)
        self._set_levels(self.sink.levels())

    def _set_levels(self, levels: tuple[str, ...]) -> None:
        selected = self._filters.checkedButton()
        current = selected.property("log_level") if selected else "ALL"
        for button in self._filters.buttons():
            self._filters.removeButton(button)
            self.layout_filters.removeWidget(button)
            button.deleteLater()
        current = current if current in ("ALL", *levels) else "ALL"
        for level in ("ALL", *levels):
            button = PrimaryButton("Все" if level == "ALL" else _LEVEL_LABELS.get(level, level),
                                   variant="neutral", compact=True)
            button.setCheckable(True)
            button.setProperty("log_level", level)
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
            button.setChecked(level == current)
        self.log_view.set_filter(current)

    def _on_filter_changed(self, button) -> None:
        self.log_view.set_filter(button.property("log_level"))

    def closeEvent(self, event) -> None:  # noqa: N802
        self.sink.close()
        super().closeEvent(event)


if __name__ == "__main__":
    from dark_pro_widgets.core import preview

    preview(EventLogWidget, title="Журнал событий", size=(1100, 550))
