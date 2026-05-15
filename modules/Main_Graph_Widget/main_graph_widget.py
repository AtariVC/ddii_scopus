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


from app.widgets.oscilloscope.graph_widget import GraphWidget
from app.plugins.connection.main_serial_dialog_tcp import SerialConnect
from app.src.components.modbus.ddii_command import ModbusCMCommand, ModbusMPPCommand
from app.src.components.log.config import log_init
from app.src.components.modbus.worker import ModbusWorker
from app.src.components.parsers.custom_parsers import Parsers
from app.src.components.parsers.parsers_pack import LineEObj


class MainGraphWidget(QtWidgets.QDialog):
    lineEdit_T_cher: QtWidgets.QLineEdit
    lineEdit_T_sipm: QtWidgets.QLineEdit
    pushButton_OK: QtWidgets.QPushButton
    vLayout_ser_connect: QtWidgets.QVBoxLayout
    verticalLayout_graph: QtWidgets.QVBoxLayout

    coroutine_get_temp_finished = QtCore.pyqtSignal()

    def __init__(self, logger, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).resolve().parent.joinpath("DialogGraphWidget.ui"), self)
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
        self.task = None  # type: ignore
        # self.pushButton_OK.clicked.connect(self.pushButton_OK_handler)
        # self.coroutine_get_temp_finished.connect(self.creator_task)
        # # инициализация структур обновляемых полей приложения
        # self.le_obj: list[LineEObj] = self.init_linEdit_list()

    @qasync.asyncSlot()
    async def get_client(self) -> None:
        """Перехватывает client от SerialConnect и переподключается к нему"""
        if self.w_ser_dialog:
            self.client: AsyncModbusSerialClient = self.w_ser_dialog.client
            await self.client.connect()
            self.cm_cmd = ModbusCMCommand(self.client, self.logger)
        if self.w_ser_dialog.pushButton_connect_flag == 0:
            if self.task:
                self.task.cancel()

        if self.w_ser_dialog.status_CM == 1:
            self.coroutine_get_temp_finished.emit()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    # light(app)
    logger = log_init()
    w_ser_dialog: SerialConnect = SerialConnect(logger)
    graph_widget: GraphWidget = GraphWidget()
    w: MainGraphWidget = MainGraphWidget(logger, w_ser_dialog)

    # spacer_g = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    # spacer_v = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    # grBox : QGroupBox = QGroupBox("Подключение")
    # Настройка шрифта для QGroupBox
    # font = QFont()
    # font.setFamily("Arial")         # Шрифт
    # font.setPointSize(12)           # Размер шрифта
    # font.setBold(False)             # Жирный текст
    # font.setItalic(False)           # Курсив
    # grBox.setFont(font)
    # gridL: QGridLayout = QGridLayout()
    # w.vLayout_ser_connect.addWidget(grBox)
    # grBox.setMinimumWidth(10)
    # grBox.setLayout(gridL)
    # gridL.addItem(spacer_g, 0, 0)
    # gridL.addItem(spacer_g, 0, 2)
    # gridL.addItem(spacer_v, 2, 1, 1, 3)
    # gridL.addWidget(w_ser_dialog, 0, 1)

    w.verticalLayout_graph.addWidget(graph_widget)

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
