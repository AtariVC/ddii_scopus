"""Меню запуска: объединяет прежние ``run_meas_widget`` и ``run_flux_widget``.

Одна кнопка запускает то, что отмечено галочками:

* «Чтение осциллограмм» — цикл ``ACQ_task``: читает осциллограммы PIPS/SiPM,
  рисует их и пики в гистограммы (бывший run_meas);
* «Опрос счётчиков» — цикл ``HH_task``: гистограммы электронов/протонов/HCP в
  панель счётчика частиц (бывший run_flux).

Когда счётчики опрашиваются, а осциллограммы не читаются, дополнительно идёт
``ACQ_Peak_task`` — он берёт пики прямо из регистров АЦП. При включённом чтении
осциллограмм этого не делаем: пики туда уже кладёт ``ACQ_task``, иначе
гистограммы PIPS/SiPM считали бы одно и то же дважды.

Порог запуска и тригер — одно и то же поле ``lineEdit_trigger``.

Запуск отдельно (панель поднимается с настоящими графиками и счётчиком):

    python app/widgets/oscilloscope/run_control_widget.py
    python -m app.widgets.oscilloscope.run_control_widget
"""

# Прямой запуск файла: абсолютные импорты `app.*` и promoted-виджеты из .ui
# работают только когда модуль исполняется в контексте пакета.
if __name__ == "__main__" and __package__ in (None, ""):
    import os
    import runpy
    import sys

    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    runpy.run_module("app.widgets.oscilloscope.run_control_widget", run_name="__main__", alter_sys=True)
    raise SystemExit(0)

import asyncio
import datetime
from pathlib import Path
from typing import Awaitable, Callable

import numpy as np
import qasync
from PyQt6 import QtWidgets
from qtpy.uic import loadUi

from dark_pro_widgets import theme
from dark_pro_widgets.buttons import PrimaryButton

from app.plugins.connection.connection_bar import ConnectionBar
from app.src.components.modbus.worker import ModbusWorker
from app.src.components.parsers.custom_parsers import Parsers
from app.src.event.event import Event
from app.src.util.async_task_manager import AsyncTaskManager
from app.widgets.oscilloscope.graph_widget import GraphWidget

# 12-битные внешние счётчики (0..4095) — для детекции переполнения/сброса
_COUNTER_MODULUS = 4096


class _RunButton(PrimaryButton):
    """Акцентная кнопка запуска. Адаптер под загрузчик .ui, который создаёт
    promoted-виджет как ``Class(parent)``."""

    def __init__(self, parent=None):
        super().__init__("", variant="accent", parent=parent)


