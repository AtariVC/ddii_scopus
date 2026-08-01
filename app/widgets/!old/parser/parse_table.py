from __future__ import annotations

from dataclasses import dataclass, field

from bytes_parser.frame import Frame
from bytes_parser.row import Row
from pandas import DataFrame
from tabulate import tabulate


ddi_frame: Frame = Frame(
    "Кадр ДДИИ",
    [
        Row("Метка кадра", 2, "04X"),
        Row("Определитель", 2, "X"),
        Row("Номер кадра", 2),
        Row("Время, с", 4),
        Row("Длительность измерения", 2),
        Row("ТЗЧ dE > 1 МэВ/(мг/см^2)", 2),
        Row("ТЗЧ dE > 5 МэВ/(мг/см^2)", 2),
        Row("ТЗЧ dE > 10 МэВ/(мг/см^2)", 2),
        Row("ТЗЧ dE > 20 МэВ/(мг/см^2)", 2),
        Row("ТЗЧ dE > 45 МэВ/(мг/см^2)", 2),
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
        Row("Счетчик общего числа событий E > 1.6 МэВ", 4),
        Row("CRC16", 2, "X"),
    ],
)


@dataclass
class DDIIFrameParser:
    """
    Класс‑обёртка вокруг bytes_parser.Frame для работы с кадром ДДИИ.

    - корректирует "лишние" байты Modbus (если их прислали вместе с кадром);
    - парсит кадр в DataFrame;
    - по требованию печатает результат в консоль в виде таблицы (tabulate).
    """
		
    frame: Frame = field(default_factory=lambda: ddi_frame)

    def _normalize_raw(self, data: bytes | bytearray | str) -> bytes:
        """Приводит вход к ровно frame.full_size байтам."""
        if isinstance(data, str):
            raw = bytes.fromhex(data)
        else:
            raw = bytes(data)

        full_size = self.frame.full_size

        # Если Modbus вернул служебный байт/заголовок, берём последние full_size байт.
        if len(raw) > full_size:
            raw = raw[-full_size:]
        elif len(raw) < full_size:
            raise ValueError(f"Недостаточно данных: ожидалось {full_size} байт, получено {len(raw)}")

        return raw

    def parse(self, data: bytes | bytearray | str) -> DataFrame:
        """Парсит кадр ДДИИ и возвращает DataFrame."""
        raw = self._normalize_raw(data)
        return self.frame.parse(raw)

    def print_table(self, df: DataFrame) -> None:
        """Печатает DataFrame в консоль в виде таблицы."""
        # DataFrame напрямую поддерживается tabulate
        print(tabulate(df, headers="keys", tablefmt="grid", showindex=False))

    def parse_and_print(self, data: bytes | bytearray | str) -> DataFrame:
        """Удобный метод: парсинг + печать таблицы."""
        df = self.parse(data)
        self.print_table(df)
        return df


_parser = DDIIFrameParser()


def parse(data: bytes | bytearray | str) -> DataFrame:
    """
    Упрощённый интерфейс:
    - парсит кадр ДДИИ;
    - печатает результат в консоль (tabulate);
    - возвращает DataFrame.
    """
    return _parser.parse_and_print(data)


__all__ = ["DDIIFrameParser", "ddi_frame", "parse"]
