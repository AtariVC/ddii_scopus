import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QTreeView, QSplitter, QLabel,
                             QFileDialog, QMessageBox, QPushButton, 
                             QTableView, QHeaderView)
from PyQt6.QtGui import QFileSystemModel, QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, QDir, QModelIndex, QAbstractItemModel, QFileInfo
import h5py
import os
import time


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


class HDF5Explorer(QWidget):
    def __init__(self):
        super().__init__()
        self.hdf5_model = HDF5TreeModel()
        self.fs_model = QFileSystemModel()
        self.fs_model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)
        self.table_model = QStandardItemModel()
        self.current_model = None
        self.current_folder = os.path.expanduser("~")
        self.history = []
        self.history_index = -1
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('HDF5 Explorer')
        self.setAcceptDrops(True)
        self.resize(1200, 800)

        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Path navigation
        path_layout = QHBoxLayout()
        
        self.back_button = QPushButton("←")
        self.back_button.setFixedWidth(40)
        self.back_button.clicked.connect(self.navigate_back)
        path_layout.addWidget(self.back_button)
        
        self.forward_button = QPushButton("→")
        self.forward_button.setFixedWidth(40)
        self.forward_button.setEnabled(False)
        path_layout.addWidget(self.forward_button)
        
        self.up_button = QPushButton("↑")
        self.up_button.setFixedWidth(40)
        self.up_button.clicked.connect(self.navigate_up)
        path_layout.addWidget(self.up_button)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Current folder path...")
        self.path_edit.returnPressed.connect(self.navigate_to_path)
        path_layout.addWidget(self.path_edit, 5)
        
        self.refresh_button = QPushButton("↻")
        self.refresh_button.setFixedWidth(40)
        self.refresh_button.clicked.connect(self.refresh_view)
        path_layout.addWidget(self.refresh_button)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_folder)
        path_layout.addWidget(self.browse_button)
        
        main_layout.addLayout(path_layout)

        # Splitter for views
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel with tree and table
        left_panel = QSplitter(Qt.Orientation.Vertical)
        
        # Tree view
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.doubleClicked.connect(self.on_item_double_clicked)
        left_panel.addWidget(self.tree_view)
        
        # Table view
        self.tableView = QTableView()
        self.tableView.setModel(self.table_model)
        
        # Configure table header after model is set
        header = self.tableView.horizontalHeader()
        if header:  # Проверяем, что заголовок существует
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionsMovable(True)
        
        left_panel.addWidget(self.tableView)
        left_panel.setSizes([400, 300])
        splitter.addWidget(left_panel)

        # Content view
        self.content_view = QLabel()
        self.content_view.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.content_view.setWordWrap(True)
        self.content_view.setStyleSheet("""
            padding: 15px; 
            background-color: #f8f8f8; 
            font-family: monospace;
            border: 1px solid #ddd;
        """)
        splitter.addWidget(self.content_view)

        splitter.setSizes([500, 700])
        main_layout.addWidget(splitter, 1)
        
        # Initial load
        self.load_folder(self.current_folder)

    def populate_table_view(self, folder_path):
        """Fill table with folder contents"""
        self.table_model.clear()
        self.table_model.setHorizontalHeaderLabels(["Name", "Size", "Modified", "Type"])
        
        try:
            for item in sorted(os.listdir(folder_path)):
                full_path = os.path.join(folder_path, item)
                file_info = QFileInfo(full_path)
                
                # Name
                name_item = QStandardItem(item)
                name_item.setEditable(False)
                
                # Size
                size = file_info.size()
                size_item = QStandardItem(self.format_size(size))
                size_item.setEditable(False)
                
                # Modified date
                modified = file_info.lastModified().toString("yyyy-MM-dd HH:mm:ss")
                modified_item = QStandardItem(modified)
                modified_item.setEditable(False)
                
                # Type
                file_type = "Folder" if file_info.isDir() else file_info.suffix().upper() + " File"
                type_item = QStandardItem(file_type)
                type_item.setEditable(False)
                
                self.table_model.appendRow([name_item, size_item, modified_item, type_item])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not read directory: {str(e)}")

    def format_size(self, size):
        """Format file size in human-readable format"""
        if size == 0:
            return "0 B"
            
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", self.current_folder)
        if folder:
            self.load_folder(folder)

    def navigate_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.load_folder(self.history[self.history_index], add_to_history=False)

    def navigate_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.load_folder(self.history[self.history_index], add_to_history=False)

    def navigate_up(self):
        parent = os.path.dirname(self.current_folder)
        if parent != self.current_folder:
            self.load_folder(parent)

    def navigate_to_path(self):
        path = self.path_edit.text()
        if os.path.exists(path):
            self.load_folder(path)
        else:
            QMessageBox.warning(self, "Path Error", "The specified path does not exist")

    def refresh_view(self):
        self.load_folder(self.current_folder)

    def load_folder(self, folder_path, add_to_history=True):
        if not os.path.isdir(folder_path):
            return
            
        self.current_folder = folder_path
        self.path_edit.setText(folder_path)
        
        if add_to_history:
            self.history = self.history[:self.history_index+1]
            self.history.append(folder_path)
            self.history_index += 1
            self.back_button.setEnabled(self.history_index > 0)
            self.forward_button.setEnabled(self.history_index < len(self.history) - 1)
        
        self.fs_model.setRootPath(folder_path)
        self.tree_view.setModel(self.fs_model)
        self.tree_view.setRootIndex(self.fs_model.index(folder_path))
        self.current_model = "fs"
        
        self.populate_table_view(folder_path)
        self.content_view.setText(f"Folder: {folder_path}")

    def load_hdf5_file(self, file_path):
        if self.hdf5_model.load_hdf5(file_path):
            folder_path = os.path.dirname(file_path)
            self.path_edit.setText(folder_path)
            self.current_folder = folder_path
            
            self.tree_view.setModel(self.hdf5_model)
            self.current_model = "hdf5"
            self.tree_view.expandAll()
            
            self.table_model.clear()
            self.table_model.setHorizontalHeaderLabels(["HDF5 File Contents"])
            
            self.content_view.setText(f"HDF5 file: {os.path.basename(file_path)}")

    def on_item_double_clicked(self, index):
        if not index.isValid():
            return
            
        if self.current_model == "hdf5":
            item = index.internalPointer()
            h5_item = item["item"]
            
            content = ""
            if isinstance(h5_item, h5py.Group):
                content = f"Group: {item['path']}\n\nContents:\n"
                for name in h5_item:
                    content += f"{name}\n"
            elif isinstance(h5_item, h5py.Dataset):
                content = f"Dataset: {item['path']}\n\n"
                content += f"Shape: {h5_item.shape}\n"
                content += f"Dtype: {h5_item.dtype}\n\n"
                if h5_item.size <= 100:
                    content += f"Data:\n{h5_item[()]}"
                else:
                    content += "First 10 elements:\n"
                    content += str(h5_item[:10])
            
            self.content_view.setText(content)
        
        elif self.current_model == "fs":
            path = self.fs_model.filePath(index)
            
            if os.path.isdir(path):
                self.load_folder(path)
            elif os.path.isfile(path) and (path.lower().endswith('.hdf5') or path.lower().endswith('.h5')):
                self.load_hdf5_file(path)
            else:
                try:
                    content = f"File: {os.path.basename(path)}\n"
                    content += f"Size: {os.path.getsize(path)} bytes\n"
                    content += f"Modified: {time.ctime(os.path.getmtime(path))}\n\n"
                    
                    if os.path.getsize(path) < 1000000:
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                preview = f.read(1000)
                                content += f"Preview:\n{preview}"
                                if len(preview) == 1000:
                                    content += "\n... (truncated)"
                        except:
                            pass
                    
                    self.content_view.setText(content)
                except Exception as e:
                    self.content_view.setText(f"Error reading file: {str(e)}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            
            if os.path.isfile(path) and (path.lower().endswith('.hdf5') or path.lower().endswith('.h5')):
                self.load_hdf5_file(path)
            elif os.path.isdir(path):
                self.load_folder(path)
            else:
                QMessageBox.warning(self, "Unsupported", "Only HDF5 files and folders are supported")

    def closeEvent(self, event):
        self.hdf5_model.close_file()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    explorer = HDF5Explorer()
    explorer.show()
    sys.exit(app.exec())