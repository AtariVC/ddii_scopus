import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class _LoggerLike(Protocol):
    def error(self, message: str) -> object:
        ...


@dataclass(slots=True)
class DDIIControlDefaults:
    data: dict
    path: Path

    DEFAULTS_PATH = Path(__file__).with_name("ddii_control_defaults.json")

    # Чтение и нормализация JSON.
    @classmethod
    def load(cls, logger: _LoggerLike | None = None, path: Path | None = None) -> "DDIIControlDefaults":
        defaults_path = path or cls.DEFAULTS_PATH
        try:
            with defaults_path.open("r", encoding="utf-8") as open_file:
                data = json.load(open_file)
            if not isinstance(data, dict):
                data = {}
        except Exception as exc:
            if logger is not None:
                logger.error(f"Не удалось загрузить {defaults_path.name}: {exc}")
            data = {}
        return cls(data=data, path=defaults_path)

    def section(self, section_name: str) -> dict:
        section = self.data.get(section_name, {})
        return section if isinstance(section, dict) else {}

    def _coerce_int(self, value: object, fallback: int, minimum: int | None = None) -> int:
        try:
            result = int(value)
        except Exception:
            result = fallback
        if minimum is not None:
            result = max(minimum, result)
        return result

    def _coerce_float(self, value: object, fallback: float) -> float:
        try:
            return float(value)
        except Exception:
            return fallback

    # Уровни и HH.
    @property
    def level_01(self) -> int:
        return self._coerce_int(self.section("levels").get("level_0_1"), 80, minimum=0)

    def levels_in_kev(self) -> bool:
        return str(self.section("levels").get("display_unit", "lsb")).strip().lower() == "kev"

    def coeff_value(self, coeff_name: str) -> int:
        coeffs = self.section("levels").get("coefficients_lsb_per_kev", {})
        coeff_value = coeffs.get(coeff_name) if isinstance(coeffs, dict) else None
        return self._coerce_int(coeff_value, 1, minimum=1)

    def hh_default_kev_values(self, hh_count: int) -> list[int]:
        hh_values = self.section("levels").get("hh_default_kev", [])
        if not isinstance(hh_values, list):
            hh_values = []
        normalized = [self._coerce_int(value, 0, minimum=0) for value in hh_values[:hh_count]]
        if len(normalized) < hh_count:
            normalized.extend([0] * (hh_count - len(normalized)))
        return normalized

    def hh_default_lsb_values(self, hh_count: int, ppd_hh_numbers: set[int] | frozenset[int]) -> list[int]:
        ppd_coeff = self.coeff_value("ppd")
        scd_coeff = self.coeff_value("scd")
        hh_values_lsb: list[int] = []
        for hh_number, hh_value_kev in enumerate(self.hh_default_kev_values(hh_count), start=1):
            coeff = ppd_coeff if hh_number in ppd_hh_numbers else scd_coeff
            hh_values_lsb.append(hh_value_kev // coeff)
        return hh_values_lsb

    # Питание.
    def float_value(self, group_name: str, channel_name: str) -> float:
        group = self.section("power").get(group_name, {})
        value = group.get(channel_name) if isinstance(group, dict) else 0.0
        return self._coerce_float(value, 0.0)

    def float_text(self, group_name: str, channel_name: str) -> str:
        return f"{self.float_value(group_name, channel_name):.2f}"

    # Общие настройки.
    @property
    def interval_text(self) -> str:
        return str(self._coerce_int(self.section("common").get("interval_request"), 0, minimum=0))

    def filter_items(self) -> list[dict[str, str]]:
        default_items = [
            {"id": "none", "label": "нет"},
            {"id": "median", "label": "медианный"},
            {"id": "bypass_lp", "label": "ФНЧ"},
            {"id": "bypass_hp", "label": "ФВЧ"},
        ]
        items = self.section("common").get("filters", [])
        if not isinstance(items, list):
            return default_items
        normalized: list[dict[str, str]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            filter_id = str(item.get("id", "")).strip()
            label = str(item.get("label", "")).strip()
            if filter_id and label:
                normalized.append({"id": filter_id, "label": label})
        return normalized or default_items

    @property
    def default_filter_id(self) -> str:
        return str(self.section("common").get("default_filter_id", "none"))
