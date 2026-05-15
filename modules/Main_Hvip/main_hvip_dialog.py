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
from modules.Main_Hvip.save_config import ConfigSaver

from custom.widgets import widget_led_off, widget_led_on
from app.plugins.connection.main_serial_dialog_tcp import SerialConnect
from app.src.util.async_task_manager import AsyncTaskManager
from app.src.components.ui.craft_custom_widget import add_serial_widget
from app.src.components.modbus.ddii_command import ModbusCMCommand, ModbusMPPCommand
from app.src.components.log.config import log_init, log_s
from app.src.components.modbus.worker import ModbusWorker
from app.src.components.parsers.custom_parsers import Parsers
from app.src.components.parsers.parsers_pack import LineEditPack, LineEObj


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

    spinBox_ch_a_u: QtWidgets.QDoubleSpinBox
    spinBox_ch_b_u: QtWidgets.QDoubleSpinBox
    spinBox_ch_a_i: QtWidgets.QDoubleSpinBox
    spinBox_ch_b_i: QtWidgets.QDoubleSpinBox

    spinBox_pips_a_u: QtWidgets.QDoubleSpinBox
    spinBox_pips_b_u: QtWidgets.QDoubleSpinBox
    spinBox_pips_a_i: QtWidgets.QDoubleSpinBox
    spinBox_pips_b_i: QtWidgets.QDoubleSpinBox

    spinBox_sipm_a_u: QtWidgets.QDoubleSpinBox
    spinBox_sipm_b_u: QtWidgets.QDoubleSpinBox
    spinBox_sipm_a_i: QtWidgets.QDoubleSpinBox
    spinBox_sipm_b_i: QtWidgets.QDoubleSpinBox

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
        self.parser = Parsers()
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
        self.spin_box_cfg_pwm: dict[str, QtWidgets.QDoubleSpinBox] = {
            "doubleSpinBox_ch_pwm": self.doubleSpinBox_ch_pwm,
            "doubleSpinBox_pips_pwm": self.doubleSpinBox_pips_pwm,
            "doubleSpinBox_sipm_pwm": self.doubleSpinBox_sipm_pwm,
        }
        self.label_meas: dict[str, QtWidgets.QLabel | int] = {
            "label_ch_v_mes": self.label_ch_v_mes,
            "label_ch_pwm_mes": self.label_ch_pwm_mes,
            "label_ch_cur": self.label_ch_cur,
            "hvip_mode_ch": 1,
            "label_pips_v_mes": self.label_pips_v_mes,
            "label_pips_pwm_mes": self.label_pips_pwm_mes,
            "label_pips_cur": self.label_pips_cur,
            "hvip_mode_pips": 1,
            "label_sipm_v_mes": self.label_sipm_v_mes,
            "label_sipm_pwm_mes": self.label_sipm_pwm_mes,
            "label_sipm_cur": self.label_sipm_cur,
            "hvip_mode_sipm": 1,
        }

        self.label_desired_v: dict[str, QtWidgets.QLabel] = {
            "label_desired_v_ch": self.label_desired_v_ch,
            "label_desired_v_pips": self.label_desired_v_pips,
            "label_desired_v_sipm": self.label_desired_v_sipm,
        }
        self.label_desired_v_T: list[LineEObj] = [
            LineEObj(key=key, lineobj_txt=value.text(), tp="f") for (key, value) in self.label_desired_v.items()
        ]

        self.spin_box_A_B: dict[str, QtWidgets.QDoubleSpinBox] = {
            "spinBox_ch_a_u": self.spinBox_ch_a_u,
            "spinBox_pips_a_u": self.spinBox_pips_a_u,
            "spinBox_sipm_a_u": self.spinBox_sipm_a_u,
            "spinBox_ch_b_u": self.spinBox_ch_b_u,
            "spinBox_pips_b_u": self.spinBox_pips_b_u,
            "spinBox_sipm_b_u": self.spinBox_sipm_b_u,
            "spinBox_ch_a_i": self.spinBox_ch_a_i,
            "spinBox_pips_a_i": self.spinBox_pips_a_i,
            "spinBox_sipm_a_i": self.spinBox_sipm_a_i,
            "spinBox_ch_b_i": self.spinBox_ch_b_i,
            "spinBox_pips_b_i": self.spinBox_pips_b_i,
            "spinBox_sipm_b_i": self.spinBox_sipm_b_i,
        }

    @qasync.asyncSlot()
    async def get_cfg_data_from_widget(self, d_struct: dict, tp: str) -> list[int]:
        pack: list[LineEObj] = [
            LineEObj(key=key, lineobj_txt=value.value(), tp=tp) for i, (key, value) in enumerate(d_struct.items())
        ]
        get_data_widget = LineEditPack()
        return get_data_widget(pack, "little")

    @qasync.asyncSlot()
    async def update_gui_data_spinbox(self) -> None:
        if not await self.w_ser_dialog.check_connection():
            await self.on_serial_disconnected()
            return
        err_cfg_volt = 0
        err_cfg_pwm = 0
        err_cfg_a_b = 0
        try:
            answ_cfg_volt: bytes = await self.cm_cmd.get_cfg_voltage()
            data_cfg_volt: dict[str, str] = await self.parser.pars_cfg_volt(answ_cfg_volt)
        except Exception as e:
            err_cfg_volt = 1
            self.logger.error(str(e))
        try:
            answ_cfg_pwm: bytes = await self.cm_cmd.get_cfg_pwm()
            data_cfg_pwm: dict[str, str] = await self.parser.pars_cfg_pwm(answ_cfg_pwm)
        except Exception as e:
            err_cfg_pwm = 1
            self.logger.error(str(e))
        try:
            await asyncio.sleep(0.1)
            answ_cfg_a_b: bytes = await self.cm_cmd.get_cfg_a_b()
            data_cfg_a_b: dict[str, str] = await self.parser.pars_cfg_a_b(answ_cfg_a_b)
        except Exception as e:
            err_cfg_a_b = 1
            self.logger.error(str(e))
        if err_cfg_volt == 0:
            for key, val in self.spin_box_cfg_volt.items():
                val.setValue(float(data_cfg_volt.get(key)))  # type: ignore
        if err_cfg_pwm == 0:
            for key, val in self.spin_box_cfg_pwm.items():
                val.setValue(float(data_cfg_pwm.get(key)))  # type: ignore
        if err_cfg_a_b == 0:
            for key, val in self.spin_box_A_B.items():
                val.setValue(float(data_cfg_a_b.get(key)))  # type: ignore

    @qasync.asyncSlot()
    async def update_gui_data_label(self) -> None:
        if not await self.w_ser_dialog.check_connection(only_cm=True):
            await self.on_serial_disconnected()
            return
        try:
            answer: bytes = await self.cm_cmd.get_voltage()
            desired_v: bytes = await self.cm_cmd.get_desired_voltage()
            data: dict[str, str] = await self.parser.pars_voltage(answer)
            data_desired_v: dict[str, str] = await self.parser.pars_everything(
                self.label_desired_v_T, desired_v, endian="big"
            )
            for key, val in self.label_desired_v.items():
                val.setText(data_desired_v[key])
            for i, (key, val) in enumerate(self.label_meas.items()):
                if "mode" in key:
                    if key == "hvip_mode_ch":
                        self.update_power_status([self.CHERENKOV_CH_VOLTAGE, int(data[key])])
                    if key == "hvip_mode_pips":
                        self.update_power_status([self.PIPS_CH_VOLTAGE, int(data[key])])
                    if key == "hvip_mode_sipm":
                        self.update_power_status([self.SIPM_CH_VOLTAGE, int(data[key])])
                else:
                    val.setText("{:.2f}".format(float(list(data.values())[i])))  # type: ignore
        except Exception as e:
            self.logger.error(str(e))

    ############ handler button ##############
    @qasync.asyncSlot()
    async def pushButton_pips_on_handler(self) -> None:
        if not await self.w_ser_dialog.check_connection():
            return
        if self.pips_on == 1:
            await self.cm_cmd.switch_power([self.PIPS_CH_VOLTAGE, 0])
            self.pips_on = 0
            self.pushButton_pips_on.setText("Включить")
            self.led_pips.setStyleSheet(widget_led_off())

        else:
            await self.cm_cmd.switch_power([self.PIPS_CH_VOLTAGE, 1])
            self.pips_on = 1
            self.pushButton_pips_on.setText("Отключить")
            self.led_pips.setStyleSheet(widget_led_on())

    @qasync.asyncSlot()
    async def pushButton_sipm_on_handler(self) -> None:
        if not await self.w_ser_dialog.check_connection():
            return
        if self.sipm_on == 1:
            await self.cm_cmd.switch_power([self.SIPM_CH_VOLTAGE, 0])
            self.sipm_on = 0
            self.pushButton_sipm_on.setText("Включить")
            self.led_sipm.setStyleSheet(widget_led_off())

        else:
            await self.cm_cmd.switch_power([self.SIPM_CH_VOLTAGE, 1])
            self.sipm_on = 1
            self.pushButton_sipm_on.setText("Отключить")
            self.led_sipm.setStyleSheet(widget_led_on())

    @qasync.asyncSlot()
    async def pushButton_ch_on_handler(self) -> None:
        if not await self.w_ser_dialog.check_connection():
            return
        if self.ch_on == 1:
            await self.cm_cmd.switch_power([self.CHERENKOV_CH_VOLTAGE, 0])
            self.ch_on = 0
            self.pushButton_ch_on.setText("Включить")
            self.led_ch.setStyleSheet(widget_led_off())

        else:
            await self.cm_cmd.switch_power([self.CHERENKOV_CH_VOLTAGE, 1])
            self.ch_on = 1
            self.pushButton_ch_on.setText("Отключить")
            self.led_ch.setStyleSheet(widget_led_on())

    @qasync.asyncSlot()
    async def pushButton_apply_handler(self) -> None:
        if not await self.w_ser_dialog.check_connection():
            return
        vlt_data: list[int] = await self.get_cfg_data_from_widget(self.spin_box_cfg_volt, "f")
        pwm_data: list[int] = await self.get_cfg_data_from_widget(self.spin_box_cfg_pwm, "f")
        pwm_max_data: list[int] = await self.get_cfg_data_from_widget(self.spin_box_cfg_pwm, "i")
        await self.cm_cmd.set_voltage_pwm(vlt_data + pwm_data)
        cfg_a_b_data: list[int] = await self.get_cfg_data_from_widget(self.spin_box_A_B, "f")
        await asyncio.sleep(0.1)
        await self.cm_cmd.set_cfg_a_b(cfg_a_b_data)
        self.label_status.setText("Status: cfg was written")
        # self.save_gui_data()

    def save_gui_data(self):
        loaded_cfg: list[dict[str, float | int | str]] = [
            {key: spin_box.value() for key, spin_box in item.items()}
            for item in [self.spin_box_cfg_volt, self.spin_box_cfg_pwm, self.spin_box_A_B]
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
                self.spin_box_A_B,
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
                if data[1] == 1:
                    self.pips_on = 1
                    self.pushButton_pips_on.setText("Отключить")
                    self.led_pips.setStyleSheet(widget_led_on())
                else:
                    self.pips_on = 0
                    self.pushButton_pips_on.setText("Включить")
                    self.led_pips.setStyleSheet(widget_led_off())
            elif data[0] == self.SIPM_CH_VOLTAGE:
                if data[1] == 1:
                    self.sipm_on = 1
                    self.pushButton_sipm_on.setText("Отключить")
                    self.led_sipm.setStyleSheet(widget_led_on())
                else:
                    self.sipm_on = 0
                    self.pushButton_sipm_on.setText("Включить")
                    self.led_sipm.setStyleSheet(widget_led_off())
            elif data[0] == self.CHERENKOV_CH_VOLTAGE:
                if data[1] == 1:
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
