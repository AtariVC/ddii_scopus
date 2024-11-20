from PyQt6 import QtWidgets, QtCore
from qtpy.uic import loadUi
from qasync import asyncSlot
import qasync
from PyQt6.QtWidgets import QGroupBox, QGridLayout, QSpacerItem, QSizePolicy
from PyQt6.QtGui import QFont
import qtmodern.styles
import sys
from pymodbus.client import AsyncModbusSerialClient
from save_config import ConfigSaver
from PyQt6.QtGui import QIntValidator, QDoubleValidator
import asyncio
from pathlib import Path

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from src.modbus_worker import ModbusWorker                          # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand         # noqa: E402
from src.parsers import  Parsers                                    # noqa: E402
from modules.Main_Serial.main_serial_dialog import SerialConnect    # noqa: E402
from src.log_config import log_init, log_s                          # noqa: E402
from style.styleSheet import widget_led_on, widget_led_off          # noqa: E402
from src.parsers_pack import LineEObj, LineEditPack                 # noqa: E402


class MainHvipDialog(QtWidgets.QDialog):
    spinBox_ch_volt                     : QtWidgets.QDoubleSpinBox
    spinBox_pips_volt                   : QtWidgets.QDoubleSpinBox
    spinBox_sipm_volt                   : QtWidgets.QDoubleSpinBox

    doubleSpinBox_ch_pwm                : QtWidgets.QDoubleSpinBox
    doubleSpinBox_pips_pwm              : QtWidgets.QDoubleSpinBox
    doubleSpinBox_sipm_pwm              : QtWidgets.QDoubleSpinBox

    label_ch_cur                        : QtWidgets.QLabel
    label_sipm_cur                      : QtWidgets.QLabel
    label_pips_cur                      : QtWidgets.QLabel

    label_ch_pwm_mes                    : QtWidgets.QLabel
    label_pips_pwm_mes                  : QtWidgets.QLabel
    label_sipm_pwm_mes                  : QtWidgets.QLabel

    label_ch_v_mes                      : QtWidgets.QLabel
    label_pips_v_mes                    : QtWidgets.QLabel
    label_sipm_v_mes                    : QtWidgets.QLabel

    label_status                        : QtWidgets.QLabel

    spinBox_ch_a_u                      : QtWidgets.QDoubleSpinBox
    spinBox_ch_b_u                      : QtWidgets.QDoubleSpinBox
    spinBox_ch_a_i                      : QtWidgets.QDoubleSpinBox
    spinBox_ch_b_i                      : QtWidgets.QDoubleSpinBox

    spinBox_pips_a_u                    : QtWidgets.QDoubleSpinBox
    spinBox_pips_b_u                    : QtWidgets.QDoubleSpinBox
    spinBox_pips_a_i                    : QtWidgets.QDoubleSpinBox
    spinBox_pips_b_i                    : QtWidgets.QDoubleSpinBox

    spinBox_sipm_a_u                    : QtWidgets.QDoubleSpinBox
    spinBox_sipm_b_u                    : QtWidgets.QDoubleSpinBox
    spinBox_sipm_a_i                    : QtWidgets.QDoubleSpinBox
    spinBox_sipm_b_i                    : QtWidgets.QDoubleSpinBox

    pushButton_ok                       : QtWidgets.QPushButton
    pushButton_apply                    : QtWidgets.QPushButton

    pushButton_pips_on                  : QtWidgets.QPushButton
    pushButton_sipm_on                  : QtWidgets.QPushButton
    pushButton_ch_on                    : QtWidgets.QPushButton
    pushButton_get_rst                  : QtWidgets.QPushButton

    led_pips                            : QtWidgets.QWidget
    led_sipm                            : QtWidgets.QWidget
    led_ch                              : QtWidgets.QWidget

    vLayout_ser_connect                 : QtWidgets.QVBoxLayout

    PIPS_CH_VOLTAGE = 1
    SIPM_CH_VOLTAGE = 2
    CHERENKOV_CH_VOLTAGE = 3

    coroutine_get_client_finished = QtCore.pyqtSignal()


    def __init__(self, logger, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).resolve().parent.parent.parent.joinpath('frontend/HVIP_window.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.logger = logger
        self.init_QObjects()
        self.config = ConfigSaver()
        self.flg_get_rst = 0
        if __name__ == "__main__":
            self.w_ser_dialog: SerialConnect = args[0]
            self.w_ser_dialog.coroutine_finished.connect(self.get_client)
        else:
            self.client: AsyncModbusSerialClient = args[0]
            self.cm_cmd: ModbusCMCommand = ModbusCMCommand(self.client, self.logger)
            self.mpp_cmd: ModbusMPPCommand = ModbusMPPCommand(self.client, self.logger)
        self.task = None # type: ignore
        # self.pushButton_ok.clicked.connect(self.pushButton_ok_handler)
        self.pushButton_get_rst.clicked.connect(self.pushButton_get_rst_handler)
        self.pushButton_apply.clicked.connect(self.pushButton_apply_handler)

        self.pushButton_pips_on.clicked.connect(self.pushButton_pips_on_handler)
        self.pushButton_sipm_on.clicked.connect(self.pushButton_sipm_on_handler)
        self.pushButton_ch_on.clicked.connect(self.pushButton_ch_on_handler)
        self.coroutine_get_client_finished.connect(self.creator_task)
        self.flag_measure = 1

    @asyncSlot()
    async def get_client(self) -> None:
        """Перехватывает client от SerialConnect и переподключается к нему"""
        self.label_status.setText("Status:")
        if self.w_ser_dialog.pushButton_connect_flag == 1:
            self.client: AsyncModbusSerialClient = self.w_ser_dialog.client
            await self.client.connect()
            self.cm_cmd = ModbusCMCommand(self.client, self.logger)
            await self.update_gui_data_label()
            await self.update_gui_data_spinbox()
        if self.w_ser_dialog.pushButton_connect_flag == 0:
            if self.task:
                self.task.cancel()
        if self.w_ser_dialog.status_CM == 1:
            self.coroutine_get_client_finished.emit()

    def creator_task(self) -> None:
        try:
            if self.task is None or self.task.done():
                self.task: asyncio.Task[None] = asyncio.create_task(self.asyncio_loop_request())
        except Exception as e:
            self.logger.error(f"Error in creating task: {str(e)}")

        if self.w_ser_dialog.pushButton_connect_flag == 0:
            # Если соединение закрыто, отменяем задачу
            if self.task:
                self.task.cancel()
    
    def init_QObjects(self) -> None:
        self.spin_box_cfg_volt: dict[str, QtWidgets.QDoubleSpinBox] = {
            "spinBox_ch_volt"               : self.spinBox_ch_volt,
            "spinBox_pips_volt"             : self.spinBox_pips_volt,
            "spinBox_sipm_volt"             : self.spinBox_sipm_volt,
    }
        self.spin_box_cfg_pwm: dict[str, QtWidgets.QDoubleSpinBox] = {
            "doubleSpinBox_ch_pwm"          : self.doubleSpinBox_ch_pwm,
            "doubleSpinBox_pips_pwm"        : self.doubleSpinBox_pips_pwm,
            "doubleSpinBox_sipm_pwm"        : self.doubleSpinBox_sipm_pwm
    }
        self.label_meas: dict[str, QtWidgets.QLabel | int] = {
            "label_ch_v_mes"                : self.label_ch_v_mes,
            "label_ch_pwm_mes"              : self.label_ch_pwm_mes,
            "label_ch_cur"                  : self.label_ch_cur,
            "hvip_mode_ch"                  : 1,

            "label_pips_v_mes"                : self.label_pips_v_mes,
            "label_pips_pwm_mes"            : self.label_pips_pwm_mes,
            "label_pips_cur"                : self.label_pips_cur,
            "hvip_mode_pips"                : 1,

            "label_sipm_v_mes"              : self.label_sipm_v_mes,
            "label_sipm_pwm_mes"            : self.label_sipm_pwm_mes,
            "label_sipm_cur"                : self.label_sipm_cur,
            "hvip_mode_sipm"                : 1
        }

        self.spin_box_A_B: dict[str, QtWidgets.QDoubleSpinBox] = {
            "spinBox_ch_a_u"                : self.spinBox_ch_a_u,
            "spinBox_pips_a_u"              : self.spinBox_pips_a_u,
            "spinBox_sipm_a_u"              : self.spinBox_sipm_a_u,

            "spinBox_ch_b_u"                : self.spinBox_ch_b_u,
            "spinBox_pips_b_u"              : self.spinBox_pips_b_u,
            "spinBox_sipm_b_u"              : self.spinBox_sipm_b_u,
            
            "spinBox_ch_a_i"                : self.spinBox_ch_a_i,
            "spinBox_pips_a_i"              : self.spinBox_pips_a_i,
            "spinBox_sipm_a_i"              : self.spinBox_sipm_a_i,
            
            "spinBox_ch_b_i"                : self.spinBox_ch_b_i,
            "spinBox_pips_b_i"              : self.spinBox_pips_b_i,
            "spinBox_sipm_b_i"              : self.spinBox_sipm_b_i,
        }

    async def asyncio_loop_request(self) -> None:
        try:
            while 1:
                await self.update_gui_data_label()
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            ...

    @asyncSlot()  
    async def get_cfg_data_from_widget(self, d_struct: dict, tp : str) -> list[int]:
        pack: list[LineEObj] = [LineEObj(key=key, lineobj_txt=value.value(), tp=tp) 
            for  i, (key, value) in enumerate(d_struct.items())]
        get_data_widget = LineEditPack()
        return get_data_widget(pack, 'little')
    
    @asyncSlot()    
    async def update_gui_data_spinbox(self) -> None:
        err_cfg_volt = 0
        err_cfg_pwm = 0
        err_cfg_a_b = 0
        try:
            answ_cfg_volt: bytes = await self.cm_cmd.get_cfg_voltage()
            data_cfg_volt: dict[str, str] = await self.parser.pars_cfg_volt(answ_cfg_volt)
        except Exception as e:
            err_cfg_volt = 1
            self.logger.error(e)
        try:
            answ_cfg_pwm: bytes = await self.cm_cmd.get_cfg_pwm()
            data_cfg_pwm: dict[str, str] = await self.parser.pars_cfg_pwm(answ_cfg_pwm)
        except Exception as e:
            err_cfg_pwm = 1
            self.logger.error(e)
        try:
            await asyncio.sleep(0.1)
            answ_cfg_a_b: bytes = await self.cm_cmd.get_cfg_a_b()
            data_cfg_a_b: dict[str, str] = await self.parser.pars_cfg_a_b(answ_cfg_a_b)
        except Exception as e:
            err_cfg_a_b = 1
            self.logger.error(e)
        if err_cfg_volt == 0:
            for (key, val) in self.spin_box_cfg_volt.items():
                val.setValue(float(data_cfg_volt.get(key)))   # type: ignore
        if err_cfg_pwm == 0:
            for (key, val) in self.spin_box_cfg_pwm.items():
                val.setValue(float(data_cfg_pwm.get(key)))    # type: ignore
        if err_cfg_a_b == 0:
            for (key, val) in self.spin_box_A_B.items():
                val.setValue(float(data_cfg_a_b.get(key)))    # type: ignore

    @asyncSlot()
    async def update_gui_data_label(self) -> None:
        try:
            answer: bytes = await self.cm_cmd.get_voltage()
            data: dict[str, str] = await self.parser.pars_voltage(answer)
            for i, (key, val) in enumerate(self.label_meas.items()):
                if "mode" in key:
                    if key == "hvip_mode_ch":
                        self.update_power_status([self.CHERENKOV_CH_VOLTAGE, int(data[key])])
                    if key == "hvip_mode_pips":
                        self.update_power_status([self.PIPS_CH_VOLTAGE, int(data[key])])
                    if key == "hvip_mode_sipm":
                        self.update_power_status([self.SIPM_CH_VOLTAGE, int(data[key])])
                else:
                    val.setText("{:.2f}".format(float(list(data.values())[i]))) # type: ignore
        except Exception as e:
            self.logger.error(e)

    ############ handler button ##############
    @asyncSlot()
    async def pushButton_pips_on_handler(self) -> None:
        if self.pips_on == 1:
            await self.cm_cmd.switch_power([self.PIPS_CH_VOLTAGE, 0])
            self.pips_on = 0
            self.pushButton_pips_on.setText("Включить")
            self.led_pips.setStyleSheet(widget_led_off())
            
        else:
            await self.cm_cmd.switch_power([self.PIPS_CH_VOLTAGE, 1])
            self.pips_on = 1
            self.pushButton_pips_on.setText("Отключить")
            self.led_pips.setStyleSheet(widget_led_on())
    @asyncSlot()    
    async def pushButton_sipm_on_handler(self):
        if self.pips_on == 1:
            await self.cm_cmd.switch_power([self.SIPM_CH_VOLTAGE, 0])
            self.pips_on = 0
            self.pushButton_pips_on.setText("Включить")
            self.led_sipm.setStyleSheet(widget_led_off())
            
        else:
            await self.cm_cmd.switch_power([self.SIPM_CH_VOLTAGE, 1])
            self.pips_on = 1
            self.pushButton_pips_on.setText("Отключить")
            self.led_sipm.setStyleSheet(widget_led_on())
    
    @asyncSlot() 
    async def pushButton_ch_on_handler(self):
        if self.pips_on == 1:
            await self.cm_cmd.switch_power([self.CHERENKOV_CH_VOLTAGE, 0])
            self.pips_on = 0
            self.pushButton_pips_on.setText("Включить")
            self.led_ch.setStyleSheet(widget_led_off())
            
        else:
            await self.cm_cmd.switch_power([self.CHERENKOV_CH_VOLTAGE, 1])
            self.pips_on = 1
            self.pushButton_pips_on.setText("Отключить")
            self.led_ch.setStyleSheet(widget_led_on())

    @asyncSlot() 
    async def pushButton_apply_handler(self) -> None:
        vlt_data: list[int] = await self.get_cfg_data_from_widget(self.spin_box_cfg_volt, 'f')
        pwm_data: list[int] = await self.get_cfg_data_from_widget(self.spin_box_cfg_pwm, 'f')
        await self.cm_cmd.set_voltage_pwm(vlt_data + pwm_data)
        cfg_a_b_data: list[int] = await self.get_cfg_data_from_widget(self.spin_box_A_B, 'f')
        await asyncio.sleep(0.1)
        await self.cm_cmd.set_cfg_a_b(cfg_a_b_data)
        self.label_status.setText("Status: cfg was written")
        loaded_cfg: list[dict[str, float|int|str]] = [
            {key: spin_box.value() for key, spin_box in item.items()}
            for item in [self.spin_box_cfg_volt,
                    self.spin_box_cfg_pwm,
                    self.spin_box_A_B]
            ]
        # Объединение всех словарей в один
        combined_cfg: dict[str, float | int | str] = {}
        for item in loaded_cfg:
            combined_cfg.update(item)
        self.config.save_to_config(combined_cfg)

    @asyncSlot()
    async def pushButton_get_rst_handler(self) -> None:
        if self.flg_get_rst == 0:
            await self.update_gui_data_spinbox()
            self.label_status.setText("Status: Get data")
            self.pushButton_get_rst.setText("R")
            self.flg_get_rst = 1
        else:
            self.label_status.setText("Status: Reset data")
            self.pushButton_get_rst.setText("G")
            for_updt: list[dict[str, QtWidgets.QDoubleSpinBox]] = [self.spin_box_cfg_volt,
                    self.spin_box_cfg_pwm,
                    self.spin_box_A_B]
            for item in for_updt:
                self.config.load_from_config(item)
            self.flg_get_rst = 0

    def pushButton_ok_handler(self) -> None:
        try:
            if self.client.connected:
                self.client.close()
        except Exception as VErr:
            self.logger.debug(VErr)
        self.close()


    ############# update label ###############
    def update_power_status(self, data) -> None:
        try:
            if data[0] == self.PIPS_CH_VOLTAGE:
                if data[1] == 1:
                    self.pips_on = 1
                    self.pushButton_pips_on.setText("Отключить")
                    self.led_pips.setStyleSheet(widget_led_on())
                else:
                    self.pips_on = 0
                    self.pushButton_pips_on.setText("Включить")
                    self.led_pips.setStyleSheet(widget_led_off())
            elif data[0] == self.SIPM_CH_VOLTAGE:
                if data[1] == 1:
                    self.sipm_on = 1
                    self.pushButton_sipm_on.setText("Отключить")
                    self.led_sipm.setStyleSheet(widget_led_on())
                else:
                    self.sipm_on = 0
                    self.pushButton_sipm_on.setText("Включить")
                    self.led_sipm.setStyleSheet(widget_led_off())
            elif data[0] == self.CHERENKOV_CH_VOLTAGE:
                if data[1] == 1:
                    self.ch_on = 1
                    self.pushButton_ch_on.setText("Отключить")
                    self.led_ch.setStyleSheet(widget_led_on())
                else:
                    self.ch_on = 0
                    self.pushButton_ch_on.setText("Включить")
                    self.led_ch.setStyleSheet(widget_led_off())
        except Exception as ex:
            self.logger.debug(ex)


    def closeEvent(self, event) -> None:
        try:
            if self.client.connected:
                self.client.close()
                for i in range(3):
                    self.update_power_status([i, 0])
        except Exception:
            pass

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    # light(app)
    logger = log_init()
    spacer_g = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    spacer_v = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    w_ser_dialog: SerialConnect = SerialConnect(logger)
    w: MainHvipDialog = MainHvipDialog(logger, w_ser_dialog)
    grBox : QGroupBox = QGroupBox("Подключение")
    # Настройка шрифта для QGroupBox
    font = QFont()
    font.setFamily("Arial")         # Шрифт
    font.setPointSize(12)           # Размер шрифта
    font.setBold(False)             # Жирный текст
    font.setItalic(False)           # Курсив
    grBox.setFont(font)
    gridL: QGridLayout = QGridLayout()
    w.vLayout_ser_connect.addWidget(grBox)
    grBox.setMinimumWidth(10)
    grBox.setLayout(gridL)
    gridL.addItem(spacer_g, 0, 0)
    gridL.addItem(spacer_g, 0, 2)
    gridL.addItem(spacer_v, 2, 1, 1, 3)
    gridL.addWidget(w_ser_dialog, 0, 1)

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