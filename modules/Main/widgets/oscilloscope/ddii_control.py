import asyncio
import sys
from pathlib import Path

import qasync
import qtmodern.styles
from pymodbus.client import AsyncModbusSerialClient
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QDoubleValidator, QFont, QIntValidator
from PyQt6.QtWidgets import QGroupBox, QLineEdit, QSizePolicy, QSpacerItem, QVBoxLayout
from qtpy.uic import loadUi

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parents[4]
modules_path = Path(__file__).resolve().parents[3]
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from modules.Main_Serial.main_serial_dialog_tcp import SerialConnect  # noqa: E402
from src.async_task_manager import AsyncTaskManager  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.env_var import EnvironmentVar  # noqa: E402
from src.log_config import log_init  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
from src.parsers import Parsers  # noqa: E402
from src.parsers_pack import LineEditPack, LineEObj  # noqa: E402


class DDIIControlWidget(QtWidgets.QWidget):
    lineEdit_hvip_pips: QtWidgets.QLineEdit
    lineEdit_hvip_sipm: QtWidgets.QLineEdit
    lineEdit_hvip_ch: QtWidgets.QLineEdit

    lineEdit_pwm_sipm: QtWidgets.QLineEdit
    lineEdit_pwm_pips: QtWidgets.QLineEdit
    lineEdit_pwm_ch: QtWidgets.QLineEdit

    lineEdit_lvl_0_1: QtWidgets.QLineEdit
    lineEdit_lvl_0_5: QtWidgets.QLineEdit
    lineEdit_lvl_0_8: QtWidgets.QLineEdit
    lineEdit_lvl_1_6: QtWidgets.QLineEdit
    lineEdit_lvl_3: QtWidgets.QLineEdit
    lineEdit_lvl_5: QtWidgets.QLineEdit

    def __init__(self, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).parent / "ddii_control.ui", self)
        # self.parent = parent
        self.mw = ModbusWorker()
        self.logger = log_init()
        i_validator = QIntValidator()
        d_validator = QDoubleValidator()


# self.initValidator(i_validator, d_validator)

# def initValidator(self, validator, d_validator) -> None:
#     self.lineEdit_lvl_0_1.setValidator(validator)
#     self.lineEdit_lvl_0_5.setValidator(validator)
#     self.lineEdit_lvl_0_8.setValidator(validator)
#     self.lineEdit_lvl_1_6.setValidator(validator)
#     self.lineEdit_lvl_3.setValidator(validator)
#     self.lineEdit_lvl_5.setValidator(validator)
#     self.lineEdit_lvl_10.setValidator(validator)
#     self.lineEdit_lvl_30.setValidator(validator)
#     self.lineEdit_lvl_60.setValidator(validator)
#     self.lineEdit_pwm_pips.setValidator(d_validator)
#     self.lineEdit_hvip_pips.setValidator(d_validator)
#     self.lineEdit_pwm_sipm.setValidator(d_validator)
#     self.lineEdit_hvip_sipm.setValidator(d_validator)
#     self.lineEdit_pwm_ch.setValidator(d_validator)
#     self.lineEdit_hvip_ch.setValidator(d_validator)
#     self.lineEdit_interval.setValidator(d_validator)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    # light(app)
    logger = log_init()
    w_ser_dialog: SerialConnect = SerialConnect(logger)
    w: DDIIControlWidget = DDIIControlWidget(w_ser_dialog)
    vLayout_ser_connect: QVBoxLayout = QVBoxLayout()
    w.setLayout(vLayout_ser_connect)
    vLayout_ser_connect.addWidget(w_ser_dialog)

    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    w.show()

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
