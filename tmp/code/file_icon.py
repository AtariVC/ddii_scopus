import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTreeView, QFileIconProvider
from PyQt6.QtGui import QIcon, QFileSystemModel
from PyQt6.QtCore import QDir


class CustomIconProvider(QFileIconProvider):
    def __init__(self):
        super().__init__()
        # Подгружаем иконки из файлов напрямую
        self.icons = {
            "hdf5": QIcon("icon/HDF_logo_(2017).svg"),
            "py": QIcon("icon/python-svgrepo-com.svg"),
            # "gif": QIcon("icons/image.png"),
            # "txt": QIcon("icons/text.png"),
            # "md": QIcon("icons/text.png"),
            # "log": QIcon("icons/text.png"),
            # "zip": QIcon("icons/archive.png"),
            # "rar": QIcon("icons/archive.png"),
            # "tar": QIcon("icons/archive.png"),
            # "gz": QIcon("icons/archive.png"),
            # "exe": QIcon("icons/executable.png"),
            # "sh": QIcon("icons/executable.png"),
            # "bat": QIcon("icons/executable.png"),
        }

    def icon(self, file_info):
        if file_info.isFile():
            ext = file_info.suffix().lower()
            icon = self.icons.get(ext)
            if icon and not icon.isNull():
                return icon
        return super().icon(file_info)


class FileExplorer(QWidget):
    def __init__(self):
        super().__init__()

        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)
        self.model.setIconProvider(CustomIconProvider())

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(QDir.homePath()))

        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        self.setLayout(layout)
        self.setWindowTitle("File Explorer with Icons")
        self.resize(800, 600)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileExplorer()
    window.show()
    sys.exit(app.exec())