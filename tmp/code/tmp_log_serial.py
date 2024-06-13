from loguru import logger
# from loguru import Level
from datetime import datetime
import sys
import typing

def log_s():
    pass
# Line{line:} 
def log_init():
    logger.remove(0)

    rx_level= logger.level("RX", no=0, color="<red>", icon="")
    tx_level= logger.level("TX", no=0, color="<green>", icon="")

    time_now = datetime.now()
    form_time = time_now.strftime("%Y-%m-%d %H_%M_%S")
    log_path_debug = "./tmp/log/debug/" + str(form_time) + ".log"
    log_path_serial = "./tmp/log/serial/" + str(form_time) + ".log"
    log_format_debug = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <4}</level> | \
<yellow>{file}:{line}</yellow> | <b>{message}</b>"
    log_format_serial = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <1}</level> : \
<b>{message}</b>"

    logger.add(sys.stderr, level="DEBUG", format=log_format_debug, 
            colorize=True, backtrace=True, diagnose=True, filter=debug_filter)
    # логирование serial rx
    logger.add(sys.stdout,level=rx_level.name, format=log_format_serial, 
            colorize=True, backtrace=True, diagnose=True, filter=rx_filter)
    # логирование seriak tx
    logger.add(sys.stdout,level=tx_level.name, format=log_format_serial, 
            colorize=True, backtrace=True, diagnose=True, filter=tx_filter)
    # логгирование debug в файл
    logger.add(log_path_debug, level="DEBUG", format=log_format_debug, rotation="100 MB", enqueue=True)
    logger.add(log_path_serial, level=rx_level.name, format=log_format_serial, enqueue=True, filter=rx_filter)
    logger.add(log_path_serial, level=tx_level.name, format=log_format_serial, enqueue=True, filter=tx_filter)
    # логгирование в файл
    # logger.add(log_path_debug, level=log_level, format=log_format, colorize=False, backtrace=True, diagnose=True)
    return logger

def tx_filter(record):
    return record["level"].name == "TX"

def rx_filter(record):
    return record["level"].name == "RX"

def debug_filter(record):
    return record["level"].name == "DEBUG"

mylog = log_init()
# log_ser = log_init_serial(mode = "RX")

def rand_func():
    mylog.debug("Это дебаг сообщение")
    mylog.log("RX", "00 01 34 ff FE".upper())

rand_func()


# Тестовый модуль

# log_level = "DEBUG"
# rx_level= logger.level("RX", no=0, color="<red>", icon="")
# tx_level= logger.level("TX", no=0, color="<green>", icon="")
# time_now = datetime.now()
# form_time = time_now.strftime("%Y-%m-%d %H_%M_%S")
# log_path_debug = "./tmp/log/debug/" + str(form_time) + ".log"
# log_path_serial = "./tmp/log/serial/" + str(form_time) + ".log"
# log_format_debug = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <4}</level> | \
# <yellow>Line{line:} ({file}):</yellow> <b>{message}</b>"
# log_format_serial = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <1}</level> | \
# <b>{message}</b>"
# log_format_tx = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <1}</level> | \
# <b>{message}</b>"

# logger.add(sys.stderr, level=tx_level.name, format=log_format_tx, 
#             colorize=True, backtrace=True, diagnose=True, filter=tx_filter)
# logger.add(sys.stderr, level=rx_level.name, format=log_format_rx, 
#             colorize=True, backtrace=True, diagnose=True, filter=rx_filter)
# logger.log("TX", "TX!")
# logger.log("RX", "RX!")