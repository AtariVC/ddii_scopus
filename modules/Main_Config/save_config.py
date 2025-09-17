from dynaconf import Dynaconf, Validator, ValidationError
from PyQt6.QtWidgets import QLineEdit, QMessageBox
import yaml
from pathlib import Path

# Настройка Dynaconf
settings = Dynaconf(
    settings_files=["config_dialog.yaml"],
)

class ConfigSaver():
    def __init__(self, *args):
        # Инициализация полей QLineEdit
        self.wd = args[0]
    def save_to_config(self):
        config_data = {
            "01_hh_l": int(self.wd.lineEdit_lvl_0_1.text()),
            "05_hh_l": int(self.wd.lineEdit_lvl_0_5.text()),
            "08_hh_l": int(self.wd.lineEdit_lvl_0_8.text()),
            "1_6_hh_l": int(self.wd.lineEdit_lvl_1_6.text()),
            "3_hh_l": int(self.wd.lineEdit_lvl_3.text()),
            "5_hh_l": int(self.wd.lineEdit_lvl_5.text()),
            "10_hh_l": int(self.wd.lineEdit_lvl_10.text()),
            "30_hh_l": int(self.wd.lineEdit_lvl_30.text()),
            "60_hh_l": int(self.wd.lineEdit_lvl_60.text()),

            "hvip_cfg_pwm_pips": float(self.wd.lineEdit_pwm_pips.text()),
            "hvip_cfg_vlt_pips": float(self.wd.lineEdit_hvip_pips.text()),

            "hvip_cfg_pwm_sipm": float(self.wd.lineEdit_pwm_sipm.text()),
            "hvip_cfg_vlt_sipm": float(self.wd.lineEdit_hvip_sipm.text()),

            "hvip_cfg_pwm_ch": float(self.wd.lineEdit_pwm_ch.text()),
            "hvip_cfg_vlt_ch": float(self.wd.lineEdit_hvip_ch.text()),

            "interval_measure": int(self.wd.lineEdit_interval.text()),
            "mpp_id": int(self.wd.lineEdit_cfg_mpp_id.text()),

            "lineEdit_pwm_max_ch"   : float(self.wd.lineEdit_pwm_max_ch.text()),
            "lineEdit_pwm_max_pips" : float(self.wd.lineEdit_pwm_max_pips.text()),
            "lineEdit_pwm_max_sipm" : float(self.wd.lineEdit_pwm_max_sipm.text())    

        }
        settings_path = Path(__file__).parent.joinpath("config_dialog.yaml")
        if not settings_path.exists():
                settings_path.touch()
        with open(str(settings_path), 'w', encoding='utf-8') as open_file:
            yaml.dump(config_data, open_file)
        open_file.close()
        
    def load_from_config(self):
        settings_path = Path(__file__).parent.joinpath("config_dialog.yaml")

        if not settings_path.exists():
                QMessageBox.warning(None, "Ошибка", "Файл конфигурации не найден.")
                return
        # Чтение данных из YAML-файла
        with open(settings_path, "r", encoding="utf-8") as file:
            config_data = yaml.safe_load(file)

        self.wd.lineEdit_lvl_0_1.setText(str(config_data.get("01_hh_l", "")))
        self.wd.lineEdit_lvl_0_5.setText(str(config_data.get("05_hh_l", "")))
        self.wd.lineEdit_lvl_0_8.setText(str(config_data.get("08_hh_l", "")))
        self.wd.lineEdit_lvl_1_6.setText(str(config_data.get("1_6_hh_l", "")))
        self.wd.lineEdit_lvl_3.setText(str(config_data.get("3_hh_l", "")))
        self.wd.lineEdit_lvl_5.setText(str(config_data.get("5_hh_l", "")))
        self.wd.lineEdit_lvl_10.setText(str(config_data.get("10_hh_l", "")))
        self.wd.lineEdit_lvl_30.setText(str(config_data.get("30_hh_l", "")))
        self.wd.lineEdit_lvl_60.setText(str(config_data.get("60_hh_l", "")))

        self.wd.lineEdit_pwm_pips.setText(str(config_data.get("hvip_cfg_pwm_pips", "")))
        self.wd.lineEdit_hvip_pips.setText(str(config_data.get("hvip_cfg_vlt_pips", "")))

        self.wd.lineEdit_pwm_sipm.setText(str(config_data.get("hvip_cfg_pwm_sipm", "")))
        self.wd.lineEdit_hvip_sipm.setText(str(config_data.get("hvip_cfg_vlt_sipm", "")))

        self.wd.lineEdit_pwm_ch.setText(str(config_data.get("hvip_cfg_pwm_ch", "")))
        self.wd.lineEdit_hvip_ch.setText(str(config_data.get("hvip_cfg_vlt_ch", "")))

        self.wd.lineEdit_interval.setText(str(config_data.get("interval_measure", "")))
        self.wd.lineEdit_cfg_mpp_id.setText(str(config_data.get("mpp_id", "")))

        self.wd.lineEdit_pwm_max_ch.setText(str(config_data.get("lineEdit_pwm_max_ch", "")))
        self.wd.lineEdit_pwm_max_pips.setText(str(config_data.get("lineEdit_pwm_max_pips", "")))
        self.wd.lineEdit_pwm_max_sipm.setText(str(config_data.get("lineEdit_pwm_max_sipm", "")))
        file.close()

