import struct


class ModbusWorker:
    def _REV16(self, byte_str: bytes) -> bytes:
        reversed_bytes: bytes = struct.pack('<H', int(byte_str.hex(), 16))
        return reversed_bytes
    
    def _REV32(self, byte_str: bytes) -> bytes:
        reversed_bytes: bytes = self._REV16(byte_str[2:]) + self._REV16(byte_str[:2])
        return reversed_bytes
    
    def byte_to_float(self, byte_str: bytes) -> float:
        # n0: bytes = self._REV32(byte_str)
        n_i: int = int(byte_str.hex(), 16)
        b : bytes = n_i.to_bytes(4, byteorder='little')
        float_t: float = struct.unpack('!f', b)[0]
        return float_t
    
    def float_to_byte(self, val: float) -> bytes:
        byte_str: bytes = struct.pack('<f', val)
        return byte_str


if __name__ == "__main__":
    mw = ModbusWorker()
    # print(mw.byte_to_float(0x33334341.to_bytes(4, 'big'))) # 12.2
    # print(mw._REV16(0x4143.to_bytes(2)).hex())
    # print(mw._REV8(0x35).to_bytes(1).hex())
