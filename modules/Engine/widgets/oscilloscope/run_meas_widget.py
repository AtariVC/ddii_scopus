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

from src.write_data_to_file import write_to_hdf5_file

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))


from modules.Engine.widgets.oscilloscope.graph_widget import GraphWidget  # noqa: E402
from modules.Main_Serial.main_serial_dialog_tcp import SerialConnect  # noqa: E402
from src.async_task_manager import AsyncTaskManager  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.event.event import Event  # noqa: E402
from src.filters_data import FiltersData  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
from src.parsers import Parsers  # noqa: E402
from src.print_logger import PrintLogger  # noqa: E402


class RunMeasWidget(QtWidgets.QDialog):
    """Управление окном run_meas_widget.ui
    Запуск измерения, запуск тестовых импульсов, запись логфайла всех измерений.
    Опрос гистограмм МПП.

    Args:
        QtWidgets (_type_): _description_Базовый класс виджетов
    """

    lineEdit_trigger: QtWidgets.QLineEdit
    pushButton_run_measure: QtWidgets.QPushButton
    pushButton_autorun: QtWidgets.QPushButton
    checkBox_enable_test_csa: QtWidgets.QCheckBox
    gridLayout_meas: QtWidgets.QGridLayout

    checkBox_wr_log: QtWidgets.QCheckBox
    checkBox_hist_request: QtWidgets.QCheckBox

    checkBox_enable_trig_meas: QtWidgets.QCheckBox
    pushButton_calibr_acq: QtWidgets.QPushButton

    checkBox_request_hist: QtWidgets.QCheckBox

    comboBox_filter: QtWidgets.QComboBox

    # graph_done_signal = QtCore.pyqtSignal()

    def __init__(self, *args) -> None:
        super().__init__()
        self.parent = args[0]
        loadUi(Path(__file__).parent.joinpath("run_meas_widget.ui"), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.graph_widget: GraphWidget = self.parent.w_graph_widget  # type: ignore
        self.ACQ_task_sync_time_event = Event(str)
        self.get_electron_hist_event = Event(list)
        self.get_proton_hist_event = Event(list)
        self.get_hcp_hist_event = Event(list)
        self.get_electron_hist_event.subscribe(self.parent.flux_widget.update_gui_data_electron)  # type: ignore
        self.get_proton_hist_event.subscribe(self.parent.flux_widget.update_gui_data_proton)  # type: ignore
        self.get_hcp_hist_event.subscribe(self.parent.flux_widget.update_gui_data_hcp)  # type: ignore
        self.filters_data: FiltersData = FiltersData()
        self.hist_filters = None
        self.enable_test_csa_flag: str = "enable_test_csa_flag"
        self.enable_trig_meas_flag: str = "enable_trig_meas_flag"
        self.start_measure_flag: str = "start_measure_flag"
        self.wr_log_flag: str = "wr_log_flag"
        self.request_hist_flag: str = "request_hist_flag"

        self.flags = {
            self.enable_test_csa_flag: False,
            self.enable_trig_meas_flag: True,
            self.start_measure_flag: False,
            self.wr_log_flag: False,
            self.request_hist_flag: True,
        }

        self.checkbox_flag_mapping = {
            self.checkBox_enable_test_csa: self.enable_test_csa_flag,
            self.checkBox_enable_trig_meas: self.enable_trig_meas_flag,
            self.checkBox_wr_log: self.wr_log_flag,
            self.checkBox_request_hist: self.request_hist_flag,
        }

        self.init_flags()
        self.init_combobox_filter()

        if __name__ != "__main__":
            self.w_ser_dialog: SerialConnect = self.parent.w_ser_dialog  # type: ignore
            self.logger = self.parent.logger  # type: ignore
            self.w_ser_dialog.coroutine_finished.connect(self.init_mb_cmd)
            # Остановка измерений при отключении Serial
            self.w_ser_dialog.disconnected.connect(self.on_serial_disconnected)
            self.task_manager = AsyncTaskManager(self.logger)
            self.comboBox_filter.currentIndexChanged.connect(self.comboBox_filter_handler)
            self.pushButton_run_measure.clicked.connect(self.pushButton_run_measure_handler)
            self.pushButton_calibr_acq.clicked.connect(self.pushButton_calibr_acq_handler)
            self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)
        else:
            self.task_manager = AsyncTaskManager()
            self.logger = PrintLogger()

    def init_flags(self):
        for checkBox, flag in self.checkbox_flag_mapping.items():
            checkBox.setChecked(self.flags[flag])
            if flag == self.request_hist_flag:
                self.parent.run_flux_widget.pushButton_hist_run_measure.setEnabled(not self.flags[flag])  # type: ignore
                self.parent.run_flux_widget.lineEdit_interval_request.setEnabled(not self.flags[flag])  # type: ignore
                self.parent.run_flux_widget.checkBox_write_log.setEnabled(not self.flags[flag])  # type: ignore
        for checkbox, flag_name in self.checkbox_flag_mapping.items():
            checkbox.clicked.connect(partial(self.flag_exhibit, flag=flag_name))

    def init_combobox_filter(self) -> None:
        for key in self.filters_data.filters.keys():
            self.comboBox_filter.addItem(key)

    def comboBox_filter_handler(self):
        self.hist_filters = self.filters_data.filters[self.comboBox_filter.currentText()]

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
        self.pushButton_run_measure.setText("Запустить изм.")

    @qasync.asyncSlot()
    async def init_mb_cmd(self) -> None:
        """Инициализация командного интерфейса МПП и ЦМ"""
        if not self.w_ser_dialog or not self.w_ser_dialog.is_modbus_ready():
            self.logger.warning("Modbus не готов: нет активного serial-соединения")
            self.cm_cmd, self.mpp_cmd = (
                self.w_ser_dialog.get_commands_interface(self.logger)
                if self.w_ser_dialog
                else (self.cm_cmd, self.mpp_cmd)
            )
            return
        try:
            ready = await self.w_ser_dialog.check_connection()
        except Exception as e:
            self.logger.warning(f"Не удалось обновить статус ЦМ/МПП при инициализации команд: {e}")
            self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)
            return
        # Всегда берём команды через фабрику, она сама подставит нужный клиент/mpp_id
        self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)
        if not ready:
            self.logger.warning("ЦМ/МПП недоступны — запуск измерений невозможен")

    @qasync.asyncSlot()
    async def on_serial_disconnected(self):
        await self._stop_measuring("Serial отключен")
        # Обновляем команды через фабрику (вернутся null‑клиент команды)
        if self.w_ser_dialog:
            self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)

    @qasync.asyncSlot()
    async def pushButton_calibr_acq_handler(self):
        if not await self.w_ser_dialog.check_connection():
            self.logger.error("Нет подключения (ЦМ/МПП недоступны)")
            return
        # Обновляем клиент/ID для команд
        await self.init_mb_cmd()
        try:
            await self.mpp_cmd.calibrate_ACQ()
            buffer = self.w_ser_dialog.label_state_w.text()
            self.w_ser_dialog.label_state_w.setText("Выполняется калибровка АЦП...")
            await asyncio.sleep(5)
            self.w_ser_dialog.label_state_w.setText("Калибровка АЦП завершена.")
            await asyncio.sleep(2)
            self.w_ser_dialog.label_state_w.setText(buffer)
        except Exception as e:
            await self._stop_measuring(f"Ошибка при калибровке: {e}")

    @qasync.asyncSlot()
    async def pushButton_run_measure_handler(self) -> None:
        """Запуск асинхронной задачи. Создаем задачу asyncio_measure_loop_request через creator_asyncio_tasks
        asyncio_ACQ_loop_request - непрерывный опрос МПП для получения данных АЦП
        """
        #### Path to save ####
        self.parent_path: Path = Path("./log/output_graph_data").resolve()
        current_datetime = datetime.datetime.now()
        time: str = current_datetime.strftime("%d-%m-%Y")[:23]
        self.path_to_save: Path = self.parent_path / time

        ACQ_task: Callable[[], Awaitable[None]] = self.asyncio_ACQ_loop_request
        HH_task: Callable[[], Awaitable[None]] = self.asyncio_HH_loop_request
        if await self.w_ser_dialog.check_connection():
            self.flags[self.start_measure_flag] = not self.flags[self.start_measure_flag]
            if self.flags[self.start_measure_flag]:
                self.pushButton_run_measure.setText("Остановить изм.")
                # TODO: сделать чек боксы не активными
                current_datetime = datetime.datetime.now()
                self.name_file_save: str = current_datetime.strftime("%d-%m-%Y_%H-%M-%S-%f")[:23]
                # Обновляем клиент/ID для команд
                await self.init_mb_cmd()
                try:
                    self.task_manager.create_task(ACQ_task(), "ACQ_task")
                    if self.flags[self.request_hist_flag]:
                        self.task_manager.create_task(HH_task(), "HH_task")
                    # await ACQ_task()
                except Exception as e:
                    await self._stop_measuring(f"Ошибка запуска задач: {e}")
            else:
                # self.graph_done_signal.emit()
                try:
                    await self.mpp_cmd.start_measure(on=0)
                except Exception:
                    pass
                self.task_manager.cancel_task("ACQ_task")
                if self.flags[self.request_hist_flag]:
                    try:
                        await self.mpp_cmd.clear_hist()
                    except Exception:
                        pass
                    self.task_manager.cancel_task("HH_task")
                self.pushButton_run_measure.setText("Запустить изм.")
        else:
            self.logger.error(f"Нет подключения")

    async def asyncio_ACQ_loop_request(self) -> None:
        try:
            self.graph_widget.hp_sipm.hist_clear()
            self.graph_widget.hp_pips.hist_clear()
            lvl = int(self.lineEdit_trigger.text())
            save: bool = False
            if not self.w_ser_dialog.is_modbus_ready():
                await self._stop_measuring("Потеряно соединение")
                return
            if self.flags[self.enable_trig_meas_flag]:
                await self.mpp_cmd.set_level(lvl)
                await self.mpp_cmd.start_measure(on=1)
            self.graph_widget.show()
            while 1:
                if not self.w_ser_dialog.is_modbus_ready():
                    await self._stop_measuring("Потеряно соединение")
                    return
                current_datetime = datetime.datetime.now()
                self.name_data = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:23]
                self.ACQ_task_sync_time_event.emit(self.name_data)  # для синхронизации данных по времени
                if not self.flags[self.enable_trig_meas_flag]:
                    await self.mpp_cmd.start_measure_forced(0)
                    await self.mpp_cmd.start_measure_forced(1)
                else:
                    await self.mpp_cmd.issue_waveform()
                result_ch0: bytes = await self.mpp_cmd.read_oscill(ch=0)
                result_ch1: bytes = await self.mpp_cmd.read_oscill(ch=1)
                # result_ch0_int = np.random.randint(np.random.randint(50, 200)+1, size=100).tolist()
                # result_ch1_int = np.random.randint(np.random.randint(50, 200)+1, size=100).tolist()
                result_ch0_int: list[int] = await self.parser.mpp_pars_16b(result_ch0)
                result_ch1_int: list[int] = await self.parser.mpp_pars_16b(result_ch1)
                # Сохранять только те данные которые выше порога
                if self.flags[self.wr_log_flag]:
                    if (
                        max(result_ch0_int) > np.mean(result_ch0_int) * 3
                        or max(result_ch1_int) > np.mean(result_ch1_int) * 3
                    ):
                        save = True
                    else:
                        save = False
                else:
                    save = False
                try:
                    data_pips = await self.graph_widget.gp_pips.draw_graph(
                        result_ch0_int,
                        name_file_save_data=self.name_file_save,
                        name_data=self.name_data,
                        save_log=save,
                        clear=True,
                    )  # x, y
                    data_sipm = await self.graph_widget.gp_sipm.draw_graph(
                        result_ch1_int,
                        name_file_save_data=self.name_file_save,
                        name_data=self.name_data,
                        save_log=save,
                        clear=True,
                    )  # x, y
                    await self.graph_widget.hp_pips.draw_hist(
                        data_pips[1],
                        name_file_save_data=self.name_file_save,
                        name_data=self.name_data,
                        save_log=save,
                        filter=self.hist_filters,
                    )
                    await self.graph_widget.hp_sipm.draw_hist(
                        data_sipm[1],
                        name_file_save_data=self.name_file_save,
                        name_data=self.name_data,
                        save_log=save,
                        filter=self.hist_filters,
                    )
                except asyncio.exceptions.CancelledError:
                    return None
        except asyncio.CancelledError:
            ...
        except Exception as e:
            await self._stop_measuring(f"Ошибка (ACQ): {e}")
            return

    async def asyncio_HH_loop_request(self) -> None:
        """Опрос счетчика частиц"""
        self.graph_widget.hp_counter.hist_clear()
        try:
            if not self.w_ser_dialog.is_modbus_ready():
                await self._stop_measuring("Потеряно соединение (HH init)")
                return
            await self.mpp_cmd.clear_hist()
            await self.mpp_cmd.clear_hcp_hist()
        except Exception as e:
            await self._stop_measuring(f"Ошибка подготовки гистограмм: {e}")
            return
        save: bool = False
        self.graph_widget.show()
        # counter_clear = 0
        data: list[int] = []
        accumulate_data = np.array([0] * 12)
        bins = np.linspace(
            1, 13, 12
        )  # [0.1, 0.5, 0.8, 1.6, 3, 5, 10, 30, 60, 100, 200, 500, 1000]  # np.linspace(1, 13, 12)
        while 1:
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

            result_hist32_int: list[int] = await self.parser.mpp_pars_32b(result_hist32)
            result_hist16_int: list[int] = await self.parser.mpp_pars_16b(result_hist16)
            result_hcp_hist_int: list[int] = await self.parser.mpp_pars_16b(result_hcp_hist)
            self.get_electron_hist_event.emit(result_hist32_int)
            self.get_proton_hist_event.emit(result_hist16_int)
            self.get_hcp_hist_event.emit(result_hcp_hist_int)

            # Обработчик флага сохранения
            if self.flags[self.wr_log_flag]:
                save = True
            else:
                save = False

            try:
                data = result_hist32_int + result_hist16_int
                # сохраняем все counter
                if save:
                    hdf5_path = self.graph_widget
                    data_save = [[x, y] for x, y in enumerate(data + result_hcp_hist_int)]
                    write_to_hdf5_file(data_save, "h_counter", Path(self.name_file_save), self.name_data)  # type: ignore
                # accumulate_data += np.array(data)
                await self.graph_widget.hp_counter._draw_graph(data, bins=bins, calculate_hist=False, autoscale=False)  # type: ignore
            except asyncio.exceptions.CancelledError as e:
                print(e)
                return None

    def enable_trig_meas_handler(self, state) -> None:
        if state:
            self.lineEdit_trigger.setEnabled(True)
        else:
            self.lineEdit_trigger.setEnabled(False)

    def flag_exhibit(self, state: bool, flag: str):
        if flag == self.enable_trig_meas_flag:
            self.enable_trig_meas_handler(state)
        if flag == self.request_hist_flag:
            self.parent.run_flux_widget.pushButton_hist_run_measure.setEnabled(not state)  # type: ignore
            self.parent.run_flux_widget.lineEdit_interval_request.setEnabled(not state)  # type: ignore
            self.parent.run_flux_widget.checkBox_write_log.setEnabled(not state)  # type: ignore
        self.flags[flag] = state


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
