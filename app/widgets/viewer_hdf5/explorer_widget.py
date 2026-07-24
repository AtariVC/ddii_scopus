"""Файл-менеджер экрана «Вьюер».
"""

from pathlib import Path

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QVBoxLayout

from dark_pro_widgets import FileTree

from app.src.event.event import Event


PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Вьюер работает только с HDF5 — остальные записи в списке игнорируем.
_HDF5_SUFFIXES = (".h5", ".hdf5")


class ExplorerHDF5Widget(QtWidgets.QWidget):
    """Левый сайдбар «Вьюер»: обёртка над ``FileTree``.

        double_clicked_event (Event[str]): путь открытого HDF5-файла.
    """

    double_clicked_event: Event

    def __init__(self) -> None:
        super().__init__()
        self.double_clicked_event = Event(str)

        self.tree = FileTree(parent=self)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.tree)

        # FileTree сам ходит по каталогам; наружу пробрасываем только файлы.
        self.tree.fileActivated.connect(self._on_file_activated)

        start = PROJECT_ROOT / "log" / "scope"
        self.tree.set_path(str(start if start.is_dir() else PROJECT_ROOT))

    def _on_file_activated(self, path: str) -> None:
        if path.lower().endswith(_HDF5_SUFFIXES):
            self.double_clicked_event.emit(path)


if __name__ == "__main__":
    import asyncio
    import sys

    import qasync

    from dark_pro_widgets import qss, theme
    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget

    app = QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())

    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    widget = ExplorerHDF5Widget()
    widget.double_clicked_event.subscribe(lambda p: print("открыть HDF5:", p))

    host = QWidget()
    host.setWindowTitle("Файловое дерево — demo")
    host.setStyleSheet(f"background-color: {theme.BG};")
    layout = QVBoxLayout(host)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.addWidget(widget)
    layout.addStretch()

    host.resize(320, 760)
    theme.tint_window_board(int(host.winId()))  # тёмный заголовок ДО show()
    host.show()

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
