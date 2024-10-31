from dynaconf import Dynaconf, Validator, ValidationError
from PyQt6.QtWidgets import QLineEdit, QMessageBox
from main_config_dialog import MainConfigDialog

# Настройка Dynaconf с валидаторами
settings = Dynaconf(
    settings_files=["settings.yaml"],
    validators=[
        Validator("01_hh_l", must_exist=True, is_type_of=int, lte=4096, gt=0),
        Validator("05_hh_l", must_exist=True, is_type_of=int, lte=4096, gt=0),
        Validator("08_hh_l", must_exist=True, is_type_of=int, lte=4096, gt=0),
        Validator("1_6_hh_l", must_exist=True, is_type_of=int, lte=4096, gt=0),
        Validator("3_hh_l", must_exist=True, is_type_of=int, lte=4096, gt=0),
        Validator("5_hh_l", must_exist=True, is_type_of=int, lte=4096, gt=0),
        Validator("10_hh_l", must_exist=True, is_type_of=int, lte=4096, gt=0),
        Validator("30_hh_l", must_exist=True, is_type_of=int, lte=4096, gt=0),
        Validator("60_hh_l", must_exist=True, is_type_of=int, lte=4096, gt=0),
        
        Validator("hvip_cfg_pwm_pips", must_exist=True, is_type_of=float),
        Validator("hvip_cfg_vlt_pips", must_exist=True, is_type_of=float),
        
        Validator("hvip_cfg_pwm_sipm", must_exist=True, is_type_of=float),
        Validator("hvip_cfg_vlt_sipm", must_exist=True, is_type_of=float),
        
        Validator("hvip_cfg_pwm_ch", must_exist=True, is_type_of=float),
        Validator("hvip_cfg_vlt_ch", must_exist=True, is_type_of=float),
        
        Validator("interval_measure", must_exist=True, is_type_of=int, gt=0),
        Validator("mpp_id", must_exist=True, is_type_of=int)
    ]
)

class ConfigSaver(MainConfigDialog):
    def __init__(self):
        pass

    def save_to_config(self):
        # Считывание данных с QLineEdit и конвертация их в нужный формат
        config_data = {
            "01_hh_l": int(self.lineEdit_lvl_0_1.text()),
            "05_hh_l": int(self.lineEdit_lvl_0_5.text()),
            "08_hh_l": int(self.lineEdit_lvl_0_8.text()),
            "1_6_hh_l": int(self.lineEdit_lvl_1_6.text()),
            "3_hh_l": int(self.lineEdit_lvl_3.text()),
            "5_hh_l": int(self.lineEdit_lvl_5.text()),
            "10_hh_l": int(self.lineEdit_lvl_10.text()),
            "30_hh_l": int(self.lineEdit_lvl_30.text()),
            "60_hh_l": int(self.lineEdit_lvl_60.text()),
            "hvip_cfg_pwm_pips": float(self.lineEdit_pwm_pips.text()),
            "hvip_cfg_vlt_pips": float(self.lineEdit_hvip_pips.text()),
            "hvip_cfg_pwm_sipm": float(self.lineEdit_pwm_sipm.text()),
            "hvip_cfg_vlt_sipm": float(self.lineEdit_hvip_sipm.text()),
            "hvip_cfg_pwm_ch": float(self.lineEdit_pwm_ch.text()),
            "hvip_cfg_vlt_ch": float(self.lineEdit_hvip_ch.text()),
            "interval_measure": int(self.lineEdit_interval.text()),
            "mpp_id": int(self.lineEdit_cfg_mpp_id.text())
        }

        # Валидация данных перед сохранением
        try:
            settings.validators.validate(config_data)  # Проверка по валидаторам Dynaconf
        except ValidationError as e:
            QMessageBox.warning(None, "Ошибка валидации", f"Ошибка: {e}")
            return

        # Сохранение валидных данных в settings.yaml
        settings.update(config_data)
        settings.store()  # Сохраняет в указанный файл settings.yaml
        QMessageBox.information(None, "Сохранение", "Конфигурация успешно сохранена.")
