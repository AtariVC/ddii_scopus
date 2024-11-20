from pymodbus.pdu import ModbusResponse
from qasync import asyncSlot
from pymodbus.client import AsyncModbusSerialClient
from src.modbus_worker import ModbusWorker
from src.log_config import log_s

from src.env_var import EnvironmentVar

class ModbusCMCommand(EnvironmentVar):
    def __init__(self, client, logger, **kwargs):
        super().__init__()
        self.mw = ModbusWorker()
        self.client: AsyncModbusSerialClient = client
        self.logger = logger

    ####### Получение структур CM ######
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
                                                                            25, 
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
    def __init__(self, client, logger, **kwargs):
        super().__init__()
        self.mw = ModbusWorker()
        self.client: AsyncModbusSerialClient = client
        self.logger = logger

    @asyncSlot()
    async def get_data(self) -> bytes:
        try:
            result: ModbusResponse = await self.client.read_holding_registers(self.GET_MPP_DATA, 
                                                                            24,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    @asyncSlot()
    async def set_hh(self, data: list[int]) -> bytes:
        try:
            result: ModbusResponse = await self.client.write_registers(self.REG_MPP_HH, 
                                                                            data,
                                                                            slave=self.MPP_ID)
            await log_s(self.mw.send_handler.mess)
            return result.encode()
        except Exception as e:
            self.logger.error(e)
            self.logger.debug('МПП не отвечает')
            return b'-1'

    @asyncSlot()
    async def set_level(self, lvl: int) -> bytes:
        cmd: list[int] = [self.MPP_LEVEL_TRIG, lvl] 
        try:
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
