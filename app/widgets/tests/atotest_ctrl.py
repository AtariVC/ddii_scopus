'''AutotestCtrl - панель управление автотестом

'''

import qasync
from loguru import logger

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget
from dark_pro_widgets.widgets.composite.param_form import ParamForm
from app.src.components.modbus.command_interface import ModbusCMCommand
from app.src.components.modbus.modbus_reg import ModbusReg
from app.src.util.async_task_manager import AsyncTaskManager
from app.src.util.preview import preview

_CTRL_FIELDS = [("Частота импульсов, Гц", 100), ("Количество импульсов", 1000)]

class AutotestCtrl(QWidget):
    """Панель управления автотестом
    Attributes:
        panel_ctrl(ParamForm): форма запуска автотеста
    """

    def __init__(self, client=None, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.cm_ib: ModbusCMCommand | None = None      # берётся у ConnectionBar при подключении ЦМ
        self.reg = ModbusReg()
        self._tasks = AsyncTaskManager()
        self.logger = logger
        self.panel_ctrl = ParamForm()
        self.panel_ctrl.started.connect(self.start_autotest)
        self.panel_ctrl.stopped.connect(self.stop_autotest)
        self._build_widget()

    def _build_widget(self):
        self.panel_ctrl.set_title("Настройка генерации импульсов")
        self.panel_ctrl.set_fields(_CTRL_FIELDS)
        self.panel_ctrl.set_button("Запуск тестирования", "Остановить тестирование")
        vcontainer = QVBoxLayout(self)
        vcontainer.setContentsMargins(0, 0, 0, 0)
        vcontainer.addWidget(self.panel_ctrl)

    def _refresh_cm(self) -> None:
        """Свежий командный интерфейс ЦМ (берётся у ConnectionBar)."""
        if self.client is None:
            self.cm_ib = None
            return
        self.cm_ib, _mpp = self.client.get_commands_interface()

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
    widget = AutotestCtrl
    preview(widget, "AutotestCtrl")