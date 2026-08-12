"""FrameViewerWidget — просмотрщик кадров прибора: системный кадр и кадр ДДИИ.

API:
* ``FrameViewerWidget(client=None, parent=None)`` — две таблицы кадров и навигация
  по истории; ``client`` (ConnectionBar) даёт командный интерфейс ЦМ, в demo — ``None``.
* ``start_polling()`` / ``stop_polling()`` — запуск/остановка фонового опроса кадров.
* ``set_intervals(intervals)`` — периоды опроса, мс (ключи ``'system'`` / ``'ddii'``).
* ``set_history_depth(depth)`` — глубина окна истории.
* ``push_frame(key, raw)`` — разобрать сырой кадр и положить в историю.
* ``table(key)`` — таблица кадра (:class:`StatTable`) по ключу.

Кадры читаются целиком из debug-регистров ЦМ (``read_system_frame`` /
``read_ddii_frame``), разбираются ``bytes_parser`` по схемам
:mod:`~app.src.components.frames.stream_frames` и складываются в историю на
``_HISTORY_DEPTH`` кадров: окно FIFO — новый кадр вытесняет самый старый.
Стрелки листают историю; на самом свежем кадре (``offset == 0``) вид едет за
опросом, при листании назад — остаётся на выбранном кадре.

Опрос — одна бесконечная задача в :class:`AsyncTaskManager` (шина одна, чтения
идут по очереди), у каждого кадра свой период; периоды и глубина истории
правятся кнопкой ⚙ в верхней панели.
"""
from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass

import qasync
from loguru import logger

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
                             QScrollArea, QVBoxLayout, QWidget)
from dark_pro_widgets.core import theme
from dark_pro_widgets.core.formatting import group_int
from dark_pro_widgets.widgets.composite.stat_table import StatTable
from dark_pro_widgets.widgets.controls.buttons import PrimaryButton
from dark_pro_widgets.widgets.controls.icon_button import IconButton
from dark_pro_widgets.widgets.controls.spin_box import SpinBox

from app.src.components.frames.stream_frames import FRAME_SIZE, parse_stream_frame
from app.src.components.modbus.command_interface import ModbusCMCommand
from app.src.util.async_task_manager import AsyncTaskManager

_MONO = theme.MONO_FAMILY.split(",")[0].strip()


@dataclass(frozen=True)
class FrameConfig:
    """Конфигурация одной карточки кадра.

    Attributes:
        key (str): ключ кадра (``'system'`` / ``'ddii'``) — он же ключ схемы разбора.
        title (str): заголовок карточки до первого разбора.
        dot (str): цвет точки состояния — токен темы.
        reader (str): метод :class:`ModbusCMCommand`, читающий сырой кадр.
        interval_ms (int): период опроса по умолчанию, мс.
    """
    key: str
    title: str
    dot: str
    reader: str
    interval_ms: int


@dataclass(frozen=True)
class FrameRecord:
    """Один кадр в истории: номер кадра и разобранная таблица (``DataFrame``)."""
    number: int | None
    table: object


# Карточки идут слева направо в этом порядке (как в макете).
_FRAMES: list[FrameConfig] = [
    FrameConfig("system", "Системный кадр", theme.ACCENT, "read_system_frame", 1000),
    FrameConfig("ddii", "Кадр ДДИИ", theme.OK, "read_ddii_frame", 1000),
]

_HISTORY_DEPTH = 50          # окно истории кадров (FIFO: новый вытесняет самый старый)
_MIN_HISTORY_DEPTH = 5
_MAX_HISTORY_DEPTH = 500
_MIN_INTERVAL_MS = 100
_MAX_INTERVAL_MS = 600_000
_POLL_TICK = 0.01            # минимальный сон цикла опроса, с (защита от busy loop)
_NUMBER_ROW = "Номер кадра"  # строка кадра, из которой берётся номер для навигации


