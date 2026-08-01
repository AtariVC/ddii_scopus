from __future__ import annotations

from pathlib import Path
from typing import Optional

import qasync
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QIntValidator
from qtpy.uic import loadUi

from app.src.components.modbus.ddii_command import ModbusMPPCommand
from app.src.components.parsers.custom_parsers import Parsers
from app.src.components.log.config import log_init

# mppa.h: CMD_FILTER_BYPASS = 10, Params[0] = {median_en[2], bypass_lp[1], bypass_hp[1]}
_FILTER_MASKS: dict[str, int] = {
    "нет":       0b011,
    "медианный": 0b100,
    "ФНЧ":       0b001,
    "ФВЧ":       0b010,
}
_CMD_FILTER_BYPASS = 10


class MppSettingsWidget(QtWidgets.QWidget):
    lineEdit_level: QtWidgets.QLineEdit
    comboBox_filter: QtWidgets.QComboBox
    widget_hh_container: QtWidgets.QWidget
    pushButton_update: QtWidgets.QPushButton
    pushButton_apply: QtWidgets.QPushButton

    def __init__(self, mw=None) -> None:
        super().__init__(mw)
        self._mw = mw
        self.mpp_cmd: Optional[ModbusMPPCommand] = None
        self.parser = Parsers()
        self.logger = getattr(mw, "logger", None) or log_init()
        self._hh_edits: list[QtWidgets.QLineEdit] = []

        loadUi(Path(__file__).parent / "mpp_settings_widget.ui", self)

        self._build_hh_grid()
        self.lineEdit_level.setValidator(QIntValidator(0, 65535, self))
        self.comboBox_filter.addItems(list(_FILTER_MASKS.keys()))
        self.pushButton_update.clicked.connect(self._on_update)
        self.pushButton_apply.clicked.connect(self._on_apply)

        if mw is not None:
            try:
                mw.w_ser_dialog.coroutine_finished.connect(self.init_mb_cmd)
            except Exception:
                pass

    def _build_hh_grid(self) -> None:
        grid = QtWidgets.QGridLayout(self.widget_hh_container)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(5)
        iv = QIntValidator(0, 65535, self)
        COLS = 4
        for i in range(32):
            r, c = divmod(i, COLS)
            lbl = QtWidgets.QLabel(f"HH{i + 1:02d}")
            lbl.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
            le = QtWidgets.QLineEdit("0")
            le.setValidator(iv)
            le.setFixedWidth(68)
            le.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self._hh_edits.append(le)
            grid.addWidget(lbl, r, c * 2)
            grid.addWidget(le, r, c * 2 + 1)

    @qasync.asyncSlot()
    async def init_mb_cmd(self) -> None:
        if self._mw is None:
            return
        try:
            _, self.mpp_cmd = self._mw.w_ser_dialog.get_commands_interface(self.logger)
        except Exception as ex:
            self.logger.error(str(ex))
            return
        await self._on_update()

    @qasync.asyncSlot()
    async def _on_update(self) -> None:
        if self.mpp_cmd is None:
            return
        try:
            level_data = await self.mpp_cmd.get_level()
            if level_data != b"-1":
                d = await self.parser.pars_mpp_lvl(level_data)
                self.lineEdit_level.setText(d.get("01_hh_l", "0"))

            hh_data = await self.mpp_cmd.get_hh()
            if hh_data != b"-1":
                values = self.parser._u16_values(hh_data)
                for i, le in enumerate(self._hh_edits):
                    le.setText(str(values[i]) if i < len(values) else "0")
        except Exception as ex:
            self.logger.error(str(ex))

    @qasync.asyncSlot()
    async def _on_apply(self) -> None:
        if self.mpp_cmd is None:
            return
        try:
            level = self._int(self.lineEdit_level)
            hh_values = [self._int(le) for le in self._hh_edits]
            await self.mpp_cmd.set_level(level)
            await self.mpp_cmd.set_hh(hh_values)
            mask = _FILTER_MASKS.get(self.comboBox_filter.currentText(), 0)
            await self.mpp_cmd.write_mpp_ctrl([_CMD_FILTER_BYPASS, mask])
        except Exception as ex:
            self.logger.error(str(ex))

    def _int(self, le: QtWidgets.QLineEdit, default: int = 0) -> int:
        try:
            return int(le.text())
        except Exception:
            return default
