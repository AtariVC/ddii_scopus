"""DeviceState — живое состояние регистров прибора со слиянием частичных чтений.

Держит по «слоту» (кадр или кадр+канал, напр. ``"hvip:0"``) словарь разобранных
полей. Каждое чтение обновляет **только** пришедшие поля (:meth:`update`), остальные
сохраняются — поэтому частичное чтение окна регистров не затирает остальную
телеметрию. Тяжёлый ``DataFrame`` строится по требованию из уже разобранного
состояния, а не в цикле опроса.

Публичное:
* ``DeviceState()`` — пустое состояние.
* ``update(slot, frame, raw, start=0) -> dict`` — разобрать окно и слить в слот.
* ``get(slot) -> dict`` · ``value(slot, name, default=None)`` — чтение состояния.
* ``dataframe(slot, frame) -> pandas.DataFrame`` — таблица слота (ленивый pandas).
"""
from __future__ import annotations

from app.src.components.frames.codec import Frame, to_dataframe


class DeviceState:
    """Состояние регистров прибора по слотам с частичным слиянием полей."""

    def __init__(self) -> None:
        self._state: dict[str, dict[str, float]] = {}

    def update(self, slot: str, frame: Frame, raw: bytes, start: int = 0) -> dict[str, float]:
        """Разобрать окно и слить его поля в слот (частично, не затирая прочие).

        Args:
            slot (str): ключ слота, напр. ``"hvip:0"`` (кадр+канал).
            frame (Frame): схема кадра для разбора.
            raw (bytes): сырые байты окна (2 байта на регистр).
            start (int): offset слова, с которого начинается ``raw`` (для под-окон).

        Returns:
            Только что разобранные поля (то, что реально пришло в этом чтении).
        """
        decoded = frame.decode(raw, start)
        self._state.setdefault(slot, {}).update(decoded)
        return decoded

    def get(self, slot: str) -> dict[str, float]:
        """Копия всех накопленных полей слота (пустой ``{}``, если слота нет)."""
        return dict(self._state.get(slot, {}))

    def value(self, slot: str, name: str, default: float | None = None) -> float | None:
        """Значение одного поля слота или ``default``, если его ещё не читали."""
        return self._state.get(slot, {}).get(name, default)

    def dataframe(self, slot: str, frame: Frame):
        """Табличное представление слота (ленивый pandas) — для отладки/лога."""
        return to_dataframe(frame, self.get(slot))
