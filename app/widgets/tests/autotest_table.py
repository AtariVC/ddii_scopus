'''AutotestCtrl - панель управление автотестом

'''


import asyncio
import time

import qasync
from loguru import logger

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget
from dark_pro_widgets.core import preview
from dark_pro_widgets.widgets.composite.data_table import DataTable
from app.src.components.modbus.command_interface import ModbusCMCommand
from app.src.components.modbus.modbus_reg import ModbusReg
from app.src.util.async_task_manager import AsyncTaskManager
from dark_pro_widgets.widgets.indicators.badge_label import BadgeLabel

_COLUMN_NAMES = ["КАНАЛ", "ЗАДАНО", "ЗАРЕГ.", "СТАТУС"]
TIMEOUT_S = 60

class AutotestTable(QWidget):
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
        self.table = DataTable()
        self._build_widget()
        self.parent.started.connect(self.start_autotest)
        self.parent.stopped.connect(self.stop_autotest)


    def _build_widget(self):
        self.table.set_title("Результаты автотеста")
        self.table.set_columns(_COLUMN_NAMES)
        vcontainer = QVBoxLayout(self)
        vcontainer.setContentsMargins(0, 0, 0, 0)
        vcontainer.addWidget(self.table)

    def _refresh_cm(self) -> None:
        """Свежий командный интерфейс ЦМ (берётся у ConnectionBar)."""
        if self.client is None:
            self.cm_ib = None
            return
        self.cm_ib, _mpp = self.client.get_commands_interface()

    @qasync.asyncSlot(dict)
    async def request_res_autotest(self) -> None:
        

    @qasync.asyncSlot(dict)
    async def start_autotest(self, params: dict) -> None:
        args = []
        try:
            args = map(int, params.values())
        except Exception as e:
            self.logger.error(e)
        self._refresh_cm()
        if self.cm_ib is None:
            self.logger.warning("Ошибка подключения к ЦМ")
            return
        if await self.cm_ib.write_registers(self.reg.ctrl_reg.START_AUTOTEST, [1, *args]) == b"-1":
            self.logger.error("Не удалось запустить автотест")

    @qasync.asyncSlot()
    async def stop_autotest(self):
        if self.cm_ib is None:
            self.logger.warning("Ошибка подключения к ЦМ")
            return
        if await self.cm_ib.write_registers(self.reg.ctrl_reg.START_AUTOTEST,[0]) == b"-1":
            self.logger.error("Не удалось запустить автотест")



if __name__ == "__main__":
    def _build():
        return AutotestTable()
    preview(_build, title="AutotestCtrl", stretch=False)