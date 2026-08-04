"""Кадры прибора: декларативные схемы регистров + лёгкий кодек (decode/encode).

Одна декларация поля-регистра — источник истины и для чтения (обновление UI), и
для записи (пакеты на регистры). Рантайм-путь лёгкий (``dict``/``int``, без pandas);
табличное представление строится по требованию (:func:`to_dataframe`) для
отладки/логов, а не в цикле опроса.

Регистр = 16-битное слово. Поле занимает одно или несколько подряд идущих слов
(``FieldType.words``). ``Field.offset`` — индекс первого слова поля от начала кадра
(совпадает с ``reg`` в прошивке: address = BASE + ch*NUMBER + reg).

Публичное:
* ``FieldType`` — тип поля: ширина в словах + кодек ``слова <-> значение``.
* ``U16`` · ``I16`` · ``U32`` · ``F32`` · ``MASK`` — готовые типы.
* ``Field(name, offset, ftype=U16, scale=1.0, unit="", access="r")`` — одно поле.
* ``Frame(key, fields, byte_order="big")`` — кадр; ``decode`` / ``encode`` / ``span``.
* ``to_dataframe(frame, decoded)`` — табличное представление (ленивый pandas).
"""
from __future__ import annotations

import struct
from collections.abc import Callable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class FieldType:
    """Тип поля: ширина в 16-битных словах и кодек слово<->значение.

    Attributes:
        words (int): сколько подряд идущих регистров занимает поле.
        decode (Callable): список слов -> целое/сырое значение (без scale).
        encode (Callable): целое сырое значение -> список слов.
    """
    words: int
    decode: Callable[[Sequence[int]], int]
    encode: Callable[[int], list[int]]


def _u16_dec(w: Sequence[int]) -> int:
    return w[0]


def _u16_enc(v: int) -> list[int]:
    return [int(v) & 0xFFFF]


def _i16_dec(w: Sequence[int]) -> int:
    return w[0] - 0x10000 if w[0] & 0x8000 else w[0]


def _u32_dec(w: Sequence[int]) -> int:
    return (w[0] << 16) | w[1]


def _u32_enc(v: int) -> list[int]:
    iv = int(v) & 0xFFFFFFFF
    return [(iv >> 16) & 0xFFFF, iv & 0xFFFF]


def _f32_dec(w: Sequence[int]) -> int:
    # big-endian: старшее слово первым; возвращаем float (в int-контракте допустимо)
    return struct.unpack(">f", struct.pack(">HH", w[0], w[1]))[0]


def _f32_enc(v: int) -> list[int]:
    return list(struct.unpack(">HH", struct.pack(">f", float(v))))


U16 = FieldType(1, _u16_dec, _u16_enc)
I16 = FieldType(1, _i16_dec, _u16_enc)          # знак — при decode; пишем те же 16 бит
U32 = FieldType(2, _u32_dec, _u32_enc)
F32 = FieldType(2, _f32_dec, _f32_enc)
MASK = FieldType(1, _u16_dec, _u16_enc)         # как U16, но по смыслу битовая маска


@dataclass(frozen=True)
class Field:
    """Одно поле-регистр кадра.

    Attributes:
        name (str): имя поля (ключ в decode/encode и в UI-биндинге).
        offset (int): индекс первого слова поля от начала кадра (== reg прошивки).
        ftype (FieldType): тип/ширина поля (по умолчанию :data:`U16`).
        scale (float): значение = raw * scale (для ``*X100`` → 0.01, ``*X10000`` → 0.0001).
        unit (str): единица измерения (для подписи/таблицы).
        access (str): ``"r"`` — только чтение, ``"rw"`` — участвует в encode на запись.
    """
    name: str
    offset: int
    ftype: FieldType = U16
    scale: float = 1.0
    unit: str = ""
    access: str = "r"

    @property
    def end(self) -> int:
        """Индекс слова сразу за полем (offset + ширина)."""
        return self.offset + self.ftype.words


