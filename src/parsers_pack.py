
from PyQt6.QtWidgets import QLineEdit
from src.parsers import  Parsers
from src.modbus_worker import ModbusWorker
import struct
from dataclasses import dataclass

@dataclass
class LineObj:
    '''
    key: str - название переменной

    lineobj: QLineEdit - объект QLineEdit

    tp: str - тип данных записанный в QLineEdit, 
    нужно чтобы правильно извлечь значение QLineEdit
    '''
    key: str 
    lineobj: QLineEdit
    tp: str

class LineEditPack:
    """
    Извлекает все значения из QLineEdit и упаковывает их в list для отправки

    ln_objects: list[LineObj] - список объектов QLineEdit

    endian: str - формат такой же как struct "little", "big"

    """
    def __init__(self):
        super().__init__()
        self.mw = ModbusWorker()

    def __call__(self, ln_objects: list[LineObj], endian: str) -> list[int]:
        data: list[int] = []
        for obj in ln_objects:
            if obj.tp == "i":
                data.append(int.from_bytes(struct.pack((">H" if endian=='big' else "<H"), int(obj.lineobj.text()))))
            if obj.tp == "f":
                data += [
                    int(struct.pack((">f" if endian=='big' else "<f"),
                                    float(obj.lineobj.text()))[i*2: i*2+2].hex(), 
                    16) for i in range(2)]
        return data
