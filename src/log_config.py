"""
Лог конфиги.
"DEBUG" - для записи отладочной информации
"ERROR" - для записи ошибок в журнал ошибок
"INFO" - для записи команд serial port как в DockLight
"""
import logging
import loguru
from loguru import logger
from datetime import datetime
import sys
import re

# from logger import logging

def log_init():
    logger.remove(0)

    rx_level= logger.level("RX", no=0, color="<red>", icon="")
    tx_level= logger.level("TX", no=0, color="<green>", icon="")
    emulator_level = logger.level("EMULATOR", no=0, color="<y>", icon="")

    time_now = datetime.now()
    form_time = time_now.strftime("%Y-%m-%d %H_%M_%S")
    log_path_debug = "./log/debug/" + str(form_time) + ".log"
    log_path_serial = "./log/serial/" + str(form_time) + ".log"
    log_path_emulator = "./log/emulator/" + str(form_time) + ".log"
    log_format_debug = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <4}</level> | \
<yellow>{file}:{line}</yellow> | <w>{message}</w>"
    log_format_tx = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <1}</level> | \
<m>{message}</m>"
    log_format_rx = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <1}</level> | \
<c>{message}</c>"
    log_format_emulator = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <1}</level> | \
<w>{message}</w>"

    logger.add(sys.stderr, level="DEBUG", format=log_format_debug, 
            colorize=True, backtrace=True, diagnose=True, filter=debug_filter)
    # логирование serial rx
    logger.add(sys.stdout,level=rx_level.name, format=log_format_rx, 
            colorize=True, backtrace=True, diagnose=True, filter=rx_filter)
    # логирование serial tx
    logger.add(sys.stdout,level=tx_level.name, format=log_format_tx, 
            colorize=True, backtrace=True, diagnose=True, filter=tx_filter)
    # эмулятор
    logger.add(sys.stdout,level=emulator_level.name, format=log_format_emulator, 
            colorize=True, backtrace=True, diagnose=True, filter=emulator_filter)
    # логирование debug в файл
    logger.add(log_path_debug, level="DEBUG", format=log_format_debug, rotation="100 MB", enqueue=True, filter=debug_filter)
    logger.add(log_path_serial, level=rx_level.name, format=log_format_rx, enqueue=True, filter=rx_filter)
    logger.add(log_path_serial, level=tx_level.name, format=log_format_tx, enqueue=True, filter=tx_filter)
    logger.add(log_path_emulator, level=emulator_level.name, format=log_format_emulator, enqueue=True, filter=emulator_filter)
    # логирование в файл
    # logger.add(log_path_debug, level=log_level, format=log_format, colorize=False, backtrace=True, diagnose=True)
    return logger

def emulator_filter(record):
    return record["level"].name == "EMULATOR"

def tx_filter(record):
    return record["level"].name == "TX"

def rx_filter(record):
    return record["level"].name == "RX"

def debug_filter(record):
    return record["level"].name == "DEBUG"

def log_s(message: list):
    mess = ''
    for item in message:
        try:
            if item[:4] == "SEND":
                mess = item[6:].replace("0x", "")
                mode = "TX"
            if item[:4] == "RECV":
                mode = "RX"
                mess = item[6:].replace("0x", "")
        except IndexError as e:
            logger.debug("Нет ответа от устройства")
            logger.debug("pymodus.send_handler.mass: IndexError")
            return 0
        mess = re.findall(r"[a-f0-9]{1,2}", mess)
        new_mess = ""
        for i in range(0, len(mess)):
            if len(mess[i]) == 1:
                mess[i] = "0" + mess[i]
            new_mess = new_mess + mess[i] + " "
        if mode == "RX":
            logger.log("RX", new_mess.upper())
        elif mode == "TX":
            logger.log("TX", new_mess.upper())
    message.clear()




# def log_init_debug():
#     logger.remove(0)
#     log_level = "DEBUG"
#     log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <4}</level> | \
# <yellow>Line{line:} ({file}):</yellow> <b>{message}</b>"
#     logger.add(sys.stderr, level=log_level, format=log_format, colorize=True, backtrace=True, diagnose=True)
#     time_now = datetime.now()
#     form_time = time_now.strftime("%Y-%m-%d %H_%M_%S")
#     log_path_debug = "./log/debug/" + str(form_time) + ".log"
#     # логгирование в файл
#     # logger.add(log_path_debug, level=log_level, format=log_format, colorize=False, backtrace=True, diagnose=True)
#     return logger


# # class CustomLogger_Serial(logging.Logger):

#     # def __init__(self, name, level=logging.NOTSET):
#     #     super().__init__(name, level=level)
#     #     log_level = "INFO"
#     #     log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <4}</level> | \
#     #     <yellow>Line {line: >4} ({file}):</yellow> <b>{message}</b>"
#     #     logger.add("SERIAL", level=log_level, format=log_format, colorize=True, backtrace=True, diagnose=True)
#     #     time_now = datetime.now()
#     #     form_time = time_now.strftime("%Y-%m-%d %H_%M_%S")
#     #     log_path_debug = f"./log/serial/{form_time}.log"
#     #     logger.add(log_path_debug, level=log_level, format=log_format, colorize=False, backtrace=True, diagnose=True)

# def log_init_serial():
#     log_level = "INFO"
#     log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <4}</level> | \
#     <yellow>Line {line: >4} ({file}):</yellow> <b>{message}</b>"
#     logger.add("SERIAL", level=log_level, format=log_format, colorize=True, backtrace=True, diagnose=True)
#     time_now = datetime.now()
#     form_time = time_now.strftime("%Y-%m-%d %H_%M_%S")
#     log_path_debug = "./log/serial/" + str(form_time) + ".log"
#     # логгирование в файл
#     # logger.add(log_path_debug, level=log_level, format=log_format, colorize=False, backtrace=True, diagnose=True)
#     return logger

# def log_s(massage):
#     print(massage)
#     mass = str(massage)
#     print(mass)
#     mass = re.findall(r"\w\w", mass)
#     print(mass)
#     new_mass = ""
#     for i in range(0, len(mass)):
#         new_mass = new_mass + mass[i] + " " 
#     logger.log("INFO", new_mass)




