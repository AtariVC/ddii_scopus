import re
import struct
from PyQt6 import QtWidgets
from qtpy.uic import loadUi
from src.log_config import log_init, log_s
# from engine_trapezoid_dialog import EngineTrapezoidFilter
import os
from PyQt6.QtCore import QTimer


class MainMppControlDialog(QtWidgets.QDialog):
    spinBox_0_1: QtWidgets.QSpinBox
    spinBox_0_5: QtWidgets.QSpinBox
    spinBox_0_8: QtWidgets.QSpinBox
    spinBox_1_6: QtWidgets.QSpinBox
    spinBox_3: QtWidgets.QSpinBox
    spinBox_5: QtWidgets.QSpinBox
    spinBox_10: QtWidgets.QSpinBox
    spinBox_30: QtWidgets.QSpinBox
    spinBox_60: QtWidgets.QSpinBox

    pushButton_apply: QtWidgets.QPushButton
    pushButton_ok: QtWidgets.QPushButton

    CM_ID = 1
    F_CODE = 16
    CNTRL_PIPS = 8
    CNTRL_SIPM = 9
    REQUEST_PIPS = 10
    REQUEST_SIPM = 11
    MMP_ENABLE = 12

    def __init__(self, root, **kwargs) -> None:
        super().__init__(root, **kwargs)
        loadUi(os.path.join(os.path.dirname(__file__),  'style/DialogMPPLavelControl.ui'), self)
        self.root = root
        self.pushButton_apply.clicked.connect(self.pushButton_apply_handler)
        self.pushButton_ok.clicked.connect(self.pushButton_ok_handler)
        # self.flag_measure = 1

        
    def pushButton_apply_handler(self) -> None:
        try:
            data = self.set_mpp_lavel()
            self.root.client.write_registers(address = 0x000B, values = data, slave = self.root.mpp_id)
            log_s(self.root.send_handler.mess)
        except Exception as err:
            self.root.logger.debug(err)
    
    def pushButton_ok_handler(self) -> None:
        try:
            data = self.set_mpp_lavel()
            self.root.client.write_registers(address = 0x000B, values = data, slave = self.root.mpp_id)
            log_s(self.root.send_handler.mess)
        except Exception as err:
            self.root.logger.debug(err)
        self.close()

    def set_mpp_lavel(self):
        data = []
        data.append(int(self.spinBox_0_1.text()))
        data.append(int(self.spinBox_0_5.text()))
        data.append(int(self.spinBox_0_8.text()))
        data.append(int(self.spinBox_1_6.text()))
        data.append(int(self.spinBox_3.text()))
        data.append(int(self.spinBox_5.text()))
        data.append(int(self.spinBox_10.text()))
        data.append(int(self.spinBox_30.text()))
        data.append(int(self.spinBox_60.text()))
        return data

        