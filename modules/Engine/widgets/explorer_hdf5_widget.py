import asyncio
import struct
import sys
# from save_config import ConfigSaver
from pathlib import Path
from typing import Optional, Sequence, Callable, Union, Dict, Awaitable

import numpy as np
import qasync
import qtmodern.styles
from pymodbus.client import AsyncModbusSerialClient
from PyQt6 import QtCore, QtWidgets
from qtpy.uic import loadUi

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QTreeView, QSplitter, QLabel,
                             QFileDialog, QMessageBox, QPushButton)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt, QDir, QModelIndex, QAbstractItemModel
import h5py
import os
import time


####### импорты из других директорий ######
# /src
src_path = Path(__file__).resolve().parent.parent.parent.parent
modules_path = Path(__file__).resolve().parent.parent.parent
# Добавляем папку src в sys.path
sys.path.append(str(src_path))
sys.path.append(str(modules_path))

from modules.Engine.widgets.graph_widget import GraphWidget  # noqa: E402
from modules.Main_Serial.main_serial_dialog import SerialConnect  # noqa: E402
from src.async_task_manager import AsyncTaskManager  # noqa: E402
from src.ddii_command import ModbusCMCommand, ModbusMPPCommand  # noqa: E402
from src.modbus_worker import ModbusWorker  # noqa: E402
from src.parsers import Parsers  # noqa: E402
from src.print_logger import PrintLogger  # noqa: E402


class ExplorerHDF5Widget(QtWidgets.QDialog):
    lineEdit_path_edit                    : QtWidgets.QLineEdit
    pushButton_back                       : QtWidgets.QPushButton
    pushButton_browser                    : QtWidgets.QPushButton
    pushButton_close_hdf5                 : QtWidgets.QPushButton
    pushButton_next                       : QtWidgets.QPushButton
    columnView_explorer                   : QtWidgets.QColumnView

    def __init__(self, *args) -> None:
        super().__init__()
        self.parent = args[0]
        loadUi(Path(__file__).parent.joinpath('explorer_hdf5_widget.ui'), self)
        self.mw = ModbusWorker()
        self.parser = Parsers()
        self.hdf5_model = HDF5TreeModel()
        self.fs_model = QFileSystemModel()
        self.fs_model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)
        self.current_model = None
        self.current_folder = os.path.expanduser("~")  # Начинаем с домашней директории

    def init_widgets(self) -> None:
        self.lineEdit_path_edit.setPlaceholderText("Current folder path...")
        self.lineEdit_path_edit.returnPressed.connect(self.navigate_to_path)

    def navigate_to_path(self):
        """Переход по указанному пути"""
        path = self.lineEdit_path_edit.text()
        if os.path.exists(path):
            self.load_folder(path)
        else:
            QMessageBox.warning(self, "Path Error", "The specified path does not exist")

    def load_folder(self, folder_path):
        """Загружает папку в файловую модель"""
        if not os.path.isdir(folder_path):
            return
            
        self.current_folder = folder_path
        self.lineEdit_path_edit.setText(folder_path)
        
        self.fs_model.setRootPath(folder_path)
        self.tree_view.setModel(self.fs_model)
        self.tree_view.setRootIndex(self.fs_model.index(folder_path))
        self.current_model = "fs"
        
        # Очищаем область просмотра
        self.content_view.setText(f"Folder contents: {folder_path}\n\nDouble-click on HDF5 files to open them.")

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
                
            self.hdf5_file = h5py.File(file_path, 'r')
            self.file_path = file_path
            
            self.root_item = {
                "name": os.path.basename(file_path),
                "path": "/",
                "item": self.hdf5_file,
                "parent": None,
                "children": []
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
            child = {
                "name": name,
                "path": child_path,
                "item": item,
                "parent": parent_item,
                "children": []
            }
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