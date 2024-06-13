import re
import struct
from PyQt6 import QtWidgets
from qtpy.uic import loadUi
# from engine_trapezoid_dialog import EngineTrapezoidFilter
import os
from PyQt6.QtCore import QTimer


class MainMppControlDialog(QtWidgets.QDialog):
    lineEdit_level_pips: QtWidgets.QLineEdit
    lineEdit_level_sipm: QtWidgets.QLineEdit
    label_current_level_pips: QtWidgets.QLabel
    label_current_level_sipm: QtWidgets.QLabel

    pushButton_control_pips: QtWidgets.QPushButton
    pushButton_control_sipm: QtWidgets.QPushButton
    pushButton_ok: QtWidgets.QPushButton
    pushButton_apply: QtWidgets.QPushButton
    pushButton_request_level_mpp_pips: QtWidgets.QPushButton
    pushButton_request_level_mpp_sipm: QtWidgets.QPushButton

    horizontalSlider_offset_pips: QtWidgets.QSlider
    horizontalSlider_offset_sipm: QtWidgets.QSlider

    CM_ID = 1
    F_CODE = 16
    CNTRL_PIPS = 8
    CNTRL_SIPM = 9
    REQUEST_PIPS = 10
    REQUEST_SIPM = 11
    MMP_ENABLE = 12
    


    def __init__(self, root, **kwargs) -> None:
        super().__init__(root, **kwargs)
        loadUi(os.path.join(os.path.dirname(__file__),  'style/DialogControlMPP.ui'), self)
        self.root = root
        self.pushButton_control_pips.clicked.connect(self.pushButton_control_pips_handler)
        self.pushButton_apply.clicked.connect(self.pushButton_apply_handler)
        self.pushButton_ok.clicked.connect(self.pushButton_ok_handler)
        self.pushButton_request_level_mpp_pips.clicked.connect(self.pushButton_request_level_mpp_pips_handler)
        self.pushButton_request_level_mpp_sipm.clicked.connect(self.pushButton_request_level_mpp_sipm_handler)
        self.pushButton_control_sipm.clicked.connect(self.pushButton_control_sipm_handler)

        self.horizontalSlider_offset_pips.valueChanged.connect(lambda: self.slider_value_changed(self.CNTRL_PIPS))
        self.horizontalSlider_offset_sipm.valueChanged.connect(lambda: self.slider_value_changed(self.CNTRL_SIPM))

    def slider_value_changed(self, numlineEdit):

        match numlineEdit:
            case self.CNTRL_PIPS:
                self.lineEdit_level_pips.setText(str(self.horizontalSlider_offset_pips.value()))
            case self.CNTRL_SIPM:
                self.lineEdit_level_sipm.setText(str(self.horizontalSlider_offset_sipm.value()))
        # self.pushButton_ok_handler()
    
    def slider_value_update(self, text, numlineEdit):
        match numlineEdit:
            case self.CNTRL_PIPS:
                try:
                    value = int(text)
                    if  0 <= value <= 4095:
                        self.horizontalSlider_offset_pips.setValue(value)
                    elif value > 4095:
                        self.horizontalSlider_offset_pips.setValue(4095)
                    elif value < 0:
                        self.horizontalSlider_offset_pips.setValue(0)
                except ValueError:
                    pass
            case self.CNTRL_SIPM:
                try:
                    value = int(text)
                    if  0 <= value <= 4095:
                        self.horizontalSlider_offset_sipm.setValue(value)
                    elif value > 4095:
                        self.horizontalSlider_offset_sipm.setValue(4095)
                    elif value < 0:
                        self.horizontalSlider_offset_sipm.setValue(0)
                except ValueError:
                    pass


        # self.flag_measure = 1
    ############ handler button ##############
    def pushButton_control_pips_handler(self) -> None:
        """
            01 16 00 0A 00 00 68 0B
            |   | |__|   |__|   |-- CRC16 (младший байт первый, старший байт последний)
            |   |    |      |-- command Сюда записываются передаваемые значения
            |   |    |-- reg_cnt Cюда записывается номер команды
            |   |-- f_code Команда записи массива
            |-- ЦМ ID
        """
        #  Костыль, чтобы избавится от ошибки - переменная не определена
        level_pips = ""
        try:
                level_pips = int(self.lineEdit_level_pips.text())
                self.slider_value_update(level_pips, self.CNTRL_PIPS)
        except ValueError as VErr:
            self.root.logger.debug(VErr)
            if isinstance(level_pips, int) == False:
                level_pips = 1

        self.root.send_comand_Modbus(dev_id = self.CM_ID,
                            f_code = 16,
                            reg_cnt = self.CNTRL_PIPS,
                            comand = level_pips)
        self.root.get_transaction_Modbus(2)
        # self.root.ser.reset_input_buffer()
        # self.pushButton_request_level_mpp_pips_handler()
        # self.root.pushButton_single_measure_clicked(self.root.PIPS)

    def pushButton_control_sipm_handler(self) -> None:
        """
            01 16 00 0B 00 00 39 CB
            |   | |__|   |__|   |-- CRC16 (младший байт первый, старший байт последний)
            |   |    |      |-- command Сюда записываются передаваемые значения
            |   |    |-- reg_cnt Cюда записывается номер команды
            |   |-- f_code Команда записи массива
            |-- ЦМ ID
        """
        level_sipm = ""
        try:
                level_sipm = int(self.lineEdit_level_sipm.text())
                self.slider_value_update(level_sipm, self.CNTRL_SIPM)
        except ValueError as VErr:
            self.root.logger.debug(VErr)
            if isinstance(level_sipm, int) == False:
                level_sipm = 1

        self.root.send_comand_Modbus(dev_id = self.CM_ID,
                            f_code = self.F_CODE,
                            reg_cnt = self.CNTRL_SIPM,
                            comand = level_sipm)
        # self.pushButton_request_level_mpp_sipm_handler()
        # self.root.pushButton_single_measure_clicked(self.root.SIPM)
        

    def pushButton_apply_handler(self) -> None:
        self.close()
    
    def pushButton_ok_handler(self) -> None:
        self.root.send_comand_Modbus(dev_id = self.CM_ID,
                            f_code = self.F_CODE,
                            reg_cnt = self.MMP_ENABLE,
                            comand = 0)
        self.root.get_transaction_Modbus(2)

    def pushButton_request_level_mpp_pips_handler(self) -> None:
        self.root.send_comand_Modbus(dev_id = self.CM_ID,
                                    f_code = self.F_CODE,
                                    reg_cnt = self.REQUEST_PIPS,
                                    comand = 0)
        transaction = self.root.get_transaction_Modbus(2)
        offset_pips = ''.join(re.findall(r'\w\w', transaction)[::-1])
        decimal_offset_pips = int(offset_pips, 16)
        self.label_current_level_pips.setText("{:}".format(decimal_offset_pips))

    def pushButton_request_level_mpp_sipm_handler(self) -> None:
        self.root.send_comand_Modbus(dev_id = self.CM_ID,
                                    f_code = self.F_CODE,
                                    reg_cnt = self.REQUEST_SIPM,
                                    comand = 0)
        transaction = self.root.get_transaction_Modbus(2)
        offset_sipm = ''.join(re.findall(r'\w\w', transaction)[::-1])
        decimal_offset_sipm = int(offset_sipm, 16)
        self.label_current_level_sipm.setText("{:}".format(decimal_offset_sipm))

        