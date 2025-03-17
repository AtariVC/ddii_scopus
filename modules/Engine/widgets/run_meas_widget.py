from PyQt6 import QtWidgets, QtCore
from qtpy.uic import loadUi
from qasync import asyncSlot
import asyncio
import qtmodern.styles
import sys
import qasync
# from save_config import ConfigSaver
from pathlib import Path

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from src.modbus_worker import ModbusWorker                          # noqa: E402
from src.parsers import  Parsers                                    # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand      # noqa: E402


class RunMaesWidget(QtWidgets.QDialog):
    lineEdit_triger              : QtWidgets.QLineEdit
    pushButton_run_trig_pips     : QtWidgets.QPushButton
    pushButton_autorun           : QtWidgets.QPushButton
    checkBox_enable_test_csa     : QtWidgets.QCheckBox
    gridLayout_meas              : QtWidgets.QGridLayout


    pushButton_autorun_signal           = QtCore.pyqtSignal()
    pushButton_run_trig_pips_signal     = QtCore.pyqtSignal()
    checkBox_enable_test_csa_signal     = QtCore.pyqtSignal()

    def __init__(self, client, logger) -> None:
        super().__init__()
        loadUi(Path().resolve().joinpath('frontend/engineWidget/WidgetRunMeasure.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.task = None
        self.client = client
        self.logger = logger
        self.cm_cmd: ModbusCMCommand = ModbusCMCommand(self.client, self.logger)
        self.mpp_cmd: ModbusMPPCommand = ModbusMPPCommand(self.client, self.logger)
        # self.pushButton_autorun.clicked.connect(self.pushButton_autorun_handler)
        self.pushButton_run_trig_pips.clicked.connect(self.pushButton_run_trig_pips_handler)
        self.checkBox_enable_test_csa.clicked.connect(self.checkBox_enable_test_csa_handler)

    # def pushButton_autorun_handler(self) -> None:
    #     self.pushButton_autorun_signal.emit()

    def pushButton_run_trig_pips_handler(self) -> None:
        self.pushButton_run_trig_pips_signal.emit()
        # self.

    def checkBox_enable_test_csa_handler(self, state) -> None:
        print(state)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    w = RunMaesWidget()
    event_loop = qasync.QEventLoop(app)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    w.show()

    if event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...



