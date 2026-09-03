'''AutotestCtrl - панель управление автотестом

'''


import asyncio
import time

import qasync
from loguru import logger

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget
from dark_pro_widgets.core import preview
from app.widgets.tests.atotest_ctrl import AutotestCtrl 
from app.src.components.modbus.command_interface import ModbusCMCommand
from app.src.components.modbus.modbus_reg import ModbusReg
from app.src.util.async_task_manager import AsyncTaskManager



class AutotestWidget(QWidget):
    """Панель управления автотестом
    Attributes:
        panel_ctrl(ParamForm): форма запуска автотеста
    """

    def __init__(self, client=None, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.cm_ib: ModbusCMCommand | None = None  # берётся у ConnectionBar при подключении ЦМ
        self.reg = ModbusReg()
        self._tasks = AsyncTaskManager()
        self.logger = logger
        self.autotest_ctrl = AutotestCtrl()
        self._build_widget_wholly()

    def _build_widget_wholly(self):
        vcontainer = QVBoxLayout(self)
        vcontainer.setContentsMargins(0, 0, 0, 0)
        vcontainer.setSpacing(12)
        vcontainer.addWidget(self.autotest_ctrl, 1)

if __name__ == "__main__":
    def _build() -> AutotestWidget:
        return AutotestWidget()

    preview(_build, title="AutotestWidget", stretch=False)