"""Функционал движка:
    1. Обработка событий gui
    2. Работа с иммулятором ДДИИ
    3. Работа с ДДИИ
    4. Работа с построением графиков
    5. Работа с построением гистограмм
    6. Запись log
    7. Сохранение графиков и гистограмм
    8. Вывод log
    9. Вывод значениий колличества частиц по энергиям согласной ТЗ на ДДИИ

    Модуль Emulator является опциональным, поэтму подключается отдельно к Engine

    # Пример использования логгера
    self.logger.debug('Это сообщение уровня DEBUG')
    self.logger.info('Это сообщение уровня INFO')
    self.logger.warning('Это сообщение уровня WARNING')
    self.logger.error('Это сообщение уровня ERROR')
    self.logger.critical('Это сообщение уровня CRITICAL')

"""
import pdb
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import QSplitter, QSizePolicy, QLineEdit
from PyQt6.QtCore import Qt, QTimer, QThread
from PyQt6.QtGui import QAction, QIcon
import numpy as np
import pyqtgraph as pg
import serial.tools.list_ports
import sys  # We need sys so that we can pass argv to QApplication
import os
# from random import randint
# from ui.MainWindow_ui import Ui_MainWindow
from qtpy.uic import loadUi
import serial
# from pyqtgraph import plot
# from qtmodern.styles import dark, light
# from qtmodern.windows import ModernWindow
# import serial.tools.list_ports
from style.styleSheet import styleSheet as style
import crcmod
import math as m
import re
from emulator import Emulator as emulator
from serial.serialutil import SerialException
from src.py_toggle import pyToggle
# from serial.serialutil import SerialException
# from src.py_toggle import pyToggle
from src.log_config import log_init, log_s
import logging
from src.customComboBox_COMport import CustomComboBox_COMport
import copy as cp
# import time
import threading
from main_trapezoid_dialog import MainTrapezoidDialog
from main_hvip_dialog import MainHvipDialog
from main_mpp_dialog import MainMppControlDialog
from queue import Queue
import numpy as np
import os
import datetime
import csv
import pandas as pd 
import numpy as np
import configparser
import src.parsers as parser
import time
import pymodbus.client as ModbusClient
from pymodbus.pdu import ModbusResponse
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
import colorlog
# from firstblood.all import *

# Создание фильтра для pymodbus
class SendFilter(logging.Filter):
    def filter(self, record):
        # message = record.getMessage()
        return False #'SEND:' in message or 'RECV:' in message
    
# Создание обработчика для pymodbus
class SendHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.mess = []

    def emit(self, record):
        message = self.format(record)
        # print(message)
        if 'SEND:' in message:
            self.mess.append(message)
        if 'RECV:' in message:
            self.mess.append(message)

