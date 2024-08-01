from PyQt6 import QtWidgets
from qtpy.uic import loadUi
from src.log_config import log_init, log_s, SendFilter, SendHandler
# from engine_trapezoid_dialog import EngineTrapezoidFilter
import os
import struct
from style.styleSheet import styleSheet as style
import sys
import threading
import logging
from PyQt6.QtCore import QTimer
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QDoubleValidator, QCloseEvent


class ModbusWorker(QThread):
    # Сигнал для обновления интерфейса
    update_signal = pyqtSignal(str)
    def __init__(self, root):
        super().__init__()
        self.root = root
        log = logging.getLogger('pymodbus')
        log.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.addFilter(SendFilter())
        log.addHandler(handler)
        self.send_handler = SendHandler()
        log.addHandler(self.send_handler)

    def get_hvip_data(self):
        self.root.client.write_registers(address=0x0001, values=1, slave=1)
        result = self.root.client.read_holding_registers(0x0000, 62, slave=1)
        log_s(self.send_handler.mess)

    ## TODO: Переписать через update_signal
    def th_measure_voltage_pips(self):
        self.root.measure_voltage_pips

    def update_label_data(self):
        pass
    def send_hvip_data(self):
        pass

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

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

    PIPS_CH_VOLTAGE = 1
    SIPM_CH_VOLTAGE = 2
    CHERENKOV_CH_VOLTAGE = 3

    CM_DBG_SET_VOLTAGE = 0x0006
    CM_DBG_GET_VOLTAGE = 0x0009

    def __init__(self, root, **kwargs) -> None:
        super().__init__(root, **kwargs)
        loadUi(os.path.join(os.path.dirname(__file__),  f'style/HVIP_window.ui'), self)
        self.root = root
        self.modbus_worker = ModbusWorker(root)
        self.spinBox_pips_volt.setValue(root.v_cfg_pips)
        self.spinBox_sipm_volt.setValue(root.v_cfg_sipm)
        self.spinBox_ch_volt.setValue(root.v_cfg_cherenkov)

        self.doubleSpinBox_pips_pwm.setValue(root.hvip_pwm_pips)
        self.doubleSpinBox_sipm_pwm.setValue(root.hvip_pwm_sipm)
        self.doubleSpinBox_ch_pwm.setValue(root.hvip_pwm_ch)

        self.label_pips_mes.setText("{:.2f}".format(root.hvip_pips))
        self.label_sipm_mes.setText("{:.2f}".format(root.hvip_sipm))
        self.label_ch_mes.setText("{:.2f}".format(root.hvip_ch))

        self.label_pips_cur.setText("{:.2f}".format(root.hvip_current_pips))
        self.label_sipm_cur.setText("{:.2f}".format(root.hvip_current_sipm))
        self.label_ch_cur.setText("{:.2f}".format(root.hvip_current_ch))

        self.label_pips_pwm_mes.setText("{:.2f}".format(root.hvip_pwm_pips))
        self.label_sipm_pwm_mes.setText("{:.2f}".format(root.hvip_pwm_sipm))
        self.label_ch_pwm_mes.setText("{:.2f}".format(root.hvip_pwm_ch))

        if root.hvip_mode_pips == 1:
            self.pushButton_pips_on.setText("Отключить")
            self.led_pips.setStyleSheet(style.widget_led_on())
        if root.hvip_mode_sipm == 1:
            self.pushButton_sipm_on.setText("Отключить")
            self.led_sipm.setStyleSheet(style.widget_led_on())
        if root.hvip_mode_ch == 1:
            self.pushButton_ch_on.setText("Отключить")
            self.led_ch.setStyleSheet(style.widget_led_on())

        self.pushButton_ok.clicked.connect(self.pushButton_ok_handler)
        self.pushButton_apply.clicked.connect(self.pushButton_apply_handler)

        self.pushButton_pips_on.clicked.connect(self.pushButton_pips_on_handler)
        self.pushButton_sipm_on.clicked.connect(self.pushButton_sipm_on_handler)
        self.pushButton_ch_on.clicked.connect(self.pushButton_ch_on_handler)
        # # self.horizontalSlider_v_pips.valueChanged.connect(lambda: self.slider_value_changed(self.V_PIPS))
        self.timer = QTimer()
        self.timer.timeout.connect(self.measure_voltage_pips)
        self.timer.start(10)
        # self.spinBox_pips_volt.setValidator(double_validator)
        # self.label_sipm_mes.setValidator(double_validator)
        # self.label_ch_mes.setValidator(double_validator)
        self.flag_measure = 1

        # self.timer = threading.Timer(4, self.pushButton_meas_handler)

    # def slider_value_update(self, text):
    #     try:
    #         value = int(text)
    #         if  22 <= value <= 77:
    #             self.horizontalSlider_v_pips.setValue(value)
    #         elif value > 77:
    #             self.horizontalSlider_v_pips.setValue(77)
    #         elif value < 22:
    #             self.horizontalSlider_v_pips.setValue(22)
    #     except ValueError:
    #         pass
    
    # def slider_value_changed(self, numlineEdit):

    #     match numlineEdit:
    #         case self.V_PIPS:
    #             self.lineEdit_set_v_pips.setText(str(self.horizontalSlider_v_pips.value()))
    #     # self.pushButton_ok_handler()
    
    def pushButton_pips_on_handler(self):
        pips_on = threading.Thread(target=self.modbus_worker.get_hvip_data, daemon = True)
        pips_on.start()

    def pushButton_sipm_on_handler(self):
        pass

    def pushButton_ch_on_handler(self):
        pass

    def pushButton_apply_handler(self) -> None:
        #  Костыль, чтобы избавится от ошибки - переменная не определена
        try:
            float_t = float(self.spinBox_pips_volt.text().replace(',', '.'))
            v_pips: bytes = struct.pack('>f', float_t)
            v_pips_l = [int(v_pips[0:2].hex(), 16), int(v_pips[2:4].hex(), 16)]
            float_t = float(self.spinBox_sipm_volt.text().replace(',', '.'))
            v_sipm: bytes = struct.pack('>f', float_t)
            v_sipm_l = [int(v_sipm[0:2].hex(), 16), int(v_sipm[2:4].hex(), 16)]
            float_t = float(self.spinBox_ch_volt.text().replace(',', '.'))
            v_ch: bytes = struct.pack('>f', float_t)
            v_ch_l = [int(v_ch[0:2].hex(), 16), int(v_ch[2:4].hex(), 16)]
            data = v_pips_l + v_sipm_l + v_ch_l
            self.root.client.write_registers(address = self.CM_DBG_SET_VOLTAGE,
                                values = data, 
                                slave = self.root.CM_ID)
            log_s(self.root.send_handler.mess)
            self.timer.start(1000)
            self.flag_measure = 0
        except Exception as VErr:
            self.root.logger.debug(VErr)
        

    def pushButton_ok_handler(self) -> None:
        try:
            float_t = float(self.spinBox_pips_volt.text().replace(',', '.'))
            v_pips: bytes = struct.pack('>f', float_t)
            v_pips_l = [int(v_pips[0:2].hex(), 16), int(v_pips[2:4].hex(), 16)]
            float_t = float(self.spinBox_sipm_volt.text().replace(',', '.'))
            v_sipm: bytes = struct.pack('>f', float_t)
            v_sipm_l = [int(v_sipm[0:2].hex(), 16), int(v_sipm[2:4].hex(), 16)]
            float_t = float(self.spinBox_ch_volt.text().replace(',', '.'))
            v_ch: bytes = struct.pack('>f', float_t)
            v_ch_l = [int(v_ch[0:2].hex(), 16), int(v_ch[2:4].hex(), 16)]
            data = v_pips_l + v_sipm_l + v_ch_l
            self.root.client.write_registers(address = self.CM_DBG_SET_VOLTAGE,
                                values = data, 
                                slave = self.root.CM_ID)
            log_s(self.root.send_handler.mess)
            self.timer.stop()
        except Exception as VErr:
            self.root.logger.debug(VErr)
        self.timer.stop()
        self.close()

    def measure_voltage_pips(self):
        try:
            # Измерение напряжения: 01 10 00 07 00 00 71 C8
            transaction = self.get_voltage()
            voltage = self.root.parse_voltage(transaction)
            ### pips ###
            self.label_pips_mes.setText("{:.2f}".format(voltage[0]))
            self.label_pips_pwm_mes.setText("{:.2f}".format(voltage[1]))
            self.label_pips_cur.setText("{:.2f}".format(voltage[2]))
            if voltage[3] == 1:
                self.pushButton_pips_on.setText("Отключить")
                self.led_pips.setStyleSheet(style.widget_led_on())
            elif voltage[3] == 0:
                self.pushButton_pips_on.setText("Включить")
                self.led_pips.setStyleSheet(style.widget_led_off())
            else:
                self.root.logger.debug("Ошибка работы HVIP PIPS")
            ### sipm ###
            self.label_sipm_mes.setText("{:.2f}".format(voltage[4]))
            self.label_sipm_pwm_mes.setText("{:.2f}".format(voltage[5]))
            self.label_sipm_cur.setText("{:.2f}".format(voltage[6]))
            if voltage[7] == 1:
                self.pushButton_sipm_on.setText("Отключить")
                self.led_sipm.setStyleSheet(style.widget_led_on())
            elif voltage[7] == 0:
                self.pushButton_sipm_on.setText("Включить")
                self.led_sipm.setStyleSheet(style.widget_led_off())
            else:
                self.root.logger.debug("Ошибка работы HVIP SIPM")
            ### ch ###
            self.label_ch_mes.setText("{:.2f}".format(voltage[8]))
            self.label_ch_pwm_mes.setText("{:.2f}".format(voltage[9]))
            self.label_ch_cur.setText("{:.2f}".format(voltage[10]))
            if voltage[3] == 1:
                self.pushButton_ch_on.setText("Отключить")
                self.led_ch.setStyleSheet(style.widget_led_on())
            elif voltage[3] == 0:
                self.pushButton_ch_on.setText("Включить")
                self.led_ch.setStyleSheet(style.widget_led_off())
            else:
                self.root.logger.debug("Ошибка работы HVIP CHERENKOV")

        except struct.error as err:
            self.root.logger.debug(err)
            self.timer.stop()
    
    def get_voltage(self):
        self.root.client.write_registers(address = self.root.DDII_SWITCH_MODE, values = self.root.DEBUG_MODE, slave = self.root.CM_ID)
        result = self.root.client.read_holding_registers(self.CM_DBG_GET_VOLTAGE, 16, slave=self.root.CM_ID)
        log_s(self.root.send_handler.mess)
        self.root.client.write_registers(address = self.root.DDII_SWITCH_MODE, values = self.root.COMBAT_MODE, slave = self.root.CM_ID)
        return result
    
    def closeEvent(self, event) -> None:
        self.timer.stop()
        self.modbus_worker.stop()
        self.close()
        self.destroy()
        event.accept()
        return super().closeEvent(event)
    
    

    # def pushButton_meas_handler(self) -> None:
    #     """
    #     Обработчик нажатия кнопки "Измерить напряжение ВИП"
    #     """
    #     if self.flag_measure == 1:
    #         self.measure_voltage_pips()
            
    #         # self.flag_measure = 0
    #     else:
    #         self.pushButton_meas.setText("Измерить")
    #         self.flag_measure = 1
    #         self.timer.stop()
        