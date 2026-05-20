from __future__ import annotations

from bytes_parser.frame import Frame
from bytes_parser.row import Row


def parse_u32_words(field: Row) -> int:
    raw = field.raw_val
    if len(raw) != 4:
        return int.from_bytes(raw, field.byte_order, signed=field.signed)
    return int.from_bytes(raw[2:4] + raw[0:2], "big", signed=field.signed)


def parse_i16(field: Row) -> int:
    return int.from_bytes(field.raw_val, "big", signed=True)


def u32_row(label: str) -> Row:
    return Row(label, 4, parser=parse_u32_words)


ddii_frame: Frame = Frame(
    "Кадр ДДИИ",
    [
        Row("Метка начала кадра", 2, "X"),
        Row("Определитель кадра", 2, "X"),
        Row("Номер кадра", 2),
        u32_row("Время кадра, с"),
        Row("Длительность измерения, с", 2),
        u32_row("Электроны E > 0.1 МэВ"),
        u32_row("Электроны E > 0.5 МэВ"),
        u32_row("Электроны E > 0.8 МэВ"),
        u32_row("Электроны E > 1.6 МэВ"),
        u32_row("Электроны E > 3 МэВ"),
        u32_row("Электроны E > 5 МэВ"),
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
        u32_row("Счетчик общего числа событий E > 1.6 МэВ"),
        Row("CRC16", 2, "X"),
    ],
)

system_frame: Frame = Frame(
    "Системный кадр",
    [
        Row("Метка начала кадра", 2, "X"),
        Row("Определитель кадра", 2, "X"),
        Row("Номер кадра", 2),
        u32_row("Время кадра, с"),
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
        u32_row("Время работы, с"),
        Row("Объем FRAM, кадров", 2),
        Row("Температура", 2, parser=parse_i16),
        Row("Указатель чтения", 2),
        Row("Указатель записи", 2),
        Row("Версия ПО", 2, "X"),
        Row("CRC16", 2, "X"),
    ],
)


def normalize_frame_raw(frame: Frame, data: bytes | bytearray | str) -> bytes:
    raw = bytes.fromhex(data) if isinstance(data, str) else bytes(data)
    if len(raw) > frame.full_size:
        raw = raw[-frame.full_size :]
    if len(raw) != frame.full_size:
        raise ValueError(f"Ожидалось {frame.full_size} байт, получено {len(raw)}")
    return raw


def parse_ddii_frame(data: bytes | bytearray | str):
    return ddii_frame.parse(normalize_frame_raw(ddii_frame, data))


def parse_system_frame(data: bytes | bytearray | str):
    return system_frame.parse(normalize_frame_raw(system_frame, data))
