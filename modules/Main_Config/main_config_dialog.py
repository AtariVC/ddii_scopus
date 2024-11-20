from PyQt6 import QtWidgets
from qtpy.uic import loadUi
from qasync import asyncSlot
import qasync
from PyQt6.QtWidgets import QGroupBox, QGridLayout, QSpacerItem, QSizePolicy, QLineEdit
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
from src.log_config import log_init                                 # noqa: E402
from src.env_var import EnvironmentVar                               # noqa: E402
from src.parsers_pack import LineEObj, LineEditPack                 # noqa: E402


class MainConfigDialog(QtWidgets.QDialog, EnvironmentVar):
    lineEdit_pwm_pips                   : QtWidgets.QLineEdit
    lineEdit_hvip_pips                  : QtWidgets.QLineEdit
    lineEdit_pwm_sipm                   : QtWidgets.QLineEdit
    lineEdit_hvip_sipm                  : QtWidgets.QLineEdit
    lineEdit_pwm_ch                     : QtWidgets.QLineEdit
    lineEdit_hvip_ch                    : QtWidgets.QLineEdit
    lineEdit_interval                   : QtWidgets.QLineEdit

    lineEdit_lvl_0_1                    : QtWidgets.QLineEdit
    lineEdit_lvl_0_5                    : QtWidgets.QLineEdit
    lineEdit_lvl_0_8                    : QtWidgets.QLineEdit
    lineEdit_lvl_1_6                    : QtWidgets.QLineEdit
    lineEdit_lvl_3                      : QtWidgets.QLineEdit
    lineEdit_lvl_5                      : QtWidgets.QLineEdit

    lineEdit_lvl_10                     : QtWidgets.QLineEdit
    lineEdit_lvl_30                     : QtWidgets.QLineEdit
    lineEdit_lvl_60                     : QtWidgets.QLineEdit

    label_check_cfg                    : QtWidgets.QLabel

    pushButton_save_hvip                : QtWidgets.QPushButton
    pushButton_save_mpp                 : QtWidgets.QPushButton
    lineEdit_cfg_mpp_id                 : QtWidgets.QLineEdit
    vLayout_ser_connect                 : QtWidgets.QVBoxLayout

    radioButton_mpp                     : QtWidgets.QRadioButton
    radioButton_cm                      : QtWidgets.QRadioButton

    pushButton_Get_Rst                  : QtWidgets.QPushButton

    CM_DBG_SET_CFG = 0x0005
    CM_ID = 1
    #CM_DBG_SET_VOLTAGE = 0x0006
    #CM_DBG_GET_VOLTAGE = 0x0009
    #CMD_HVIP_ON_OFF = 0x000B

    def __init__(self, logger, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).resolve().parent.parent.parent.joinpath('frontend/DialogConfig.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.logger = logger
        i_validator = QIntValidator()
        d_validator = QDoubleValidator()
        self.config = ConfigSaver(self)
        self.flg_get_rst = 0
        self.label_check_cfg.setText("Status: ")
        self.initValidator(i_validator, d_validator)
        if __name__ == "__main__":
            self.w_ser_dialog: SerialConnect = args[0]
            self.w_ser_dialog.coroutine_finished.connect(self.get_client)
        else:
            self.client: AsyncModbusSerialClient = args[0]
            self.cm_cmd: ModbusCMCommand = ModbusCMCommand(self.client, self.logger)
            self.mpp_cmd: ModbusMPPCommand = ModbusMPPCommand(self.client, self.logger)
        self.pushButton_save_mpp.clicked.connect(self.pushButton_save_cfg_handler)
        self.pushButton_Get_Rst.clicked.connect(self.pushButton_get_rst_handler)
        self.le_obj: dict[str, QLineEdit] = self.init_linEdit_list()

    def init_linEdit_list(self) -> dict[str, QtWidgets.QLineEdit]:
        le_obj: dict[str, QtWidgets.QLineEdit] = {
                    "lineEdit_lvl_0_1": self.lineEdit_lvl_0_1,

                    "lineEdit_lvl_0_5": self.lineEdit_lvl_0_5,
                    "lineEdit_lvl_0_8": self.lineEdit_lvl_0_8,
                    "lineEdit_lvl_1_6": self.lineEdit_lvl_1_6,
                    "lineEdit_lvl_3": self.lineEdit_lvl_3,
                    "lineEdit_lvl_5": self.lineEdit_lvl_5,
                    "lineEdit_lvl_10": self.lineEdit_lvl_10,
                    "lineEdit_lvl_30": self.lineEdit_lvl_30,
                    "lineEdit_lvl_60": self.lineEdit_lvl_60,

                    "lineEdit_pwm_ch": self.lineEdit_pwm_ch,
                    "lineEdit_pwm_pips": self.lineEdit_pwm_pips,
                    "lineEdit_pwm_sipm": self.lineEdit_pwm_sipm,

                    "lineEdit_hvip_ch": self.lineEdit_hvip_ch,
                    "lineEdit_hvip_pips": self.lineEdit_hvip_pips,
                    "lineEdit_hvip_sipm": self.lineEdit_hvip_sipm,

                    "lineEdit_cfg_mpp_id": self.lineEdit_cfg_mpp_id,
                    "lineEdit_interval": self.lineEdit_interval
                    }
        return le_obj

    @asyncSlot()
    async def get_client(self) -> None:
        """Функция перехватывает client и переподключается к нему
        """
        try:
            if self.w_ser_dialog.pushButton_connect_flag == 1:
                self.client: AsyncModbusSerialClient = self.w_ser_dialog.client
                await self.client.connect()
                # print(self.client.is_connected())
                self.cm_cmd: ModbusCMCommand = ModbusCMCommand(self.client, self.logger)
                self.mpp_cmd: ModbusMPPCommand = ModbusMPPCommand(self.client, self.logger)
                if self.w_ser_dialog.status_CM == 1:
                    await self.update_gui_data_cm()
                    self.radioButton_cm.setChecked(True)
                    self.radioButton_cm.setEnabled(True)
                    if self.w_ser_dialog.status_MPP == 0:
                        self.radioButton_mpp.setEnabled(False)
                        self.radioButton_mpp.setChecked(False)
                    else:
                        self.radioButton_mpp.setEnabled(True)
                if self.w_ser_dialog.status_CM == 0:
                        self.radioButton_cm.setChecked(False)
                        self.radioButton_cm.setEnabled(False)
                if self.w_ser_dialog.status_CM == 0 and self.w_ser_dialog.status_MPP == 0:
                    self.radioButton_cm.setChecked(True)
                    self.radioButton_cm.setEnabled(False)
                    self.radioButton_mpp.setEnabled(False)
                
        except Exception:
            pass

    @asyncSlot()
    async def update_gui_data_mpp(self) -> None:
        try:
            answer: bytes = await self.mpp_cmd.get_hh()
            tel_dict: dict[str, str] = await self.parser.pars_mpp_hh(answer)

            answ_lvl: bytes = await self.mpp_cmd.get_level()
            tel_dict_lvl: dict[str, str] = await self.parser.pars_mpp_lvl(answ_lvl)

            self.lineEdit_lvl_0_1.setText(str(tel_dict_lvl["01_hh_l"]))

            for i, (key, val) in enumerate(self.le_obj.items()):
                if 0 < i < 9:
                    val.setText(list(tel_dict.values())[i-1])

        except Exception as e:
            self.logger.error(e)

    @asyncSlot()    
    async def update_gui_data_cm(self) -> None:
        try:
            answer: bytes = await self.cm_cmd.get_cfg_ddii()
            tel_dict: dict = await self.parser.pars_cfg_ddii(answer)
            for i, (key, val) in enumerate(self.le_obj.items()):
                val.setText(list(tel_dict.values())[i])            
        except Exception as e:
            self.logger.error(e)

    def closeEvent(self, event) -> None:
        try:
            if self.client.connected:
                self.client.close()
        except Exception:
            pass

    @asyncSlot()
    async def pushButton_save_cfg_handler(self) -> None:
        head: list[int] = [int(self.HEAD.to_bytes(2, 'little').hex(), 16)]
        if self.radioButton_cm.isChecked():
            try:
                data: list[int] = await self.get_cfg_data_from_widget("cm")
                await self.cm_cmd.set_cfg_ddii(head + data)
                self.config.save_to_config()
                self.logger.debug("config_dialog.yaml update")
                self.label_check_cfg.setText("Status: CM config writed")
                # await asyncio.sleep(0.3)
                # if await self.cheack_writed_cfg(data, "cm"):
                #     self.label_check_cfg.setText("Проверка записи: CM data correct")
                # else:
                #     self.label_check_cfg.setText("Проверка записи: CM data uncorrect")
            except Exception as e:
                self.logger.debug(e)
        if self.radioButton_mpp.isChecked():
            try:
                data: list[int] = await self.get_cfg_data_from_widget("mpp")
                await self.mpp_cmd.set_level(data[0])
                await self.mpp_cmd.set_hh(data[1:9])
                await asyncio.sleep(0.3)
                if await self.check_writed_cfg(data[0:9], "mpp"):
                    self.label_check_cfg.setText("Status: MPP config writed correct")
                    self.config.save_to_config()
                    self.logger.debug("config_dialog.yaml update")
                else:
                    self.label_check_cfg.setText("Status: MPP config writed uncorrect")
            except Exception as e:
                self.logger.debug(e)
    
    @asyncSlot()
    async def check_writed_cfg(self, data: list[int], device: str) -> bool:
        """Поверяет записалась ли в память конфигурация
        Args:
            data (list[int]): отправленные данные концигурации
            device (str): 
            - "cm"
            - "mpp"
        Returns:
            bool: Статус проверки
        """
        try:
            if device == "mpp":
                cheack_lvl: bytes = await self.mpp_cmd.get_level()
                cheack_hh: bytes = await self.mpp_cmd.get_hh()
                d_cheack_lvl: dict[str, str] =  await self.parser.pars_mpp_lvl(cheack_lvl)
                d_cheack_hh: dict[str, str] = await self.parser.pars_mpp_hh(cheack_hh)
                if list(map(int, d_cheack_hh.values())) == data[1:9] and \
                        list(map(int, d_cheack_lvl.values())) == data[:1]:
                    return True
                else:
                    return False
        except Exception as e:
            self.logger.error(e)

        try:
            if device == "cm": # для цм не работает из-за точности float
                cheack_cfg_ddii: bytes = await self.cm_cmd.get_cfg_ddii()
                d_cheack_cfg_ddii:list[int] =  [int.from_bytes(cheack_cfg_ddii[i*2:i*2+2], "little") for i in range(2, 24)]
                if d_cheack_cfg_ddii == data[1:]:
                    return True
                else:
                    return False
        except Exception as e:
            self.logger.error(e)

        return False



    @asyncSlot()
    async def pushButton_get_rst_handler(self) -> None:
        if self.flg_get_rst == 0:
            if self.radioButton_cm.isChecked() and self.w_ser_dialog.status_CM == 1:
                await self.update_gui_data_cm()
                self.label_check_cfg.setText("Status: Get CM config")
                self.pushButton_Get_Rst.setText("R")
                self.flg_get_rst = 1
            if self.radioButton_mpp.isChecked() and self.w_ser_dialog.status_MPP == 1:
                await self.update_gui_data_mpp()
                self.pushButton_Get_Rst.setText("R")
                self.label_check_cfg.setText("Status: Get MMP config")
                self.flg_get_rst = 1
            
        else:
            self.pushButton_Get_Rst.setText("G")
            self.label_check_cfg.setText("Status: Reset data")
            self.config.load_from_config()
            self.flg_get_rst = 0

    @asyncSlot()
    async def get_cfg_data_from_widget(self, device: str) -> list[int]:
        """Получает данные с виджетов и упаковывает их в пакет
        Args:
            device (str): Указать модуль:
            - "cm"
            - "mpp"
        Returns:
            list[int]: Пакет для отправки по ВШ
        """
        pack: list[LineEObj] = [LineEObj(key=key, lineobj_txt=value.text(), tp=('f' if 8 < i < 15 else 'i')) 
        for  i, (key, value) in enumerate(self.le_obj.items())]
        get_data_widget = LineEditPack()
        if device == 'mpp':
            return get_data_widget(pack, 'big')
        if device == 'cm':
            return get_data_widget(pack, 'little')
        else:
            return []


    def initValidator(self, validator, d_validator) -> None:
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

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    # light(app)
    logger = log_init()
    spacer_g = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    spacer_v = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
    w_ser_dialog: SerialConnect = SerialConnect(logger)
    w: MainConfigDialog = MainConfigDialog(logger, w_ser_dialog)
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
