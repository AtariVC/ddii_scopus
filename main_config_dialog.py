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
from src.log_config import log_init, log_s

class MainConfigDialog(QtWidgets.QDialog):
    lineEdit_pwm_pips: QtWidgets.QLineEdit
    lineEdit_hvip_pips: QtWidgets.QLineEdit
    lineEdit_pwm_sipm: QtWidgets.QLineEdit
    lineEdit_hvip_sipm: QtWidgets.QLineEdit
    lineEdit_pwm_ch: QtWidgets.QLineEdit
    lineEdit_hvip_ch: QtWidgets.QLineEdit
    lineEdit_th_100: QtWidgets.QLineEdit
    lineEdit_interval: QtWidgets.QLineEdit

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

    CM_DBG_SET_CFG = 0x0005
    CM_ID = 1

    def __init__(self, root, **kwargs) -> None:
        super().__init__(root, **kwargs)
        loadUi(os.path.join(os.path.dirname(__file__),  f'style/DialogConfig.ui'), self)
        self.root = root
        self.pushButton_save_mpp.clicked.connect(self.pushButton_save_mpp_handler)

    def pushButton_save_mpp_handler(self):
        data = self.set_ddii_cfg()
        print(data)
        self.root.client.write_registers(address = self.CM_DBG_SET_CFG, values = data[0], slave = self.CM_ID)
        log_s(self.root.send_handler.mess)

    def set_ddii_cfg(self) -> list[int]:
        data = [0x0ff1]
        data.append(int(self.lineEdit_th_100.text()))
        data.append(int(self.lineEdit_lvl_0_1.text()))
        data.append(int(self.lineEdit_lvl_0_5.text()))
        data.append(int(self.lineEdit_lvl_0_8.text()))
        data.append(int(self.lineEdit_lvl_1_6.text()))
        data.append(int(self.lineEdit_lvl_3.text()))
        data.append(int(self.lineEdit_lvl_5.text()))

        data.append(int(self.lineEdit_lvl_10.text()))
        data.append(int(self.lineEdit_lvl_30.text()))
        data.append(int(self.lineEdit_lvl_60.text()))

        data.append(struct.unpack('<I', struct.pack('<f', float(self.lineEdit_pwm_ch.text())))[0])
        data.append(struct.unpack('<I', struct.pack('<f', float(self.lineEdit_pwm_pips.text())))[0])
        data.append(struct.unpack('<I', struct.pack('<f', float(self.lineEdit_pwm_sipm.text())))[0])
        
        data.append(struct.unpack('<I', struct.pack('<f', float(self.lineEdit_hvip_ch.text())))[0])
        data.append(struct.unpack('<I', struct.pack('<f', float(self.lineEdit_hvip_pips.text())))[0])
        data.append(struct.unpack('<I', struct.pack('<f', float(self.lineEdit_hvip_sipm.text())))[0])

        data.append(int(self.lineEdit_interval.text()))
        data.append(int(self.lineEdit_))

        return data
    
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