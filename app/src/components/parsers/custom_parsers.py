"""Различные парсеры
Парсер данных мпп
Парсер log
"""
from app.src.components.modbus.worker import ModbusWorker
from app.src.components.parsers.parsers_pack import LineEObj
import struct

class Parsers(ModbusWorker):
    def __init__(self, **kwargs):
        super().__init__()

    async def pars_everything(self, dataObj: list[LineEObj], bytes_data: bytes, endian: str) -> dict[str, str]:
        d: dict[str, str] = {}
        s_bit = 0
        for i, obj in enumerate(dataObj):
            if obj.tp == "i":
                if endian == "big":
                    d[obj.key] = str(int(bytes_data[s_bit:s_bit+2].hex(), 16))
                if endian == "little":
                    d[obj.key] = str(int(self._REV16(bytes_data[s_bit:s_bit+2]).hex(), 16))
                s_bit += 2

            if obj.tp == "f":
                n_i: int = int(bytes_data[s_bit:s_bit+4].hex(), 16)
                b : bytes = n_i.to_bytes(4, byteorder = endian) # type: ignore
                float_t: float = struct.unpack('!f', b)[0]
                if float_t < -1E6:
                    d[obj.key] = "0"
                else:
                    d[obj.key] = "{:.2f}".format(float_t)
                s_bit += 4
        return d
    
    async def mpp_pars_16b(self, data: bytes) -> list[int]:
        """
        Преобразует кванты АЦП в int
        """
        data_out = [int.from_bytes(data[i:i+2], byteorder='big') for i in range(0, len(data), 2)]
        return data_out
    

    async def mpp_pars_32b(self, data: bytes) -> list[int]:
        """
        Преобразует кванты АЦП в int
        """
        data_out = [int.from_bytes(data[i:i+4], byteorder='big') for i in range(0, len(data), 4)]
        return data_out