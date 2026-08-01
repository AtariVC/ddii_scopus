from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from PyQt6 import QtCore, QtWidgets
from qtpy.uic import loadUi


class DebugTableWidget(QtWidgets.QWidget):
    """Debug table: group box with a two-column table.

    Left column: telemetry name, right column: current value.
    Provides helpers to pre-create rows and update values efficiently.
    """

    tableWidget: QtWidgets.QTableWidget

    def __init__(self, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath("debug_table.ui"), self)
        self._configure_table()

    def _configure_table(self) -> None:
        tw = self.tableWidget
        tw.setColumnCount(2)
        tw.setHorizontalHeaderLabels(["Название", "Значение"])
        tw.horizontalHeader().setStretchLastSection(True)
        tw.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        tw.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        tw.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        tw.verticalHeader().setVisible(False)
        # Name column a bit wider by default
        tw.setColumnWidth(0, 220)

    # --- Public API ---
    def set_rows(self, names: list[str]) -> None:
        """Create rows with given telemetry names; values are left empty."""
        tw = self.tableWidget
        tw.setRowCount(len(names))
        for row, name in enumerate(names):
            name_item = QtWidgets.QTableWidgetItem(str(name))
            value_item = QtWidgets.QTableWidgetItem("")
            # Make sure they are not editable
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            value_item.setFlags(value_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            tw.setItem(row, 0, name_item)
            tw.setItem(row, 1, value_item)

    def update_value(self, name: str, value: Any) -> None:
        """Update a single telemetry value by name. Adds a new row if name not found."""
        row = self._find_row_by_name(name)
        if row is None:
            row = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row)
            name_item = QtWidgets.QTableWidgetItem(str(name))
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.tableWidget.setItem(row, 0, name_item)
        value_item = self.tableWidget.item(row, 1)
        if value_item is None:
            value_item = QtWidgets.QTableWidgetItem("")
            value_item.setFlags(value_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.tableWidget.setItem(row, 1, value_item)
        value_item.setText(self._to_text(value))

    def update_values(self, mapping: dict[str, Any]) -> None:
        """Bulk update from a name->value mapping."""
        for k, v in mapping.items():
            self.update_value(k, v)

    # --- Helpers ---
    def _find_row_by_name(self, name: str) -> Optional[int]:
        tw = self.tableWidget
        for row in range(tw.rowCount()):
            item = tw.item(row, 0)
            if item and item.text() == name:
                return row
        return None

    def _to_text(self, value: Any) -> str:
        if value is None:
            return "—"
        try:
            return str(value)
        except Exception:
            return "—"


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = DebugTableWidget()
    w.set_rows(["Температура", "Напряжение", "Ток"])
    w.update_values({"Температура": "36.6 °C", "Напряжение": "12.1 V", "Ток": "0.42 A"})
    w.resize(480, 320)
    w.show()
    sys.exit(app.exec())
