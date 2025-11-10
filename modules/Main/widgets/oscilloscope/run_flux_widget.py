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

from modules.Main.widgets.oscilloscope.graph_widget import GraphWidget  # noqa: E402
from modules.Main_Serial.main_serial_dialog_tcp import SerialConnect  # noqa: E402
from src.async_task_manager import AsyncTaskManager  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.event.event import Event  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
from src.parsers import Parsers  # noqa: E402
from src.print_logger import PrintLogger  # noqa: E402


class RunFluxWidget(QtWidgets.QDialog):
    checkBox_write_log: QtWidgets.QCheckBox
    pushButton_hist_run_measure: QtWidgets.QPushButton
    lineEdit_interval_request: QtWidgets.QLineEdit

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
        self.flags = {self.wr_log_flag: False, self.start_measure_flag: False}

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
        """Запуск асинхронной задачи. Создаем задачи asyncio_measure_loop_request и
        asyncio__loop_request через creator_asyncio_tasks
        asyncio_ACQ_loop_request для непрерывного получения данных АЦП
        asyncio_HH_loop_request для непрерывного получения данных гистограмм МПП
        """
        HH_task: Callable[[], Awaitable[None]] = self.asyncio_HH_loop_request
        if await self.w_ser_dialog.check_connection():
            self.flags[self.start_measure_flag] = not self.flags[self.start_measure_flag]
            if self.flags[self.start_measure_flag]:
                self.pushButton_hist_run_measure.setText("Остановить изм.")
                #### Path to save ####
                parent_path: Path = Path("./log/scope").resolve()
                current_datetime = datetime.datetime.now()
                time: str = current_datetime.strftime("%d-%m-%Y")[:23]
                self.path_to_save: Path = parent_path / time
                try:
                    self.task_manager.create_task(HH_task(), "HH_task")
                    # await ACQ_task()
                except Exception as e:
                    self.logger.error(f"Ошибка: {e}")
            else:
                # self.graph_done_signal.emit()
                try:
                    await self.mpp_cmd.start_measure(on=0)
                except Exception:
                    ...
                self.task_manager.cancel_task("HH_task")
                self.pushButton_hist_run_measure.setText("Запустить изм.")
        else:
            self.logger.error(f"Нет подключения к ДДИИ")
            
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
                if name == "HH_task":
                    try:
                        await self.mpp_cmd.clear_hist()
                    except Exception:
                        ...
                    self.task_manager.cancel_task(name)
                if name == "ACQ_task":
                    try:
                        await self.mpp_cmd.stop_measure()
                    except Exception:
                        ...
                    self.task_manager.cancel_task(name)
        except Exception as e:
            self.logger.error(f"Error in stopping measurements: {str(e)}")
        # Сбрасываем флаг и UI
        self.flags[self.start_measure_flag] = False
        self.pushButton_hist_run_measure.setText("Запустить изм.")

    async def asyncio_HH_loop_request(self) -> None:
        """Опрос счетчика частиц"""
        self.graph_widget.hp_counter.hist_clear()
        save: bool = False
        self.graph_widget.show()
        current_datetime = datetime.datetime.now()
        name_file_save_data = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:23]
        while 1:
            if not await self.w_ser_dialog.check_connection():
                self.task_manager.cancel_task("HH_task")
                return
            current_datetime = datetime.datetime.now()
            name_data = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:23]
            self.HH_task_sync_time_event.emit(name_data)  # для синхронизации данных по времени
            try:
                result_hist32: bytes = await self.mpp_cmd.get_hist32()
                result_hist16: bytes = await self.mpp_cmd.get_hist16()
                result_hcp_hist: bytes = await self.mpp_cmd.get_hcp_hist()
            except Exception as e:
                await self._stop_measuring(f"Ошибка чтения гистограмм: {e}")
                return


            result_hist32_int: list[int] = await self.parser.mpp_pars_32b(result_hist32)
            result_hist16_int: list[int] = await self.parser.mpp_pars_16b(result_hist16)
            result_hcp_hist_int: list[int] = await self.parser.mpp_pars_16b(result_hcp_hist)
            # accumulate with reset detection
            self._prev_electron, self._acc_electron = self._accumulate_with_reset(self._prev_electron, self._acc_electron, result_hist32_int)
            self._prev_proton, self._acc_proton = self._accumulate_with_reset(self._prev_proton, self._acc_proton, result_hist16_int)
            self._prev_hcp, self._acc_hcp = self._accumulate_with_reset(self._prev_hcp, self._acc_hcp, result_hcp_hist_int)

            # Обработчик флага сохранения
            if self.flags[self.wr_log_flag]:
                save = True
            else:
                save = False

            try:
                data = result_hist32_int + result_hist16_int
                await self.graph_widget.hp_counter.draw_hist(data, bin_count=len(data),
                    name_file_save_data=name_file_save_data,
                    name_data=name_data,
                    path_to_save=self.path_to_save,
                    save_log=save,
                    data_is_hist=True
                    )
            except asyncio.exceptions.CancelledError:
                return None

    def flag_exhibit(self, state, flag: str):
        if state > 1:
            self.flags[flag] = True
        else:
            self.flags[flag] = False
