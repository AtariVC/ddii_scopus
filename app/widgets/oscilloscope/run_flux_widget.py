import asyncio
import datetime
import struct
import sys

# from save_config import ConfigSaver
from pathlib import Path
from typing import Awaitable, Callable, Dict, Optional, Sequence, Union

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

from app.widgets.oscilloscope.graph_widget import GraphWidget  # noqa: E402
from app.plugins.connection.main_serial_dialog_tcp import SerialConnect  # noqa: E402
from app.src.util.async_task_manager import AsyncTaskManager  # noqa: E402
from app.src.components.modbus.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from app.src.event.event import Event  # noqa: E402
from app.src.components.modbus.worker import ModbusWorker  # noqa: E402
from app.src.components.parsers.custom_parsers import Parsers  # noqa: E402
from app.src.components.log.print_logger import PrintLogger  # noqa: E402


class RunFluxWidget(QtWidgets.QDialog):
    checkBox_write_log: QtWidgets.QCheckBox
    pushButton_hist_run_measure: QtWidgets.QPushButton
    lineEdit_interval_request: QtWidgets.QLineEdit
    lineEdit_threshold: QtWidgets.QLineEdit

    def __init__(self, *args) -> None:
        super().__init__()
        self.parent = args[0]
        loadUi(Path(__file__).parent.joinpath("run_flux_widget.ui"), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.asyncio_task_list: list = []
        self.graph_widget: GraphWidget = self.parent.w_graph_widget # type: ignore
        self.HH_task_sync_time_event = Event(str)
        self.wr_log_flag: str = "wr_log_flag"
        self.start_measure_flag: str = "start_measure_flag"
        self.flags: dict = {self.wr_log_flag: False, self.start_measure_flag: False}
        self.only_acq_flag: bool = False 
        # ==== Events ====
        self.get_electron_hist_event = Event(list)
        self.get_proton_hist_event = Event(list)
        self.get_hcp_hist_event = Event(list)
        self.get_acq_event = Event(list)
        self.name_data: str = ''
        self.TmpCount: int = 0 
        self.get_electron_hist_event.subscribe(self.parent.flux_widget.update_gui_data_electron)  # type: ignore
        self.get_proton_hist_event.subscribe(self.parent.flux_widget.update_gui_data_proton)  # type: ignore
        self.get_hcp_hist_event.subscribe(self.parent.flux_widget.update_gui_data_hcp)  # type: ignore
        self.get_acq_event.subscribe(self.parent.flux_widget.update_data_acq) # type: ignore
        self.parent.shared_bfr_update_event.subscribe(self._update_sync_name_hh) # type: ignore
        self.delay: int = 2 # задержка опроса гистограмм

        self.checkbox_flag_mapping = {self.checkBox_write_log: self.wr_log_flag}
        self.init_flags()

        if __name__ != "__main__":
            self.w_ser_dialog: SerialConnect = self.parent.w_ser_dialog # type: ignore
            self.logger = self.parent.logger # type: ignore
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
        if await self.w_ser_dialog.check_connection():
            self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)

    @qasync.asyncSlot()
    async def pushButton_hist_run_measure_handler(self) -> None:
        if not self.w_ser_dialog.is_modbus_ready():
            await self._stop_measuring("Нет соединения")
        if not self.flags[self.start_measure_flag]:
            self.pushButton_hist_run_measure.setText("Остановить изм.")
            self.graph_widget.hp_sipm.hist_clear()
            self.graph_widget.hp_pips.hist_clear()
            delay = int(self.lineEdit_interval_request.text())
            #### Path to save ####
            path_to_save: Path = self._init_path_to_save()
            name_file_save: str = self._init_name_file_save()
            status_init: bool = await self.init_HH_request(delay, path_to_save,
                                                          name_file_save,
                                                          self.flags[self.wr_log_flag])
            if status_init:
                self.flags[self.start_measure_flag] = True
                try:
                    lvl = int(self.lineEdit_threshold.text())
                except Exception:
                    lvl = 0
                await self.mpp_cmd.set_level(lvl)
                await self.mpp_cmd.start_measure(on=1)
                HH_task: Callable[[], Awaitable[None]] = self.asyncio_HH_loop_request
                ACQ_Peak_task: Callable[[], Awaitable[None]] = self.asyncio_ACQ_Peak_loop_request
                if await self.w_ser_dialog.check_connection():
                    await self.init_mb_cmd()
                    try:
                        self.task_manager.create_task(HH_task(), "HH_task")
                        self.task_manager.create_task(ACQ_Peak_task(), "ACQ_Peak_task")
                    except Exception as e:
                        self.graph_widget.hp_sipm.hist_clear()
                        self.graph_widget.hp_pips.hist_clear()
                        await self._stop_measuring(f"Ошибка запуска задач: {e}")
                
        else:
            self.flags[self.start_measure_flag] = False
            await self._stop_measuring()
            self.only_acq_flag = False
            self.pushButton_hist_run_measure.setText("Начать изм")
    
    def _update_sync_name_hh(self, sync_name):
        self.name_data = sync_name
        
    async def _stop_measuring(self, reason: str | None = None):
        """Останавливает измерения, гасит задачи и приводит UI в исходное состояние."""
        if reason:
            self.logger.error(reason)
        # Пытаемся остановить измерение на стороне МПП
        try:
            await self.mpp_cmd.start_measure(on=0)
        except Exception:
            ...
        # Отменяем все активные задачи по списку
        try:
            for name in self.task_manager.get_active_tasks():
                # Очистку гистограмм делаем только если была HH задача
                if name == "ACQ_Peak_task":
                    self.task_manager.cancel_task(name)
                if name == "HH_task":
                    try:
                        await self.mpp_cmd.clear_hist()
                    except Exception:
                        ...
                    self.task_manager.cancel_task(name)
        except Exception as e:
            self.logger.error(f"Error in stopping measurements: {str(e)}")
        # Приводим UI в исходное состояние
        self.flags[self.start_measure_flag] = False
        self.pushButton_hist_run_measure.setText("Запустить изм.")

    def _init_path_to_save(self) -> Path:
        #### Path to save ####
        parent_path: Path = Path("./log/scope").resolve()
        current_datetime = datetime.datetime.now()
        time: str = current_datetime.strftime("%d-%m-%Y")[:23]
        path_to_save: Path = parent_path / time
        return path_to_save
    
    def _init_name_file_save(self) -> str:
        current_datetime = datetime.datetime.now()
        name_file_save: str = current_datetime.strftime("%d-%m-%Y_%H-%M-%S-%f")[:23]
        return name_file_save

    async def init_HH_request(self, delay, path_to_save: Path, name_file_save: str, save_log_file: bool) -> bool:
        self.delay: int = delay
        self.path_to_save = path_to_save
        self.name_file_save = name_file_save
        self.save_log_file = save_log_file
        try:
            if not self.w_ser_dialog.is_modbus_ready():
                await self._stop_measuring("Потеряно соединение (HH init)")
                return False
            await self.mpp_cmd.clear_hist()
            await self.mpp_cmd.clear_hcp_hist()
            return True
        except Exception as e:
            await self._stop_measuring(f"Ошибка подготовки гистограмм: {e}")
            return False
        # set flag start measure



    async def asyncio_HH_loop_request(self) -> None:
        """Опрос счетчика частиц"""
        # counter_clear = 0
        data: list[int] = []
        # reset accumulators at HH start
        self.graph_widget.hp_counter.hist_clear()
        self._prev_electron = None; self._acc_electron = None
        self._prev_proton = None; self._acc_proton = None
        self._prev_hcp = None; self._acc_hcp = None
        self.graph_widget.show()
        while 1:
            await asyncio.sleep(self.delay)
            if not self.w_ser_dialog.is_modbus_ready():
                await self._stop_measuring("Потеряно соединение")
                return
            # counter_clear += 1
            # if counter_clear > 50:
            #     counter_clear = 0
            #     await self.mpp_cmd.clear_hist()
            try:
                result_hist32: bytes = await self.mpp_cmd.get_hist32()
                result_hist16: bytes = await self.mpp_cmd.get_hist16()
                result_hcp_hist: bytes = await self.mpp_cmd.get_hcp_hist()
            except Exception as e:
                await self._stop_measuring(f"Ошибка чтения гистограмм: {e}")
                return
            
            if not self.name_data:
                current_datetime = datetime.datetime.now()
                self.name_data = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:24]

            result_hist32_int: list[int] = await self.parser.mpp_pars_32b(result_hist32)
            result_hist16_int: list[int] = await self.parser.mpp_pars_16b(result_hist16)
            result_hcp_hist_int: list[int] = await self.parser.mpp_pars_16b(result_hcp_hist)
            # accumulate with reset detection
            self._prev_electron, self._acc_electron = self._accumulate_with_reset(self._prev_electron,
                                                                                  self._acc_electron,
                                                                                  result_hist32_int)
            self._prev_proton, self._acc_proton = self._accumulate_with_reset(self._prev_proton,
                                                                              self._acc_proton,
                                                                              result_hist16_int)
            self._prev_hcp, self._acc_hcp = self._accumulate_with_reset(self._prev_hcp,
                                                                        self._acc_hcp,
                                                                        result_hcp_hist_int)
            try:
                self.get_electron_hist_event.emit(self._acc_electron.tolist())
                self.get_proton_hist_event.emit(self._acc_proton.tolist())
                self.get_hcp_hist_event.emit(self._acc_hcp.tolist())
            except Exception:
                self.get_electron_hist_event.emit(result_hist32_int)
                self.get_proton_hist_event.emit(result_hist16_int)
                self.get_hcp_hist_event.emit(result_hcp_hist_int)

            try:
                if self._acc_electron is not None and self._acc_proton is not None and self._acc_hcp is not None:
                    data = self._acc_electron.tolist() + self._acc_proton.tolist() + self._acc_hcp.tolist()
                else:
                    data = result_hist32_int + result_hist16_int + result_hcp_hist_int
                await self.graph_widget.hp_counter.draw_hist(data, bin_count=len(data),
                    name_file_save_data=self.name_file_save,
                    name_data=self.name_data,
                    path_to_save=self.path_to_save,
                    save_log=self.save_log_file,
                    data_is_hist=True
                    )
                self.name_data = '' # Сбрасываем имя, нужно для работы синхронизации имени данных с другими процессами
            except asyncio.exceptions.CancelledError as e:
                self.name_data = ''
                self.logger.error(str(e))
                return None
            
    async def asyncio_ACQ_Peak_loop_request(self) -> None:
        """Опрос ACQ_Peak"""
        self.graph_widget.hp_counter.hist_clear()
        self._prev_electron = None; self._acc_electron = None
        self._prev_proton = None; self._acc_proton = None
        self._prev_hcp = None; self._acc_hcp = None
        self.graph_widget.show()
        while 1:
            await asyncio.sleep(0.0005)
            if not self.w_ser_dialog.is_modbus_ready():
                await self._stop_measuring("Потеряно соединение")
                return
            try:
                result_acq1: bytes = await self.mpp_cmd.get_acq1()
                result_acq2: bytes = await self.mpp_cmd.get_acq2()
                result_tmp_count: bytes = await self.mpp_cmd.get_tmp_count() 
                
            except Exception as e:
                await self._stop_measuring(f"Ошибка чтения гистограмм: {e}")
                return
            
            # if not self.name_data:
            current_datetime = datetime.datetime.now()
            # self.parent.shared_bfr_update_event.emit(self.name_data) # type: ignore
            self.name_data = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:24]

            acq1: list[int]  = await self.parser.mpp_pars_16b(result_acq1)
            acq2: list[int]  = await self.parser.mpp_pars_16b(result_acq2)
            tmp_count: list[int]  = await self.parser.mpp_pars_16b(result_tmp_count)
            self.get_acq_event.emit([str(acq1[1]), str(acq2[1])])

            try:
                if self.TmpCount != tmp_count[1]:
                    self.TmpCount = tmp_count[1]
                    await self.graph_widget.hp_pips.draw_hist([acq1[1]], bin_count=4096,
                        name_file_save_data=self.name_file_save,
                        name_data=self.name_data,
                        path_to_save=self.path_to_save,
                        save_log=self.save_log_file,
                        data_is_hist=False
                        )
                    await self.graph_widget.hp_sipm.draw_hist([acq2[1]], bin_count=4096,
                        name_file_save_data=self.name_file_save,
                        name_data=self.name_data,
                        path_to_save=self.path_to_save,
                        save_log=self.save_log_file,
                        data_is_hist= False
                        )
                # self.name_data = '' # Сбрасываем имя, нужно для работы синхронизации имени данных с другими процессами
            except asyncio.exceptions.CancelledError as e:
                # self.name_data = ''
                self.logger.error(str(e))
                return None

    
    def _accumulate_with_reset(self, prev, acc, curr):
        """Accumulate per-bin counts with reset or wrap detection.

        Logic per bin:
        - If curr >= prev: delta = curr - prev
        - If curr < prev and prev is near max (wrap on 12-bit): delta = (MOD - prev) + curr
        - Else (hard reset): delta = curr

        Returns updated (prev, acc) as numpy arrays.
        """
        import numpy as np
        curr_arr = np.array(curr, dtype=np.int64)
        if prev is None or acc is None:
            return curr_arr, curr_arr.copy()
        try:
            prev_arr = np.array(prev, dtype=np.int64)
            acc_arr = np.array(acc, dtype=np.int64)
            if len(prev_arr) != len(curr_arr) or len(acc_arr) != len(curr_arr):
                return curr_arr, curr_arr.copy()
            raw_delta = curr_arr - prev_arr
            MOD = getattr(self, "_counter_modulus", 4096)
            wrap_threshold = MOD - 64
            is_wrap = (raw_delta < 0) & (prev_arr >= wrap_threshold)
            wrap_delta = (MOD - prev_arr) + curr_arr
            reset_delta = curr_arr
            delta = np.where(raw_delta >= 0, raw_delta, np.where(is_wrap, wrap_delta, reset_delta))
            acc_arr = acc_arr + delta
            return curr_arr, acc_arr
        except Exception:
            return curr_arr, curr_arr.copy()

    def flag_exhibit(self, state, flag: str):
        if state:
            self.flags[flag] = True
        else:
            self.flags[flag] = False
