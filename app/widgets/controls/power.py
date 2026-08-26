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
значения копятся в ``hystory_measure`` (окно 10 минут) и рисуются на трёх графиках.
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
from app.widgets.controls.hvip_channels import CHANNELS, ChannelConfig


_PLOT_TITLE = ("Напряжение, В", "Ток, мА", "PWM, %")

# Набор плиток телеметрии и подпись уставки — одинаковы для всех трёх каналов.
_TILES_LABEL = ("Напр., В", "Ток, мА", "PWM, %")
_TILES: list[tuple[str, str]] = [(label, "—") for label in _TILES_LABEL]
_SETPOINT_LABEL = "Уставка, V"

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

        self.logger = logger
        self._poll_interval = 2.0                      # период опроса HVIP, с (как в main_hvip_dialog)
        # окно чтения кадра HVIP начинается со STATE (offset == reg внутри канала)
        self._hvip_window_start = self.reg.hvip_reg.STATE - self.reg.hvip_reg.BASE
        self.hystory_measure = {ch.key: [] for ch in CHANNELS}
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
        """Свежий командный интерфейс ЦМ (как в run_control: get_commands_interface)."""
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
        """Собирает виджет целиком
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
            setattr(self, f"plot_{metric}", plot)          # plot_voltage/plot_current/plot_pwm
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
        count = hvip.CURRENT_X100 - hvip.STATE + 1    # окно STATE … CURRENT_X100
        return await self.cm_ib.read_registers(address, count)

    async def _polling_step(self) -> None:
        """Один проход опроса: по каждому каналу прочитать окно, разобрать кадром
        HVIP в состояние (частичное слияние), обновить плитки, историю и графики."""
        for channel in CHANNELS:
            raw = await self._request_ch_hvip(channel.ch)
            self.state.update(f"hvip:{channel.ch}", HVIP, raw, start=self._hvip_window_start)
        self._update_all_tiles()
        self._record_history()
        self._update_plots()

    def _record_history(self) -> None:
        """Дописать текущие значения каналов в историю и выкинуть старше 10 минут."""
        now = time.monotonic()
        horizon = now - _HISTORY_SECONDS
        for channel in CHANNELS:
            fields = self.state.get(f"hvip:{channel.ch}")
            if not all(metric in fields for metric in _PLOT_METRICS):
                continue  # неполные данные (напр. ошибка чтения) — этот кадр пропускаем
            hist = self.hystory_measure[channel.key]
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
                hist = self.hystory_measure[channel.key]
                plot.set_data(index, [record[metric] for record in hist])
            if not self._plot_framed[metric] and any(self.hystory_measure[c.key] for c in CHANNELS):
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
