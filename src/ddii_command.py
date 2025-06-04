from pymodbus.pdu import ModbusResponse
from qasync import asyncSlot
from pymodbus.client import AsyncModbusSerialClient
from src.modbus_worker import ModbusWorker
from src.log_config import log_s
from copy import copy
from typing import Coroutine, Any, Callable, Awaitable, Optional
from src.env_var import EnvironmentVar

class ModbusCMCommand(EnvironmentVar):
    def __init__(self, client, logger, **kwargs):
        super().__init__()
        self.mw = ModbusWorker()
        self.client: AsyncModbusSerialClient = client
        self.logger = logger

    @asyncSlot()
    async def get_cfg_voltage(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.CMD_DBG_GET_CFG_VOLTAGE, 
                                                                            6, 
                                                                            slave=self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')
            return b'-1'
        
    @asyncSlot()
    async def set_csa_test_enable(self, state) -> bytes:
        try:
            result: ModbusResponse = await self.client.write_registers(address = self.DDII_SWITCH_MODE,
                                                                        values = state,
                                                                        slave = self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')
            return b'-1'

    @asyncSlot()
    async def set_mode(self, mode) -> bytes:
        try:
            result: ModbusResponse = await self.client.write_registers(address = self.DDII_SWITCH_MODE,
                                                                        values = mode,
                                                                        slave = self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')
            return b'-1'
        
    @asyncSlot()
    async def get_desired_voltage(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.CM_DBG_GET_DESIRED_HVIP, 
                                                                            6, 
                                                                            slave=self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')
            return b'-1'

    @asyncSlot()
    async def get_cfg_pwm(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.CMD_DBG_GET_CFG_PWM,
                                                                            6, 
                                                                            slave=self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')
            return b'-1'
        
    @asyncSlot()
    async def get_term(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.CM_GET_TERM,
                                                                            4, 
                                                                            slave=self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')
            return b'-1'

    @asyncSlot()
    async def get_cfg_a_b(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.CM_DBG_GET_HVIP_AB,
                                                                            24, 
                                                                            slave=self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает') 
            return b'-1'
    
    @asyncSlot()
    async def get_telemetry(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.CMD_DBG_GET_TELEMETRY, 
                                                                            58, 
                                                                            slave=self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')
            return b'-1'
        
    @asyncSlot()
    async def get_cfg_ddii(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.CMD_DBG_GET_CFG, 
                                                                            32, 
                                                                            slave=self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')
            return b'-1'

    @asyncSlot()
    async def set_cfg_ddii(self, data: list[int] | int)  -> None:
        try:
            await self.client.write_registers(address = self.CMD_DBG_SET_CFG, values = data, slave = self.CM_ID)
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')

    @asyncSlot()
    async def get_voltage(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.CMD_DBG_GET_VOLTAGE, 
                                                                            21, 
                                                                            slave=self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')
            return b'-1'
        
    @asyncSlot()
    async def switch_power(self, data: list[int]) -> bytes:
        try:
            result: ModbusResponse = await self.client.write_registers(self.CMD_DBG_HVIP_ON_OFF, 
                                                                            data, 
                                                                            slave=self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')
            return b'-1'

    @asyncSlot()
    async def set_voltage_pwm(self, data: list[int]) -> bytes:
        try:
            result: ModbusResponse = await self.client.write_registers(self.CMD_DBG_SET_VOLTAGE, 
                                                                            data, 
                                                                            slave=self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')
            return b'-1'
    
    @asyncSlot()
    async def set_cfg_a_b(self, data: list[int]) -> bytes:
        try:
            result: ModbusResponse = await self.client.write_registers(self.CM_DBG_SET_HVIP_AB, 
                                                                            data, 
                                                                            slave=self.CM_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('ЦМ не отвечает')
            return b'-1'




class ModbusMPPCommand(EnvironmentVar):
    """Регистр 0x00 ..... 0x00 0x01
                            |    |—команда МПП
                            |—канал МПП (0, 1) 

    Args:
        EnvironmentVar (_type_): внутренние постоянные окружения
    """
    def __init__(self, client, logger, *args):
        super().__init__()
        self.mw = ModbusWorker()
        self.client: AsyncModbusSerialClient = client
        self.logger = logger
        self.MPP_ID = args[0] if args else self.MPP_ID_DEFAULT

    @asyncSlot()
    async def read_oscill(self, ch: int = 0) -> bytes:
        try:
            all_data = bytearray()
            for offset in range(0, 511, 32):
                reg_addr = (self.REG_OSCILL_CH1 if ch == 1 else self.REG_OSCILL_CH0) + offset
 
                result: ModbusResponse = await self.client.read_holding_registers(reg_addr,
                                                                                32, 
                                                                                slave=self.MPP_ID)

                await log_s(self.mw.send_handler.mess)
                all_data.extend(result.encode()[1:])

            return bytes(all_data)
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    @asyncSlot()
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
    
    @asyncSlot()
    async def start_measure(self, ch: Optional[int] = None, on: Optional[int] = 1) -> bytes:
        try:
            if ch:
                if on:
                    STATE_MEASURE = self.MPP_START_MEASURE.copy()
                    STATE_MEASURE[0] = ch & 0xFF << 8 | STATE_MEASURE[0] & 0xFFFF
                    await self.client.write_registers(self.REG_MPP_COMMAND, 
                                                                            0x0009,
                                                                            slave=self.MPP_ID) # выдать waveform
                    await log_s(self.mw.send_handler.mess)
                else:
                    STATE_MEASURE = self.MPP_STOP_MEASURE.copy()
                    STATE_MEASURE[0] = ch & 0xFF << 8 | STATE_MEASURE[0] & 0xFFFF
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_COMMAND, 
                                                                            STATE_MEASURE,
                                                                            slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)

            else:
                if on:
                    STATE_MEASURE = self.MPP_START_MEASURE
                    await self.client.write_registers(self.REG_MPP_COMMAND, 
                                                                            0x0009,
                                                                            slave=self.MPP_ID) # выдать waveform
                    await log_s(self.mw.send_handler.mess)
                else:
                    STATE_MEASURE = self.MPP_STOP_MEASURE
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_COMMAND, 
                                                                            STATE_MEASURE,
                                                                            slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)

            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    @asyncSlot()
    async def start_measure_forced(self, ch: int|None) -> bytes:
        try:
            if ch:
                MPP_START_MEASURE_FORCED = ch & 0xFF << 8 | self.MPP_START_MEASURE_FORCED & 0xFFFF
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_COMMAND, 
                                                                            MPP_START_MEASURE_FORCED,
                                                                            slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
            else:
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_COMMAND, 
                                                                            self.MPP_START_MEASURE_FORCED,
                                                                            slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    @asyncSlot()
    async def stop_measure(self, ch: int|None) -> bytes:
        try:
            if ch:
                MPP_STOP_MEASURE = self.MPP_STOP_MEASURE.copy()
                MPP_STOP_MEASURE[0] = ch & 0xFF << 8 | MPP_STOP_MEASURE[0] & 0xFFFF
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_COMMAND, 
                                                                            MPP_STOP_MEASURE,
                                                                            slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
            else:
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_COMMAND, 
                                                                            self.MPP_STOP_MEASURE,
                                                                            slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    @asyncSlot()
    async def set_hh(self, hh: list[int]) -> bytes:
        if len(hh) != 8:
            self.logger.error("Len hh[8] не равно 8")
            return b'-1'
        try:
            result: ModbusResponse = await self.client.write_registers(self.REG_MPP_HH, 
                                                                            hh,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    @asyncSlot()
    async def set_level(self, lvl: int, ch: Optional[int] = None) -> bytes:
        cmd: list[int] = [self.MPP_LEVEL_TRIG, lvl]
        try:
            if ch:
                cmd_ch = cmd.copy()
                cmd_ch[0] = ch & 0xFFFF << 8 | cmd_ch[0] & 0xFFFF
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_COMMAND, 
                                                                                cmd_ch,
                                                                                slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
            else:
                result: ModbusResponse = await self.client.write_registers(self.REG_MPP_COMMAND, 
                                                                                cmd,
                                                                                slave=self.MPP_ID)
                await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    @asyncSlot()
    async def get_hh(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.REG_MPP_HH, 
                                                                            8,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    @asyncSlot()
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
