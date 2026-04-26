import asyncio
import sys
from pathlib import Path

import qasync
import qtmodern.styles
from pymodbus.client import AsyncModbusSerialClient
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QDoubleValidator, QFont, QIcon, QIntValidator
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

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parents[4]
modules_path = Path(__file__).resolve().parents[3]
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from Main.widgets.oscilloscope.ddii_control_defaults_loader import DDIIControlDefaults  # noqa: E402
from modules.Main_Serial.main_serial_dialog_tcp import SerialConnect  # noqa: E402
from src.async_task_manager import AsyncTaskManager  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.env_var import EnvironmentVar  # noqa: E402
from src.log_config import log_init  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
from src.parsers import Parsers  # noqa: E402
from src.parsers_pack import LineEditPack, LineEObj  # noqa: E402


class DDIIControlWidget(QtWidgets.QWidget):
    HH_COUNT = 32
    ICON_DIR = Path(__file__).resolve().parents[4] / "icon"
    # HH с коэффициентом ППД: HH1-HH6, ряды от HH7/HH9/HH10 с шагом +4 до HH19, HH30.
    PPD_HH_NUMBERS = frozenset(range(1, 7)) | frozenset(hh for start in (7, 9, 10) for hh in range(start, 20, 4)) | {30}

    lineEdit_hvip_pips: QtWidgets.QLineEdit
    lineEdit_hvip_sipm: QtWidgets.QLineEdit
    lineEdit_hvip_ch: QtWidgets.QLineEdit

    comboBox_filter: QtWidgets.QComboBox

    lineEdit_pwm_sipm: QtWidgets.QLineEdit
    lineEdit_pwm_pips: QtWidgets.QLineEdit
    lineEdit_pwm_ch: QtWidgets.QLineEdit
    lineEdit_lvl_0_1: QtWidgets.QLineEdit
    lineEdit_lvl_ppd_lsb_kev: QtWidgets.QLineEdit
    lineEdit_lvl_scd_lsb_kev: QtWidgets.QLineEdit
    hh_line_edits: list[QtWidgets.QLineEdit]
    hh_lsb_values: list[int]
    lvl_coeff_widgets: list[QtWidgets.QWidget]
    lvl_coeff_line_edits: list[QtWidgets.QLineEdit]
    radioButton_lvl_lsb: QtWidgets.QRadioButton
    radioButton_lvl_kev: QtWidgets.QRadioButton

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
        self.logger = log_init()
        self.defaults = DDIIControlDefaults.load(self.logger)
        self.hh_line_edits = []
        self.hh_lsb_values = self.defaults.hh_default_lsb_values(self.HH_COUNT, self.PPD_HH_NUMBERS)
        self.lvl_coeff_widgets = []
        self._levels_display_kev = self.defaults.levels_in_kev()
        self._rebuild_levels_tab()
        # Core helpers
        self.mw = ModbusWorker()
        self.parser = Parsers()

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
        self._apply_defaults_to_static_fields()
        self._configure_action_buttons()

    def _coerce_int(self, value: object, fallback: int, minimum: int | None = None) -> int:
        try:
            result = int(value)
        except Exception:
            result = fallback
        if minimum is not None:
            result = max(minimum, result)
        return result

    def _coerce_float(self, value: object, fallback: float) -> float:
        try:
            return float(value)
        except Exception:
            return fallback

    def _apply_defaults_to_static_fields(self) -> None:
        self.lineEdit_interval_request.setText(self.defaults.interval_text)
        self.lineEdit_hvip_ch.setText(self.defaults.float_text("voltage", "ch"))
        self.lineEdit_hvip_pips.setText(self.defaults.float_text("voltage", "pips"))
        self.lineEdit_hvip_sipm.setText(self.defaults.float_text("voltage", "sipm"))
        self.lineEdit_pwm_sipm_2.setText(self.defaults.float_text("pwm", "ch"))
        self.lineEdit_pwm_pips.setText(self.defaults.float_text("pwm", "pips"))
        self.lineEdit_pwm_sipm.setText(self.defaults.float_text("pwm", "sipm"))
        self.lineEdit_hvip_m_ch.setText(self.defaults.float_text("measured_voltage", "ch"))
        self.lineEdit_hvip_m_pips.setText(self.defaults.float_text("measured_voltage", "pips"))
        self.lineEdit_hvip_m_sipm.setText(self.defaults.float_text("measured_voltage", "sipm"))

    # Компактные action-кнопки с material-style иконками.
    def _icon(self, icon_name: str) -> QIcon:
        return QIcon(str(self.ICON_DIR / icon_name))

    def _configure_action_button(self, button: QtWidgets.QPushButton, icon_name: str, tooltip: str) -> None:
        button.setText("")
        button.setToolTip(tooltip)
        button.setStatusTip(tooltip)
        button.setIcon(self._icon(icon_name))
        button.setIconSize(QtCore.QSize(18, 18))
        button.setFixedSize(QtCore.QSize(34, 28))

    def _configure_action_buttons(self) -> None:
        self._configure_action_button(self.pushButton_lvl_update, "refresh.svg", "Обновить уровни")
        self._configure_action_button(self.pushButton_lvl_apply, "save.svg", "Применить уровни")
        self._configure_action_button(self.pushButton_hvip_update, "refresh.svg", "Обновить питание")
        self._configure_action_button(self.pushButton_hvip_apply, "save.svg", "Применить питание")
        self._configure_action_button(self.pushButton_update, "refresh.svg", "Обновить настройки")
        self._configure_action_button(self.pushButton_apply, "save.svg", "Применить настройки")

    def _init_validators(self) -> None:
        self._u16_validator = QIntValidator(0, 65535, self)
        self._coeff_validator = QIntValidator(1, 1000000, self)
        self._hh_kev_validator = QIntValidator(0, 1000000, self)
        d_validator = QDoubleValidator()
        try:
            self.lineEdit_lvl_0_1.setValidator(self._u16_validator)
            self.lineEdit_lvl_ppd_lsb_kev.setValidator(self._coeff_validator)
            self.lineEdit_lvl_scd_lsb_kev.setValidator(self._coeff_validator)
            self._set_hh_display_validators()
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
        self.comboBox_filter.clear()
        for filter_item in self.defaults.filter_items():
            self.comboBox_filter.addItem(filter_item["label"], filter_item["id"])
        default_filter_id = self.defaults.default_filter_id
        default_index = self.comboBox_filter.findData(default_filter_id)
        default_index = max(default_index, 0)
        self.comboBox_filter.setCurrentIndex(default_index)

    def _clear_layout(self, layout: QtWidgets.QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            child_widget = item.widget()
            if child_layout is not None:
                self._clear_layout(child_layout)
            elif child_widget is not None:
                child_widget.setParent(None)

    def _make_center_label(self, text: str, parent: QWidget, width: int) -> QLabel:
        label = QLabel(text, parent)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(QtCore.QSize(width, 23))
        return label

    def _make_center_line_edit(
        self,
        parent: QWidget,
        object_name: str,
        width: int,
        text: str = "",
    ) -> QLineEdit:
        line_edit = QLineEdit(parent)
        line_edit.setObjectName(object_name)
        line_edit.setText(text)
        line_edit.setMinimumSize(QtCore.QSize(width, 23))
        line_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        return line_edit

    def _rebuild_levels_tab(self) -> None:
        tab_levels = self.findChild(QtWidgets.QWidget, "tab_3")
        if tab_levels is None:
            logger = getattr(self, "logger", None)
            if logger is not None:
                logger.error("Не найдена вкладка уровней tab_3")
            return
        tab_layout = tab_levels.layout()
        if tab_layout is None:
            return
        self._clear_layout(tab_layout)
        # Обертка вкладки.
        levels_wrap = QWidget(tab_levels)
        levels_layout = QVBoxLayout(levels_wrap)
        levels_layout.setContentsMargins(6, 6, 6, 6)
        levels_layout.setSpacing(6)

        # Управление отображением и коэффициентами.
        controls_layout = QGridLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setHorizontalSpacing(6)
        controls_layout.setVerticalSpacing(4)
        self.lineEdit_lvl_0_1 = self._make_center_line_edit(
            levels_wrap,
            "lineEdit_lvl_0_1",
            78,
            str(self.defaults.level_01),
        )
        self.lineEdit_lvl_ppd_lsb_kev = self._make_center_line_edit(
            levels_wrap,
            "lineEdit_lvl_ppd_lsb_kev",
            70,
            str(self.defaults.coeff_value("ppd")),
        )
        self.lineEdit_lvl_scd_lsb_kev = self._make_center_line_edit(
            levels_wrap,
            "lineEdit_lvl_scd_lsb_kev",
            70,
            str(self.defaults.coeff_value("scd")),
        )
        self.radioButton_lvl_lsb = QtWidgets.QRadioButton("lsb", levels_wrap)
        self.radioButton_lvl_kev = QtWidgets.QRadioButton("keV", levels_wrap)
        self.radioButton_lvl_lsb.setObjectName("radioButton_lvl_lsb")
        self.radioButton_lvl_kev.setObjectName("radioButton_lvl_kev")
        self.radioButton_lvl_lsb.setChecked(not self.defaults.levels_in_kev())
        self.radioButton_lvl_kev.setChecked(self.defaults.levels_in_kev())

        self.levels_unit_group = QtWidgets.QButtonGroup(levels_wrap)
        self.levels_unit_group.addButton(self.radioButton_lvl_lsb)
        self.levels_unit_group.addButton(self.radioButton_lvl_kev)

        ppd_label = self._make_center_label("ППД (lsb/keV)", levels_wrap, 105)
        scd_label = self._make_center_label("СцД (lsb/keV)", levels_wrap, 105)
        self.lvl_coeff_widgets = [
            ppd_label,
            self.lineEdit_lvl_ppd_lsb_kev,
            scd_label,
            self.lineEdit_lvl_scd_lsb_kev,
        ]
        self.lvl_coeff_line_edits = [
            self.lineEdit_lvl_ppd_lsb_kev,
            self.lineEdit_lvl_scd_lsb_kev,
        ]

        controls_layout.addWidget(self._make_center_label("Level", levels_wrap, 55), 0, 0)
        controls_layout.addWidget(self.lineEdit_lvl_0_1, 0, 1)
        controls_layout.addWidget(self.radioButton_lvl_lsb, 0, 2)
        controls_layout.addWidget(self.radioButton_lvl_kev, 0, 3)
        controls_layout.addWidget(ppd_label, 1, 0)
        controls_layout.addWidget(self.lineEdit_lvl_ppd_lsb_kev, 1, 1)
        controls_layout.addWidget(scd_label, 1, 2)
        controls_layout.addWidget(self.lineEdit_lvl_scd_lsb_kev, 1, 3)
        controls_layout.setColumnStretch(4, 1)
        levels_layout.addLayout(controls_layout)

        # Сетка HH.
        hh_scroll = QScrollArea(levels_wrap)
        hh_scroll.setObjectName("scrollArea_hh")
        hh_scroll.setWidgetResizable(True)
        hh_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        hh_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        hh_scroll.setMinimumHeight(180)

        hh_container = QWidget()
        hh_layout = QGridLayout(hh_container)
        hh_layout.setContentsMargins(0, 0, 0, 0)
        hh_layout.setHorizontalSpacing(7)
        hh_layout.setVerticalSpacing(5)
        self.hh_line_edits = []
        for idx in range(self.HH_COUNT):
            row = idx // 4
            col = (idx % 4) * 3
            hh_label = self._make_center_label(f"HH{idx + 1}", hh_container, 45)
            hh_edit = self._make_center_line_edit(hh_container, f"lineEdit_hh_{idx + 1}", 72)
            hh_edit.textEdited.connect(lambda _text, edit=hh_edit: self._mark_hh_dirty(edit))
            self.hh_line_edits.append(hh_edit)
            hh_layout.addWidget(hh_label, row, col)
            hh_layout.addWidget(hh_edit, row, col + 1)
            if (idx % 4) != 3:
                hh_layout.setColumnMinimumWidth(col + 2, 10)
        hh_scroll.setWidget(hh_container)
        levels_layout.addWidget(hh_scroll, 1)
        levels_layout.addItem(
            QSpacerItem(
                20,
                8,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Fixed,
            )
        )

        # Команды МПП.
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 2, 0, 0)
        buttons_layout.addStretch(1)
        self.pushButton_lvl_update = QtWidgets.QPushButton("Обновить", levels_wrap)
        self.pushButton_lvl_update.setObjectName("pushButton_lvl_update")
        self.pushButton_lvl_update.setMinimumSize(QtCore.QSize(34, 28))
        self.pushButton_lvl_apply = QtWidgets.QPushButton("Применить", levels_wrap)
        self.pushButton_lvl_apply.setObjectName("pushButton_lvl_apply")
        self.pushButton_lvl_apply.setMinimumSize(QtCore.QSize(34, 28))
        buttons_layout.addWidget(self.pushButton_lvl_update)
        buttons_layout.addWidget(self.pushButton_lvl_apply)
        levels_layout.addLayout(buttons_layout)

        tab_layout.addWidget(levels_wrap)
        self.radioButton_lvl_lsb.toggled.connect(self._levels_mode_changed)
        self.radioButton_lvl_kev.toggled.connect(self._levels_mode_changed)
        self.lineEdit_lvl_ppd_lsb_kev.editingFinished.connect(self._levels_coeff_changed)
        self.lineEdit_lvl_scd_lsb_kev.editingFinished.connect(self._levels_coeff_changed)
        self._configure_action_button(self.pushButton_lvl_update, "refresh.svg", "Обновить уровни")
        self._configure_action_button(self.pushButton_lvl_apply, "save.svg", "Применить уровни")
        self._set_levels_coeff_visible()
        self._render_hh_values(self.hh_lsb_values)

    def _levels_in_kev(self) -> bool:
        return bool(getattr(self, "radioButton_lvl_kev", None) and self.radioButton_lvl_kev.isChecked())

    def _set_levels_coeff_visible(self) -> None:
        for widget in getattr(self, "lvl_coeff_widgets", []):
            widget.setVisible(True)
        for line_edit in getattr(self, "lvl_coeff_line_edits", []):
            line_edit.setEnabled(self._levels_in_kev())

    def _set_hh_display_validators(self) -> None:
        validator = getattr(
            self,
            "_hh_kev_validator" if self._levels_in_kev() else "_u16_validator",
            None,
        )
        if validator is None:
            return
        for line_edit in self.hh_line_edits:
            line_edit.setValidator(validator)

    def _mark_hh_dirty(self, line_edit: QLineEdit) -> None:
        line_edit.setProperty("dirty", True)

    def _levels_mode_changed(self, checked: bool) -> None:
        if not checked:
            self._set_levels_coeff_visible()
            return
        self._commit_hh_display_to_lsb()
        self._render_hh_values(self.hh_lsb_values)

    def _levels_coeff_changed(self) -> None:
        if self._levels_in_kev():
            self._commit_hh_display_to_lsb()
            self._render_hh_values(self.hh_lsb_values)

    def _hh_coeff(self, hh_number: int) -> int:
        coeff_edit = (
            self.lineEdit_lvl_ppd_lsb_kev if hh_number in self.PPD_HH_NUMBERS else self.lineEdit_lvl_scd_lsb_kev
        )
        return max(1, self._get_int(coeff_edit))

    def _format_hh_value(self, hh_number: int, lsb_value: int) -> str:
        if self._levels_in_kev():
            return str(int(round(lsb_value * self._hh_coeff(hh_number))))
        return str(lsb_value)

    def _hh_edit_to_lsb(self, hh_number: int, line_edit: QLineEdit, display_kev: bool) -> int:
        if display_kev:
            return self._get_int(line_edit) // self._hh_coeff(hh_number)
        return self._get_int(line_edit)

    def _collect_hh_lsb_values(self, display_kev: bool | None = None) -> list[int]:
        display_kev = self._levels_display_kev if display_kev is None else display_kev
        values: list[int] = []
        for idx, line_edit in enumerate(self.hh_line_edits):
            saved_value = line_edit.property("lsb_value")
            if display_kev and not line_edit.property("dirty") and saved_value is not None:
                values.append(int(saved_value))
            else:
                values.append(self._hh_edit_to_lsb(idx + 1, line_edit, display_kev))
        return values

    def _commit_hh_display_to_lsb(self) -> None:
        self.hh_lsb_values = self._collect_hh_lsb_values(self._levels_display_kev)
        for idx, line_edit in enumerate(self.hh_line_edits):
            line_edit.setProperty("lsb_value", self.hh_lsb_values[idx])
            line_edit.setProperty("dirty", False)

    def _render_hh_values(self, values: list[int]) -> None:
        self._set_hh_display_validators()
        self.hh_lsb_values = values[: self.HH_COUNT] + [0] * max(0, self.HH_COUNT - len(values))
        for idx, line_edit in enumerate(self.hh_line_edits):
            lsb_value = self.hh_lsb_values[idx]
            line_edit.blockSignals(True)
            line_edit.setProperty("lsb_value", lsb_value)
            line_edit.setProperty("dirty", False)
            line_edit.setText(self._format_hh_value(idx + 1, lsb_value))
            line_edit.blockSignals(False)
        self._levels_display_kev = self._levels_in_kev()

    def _parse_u16_registers(self, answer: bytes, count: int) -> list[int]:
        payload = answer[1:] if len(answer) > 1 else b""
        values: list[int] = []
        for i in range(0, min(len(payload), count * 2), 2):
            chunk = payload[i : i + 2]
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
                level_value = tel_dict_lvl.get("01_hh_l", self.defaults.level_01)
                self.lineEdit_lvl_0_1.setText(str(level_value))
            except Exception:
                ...
            self._render_hh_values(hh_values)
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
            self._commit_hh_display_to_lsb()
            hh_values: list[int] = self.hh_lsb_values[: self.HH_COUNT]
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
                self.lineEdit_hvip_m_ch.setText(
                    "{:.2f}".format(
                        self._coerce_float(
                            data_meas.get("label_ch_v_mes"),
                            self.defaults.float_value("measured_voltage", "ch"),
                        )
                    )
                )
                self.lineEdit_hvip_m_pips.setText(
                    "{:.2f}".format(
                        self._coerce_float(
                            data_meas.get("label_pips_v_mes"),
                            self.defaults.float_value("measured_voltage", "pips"),
                        )
                    )
                )
                self.lineEdit_hvip_m_sipm.setText(
                    "{:.2f}".format(
                        self._coerce_float(
                            data_meas.get("label_sipm_v_mes"),
                            self.defaults.float_value("measured_voltage", "sipm"),
                        )
                    )
                )
            except Exception:
                ...
            # Config voltages
            answ_cfg_volt: bytes = await self.cm_cmd.get_cfg_voltage()  # type: ignore[union-attr]
            data_cfg_volt: dict[str, str] = await self.parser.pars_cfg_volt(answ_cfg_volt)
            try:
                self.lineEdit_hvip_ch.setText(
                    "{:.2f}".format(
                        self._coerce_float(
                            data_cfg_volt.get("spinBox_ch_volt"),
                            self.defaults.float_value("voltage", "ch"),
                        )
                    )
                )
                self.lineEdit_hvip_pips.setText(
                    "{:.2f}".format(
                        self._coerce_float(
                            data_cfg_volt.get("spinBox_pips_volt"),
                            self.defaults.float_value("voltage", "pips"),
                        )
                    )
                )
                self.lineEdit_hvip_sipm.setText(
                    "{:.2f}".format(
                        self._coerce_float(
                            data_cfg_volt.get("spinBox_sipm_volt"),
                            self.defaults.float_value("voltage", "sipm"),
                        )
                    )
                )
            except Exception:
                ...
            # Config PWM
            answ_cfg_pwm: bytes = await self.cm_cmd.get_cfg_pwm()  # type: ignore[union-attr]
            data_cfg_pwm: dict[str, str] = await self.parser.pars_cfg_pwm(answ_cfg_pwm)
            try:
                self.lineEdit_pwm_sipm_2.setText(
                    "{:.2f}".format(
                        self._coerce_float(
                            data_cfg_pwm.get("doubleSpinBox_ch_pwm"),
                            self.defaults.float_value("pwm", "ch"),
                        )
                    )
                )
                self.lineEdit_pwm_pips.setText(
                    "{:.2f}".format(
                        self._coerce_float(
                            data_cfg_pwm.get("doubleSpinBox_pips_pwm"),
                            self.defaults.float_value("pwm", "pips"),
                        )
                    )
                )
                self.lineEdit_pwm_sipm.setText(
                    "{:.2f}".format(
                        self._coerce_float(
                            data_cfg_pwm.get("doubleSpinBox_sipm_pwm"),
                            self.defaults.float_value("pwm", "sipm"),
                        )
                    )
                )
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
                self.lineEdit_interval_request.setText(
                    str(d_cfg.get("interval_measure", self.defaults.interval_text))
                )
            except Exception:
                ...
        except Exception as e:
            self.logger.error(f"Ошибка обновления интервала: {e}")

    @qasync.asyncSlot()
    async def pushButton_common_apply_handler(self) -> None:
        """Отправить интервал из UI в конфигурацию ЦМ."""
        try:
            # interval: int = self._get_int(self.lineEdit_interval_request)
            filter_id = str(self.comboBox_filter.currentData())
            # await self.cm_cmd.set_cfg_ddii_interval(interval)  # type: ignore[union-attr]
            if filter_id == "none":
                await self.mpp_cmd.reset_filter()  # type: ignore[union-attr]
            elif filter_id == "median":
                await self.mpp_cmd.set_median_filter()  # type: ignore[union-attr]
            elif filter_id == "bypass_lp":
                await self.mpp_cmd.set_bypass_lp_filter()  # type: ignore[union-attr]
            elif filter_id == "bypass_hp":
                await self.mpp_cmd.set_bypass_hp_filter()  # type: ignore[union-attr]
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
