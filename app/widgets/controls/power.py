"""PowerControlWidget — три панели управления питанием: PIPS, SiPM, Черенковский счётчик.

API:
* ``PowerControlWidget(client=None, parent=None)`` — три сконфигурированные панели
  каналов; ``client`` даёт командный интерфейс (``client.cm``), в demo — ``None``.
* ``panel(key) -> PowerCtrlPanel | None`` — панель канала (``'pips'``/``'sipm'``/``'cherenkov'``).
* ``panels: dict[str, PowerCtrlPanel]`` — все панели по ключу канала.
* ``start_polling()`` / ``stop_polling()`` — запуск/остановка фонового опроса HVIP.
* атрибуты ``panel_pips`` · ``panel_sipm`` · ``panel_cherenkov`` — прямой доступ к панелям.

Телеметрия HVIP разбирается кадром :data:`~app.src.components.frames.HVIP` и
копится в :class:`~app.src.components.frames.DeviceState` (слот ``hvip:<ch>``);
опрос стартует/стопится по подключению ЦМ (``coroutine_finished`` / ``disconnected``);
значения копятся в ``history_measure`` (окно 10 минут) и рисуются на трёх графиках.
"""
from __future__ import annotations

import asyncio
import time

import qasync
from loguru import logger

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget
from dark_pro_widgets.core import theme
from dark_pro_widgets.widgets.composite.control_power_panel import PowerCtrlPanel
from dark_pro_widgets.widgets.composite.plot_graphiclegend import PlotGraphicLegend
from app.src.components.frames import HVIP, DeviceState
from app.src.components.modbus.command_interface import ModbusCMCommand
from app.src.components.modbus.modbus_reg import ModbusReg
from app.src.util.async_task_manager import AsyncTaskManager
from app.widgets.settings.hvip_channels import CHANNELS, ChannelConfig


_PLOT_TITLE = ("Напряжение, В", "Ток, мА", "PWM, %")

# Набор плиток телеметрии и подпись уставки — одинаковы для всех трёх каналов.
_TILES_LABEL = ("Напр., В", "Ток, мА", "PWM, %")
_TILES: list[tuple[str, str]] = [(label, "—") for label in _TILES_LABEL]
_SETPOINT_LABEL = "Уставка, V"
# Потолок уставки: voltage_desired — одно беззнаковое слово, значение = raw * scale.
# Больше него запись молча свернулась бы по модулю 65536 (см. _u16_enc в codec).
_SETPOINT_FIELD = HVIP.field("voltage_desired")
_SETPOINT_MAX = round(0xFFFF * (_SETPOINT_FIELD.scale if _SETPOINT_FIELD else 1.0), 2)

# Плитка (в порядке _TILES_LABEL) -> поле кадра HVIP.
_TILE_FIELDS: tuple[tuple[str, int], ...] = (("voltage", 0), ("current", 1), ("pwm", 2))

