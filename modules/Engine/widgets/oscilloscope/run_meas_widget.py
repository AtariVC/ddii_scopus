import asyncio
import datetime
import struct
import sys
from functools import partial
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


from modules.Engine.widgets.oscilloscope.graph_widget import GraphWidget  # noqa: E402
from modules.Main_Serial.main_serial_dialog import SerialConnect  # noqa: E402
from src.async_task_manager import AsyncTaskManager  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.filtrs_data import FiltrsData  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
from src.parsers import Parsers  # noqa: E402
from src.print_logger import PrintLogger  # noqa: E402
from src.event.event import Event  # noqa: E402


class RunMeasWidget(QtWidgets.QDialog):
    """Управление окном run_meas_widget.ui
    Запуск измерения, запуск тестовых импульсов, запись логфайла всех измерений.
    Опрос гистограмм МПП.

    Args:
        QtWidgets (_type_): _description_Базовый класс виджетов
    """
    lineEdit_trigger             : QtWidgets.QLineEdit
    pushButton_run_measure       : QtWidgets.QPushButton
    pushButton_autorun           : QtWidgets.QPushButton
    checkBox_enable_test_csa     : QtWidgets.QCheckBox
    gridLayout_meas              : QtWidgets.QGridLayout

    checkBox_wr_log              : QtWidgets.QCheckBox
    checkBox_hist_request        : QtWidgets.QCheckBox

    checkBox_enable_trig_meas    : QtWidgets.QCheckBox
    pushButton_calibr_acq        : QtWidgets.QPushButton

    comboBox_filter           : QtWidgets.QComboBox

    # graph_done_signal = QtCore.pyqtSignal()

    def __init__(self, *args) -> None:
        super().__init__()
        self.parent = args[0]
        loadUi(Path(__file__).parent.joinpath('run_meas_widget.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.graph_widget: GraphWidget = self.parent.w_graph_widget
        self.ACQ_task_sync_time_event = Event(str)
        self.filtrs_data: FiltrsData = FiltrsData() 
        self.hist_filters= None
        self.enable_test_csa_flag: str = "enable_test_csa_flag"
        self.enable_trig_meas_flag: str = "enable_trig_meas_flag"
        self.start_measure_flag: str = "start_measure_flag"
        self.wr_log_flag: str = "wr_log_flag"

        self.flags = {self.enable_test_csa_flag: False,
                    self.enable_trig_meas_flag: True,
                    self.start_measure_flag: False,
                    self.wr_log_flag: False}

        self.checkbox_flag_mapping = {
        self.checkBox_enable_test_csa: self.enable_test_csa_flag,
        self.checkBox_enable_trig_meas: self.enable_trig_meas_flag,
        self.checkBox_wr_log: self.wr_log_flag}

        self.init_flags()
        self.init_combobox_filtrer()

        current_datetime = datetime.datetime.now()
        self.name_file_save: str = current_datetime.strftime("%d-%m-%Y_%H-%M-%S-%f")[:23]

        if __name__ != "__main__":
            self.w_ser_dialog: SerialConnect = self.parent.w_ser_dialog
            self.logger = self.parent.logger
            self.w_ser_dialog.coroutine_finished.connect(self.init_mb_cmd)
            self.task_manager = AsyncTaskManager(self.logger)
            self.comboBox_filter.currentIndexChanged.connect(self.comboBox_filtrer_handler)
            self.pushButton_run_measure.clicked.connect(self.pushButton_run_measure_handler)
            self.pushButton_calibr_acq.clicked.connect(self.pushButton_calibr_acq_handler)
        else:
            self.task_manager = AsyncTaskManager()
            self.logger = PrintLogger()

    def init_flags(self):
        for checkBox, flag in self.checkbox_flag_mapping.items():
            checkBox.setChecked(self.flags[flag])
        for checkbox, flag_name in self.checkbox_flag_mapping.items():
            checkbox.clicked.connect(partial(self.flag_exhibit, flag=flag_name))
    
    def init_combobox_filtrer(self) -> None:
        for key, value in self.filtrs_data.filters.items():
            self.comboBox_filter.addItem(key)
    
    def comboBox_filtrer_handler(self):
        self.hist_filters = self.filtrs_data.filters[self.comboBox_filter.currentText()]

    @qasync.asyncSlot()
    async def init_mb_cmd(self) -> None:
        mpp_id = self.w_ser_dialog.mpp_id
        self.cm_cmd: ModbusCMCommand = ModbusCMCommand(self.w_ser_dialog.client, self.logger)
        self.mpp_cmd: ModbusMPPCommand = ModbusMPPCommand(self.w_ser_dialog.client, self.logger, mpp_id)

    @qasync.asyncSlot()
    async def pushButton_calibr_acq_handler(self):
        if self.w_ser_dialog.pushButton_connect_flag != 1:
            await self.mpp_cmd.calibrate_ACQ()
            await asyncio.sleep(5)
        else:
            self.logger.error(f"Нет подключения к ДДИИ")

    @qasync.asyncSlot()
    async def pushButton_run_measure_handler(self) -> None:
        """Запуск асинхронной задачи. Создаем задачу asyncio_measure_loop_request через creator_asyncio_tasks
        asyncio_ACQ_loop_request - непрерывный опрос МПП для получения данных АЦП
        """
        ACQ_task:  Callable[[], Awaitable[None]] = self.asyncio_ACQ_loop_request
        if self.w_ser_dialog.pushButton_connect_flag != 0:
            self.flags[self.start_measure_flag] = not self.flags[self.start_measure_flag] 
            if self.flags[self.start_measure_flag]:
                self.pushButton_run_measure.setText("Остановить изм.")
                try:
                    self.task_manager.create_task(ACQ_task(), "ACQ_task")
                    # await ACQ_task()
                except Exception as e:
                    self.logger.error(f"Ошибка: {e}")
            else:
                # self.graph_done_signal.emit()
                await self.mpp_cmd.start_measure(on = 0)
                self.task_manager.cancel_task("ACQ_task")
                self.pushButton_run_measure.setText("Запустить изм.")
        else:
            self.logger.error(f"Нет подключения к ДДИИ")
    

    async def asyncio_ACQ_loop_request(self) -> None:
        try:
            self.graph_widget.hp_sipm.hist_clear()
            self.graph_widget.hp_pips.hist_clear()
            lvl = int(self.lineEdit_trigger.text())
            save: bool = False
            if self.flags[self.enable_trig_meas_flag]:
                await self.mpp_cmd.set_level(lvl)
                await self.mpp_cmd.start_measure(on = 1)
            self.graph_widget.show()
            while 1:
                current_datetime = datetime.datetime.now()
                name_data = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:23]
                self.ACQ_task_sync_time_event.emit(name_data) # для синхронизации данных по времени
                if not self.flags[self.enable_trig_meas_flag]:
                    await self.mpp_cmd.start_measure_forced()
                else:
                    await self.mpp_cmd.issue_waveform()
                result_ch0: bytes = await self.mpp_cmd.read_oscill(ch = 0)
                result_ch1: bytes = await self.mpp_cmd.read_oscill(ch = 1)
                # result_ch0_int = np.random.randint(np.random.randint(50, 200)+1, size=100).tolist()
                # result_ch1_int = np.random.randint(np.random.randint(50, 200)+1, size=100).tolist()
                result_ch0_int: list[int] = await self.parser.acq_parser(result_ch0)
                result_ch1_int: list[int] = await self.parser.acq_parser(result_ch1)
                # Сохранять только те данные которые выше порога
                if self.flags[self.wr_log_flag]:
                    if max(result_ch0_int)>np.mean(result_ch0_int)*3 or max(result_ch1_int)>np.mean(result_ch1_int)*3:
                        save = True
                    else:
                        save = False
                else:
                    save = False
                try:
                    data_pips = await self.graph_widget.gp_pips.draw_graph(result_ch0_int, name_file_save_data=self.name_file_save, name_data=name_data, save_log=save, clear=True) # x, y
                    data_sipm = await self.graph_widget.gp_sipm.draw_graph(result_ch1_int, name_file_save_data=self.name_file_save, name_data=name_data, save_log=save, clear=True) # x, y
                    await self.graph_widget.hp_pips.draw_hist(data_pips[1], name_file_save_data=self.name_file_save, name_data=name_data, save_log=save, filter=self.hist_filters)
                    await self.graph_widget.hp_sipm.draw_hist(data_sipm[1], name_file_save_data=self.name_file_save, name_data=name_data, save_log=save, filter=self.hist_filters)
                except asyncio.exceptions.CancelledError:
                    return None
                # await self.update_gui_data_label()
                # break
        except asyncio.CancelledError:
            ...

    def enable_trig_meas_handler(self, state) -> None:
        if state:
            self.lineEdit_trigger.setEnabled(True)
        else:
            self.lineEdit_trigger.setEnabled(False)

    def flag_exhibit(self, state, flag: str):
        if flag == self.enable_trig_meas_flag:
                self.enable_trig_meas_handler(state)
        if state:
            self.flags[flag] = True
        else:
            self.flags[flag] = False

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    w = RunMeasWidget()
    event_loop = qasync.QEventLoop(app)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    w.show()

    if event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...



