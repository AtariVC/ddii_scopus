from PyQt6 import QtWidgets
from qtpy.uic import loadUi
from qasync import QEventLoop, asyncSlot
import qasync
# from engine_trapezoid_dialog import EngineTrapezoidFilter
import os
import struct
# import threading
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import QWidget, QGroupBox, QGridLayout, QSpacerItem, QSizePolicy
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
import qtmodern.styles
from qtmodern.windows import ModernWindow
import sys
from pymodbus.client import AsyncModbusSerialClient


# from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QIntValidator, QDoubleValidator
import logging
# from modules.dialog_window.main_hvip_dialog import MainHvipDialog as hvip_dialog
# from copy import deepcopy
import asyncio
from pathlib import Path

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from src.modbus_worker import ModbusWorker
from src.ddii_comand import ModbusCMComand, ModbusMPPComand
from src.parsers import  Parsers
from modules.Main_Serial.main_serial_dialog import SerialConnect
from src.log_config import log_init, log_s
from src.env_var import EnviramentVar


    # def th_measure_voltage(self):
    #     while self.running:
    #         res = self.measure_voltage()
    #         if res != 0:
    #             self.update_signal.emit(res)
    #             self.sleep(2)

    # def measure_voltage(self):
    #     # Измерение напряжения: 01 10 00 07 00 00 71 C8
    #     transaction = self.get_voltage()
    #     if transaction != 0:
    #         voltage = self.root.parse_voltage(transaction)
    #         if voltage != (0,):
    #             return voltage
    #         else:
    #             return 0
    #     else:
    #         return 0

    # def get_voltage(self):
    #     try:
    #         result = self.root.client.read_holding_registers(self.CM_DBG_GET_VOLTAGE, 21, slave=self.root.CM_ID)
    #         log_s(self.root.send_handler.mess)
    #         return result
    #     except Exception as ex:
    #         self.root.logger.debug(ex)
    #         return 0
    
    # def th_set_voltage(self, data):
    #     self.stop()
    #     try:
    #         self.root.client.write_registers(address = self.CM_DBG_SET_VOLTAGE,
    #                             values = data, 
    #                             slave = self.root.CM_ID)
    #         log_s(self.root.send_handler.mess)
    #         self.finished_signal.emit()
    #         self.running = True
    #     except Exception as ex:
    #         self.root.logger.debug(ex)
    
    # def th_hvip_power(self, data):
    #     self.stop()
    #     try:
    #         self.root.client.write_registers(address = self.CMD_HVIP_ON_OFF,
    #                             values = data, 
    #                             slave = self.root.CM_ID)
    #         log_s(self.root.send_handler.mess)
    #         # res_encode = res.encode()
    #         # data = [int(res_encode[1:2].hex(), 16), int(res_encode[3:4].hex(), 16)]
    #         self.finished_signal.emit()
    #         self.running = True
    #     except Exception as ex:
    #         self.root.logger.debug(ex)

    # def stop(self):
    #     self.running = False
    #     self.quit()
    #     self.wait()

    # def start_voltage_thread(self, data):
    #     self.set_voltage_thread = threading.Thread(target=self.th_set_voltage, args=(data,), daemon=True)
    #     self.set_voltage_thread.start()

