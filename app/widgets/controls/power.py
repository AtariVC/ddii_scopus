"""PowerControlWidget — три панели управления питанием: PIPS, SiPM, Черенковский счётчик.

API:
* ``PowerControlWidget(client=None, parent=None)`` — три сконфигурированные панели
  каналов; ``client`` даёт командный интерфейс (``client.cm``), в demo — ``None``.
* ``panel(key) -> PowerCtrlPanel | None`` — панель канала (``'pips'``/``'sipm'``/``'cherenkov'``).
* ``panels: dict[str, PowerCtrlPanel]`` — все панели по ключу канала.
* атрибуты ``panel_pips`` · ``panel_sipm`` · ``panel_cherenkov`` — прямой доступ к панелям.
"""
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtWidgets import QHBoxLayout, QWidget
from PyQt6.QtCore import pyqtSignal
from dark_pro_widgets.core import theme
from dark_pro_widgets.widgets.composite import PowerCtrlPanel
from app.src.components.modbus.command_interface import ModbusCMCommand
from typing import Callable


@dataclass(frozen=True)
class ChannelConfig:
    """Конфигурация одной панели канала питания.

    Attributes:
        key: ключ канала (``'pips'``/``'sipm'``/``'cherenkov'``).
        title: заголовок панели.
        color: цвет точки состояния — токен темы, закреплённый за каналом.
        enable_ch_v: команда управления напряжением
        set_v: команда установки уставки напряжения 
        
    """
    key: str
    title: str
    color: str
    # enable_ch_v: Callable
    # set_v: Callable


# Цвет закреплён за каналом, как на графиках: PIPS — зелёный, SiPM — янтарный,
# черенковский счётчик — синий (accent).
_CHANNELS: list[ChannelConfig] = [
    ChannelConfig("pips", "Канал PIPS", theme.PIPS),
    ChannelConfig("sipm", "Канал SiPM", theme.SIPM),
    ChannelConfig("cherenkov", "Черенковский счётчик", theme.ACCENT),
]

# Набор плиток телеметрии и подпись уставки — одинаковы для всех трёх каналов.
_TILES: list[tuple[str, str]] = [("Напряжение, V", "—"), ("Ток, µA", "—"), ("ШИМ, %", "—")]
_SETPOINT_LABEL = "Уставка, V"


class PowerControlWidget(QWidget):
    """Три панели управления питанием: PIPS, SiPM, черенковский счётчик.

    Attributes:
        panel_pips (PowerCtrlPanel): панель канала PIPS.
        panel_sipm (PowerCtrlPanel): панель канала SiPM.
        panel_cherenkov (PowerCtrlPanel): панель черенковского счётчика.
    """

    panel_pips: PowerCtrlPanel
    panel_sipm: PowerCtrlPanel
    panel_cherenkov: PowerCtrlPanel

    def __init__(self, client=None, parent=None) -> None:
        super().__init__(parent)
        self.panels: dict[str, PowerCtrlPanel] = {}

        self.client = client
        # командный интерфейс ВШ ЦМ; в demo/без подключения — None (getattr не падает)
        self.cm_ib: ModbusCMCommand | None = getattr(client, "cm", None)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)
        # панели в ряд, равной ширины (stretch=1 на каждую)
        for channel in _CHANNELS:
            outer.addWidget(self._build_panel(channel), 1)

    def _build_panel(self, channel: ChannelConfig) -> PowerCtrlPanel:
        """Собрать и настроить одну панель канала.

        Args:
            channel: конфигурация канала (ключ, заголовок, цвет точки).

        Returns:
            Настроенная :class:`PowerCtrlPanel`; ссылка также кладётся в
            ``self.panels[channel.key]`` и в атрибут ``panel_<key>``.
        """
        panel = PowerCtrlPanel()
        panel.set_title_widget(channel.title, channel.color)
        panel.set_tiles(_TILES)
        panel.set_lineEdit_label(_SETPOINT_LABEL)
        self.panels[channel.key] = panel
        setattr(self, f"panel_{channel.key}", panel)
        return panel

    def panel(self, key: str) -> PowerCtrlPanel | None:
        """Панель канала по ключу (``'pips'``/``'sipm'``/``'cherenkov'``) или ``None``."""
        return self.panels.get(key)


if __name__ == "__main__":
    from dark_pro_widgets.core._preview import preview

    def build() -> PowerControlWidget:
        widget = PowerControlWidget()
        # демо-телеметрия, чтобы плитки и уставки не были пустыми в превью
        widget.panel_pips.set_tiles([("HV, V", "420"), ("Ток, µA", "0.82"), ("Темп, °C", "21.6")])
        widget.panel_pips.set_lineEdit_value("420")
        widget.panel_pips.set_power(True)
        widget.panel_sipm.set_tiles([("HV, V", "56"), ("Ток, µA", "1.10"), ("Темп, °C", "22.1")])
        widget.panel_cherenkov.set_tiles([("HV, V", "1500"), ("Ток, µA", "3.40"), ("Темп, °C", "23.0")])
        for ch, pnl in widget.panels.items():
            pnl.signal_switch_power.connect(lambda on, c=ch: print(c, "питание:", on))
            pnl.signal_set_value.connect(lambda v, c=ch: print(c, "уставка:", v))
        return widget

    preview(build, title="Управление питанием — PIPS · SiPM · Черенков", size=(1120, 340), stretch=False)
