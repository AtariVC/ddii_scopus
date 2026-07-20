"""Точка входа консоли ддии.

Окно показывается с системной рамкой. qtmodern намеренно не используется:
его ``ModernWindow`` подменяет рамку своей (отсюда чужеродный заголовок) и сам
реализует изменение размера, которое на Windows не работает. Тема — глобальный
QSS палитры ddii, цвет системного заголовка на Windows подгоняется в
``MainUIRenderer`` (см. ``_tint_titlebar``).
"""
import asyncio
import sys

import qasync
from PyQt6 import QtWidgets

from dark_pro_widgets import qss

from app.ui.window_linker_new import MainUIRenderer

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())

    w: MainUIRenderer = MainUIRenderer()

    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    w.show()

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...
