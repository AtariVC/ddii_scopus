import asyncio
from pathlib import Path
import qasync
from PyQt6 import QtWidgets
from qtpy.uic import loadUi

from dark_pro_widgets import theme
from dark_pro_widgets.buttons import PrimaryButton
from loguru import logger

from app.plugins.connection.connection_bar import ConnectionBar
from app.src.components.modbus.worker import ModbusWorker

class TestImpactControl(QtWidgets.QDialog):
    spinBox_dur_imp_us: QtWidgets.QSpinBox
    pushButton_impact: PrimaryButton

    def __init__(self, *args) -> None:
        super().__init__()
        self.parent = args[0]
        self.logger = logger
        loadUi(Path(__file__).parent.joinpath("test_impact_ctrl.ui"), self)
        self.w_ser_dialog: ConnectionBar = self.parent.w_ser_dialog  # type: ignore
        self.mw = ModbusWorker()
        self.pushButton_impact.setVariant("neutral")
        self.pushButton_impact.clicked.connect(self.pushButton_impact_handler)
        self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)

    # ===== запуск/остановка =====
    @qasync.asyncSlot()
    async def pushButton_impact_handler(self) -> None:
        if not await self.w_ser_dialog.check_connection():
            self.logger.error("Нет подключения (ЦМ/МПП недоступны)")
            return
        self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)
        await self.cm_cmd.set_gpio_impact_autotest()

if __name__ == "__main__":
    import sys
    from types import SimpleNamespace

    from dark_pro_widgets import qss, theme

    from app.src.components.log.config import log_init
    from app.widgets.oscilloscope.flux_widget import FluxWidget

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())

    # Обработчик воздействия — асинхронный, без qasync кнопка не сработает
    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    logger = log_init()

    host_parent = SimpleNamespace(
        w_ser_dialog=ConnectionBar(logger),
        logger=logger,

    )
    widget = TestImpactControl(host_parent)

    host = QtWidgets.QWidget()
    host.setWindowTitle("Воздействие — виджет")
    host.setStyleSheet(f"background-color: {theme.BG};")
    layout = QtWidgets.QVBoxLayout(host)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.addWidget(widget)
    layout.addStretch()

    host.resize(328, 420)
    host.show()

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