class Engine(QtWidgets.QMainWindow, QThread):
    my_button: QtWidgets.QPushButton
    vLayout_gist_EdE: QtWidgets.QVBoxLayout
    vLayout_gist_pips: QtWidgets.QVBoxLayout
    vLayout_gist_sipm: QtWidgets.QVBoxLayout
    vLayout_pips: QtWidgets.QVBoxLayout
    vLayout_sipm: QtWidgets.QVBoxLayout
    pushButton_connect_2: QtWidgets.QPushButton
    lineEdit_Bauderate_2: QtWidgets.QLineEdit
    lineEdit_IDmpp_2: QtWidgets.QLineEdit
    lineEdit_level_pips: QtWidgets.QLineEdit
    # pushButton_single_pips: QtWidgets.QPushButton
    # pushButton_auto_pips: QtWidgets.QPushButton
    pushButton_trapezoid: QtWidgets.QPushButton
    checkBox_writeLog_pips: QtWidgets.QLineEdit
    lineEdit_level_sipm: QtWidgets.QLineEdit
    # pushButton_single_sipm: QtWidgets.QPushButton
    # pushButton_auto_sipm: QtWidgets.QPushButton
    checkBox_writeLog_sipm: QtWidgets.QLineEdit
    pushButton_single_all: QtWidgets.QPushButton
    # pushButton_auto_all: QtWidgets.QPushButton
    label_state_2: QtWidgets.QLabel
    widget_led_2: QtWidgets.QWidget
    tabWidget_measure_2: QtWidgets.QTabWidget
    horizontalSlider_2: QtWidgets.QSlider
    tab_em_2: QtWidgets.QWidget
    gridLayout_emulator: QtWidgets.QGridLayout
    hLayout_em_2: QtWidgets.QHBoxLayout
    horizontalLayou_forComboBox_comport: QtWidgets.QHBoxLayout
    horizontalLayout_splitter: QtWidgets.QHBoxLayout
    horizontalLayout_main: QtWidgets.QHBoxLayout
    graph_widget: QtWidgets.QWidget
    measure_widget: QtWidgets.QWidget
    radioButton_auto_traprzoid: QtWidgets.QRadioButton
    menu_action_HVIP: QAction
    menu_action_parser: QAction
    menu_action_MPP_cntrl: QAction
    checkBox_enable_test_csa: QtWidgets.QCheckBox
    toolBar: QtWidgets.QToolBar
    # pushButton_setting_trapezoid: QtWidgets.QPushButton

    ########### Виджеты эмулятора #################
    #### Main ####
    lineEdit_emulation_proton: QtWidgets.QLineEdit
    lineEdit_emulation_electron: QtWidgets.QLineEdit
    pushButton_open_electron_dataframe: QtWidgets.QPushButton
    pushButton_open_proton_dataframe: QtWidgets.QPushButton
    pushButton_start_emulation: QtWidgets.QPushButton
    lineEdit_amout_particle: QtWidgets.QLineEdit

    widget_led_start_emulation: QtWidgets.QWidget
    #### Pockets ####
    pushButton_unit_save: QtWidgets.QPushButton
    pushButton_em_ok: QtWidgets.QPushButton
    lineEdit_pips1_MeV_to_mV: QtWidgets.QLineEdit
    lineEdit_pips1_amplif: QtWidgets.QLineEdit
    lineEdit_sipm_MeV_to_mV: QtWidgets.QLineEdit
    lineEdit_sipm_amplif: QtWidgets.QLineEdit
    lineEdit_pips2_amplif: QtWidgets.QLineEdit
    lineEdit_pips3_amplif: QtWidgets.QLineEdit
    lineEdit_pips4_amplif: QtWidgets.QLineEdit
    lineEdit_MeV_to_mV: QtWidgets.QLineEdit
    lineEdit_MeV_to_lsb: QtWidgets.QLineEdit
    lineEdit_mV_to_lsb: QtWidgets.QLineEdit
    pushButton_unit_save_setting: QtWidgets.QLineEdit
    radioButton_MeV: QtWidgets.QRadioButton
    radioButton_lsb: QtWidgets.QRadioButton
    radioButton_mV: QtWidgets.QRadioButton
    label_unit_1: QtWidgets.QLabel
    label_unit_2: QtWidgets.QLabel
    label_unit_3: QtWidgets.QLabel
    label_unit_4: QtWidgets.QLabel
    label_unit_5: QtWidgets.QLabel
    label_unit_6: QtWidgets.QLabel
    label_unit_7: QtWidgets.QLabel
    label_unit_8: QtWidgets.QLabel
    label_unit_9: QtWidgets.QLabel
    label_unit_10: QtWidgets.QLabel
    label_unit_11: QtWidgets.QLabel
    label_unit_12: QtWidgets.QLabel
    checkBox_ampl_pips1: QtWidgets.QCheckBox
    # lineEdit_th_e_0_1: QtWidgets.QLineEdit
    lineEdit_th_e_0_5: QtWidgets.QLineEdit
    lineEdit_th_e_0_8: QtWidgets.QLineEdit
    lineEdit_th_e_1_6: QtWidgets.QLineEdit
    lineEdit_th_e_3: QtWidgets.QLineEdit
    lineEdit_th_e_5: QtWidgets.QLineEdit
    lineEdit_th_p_10: QtWidgets.QLineEdit
    lineEdit_th_p_30: QtWidgets.QLineEdit
    lineEdit_th_p_60: QtWidgets.QLineEdit
    lineEdit_th_p_100: QtWidgets.QLineEdit
    lineEdit_th_p_200: QtWidgets.QLineEdit
    lineEdit_th_p_500: QtWidgets.QLineEdit
    lineEdit_th_pips1_0_1: QtWidgets.QLineEdit

    lineEdit_proton_E_x_10_30: QtWidgets.QLineEdit
    lineEdit_proton_E_x_30_60: QtWidgets.QLineEdit
    lineEdit_proton_E_x_60: QtWidgets.QLineEdit
    lineEdit_proton_E_y_10_30: QtWidgets.QLineEdit
    lineEdit_proton_E_y_30_60: QtWidgets.QLineEdit
    lineEdit_proton_dE_x_10_30: QtWidgets.QLineEdit
    lineEdit_proton_dE_x_30_60: QtWidgets.QLineEdit
    lineEdit_proton_dE_y_10_30: QtWidgets.QLineEdit
    lineEdit_proton_dE_y_30_60: QtWidgets.QLineEdit
    lineEdit_proton_E_x_60: QtWidgets.QLineEdit
    lineEdit_electron_dE: QtWidgets.QLineEdit
    lineEdit_electron_E: QtWidgets.QLineEdit
    lineEdit_comparator: QtWidgets.QLineEdit
    pushButton_reload: QtWidgets.QPushButton
    pushButton_clear_hist: QtWidgets.QPushButton

    ######### Измерение ##############
    lineEdit_triger: QtWidgets.QLineEdit
    spinBox_level_pips: QtWidgets.QSpinBox
    spinBox_level_sipm: QtWidgets.QSpinBox
    lineEdit_point_pips: QtWidgets.QLineEdit
    lineEdit_point_sipm: QtWidgets.QLineEdit
    lineEdit_ACQ1: QtWidgets.QLineEdit
    lineEdit_ACQ2: QtWidgets.QLineEdit
    lineEdit_01_hh_l: QtWidgets.QLineEdit
    lineEdit_05_hh_l: QtWidgets.QLineEdit
    lineEdit_08_hh_l: QtWidgets.QLineEdit
    lineEdit_1_6_hh_l: QtWidgets.QLineEdit
    lineEdit_3_hh_l: QtWidgets.QLineEdit
    lineEdit_5_hh_l: QtWidgets.QLineEdit
    lineEdit_10_hh_l: QtWidgets.QLineEdit
    lineEdit_30_hh_l: QtWidgets.QLineEdit
    lineEdit_60_hh_l: QtWidgets.QLineEdit
    lineEdit_01_hh: QtWidgets.QLineEdit
    lineEdit_05_hh: QtWidgets.QLineEdit
    lineEdit_08_hh: QtWidgets.QLineEdit
    lineEdit_1_6_hh: QtWidgets.QLineEdit
    lineEdit_3_hh: QtWidgets.QLineEdit
    lineEdit_5_hh: QtWidgets.QLineEdit
    lineEdit_10_hh: QtWidgets.QLineEdit
    lineEdit_30_hh: QtWidgets.QLineEdit
    lineEdit_60_hh: QtWidgets.QLineEdit
    lineEdit_hvip_pips: QtWidgets.QLineEdit
    lineEdit_hvip_sipm: QtWidgets.QLineEdit
    lineEdit_hvip_ch: QtWidgets.QLineEdit
    radioButton_db_mode: QtWidgets.QRadioButton
    radioButton_cmbt_mode: QtWidgets.QRadioButton
    radioButton_slnt_mode: QtWidgets.QRadioButton
    radioButton_const_mode: QtWidgets.QRadioButton
    


    ########### var #################
    state_serial = 0
    f_comand_read = 3
    f_comand_write = 6
    start_measure = 81
    connect_to_mpp = 81
    pushButton_connect_flag = 0
    modulename = ["emulator"] # подключаемые модули, обязательно для заполения

    ALL = 0
    SIPM = 1
    PIPS = 2

    CM_DBG_CMD_CONNECT = 0
    CSA_TEST_ENABLE = 5
    HVIP_PIPS_VOLTAGE = 6
    HVIP_PIPS_READ_VOLTAGE = 7

    CM_ID = 1
    MB_F_CODE_16 = 0x10
    MB_F_CODE_3 = 0x03
    MB_F_CODE_6 = 0x06
    REG_COMAND = 0

    DEBUG_MODE = 0x0C
    COMBAT_MODE = 0x0E
    CONSTANT_MODE = 0x0F
    SILENT_MODE = 0x0D

    DDII_SWITCH_MODE = 0x0001

    CMD_TEST_ENABLE = 0x0004
    

    def __init__(self) -> None:
        super().__init__()
        loadUi(os.path.join(os.path.dirname(__file__),  'style/MainWindow4.ui'), self)
        # Создаем конфиг файл
        self.config = configparser.ConfigParser()
        self.parser = parser
        #####################
        self.dialog_trapezoid_settings = MainTrapezoidDialog(self)
        self.plot_pips = pg.PlotWidget()
        self.plot_sipm = pg.PlotWidget()
        self.plot_gist_EdE = pg.PlotWidget()
        self.plot_gist_pips = pg.PlotWidget()
        self.plot_gist_sipm = pg.PlotWidget()
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.comboBox_comm = CustomComboBox_COMport()
        self.size_policy = self.comboBox_comm.sizePolicy()
        self.size_policy.setHorizontalPolicy(QSizePolicy.Policy.Preferred)
        self.comboBox_comm.setSizePolicy(self.size_policy)
        self.splitter.addWidget(self.graph_widget)
        self.splitter.addWidget(self.measure_widget)
        self.pushButton_start_emulation.setEnabled(False)
        # Устанавливаем минимальные размеры для виджетов
        # self.graph_widget.setMinimumWidth(100)
        # self.measure_widget.setMinimumWidth(401)
        # Устанавливаем размер сплиттера
        self.splitter.setSizes([800, 483])
        self.horizontalLayout_splitter.addWidget(self.splitter)
        self.vLayout_pips.addWidget(self.plot_pips)
        self.vLayout_sipm.addWidget(self.plot_sipm)
        self.vLayout_gist_EdE.addWidget(self.plot_gist_EdE)
        self.vLayout_gist_pips.addWidget(self.plot_gist_pips)
        self.vLayout_gist_sipm.addWidget(self.plot_gist_sipm)
        self.horizontalLayou_forComboBox_comport.addWidget(self.comboBox_comm)
        # Создание вертикальной линии уровня pips
        self.posiInfLine_pips = 10
        self.hoverPen_pips = pg.mkPen(color=(200, 100, 0), width=5, style=QtCore.Qt.PenStyle.DashDotLine)
        self.pen_pips = pg.mkPen(color=(100, 100, 0), width=5, style=QtCore.Qt.PenStyle.DashDotLine)
        self.v_line_pips = pg.InfiniteLine(pos=self.posiInfLine_pips, angle=0, movable=True,
                                hoverPen = self.hoverPen_pips, pen = self.pen_pips)
        self.plot_pips.addItem(self.v_line_pips)
        self.v_line_pips_label = pg.InfLineLabel(line = self.v_line_pips, 
                                                text = str(self.posiInfLine_pips),
                                                position=0.95)
        # Создание вертикальной линии уровня sipm
        self.posiInfLine_sipm = 10
        self.hoverPen_sipm = pg.mkPen(color=(200, 100, 0), width=5, style=QtCore.Qt.PenStyle.DashDotLine)
        self.pen_sipm = pg.mkPen(color=(100, 100, 0), width=5, style=QtCore.Qt.PenStyle.DashDotLine)
        self.v_line_sipm = pg.InfiniteLine(pos=self.posiInfLine_sipm, angle=0, movable=True,
                                hoverPen = self.hoverPen_sipm, pen = self.pen_sipm)
        self.plot_sipm.addItem(self.v_line_sipm)
        self.v_line_sipm_label = pg.InfLineLabel(line = self.v_line_sipm,
                                                text = str(self.posiInfLine_sipm),
                                                position=0.95)

        ##################### Коннекторы ###################
        # self.v_line_pips.sigPositionChanged.connect(lambda: self.update_line_pips())
        # self.v_line_pips.sigPositionChanged.connect(lambda: self.update_line_sipm())
        # self.v_line_pips.sigPositionChangeFinished.connect(self.update_line_static_pips)
        # self.v_line_sipm.sigPositionChangeFinished.connect(self.update_line_static_sipm)
        ############## Инициализация других окон #############
        self.dialog_trap: MainTrapezoidDialog =  MainTrapezoidDialog(self)
        self.munu_action_HVIP: MainHvipDialog =  MainHvipDialog(self)
        self.menu_action_MPP_cntrl_dialog: MainMppControlDialog =  MainMppControlDialog(self)
        

        ############## Tool Bar #############
        self.start_accumulation_wave_start_action = QAction(QIcon("./icon/start.svg"), None, self) # color #949494
        self.stop_accumulation_wave_stop_action = QAction(QIcon("./icon/stop_notVisible.svg"), None, self) # color 94949459
        self.toolBar.addAction(self.start_accumulation_wave_start_action)
        self.toolBar.addAction(self.stop_accumulation_wave_stop_action)
        self.start_accumulation_wave_start_action.setToolTip("Начать накопление")
        self.stop_accumulation_wave_stop_action.setToolTip("Остановить накопление")
        self.stop_accumulation_wave_stop_action.setEnabled(False)

        self.v_line_pips.sigPositionChanged.connect(lambda: self.update_line(self.lineEdit_level_pips,
                                                                            self.v_line_pips_label,
                                                                            self.v_line_pips, self.hoverPen_pips,
                                                                            self.pen_pips, 0))
        self.v_line_sipm.sigPositionChanged.connect(lambda: self.update_line(self.lineEdit_level_sipm,
                                                                            self.v_line_sipm_label,
                                                                            self.v_line_sipm, self.hoverPen_sipm,
                                                                            self.pen_sipm, 0))
        self.v_line_pips.sigPositionChangeFinished.connect(lambda: self.update_line_static(self.v_line_pips,
                                                                            self.pen_pips))
        self.v_line_sipm.sigPositionChangeFinished.connect(lambda: self.update_line_static(self.v_line_sipm,
                                                                            self.pen_sipm))
        self.lineEdit_level_pips.editingFinished.connect(lambda: self.update_line(self.lineEdit_level_pips,
                                                                            self.v_line_pips_label,
                                                                            self.v_line_pips, self.hoverPen_pips,
                                                                            self.pen_pips, 1))
        self.lineEdit_level_sipm.editingFinished.connect(lambda: self.update_line(self.lineEdit_level_sipm,
                                                                            self.v_line_sipm_label,
                                                                            self.v_line_sipm, self.hoverPen_sipm,
                                                                            self.pen_sipm, 1))
        self.pushButton_connect_2.clicked.connect(self.pushButtonConnect_clicked)
        # self.pushButton_single_pips.clicked.connect(lambda: self.pushButton_single_measure_clicked(self.PIPS))
        # self.pushButton_auto_pips.clicked.connect(lambda: self.pushButton_auto_measure_clicked(self.PIPS))
        # self.pushButton_single_sipm.clicked.connect(lambda: self.pushButton_single_measure_clicked(self.SIPM))
        # self.pushButton_auto_sipm.clicked.connect(lambda: self.pushButton_auto_measure_clicked(self.SIPM))
        self.pushButton_single_all.clicked.connect(lambda: self.pushButton_single_measure_clicked(self.ALL))
        # self.pushButton_auto_all.clicked.connect(lambda: self.pushButton_auto_measure_clicked(self.ALL))
        self.pushButton_trapezoid.clicked.connect(self.pushButton_trapezoid_clicked_handler)
        self.menu_action_HVIP.triggered.connect(self.menu_action_HVIP_triggered)
        self.menu_action_parser.triggered.connect(self.menu_action_parser_triggered)
        self.menu_action_MPP_cntrl.triggered.connect(self.menu_action_MPP_cntrl_triggered)
        self.checkBox_enable_test_csa.stateChanged.connect(self.checkBox_enable_test_csa_stateChanged)
        self.start_accumulation_wave_start_action.triggered.connect(self.start_accumulation_wave_start_action_toolbar_triggered)
        self.stop_accumulation_wave_stop_action.triggered.connect(self.stop_accumulation_wave_stop_action_toolbar_triggered)
        self.radioButton_db_mode.toggled.connect(lambda: self.radioButton_mode_toggled(mode = self.DEBUG_MODE))
        self.radioButton_slnt_mode.toggled.connect(lambda: self.radioButton_mode_toggled(mode = self.SILENT_MODE))
        self.radioButton_cmbt_mode.toggled.connect(lambda: self.radioButton_mode_toggled(mode = self.COMBAT_MODE))
        self.radioButton_const_mode.toggled.connect(lambda: self.radioButton_mode_toggled(mode = self.CONSTANT_MODE))
        self.pushButton_clear_hist.clicked.connect(self.pushButton_clear_hist_clicked_handler)

        # Обновление файлов в потоке
        self.timer = QTimer()
        self.timer.timeout.connect(self.queue_qt_plot)
        self.timer.start(10)

        # self.pushButton_setting_trapezoid.clicked.connect(self.pushButton_trapezoid_setting_handler)
        
        # self.comboBox_comm.highlighted.connect(self.comboBox_comm_highlighted)
        # self.lineEdit_level_pips.editingFinished.connect(self.lineEdit_level_pips_editingFinished)
        # self.lineEdit_level_sipm.editingFinished.connect(self.lineEdit_level_sipm_editingFinished)
        self.init_COMports_comboBox_comport_list()
        self.tmp_bufer = []
        self.x : list[int]
        self.y: list[int]
        self.T_decay: int = 1
        self.T_rise: int = 1
        self.T_top: int = 1
        self.invert: int = 1
        self.data_pips = []
        self.data_sipm = []
        self.color_pips = (255, 255, 0)
        self.color_sipm = (0, 255, 255)
        self.pushButton_auto_flag = 1
        self.queue = Queue()
        self.gistogram_data_pips = []
        self.gistogram_data_sipm = []
        self.gistogram_data_EdE = []
        self.start_accumulation_flag = 1
        self.data_flow_flag: int = 0
        self.folder_path: str = ""
        self.current_datetime = datetime.datetime.now()
        self.file_extension = 0
        self.gistogram_data_pips = []
        self.gistogram_data_sipm = []
        self.gistogram_data_EdE = []

        # self.finished = pyqtSignal()
        # config log
        self.logger = log_init()


        # Заполнить modulename!!! Добавление сторонних модулей (плагинов).
        for module in self.modulename:
            if module not in sys.modules:
                self.tabWidget_measure_2.removeTab(2)  # удаление неимпортированных модулей из tabWidget_measure
            else:
                self.emulator = emulator(self)
                ## в эмуляторе есть слайдер, который будет заменен на Toggle
                # emulator.ChangeSliderToToggle(self.horizontalSlider, self.tab_em, self.hLayout_em)

                # emToggle = pyToggle()
                # self.horizontalSlider.deleteLater()
                # Emulator_layout = QtWidgets.QVBoxLayout(self.tab)
                # Emulator_layout.addWidget(emToggle)
                # self.tab.setLayout(self.gridLayout_emulator)
                # self.setCentralWidget(emToggle)

    ############ Infinite Line Event ##############
    def update_line(self,
                    lineEdit_level: QLineEdit,
                    v_line_label: pg.TextItem,
                    v_line: pg.Color,
                    hoverPen: pg.Color,
                    pen: pg.Color,
                    flag_edit_text: int) -> None:

        if flag_edit_text == 1:
            pos = round(int(lineEdit_level.text()))
            v_line.setPos(pos)
            #  TODO: Сделать обновлдение lineEdit
            # v_line.setPen(pen)
            self.update_line_static(v_line, pen)
        else:
            pos = round(v_line.value())
            # v_line.setPos(pos)
            # v_line.setPen(hoverPen)
        # print("Положение вертикальной линии:", pos)
        lineEdit_level.setText(str(pos))
        v_line_label.setText(str(pos))



    def update_line_static(self, v_line: pg.Color, pen: pg.Color) -> None:
        """
        Если курсор с InfLine убран, то неободимо вернуть цвет в начальное состояние.
        """
        v_line.setPen(pen)

    def radioButton_mode_toggled(self, mode):
        match (mode):
            case self.DEBUG_MODE:
                cmd = threading.Thread(target=self.thread_write_reg_not_answer(self.DDII_SWITCH_MODE, 
                                                                            self.DEBUG_MODE, 
                                                                            self.CM_ID), 
                                                                            daemon = True)        
                cmd.start()
            case self.SILENT_MODE:
                cmd = threading.Thread(target=self.thread_write_reg_not_answer(self.DDII_SWITCH_MODE, 
                                                                            self.SILENT_MODE, 
                                                                            self.CM_ID), 
                                                                            daemon = True)        
                cmd.start()
            case self.COMBAT_MODE:
                cmd = threading.Thread(target=self.thread_write_reg_not_answer(self.DDII_SWITCH_MODE, 
                                                                            self.COMBAT_MODE, 
                                                                            self.CM_ID), 
                                                                            daemon = True)        
                cmd.start()
            case self.CONSTANT_MODE:
                cmd = threading.Thread(target=self.thread_write_reg_not_answer(self.DDII_SWITCH_MODE, 
                                                                            self.CONSTANT_MODE, 
                                                                            self.CM_ID), 
                                                                            daemon = True)        
                cmd.start()

    ############ handler button ##############

    def pushButton_clear_hist_clicked_handler(self):
        self.client.write_registers(address = 0x0014, values = [0x0000 for i in range(18)], slave = self.mpp_id)
        log_s(self.send_handler.mess)

    def pushButtonConnect_clicked(self) -> None:
        """
        Эта функция вызывается при нажатии кнопки подключение.
        Для успешного подключения необходимы значения:
        1. ID MPP
        2. Cкорость передачи данных последовательного порта
        3. Любая команда записи modbus
        4. Команда выдачи ответа мпп
        Если отет есть, значит устройство подключено

        Returns:
        None
        """
        baudrate = int(self.lineEdit_Bauderate_2.text())
        self.mpp_id = int(self.lineEdit_IDmpp_2.text())

        self.serialConnect(self.mpp_id, baudrate, self.f_comand_write, self.start_measure)

    def pushButton_single_measure_clicked(self, chanal: int) -> None:
        """
        Эта функция вызывается при нажатии кнопки «Одиночный».
        Получение waveform ADCA и построение осциллограммы
        """
        match chanal:
            case self.ALL:
                t_all_single = threading.Thread(target=self.thread_readWaveform_adc_all, daemon = True)
                t_all_single.start()
                # t_all_single.join()
                # self.qt_plotter(self.data_pips, self.v_line_pips, self.plot_pips, color = self.color_pips)
                # self.qt_plotter(self.data_sipm, self.v_line_sipm, self.plot_sipm, color = self.color_sipm)
            case self.PIPS:
                t_pips_single = threading.Thread(target=self.thread_readWaveform_adcA, daemon = True)
                t_pips_single.start()
                # t_pips_single.join()
                # self.qt_plotter(self.data_pips, self.v_line_pips, self.plot_pips, color = self.color_pips) # раскомментировать

            case self.SIPM:
                t_sipm_single = threading.Thread(target=self.thread_readWaveform_adcB, daemon = True)
                t_sipm_single.start()
                # t_sipm_single.join() # запустили поток как фоновый и ждем конца выполнения
                # self.qt_plotter(self.data_sipm, self.v_line_sipm, self.plot_sipm, color = self.color_sipm)


    def pushButton_auto_measure_clicked(self, chanal: int) -> None:
        """
        Эта функция вызывается при нажатии кнопки «Автозапуск».
        Получение waveform ADCA и построение осциллограммы. 
        """
        if self.pushButton_auto_flag == 1:
            self.pushButton_auto_flag = 0
            match chanal:
                case self.ALL:
                    t_all_auto = threading.Thread(target=self.thread_readWaveform_adc_auto_adc_all, daemon = True)
                    
                    t_all_auto.start()
                    # t_all_auto.join()

                case self.PIPS:
                    t_pips_auto = threading.Thread(target=self.thread_readWaveform_adc_auto_adcA, daemon = True)
                    # t_pips_auto = WorkerThread()
                    t_pips_auto.start()
                    # self.qt_plotter(waveform, self.v_line_pips, self.plot_pips, color = self.color_pips)
                    # t_pips_auto.join()
                case self.SIPM:
                    t_sipm_auto = threading.Thread(target=self.thread_readWaveform_adc_auto_adcB, daemon = True)
                    t_sipm_auto.start()
                    # t_sipm.join()
        else:
            self.pushButton_auto_flag = 1
        
    def tmp_print_treading(self, data):
        print(data)


    def pushButton_trapezoid_clicked_handler(self) -> None:
        self.dialog_trap.show()

    def checkBox_enable_test_csa_stateChanged(self, state) -> None:
        if state == 2:
            st = 1
        else:
            st = 0
        t_flow_auto = threading.Thread(target=self.thread_write_reg_not_answer(self.CMD_TEST_ENABLE, 
                                                                            st, 
                                                                            self.CM_ID), 
                                                                            daemon = True)        
        t_flow_auto.start()

    ############ Triggered Menu Action ##############
    def menu_action_HVIP_triggered(self) -> None:
        self.munu_action_HVIP.show()
    
    def menu_action_MPP_cntrl_triggered(self) -> None:
        self.menu_action_MPP_cntrl_dialog.show()

    def menu_action_parser_triggered(self) -> None:
        pass

    ############ Triggered Menu Bar ##############
    def start_accumulation_wave_start_action_toolbar_triggered(self) -> None:
        self.start_accumulation_wave_start_action.setIcon(QIcon("./icon/start_notVisible.svg"))
        self.start_accumulation_wave_start_action.setToolTip("Пауза")
        self.stop_accumulation_wave_stop_action.setEnabled(True)
        self.start_accumulation_wave_start_action.setEnabled(False)
        self.stop_accumulation_wave_stop_action.setIcon(QIcon("./icon/stop.svg"))
        self.start_accumulation_flag = 0
        # папка /log/data_flow/ с сегодняшней датой и временем
        
        folder_name = self.current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:23]
        self.folder_path = os.path.join("./log/data_flow/", folder_name)
        try:
            self.file_extension += 1
            os.makedirs(self.folder_path)
        except FileExistsError:
            os.makedirs(self.folder_path + "_" + str(self.file_extension))
        self.logger.debug("Создана папка для записи данных: " + self.folder_path)
        self.data_flow_flag = 1 # флаг записи данных в файл
        self.pushButton_auto_flag = 0 # флаг автозапуска
        t_flow_auto = threading.Thread(target=self.thread_readWaveform_adc_flowl, daemon = True)        
        t_flow_auto.start()
        # ese:
        #     self.start_accumulation_wave_start_action.setIcon(QIcon("./icon/resume.svg"))
        #     self.data_flow_flag = 0
        
        #     self.pushButton_auto_flag = 1
        #     self.start_accumulation_wave_start_action.setToolTip("Продолжить накопление")
        #     self.start_accumulation_flag = 1

    
    def stop_accumulation_wave_stop_action_toolbar_triggered(self) -> None:
        self.stop_accumulation_wave_stop_action.setIcon(QIcon("./icon/stop_notVisible.svg"))
        self.start_accumulation_wave_start_action.setIcon(QIcon("./icon/start.svg"))
        self.stop_accumulation_wave_stop_action.setEnabled(False)
        self.start_accumulation_wave_start_action.setEnabled(True)
        self.data_flow_flag = 0 # запрещаем запись данных в файл
        self.pushButton_auto_flag = 1 # флаг автозапуска
        self.start_accumulation_wave_start_action.setToolTip("Начать накопление")
        # if self.start_accumulation_flag == 0:
        #     self.start_accumulation_wave_start_action_toolbar_triggered()
    


    ############ Потоки ##############
    def thread_write_reg_not_answer(self, adr, val, slv):
        self.client.write_registers(address = adr, values = val, slave = slv)
        log_s(self.send_handler.mess)


    def thread_readWaveform_adcA(self) -> None:

        self.start_measurement_func()

        # self.start_measurement_func()
        waveform = self.readWaveform_adcA()
        self.data_pips = waveform
        self.queue.put((waveform, self.v_line_pips, self.plot_pips, self.color_pips))

        # self.logger.debug(self.tmp_bufer)

    def thread_readWaveform_adcB(self) -> None:
        self.start_measurement_func()

        # self.start_measurement_func()
        waveform = self.readWaveform_adcB()
        self.data_sipm = waveform
        self.queue.put((waveform, self.v_line_sipm, self.plot_sipm, self.color_sipm))
        

    def thread_readWaveform_adc_all(self) -> None:
        self.start_measurement_func()
        waveformA = self.readWaveform_adcA()
        waveformB = self.readWaveform_adcB()
        self.data_pips = waveformA
        self.data_sipm = waveformB
        self.queue.put((waveformA, self.v_line_pips, self.plot_pips, self.color_pips))
        self.queue.put((waveformB, self.v_line_sipm, self.plot_sipm, self.color_sipm))

    def thread_readWaveform_adc_auto_adcA(self) -> None:
        """
        Ищем waveform такую, чтобы max значение было выше порого. Если так, то выхожим из while
        """
        max_value = 0
        while max_value < int(self.v_line_pips.value()):
            
            self.reciveModbus(2)
            # self.start_measurement_func()
            # waveform = self.readWaveform_adcA()
            # self.data_pips = waveform
            # self.queue.put((waveform, self.v_line_pips, self.plot_pips, self.color_pips))
            # data = self.hex_to_list(waveform)[1]
            # max_value = max(data)
            self.start_measurement_func()
            waveform = self.readWaveform_adcA()
            self.data_pips = waveform
            self.queue.put((waveform, self.v_line_pips, self.plot_pips, self.color_pips))
            data = self.hex_to_list(waveform)[1]
            max_value = max(data)
            if self.pushButton_auto_flag == 1:
                break
        self.pushButton_auto_flag = 1

    def thread_readWaveform_adc_auto_adcB(self) -> None:
        max_value = 0
        while max_value < int(self.v_line_sipm.value()):
            self.start_measurement_func()
            waveform = self.readWaveform_adcB()
            self.data_sipm = waveform
            self.queue.put((waveform, self.v_line_sipm, self.plot_sipm, self.color_sipm))
            data = self.hex_to_list(waveform)[1]
            max_value = max(data)
            if self.pushButton_auto_flag == 1:
                break
        self.pushButton_auto_flag = 1

    def thread_readWaveform_adc_auto_adc_all(self) -> None:
        max_valueA = -m.inf
        max_valueB = -m.inf
        while max_valueA < int(self.v_line_pips.value()) or max_valueB < int(self.v_line_sipm.value()):
            self.start_measurement_func()
            if max_valueA < self.v_line_pips.value():
                self.start_measurement_func()
                waveformA = self.readWaveform_adcA()
                self.data_pips = waveformA
                self.queue.put((waveformA, self.v_line_pips, self.plot_pips, self.color_pips))
                dataA = self.hex_to_list(waveformA)[1]
                max_valueA = max(dataA)
            if max_valueB < self.v_line_sipm.value():
                self.start_measurement_func()
                waveformB  = self.readWaveform_adcB()
                self.data_sipm = waveformB
                self.queue.put((waveformB, self.v_line_sipm, self.plot_sipm, self.color_sipm))
                dataB = self.hex_to_list(waveformB)[1]
                max_valueB = max(dataB)
            if self.pushButton_auto_flag == 1:
                break
        self.pushButton_auto_flag = 1

    def thread_readWaveform_adc_flowl(self) -> None:
        while 1:
            self.start_measurement_func()
            waveformA = self.readWaveform_adcA()
            self.data_pips = waveformA
            self.queue.put((waveformA, self.v_line_pips, self.plot_pips, self.color_pips))
            waveformB  = self.readWaveform_adcB()
            self.data_sipm = waveformB
            self.queue.put((waveformB, self.v_line_sipm, self.plot_sipm, self.color_sipm))
            if self.pushButton_auto_flag == 1:
                break
        self.pushButton_auto_flag = 1

    ############ function service ##############

    def trapezoid_calculater(self, x, y, T_decay: int, T_rise: int, T_top: int, invert = 0):
        """
            Calculate Moving Window Deconvolution
        """
        try:
            # dx : int = 1
            Ndecay : int = T_decay
            Nrise : int = T_rise
            Ntop : int = T_top
            # betta: float = m.exp(-dx/self.T_decay)
            Len: int = len(y)

            L = Nrise
            M = L + Ntop
            if invert:
                yin = [-y for y in y]
            else:
                yin  = y
            # 1-Stage Moving window deconvolution
            # allocate memory
            ym = cp.deepcopy(yin)
            # window summation
            for i in range(M + 1, Len):
                dm = y[i] - yin[i-M]
                ma = 0
                for j in range(i-M, i-1):
                    ma = ma + yin[j]
                ym[i] = dm + ma/Ndecay
            # 2-Stage Moving average
            ytrp = cp.deepcopy(yin)
            for i in range(L+1, Len):
                ytrp[i] = 0
                for j in range(i-L, i-1):
                    ytrp[i] = ytrp[i] + ym[j]
                ytrp[i] = ytrp[i] / L
            return x, ytrp
        except Exception:
            self.logger.debug("Нет данных или не заданы константы трапеции")
            return [], []

    def calculateCrc16_modbus(self, data: int) -> int:
        """
        Эта функция вычисляет CRC-16 для заданных данных, используя полином MODBUS.

        Parameters:
        data (int): The data to be used in the calculation.

        Returns:
        int: The calculated CRC-16 value.
        """
        crc16_func = crcmod.predefined.mkPredefinedCrcFun('modbus')
        num_bytes: int = m.ceil(data.bit_length() / 8)
        data_bytes: bytes = data.to_bytes(num_bytes, byteorder='big')
        crc = crc16_func(data_bytes)
        return crc

    def swappedByte_crc_modbus(self, data: int) -> int:
        """
        Эта функция меняет местами старшие и младшие байты целого числа и возвращает результат.

        Parameters:
        data (int): The integer to be swapped.

        Returns:
        int: The result of swapping the high and low bytes of the input integer.
        """
        # Получение старшего и младшего байта
        byte1: int = (data >> 8) & 0xff
        byte2: int = data & 0xff
        # Обмен местами старшего и младшего байта
        swapped_data: int = (byte2 << 8) | byte1
        return swapped_data

    def init_COMports_comboBox_comport_list(self):
        for n, (portname, desc, hwid) in enumerate(sorted(serial.tools.list_ports.comports())):
            self.comboBox_comm.addItem(portname)
    
    def get_telemetria(self):
        result: ModbusResponse = self.client.read_holding_registers(0x0000, 62, slave=1)
        log_s(self.send_handler.mess)
        return result
    
    def pars_telemetria(self, tel: ModbusResponse) -> None:
        ## endian is wrong
        tel = tel.encode()
        tel_b = int(tel[1:2].hex(), 16)
        if tel_b == self.DEBUG_MODE:
            self.radioButton_db_mode.setChecked(True)
        elif tel_b == self.COMBAT_MODE:
            self.radioButton_slnt_mode.setChecked(True)
        elif tel_b == self.CONSTANT_MODE:
            self.radioButton_cmbt_mode.setChecked(True)
        elif tel_b == self.SILENT_MODE:
            self.radioButton_const_mode.setChecked(True)
        tel_b = int(tel[1:2].hex(), 16)
        print(tel[2:2])
        print(tel_b)
        self.lineEdit_triger.setText("")

    ############ function connect mpp ##############
    def serialConnect(self, id: int, baudrate: int, f_comand: int, data: int) -> None:
        """Подключкние к ДДИИ
        Подключение происходит одновременно к ЦМ и МПП. 
        Для подключение к МПП нужно задать првельный ID. 
        При успешном подключении ЦМ выдаст структуру ddii_mpp_data.

        Parameters:
        self (экземпляр Engine): текущий экземпляр класса Engine.
        id (int): идентификатор подключаемого MPP.
        baudrate (int): Скорость передачи данных для последовательной связи.
        f_comand (int): команда для записи в Modbus.
        data (int): Команда чтения из Modbus.

        Returns:
        None
        """
        # logging.basicConfig()
        log = logging.getLogger('pymodbus')
        log.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.addFilter(SendFilter())
        log.addHandler(handler)
        self.send_handler = SendHandler()
        log.addHandler(self.send_handler)
        status_CM = 0
        self.status_MPP = 0
        self.state_serial = 0
        tmp_res = []
        if self.pushButton_connect_flag == 0:
            port = self.comboBox_comm.currentText()
            self.client = ModbusClient.ModbusSerialClient(
                port,
                timeout=1,
                baudrate=baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
                handle_local_echo=True,
                )
            if self.client.connect():
                self.state_serial = 1
                self.logger.debug(port + " ,Baudrate = " + str(baudrate) +
                                ", Parity = "+"None"+
                                ", Stopbits = "+ "1" +
                                ", Bytesize = " + str(self.client.comm_params.bytesize))
            else:
                self.label_state_2.setText("State: COM-порт занят. Попробуйте переподключиться")
                self.state_serial = 0

            if self.state_serial == 1:
                # две команды на подключение: 1-ЦМ, 2-МПП
                # CM 01 10 0000 0000 C0 09
                # MPP 0F 06 0000 0051 49 18
                ######## CM #######     
                self.client.write_registers(address = self.DDII_SWITCH_MODE, values = self.DEBUG_MODE, slave = self.CM_ID)
                # print(self.send_handler.mess)
                log_s(self.send_handler.mess)
                result = self.get_telemetria()
                log_s(self.send_handler.mess)
                try:
                    tmp_res = result.registers
                except Exception:
                    self.logger.debug("Modbus Error CM")
                if not tmp_res:
                    self.logger.debug("Соединение c ЦМ не установлено")
                else:
                    status_CM = 1
                    self.widget_led_2.setStyleSheet(style.widget_led_on())
                    self.pars_telemetria(result)
                ######## MPP #######  
                slv = int(self.lineEdit_IDmpp_2.text())
                result: ModbusResponse = self.client.read_holding_registers(0x0000, 4, slave=slv)
                log_s(self.send_handler.mess)
                try:
                    tmp_res = result.registers
                except Exception:
                    self.logger.debug("Modbus Error MPP")
                    self.status_MPP = 0
                    self.logger.debug("Соединение c МПП не установлено")
                    if status_CM == 0:
                        self.label_state_2.setText("State: CM - None, MPP - None")
                        self.widget_led_2.setStyleSheet(style.widget_led_off())
                        self.client.close()
                    else:
                        self.label_state_2.setText("State: CM - OK, MPP - None")
                else:
                    self.status_MPP = 1
                    if status_CM == 1:
                        self.label_state_2.setText("State: CM - OK, MPP - OK")
                    else:
                        self.label_state_2.setText("State: CM - None, MPP - OK")
                self.pushButton_connect_2.setText("Отключить")
                self.pushButton_connect_flag = 1
        else:
            self.pushButton_connect_2.setText("Подключить")
            self.client.write_registers(address = self.DDII_SWITCH_MODE, values = self.COMBAT_MODE, slave = self.CM_ID)
            self.pushButton_connect_flag = 0
            self.widget_led_2.setStyleSheet(style.widget_led_off())
            self.client.close()
            self.label_state_2.setText("State: ")
    ############ Function MODBUS ################
    def sendModbus(self, data):
        """
        Эта функция используется для отправки данных по Modbus.
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

        Args:
            data (int): The data to be sent over Modbus.

        Returns:
            tuple: A tuple containing the number of bytes sent and CRC.

        Raises:
            SerialException: If there is an error while communicating with the serial port.
        """
        crc: int = self.calculateCrc16_modbus(data)
        data_crc: int = (data << 16) + self.swappedByte_crc_modbus(crc)
        num_bytes: int = m.ceil(data_crc.bit_length() / 8)
        data_bytes: bytes = data_crc.to_bytes(num_bytes, byteorder='big')
        try:
            # self.ser.open()
            self.ser.write(data_bytes)
            # self.ser.close()
            log_s("TX", data_bytes.hex())
            # print(data_bytes.hex())
        except serial.SerialException as e:
            self.label_state_2.setText("State: Общая ошибка последовательного порта.")
            self.logger.error("Общая ошибка последовательного порта: " + str(e))
        return num_bytes, data_crc

    def send_comand_Modbus(self, dev_id: int, f_code: int, reg_cnt: int, comand: int) -> None:
        """
            Отдельная функция для отправки модбасс команд
            
            Args:
            dev_id (int): ID девайса
            f_code (int): Функциональная команда
            reg_cnt (int): Количество регистров считывания (если нет, то 00 00)
            data : данные для передачи
        """

        transaction: int = (dev_id << 40) + \
                            (f_code << 32) + \
                            (reg_cnt << 16) +\
                            + comand
        self.sendModbus(transaction)

    def get_transaction_Modbus(self, num_bite: int) -> str:
        """
            Получение транзакции модбас
            Обрезаем эхо, CRC, заголовок модбас
            Returns:
        """
        # self.logger.debug("Buffer input = " + str(self.ser.in_waiting))
        # transaction: bytes = self.ser.readall()
        # self.ser.reset_input_buffer()
        # log_s("TX", transaction.hex())
        # self.ser.reset_input_buffer()

        transaction = self.reciveModbus(0)[::-1]
        tr = transaction[4:num_bite*2+4]
        self.logger.debug(tr[::-1])
        return tr[::-1]
    
    def write_modbus_timeout(self, dev_id:int, data:str, num_bite:int, timeout:int) -> str:
        """F CODE 16
        Отправляет команду и ждет ответ
        Args:
            dev_id (_type_): ID
            num_bite (_type_): Колдичество байт для приема
            timeout (_type_): Время одидания ответа

        Returns:
            str: _description_
        """
        self.send_comand_Modbus(dev_id = dev_id,
                                        f_code = self.MB_F_CODE_16, 
                                        comand = self.REG_COMAND, 
                                        reg_cnt = self.CM_DBG_CMD_CONNECT)
        time_start = time.time_ns() // 1_000_000
        time_now = time_start
        while timeout > time_now - time_start:
            time_now = time.time_ns() // 1_000_000
            transaction = self.reciveModbus(0)[::-1]
            tr = transaction[4:num_bite*2+4]
            # self.logger.debug(tr[::-1])
            self.logger.debug(tr[:2])
            self.logger.debug("Timeout:" + str(time.time_ns() // 1_000_000 - time_start))
            if tr[:2] == dev_id:
                return tr[::-1]
        return "^_^"

    def reciveModbus(self, amount_bytes: int) -> str:
        """
        TODO: Проверка CRC
        """

        try:
            # self.ser.open()
            self.logger.debug("Buffer input = " + str(self.ser.in_waiting))
            # self.ser.reset_input_buffer()
            answer: bytes = self.ser.readall()
            # self.ser.reset_input_buffer()
            # self.ser.close()
            # self.logger.debug(answer.hex())
            # print(answer.hex())
            log_s("RX", answer.hex())
            # return int(answer.hex(), 16)
            return answer.hex()
        except serial.SerialException as e:
            self.label_state_2.setText("State: Общая ошибка последовательного порта.")
            self.logger.error("Общая ошибка последовательного порта: " + str(e))
            return ""

    ###### Read data & plot oscillogramm #########
    def readWaveform_adcA(self) -> list[int]:
        """
        This function is used to read the waveform from the ADCA of the MPP.
        Преобразует hex в лист для отрисовки графиков +
        Регистры хранения осфиллограмм:
        ADCA: 0xA000 ... 0xA1FF (512 байт)
        ADCB: 0xA200 ... 0xA3FF (512 байт)

        Returns:
            A list containing the waveform data.
        """
        initial_reg = 0xA000
        waveform_list = self.readWaveform_engine(initial_reg)
        self.tmp_bufer = waveform_list
        return waveform_list

    def readWaveform_adcB(self) -> list[int]:
        """
        This function is used to read the waveform from the ADCA of the MPP.
        Регистры хранения осфиллограмм:
        ADCA: 0xA000 ... 0xA1FF (512 байт) 2*256
        ADCB: 0xA200 ... 0xA3FF (512 байт) 2*256
        Returns:
            A list containing the waveform data.
        """
        initial_reg = 0xA200
        waveform_list = self.readWaveform_engine(initial_reg)
        self.tmp_bufer = waveform_list
        return waveform_list

    def start_measurement_func(self):
        start_measure_comand: int = (self.mpp_id << 40) + (self.f_comand_write << 32) + (self.start_measure << 0)
        num_bytes, data_crc = self.sendModbus(start_measure_comand)
        self.reciveModbus(num_bytes*2)


    def readWaveform_engine(self, initial_reg: int):
        """
        Начать змерение.
        Считывание waveform порциями по N байт из памяти МПП. Сначала формируется запрос к МПП на считывание:
        ModBuss:
            0E 06 00 00 00 81 A6ED
            |   | |__|   |__|   |-- CRC16 (старший байт первый, младший байт последний)
            |   |    |      |-- Команда МПП начать считывание waveform из памяти (start_measure)
            |   |    |-- Регистры начала считывания (если запрос 00 00) (нет)
            |   |-- Команда на запись (f_comand_write)
            |-- Адрес устройства (mpp_id)

        Регистры хранения осфиллограмм:
        ADCA: 0xA000 ... 0xA1FF (512 байт)
        ADCB: 0xA200 ... 0xA3FF (512 байт)

        Размер пакета Modbus PDU(Protocol Data Unit)
        Ограничение: 253 байта
        
        Args:
            initial_reg (int): С каго регистра начать считывать осциллограмму
            amount_read_reg (int) = 100: кол-во байт для считывания

        TODO: Выделить отдельный поток для считывания и парсинга осциллограммы.
        Возможно нужно добавить, чтобы при считывании все кнопки осциллограммы становились неактивными.
        Returns:
            A list containing the waveform data.
        """
        amount_read_reg = 126 # так как потом умножается на 2
        # start_measure_comand: int = (self.mpp_id << 40) + (self.f_comand_write << 32) + (self.start_measure << 0)
        # num_bytes, data_crc = self.sendModbus(start_measure_comand)
        # self.reciveModbus(num_bytes*2)
        # time.sleep(0.5)
        waveform_list = []
        end_reg = 0
        if initial_reg == 0xA000:
            end_reg = 0xA1FF
        if initial_reg == 0xA200:
            end_reg = 0xA3FF
        while initial_reg != end_reg:
            read_waveform_comand: int = (self.mpp_id << 40) + \
                                        (self.f_comand_read << 32) + \
                                        (initial_reg << 16) + \
                                        amount_read_reg
            self.sendModbus(read_waveform_comand)
            data_hex: str = self.get_transaction_Modbus(amount_read_reg*2)
            
            # waveform_data: str = data_hex[22:(amount_read_reg * 4 + 22)]
            # self.logger.debug(data)
            waveform_list = waveform_list + self.parserWaveform(data_hex)
            initial_reg = initial_reg + amount_read_reg
            if initial_reg + amount_read_reg > end_reg:
                amount_read_reg = end_reg - initial_reg
        # self.logger.debug(waveform_list)
        # print(waveform_list)
        return waveform_list

    def parserWaveform(self, data: str) -> list[str]:
        """
        Эта функция принимает 16-битное целое число и возвращает список строк из 4 символов.
        Функция сначала преобразует входное целое число в шестнадцатеричную строку, удаляет префикс «0x»,
        а затем использует регулярное выражение для извлечения из строки четырехсимвольных подстрок.
        Затем функция возвращает список подстрок.

        Parameters:
        data (int): A 32-bit integer

        Returns:
        list: A list of 4-character strings
        """
        # self.logger.debug(data)
        data_str: str = data.replace("0x", "")
        # self.logger.debug(data_str)
        data_list= re.findall(r"\w\w\w\w", data_str)
        # self.logger.debug(data_list)
        return data_list

    def qt_plotter(self, data, v_line: pg.Color, plot_widget: pg.PlotWidget, color : tuple = (255, 0, 0)):
        x, y = self.hex_to_list(data) # map(int, data)?
        plot_widget.clear()
        pen = pg.mkPen(color)

        # if self.data_flow_flag == 1: # раскомментировать
        #     self.writer_data(color, x, y)
        
        data_line = plot_widget.plot(x, y, pen=pen)
        data_line.setData(x, y)  # обновляем данные графика
        plot_widget.addItem(v_line)
        return y
        # self.data_line.setData(self.x, self.y)
        # print(y)

    def qt_gistogram_plotter(self, data: list,
                            bins: np.ndarray,
                            plot_widget: pg.PlotWidget,
                            color : tuple = (255, 0, 0)) -> None:
        
        self.plot_gist_EdE.clear()
        self.plot_gist_pips.clear()
        self.plot_gist_sipm.clear()

        pen = pg.mkPen(color)
        gist_data = np.histogram(data, bins=bins)
        self.plot_gist_EdE.plot(gist_data, pen=pen)

    def change_gistogramm_bins(self, data: list,
                                bins: np.ndarray,
                                plot_widget: pg.PlotWidget,
                                color : tuple = (255, 0, 0)):
        """
        Изменение количества бинов соответствующей гистограммы.
        Должна быть в классе отдельного окна.
        """


    
    def writer_data(self, color: tuple, x, y):
        current_datetime = datetime.datetime.now()
        match color:
            case self.color_pips:
                time = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:23]
                with open(self.folder_path + "/" + time + " -- pips.csv", "wb") as file:
                    frame = pd.DataFrame(zip(x, y))
                    frame.to_csv(file, index = False, sep=" ")
                file.close()
            case self.color_sipm:
                time = current_datetime.strftime("%Y-%m-%d_%H-%M-%S-%f")[:23]
                with open(self.folder_path + "/" + time + " -- sipm.csv", "wb") as file:
                    frame = pd.DataFrame(zip(x, y))
                    frame.to_csv(file, index = False, sep=" ")
                file.close()
            
    def qt_plotter_trapezoid(self, 
                            xtr_pips,
                            ytr_pips,
                            xtr_sipm,
                            ytr_sipm,
                            color_tr_pips : tuple = (255, 120, 10), 
                            color_tr_sipm : tuple = (134, 255, 82)):
        xpips, ypips = self.hex_to_list(self.data_pips)
        xsipm, ysipm = self.hex_to_list(self.data_sipm)
        self.plot_pips.clear()
        self.plot_sipm.clear()

        pen = pg.mkPen(color_tr_pips)
        data_line = self.plot_pips.plot(xtr_pips, ytr_pips, pen=pen)
        data_line.setData(xtr_pips, ytr_pips)

        pen = pg.mkPen(color_tr_sipm)
        data_line = self.plot_sipm.plot(xtr_sipm, ytr_sipm, pen=pen)
        data_line.setData(xtr_sipm, ytr_sipm)

        pen_pips = pg.mkPen(self.color_pips)
        data_line = self.plot_pips.plot(xpips, ypips, pen=pen_pips)
        data_line.setData(xpips, ypips)
        self.plot_pips.addItem(self.v_line_pips)

        pen_sipm = pg.mkPen(self.color_sipm)
        data_line = self.plot_sipm.plot(xsipm, ysipm, pen=pen_sipm)
        data_line.setData(xsipm, ysipm)
        self.plot_sipm.addItem(self.v_line_sipm)

    # def hex_to_list(self, data: list) -> tuple[list, list]:
    #     x = []  # список для порядковых номеров
    #     y = []  # список для значений
    #     hex = []
    #     # print(data)
    #     for index, value in enumerate(data):
    #         hex_value = value # value.replace('e', '0', 1)  # удаляем старший бит E
    #         hex.append(hex_value)
    #         try:
    #             decimal_value = int(hex_value, 16)  # преобразуем значение из
    #                                                     # шестнадцатеричного в десятичный формат
    #                                                     # и отнимаем смещение E0 00
    #             if decimal_value > 4096:
    #                 if decimal_value < 8191:
    #                     decimal_value -= 8191
    #                 else:
    #                     decimal_value = 0
    #             x.append(index)
    #             y.append(decimal_value)
    #         except ValueError:
    #             self.logger.debug(f"Ошибка преобразования значения: {value}")
    #             continue
    #     # self.logger.debug(hex)
    #     self.x = x
    #     self.y = y
    #     return x, y
        
    def hex_to_list(self, data: list) -> tuple[list, list]:
        x = []  # список для порядковых номеров
        y = []  # список для значений
        hex = []
        for index, value in enumerate(data):
            hex_value = value # value.replace('e', '0', 1)  # удаляем старший бит E
            hex.append(hex_value)
            try:
                decimal_value = int(hex_value[1:], 16)  # преобразуем значение из
                                                        # шестнадцатеричного в десятичный формат
                                                        # и отнимаем смещение E0 00
                if decimal_value > 4000:
                    decimal_value = 0
                x.append(index)
                y.append(decimal_value)
            except ValueError:
                self.logger.debug(f"Ошибка преобразования значения: {value}")
                continue
        # self.logger.debug(hex)
        self.x = x
        self.y = y
        return x, y

    def qt_bargraph_plotter(self):
        pass

    def queue_qt_plot(self):
        """
            Очередь для отрисовки данных МПП
        """
        while not self.queue.empty():
            data, v_line, plot, color = self.queue.get()
            self.qt_plotter(data, v_line, plot, color)
    ##########################################