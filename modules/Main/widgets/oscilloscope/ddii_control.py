import asyncio
import sys
from pathlib import Path

import qasync
import qtmodern.styles
from pymodbus.client import AsyncModbusSerialClient
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QDoubleValidator, QFont, QIntValidator
from PyQt6.QtWidgets import QGroupBox, QLineEdit, QSizePolicy, QSpacerItem, QVBoxLayout
from qtpy.uic import loadUi

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parents[4]
modules_path = Path(__file__).resolve().parents[3]
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from modules.Main_Serial.main_serial_dialog_tcp import SerialConnect  # noqa: E402
from src.async_task_manager import AsyncTaskManager  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.env_var import EnvironmentVar  # noqa: E402
from src.log_config import log_init  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
from src.parsers import Parsers  # noqa: E402
from src.parsers_pack import LineEditPack, LineEObj  # noqa: E402


class DDIIControlWidget(QtWidgets.QWidget):
    lineEdit_hvip_pips: QtWidgets.QLineEdit
    lineEdit_hvip_sipm: QtWidgets.QLineEdit
    lineEdit_hvip_ch: QtWidgets.QLineEdit

    comboBox_filter: QtWidgets.QComboBox

    lineEdit_pwm_sipm: QtWidgets.QLineEdit
    lineEdit_pwm_pips: QtWidgets.QLineEdit
    lineEdit_pwm_ch: QtWidgets.QLineEdit

    lineEdit_lvl_0_1: QtWidgets.QLineEdit
    lineEdit_lvl_0_5: QtWidgets.QLineEdit
    lineEdit_lvl_0_8: QtWidgets.QLineEdit
    lineEdit_lvl_1_6: QtWidgets.QLineEdit
    lineEdit_lvl_3: QtWidgets.QLineEdit
    lineEdit_lvl_5: QtWidgets.QLineEdit
    lineEdit_lvl_10: QtWidgets.QLineEdit
    lineEdit_lvl_30: QtWidgets.QLineEdit
    lineEdit_lvl_60: QtWidgets.QLineEdit

    pushButton_lvl_update: QtWidgets.QPushButton
    pushButton_lvl_apply: QtWidgets.QPushButton

    # Power tab widgets
    lineEdit_hvip_m_ch: QtWidgets.QLineEdit
    lineEdit_hvip_m_pips: QtWidgets.QLineEdit
    lineEdit_hvip_m_sipm: QtWidgets.QLineEdit
    # Note: UI name for CH pwm is lineEdit_pwm_sipm_2
    lineEdit_pwm_sipm_2: QtWidgets.QLineEdit
    pushButton_hvip_update: QtWidgets.QPushButton
    pushButton_hvip_apply: QtWidgets.QPushButton

    # Time tab widgets
    lineEdit_interval_request: QtWidgets.QLineEdit
    pushButton_apply: QtWidgets.QPushButton  # Обновить (time tab)
    pushButton_update: QtWidgets.QPushButton  # Применить (time tab)

    def __init__(self, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).parent / "ddii_control.ui", self)
        # Core helpers
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.logger = log_init()

        # Optional context from args: either SerialConnect or parent providing it
        self.w_ser_dialog: SerialConnect | None = None
        if len(args) >= 1:
            # If passed a SerialConnect directly
            if isinstance(args[0], SerialConnect):
                self.w_ser_dialog = args[0]
            else:
                # If parent object provided with attributes
                parent = args[0]
                try:
                    self.w_ser_dialog = parent.w_ser_dialog  # type: ignore[attr-defined]
                    self.logger = getattr(parent, "logger", self.logger)
                except Exception:
                    ...

        # Validators for level fields (integers)
        self._init_validators()

        # Wire command interfaces when serial connects (if available)
        if self.w_ser_dialog is not None:
            try:
                self.w_ser_dialog.coroutine_finished.connect(self.init_mb_cmd)  # type: ignore[arg-type]
            except Exception:
                ...

        # Button handlers (Levels tab)
        try:
            self.pushButton_lvl_update.clicked.connect(self.pushButton_levels_update_handler)
            self.pushButton_lvl_apply.clicked.connect(self.pushButton_levels_apply_handler)
        except Exception:
            ...

        # Button handlers (Power tab)
        try:
            self.pushButton_hvip_update.clicked.connect(self.pushButton_power_update_handler)
            self.pushButton_hvip_apply.clicked.connect(self.pushButton_power_apply_handler)
        except Exception:
            ...

        # Button handlers (Time tab: only update requested)
        try:
            self.pushButton_update.clicked.connect(self.pushButton_common_update_handler)
            self.pushButton_apply.clicked.connect(self.pushButton_common_apply_handler)
        except Exception:
            ...

        # Command handles (late-initialized)
        self.cm_cmd: ModbusCMCommand
        self.mpp_cmd: ModbusMPPCommand

        self.filter_combobox_init()

    def _init_validators(self) -> None:
        i_validator = QIntValidator()
        d_validator = QDoubleValidator()
        try:
            self.lineEdit_lvl_0_1.setValidator(i_validator)
            self.lineEdit_lvl_0_5.setValidator(i_validator)
            self.lineEdit_lvl_0_8.setValidator(i_validator)
            self.lineEdit_lvl_1_6.setValidator(i_validator)
            self.lineEdit_lvl_3.setValidator(i_validator)
            self.lineEdit_lvl_5.setValidator(i_validator)
            self.lineEdit_lvl_10.setValidator(i_validator)
            self.lineEdit_lvl_30.setValidator(i_validator)
            self.lineEdit_lvl_60.setValidator(i_validator)
        except Exception:
            # Some fields may be absent if UI changes
            ...
        # Power tab validators (floats)
        try:
            self.lineEdit_hvip_ch.setValidator(d_validator)
            self.lineEdit_hvip_pips.setValidator(d_validator)
            self.lineEdit_hvip_sipm.setValidator(d_validator)
            self.lineEdit_pwm_sipm_2.setValidator(d_validator)
            self.lineEdit_pwm_pips.setValidator(d_validator)
            self.lineEdit_pwm_sipm.setValidator(d_validator)
        except Exception:
            ...

    def filter_combobox_init(self) -> None:
        filters: list = ["нет", "медианный", "ФНЧ", "ФВЧ"]
        self.comboBox_filter.addItems(filters)

    @qasync.asyncSlot()
    async def init_mb_cmd(self) -> None:
        if self.w_ser_dialog is None:
            return
        try:
            # Проверяем доступность именно МПП
            ready = await self.w_ser_dialog.check_connection(only_cm=False, only_mpp=True)
        except Exception:
            ready = False
        self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)
        if not ready:
            self.logger.debug("ЦМ/МПП недоступны для инициализации команд")
            return
        # Если МПП доступен — сразу обновляем поля уровней
        try:
            await self.pushButton_levels_update_handler()
        except Exception:
            ...
        # Если доступен ЦМ — обновляем питание и время
        try:
            if await self.w_ser_dialog.check_connection(only_cm=True, only_mpp=False):
                await self.pushButton_power_update_handler()
                await self.pushButton_common_update_handler()
        except Exception:
            ...

    def _get_int(self, le: QLineEdit) -> int:
        try:
            return int(le.text())
        except Exception:
            return 0

    @qasync.asyncSlot()
    async def pushButton_levels_update_handler(self) -> None:
        """Обновить уровни с МПП и отобразить в UI."""
        try:
            if self.mpp_cmd is None:
                self.logger.error("Интерфейс команд МПП не инициализирован")
                return
            # Read level and HH thresholds
            answ_lvl: bytes = await self.mpp_cmd.get_level()
            tel_dict_lvl: dict[str, str] = await self.parser.pars_mpp_lvl(answ_lvl)
            answer_hh: bytes = await self.mpp_cmd.get_hh()
            tel_dict_hh: dict[str, str] = await self.parser.pars_mpp_hh(answer_hh)

            # Map values into UI fields
            try:
                self.lineEdit_lvl_0_1.setText(str(tel_dict_lvl.get("01_hh_l", "0")))
            except Exception:
                ...
            mapping = [
                ("05_hh_l", self.lineEdit_lvl_0_5),
                ("08_hh_l", self.lineEdit_lvl_0_8),
                ("1_6_hh_l", self.lineEdit_lvl_1_6),
                ("3_hh_l", self.lineEdit_lvl_3),
                ("5_hh_l", self.lineEdit_lvl_5),
                ("10_hh_l", self.lineEdit_lvl_10),
                ("30_hh_l", self.lineEdit_lvl_30),
                ("60_hh_l", self.lineEdit_lvl_60),
            ]
            for key, widget in mapping:
                try:
                    widget.setText(str(tel_dict_hh.get(key, "0")))
                except Exception:
                    ...
        except Exception as e:
            self.logger.error(f"Ошибка обновления уровней: {e}")

    @qasync.asyncSlot()
    async def pushButton_levels_apply_handler(self) -> None:
        """Отправить уровни из UI в МПП."""
        try:
            if self.mpp_cmd is None:
                self.logger.error("Интерфейс команд МПП не инициализирован")
                return
            # Build payloads: level (0.1) is separate, the rest are HH thresholds
            lvl_01 = self._get_int(self.lineEdit_lvl_0_1)
            hh_values: list[int] = [
                self._get_int(self.lineEdit_lvl_0_5),
                self._get_int(self.lineEdit_lvl_0_8),
                self._get_int(self.lineEdit_lvl_1_6),
                self._get_int(self.lineEdit_lvl_3),
                self._get_int(self.lineEdit_lvl_5),
                self._get_int(self.lineEdit_lvl_10),
                self._get_int(self.lineEdit_lvl_30),
                self._get_int(self.lineEdit_lvl_60),
            ]
            await self.mpp_cmd.set_level(lvl_01)
            await self.mpp_cmd.set_hh(hh_values)
        except Exception as e:
            self.logger.error(f"Ошибка отправки уровней: {e}")

    @qasync.asyncSlot()
    async def pushButton_power_update_handler(self) -> None:
        """Обновить значения на вкладке Питание с ЦМ.
        - Uизм (measured) из get_voltage()
        - U, pwm (config) из get_cfg_voltage()/get_cfg_pwm()
        """
        try:
            # Measured voltages
            answer_meas: bytes = await self.cm_cmd.get_voltage()  # type: ignore[union-attr]
            data_meas: dict[str, str] = await self.parser.pars_voltage(answer_meas)
            try:
                self.lineEdit_hvip_m_ch.setText("{:.2f}".format(float(data_meas.get("label_ch_v_mes", "0"))))
                self.lineEdit_hvip_m_pips.setText("{:.2f}".format(float(data_meas.get("label_pips_v_mes", "0"))))
                self.lineEdit_hvip_m_sipm.setText("{:.2f}".format(float(data_meas.get("label_sipm_v_mes", "0"))))
            except Exception:
                ...
            # Config voltages
            answ_cfg_volt: bytes = await self.cm_cmd.get_cfg_voltage()  # type: ignore[union-attr]
            data_cfg_volt: dict[str, str] = await self.parser.pars_cfg_volt(answ_cfg_volt)
            try:
                self.lineEdit_hvip_ch.setText("{:.2f}".format(float(data_cfg_volt.get("spinBox_ch_volt", "0"))))
                self.lineEdit_hvip_pips.setText("{:.2f}".format(float(data_cfg_volt.get("spinBox_pips_volt", "0"))))
                self.lineEdit_hvip_sipm.setText("{:.2f}".format(float(data_cfg_volt.get("spinBox_sipm_volt", "0"))))
            except Exception:
                ...
            # Config PWM
            answ_cfg_pwm: bytes = await self.cm_cmd.get_cfg_pwm()  # type: ignore[union-attr]
            data_cfg_pwm: dict[str, str] = await self.parser.pars_cfg_pwm(answ_cfg_pwm)
            try:
                self.lineEdit_pwm_sipm_2.setText("{:.2f}".format(float(data_cfg_pwm.get("doubleSpinBox_ch_pwm", "0"))))
                self.lineEdit_pwm_pips.setText("{:.2f}".format(float(data_cfg_pwm.get("doubleSpinBox_pips_pwm", "0"))))
                self.lineEdit_pwm_sipm.setText("{:.2f}".format(float(data_cfg_pwm.get("doubleSpinBox_sipm_pwm", "0"))))
            except Exception:
                ...
        except Exception as e:
            self.logger.error(f"Ошибка обновления питания: {e}")

    @qasync.asyncSlot()
    async def pushButton_power_apply_handler(self) -> None:
        """Отправить значения U и PWM с вкладки Питание в ЦМ."""
        try:
            # Build float payloads in little-endian using LineEditPack
            pack_vlt = [
                LineEObj("vlt_ch", self.lineEdit_hvip_ch.text(), "f"),
                LineEObj("vlt_pips", self.lineEdit_hvip_pips.text(), "f"),
                LineEObj("vlt_sipm", self.lineEdit_hvip_sipm.text(), "f"),
            ]
            pack_pwm = [
                LineEObj("pwm_ch", self.lineEdit_pwm_sipm_2.text(), "f"),
                LineEObj("pwm_pips", self.lineEdit_pwm_pips.text(), "f"),
                LineEObj("pwm_sipm", self.lineEdit_pwm_sipm.text(), "f"),
            ]
            get_data_widget = LineEditPack()
            vlt_data: list[int] = get_data_widget(pack_vlt, "little")
            pwm_data: list[int] = get_data_widget(pack_pwm, "little")
            await self.cm_cmd.set_voltage_pwm(vlt_data + pwm_data)  # type: ignore[union-attr]
        except Exception as e:
            self.logger.error(f"Ошибка отправки питания: {e}")

    @qasync.asyncSlot()
    async def pushButton_common_update_handler(self) -> None:
        """Обновить поле интервала из конфигурации ЦМ."""
        try:
            cfg: bytes = await self.cm_cmd.get_cfg_ddii()  # type: ignore[union-attr]
            d_cfg: dict[str, str] = await self.parser.pars_cfg_ddii(cfg)
            try:
                self.lineEdit_interval_request.setText(d_cfg.get("interval_measure", "0"))
            except Exception:
                ...
        except Exception as e:
            self.logger.error(f"Ошибка обновления интервала: {e}")

    @qasync.asyncSlot()
    async def pushButton_common_apply_handler(self) -> None:
        """Отправить интервал из UI в конфигурацию ЦМ."""
        try:
            # interval: int = self._get_int(self.lineEdit_interval_request)
            filter_name: str = self.comboBox_filter.currentText()
            # await self.cm_cmd.set_cfg_ddii_interval(interval)  # type: ignore[union-attr]
            if filter_name == "нет":
                await self.mpp_cmd.reset_filter()  # type: ignore[union-attr]
            elif filter_name == "медианный":
                await self.mpp_cmd.set_median_filter()  # type: ignore[union-attr]
            elif filter_name == "ФНЧ": 
                await self.mpp_cmd.set_bypass_lp_filter()  # type: ignore[union-attr]
            elif filter_name == "ФВЧ":
                await self.mpp_cmd.set_bypass_hp_filter() # type: ignore[union-attr]
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    # light(app)
    logger = log_init()
    w_ser_dialog: SerialConnect = SerialConnect(logger)
    w: DDIIControlWidget = DDIIControlWidget(w_ser_dialog)
    vLayout_ser_connect: QVBoxLayout = QVBoxLayout()
    w.setLayout(vLayout_ser_connect)
    vLayout_ser_connect.addWidget(w_ser_dialog)

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
