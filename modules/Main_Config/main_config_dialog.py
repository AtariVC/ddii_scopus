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
from save_config import ConfigSaver

# from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QIntValidator, QDoubleValidator
import logging
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
from src.parsers_pack import LineObj, LineEditPack


class MainConfigDialog(QtWidgets.QDialog, EnviramentVar):
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

    pushButton_Get_Rst                  : QtWidgets.QPushButton

    CM_DBG_SET_CFG = 0x0005
    CM_ID = 1
    #CM_DBG_SET_VOLTAGE = 0x0006
    #CM_DBG_GET_VOLTAGE = 0x0009
    #CMD_HVIP_ON_OFF = 0x000B

    def __init__(self, logger, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).resolve().parent.parent.parent.joinpath('frontend/DialogConfig.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.logger = logger
        i_validator = QIntValidator()
        d_validator = QDoubleValidator()
        self.config = ConfigSaver(self)
        self.flg_get_rst = 0
        self.initValidator(i_validator, d_validator)
        if __name__ == "__main__":
            self.w_ser_dialog: SerialConnect = args[0]
            self.w_ser_dialog.coroutine_finished.connect(self.get_client)
        else:
            self.client: AsyncModbusSerialClient = args[0]
            self.cm_cmd: ModbusCMComand = ModbusCMComand(self.client, self.logger)
            self.mpp_cmd: ModbusMPPComand = ModbusMPPComand(self.client, self.logger)
        self.pushButton_save_mpp.clicked.connect(self.pushButton_save_cfg_handler)
        self.pushButton_Get_Rst.clicked.connect(self.pushButton_get_rst_handler)
        self.le_obj = self.init_linEdit_list()

    def init_linEdit_list(self) -> dict[str, QtWidgets.QLineEdit]:
        le_obj: dict[str, QtWidgets.QLineEdit] = {
                    "lineEdit_pwm_ch": self.lineEdit_pwm_ch,
                    "lineEdit_pwm_pips": self.lineEdit_pwm_pips,
                    "lineEdit_pwm_sipm": self.lineEdit_pwm_sipm,
                    "lineEdit_hvip_ch": self.lineEdit_hvip_ch,
                    "lineEdit_hvip_pips": self.lineEdit_hvip_pips,
                    "lineEdit_hvip_sipm": self.lineEdit_hvip_sipm,
                    "lineEdit_interval": self.lineEdit_interval,
                    "lineEdit_lvl_0_1": self.lineEdit_lvl_0_1,
                    "lineEdit_lvl_0_5": self.lineEdit_lvl_0_5,
                    "lineEdit_lvl_0_8": self.lineEdit_lvl_0_8,
                    "lineEdit_lvl_1_6": self.lineEdit_lvl_1_6,
                    "lineEdit_lvl_3": self.lineEdit_lvl_3,
                    "lineEdit_lvl_5": self.lineEdit_lvl_5,
                    "lineEdit_lvl_10": self.lineEdit_lvl_10,
                    "lineEdit_lvl_30": self.lineEdit_lvl_30,
                    "lineEdit_lvl_60": self.lineEdit_lvl_60,
                    "lineEdit_cfg_mpp_id": self.lineEdit_cfg_mpp_id
                    }
        return le_obj

    @asyncSlot()
    async def get_client(self) -> None:
        """Функция перехватывает client и переподключается к нему
        """
        try:
            if self.w_ser_dialog.pushButton_connect_flag == 1:
                self.client: AsyncModbusSerialClient = self.w_ser_dialog.client
                await self.client.connect()
                # print(self.client.is_connected())
                self.cm_cmd: ModbusCMComand = ModbusCMComand(self.client, self.logger)
                self.mpp_cmd: ModbusMPPComand = ModbusMPPComand(self.client, self.logger)
                if self.w_ser_dialog.status_CM == 1:
                    await self.update_gui_data()
                    if self.w_ser_dialog.status_MPP == 0:
                        self.radioButton_mpp.setEnabled(False)
                if self.w_ser_dialog.status_CM == 0:
                        self.radioButton_mpp.setChecked(True)
                        self.radioButton_cm.setEnabled(False)
                
        except Exception:
            pass

    @asyncSlot()
    async def update_gui_data_mpp(self) -> None:
        try:
            answer: bytes = await self.mpp_cmd.get_hh()
            tel_dict: dict = await self.parser.pars_mpp_hh(answer)

            answ_lvl: bytes = await self.mpp_cmd.get_level()
            tel_dict_lvl: dict = await self.parser.pars_mpp_lvl(answ_lvl)

            self.lineEdit_lvl_0_1.setText(str(tel_dict_lvl["01_hh_l"]))
            self.lineEdit_lvl_0_5.setText(str(tel_dict["05_hh_l"]))
            self.lineEdit_lvl_0_8.setText(str(tel_dict["08_hh_l"]))
            self.lineEdit_lvl_1_6.setText(str(tel_dict["1_6_hh_l"]))
            self.lineEdit_lvl_3.setText(str(tel_dict["3_hh_l"]))
            self.lineEdit_lvl_5.setText(str(tel_dict["5_hh_l"]))
            self.lineEdit_lvl_10.setText(str(tel_dict["10_hh_l"]))
            self.lineEdit_lvl_30.setText(str(tel_dict["30_hh_l"]))
            self.lineEdit_lvl_60.setText(str(tel_dict["60_hh_l"]))
        except Exception as e:
            self.logger.error(e)

    @asyncSlot()    
    async def update_gui_data(self) -> None:
        try:
            answer: bytes = await self.cm_cmd.get_cfg_ddii()
            tel_dict: dict = await self.parser.pars_cfg_ddii(answer)
            self.lineEdit_lvl_0_1.setText(str(tel_dict["01_hh_l"]))
            self.lineEdit_lvl_0_5.setText(str(tel_dict["05_hh_l"]))
            self.lineEdit_lvl_0_8.setText(str(tel_dict["08_hh_l"]))
            self.lineEdit_lvl_1_6.setText(str(tel_dict["1_6_hh_l"]))
            self.lineEdit_lvl_3.setText(str(tel_dict["3_hh_l"]))
            self.lineEdit_lvl_5.setText(str(tel_dict["5_hh_l"]))
            self.lineEdit_lvl_10.setText(str(tel_dict["10_hh_l"]))
            self.lineEdit_lvl_30.setText(str(tel_dict["30_hh_l"]))
            self.lineEdit_lvl_60.setText(str(tel_dict["60_hh_l"]))

            self.lineEdit_pwm_pips.setText(tel_dict["hvip_cfg_pwm_pips"])
            self.lineEdit_hvip_pips.setText(tel_dict["hvip_cfg_vlt_pips"])

            self.lineEdit_pwm_sipm .setText(tel_dict["hvip_cfg_pwm_sipm"])
            self.lineEdit_hvip_sipm.setText(tel_dict["hvip_cfg_vlt_sipm"])

            self.lineEdit_pwm_ch.setText(tel_dict["hvip_cfg_pwm_ch"])
            self.lineEdit_hvip_ch.setText(tel_dict["hvip_cfg_vlt_ch"])

            self.lineEdit_interval.setText(str(tel_dict["interval_measure"]))

            self.lineEdit_cfg_mpp_id.setText(str(tel_dict["mpp_id"]))
            
        except Exception as e:
            self.logger.error(e)

    def closeEvent(self, event) -> None:
        try:
            if self.client.connected:
                self.client.close()
        except Exception:
            pass

    @asyncSlot()
    async def pushButton_save_cfg_handler(self) -> None:
        msg: list[int] = [self.HEAD]
        if self.radioButton_cm.isChecked():
            try:
                data: list[int] = await self.get_cfg_data_from_widget("cm")
                msg.append(data[13])
                await self.cm_cmd.set_cfg_ddii(msg +
                    data[13:14] + data[14:-1] + data[:12] + data[21:-1] + data[13:14])
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.debug(e)
        if self.radioButton_mpp.isChecked():
            try:
                data: list[int] = await self.get_cfg_data_from_widget("mpp")
                await self.mpp_cmd.set_level(data[13])
                await self.mpp_cmd.set_hh(data[14:-1])
            except Exception as e:
                self.logger.debug(e)
    
    @asyncSlot()
    async def pushButton_get_rst_handler(self) -> None:
        if self.flg_get_rst == 0:
            if self.radioButton_cm.isChecked() and self.w_ser_dialog.status_CM == 1:
                await self.update_gui_data()
                self.pushButton_Get_Rst.setText("R")
                self.flg_get_rst = 1
            if self.radioButton_mpp.isChecked() and self.w_ser_dialog.status_MPP == 1:
                await self.update_gui_data_mpp()
                self.pushButton_Get_Rst.setText("R")
                self.flg_get_rst = 1
            
        else:
            self.pushButton_Get_Rst.setText("G")
            self.config.load_from_config()
            self.flg_get_rst = 0

    @asyncSlot()
    async def get_cfg_data_from_widget(self, device: str) -> list[int]:
        pack = [LineObj(key=key, lineobj=value, tp=('f' if i < 6 else 'i')) 
        for  i, (key, value) in enumerate(self.le_obj.items())]
        get_data_widget = LineEditPack()
        if device == 'mpp':
            return get_data_widget(pack, 'big')
        if device == 'cm':
            return get_data_widget(pack, 'little')
        else:
            return []


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

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    # light(app)
    logger = log_init()
    spacer_g = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    spacer_v = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    w_ser_dialog: SerialConnect = SerialConnect(logger)
    w: MainConfigDialog = MainConfigDialog(logger, w_ser_dialog)
    grBox : QGroupBox = QGroupBox("Подключение")
    # Настройка шрифта для QGroupBox
    font = QFont()
    font.setFamily("Arial")         # Шрифт
    font.setPointSize(12)           # Размер шрифта
    font.setBold(False)             # Жирный текст
    font.setItalic(False)           # Курсив
    grBox.setFont(font)
    gridL: QGridLayout = QGridLayout()
    w.vLayout_ser_connect.addWidget(grBox)
    grBox.setMinimumWidth(10)
    grBox.setLayout(gridL)
    gridL.addItem(spacer_g, 0, 0)
    gridL.addItem(spacer_g, 0, 2)
    gridL.addItem(spacer_v, 2, 1, 1, 3)
    gridL.addWidget(w_ser_dialog, 0, 1)

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