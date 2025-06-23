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
        self.init_QObjects()
        # self.parent.run_meas_widget.get_electron_hist_event.subscribe(self.update_gui_data_proton)
        # self.parent.run_meas_widget.get_proton_hist_event.subscribe(self.update_gui_data_proton)
        if __name__ != "__main__":
            self.logger = self.parent.logger
            # self.w_ser_dialog.coroutine_finished.connect(self.get_client)
        else:
            pass

    def init_QObjects(self) -> None:
        self.le_obj_electron: dict[str, QtWidgets.QLineEdit] = {
            "lineEdit_0_1"           : self.lineEdit_0_1,
            "lineEdit_0_5"           : self.lineEdit_0_5,
            "lineEdit_0_8"           : self.lineEdit_0_8,
            "lineEdit_1_6"           : self.lineEdit_1_6,
            "lineEdit_3"             : self.lineEdit_3,
            "lineEdit_5"             : self.lineEdit_5
        }
        self.le_obj_proton: dict[str, QtWidgets.QLineEdit] = {
            "lineEdit_10"             : self.lineEdit_10,
            "lineEdit_30"             : self.lineEdit_30,
            "lineEdit_60"             : self.lineEdit_60,
            "lineEdit_100"            : self.lineEdit_100,
            "lineEdit_200"            : self.lineEdit_200,
            "lineEdit_500"            : self.lineEdit_500
        }
        self.le_obj_hcp: dict[str, QtWidgets.QLineEdit] = {
            "lineEdit_hcp_1"          : self.lineEdit_hcp_1,
            "lineEdit_hcp_5"          : self.lineEdit_hcp_5,
            "lineEdit_hcp_10"         : self.lineEdit_hcp_10,
            "lineEdit_hcp_20"         : self.lineEdit_hcp_20,
            "lineEdit_hcp_45"         : self.lineEdit_hcp_45
        }

    def update_gui_data_electron(self, massage: list) -> None:
        try:
            for i, (key, val) in enumerate(self.le_obj_electron.items()):
                val.setText(str(massage[i]))
        except Exception as e:
            self.logger.error(e)
    

    def update_gui_data_proton(self, massage: list) -> None:
        try:
            for i, (key, val) in enumerate(self.le_obj_proton.items()):
                val.setText(str(massage[i]))
        except Exception as e:
            self.logger.error(e)


    def update_gui_data_hcp(self, massage: list) -> None:
        try:
            for i, (key, val) in enumerate(self.le_obj_hcp.items()):
                val.setText(str(massage[i]))
        except Exception as e:
            self.logger.error(e)