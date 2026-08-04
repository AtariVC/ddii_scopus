import asyncio
from typing import Optional

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.pdu import ModbusResponse
from loguru import logger

from app.src.components.log.config import apply_glob_serial_log_flag
from app.src.components.modbus.command_codec import mb_encode
from app.src.components.modbus.modbus_reg import ModbusReg
from app.src.components.modbus.worker import ModbusWorker


class _NoopLogger:
    def error(self, *args, **kwargs):
        return None
    def debug(self, *args, **kwargs):
        return None

class ModbusCMCommand(ModbusReg):
    device_name = "ЦМ"
    log_serial_exchange = True

    def __init__(self, client, *, log_enabled: bool = True, log_serial_exchange: bool = True, **kwargs):
        super().__init__()
        self.mw = ModbusWorker()
        self.client: AsyncModbusSerialClient = client
        # Swap to no-op logger if disabled
        self.logger = logger if log_enabled else _NoopLogger()
        self.log_serial_exchange = log_serial_exchange
        # Apply global serial log flag for TX/RX dumps
        apply_glob_serial_log_flag(log_serial_exchange)
    
    @mb_encode
    async def set_gpio_impact_autotest(self) -> ModbusResponse:
        return await self.client.write_registers(
            self.ctrl_reg.GPIO_IMPACT_AUTOTEST,
            3,
            slave=self.CM_ID,
        )

    @mb_encode
    async def read_registers(self, address: int, count: int) -> ModbusResponse:
        return await self.client.read_holding_registers(
            address,
            count,
            slave=self.CM_ID,
        )

    @mb_encode
    async def set_vlotage_ch_hvip(self, ch: int, v: float) -> ModbusResponse:
        '''Устанавливает значение напряжения для канала HVIP

        Args:
            ch(int): Канал HVIP
            v(float): Напряжение с точностью до второго знака
        '''
        return await self.client.write_registers(
            self.hvip_reg.V_HV_DESIRED_X100,
            [ch, int(round(v, 2)*100)],
            slave=self.CM_ID,
        )

    @mb_encode
    async def enable_ch_hvip(self, ch: int, state: int) -> ModbusResponse:
        return await self.client.write_registers(
            self.hvip_reg.STATE,
            [ch, state],
            slave=self.CM_ID,
        )

