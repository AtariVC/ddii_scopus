"""Настройки соединения ДДИИ: модель + диалог.

Здесь живёт всё, что раньше было разбросано по бару и константам:
порт, baudrate, адреса ЦМ/МПП и режим опроса (какие устройства спрашивать).
Значения сохраняются между запусками через ``QSettings`` — без новых
зависимостей и без лишних файлов в репозитории.

Разметка диалога — ``connection_settings.ui`` (loadUi), как и везде в проекте.

Запуск отдельно (из корня проекта):

    python -m app.plugins.connection.connection_settings
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import serial.tools.list_ports
from PyQt6 import QtWidgets
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QIntValidator
from qtpy.uic import loadUi

from dark_pro_widgets import theme
from dark_pro_widgets.combo_box import ComboBox

from app.src.components.modbus.modbus_var import ModbusReg

# Организация/приложение для QSettings (macOS: ~/Library/Preferences, Win: реестр)
_ORG = "ddii"
_APP = "scopus"
_GROUP = "connection"

BAUDRATE_DEFAULT = 125000
TCP_PORT_DEFAULT = 5012

# Частые скорости + рабочая 125000 (ДДИИ)
BAUDRATE_PRESETS = [9600, 19200, 38400, 57600, 115200, 125000, 230400, 250000, 500000, 921600]

# Режимы опроса
POLL_BOTH = "both"
POLL_CM = "cm"
POLL_MPP = "mpp"


def list_serial_ports() -> list[str]:
    """Доступные COM-порты (пустой список, если перечислить не удалось)."""
    try:
        return [p.device for p in sorted(serial.tools.list_ports.comports())]
    except Exception:
        return []


class _DialogCombo(ComboBox):
    """Промоут-адаптер: тема dark_pro_widgets рисует шеврон сама (с отступом от
    края), а загрузчик .ui создаёт виджет как ``Class(parent)``.
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)


@dataclass
class ConnectionSettings:
    """Параметры соединения. ``load()``/``save()`` работают через QSettings."""

    poll_mode: str = POLL_BOTH
    serial_port: str = ""
    baudrate: int = BAUDRATE_DEFAULT
    tcp_host: str = ""
    tcp_port: int = TCP_PORT_DEFAULT
    cm_id: int = field(default=ModbusReg.CM_ID)
    mpp_id: int = field(default=ModbusReg.MPP_ID)

    # --- какие устройства участвуют в опросе ---
    @property
    def poll_cm(self) -> bool:
        return self.poll_mode in (POLL_BOTH, POLL_CM)

    @property
    def poll_mpp(self) -> bool:
        return self.poll_mode in (POLL_BOTH, POLL_MPP)

    def poll_label(self) -> str:
        return {POLL_BOTH: "ЦМ + МПП", POLL_CM: "только ЦМ", POLL_MPP: "только МПП"}.get(
            self.poll_mode, self.poll_mode
        )

    # --- сохранение/загрузка ---
    @classmethod
    def load(cls) -> "ConnectionSettings":
        s = QSettings(_ORG, _APP)
        s.beginGroup(_GROUP)
        defaults = cls()

        def _int(key: str, default: int) -> int:
            try:
                return int(s.value(key, default))
            except (TypeError, ValueError):
                return default

        obj = cls(
            poll_mode=str(s.value("poll_mode", defaults.poll_mode)),
            serial_port=str(s.value("serial_port", defaults.serial_port)),
            baudrate=_int("baudrate", defaults.baudrate),
            tcp_host=str(s.value("tcp_host", defaults.tcp_host)),
            tcp_port=_int("tcp_port", defaults.tcp_port),
            cm_id=_int("cm_id", defaults.cm_id),
            mpp_id=_int("mpp_id", defaults.mpp_id),
        )
        s.endGroup()
        if obj.poll_mode not in (POLL_BOTH, POLL_CM, POLL_MPP):
            obj.poll_mode = POLL_BOTH
        return obj

    def save(self) -> None:
        s = QSettings(_ORG, _APP)
        s.beginGroup(_GROUP)
        s.setValue("poll_mode", self.poll_mode)
        s.setValue("serial_port", self.serial_port)
        s.setValue("baudrate", int(self.baudrate))
        s.setValue("tcp_host", self.tcp_host)
        s.setValue("tcp_port", int(self.tcp_port))
        s.setValue("cm_id", int(self.cm_id))
        s.setValue("mpp_id", int(self.mpp_id))
        s.endGroup()
        s.sync()


