
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


class FilterViewerWidget(QtWidgets.QWidget):
    """Фильтр кадров для Viewer: порог + выбор каналов + навигация.

    Ожидает, что родитель передан как MainUIRenderer и содержит graph_viewer_widget.
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._mw = parent  # MainUIRenderer or None
        # Ensure container reports a reasonable minimum height so outer wrapper
        # (create_tab_widget_items) doesn't clamp it to ~40px and hide content
        self.setMinimumHeight(220)
        self._matched: List[int] = []  # 1-based индексы кадров
        self._pos: int = -1

        self._build_ui()
        self._wire()

    def _build_ui(self) -> None:
        self.setObjectName("FilterViewerWidget")
        layout = QtWidgets.QVBoxLayout(self)
        # Horizontal controls row (no inner group box)
        h = QtWidgets.QHBoxLayout()

        self.label_threshold_pips = QtWidgets.QLabel("Порог PIPS:")
        self.lineEdit_threshold_pips = QtWidgets.QLineEdit()
        self.lineEdit_threshold_pips.setPlaceholderText("Порог PIPS…")
        self.lineEdit_threshold_pips.setFixedWidth(90)
        self.lineEdit_threshold_pips.setValidator(QIntValidator(0, 10000, self))
        self.label_threshold_sipm = QtWidgets.QLabel("Порог SiPM:")
        self.lineEdit_threshold_sipm = QtWidgets.QLineEdit()
        self.lineEdit_threshold_sipm.setPlaceholderText("Порог SiPM…")
        self.lineEdit_threshold_sipm.setFixedWidth(90)
        self.lineEdit_threshold_sipm.setValidator(QIntValidator(0, 10000, self))
        self.checkBox_pips = QtWidgets.QCheckBox("Порог PIPS:")
        self.checkBox_pips.setChecked(True)
        self.checkBox_sipm = QtWidgets.QCheckBox("Порог SiPM:")
        self.checkBox_sipm.setChecked(True)
        # Place indicator after text (checkbox on the right side)
        self.checkBox_pips.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.checkBox_sipm.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.pushButton_apply = QtWidgets.QPushButton("Фильтровать")
        self.pushButton_prev = QtWidgets.QPushButton("<")
        self.pushButton_next = QtWidgets.QPushButton(">")

        for w in (
            self.checkBox_pips,
            self.lineEdit_threshold_pips,
            self.checkBox_sipm,
            self.lineEdit_threshold_sipm,
            self.pushButton_apply,
            self.pushButton_prev,
            self.pushButton_next,
        ):
            h.addWidget(w)

        self.listWidget_times = QtWidgets.QListWidget()
        self.listWidget_times.setMaximumHeight(120)

        layout.addLayout(h)
        layout.addWidget(self.listWidget_times)

    def _wire(self) -> None:
        self.pushButton_apply.clicked.connect(self._on_apply)
        self.pushButton_prev.clicked.connect(lambda: self._step(-1))
        self.pushButton_next.clicked.connect(lambda: self._step(+1))
        self.listWidget_times.itemClicked.connect(self._on_pick)

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
