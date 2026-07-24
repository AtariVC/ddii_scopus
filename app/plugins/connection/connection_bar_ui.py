"""Презентационный виджет нижней панели подключения (UI, без бэкенда).

Разметка — ``connection_bar.ui`` (loadUi), тема и промоут-виджеты — из
``dark_pro_widgets``. Здесь только вид и презентационный API; вся логика связи
(Serial/TCP/relay, опрос ЦМ/МПП) живёт в наследнике
``connection_bar.ConnectionBar``.

Модуль самодостаточен (зависит только от ``dark_pro_widgets`` и Qt) и рассчитан
на перенос в ``dark_pro_widgets`` как composite-виджет: при переносе достаточно
переложить рядом ``connection_bar.ui`` и поправить в нём ``<header>`` промоут-
виджетов на новый путь модуля.

● статус │ [Serial|TCP] │ ⚙ │ [Подключить] … State: …

Сигналы:
    connectToggled(bool):   нажата кнопка (True = запрошено подключение).
    transportChanged(str):  сменён транспорт (Serial/TCP).
    portChanged(str):       сменён порт (для совместимости; панель без комбо).
    settingsClicked():      нажата ⚙.

Иконку ⚙ ставит владелец (у библиотеки нет доступа к иконкам приложения) —
через ``settings_btn.setIcon(...)``.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6 import QtWidgets
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from qtpy.uic import loadUi

from dark_pro_widgets import PrimaryButton, SegmentedControl, theme

# Единая высота контролов панели — продублирована в connection_bar.ui.
CONTROL_H = 32
# Фон панели — RGB(19, 20, 23); рельс — theme.FIELD_BG RGB(15, 16, 19).
BAR_BG = "#131417"

_FONT = theme.FONT_FAMILY.split(",")[0].strip()
_MONO = theme.MONO_FAMILY.split(",")[0].strip()


# --- promotion-адаптеры ------------------------------------------------------
# Загрузчик .ui создаёт promoted-виджеты только как ``Class(parent)``, а базовые
# виджеты dark_pro_widgets требуют обязательные аргументы (items/text). Тонкие
# подклассы дают конструктор ``(parent)`` с нужными умолчаниями. Подключены в
# connection_bar.ui через <customwidget> (header = этот модуль).

class _TransportSwitch(SegmentedControl):
    """Сегменты Serial | TCP."""

    def __init__(self, parent=None):
        super().__init__(["Serial", "TCP"], parent=parent)


class _ConnectButton(PrimaryButton):
    """Кнопка Подключить/Отключить — компактная, акцентная по умолчанию."""

    def __init__(self, parent=None):
        super().__init__("", variant="accent", compact=True, parent=parent)


class _IconButton(QtWidgets.QPushButton):
    """Плоская иконочная кнопка панели (32×32). Саму иконку ставит владелец —
    через ``setIcon`` с цветом из темы."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(18, 18))
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 7px;
            }}
            QPushButton:hover {{
                background-color: {theme.FIELD_BG};
                border: 1px solid {theme.BORDER};
            }}
            QPushButton:pressed {{ background-color: #2f343d; }}
        """)


class ConnectionBarUI(QtWidgets.QWidget):
    """Постоянная нижняя панель связи — только вид и презентационный API.

    Разметка — connection_bar.ui; тема и сигналы — здесь. Бэкенд добавляет
    наследник (см. модуль ``connection_bar``).
    """

    connectToggled = pyqtSignal(bool)
    transportChanged = pyqtSignal(str)
    portChanged = pyqtSignal(str)
    settingsClicked = pyqtSignal()

    # Аннотации виджетов из .ui
    _dot: QtWidgets.QLabel
    _status: QtWidgets.QLabel
    sep1: QtWidgets.QFrame
    transport: _TransportSwitch
    settings_btn: _IconButton
    _btn: _ConnectButton
    _state_caption: QtWidgets.QLabel
    _state: QtWidgets.QLabel

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # виджеты .ui становятся атрибутами self (см. аннотации выше)
        loadUi(Path(__file__).parent / "connection_bar.ui", self)
        self._connected = False
        self._apply_theme()

        # --- сигналы: кнопка/⚙ шлют презентационные сигналы наружу ---
        self.transport.currentTextChanged.connect(self.transportChanged)
        self._btn.clicked.connect(lambda: self.connectToggled.emit(not self._connected))
        self.settings_btn.clicked.connect(self.settingsClicked)

        self.set_connected(False)

    # ===== оформление =====
    def _apply_theme(self) -> None:
        self.setObjectName("ConnectionBar")
        # без WA_StyledBackground QSS-граница (border-top) не отрисуется на подклассе
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(46)
        self.setStyleSheet(
            f"#ConnectionBar {{ background-color: {BAR_BG}; "
            f"border-top: 1px solid {theme.SEPARATOR}; }}"
        )
        self._status.setStyleSheet(
            f"color: {theme.TEXT}; font-family: '{_FONT}'; background: transparent; border: none;"
        )
        self.sep1.setStyleSheet(f"background-color: {theme.BORDER}; border: none;")
        self._state_caption.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-family: '{_MONO}'; background: transparent; border: none;"
        )

    # ===== презентационный API =====
    def _set_dot(self, ok: bool) -> None:
        self._paint_status(color=theme.OK if ok else theme.TEXT_DIM)

    def _paint_status(self, color: str) -> None:
        """Красит точку и надпись статуса одним цветом состояния."""
        self._dot.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        self._status.setStyleSheet(
            f"color: {color}; font-family: '{_FONT}'; font-weight: 600; "
            "background: transparent; border: none;"
        )

    def _set_status(self, text: str, color: str) -> None:
        """Короткий вердикт слева: текст + цвет. Детализация — в State."""
        self._status.setText(text)
        self._paint_status(color)

    def set_connected(self, connected: bool) -> None:
        self._connected = bool(connected)
        if self._connected:
            self._set_status("Подключено", theme.OK)
        else:
            self._set_status("Отключено", theme.TEXT_DIM)
        # 'Отключить' — нейтральная тёмная; 'Подключить' — акцентная
        self._btn.setText("Отключить" if self._connected else "Подключить")
        self._btn.setVariant("neutral" if self._connected else "accent")

    def set_transport(self, name: str) -> None:
        idx = 0 if name.lower().startswith("serial") else 1
        self.transport.setCurrentIndex(idx)

    def set_state(self, text: str, color: str | None = None) -> None:
        """Прямая установка поля State."""
        self._state.setText(text)
        self._state.setStyleSheet(
            f"color: {color or theme.TEXT_DIM}; font-family: '{_MONO}'; font-weight: 600; "
            "background: transparent; border: none;"
        )

    # ===== геттеры =====
    def is_connected(self) -> bool:
        return self._connected

    def current_transport(self) -> str:
        return self.transport.currentText()

    def is_serial_transport(self) -> bool:
        return self.current_transport().lower().startswith("serial")


if __name__ == "__main__":
    # Чистый UI без бэкенда: async-слотов нет, поэтому годится preview (памятка §10).
    from dark_pro_widgets.core import preview

    def _demo():
        bar = ConnectionBarUI()
        bar.set_state("RUN", theme.OK)
        bar.connectToggled.connect(bar.set_connected)          # демо: кнопка меняет статус
        bar.transportChanged.connect(lambda t: print("transport:", t))
        bar.settingsClicked.connect(lambda: print("settings clicked"))
        return bar

    preview(_demo, title="ConnectionBar UI — превью", size=(900, 220), stretch=False)
