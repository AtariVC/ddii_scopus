from logger import logging
logging.basicConfig(filename="./log/21.12.2023.txt",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)

logging.info("Running Urban Planning")

logger = logging.getLogger('urbanGUI')

fh = logging.FileHandler("./log/21.12.2023.log")
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

import logging

# Инициализация логгера
logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)

# Создание файла для записи логов
log_file_path = 'example.log'
file_handler = logging.FileHandler(log_file_path)

# Установка уровня логирования для файла
file_handler.setLevel(logging.DEBUG)

# Создание форматтера
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Привязка форматтера к обработчику
file_handler.setFormatter(formatter)

# Добавление файла в логгер
logger.addHandler(file_handler)

# Запись логов
logger.debug('Debug message')
logger.info('Info message')
logger.warning('Warning message')
logger.error('Error message')
logger.critical('Critical message')
