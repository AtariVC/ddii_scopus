import asyncio
import struct
import sys
# from save_config import ConfigSaver
from pathlib import Path
from typing import Optional, Sequence, Callable, Union, Dict, Awaitable

import numpy as np
import qasync
import qtmodern.styles
from pymodbus.client import AsyncModbusSerialClient
from PyQt6 import QtCore, QtWidgets
from qtpy.uic import loadUi
import datetime

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from modules.Engine.widgets.oscilloscope.graph_widget import GraphWidget  # noqa: E402
from modules.Main_Serial.main_serial_dialog import SerialConnect  # noqa: E402
from src.async_task_manager import AsyncTaskManager  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
from src.parsers import Parsers  # noqa: E402
from src.print_logger import PrintLogger  # noqa: E402
from src.event.event import Event  # noqa: E402


class RunFluxWidget(QtWidgets.QDialog):
    checkBox_write_log					  : QtWidgets.QCheckBox
    pushButton_hist_run_measure           : QtWidgets.QPushButton
    lineEdit_interval_request			  : QtWidgets.QLineEdit

    def __init__(self, *args) -> None:
        super().__init__()
        self.parent = args[0]
        loadUi(Path(__file__).parent.joinpath('run_flux_widget.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.asyncio_task_list: list = []
        self.graph_widget: GraphWidget = self.parent.w_graph_widget
        self.HH_task_sync_time_event = Event(str)
        self.wr_log_flag: str = "wr_log_flag"
        self.start_measure_flag: str = "start_measure_flag"
        self.flags = {self.wr_log_flag: False,
                        self.start_measure_flag: False}
        
        self.checkbox_flag_mapping = {self.checkBox_write_log: self.wr_log_flag}
        self.init_flags()	
        
        if __name__ != "__main__":
            self.w_ser_dialog: SerialConnect = self.parent.w_ser_dialog
            self.logger = self.parent.logger
            self.w_ser_dialog.coroutine_finished.connect(self.init_mb_cmd)
            self.task_manager = AsyncTaskManager(self.logger)
            self.pushButton_hist_run_measure.clicked.connect(self.pushButton_hist_run_measure_handler)
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

    @qasync.asyncSlot()
    async def pushButton_hist_run_measure_handler(self) -> None:
        """Запуск асинхронной задачи. Создаем задачи asyncio_measure_loop_request и 
        asyncio__loop_request через creator_asyncio_tasks
        asyncio_ACQ_loop_request для непрерывного получения данных АЦП
        asyncio_HH_loop_request для непрерывного получения данных гистограмм МПП
        """
        HH_task: Callable[[], Awaitable[None]] = self.asyncio_HH_loop_request
        if self.w_ser_dialog.pushButton_connect_flag != 0:
            self.flags[self.start_measure_flag] = not self.flags[self.start_measure_flag] 
            if self.flags[self.start_measure_flag]:
                self.pushButton_hist_run_measure.setText("Остановить изм.")
                try:
                    self.task_manager.create_task(HH_task(), "HH_task")
                    # await ACQ_task()
                except Exception as e:
                    self.logger.error(f"Ошибка: {e}")
            else:
                # self.graph_done_signal.emit()
                await self.mpp_cmd.start_measure(on = 0)
                self.task_manager.cancel_task("HH_task")
                self.pushButton_hist_run_measure.setText("Запустить изм.")
        else:
            self.logger.error(f"Нет подключения к ДДИИ")

    async def asyncio_HH_loop_request(self) -> None:
        """Опрос счетчика частиц
        """
        self.graph_widget.hp_counter.hist_clear()
        save: bool = False
        self.graph_widget.show()
        while 1:
            current_datetime = datetime.datetime.now()
            name_data = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:23]
            self.HH_task_sync_time_event.emit(name_data) # для синхронизации данных по времени
            result_hist32: bytes = await self.mpp_cmd.get_hist32()
            result_hist16: bytes = await self.mpp_cmd.get_hist16()

            result_hist32_int: list[int] = await self.parser.mpp_pars_32b(result_hist32)
            result_hist16_int: list[int] = await self.parser.mpp_pars_16b(result_hist16)

            # Обработчик флага сохранения 
            if self.flags[self.wr_log_flag]:
                save = True
            else:
                save = False
            
            try:
                data = result_hist32_int + result_hist16_int
                # await self.graph_widget.hp_counter._draw_graph(data, name_file_save_data=self.name_file_save, name_data=name_data, save_log=save, filter=self.hist_filters)
            except asyncio.exceptions.CancelledError:
                return None
        

    


    def flag_exhibit(self, state, flag: str):
        if state > 1:
            self.flags[flag] = True
        else:
            self.flags[flag] = False