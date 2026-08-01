from pathlib import Path
from typing import Any

from PyQt6 import QtWidgets
from qtpy.uic import loadUi


class TestTablesWidget(QtWidgets.QWidget):
    tableWidget_system_frame: QtWidgets.QTableWidget
    tableWidget_ddii_frame: QtWidgets.QTableWidget

    def __init__(self, *args) -> None:
        super().__init__(*args)
        loadUi(Path(__file__).parent.joinpath("test_tables_widget.ui"), self)
        self._configure_table(self.tableWidget_system_frame)
        self._configure_table(self.tableWidget_ddii_frame)

    def set_system_frame(self, table_data: Any) -> None:
        self._set_table_data(self.tableWidget_system_frame, table_data)

    def set_ddii_frame(self, table_data: Any) -> None:
        self._set_table_data(self.tableWidget_ddii_frame, table_data)

    def _configure_table(self, table: QtWidgets.QTableWidget) -> None:
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)

    def _set_table_data(self, table: QtWidgets.QTableWidget, table_data: Any) -> None:
        columns = [str(column) for column in table_data.columns]
        table.clear()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setRowCount(len(table_data.index))
        for row_idx, row in enumerate(table_data.itertuples(index=False, name=None)):
            for col_idx, value in enumerate(row):
                table.setItem(row_idx, col_idx, QtWidgets.QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()
