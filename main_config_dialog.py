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
from PyQt6.QtGui import QIntValidator, QDoubleValidator

class MainConfigDialog(QtWidgets.QDialog):
    lineEdit_pwm_pips   :  QtWidgets.QLineEdit
    lineEdit_hvip_pips  : QtWidgets.QLineEdit
    lineEdit_pwm_sipm   :  QtWidgets.QLineEdit
    lineEdit_hvip_sipm  : QtWidgets.QLineEdit
    lineEdit_pwm_ch     :    QtWidgets.QLineEdit
    lineEdit_hvip_ch    :   QtWidgets.QLineEdit
    lineEdit_interval   :  QtWidgets.QLineEdit

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

    def pushButton_save_mpp_handler(self):
        try:
            data = self.set_ddii_cfg()
            print(data)
            self.root.client.write_registers(address = self.CM_DBG_SET_CFG, values = data, slave = self.CM_ID)
            log_s(self.root.send_handler.mess)
        except Exception as err:
            self.root.logger.debug(err)
        self.close()

    def set_ddii_cfg(self):
        data = []
        data.append(0x0ff1)
        data.append(int(self.lineEdit_lvl_0_1.text()))
        data.append(int(self.lineEdit_lvl_0_5.text()))
        data.append(int(self.lineEdit_lvl_0_8.text()))
        data.append(int(self.lineEdit_lvl_1_6.text()))
        data.append(int(self.lineEdit_lvl_3.text()))
        data.append(int(self.lineEdit_lvl_5.text()))

        data.append(int(self.lineEdit_lvl_10.text()))
        data.append(int(self.lineEdit_lvl_30.text()))
        data.append(int(self.lineEdit_lvl_60.text()))

        data.append(struct.unpack('<i', struct.pack('<f', float(self.lineEdit_pwm_ch.text())))[0])
        data.append(struct.pack('<f', float(self.lineEdit_pwm_pips.text())))
        data.append(struct.pack('<f', float(self.lineEdit_pwm_sipm.text())))

        data.append(struct.pack('<f', float(self.lineEdit_hvip_ch.text())))
        data.append(struct.pack('<f', float(self.lineEdit_hvip_pips.text())))
        data.append(struct.pack('<f', float(self.lineEdit_hvip_sipm.text())))

        self.root.cfg_pips(self.lineEdit_hvip_pips)
        self.root.cfg_sipm(self.lineEdit_hvip_sipm)
        self.root.cfg_cherenkov(self.lineEdit_hvip_ch)

        data.append(int(self.lineEdit_interval.text()))
        data.append(int(self.lineEdit_cfg_mpp_id.text()))

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