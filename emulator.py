"""
Дабовляет вкладку эмулятор в gui
Является плагтном для основного движка
Функционал:
0. Включить режим эмуляции ддии
1. Получить осциллограмму mpp
2. Задать канал АЦП (1 или 2)
3. Задать колличество байт для считывания
"""
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import QSplitter, QWidget, QSizePolicy, QLineEdit
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
import pyqtgraph as pg
import serial.tools.list_ports
import sys  # We need sys so that we can pass argv to QApplication
import os
import sys
# from random import randint
# from ui.MainWindow_ui import Ui_MainWindow
from qtpy.uic import loadUi
import serial
from pyqtgraph import plot
# from qtmodern.styles import dark, light
# from qtmodern.windows import ModernWindow
# import serial.tools.list_ports
from style.styleSheet import styleSheet as style
import crcmod
import math as m
import re
import emulator
from serial.serialutil import SerialException
from src.py_toggle import pyToggle
from src.log_config import log_init, log_s
from src.customComboBox_COMport import CustomComboBox_COMport
import copy as cp
import time
import threading
from main_trapezoid_dialog import MainTrapezoidDialog
from queue import Queue
import re
import random
import pandas as pd
from tabulate import tabulate
from decimal import Decimal
from datetime import datetime
# import log_config


############## var ##################
# logger = log_config.log_init()

