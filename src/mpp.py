"""
Эмулятор мпп: генератор кадра мпп, вывод осциллограм, потоков частиц, обработка полезного сигнала pips и sipm

Есть возможность считать данные waveform из файла и его перевести в hex

ModBuss:
0E 03 00 00 00 81 A6ED
|   | |__|   |__|   |-- CRC16 (старший байт первый, младший байт последний)
|   |    |      |--Команда МПП
|   |    |--Адресс
|   |--Функционая команда
|--Адрес устройства

Регистры:
1-9999	        0000 до 270E	Чтение-запись	Discrete Output Coils	            DO
10001-19999	    0000 до 270E	Чтение	        Discrete Input Contacts	            DI
30001-39999	    0000 до 270E	Чтение	        Analog Input Registers	            AI
40001-49999	    0000 до 270E	Чтение-запись	Analog Output Holding Registers	    AO

Адрес МПП смотреть по перемычкам на плате. Премычка - 0, нет перемычки - 1. Пример 1110 = 14 = 0x0E
Команды:
03 (0x03)	Чтение AO	            Read Holding Registers	        16 битное	    Чтение
06 (0x06)	Запись одного AO	    Preset Single Register	        16 битное	    Запись
16 (0x10)	Запись нескольких AO	Preset Multiple Registers	    16 битное	    Запись
Управление МПП:
00 81 - принудительный запуск цикла регистрации
"""
import os
import re
from logger import logging
import crcmod
import math
from engine import Engine

####################  Эмулятор МПП  #####################
def mpp_frame_gen(payload: list) -> int:
    """
    Формирователь кадра mpp согласно протоколу ModBuss
    Кадр: Зеркало команды на ситывание осциллограммы + ID + 03 + полезные данные + CRC без зеркала
    0E 03 A2 00 00 81 A6 ED | 0E 03 DATA CRC16
    """
    data = 0x00
    if len(payload) == 0:
        payload = [0x12, 0x23, 0x34, 0x45, 0x56, 0x67, 0x78, 0x89, 0xA3, 0xB4, 0xC5, 0xD6, 0xE7, 0xF8, 0x12, 0x23, 0x45,
                   0x56, 0x67, 0x78]
    for i, val in enumerate(payload):
        data += (val << (len(payload) - i - 1) * 8)  # Формирование слова байтов из массива data
    len_data = len(payload) # количество байт для счит
    print(len_data)
    print(hex(data))
    mpp_id = 0x0E
    modbus_comand = 0x03
    init_reg = 0xA200  # стартовый регистр считывания
    amount_read_reg = 0x007C  # количество байт для считывания 124
    data_tmp = (((mpp_id << 8) + (modbus_comand)) << len_data * 8) + (data)
    crc = calculateCrc16_modbus(data_tmp)
    data_mpp = (data_tmp << 16) + swappedByte_crc_modbus(crc)
    return data_mpp



def swappedByte_crc_modbus(data: int) -> int:
    """
    This function swaps the high and low bytes of an integer and returns the result.

    Parameters:
        data (bytes): The integer to be swapped.

    Returns:
        int: The swapped integer.
    """
    # Получение старшего и младшего байта
    byte1: int = (data >> 8) & 0xff
    byte2: int = data & 0xff
    # Обмен местами старшего и младшего байта
    swapped_data: int = (byte2 << 8) | byte1

    return swapped_data


def trap():
    pass
def treangul():
    pass    
    
####################  Вспомогателные функции  #############


def calculateCrc16_modbus(data: int) -> int:
    """
        Calculates the CRC-16 for a given data using the MODBUS algorithm.
    
    Parameters:
        data (int): The data to be used in the calculation.
    Returns:
        int: The calculated CRC-16 value.
    """
    crc16_func = crcmod.predefined.mkPredefinedCrcFun('modbus')
    num_bytes: int = math.ceil(data.bit_length() / 8)
    data_bytes: bytes = data.to_bytes(num_bytes, byteorder='big')
    crc = crc16_func(data_bytes)
    return crc

data1 = read_waveform_csv()
data1 = list(map(int, data1))
mpp_data = mpp_frame_gen(data1)
data_list = Engine.parserWaveform(mpp_data)
x, y = Engine.hex_to_list(data_list)
print(hex(mpp_data))



