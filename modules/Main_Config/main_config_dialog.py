from PyQt6 import QtWidgets
from qtpy.uic import loadUi
from qasync import QEventLoop, asyncSlot
import qasync
# from engine_trapezoid_dialog import EngineTrapezoidFilter
import os
import struct
# import threading
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import QWidget, QGroupBox, QGridLayout, QSpacerItem, QSizePolicy
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
import qtmodern.styles
from qtmodern.windows import ModernWindow
import sys
from pymodbus.client import AsyncModbusSerialClient

# from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QIntValidator, QDoubleValidator
import logging
from pymodbus.pdu import ModbusResponse
# from modules.dialog_window.main_hvip_dialog import MainHvipDialog as hvip_dialog
# from copy import deepcopy
import asyncio
from pathlib import Path

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from src.modbus_worker import ModbusWorker
from src.ddii_comand import ModbusCMComand, ModbusMPPComand
from src.parsers import  Parsers
from modules.Main_Serial.main_serial_dialog import SerialConnect
from src.log_config import log_init, log_s
from src.env_var import EnviramentVar


class MainConfigDialog(QtWidgets.QDialog):
    lineEdit_pwm_pips                   : QtWidgets.QLineEdit
    lineEdit_hvip_pips                  : QtWidgets.QLineEdit
    lineEdit_pwm_sipm                   : QtWidgets.QLineEdit
    lineEdit_hvip_sipm                  : QtWidgets.QLineEdit
    lineEdit_pwm_ch                     : QtWidgets.QLineEdit
    lineEdit_hvip_ch                    : QtWidgets.QLineEdit
    lineEdit_interval                   : QtWidgets.QLineEdit

    lineEdit_lvl_0_1                    : QtWidgets.QLineEdit
    lineEdit_lvl_0_5                    : QtWidgets.QLineEdit
    lineEdit_lvl_0_8                    : QtWidgets.QLineEdit
    lineEdit_lvl_1_6                    : QtWidgets.QLineEdit
    lineEdit_lvl_3                      : QtWidgets.QLineEdit
    lineEdit_lvl_5                      : QtWidgets.QLineEdit

    lineEdit_lvl_10                     : QtWidgets.QLineEdit
    lineEdit_lvl_30                     : QtWidgets.QLineEdit
    lineEdit_lvl_60                     : QtWidgets.QLineEdit

    pushButton_save_hvip                : QtWidgets.QPushButton
    pushButton_save_mpp                 : QtWidgets.QPushButton
    lineEdit_cfg_mpp_id                 : QtWidgets.QLineEdit
    vLayout_ser_connect                 : QtWidgets.QVBoxLayout

    radioButton_mpp                     : QtWidgets.QRadioButton
    radioButton_cm                      : QtWidgets.QRadioButton

    CM_DBG_SET_CFG = 0x0005
    CM_ID = 1
    #CM_DBG_SET_VOLTAGE = 0x0006
    #CM_DBG_GET_VOLTAGE = 0x0009
    #CMD_HVIP_ON_OFF = 0x000B


    def __init__(self, logger, **kwargs) -> None:
        super().__init__(**kwargs)
        loadUi(Path(__file__).resolve().parent.parent.parent.joinpath('frontend/DialogConfig.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.logger = logger
        self.cm_cmd: ModbusCMComand = ModbusCMComand(client, logger)
        self.mpp_cmd: ModbusMPPComand = ModbusMPPComand(client, logger)
        self.w_ser_connect: QWidget = SerialConnect(logger)
        i_validator = QIntValidator()
        d_validator = QDoubleValidator()
        self.initValidator(i_validator, d_validator)
        ## создать ообработчик кнопки serial_connect и считывать состояние кнопки, если есть коннект, 
        # то забрать наследуемся от client
        # self.pushButton_save_mpp.clicked.connect(self.pushButton_save_mpp_handler)

    def initValidator(self, validator, d_validator) -> None:
        self.lineEdit_lvl_0_1.setValidator(validator)
        self.lineEdit_lvl_0_5.setValidator(validator)
        self.lineEdit_lvl_0_8.setValidator(validator)
        self.lineEdit_lvl_1_6.setValidator(validator)
        self.lineEdit_lvl_3.setValidator(validator)
        self.lineEdit_lvl_5.setValidator(validator)
        self.lineEdit_lvl_10.setValidator(validator)
        self.lineEdit_lvl_30.setValidator(validator)
        self.lineEdit_lvl_60.setValidator(validator)
        self.lineEdit_pwm_pips.setValidator(d_validator)
        self.lineEdit_hvip_pips.setValidator(d_validator)
        self.lineEdit_pwm_sipm .setValidator(d_validator)
        self.lineEdit_hvip_sipm.setValidator(d_validator)
        self.lineEdit_pwm_ch.setValidator(d_validator)
        self.lineEdit_hvip_ch.setValidator(d_validator)
        self.lineEdit_interval.setValidator(d_validator)
    
    @asyncSlot()    
    async def update_gui_data(self, event) -> None:
        try:
            answer: bytes = await self.cm_cmd.get_telemetria()
            tel_dict: dict = self.parser.pars_telemetria(answer)
            self.lineEdit_lvl_0_1.setText(str(tel_dict["01_hh_l"]))
            self.lineEdit_lvl_0_5.setText(str(tel_dict["05_hh_l"]))
            self.lineEdit_lvl_0_8.setText(str(tel_dict["08_hh_l"]))
            self.lineEdit_lvl_1_6.setText(str(tel_dict["1_6_hh_l"]))
            self.lineEdit_lvl_3.setText(str(tel_dict["3_hh_l"]))
            self.lineEdit_lvl_5.setText(str(tel_dict["5_6_hh_l"]))
            self.lineEdit_lvl_10.setText(str(tel_dict["5_6_hh_l"]))
            self.lineEdit_lvl_30.setText(str(tel_dict["5_6_hh_l"]))
            self.lineEdit_lvl_60.setText(str(tel_dict["5_6_hh_l"]))

            self.lineEdit_pwm_pips.setText(tel_dict["hvip_pwm_pips"])
            self.lineEdit_hvip_pips.setText(tel_dict["hvip_pips"])
            self.lineEdit_pwm_sipm .setText(tel_dict["hvip_pwm_sipm"])
            self.lineEdit_hvip_sipm.setText(tel_dict["hvip_sipm"])
            self.lineEdit_pwm_ch.setText(tel_dict["hvip_pwm_ch"])
            self.lineEdit_hvip_ch.setText(tel_dict["hvip_ch"])

            self.lineEdit_interval.setText(str(tel_dict["hvip_pwm_pips"]))

            self.lineEdit_cfg_mpp_id.setText(str(tel_dict["hvip_pwm_pips"]))
        except Exception as e:
            self.logger.error(e)

    # def pushButton_save_mpp_handler(self):
    #     try:
    #         data = self.set_ddii_cfg()
    #         self.root.client.write_registers(address = self.CM_DBG_SET_CFG, values = data, slave = self.CM_ID)
    #         log_s(self.root.send_handler.mess)
    #         self.update_parent_data()
    #     except Exception as err:
    #         self.root.logger.debug(err)
    #     self.close()

    def set_ddii_cfg(self):
        pass
        # try:
        #     data = []
        #     data.append(0xf10f)
        #     data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_0_1.text()))))
        #     data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_0_5.text()))))
        #     data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_0_8.text()))))
        #     data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_1_6.text()))))
        #     data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_3.text()))))
        #     data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_5.text()))))
        #     data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_10.text()))))
        #     data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_30.text()))))
        #     data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_60.text()))))

        #     str_b = float(self.lineEdit_pwm_ch.text().replace(',', '.'))
        #     val: list[int] = self.float_to_byte(str_b)
        #     data += val
        #     str_b = float(self.lineEdit_pwm_pips.text().replace(',', '.'))
        #     val: list[int] = self.float_to_byte(str_b)
        #     data += val
        #     str_b = float(self.lineEdit_pwm_sipm.text().replace(',', '.'))
        #     val: list[int] = self.float_to_byte(str_b)
        #     data += val

        #     str_b = float(self.lineEdit_hvip_ch.text().replace(',', '.'))
        #     val: list[int] = self.float_to_byte(str_b)
        #     data += val
        #     str_b = float(self.lineEdit_hvip_pips.text().replace(',', '.'))
        #     val: list[int] = self.float_to_byte(str_b)
        #     data += val
        #     str_b = float(self.lineEdit_hvip_sipm.text().replace(',', '.'))
        #     val: list[int] = self.float_to_byte(str_b)
        #     data += val
            
        #     data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_cfg_mpp_id.text()))))
        #     data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_interval.text()))))
        # except Exception as ex:
        #     # self.root.logger.debug(ex)
        #     pass

        # return data
    
    # def update_parent_data(self):
    #     self.root.v_cfg_pips = float(self.lineEdit_hvip_pips.text())
    #     self.root.v_cfg_sipm = float(self.lineEdit_hvip_sipm.text())
    #     self.root.v_cfg_cherenkov = float(self.lineEdit_hvip_ch.text())
        
    #     self.root.pwm_cfg_pips = float(self.lineEdit_pwm_pips.text())
    #     self.root.pwm_cfg_sipm = float(self.lineEdit_pwm_sipm.text())
    #     self.root.pwm_cfg_cherenkov = float(self.lineEdit_pwm_ch.text())
        
    #     self.root.lineEdit_01_hh_l.setText(self.lineEdit_lvl_0_1.text())
    #     self.root.lineEdit_05_hh_l.setText(self.lineEdit_lvl_0_5.text())
    #     self.root.lineEdit_08_hh_l.setText(self.lineEdit_lvl_0_8.text())
    #     self.root.lineEdit_1_6_hh_l.setText(self.lineEdit_lvl_1_6.text())
    #     self.root.lineEdit_3_hh_l.setText(self.lineEdit_lvl_3.text())
    #     self.root.lineEdit_5_hh_l.setText(self.lineEdit_lvl_5.text())
    #     self.root.lineEdit_10_hh_l.setText(self.lineEdit_lvl_10.text())
    #     self.root.lineEdit_30_hh_l.setText(self.lineEdit_lvl_30.text())
    #     self.root.lineEdit_60_hh_l.setText(self.lineEdit_lvl_60.text())

    #     self.root.ddii_interval_measure = self.lineEdit_interval.text()

    # def float_to_byte(self, float_t) -> list:
    #     byte_str: bytes = struct.pack('>f', float_t)
    #     n0: bytes = self.root.swap_bytes(byte_str[0:2])
    #     n1: bytes = self.root.swap_bytes(byte_str[2:4])
    #     return [int(n1.hex(), 16), int(n0.hex(), 16)]
    

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    # light(app)
    logger = log_init()
    spacer_g = QSpacerItem(40, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    spacer_v = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    w_ser_connect: SerialConnect = SerialConnect(logger)
    w: MainConfigDialog = MainConfigDialog(logger)
    grBox : QGroupBox = QGroupBox("Подключение")
    # Настройка шрифта для QGroupBox
    font = QFont()
    font.setFamily("Arial")         # Шрифт
    font.setPointSize(12)           # Размер шрифта
    font.setBold(False)              # Жирный текст
    font.setItalic(False)            # Курсив
    grBox.setFont(font)
    gridL: QGridLayout = QGridLayout()
    w.vLayout_ser_connect.addWidget(grBox)
    grBox.setLayout(gridL)
    gridL.addItem(spacer_g, 0, 0)
    gridL.addItem(spacer_g, 0, 2)
    gridL.addItem(spacer_v, 2, 1, 1, 3)
    gridL.addWidget(w_ser_connect, 0, 1)

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