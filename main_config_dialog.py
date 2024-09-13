from PyQt6 import QtWidgets
from qtpy.uic import loadUi
# from engine_trapezoid_dialog import EngineTrapezoidFilter
import os
import struct
import threading
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import QTimer
import qtmodern.styles
from qtmodern.windows import ModernWindow
import sys
from src.log_config import log_init, log_s, SendFilter, SendHandler
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QIntValidator, QDoubleValidator
import logging
from pymodbus.pdu import ModbusResponse
from main_hvip_dialog import MainHvipDialog as hvip_dialog

class ModbusWorker(QThread):
    # Сигнал для обновления интерфейса

    CM_DBG_SET_VOLTAGE = 0x0006
    CM_DBG_GET_VOLTAGE = 0x0009
    CMD_HVIP_ON_OFF = 0x000B

    update_signal = pyqtSignal(tuple)
    finished_signal = pyqtSignal()
    def __init__(self, root, root_d):
        super().__init__()
        self.root = root
        self.root_d = root_d
        log = logging.getLogger('pymodbus')
        log.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.addFilter(SendFilter())
        log.addHandler(handler)
        self.send_handler = SendHandler()
        log.addHandler(self.send_handler)
        self.running = True
        self.set_voltage_thread = None

class MainConfigDialog(QtWidgets.QDialog):
    lineEdit_pwm_pips   : QtWidgets.QLineEdit
    lineEdit_hvip_pips  : QtWidgets.QLineEdit
    lineEdit_pwm_sipm   : QtWidgets.QLineEdit
    lineEdit_hvip_sipm  : QtWidgets.QLineEdit
    lineEdit_pwm_ch     : QtWidgets.QLineEdit
    lineEdit_hvip_ch    : QtWidgets.QLineEdit
    lineEdit_interval   : QtWidgets.QLineEdit

    lineEdit_lvl_0_1: QtWidgets.QLineEdit
    lineEdit_lvl_0_5: QtWidgets.QLineEdit
    lineEdit_lvl_0_8: QtWidgets.QLineEdit
    lineEdit_lvl_1_6: QtWidgets.QLineEdit
    lineEdit_lvl_3: QtWidgets.QLineEdit
    lineEdit_lvl_5: QtWidgets.QLineEdit

    lineEdit_lvl_10: QtWidgets.QLineEdit
    lineEdit_lvl_30: QtWidgets.QLineEdit
    lineEdit_lvl_60: QtWidgets.QLineEdit

    pushButton_save_hvip: QtWidgets.QPushButton
    pushButton_save_mpp: QtWidgets.QPushButton
    lineEdit_cfg_mpp_id: QtWidgets.QLineEdit

    CM_DBG_SET_CFG = 0x0005
    CM_ID = 1

    def __init__(self, root, **kwargs) -> None:
        super().__init__(root, **kwargs)
        loadUi(os.path.join(os.path.dirname(__file__),  f'style/DialogConfig.ui'), self)
        self.root = root
        self.pushButton_save_mpp.clicked.connect(self.pushButton_save_mpp_handler)
        validator = QIntValidator()
        d_validator = QDoubleValidator()
        self.lineEdit_lvl_0_1.setValidator(validator)
        self.lineEdit_lvl_0_5.setValidator(validator)
        self.lineEdit_lvl_0_8.setValidator(validator)
        self.lineEdit_lvl_1_6.setValidator(validator)
        self.lineEdit_lvl_3.setValidator(validator)
        self.lineEdit_lvl_5.setValidator(validator)
        self.lineEdit_lvl_10.setValidator(validator)
        self.lineEdit_lvl_30.setValidator(validator)
        self.lineEdit_lvl_60.setValidator(validator)
        self.lineEdit_pwm_pips.setValidator(d_validator)
        self.lineEdit_hvip_pips.setValidator(d_validator)
        self.lineEdit_pwm_sipm .setValidator(d_validator)
        self.lineEdit_hvip_sipm.setValidator(d_validator)
        self.lineEdit_pwm_ch.setValidator(d_validator)
        self.lineEdit_hvip_ch.setValidator(d_validator)
        self.lineEdit_interval.setValidator(d_validator)



    def showEvent(self, event):
        self.lineEdit_lvl_0_1.setText(str(self.root.lineEdit_01_hh_l.text()))
        self.lineEdit_lvl_0_5.setText(str(self.root.lineEdit_05_hh_l.text()))
        self.lineEdit_lvl_0_8.setText(str(self.root.lineEdit_08_hh_l.text()))
        self.lineEdit_lvl_1_6.setText(str(self.root.lineEdit_1_6_hh_l.text()))
        self.lineEdit_lvl_3.setText(str(self.root.lineEdit_3_hh_l.text()))
        self.lineEdit_lvl_5.setText(str(self.root.lineEdit_5_hh_l.text()))
        self.lineEdit_lvl_10.setText(str(self.root.lineEdit_10_hh_l.text()))
        self.lineEdit_lvl_30.setText(str(self.root.lineEdit_30_hh_l.text()))
        self.lineEdit_lvl_60.setText(str(self.root.lineEdit_60_hh_l.text()))

        self.lineEdit_pwm_pips.setText("{:.2f}".format(self.root.pwm_cfg_pips))
        self.lineEdit_hvip_pips.setText("{:.2f}".format(self.root.v_cfg_pips))
        self.lineEdit_pwm_sipm .setText("{:.2f}".format(self.root.pwm_cfg_sipm))
        self.lineEdit_hvip_sipm.setText("{:.2f}".format(self.root.v_cfg_sipm))
        self.lineEdit_pwm_ch.setText("{:.2f}".format(self.root.pwm_cfg_cherenkov))
        self.lineEdit_hvip_ch.setText("{:.2f}".format(self.root.v_cfg_cherenkov))

        self.lineEdit_interval.setText(str(self.root.ddii_interval_measure))

        self.lineEdit_cfg_mpp_id.setText(str(self.root.mpp_id))

    def pushButton_save_mpp_handler(self):
        try:
            data = self.set_ddii_cfg()
            self.root.client.write_registers(address = self.CM_DBG_SET_CFG, values = data, slave = self.CM_ID)
            log_s(self.root.send_handler.mess)
            self.update_parent_data()
        except Exception as err:
            self.root.logger.debug(err)
        self.close()

    def set_ddii_cfg(self) -> list[int]:
        try:
            data = []
            data.append(0xf10f)
            data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_0_1.text()))))
            data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_0_5.text()))))
            data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_0_8.text()))))
            data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_1_6.text()))))
            data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_3.text()))))
            data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_5.text()))))
            data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_10.text()))))
            data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_30.text()))))
            data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_lvl_60.text()))))

            str_b = float(self.lineEdit_pwm_ch.text().replace(',', '.'))
            val: list[int] = self.float_to_byte(str_b)
            data += val
            str_b = float(self.lineEdit_pwm_pips.text().replace(',', '.'))
            val: list[int] = self.float_to_byte(str_b)
            data += val
            str_b = float(self.lineEdit_pwm_sipm.text().replace(',', '.'))
            val: list[int] = self.float_to_byte(str_b)
            data += val

            str_b = float(self.lineEdit_hvip_ch.text().replace(',', '.'))
            val: list[int] = self.float_to_byte(str_b)
            data += val
            str_b = float(self.lineEdit_hvip_pips.text().replace(',', '.'))
            val: list[int] = self.float_to_byte(str_b)
            data += val
            str_b = float(self.lineEdit_hvip_sipm.text().replace(',', '.'))
            val: list[int] = self.float_to_byte(str_b)
            data += val
            
            data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_cfg_mpp_id.text()))))
            data.append(int.from_bytes(struct.pack('<H', int(self.lineEdit_interval.text()))))
        except Exception as ex:
            self.root.logger.debug(ex)

        return data
    
    def update_parent_data(self):
        self.root.v_cfg_pips = float(self.lineEdit_hvip_pips.text())
        self.root.v_cfg_sipm = float(self.lineEdit_hvip_sipm.text())
        self.root.v_cfg_cherenkov = float(self.lineEdit_hvip_ch.text())
        
        self.root.pwm_cfg_pips = float(self.lineEdit_pwm_pips.text())
        self.root.pwm_cfg_sipm = float(self.lineEdit_pwm_sipm.text())
        self.root.pwm_cfg_cherenkov = float(self.lineEdit_pwm_ch.text())
        
        self.root.lineEdit_01_hh_l.setText(self.lineEdit_lvl_0_1.text())
        self.root.lineEdit_05_hh_l.setText(self.lineEdit_lvl_0_5.text())
        self.root.lineEdit_08_hh_l.setText(self.lineEdit_lvl_0_8.text())
        self.root.lineEdit_1_6_hh_l.setText(self.lineEdit_lvl_1_6.text())
        self.root.lineEdit_3_hh_l.setText(self.lineEdit_lvl_3.text())
        self.root.lineEdit_5_hh_l.setText(self.lineEdit_lvl_5.text())
        self.root.lineEdit_10_hh_l.setText(self.lineEdit_lvl_10.text())
        self.root.lineEdit_30_hh_l.setText(self.lineEdit_lvl_30.text())
        self.root.lineEdit_60_hh_l.setText(self.lineEdit_lvl_60.text())

        self.root.ddii_interval_measure = self.lineEdit_interval.text()
        self.root.mpp_id = self.lineEdit_cfg_mpp_id.text()
        self.root.lineEdit_IDmpp_2.setText(self.lineEdit_cfg_mpp_id.text())

    def float_to_byte(self, float_t) -> list:
        byte_str: bytes = struct.pack('>f', float_t)
        n0: bytes = self.root.swap_bytes(byte_str[0:2])
        n1: bytes = self.root.swap_bytes(byte_str[2:4])
        return [int(n1.hex(), 16), int(n0.hex(), 16)]
# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)
#     qtmodern.styles.dark(app)
#     # light(app)
#     w: MainConfigDialog = MainConfigDialog()
#     # w.show()
#     mw: ModernWindow = ModernWindow(w)
#     mw.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, False)  # fix flickering on resize window
#     mw.show()
#     # with open("style\Light.css", "r") as f:#QSS not CSS for pyqt5
#     #     stylesheet = f.read()
#     #     w.setStyleSheet(stylesheet)
#     #     f.close()
#     sys.exit(app.exec())

# typedef struct {
# 	uint16_t head; //+ 0
# 	uint16_t mpp_level_trig; // + 2
# 	uint16_t mpp_HH[8]; // + 4
# 	float hvip_pwm_val[3]; // + 12
# 	float hvip_voltage[3]; // + 14
#     uint8_t mpp_id;
# }typeDDII_cfg;