class RunControlWidget(QtWidgets.QDialog):
    lineEdit_trigger: QtWidgets.QLineEdit
    lineEdit_interval: QtWidgets.QLineEdit
    checkBox_trigger_start: QtWidgets.QCheckBox
    checkBox_counters: QtWidgets.QCheckBox
    checkBox_waveform: QtWidgets.QCheckBox
    checkBox_write_log: QtWidgets.QCheckBox
    pushButton_run: _RunButton

    def __init__(self, *args) -> None:
        super().__init__()
        self.parent = args[0]
        loadUi(Path(__file__).parent.joinpath("run_control_widget.ui"), self)

        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.graph_widget: GraphWidget = self.parent.w_graph_widget  # type: ignore
        self.w_ser_dialog: ConnectionBar = self.parent.w_ser_dialog  # type: ignore
        self.logger = self.parent.logger  # type: ignore
        self.task_manager = AsyncTaskManager(self.logger)

        # ==== флаги ====
        self.enable_trig_meas_flag = "enable_trig_meas_flag"
        self.poll_counters_flag = "poll_counters_flag"
        self.read_waveform_flag = "read_waveform_flag"
        self.wr_log_flag = "wr_log_flag"
        self.start_measure_flag = "start_measure_flag"
        self.flags: dict = {
            self.enable_trig_meas_flag: True,
            self.poll_counters_flag: True,
            self.read_waveform_flag: True,
            self.wr_log_flag: False,
            self.start_measure_flag: False,
        }
        self.checkbox_flag_mapping = {
            self.checkBox_trigger_start: self.enable_trig_meas_flag,
            self.checkBox_counters: self.poll_counters_flag,
            self.checkBox_waveform: self.read_waveform_flag,
            self.checkBox_write_log: self.wr_log_flag,
        }

        # ==== события ====
        self.save_threshold_event = Event(int)
        self.get_electron_hist_event = Event(list)
        self.get_proton_hist_event = Event(list)
        self.get_hcp_hist_event = Event(list)
        self.get_acq_event = Event(list)
        self.HH_task_sync_time_event = Event(str)

        flux = self.parent.flux_widget  # type: ignore
        self.get_electron_hist_event.subscribe(flux.update_gui_data_electron)
        self.get_proton_hist_event.subscribe(flux.update_gui_data_proton)
        self.get_hcp_hist_event.subscribe(flux.update_gui_data_hcp)
        self.get_acq_event.subscribe(flux.update_data_acq)
        self.parent.shared_bfr_update_event.subscribe(self._update_sync_name_hh)  # type: ignore

        # порог сохранения уходит в отрисовщики
        for pen in (self.graph_widget.gp_pips, self.graph_widget.gp_sipm,
                    self.graph_widget.hp_pips, self.graph_widget.hp_sipm):
            try:
                self.save_threshold_event.subscribe(pen.set_save_threshold)
            except Exception:
                ...

        # ==== состояние опроса счётчиков ====
        self.name_data: str = ""
        self.name_file_save: str = ""
        self.path_to_save: Path = self._init_path_to_save()
        self.save_log_file: bool = False
        self.delay: int = 2
        self.TmpCount: int = 0
        self._prev_electron = self._acc_electron = None
        self._prev_proton = self._acc_proton = None
        self._prev_hcp = self._acc_hcp = None
        self._counter_modulus = _COUNTER_MODULUS

        self._apply_theme()
        self.init_flags()
        self.lineEdit_trigger.editingFinished.connect(self._on_trigger_changed)
        self._on_trigger_changed()

        self.w_ser_dialog.coroutine_finished.connect(self.init_mb_cmd)
        self.w_ser_dialog.disconnected.connect(self.on_serial_disconnected)
        self.pushButton_run.clicked.connect(self.pushButton_run_handler)
        self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)

    # ===== оформление =====
    def _apply_theme(self) -> None:
        """Тема заливает отмеченный чекбокс цветом, но глифа ✓ не рисует —
        подставляем свою галочку (в наборе иконок подходящей нет).
        """
        check = (Path(__file__).resolve().parents[3] / "icon" / "check.svg").as_posix()
        self.setStyleSheet(
            f"""
            QCheckBox {{ spacing: 8px; background: transparent; }}
            QCheckBox::indicator {{
                width: 18px; height: 18px;
                border: 1px solid {theme.BORDER};
                border-radius: 5px;
                background: {theme.FIELD_BG};
            }}
            QCheckBox::indicator:hover {{ border: 1px solid {theme.ACCENT}; }}
            QCheckBox::indicator:checked {{
                background: {theme.ACCENT};
                border: 1px solid {theme.ACCENT};
                image: url("{check}");
            }}
            """
        )

    # ===== флаги =====
    def init_flags(self) -> None:
        for checkbox, flag in self.checkbox_flag_mapping.items():
            checkbox.setChecked(self.flags[flag])
            checkbox.clicked.connect(lambda state, f=flag: self.flag_exhibit(state, f))
        self._sync_trigger_enabled()

    def flag_exhibit(self, state: bool, flag: str) -> None:
        self.flags[flag] = bool(state)
        if flag == self.enable_trig_meas_flag:
            self._sync_trigger_enabled()

    def _sync_trigger_enabled(self) -> None:
        """Порог осмыслен только при запуске по тригеру."""
        self.lineEdit_trigger.setEnabled(self.flags[self.enable_trig_meas_flag])

    def _on_trigger_changed(self) -> None:
        """Отдать порог отрисовщикам — они по нему фильтруют сохранение."""
        try:
            self.save_threshold_event.emit(self._trigger_level())
        except Exception:
            ...

    def _trigger_level(self) -> int:
        try:
            return int(self.lineEdit_trigger.text())
        except (TypeError, ValueError):
            return 0

    def _interval(self) -> int:
        try:
            return max(1, int(self.lineEdit_interval.text()))
        except (TypeError, ValueError):
            return 2

    # ===== подключение =====
    @qasync.asyncSlot()
    async def init_mb_cmd(self) -> None:
        """Инициализация командного интерфейса МПП и ЦМ."""
        if not self.w_ser_dialog or not self.w_ser_dialog.is_modbus_ready():
            self.logger.warning("Modbus не готов: нет активного соединения")
            if self.w_ser_dialog:
                self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)
            return
        try:
            ready = await self.w_ser_dialog.check_connection()
        except Exception as e:
            self.logger.warning(f"Не удалось обновить статус ЦМ/МПП: {e}")
            self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)
            return
        self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)
        if not ready:
            self.logger.warning("ЦМ/МПП недоступны — запуск измерений невозможен")

    @qasync.asyncSlot()
    async def on_serial_disconnected(self) -> None:
        await self._stop_measuring("Связь потеряна")
        if self.w_ser_dialog:
            self.cm_cmd, self.mpp_cmd = self.w_ser_dialog.get_commands_interface(self.logger)

    # ===== запуск/остановка =====
    @qasync.asyncSlot()
    async def pushButton_run_handler(self) -> None:
        if self.flags[self.start_measure_flag]:
            await self._stop_measuring()
            return

        if not (self.flags[self.read_waveform_flag] or self.flags[self.poll_counters_flag]):
            self.logger.error("Нечего запускать: отметьте чтение осциллограмм или опрос счётчиков")
            return
        if not await self.w_ser_dialog.check_connection():
            self.logger.error("Нет подключения (ЦМ/МПП недоступны)")
            return

        self.path_to_save = self._init_path_to_save()
        self.name_file_save = self._init_name_file_save()
        self.save_log_file = self.flags[self.wr_log_flag]
        self.delay = self._interval()

        await self.init_mb_cmd()
        self.graph_widget.hp_pips.hist_clear()
        self.graph_widget.hp_sipm.hist_clear()

        if self.flags[self.poll_counters_flag]:
            ready = await self.init_HH_request(self.delay, self.path_to_save,
                                               self.name_file_save, self.save_log_file)
            if not ready:
                return

        self.flags[self.start_measure_flag] = True
        self.pushButton_run.setText("Остановить измерение")
        self._set_controls_enabled(False)

        try:
            if self.flags[self.read_waveform_flag]:
                acq_task: Callable[[], Awaitable[None]] = self.asyncio_ACQ_loop_request
                self.task_manager.create_task(acq_task(), "ACQ_task")
            if self.flags[self.poll_counters_flag]:
                hh_task: Callable[[], Awaitable[None]] = self.asyncio_HH_loop_request
                self.task_manager.create_task(hh_task(), "HH_task")
                # пики из регистров АЦП нужны только когда осциллограммы не читаем,
                # иначе ACQ_task уже наполняет те же гистограммы
                if not self.flags[self.read_waveform_flag]:
                    await self.mpp_cmd.set_level(self._trigger_level())
                    await self.mpp_cmd.start_measure(on=1)
                    peak_task: Callable[[], Awaitable[None]] = self.asyncio_ACQ_Peak_loop_request
                    self.task_manager.create_task(peak_task(), "ACQ_Peak_task")
        except Exception as e:
            await self._stop_measuring(f"Ошибка запуска задач: {e}")

    async def _stop_measuring(self, reason: str | None = None) -> None:
        """Останавливает измерение, гасит задачи и возвращает UI в исходное состояние."""
        if reason:
            self.logger.error(reason)
        try:
            await self.mpp_cmd.start_measure(on=0)
        except Exception:
            ...
        try:
            for name in self.task_manager.get_active_tasks():
                if name in ("HH_task",):
                    try:
                        await self.mpp_cmd.clear_hist()
                    except Exception:
                        ...
                if name == "ACQ_task":
                    try:
                        await self.mpp_cmd.stop_measure()
                    except Exception:
                        ...
                self.task_manager.cancel_task(name)
        except Exception as e:
            self.logger.error(f"Ошибка остановки измерений: {e}")

        self.flags[self.start_measure_flag] = False
        self.pushButton_run.setText("Начать измерение")
        self._set_controls_enabled(True)

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Во время измерения параметры не меняем."""
        for checkbox in self.checkbox_flag_mapping:
            checkbox.setEnabled(enabled)
        self.lineEdit_interval.setEnabled(enabled)
        self.lineEdit_trigger.setEnabled(enabled and self.flags[self.enable_trig_meas_flag])

    # ===== пути сохранения =====
    def _init_path_to_save(self) -> Path:
        parent_path: Path = Path("./log/scope").resolve()
        return parent_path / datetime.datetime.now().strftime("%d-%m-%Y")[:23]

    def _init_name_file_save(self) -> str:
        return datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S-%f")[:23]

    def _update_sync_name_hh(self, sync_name) -> None:
        self.name_data = sync_name

    # ===== цикл чтения осциллограмм (бывший run_meas) =====
    async def asyncio_ACQ_loop_request(self) -> None:
        try:
            lvl = self._trigger_level()
            save: bool = False
            if not self.w_ser_dialog.is_modbus_ready():
                await self._stop_measuring("Потеряно соединение")
                return
            if self.flags[self.enable_trig_meas_flag]:
                await self.mpp_cmd.set_level(lvl)
                await self.mpp_cmd.start_measure(on=1)
            while 1:
                if not self.w_ser_dialog.is_modbus_ready():
                    await self._stop_measuring("Потеряно соединение")
                    return
                self.name_data = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:24]
                self.parent.shared_bfr_update_event.emit(self.name_data)  # type: ignore
                if not self.flags[self.enable_trig_meas_flag]:
                    await self.mpp_cmd.start_measure_forced(0)
                    await self.mpp_cmd.start_measure_forced(1)
                else:
                    await self.mpp_cmd.issue_waveform()
                await self.mpp_cmd.waveform_release()
                await asyncio.sleep(1)
                result_ch0: bytes = await self.mpp_cmd.read_oscill(ch=0)
                result_ch1: bytes = await self.mpp_cmd.read_oscill(ch=1)
                result_ch0_int: list[int] = await self.parser.mpp_pars_16b(result_ch0)
                result_ch1_int: list[int] = await self.parser.mpp_pars_16b(result_ch1)
                # сохраняем только то, что выше порога
                if self.flags[self.wr_log_flag]:
                    peak0 = max(result_ch0_int)
                    peak1 = max(result_ch1_int)
                    save = (peak0 & 0xFFF > lvl) or (peak1 & 0xFFF > 5)
                else:
                    save = False
                try:
                    data_pips = await self.graph_widget.gp_pips.draw_graph(
                        result_ch0_int,
                        name_file_save_data=self.name_file_save,
                        name_data=self.name_data,
                        path_to_save=self.path_to_save,
                        save_log=save,
                        clear=True,
                    )
                    data_sipm = await self.graph_widget.gp_sipm.draw_graph(
                        result_ch1_int,
                        name_file_save_data=self.name_file_save,
                        name_data=self.name_data,
                        path_to_save=self.path_to_save,
                        save_log=save,
                        clear=True,
                    )
                    await self.graph_widget.hp_pips.draw_hist(
                        [max(data_pips[1])],
                        name_file_save_data=self.name_file_save,
                        name_data=self.name_data,
                        path_to_save=self.path_to_save,
                        save_log=save,
                    )
                    await self.graph_widget.hp_sipm.draw_hist(
                        [max(data_sipm[1])],
                        name_file_save_data=self.name_file_save,
                        name_data=self.name_data,
                        path_to_save=self.path_to_save,
                        save_log=save,
                    )
                    self.graph_widget.refresh_badges()
                except asyncio.exceptions.CancelledError:
                    return None
        except asyncio.CancelledError:
            ...
        except Exception as e:
            await self._stop_measuring(f"Ошибка (осциллограммы): {e}")
            return

    # ===== цикл опроса счётчиков (бывший run_flux) =====
    async def init_HH_request(self, delay, path_to_save: Path, name_file_save: str,
                              save_log_file: bool) -> bool:
        self.delay = delay
        self.path_to_save = path_to_save
        self.name_file_save = name_file_save
        self.save_log_file = save_log_file
        try:
            if not self.w_ser_dialog.is_modbus_ready():
                await self._stop_measuring("Потеряно соединение (HH init)")
                return False
            await self.mpp_cmd.clear_hist()
            await self.mpp_cmd.clear_hcp_hist()
            return True
        except Exception as e:
            await self._stop_measuring(f"Ошибка подготовки гистограмм: {e}")
            return False

    async def asyncio_HH_loop_request(self) -> None:
        """Опрос счётчика частиц."""
        data: list[int] = []
        self.graph_widget.hp_counter.hist_clear()
        self._prev_electron = self._acc_electron = None
        self._prev_proton = self._acc_proton = None
        self._prev_hcp = self._acc_hcp = None
        while 1:
            await asyncio.sleep(self.delay)
            if not self.w_ser_dialog.is_modbus_ready():
                await self._stop_measuring("Потеряно соединение")
                return
            try:
                result_hist32: bytes = await self.mpp_cmd.get_hist32()
                result_hist16: bytes = await self.mpp_cmd.get_hist16()
                result_hcp_hist: bytes = await self.mpp_cmd.get_hcp_hist()
            except Exception as e:
                await self._stop_measuring(f"Ошибка чтения гистограмм: {e}")
                return

            if not self.name_data:
                self.name_data = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:24]

            result_hist32_int: list[int] = await self.parser.mpp_pars_32b(result_hist32)
            result_hist16_int: list[int] = await self.parser.mpp_pars_16b(result_hist16)
            result_hcp_hist_int: list[int] = await self.parser.mpp_pars_16b(result_hcp_hist)

            self._prev_electron, self._acc_electron = self._accumulate_with_reset(
                self._prev_electron, self._acc_electron, result_hist32_int)
            self._prev_proton, self._acc_proton = self._accumulate_with_reset(
                self._prev_proton, self._acc_proton, result_hist16_int)
            self._prev_hcp, self._acc_hcp = self._accumulate_with_reset(
                self._prev_hcp, self._acc_hcp, result_hcp_hist_int)
            try:
                self.get_electron_hist_event.emit(self._acc_electron.tolist())
                self.get_proton_hist_event.emit(self._acc_proton.tolist())
                self.get_hcp_hist_event.emit(self._acc_hcp.tolist())
            except Exception:
                self.get_electron_hist_event.emit(result_hist32_int)
                self.get_proton_hist_event.emit(result_hist16_int)
                self.get_hcp_hist_event.emit(result_hcp_hist_int)

            try:
                if self._acc_electron is not None and self._acc_proton is not None and self._acc_hcp is not None:
                    data = self._acc_electron.tolist() + self._acc_proton.tolist() + self._acc_hcp.tolist()
                else:
                    data = result_hist32_int + result_hist16_int + result_hcp_hist_int
                await self.graph_widget.hp_counter.draw_hist(
                    data, bin_count=len(data),
                    name_file_save_data=self.name_file_save,
                    name_data=self.name_data,
                    path_to_save=self.path_to_save,
                    save_log=self.save_log_file,
                    data_is_hist=True,
                )
                self.graph_widget.refresh_badges()
                # сбрасываем имя — нужно для синхронизации с другими процессами
                self.name_data = ""
            except asyncio.exceptions.CancelledError as e:
                self.name_data = ""
                self.logger.error(str(e))
                return None

    async def asyncio_ACQ_Peak_loop_request(self) -> None:
        """Опрос пиков АЦП напрямую из регистров."""
        self.graph_widget.hp_counter.hist_clear()
        self._prev_electron = self._acc_electron = None
        self._prev_proton = self._acc_proton = None
        self._prev_hcp = self._acc_hcp = None
        while 1:
            await asyncio.sleep(0.0005)
            if not self.w_ser_dialog.is_modbus_ready():
                await self._stop_measuring("Потеряно соединение")
                return
            try:
                result_acq1: bytes = await self.mpp_cmd.get_acq1()
                result_acq2: bytes = await self.mpp_cmd.get_acq2()
                result_tmp_count: bytes = await self.mpp_cmd.get_tmp_count()
            except Exception as e:
                await self._stop_measuring(f"Ошибка чтения пиков АЦП: {e}")
                return

            self.name_data = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:24]
            acq1: list[int] = await self.parser.mpp_pars_16b(result_acq1)
            acq2: list[int] = await self.parser.mpp_pars_16b(result_acq2)
            tmp_count: list[int] = await self.parser.mpp_pars_16b(result_tmp_count)
            acq1_value = acq1[0] if acq1 else 0
            acq2_value = acq2[0] if acq2 else 0
            tmp_count_value = tmp_count[0] if tmp_count else 0
            self.get_acq_event.emit([str(acq1_value), str(acq2_value)])

            try:
                if self.TmpCount != tmp_count_value:
                    self.TmpCount = tmp_count_value
                    await self.graph_widget.hp_pips.draw_hist(
                        [acq1_value], bin_count=4096,
                        name_file_save_data=self.name_file_save,
                        name_data=self.name_data,
                        path_to_save=self.path_to_save,
                        save_log=self.save_log_file,
                        data_is_hist=False,
                    )
                    await self.graph_widget.hp_sipm.draw_hist(
                        [acq2_value], bin_count=4096,
                        name_file_save_data=self.name_file_save,
                        name_data=self.name_data,
                        path_to_save=self.path_to_save,
                        save_log=self.save_log_file,
                        data_is_hist=False,
                    )
                    self.graph_widget.refresh_badges()
            except asyncio.exceptions.CancelledError as e:
                self.logger.error(str(e))
                return None

    def _accumulate_with_reset(self, prev, acc, curr):
        """Накопление по бинам с детекцией сброса и переполнения счётчика.

        Для каждого бина:
        - curr >= prev: delta = curr - prev
        - curr < prev и prev у потолка (12 бит): delta = (MOD - prev) + curr
        - иначе (жёсткий сброс): delta = curr
        """
        curr_arr = np.array(curr, dtype=np.int64)
        if prev is None or acc is None:
            return curr_arr, curr_arr.copy()
        try:
            prev_arr = np.array(prev, dtype=np.int64)
            acc_arr = np.array(acc, dtype=np.int64)
            if len(prev_arr) != len(curr_arr) or len(acc_arr) != len(curr_arr):
                return curr_arr, curr_arr.copy()
            raw_delta = curr_arr - prev_arr
            MOD = getattr(self, "_counter_modulus", _COUNTER_MODULUS)
            wrap_threshold = MOD - 64
            is_wrap = (raw_delta < 0) & (prev_arr >= wrap_threshold)
            wrap_delta = (MOD - prev_arr) + curr_arr
            reset_delta = curr_arr
            delta = np.where(raw_delta >= 0, raw_delta, np.where(is_wrap, wrap_delta, reset_delta))
            return curr_arr, acc_arr + delta
        except Exception:
            return curr_arr, curr_arr.copy()


if __name__ == "__main__":
    import sys
    from types import SimpleNamespace

    from dark_pro_widgets import qss, theme

    from app.src.components.log.config import log_init
    from app.widgets.oscilloscope.flux_widget import FluxWidget

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())

    # Циклы измерения — асинхронные, без qasync кнопка запуска не сработает
    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    logger = log_init()

    # Панель обращается к графикам, счётчику и связи, поэтому конструктору нужен
    # «родитель» с ними. В окне показываем только саму панель — виджеты-зависимости
    # создаются рядом и остаются невидимыми.
    host_parent = SimpleNamespace(
        w_graph_widget=GraphWidget(),
        flux_widget=FluxWidget(),
        w_ser_dialog=ConnectionBar(logger),
        logger=logger,
        shared_bfr_update_event=Event(str),
    )
    widget = RunControlWidget(host_parent)

    host = QtWidgets.QWidget()
    host.setWindowTitle("Меню запуска — автономный запуск")
    host.setStyleSheet(f"background-color: {theme.BG};")
    layout = QtWidgets.QVBoxLayout(host)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.addWidget(widget)
    layout.addStretch()

    host.resize(328, 420)
    host.show()

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
