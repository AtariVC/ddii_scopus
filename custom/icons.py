"""Загрузка SVG-иконок с перекраской под тему.

Иконки берутся из пакета ``qcustomwidgets`` (`assets/svg`), который стоит в
зависимостях с пином на коммит — см. ``[tool.uv.sources]`` в pyproject.toml.
Пин защищает от переименования/удаления иконок в апстриме: набор меняется
только при осознанном обновлении ``rev``.

Иконки залиты чёрным (``fill="#000000"``), поэтому на тёмной теме их нужно
перекрашивать — иначе они сливаются с фоном. Хелпер подменяет цвет прямо в
разметке SVG и рендерит результат в ``QIcon``.

    from custom.icons import load_svg_icon
    from dark_pro_widgets import theme

    button.setIcon(load_svg_icon("settings", theme.TEXT_DIM))

Имя иконки передаётся без расширения. Список доступных имён — ``available()``.
"""
from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

# Цвета, которыми залиты исходные SVG (SVG Repo отдаёт чёрный).
_SOURCE_COLORS = ("#000000", "#000", "black")

# Размер растра по умолчанию: с запасом под HiDPI, QIcon сам масштабирует вниз.
_DEFAULT_SIZE = 64


def _resolve_icon_dir() -> Path | None:
    """Каталог ``assets/svg`` внутри установленного qcustomwidgets.

    Пакет намеренно НЕ импортируется: его ``__init__`` тянет виджеты и
    ``qcustomwindow`` (тот ставится только под Windows, см. override-dependencies
    в pyproject.toml), а нам нужны исключительно файлы. ``find_spec`` находит
    расположение пакета, не исполняя его код.
    """
    try:
        spec = importlib.util.find_spec("qcustomwidgets")
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.origin:
        return None
    svg_dir = Path(spec.origin).parent / "assets" / "svg"
    return svg_dir if svg_dir.is_dir() else None


ICON_DIR = _resolve_icon_dir()


def icon_path(name: str) -> Path | None:
    """Путь к SVG по имени (с расширением или без); None — если пакета нет."""
    if ICON_DIR is None:
        return None
    return ICON_DIR / (name if name.endswith(".svg") else f"{name}.svg")


def available() -> list[str]:
    """Отсортированный список доступных имён иконок (без расширения)."""
    if ICON_DIR is None:
        return []
    return sorted(p.stem for p in ICON_DIR.glob("*.svg"))


@lru_cache(maxsize=256)
def load_svg_icon(name: str, color: str | None = None, size: int = _DEFAULT_SIZE) -> QIcon:
    """SVG → QIcon с перекраской в ``color`` (hex, напр. ``theme.TEXT_DIM``).

    Если пакет не установлен или иконки с таким именем нет — возвращает пустую
    QIcon: кнопка останется без картинки, но приложение не упадёт. Результат
    кешируется по (имя, цвет, размер).
    """
    path = icon_path(name)
    if path is None or not path.is_file():
        return QIcon()

    markup = path.read_text(encoding="utf-8")
    if color:
        for src in _SOURCE_COLORS:
            markup = markup.replace(f'"{src}"', f'"{color}"')

    renderer = QSvgRenderer(QByteArray(markup.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    return QIcon(pixmap)
