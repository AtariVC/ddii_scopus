"""FrameTable — адаптер StatTable для просмотрщика кадров.

API:
* ``FrameTable(title='', dot=theme.OK, parent=None)`` — карточка кадра.
* ``controls`` — самостоятельная панель FramePollControls в шапке.
* ``set_interval(seconds)`` / ``interval() -> int`` — интервал опроса, с.
* ``set_available(bool)`` / ``set_polling(bool)`` — состояние панели.
* ``refreshRequested(bool, int)`` / ``stopRequested()`` — сигналы панели.
"""

from PyQt6.QtCore import pyqtSignal

from dark_pro_widgets import StatTable, theme

from app.widgets.composite.frame_poll_controls import FramePollControls


class FrameTable(StatTable):
    """Карточка кадра с панелью управления в заголовке."""

    refreshRequested = pyqtSignal(bool, int)
    stopRequested = pyqtSignal()

    def __init__(self, title: str = "", dot: str = theme.OK, parent=None) -> None:
        super().__init__(title=title, dot=dot, parent=parent)
        self.controls = FramePollControls(unavailable_hint="Подключите ЦМ, чтобы обновить кадр")
        self.controls.refreshRequested.connect(self.refreshRequested)
        self.controls.stopRequested.connect(self.stopRequested)
        # StatTable не предоставляет публичный слот шапки.
        header = self._tags.parentWidget().layout()
        margins = header.contentsMargins()
        header.setContentsMargins(margins.left(), 8, margins.right(), 8)
        header.addWidget(self.controls)

    def set_interval(self, seconds: int) -> None:
        """Установить период опроса."""
        self.controls.set_interval(seconds)

    def interval(self) -> int:
        """Вернуть период опроса в секундах."""
        return self.controls.interval()

    def set_available(self, available: bool) -> None:
        """Установить доступность панели."""
        self.controls.set_available(available)

    def set_polling(self, active: bool) -> None:
        """Обновить состояние активного опроса."""
        self.controls.set_polling(active)
