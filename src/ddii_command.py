import asyncio
import struct
from copy import copy
from typing import Any, Awaitable, Callable, Coroutine, Optional

import qasync
from pymodbus.client import AsyncModbusSerialClient
from pymodbus.pdu import ModbusResponse

from src.env_var import EnvironmentVar
from src.log_config import log_s, set_serial_log_enabled
from src.modbus_worker import ModbusWorker


class ModbusCMCommand(EnvironmentVar):
    def __init__(self, client, logger, *, log_enabled: bool = True, serial_log_enabled: bool = True, **kwargs):
        super().__init__()
        self.mw = ModbusWorker()
        self.client: AsyncModbusSerialClient = client
        # Swap to no-op logger if disabled
        self.logger = logger if log_enabled else _NoopLogger()
        # Apply global serial log flag for TX/RX dumps
        set_serial_log_enabled(serial_log_enabled)

    def _cm_hvip_app_ch_to_fw_ch(self, ch: int) -> int:
        ch_map = {
            self.CHERENKOV_CH_VOLTAGE: 0,
            self.PIPS_CH_VOLTAGE: 1,
            self.SIPM_CH_VOLTAGE: 2,
        }
        return ch_map.get(ch, max(0, min(2, ch)))

    def _parse_u16_response(self, answer: bytes) -> list[int]:
        payload = answer[1:] if len(answer) > 1 else b""
        return [
            int.from_bytes(payload[i:i + 2], byteorder="big", signed=False)
            for i in range(0, len(payload) - 1, 2)
        ]

    def _legacy_float_bytes(self, value: float) -> bytes:
        return struct.pack("<f", float(value))

    def _legacy_regs_to_float(self, regs: list[int]) -> float:
        payload = b"".join((reg & 0xFFFF).to_bytes(2, "big") for reg in regs[:2])
        if len(payload) < 4:
            return 0.0
        return struct.unpack("!f", int(payload.hex(), 16).to_bytes(4, byteorder="little"))[0]

    async def read_cm_registers(self, address: int, count: int) -> bytes:
        """Read raw CM holding registers."""
        try:
            result: ModbusResponse = await self.client.read_holding_registers(address, count, slave=self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')
            return b'-1'

    async def read_cm_u16_registers(self, address: int, count: int) -> list[int]:
        return self._parse_u16_response(await self.read_cm_registers(address, count))

    async def write_cm_registers(self, address: int, values: list[int] | int) -> bytes:
        """Write raw CM holding registers."""
        try:
            result: ModbusResponse = await self.client.write_registers(address=address, values=values, slave=self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')
            return b'-1'

    async def cm_legacy_debug_command(self, command_addr: int, value: int = 0) -> bytes:
        return await self.write_cm_registers(command_addr, value)

    async def cm_legacy_switch_debug(self, enabled: int) -> bytes:
        return await self.cm_legacy_debug_command(self.CM_DBG_CMD_SWITCH_ON_OFF, enabled & 0x01)

    async def cm_legacy_reset(self) -> bytes:
        return await self.cm_legacy_debug_command(self.CM_DBG_CMD_CM_RESET)

    async def cm_legacy_check_memory(self) -> bytes:
        return await self.cm_legacy_debug_command(self.CM_DBG_CMD_CM_CHECK_MEM)

    async def cm_legacy_init(self) -> bytes:
        return await self.cm_legacy_debug_command(self.CM_DBG_CMD_CM_INIT, 0xAA55)

    async def cm_legacy_request_archive_frame(self) -> bytes:
        return await self.cm_legacy_debug_command(self.CM_DBG_CMD_ARCH_REQUEST)

    async def read_cm_debug_map(self) -> bytes:
        return await self.read_cm_registers(self.MB_DBG_REG_BASE, self.MB_DBG_REG_NUMBER)

    async def write_cm_debug_register(self, reg_offset: int, value: int) -> bytes:
        return await self.write_cm_registers(self.MB_DBG_REG_BASE + reg_offset, value)

    async def run_cm_debug_command(self, command_mask: int) -> bytes:
        return await self.write_cm_debug_register(self.MB_DBG_REG_COMMAND, command_mask)

    async def cm_debug_init(self) -> bytes:
        return await self.run_cm_debug_command(self.MB_DBG_CMD_CM_INIT)

    async def cm_format_memory(self) -> bytes:
        return await self.run_cm_debug_command(self.MB_DBG_CMD_MEM_FORMAT)

    async def cm_clear_frame_fifo(self) -> bytes:
        return await self.run_cm_debug_command(self.MB_DBG_CMD_FIFO_CLEAR)

    async def cm_reset_memory_read_pointer(self) -> bytes:
        return await self.run_cm_debug_command(self.MB_DBG_CMD_MEM_RD_PTR_ZERO)

    async def cm_prepare_ddii_frame(self) -> bytes:
        return await self.run_cm_debug_command(self.MB_DBG_CMD_PREPARE_FRAME)

    async def cm_prepare_sys_frame(self) -> bytes:
        return await self.run_cm_debug_command(self.MB_DBG_CMD_PREPARE_SYS_FRAME)

    async def cm_ctrl_command(self, ctrl_cmd: int, ctrl_data: list[int] | None = None) -> bytes:
        payload = [ctrl_cmd] + (ctrl_data or [])
        return await self.write_cm_registers(self.CM_DBG_CMD_CTRL, payload)

    async def read_cm_ddii_frame(self) -> bytes:
        return await self.read_cm_registers(self.MB_DDII_FRAME_REG_BASE, self.MB_DDII_FRAME_REG_NUMBER)

    async def read_cm_sys_frame(self) -> bytes:
        return await self.read_cm_registers(self.MB_SYS_FRAME_REG_BASE, self.MB_SYS_FRAME_REG_NUMBER)

    async def read_cm_cfg_report(self) -> bytes:
        return await self.read_cm_registers(self.MB_CFG_REG_BASE, self.MB_CFG_REG_NUMBER)

    async def write_cm_cfg_report(self, data: list[int]) -> bytes:
        if data and data[0] == self.HEAD:
            data = data[1:]
        return await self.write_cm_registers(self.MB_CFG_REG_BASE, data)

    async def select_cm_hvip_channel(self, ch: int) -> bytes:
        return await self.write_cm_registers(self.REG_CM_HVIP_CH_SELECT, self._cm_hvip_app_ch_to_fw_ch(ch))

    async def read_cm_hvip_debug(self, ch: int | None = None) -> bytes:
        if ch is not None:
            await self.select_cm_hvip_channel(ch)
        return await self.read_cm_registers(self.MB_HVIP_REG_BASE, self.MB_HVIP_REG_NUMBER)

    async def read_cm_hvip_debug_values(self, ch: int | None = None) -> list[int]:
        return self._parse_u16_response(await self.read_cm_hvip_debug(ch))

    async def write_cm_hvip_debug_register(self, reg_offset: int, value: int, ch: int | None = None) -> bytes:
        if ch is not None:
            await self.select_cm_hvip_channel(ch)
        return await self.write_cm_registers(self.MB_HVIP_REG_BASE + reg_offset, value)

    async def set_cm_debug_enabled(self, enabled: int) -> bytes:
        return await self.write_cm_registers(self.REG_CM_DBG_ENABLE, enabled & 0x01)

    async def set_cm_const_mode(self, enabled: int) -> bytes:
        return await self.write_cm_registers(self.REG_CM_DBG_CONST_MODE, enabled & 0x01)

    async def set_cm_meas_interval_ms(self, interval_ms: int) -> bytes:
        return await self.write_cm_registers(self.REG_CM_DBG_MEAS_INTERVAL_MS, interval_ms)

    async def set_cm_ddii_interval_ms(self, interval_ms: int) -> bytes:
        return await self.write_cm_registers(self.REG_CM_DBG_DDII_INTERVAL_MS, interval_ms)

    async def get_cm_command_result(self) -> bytes:
        return await self.read_cm_registers(self.REG_CM_DBG_COMMAND_RESULT, 1)

    async def get_cm_status(self) -> bytes:
        return await self.read_cm_registers(self.REG_CM_DBG_STATUS, 1)

    async def set_cm_hvip_voltage(self, ch: int, voltage: float) -> bytes:
        return await self.write_cm_hvip_debug_register(
            self.MB_HVIP_REG_V_HV_DESIRED_X100,
            int(round(voltage * 100.0)),
            ch,
        )

    async def set_cm_hvip_pwm(self, ch: int, pwm: float) -> bytes:
        return await self.write_cm_hvip_debug_register(self.MB_HVIP_REG_PWM_X100, int(round(pwm * 100.0)), ch)

    async def set_cm_hvip_mode(self, ch: int, mode: int) -> bytes:
        return await self.write_cm_hvip_debug_register(self.MB_HVIP_REG_MODE, mode, ch)

    async def _read_hvip_channels(self) -> dict[int, list[int]]:
        channels = (self.CHERENKOV_CH_VOLTAGE, self.PIPS_CH_VOLTAGE, self.SIPM_CH_VOLTAGE)
        return {ch: await self.read_cm_hvip_debug_values(ch) for ch in channels}

    def _hvip_value_x100(self, regs: list[int], offset: int) -> float:
        return (regs[offset] if len(regs) > offset else 0) / 100.0

    async def get_cfg_voltage(self) -> bytes:
        channels = await self._read_hvip_channels()
        payload = b"".join(
            self._legacy_float_bytes(self._hvip_value_x100(channels[ch], self.MB_HVIP_REG_V_HV_DESIRED_X100))
            for ch in (self.CHERENKOV_CH_VOLTAGE, self.PIPS_CH_VOLTAGE, self.SIPM_CH_VOLTAGE)
        )
        return bytes([len(payload)]) + payload

    async def write_mem_ptr(self, rad_ptr: int) -> bytes:
        return await self.write_cm_registers(self.REG_CM_DBG_MEM_RD_PTR, rad_ptr)

    async def read_mem(self) -> bytes:
        return await self.read_cm_sys_frame()

    async def set_csa_test_enable(self, state) -> bytes:
        return await self.set_cm_debug_enabled(int(state))

    async def set_mode(self, mode) -> bytes:
        if mode == self.CONSTANT_MODE:
            await self.set_cm_debug_enabled(1)
            return await self.set_cm_const_mode(1)
        if mode == self.DEBUG_MODE:
            await self.set_cm_const_mode(0)
            return await self.set_cm_debug_enabled(1)
        await self.set_cm_const_mode(0)
        return await self.set_cm_debug_enabled(0)

    async def get_desired_voltage(self) -> bytes:
        channels = await self._read_hvip_channels()
        return b"".join(
            struct.pack(">f", self._hvip_value_x100(channels[ch], self.MB_HVIP_REG_V_HV_DESIRED_X100))
            for ch in (self.CHERENKOV_CH_VOLTAGE, self.PIPS_CH_VOLTAGE, self.SIPM_CH_VOLTAGE)
        )

    async def get_cfg_pwm(self) -> bytes:
        channels = await self._read_hvip_channels()
        payload = b"".join(
            self._legacy_float_bytes(self._hvip_value_x100(channels[ch], self.MB_HVIP_REG_PWM_X100))
            for ch in (self.CHERENKOV_CH_VOLTAGE, self.PIPS_CH_VOLTAGE, self.SIPM_CH_VOLTAGE)
        )
        return bytes([len(payload)]) + payload

    async def get_term(self) -> bytes:
        return b'-1'

    async def get_cfg_a_b(self) -> bytes:
        return b'-1'

    async def get_telemetry(self) -> bytes:
        return await self.read_cm_debug_map()

    async def get_cfg_ddii(self) -> bytes:
        return await self.read_cm_cfg_report()

    async def set_cfg_ddii(self, data: list[int] | int) -> bytes:
        if isinstance(data, int):
            data = [data]
        return await self.write_cm_cfg_report(data)

    async def get_voltage(self) -> bytes:
        channels = await self._read_hvip_channels()
        payload = bytearray()
        for ch in (self.CHERENKOV_CH_VOLTAGE, self.PIPS_CH_VOLTAGE, self.SIPM_CH_VOLTAGE):
            regs = channels[ch]
            payload.extend(self._legacy_float_bytes(self._hvip_value_x100(regs, self.MB_HVIP_REG_V_HV_X100)))
            payload.extend(self._legacy_float_bytes(self._hvip_value_x100(regs, self.MB_HVIP_REG_PWM_X100)))
            payload.extend(self._legacy_float_bytes(self._hvip_value_x100(regs, self.MB_HVIP_REG_CURRENT_X100)))
            payload.extend(bytes([regs[self.MB_HVIP_REG_MODE] if len(regs) > self.MB_HVIP_REG_MODE else 0, 0]))
        return bytes([len(payload)]) + bytes(payload)

    async def switch_power(self, data: list[int]) -> bytes:
        if len(data) < 2:
            self.logger.error("switch_power ожидает [channel, state]")
            return b'-1'
        ch, state = data[0], data[1]
        return await self.set_cm_hvip_mode(ch, state)

    async def set_voltage_pwm(self, data: list[int]) -> bytes:
        if len(data) < 12:
            self.logger.error("set_voltage_pwm ожидает 12 регистров: 3 float U + 3 float PWM")
            return b'-1'
        ch_order = (self.CHERENKOV_CH_VOLTAGE, self.PIPS_CH_VOLTAGE, self.SIPM_CH_VOLTAGE)
        result = b'-1'
        for idx, ch in enumerate(ch_order):
            voltage = self._legacy_regs_to_float(data[idx * 2: idx * 2 + 2])
            result = await self.set_cm_hvip_voltage(ch, voltage)
        pwm_offset = 6
        for idx, ch in enumerate(ch_order):
            pwm = self._legacy_regs_to_float(data[pwm_offset + idx * 2: pwm_offset + idx * 2 + 2])
            result = await self.set_cm_hvip_pwm(ch, pwm)
        return result

    async def set_cfg_a_b(self, data: list[int]) -> bytes:
        return b'-1'


class _NoopLogger:
    def error(self, *args, **kwargs):
        return None
    def debug(self, *args, **kwargs):
        return None

class ModbusMPPCommand(EnvironmentVar):
    """Регистр 0x00 ..... 0x00 0x01
                            |    |—команда МПП
                            |—канал МПП (0, 1) 

    Args:
        EnvironmentVar (_type_): внутренние постоянные окружения
    """
    def __init__(self, client, logger, *args, log_enabled: bool = True, serial_log_enabled: bool = False):
        super().__init__()
        self.mw = ModbusWorker()
        self.client: AsyncModbusSerialClient = client
        self.logger = logger if log_enabled else _NoopLogger()
        set_serial_log_enabled(serial_log_enabled)
        self.MPP_ID = args[0] if args else self.MPP_ID_DEFAULT

    async def read_oscill(self, ch: int = 0) -> bytes:
        try:
            all_data = bytearray()
            for offset in range(0, 512, 64):
                reg_addr = (self.REG_OSCILL_CH1 if ch == 1 else self.REG_OSCILL_CH0) + offset

                result: ModbusResponse = await self.client.read_holding_registers(reg_addr,
                                                                                64, 
                                                                                slave=self.MPP_ID)

                await log_s(self.mw.send_handler.mess)
                all_data.extend(result.encode()[1:])

            return bytes(all_data)
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    async def get_hist_32(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.REG_MPP_HIST_16, 
                                                                            12,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()[1:]
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'
        
    async def get_hist_16(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.REG_MPP_HIST_32, 
                                                                            6,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()[1:]
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    async def get_mpp_struct(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.REG_GET_MPP_STRUCT, 
                                                                            24,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'
        
    async def reset_filter(self) -> bytes:
        """_summary_

        Args:
            enable (int): 1 - включить, 0 - выключить

        Returns:
            result (bytes)
        """
        cmd = [10, 0x00]
        try:
            result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                            cmd,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'
        
    async def set_median_filter(self) -> bytes:
        """_summary_

        Args:
            enable (int): 1 - включить, 0 - выключить

        Returns:
            result (bytes)
        """
        val = (1 << 2) & 0x04
        cmd = [10, val]
        try:
            result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                            cmd,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'
        
    async def set_bypass_lp_filter(self) -> bytes:
        """_summary_

        Args:
            enable (int): 1 - включить, 0 - выключить

        Returns:
            result (bytes)
        """
        val = (1 << 1) & 0x02
        cmd = [10, 0x07]
        try:
            result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                            cmd,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'
        
    async def set_bypass_hp_filter(self) -> bytes:
        """_summary_

        Args:
            enable (int): 1 - включить, 0 - выключить

        Returns:
            result (bytes)
        """
        val = (1 << 0) & 0x01
        cmd = [10, val]
        try:
            result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                            cmd,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    async def get_ddin(self):
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.DDIN_PEACK, 
                                                                            1,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'
        
    async def get_tmp_count(self):
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.TMPCOUNT, 
                                                                            1,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'
        
    async def get_acq1(self):
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.ACQ1_PEACK, 
                                                                            1,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'
        
    async def get_acq2(self):
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.ACQ2_PEACK, 
                                                                            1,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    async def calibrate_ACQ(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                            self.REG_CALIBR_ALL_CH,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'
    
    async def issue_waveform(self) -> bytes:
        """Выдать waveform
        Returns:
            bytes
        """
        try:
            result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                            self.REG_MPP_CTRL_ISSUE_WAVEFORM,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    async def start_measure(self, ch: Optional[int] = None, on: Optional[int] = 1) -> bytes:
        try:
            if ch:
                if on:
                    STATE_MEASURE = self.MPP_START_MEASURE.copy()
                    STATE_MEASURE[0] = ch & 0xFF << 8 | STATE_MEASURE[0] & 0xFFFF
                else:
                    STATE_MEASURE = self.MPP_STOP_MEASURE.copy()
                    STATE_MEASURE[0] = ch & 0xFF << 8 | STATE_MEASURE[0] & 0xFFFF
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                            STATE_MEASURE,
                                                                            slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
                await self.client.read_holding_registers(self.REG_MPP_CTRL, 1, self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
                if on:
                    await self.issue_waveform()
                    await log_s(self.mw.send_handler.mess)
                    await self.client.read_holding_registers(self.REG_MPP_CTRL, 1, self.MPP_ID)
            else:
                if on:
                    STATE_MEASURE = self.MPP_START_MEASURE
                else:
                    STATE_MEASURE = self.MPP_STOP_MEASURE
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                            STATE_MEASURE,
                                                                            slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
                await self.client.read_holding_registers(self.REG_MPP_CTRL, 1, self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
                if on:
                    await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                            0x0009,
                                                                            slave=self.MPP_ID) # выдать waveform
                    await log_s(self.mw.send_handler.mess)
                    await self.client.read_holding_registers(self.REG_MPP_CTRL, 1, self.MPP_ID)
                    await log_s(self.mw.send_handler.mess)

            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    async def get_hist32(self):
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.REG_MPP_HIST_32, 
                                                                            12,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()[1:]
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    async def get_hist16(self):
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.REG_MPP_HIST_16, 
                                                                            6,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()[1:]
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'
    
    async def get_hcp_hist(self):
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.REG_MPP_HIST_HCP, 
                                                                            5,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()[1:]
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'
    
    async def clear_hcp_hist(self):
        try:
            result: ModbusResponse = await self.client.write_registers(self.    REG_COMMAND, self.MPP_TRIG_CNT_CLEAR, slave=self.MPP_ID)
            
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'
    
    async def clear_hist(self):
        try:
            result: ModbusResponse = await self.client.write_registers(self.REG_MPP_HIST_32, [0]*18, slave=self.MPP_ID)
            
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'
        
    async def waveform_release(self):
        try:
            result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 0x09, slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    async def start_measure_forced(self, ch: Optional[int] = None) -> bytes:
        try:
            if ch:
                MPP_START_MEASURE_FORCED = ch<<8 & 0xFFFF | self.MPP_START_MEASURE_FORCED
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                            MPP_START_MEASURE_FORCED,
                                                                            slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
            else:
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                            self.MPP_START_MEASURE_FORCED,
                                                                            slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    async def stop_measure(self, ch: int|None = None) -> bytes:
        try:
            if ch:
                MPP_STOP_MEASURE = self.MPP_STOP_MEASURE.copy()
                MPP_STOP_MEASURE[0] = ch<<8 & 0xFFFF | MPP_STOP_MEASURE[0]
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                            MPP_STOP_MEASURE,
                                                                            slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
            else:
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                            self.MPP_STOP_MEASURE,
                                                                            slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    async def set_hh(self, hh: list[int]) -> bytes:
        if len(hh) not in (8, 32):
            self.logger.error("Len hh должен быть 8 или 32")
            return b'-1'
        try:
            result: ModbusResponse = await self.client.write_registers(self.REG_MPP_HH, 
                                                                            hh,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            await asyncio.sleep(0.1)
            result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                            0x08,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    async def set_level(self, lvl: int, ch: Optional[int] = None) -> bytes:
        cmd: list[int] = [self.MPP_LEVEL_TRIG, lvl]
        try:
            if ch:
                cmd_ch = cmd.copy()
                cmd_ch[0] = ch & 0xFFFF << 8 | cmd_ch[0] & 0xFFFF
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                                cmd_ch,
                                                                                slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
            else:
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_CTRL, 
                                                                                cmd,
                                                                                slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    async def get_hh(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.REG_MPP_HH, 
                                                                            32,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    async def get_level(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.REG_MPP_LEVEL, 
                                                                            1,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'
