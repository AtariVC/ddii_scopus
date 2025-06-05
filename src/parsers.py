"""Различные парсеры
Парсер данных мпп
Парсер log
"""
from src.modbus_worker import ModbusWorker
from src.parsers_pack import LineEObj
import struct


class Parsers(ModbusWorker):
    def __init__(self, **kwargs):
        super().__init__()

    

    async def pars_telemetria(self, tel: bytes) -> dict[str, str]:
        d_tel: dict = {}
        # print(tel)
        tel_b: str = tel[1:2].hex()
        d_tel["working_mode"] = str(int(tel_b, 16))
        # if tel_b == self.DEBUG_MODE:
        # if tel_b == self.COMBAT_MODE | tel_b == self.DEBUG_MODE:
        #     self.radioButton_db_mode.setChecked(True)
        #     self.radioButton_cmbt_mode.setChecked(True)
        # elif tel_b == self.CONSTANT_MODE:
        #     self.radioButton_const_mode.setChecked(True)
        # elif tel_b == self.SILENT_MODE:
        #     self.radioButton_slnt_mode.setChecked(True)

        ######### LEVEL ###########
        tel_b = self._REV16(tel[3:5]).hex()
        d_tel["05_hh_l"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[5:7]).hex()
        d_tel["08_hh_l"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[7:9]).hex()
        d_tel["1_6_hh_l"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[9:11]).hex()
        d_tel["3_hh_l"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[11:13]).hex()
        d_tel["5_hh_l"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[13:15]).hex()
        d_tel["10_hh_l"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[15:17]).hex()
        d_tel["30_hh_l"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[17:19]).hex()
        d_tel["60_hh_l"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[19:21]).hex()
        d_tel["01_hh_l"] = str(int(tel_b, 16))
        ######### ВИП1 ###########
        float_t: float = self.byte_to_float(tel[21:25])
        hvip_ch: str = "{:.2f}".format(float_t)
        d_tel["hvip_ch"] = hvip_ch
        float_t = self.byte_to_float(tel[25:29])
        hvip_pwm_ch: str = "{:.2f}".format(float_t)
        d_tel["hvip_pwm_ch"] = hvip_pwm_ch
        float_t = self.byte_to_float(tel[29:33])
        hvip_current_ch: str = "{:.2f}".format(float_t)
        d_tel["hvip_current_ch"] = hvip_current_ch
        hvip_mode_ch = int(tel[33:34].hex(), 16)  # второй байт мусор
        d_tel["hvip_mode_ch"] = str(int(hvip_mode_ch))
        ######### ВИП2 ###########
        float_t = self.byte_to_float(tel[35:39])
        hvip_pips: str = "{:.2f}".format(float_t)
        d_tel["hvip_pips"] = hvip_pips
        float_t = self.byte_to_float(tel[39:43])
        hvip_pwm_pips: str = "{:.2f}".format(float_t)
        d_tel["hvip_pwm_pips"] = hvip_pwm_pips
        float_t = self.byte_to_float(tel[43:47])
        hvip_current_pips: str = "{:.2f}".format(float_t)
        d_tel["hvip_current_pips"] = hvip_current_pips
        hvip_mode_pips: str = tel[47:48].hex()  # второй байт мусор
        d_tel["hvip_mode_pips"] = str(int(hvip_mode_pips))
        ######### ВИП3 ###########
        float_t = self.byte_to_float(tel[49:53])
        hvip_sipm: str = "{:.2f}".format(float_t)
        d_tel["hvip_sipm"] = hvip_sipm
        float_t = self.byte_to_float(tel[53:57])
        hvip_pwm_sipm: str = "{:.2f}".format(float_t)
        d_tel["hvip_pwm_sipm"] = hvip_pwm_sipm
        float_t = self.byte_to_float(tel[57:61])
        hvip_current_sipm: str = "{:.2f}".format(float_t)
        d_tel["hvip_current_sipm"] = hvip_current_sipm
        hvip_mode_sipm: str = tel[61:62].hex()  # второй байт мусор
        d_tel["hvip_mode_sipm"] = str(int(hvip_mode_sipm))
        ######### TEST CSA ###########
        tel_b = self._REV16(tel[63:64]).hex()
        d_tel["enable_test_csa"] = str(int(tel_b, 16))
        ######### INTERVAL MEASURE ###########
        tel_b = self._REV16(tel[64:66]).hex()
        d_tel["ddii_interval_measure"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[66:68]).hex()
        d_tel["ACQ1"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[68:70]).hex()
        d_tel["ACQ2"] = str(int(tel_b, 16))
        ######### HIST ###########
        tel_b = self._REV16(tel[70:72]).hex()
        d_tel["HCP_1"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[72:74]).hex()
        d_tel["HCP_5"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[74:76]).hex()
        d_tel["HCP_10"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[76:78]).hex()
        d_tel["HCP_20"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[78:80]).hex()
        d_tel["HCP_45"] = str(int(tel_b, 16))
        tel_b = self._REV32(tel[80:84]).hex()
        d_tel["01_hh"] = str(int(tel_b, 16))
        tel_b = self._REV32(tel[84:88]).hex()
        d_tel["05_hh"] = str(int(tel_b, 16))
        tel_b = self._REV32(tel[88:92]).hex()
        d_tel["08_hh"] = str(int(tel_b, 16))
        tel_b = self._REV32(tel[92:96]).hex()
        d_tel["1_6_hh"] = str(int(tel_b, 16))
        tel_b = self._REV32(tel[96:100]).hex()
        d_tel["3_hh"] = str(int(tel_b, 16))
        tel_b = self._REV32(tel[100:104]).hex()
        d_tel["5_hh"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[104:106]).hex()
        d_tel["10_hh"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[106:108]).hex()
        d_tel["30_hh"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[108:110]).hex()
        d_tel["60_hh"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[110:112]).hex()
        d_tel["100_hh"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[112:114]).hex()
        d_tel["200_hh"] = str(int(tel_b, 16))
        tel_b = self._REV16(tel[114:116]).hex()
        d_tel["500_hh"] = str(int(tel_b, 16))

        return d_tel

    async def pars_cfg_ddii(self, b: bytes) -> dict[str, str]:
        d = {}
        
        ######## УРОВЕНЬ ###########
        d["01_hh_l"]              =     str(int(self._REV16(b[3:5]).hex(), 16))
        d["05_hh_l"]              =     str(int(self._REV16(b[5:7]).hex(), 16))
        d["08_hh_l"]              =     str(int(self._REV16(b[7:9]).hex(), 16))
        d["1_6_hh_l"]             =     str(int(self._REV16(b[9:11]).hex(), 16))
        d["3_hh_l"]               =     str(int(self._REV16(b[11:13]).hex(), 16))
        d["5_hh_l"]               =     str(int(self._REV16(b[13:15]).hex(), 16))
        d["10_hh_l"]              =     str(int(self._REV16(b[15:17]).hex(), 16))
        d["30_hh_l"]              =     str(int(self._REV16(b[17:19]).hex(), 16))
        d["60_hh_l"]              =     str(int(self._REV16(b[19:21]).hex(), 16))
    
        ######### ВИП PWM ###########
        d["hvip_cfg_pwm_ch"]      =     "{:.2f}".format(self.byte_to_float(b[21:25]))
        d["hvip_cfg_pwm_pips"]    =     "{:.2f}".format(self.byte_to_float(b[25:29]))
        d["hvip_cfg_pwm_sipm"]    =     "{:.2f}".format(self.byte_to_float(b[29:33]))
        ######### ВИП Voltage ###########
        d["hvip_cfg_vlt_ch"]      =     "{:.2f}".format(self.byte_to_float(b[33:37]))
        d["hvip_cfg_vlt_pips"]    =     "{:.2f}".format(self.byte_to_float(b[37:41]))
        d["hvip_cfg_vlt_sipm"]    =     "{:.2f}".format(self.byte_to_float(b[41:45]))

        d["mpp_id"] = str(int(self._REV16(b[45:47]).hex(), 16))
        d["interval_measure"]     =     str(int(self._REV32(b[47:51]).hex(), 16))
        return d
    
    async def pars_mpp_hh(self, b: bytes) -> dict[str, str]:
        d: dict[str, str] = {}
        ######### УРОВЕНЬ ###########
        d["05_hh_l"]              =     str(int((b[1:3]).hex(), 16))
        d["08_hh_l"]              =     str(int((b[3:5]).hex(), 16))
        d["1_6_hh_l"]             =     str(int((b[5:7]).hex(), 16))
        d["3_hh_l"]               =     str(int((b[7:9]).hex(), 16))
        d["5_hh_l"]               =     str(int((b[9:11]).hex(), 16))
        d["10_hh_l"]              =     str(int((b[11:13]).hex(), 16))
        d["30_hh_l"]              =     str(int((b[13:15]).hex(), 16))
        d["60_hh_l"]              =     str(int((b[15:17]).hex(), 16))
        return d
    
    async def pars_mpp_lvl(self, b: bytes) -> dict[str, str]:
        d: dict[str, str] = {}
        d["01_hh_l"]              =     str(int((b[1:3]).hex(), 16))
        return d

    async def pars_voltage(self, data_v: bytes) -> dict[str, str]:
        d: dict[str, str] = {}

        d["label_ch_v_mes"]       =     str(self.byte_to_float(data_v[1:5]))
        d["label_ch_pwm_mes"]     =     str(self.byte_to_float(data_v[5:9]))
        d["label_ch_cur"]         =     str(self.byte_to_float(data_v[9:13]))
        d["hvip_mode_ch"]         =     str(int(data_v[13:14].hex(), 16))

        d["label_pips_v_mes"]     =     str(self.byte_to_float(data_v[15:19]))
        d["label_pips_pwm_mes"]   =     str(self.byte_to_float(data_v[19:23]))
        d["label_pips_cur"]       =     str(self.byte_to_float(data_v[23:27]))
        d["hvip_mode_pips"]       =     str(int(data_v[27:28].hex(), 16))

        d["label_sipm_v_mes"]     =     str(self.byte_to_float(data_v[29:33]))
        d["label_sipm_pwm_mes"]   =     str(self.byte_to_float(data_v[33:37]))
        d["label_sipm_cur"]       =     str(self.byte_to_float(data_v[37:41]))
        d["hvip_mode_sipm"]       =     str(int(data_v[41:42].hex(), 16))
        return d
    
    async def pars_cfg_volt(self, data_v: bytes) -> dict[str, str]:
        d: dict[str, str] = {}

        d["spinBox_ch_volt"]     =     str(self.byte_to_float(data_v[1:5]))
        d["spinBox_pips_volt"]   =     str(self.byte_to_float(data_v[5:9]))
        d["spinBox_sipm_volt"]   =     str(self.byte_to_float(data_v[9:13]))
        return d

    async def pars_cfg_pwm(self, data_v: bytes) -> dict[str, str]:
        d: dict[str, str] = {}

        d["doubleSpinBox_ch_pwm"]      =     str(self.byte_to_float(data_v[1:5]))
        d["doubleSpinBox_pips_pwm"]    =     str(self.byte_to_float(data_v[5:9]))
        d["doubleSpinBox_sipm_pwm"]    =     str(self.byte_to_float(data_v[9:13]))
        return d

    async def pars_cfg_a_b(self, data_v: bytes) -> dict[str, str]:
        d: dict[str, str] = {}

        d["spinBox_ch_a_u"]         =     str(self.byte_to_float(data_v[1:5]))
        d["spinBox_ch_b_u"]         =     str(self.byte_to_float(data_v[5:9]))
        d["spinBox_ch_a_i"]         =     str(self.byte_to_float(data_v[9:13]))
        d["spinBox_ch_b_i"]         =     str(self.byte_to_float(data_v[13:17]))

        d["spinBox_pips_a_u"]       =     str(self.byte_to_float(data_v[17:21]))
        d["spinBox_pips_b_u"]       =     str(self.byte_to_float(data_v[21:25]))
        d["spinBox_pips_a_i"]       =     str(self.byte_to_float(data_v[25:29]))
        d["spinBox_pips_b_i"]       =     str(self.byte_to_float(data_v[29:33]))

        d["spinBox_sipm_a_u"]       =     str(self.byte_to_float(data_v[33:37]))
        d["spinBox_sipm_b_u"]       =     str(self.byte_to_float(data_v[37:41]))
        d["spinBox_sipm_a_i"]       =     str(self.byte_to_float(data_v[41:45]))
        d["spinBox_sipm_b_i"]       =     str(self.byte_to_float(data_v[45:49]))
        return d

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
    
    async def acq_parser(self, data: bytes) -> list[int]:
        """
        Преобразует кванты АЦП в int
        """
        data_out = [int.from_bytes(data[i:i+2], byteorder='big') for i in range(0, len(data), 2)]
        return data_out
    

    