from __future__ import annotations

from pathlib import Path
from typing import Optional

import qasync
from PyQt6.QtGui import QDoubleValidator
from PyQt6 import QtWidgets
from qtpy.uic import loadUi

from app.src.components.modbus.ddii_command import ModbusCMCommand
from app.src.components.parsers.custom_parsers import Parsers
from app.src.components.parsers.parsers_pack import LineEObj, LineEditPack
from app.src.components.log.config import log_init

# set_voltage_pwm expects CH, PIPS, SiPM order; UI rows are PIPS[0], SiPM[1], CH[2]
_SEND_ORDER = [2, 0, 1]


class CmSettingsWidget(QtWidgets.QWidget):
    lineEdit_u_meas_pips: QtWidgets.QLineEdit
    lineEdit_u_meas_sipm: QtWidgets.QLineEdit
    lineEdit_u_meas_ch: QtWidgets.QLineEdit
    lineEdit_u_target_pips: QtWidgets.QLineEdit
    lineEdit_u_target_sipm: QtWidgets.QLineEdit
    lineEdit_u_target_ch: QtWidgets.QLineEdit
    lineEdit_pwm_pips: QtWidgets.QLineEdit
    lineEdit_pwm_sipm: QtWidgets.QLineEdit
    lineEdit_pwm_ch: QtWidgets.QLineEdit
    lineEdit_interval: QtWidgets.QLineEdit
    pushButton_update: QtWidgets.QPushButton
    pushButton_apply: QtWidgets.QPushButton

    def __init__(self, mw=None) -> None:
        super().__init__(mw)
        self._mw = mw
        self.cm_cmd: Optional[ModbusCMCommand] = None
        self.parser = Parsers()
        self.logger = getattr(mw, "logger", None) or log_init()

        loadUi(Path(__file__).parent / "cm_settings_widget.ui", self)

        dv = QDoubleValidator(0.0, 9999.99, 2, self)
        for le in (
            self.lineEdit_u_target_pips, self.lineEdit_u_target_sipm, self.lineEdit_u_target_ch,
            self.lineEdit_pwm_pips, self.lineEdit_pwm_sipm, self.lineEdit_pwm_ch,
        ):
            le.setValidator(dv)

        self.pushButton_update.clicked.connect(self._on_update)
        self.pushButton_apply.clicked.connect(self._on_apply)

        if mw is not None:
            try:
                mw.w_ser_dialog.coroutine_finished.connect(self.init_mb_cmd)
            except Exception:
                pass

    @qasync.asyncSlot()
    async def init_mb_cmd(self) -> None:
        if self._mw is None:
            return
        try:
            self.cm_cmd, _ = self._mw.w_ser_dialog.get_commands_interface(self.logger)
        except Exception as ex:
            self.logger.error(str(ex))
            return
        await self._on_update()

    @qasync.asyncSlot()
    async def _on_update(self) -> None:
        if self.cm_cmd is None:
            return
        try:
            meas = await self.cm_cmd.get_voltage()
            if meas != b"-1":
                d = await self.parser.pars_voltage(meas)
                self.lineEdit_u_meas_pips.setText(d.get("label_pips_v_mes", "0"))
                self.lineEdit_u_meas_sipm.setText(d.get("label_sipm_v_mes", "0"))
                self.lineEdit_u_meas_ch.setText(d.get("label_ch_v_mes", "0"))

            cfg_v = await self.cm_cmd.get_cfg_voltage()
            if cfg_v != b"-1":
                d = await self.parser.pars_cfg_volt(cfg_v)
                self.lineEdit_u_target_pips.setText(d.get("spinBox_pips_volt", "0.00"))
                self.lineEdit_u_target_sipm.setText(d.get("spinBox_sipm_volt", "0.00"))
                self.lineEdit_u_target_ch.setText(d.get("spinBox_ch_volt", "0.00"))

            cfg_p = await self.cm_cmd.get_cfg_pwm()
            if cfg_p != b"-1":
                d = await self.parser.pars_cfg_pwm(cfg_p)
                self.lineEdit_pwm_pips.setText(d.get("doubleSpinBox_pips_pwm", "0.00"))
                self.lineEdit_pwm_sipm.setText(d.get("doubleSpinBox_sipm_pwm", "0.00"))
                self.lineEdit_pwm_ch.setText(d.get("doubleSpinBox_ch_pwm", "0.00"))

            cfg_d = await self.cm_cmd.get_cfg_ddii()
            if cfg_d != b"-1":
                d = await self.parser.pars_cfg_ddii(cfg_d)
                self.lineEdit_interval.setText(d.get("interval_measure", "10"))
        except Exception as ex:
            self.logger.error(str(ex))

    @qasync.asyncSlot()
    async def _on_apply(self) -> None:
        if self.cm_cmd is None:
            return
        try:
            u_fields = [self.lineEdit_u_target_pips, self.lineEdit_u_target_sipm, self.lineEdit_u_target_ch]
            p_fields = [self.lineEdit_pwm_pips, self.lineEdit_pwm_sipm, self.lineEdit_pwm_ch]
            packer = LineEditPack()
            pack_vlt = [LineEObj(f"v{i}", u_fields[idx].text(), "f") for i, idx in enumerate(_SEND_ORDER)]
            pack_pwm = [LineEObj(f"p{i}", p_fields[idx].text(), "f") for i, idx in enumerate(_SEND_ORDER)]
            await self.cm_cmd.set_voltage_pwm(packer(pack_vlt, "little") + packer(pack_pwm, "little"))
        except Exception as ex:
            self.logger.error(str(ex))
