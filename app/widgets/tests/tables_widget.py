from pathlib import Path

from PyQt6 import QtWidgets
from qtpy.uic import loadUi


class TestTablesWidget(QtWidgets.QWidget):
    tableWidget_system_frame: QtWidgets.QTableWidget
    tableWidget_ddii_frame: QtWidgets.QTableWidget

    def __init__(self, *args) -> None:
        super().__init__(*args)
        loadUi(Path(__file__).parent.joinpath("test_tables_widget.ui"), self)
