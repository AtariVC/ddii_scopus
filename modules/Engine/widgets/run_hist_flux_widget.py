import asyncio
import struct
import sys
# from save_config import ConfigSaver
from pathlib import Path
from typing import Any, Awaitable, Callable, Coroutine

import numpy as np
import qasync
import qtmodern.styles
from pymodbus.client import AsyncModbusSerialClient
from PyQt6 import QtCore, QtWidgets
from qtpy.uic import loadUi


####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from modules.Engine.widgets.graph_widget import GraphWidget  # noqa: E402
from modules.Main_Serial.main_serial_dialog import SerialConnect  # noqa: E402
from src.async_task_manager import AsyncTaskManager  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
from src.parsers import Parsers  # noqa: E402
from src.print_logger import PrintLogger  # noqa: E402


class RunHistFluxWidget(QtWidgets.QDialog):
    checkBox_write_log					  : QtWidgets.QCheckBox
    pushButton_hist_run_measure           : QtWidgets.QPushButton
    lineEdit_interval_request			  : QtWidgets.QLineEdit

    def __init__(self, *args) -> None:
        super().__init__()
        self.parent = args[0]
        loadUi(Path(__file__).parent.joinpath('run_meas_widget.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.asyncio_task_list: list = []
        self.graph_widget: GraphWidget = self.parent.w_graph_widget
        self.parser = Parsers()
        self.enable_test_csa_flag: str = "enable_test_csa_flag"
        self.flags = {self.enable_test_csa_flag: False,
                        self.enable_test_csa_flag: True}

        self.checkbox_flag_mapping = {
        self.checkBox_enable_test_csa: self.enable_test_csa_flag}

        self.init_flags()		
        if __name__ != "__main__":
            self.w_ser_dialog: SerialConnect = self.parent.w_ser_dialog
            self.logger = self.parent.logger
            self.w_ser_dialog.coroutine_finished.connect(self.get_client)
            self.task_manager = AsyncTaskManager(self.logger)		
            self.pushButton_run_measure.clicked.connect(self.		pushButton_run_measure_handler)
            self.pushButton_calibr_acq.clicked.connect(self.pushButton_calibr_acq_handler)
        else:
            self.task_manager = AsyncTaskManager()
            self.logger = PrintLogger()

    def init_flags(self):
        for checkBox, flag in self.checkbox_flag_mapping.items():
            checkBox.setChecked(self.flags[flag])
        for checkbox, flag_name in self.checkbox_flag_mapping.items():
            checkbox.clicked.connect(lambda state: self.flag_exhibit(state, flag_name))

    @qasync.asyncSlot()
    async def init_mb_cmd(self) -> None:
        mpp_id = self.w_ser_dialog.mpp_id
        self.cm_cmd: ModbusCMCommand = ModbusCMCommand(self.w_ser_dialog.client, self.logger)
        self.mpp_cmd: ModbusMPPCommand = ModbusMPPCommand(self.w_ser_dialog.client, self.logger, mpp_id)


    def flag_exhibit(self, state, flag: str):
        if state > 1:
            self.flags[flag] = True
        else:
            self.flags[flag] = False