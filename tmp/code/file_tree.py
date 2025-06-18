from dataclasses import dataclass
from pathlib import Path
from typing_extensions import override
from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtGui import QEnterEvent, QIcon
from PyQt6.QtWidgets import QTreeWidgetItem, QTreeWidget, QApplication

class ItemDelegate(QtWidgets.QItemDelegate):
    editing_finished = QtCore.pyqtSignal(QtCore.QModelIndex)
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.line_edit: QtWidgets.QLineEdit | None = None

    @override
    def setModelData(self, editor: QtWidgets.QWidget | None,
                     model: QtCore.QAbstractItemModel | None,
                     index: QtCore.QModelIndex) -> None:
        super().setModelData(editor, model, index)
        if index.column() == 0:
            self.editing_finished.emit(index)
        return None

    @override
    def setEditorData(self, editor: QtWidgets.QWidget | None,
                      index: QtCore.QModelIndex) -> None:
        if editor and isinstance(editor, QtWidgets.QLineEdit):
            self.line_edit = editor
            self.last_index = index
        return super().setEditorData(editor, index)

    @override
    def eventFilter(self, object: QtCore.QObject | None,
                    event: QtCore.QEvent | None) -> bool:
        if self.line_edit and event:
            event_type = event.type()
            if object == self.line_edit and event_type == QtCore.QEvent.Type.KeyPress:
                if event.key() == QtCore.Qt.Key.Key_Escape:  # type: ignore
                    self.editing_finished.emit(self.last_index)
        return super().eventFilter(object, event)

model = {
  "label": "admin",
  "key": "admin",
  "node_type": "root",
  "children": [
    {
      "label": "folder",
      "key": "admin/folder",
      "node_type": "folder"
    },
    {
      "label": "test2",
      "key": "admin/test2",
      "node_type": "folder",
      "children": [
        {
          "label": "file.txt",
          "key": "admin/test2/file.txt",
          "node_type": "file",
          "file_id": "fa86c6be-7281-40bc-86ab-5f5c882b8c05"
        }
      ]
    },
    {
      "label": "test.py",
      "key": "admin/test.py",
      "node_type": "file",
      "file_id": "6eff228b-e5e6-496f-a5f0-cbcbbde9cc37"
    }
  ]
}

icon_path: Path = Path(__file__).parents[2].joinpath('icon')

