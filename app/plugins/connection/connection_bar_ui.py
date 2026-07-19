"""ConnectionBar из .ui, загруженного через QtPy.

То же превью, что и `python -m dark_pro_widgets.connection_bar`, но разметка
поднимается напрямую из connection_bar.ui загрузчиком QtPy:

    from qtpy.uic import loadUi

QtPy сам выбирает установленный биндинг Qt (здесь — PyQt6), поэтому пример не
привязан к конкретной библиотеке. Продвинутые (promoted) кастомные виджеты
берутся из dark_pro_widgets.connection_bar (см. <customwidget> в .ui). Тема и
логика навешиваются в Python после загрузки — ровно так же, как это делает сам
класс ConnectionBar.

Запуск:  uv run python examples/connection_bar_preview.py
"""

import os
import sys

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout, QWidget
from qtpy.uic import loadUi

from dark_pro_widgets import (
    ComboBox,
    LineEdit,
    PrimaryButton,
    SegmentedControl,
    qss,
    theme,
)
from dark_pro_widgets import connection_bar as _cb

_FONT = theme.FONT_FAMILY.split(",")[0].strip()
_MONO = theme.MONO_FAMILY.split(",")[0].strip()
BAR_BG = "#131417"  # фон панели (RGB 19,20,23)


class ConnectionBarPreview(QWidget):

    _dot: QLabel
    _status: QLabel
    sep1: QFrame
    transport: SegmentedControl
    port: ComboBox
    mpp_label: QLabel
    mpp: LineEdit
    _btn: PrimaryButton
    _state_caption: QLabel
    _state: QLabel

    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi("connection_bar.ui", self)

        self._connected = False
        self.setObjectName("ConnectionBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(46)
        self.setStyleSheet(
            f"#ConnectionBar {{ background-color: {BAR_BG}; "
            f"border-top: 1px solid {theme.SEPARATOR}; }}"
        )

        # тема на именованные виджеты .ui (цвета из theme.*)
        self._status.setStyleSheet(
            f"color: {theme.TEXT}; font-family: '{_FONT}'; background: transparent; border: none;"
        )
        self.sep1.setStyleSheet(f"background-color: {theme.BORDER}; border: none;")
        self.mpp_label.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-family: '{_MONO}'; font-size: 13px; "
            "background: transparent; border: none;"
        )
        self._state_caption.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-family: '{_MONO}'; background: transparent; border: none;"
        )

        # демо-поведение: кнопка переключает статус, сигналы печатаются в консоль
        self._btn.clicked.connect(lambda: self.set_connected(not self._connected))
        self.transport.currentTextChanged.connect(lambda t: print("transport:", t))
        self.port.currentTextChanged.connect(lambda p: print("port:", p))

        self.set_connected(False)
        self.set_state("IDLE")

    def set_connected(self, connected):
        self._connected = connected
        color = theme.OK if connected else theme.TEXT_DIM
        self._dot.setStyleSheet(
            f"color: {color}; background: transparent; border: none;"
        )
        self._status.setText("Подключено" if connected else "Отключено")
        self._btn.setText("Отключить" if connected else "Подключить")
        self._btn.setVariant("neutral" if connected else "accent")

    def set_ports(self, ports, current=None):
        self.port.clear()
        self.port.addItems(list(ports))
        if current:
            self.port.setCurrentText(current)

    def set_state(self, state):
        state = state.upper()
        color = theme.OK if state == "RUN" else theme.TEXT_DIM
        self._state.setText(state)
        self._state.setStyleSheet(
            f"color: {color}; font-family: '{_MONO}'; font-weight: 600; "
            "background: transparent; border: none;"
        )


# def main():
#     app = QApplication(sys.argv)
#     app.setStyleSheet(qss.build_stylesheet())

#     host = QWidget()
#     host.setWindowTitle("ConnectionBar")
#     layout = QVBoxLayout(host)
#     layout.setContentsMargins(0, 0, 0, 0)
#     layout.addStretch()

#     bar = ConnectionBarPreview()
#     bar.transport.setCurrentIndex(1)  # TCP
#     bar.set_state("RUN")
#     layout.addWidget(bar)

#     host.resize(900, 220)
#     host.show()
#     return app.exec()


# if __name__ == "__main__":
#     sys.exit(main())
