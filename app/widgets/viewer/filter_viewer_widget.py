from __future__ import annotations

from pathlib import Path
from typing import List

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QWidget
from qtpy.uic import loadUi

from dark_pro_widgets.core import theme
from dark_pro_widgets.widgets.controls import CheckBox, IconButton, LineEdit, PrimaryButton

_MONO = theme.MONO_FAMILY.split(",")[0].strip()


class FilterViewerWidget(QWidget):
    """Фильтр кадров для Viewer: порог + выбор каналов + навигация.

    Ожидает, что родитель передан как MainUIRenderer и содержит graph_viewer_widget.
    Список найденных кадров (``listWidget_times``) здесь только размещается и
    стилизуется — его наполнение вынесено в отдельную библиотеку.
    """

    label_found: QtWidgets.QLabel
    label_save: QtWidgets.QLabel
    checkBox_pips: CheckBox
    lineEdit_threshold_pips: LineEdit
    checkBox_sipm: CheckBox
    lineEdit_threshold_sipm: LineEdit
    pushButton_filter: PrimaryButton
    pushButton_prev: IconButton
    pushButton_next: IconButton
    listWidget_times: QtWidgets.QListWidget
    pushButton_save_frame: PrimaryButton
    lineEdit_num_frame: LineEdit

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mw = parent  # MainUIRenderer or None
        loadUi(Path(__file__).parent.joinpath("filter_viewer_widget.ui"), self)
        self._matched: List[int] = []  # 1-based индексы кадров
        # подписка нужна только когда есть настоящий viewer (в приложении);
        # при автономном запуске parent=None — просто пропускаем
        _gw = self._viewer()
        if _gw is not None:
            _gw.slider_update_event.subscribe(lambda val: self.lineEdit_num_frame.setText(str(val)))  # type: ignore
        self._pos: int = -1

        self._implement_style()
        self._wire()

    def _implement_style(self):
        # варианты и глифы кнопок (тема их не задаёт)
        self.pushButton_prev.setGlyph("chevron_left")
        self.pushButton_next.setGlyph("chevron_right")
        self.pushButton_filter.setVariant("accent")
        self.pushButton_save_frame.setVariant("blue")

        # счётчик найденного и подпись сохранения — приглушённый моно
        for lbl in (self.label_found, self.label_save):
            lbl.setStyleSheet(
                f"color: {theme.TEXT_DIM}; font-family: '{_MONO}'; font-size: 13px; "
                "background: transparent; border: none;"
            )

        # карточка списка: рамка со скруглением, отступы, подсветка выбранного
        self.listWidget_times.setStyleSheet(
            f"""
            QListWidget {{
                background-color: {theme.FIELD_BG};
                border: 1px solid {theme.BORDER};
                border-radius: 8px;
                padding: 6px;
                outline: none;
                color: {theme.TEXT};
                font-family: '{_MONO}';
            }}
            QListWidget::item {{ padding: 8px 10px; border-radius: 6px; }}
            QListWidget::item:selected {{
                background-color: {theme.rgba(theme.ACCENT, 40)};
                color: {theme.TEXT};
            }}
            QListWidget::item:hover {{ background-color: {theme.rgba(theme.ACCENT, 18)}; }}
            """
        )

    def _wire(self) -> None:
        self.pushButton_filter.clicked.connect(self._on_filter)
        self.pushButton_prev.clicked.connect(lambda: self._step(-1))
        self.pushButton_next.clicked.connect(lambda: self._step(+1))
        self.listWidget_times.itemClicked.connect(self._on_pick)
        self.pushButton_save_frame.clicked.connect(self._save_frame)

    def _save_frame(self):
        num_frame: int = int(self.lineEdit_num_frame.text())
        self._mw.graph_viewer_widget.save_desired_frame_hdf5(num_frame) # type: ignore

    def _viewer(self):
        return getattr(self._mw, "graph_viewer_widget", None)

    def _on_filter(self):
        gv = self._viewer()
        if gv is None:
            return
        try:
            lvl_pips = int(self.lineEdit_threshold_pips.text()) if self.lineEdit_threshold_pips.text() else 0
        except Exception:
            lvl_pips = 0
        try:
            lvl_sipm = int(self.lineEdit_threshold_sipm.text()) if self.lineEdit_threshold_sipm.text() else 0
        except Exception:
            lvl_sipm = 0
        use_pips = self.checkBox_pips.isChecked()
        use_sipm = self.checkBox_sipm.isChecked()
        matched = gv.apply_filter(lvl_pips, lvl_sipm, use_pips, use_sipm)
        self._matched = matched
        self._pos = 0 if matched else -1
        self.label_found.setText(f"Найдено {len(matched)} кадров")
        self.listWidget_times.clear()
        for idx in matched:
            self.listWidget_times.addItem(f"{idx}: {gv.get_time_for_index(idx)}")
        # Jump to first match
        if self._pos != -1:
            gv.go_to_index(self._matched[self._pos])
            try:
                self.listWidget_times.setCurrentRow(self._pos)
            except Exception:
                ...

    def _step(self, step: int):
        gv = self._viewer()
        if gv is None or not self._matched:
            return
        self._pos = max(0, min(len(self._matched) - 1, self._pos + step))
        self.lineEdit_num_frame.setText(str(self._pos))
        gv.go_to_index(self._matched[self._pos])
        try:
            self.listWidget_times.setCurrentRow(self._pos)
        except Exception:
            ...

    def _on_pick(self, _item):
        gv = self._viewer()
        if gv is None:
            return
        row = self.listWidget_times.currentRow()
        if 0 <= row < len(self._matched):
            self._pos = row
            gv.go_to_index(self._matched[self._pos])

if __name__ == "__main__":
    from dark_pro_widgets.core._preview import preview
    preview(FilterViewerWidget, title="Фильтр кадров — demo", size=(340, 560), stretch=False)
