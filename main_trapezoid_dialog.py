from PyQt6 import QtWidgets
from qtpy.uic import loadUi
# from engine_trapezoid_dialog import EngineTrapezoidFilter
import os



class MainTrapezoidDialog(QtWidgets.QDialog):
    pushButton_OK: QtWidgets.QPushButton
    pushButton_cancel: QtWidgets.QPushButton
    lineEdit_t_decay_pips: QtWidgets.QLineEdit
    lineEdit_t_rise_pips: QtWidgets.QLineEdit
    lineEdit_t_top_pips: QtWidgets.QLineEdit
    checkBox_invert_pips: QtWidgets.QCheckBox
    lineEdit_t_decay_sipm: QtWidgets.QLineEdit
    lineEdit_t_rise_sipm: QtWidgets.QLineEdit
    lineEdit_t_top_sipm: QtWidgets.QLineEdit
    checkBox_invert_sipm: QtWidgets.QCheckBox
    horizontalSlider_T_decay_pips: QtWidgets.QSlider
    horizontalSlider_T_rise_pips: QtWidgets.QSlider
    horizontalSlider_T_top_pips: QtWidgets.QSlider
    horizontalSlider_T_decay_sipm: QtWidgets.QSlider
    horizontalSlider_T_rise_sipm: QtWidgets.QSlider
    horizontalSlider_T_top_sipm: QtWidgets.QSlider

    T_DECAY_PIPS = 0
    T_RISE_PIPS = 1
    T_TOP_PIPS = 2

    T_DECAY_SIPM = 3
    T_RISE_SIPM = 4
    T_TOP_SIPM = 5

    def __init__(self, root, **kwargs) -> None:
        super().__init__(root, **kwargs)
        loadUi(os.path.join(os.path.dirname(__file__),  f'style/DialogTrapezoid.ui'), self)
        self.root = root
        self.pushButton_OK.clicked.connect(self.pushButton_OK_handler)
        self.pushButton_cancel.clicked.connect(self.pushButton_pushButton_cancel_handler)
        
        self.horizontalSlider_T_decay_pips.valueChanged.connect(lambda: self.slider_value_changed(self.T_DECAY_PIPS))
        self.horizontalSlider_T_rise_pips.valueChanged.connect(lambda: self.slider_value_changed(self.T_RISE_PIPS))
        self.horizontalSlider_T_top_pips.valueChanged.connect(lambda: self.slider_value_changed(self.T_TOP_PIPS))
        
        self.horizontalSlider_T_decay_sipm.valueChanged.connect(lambda: self.slider_value_changed(self.T_DECAY_SIPM))
        self.horizontalSlider_T_rise_sipm.valueChanged.connect(lambda: self.slider_value_changed(self.T_RISE_SIPM))
        self.horizontalSlider_T_top_sipm.valueChanged.connect(lambda: self.slider_value_changed(self.T_TOP_SIPM))


    # def line_edit_text_changed(self, text):
    # try:
    #     value = int(text)
    #     if 0 <= value <= 100:
    #         self.slider.setValue(value)
    # except ValueError:
    #     pass
    
    def slider_value_changed(self, numlineEdit):

        match numlineEdit:
            case self.T_DECAY_PIPS:
                self.lineEdit_t_decay_pips.setText(str(self.horizontalSlider_T_decay_pips.value()))
            case self.T_RISE_PIPS:
                self.lineEdit_t_rise_pips.setText(str(self.horizontalSlider_T_rise_pips.value()))
            case self.T_TOP_PIPS:
                self.lineEdit_t_top_pips.setText(str(self.horizontalSlider_T_top_pips.value()))

            case self.T_DECAY_SIPM:
                self.lineEdit_t_decay_sipm.setText(str(self.horizontalSlider_T_decay_sipm.value()))
            case self.T_RISE_SIPM:
                self.lineEdit_t_rise_sipm.setText(str(self.horizontalSlider_T_rise_sipm.value()))
            case self.T_TOP_SIPM:
                self.lineEdit_t_top_sipm.setText(str(self.horizontalSlider_T_top_sipm.value()))
        self.pushButton_OK_handler()


    def pushButton_OK_handler(self) -> None:

        #  Костыль, чтобы избавится от ошибки - переменная не определена
        T_decay_pips = ""
        T_rise_pips = ""
        T_top_pips = ""
        T_decay_sipm = ""
        T_rise_sipm = ""
        T_top_sipm = ""
        try:
            T_decay_pips = int(self.lineEdit_t_decay_pips.text())
            T_rise_pips = int(self.lineEdit_t_rise_pips.text())
            T_top_pips = int(self.lineEdit_t_top_pips.text())

            T_decay_sipm = int(self.lineEdit_t_decay_sipm.text())
            T_rise_sipm = int(self.lineEdit_t_rise_sipm.text())
            T_top_sipm = int(self.lineEdit_t_top_sipm.text())

        except ValueError as VErr:
            self.root.logger.debug(VErr)
            if isinstance(T_top_sipm, int) == False:
                T_top_sipm = 1
            if isinstance(T_decay_pips, int) == False:
                T_decay_pips = 1
            if isinstance(T_rise_pips, int) == False:
                T_rise_pips = 1
            if isinstance(T_top_pips, int) == False:
                T_top_pips = 1
            if isinstance(T_decay_sipm, int) == False:
                T_decay_sipm = 1
            if isinstance(T_rise_sipm, int) == False:
                T_rise_sipm = 1



        if self.checkBox_invert_pips.isChecked():
            invert_pips = 1
        else:
            invert_pips = 0
        if self.checkBox_invert_sipm.isChecked():
            invert_sipm = 1
        else:
            invert_sipm = 0
        # TODO: Необходма обработка ошибки, если введено ничего
        # self.main.logger.debug("T decay: " + str(self.main.T_decay_pips))
        # self.main.logger.debug("T rise: " + str(self.main.T_rise_pips))
        # self.main.logger.debug("T top: " + str(self.main.T_top_pips))
        # self.main.logger.debug("Invert: " + str(self.main.invert_pips))
        xpips, ypips = self.root.hex_to_list(self.root.data_pips)
        xsipm, ysipm = self.root.hex_to_list(self.root.data_sipm)
        xtr_pips, ytr_pips = self.root.trapezoid_calculater(xpips, ypips, 
                                                            T_decay_pips,
                                                            T_rise_pips,
                                                            T_top_pips,
                                                            invert_pips)
        xtr_sipm, ytr_sipm = self.root.trapezoid_calculater(xsipm, ysipm, 
                                                            T_decay_sipm, 
                                                            T_rise_sipm,
                                                            T_top_sipm,
                                                            invert_sipm)
        self.root.qt_plotter_trapezoid(xtr_pips, ytr_pips, xtr_sipm, ytr_sipm)

    def pushButton_pushButton_cancel_handler(self) -> None:
        self.close()
