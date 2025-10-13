import asyncio
import sys
from pathlib import Path

import qasync
import qtmodern.styles
from pymodbus.client import AsyncModbusSerialClient
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QDoubleValidator, QFont, QIntValidator
from PyQt6.QtWidgets import QGridLayout, QGroupBox, QLineEdit, QSizePolicy, QSpacerItem
from qtpy.uic import loadUi
from save_config import ConfigSaver

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from modules.Main_Serial.main_serial_dialog_tcp import SerialConnect  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.env_var import EnvironmentVar  # noqa: E402
from src.log_config import log_init  # noqa: E402
from src.async_task_manager import AsyncTaskManager  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
from src.parsers import Parsers  # noqa: E402
from src.parsers_pack import LineEditPack, LineEObj  # noqa: E402


class MainConfigDialog(QtWidgets.QDialog, EnvironmentVar):
    lineEdit_interval: QtWidgets.QLineEdit

    lineEdit_hvip_pips: QtWidgets.QLineEdit
    lineEdit_hvip_sipm: QtWidgets.QLineEdit
    lineEdit_hvip_ch: QtWidgets.QLineEdit

    lineEdit_pwm_sipm: QtWidgets.QLineEdit
    lineEdit_pwm_pips: QtWidgets.QLineEdit
    lineEdit_pwm_ch: QtWidgets.QLineEdit

    lineEdit_pwm_max_sipm: QtWidgets.QLineEdit
    lineEdit_pwm_max_pips: QtWidgets.QLineEdit
    lineEdit_pwm_max_ch: QtWidgets.QLineEdit

    lineEdit_lvl_0_1: QtWidgets.QLineEdit
    lineEdit_lvl_0_5: QtWidgets.QLineEdit
    lineEdit_lvl_0_8: QtWidgets.QLineEdit
    lineEdit_lvl_1_6: QtWidgets.QLineEdit
    lineEdit_lvl_3: QtWidgets.QLineEdit
    lineEdit_lvl_5: QtWidgets.QLineEdit

    lineEdit_lvl_10: QtWidgets.QLineEdit
    lineEdit_lvl_30: QtWidgets.QLineEdit
    lineEdit_lvl_60: QtWidgets.QLineEdit

    label_check_cfg: QtWidgets.QLabel

    pushButton_save_hvip: QtWidgets.QPushButton
    pushButton_save_mpp: QtWidgets.QPushButton
    lineEdit_cfg_mpp_id: QtWidgets.QLineEdit
    vLayout_ser_connect: QtWidgets.QVBoxLayout

    radioButton_mpp: QtWidgets.QRadioButton
    radioButton_cm: QtWidgets.QRadioButton

    pushButton_Get_Rst: QtWidgets.QPushButton

    cmd_interface_init_signal = QtCore.pyqtSignal()

    def __init__(self, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).resolve().parent.joinpath("DialogConfig.ui"), self)
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
            self.logger = args[0]
            self.w_ser_dialog: SerialConnect = args[1]
            self.task_manager = AsyncTaskManager(self.logger)
            w_ser_dialog.checkBox_mpp_only.setHidden(True)
        else:
            self.logger = self.parent.logger  # type: ignore
            self.w_ser_dialog: SerialConnect = self.parent.w_ser_dialog  # type: ignore

        self.w_ser_dialog.coroutine_finished.connect(self.cmd_interface_init)
        self.pushButton_save_mpp.clicked.connect(self.pushButton_save_cfg_handler)
        self.pushButton_Get_Rst.clicked.connect(self.pushButton_get_rst_handler)
        self.le_obj, self.le_obj_pwm_max = self.init_linEdit_list()
        self.update_pack_from_widget()

    def update_pack_from_widget(self):
        self.pack: list[LineEObj] = [
            LineEObj(key=key, lineobj_txt=value.text(), tp=("f" if 8 < i < 15 else "i"))
            for i, (key, value) in enumerate(self.le_obj.items())
        ]
        self.pack_pwm_max: list[LineEObj] = [
            LineEObj(key=key, lineobj_txt=value.text(), tp="f")
            for i, (key, value) in enumerate(self.le_obj_pwm_max.items())
        ]

    def init_linEdit_list(self) -> tuple[dict[str, QLineEdit], dict[str, QLineEdit]]:
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
            "lineEdit_interval": self.lineEdit_interval,
        }

        le_obj_pwm_max: dict[str, QtWidgets.QLineEdit] = {
            "lineEdit_pwm_max_ch": self.lineEdit_pwm_max_ch,
            "lineEdit_pwm_max_pips": self.lineEdit_pwm_max_pips,
            "lineEdit_pwm_max_sipm": self.lineEdit_pwm_max_sipm,
        }
        return le_obj, le_obj_pwm_max


    @qasync.asyncSlot()
    async def cmd_interface_init(self) -> None:
        """Перехватывает client от SerialConnect и переподключается к нему"""
        if await self.w_ser_dialog.check_connection():
            self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)
            self.cmd_interface_init_signal.emit()
        # Обновление radioButton
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

    @qasync.asyncSlot()
    async def update_gui_data_mpp(self) -> None:
        if not self.w_ser_dialog.check_connection():
            return
        try:
            answer: bytes = await self.mpp_cmd.get_hh()
            tel_dict: dict[str, str] = await self.parser.pars_mpp_hh(answer)

            answ_lvl: bytes = await self.mpp_cmd.get_level()
            tel_dict_lvl: dict[str, str] = await self.parser.pars_mpp_lvl(answ_lvl)

            self.lineEdit_lvl_0_1.setText(str(tel_dict_lvl["01_hh_l"]))

            for i, (key, val) in enumerate(self.le_obj.items()):
                if 0 < i < 9:
                    val.setText(list(tel_dict.values())[i - 1])

        except Exception as e:
            self.logger.error(str(e))

    @qasync.asyncSlot()
    async def update_gui_data_cm(self) -> None:
        if not self.w_ser_dialog.check_connection():
            return
        try:
            answer: bytes = await self.cm_cmd.get_cfg_ddii()
            tel_dict: dict = await self.parser.pars_everything(
                self.pack + self.pack_pwm_max, answer[3:], "little"
            )  # отбрасываем 0x0FF1
            total_struct = self.le_obj | self.le_obj_pwm_max
            for i, (key, val) in enumerate(total_struct.items()):
                val.setText(list(tel_dict.values())[i])
        except Exception as e:
            self.logger.error(str(e))

    @qasync.asyncSlot()
    async def pushButton_save_cfg_handler(self) -> None:
        if not await self.w_ser_dialog.check_connection():
            return
        head: list[int] = [int(self.HEAD.to_bytes(2, "little").hex(), 16)]
        # await self.cm_cmd.set_mode(self.SILENT_MODE)
        # await asyncio.sleep(0.5)
        if self.radioButton_cm.isChecked():
            try:
                data: list[int] = await self.get_cfg_data_from_widget("cm")
                await self.cm_cmd.set_cfg_ddii(head + data)
                self.config.save_to_config()
                self.logger.debug("config_dialog.yaml update")
                self.label_check_cfg.setText("Status: CM config is written")
            except Exception as e:
                self.logger.debug(e)
        if self.radioButton_mpp.isChecked():
            try:
                data: list[int] = await self.get_cfg_data_from_widget("mpp")
                await self.mpp_cmd.set_level(data[0])
                await self.mpp_cmd.set_hh(data[1:9])
                await asyncio.sleep(0.3)
                if await self.check_wrote_cfg(data[0:9], "mpp"):
                    self.label_check_cfg.setText("Status: MPP config is written correct")
                    self.config.save_to_config()
                    self.logger.debug("config_dialog.yaml update")
                else:
                    self.label_check_cfg.setText("Status: MPP config is written incorrect")
            except Exception as e:
                self.logger.debug(e)
        # await asyncio.sleep(0.5)
        # await self.cm_cmd.set_mode(self.COMBAT_MODE)

    @qasync.asyncSlot()
    async def check_wrote_cfg(self, data: list[int], device: str) -> bool:
        if not await self.w_ser_dialog.check_connection():
            return False
        """Поверяет записалась ли в память конфигурация
        Args:
            data (list[int]): отправленные данные конфигурации
            device (str):
            - "cm"
            - "mpp"
        Returns:
            bool: Статус проверки
        """
        # await self.cm_cmd.set_mode(self.SILENT_MODE)
        # await asyncio.sleep(0.5)
        try:
            if device == "mpp":
                check_lvl: bytes = await self.mpp_cmd.get_level()
                check_hh: bytes = await self.mpp_cmd.get_hh()
                d_check_lvl: dict[str, str] = await self.parser.pars_mpp_lvl(check_lvl)
                d_check_hh: dict[str, str] = await self.parser.pars_mpp_hh(check_hh)
                if (
                    list(map(int, d_check_hh.values())) == data[1:9]
                    and list(map(int, d_check_lvl.values())) == data[:1]
                ):
                    return True
                else:
                    return False
        except Exception as e:
            self.logger.error(str(e))

        try:
            if device == "cm":  # для цм не работает из-за точности float
                check_cfg_ddii: bytes = await self.cm_cmd.get_cfg_ddii()
                d_cheack_cfg_ddii: list[int] = [
                    int.from_bytes(check_cfg_ddii[i * 2 : i * 2 + 2], "little") for i in range(2, 24)
                ]
                if d_cheack_cfg_ddii == data[1:]:
                    return True
                else:
                    return False
        except Exception as e:
            self.logger.error(str(e))
        # await asyncio.sleep(0.5)
        # await self.cm_cmd.set_mode(self.COMBAT_MODE)
        return False

    @qasync.asyncSlot()
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

    @qasync.asyncSlot()
    async def get_cfg_data_from_widget(self, device: str) -> list[int]:
        """Получает данные с виджетов и упаковывает их в пакет
        Args:
            device (str): Указать модуль:
            - "cm"
            - "mpp"
        Returns:
            list[int]: Пакет для отправки по ВШ
        """
        self.update_pack_from_widget()
        pack = self.pack + self.pack_pwm_max
        get_data_widget = LineEditPack()
        if device == "mpp":
            return get_data_widget(pack, "big")
        if device == "cm":
            return get_data_widget(pack, "little")
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
        self.lineEdit_pwm_sipm.setValidator(d_validator)
        self.lineEdit_hvip_sipm.setValidator(d_validator)
        self.lineEdit_pwm_ch.setValidator(d_validator)
        self.lineEdit_hvip_ch.setValidator(d_validator)
        self.lineEdit_interval.setValidator(d_validator)


    def closeEvent(self, event) -> None:
        try:
            if __name__ == "__main__":
                self.w_ser_dialog.disconnect_serial_client()
        except Exception:
            pass


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    # light(app)
    logger = log_init()
    w_ser_dialog: SerialConnect = SerialConnect(logger)
    w: MainConfigDialog = MainConfigDialog(logger, w_ser_dialog)
    w.vLayout_ser_connect.addWidget(w_ser_dialog)

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
