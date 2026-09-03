"""Каналы HVIP прибора — общая таблица «канал ↔ панель» для виджетов питания.

Один источник истины о трёх каналах высоковольтного источника: ключ, заголовок
панели, закреплённый цвет и номер канала в прошивке (адресация регистров:
``BASE + ch * NUMBER + offset``). Таблицей пользуются
:class:`~app.widgets.controls.power.PowerControlWidget` (телеметрия и графики) и
:class:`~app.widgets.controls.power_settings.PowerSettingsWidget` (настройка),
чтобы порядок, названия и цвета каналов не разъезжались по виджетам.

API:
* ``ChannelConfig(key, title, color, ch)`` — конфигурация одного канала.
* ``CHANNELS: list[ChannelConfig]`` — три канала в порядке отображения.
"""
from __future__ import annotations

from dataclasses import dataclass

from dark_pro_widgets.core import theme


@dataclass(frozen=True)
class ChannelConfig:
    """Конфигурация одного канала питания.

    Attributes:
        key (str): ключ канала (``'pips'``/``'sipm'``/``'cherenkov'``).
        title (str): заголовок панели.
        color (str): цвет точки состояния — токен темы, закреплённый за каналом.
        ch (int): индекс канала HVIP в прошивке (адресация регистров).
    """
    key: str
    title: str
    color: str
    ch: int


# Цвет закреплён за каналом, как на графиках: PIPS — зелёный, SiPM — янтарный,
# черенковский счётчик — синий (accent).
CHANNELS: list[ChannelConfig] = [
    ChannelConfig("pips", "PIPS", theme.PIPS, ch=2),
    ChannelConfig("sipm", "SiPM", theme.SIPM, ch=1),
    ChannelConfig("cherenkov", "Чер. счётчик", theme.ACCENT, ch=0),
]