class FrameViewerWidget(QWidget):
    """Две таблицы кадров (системный · ДДИИ) с навигацией по истории.

    Attributes:
        button_prev (IconButton): шаг к более старому кадру.
        button_next (IconButton): шаг к более свежему кадру.
        button_settings (IconButton): настройка периодов опроса и глубины истории.
        label_counter (QLabel): номер текущего кадра и позиция в истории.
    """

    button_prev: IconButton
    button_next: IconButton
    button_settings: IconButton
    label_counter: QLabel

    def __init__(self, client=None, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.cm_ib: ModbusCMCommand | None = None   # берётся у ConnectionBar при подключении ЦМ
        self.logger = logger
        self._tasks = AsyncTaskManager()

        self._depth = _HISTORY_DEPTH
        self._intervals = {cfg.key: cfg.interval_ms / 1000 for cfg in _FRAMES}
        self._history: dict[str, deque[FrameRecord]] = {
            cfg.key: deque(maxlen=self._depth) for cfg in _FRAMES
        }
        self._offset = 0                            # 0 — самый свежий кадр истории
        self._tables: dict[str, StatTable] = {}

        self._build_widget_wholly()
        self._wire_connection()
        self._refresh_view()

    # --- сборка --------------------------------------------------------------
    def _build_widget_wholly(self) -> None:
        """Собирает виджет целиком: верхняя панель и колонка таблиц."""
        vcontainer = QVBoxLayout(self)
        vcontainer.setContentsMargins(0, 0, 0, 0)
        vcontainer.setSpacing(12)
        vcontainer.addWidget(self._build_topbar())
        vcontainer.addWidget(self._build_tables_scroll(), 1)

    def _build_topbar(self) -> QWidget:
        """Верхняя панель: ⚙ слева, навигация по кадрам справа."""
        bar = QWidget()
        hbox = QHBoxLayout(bar)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(8)

        self.button_settings = IconButton(icon="settings")
        self.button_settings.setToolTip("Настройка опроса кадров")
        self.button_settings.clicked.connect(self.open_settings)

        self.button_prev = IconButton(glyph="chevron_left")
        self.button_prev.setToolTip("Кадр старше")
        self.button_prev.clicked.connect(self.show_older_frame)

        self.button_next = IconButton(glyph="chevron_right")
        self.button_next.setToolTip("Кадр свежее")
        self.button_next.clicked.connect(self.show_newer_frame)

        self.label_counter = QLabel()
        self.label_counter.setTextFormat(Qt.TextFormat.RichText)
        self.label_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_counter.setMinimumWidth(160)
        self.label_counter.setStyleSheet(
            f"color: {theme.TEXT}; font-family: '{_MONO}'; font-size: 14px; "
            "background: transparent; border: none;")

        hbox.addWidget(self.button_settings)
        hbox.addStretch(1)
        hbox.addWidget(self.button_prev)
        hbox.addWidget(self.label_counter)
        hbox.addWidget(self.button_next)
        return bar

    def _build_tables_scroll(self) -> QScrollArea:
        """Две таблицы кадров в ряд, в вертикальном ``QScrollArea``.

        Кадр — это 35 строк, поэтому карточки живут в прокручиваемой области:
        окно держит разумную высоту, а лишнее уходит под скролл (как колонка
        графиков в ``PowerControlWidget``).
        """
        holder = QWidget()
        holder.setStyleSheet("background: transparent;")
        hbox = QHBoxLayout(holder)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(12)
        for cfg in _FRAMES:
            hbox.addWidget(self._build_table(cfg), 1, Qt.AlignmentFlag.AlignTop)

        scroll = QScrollArea()
        scroll.setWidget(holder)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(240)
        # прозрачный контейнер: сливаемся с фоном рабочей зоны, иначе QScrollArea
        # красит свой фон серым из палитры
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setStyleSheet("background: transparent;")  # type: ignore
        return scroll

    def _build_table(self, cfg: FrameConfig) -> StatTable:
        """Собрать таблицу одного кадра.

        Args:
            cfg (FrameConfig): конфигурация кадра (заголовок, цвет точки).

        Returns:
            Настроенная :class:`StatTable`; ссылка кладётся в ``self._tables[cfg.key]``.
        """
        table = StatTable(title=cfg.title, dot=cfg.dot, tags=[f"{FRAME_SIZE} байта"])
        table.setMinimumWidth(360)
        self._tables[cfg.key] = table
        return table

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
        """Связь потеряна — остановить опрос."""
        self.stop_polling()

    def _refresh_cm(self) -> None:
        """Свежий командный интерфейс ЦМ."""
        self.cm_ib, _mpp = self.client.get_commands_interface()  # type: ignore

    # --- опрос ---------------------------------------------------------------
    def start_polling(self) -> None:
        """Запустить фоновый опрос кадров (идемпотентно; без ЦМ — no-op)."""
        if self.cm_ib is None:
            return
        self._tasks.create_task(self._frames_polling(), "frames_polling")

    def stop_polling(self) -> None:
        """Остановить фоновый опрос кадров."""
        self._tasks.cancel_task("frames_polling")

    async def _read_frame(self, cfg: FrameConfig) -> bytes:
        """Прочитать сырой кадр у ЦМ.

        Args:
            cfg (FrameConfig): конфигурация кадра (метод чтения).

        Returns:
            Сырые байты кадра или ``b"-1"`` при ошибке / отсутствии командного
            интерфейса.
        """
        if self.cm_ib is None:
            return b"-1"
        return await getattr(self.cm_ib, cfg.reader)()

    async def _polling_step(self, cfg: FrameConfig) -> None:
        """Один проход опроса кадра: прочитать, разобрать и положить в историю."""
        raw = await self._read_frame(cfg)
        if raw == b"-1":
            return
        self.push_frame(cfg.key, raw)

    async def _frames_polling(self) -> None:
        """Непрерывный опрос кадров, пока задача не отменена.

        У каждого кадра свой период, но задача одна: шина общая, поэтому чтения
        идут по очереди, а не параллельно.
        """
        due = {cfg.key: 0.0 for cfg in _FRAMES}
        while True:
            for cfg in _FRAMES:
                if time.monotonic() >= due[cfg.key]:
                    await self._polling_step(cfg)
                    due[cfg.key] = time.monotonic() + self._intervals[cfg.key]
            await asyncio.sleep(max(min(due.values()) - time.monotonic(), _POLL_TICK))

    # --- история кадров ------------------------------------------------------
    def push_frame(self, key: str, raw: bytes) -> None:
        """Разобрать сырой кадр и положить в историю.

        Args:
            key (str): ключ кадра (``'system'`` / ``'ddii'``).
            raw (bytes): сырые байты кадра (``FRAME_SIZE`` байт).
        """
        try:
            table = parse_stream_frame(key, raw)
        except Exception as ex:  # noqa: BLE001 - битый кадр не должен ронять опрос
            self.logger.debug(f"Кадр '{key}' не разобран: {ex}")
            return
        self._history[key].append(FrameRecord(self._frame_number(table), table))
        if self._offset:
            # пользователь листает историю — держим тот же кадр, а не уезжаем за опросом
            self._offset = min(self._offset + 1, self._max_offset())
        self._refresh_view()

    def clear_history(self) -> None:
        """Очистить историю кадров и вернуться на самый свежий."""
        for history in self._history.values():
            history.clear()
        self._offset = 0
        for cfg in _FRAMES:
            self._tables[cfg.key].clear_rows()
        self._refresh_view()

    def set_history_depth(self, depth: int) -> None:
        """Задать глубину окна истории (старые кадры за окном отбрасываются)."""
        depth = max(_MIN_HISTORY_DEPTH, min(int(depth), _MAX_HISTORY_DEPTH))
        if depth == self._depth:
            return
        self._depth = depth
        self._history = {key: deque(history, maxlen=depth)
                         for key, history in self._history.items()}
        self._offset = min(self._offset, self._max_offset())
        self._refresh_view()

    def set_intervals(self, intervals: dict[str, int]) -> None:
        """Задать периоды опроса кадров в мс (ключи ``'system'`` / ``'ddii'``).

        Применяется на лету: работающая задача опроса берёт период каждый проход.
        """
        for key, interval_ms in intervals.items():
            if key not in self._intervals:
                continue
            self._intervals[key] = max(_MIN_INTERVAL_MS, min(int(interval_ms),
                                                             _MAX_INTERVAL_MS)) / 1000

    def intervals(self) -> dict[str, int]:
        """Текущие периоды опроса кадров, мс."""
        return {key: int(seconds * 1000) for key, seconds in self._intervals.items()}

    def table(self, key: str) -> StatTable | None:
        """Таблица кадра по ключу (``'system'`` / ``'ddii'``) или ``None``."""
        return self._tables.get(key)

    # --- навигация -----------------------------------------------------------
    def show_older_frame(self) -> None:
        """Шаг назад по истории (к более старому кадру)."""
        self._set_offset(self._offset + 1)

    def show_newer_frame(self) -> None:
        """Шаг вперёд по истории (к более свежему кадру)."""
        self._set_offset(self._offset - 1)

    def _set_offset(self, offset: int) -> None:
        """Встать на кадр в ``offset`` шагах от самого свежего."""
        offset = max(0, min(offset, self._max_offset()))
        if offset == self._offset:
            return
        self._offset = offset
        self._refresh_view()

    def _max_offset(self) -> int:
        """Самый дальний шаг назад, на который есть кадры."""
        return max((len(history) for history in self._history.values()), default=0) - 1

    def _record(self, key: str) -> FrameRecord | None:
        """Кадр истории под текущим смещением (``None``, если истории нет).

        Истории кадров независимы (у каждого свой период), поэтому короткая
        история упирается в свой самый старый кадр.
        """
        history = self._history[key]
        if not history:
            return None
        return history[max(len(history) - 1 - self._offset, 0)]

    # --- отрисовка -----------------------------------------------------------
    def _refresh_view(self) -> None:
        """Перерисовать таблицы под текущее смещение и обновить навигацию."""
        for key, table in self._tables.items():
            record = self._record(key)
            if record is not None:
                table.set_dataframe(record.table)
        self._update_nav()

    def _update_nav(self) -> None:
        """Обновить счётчик кадра и доступность стрелок."""
        max_offset = self._max_offset()
        self.button_prev.setEnabled(self._offset < max_offset)
        self.button_next.setEnabled(self._offset > 0)
        self.label_counter.setText(self._counter_html())

    def _counter_html(self) -> str:
        """Текст счётчика: номер кадра и позиция в окне истории."""
        record = self._record("ddii") or self._record("system")
        if record is None:
            return f'<span style="color:{theme.TEXT_DIM}">кадр —</span>'
        number = "—" if record.number is None else group_int(record.number)
        depth = max(len(history) for history in self._history.values())
        return (f'<span style="color:{theme.TEXT}">кадр #{number}</span> '
                f'<span style="color:{theme.TEXT_DIM}">· {depth - self._offset}/{depth}</span>')

    @staticmethod
    def _frame_number(table) -> int | None:
        """Номер кадра из разобранной таблицы (``None``, если строки нет)."""
        labels = list(table[table.columns[0]])
        if _NUMBER_ROW not in labels:
            return None
        return int(list(table["Numeric"])[labels.index(_NUMBER_ROW)])

    # --- настройки -----------------------------------------------------------
    def open_settings(self) -> None:
        """Открыть диалог настройки периодов опроса и глубины истории."""
        dialog = FramePollSettingsDialog(self.intervals(), self._depth, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        intervals, depth = dialog.values()
        self.set_intervals(intervals)
        self.set_history_depth(depth)

    def closeEvent(self, a0) -> None:  # noqa: N802 - имя из Qt
        """Снять фоновые задачи вместе с виджетом."""
        self._tasks.cancel_all_tasks()
        super().closeEvent(a0)


class FramePollSettingsDialog(QDialog):
    """Диалог настройки опроса: период по каждому кадру и глубина истории.

    Attributes:
        spinBox_depth (SpinBox): глубина окна истории, кадров.
    """

    spinBox_depth: SpinBox

    def __init__(self, intervals: dict[str, int], depth: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройка опроса кадров")
        self._spins: dict[str, SpinBox] = {}

        form = QFormLayout(self)
        form.setContentsMargins(20, 18, 20, 16)
        form.setSpacing(12)
        for cfg in _FRAMES:
            self._spins[cfg.key] = self._build_spin(
                _MIN_INTERVAL_MS, _MAX_INTERVAL_MS, intervals.get(cfg.key, cfg.interval_ms),
                step=100)
            form.addRow(f"{cfg.title}, мс", self._spins[cfg.key])
        self.spinBox_depth = self._build_spin(
            _MIN_HISTORY_DEPTH, _MAX_HISTORY_DEPTH, depth, step=5)
        form.addRow("Глубина истории, кадров", self.spinBox_depth)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addStretch(1)
        button_cancel = PrimaryButton("Отмена", variant="neutral", compact=True)
        button_cancel.clicked.connect(self.reject)
        button_apply = PrimaryButton("Применить", variant="accent", compact=True)
        button_apply.clicked.connect(self.accept)
        buttons.addWidget(button_cancel)
        buttons.addWidget(button_apply)
        form.addRow(buttons)

    @staticmethod
    def _build_spin(minimum: int, maximum: int, value: int, step: int) -> SpinBox:
        """Спинбокс с диапазоном и шагом."""
        spin = SpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setValue(int(value))
        return spin

    def values(self) -> tuple[dict[str, int], int]:
        """Настройки из полей: ``({ключ кадра: период, мс}, глубина истории)``."""
        return ({key: spin.value() for key, spin in self._spins.items()},
                self.spinBox_depth.value())


if __name__ == "__main__":
    # Сырой запуск (памятка §10): у виджета есть async-слот подключения,
    # поэтому вместо preview — ручной qasync-скелет.
    import sys

    from PyQt6.QtWidgets import QApplication

    from dark_pro_widgets import qss

    def _demo_raw(key: str, number: int) -> bytes:
        """Синтетический кадр для превью: маркер, номер и правдоподобная начинка."""
        raw = bytearray(FRAME_SIZE)
        raw[0:2] = (0xAA55).to_bytes(2, "big")
        raw[2:4] = (0x0001 if key == "system" else 0x0002).to_bytes(2, "big")
        raw[4:6] = (number & 0xFFFF).to_bytes(2, "big")
        for i in range(6, FRAME_SIZE):
            raw[i] = (number * 7 + i * 13) & 0xFF
        return bytes(raw)

    app = QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())  # тема ddii (как в приложении)

    host = QWidget()
    host.setWindowTitle("Просмотрщик кадров — автономный запуск")
    host.setStyleSheet(f"background-color: {theme.BG};")
    layout = QVBoxLayout(host)
    layout.setContentsMargins(16, 16, 16, 16)
    viewer = FrameViewerWidget()
    layout.addWidget(viewer)
    for demo_number in range(48_200, 48_214):  # история, чтобы стрелки листали
        viewer.push_frame("system", _demo_raw("system", demo_number))
        viewer.push_frame("ddii", _demo_raw("ddii", demo_number))

    host.resize(940, 760)
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
