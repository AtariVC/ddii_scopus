# import asyncio

import pymodbus.client as ModbusClient
from pymodbus.pdu import ModbusResponse
import logging
# import logging.handlers as Handlers
# import pymodbus
# from pymodbus import (
#     ExceptionResponse,
#     Framer,
#     ModbusException,
#     pymodbus_apply_logging_config,
# )

# Get handles to the various logs
server_log          = logging.getLogger("pysnmp.server")
client_log          = logging.getLogger("pysnmp.client")
protocol_log        = logging.getLogger("pysnmp.protocol")
store_log           = logging.getLogger("pysnmp.store")

# Enable logging levels
server_log.setLevel(logging.DEBUG)
protocol_log.setLevel(logging.DEBUG)
client_log.setLevel(logging.DEBUG)
store_log.setLevel(logging.DEBUG)

# Initialize the logging
try:
    logging.basicConfig()
except Exception as e:
    print("Logging is not supported on this system")


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
if client.connect():
# data= [0]
    client.write_registers(address = 0x0001, values = 1, slave = 1)
    result: ModbusResponse = client.read_holding_registers(0x0000, 62, slave=1)
# result = client.read_coils(1,10)
    print(result.encode())