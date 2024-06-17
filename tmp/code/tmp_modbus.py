import asyncio

import pymodbus.client as ModbusClient
from pymodbus.pdu import ModbusResponse
import logging
import logging.handlers as Handlers
import pymodbus
from pymodbus import (
    ExceptionResponse,
    Framer,
    ModbusException,
    pymodbus_apply_logging_config,
)

client = ModbusClient.ModbusSerialClient(
            "COM5",
            # timeout=10,
            # retries=3,
            # retry_on_empty=False,
            # strict=True,
            timeout=1,
            baudrate=125000,
            bytesize=8,
            parity="N",
            stopbits=1,
            handle_local_echo=True,
        )
# log = logging.getLogger()
# log.setLevel(logging.DEBUG)
if client.connect():
# data= [0]
    result: ModbusResponse = client.write_registers(1, [0], slave=1)
# result = client.read_coils(1,10)
    print(result)