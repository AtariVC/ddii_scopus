"""Различные парсеры
Парсер данных мпп
Парсер log
"""

from src.modbus_worker import ModbusWorker
from src.env_var import EnviramentVar


class Parsers(ModbusWorker, EnviramentVar):
    def __init__(self, **kwargs):
        super().__init__()

    async def pars_telemetria(self, tel: bytes) -> dict:
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

    async def pars_cfg_ddii(self, b: bytes) -> dict:
        d = {}
        ######### УРОВЕНЬ ###########
        d["01_hh_l"] = str(int(self._REV16(b[3:5]).hex(), 16))
        d["05_hh_l"] = str(int(self._REV16(b[5:7]).hex(), 16))
        d["08_hh_l"] = str(int(self._REV16(b[7:9]).hex(), 16))
        d["1_6_hh_l"] = str(int(self._REV16(b[9:11]).hex(), 16))
        d["3_hh_l"] = str(int(self._REV16(b[11:13]).hex(), 16))
        d["5_hh_l"] = str(int(self._REV16(b[13:15]).hex(), 16))
        d["10_hh_l"] = str(int(self._REV16(b[15:17]).hex(), 16))
        d["30_hh_l"] = str(int(self._REV16(b[17:19]).hex(), 16))
        d["60_hh_l"] = str(int(self._REV16(b[19:21]).hex(), 16))
        ######### ВИП PWM ###########
        d["hvip_cfg_pwm_ch"] = "{:.2f}".format(self.byte_to_float(b[21:25]))
        d["hvip_cfg_pwm_pips"] = "{:.2f}".format(self.byte_to_float(b[25:29]))
        d["hvip_cfg_pwm_sipm"] = "{:.2f}".format(self.byte_to_float(b[29:33]))
        ######### ВИП Voltage ###########
        d["hvip_cfg_vlt_ch"] = "{:.2f}".format(self.byte_to_float(b[33:37]))
        d["hvip_cfg_vlt_pips"] = "{:.2f}".format(self.byte_to_float(b[37:41]))
        d["hvip_cfg_vlt_sipm"] = "{:.2f}".format(self.byte_to_float(b[41:45]))
        
        d["mpp_id"] = str(int(self._REV16(b[45:47]).hex(), 16))
        d["interval_measure"] = str(int(self._REV32(b[47:51]).hex(), 16))
        return d
    
    async def pars_mpp_hh(self, b: bytes) -> dict:
        d = {}
        ######### УРОВЕНЬ ###########
        d["05_hh_l"] = str(int((b[1:3]).hex(), 16))
        d["08_hh_l"] = str(int((b[3:5]).hex(), 16))
        d["1_6_hh_l"] = str(int((b[5:7]).hex(), 16))
        d["3_hh_l"] = str(int((b[7:9]).hex(), 16))
        d["5_hh_l"] = str(int((b[9:11]).hex(), 16))
        d["10_hh_l"] = str(int((b[11:13]).hex(), 16))
        d["30_hh_l"] = str(int((b[13:15]).hex(), 16))
        d["60_hh_l"] = str(int((b[15:17]).hex(), 16))
        return d
    
    async def pars_mpp_lvl(self, b: bytes) -> dict:
        d = {}
        d["01_hh_l"] = str(int((b[1:3]).hex(), 16))
        return d

    async def parse_voltage(self, data_v: bytes) -> dict:
        try:
            cherenkov_v = self.byte_to_float(data_v[1:5])
            cherenkov_pwm = self.byte_to_float(data_v[5:9])
            cherenkov_cur = self.byte_to_float(data_v[9:13])
            cherenkov_mode = int(data_v[13:14].hex(), 16)

            pips_v = self.byte_to_float(data_v[15:19])
            pips_pwm = self.byte_to_float(data_v[19:23])
            pips_cur = self.byte_to_float(data_v[23:27])
            pips_mode = int(data_v[27:28].hex(), 16)

            sipm_mode = int(data_v[41:42].hex(), 16)
            sipm_v = self.byte_to_float(data_v[29:33])
            sipm_pwm = self.byte_to_float(data_v[33:37])
            sipm_cur = self.byte_to_float(data_v[37:41])

            data_out = {
                pips_v,
                pips_pwm,
                pips_cur,
                pips_mode,
                sipm_v,
                sipm_pwm,
                sipm_cur,
                sipm_mode,
                cherenkov_v,
                cherenkov_pwm,
                cherenkov_cur,
                cherenkov_mode,
            }
            return data_out
        except Exception as ex:
            self.logger.debug(ex)
            self.logger.exception("message")
            return (0,)
