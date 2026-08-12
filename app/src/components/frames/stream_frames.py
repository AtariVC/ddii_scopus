"""Кадры потока прибора (``bytes_parser``): системный кадр и кадр ДДИИ.

Оба кадра — по 64 байта (32 регистра), читаются целиком из debug-регистров ЦМ
(``ModbusCMCommand.read_system_frame`` / ``read_ddii_frame``). Разбор даёт
``DataFrame`` со столбцами ``Value · Numeric · Hex · IsOK · ErrCnt`` — его
напрямую принимает ``StatTable.set_dataframe`` (см. ``frame_viewer.py``).

Поля здесь байтовые (не регистровые): один регистр может нести два поля
(напр. «PWM raw» + «состояние» HVIP), поэтому раскладка описана
``bytes_parser``, а не register-ориентированным кодеком
:mod:`~app.src.components.frames.codec`.

Публичное:
* ``SYSTEM_FRAME`` · ``DDII_FRAME`` — схемы кадров.
* ``parse_system_frame(raw)`` · ``parse_ddii_frame(raw)`` — байты -> ``DataFrame``.
* ``FRAME_SIZE`` — размер кадра в байтах.
"""
from __future__ import annotations

from bytes_parser.frame import Frame
from bytes_parser.row import Row

#: Размер обоих кадров: 32 регистра по 2 байта.
FRAME_SIZE = 64


def parse_u32_words(field: Row) -> int:
    """Разобрать 32-битное поле с порядком слов прошивки (младшее слово первым)."""
    raw = field.raw_val
    if len(raw) != 4:
        return int.from_bytes(raw, field.byte_order, signed=field.signed)
    return int.from_bytes(raw[2:4] + raw[0:2], "big", signed=field.signed)


def parse_i16(field: Row) -> int:
    """Разобрать знаковое 16-битное поле (температура)."""
    return int.from_bytes(field.raw_val, "big", signed=True)


def u32_row(label: str) -> Row:
    """Строка на 4 байта с обратным порядком слов (младшее слово первым).

    Пока не используется: прошивка отдаёт 32-битные поля старшим словом вперёд
    (как штатный big-endian ``Row(label, 4)``). Готовый парсер оставлен на случай
    полей с обратным порядком слов.
    """
    return Row(label, 4, parser=parse_u32_words)


DDII_FRAME: Frame = Frame(
    "Кадр ДДИИ",
    [
        Row("Метка начала кадра", 2, "X"),
        Row("Определитель кадра", 2, "X"),
        Row("Номер кадра", 2),
        Row("Время кадра, с", 4),
        Row("Длительность измерения, с", 2),
        Row("Электроны E > 0.1 МэВ", 4),
        Row("Электроны E > 0.5 МэВ", 4),
        Row("Электроны E > 0.8 МэВ", 4),
        Row("Электроны E > 1.6 МэВ", 4),
        Row("Электроны E > 3 МэВ", 4),
        Row("Электроны E > 5 МэВ", 4),
        Row("Протоны E > 10 МэВ", 2),
        Row("Протоны E > 30 МэВ", 2),
        Row("Протоны E > 60 МэВ", 2),
        Row("Протоны E > 100 МэВ", 2),
        Row("Протоны E > 200 МэВ", 2),
        Row("Протоны E > 500 МэВ", 2),
        Row("ТЗЧ E > 1 МэВ", 2),
        Row("ТЗЧ E > 5 МэВ", 2),
        Row("ТЗЧ E > 10 МэВ", 2),
        Row("ТЗЧ E > 20 МэВ", 2),
        Row("ТЗЧ E > 45 МэВ", 2),
        Row("Счетчик общего числа событий E > 1.6 МэВ", 4),
        Row("CRC16", 2, "X"),
    ],
)

SYSTEM_FRAME: Frame = Frame(
    "Системный кадр",
    [
        Row("Метка начала кадра", 2, "X"),
        Row("Определитель кадра", 2, "X"),
        Row("Номер кадра", 2),
        Row("Время кадра, с", 4),
        Row("HVIP 1: PWM raw", 1),
        Row("HVIP 1: состояние", 1),
        Row("HVIP 1: U HV", 2),
        Row("HVIP 1: U заданное", 2),
        Row("HVIP 1: ток", 2),
        Row("HVIP 2: PWM raw", 1),
        Row("HVIP 2: состояние", 1),
        Row("HVIP 2: U HV", 2),
        Row("HVIP 2: U заданное", 2),
        Row("HVIP 2: ток", 2),
        Row("HVIP 3: PWM raw", 1),
        Row("HVIP 3: состояние", 1),
        Row("HVIP 3: U HV", 2),
        Row("HVIP 3: U заданное", 2),
        Row("HVIP 3: ток", 2),
        Row("Уровень MPP", 2),
        Row("PD K, кэВ/LSB", 2),
        Row("SC K, кэВ/LSB", 2),
        Row("PD B, кэВ/LSB", 2),
        Row("Счетчик таймаутов", 2),
        Row("Счетчик перезапусков", 1),
        Row("Статус неответов", 1),
        Row("Резерв", 1),
        Row("Статус ЦМ", 1),
        Row("Время работы, с", 4),
        Row("Объем FRAM, кадров", 2),
        Row("Температура", 2, parser=parse_i16),
        Row("Указатель чтения", 2),
        Row("Указатель записи", 2),
        Row("Версия ПО", 2, "X"),
        Row("CRC16", 2, "X"),
    ],
)

#: Ключ кадра -> схема (ключи совпадают с ключами карточек просмотрщика).
STREAM_FRAMES: dict[str, Frame] = {"system": SYSTEM_FRAME, "ddii": DDII_FRAME}


def normalize_frame_raw(frame: Frame, data: bytes | bytearray | str) -> bytes:
    """Привести сырые данные к размеру кадра (хвост длиннее — обрезать слева).

    Args:
        frame (Frame): схема кадра.
        data (bytes | bytearray | str): байты или hex-строка.

    Returns:
        Ровно ``frame.full_size`` байт.

    Raises:
        ValueError: длины не совпали.
    """
    raw = bytes.fromhex(data) if isinstance(data, str) else bytes(data)
    if len(raw) > frame.full_size:
        raw = raw[-frame.full_size:]
    if len(raw) != frame.full_size:
        raise ValueError(f"Ожидалось {frame.full_size} байт, получено {len(raw)}")
    return raw


def parse_ddii_frame(data: bytes | bytearray | str):
    """Разобрать кадр ДДИИ в ``DataFrame``."""
    return DDII_FRAME.parse(normalize_frame_raw(DDII_FRAME, data))


def parse_system_frame(data: bytes | bytearray | str):
    """Разобрать системный кадр в ``DataFrame``."""
    return SYSTEM_FRAME.parse(normalize_frame_raw(SYSTEM_FRAME, data))


def parse_stream_frame(key: str, data: bytes | bytearray | str):
    """Разобрать кадр по ключу (``'system'`` / ``'ddii'``) в ``DataFrame``."""
    frame = STREAM_FRAMES[key]
    return frame.parse(normalize_frame_raw(frame, data))
