from __future__ import annotations

from pathlib import Path
from typing import List

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QWidget
from qtpy.uic import loadUi

from dark_pro_widgets.core import theme
from dark_pro_widgets.widgets.controls import CheckBox, IconButton, LineEdit, PrimaryButton

_MONO = theme.MONO_FAMILY.split(",")[0].strip()


class FilterViewerWidget(QWidget):
    """Фильтр кадров для Viewer: порог + выбор каналов + навигация.

    Ожидает, что родитель передан как MainUIRenderer и содержит graph_viewer_widget.
    Список найденных кадров (``listWidget_times``) здесь только размещается и
    стилизуется — его наполнение вынесено в отдельную библиотеку.
    """

    label_found: QtWidgets.QLabel
    label_save: QtWidgets.QLabel
    checkBox_pips: CheckBox
    lineEdit_threshold_pips: LineEdit
    checkBox_sipm: CheckBox
    lineEdit_threshold_sipm: LineEdit
    pushButton_filter: PrimaryButton
    pushButton_prev: IconButton
    pushButton_next: IconButton
    listWidget_times: QtWidgets.QListWidget
    pushButton_save_frame: PrimaryButton
    lineEdit_num_frame: LineEdit

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mw = parent  # MainUIRenderer or None
        loadUi(Path(__file__).parent.joinpath("filter_viewer_widget.ui"), self)
        self._matched: List[int] = []  # 1-based индексы кадров
        # подписка нужна только когда есть настоящий viewer (в приложении);
        # при автономном запуске parent=None — просто пропускаем
        _gw = self._viewer()
        if _gw is not None:
            _gw.slider_update_event.subscribe(lambda val: self.lineEdit_num_frame.setText(str(val)))  # type: ignore
        self._pos: int = -1

        self._implement_style()
        self._wire()

    def _implement_style(self):
        # варианты и глифы кнопок (тема их не задаёт)
        self.pushButton_prev.setGlyph("chevron_left")
        self.pushButton_next.setGlyph("chevron_right")
        self.pushButton_filter.setVariant("accent")
        self.pushButton_save_frame.setVariant("blue")

        # счётчик найденного и подпись сохранения — приглушённый моно
        for lbl in (self.label_found, self.label_save):
            lbl.setStyleSheet(
                f"color: {theme.TEXT_DIM}; font-family: '{_MONO}'; font-size: 13px; "
                "background: transparent; border: none;"
            )

        # карточка списка: рамка со скруглением, отступы, подсветка выбранного
        self.listWidget_times.setStyleSheet(
            f"""
            QListWidget {{
                background-color: {theme.FIELD_BG};
                border: 1px solid {theme.BORDER};
                border-radius: 8px;
                padding: 6px;
                outline: none;
                color: {theme.TEXT};
                font-family: '{_MONO}';
            }}
            QListWidget::item {{ padding: 8px 10px; border-radius: 6px; }}
            QListWidget::item:selected {{
                background-color: {theme.rgba(theme.ACCENT, 40)};
                color: {theme.TEXT};
            }}
            QListWidget::item:hover {{ background-color: {theme.rgba(theme.ACCENT, 18)}; }}
            """
        )

    def _wire(self) -> None:
        self.pushButton_filter.clicked.connect(self._on_filter)
        self.pushButton_prev.clicked.connect(lambda: self._step(-1))
        self.pushButton_next.clicked.connect(lambda: self._step(+1))
        self.listWidget_times.itemClicked.connect(self._on_pick)
        self.pushButton_save_frame.clicked.connect(self._save_frame)

    def _save_frame(self):
        num_frame: int = int(self.lineEdit_num_frame.text())
        self._mw.graph_viewer_widget.save_desired_frame_hdf5(num_frame) # type: ignore

    def _viewer(self):
        return getattr(self._mw, "graph_viewer_widget", None)

    def _on_filter(self):
        gv = self._viewer()
        if gv is None:
            return
        matched = self._run_filter(gv)
        if matched is None:
            # ввод не прошёл проверку — предупреждение показано, список не трогаем
            return
        self._populate_list([(idx, f"кадр #{idx:04d}", str(gv.get_time_for_index(idx))) for idx in matched])
        # перейти к первому совпадению
        if self._pos != -1:
            gv.go_to_index(self._matched[self._pos])

    def _run_filter(self, gv) -> list[int] | None:
        """Проверить галочки/пороги и вернуть индексы подходящих кадров.

        Фильтр идёт по каждому *включённому* каналу (галочке):

        * ни одна галочка не выбрана — предупреждение, ``None``;
        * для каждого включённого канала порог обязателен; если он пустой или
          не число — предупреждение со списком незаполненных порогов, ``None``;
        * иначе — совпадение по всем включённым каналам сразу (две галочки — оба
          условия, одна — только своё), невыбранные каналы игнорируются.
        """
        use_pips = self.checkBox_pips.isChecked()
        use_sipm = self.checkBox_sipm.isChecked()

        if not (use_pips or use_sipm):
            self._warn("Выберите канал",
                       "Отметьте хотя бы один канал (SiPM или PIPS) для фильтрации.")
            return None

        lvl_pips = self._read_threshold(self.lineEdit_threshold_pips) if use_pips else None
        lvl_sipm = self._read_threshold(self.lineEdit_threshold_sipm) if use_sipm else None

        missing = [name for name, use, lvl in
                   (("SiPM", use_sipm, lvl_sipm), ("PIPS", use_pips, lvl_pips))
                   if use and lvl is None]
        if missing:
            self._warn("Укажите порог",
                       "Укажите порог для: " + ", ".join(missing) + ".")
            return None

        return gv.apply_filter(lvl_pips, lvl_sipm, use_pips, use_sipm)

    @staticmethod
    def _read_threshold(line_edit: LineEdit) -> int | None:
        """Разобрать целочисленный порог из поля. ``None`` — пусто или не число."""
        text = line_edit.text().strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None

    def _warn(self, title: str, text: str) -> None:
        QtWidgets.QMessageBox.warning(self, title, text)

    def _populate_list(self, rows: List[tuple[int, str, str]]) -> None:
        """Только наполнение списка: заполнить ``listWidget_times`` и счётчик найденного.

        ``rows`` — тройки ``(индекс_кадра, заголовок, значения)``. Заголовок рисуется
        обычным цветом текста, значения пика — приглушённым (как на макете). Индексы
        сохраняются в ``self._matched`` для навигации prev/next и клика по строке.
        """
        self._matched = [idx for idx, _, _ in rows]
        self._pos = 0 if self._matched else -1
        self.label_found.setText(f"Найдено {len(self._matched)} кадров")
        self.listWidget_times.clear()
        for _idx, title, detail in rows:
            item = QtWidgets.QListWidgetItem()
            label = self._make_row_label(title, detail)
            # прибавляем вертикальные отступы QListWidget::item (padding 8px сверху/снизу),
            # иначе виджет строки сплющивается до ~6px и текст не виден
            hint = label.sizeHint()
            item.setSizeHint(QSize(hint.width(), hint.height() + 16))
            self.listWidget_times.addItem(item)
            self.listWidget_times.setItemWidget(item, label)
        if self._pos != -1:
            self.listWidget_times.setCurrentRow(self._pos)

    def _make_row_label(self, title: str, detail: str) -> QtWidgets.QLabel:
        """Строка списка: заголовок обычным цветом + приглушённые значения справа.

        Двухцветный текст в одной строке ``QListWidget`` возможен только через
        собственный виджет — берём ``QLabel`` с rich-text (без ручных layout'ов).
        Клик прозрачно проходит на элемент списка, чтобы работали выбор и навигация.
        """
        label = QtWidgets.QLabel()
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setText(
            "<table width='100%' cellspacing='0' cellpadding='0'><tr>"
            f"<td align='left'><span style=\"color:{theme.TEXT}; font-weight:600;\">{title}</span></td>"
            f"<td align='right'><span style=\"color:{theme.TEXT_DIM};\">{detail}</span></td>"
            "</tr></table>"
        )
        label.setStyleSheet(
            f"background: transparent; border: none; font-family: '{_MONO}'; "
            "font-size: 13px; padding: 2px 2px;"
        )
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        return label

    def load_demo_data(self) -> None:
        """Заполнить список демонстрационными кадрами (для автономного превью)."""
        samples = [
            (88, 0.81, 0.29),
            (124, 0.92, 0.44),
            (301, 0.77, 0.35),
            (455, 1.04, 0.51),
            (620, 0.83, 0.30),
        ]
        self._populate_list([
            (idx, f"кадр #{idx:04d}", f"PIPS {pips:.2f} · SiPM {sipm:.2f}")
            for idx, sipm, pips in samples
        ])

    def _step(self, step: int):
        gv = self._viewer()
        if gv is None or not self._matched:
            return
        self._pos = max(0, min(len(self._matched) - 1, self._pos + step))
        self.lineEdit_num_frame.setText(str(self._pos))
        gv.go_to_index(self._matched[self._pos])
        try:
            self.listWidget_times.setCurrentRow(self._pos)
        except Exception:
            ...

    def _on_pick(self, _item):
        gv = self._viewer()
        if gv is None:
            return
        row = self.listWidget_times.currentRow()
        if 0 <= row < len(self._matched):
            self._pos = row
            gv.go_to_index(self._matched[self._pos])

if __name__ == "__main__":
    from dark_pro_widgets.core._preview import preview

    def _build() -> FilterViewerWidget:
        widget = FilterViewerWidget()
        widget.load_demo_data()
        return widget

    preview(_build, title="Фильтр кадров — demo", size=(340, 560), stretch=False)
