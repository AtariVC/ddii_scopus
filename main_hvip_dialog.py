from PyQt6 import QtWidgets
from qtpy.uic import loadUi
# from engine_trapezoid_dialog import EngineTrapezoidFilter
import os
import struct
import threading
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QDoubleValidator



class MainHvipDialog(QtWidgets.QDialog):
    spinBox_pips_volt: QtWidgets.QSpinBox
    spinBox_sipm_volt: QtWidgets.QSpinBox
    spinBox_ch_volt: QtWidgets.QSpinBox
    label_pips_mes: QtWidgets.QLabel
    label_sipm_mes: QtWidgets.QLabel
    label_ch_mes: QtWidgets.QLabel
    pushButton_ok: QtWidgets.QPushButton
    pushButton_apply: QtWidgets.QPushButton

    PIPS_CH_VOLTAGE = 1
    SIPM_CH_VOLTAGE = 2
    CHERENKOV_CH_VOLTAGE = 3

    CM_DBG_SET_VOLTAGE = 0x0006

    def __init__(self, root, **kwargs) -> None:
        super().__init__(root, **kwargs)
        loadUi(os.path.join(os.path.dirname(__file__),  f'style/HVIP_window.ui'), self)
        self.root = root
        self.spinBox_pips_volt.setValue(root.cfg_cherenkov)
        self.spinBox_sipm_volt.setValue(root.cfg_pips)
        self.spinBox_ch_volt.setValue(root.cfg_sipm)
        self.pushButton_ok.clicked.connect(self.pushButton_ok_handler)
        self.pushButton_apply.clicked.connect(self.pushButton_apply_handler)
        # # self.horizontalSlider_v_pips.valueChanged.connect(lambda: self.slider_value_changed(self.V_PIPS))
        self.timer = QTimer()
        # self.timer.timeout.connect(self.measure_voltage_pips)
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

    def pushButton_apply_handler(self) -> None:
        #  Костыль, чтобы избавится от ошибки - переменная не определена
        try:
            v_pips = int(self.spinBox_pips_volt.text())
            v_sipm = int(self.spinBox_sipm_volt.text())
            v_ch = int(self.spinBox_ch_volt.text())
            self.root.write_registers(address = self.CM_DBG_SET_VOLTAGE, 
                                values = [v_pips, v_sipm, v_ch], 
                                slave = self.root.CM_ID)
            self.root.log_s(self.root.send_handler.mess)
            self.timer.start(1000)
            self.flag_measure = 0
        except Exception as VErr:
            self.root.logger.debug(VErr)
        

    def pushButton_ok_handler(self) -> None:
        try:
            v_pips = int(self.spinBox_pips_volt.text())
            v_sipm = int(self.spinBox_sipm_volt.text())
            v_ch = int(self.spinBox_ch_volt.text())
            self.root.write_registers(address = self.CM_DBG_SET_VOLTAGE, 
            values = [v_pips, v_sipm, v_ch], 
            slave = self.root.CM_ID)
            self.root.log_s(self.root.send_handler.mess)
            self.timer.stop()
        except Exception as VErr:
            self.root.logger.debug(VErr)
        self.close()



    def measure_voltage_pips(self):
        try:
            # Измерение напряжения: 01 10 00 07 00 00 71 C8
            self.root.send_comand_Modbus(dev_id = 1,
                                        f_code = 16, 
                                        comand = 0, 
                                        reg_cnt = self.root.HVIP_PIPS_READ_VOLTAGE)
            transaction = self.root.client.read_holding_registers(self.root.CM_DBG_GET_VOLTAGE, 6, slave=1)
            self.root.log_s(self.root.send_handler.mess)
            voltage = self.root.parse_voltage(transaction)
            self.label_pips_mes.setText("{:.2f}".format(voltage[0]))
            self.label_sipm_mes.setText("{:.2f}".format(voltage[1]))
            self.label_ch_mes.setText("{:.2f}".format(voltage[2]))
        except struct.error as err:
            self.root.logger.debug(err)
            self.timer.start()
    
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
        