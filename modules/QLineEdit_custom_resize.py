from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtCore import QSize


class AutoSizeLineEdit(QLineEdit):
    """
    Простая реализация QLineEdit, которая подстраивает минимальную ширину
    под текущий текст (чтобы соответствовать промоуту из .ui).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self._auto_resize)
        # Первичная подстройка
        self._auto_resize()

    def _auto_resize(self):
        fm = QFontMetrics(self.font())
        text = self.text() or " "
        content_width = fm.horizontalAdvance(text)
        margins = self.textMargins()
        # Немного отступа для курсора/рамки
        padding = 20
        self.setMinimumWidth(content_width + margins.left() + margins.right() + padding)

