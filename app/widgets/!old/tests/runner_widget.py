from pathlib import Path
from typing import Optional
import qasync
from PyQt6 import QtWidgets
from qtpy.uic import loadUi
from loguru import logger

from app.src.components.modbus.ddii_command import ModbusCMCommand


class TestRunnerWidget(QtWidgets.QWidget):
    spinBox_dur_imp: QtWidgets.QSpinBox
    pushButton_start_test: QtWidgets.QPushButton
    pushButton_enable_impl: QtWidgets.QPushButton
    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.logger = logger
        self._mw = args[0] if args else None
        self.cm_cmd: Optional[ModbusCMCommand] = None
        loadUi(Path(__file__).parent.joinpath("test_runner_widget.ui"), self)
        self.pushButton_start_test.clicked.connect(self.pushButton_start_test_handler)
        self.pushButton_enable_impl.clicked.connect(self.pushButton_enable_impl_handler)

    def pushButton_start_test_handler(self):
        ...

    @qasync.asyncSlot(bool)
    async def pushButton_enable_impl_handler(self):
        value: int = self.spinBox_dur_imp.value()
        if not isinstance(value, int):
            value = 0
            self.logger.warning(f"Invalid value for impact time: {value}, defaulting to 0")
            raise ValueError(f"Invalid value for impact time: {value}")
        result = await self.cm_cmd.set_test_gpio_impact(value)