class Emulator(QtWidgets.QMainWindow, QThread):
    # Иницилизация всех используемых виджетов происходит в engine.py
    # lineEdit_emulation_proton: QtWidgets.QLineEdit
    # lineEdit_emulation_electron: QtWidgets.QLineEdit
    # pushButton_open_electron_dataframe: QtWidgets.QPushButton
    # pushButton_open_proton_dataframe: QtWidgets.QPushButton
    # pushButton_start_emulation: QtWidgets.QPushButton
    # lineEdit_amout_particle: QtWidgets.QLineEdit
    # lineEdit_MeV_to_mV: QtWidgets.QLineEdit
    # widget_led_start_emulation: QtWidgets.QWidget


    def __init__(self,  parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.path_electron_data = ""
        self.path_proton_data = ""
        self.dataframe_proton: pd.DataFrame
        self.dataframe_electron: pd.DataFrame

        self.ELECTRON = 1
        self.PROTON = 2

        self.MEV = 1
        self.LSB = 2
        self.MV = 3
        self.KEV = 4

        self.parent = parent
        self.config = self.parent.config

        self.amount_electrons_in_file = 0
        self.amount_protons_in_file = 0
        self.flag_pushButton_em_ok_clicked = 1
        self.dataframe_particles: pd.DataFrame
        self.k_mv_lsb = float(self.parent.lineEdit_mV_to_lsb.text())
        self.k_pips = float(self.parent.lineEdit_mV_to_lsb.text()) # mV/MeV
        self.k_sipm = float(self.parent.lineEdit_mV_to_lsb.text()) # mV/MeV

        # Счетчик процесса обработки данных
        self.timer = QTimer()
        self.timer.timeout.connect(self.queue_state)
        self.timer.start(10)
        self.queue = Queue()

        self.initThresholdToConfigFile() # подтягивает дефолтную конфинурацию
        self.initThreshold()
        # инициализация обработчиков
        parent.pushButton_start_emulation.clicked.connect(self.pushButton_start_emulation_clicked)
        parent.pushButton_open_proton_dataframe.clicked.connect(lambda: 
                                                                self.pushButton_open_proton_dataframe_clicked(parent))
        parent.pushButton_open_electron_dataframe.clicked.connect(lambda: 
                                                                self.pushButton_open_electron_dataframe_clicked(parent))
        parent.pushButton_unit_save.clicked.connect(self.saveThresholdToConfigFile)
        parent.checkBox_ampl_pips1.stateChanged.connect(self.checkBox_ampl_pips1_conect)
        parent.radioButton_MeV.toggled.connect(lambda: self.radioButton_toggled(unit = self.MEV))
        parent.radioButton_lsb.toggled.connect(lambda: self.radioButton_toggled(unit = self.LSB))
        parent.radioButton_mV.toggled.connect(lambda: self.radioButton_toggled(unit = self.MV))
        parent.pushButton_em_ok.clicked.connect(self.pushButton_em_ok_clicked)
        parent.pushButton_reload.clicked.connect(self.pushButton_reload_clicked)
        parent.lineEdit_pips1_MeV_to_mV.textChanged.connect(self.lineEdit_pips1_MeV_to_mV_textChanged)
        parent.lineEdit_pips1_amplif.textChanged.connect(self.lineEdit_pips1_amplif_textChanged)
        parent.lineEdit_sipm_amplif.textChanged.connect(self.lineEdit_sipm_amplif_textChanged)
        parent.lineEdit_pips2_amplif.textChanged.connect(self.lineEdit_pips2_amplif_textChanged)
        parent.lineEdit_pips3_amplif.textChanged.connect(self.lineEdit_pips3_amplif_textChanged)
        parent.lineEdit_pips4_amplif.textChanged.connect(self.lineEdit_pips4_amplif_textChanged)

    ############ lineEdit Changed ##############
    def lineEdit_pips1_MeV_to_mV_textChanged(self):
        k_pips = float(self.parent.lineEdit_pips1_MeV_to_mV.text()) # mV/Me
        k_sipm = float(self.parent.lineEdit_sipm_MeV_to_mV.text()) # mV/MeV
        if self.parent.radioButton_mV.isChecked():
            self.transfer_threhold(k_pips, k_sipm, ndigits = 3)
        if self.parent.radioButton_lsb.isChecked():
            k_pips, k_sipm = self.get_unit_label_for_transfer(self.LSB)
            self.transfer_threhold(k_pips, k_sipm, ndigits = 3)
    
    def lineEdit_pips1_amplif_textChanged(self):
        if self.parent.checkBox_ampl_pips1.isChecked():
            amp_pips1 = float(self.parent.lineEdit_pips1_amplif.text())
        else:
            amp_pips1 = 1
        if self.parent.radioButton_mV.isChecked():
            k_pips, k_sipm = self.get_unit_label_for_transfer(self.MV)
            self.transfer_threhold(k_pips, k_sipm, ndigits = 3, amp = [amp_pips1, 1, 1, 1, 1])
        if self.parent.radioButton_lsb.isChecked():
            k_pips, k_sipm = self.get_unit_label_for_transfer(self.LSB)
            self.transfer_threhold(k_pips, k_sipm, ndigits = 3, amp = [amp_pips1, 1, 1, 1, 1])

    def lineEdit_sipm_amplif_textChanged(self):
        if self.parent.checkBox_ampl_pips1.isChecked():
            amp_sipm = float(self.parent.lineEdit_sipm_amplif.text())
        else:
            amp_sipm = 1
        if self.parent.radioButton_mV.isChecked():
            k_pips, k_sipm = self.get_unit_label_for_transfer(self.MV)
            self.transfer_threhold(k_pips, k_sipm, ndigits = 3, amp = [1, amp_sipm, 1, 1, 1])
        if self.parent.radioButton_lsb.isChecked():
            k_pips, k_sipm = self.get_unit_label_for_transfer(self.LSB)
            self.transfer_threhold(k_pips, k_sipm, ndigits = 3, amp = [1, amp_sipm, 1, 1, 1])
    
    def lineEdit_pips2_amplif_textChanged(self):
        if self.parent.checkBox_ampl_pips1.isChecked():
            amp_pips2 = float(self.parent.lineEdit_pips2_amplif.text())
        else:
            amp_pips2 = 1
        if self.parent.radioButton_mV.isChecked():
            k_pips, k_sipm = self.get_unit_label_for_transfer(self.MV)
            self.transfer_threhold(k_pips, k_sipm, ndigits = 3, amp = [1, 1, amp_pips2, 1, 1])
        if self.parent.radioButton_lsb.isChecked():
            k_pips, k_sipm = self.get_unit_label_for_transfer(self.LSB)
            self.transfer_threhold(k_pips, k_sipm, ndigits = 3, amp = [1, 1, amp_pips2, 1, 1])

    def lineEdit_pips3_amplif_textChanged(self):
        if self.parent.checkBox_ampl_pips1.isChecked():
            amp_pips3 = float(self.parent.lineEdit_pips3_amplif.text())
        else:
            amp_pips3 = 1
        if self.parent.radioButton_mV.isChecked():
            k_pips, k_sipm = self.get_unit_label_for_transfer(self.MV)
            self.transfer_threhold(k_pips, k_sipm, ndigits = 3, amp = [1, 1, 1, amp_pips3, 1])
        if self.parent.radioButton_lsb.isChecked():
            k_pips, k_sipm = self.get_unit_label_for_transfer(self.LSB)
            self.transfer_threhold(k_pips, k_sipm, ndigits = 3, amp = [1, 1, 1, amp_pips3, 1])
    
    def lineEdit_pips4_amplif_textChanged(self):
        if self.parent.checkBox_ampl_pips1.isChecked():
            amp_pips3 = float(self.parent.lineEdit_pips4_amplif.text())
        else:
            amp_pips3 = 1
        if self.parent.radioButton_mV.isChecked():
            k_pips, k_sipm = self.get_unit_label_for_transfer(self.MV)
            self.transfer_threhold(k_pips, k_sipm, ndigits = 3, amp = [1, 1, 1, 1, amp_pips3])
        if self.parent.radioButton_lsb.isChecked():
            k_pips, k_sipm = self.get_unit_label_for_transfer(self.LSB)
            self.transfer_threhold(k_pips, k_sipm, ndigits = 3, amp = [1, 1, 1, 1, amp_pips3])
    
    ############ handler button ##############
    def pushButton_reload_clicked(self):
        self.initThreshold()

    def pushButton_em_ok_clicked(self) -> None:
        state = self.parent.checkBox_ampl_pips1.isChecked()
        if self.flag_pushButton_em_ok_clicked:
            self.checkBox_ampl_pips1_conect(state)
            self.flag_pushButton_em_ok_clicked = 0
        if state == 0:
            self.flag_pushButton_em_ok_clicked = 1
            self.checkBox_ampl_pips1_conect(state)
        

    def radioButton_toggled(self, unit) -> None:
        if self.parent.checkBox_ampl_pips1.isChecked():
            ampl_pips1 = float(self.parent.lineEdit_pips1_amplif.text())
            ampl_sipm  = float(self.parent.lineEdit_sipm_amplif.text())
            ampl_pips2 = float(self.parent.lineEdit_pips2_amplif.text())
            ampl_pips3 = float(self.parent.lineEdit_pips3_amplif.text())
            ampl_pips4 = float(self.parent.lineEdit_pips4_amplif.text())
            amplif = [ampl_pips1, ampl_sipm, ampl_pips2, ampl_pips3, ampl_pips4]
        else:
            amplif = [1, 1, 1, 1, 1]
        k_pips, k_sipm  = self.get_unit_label_for_transfer(unit)
        match unit:
            case self.MEV:
                self.change_unit_line_edit("МэВ")
                self.transfer_threhold(k_pips, k_sipm, 8)
            case self.LSB:
                self.change_unit_line_edit("lsb")
                self.transfer_threhold(k_pips, k_sipm, 8, amplif)
            case self.MV:
                self.change_unit_line_edit("мВ")
                self.transfer_threhold(k_pips, k_sipm, 8, amplif)


    def pushButton_start_emulation_clicked(self):
        """
        Обработчик кнопки запуска эмуляции
        """
        self.start_emulation(write_gist = 0)
    
    def pushButton_open_proton_dataframe_clicked(self, parent):
        """
        Обработчик кнопки открытия файла с данными энерговыделения протонов в детекторах
        """
        self.path_proton_data = self.browse_file()
        path_proton_data_name_file = self.path_proton_data.split("/")[-1]
        parent.lineEdit_emulation_proton.setText(path_proton_data_name_file)
        try:
            with open(self.path_proton_data, 'r') as f:
                self.amount_protons_in_file = len(re.findall(r'\d+\n+', f.read()))
            f.close()
            parent.logger.debug("Колличество протонов для эмуляции: " + str(self.amount_protons_in_file))
            self.parent.pushButton_start_emulation.setEnabled(True)
        except FileNotFoundError:
            parent.logger.error("Файл не найден")
            
    
    def pushButton_open_electron_dataframe_clicked(self, parent):
        """
        Обработчик кнопки открытия файла с данными энерговыделения электронов в детекторах
        """
        self.path_electron_data = self.browse_file()
        path_electron_data_name_file = self.path_electron_data.split("/")[-1]
        parent.lineEdit_emulation_electron.setText(path_electron_data_name_file)
        try:
            with open(self.path_electron_data, 'r') as f:
                self.amount_electrons_in_file = len(re.findall(r'\d+\n+', f.read()))
            f.close()
            parent.logger.debug("Колличество электронов для эмуляции: " + str(self.amount_electrons_in_file))
            self.parent.pushButton_start_emulation.setEnabled(True)
        except FileNotFoundError:
            parent.logger.error("Файл не найден")


    ############ toggle #######################
    # def ChangeSliderToToggle(hSlider: QtWidgets.QSlider, hLayout_em: QtWidgets.QHBoxLayout):
    #     """
    #     Заменяет в GUI слайдер на Toggle
    #     """
    #     emToggle = pyToggle()
    #     hSlider.deleteLater()
    #     hLayout_em.addWidget(emToggle)

    ############ emulation function ############
    def start_emulation(self, write_gist):
        """
        Открывает файл с потоками протонов, берет рандомное значение поглощения в детекторах
        pips и sipm и суммирует, затем все эти значения добавляются на график гистограммы.
        
        Затем вызывается функция обработки событий (алгоритм мпп).

        Все значения записываются в dataframe:
        Тип частицы | Энергия частицы | Поглощение sipm | Поглощение pips | .....
        ....| Сумма поглощений | Результат алгоритма (тип частицы + энергия)) | Статус

        После окончания счета выводит в консольль результат эмуляции в виде таблицы:
        ******* ELECTRONS *********
            Тип     | N частиц реальное | N частиц алгоритм | N частиц None | N частиц Error
        E < 0.1 МэВ |...................|.........
        ......
        ----------
        ******* PROTONS *********
            Тип     | N частиц реальное | N частиц алгоритм | N частиц None | N частиц Error
        E < 1 МэВ   |...................|.........
        ......
        ----------
        TODO: Сделать вывод числа ошибок и dataframe с ошибками
        TODO: Вывод в лог каким алгоритмом считалось
        Returns:
        """
        dict_electron_tmp = self.get_value_particle(self.ELECTRON)
        dict_proton_tmp = self.get_value_particle(self.PROTON)
        self.parent.logger.debug("Электроны: " + str(dict_electron_tmp))
        self.parent.logger.debug("Протоны: " + str(dict_proton_tmp))
        self.dataframe_particles_init() # инициализируем dataframe_particles, dataframe_proton, dataframe_electron
        # далее функции заполняют строки dataframe_particles, dataframe_proton, dataframe_electron
        # Создаем отдельный поток для подсчета частиц
        thread_emulation = threading.Thread(target=self.thread_emulation_mpp, daemon = True)
        thread_emulation.start()
        if write_gist == 1:
            # TODO: отрисовываем гистограммы
            pass
    
    def thread_emulation_mpp(self) -> None:
        try:
            n_particle = int(self.parent.lineEdit_amout_particle.text())
            self.parent.lineEdit_amout_particle.setText(str(n_particle))
        except ValueError:
            self.parent.lineEdit_amout_particle.setText("")
            self.parent.logger.error("n_particle не число")
        self.parent.logger.debug("Расчет начался")
        for i in range(int(n_particle)):
            self.queue.put(i)
            if len(self.path_electron_data) and len(self.path_proton_data): 
                if i % 2 == 0:
                    dict_electron_real: dict = self.get_value_particle(self.ELECTRON)
                    mpp_type_particle: dict = self.mpp_define_type_particle(dict_electron_real)
                    self.put_data_to_dataframes(dict_electron_real, mpp_type_particle)
                else:
                    dict_proton_real: dict = self.get_value_particle(self.PROTON)
                    mpp_type_particle: dict = self.mpp_define_type_particle(dict_proton_real)
                    self.put_data_to_dataframes(dict_proton_real, mpp_type_particle)
            else:
                if len(self.path_electron_data):
                    dict_electron_real: dict = self.get_value_particle(self.ELECTRON)
                    mpp_type_particle: dict = self.mpp_define_type_particle(dict_electron_real)
                    self.put_data_to_dataframes(dict_electron_real, mpp_type_particle)
                if len(self.path_proton_data):
                    dict_proton_real: dict = self.get_value_particle(self.PROTON)
                    mpp_type_particle: dict = self.mpp_define_type_particle(dict_proton_real)
                    self.put_data_to_dataframes(dict_proton_real, mpp_type_particle)
        
        self.parent.logger.log("EMULATOR", "\n" + tabulate(self.dataframe_particles.to_dict('series'), headers='keys', tablefmt="grid"))
        self.statistics_data()
        self.parent.logger.log("EMULATOR", "\n" + tabulate(self.dataframe_particles_error.to_dict('series'), headers='keys', tablefmt="grid"))
        self.parent.logger.log("EMULATOR", "\n" + tabulate(self.dataframe_electron.to_dict('series'), headers='keys', tablefmt="grid"))
        self.parent.logger.log("EMULATOR", "\n" + tabulate(self.dataframe_proton.to_dict('series'), headers='keys', tablefmt="grid"))
        self.save_df_infile(self.dataframe_particles, "results")
        self.save_df_infile(self.dataframe_particles_error, "error")

        N_nan_e = float(self.dataframe_electron["N None"].values[-1])
        N_er_e =  float(self.dataframe_electron["N Error"].values[-1])
        N_al_e =  float(self.dataframe_electron["N алгоритм"].values[-1])
        N_rl_e =  float(self.dataframe_electron["N реальное"].values[-1])

        N_nan_p = float(self.dataframe_proton["N None"].values[-1])
        N_er_p =  float(self.dataframe_proton["N Error"].values[-1])
        N_al_p =  float(self.dataframe_proton["N алгоритм"].values[-1])
        N_rl_p =  float(self.dataframe_proton["N реальное"].values[-1])
        if (N_rl_e - N_nan_e) != 0:
            acc_e = (N_al_e - N_er_e) /(N_rl_e - N_nan_e)
            if acc_e < 0:
                acc_e = 0
            # acc = (acc_e**2 + acc_p**2)**(1/2)
        else:
            acc_e = None

        if (N_rl_p - N_nan_p) != 0:
            acc_p = (N_al_p - N_er_p) /(N_rl_p - N_nan_p)
            if acc_p < 0:
                acc_p = 0
        else:
            acc_p = None
            # acc = None
        self.parent.logger.debug("Точность по электронам: " + str(acc_e))
        self.parent.logger.debug("Точность по протонам: " + str(acc_p))
        # self.parent.logger.debug("Точность ср.кв.: " + str(acc))

    def save_df_infile(self, df, name : str):
        time_now = datetime.now()
        form_time = str(time_now.strftime("%Y-%m-%d %H_%M_%S"))
        file_path = ".\\tests\\results\\" + form_time + "_" + name + ".xlsx"
        file_path_csv = ".\\tests\\res_csv\\" + form_time + "_" + name + ".csv"
        df.to_excel(file_path, index=False)
        df.to_csv(file_path_csv, index=False)



    def put_data_to_dataframes(self, real_particle: dict, mpp_type_particle: dict):
        """
        Заполняем все dataframe
        Args:
            real_particle (dict): Частица из csv 
            mpp_type_particle (list): Тип частицы по определенное мпп
        """
        E_th: float = float(self.parent.lineEdit_th_pips1_0_1.text())
        # self.parent.logger.debug(real_particle)
        if not real_particle:
            self.parent.logger.debug("Error real_particle is empty")
            return 0
        if not mpp_type_particle:
            self.parent.logger.debug("Error mpp_type_particle is empty")
            return 0
        try:
            dict_row = {"Type": real_particle["Type"],
                        "E_prim": real_particle["E_prim"],
                        "E_pips": real_particle["E_pips"],
                        "E_sipm": real_particle["E_sipm"],
                        "Sum E(pips + sipm)": real_particle["E_pips"] + real_particle["E_sipm"],
                        "E_pips2": real_particle["E_pips2"],
                        "E_pips3": real_particle["E_pips3"],
                        "E_pips4": real_particle["E_pips4"],
                        "N_ch": real_particle["E_ch"],
                        "Type_mpp_algorithm": mpp_type_particle["Type"],
                        "E_mpp_algorithm, E > x": mpp_type_particle["E"],
                        "Status": self.get_status_emulator(real_particle, mpp_type_particle)}
        except:
            self.parent.logger.debug("KeyError")
        row_dataframe_particles = [v for k, v in dict_row.items()]
        self.dataframe_particles.loc[len(self.dataframe_particles)] = row_dataframe_particles
        

    def statistics_data(self):
        E_e = [0.1, 0.5, 0.8, 1.6, 3, 5]
        N_e_real = []
        N_e_mpp = []
        N_e_none = []
        N_e_error = []
        for i, E in enumerate(E_e):
            filtered_df = self.dataframe_particles[(self.dataframe_particles['E_mpp_algorithm, E > x'] == E) & \
                                                (self.dataframe_particles["Type_mpp_algorithm"] == "electron") & \
                                                (self.dataframe_particles["Type"] != "proton")]
            N_e_mpp.append(len(filtered_df))
            if i < len(E_e)-1:
                filtered_df = self.dataframe_particles[(E <= self.dataframe_particles["E_prim"]) & \
                                                        (self.dataframe_particles["E_prim"] <= E_e[i+1]) & \
                                                    (self.dataframe_particles['Type'] == "electron")]
                N_e_real.append(len(filtered_df))
            else:
                filtered_df = self.dataframe_particles[(self.dataframe_particles['E_prim'] >= E) & \
                                                    (self.dataframe_particles['Type'] == "electron")]
                N_e_real.append(len(filtered_df))
                
            if i < len(E_e)-1:
                filtered_df = self.dataframe_particles[(self.dataframe_particles['Status'] == "None") & \
                                                        (E <= self.dataframe_particles["E_prim"]) & \
                                                        (self.dataframe_particles["E_prim"] <= E_e[i+1]) & \
                                                        (self.dataframe_particles['Type'] == "electron")]
                N_e_none.append(len(filtered_df))
            else:
                filtered_df = self.dataframe_particles[(self.dataframe_particles['Status'] == "None") & \
                                                        (self.dataframe_particles['E_prim'] >= E) & \
                                                        (self.dataframe_particles['Type'] == "electron")]
                N_e_none.append(len(filtered_df))
                
            if i < len(E_e)-1:
                filtered_df = self.dataframe_particles[(E <= self.dataframe_particles["Sum E(pips + sipm)"]) & \
                                                        (self.dataframe_particles["Sum E(pips + sipm)"] <= E_e[i+1]) & \
                                                        (self.dataframe_particles['Status'] == "ERROR") & \
                                                        (self.dataframe_particles['Type'] == "electron")]
                N_e_error.append(len(filtered_df))
            else:
                filtered_df = self.dataframe_particles[(self.dataframe_particles['Sum E(pips + sipm)'] >= E) & \
                                                        (self.dataframe_particles['Status'] == "ERROR") & \
                                                        (self.dataframe_particles['Type'] == "electron")]
                N_e_error.append(len(filtered_df))

        filtered_df = self.dataframe_particles[(self.dataframe_particles['E_mpp_algorithm, E > x'] == -1) & \
                                                (self.dataframe_particles['Status'] == "ERROR") & \
                                                (self.dataframe_particles['Type'] == "electron")]
        N_e_error.append(len(filtered_df))
        N_e_mpp.append(0)
        N_e_real.append(0)
        N_e_none.append(0)

        N_e_real.append (sum(N_e_real))
        N_e_mpp.append  (sum(N_e_mpp))
        N_e_none.append (sum(N_e_none))
        N_e_error.append(sum(N_e_error))
        print(N_e_real)
        print(N_e_mpp)
        print(N_e_none)
        print(N_e_error)
        try:
            self.dataframe_electron["N реальное"] = N_e_real
            self.dataframe_electron["N алгоритм"] = N_e_mpp
            self.dataframe_electron["N None"] = N_e_none
            self.dataframe_electron["N Error"] = N_e_error
        except ValueError:
            self.parent.logger.debug("Нет электронов")

        
        E_p = [10, 30, 60, 100, 200, 500]
        N_p_real = []
        N_p_mpp = []
        N_p_none = []
        N_p_error = []
        for i, E in enumerate(E_p):
            filtered_df = self.dataframe_particles[(self.dataframe_particles['E_mpp_algorithm, E > x'] == E) & \
                                                        (self.dataframe_particles['Type_mpp_algorithm'] == "proton")]
            N_p_mpp.append(len(filtered_df))
            
            if i < len(E_p)-1:
                filtered_df = self.dataframe_particles[(E <= self.dataframe_particles['E_prim']) & \
                                                        (self.dataframe_particles['E_prim'] <=  E_p[i+1]) & \
                                                        (self.dataframe_particles['Type'] == "proton")]
                N_p_real.append(len(filtered_df))
            else:
                filtered_df = self.dataframe_particles[(self.dataframe_particles['E_prim'] >= E) & \
                                                        (self.dataframe_particles['Type'] == "proton")]
                N_p_real.append(len(filtered_df))
                
            if i < len(E_p)-1:
                filtered_df = self.dataframe_particles[(self.dataframe_particles['Status'] == "None") & \
                                                        (E <= self.dataframe_particles['E_prim']) & \
                                                        (self.dataframe_particles['E_prim'] <=  E_p[i+1]) & \
                                                        (self.dataframe_particles['Type'] == "proton")]
                N_p_none.append(len(filtered_df))
            else:
                filtered_df = self.dataframe_particles[(self.dataframe_particles['Status'] == "None") & \
                                                        (self.dataframe_particles['E_prim'] >= E) & \
                                                        (self.dataframe_particles['Type'] == "proton")]
                N_p_none.append(len(filtered_df))
                
            if i < len(E_p)-1:
                filtered_df = self.dataframe_particles[(E <= self.dataframe_particles['E_prim']) & \
                                                        (self.dataframe_particles['E_prim'] < E_p[i+1]) & \
                                                        (self.dataframe_particles['Status'] == "ERROR") & \
                                                        (self.dataframe_particles['Type'] == "proton")]
                N_p_error.append(len(filtered_df))
            else:
                filtered_df = self.dataframe_particles[(self.dataframe_particles['E_prim'] >= E) & \
                                                        (self.dataframe_particles['Status'] == "ERROR") & \
                                                        (self.dataframe_particles['Type'] == "proton")]
                N_p_error.append(len(filtered_df))
        
        filtered_df = self.dataframe_particles[(self.dataframe_particles['E_mpp_algorithm, E > x'] == -1) & \
                                                    (self.dataframe_particles['Status'] == "ERROR") & \
                                                    (self.dataframe_particles['Type'] == "proton")]
        N_p_error.append(len(filtered_df))
        N_p_mpp.append(0)
        N_p_none.append(0)
        N_p_real.append(0)


        N_p_real.append (sum(N_p_real))
        N_p_mpp.append  (sum(N_p_mpp))
        N_p_none.append (sum(N_p_none))
        N_p_error.append(sum(N_p_error))
        try:
            self.dataframe_proton["N реальное"] = N_p_real
            self.dataframe_proton["N алгоритм"] = N_p_mpp
            self.dataframe_proton["N None"] = N_p_none
            self.dataframe_proton["N Error"] = N_p_error
        except ValueError:
            self.parent.logger.debug("Нет протонов")

        self.dataframe_particles_error = self.dataframe_particles[self.dataframe_particles['Status'] == "ERROR"]





    def get_status_emulator(self, real_particle: dict, mpp_type_particle: dict) -> str:
        E_th: float = 0.1
        E_0_5 = float(self.parent.lineEdit_th_e_0_5.text())
        E_0_8 = float(self.parent.lineEdit_th_e_0_8.text())
        E_1_6 = float(self.parent.lineEdit_th_e_1_6.text())
        E_3 = float(self.parent.lineEdit_th_e_3.text())
        E_5 = float(self.parent.lineEdit_th_e_5.text())

        E_10 = float(self.parent.lineEdit_th_p_30.text())
        E_30 = float(self.parent.lineEdit_th_p_60.text())
        E_60 = float(self.parent.lineEdit_th_p_100.text())
        E_100 = float(self.parent.lineEdit_th_p_200.text())
        E_200 = float(self.parent.lineEdit_th_p_500.text())
        E_500 = 501
        if mpp_type_particle["Type"] == "None":
            return "None"
        if real_particle["Type"] == mpp_type_particle["Type"]:
            if mpp_type_particle["Type"] == "electron":
                if E_5 <=  mpp_type_particle["E"] <= real_particle["E_prim"]:
                    return "OK"
                if real_particle["E_prim"] < E_5:
                    if E_3 <=  real_particle["E_prim"] < E_5:
                        if mpp_type_particle["E"] == E_3:
                            return "OK"
                        else:
                            return "ERROR"
                    elif E_1_6 <=  real_particle["E_prim"] < E_3:
                        if mpp_type_particle["E"] == E_1_6:
                            return "OK"
                        else:
                            return "ERROR"
                    elif E_0_8 <=  real_particle["E_prim"] < E_1_6:
                        if mpp_type_particle["E"] == E_0_8:
                            return "OK"
                        else:
                            return "ERROR"
                    elif E_0_5 <=  real_particle["E_prim"] < E_0_8:
                        if mpp_type_particle["E"] == E_0_5:
                            return "OK"
                        else:
                            return "ERROR"
                    elif E_th <=  real_particle["E_prim"] < E_0_5:
                        if mpp_type_particle["E"] == E_th:
                            return "OK"
                        else:
                            return "ERROR"
                    else:
                        return "ERROR"
                else:
                        return "ERROR"
            # elif mpp_type_particle["E"] <= real_particle["E_prim"]:
            #     return "OK"
            if mpp_type_particle["Type"] == "proton":
                if E_500 <= real_particle["E_prim"]:
                    if mpp_type_particle["E"] == E_500:
                        return "OK"
                    else: 
                        return "ERROR"
                if E_200 <=  mpp_type_particle["E"] < E_500:
                    if mpp_type_particle["E"] == E_200:
                        return "OK"
                    else: 
                        return "ERROR"
                if E_100 <=  mpp_type_particle["E"] < E_200:
                    if mpp_type_particle["E"] == E_100:
                        return "OK"
                    else: 
                        return "ERROR"
                if E_60 <=  mpp_type_particle["E"] < E_100:
                    if mpp_type_particle["E"] == E_60:
                        return "OK"
                    else: 
                        return "ERROR"
                if E_30 <=  mpp_type_particle["E"] < E_60:
                    if mpp_type_particle["E"] == E_30:
                        return "OK"
                    else: 
                        return "ERROR"
                if E_10 <=  mpp_type_particle["E"] < E_30:
                    if mpp_type_particle["E"] == E_10:
                        return "OK"
                    else: 
                        return "ERROR"
                else:
                    return "ERROR"
            else:
                return "ERROR"
        else:
            return "ERROR"


    def mpp_define_type_particle(self, particle: dict) -> dict:
        """
        Алгоритм определения типа частицы. Алгоритм предоставил Поросев Вячеслав: 
        v.porosev@nsu.ru
        Если алгоритм не сработал возвращает {"Type": None, "E": None}
        Args:
            particle (dict): поглощение частиц

        Returns:
            out_mpp (sict): {"Type": None, "E": None}
        """
        out_mpp = {}
        E_th: float = float(self.parent.lineEdit_th_pips1_0_1.text())
        if not particle:
            self.parent.logger.debug("Error particle is empty")
            return {}
        try:
            if particle["E_pips"] < E_th:
                return {"Type": "None", "E": 0}
            if particle["E_pips"] < float(self.parent.lineEdit_electron_dE.text()) and \
                particle["E_sipm"] < float(self.parent.lineEdit_electron_E.text()):
                out_mpp["Type"] = "electron"
                if particle["E_pips"] + particle["E_sipm"] >= E_th:
                    out_mpp["E"] = 0.1
                if particle["E_pips"] + particle["E_sipm"] >= float(self.parent.lineEdit_th_e_0_5.text()):
                    out_mpp["E"] = 0.5
                if particle["E_pips"] + particle["E_sipm"] >= float(self.parent.lineEdit_th_e_0_8.text()):
                    out_mpp["E"] = 0.8
                if particle["E_pips"] + particle["E_sipm"] >= float(self.parent.lineEdit_th_e_1_6.text()):
                    out_mpp["E"] = 1.6
                if particle["E_pips"] + particle["E_sipm"] >= float(self.parent.lineEdit_th_e_3.text()):
                    out_mpp["E"] = 3
                if particle["E_pips"] + particle["E_sipm"] >= float(self.parent.lineEdit_th_e_5.text()):
                    out_mpp["E"] = 5
            if  float(self.parent.lineEdit_proton_dE_x_10_30.text()) < \
                particle["E_pips"] < float(self.parent.lineEdit_proton_dE_y_10_30.text()) and \
                float(self.parent.lineEdit_proton_E_x_10_30.text()) < \
                particle["E_sipm"] < float(self.parent.lineEdit_proton_E_y_10_30.text()) and \
                particle["E_pips2"] >= float(self.parent.lineEdit_comparator.text()) and \
                particle["E_pips3"] >= float(self.parent.lineEdit_comparator.text()) and \
                particle["E_pips4"] >= float(self.parent.lineEdit_comparator.text()):
                out_mpp["Type"] = "proton"
                out_mpp["E"] = 30
            if float(self.parent.lineEdit_proton_dE_x_30_60.text()) < \
                particle["E_pips"] < float(self.parent.lineEdit_proton_dE_y_30_60.text()) and \
                float(self.parent.lineEdit_proton_E_x_30_60.text()) < \
                particle["E_sipm"] < float(self.parent.lineEdit_proton_E_y_30_60.text()) and \
                particle["E_pips2"] >= float(self.parent.lineEdit_comparator.text()) and \
                particle["E_pips3"] >= float(self.parent.lineEdit_comparator.text()) and \
                particle["E_pips4"] >= float(self.parent.lineEdit_comparator.text()):
                out_mpp["Type"] = "proton"
                out_mpp["E"] = 60
            if particle["E_sipm"] > float(self.parent.lineEdit_proton_E_x_60.text()) and \
                particle["E_pips2"] >= float(self.parent.lineEdit_comparator.text()) and \
                particle["E_pips3"] < float(self.parent.lineEdit_comparator.text()) and \
                particle["E_pips4"] < float(self.parent.lineEdit_comparator.text()):
                out_mpp["Type"] = "proton"
                out_mpp["E"] = 100
            if particle["E_sipm"] > float(self.parent.lineEdit_proton_E_x_60.text()) and \
                particle["E_pips2"] >= float(self.parent.lineEdit_comparator.text()) and \
                particle["E_pips3"] >= float(self.parent.lineEdit_comparator.text()) and \
                particle["E_pips4"] < float(self.parent.lineEdit_comparator.text()):
                out_mpp["Type"] = "proton"
                out_mpp["E"] = 200
            if particle["E_sipm"] > float(self.parent.lineEdit_proton_E_x_60.text()) and \
                particle["E_pips2"] >= float(self.parent.lineEdit_comparator.text()) and \
                particle["E_pips3"] >= float(self.parent.lineEdit_comparator.text()) and \
                particle["E_pips4"] >= float(self.parent.lineEdit_comparator.text()):
                out_mpp["Type"] = "proton"
                out_mpp["E"] = 500
            if particle["E_sipm"] > float(self.parent.lineEdit_proton_E_x_60.text()) and \
                particle["E_pips2"] >= float(self.parent.lineEdit_comparator.text()) and \
                particle["E_pips3"] >= float(self.parent.lineEdit_comparator.text()) and \
                particle["E_pips4"] >= float(self.parent.lineEdit_comparator.text()) and \
                particle["E_ch"] > 1:
                out_mpp["Type"] = "proton"
                out_mpp["E"] = 501
            if not out_mpp:
                if particle["Type"] == "electron":
                    return {"Type": "electron", "E": -1} # Если алгоритм не сработал
                if particle["Type"] == "proton":
                    return {"Type": "proton", "E": -1} # Если алгоритм не сработал
            return out_mpp
        except:
            # Если пришел пустой particle
            self.parent.logger.debug("Error")
            return {} 
        # elif E_th >= particle["E_pips"]:
        #     return {"Type": None, "E": 0.1}
        # return {"Type": None, "E": None}


    def get_value_particle(self, type_particle) -> dict:
        """
        Получает значение энергии частицы и поглощений
        
        Returns: dict{E_prim, E_pips, E_sipm, E_pips2, E_pips3, E_pips4, Cherenkov}
        """
        dict_particle = {}
        match type_particle:
            case self.ELECTRON:
                try: 
                    with open(self.path_electron_data) as f: 
                        line = f.readlines()[random.randint(0, self.amount_electrons_in_file)]
                        # self.parent.logger.debug(random.randint(0, self.amount_electrons_in_file))
                        list_value_electrons_tmp: list[float] = list(map(float, re.findall(r'(?:\d+\.\d+|\d+)',line)))
                        # self.parent.logger.debug("Электроны: " + str(re.findall(r'(?:\d+\.\d+|\d+)', line)))
                        if not list_value_electrons_tmp:
                            self.parent.logger.debug("Error list_value_electrons_tmp is empty")
                            return {}
                        dict_particle['Type'] = "electron"
                        dict_particle['E_prim'] = list_value_electrons_tmp[0] # E_prev
                        dict_particle['E_pips'] = list_value_electrons_tmp[3] # E_pips
                        dict_particle['E_sipm'] = list_value_electrons_tmp[4] # E_sipm
                        dict_particle['E_pips2'] = list_value_electrons_tmp[6] # E_pips2
                        dict_particle['E_pips3'] = list_value_electrons_tmp[7] # E_pips3
                        dict_particle['E_pips4'] = list_value_electrons_tmp[8] # E_pips4
                        dict_particle['E_ch'] = list_value_electrons_tmp[-1] # E_ch
                    f.close()
                    return dict_particle
                except:
                    self.parent.logger.error("Файл не найден или не тот файл")

            case self.PROTON:
                try: 
                    with open(self.path_proton_data) as f: 
                        line = f.readlines()[random.randint(0, self.amount_protons_in_file)]
                        # self.parent.logger.debug(random.randint(0, self.amount_protons_in_file))
                        list_value_protons_tmp: list[float] = list(map(float, re.findall(r'(?:\d+\.\d+|\d+)',line)))
                        # self.parent.logger.debug("Протоны: " + str(re.findall(r'(?:\d+\.\d+|\d+)', line)))
                        if not list_value_protons_tmp:
                            self.parent.logger.debug("Error list_value_protons_tmp is empty")
                            return {}
                        dict_particle['Type'] = "proton"
                        dict_particle['E_prim'] = list_value_protons_tmp[0] # E_prev
                        dict_particle['E_pips'] = list_value_protons_tmp[3] # E_pips
                        dict_particle['E_sipm'] = list_value_protons_tmp[4] # E_sipm
                        dict_particle['E_pips2'] = list_value_protons_tmp[6] # E_pips2
                        dict_particle['E_pips3'] = list_value_protons_tmp[7] # E_pips3
                        dict_particle['E_pips4'] = list_value_protons_tmp[8] # E_pips4
                        dict_particle['E_ch'] = list_value_protons_tmp[-1] # E_ch
                    f.close()
                    return dict_particle
                except:
                    self.parent.logger.error("Файл не найден или не тот файл")
        
        return {}

    def det_error_mpp_algoritm(self):
        pass

    ############ service function ##############
    def get_unit_label_for_transfer(self, unit) -> tuple:
        """
        Функция для определения коэффициента преобразования
        Сначала определяет какой unit был, потом его преобразует в нужный unit
        """
        label = self.parent.label_unit_1.text()
        try:
            k_mv_lsb = float(self.parent.lineEdit_mV_to_lsb.text())
            
        except ValueError:
            self.parent.logger.debug("k_mv_lsb: Ошибка ввода данных, не число")
        try:
            k_pips = float(self.parent.lineEdit_pips1_MeV_to_mV.text()) # mV/MeV
            
        except ValueError:
            self.parent.logger.debug("k_pips: Ошибка ввода данных, не число")
        try:
            k_sipm = float(self.parent.lineEdit_sipm_MeV_to_mV.text()) # mV/MeV
        except ValueError:
            self.parent.logger.debug("k_pips: Ошибка ввода данных, не число")
        k1 = 1
        k2 = 1
        if unit == self.LSB:
            k1 = 1 / k_mv_lsb * k_pips
            k2 = 1 / k_mv_lsb * k_sipm
        elif unit == self.MV:
            k1 = k_pips
            k2 = k_sipm
        return k1, k2

    def checkBox_ampl_pips1_conect(self, state) -> None:
        if state:
            try:
                self.ampl_pips1 = float(self.parent.lineEdit_pips1_amplif.text())
            except ValueError:
                self.parent.logger.debug("ampl_pips1: Ошибка ввода данных, не число")
            try:
                self.ampl_sipm = float(self.parent.lineEdit_sipm_amplif.text())
            except ValueError:
                self.parent.logger.debug("ampl_sipm: Ошибка ввода данных, не число")
            try:
                self.ampl_pips2 = float(self.parent.lineEdit_pips2_amplif.text())
            except ValueError:
                self.parent.logger.debug("ampl_pips2: Ошибка ввода данных, не число")
            try:
                self.ampl_pips3 = float(self.parent.lineEdit_pips3_amplif.text())
            except ValueError:
                self.parent.logger.debug("ampl_pips3: Ошибка ввода данных, не число")
            try:
                self.ampl_pips4 = float(self.parent.lineEdit_pips4_amplif.text())
            except ValueError:
                self.parent.logger.debug("ampl_pips4: Ошибка ввода данных, не число")
            
            amplif = [self.ampl_pips1, self.ampl_sipm, self.ampl_pips2, self.ampl_pips3, self.ampl_pips4]
            if self.parent.radioButton_mV.isChecked():
                k_pips, k_sipm = self.get_unit_label_for_transfer(self.MV)
            if self.parent.radioButton_lsb.isChecked():
                k_pips, k_sipm = self.get_unit_label_for_transfer(self.LSB)
            self.transfer_threhold(k_pips, k_sipm, ndigits = 8, amp = amplif)
        else:
            self.ampl_pips1 = 1
            self.ampl_sipm =  1
            self.ampl_pips2 = 1
            self.ampl_pips3 = 1
            self.ampl_pips4 = 1

            amplif = [self.ampl_pips1, self.ampl_sipm, self.ampl_pips2, self.ampl_pips3, self.ampl_pips4]
            if self.parent.radioButton_mV.isChecked():
                k_pips, k_sipm = self.get_unit_label_for_transfer(self.MV)
            if self.parent.radioButton_lsb.isChecked():
                k_pips, k_sipm = self.get_unit_label_for_transfer(self.LSB)
            self.transfer_threhold(k_pips, k_sipm, ndigits = 8, amp = amplif)

    def initThreshold(self):
        path = "./config/config.ini"
        self.config.read(path)
        self.parent.radioButton_MeV.setChecked(True)
        # self.parent.radioButton_lsb.setChecked(int(self.config.get("Emulator", "radiobutton_lsb")))
        # self.parent.radioButton_mV.setChecked(int(self.config.get("Emulator", "radiobutton_mv")))

        self.parent.lineEdit_th_pips1_0_1.setText(self.config.get("Emulator", "lineedit_th_pips1_0_1"))
        
        self.parent.lineEdit_th_e_0_5.setText(self.config.get("Emulator", "lineedit_th_e_0_5"))
        self.parent.lineEdit_th_e_0_8.setText(self.config.get("Emulator", "lineedit_th_e_0_8"))
        self.parent.lineEdit_th_e_1_6.setText(self.config.get("Emulator", "lineedit_th_e_1_6"))
        self.parent.lineEdit_th_e_3.setText(self.config.get("Emulator", "lineedit_th_e_3"))
        self.parent.lineEdit_th_e_5.setText(self.config.get("Emulator", "lineedit_th_e_5"))
        self.parent.lineEdit_th_p_10.setText(self.config.get("Emulator", "lineedit_th_p_10"))
        self.parent.lineEdit_th_p_30.setText(self.config.get("Emulator", "lineedit_th_p_30"))
        self.parent.lineEdit_th_p_60.setText(self.config.get("Emulator", "lineedit_th_p_60"))
        self.parent.lineEdit_th_p_100.setText(self.config.get("Emulator", "lineedit_th_p_100"))
        self.parent.lineEdit_th_p_200.setText(self.config.get("Emulator", "lineedit_th_p_200"))
        self.parent.lineEdit_th_p_500.setText(self.config.get("Emulator", "lineedit_th_p_500"))

        self.parent.lineEdit_pips1_amplif.setText(self.config.get("Emulator", "lineedit_pips1_amplif"))
        self.parent.lineEdit_sipm_amplif.setText(self.config.get("Emulator", "lineedit_sipm_amplif"))
        self.parent.lineEdit_pips2_amplif.setText(self.config.get("Emulator", "lineedit_pips2_amplif"))
        self.parent.lineEdit_pips3_amplif.setText(self.config.get("Emulator", "lineedit_pips3_amplif"))
        self.parent.lineEdit_pips4_amplif.setText(self.config.get("Emulator", "lineedit_pips4_amplif"))
        self.ampl_pips1 = int(self.config.get("Emulator", "lineedit_pips1_amplif"))
        self.ampl_sipm  = int(self.config.get("Emulator", "lineedit_sipm_amplif"))
        self.ampl_pips2 = int(self.config.get("Emulator", "lineedit_pips2_amplif"))
        self.ampl_pips3 = int(self.config.get("Emulator", "lineedit_pips3_amplif"))
        self.ampl_pips4 = int(self.config.get("Emulator", "lineedit_pips4_amplif"))

        self.th_e_0_1 = float(self.parent.lineEdit_th_pips1_0_1.text())
        self.th_e_0_5 = float(self.parent.lineEdit_th_e_0_5.text())
        self.th_e_0_8 = float(self.parent.lineEdit_th_e_0_8.text())
        self.th_e_1_6 = float(self.parent.lineEdit_th_e_1_6.text())
        self.th_e_3   = float(self.parent.lineEdit_th_e_3.text())
        self.th_e_5   = float(self.parent.lineEdit_th_e_5.text())
        self.th_p_10  = float(self.parent.lineEdit_th_p_10.text())
        self.th_p_30  = float(self.parent.lineEdit_th_p_30.text())
        self.th_p_60  = float(self.parent.lineEdit_th_p_60.text())
        self.th_p_100 = float(self.parent.lineEdit_th_p_100.text())
        self.th_p_200 = float(self.parent.lineEdit_th_p_200.text())
        self.th_p_500 = float(self.parent.lineEdit_th_p_500.text())

        self.parent.lineEdit_mV_to_lsb.setText(self.config.get("Emulator", "lineEdit_mv_to_lsb"))

        self.parent.checkBox_ampl_pips1.setChecked(int(self.config.get("Emulator", "checkBox_ampl_pips1")))


    def initThresholdToConfigFile(self):
        """
        Create a config file
        """
        path = "./config/config.ini"
        self.config.add_section("Emulator")
        self.config.set("Emulator", "radiobutton_mev", "1")
        self.config.set("Emulator", "radiobutton_lsb", "0")
        self.config.set("Emulator", "radiobutton_mv", "0")

        self.config.set("Emulator", "lineedit_mv_to_lsb", "0.2")

        self.config.set("Emulator", "lineedit_pips1_mev_to_mv", "30.03")
        self.config.set("Emulator", "lineedit_pips1_amplif", "1")

        self.config.set("Emulator", "lineedit_th_pips1_0_1", "0.1")
        self.config.set("Emulator", "lineedit_th_e_0_5",  "0.5")
        self.config.set("Emulator", "lineedit_th_e_0_8", "0.8")
        self.config.set("Emulator", "lineedit_th_e_1_6", "1.6")
        self.config.set("Emulator", "lineedit_th_e_3", "3")
        self.config.set("Emulator", "lineedit_th_e_5", "5")

        self.config.set("Emulator", "lineedit_sipm_mev_to_mv", "120.8")
        self.config.set("Emulator", "lineedit_sipm_amplif", "1")
        self.config.set("Emulator", "lineedit_th_p_10", "10")
        self.config.set("Emulator", "lineedit_th_p_30", "30")
        self.config.set("Emulator", "lineedit_th_p_60", "60")

        self.config.set("Emulator", "lineedit_th_p_100", "100")
        self.config.set("Emulator", "lineedit_pips2_amplif", "1")

        self.config.set("Emulator", "lineedit_th_p_200", "200")
        self.config.set("Emulator", "lineedit_pips3_amplif", "1")

        self.config.set("Emulator", "lineedit_th_p_500", "500")
        self.config.set("Emulator", "lineedit_pips4_amplif", "1")

        self.config.set("Emulator", "checkBox_ampl_pips1", "0")

        with open(path, "w") as config_file:
            self.config.write(config_file)
        config_file.close()
    
    def saveThresholdToConfigFile(self):
        """
        Save a config file
        """
        path = "./config/config.ini"
        try:
            self.config.add_section("Emulator")
        except:
            pass
        # self.config.set("Emulator", "radiobutton_mev", str(int(self.parent.radioButton_MeV.isChecked())))
        # self.config.set("Emulator", "radiobutton_lsb", str(int(self.parent.radioButton_lsb.isChecked())))
        # self.config.set("Emulator", "radiobutton_mv", str(int(self.parent.radioButton_mV.isChecked())))
        
        self.config.set("Emulator", "lineedit_mv_to_lsb", self.parent.lineEdit_mV_to_lsb.text())

        self.config.set("Emulator", "lineedit_pips1_mev_to_mv", self.parent.lineEdit_pips1_MeV_to_mV.text())
        self.config.set("Emulator", "lineedit_pips1_amplif", self.parent.lineEdit_pips1_amplif.text())

        self.config.set("Emulator", "lineedit_th_pips1_0_1", self.th_e_0_1)
        self.config.set("Emulator", "lineedit_th_e_0_5", self.th_e_0_5)
        self.config.set("Emulator", "lineedit_th_e_0_8", self.th_e_0_8)
        self.config.set("Emulator", "lineedit_th_e_1_6", self.th_e_1_6)
        self.config.set("Emulator", "lineedit_th_e_3", self.th_e_3)
        self.config.set("Emulator", "lineedit_th_e_5", self.th_e_5)

        self.config.set("Emulator", "lineedit_sipm_mev_to_mv", self.parent.lineEdit_sipm_MeV_to_mV.text())
        self.config.set("Emulator", "lineedit_sipm_amplif", self.parent.lineEdit_sipm_amplif.text())

        self.config.set("Emulator", "lineedit_th_p_10", self.th_p_10)
        self.config.set("Emulator", "lineedit_th_p_30", self.th_p_30)
        self.config.set("Emulator", "lineedit_th_p_60", self.th_p_60)

        self.config.set("Emulator", "lineedit_th_p_100", self.th_p_100)
        self.config.set("Emulator", "lineedit_pips2_amplif", self.parent.lineEdit_pips2_amplif.text())

        self.config.set("Emulator", "lineedit_th_p_200", self.th_p_200)
        self.config.set("Emulator", "lineedit_pips3_amplif", self.parent.lineEdit_pips3_amplif.text())

        self.config.set("Emulator", "lineedit_th_p_500", self.th_p_500)
        self.config.set("Emulator", "lineedit_pips4_amplif", self.parent.lineEdit_pips4_amplif.text())

        self.config.set("Emulator", "checkBox_ampl_pips1", str(int(self.parent.checkBox_ampl_pips1.isChecked())))

        with open(path, "w") as config_file:
            self.config.write(config_file)
        config_file.close()


    def dataframe_particles_init(self):
        columns_particle = ["Type", "E_prim", "E_pips", 
                "E_sipm", "Sum E(pips + sipm)", "E_pips2", "E_pips3", "E_pips4", "N_ch",
                "Type_mpp_algorithm", "E_mpp_algorithm, E > x", "Status"]
        self.dataframe_particles = pd.DataFrame([], columns = columns_particle)
        # self.parent.logger.debug("\n" + tabulate(self.dataframe_particles.to_dict('series'), headers='keys', tablefmt="grid"))

        columns_proton = ["Протоны", "N реальное", "N алгоритм", "N Error", "N None"]
        type_proton = ["E > 10 МэВ", "E > 30 МэВ", "E > 60 МэВ", "E > 100 МэВ", "E > 200 МэВ", "E > 500 МэВ", "E = -1", "N общее"]
        self.dataframe_proton = pd.DataFrame([], columns = columns_proton, index=None)
        self.dataframe_proton["Протоны"] = type_proton
        # self.parent.logger.debug("\n" + tabulate(self.dataframe_proton.to_dict('series'), headers='keys', tablefmt="grid"))

        columns_electron = ["Электроны", "N реальное", "N алгоритм", "N Error" ,"N None"]
        type_electron = ["E > 0.1 МэВ", "E > 0.5 МэВ", "E > 0.8 МэВ", "E > 1.6 МэВ", "E > 3 МэВ", "E > 5 МэВ", "E = -1", "N общее"]
        self.dataframe_electron = pd.DataFrame([], columns = columns_electron, index=None)
        self.dataframe_electron["Электроны"] = type_electron
        # self.parent.logger.debug("\n" + tabulate(self.dataframe_electron.to_dict('series'), headers='keys', tablefmt="grid"))
        
        # columns_particle_error = ["Type", "E_prim", "E_pips", 
        #         "E_sipm1", "E_pips2", "E_pips3", "E_pips4", "Sum E(pips + sipm)", "Type_mpp_algorithm", "Status"]
        # self.dataframe_particles_error = pd.DataFrame([], columns = columns_particle_error, index=None)
        # self.parent.logger.debug("\n" + tabulate(self.dataframe_particles_error.to_dict('series'), headers='keys', tablefmt="grid"))



    def transfer_threhold(self, k_pips, k_sipm, ndigits, amp = [1, 1, 1, 1, 1]):
        """_summary_

        Args:
            k (_type_): коэффициент преобразования величин
            ndigits (_type_): знаков после запятой
            amp (list): [self.ampl_pips1, self.ampl_sipm, self.ampl_pips2, self.ampl_pips3, self.ampl_pips4]
        """
        form = "{:." + str(ndigits) + "f}"
        # if self.parent.checkBox_ampl_pips1.isChecked():
        
        self.parent.lineEdit_th_pips1_0_1.setText(form.format(self.th_e_0_1  * k_pips * amp[0]).rstrip('0').rstrip('.'))
        self.parent.lineEdit_th_e_0_5.setText    (form.format(self.th_e_0_5  * k_pips * amp[0]).rstrip('0').rstrip('.'))
        self.parent.lineEdit_th_e_0_8.setText    (form.format(self.th_e_0_8  * k_pips * amp[0]).rstrip('0').rstrip('.'))
        self.parent.lineEdit_th_e_1_6.setText    (form.format(self.th_e_1_6  * k_pips * amp[0]).rstrip('0').rstrip('.'))
        self.parent.lineEdit_th_e_3.setText      (form.format(self.th_e_3    * k_pips * amp[0]).rstrip('0').rstrip('.'))
        self.parent.lineEdit_th_e_5.setText      (form.format(self.th_e_5    * k_pips * amp[0]).rstrip('0').rstrip('.'))
        self.parent.lineEdit_th_p_10.setText     (form.format(self.th_p_10   * k_sipm * amp[1]).rstrip('0').rstrip('.'))
        self.parent.lineEdit_th_p_30.setText     (form.format(self.th_p_30   * k_sipm * amp[1]).rstrip('0').rstrip('.'))
        self.parent.lineEdit_th_p_60.setText     (form.format(self.th_p_60   * k_sipm * amp[1]).rstrip('0').rstrip('.'))
        self.parent.lineEdit_th_p_100.setText    (form.format(self.th_p_100  * k_pips * amp[2]).rstrip('0').rstrip('.'))
        self.parent.lineEdit_th_p_200.setText    (form.format(self.th_p_200  * k_pips * amp[3]).rstrip('0').rstrip('.'))
        self.parent.lineEdit_th_p_500.setText    (form.format(self.th_p_500  * k_pips * amp[4]).rstrip('0').rstrip('.'))
        # else:
        #     self.parent.lineEdit_th_pips1_0_1.setText(form.format(float(self.parent.lineEdit_th_pips1_0_1.text()) * k).rstrip('0').rstrip('.'))
        #     self.parent.lineEdit_th_e_0_5.setText(form.format(float(self.parent.lineEdit_th_e_0_5.text()) * k).rstrip('0').rstrip('.'))
        #     self.parent.lineEdit_th_e_0_8.setText(form.format(float(self.parent.lineEdit_th_e_0_8.text()) * k).rstrip('0').rstrip('.'))
        #     self.parent.lineEdit_th_e_1_6.setText(form.format(float(self.parent.lineEdit_th_e_1_6.text()) * k).rstrip('0').rstrip('.'))
        #     self.parent.lineEdit_th_e_3.setText(form.format(float(self.parent.lineEdit_th_e_3.text()) * k).rstrip('0').rstrip('.'))
        #     self.parent.lineEdit_th_e_5.setText(form.format(float(self.parent.lineEdit_th_e_5.text()) * k).rstrip('0').rstrip('.'))

        #     self.parent.lineEdit_th_p_10.setText(form.format(float(self.parent.lineEdit_th_p_10.text()) * k).rstrip('0').rstrip('.'))
        #     self.parent.lineEdit_th_p_30.setText(form.format(float(self.parent.lineEdit_th_p_30.text()) * k).rstrip('0').rstrip('.'))
        #     self.parent.lineEdit_th_p_60.setText(form.format(float(self.parent.lineEdit_th_p_60.text()) * k).rstrip('0').rstrip('.'))

        #     self.parent.lineEdit_th_p_100.setText(form.format(float(self.parent.lineEdit_th_p_100.text()) * k).rstrip('0').rstrip('.'))

        #     self.parent.lineEdit_th_p_200.setText(form.format(float(self.parent.lineEdit_th_p_200.text()) * k).rstrip('0').rstrip('.'))

        #     self.parent.lineEdit_th_p_500.setText(form.format(float(self.parent.lineEdit_th_p_500.text()) * k).rstrip('0').rstrip('.'))

    def change_unit_line_edit(self, unit):
            self.parent.label_unit_1.setText(unit)
            self.parent.label_unit_2.setText(unit)
            self.parent.label_unit_3.setText(unit)
            self.parent.label_unit_4.setText(unit)
            self.parent.label_unit_5.setText(unit)
            self.parent.label_unit_6.setText(unit)
            self.parent.label_unit_7.setText(unit)
            self.parent.label_unit_8.setText(unit)
            self.parent.label_unit_9.setText(unit)
            self.parent.label_unit_10.setText(unit)
            self.parent.label_unit_11.setText(unit)
            self.parent.label_unit_12.setText(unit)
        
    def browse_file(self):
        """
        Открывает диалоговое окно для выбора файла
        """
        file = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File', "./tests/test_data", "CSV Files (*.csv)")
        return file[0]

    def queue_state(self):
        """
            Очередь для отрисовки данных МПП
        """
        while not self.queue.empty():
            n = self.queue.get() + 1
            self.parent.label_state_2.setText(f"State: {n}")
            