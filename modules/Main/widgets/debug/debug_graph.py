from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PyQt6 import QtCore, QtWidgets, QtGui
from qtpy.uic import loadUi

# pyqtgraph is used for plotting
import pyqtgraph as pg


class _GraphGroupBox(QtWidgets.QGroupBox):
    """GroupBox without title that hosts a PlotWidget and a hover delete button."""

    def __init__(self, on_remove: Callable[[QtWidgets.QGroupBox], None]) -> None:
        super().__init__("")
        self.setFlat(True)
        self.setObjectName("graphGroupBox")
        self._on_remove = on_remove

        # Layout for plot
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Plot widget
        self.plot: pg.PlotWidget = pg.PlotWidget(self)
        layout.addWidget(self.plot)

        # Floating delete button (hidden by default)
        self._btn_del = QtWidgets.QPushButton("✖", self)
        self._btn_del.setToolTip("Удалить график")
        self._btn_del.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._btn_del.setFixedSize(18, 18)
        self._btn_del.setVisible(False)
        # Compact square button, rounded corners, transparent with gray border/icon
        self._btn_del.setStyleSheet(
            "QPushButton{background-color: rgba(0,0,0,0); color: #888;"
            " border: 1px solid rgba(128,128,128,160); border-radius: 4px;}"
            "QPushButton:hover{color: #666; border: 1px solid rgba(128,128,128,220);}" 
        )
        self._btn_del.clicked.connect(lambda: self._on_remove(self))

        # Track hover on both the group box and the plot widget
        self.setMouseTracking(True)
        self.plot.setMouseTracking(True)
        self.installEventFilter(self)
        self.plot.installEventFilter(self)

    # Keep button at bottom-right corner
    def resizeEvent(self, event: Optional[QtGui.QResizeEvent]) -> None:  # type: ignore[override]
        try:
            w = self.width()
            h = self.height()
            bw = self._btn_del.width()
            bh = self._btn_del.height()
            # Place in top-right corner
            self._btn_del.move(max(4, w - bw - 8), 33)
        except Exception:
            ...
        super().resizeEvent(event)

    def _update_btn_visibility(self) -> None:
        # Show if cursor is over the plot, group box, or the button itself
        show = self.plot.underMouse() or self.underMouse() or self._btn_del.underMouse()
        self._btn_del.setVisible(show)

    # Show/hide on hover events
    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:  # noqa: N802
        et = event.type()
        if et in (
            QtCore.QEvent.Type.HoverEnter,
            QtCore.QEvent.Type.HoverMove,
            QtCore.QEvent.Type.HoverLeave,
            QtCore.QEvent.Type.Enter,
            QtCore.QEvent.Type.Leave,
            QtCore.QEvent.Type.MouseMove,
        ):
            # Slightly defer hide to allow moving onto the button
            QtCore.QTimer.singleShot(0, self._update_btn_visibility)
        return super().eventFilter(obj, event)


class DebugGraphWidget(QtWidgets.QWidget):
    """Debug module: add/remove graphs dynamically with a hover delete button."""

    # UI elements loaded from .ui at runtime
    verticalLayout_graph: QtWidgets.QVBoxLayout
    verticalLayout_2: QtWidgets.QVBoxLayout

    def __init__(self, *args) -> None:
        super().__init__()
        loadUi(Path(__file__).parent.joinpath("debug_graph.ui"), self)

        # Add-graph button may be named differently; try both
        self._btn_add: Optional[QtWidgets.QPushButton] = None
        for name in ("pushButton_add_graph", "pushButton"):
            btn = getattr(self, name, None)
            if isinstance(btn, QtWidgets.QPushButton):
                self._btn_add = btn
                break
        if self._btn_add is None:
            # Fallback: create a button and put it at the bottom of main layout
            self._btn_add = QtWidgets.QPushButton("Добавить график", self)
            if hasattr(self, "verticalLayout_graph") and isinstance(self.verticalLayout_graph, QtWidgets.QLayout):
                self.verticalLayout_graph.addWidget(self._btn_add)
            else:
                lay = self.layout() or QtWidgets.QVBoxLayout(self)
                if isinstance(lay, QtWidgets.QLayout):
                    lay.addWidget(self._btn_add)

        self._btn_add.clicked.connect(self._on_add_graph)

        # Container layout for graph group boxes
        self._container_layout: QtWidgets.QLayout
        if hasattr(self, "verticalLayout_2") and isinstance(self.verticalLayout_2, QtWidgets.QLayout):
            self._container_layout = self.verticalLayout_2
        else:
            # Fallback to the main vertical layout if needed
            self._container_layout = self.verticalLayout_graph if hasattr(self, "verticalLayout_graph") else (self.layout() or QtWidgets.QVBoxLayout(self))  # type: ignore[assignment]

    # Slot: add a new graph group box
    def _on_add_graph(self) -> None:
        box = _GraphGroupBox(on_remove=self._remove_box)
        self._container_layout.addWidget(box)

    # Remove the whole group box
    def _remove_box(self, box: QtWidgets.QGroupBox) -> None:
        try:
            # Find and remove from layout
            lay = self._container_layout
            for i in range(lay.count()):
                item = lay.itemAt(i)
                if item and item.widget() is box:
                    lay.takeAt(i)
                    break
            box.setParent(None)
            box.deleteLater()
        except Exception:
            ...


# Optional manual test
if __name__ == "__main__":
    import sys
    import qtmodern.styles

    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    w = DebugGraphWidget()
    w.resize(900, 600)
    w.show()
    sys.exit(app.exec())
