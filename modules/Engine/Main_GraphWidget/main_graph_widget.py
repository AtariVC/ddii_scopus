from PyQt6 import QtWidgets, QtCore
from qtpy.uic import loadUi
from qasync import asyncSlot
import qasync
from PyQt6.QtWidgets import QGroupBox, QGridLayout, QSpacerItem, QSizePolicy
from PyQt6.QtGui import QFont
import qtmodern.styles
import sys
from pymodbus.client import AsyncModbusSerialClient
# from save_config import ConfigSaver
from PyQt6.QtGui import QIntValidator, QDoubleValidator
import asyncio
from pathlib import Path
import pyqtgraph as pg

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from src.modbus_worker import ModbusWorker                          # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand      # noqa: E402
from src.parsers import  Parsers                                    # noqa: E402
from modules.Main_Serial.main_serial_dialog import SerialConnect    # noqa: E402
from src.log_config import log_init, log_s                          # noqa: E402
from style.styleSheet import widget_led_on, widget_led_off          # noqa: E402
from src.parsers_pack import LineEObj, LineEditPack                 # noqa: E402

class Main_Graph_Widget(QtWidgets.QDialog):
    vLayout_gist_EdE            : QtWidgets.QVBoxLayout
    vLayout_gist_pips           : QtWidgets.QVBoxLayout
    vLayout_gist_sipm           : QtWidgets.QVBoxLayout
    vLayout_pips                : QtWidgets.QVBoxLayout
    vLayout_sipm                : QtWidgets.QVBoxLayout

    vLayout_ser_connect         : QtWidgets.QVBoxLayout




    def __init__(self, logger, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).resolve().parent.parent.parent.parent.joinpath('frontend/engineWidget/WidgetGraph.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.logger = logger
        self.flg_get_rst = 0
        if __name__ == "__main__":
            self.w_ser_dialog: SerialConnect = args[0]
            self.w_ser_dialog.coroutine_finished.connect(self.get_client)
        else:
            self.client: AsyncModbusSerialClient = args[0]
            self.cm_cmd: ModbusCMCommand = ModbusCMCommand(self.client, self.logger)
            self.mpp_cmd: ModbusMPPCommand = ModbusMPPCommand(self.client, self.logger)
        self.task = None # type: ignore
        self.plot_pips = pg.PlotWidget()
        self.plot_sipm = pg.PlotWidget()
        self.plot_gist_EdE = pg.PlotWidget()
        self.plot_gist_pips = pg.PlotWidget()
        self.plot_gist_sipm = pg.PlotWidget()
        self.vLayout_pips.addWidget(self.plot_pips)
        self.vLayout_sipm.addWidget(self.plot_sipm)
        self.vLayout_gist_EdE.addWidget(self.plot_gist_EdE)
        self.vLayout_gist_pips.addWidget(self.plot_gist_pips)
        self.vLayout_gist_sipm.addWidget(self.plot_gist_sipm)

    @asyncSlot()
    async def get_client(self) -> None:
        """Перехватывает client от SerialConnect и переподключается к нему"""
        # self.label_status.setText("Status:")
        if self.w_ser_dialog.pushButton_connect_flag == 1:
            self.client: AsyncModbusSerialClient = self.w_ser_dialog.client
            await self.client.connect()
            self.cm_cmd = ModbusCMCommand(self.client, self.logger)
            self.flg_get_rst = 1
            # await self.update_gui_data_label()
            # await self.update_gui_data_spinbox()
        if self.w_ser_dialog.pushButton_connect_flag == 0:
            if self.task:
                self.task.cancel()
        if self.w_ser_dialog.status_CM == 1:
            # self.coroutine_get_client_finished.emit()
            pass
    
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    # light(app)
    logger = log_init()
    w_ser_dialog: SerialConnect = SerialConnect(logger)
    w: Main_Graph_Widget = Main_Graph_Widget(logger, w_ser_dialog)

    # spacer_g = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    # spacer_v = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    # grBox : QGroupBox = QGroupBox("Подключение")
    # # Настройка шрифта для QGroupBox
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