class ConnectionSettingsDialog(QtWidgets.QDialog):
    """Диалог правки ``ConnectionSettings`` (модальный, OK/Отмена)."""

    radio_both: QtWidgets.QRadioButton
    radio_cm: QtWidgets.QRadioButton
    radio_mpp: QtWidgets.QRadioButton
    combo_port: QtWidgets.QComboBox
    button_refresh: QtWidgets.QPushButton
    combo_baudrate: QtWidgets.QComboBox
    edit_host: QtWidgets.QLineEdit
    edit_tcp_port: QtWidgets.QLineEdit
    edit_cm_id: QtWidgets.QLineEdit
    edit_mpp_id: QtWidgets.QLineEdit
    buttons: QtWidgets.QDialogButtonBox

    def __init__(self, settings: ConnectionSettings, parent=None) -> None:
        super().__init__(parent)
        loadUi(Path(__file__).parent / "connection_settings.ui", self)

        self._settings = settings
        self._apply_theme()

        self.edit_tcp_port.setValidator(QIntValidator(1, 65535, self))
        self.edit_cm_id.setValidator(QIntValidator(0, 247, self))
        self.edit_mpp_id.setValidator(QIntValidator(0, 247, self))

        self.combo_baudrate.addItems([str(b) for b in BAUDRATE_PRESETS])
        self.button_refresh.clicked.connect(self._refresh_ports)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self._refresh_ports()
        self._load_into_widgets(settings)

    def _apply_theme(self) -> None:
        """Глобальная тема рисует рамку QGroupBox, но не разводит заголовок —
        без отступа он наезжает на рамку и обрезается. Плюс русские подписи кнопок.
        """
        self.setStyleSheet(
            f"""
            QGroupBox {{
                margin-top: 10px;
                padding: 14px 12px 12px 12px;
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
                color: {theme.TEXT_DIM};
                background: transparent;
            }}
            /* тема знает QCheckBox, но не QRadioButton — иначе фон виджета
               проступает прямоугольником за подписью */
            QRadioButton {{ spacing: 8px; background: transparent; }}
            QRadioButton::indicator {{
                width: 16px; height: 16px;
                border: 1px solid {theme.BORDER};
                border-radius: 9px;
                background: {theme.FIELD_BG};
            }}
            QRadioButton::indicator:checked {{
                background: {theme.ACCENT};
                border: 1px solid {theme.ACCENT};
            }}
            """
        )
        ok = self.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        cancel = self.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        if ok is not None:
            ok.setText("Сохранить")
            ok.setMinimumHeight(30)
        if cancel is not None:
            cancel.setText("Отмена")
            cancel.setMinimumHeight(30)

    # --- модель -> виджеты ---
    def _load_into_widgets(self, s: ConnectionSettings) -> None:
        {POLL_BOTH: self.radio_both, POLL_CM: self.radio_cm, POLL_MPP: self.radio_mpp}.get(
            s.poll_mode, self.radio_both
        ).setChecked(True)

        if s.serial_port:
            if self.combo_port.findText(s.serial_port) < 0:
                # порт мог отвалиться (кабель вынут) — показываем, но помечаем
                self.combo_port.addItem(f"{s.serial_port}")
            self.combo_port.setCurrentText(s.serial_port)

        self.combo_baudrate.setCurrentText(str(s.baudrate))
        self.edit_host.setText(s.tcp_host)
        self.edit_tcp_port.setText(str(s.tcp_port))
        self.edit_cm_id.setText(str(s.cm_id))
        self.edit_mpp_id.setText(str(s.mpp_id))

    # --- виджеты -> модель ---
    def result_settings(self) -> ConnectionSettings:
        """Собирает настройки из полей. Некорректные значения — на дефолт."""

        def _int(text: str, default: int) -> int:
            try:
                return int(str(text).strip())
            except (TypeError, ValueError):
                return default

        if self.radio_cm.isChecked():
            poll_mode = POLL_CM
        elif self.radio_mpp.isChecked():
            poll_mode = POLL_MPP
        else:
            poll_mode = POLL_BOTH

        return ConnectionSettings(
            poll_mode=poll_mode,
            serial_port=self.combo_port.currentText().strip(),
            baudrate=_int(self.combo_baudrate.currentText(), BAUDRATE_DEFAULT),
            tcp_host=self.edit_host.text().strip(),
            tcp_port=_int(self.edit_tcp_port.text(), TCP_PORT_DEFAULT),
            cm_id=_int(self.edit_cm_id.text(), ModbusReg.CM_ID),
            mpp_id=_int(self.edit_mpp_id.text(), ModbusReg.MPP_ID),
        )

    def _refresh_ports(self) -> None:
        current = self.combo_port.currentText()
        ports = list_serial_ports()
        self.combo_port.clear()
        self.combo_port.addItems(ports)
        if current:
            if self.combo_port.findText(current) < 0:
                self.combo_port.addItem(current)
            self.combo_port.setCurrentText(current)


if __name__ == "__main__":
    import sys

    from dark_pro_widgets import qss

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())

    dialog = ConnectionSettingsDialog(ConnectionSettings.load())
    if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        result = dialog.result_settings()
        print(f"сохранено: {result.poll_label()}, порт={result.serial_port or '—'}, "
              f"baudrate={result.baudrate}, ЦМ={result.cm_id}, МПП={result.mpp_id}")
    else:
        print("отменено")
    sys.exit(0)
