import asyncio
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, Coroutine

import qasync
import qtmodern.styles
from pymodbus.client import AsyncModbusSerialClient
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QDoubleValidator, QFont, QIntValidator
from PyQt6.QtWidgets import QGridLayout, QGroupBox, QSizePolicy, QSpacerItem
from qtpy.uic import loadUi
from save_config import ConfigSaver

####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from custom.widgets import widget_led_off, widget_led_on  # noqa: E402
from modules.Main_Serial.main_serial_dialog_tcp import SerialConnect  # noqa: E402
from src.async_task_manager import AsyncTaskManager  # noqa: E402
from src.craft_custom_widget import add_serial_widget  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.log_config import log_init  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
# from src.print_logger import PrintLogger  # noqa: E402


class MainHvipDialog(QtWidgets.QDialog):
    spinBox_ch_volt: QtWidgets.QDoubleSpinBox
    spinBox_pips_volt: QtWidgets.QDoubleSpinBox
    spinBox_sipm_volt: QtWidgets.QDoubleSpinBox

    doubleSpinBox_ch_pwm: QtWidgets.QDoubleSpinBox
    doubleSpinBox_pips_pwm: QtWidgets.QDoubleSpinBox
    doubleSpinBox_sipm_pwm: QtWidgets.QDoubleSpinBox

    label_ch_cur: QtWidgets.QLabel
    label_sipm_cur: QtWidgets.QLabel
    label_pips_cur: QtWidgets.QLabel

    label_ch_pwm_mes: QtWidgets.QLabel
    label_pips_pwm_mes: QtWidgets.QLabel
    label_sipm_pwm_mes: QtWidgets.QLabel

    label_ch_v_mes: QtWidgets.QLabel
    label_pips_v_mes: QtWidgets.QLabel
    label_sipm_v_mes: QtWidgets.QLabel

    label_status: QtWidgets.QLabel

    doubleSpinBox_ch_pwm_max: QtWidgets.QDoubleSpinBox
    doubleSpinBox_pips_pwm_max: QtWidgets.QDoubleSpinBox
    doubleSpinBox_sipm_pwm_max: QtWidgets.QDoubleSpinBox

    pushButton_ok: QtWidgets.QPushButton
    pushButton_apply: QtWidgets.QPushButton

    pushButton_pips_on: QtWidgets.QPushButton
    pushButton_sipm_on: QtWidgets.QPushButton
    pushButton_ch_on: QtWidgets.QPushButton
    pushButton_get_rst: QtWidgets.QPushButton

    led_pips: QtWidgets.QWidget
    led_sipm: QtWidgets.QWidget
    led_ch: QtWidgets.QWidget

    label_desired_v_pips: QtWidgets.QLabel
    label_desired_v_sipm: QtWidgets.QLabel
    label_desired_v_ch: QtWidgets.QLabel

    vLayout_ser_connect: QtWidgets.QVBoxLayout

    PIPS_CH_VOLTAGE = 1
    SIPM_CH_VOLTAGE = 2
    CHERENKOV_CH_VOLTAGE = 3

    cmd_interface_init_signal = QtCore.pyqtSignal()

    def __init__(self, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).resolve().parent.joinpath("HVIP_window.ui"), self)
        self.mw = ModbusWorker()
        self.init_QObjects()
        self.config = ConfigSaver()
        self.flg_get_rst = 0
        if __name__ == "__main__":
            self.logger = args[0]
            self.w_ser_dialog: SerialConnect = args[1]
            self.task_manager = AsyncTaskManager(self.logger)
            w_ser_dialog.checkBox_mpp_only.setHidden(True)

        else:
            self.logger = self.parent.logger  # type: ignore
            self.w_ser_dialog: SerialConnect = self.parent.w_ser_dialog  # type: ignore
            
        self.w_ser_dialog.coroutine_finished.connect(self.cmd_interface_init)
        self.pushButton_ok.clicked.connect(self.pushButton_ok_handler)
        self.pushButton_get_rst.clicked.connect(self.pushButton_get_rst_handler)
        self.pushButton_apply.clicked.connect(self.pushButton_apply_handler)

        self.pushButton_pips_on.clicked.connect(self.pushButton_pips_on_handler)
        self.pushButton_sipm_on.clicked.connect(self.pushButton_sipm_on_handler)
        self.pushButton_ch_on.clicked.connect(self.pushButton_ch_on_handler)
        self.cmd_interface_init_signal.connect(self.creator_task)
        # Остановка измерений при отключении Serial
        self.w_ser_dialog.disconnected.connect(self.on_serial_disconnected)
        self.flag_measure = 1
        self.label_status.setText("Status:")

    @qasync.asyncSlot()
    async def cmd_interface_init(self) -> None:
        """Инициализация командного интерфейса"""
        if await self.w_ser_dialog.check_connection():
            self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)
            self.cmd_interface_init_signal.emit()
        await self.update_gui_data_spinbox()
        await self.update_gui_data_label()

    def creator_task(self) -> None:
        v_loop_req = self.asyncio_voltage_loop_request
        try:
            self.task_manager.create_task(v_loop_req(), "v_loop_req")
        except Exception as e:
            self._stop_measuring(f"Ошибка запуска задач: {e}")

    async def asyncio_voltage_loop_request(self) -> None:
        while 1:
            await self.update_gui_data_label()
            await asyncio.sleep(2)

    def _stop_measuring(self, reason: str | None = None):
        """Останавливает измерения, гасит задачи и приводит UI в исходное состояние."""
        if reason:
            self.logger.info(reason)
        # Отменяем все активные задачи по списку
        try: 
            for name in self.task_manager.get_active_tasks():
                # Очистку гистограмм делаем только если была HH задача
                if name == "v_loop_req":
                    self.task_manager.cancel_task(name)
        except Exception as e:
            self.logger.error(f"Error in stopping measurements: {str(e)}")

    @qasync.asyncSlot()
    async def on_serial_disconnected(self):
        self._stop_measuring("Serial отключен")
        # Обновляем команды через фабрику (вернутся null‑клиент команды)
        if self.w_ser_dialog:
            self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)

    def init_QObjects(self) -> None:
        self.spin_box_cfg_volt: dict[str, QtWidgets.QDoubleSpinBox] = {
            "spinBox_ch_volt": self.spinBox_ch_volt,
            "spinBox_pips_volt": self.spinBox_pips_volt,
            "spinBox_sipm_volt": self.spinBox_sipm_volt,
        }
        self.spin_box_cfg_pwm: dict[str, QtWidgets.QDoubleSpinBox] = {
            "doubleSpinBox_ch_pwm": self.doubleSpinBox_ch_pwm,
            "doubleSpinBox_pips_pwm": self.doubleSpinBox_pips_pwm,
            "doubleSpinBox_sipm_pwm": self.doubleSpinBox_sipm_pwm,
        }
        self.spin_box_cfg_pwm_max: dict[str, QtWidgets.QDoubleSpinBox] = {
            "doubleSpinBox_ch_pwm_max": self.doubleSpinBox_ch_pwm_max,
            "doubleSpinBox_pips_pwm_max": self.doubleSpinBox_pips_pwm_max,
            "doubleSpinBox_sipm_pwm_max": self.doubleSpinBox_sipm_pwm_max,
        }
        self.hvip_channels: dict[int, dict[str, Any]] = {
            self.CHERENKOV_CH_VOLTAGE: {
                "cfg_volt": self.spinBox_ch_volt,
                "cfg_pwm": self.doubleSpinBox_ch_pwm,
                "cfg_pwm_max": self.doubleSpinBox_ch_pwm_max,
                "desired": self.label_desired_v_ch,
                "meas_v": self.label_ch_v_mes,
                "meas_pwm": self.label_ch_pwm_mes,
                "meas_cur": self.label_ch_cur,
            },
            self.PIPS_CH_VOLTAGE: {
                "cfg_volt": self.spinBox_pips_volt,
                "cfg_pwm": self.doubleSpinBox_pips_pwm,
                "cfg_pwm_max": self.doubleSpinBox_pips_pwm_max,
                "desired": self.label_desired_v_pips,
                "meas_v": self.label_pips_v_mes,
                "meas_pwm": self.label_pips_pwm_mes,
                "meas_cur": self.label_pips_cur,
            },
            self.SIPM_CH_VOLTAGE: {
                "cfg_volt": self.spinBox_sipm_volt,
                "cfg_pwm": self.doubleSpinBox_sipm_pwm,
                "cfg_pwm_max": self.doubleSpinBox_sipm_pwm_max,
                "desired": self.label_desired_v_sipm,
                "meas_v": self.label_sipm_v_mes,
                "meas_pwm": self.label_sipm_pwm_mes,
                "meas_cur": self.label_sipm_cur,
            },
        }
        self.pips_on = 0
        self.sipm_on = 0
        self.ch_on = 0

    async def _read_hvip_channels(self) -> dict[int, list[int]]:
        return {
            ch: await self.cm_cmd.read_cm_hvip_debug_values(ch)
            for ch in (self.CHERENKOV_CH_VOLTAGE, self.PIPS_CH_VOLTAGE, self.SIPM_CH_VOLTAGE)
        }

    @staticmethod
    def _reg_x100_to_float(regs: list[int], offset: int) -> float:
        return (regs[offset] if len(regs) > offset else 0) / 100.0

    @qasync.asyncSlot()
    async def update_gui_data_spinbox(self) -> None:
        if not await self.w_ser_dialog.check_connection():
            await self.on_serial_disconnected()
            return
        try:
            channels = await self._read_hvip_channels()
            for ch, widgets in self.hvip_channels.items():
                regs = channels[ch]
                widgets["cfg_volt"].setValue(self._reg_x100_to_float(regs, self.cm_cmd.MB_HVIP_REG_V_HV_DESIRED_X100))
                widgets["cfg_pwm"].setValue(self._reg_x100_to_float(regs, self.cm_cmd.MB_HVIP_REG_PWM_X100))
                widgets["cfg_pwm_max"].setValue(self._reg_x100_to_float(regs, self.cm_cmd.MB_HVIP_REG_PWM_MAX_X100))
        except Exception as e:
            self.logger.error(str(e))

    @qasync.asyncSlot()
    async def update_gui_data_label(self) -> None:
        if not await self.w_ser_dialog.check_connection(only_cm=True):
            await self.on_serial_disconnected()
            return
        try:
            channels = await self._read_hvip_channels()
            for ch, widgets in self.hvip_channels.items():
                regs = channels[ch]
                widgets["desired"].setText(
                    "{:.2f}".format(self._reg_x100_to_float(regs, self.cm_cmd.MB_HVIP_REG_V_HV_DESIRED_X100))
                )
                widgets["meas_v"].setText(
                    "{:.2f}".format(self._reg_x100_to_float(regs, self.cm_cmd.MB_HVIP_REG_V_HV_X100))
                )
                widgets["meas_pwm"].setText(
                    "{:.2f}".format(self._reg_x100_to_float(regs, self.cm_cmd.MB_HVIP_REG_PWM_X100))
                )
                widgets["meas_cur"].setText(
                    "{:.2f}".format(self._reg_x100_to_float(regs, self.cm_cmd.MB_HVIP_REG_CURRENT_X100))
                )
                mode = regs[self.cm_cmd.MB_HVIP_REG_MODE] if len(regs) > self.cm_cmd.MB_HVIP_REG_MODE else 0
                self.update_power_status([ch, mode])
        except Exception as e:
            self.logger.error(str(e))

    ############ handler button ##############
    @qasync.asyncSlot()
    async def pushButton_pips_on_handler(self) -> None:
        if not await self.w_ser_dialog.check_connection():
            return
        if self.pips_on == 1:
            await self.cm_cmd.set_cm_hvip_mode(self.PIPS_CH_VOLTAGE, 0)
            self.pips_on = 0
            self.pushButton_pips_on.setText("Включить")
            self.led_pips.setStyleSheet(widget_led_off())

        else:
            await self.cm_cmd.set_cm_hvip_mode(self.PIPS_CH_VOLTAGE, 1)
            self.pips_on = 1
            self.pushButton_pips_on.setText("Отключить")
            self.led_pips.setStyleSheet(widget_led_on())

    @qasync.asyncSlot()
    async def pushButton_sipm_on_handler(self) -> None:
        if not await self.w_ser_dialog.check_connection():
            return
        if self.sipm_on == 1:
            await self.cm_cmd.set_cm_hvip_mode(self.SIPM_CH_VOLTAGE, 0)
            self.sipm_on = 0
            self.pushButton_sipm_on.setText("Включить")
            self.led_sipm.setStyleSheet(widget_led_off())

        else:
            await self.cm_cmd.set_cm_hvip_mode(self.SIPM_CH_VOLTAGE, 1)
            self.sipm_on = 1
            self.pushButton_sipm_on.setText("Отключить")
            self.led_sipm.setStyleSheet(widget_led_on())

    @qasync.asyncSlot()
    async def pushButton_ch_on_handler(self) -> None:
        if not await self.w_ser_dialog.check_connection():
            return
        if self.ch_on == 1:
            await self.cm_cmd.set_cm_hvip_mode(self.CHERENKOV_CH_VOLTAGE, 0)
            self.ch_on = 0
            self.pushButton_ch_on.setText("Включить")
            self.led_ch.setStyleSheet(widget_led_off())

        else:
            await self.cm_cmd.set_cm_hvip_mode(self.CHERENKOV_CH_VOLTAGE, 1)
            self.ch_on = 1
            self.pushButton_ch_on.setText("Отключить")
            self.led_ch.setStyleSheet(widget_led_on())

    @qasync.asyncSlot()
    async def pushButton_apply_handler(self) -> None:
        if not await self.w_ser_dialog.check_connection():
            return
        try:
            for ch, widgets in self.hvip_channels.items():
                await self.cm_cmd.set_cm_hvip_voltage(ch, widgets["cfg_volt"].value())
                await self.cm_cmd.set_cm_hvip_pwm(ch, widgets["cfg_pwm"].value())
                await self.cm_cmd.write_cm_hvip_debug_register(
                    self.cm_cmd.MB_HVIP_REG_PWM_MAX_X100,
                    int(round(widgets["cfg_pwm_max"].value() * 100.0)),
                    ch,
                )
            self.label_status.setText("Status: cfg was written")
        except Exception as e:
            self.logger.error(str(e))
            self.label_status.setText("Status: write error")

    def save_gui_data(self):
        loaded_cfg: list[dict[str, float | int | str]] = [
            {key: spin_box.value() for key, spin_box in item.items()}
            for item in [self.spin_box_cfg_volt, self.spin_box_cfg_pwm, self.spin_box_cfg_pwm_max]
        ]
        # Объединение всех словарей в один
        combined_cfg: dict[str, float | int | str] = {}
        for item in loaded_cfg:
            combined_cfg.update(item)
        self.config.save_to_config(combined_cfg)

    @qasync.asyncSlot()
    async def pushButton_get_rst_handler(self) -> None:
        if self.flg_get_rst == 0:
            await self.update_gui_data_spinbox()
            self.label_status.setText("Status: Data configuration is get")
            self.pushButton_get_rst.setText("R")
            self.flg_get_rst = 1
        else:
            self.label_status.setText("Status: Config loaded from file")
            self.pushButton_get_rst.setText("G")
            for_updt: list[dict[str, QtWidgets.QDoubleSpinBox]] = [
                self.spin_box_cfg_volt,
                self.spin_box_cfg_pwm,
                self.spin_box_cfg_pwm_max,
            ]
            for item in for_updt:
                self.config.load_from_config(item)
            self.flg_get_rst = 0

    def pushButton_ok_handler(self) -> None:
        # try:
        #     if self.client.connected:
        #         self.client.close()
        # except Exception as VErr:
        #     self.logger.debug(VErr)
        self.save_gui_data()
        # self.close()

    ############# update label ###############
    def update_power_status(self, data) -> None:
        try:
            if data[0] == self.PIPS_CH_VOLTAGE:
                if data[1] > 0:
                    self.pips_on = 1
                    self.pushButton_pips_on.setText("Отключить")
                    self.led_pips.setStyleSheet(widget_led_on())
                else:
                    self.pips_on = 0
                    self.pushButton_pips_on.setText("Включить")
                    self.led_pips.setStyleSheet(widget_led_off())
            elif data[0] == self.SIPM_CH_VOLTAGE:
                if data[1] > 0:
                    self.sipm_on = 1
                    self.pushButton_sipm_on.setText("Отключить")
                    self.led_sipm.setStyleSheet(widget_led_on())
                else:
                    self.sipm_on = 0
                    self.pushButton_sipm_on.setText("Включить")
                    self.led_sipm.setStyleSheet(widget_led_off())
            elif data[0] == self.CHERENKOV_CH_VOLTAGE:
                if data[1] > 0:
                    self.ch_on = 1
                    self.pushButton_ch_on.setText("Отключить")
                    self.led_ch.setStyleSheet(widget_led_on())
                else:
                    self.ch_on = 0
                    self.pushButton_ch_on.setText("Включить")
                    self.led_ch.setStyleSheet(widget_led_off())
        except Exception as ex:
            self.logger.debug(str(ex))

    def closeEvent(self, event) -> None:
        try:
            self._stop_measuring("Все задачи завершены")
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
    w: MainHvipDialog = MainHvipDialog(logger, w_ser_dialog)
    # add_serial_widget(w.vLayout_ser_connect, w_ser_dialog)
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
