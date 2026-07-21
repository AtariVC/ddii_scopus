import asyncio
import sys
from pathlib import Path

import qasync
import qtmodern.styles
from pymodbus.client import AsyncModbusSerialClient
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QDoubleValidator, QFont, QIntValidator
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from qtpy.uic import loadUi


from app.plugins.connection.connection_bar import ConnectionBar
from app.src.util.async_task_manager import AsyncTaskManager
from app.src.components.modbus.ddii_command import ModbusCMCommand, ModbusMPPCommand
from app.src.components.modbus.modbus_var import ModbusReg
from app.src.components.log.config import log_init
from app.src.components.modbus.worker import ModbusWorker
from app.src.components.parsers.custom_parsers import Parsers
from app.src.components.parsers.parsers_pack import LineEditPack, LineEObj


class DDIIControlWidget(QtWidgets.QWidget):
    lineEdit_hvip_pips: QtWidgets.QLineEdit
    lineEdit_hvip_sipm: QtWidgets.QLineEdit
    lineEdit_hvip_ch: QtWidgets.QLineEdit

    comboBox_filter: QtWidgets.QComboBox

    lineEdit_pwm_sipm: QtWidgets.QLineEdit
    lineEdit_pwm_pips: QtWidgets.QLineEdit
    lineEdit_pwm_ch: QtWidgets.QLineEdit
    lineEdit_lvl_0_1: QtWidgets.QLineEdit
    hh_line_edits: list[QtWidgets.QLineEdit]

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
        self.hh_line_edits = []
        self._rebuild_levels_tab()
        # Core helpers
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.logger = log_init()

        # Optional context from args: either ConnectionBar or parent providing it
        self.w_ser_dialog: ConnectionBar | None = None
        if len(args) >= 1:
            # If passed a ConnectionBar directly
            if isinstance(args[0], ConnectionBar):
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
            for line_edit in self.hh_line_edits:
                line_edit.setValidator(i_validator)
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

    def _clear_layout(self, layout: QtWidgets.QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            child_widget = item.widget()
            if child_layout is not None:
                self._clear_layout(child_layout)
            elif child_widget is not None:
                child_widget.setParent(None)

    def _rebuild_levels_tab(self) -> None:
        tab_levels = self.findChild(QtWidgets.QWidget, "tab_3")
        if tab_levels is None:
            self.logger.error("Не найдена вкладка уровней tab_3")
            return
        tab_layout = tab_levels.layout()
        if tab_layout is None:
            return
        self._clear_layout(tab_layout)

        levels_wrap = QWidget(tab_levels)
        levels_layout = QVBoxLayout(levels_wrap)
        levels_layout.setContentsMargins(7, 7, 7, 7)
        levels_layout.setSpacing(7)

        level_layout = QHBoxLayout()
        level_label = QLabel("Level", levels_wrap)
        level_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        level_label.setMinimumSize(QtCore.QSize(100, 25))
        self.lineEdit_lvl_0_1 = QLineEdit(levels_wrap)
        self.lineEdit_lvl_0_1.setMinimumSize(QtCore.QSize(90, 25))
        self.lineEdit_lvl_0_1.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lineEdit_lvl_0_1.setObjectName("lineEdit_lvl_0_1")
        level_layout.addWidget(level_label)
        level_layout.addWidget(self.lineEdit_lvl_0_1)
        level_layout.addStretch(1)
        levels_layout.addLayout(level_layout)

        hh_scroll = QScrollArea(levels_wrap)
        hh_scroll.setObjectName("scrollArea_hh")
        hh_scroll.setWidgetResizable(True)
        hh_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        hh_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        hh_scroll.setMinimumHeight(180)

        hh_container = QWidget()
        hh_layout = QGridLayout(hh_container)
        hh_layout.setContentsMargins(0, 0, 0, 0)
        hh_layout.setHorizontalSpacing(10)
        hh_layout.setVerticalSpacing(10)
        self.hh_line_edits = []
        for idx in range(32):
            row = idx // 4
            col = (idx % 4) * 3
            hh_label = QLabel(f"HH{idx + 1}", hh_container)
            hh_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            hh_label.setMinimumSize(QtCore.QSize(55, 25))
            hh_edit = QLineEdit(hh_container)
            hh_edit.setObjectName(f"lineEdit_hh_{idx + 1}")
            hh_edit.setMinimumSize(QtCore.QSize(80, 25))
            hh_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.hh_line_edits.append(hh_edit)
            hh_layout.addWidget(hh_label, row, col)
            hh_layout.addWidget(hh_edit, row, col + 1)
            if (idx % 4) != 3:
                hh_layout.setColumnMinimumWidth(col + 2, 18)
        hh_scroll.setWidget(hh_container)
        levels_layout.addWidget(hh_scroll, 1)
        levels_layout.addItem(
            QSpacerItem(
                20,
                16,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Fixed,
            )
        )

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 4, 0, 0)
        buttons_layout.addStretch(1)
        self.pushButton_lvl_update = QtWidgets.QPushButton("Обновить", levels_wrap)
        self.pushButton_lvl_update.setObjectName("pushButton_lvl_update")
        self.pushButton_lvl_update.setMinimumSize(QtCore.QSize(120, 25))
        self.pushButton_lvl_apply = QtWidgets.QPushButton("Применить", levels_wrap)
        self.pushButton_lvl_apply.setObjectName("pushButton_lvl_apply")
        self.pushButton_lvl_apply.setMinimumSize(QtCore.QSize(120, 25))
        buttons_layout.addWidget(self.pushButton_lvl_update)
        buttons_layout.addWidget(self.pushButton_lvl_apply)
        levels_layout.addLayout(buttons_layout)

        tab_layout.addWidget(levels_wrap)

    def _parse_u16_registers(self, answer: bytes, count: int) -> list[int]:
        payload = answer
        values: list[int] = []
        for i in range(0, min(len(payload), count * 2), 2):
            chunk = payload[i:i + 2]
            if len(chunk) < 2:
                break
            values.append(int.from_bytes(chunk, byteorder="big", signed=False))
        if len(values) < count:
            values.extend([0] * (count - len(values)))
        return values[:count]

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
            hh_values: list[int] = self._parse_u16_registers(answer_hh, 32)

            # Map values into UI fields
            try:
                self.lineEdit_lvl_0_1.setText(str(tel_dict_lvl.get("01_hh_l", "0")))
            except Exception:
                ...
            for idx, widget in enumerate(self.hh_line_edits):
                try:
                    widget.setText(str(hh_values[idx]))
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
            hh_values: list[int] = [self._get_int(le) for le in self.hh_line_edits]
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
    w_ser_dialog: ConnectionBar = ConnectionBar(logger)
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
