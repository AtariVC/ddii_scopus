import asyncio
import sys
from pathlib import Path

import qasync
import qtmodern.styles
from pymodbus.client import AsyncModbusSerialClient
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QDoubleValidator, QFont, QIntValidator
from PyQt6.QtWidgets import QGridLayout, QGroupBox, QSizePolicy, QSpacerItem
from qtpy.uic import loadUi

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from modules.Main_Serial.main_serial_dialog import SerialConnect  # noqa: E402
from src.craft_custom_widget import add_serial_widget  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.log_config import log_init, log_s  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
from src.parsers import Parsers  # noqa: E402
from src.parsers_pack import LineEditPack, LineEObj  # noqa: E402
from style.styleSheet import widget_led_off, widget_led_on  # noqa: E402


class FluxWidget(QtWidgets.QDialog):

    lineEdit_0_1            : QtWidgets.QLineEdit
    lineEdit_0_5            : QtWidgets.QLineEdit
    lineEdit_0_8            : QtWidgets.QLineEdit
    lineEdit_1_6            : QtWidgets.QLineEdit
    lineEdit_3              : QtWidgets.QLineEdit
    lineEdit_5              : QtWidgets.QLineEdit
    
    lineEdit_10             : QtWidgets.QLineEdit
    lineEdit_30             : QtWidgets.QLineEdit
    lineEdit_60             : QtWidgets.QLineEdit
    lineEdit_100            : QtWidgets.QLineEdit
    lineEdit_200            : QtWidgets.QLineEdit
    lineEdit_500            : QtWidgets.QLineEdit
    
    lineEdit_hcp_1          : QtWidgets.QLineEdit
    lineEdit_hcp_5          : QtWidgets.QLineEdit
    lineEdit_hcp_10         : QtWidgets.QLineEdit
    lineEdit_hcp_20         : QtWidgets.QLineEdit
    lineEdit_hcp_45         : QtWidgets.QLineEdit
    

    def __init__(self, *args) -> None:
        super().__init__()
        self.parent = args[0]
        loadUi(Path(__file__).parent.joinpath('flux_widget.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        if __name__ != "__main__":
            self.w_ser_dialog: SerialConnect = args[0]
            self.w_ser_dialog.coroutine_finished.connect(self.get_client)
        else:
            pass