class ModbusMPPCommand(ModbusReg):
    device_name = "МПП"
    log_serial_exchange = False

    """Регистр 0x00 ..... 0x00 0x01
                            |    |—команда МПП
                            |—канал МПП (0, 1) 

    Args:
        ModbusReg (_type_): внутренние постоянные окружения
    """
    def __init__(self, client, *args, log_enabled: bool = True, log_serial_exchange: bool = False):
        super().__init__()
        self.mw = ModbusWorker()
        self.client: AsyncModbusSerialClient = client
        self.logger = logger if log_enabled else _NoopLogger()
        self.log_serial_exchange = log_serial_exchange
        apply_glob_serial_log_flag(log_serial_exchange)
        self.MPP_ID = args[0] if args else ModbusReg.MPP_ID

    async def read_oscill(self, ch: int = 0):
        all_data = bytearray()
        for offset in range(0, 512, 64):
            reg_addr = (self.mpp_reg.OSCILL_CH1 if ch == 1 else self.mpp_reg.OSCILL_CH0) + offset
            result = await self.read_oscill_chunk(reg_addr)
            if result == b"-1":
                return result
            all_data.extend(result)
        return bytes(all_data)

    @mb_encode
    async def read_oscill_chunk(self, reg_addr: int) -> ModbusResponse:
        return await self.client.read_holding_registers(
            reg_addr,
            64,
            slave=self.MPP_ID,
        )

    @mb_encode
    async def get_hist_32(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.MPP_HIST_16,
            12,
            slave=self.MPP_ID,
        )

    @mb_encode
    async def get_hist_16(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.MPP_HIST_32,
            6,
            slave=self.MPP_ID,
        )

    @mb_encode
    async def get_mpp_reg_struct(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.MPP_STRUCT,
            24,
            slave=self.MPP_ID,
        )
        
    @mb_encode
    async def write_mpp_ctrl_reg(self, values: list[int] | int) -> ModbusResponse:
        return await self.client.write_registers(
            self.mpp_reg.MPP_CTRL,
            values,
            slave=self.MPP_ID,
        )

    @mb_encode
    async def read_mpp_ctrl_reg(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.MPP_CTRL,
            1,
            slave=self.MPP_ID,
        )

    @mb_encode
    async def get_ddin(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.DDIN_PEACK,
            1,
            slave=self.MPP_ID,
        )
        
    @mb_encode
    async def get_tmp_count(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.TMPCOUNT,
            1,
            slave=self.MPP_ID,
        )
        
    @mb_encode
    async def get_acq1(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.ACQ1_PEACK,
            1,
            slave=self.MPP_ID,
        )
        
    @mb_encode
    async def get_acq2(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.ACQ2_PEACK,
            1,
            slave=self.MPP_ID,
        )

    async def calibrate_ACQ(self) -> ModbusResponse:
        return await self.write_mpp_ctrl_reg(self.mpp_reg.CALIBR_ALL_CH)
    
    async def issue_waveform(self) -> ModbusResponse:
        """Выдать waveform
        Returns:
            bytes
        """
        return await self.write_mpp_ctrl_reg(self.mpp_reg.MPP_CTRL_ISSUE_WAVEFORM)

    async def start_measure(self, ch: Optional[int] = None, on: Optional[int] = 1) -> ModbusResponse:
        if ch:
            state_measure = (self.mpp_reg.MPP_START_MEASURE if on else self.mpp_reg.MPP_STOP_MEASURE).copy()
            state_measure[0] = ch & 0xFF << 8 | state_measure[0] & 0xFFFF
        else:
            state_measure = self.mpp_reg.MPP_START_MEASURE if on else self.mpp_reg.MPP_STOP_MEASURE

        result = await self.write_mpp_ctrl_reg(state_measure)
        if result == b"-1":
            return result

        result = await self.read_mpp_ctrl_reg()
        if result == b"-1":
            return result

        if on:
            result = await self.issue_waveform() if ch else await self.write_mpp_ctrl_reg(0x0009)
            if result == b"-1":
                return result
            result = await self.read_mpp_ctrl_reg()

        return result

    @mb_encode
    async def get_hist32(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.MPP_HIST_32,
            12,
            slave=self.MPP_ID,
        )

    @mb_encode
    async def get_hist16(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.MPP_HIST_16,
            6,
            slave=self.MPP_ID,
        )

    @mb_encode
    async def get_hcp_hist(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.MPP_HIST_HCP,
            5,
            slave=self.MPP_ID,
        )

    async def clear_hcp_hist(self):
        return await self.write_mpp_ctrl_reg(self.mpp_reg.MPP_TRIG_CNT_CLEAR)
    
    async def clear_hist(self):
        return await self.write_mpp_reg_hist_32([0] * 18)

    @mb_encode
    async def write_mpp_reg_hist_32(self, values: list[int]) -> ModbusResponse:
        return await self.client.write_registers(
            self.mpp_reg.MPP_HIST_32,
            values,
            slave=self.MPP_ID,
        )
        
    async def waveform_release(self):
        return await self.write_mpp_ctrl_reg(0x09)

    async def start_measure_forced(self, ch: Optional[int] = None) -> ModbusResponse:
        cmd = ((ch << 8) & 0xFFFF | self.mpp_reg.MPP_START_MEASURE_FORCED) if ch else self.mpp_reg.MPP_START_MEASURE_FORCED
        return await self.write_mpp_ctrl_reg(cmd)

    async def stop_measure(self, ch: int|None = None) -> ModbusResponse:
        cmd = self.mpp_reg.MPP_STOP_MEASURE.copy()
        if ch:
            cmd[0] = ch << 8 & 0xFFFF | cmd[0]
        return await self.write_mpp_ctrl_reg(cmd)

    async def set_hh(self, hh: list[int]) -> bytes:
        if len(hh) not in (8, 32):
            self.logger.error("Len hh должен быть 8 или 32")
            return b'-1'
        result = await self.write_mpp_reg_hh(hh)
        if result == b"-1":
            return b"-1"
        await asyncio.sleep(0.1)
        return await self.write_mpp_ctrl_reg(0x08) # type: ignore

    @mb_encode
    async def write_mpp_reg_hh(self, hh: list[int]) -> ModbusResponse:
        return await self.client.write_registers(
            self.mpp_reg.MPP_HH,
            hh,
            slave=self.MPP_ID,
        )

    async def set_level(self, lvl: int, ch: Optional[int] = None) -> ModbusResponse:
        cmd: list[int] = [self.mpp_reg.MPP_LEVEL_TRIG, lvl]
        if ch:
            cmd[0] = ch & 0xFFFF << 8 | cmd[0] & 0xFFFF
        return await self.write_mpp_ctrl_reg(cmd)

    @mb_encode
    async def get_hh(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.MPP_HH,
            32,
            slave=self.MPP_ID,
        )

    @mb_encode
    async def get_level(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.MPP_LEVEL,
            1,
            slave=self.MPP_ID,
        )

