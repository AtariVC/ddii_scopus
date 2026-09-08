import asyncio
from typing import Optional

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.pdu import ModbusResponse
from loguru import logger

from app.src.components.frames import HVIP
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
    async def write_registers(self, address: int, values: list[int]) -> ModbusResponse:
        """Записать значения в регистры ЦМ подряд, начиная с адреса.

        Args:
            address (int): адрес первого регистра.
            values (list[int]): значения регистров (по 16 бит).
        """
        return await self.client.write_registers(
            address,
            values,
            slave=self.CM_ID,
        )

    @mb_encode
    async def read_hvip(self, ch: int) -> ModbusResponse:
        """Прочитать блок регистров одного канала HVIP целиком (MODE … PID_ERROR).

        Args:
            ch (int): номер канала HVIP [0..HVIP_CH_NUM-1].

        Returns:
            Сырые байты блока (2 байта на регистр) или ``b"-1"`` при ошибке.
        """
        return await self.client.read_holding_registers(
            self.hvip_reg.BASE + ch * self.hvip_reg.NUMBER,
            self.hvip_reg.NUMBER,
            slave=self.CM_ID,
        )

    async def write_hvip(self, ch: int, values: dict[str, float]) -> bytes:
        """Записать rw-поля канала HVIP по именам полей кадра.

        Чтение HVIP поканальное (блок ``BASE + ch*NUMBER``), а **запись —
        командная**: адрес всегда базовый (``BASE + offset``, без умножения на
        канал), а номер канала идёт первым словом данных. Прошивка так и
        разбирает пакет: «номер канала и хотя бы одно значение», меньше двух слов
        отвергается как ILLEGAL_DATA_VALUE.

        Пакеты собирает кадр :data:`~app.src.components.frames.HVIP`: смежные поля
        уходят одной записью ``[ch, знач, знач, …]``. Поля только для чтения кадр
        отбрасывает сам.

        Args:
            ch (int): номер канала HVIP [0..HVIP_CH_NUM-1].
            values (dict[str, float]): значения полей в инженерных единицах
                (напр. ``{"voltage_desired": 300.0, "mode": 1}``).

        Returns:
            Ответ последней записи или ``b"-1"``, если хотя бы одна не прошла;
            ``b""`` — если писать было нечего.
        """
        result = b""
        for offset, words in HVIP.encode(values):
            result = await self.write_registers(self.hvip_reg.BASE + offset, [ch, *words])
            if result == b"-1":
                return b"-1"
        return result

    @mb_encode
    async def set_frame_interval(self, seconds: int) -> ModbusResponse:
        """Задать время формирования кадра ЦМ.

        Args:
            seconds (int): интервал измерения (формирования кадра), с.
        """
        return await self.client.write_registers(
            self.ctrl_reg.SET_INTERVAL_MEAS,
            [int(seconds) & 0xFFFF],
            slave=self.CM_ID,
        )

    @mb_encode
    async def read_system_frame(self) -> ModbusResponse:
        """Прочитать системный кадр целиком (64 байта).

        Returns:
            Сырые байты кадра или ``b"-1"`` при ошибке.
        """
        return await self.client.read_holding_registers(
            self.frame_reg.SYS_BASE,
            self.frame_reg.SYS_NUMBER,
            slave=self.CM_ID,
        )

    @mb_encode
    async def read_ddii_frame(self) -> ModbusResponse:
        """Прочитать кадр ДДИИ целиком (64 байта).

        Returns:
            Сырые байты кадра или ``b"-1"`` при ошибке.
        """
        return await self.client.read_holding_registers(
            self.frame_reg.DDII_BASE,
            self.frame_reg.DDII_NUMBER,
            slave=self.CM_ID,
        )

    async def set_vlotage_ch_hvip(self, ch: int, v: float) -> bytes:
        '''Устанавливает значение напряжения для канала HVIP

        Адрес считает кадр HVIP (``BASE + ch*NUMBER + offset``): регистр
        V_HV_DESIRED_X100 именно этого канала.

        Args:
            ch(int): Канал HVIP [0..HVIP_CH_NUM-1]
            v(float): Напряжение с точностью до второго знака
        '''
        return await self.write_hvip(ch, {"voltage_desired": v})

    async def enable_ch_hvip(self, ch: int, state: int) -> bytes:
        """Включить/выключить канал HVIP (регистр MODE этого канала).

        Args:
            ch (int): номер канала HVIP [0..HVIP_CH_NUM-1].
            state (int): 1 — включить, 0 — выключить.
        """
        return await self.write_hvip(ch, {"mode": int(bool(state))})

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

    async def set_trig_sel(self, trig_sel: int) -> ModbusResponse:
        cmd = [self.mpp_reg.MPP_TRIG_SEL, trig_sel]
        return await self.write_mpp_ctrl_reg(cmd)

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
    async def get_mpp_trig_sel(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.MPP_REG_TRIG_SEL,
            1,
            slave=self.MPP_ID,
        )

    @mb_encode
    async def get_level(self) -> ModbusResponse:
        return await self.client.read_holding_registers(
            self.mpp_reg.MPP_LEVEL,
            1,
            slave=self.MPP_ID,
        )

