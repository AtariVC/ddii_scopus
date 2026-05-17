from pathlib import Path

from PyQt6 import QtWidgets
from qtpy.uic import loadUi


class TestRunnerWidget(QtWidgets.QWidget):
    def __init__(self, *args) -> None:
        super().__init__(*args)
        loadUi(Path(__file__).parent.joinpath("test_runner_widget.ui"), self)

