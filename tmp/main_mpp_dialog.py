import asyncio
import sys
from pathlib import Path

import qasync
import qtmodern.styles
from pymodbus.client import AsyncModbusSerialClient
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QDoubleValidator, QFont, QIntValidator
from PyQt6.QtWidgets import QGridLayout, QGroupBox, QLineEdit, QSizePolicy, QSpacerItem
from qtpy.uic import loadUi

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from modules.Main_Serial.main_serial_dialog import SerialConnect  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.log_config import log_init  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
from src.parsers import Parsers  # noqa: E402
from src.parsers_pack import LineEObj


class MainMppControll(QtWidgets.QDialog):
    spinBox_0_1     : QtWidgets.QSpinBox
    spinBox_0_5     : QtWidgets.QSpinBox
    spinBox_0_8     : QtWidgets.QSpinBox
    spinBox_1_6     : QtWidgets.QSpinBox
    spinBox_3       : QtWidgets.QSpinBox
    spinBox_5       : QtWidgets.QSpinBox
    spinBox_10      : QtWidgets.QSpinBox
    spinBox_30      : QtWidgets.QSpinBox
    spinBox_60      : QtWidgets.QSpinBox

    lineEdit_01_hh  : QtWidgets.QLineEdit
    lineEdit_05_hh  : QtWidgets.QLineEdit
    lineEdit_08_hh  : QtWidgets.QLineEdit
    lineEdit_1_6_hh : QtWidgets.QLineEdit
    lineEdit_3_hh   : QtWidgets.QLineEdit
    lineEdit_5_hh   : QtWidgets.QLineEdit
    lineEdit_10_hh  : QtWidgets.QLineEdit
    lineEdit_30_hh  : QtWidgets.QLineEdit
    lineEdit_60_hh  : QtWidgets.QLineEdit

    lineEdit_ACQ1  : QtWidgets.QLineEdit
    lineEdit_ACQ2  : QtWidgets.QLineEdit

    lineEdit_1_hcp : QtWidgets.QLineEdit
    lineEdit_5_hcp : QtWidgets.QLineEdit
    lineEdit_10_hcp: QtWidgets.QLineEdit
    lineEdit_20_hcp: QtWidgets.QLineEdit
    lineEdit_45_hcp: QtWidgets.QLineEdit

    pushButton_apply: QtWidgets.QPushButton
    pushButton_ok: QtWidgets.QPushButton

    def __init__(self, logger, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).resolve().parent.parent.parent.joinpath('frontend/DialogTerm.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.logger = logger
        self.flg_get_rst = 0
        if __name__ == "__main__":
            self.w_ser_dialog: SerialConnect = args[0]
            self.resize(self.w_ser_dialog.size())
            self.w_ser_dialog.coroutine_finished.connect(self.get_client)
        else:
            self.client: AsyncModbusSerialClient = args[0]
            self.cm_cmd: ModbusCMCommand = ModbusCMCommand(self.client, self.logger)
            self.mpp_cmd: ModbusMPPCommand = ModbusMPPCommand(self.client, self.logger)
        self.task = None # type: ignore
        self.pushButton_OK.clicked.connect(self.pushButton_OK_handler)
        self.coroutine_get_temp_finished.connect(self.creator_task)
        # инициализация структур обновляемых полей приложения
        self.le_obj: list[LineEObj] = self.init_linEdit_list()

    def init_linEdit_list(self) -> list[LineEObj]:
        self.le_T: dict[str, QtWidgets.QLineEdit] = {
                    "lineEdit_T_sipm": self.lineEdit_T_sipm,
                    "lineEdit_T_cher": self.lineEdit_T_cher,
                    }
        pack_T: list[LineEObj] = [LineEObj(key=key, lineobj_txt=value.text(), tp="f") 
            for  i, (key, value) in enumerate(self.le_T.items())]
        return pack_T
    
    def pushButton_OK_handler(self) -> None:
        self.close()
    
    def creator_task(self) -> None:
        try:
            if self.task is None or self.task.done():
                self.task: asyncio.Task[None] = asyncio.create_task(self.asyncio_loop_request())
        except Exception as e:
            self.logger.error(f"Error in creating task: {str(e)}")
        if self.w_ser_dialog.pushButton_connect_flag == 0:
            # Если соединение закрыто, отменяем задачу
            if self.task:
                self.task.cancel()

    async def asyncio_loop_request(self) -> None:
        try:
            while 1:
                await self.update_gui_data_label()
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            ...

    @qasync.asyncSlot()
    async def update_gui_data_label(self) -> None:
        try:
            answer: bytes = await self.cm_cmd.get_term()
            data: dict[str, str] = await self.parser.pars_everything(self.le_obj, answer, "little")
            for i, (key, val) in enumerate(data.items()):
                self.le_T[key].setText(val)
        except Exception as e:
            self.logger.error(e)

    @qasync.asyncSlot()
    async def get_client(self) -> None:
        """Перехватывает client от SerialConnect и переподключается к нему"""
        if self.w_ser_dialog.pushButton_connect_flag == 1:
            self.client: AsyncModbusSerialClient = self.w_ser_dialog.client
            await self.client.connect()
            self.cm_cmd = ModbusCMCommand(self.client, self.logger)
        if self.w_ser_dialog.pushButton_connect_flag == 0:
            if self.task:
                self.task.cancel()


    def pushButton_apply_handler(self) -> None:
        try:
            data = self.set_mpp_lavel()
            self.root.client.write_registers(address = 0x000B, values = data, slave = self.root.mpp_id)
            log_s(self.root.send_handler.mess)
        except Exception as err:
            self.root.logger.debug(err)


        