class HeaderButtons:
    def __init__(self) -> None:
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 10, 0)
        self.file_btn = QtWidgets.QPushButton()
        self.folder_btn = QtWidgets.QPushButton()
        self.update_btn = QtWidgets.QPushButton()
        self.collapse_btn = QtWidgets.QPushButton()
        self.file_btn.setFlat(True)
        self.folder_btn.setFlat(True)
        self.update_btn.setFlat(True)
        self.collapse_btn.setFlat(True)

        self.file_btn.setIcon(QIcon(str(icon_path.joinpath('start.svg'))))
        self.folder_btn.setIcon(QIcon(str(icon_path.joinpath('start.svg'))))
        self.update_btn.setIcon(QIcon(str(icon_path.joinpath('start.svg'))))
        self.collapse_btn.setIcon(QIcon(str(icon_path.joinpath('start.svg'))))
        self.layout.addWidget(self.file_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.layout.addWidget(self.folder_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.layout.addWidget(self.update_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.layout.addWidget(self.collapse_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.layout.setStretch(0, 1)

@dataclass
class FileModel:
    label: str
    icon: QtGui.QIcon
    file_id: str
    key: str

class FileTree(QtWidgets.QTreeWidget):
    new_file = QtCore.pyqtSignal(str, str)
    new_folder = QtCore.pyqtSignal(str, str)
    update_tree = QtCore.pyqtSignal()
    file_selected: QtCore.pyqtSignal = QtCore.pyqtSignal(FileModel)
    delete_item = QtCore.pyqtSignal(str, QtWidgets.QTreeWidgetItem)
    def __init__(self) -> None:
        super().__init__()
        self.itemExpanded.connect(self.on_expand)
        self.itemCollapsed.connect(self.on_collapse)
        self.itemPressed.connect(self.on_clicked)
        self.setHeaderLabels(["Files"])
        self.last_file_id = ''
        self.root_label = ''
        self.selected_item: QtWidgets.QTreeWidgetItem | None = None

        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum,
                           QtWidgets.QSizePolicy.Policy.Expanding)
        self.btns_header = HeaderButtons()
        self.btns_header.folder_btn.clicked.connect(self.on_new_folder_btn_pressed)
        self.btns_header.file_btn.clicked.connect(self.on_new_file_btn_pressed)
        self.btns_header.update_btn.clicked.connect(lambda: self.update_tree.emit())
        self.btns_header.collapse_btn.clicked.connect(lambda: self.collapseAll())
        self.header().setLayout(self.btns_header.layout)  # type: ignore

        self.delegator = ItemDelegate()
        self.setItemDelegate(self.delegator)
        self.delegator.editing_finished.connect(self.on_editing_finished)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        # self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)

    @override
    def keyPressEvent(self, event: QtGui.QKeyEvent | None) -> None:
        if not event:
            return
        if event.key() == QtCore.Qt.Key.Key_Delete:
            if self.selected_item:
                self.delete_item.emit(getattr(self.selected_item, 'key'),
                                      self.selected_item)
                self.selected_item = None
        return super().keyPressEvent(event)

    def on_editing_finished(self, index: QtCore.QModelIndex):
        item = self.get_item_from_index(index)
        if not item:
            return
        label: str = item.text(0)
        if not label:
            self._remove_item(item)
            return
        parent_path, name = self.item_path(item)
        choose_icon(item, label)
        if hasattr(item, 'file_id'):
            self.new_file.emit(parent_path, name.strip())
        else:
            self.new_folder.emit(parent_path, name.strip())

    def _remove_item(self, item: QTreeWidgetItem):
        i: int = self.indexOfTopLevelItem(item)
        if i < 0:
            parent = item.parent()
            if parent:
                parent.removeChild(item)
                if parent.childCount() < 1:
                    self.collapseItem(parent)
        else:
            self.takeTopLevelItem(i)

    def item_path(self, item: QTreeWidgetItem) -> tuple[str, str]:
        name: str = item.text(0)
        full_path = ''
        tree_item: QTreeWidgetItem = item
        parent: QTreeWidgetItem | None = tree_item.parent()
        while parent:
            parent: QTreeWidgetItem | None = tree_item.parent()
            if parent:
                full_path: str = f'{parent.text(0)}/{full_path}'
                tree_item = parent

        return f'{self.root_label}/{full_path}', name

    @override
    def mousePressEvent(self, e: QtGui.QMouseEvent | None) -> None:  # обработка нажатия вне дерева
        super().mousePressEvent(e)
        if not e:
            return
        if not self.indexAt(e.pos()).isValid():
            if self.selected_item:
                self.selected_item.setSelected(False)
                self.selected_item = None

    def get_item_from_index(self, index: QtCore.QModelIndex):
        return self.itemFromIndex(index)

    def on_new_folder_btn_pressed(self):
        if self.selected_item:
            self.selected_item.setSelected(False)
        icon = QIcon(str(icon_path.joinpath('folder.svg')))
        if self.selected_item and hasattr(self.selected_item, 'file_id'):
            parent = self.selected_item.parent()
            if not parent:
                parent = self
        elif self.selected_item:
            parent = self.selected_item
            parent.setExpanded(True)
        else:
            parent = self

        p = QTreeWidgetItem(parent)
        p.setFlags(p.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
        p.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        p.setIcon(0, icon)
        p.setSelected(True)
        self.editItem(p, 0)
        if self.selected_item:
            self.selected_item.setSelected(False)

    def on_new_file_btn_pressed(self):
        if self.selected_item:
            self.selected_item.setSelected(False)
        icon = QIcon(str(icon_path.joinpath('document.svg')))
        if self.selected_item and hasattr(self.selected_item, 'file_id'):
            parent = self.selected_item.parent()
            if not parent:
                parent = self
        elif self.selected_item:
            parent = self.selected_item
            parent.setExpanded(True)
        else:
            parent = self

        p = QTreeWidgetItem(parent)
        setattr(p, 'file_id', '')
        p.setFlags(p.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
        p.setIcon(0, icon)
        p.setSelected(True)
        self.editItem(p, 0)
        if self.selected_item:
            self.selected_item.setSelected(False)

    def on_clicked(self, item: QtWidgets.QTreeWidgetItem):
        if hasattr(item, 'file_id'):
            self.last_file_id: str = getattr(item, 'file_id')
            model = FileModel(label=item.text(0),
                              icon=item.icon(0),
                              key=getattr(item, 'key'),
                              file_id=self.last_file_id)
            self.file_selected.emit(model)
        else:
            if item.isExpanded():
                self.collapseItem(item)
            else:
                self.expandItem(item)
        self.selected_item = item

    def enterEvent(self, event: QEnterEvent | None) -> None:
        self.btns_header.folder_btn.setVisible(True)
        self.btns_header.file_btn.setVisible(True)
        self.btns_header.update_btn.setVisible(True)
        self.btns_header.collapse_btn.setVisible(True)
        return super().enterEvent(event)

    def leaveEvent(self, a0: QtCore.QEvent | None) -> None:
        # self.btns_header.folder_btn.setVisible(False)
        # self.btns_header.file_btn.setVisible(False)
        # self.btns_header.update_btn.setVisible(False)
        # self.btns_header.collapse_btn.setVisible(False)
        self.btns_header.folder_btn.setVisible(True)
        self.btns_header.file_btn.setVisible(True)
        self.btns_header.update_btn.setVisible(True)
        self.btns_header.collapse_btn.setVisible(True)
        return super().leaveEvent(a0)

    def on_expand(self, item: QtWidgets.QTreeWidgetItem):
        item.setIcon(0, QIcon(str(icon_path.joinpath('folder-open.svg'))))

    def on_collapse(self, item: QtWidgets.QTreeWidgetItem):
        item.setIcon(0, QIcon(str(icon_path.joinpath('folder.svg'))))

    def set_header(self, label: str):
        self.setHeaderLabels([label])


def generate_tree(parent: QTreeWidget | QTreeWidgetItem, model: dict):
    children: list[dict] | None = model.get('children', None)
    if not children:
        return
    for child in children:
        p = QTreeWidgetItem(parent)
        p.setFlags(p.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
        p.setText(0, child['label'])
        p.setFont(0, QtGui.QFont('Consolas', 12))
        setattr(p, 'key', child['key'])
        setattr(p, 'node_type', child['node_type'])
        if child['node_type'] == 'folder':
            p.setIcon(0, QIcon(str(icon_path.joinpath('folder.svg'))))
            p.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
            if child.get('children', None):
                generate_tree(p, {'children': child['children']})
        else:
            label: str = child['label']
            file_id: str = child['file_id']
            setattr(p, 'file_id', file_id)
            choose_icon(p, label)


def choose_icon(p: QTreeWidgetItem, label: str):
    if label.endswith('.py'):
        p.setIcon(0, QIcon(str(icon_path.joinpath('python.svg'))))
    elif label.endswith('.txt'):
        p.setIcon(0, QIcon(str(icon_path.joinpath('document.svg'))))
    elif label.endswith('.json'):
        p.setIcon(0, QIcon(str(icon_path.joinpath('json.svg'))))
    elif label.endswith('.csv'):
        p.setIcon(0, QIcon(str(icon_path.joinpath('table.svg'))))
    elif label.endswith('.bin'):
        p.setIcon(0, QIcon(str(icon_path.joinpath('document.svg'))))

def get_all_child_files(p: QTreeWidgetItem):
    keys: list[str] = []
    if getattr(p, 'node_type') != 'folder':
        keys.append(getattr(p, 'key'))
    if p.childCount() > 0:
        for child in p.takeChildren():
            if getattr(child, 'node_type') != 'folder':
                keys.append(getattr(child, 'key'))
            if child.childCount() > 0:
                keys.extend(get_all_child_files(child))
    return keys


def main():
    app = QApplication([])
    tree = FileTree()
    generate_tree(tree, model)
    tree.show()
    app.exec()

if __name__ == '__main__':
    main()