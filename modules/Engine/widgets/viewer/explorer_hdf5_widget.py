import asyncio
import os
import struct
import sys
import time

# from save_config import ConfigSaver
from pathlib import Path
from typing import Awaitable, Callable, Dict, Optional, Sequence, Union

import h5py
import numpy as np
import qasync
import qtmodern.styles
from pymodbus.client import AsyncModbusSerialClient
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import QAbstractItemModel, QDir, QModelIndex, Qt
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from qtmodern.windows import ModernWindow
from qtpy.uic import loadUi

####### импорты из других директорий ######
# /src
if __name__ != "__main__":
    src_path = Path(__file__).resolve().parents[4]
    modules_path = Path(__file__).resolve().parents[3]
else:
    src_path = Path(__file__).resolve().parents[4]
    modules_path = Path(__file__).resolve().parents[3]
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

# from modules.Engine.widgets.oscilloscope.graph_widget import GraphWidget  # noqa: E402
# from modules.Main_Serial.main_serial_dialog import SerialConnect  # noqa: E402
# from src.async_task_manager import AsyncTaskManager  # noqa: E402
# from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
# from src.modbus_worker import ModbusWorker  # noqa: E402
# from src.parsers import Parsers  # noqa: E402
# from src.print_logger import PrintLogger  # noqa: E402
from src.event.event import Event  # noqa: E402



class ExplorerHDF5Widget(QtWidgets.QDialog):
    lineEdit_path_edit: QtWidgets.QLineEdit
    pushButton_back: QtWidgets.QPushButton
    pushButton_browser: QtWidgets.QPushButton
    pushButton_close_hdf5: QtWidgets.QPushButton
    pushButton_next: QtWidgets.QPushButton
    columnView_explorer: QtWidgets.QColumnView
    treeView_file_tree: QtWidgets.QTreeView

    def __init__(self, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath("explorer_hdf5_widget.ui"), self)
        self.history = []
        self.history_index = -1
        self.double_clicked_event = Event(str)
        if __name__ != "__main__":
            self.parent = args[0]
        # self.hdf5_model = HDF5TreeModel()
        self.fs_model = QFileSystemModel()
        self.fs_model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)
        self.current_model = None
        self.current_folder = str(
            Path(__file__).parents[4].joinpath("log/output_graph_data")
        )  # Начинаем с домашней директории
        self.load_folder(self.current_folder)
        self.init_widget()

    def init_widget(self):
        self.treeView_file_tree.setHeaderHidden(False)
        self.treeView_file_tree.hideColumn(2)
        self.treeView_file_tree.setColumnWidth(0, 200)
        self.treeView_file_tree.resizeColumnToContents(2)
        self.treeView_file_tree.doubleClicked.connect(self.on_item_double_clicked)
        self.lineEdit_path_edit.setPlaceholderText("Current folder path...")
        self.lineEdit_path_edit.returnPressed.connect(self.navigate_to_path)
        self.pushButton_back.clicked.connect(self.navigate_back)

    def navigate_to_path(self):
        path = self.lineEdit_path_edit.text()
        if os.path.exists(path):
            self.load_folder(path)
        else:
            QMessageBox.warning(self, "Path Error", "The specified path does not exist")

    def navigate_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.load_folder(self.history[self.history_index], add_to_history=False)

    def on_item_double_clicked(self, index):
        if not index.isValid():
            return
        # if self.current_model == "hdf5":
        #     item = index.internalPointer()
        #     h5_item = item["item"]

        elif self.current_model == "fs":
            path = self.fs_model.filePath(index)

            if os.path.isdir(path):
                self.load_folder(path)
            elif os.path.isfile(path) and (path.lower().endswith(".hdf5") or path.lower().endswith(".h5")):
                # self.load_hdf5_file(path)
                self.double_clicked_event.emit(path)

    def load_folder(self, folder_path, add_to_history=True):
        if not os.path.isdir(folder_path):
            return

        self.current_folder = folder_path
        self.lineEdit_path_edit.setText(folder_path)

        if add_to_history:
            self.history = self.history[: self.history_index + 1]
            self.history.append(folder_path)
            self.history_index += 1
            # Обновляем кнопки навигации, если они есть
            # self.back_button.setEnabled(self.history_index > 0)
            # self.forward_button.setEnabled(self.history_index < len(self.history) - 1)

        self.fs_model.setRootPath(folder_path)
        self.treeView_file_tree.setModel(self.fs_model)
        self.treeView_file_tree.setRootIndex(self.fs_model.index(folder_path))
        self.current_model = "fs"

    # def load_hdf5_file(self, file_path):
        # if self.hdf5_model.load_hdf5(file_path):
        #     folder_path = os.path.dirname(file_path)
        #     self.lineEdit_path_edit.setText(folder_path)
        #     self.current_folder = folder_path

            # self.treeView_file_tree.setModel(self.hdf5_model)
            # self.current_model = "hdf5"
            # self.treeView_file_tree.expandAll()


class HDF5TreeModel(QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_item = {"name": "Root", "path": "", "item": None, "parent": None, "children": []}
        self.hdf5_file = None
        self.file_path = ""

    def load_hdf5(self, file_path):
        try:
            if self.hdf5_file:
                self.hdf5_file.close()

            self.hdf5_file = h5py.File(file_path, "r")
            self.file_path = file_path

            self.root_item = {
                "name": os.path.basename(file_path),
                "path": "/",
                "item": self.hdf5_file,
                "parent": None,
                "children": [],
            }

            self.beginResetModel()
            self._populate_children(self.root_item)
            self.endResetModel()
            return True
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to open HDF5 file: {str(e)}")
            return False

    def _populate_children(self, parent_item):
        if not isinstance(parent_item["item"], h5py.Group):
            return

        for name, item in parent_item["item"].items():
            child_path = parent_item["path"] + "/" + name if parent_item["path"] != "/" else "/" + name
            child = {"name": name, "path": child_path, "item": item, "parent": parent_item, "children": []}
            parent_item["children"].append(child)

            if isinstance(item, h5py.Group):
                self._populate_children(child)

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()

        if row < len(parent_item["children"]):
            child_item = parent_item["children"][row]
            return self.createIndex(row, column, child_item)

        return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item["parent"]

        if parent_item is None or parent_item == self.root_item:
            return QModelIndex()

        grandparent = parent_item["parent"]
        if grandparent is None:
            return QModelIndex()

        row = grandparent["children"].index(parent_item)
        return self.createIndex(row, 0, parent_item)

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()

        return len(parent_item["children"])

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == Qt.ItemDataRole.DisplayRole:
            return item["name"]

        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return "HDF5 Structure"
        return None

    def hasChildren(self, parent=QModelIndex()):
        if not parent.isValid():
            return True

        item = parent.internalPointer()
        return len(item["children"]) > 0

    def close_file(self):
        if self.hdf5_file is not None:
            self.hdf5_file.close()
            self.hdf5_file = None
            self.beginResetModel()
            self.root_item = {"name": "Root", "path": "", "item": None, "parent": None, "children": []}
            self.endResetModel()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    w: ExplorerHDF5Widget = ExplorerHDF5Widget()
    mw: ModernWindow = ModernWindow(w)
    mw.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, False)  # fix flickering on resize window
    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    mw.show()

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
