"""DeviceBinding — единый жизненный цикл задач потребителя ЦМ или МПП.

``DeviceBinding(bar, owner, device, tasks, on_ready, on_stop)``: при подключении
выдаёт командный интерфейс в on_ready; при отключении отменяет все tasks и
вызывает on_stop. Скрытая страница продолжает опрос, удалённая — прекращает.
"""

from PyQt6.QtCore import QObject


class DeviceBinding(QObject):
    """Привязка задач и команд одного виджета к состоянию подключения."""

    def __init__(self, bar, owner, device: str, tasks, on_ready, on_stop) -> None:
        super().__init__(owner)
        if device not in ("cm", "mpp"):
            raise ValueError(f"Неизвестное устройство: {device}")
        self._bar = bar
        self._device = device
        self._tasks = tasks
        self._on_ready = on_ready
        self._on_stop = on_stop
        self._command = None
        bar.coroutine_finished.connect(self._sync)
        bar.settingsChanged.connect(self._sync)
        bar.disconnected.connect(self._stop)
        self.destroyed.connect(tasks.cancel_all_tasks)
        self._sync()

    def _sync(self, *_args) -> None:
        commands = self._bar.get_commands_interface()
        command = commands[0 if self._device == "cm" else 1]
        if command is None:
            self._stop()
        elif command is not self._command:
            if self._command is not None:
                self._stop()
            self._command = command
            self._on_ready(command)

    def _stop(self) -> None:
        self._command = None
        self._tasks.cancel_all_tasks()
        self._on_stop()