class MainHvipDialog(QtWidgets.QDialog):
    spinBox_pips_volt: QtWidgets.QDoubleSpinBox
    spinBox_sipm_volt: QtWidgets.QDoubleSpinBox
    spinBox_ch_volt: QtWidgets.QDoubleSpinBox
    label_pips_mes: QtWidgets.QLabel
    label_sipm_mes: QtWidgets.QLabel
    label_ch_mes: QtWidgets.QLabel
    label_pips_cur: QtWidgets.QLabel
    label_sipm_cur: QtWidgets.QLabel
    label_ch_cur: QtWidgets.QLabel
    label_pips_pwm_mes: QtWidgets.QLabel
    label_sipm_pwm_mes: QtWidgets.QLabel
    label_ch_pwm_mes:   QtWidgets.QLabel

    pushButton_ok: QtWidgets.QPushButton
    pushButton_apply: QtWidgets.QPushButton
    doubleSpinBox_pips_pwm: QtWidgets.QDoubleSpinBox
    doubleSpinBox_sipm_pwm: QtWidgets.QDoubleSpinBox
    doubleSpinBox_ch_pwm: QtWidgets.QDoubleSpinBox
    pushButton_pips_on: QtWidgets.QPushButton
    pushButton_sipm_on: QtWidgets.QPushButton
    pushButton_ch_on: QtWidgets.QPushButton
    led_pips: QtWidgets.QWidget
    led_sipm: QtWidgets.QWidget
    led_ch: QtWidgets.QWidget

    vLayout_ser_connect: QtWidgets.QVBoxLayout

    PIPS_CH_VOLTAGE = 1
    SIPM_CH_VOLTAGE = 2
    CHERENKOV_CH_VOLTAGE = 3


    def __init__(self, logger, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).resolve().parent.parent.parent.joinpath('frontend/HVIP_window.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.logger = logger

        if __name__ == "__main__":
            self.w_ser_dialog: SerialConnect = args[0]
            self.w_ser_dialog.coroutine_finished.connect(self.get_client)
        else:
            self.client: AsyncModbusSerialClient = args[0]
            self.cm_cmd: ModbusCMComand = ModbusCMComand(self.client, self.logger)
            self.mpp_cmd: ModbusMPPComand = ModbusMPPComand(self.client, self.logger)


        # self.pushButton_ok.clicked.connect(self.pushButton_ok_handler)
        self.pushButton_apply.clicked.connect(self.pushButton_apply_handler)

        self.pushButton_pips_on.clicked.connect(self.pushButton_pips_on_handler)
        self.pushButton_sipm_on.clicked.connect(self.pushButton_sipm_on_handler)
        self.pushButton_ch_on.clicked.connect(self.pushButton_ch_on_handler)
        self.flag_measure = 1
    
    @asyncSlot()
    async def get_client(self) -> None:
        """Функция перехватывает client и переподключается к нему
        """
        if self.w_ser_dialog.state_serial == 1:
            self.client: AsyncModbusSerialClient = self.w_ser_dialog.client
            await self.client.connect()
            # print(self.client.is_connected())
            self.cm_cmd: ModbusCMComand = ModbusCMComand(self.client, self.logger)
            self.mpp_cmd: ModbusMPPComand = ModbusMPPComand(self.client, self.logger)
            await self.update_gui_data()
        

    async def update_gui_data(self):      
        self.spinBox_pips_volt.setValue(self.root.v_cfg_pips)
        self.spinBox_sipm_volt.setValue(self.root.v_cfg_sipm)
        self.spinBox_ch_volt.setValue(self.root.v_cfg_cherenkov)

        self.doubleSpinBox_pips_pwm.setValue(self.root.pwm_cfg_pips)
        self.doubleSpinBox_sipm_pwm.setValue(self.root.pwm_cfg_sipm)
        self.doubleSpinBox_ch_pwm.setValue(self.root.pwm_cfg_cherenkov)

        self.label_pips_mes.setText("{:.2f}".format(self.root.hvip_pips))
        self.label_sipm_mes.setText("{:.2f}".format(self.root.hvip_sipm))
        self.label_ch_mes.setText("{:.2f}".format(self.root.hvip_ch))

        self.label_pips_cur.setText("{:.2f}".format(self.root.hvip_current_pips))
        self.label_sipm_cur.setText("{:.2f}".format(self.root.hvip_current_sipm))
        self.label_ch_cur.setText("{:.2f}".format(self.root.hvip_current_ch))

        self.label_pips_pwm_mes.setText("{:.2f}".format(self.root.hvip_pwm_pips))
        self.label_sipm_pwm_mes.setText("{:.2f}".format(self.root.hvip_pwm_sipm))
        self.label_ch_pwm_mes.setText("{:.2f}".format(self.root.hvip_pwm_ch))

        if self.root.hvip_mode_pips == 1:
            self.pushButton_pips_on.setText("Отключить")
            self.led_pips.setStyleSheet(style.widget_led_on())
        if self.root.hvip_mode_sipm == 1:
            self.pushButton_sipm_on.setText("Отключить")
            self.led_sipm.setStyleSheet(style.widget_led_on())
        if self.root.hvip_mode_ch == 1:
            self.pushButton_ch_on.setText("Отключить")
            self.led_ch.setStyleSheet(style.widget_led_on())
        super().showEvent(event)
        self.start_measure()
    
    def start_measure(self):
        self.th_measure = threading.Thread(target=self.modbus_worker.th_measure_voltage, daemon = True)
        self.th_measure.start()

    ############ handler button ##############
    def pushButton_pips_on_handler(self):
        if self.pips_on == 1:
            data = [0x0001, 0x0000]
            self.pips_on = 0
            self.pushButton_pips_on.setText("Включить")
            self.led_pips.setStyleSheet(style.widget_led_off())
            
        else:
            data = [0x0001, 0x0001]
            self.pips_on = 1
            self.pushButton_pips_on.setText("Отключить")
            self.led_pips.setStyleSheet(style.widget_led_on())
        self.th_hvip_on_off = threading.Thread(target=self.modbus_worker.th_hvip_power, args=(data,), daemon = True)
        self.th_hvip_on_off.start()

    def pushButton_sipm_on_handler(self):
        if self.sipm_on == 1:
            data = [0x0002, 0x0000]
            self.sipm_on = 0
            self.pushButton_sipm_on.setText("Включить")
            self.led_sipm.setStyleSheet(style.widget_led_off())
            
        else:
            data = [0x0002, 0x0001]
            self.sipm_on = 1
            self.pushButton_sipm_on.setText("Отключить")
            self.led_sipm.setStyleSheet(style.widget_led_on())
        self.th_hvip_on_off = threading.Thread(target=self.modbus_worker.th_hvip_power, args=(data,), daemon = True)
        self.th_hvip_on_off.start()

    def pushButton_ch_on_handler(self):
        if self.ch_on == 1:
            data = [0x0003, 0x0000]
            self.ch_on = 0
            self.pushButton_ch_on.setText("Включить")
            self.led_ch.setStyleSheet(style.widget_led_off())
            
        else:
            data = [0x0003, 0x0001]
            self.ch_on = 1
            self.pushButton_ch_on.setText("Отключить")
            self.led_ch.setStyleSheet(style.widget_led_on())
        self.th_hvip_on_off = threading.Thread(target=self.modbus_worker.th_hvip_power, args=(data,), daemon = True)
        self.th_hvip_on_off.start()

    def pushButton_apply_handler(self) -> None:
        try:
            data_voltage = self.set_voltage()
            data_pwm = self.set_pwm()
            data = data_voltage + data_pwm
            self.modbus_worker.start_voltage_thread(data)
        except Exception as VErr:
            self.root.logger.debug(VErr)

    def set_voltage(self) -> list:
        float_t = float(self.spinBox_pips_volt.text().replace(',', '.'))
        v_pips_l = self.float_to_byte(float_t)
        self.root.v_cfg_pips = v_pips_l
        float_t = float(self.spinBox_sipm_volt.text().replace(',', '.'))
        v_sipm_l = self.float_to_byte(float_t)
        self.root.v_cfg_sipm = v_sipm_l
        float_t = float(self.spinBox_ch_volt.text().replace(',', '.'))
        v_ch_l = self.float_to_byte(float_t)
        self.root.v_cfg_ch = v_ch_l
        data = v_ch_l + v_pips_l + v_sipm_l
        return data
    
    def float_to_byte(self, float_t) -> list:
        byte_str: bytes = struct.pack('>f', float_t)
        n0: bytes = self.root.swap_bytes(byte_str[0:2])
        n1: bytes = self.root.swap_bytes(byte_str[2:4])
        return [int(n1.hex(), 16), int(n0.hex(), 16)]

    def set_pwm(self) -> list:
        float_t = float(self.doubleSpinBox_pips_pwm.text().replace(',', '.'))
        v_pips_l = self.float_to_byte(float_t)
        self.root.pwm_cfg_pips = v_pips_l
        float_t = float(self.doubleSpinBox_sipm_pwm.text().replace(',', '.'))
        v_sipm_l = self.float_to_byte(float_t)
        self.root.pwm_cfg_sipm = v_sipm_l
        float_t = float(self.doubleSpinBox_ch_pwm.text().replace(',', '.'))
        v_ch_l = self.float_to_byte(float_t)
        self.root.pwm_cfg_ch = v_ch_l
        data = v_ch_l + v_pips_l + v_sipm_l
        return data

    def pushButton_ok_handler(self) -> None:
        try:
            self.modbus_worker.stop()
            self.close()
            self.destroy()
        except Exception as VErr:
            self.root.logger.debug(VErr)
        self.close()


    ############# update label ###############
    # def update_power_status(self, data):
    #     try:
    #         if data[0] == self.PIPS_CH_VOLTAGE:
    #             if data[1] == 1:
    #                 self.pips_on = 0
    #                 self.pushButton_pips_on.setText("Отключить")
    #                 self.led_pips.setStyleSheet(style.widget_led_on())
    #             else:
    #                 self.pips_on = 1
    #                 self.pushButton_pips_on.setText("Включить")
    #                 self.led_pips.setStyleSheet(style.widget_led_off())
    #         elif data[0] == self.SIPM_CH_VOLTAGE:
    #             if data[1] == 1:
    #                 self.sipm_on = 0
    #                 self.pushButton_sipm_on.setText("Отключить")
    #                 self.led_pips.setStyleSheet(style.widget_led_on())
    #             else:
    #                 self.sipm_on = 1
    #                 self.pushButton_sipm_on.setText("Включить")
    #                 self.led_sipm.setStyleSheet(style.widget_led_off())
    #         elif data[0] == self.CHERENKOV_CH_VOLTAGE:
    #             if data[1] == 1:
    #                 self.ch_on = 0
    #                 self.pushButton_ch_on.setText("Отключить")
    #                 self.led_pips.setStyleSheet(style.widget_led_on())
    #             else:
    #                 self.ch_on = 1
    #                 self.pushButton_ch_on.setText("Включить")
    #                 self.led_pips.setStyleSheet(style.widget_led_off())
    #     except Exception as ex:
    #         self.root.logger.debug(ex)

    def update_label(self, voltage):
        try:
            ### pips ###
            self.label_pips_mes.setText("{:.2f}".format(voltage[0]))
            self.label_pips_pwm_mes.setText("{:.2f}".format(voltage[1]))
            self.label_pips_cur.setText("{:.2f}".format(voltage[2]))
            if voltage[3] == 1:
                self.pips_on = 1
                self.pushButton_pips_on.setText("Отключить")
                self.led_pips.setStyleSheet(style.widget_led_on())
            elif voltage[3] == 0:
                self.pips_on = 0
                self.pushButton_pips_on.setText("Включить")
                self.led_pips.setStyleSheet(style.widget_led_off())
            else:
                self.root.logger.debug("Ошибка работы HVIP PIPS")
            ### sipm ###
            self.label_sipm_mes.setText("{:.2f}".format(voltage[4]))
            self.label_sipm_pwm_mes.setText("{:.2f}".format(voltage[5]))
            self.label_sipm_cur.setText("{:.2f}".format(voltage[6]))
            if voltage[7] == 1:
                self.sipm_on = 1
                self.pushButton_sipm_on.setText("Отключить")
                self.led_sipm.setStyleSheet(style.widget_led_on())
            elif voltage[7] == 0:
                self.sipm_on = 0
                self.pushButton_sipm_on.setText("Включить")
                self.led_sipm.setStyleSheet(style.widget_led_off())
            else:
                self.root.logger.debug("Ошибка работы HVIP SIPM")
            ### ch ###
            self.label_ch_mes.setText("{:.2f}".format(voltage[8]))
            self.label_ch_pwm_mes.setText("{:.2f}".format(voltage[9]))
            self.label_ch_cur.setText("{:.2f}".format(voltage[10]))
            if voltage[11] == 1:
                self.ch_on = 1
                self.pushButton_ch_on.setText("Отключить")
                self.led_ch.setStyleSheet(style.widget_led_on())
            elif voltage[11] == 0:
                self.ch_on = 0
                self.pushButton_ch_on.setText("Включить")
                self.led_ch.setStyleSheet(style.widget_led_off())
            else:
                self.root.logger.debug("Ошибка работы HVIP CHERENKOV")
        except Exception as ex:
            self.root.logger.debug(ex)
            self.root.logger.exception("message")

    def closeEvent(self, event) -> None:
        self.modbus_worker.stop()
        self.close()
        self.destroy()
        # event.accept()
        return super().closeEvent(event)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    # light(app)
    logger = log_init()
    spacer_g = QSpacerItem(40, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    spacer_v = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
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
    grBox.setLayout(gridL)
    gridL.addItem(spacer_g, 0, 0)
    gridL.addItem(spacer_g, 0, 2)
    gridL.addItem(spacer_v, 2, 1, 1, 3)
    gridL.addWidget(w_ser_dialog, 0, 1)
    grBox.setMinimumWidth(10)

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