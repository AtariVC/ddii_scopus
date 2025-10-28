import asyncio
import re
import sys
from dataclasses import dataclass

# from save_config import ConfigSaver
from pathlib import Path
import qasync
import qtmodern.styles
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QIntValidator
from qtpy.uic import loadUi
from src.log_config import get_logger
from modules.Main.widgets.viewer.explorer_hdf5_widget import ExplorerHDF5Widget
####### импорты из других директорий ######
# /src

src_path = Path(__file__).resolve().parents[4]
# modules_path = Path(__file__).resolve().parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
# sys.path.append(str(modules_path))

# from src.modbus_worker import ModbusWorker                          # noqa: E402
# from src.ddii_command import ModbusCMCommand, ModbusMPPCommand      # noqa: E402
# from src.parsers import  Parsers                                    # noqa: E402
# from modules.Main_Serial.main_serial_dialog_tcp import SerialConnect    # noqa: E402
# from src.log_config import log_init, log_s                          # noqa: E402
# from src.parsers_pack import LineEObj, LineEditPack                 # noqa: E402
from src.event.event import Event  # noqa: E402
from src.plot_renderer import GraphPen, HistPen  # noqa: E402
from src.write_data_to_file import read_hdf5_file  # noqa: E402


class GraphViewerWidget(QtWidgets.QWidget):
    verticalLayout_graph: QtWidgets.QVBoxLayout
    vLayout_hist_EdE: QtWidgets.QVBoxLayout
    vLayout_hist_pips: QtWidgets.QVBoxLayout
    vLayout_hist_sipm: QtWidgets.QVBoxLayout
    vLayout_hist_counter: QtWidgets.QVBoxLayout
    vLayout_pips: QtWidgets.QVBoxLayout
    vLayout_sipm: QtWidgets.QVBoxLayout
    label_counter_data: QtWidgets.QLabel
    label_time_data: QtWidgets.QLabel
    horizontalSlider_time_scale: QtWidgets.QSlider

    def __init__(self, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath("graph_viewer_widget.ui"), self)
        self.pen_init()
        if __name__ != "__main__":
            self.parent = args[0]
            self.explorer: ExplorerHDF5Widget = self.parent.explorer_hdf5_widget # type: ignore
            self.explorer.double_clicked_event.subscribe(self.open_graphs)
            self.horizontalSlider_time_scale.actionTriggered.connect(lambda: self.slider_graphs_updater())
        # UI for frame filtering/navigation
        self._init_filter_ui()

    def pen_init(self) -> None:
        self.task = None  # type: ignore
        self.name_pen_pips = "pips"
        self.name_pen_sipm = "sipm"
        self.name_pen_h_pips = "h_pips"
        self.name_pen_h_sipm = "h_sipm"
        self.name_pen_counter = "h_counter"
        self.amount_measurements = 0
        self.measure_time_list = []
        self.dataset_pips: dict = {}
        self.dataset_sipm: dict = {}
        self.dataset_h_pips: dict = {}
        self.dataset_h_sipm: dict = {}
        self.gp_pips = GraphPen(layout=self.vLayout_pips, name=self.name_pen_pips, color=(255, 255, 0))
        self.gp_sipm = GraphPen(layout=self.vLayout_sipm, name=self.name_pen_sipm, color=(0, 255, 255))
        self.hp_pips = HistPen(layout=self.vLayout_hist_pips, name=self.name_pen_h_pips, color=(255, 0, 0, 150))
        self.hp_sipm = HistPen(layout=self.vLayout_hist_sipm, name=self.name_pen_h_sipm, color=(0, 0, 255, 150))
        self.counter_h = HistPen(
            layout=self.vLayout_hist_counter, name=self.name_pen_counter, color=(123, 195, 121, 150)
        )
        # Storage for filtered frames
        self._matched_indices: list[int] = []  # 1-based indices to match slider API
        self._matched_times: list[str] = []
        self._match_pos: int = -1

    def open_graphs(self, path: str) -> None:
        """Открывает графики из файла"""
        self.horizontalSlider_time_scale.setValue(0)
        self.dataset_pips = read_hdf5_file(Path(path), self.name_pen_pips)
        self.dataset_sipm = read_hdf5_file(Path(path), self.name_pen_sipm)
        self.dataset_h_pips = read_hdf5_file(Path(path), self.name_pen_h_pips)
        self.dataset_h_sipm = read_hdf5_file(Path(path), self.name_pen_h_sipm)
        self.dataset_h_counter = read_hdf5_file(Path(path), self.name_pen_counter)
        self.amount_measurements = len(self.dataset_pips)
        self.measure_time_list = list(self.dataset_pips.keys())
        time_str = self.time_formater(self.measure_time_list[0])
        self.label_time_data.setText(f"{time_str}")
        self.horizontalSlider_time_scale.setMaximum(self.amount_measurements)
        self.label_counter_data.setText(f"{self.horizontalSlider_time_scale.value()}/{self.amount_measurements}")
        # Reset filter UI on new file
        self._clear_filter_results()

    def time_formater(self, input_time_str: str) -> str:
        """Преобразует строку вида "2024-10-08_17-52-54-261" в формат "Время: 08.10.24 17:52:54:2610"
        Args:
            input_time_str (str): Строка времени в формате "2024-10-08_17-52-54-261"
        Returns:
            str: Преобразованная строка времени в формате "Время: 08.10.24 17
        """
        # Извлекаем компоненты даты и времени
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})-(\d{3})", input_time_str)
        if match:
            year, month, day, hour, minute, second, millis = match.groups()
            output_str = f"Время: {day}.{month}.{year[-2:]} {hour}:{minute}:{second}:{millis}0"
            return output_str
        else:
            return "Время: неверный формат"

    @qasync.asyncSlot()
    async def slider_graphs_updater(self) -> None:
        """Обновляет графики при изменении слайдера"""
        logger = get_logger()
        if self.amount_measurements == 0:
            return
        try:
            current_val = self.horizontalSlider_time_scale.value()
            self.label_counter_data.setText(f"{current_val-1}/{self.amount_measurements-1}")
            time_str = self.time_formater(self.measure_time_list[current_val - 1])
            self.label_time_data.setText(f"{time_str}")
            if self.dataset_pips:
                data_pips = list(self.dataset_pips.values())[current_val-1].T
                await self.gp_pips.draw_graph(data_pips[1], clear=True)
            else:
                self.gp_pips.plt_widget.clear()
            if self.dataset_sipm:
                data_sipm = list(self.dataset_sipm.values())[current_val-1].T
                await self.gp_sipm.draw_graph(data_sipm[1], clear=True)
            else:
                self.gp_sipm.plt_widget.clear()
            if self.dataset_h_pips:
                data_h_pips = list(self.dataset_h_pips.values())[current_val-1].T
                await self.hp_pips.draw_hist(data_h_pips[1].tolist(), clear=True, data_is_hist=True)
            else:
                self.hp_pips.hist_clear()
            if self.dataset_h_sipm:
                data_h_sipm = list(self.dataset_h_sipm.values())[current_val-1].T
                await self.hp_sipm.draw_hist(data_h_sipm[1].tolist(), clear=True, data_is_hist=True)
            else:
                self.hp_sipm.hist_clear()
            if self.dataset_h_counter:
                data_h_counter = list(self.dataset_h_counter.values())[current_val // len(self.dataset_h_counter.values())].T
                await self.counter_h.draw_hist(data_h_counter[1].tolist(), clear=True, data_is_hist=True)
            else:
                self.counter_h.hist_clear()
            # await self.hp_pips.draw_hist(data_pips[1], clear=True)
            # await self.hp_sipm.draw_hist(data_sipm[1], clear=True)
        except Exception as ex:
            logger.error(ex)

        # if value < self.amount_measurements:

        # data_pips = self.gp_pips.get_data(value)
        # data_sipm = self.gp_sipm.get_data(value)
        # self.gp_pips.draw_graph(data_pips, "pips", clear=True)
        # self.gp_sipm.draw_graph(data_sipm, "sipm", clear=True)
        # self.hp_pips.draw_histogram(data_pips, "h_pips", clear=True)
        # self.hp_sipm.draw_histogram(data_sipm, "h_sipm", clear=True)

    def _init_filter_ui(self) -> None:
        """Create filter controls and insert into main layout above the slider."""
        try:
            # Controls
            self.groupBox_filter = QtWidgets.QGroupBox("Фильтр кадров")
            h = QtWidgets.QHBoxLayout(self.groupBox_filter)
            self.checkBox_filter_pips = QtWidgets.QCheckBox("PIPS")
            self.checkBox_filter_pips.setChecked(True)
            self.checkBox_filter_sipm = QtWidgets.QCheckBox("SiPM")
            self.checkBox_filter_sipm.setChecked(True)
            self.lineEdit_filter_level = QtWidgets.QLineEdit()
            self.lineEdit_filter_level.setPlaceholderText("Порог…")
            self.lineEdit_filter_level.setFixedWidth(80)
            self.lineEdit_filter_level.setValidator(QIntValidator(0, 10_000, self))
            self.pushButton_apply_filter = QtWidgets.QPushButton("Фильтровать")
            self.pushButton_prev_match = QtWidgets.QPushButton("<")
            self.pushButton_next_match = QtWidgets.QPushButton(">")
            self.lineEdit_matched_frames = QtWidgets.QLineEdit()
            self.lineEdit_matched_frames.setPlaceholderText("Номера кадров…")
            self.lineEdit_matched_frames.setReadOnly(True)
            self.listWidget_matched_times = QtWidgets.QListWidget()
            self.listWidget_matched_times.setMaximumHeight(80)
            self.listWidget_matched_times.itemClicked.connect(self._on_time_item_clicked)

            for w in (
                QtWidgets.QLabel("Порог:"),
                self.lineEdit_filter_level,
                self.checkBox_filter_pips,
                self.checkBox_filter_sipm,
                self.pushButton_apply_filter,
                self.pushButton_prev_match,
                self.pushButton_next_match,
                self.lineEdit_matched_frames,
            ):
                h.addWidget(w)

            # Wire actions
            self.pushButton_apply_filter.clicked.connect(self._apply_filter)
            self.pushButton_prev_match.clicked.connect(lambda: self._step_match(-1))
            self.pushButton_next_match.clicked.connect(lambda: self._step_match(+1))

            # Insert into layout above slider
            try:
                # insert before slider (second item from the end is slider)
                idx = max(0, self.verticalLayout_graph.count() - 2)
                self.verticalLayout_graph.insertWidget(idx, self.groupBox_filter)
                self.verticalLayout_graph.insertWidget(idx + 1, self.listWidget_matched_times)
            except Exception:
                # Fallback: append at end
                self.verticalLayout_graph.addWidget(self.groupBox_filter)
                self.verticalLayout_graph.addWidget(self.listWidget_matched_times)
        except Exception:
            ...

    def _clear_filter_results(self):
        self._matched_indices = []
        self._matched_times = []
        self._match_pos = -1
        try:
            self.lineEdit_matched_frames.setText("")
            self.listWidget_matched_times.clear()
        except Exception:
            ...

    def _apply_filter(self):
        if self.amount_measurements == 0 or not self.dataset_pips:
            self._clear_filter_results()
            return
        try:
            lvl = int(self.lineEdit_filter_level.text()) if self.lineEdit_filter_level.text() else 0
        except Exception:
            lvl = 0
        use_pips = self.checkBox_filter_pips.isChecked()
        use_sipm = self.checkBox_filter_sipm.isChecked()
        if not (use_pips or use_sipm):
            self._clear_filter_results()
            return

        matched_idx: list[int] = []
        matched_times: list[str] = []
        # Iterate 1..N to match slider indexing
        for i in range(1, self.amount_measurements + 1):
            ok = False
            if use_pips and self.dataset_pips:
                try:
                    arr = list(self.dataset_pips.values())[i - 1].T[1]
                    if len(arr) and max(arr) > lvl:
                        ok = True
                except Exception:
                    ...
            if not ok and use_sipm and self.dataset_sipm:
                try:
                    arr = list(self.dataset_sipm.values())[i - 1].T[1]
                    if len(arr) and max(arr) > lvl:
                        ok = True
                except Exception:
                    ...
            if ok:
                matched_idx.append(i)
                matched_times.append(self.time_formater(self.measure_time_list[i - 1]))

        self._matched_indices = matched_idx
        self._matched_times = matched_times
        self._match_pos = 0 if matched_idx else -1
        # Update UI
        try:
            self.lineEdit_matched_frames.setText(", ".join(map(str, matched_idx)))
            self.listWidget_matched_times.clear()
            for i, t in zip(matched_idx, matched_times):
                self.listWidget_matched_times.addItem(f"{i}: {t}")
        except Exception:
            ...
        # Jump to first match
        if self._match_pos != -1:
            self._goto_match(self._match_pos)

    def _step_match(self, step: int):
        if not self._matched_indices:
            return
        self._match_pos = max(0, min(len(self._matched_indices) - 1, self._match_pos + step))
        self._goto_match(self._match_pos)

    def _goto_match(self, pos: int):
        try:
            idx = self._matched_indices[pos]
            # Update slider and graphs
            self.horizontalSlider_time_scale.setValue(idx)
            # Trigger update explicitly
            self.slider_graphs_updater()
            # Highlight item
            try:
                self.listWidget_matched_times.setCurrentRow(pos)
            except Exception:
                ...
        except Exception:
            ...

    def _on_time_item_clicked(self, item: QtWidgets.QListWidgetItem):
        try:
            row = self.listWidget_matched_times.currentRow()
            if 0 <= row < len(self._matched_indices):
                self._match_pos = row
                self._goto_match(row)
        except Exception:
            ...


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    w: GraphViewerWidget = GraphViewerWidget()
    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    w.show()
    data: list = [1, 34.34, 324.4, 32.4, 89.4, 233.4, 234.4, 2344.4, 234.4]
    w.gp_pips.draw_graph(data, "test", clear=False)  # type: ignore
    data1: list[int] = [1, 34, 45, 435, 234, 234, 2344, 234, 23423, 324, 324234]
    w.gp_sipm.draw_graph(data1, "test", clear=False)  # type: ignore

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
