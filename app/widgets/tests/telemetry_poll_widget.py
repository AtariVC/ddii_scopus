from pathlib import Path

from PyQt6 import QtWidgets
from qtpy.uic import loadUi


class TelemetryPollWidget(QtWidgets.QWidget):
    pushButton_run_poll: QtWidgets.QPushButton

    def __init__(self, *args) -> None:
        super().__init__(*args)
        loadUi(Path(__file__).parent.joinpath("telemetry_poll_widget.ui"), self)
        self.pushButton_run_poll.setCheckable(True)
        self.pushButton_run_poll.clicked.connect(self._on_run_poll_clicked)
        self._set_run_button_state(False)

    def _on_run_poll_clicked(self, checked: bool) -> None:
        self._set_run_button_state(checked)

    def _set_run_button_state(self, is_running: bool) -> None:
        if is_running:
            self.pushButton_run_poll.setText("Остановить")
            self.pushButton_run_poll.setToolTip("Остановить опрос")
            return

        self.pushButton_run_poll.setText("Запустить")
        self.pushButton_run_poll.setToolTip("Запустить опрос")
