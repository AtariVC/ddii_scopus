from dynaconf import Dynaconf, Validator, ValidationError
from PyQt6.QtWidgets import QLineEdit, QMessageBox, QDoubleSpinBox
import PyQt6
import yaml
from pathlib import Path

# Настройка Dynaconf
settings = Dynaconf(
    settings_files=["config_dialog.yaml"],
)

class ConfigSaver():
    def __init__(self):
        pass
        # Инициализация полей QLineEdit
    def save_to_config(self, wd_dict: dict[str, float|int|str]) -> None:
        config_data: dict[str, float | int | str] = wd_dict
        settings_path: Path = Path(__file__).parent.joinpath("hvip_dialog.yaml")
        if not settings_path.exists():
                settings_path.touch()
        with open(str(settings_path), 'w', encoding='utf-8') as open_file:
            yaml.dump(config_data, open_file)
        open_file.close()

    def load_from_config(self, wd_dict: dict) -> None:
        settings_path = Path(__file__).parent.joinpath("hvip_dialog.yaml")

        if not settings_path.exists():
            QMessageBox.warning(None, "Ошибка", "Файл конфигурации не найден.")
            return
        # Чтение данных из YAML-файла
        with open(settings_path, "r", encoding="utf-8") as file:
            config_data = yaml.safe_load(file)

        for (key, val) in wd_dict.items():
            if type(val) == type(PyQt6.QtWidgets.QDoubleSpinBox):
                val.setValue(config_data.get(key, "")) # type: ignore
            if type(val) == type(QLineEdit):
                val.setText(config_data.get(key, "")) # type: ignore
        file.close()