@dataclass(frozen=True)
class Frame:
    """Кадр — окно регистров с декларативной раскладкой полей.

    Attributes:
        key (str): ключ кадра (по нему выбирают кадр из реестра).
        fields (tuple[Field, ...]): поля кадра (в любом порядке, адресуются offset).
        byte_order (str): порядок байт в слове, ``"big"`` (modbus) или ``"little"``.
    """
    key: str
    fields: tuple[Field, ...]
    byte_order: str = "big"

    @property
    def span(self) -> int:
        """Полная ширина кадра в словах (максимальный ``end`` по полям)."""
        return max((f.end for f in self.fields), default=0)

    def field(self, name: str) -> Field | None:
        """Поле по имени или ``None``."""
        return next((f for f in self.fields if f.name == name), None)

    def _words(self, raw: bytes) -> list[int]:
        return [int.from_bytes(raw[i:i + 2], self.byte_order) for i in range(0, len(raw) - 1, 2)]

    def decode(self, raw: bytes, start: int = 0) -> dict[str, float]:
        """Разобрать окно регистров, начинающееся со слова ``start``.

        Возвращаются только поля, целиком попавшие в переданные байты — значит
        частичное чтение (под-окно кадра) корректно даёт свой срез полей.

        Args:
            raw (bytes): сырые байты ответа (2 байта на регистр); ``b"-1"`` → пусто.
            start (int): индекс слова, с которого начинается ``raw`` (offset окна).

        Returns:
            ``{имя_поля: значение}`` с применённым scale (масштаб) для покрытых полей.
        """
        if raw == b"-1":
            return {}
        words = self._words(raw)
        out: dict[str, float] = {}
        for f in self.fields:
            lo, hi = f.offset - start, f.end - start
            if lo < 0 or hi > len(words):
                continue  # поле вне окна — пропускаем (частичное чтение)
            raw_val = f.ftype.decode(words[lo:hi])
            out[f.name] = raw_val * f.scale if f.scale != 1.0 else raw_val
        return out

    def encode(self, values: dict[str, float]) -> list[tuple[int, list[int]]]:
        """Собрать записываемые поля в непрерывные группы регистров.

        Берутся только поля из ``values`` c ``access == "rw"``. Смежные по offset
        поля объединяются в один блок — их можно записать одним 0x10.

        Args:
            values (dict[str, float]): значения полей (в инженерных единицах, с учётом scale).

        Returns:
            Список ``(offset, [слова])`` — offset от начала кадра; абсолютный адрес
            (BASE + ch*NUMBER + offset) и обёртку записи добавляет командный слой.
        """
        writable = sorted(
            (f for f in self.fields if f.name in values and f.access == "rw"),
            key=lambda f: f.offset,
        )
        groups: list[tuple[int, list[int]]] = []
        for f in writable:
            raw_val = round(values[f.name] / f.scale) if f.scale != 1.0 else int(values[f.name])
            words = f.ftype.encode(int(raw_val))
            if groups and groups[-1][0] + len(groups[-1][1]) == f.offset:
                groups[-1][1].extend(words)      # смежно с предыдущим блоком — дописываем
            else:
                groups.append((f.offset, list(words)))
        return groups


def to_dataframe(frame: Frame, decoded: dict[str, float]):
    """Табличное представление разобранного кадра (для отладки/логов).

    pandas импортируется лениво — не тянем его в рантайм-путь опроса.

    Args:
        frame (Frame): схема кадра (даёт порядок/единицы/доступ полей).
        decoded (dict[str, float]): результат :meth:`Frame.decode` (можно частичный).

    Returns:
        ``pandas.DataFrame`` со столбцами ``field · value · unit · access`` для
        полей, присутствующих в ``decoded`` (в порядке offset).
    """
    import pandas as pd

    rows = [
        {"field": f.name, "value": decoded[f.name], "unit": f.unit, "access": f.access}
        for f in sorted(frame.fields, key=lambda f: f.offset)
        if f.name in decoded
    ]
    return pd.DataFrame(rows, columns=["field", "value", "unit", "access"])
