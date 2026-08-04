"""Богатое табличное представление кадров через ``bytes_parser`` (отладка/логи).

Мост «наша схема → ``bytes_parser.Frame``»: те же описания полей (см.
:mod:`~app.src.components.frames.device_frames`) дают отладочную таблицу с
колонками ``Value · Numeric · Hex · IsOK · ErrCnt`` — заготовка под полную
вычитку регистров прибора. В рантайм-путь опроса это не идёт (там лёгкий
:meth:`~app.src.components.frames.codec.Frame.decode`); ``bytes_parser`` и pandas
импортируются лениво внутри функций.

Публичное:
* ``build_bp_frame(frame) -> bytes_parser.Frame`` — построить bp-кадр из схемы.
* ``parse_frame(frame, raw) -> DataFrame`` — таблица одного (полного) кадра.
* ``parse_channels(frame, raws) -> (DataFrame, DataFrame)`` — таблицы N каналов.
"""
from __future__ import annotations

import math
import struct

from app.src.components.frames.codec import F32, I16, MASK, Field, Frame


def _decimals(scale: float) -> int:
    """Число знаков после запятой под scale (0.01 → 2, 0.0001 → 4)."""
    if scale >= 1.0:
        return 0
    return max(0, -round(math.log10(scale)))


def _scaled_parser(field: Field):
    """Парсер ``bytes_parser.Row`` с учётом scale/signed/float поля схемы."""
    scale = field.scale
    is_float = field.ftype is F32
    signed = field.ftype is I16

    def parse(row, *args, **kwargs) -> float:
        order = row.byte_order or "big"
        if is_float:
            base = struct.unpack((">f" if order == "big" else "<f"), row.raw_val)[0]
        else:
            base = int.from_bytes(row.raw_val, order, signed=signed)
        return base * scale

    return parse


def _row_for(field: Field):
    """Собрать ``bytes_parser.Row`` для одного поля схемы."""
    import bytes_parser as bp

    size = field.ftype.words * 2
    label = f"{field.name}, {field.unit}" if field.unit else field.name

    if field.ftype is MASK:                       # битовая маска — двоичное представление
        return bp.Row(label, size, str_format="b")
    if field.scale == 1.0:                         # без масштаба — штатный парсер bytes_parser
        fmt = "f" if field.ftype is F32 else "d"
        return bp.Row(label, size, str_format=fmt, signed=field.ftype is I16)
    return bp.Row(                                 # масштаб → кастомный парсер + .Nf формат
        label, size,
        str_format=f".{_decimals(field.scale)}f",
        parser=_scaled_parser(field),
        signed=field.ftype is I16,
    )


def build_bp_frame(frame: Frame):
    """Построить ``bytes_parser.Frame`` из нашей схемы кадра.

    Поля укладываются по возрастанию offset; разрывы между полями заполняются
    строкой ``(reserved)``, чтобы смещения байт совпадали с прошивкой.

    Args:
        frame (Frame): схема кадра.

    Returns:
        ``bytes_parser.Frame``, готовый к ``parse`` / ``parse_table``.
    """
    import bytes_parser as bp

    rows = []
    cursor = 0  # позиция в словах
    for field in sorted(frame.fields, key=lambda f: f.offset):
        if field.offset > cursor:
            rows.append(bp.Row("(reserved)", (field.offset - cursor) * 2, str_format="X"))
        rows.append(_row_for(field))
        cursor = field.end
    return bp.Frame(frame.key, rows, byte_order=frame.byte_order)


def parse_frame(frame: Frame, raw: bytes):
    """Разобрать полный кадр в отладочный ``DataFrame`` (Value/Numeric/Hex/IsOK)."""
    return build_bp_frame(frame).parse(raw)


def parse_channels(frame: Frame, raws):
    """Разобрать несколько каналов (список сырых кадров) в таблицы.

    Args:
        frame (Frame): схема кадра.
        raws (Sequence[bytes]): по одному полному кадру на канал.

    Returns:
        Кортеж ``(значения, ошибки)`` из ``bytes_parser.Frame.parse_table``.
    """
    return build_bp_frame(frame).parse_table(list(raws))
