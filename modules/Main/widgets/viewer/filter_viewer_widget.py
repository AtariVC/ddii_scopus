
from __future__ import annotations
from pathlib import Path
from typing import List
import qtmodern.styles
import qasync
import asyncio
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
import sys
from PyQt6.QtGui import QIntValidator
from qtpy.uic import loadUi


class FilterViewerWidget(QtWidgets.QWidget):
    """Фильтр кадров для Viewer: порог + выбор каналов + навигация.

    Ожидает, что родитель передан как MainUIRenderer и содержит graph_viewer_widget.
    """

    checkBox_pips: QtWidgets.QCheckBox
    lineEdit_threshold_pips: QtWidgets.QLineEdit
    checkBox_sipm: QtWidgets.QCheckBox
    lineEdit_threshold_sipm: QtWidgets.QLineEdit
    pushButton_apply: QtWidgets.QPushButton
    pushButton_prev: QtWidgets.QPushButton
    pushButton_next: QtWidgets.QPushButton
    listWidget_times: QtWidgets.QListWidget

    pushButton_save_frame: QtWidgets.QPushButton
    lineEdit_num_frame: QtWidgets.QLineEdit

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._mw = parent  # MainUIRenderer or None
        loadUi(Path(__file__).parent.joinpath("filter_viewer_widget.ui"), self)
        # Ensure container reports a reasonable minimum height so outer wrapper
        # (create_tab_widget_items) doesn't clamp it to ~40px and hide content
        self.setMinimumHeight(220)
        self._matched: List[int] = []  # 1-based индексы кадров
        self._pos: int = -1
        self.pushButton_save_frame.clicked.connect(self.pushButton_save_frame_handler)

        # self._build_ui()
        self._wire()

    
    def _wire(self) -> None:
        self.pushButton_apply.clicked.connect(self._on_apply)
        self.pushButton_prev.clicked.connect(lambda: self._step(-1))
        self.pushButton_next.clicked.connect(lambda: self._step(+1))
        self.listWidget_times.itemClicked.connect(self._on_pick)

    def pushButton_save_frame_handler(self):
        num_frame: int = int(self.lineEdit_num_frame.text())
        self.save_desired_frame_hdf5(num_frame) # type: ignore


    def _viewer(self):
        return getattr(self._mw, "graph_viewer_widget", None)

    def _on_apply(self):
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
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    w = FilterViewerWidget()
    w.show()
    app.exec()
