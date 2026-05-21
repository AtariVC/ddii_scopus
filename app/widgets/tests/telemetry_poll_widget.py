import asyncio
from pathlib import Path
from typing import Optional

import qasync
from PyQt6 import QtGui, QtWidgets
from qtpy.uic import loadUi

from app.src.components.modbus.ddii_command import ModbusCMCommand
from app.widgets.tests.frames import parse_ddii_frame, parse_system_frame


class TelemetryPollWidget(QtWidgets.QWidget):
    checkBox_system_frame: QtWidgets.QCheckBox
    checkBox_ddii_frame: QtWidgets.QCheckBox
    checkBox_period: QtWidgets.QCheckBox
    spinBox_interval_ms: QtWidgets.QSpinBox
    pushButton_run_poll: QtWidgets.QPushButton
    lineEdit_impact_time_us: QtWidgets.QLineEdit
    pushButton_impact: QtWidgets.QPushButton

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._mw = args[0] if args else None
        self.cm_cmd: Optional[ModbusCMCommand] = None
        self._poll_task: Optional[asyncio.Task] = None
        loadUi(Path(__file__).parent.joinpath("telemetry_poll_widget.ui"), self)
        self.lineEdit_impact_time_us.setValidator(QtGui.QIntValidator(0, 65535, self))
        self.pushButton_run_poll.clicked.connect(self.pushButton_run_poll_handler)
        self._set_run_button_state(False)
        if self._mw is not None:
            try:
                self._mw.w_ser_dialog.coroutine_finished.connect(self.init_mb_cmd)
            except Exception:
                ...

    @qasync.asyncSlot()
    async def init_mb_cmd(self) -> None:
        if self._mw is None:
            return
        try:
            self.cm_cmd, _mpp_cmd = self._mw.w_ser_dialog.get_commands_interface(self._mw.logger)
        except Exception as ex:
            self.cm_cmd = None
            self._log_error(ex)

    def pushButton_run_poll_handler(self, checked: bool) -> None:
        if checked:
            self._poll_task = asyncio.create_task(self._poll())
            self._set_run_button_state(True)
            return
        self._stop_poll()

    @qasync.asyncSlot(bool)
    async def pushButton_impact_handler(self, checked: bool) -> None:
        await self._ensure_cm_cmd()
        if self.cm_cmd is None:
            self.pushButton_impact.setChecked(False)
            return
        value = self._impact_time_us() if checked else 0
        result = await self.cm_cmd.set_test_gpio_impact(value)
        if result == b"-1":
            self.pushButton_impact.setChecked(False)
            self.pushButton_impact.setText("Включить")
            return
        self.pushButton_impact.setText("Отключить" if checked else "Включить")

    async def _poll(self) -> None:
        try:
            await self._ensure_cm_cmd()
            while self.pushButton_run_poll.isChecked():
                await self._poll_once()
                if not self.checkBox_period.isChecked():
                    self.pushButton_run_poll.setChecked(False)
                    self._set_run_button_state(False)
                    return
                await asyncio.sleep(max(1, self.spinBox_interval_ms.value()) / 1000)
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            self._log_error(ex)
            self.pushButton_run_poll.setChecked(False)
            self._set_run_button_state(False)

    async def _poll_once(self) -> None:
        await self._ensure_cm_cmd()
        if self.cm_cmd is None or self._mw is None:
            return
        target = getattr(self._mw, "test_tables_widget", None)
        if target is None:
            return
        if self.checkBox_system_frame.isChecked():
            raw_system_frame = await self.cm_cmd.read_system_frame()
            if raw_system_frame != b"-1":
                target.set_system_frame(parse_system_frame(raw_system_frame))
        if self.checkBox_ddii_frame.isChecked():
            raw_ddii_frame = await self.cm_cmd.read_ddii_frame()
            if raw_ddii_frame != b"-1":
                target.set_ddii_frame(parse_ddii_frame(raw_ddii_frame))

    async def _ensure_cm_cmd(self) -> None:
        if self.cm_cmd is None:
            await self.init_mb_cmd()

    def _stop_poll(self) -> None:
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
        self._poll_task = None
        self._set_run_button_state(False)


    def _log_error(self, ex: Exception) -> None:
        if self._mw is not None and getattr(self._mw, "logger", None) is not None:
            self._mw.logger.error(ex)

    def _set_run_button_state(self, is_running: bool) -> None:
        if is_running:
            self.pushButton_run_poll.setText("Остановить")
            self.pushButton_run_poll.setToolTip("Остановить опрос")
            return

        self.pushButton_run_poll.setText("Запустить")
        self.pushButton_run_poll.setToolTip("Запустить опрос")
