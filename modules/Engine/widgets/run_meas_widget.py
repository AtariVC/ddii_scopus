import asyncio
import sys
import tracemalloc
import numpy as np
# from save_config import ConfigSaver
from pathlib import Path
from typing import Any, Awaitable, Callable, Coroutine

import qasync
import qtmodern.styles
from PyQt6 import QtCore, QtWidgets
from qasync import asyncSlot
from qtpy.uic import loadUi
import struct
from pymodbus.client import AsyncModbusSerialClient


tracemalloc.start()


####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from modules.Main_Serial.main_serial_dialog import SerialConnect  # noqa: E402
from src.async_task_manager import AsyncTaskManager  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
from src.parsers import Parsers  # noqa: E402
from src.print_logger import PrintLogger  # noqa: E402
from modules.Engine.widgets.graph_widget import GraphWidget  # noqa: E402


class RunMaesWidget(QtWidgets.QDialog):
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
    checkBox_ch_request          : QtWidgets.QCheckBox
    

    def __init__(self, *args) -> None:
        super().__init__()
        self.parent = args[0]
        loadUi(Path(__file__).parent.joinpath('run_meas_widget.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.asyncio_task_list: list = []
        self.graph_widget: GraphWidget = self.parent.w_graph_widget
        self.parser = Parsers()
        self.flag_pushButton_run_measure: bool = False
        # pushButton_autorun_signal           = QtCore.pyqtSignal()
        # pushButton_run_measure_signal       = QtCore.pyqtSignal()
        # checkBox_enable_test_csa_signal     = QtCore.pyqtSignal()
        if __name__ != "__main__":
            self.w_ser_dialog: SerialConnect = self.parent.w_ser_dialog
            self.logger = self.parent.logger
            self.w_ser_dialog.coroutine_finished.connect(self.get_client)

            self.task_manager = AsyncTaskManager(self.logger)
            # self.pushButton_autorun.clicked.connect(self.pushButton_autorun_handler)
            self.checkBox_enable_test_csa.stateChanged.connect(self.checkBox_enable_test_csa_handler)
        else:
            self.task_manager = AsyncTaskManager()
            self.logger = PrintLogger()
        self.pushButton_run_measure.clicked.connect(self.pushButton_run_measure_handler)


    # def pushButton_autorun_handler(self) -> None:
    #     self.pushButton_autorun_signal.emit()

    @asyncSlot()
    async def get_client(self) -> None:
        """Перехватывает client от SerialConnect и переподключается к нему"""
        if self.w_ser_dialog.pushButton_connect_flag == 0:
            await self.w_ser_dialog.client.connect()
        # if self.w_ser_dialog.pushButton_connect_flag == 1:
        #     pass
        mpp_id = self.w_ser_dialog.mpp_id
        self.cm_cmd: ModbusCMCommand = ModbusCMCommand(self.w_ser_dialog.client, self.logger)
        self.mpp_cmd: ModbusMPPCommand = ModbusMPPCommand(self.w_ser_dialog.client, self.logger, mpp_id)


    @asyncSlot()
    async def pushButton_run_measure_handler(self) -> None:
        """Запуск асинхронной задачи. Создаем задачи asyncio_measure_loop_request и 
        asyncio__loop_request через creator_asyncio_tasks
        asyncio_ACQ_loop_request для непрерывного получения данных АЦП
        asyncio_HH_loop_request для непрерывного получения данных гистограмм МПП
        """
        ACQ_task:  Callable[[], Awaitable[None]] = self.asyncio_ACQ_loop_request
        HH_task: Callable[[], Awaitable[None]] = self.asyncio_HH_loop_request
        if self.w_ser_dialog.pushButton_connect_flag != 1:
            self.flag_pushButton_run_measure = not self.flag_pushButton_run_measure
            if self.flag_pushButton_run_measure:
                self.pushButton_run_measure.setText("Остановить изм.")
                try:
                    await self.task_manager.create_task(ACQ_task(), "ACQ_task")
                    # await ACQ_task()
                    # await self.task_manager.create_task(HH_task(), "HH_task")
                except Exception as e:
                    self.logger.error(f"Ошибка: {e}")
            else:
                self.pushButton_run_measure.setText("Запустить изм.")
                self.task_manager.cancel_task("ACQ_task")
        else:
            self.logger.error(f"Нет подключения к ДДИИ")
        # self.coroutine_get_client_finished.connect(self.creator_asyncio_tasks)

    # def creator_asyncio_tasks(self, *asyncio_tasks) -> None:
        # try:
        #     if self.w_ser_dialog.pushButton_connect_flag != 0:
        #         for task in asyncio_tasks:
        #             if task is None:
        #                 self.task: asyncio.Task[None] = asyncio.create_task(task())
        #     else:
        #         try:
        #             self.logger.error(f"Нет подключения к ДДИИ")
        #         except Exception:
        #             print(f"Нет подключения к ДДИИ")
        #         # Если соединение нет, закрываем задачу
        #         if coroutine is not None:
        #             if coroutine.done():
        #                 coroutine.cancel()
        # except Exception as e:
        #     try:
        #         self.logger.error(f"Error in creating task: {str(e)}")
        #     except Exception:
        #         print(f"Error in creating task: {str(e)}")

    @asyncSlot()
    async def asyncio_ACQ_loop_request(self) -> None:
        try:
            # await self.mpp_cmd.set_level(lvl = int(self.lineEdit_trigger.text()))
            # await self.mpp_cmd.start_measure()
            while 1:
                # result_ch0: bytes = await self.mpp_cmd.read_oscill(ch = 0)
                # result_ch1: bytes = await self.mpp_cmd.read_oscill(ch = 1)
                # result_ch0_int: list[int] = await self.parser.acq_parser(result_ch0)
                # result_ch0_int = list(np.random.randint(200, size=512))
                # await self.graph_widget.gp_pips.draw_graph(result_ch0_int, save_log=False, clear=True)
                # self.graph_widget.show()
                # await self.update_gui_data_label()
                break
        except asyncio.CancelledError:
            ...


    @asyncSlot()
    async def asyncio_HH_loop_request(self) -> None:
        try:
            while 1:
                # await self.update_gui_data_label()
                print("task2")
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            ...

    @asyncSlot()
    async def checkBox_enable_test_csa_handler(self, state) -> None:
        if state > 1:
            await self.cm_cmd.set_csa_test_enable(state=1)
        else:
            await self.cm_cmd.set_csa_test_enable(state=0)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    w = RunMaesWidget()
    event_loop = qasync.QEventLoop(app)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    w.show()

    if event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...



