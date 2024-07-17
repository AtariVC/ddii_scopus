from PyQt6 import QtWidgets
from qtpy.uic import loadUi
# from engine_trapezoid_dialog import EngineTrapezoidFilter
import os
import struct
import threading
from PyQt6.QtCore import QTimer



class MainHvipDialog(QtWidgets.QDialog):
    lineEdit_set_v_pips: QtWidgets.QLineEdit
    label_meas_v_pips: QtWidgets.QLabel
    pushButton_meas: QtWidgets.QPushButton
    pushButton_ok: QtWidgets.QPushButton
    pushButton_apply: QtWidgets.QPushButton
    horizontalSlider_v_pips: QtWidgets.QSlider


    V_PIPS = 0

    def __init__(self, root, **kwargs) -> None:
        super().__init__(root, **kwargs)
        loadUi(os.path.join(os.path.dirname(__file__),  f'style/HVIP_window.ui'), self)
        self.root = root
        self.pushButton_ok.clicked.connect(self.pushButton_ok_handler)
        self.pushButton_apply.clicked.connect(self.pushButton_apply_handler)
        self.pushButton_meas.clicked.connect(self.pushButton_meas_handler)
        self.horizontalSlider_v_pips.valueChanged.connect(lambda: self.slider_value_changed(self.V_PIPS))
        self.timer = QTimer()
        self.timer.timeout.connect(self.measure_voltage_pips)

        self.flag_measure = 1
        # self.timer = threading.Timer(4, self.pushButton_meas_handler)


    def slider_value_update(self, text):
        try:
            value = int(text)
            if  22 <= value <= 77:
                self.horizontalSlider_v_pips.setValue(value)
            elif value > 77:
                self.horizontalSlider_v_pips.setValue(77)
            elif value < 22:
                self.horizontalSlider_v_pips.setValue(22)
        except ValueError:
            pass
    
    def slider_value_changed(self, numlineEdit):

        match numlineEdit:
            case self.V_PIPS:
                self.lineEdit_set_v_pips.setText(str(self.horizontalSlider_v_pips.value()))
        # self.pushButton_ok_handler()


    def pushButton_ok_handler(self) -> None:

        #  Костыль, чтобы избавится от ошибки - переменная не определена
        v_pips = ""
        try:
                v_pips = int(self.lineEdit_set_v_pips.text())
                self.slider_value_update(v_pips)
        except ValueError as VErr:
            self.root.logger.debug(VErr)
            if isinstance(v_pips, int) == False:
                v_pips = 1

        # TODO: Необходма обработка ошибки, если введено ничего
        self.root.send_comand_Modbus(dev_id = 1, 
                            f_code = 16, 
                            reg_cnt = 6, 
                            comand = int(v_pips)) # установка в 50В: 01 10 00 06 00 32 A1 DD 
        self.timer.start(1000)
        self.pushButton_meas.setText("Остановить")
        self.flag_measure = 0

    def pushButton_apply_handler(self) -> None:
        self.timer.stop()
        # self.timer.cancel()
        self.close()


    def measure_voltage_pips(self):
        try:
            # Измерение напряжения: 01 10 00 07 00 00 71 C8
            self.root.send_comand_Modbus(dev_id = 1,
                                        f_code = 16, 
                                        comand = 0, 
                                        reg_cnt = self.root.HVIP_PIPS_READ_VOLTAGE) 
            transaction = self.root.get_transaction_Modbus(num_bite =4)
            decimal_transaction = int(transaction, 16)
            byte_transaction : bytes = decimal_transaction.to_bytes(len(transaction)//2, byteorder='big')
            float_transaction: float = struct.unpack('<f', byte_transaction)[0]
            self.root.logger.debug("Напряжение PIPS: " + "{:.2f}".format(float_transaction))
            self.label_meas_v_pips.setText("{:.2f}".format(float_transaction))
        except struct.error:
            self.root.logger.debug("unpack requires a buffer of 4 bytes")
            # self.timer.start()

    def pushButton_meas_handler(self) -> None:
        """
        Обработчик нажатия кнопки "Измерить напряжение ВИП"
        """
        if self.flag_measure == 1:
            self.measure_voltage_pips()
            
            # self.flag_measure = 0
        else:
            self.pushButton_meas.setText("Измерить")
            self.flag_measure = 1
            self.timer.stop()
        