# Поля кадра HVIP под графики (в порядке _PLOT_TITLE) и глубина истории трендов.
_PLOT_METRICS: tuple[str, ...] = ("voltage", "current", "pwm")
_HISTORY_SECONDS = 600  # держим историю 10 минут; старьё выкидываем


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
    plot_voltage: PlotGraphicLegend
    plot_current: PlotGraphicLegend
    plot_pwm: PlotGraphicLegend

    def __init__(self, client=None, parent=None) -> None:
        super().__init__(parent)
        self.panels: dict[str, PowerCtrlPanel] = {}
        self.client = client
        self.cm_ib: ModbusCMCommand | None = None      # берётся у ConnectionBar при подключении ЦМ
        self.reg = ModbusReg()
        self.state = DeviceState()                    # накопленное состояние регистров
        self._tasks = AsyncTaskManager()
        self._syncing = False                         # идёт подтяжка тумблеров под телеметрию

        self.logger = logger
        self._poll_interval = 2.0                      # период опроса HVIP, с (как в main_hvip_dialog)
        # окно чтения кадра HVIP начинается со STATE (offset == reg внутри канала)
        self._hvip_window_start = self.reg.hvip_reg.MODE - self.reg.hvip_reg.BASE
        self.history_measure = {ch.key: [] for ch in CHANNELS}
        self._plots: dict[str, PlotGraphicLegend] = {}          # метрика -> график
        self._plot_framed: dict[str, bool] = {m: False for m in _PLOT_METRICS}
        self._history_points = int(_HISTORY_SECONDS / self._poll_interval)  # ~точек в окне
        self._build_widget_wholly()
        self._wire_connection()

    def _wire_connection(self) -> None:
        """Подписка на события связи (как в run_control_widget): соединение
        установлено — взять интерфейс ЦМ и запустить опрос; потеряно — остановить."""
        if self.client is None:
            return
        self._refresh_cm()  # начальный интерфейс (до подключения — null-клиент)
        self.client.coroutine_finished.connect(self._on_connection_finished)
        self.client.disconnected.connect(self._on_disconnected)

    @qasync.asyncSlot()
    async def _on_connection_finished(self) -> None:
        """Соединение установлено: обновить командный интерфейс ЦМ и, если ЦМ
        отвечает, (пере)запустить опрос."""
        self._refresh_cm()
        try:
            ready = await self.client.check_connection() # type: ignore
        except Exception:
            ready = self.client.is_modbus_ready() # type: ignore
        if ready:
            self.start_polling()

    def _on_disconnected(self) -> None:
        """Связь потеряна — остановить опрос."""
        self.stop_polling()

    def _refresh_cm(self) -> None:
        """Свежий командный интерфейс ЦМ"""
        self.cm_ib, _mpp = self.client.get_commands_interface() # type: ignore

    def start_polling(self) -> None:
        """Запустить фоновый опрос HVIP (идемпотентно; без ЦМ — no-op)."""
        if self.cm_ib is None:
            return
        self._tasks.create_task(self._hvip_polling(), "hvip_polling")

    def stop_polling(self) -> None:
        """Остановить фоновый опрос HVIP."""
        self._tasks.cancel_task("hvip_polling")

    def _build_widget_wholly(self):
        """Собирает виджет
        """
        vcontainer = QVBoxLayout(self)
        vcontainer.setContentsMargins(0, 0, 0, 0)
        vcontainer.setSpacing(12)
        # панели в ряд
        hbox_panel = QHBoxLayout()
        hbox_panel.setContentsMargins(0, 0, 0, 0)
        hbox_panel.setSpacing(12)
        for channel in CHANNELS:
            hbox_panel.addWidget(self._build_panel(channel), 1)
        vcontainer.addLayout(hbox_panel)
        # графики — в прокручиваемой колонке: их минимальная высота больше не
        # растягивает окно за пределы экрана, лишнее уходит под вертикальный скролл
        vcontainer.addWidget(self._build_plots_scroll(), 1)

    def _build_plots_scroll(self) -> QScrollArea:
        """Колонка графиков (Напряжение/Ток/PWM) в вертикальном ``QScrollArea``.

        Окно держит разумную высоту (см. ``setMinimumHeight``), а графики со своей
        фиксированной минимальной высотой прокручиваются внутри области.

        Returns:
            Готовый :class:`QScrollArea` с колонкой графиков.
        """
        holder = QWidget()
        holder.setStyleSheet("background: transparent;")
        vbox_plot = QVBoxLayout(holder)
        vbox_plot.setContentsMargins(0, 0, 0, 0)
        vbox_plot.setSpacing(12)
        for metric, title in zip(_PLOT_METRICS, _PLOT_TITLE):
            plot = self._build_plot(title)
            plot.set_max_points(self._history_points)
            self._plots[metric] = plot
            setattr(self, f"plot_{metric}", plot)  # plot_voltage/plot_current/plot_pwm
            vbox_plot.addWidget(plot)

        scroll = QScrollArea()
        scroll.setWidget(holder)
        scroll.setWidgetResizable(True)                                   # ширина графиков = ширине области
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(180)                                      # не схлопывать колонку в ноль
        # прозрачный контейнер: сливаемся с фоном рабочей зоны (WORK_BG),
        # иначе QScrollArea красит свой фон серым из палитры
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setStyleSheet("background: transparent;") # type: ignore
        return scroll

    def _build_plot(self, title: str):
        """Собрать и настроить одну панель канала.

        Args:
            channel: конфигурация канала (цвет точки).

        Returns:
            Настроенная :class:`ChannelConfig`; ссылка также кладётся в
            ``self.plot[channel.key]`` и в атрибут ``plot_<key>``.
        """
        plot = PlotGraphicLegend()
        plot.set_title(title)
        for channel in CHANNELS:
            plot.add_series(channel.title, channel.color, [], visible=True)
        return plot

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
        panel.signal_switch_power.connect(lambda state, ch=channel.ch: self._switch_power(ch, state))  # type: ignore
        panel.signal_set_value.connect(lambda text, ch=channel.ch: self._apply_setpoint(ch, text))  # type: ignore
        self.panels[channel.key] = panel
        setattr(self, f"panel_{channel.key}", panel)
        return panel
    
    def _update_all_tiles(self) -> None:
        """Обновить плитки всех панелей из накопленного состояния."""
        for channel in CHANNELS:
            self._apply_channel_tiles(channel)

    def _apply_channel_tiles(self, channel: ChannelConfig) -> None:
        """Разложить поля состояния канала по плиткам его панели.

        Args:
            channel (ChannelConfig): канал (панель — по ``channel.key``, слот — по ``ch``).
        """
        fields = self.state.get(f"hvip:{channel.ch}")
        panel = self.panels[channel.key]
        for name, index in _TILE_FIELDS:
            if name in fields:
                panel.set_tile_value(index, f"{fields[name]:.2f}")

    async def _request_ch_hvip(self, ch: int) -> bytes:
        """Прочитать окно регистров HVIP одного канала (STATE … CURRENT_X100).

        Args:
            ch (int): номер канала HVIP [0..HVIP_CH_NUM-1].

        Returns:
            Сырые байты окна (по 2 байта на регистр) или ``b"-1"`` при ошибке /
            отсутствии командного интерфейса.
        """
        if self.cm_ib is None:
            return b"-1"
        hvip = self.reg.hvip_reg
        address = hvip.BASE + ch * hvip.NUMBER + self._hvip_window_start
        # окно MODE … CURRENT_X100 — длину считаем от начала окна, иначе последний
        # регистр (ток) выпадает из чтения
        count = hvip.CURRENT_X100 - hvip.BASE - self._hvip_window_start + 1
        return await self.cm_ib.read_registers(address, count)

    def _sync_switch_ch(self) -> None:
        """Подтянуть переключатели панелей под ``mode`` из телеметрии.

        ``setChecked`` испускает ``toggled`` как при клике, и эхо телеметрии
        ушло бы обратно в ЦМ командой записи (а пока команда пользователя в
        полёте — ещё и старым значением). Гасим это флагом ``_syncing``, а не
        ``blockSignals``: ползунок ``ToggleSwitch`` анимируется из собственного
        слота на ``toggled``, и с заглушёнными сигналами он застыл бы в старом
        положении при изменившемся ``isChecked()``.
        """
        self._syncing = True
        try:
            for channel in CHANNELS:
                fields = self.state.get(f"hvip:{channel.ch}")
                if "mode" not in fields:
                    continue  # чтение не удалось — переключатель не трогаем
                self.panels[channel.key].switch_power.setChecked(bool(fields["mode"]))
        finally:
            self._syncing = False

    def _sync_setpoint_ch(self) -> None:
        """Показать уставку канала (``voltage_desired``) в поле панели.

        Поле в фокусе не трогаем: иначе набранное пользователем затиралось бы
        телеметрией на каждом проходе опроса, до нажатия Enter.
        """
        for channel in CHANNELS:
            desired = self.state.value(f"hvip:{channel.ch}", "voltage_desired")
            if desired is None:
                continue
            panel = self.panels[channel.key]
            if panel.lineEdit_setpoint.hasFocus():
                continue
            panel.set_lineEdit_value(f"{desired:.2f}")

    def _switch_power(self, ch: int, state: bool) -> None:
        """Переключатель питания канала — отправить команду ЦМ в фоне.

        Args:
            ch (int): номер канала HVIP [0..HVIP_CH_NUM-1].
            state (bool): требуемое состояние питания.
        """
        if self._syncing:
            return          # тумблер двинула телеметрия, а не пользователь — команду не шлём
        if self.cm_ib is None:
            return
        self._tasks.create_task(self._send_enable_ch(ch, state), f"hvip_enable_{ch}")

    async def _send_enable_ch(self, ch: int, state: bool) -> None:
        """Записать состояние питания канала HVIP (поле ``mode`` его блока)."""
        if self.cm_ib is None:
            return
        if await self.cm_ib.enable_ch_hvip(ch, int(state)) == b"-1":
            self.logger.error(f"HVIP ch{ch}: не удалось переключить питание в {int(state)}")

    def _apply_setpoint(self, ch: int, text: str) -> None:
        """Уставка напряжения канала введена (Enter в поле) — отправить в фоне.

        Args:
            ch (int): номер канала HVIP [0..HVIP_CH_NUM-1].
            text (str): введённое значение, В.
        """
        try:
            voltage = float(text.replace(",", "."))
        except ValueError:
            self.logger.error(f"HVIP ch{ch}: уставка «{text}» — не число")
            return
        if not 0.0 <= voltage <= _SETPOINT_MAX:
            self.logger.error(f"HVIP ch{ch}: уставка {voltage} В вне диапазона 0…{_SETPOINT_MAX} В")
            return
        if self.cm_ib is None:
            return
        self._tasks.create_task(self._send_setpoint_ch(ch, voltage), f"hvip_setpoint_{ch}")

    async def _send_setpoint_ch(self, ch: int, voltage: float) -> None:
        """Записать уставку напряжения канала HVIP (поле ``voltage_desired``)."""
        if self.cm_ib is None:
            return
        if await self.cm_ib.set_vlotage_ch_hvip(ch, voltage) == b"-1":
            self.logger.error(f"HVIP ch{ch}: не удалось записать уставку {voltage} В")

    async def _polling_step(self) -> None:
        """Один проход опроса: по каждому каналу прочитать окно, разобрать кадром
        HVIP в состояние (частичное слияние), обновить плитки, историю и графики."""
        for channel in CHANNELS:
            raw = await self._request_ch_hvip(channel.ch)
            self.state.update(f"hvip:{channel.ch}", HVIP, raw, start=self._hvip_window_start)
        self._update_all_tiles()
        self._record_history()
        self._update_plots()
        self._sync_switch_ch()
        self._sync_setpoint_ch()

    def _record_history(self) -> None:
        """Дописать текущие значения каналов в историю и выкинуть старше 10 минут."""
        now = time.monotonic()
        horizon = now - _HISTORY_SECONDS
        for channel in CHANNELS:
            fields = self.state.get(f"hvip:{channel.ch}")
            if not all(metric in fields for metric in _PLOT_METRICS):
                continue  # неполные данные (напр. ошибка чтения) — этот кадр пропускаем
            hist = self.history_measure[channel.key]
            hist.append({"t": now, **{metric: fields[metric] for metric in _PLOT_METRICS}})
            cut = 0
            while cut < len(hist) and hist[cut]["t"] < horizon:  # старьё — в начале списка
                cut += 1
            if cut:
                del hist[:cut]

    def _update_plots(self) -> None:
        """Отрисовать историю каналов на графиках; после первой отрисовки — фикс вида."""
        for metric, plot in self._plots.items():
            for index, channel in enumerate(CHANNELS):
                hist = self.history_measure[channel.key]
                plot.set_data(index, [record[metric] for record in hist])
            if not self._plot_framed[metric] and any(self.history_measure[c.key] for c in CHANNELS):
                self._freeze_plot_view(plot)
                self._plot_framed[metric] = True

    def _freeze_plot_view(self, plot: PlotGraphicLegend) -> None:
        """Разово подогнать вид под данные и отключить авто-масштаб.

        Дальше новые точки не двигают график: ``set_y_range`` фиксирует Y и гасит
        внутренний ре-скейл TrendPlot (``_auto_y``), а X держим фиксированным окном
        по числу точек истории.
        """
        trend = plot.plot()
        view = trend.getPlotItem().getViewBox()
        view.autoRange()                                   # рамка по текущим данным
        (_x_range, (y_lo, y_hi)) = view.viewRange()
        trend.set_y_range(y_lo, y_hi)                      # фикс Y + выключает авто-масштаб
        view.setXRange(0, self._history_points, padding=0)  # фикс окно по X (индексы точек)

    async def _hvip_polling(self) -> None:
        """Непрерывный опрос HVIP, пока задача не отменена."""
        while True:
            await self._polling_step()
            await asyncio.sleep(self._poll_interval)

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
