from PyQt6 import QtWidgets, QtCore
from qtpy.uic import loadUi
from qasync import asyncSlot
import asyncio
import qtmodern.styles
import sys
import qasync
# from save_config import ConfigSaver
from pathlib import Path
from dataclasses import dataclass

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
from src.parsers_pack import LineEObj, LineEditPack                 # noqa: E402
from src.plot_renderer import GraphPen, HistPen                     # noqa: E402




class GraphWidget(QtWidgets.QWidget):
    vLayout_hist_EdE            : QtWidgets.QVBoxLayout
    vLayout_hist_pips           : QtWidgets.QVBoxLayout
    vLayout_hist_sipm           : QtWidgets.QVBoxLayout
    vLayout_pips                : QtWidgets.QVBoxLayout
    vLayout_sipm                : QtWidgets.QVBoxLayout

    vLayout_ser_connect         : QtWidgets.QVBoxLayout

    def __init__(self) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath('graph_widget.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.task = None # type: ignore
        self.gp_pips = GraphPen(self.vLayout_pips, name = "pips", color = (255, 255, 0))
        self.gp_sipm = GraphPen(self.vLayout_sipm, name = "sipm", color = (0, 255, 255))
        self.hp_pips = HistPen(self.vLayout_hist_pips, name = "h_pips", color = (0, 0, 255, 150))
        self.hp_sipm = HistPen(self.vLayout_hist_sipm, name = "h_sipm", color = (255, 0, 0, 150))

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    # light(app)
    logger = log_init()
    w: GraphWidget = GraphWidget()
    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    w.show()
    data: list = [1.4, 34.34, 324.4, 32.4, 89.4, 233.4, 234.4, 2344.4, 234.4]
    w.gp_pips.draw_graph(data, "test", clear=False) # type: ignore
    data1: list[int] = [1, 34, 45, 435, 234, 234, 2344 ,234, 23423, 324, 324234]
    w.gp_pips.draw_graph(data1, "test", clear=False) # type: ignore

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...