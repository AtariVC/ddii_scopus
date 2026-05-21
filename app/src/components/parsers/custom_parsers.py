"""Различные парсеры
Парсер данных мпп
Парсер log
"""
from app.src.components.modbus.modbus_var import ModbusVar
from app.src.components.modbus.worker import ModbusWorker
from app.src.components.parsers.parsers_pack import LineEObj
import struct

class Parsers(ModbusWorker, ModbusVar):
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

    def _normalize_modbus_payload(self, data: bytes) -> bytes:
        if data == b"-1":
            return b""
        return data[1:] if len(data) % 2 else data

    def _u16_values(self, data: bytes, byteorder: str = "big") -> list[int]:
        payload = self._normalize_modbus_payload(data)
        return [
            int.from_bytes(payload[i : i + 2], byteorder=byteorder, signed=False)
            for i in range(0, len(payload) - 1, 2)
        ]

    def _float_values(self, data: bytes, byteorder: str = "little") -> list[float]:
        payload = self._normalize_modbus_payload(data)
        values: list[float] = []
        fmt = "<f" if byteorder == "little" else ">f"
        for i in range(0, len(payload) - 3, 4):
            try:
                values.append(struct.unpack(fmt, payload[i : i + 4])[0])
            except Exception:
                values.append(0.0)
        return values

    async def pars_mpp_lvl(self, data: bytes) -> dict[str, str]:
        values = await self.mpp_pars_16b(self._normalize_modbus_payload(data))
        return {"01_hh_l": str(values[0] if values else 0)}

    async def pars_mpp_hh(self, data: bytes) -> dict[str, str]:
        values = await self.mpp_pars_16b(self._normalize_modbus_payload(data))
        return {f"hh_{idx + 1}": str(value) for idx, value in enumerate(values)}

    async def pars_cfg_volt(self, data: bytes) -> dict[str, str]:
        values = self._float_values(data, "little")
        keys = ["spinBox_ch_volt", "spinBox_pips_volt", "spinBox_sipm_volt"]
        return {key: f"{(values[idx] if idx < len(values) else 0.0):.2f}" for idx, key in enumerate(keys)}

    async def pars_cfg_pwm(self, data: bytes) -> dict[str, str]:
        values = self._float_values(data, "little")
        keys = ["doubleSpinBox_ch_pwm", "doubleSpinBox_pips_pwm", "doubleSpinBox_sipm_pwm"]
        return {key: f"{(values[idx] if idx < len(values) else 0.0):.2f}" for idx, key in enumerate(keys)}

    async def pars_cfg_a_b(self, data: bytes) -> dict[str, str]:
        values = self._float_values(data, "little")
        keys = [
            "spinBox_ch_a_u",
            "spinBox_pips_a_u",
            "spinBox_sipm_a_u",
            "spinBox_ch_b_u",
            "spinBox_pips_b_u",
            "spinBox_sipm_b_u",
            "spinBox_ch_a_i",
            "spinBox_pips_a_i",
            "spinBox_sipm_a_i",
            "spinBox_ch_b_i",
            "spinBox_pips_b_i",
            "spinBox_sipm_b_i",
        ]
        return {key: f"{(values[idx] if idx < len(values) else 0.0):.2f}" for idx, key in enumerate(keys)}

    async def pars_voltage(self, data: bytes) -> dict[str, str]:
        values = self._u16_values(data, "big")
        keys = [
            "label_ch_v_mes",
            "label_ch_pwm_mes",
            "label_ch_cur",
            "hvip_mode_ch",
            "label_pips_v_mes",
            "label_pips_pwm_mes",
            "label_pips_cur",
            "hvip_mode_pips",
            "label_sipm_v_mes",
            "label_sipm_pwm_mes",
            "label_sipm_cur",
            "hvip_mode_sipm",
        ]
        return {key: str(values[idx] if idx < len(values) else 0) for idx, key in enumerate(keys)}

    async def pars_cfg_ddii(self, data: bytes) -> dict[str, str]:
        payload = self._normalize_modbus_payload(data)
        head_big = self.HEAD.to_bytes(2, "big")
        head_little = self.HEAD.to_bytes(2, "little")
        if len(payload) >= 2 and payload[:2] in (head_big, head_little):
            payload = payload[2:]
        values = [
            int.from_bytes(payload[i : i + 2], byteorder="little", signed=False)
            for i in range(0, len(payload) - 1, 2)
        ]
        return {"interval_measure": str(values[-1] if values else 0)}
