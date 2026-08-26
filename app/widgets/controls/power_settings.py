"""PowerSettingsWidget — настройка питания трёх каналов HVIP (PIPS · SiPM · Чер. счётчик).

Экран настройки: на каждый канал — панель ``ChannelPowerPanel`` (мониторы показаний ·
режим · колонки «Уставки»/«ПИД-регулятор» · флаги состояния канала). Панели —
готовые виджеты библиотеки, здесь только бэкенд: чтение блока регистров HVIP,
раскладка полей кадра по зонам панели и запись правок обратно в прибор.

API:
* ``PowerSettingsWidget(client=None, parent=None)`` — три панели каналов; ``client``
  (ConnectionBar) даёт командный интерфейс ЦМ, в demo — ``None``.
* ``start_polling()`` / ``stop_polling()`` — запуск/остановка фонового опроса HVIP.
* ``set_poll_interval(seconds)`` / ``poll_interval() -> float`` — период опроса, с.
* ``apply_field(ch, name, value)`` — поставить поле кадра HVIP в очередь записи.
* ``push_hvip(ch, raw)`` — разобрать блок регистров канала и обновить его панель.
* ``panel(key) -> ChannelPowerPanel | None`` — панель канала (``'pips'``/``'sipm'``/
  ``'cherenkov'``); ``panels: dict[str, ChannelPowerPanel]`` — все панели по ключу.

Блок регистров канала читается целиком (``read_hvip``), разбирается кадром
:data:`~app.src.components.frames.HVIP` и копится в
:class:`~app.src.components.frames.DeviceState` (слот ``hvip:<ch>``). Правки полей и
смена режима не уходят на шину сразу, а копятся в очереди и отправляются ближайшим
проходом опроса (``write_hvip``) — запись не делит шину с чтениями, как в
``FrameViewerWidget``. Поле, которое правят прямо сейчас (в фокусе), опрос не
перетирает. Опрос стартует/стопится по подключению ЦМ (``coroutine_finished`` /
``disconnected``).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

import qasync
from loguru import logger

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget
from dark_pro_widgets.core import theme
from dark_pro_widgets.widgets.composite.channel_power_panel import ChannelPowerPanel

from app.src.components.frames import HVIP, DeviceState
from app.src.components.modbus.command_interface import ModbusCMCommand
from app.src.util.async_task_manager import AsyncTaskManager
from app.widgets.controls.hvip_channels import CHANNELS, ChannelConfig


@dataclass(frozen=True)
class MonitorTile:
    """Плитка телеметрии панели: подпись ↔ поле кадра HVIP.

    Attributes:
        label (str): подпись плитки.
        field (str): имя поля кадра HVIP.
        digits (int): знаков после запятой в значении.
    """
    label: str
    field: str
    digits: int = 2


@dataclass(frozen=True)
class ParamField:
    """Строка колонки настроек: подпись ↔ поле кадра HVIP.

    Attributes:
        label (str): подпись строки.
        field (str): имя поля кадра HVIP (пишется, если поле ``rw``).
        unit (str): единица измерения (дописывается к подписи).
        digits (int): знаков после запятой в значении.
    """
    label: str
    field: str
    unit: str = ""
    digits: int = 2


@dataclass(frozen=True)
class ParamColumnConfig:
    """Колонка настроек панели.

    Attributes:
        title (str): заголовок колонки.
        fields (tuple[ParamField, ...]): строки колонки сверху вниз.
        header_field (str | None): поле кадра в шапке колонки (``None`` — без него).
        header_unit (str): единица значения в шапке.
        header_digits (int): знаков после запятой в значении шапки.
    """
    title: str
    fields: tuple[ParamField, ...]
    header_field: str | None = None
    header_unit: str = ""
    header_digits: int = 2


@dataclass(frozen=True)
class ChannelMode:
    """Сегмент переключателя режима: подпись ↔ значение регистра MODE."""
    label: str
    value: int


@dataclass(frozen=True)
class StateFlag:
    """Флаг состояния канала: чип ↔ бит маски ``state`` или отдельное поле кадра.

    Attributes:
        text (str): подпись чипа.
        color (str): семантический цвет — токен темы.
        bit (int | None): номер бита в маске ``state``.
        field (str | None): имя поля кадра (истина — значение ≠ 0); приоритетнее бита.
    """
    text: str
    color: str
    bit: int | None = None
    field: str | None = None


# Плитки телеметрии — одинаковы для всех каналов (поля кадра HVIP).
_MONITORS: tuple[MonitorTile, ...] = (
    MonitorTile("Напряжение, В", "voltage"),
    MonitorTile("Ток, мА", "current"),
    MonitorTile("Обр. связь, В", "v_fb"),
)

# Режимы канала: значение = регистр MODE блока HVIP.
_MODE_FIELD = "mode"
_MODES: tuple[ChannelMode, ...] = (
    ChannelMode("Выключен", 0),
    ChannelMode("Вкл. с огранич. тока", 1),
    ChannelMode("Вкл. без огранич.", 2),
)

# Колонки настроек: уставки канала и коэффициенты ПИД-регулятора.
_COLUMNS: tuple[ParamColumnConfig, ...] = (
    ParamColumnConfig("УСТАВКИ", (
        ParamField("Заданное напряжение", "voltage_desired", "В"),
        ParamField("Ограничение тока", "max_current", "мА"),
        ParamField("Скважность ШИМ", "pwm", "%"),
        ParamField("Код ШИМ", "pwm_raw", "ед.", digits=0),
        ParamField("Предел скважности", "pwm_max", "%"),
    )),
    ParamColumnConfig("ПИД-РЕГУЛЯТОР", (
        ParamField("Общий коэффициент, K", "pid_k", digits=4),
        ParamField("Пропорциональный, P", "pid_p", digits=4),
        ParamField("Интегральный, I", "pid_i", digits=4),
        ParamField("Дифференциальный, D", "pid_d", digits=4),
        ParamField("Предельный шаг", "pid_reaction_max", digits=4),
    ), header_field="pid_error", header_unit="В"),
)

# Флаги состояния канала: биты маски регистра STATE (HVIP_STATE_* прошивки) плюс
# отдельный регистр признака перенапряжения.
_STATE_FLAGS: tuple[StateFlag, ...] = (
    StateFlag("Напряжение в норме", theme.OK, bit=0),
    StateFlag("Превышение тока", theme.ERR, bit=1),
    StateFlag("Ошибка обратной связи", theme.WARN, bit=2),
    StateFlag("Ограничение ШИМ", theme.WARN, bit=3),
    StateFlag("Перенапряжение", theme.ERR, field="flag_overvolt"),
)

_POLL_INTERVAL_S = 2.0      # период опроса блоков HVIP, с (как в PowerControlWidget)
_MIN_POLL_INTERVAL_S = 0.5
_PANEL_MIN_WIDTH = 560      # ниже этой ширины колонки настроек начинают слипаться
_NO_VALUE = "—"             # значение, которого ещё не читали


def _format(value: float | None, digits: int, unit: str = "") -> str:
    """Текст значения поля кадра (``—``, если поле ещё не читали).

    Args:
        value (float | None): значение поля или ``None``.
        digits (int): знаков после запятой.
        unit (str): единица; дописывается через пробел (``""`` — без неё).

    Returns:
        Готовый текст для поля/плитки/шапки колонки.
    """
    if value is None:
        return _NO_VALUE
    text = f"{value:.{digits}f}"
    return f"{text} {unit}" if unit else text


def _parse(text: str) -> float | None:
    """Число из текста поля (``None``, если это не число); запятая = точка."""
    try:
        return float(str(text).replace(",", ".").strip())
    except ValueError:
        return None


class PowerSettingsWidget(QWidget):
    """Три панели настройки каналов HVIP: мониторы · режим · уставки/ПИД · флаги.

    Attributes:
        panels (dict[str, ChannelPowerPanel]): панели каналов по ключу канала.
        state (DeviceState): накопленное состояние регистров каналов.
    """

    panels: dict[str, ChannelPowerPanel]
    state: DeviceState

    def __init__(self, client=None, parent=None) -> None:
        """Собрать панели каналов и подписаться на события связи.

        Args:
            client: ConnectionBar — источник командного интерфейса ЦМ (``None`` в demo).
            parent: родительский виджет.
        """
        super().__init__(parent)
        self.client = client
        self.cm_ib: ModbusCMCommand | None = None   # берётся у ConnectionBar при подключении ЦМ
        self.logger = logger
        self.state = DeviceState()
        self.panels = {}
        self._tasks = AsyncTaskManager()
        self._poll_interval = _POLL_INTERVAL_S
        self._pending: dict[int, dict[str, float]] = {}   # ch -> поля в очереди на запись

        self._build_widget_wholly()
        self._wire_connection()

    # --- сборка --------------------------------------------------------------
    def _build_widget_wholly(self) -> None:
        """Собирает виджет целиком: колонка панелей каналов в прокрутке."""
        vcontainer = QVBoxLayout(self)
        vcontainer.setContentsMargins(0, 0, 0, 0)
        vcontainer.setSpacing(12)
        vcontainer.addWidget(self._build_panels_scroll(), 1)

    def _build_panels_scroll(self) -> QScrollArea:
        """Панели каналов сверху вниз в вертикальном ``QScrollArea``.

        Панель канала высокая (мониторы + форма + флаги), три подряд не влезают в
        рабочую область — лишнее уходит под скролл (как колонка графиков в
        ``PowerControlWidget``).
        """
        holder = QWidget()
        holder.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(holder)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(12)
        for channel in CHANNELS:
            vbox.addWidget(self._build_panel(channel))
        vbox.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(holder)
        scroll.setWidgetResizable(True)                  # ширина панелей = ширине области
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(240)
        # прозрачный контейнер: сливаемся с фоном рабочей зоны, иначе QScrollArea
        # красит свой фон серым из палитры
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setStyleSheet("background: transparent;")  # type: ignore
        return scroll

    def _build_panel(self, channel: ChannelConfig) -> ChannelPowerPanel:
        """Собрать и настроить панель одного канала.

        Зоны панели наполняются данными таблиц модуля (мониторы, режимы, колонки,
        флаги), значения — прочерками до первого чтения.

        Args:
            channel (ChannelConfig): канал (ключ, заголовок, цвет, номер в прошивке).

        Returns:
            Настроенная :class:`ChannelPowerPanel`; ссылка кладётся в
            ``self.panels[channel.key]``.
        """
        panel = ChannelPowerPanel()
        panel.setMinimumWidth(_PANEL_MIN_WIDTH)
        panel.set_title(channel.title, f"канал {channel.ch + 1}", theme.TEXT_DIM)
        panel.set_monitors([(tile.label, _NO_VALUE) for tile in _MONITORS])
        panel.set_modes([mode.label for mode in _MODES], current=0)
        panel.set_param_columns([
            (column.title, [(field.label, _NO_VALUE, field.unit) for field in column.fields])
            for column in _COLUMNS
        ])
        panel.set_states([(flag.text, flag.color, "disabled") for flag in _STATE_FLAGS])
        panel.modeChanged.connect(lambda index, c=channel: self._on_mode(c, index))
        panel.valueEdited.connect(
            lambda column, row, text, c=channel: self._on_value(c, column, row, text))
        self.panels[channel.key] = panel
        return panel

    # --- связь ---------------------------------------------------------------
    def _wire_connection(self) -> None:
        """Подписка на события связи: соединение установлено — взять интерфейс ЦМ
        и запустить опрос; потеряно — остановить."""
        if self.client is None:
            return
        self._refresh_cm()  # начальный интерфейс (до подключения — null-клиент)
        self.client.coroutine_finished.connect(self._on_connection_finished)
        self.client.disconnected.connect(self._on_disconnected)

    @qasync.asyncSlot()
    async def _on_connection_finished(self) -> None:
        """Соединение установлено: обновить интерфейс ЦМ и, если ЦМ отвечает,
        (пере)запустить опрос."""
        self._refresh_cm()
        try:
            ready = await self.client.check_connection()  # type: ignore
        except Exception:
            ready = self.client.is_modbus_ready()  # type: ignore
        if ready:
            self.start_polling()

    def _on_disconnected(self) -> None:
        """Связь потеряна — остановить опрос и выбросить неотправленные правки."""
        self.stop_polling()
        self._pending.clear()

    def _refresh_cm(self) -> None:
        """Свежий командный интерфейс ЦМ."""
        self.cm_ib, _mpp = self.client.get_commands_interface()  # type: ignore

    # --- опрос ---------------------------------------------------------------
    def start_polling(self) -> None:
        """Запустить фоновый опрос каналов HVIP (идемпотентно; без ЦМ — no-op)."""
        if self.cm_ib is None:
            return
        self._tasks.create_task(self._hvip_polling(), "hvip_settings_polling")

    def stop_polling(self) -> None:
        """Остановить фоновый опрос каналов HVIP."""
        self._tasks.cancel_task("hvip_settings_polling")

    def set_poll_interval(self, seconds: float) -> None:
        """Задать период опроса, с (применяется со следующего прохода)."""
        self._poll_interval = max(_MIN_POLL_INTERVAL_S, float(seconds))

    def poll_interval(self) -> float:
        """Текущий период опроса, с."""
        return self._poll_interval

    async def _hvip_polling(self) -> None:
        """Непрерывный опрос каналов, пока задача не отменена."""
        while True:
            await self._polling_step()
            await asyncio.sleep(self._poll_interval)

    async def _polling_step(self) -> None:
        """Один проход: отправить накопленные правки, затем перечитать каналы.

        Порядок важен: сначала запись, потом чтение — панель сразу показывает то,
        что прибор принял (или откатывается к прежнему значению, если не принял).
        """
        await self._flush_pending()
        for channel in CHANNELS:
            if self.cm_ib is None:
                return
            raw = await self.cm_ib.read_hvip(channel.ch)
            if raw == b"-1":
                continue
            self.push_hvip(channel.ch, raw)

    async def _flush_pending(self) -> None:
        """Отправить накопленные правки полей по каналам (по одному пакету на канал)."""
        for ch in list(self._pending):
            values = self._pending.pop(ch, None)
            if not values or self.cm_ib is None:
                continue
            if await self.cm_ib.write_hvip(ch, values) == b"-1":
                self.logger.error(f"HVIP {ch}: не записаны поля {sorted(values)}")

    # --- данные --------------------------------------------------------------
    def push_hvip(self, ch: int, raw: bytes) -> None:
        """Разобрать блок регистров канала и обновить его панель.

        Args:
            ch (int): номер канала HVIP.
            raw (bytes): сырые байты блока (2 байта на регистр, с регистра MODE).
        """
        channel = self._channel(ch)
        if channel is None:
            return
        self.state.update(f"hvip:{ch}", HVIP, raw)
        self._apply_channel(channel)

    def apply_field(self, ch: int, name: str, value: float) -> None:
        """Поставить поле кадра HVIP в очередь записи.

        Пакет уйдёт ближайшим проходом опроса; повторная правка того же поля до
        отправки заменяет предыдущее значение.

        Args:
            ch (int): номер канала HVIP.
            name (str): имя поля кадра (напр. ``"voltage_desired"``).
            value (float): значение в инженерных единицах.
        """
        field = HVIP.field(name)
        if field is None or field.access != "rw":
            self.logger.error(f"HVIP {ch}: поле '{name}' не записывается")
            return
        self._pending.setdefault(ch, {})[name] = value

    def panel(self, key: str) -> ChannelPowerPanel | None:
        """Панель канала по ключу (``'pips'``/``'sipm'``/``'cherenkov'``) или ``None``."""
        return self.panels.get(key)

    @staticmethod
    def _channel(ch: int) -> ChannelConfig | None:
        """Конфигурация канала по его номеру в прошивке или ``None``."""
        return next((channel for channel in CHANNELS if channel.ch == ch), None)

    # --- отрисовка -----------------------------------------------------------
    def _apply_channel(self, channel: ChannelConfig) -> None:
        """Разложить накопленные поля канала по зонам его панели."""
        panel = self.panels[channel.key]
        fields = self.state.get(f"hvip:{channel.ch}")
        self._apply_monitors(panel, fields)
        self._apply_mode(panel, fields, channel)
        self._apply_params(panel, fields)
        self._apply_states(panel, fields)

    @staticmethod
    def _apply_monitors(panel: ChannelPowerPanel, fields: dict[str, float]) -> None:
        """Обновить плитки телеметрии панели."""
        for index, tile in enumerate(_MONITORS):
            panel.set_monitor_value(index, _format(fields.get(tile.field), tile.digits))

    @staticmethod
    def _apply_mode(panel: ChannelPowerPanel, fields: dict[str, float],
                    channel: ChannelConfig) -> None:
        """Синхронизировать переключатель режима и цвет точки состояния канала.

        Точка гаснет (приглушённый цвет) на выключенном канале и горит цветом
        канала на включённом; неизвестное прошивке значение режима переключатель
        не двигает.
        """
        mode = fields.get(_MODE_FIELD)
        if mode is None:
            return
        index = next((i for i, item in enumerate(_MODES) if item.value == int(mode)), None)
        if index is None:
            return
        panel.set_current_mode(index)
        panel.set_status(theme.TEXT_DIM if _MODES[index].value == 0 else channel.color)

    def _apply_params(self, panel: ChannelPowerPanel, fields: dict[str, float]) -> None:
        """Обновить значения колонок настроек и значение в шапке колонки.

        Поле, которое правят прямо сейчас (в фокусе), не трогаем — иначе опрос
        затирал бы ввод под руками.
        """
        for column_index, column in enumerate(_COLUMNS):
            param_column = panel.param_column(column_index)
            if param_column is None:
                continue
            if column.header_field is not None:
                param_column.set_header_value(
                    _format(fields.get(column.header_field), column.header_digits,
                            column.header_unit),
                    theme.TEXT_LABLE)
            for row_index, spec in enumerate(column.fields):
                row = param_column.field(row_index)
                if row is None or row.edit().hasFocus():
                    continue
                row.set_value(_format(fields.get(spec.field), spec.digits))

    @staticmethod
    def _apply_states(panel: ChannelPowerPanel, fields: dict[str, float]) -> None:
        """Обновить чипы флагов состояния канала."""
        mask = fields.get("state")
        for index, flag in enumerate(_STATE_FLAGS):
            chip = panel.state_chip(index)
            if chip is not None:
                chip.set_state(PowerSettingsWidget._flag_state(flag, fields, mask))

    @staticmethod
    def _flag_state(flag: StateFlag, fields: dict[str, float],
                    mask: float | None) -> str:
        """Состояние чипа флага: ``on`` / ``off`` / ``disabled`` (данных ещё нет)."""
        if flag.field is not None:
            value = fields.get(flag.field)
            return "disabled" if value is None else ("on" if value else "off")
        if mask is None or flag.bit is None:
            return "disabled"
        return "on" if int(mask) & (1 << flag.bit) else "off"

    # --- обработчики панели --------------------------------------------------
    def _on_mode(self, channel: ChannelConfig, index: int) -> None:
        """Выбран режим канала — поставить регистр MODE в очередь записи."""
        if not 0 <= index < len(_MODES):
            return
        self.apply_field(channel.ch, _MODE_FIELD, _MODES[index].value)

    def _on_value(self, channel: ChannelConfig, column: int, row: int,
                  text: str) -> None:
        """Правка поля настроек — проверить число и поставить поле в очередь записи.

        Args:
            channel (ChannelConfig): канал, чью панель правят.
            column (int): индекс колонки настроек.
            row (int): индекс строки в колонке.
            text (str): введённый текст.
        """
        spec = self._param_field(column, row)
        if spec is None:
            return
        value = _parse(text)
        if value is None:
            self.logger.error(
                f"{channel.title}: «{text}» — не число, {spec.label} не записано")
            self._apply_params(self.panels[channel.key],
                               self.state.get(f"hvip:{channel.ch}"))
            return
        self.apply_field(channel.ch, spec.field, value)

    @staticmethod
    def _param_field(column: int, row: int) -> ParamField | None:
        """Описание строки настроек по индексам колонки и строки или ``None``."""
        if not 0 <= column < len(_COLUMNS):
            return None
        fields = _COLUMNS[column].fields
        return fields[row] if 0 <= row < len(fields) else None

    def closeEvent(self, a0) -> None:  # noqa: N802 - имя из Qt
        """Снять фоновые задачи вместе с виджетом."""
        self._tasks.cancel_all_tasks()
        super().closeEvent(a0)


def demo_hvip_block(ch: int) -> bytes:
    """Синтетический блок регистров канала HVIP для превью (17 регистров)."""
    words = [
        1 + ch % 2,                 # mode: выключен/с ограничением/без ограничения
        0b0001 | (0b0010 if ch == 1 else 0),   # state: норма (+ превышение тока у ch1)
        1480 + ch * 20,             # pwm_raw
        2260 + ch * 100,            # pwm x100, %
        6500,                       # pwm_max x100, %
        225 + ch,                   # v_fb x100, В
        42015 + ch * 500,           # voltage x100, В
        42000 + ch * 500,           # voltage_desired x100, В
        11870 + ch * 300,           # current x100, мА
        25000,                      # max_current x100, мА
        1 if ch == 2 else 0,        # flag_overvolt
        10000,                      # pid_k x10000
        4500,                       # pid_p x10000
        800,                        # pid_i x10000
        120,                        # pid_d x10000
        35000,                      # pid_reaction_max x10000
        4,                          # pid_error x100, В
    ]
    return b"".join(word.to_bytes(2, "big") for word in words)


if __name__ == "__main__":
    # Сырой запуск (памятка §10): у виджета есть async-слот подключения,
    # поэтому вместо preview — ручной qasync-скелет.
    import sys

    from PyQt6.QtWidgets import QApplication

    from dark_pro_widgets import qss

    app = QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())  # тема ddii (как в приложении)

    host = QWidget()
    host.setWindowTitle("Настройка питания — автономный запуск")
    host.setStyleSheet(f"background-color: {theme.BG};")
    layout = QVBoxLayout(host)
    layout.setContentsMargins(16, 16, 16, 16)
    settings = PowerSettingsWidget()
    layout.addWidget(settings)
    for channel_cfg in CHANNELS:                       # демо-телеметрия во все панели
        settings.push_hvip(channel_cfg.ch, demo_hvip_block(channel_cfg.ch))
    settings.panels["pips"].valueEdited.connect(
        lambda c, r, t: print(f"PIPS: поле [{c},{r}] = {t}"))

    host.resize(1040, 820)
    theme.tint_window_board(int(host.winId()))  # тёмный заголовок ДО show()
    host.show()

    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
